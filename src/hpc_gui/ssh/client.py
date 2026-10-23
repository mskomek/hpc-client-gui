from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Callable, Optional, Tuple

import socket

from hpc_gui.core.debug_support import timed

import paramiko

from hpc_gui.core.logging import get_logger
from hpc_gui.core.paths import app_data_dir
from hpc_gui.ssh.auth_strategy import (
    _ConnectionAuthStrategy as _BaseConnectionAuthStrategy,
    _KeyboardInteractiveSource,  # noqa: F401 - compatibility re-export
    _PasswordSource,  # noqa: F401 - compatibility re-export
    NoAuthenticationCredentialError,
    _agent_key_sources,
    _discoverable_key_sources,
    load_private_key_with_certificate,
)
from hpc_gui.ssh.contracts import (
    SSHConnInfo,
    SocketLike,
    _KEEPALIVE_INTERVAL_DEFAULT,
    _SSH_AUTH_TIMEOUT_SECONDS,
    _SSH_BANNER_TIMEOUT_SECONDS,
    _SSH_CHANNEL_TIMEOUT_SECONDS,
    _SSH_CONNECT_AND_KEX_TIMEOUT_SECONDS,
    coerce_keepalive_interval,
)
from hpc_gui.ssh.host_keys import (
    HostKeyChangedError,
    HostKeyInfo,  # noqa: F401 - compatibility re-export
    HostKeyRejectedError,  # noqa: F401 - compatibility re-export
    configure_known_hosts,
)
from hpc_gui.services.command_history_store import is_sensitive_command
from hpc_gui.ssh.sftp_channels import (
    SFTPChannelManager,
    _SFTP_LISTING_TIMEOUT_SECONDS,  # noqa: F401  (re-exported facade constant)
    _SFTP_TRANSFER_TIMEOUT_SECONDS,  # noqa: F401  (re-exported facade constant)
)
from hpc_gui.ssh.retry import retry_ssh_connection
from hpc_gui.ssh.shell_session import InteractiveShellSession, _sanitize_terminal_text
from hpc_gui.ssh.text import decode_remote_text as _decode_remote_text

class _ConnectionAuthStrategy(_BaseConnectionAuthStrategy):
    """Compatibility facade keeping legacy source-injection hooks stable."""

    def __init__(self, info: SSHConnInfo, pkey=None):
        super().__init__(
            info,
            pkey,
            agent_key_sources=_agent_key_sources,
            discoverable_key_sources=_discoverable_key_sources,
        )


class SSHClientWrapper:
    def __init__(
        self,
        info: Optional[SSHConnInfo] = None,
        logger: Optional[Callable[[str], None]] = None,
        log_cb: Optional[Callable[[str], None]] = None,
        shell_output_cb: Optional[Callable[[str], None]] = None,
        disconnect_cb: Optional[Callable[[str], None]] = None,
    ):
        # Accept both `logger` and legacy `log_cb` kwarg.
        # Also allow passing SSHConnInfo as first positional arg (info).
        self.info: Optional[SSHConnInfo] = info
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp = None
        self._jump_connection: Optional[object] = None
        self._sftp_channels = SFTPChannelManager(
            self._active_transport, log=self.log, opener=lambda: self.open_transfer_sftp()
        )
        self._shell_session: Optional[InteractiveShellSession] = None
        self._shell_geometry: Tuple[int, int] = (120, 40)
        self._log = logger or log_cb
        self._shell_output_cb = shell_output_cb
        self._disconnect_cb = disconnect_cb
        self._filelog = get_logger("hpc_gui.ssh")

    def log(self, msg: str) -> None:
        # File log
        try:
            self._filelog.info(msg)
        except Exception:
            pass
        # UI log (if provided)
        if self._log:
            try:
                self._log(msg)
            except Exception:
                pass

    def _active_transport(self):
        """Active Paramiko transport for the channel manager (may be None)."""
        return self.client.get_transport() if self.client else None

    def _discard_partial_client(self) -> None:
        """Drop a partially connected target client and all jump resources."""
        try:
            if self.client is not None:
                close = getattr(self.client, "close", None)
                if callable(close):
                    close()
        finally:
            self.client = None
        self._close_jump_connection()

    # ---------- interactive shell facade ----------
    # The lifecycle lives in InteractiveShellSession; these bridges keep the
    # historical attribute surface (tests inject channels/decoders directly).

    def _ensure_shell_session(self) -> InteractiveShellSession:
        if self._shell_session is None:
            self._shell_session = InteractiveShellSession(
                invoke_shell=self._invoke_shell,
                geometry=self._shell_geometry,
                on_output=self._shell_output_cb,
                on_disconnect=self._on_shell_unexpected_disconnect,
                log=self.log,
            )
        return self._shell_session

    def _invoke_shell(self, **kwargs):
        assert self.client is not None
        return self.client.invoke_shell(**kwargs)

    def _on_shell_unexpected_disconnect(self, reason: str) -> None:
        try:
            self.close()
        except Exception:
            pass
        self._notify_disconnect(reason)

    @property
    def _shell_channel(self):
        return self._shell_session.channel if self._shell_session else None

    @_shell_channel.setter
    def _shell_channel(self, channel) -> None:
        if channel is None:
            if self._shell_session is not None:
                self._shell_session.channel = None
            return
        session = self._ensure_shell_session()
        session.channel = channel

    @property
    def _shell_decoder(self):
        return self._ensure_shell_session().decoder

    @_shell_decoder.setter
    def _shell_decoder(self, decoder) -> None:
        self._ensure_shell_session().decoder = decoder

    def connect(
        self,
        info: Optional[SSHConnInfo] = None,
        *,
        shell_size: Optional[Tuple[int, int]] = None,
    ) -> None:
        retry_ssh_connection(
            lambda: self._connect_once(info, shell_size=shell_size),
            on_retry=self.log,
        )

    def _connect_once(
        self,
        info: Optional[SSHConnInfo] = None,
        *,
        shell_size: Optional[Tuple[int, int]] = None,
    ) -> None:
        info = info or self.info
        if info is None:
            raise ValueError('SSH connection info not provided')
        target = f"{info.username}@{info.host}" if info.username else info.host
        self.log(f"SSH: connecting to {target}:{info.port} ...")
        self.client = paramiko.SSHClient()
        known_hosts_path = (
            Path(info.known_hosts_path)
            if info.known_hosts_path
            else app_data_dir() / "known_hosts"
        )
        policy = configure_known_hosts(
            self.client,
            known_hosts_path,
            getattr(info, "host_key_policy", "accept-new"),
            info.host_key_decision,
        )
        if policy == "strict":
            self.log("SSH: host key policy = strict")
        else:
            self.log("SSH: host key policy = accept-new")

        timeout = info.timeout if info.timeout is not None else _SSH_CONNECT_AND_KEX_TIMEOUT_SECONDS
        banner_timeout = info.timeout if info.timeout is not None else _SSH_BANNER_TIMEOUT_SECONDS
        auth_timeout = info.timeout if info.timeout is not None else _SSH_AUTH_TIMEOUT_SECONDS
        channel_timeout = info.timeout if info.timeout is not None else _SSH_CHANNEL_TIMEOUT_SECONDS

        # One-hop jump host: open a direct-tcpip channel through the bastion
        # and feed it to the target connect as a preconnected socket.
        sock: Optional[SocketLike] = info.preconnected_socket
        jump = getattr(info, "jump", None)
        if jump is not None and getattr(jump, "enabled", False) and sock is None:
            from hpc_gui.ssh.jump import JumpConnection  # local: avoids import cycle

            jump_connection = JumpConnection(
                jump,
                target_host=info.host,
                target_port=info.port,
                known_hosts_path=str(known_hosts_path),
                host_key_decision=info.host_key_decision,
                log=self.log,
            )
            self._jump_connection = jump_connection
            try:
                sock = jump_connection.open()
                self.log(
                    f"SSH: connecting target through jump ({info.host}:{info.port})"
                )
            except Exception:
                self._jump_connection = None
                raise
        connection_kwargs = ({"sock": sock} if sock is not None else {})

        try:
            pkey = None
            if info.key_path:
                self.log("SSH: using configured key")
                pkey = load_private_key_with_certificate(
                    info.key_path, info.password or None
                )
            auth_strategy = None
            if info.keyboard_interactive_handler is not None:
                auth_strategy = _ConnectionAuthStrategy(info, pkey)
            self.log("SSH: negotiating transport and authenticating")
            if auth_strategy is not None:
                self.client.connect(
                    hostname=info.host,
                    port=info.port,
                    username=info.username or None,
                    timeout=timeout,
                    banner_timeout=banner_timeout,
                    auth_timeout=auth_timeout,
                    channel_timeout=channel_timeout,
                    auth_strategy=auth_strategy,
                    **connection_kwargs,
                )
            elif info.key_path:
                self.client.connect(
                    hostname=info.host,
                    port=info.port,
                    username=info.username or None,
                    pkey=pkey,
                    timeout=timeout,
                    banner_timeout=banner_timeout,
                    auth_timeout=auth_timeout,
                    channel_timeout=channel_timeout,
                    allow_agent=info.allow_agent,
                    look_for_keys=info.look_for_keys,
                    **connection_kwargs,
                )
            else:
                self.client.connect(
                    hostname=info.host,
                    port=info.port,
                    username=info.username or None,
                    password=info.password or None,
                    timeout=timeout,
                    banner_timeout=banner_timeout,
                    auth_timeout=auth_timeout,
                    channel_timeout=channel_timeout,
                    allow_agent=info.allow_agent,
                    look_for_keys=info.look_for_keys,
                    **connection_kwargs,
                )
        except paramiko.BadHostKeyException as exc:
            # Target host-key change: drop the partial target client and
            # all jump resources before propagating.
            self._discard_partial_client()
            raise HostKeyChangedError(exc.hostname) from exc
        except paramiko.SSHException as exc:
            # Target connect/auth failure after a jump channel exists:
            # drop the partial target client and all jump resources.
            self._discard_partial_client()
            if (
                "no authentication methods" in str(exc).lower()
                and not info.password
                and not info.key_path
                and info.keyboard_interactive_handler is None
            ):
                # Truthful classification: nothing was ever offered to the
                # server, so this is a missing-credential failure, not a
                # rejected credential.
                raise NoAuthenticationCredentialError() from exc
            raise
        except Exception:
            self._discard_partial_client()
            raise
        self.log("SSH: authentication completed")
        transport = self.client.get_transport()
        if transport is not None:
            banner = transport.get_banner()
            if banner:
                if isinstance(banner, bytes):
                    banner = _decode_remote_text(banner)
                self.log(str(banner).rstrip("\r\n"))
            keepalive = coerce_keepalive_interval(
                getattr(info, "keepalive_interval_seconds", _KEEPALIVE_INTERVAL_DEFAULT)
            )
            transport.set_keepalive(keepalive)
            if keepalive > 0:
                self.log(f"SSH: keepalive interval = {keepalive}s")
            else:
                self.log("SSH: keepalive disabled")
        if shell_size is not None:
            cols, rows = shell_size
            self._shell_geometry = (max(1, int(cols)), max(1, int(rows)))
        try:
            self.log("SSH: opening remote shell and SFTP")
            self._start_shell_session()
            self.sftp = self.client.open_sftp()
        except Exception:
            # Shell/SFTP initialization failure: full target + jump cleanup.
            self.close()
            raise
        self.log("SSH: connected, SFTP ready")

    def _start_shell_session(self) -> None:
        if not self.client:
            return
        self._stop_shell_session()
        transport = self.client.get_transport()
        if transport is None or not transport.is_active():
            return
        session = InteractiveShellSession(
            invoke_shell=self._invoke_shell,
            geometry=self._shell_geometry,
            on_output=self._shell_output_cb,
            on_disconnect=self._on_shell_unexpected_disconnect,
            log=self.log,
            defer_output=self._shell_output_cb is not None,
        )
        if not session.start():
            return
        self._shell_session = session

    def activate_shell_output(self) -> None:
        """Release shell startup output after a terminal view subscribes."""
        if self._shell_session is not None:
            self._shell_session.activate_output()

    def resize_shell_pty(self, cols: int, rows: int) -> None:
        cols = max(1, int(cols))
        rows = max(1, int(rows))
        self._shell_geometry = (cols, rows)
        if self._shell_session is not None:
            self._shell_session.resize(cols, rows)

    def send_shell_text(self, text: str) -> bool:
        return self._ensure_shell_session().send_text(text)

    def send_shell_input(self, data: str) -> bool:
        return self._ensure_shell_session().send_input(data)

    def _send_shell_payload(self, payload: bytes) -> bool:
        return self._ensure_shell_session().send_payload(payload)

    def _decode_shell_bytes(self, data: bytes, *, final: bool = False) -> None:
        self._ensure_shell_session().decode_bytes(data, final=final)

    def _stop_shell_session(self) -> None:
        if self._shell_session is not None:
            try:
                self._shell_session.stop()
            finally:
                self._shell_session = None

    def _notify_disconnect(self, reason: str) -> None:
        if not self._disconnect_cb:
            return
        try:
            from hpc_gui.core.i18n import t
            self._disconnect_cb(reason or t("login.ssh_disconnected"))
        except Exception:
            pass

    def _close_jump_connection(self) -> None:
        """Close the jump channel/client; safe and idempotent."""
        jump_connection = self._jump_connection
        self._jump_connection = None
        if jump_connection is None:
            return
        try:
            close = getattr(jump_connection, "close", None)
            if callable(close):
                close()
        except Exception:
            pass

    def close(self) -> None:
        self.log("SSH: closing")
        try:
            self._stop_shell_session()
        except Exception:
            pass
        try:
            self._drop_listing_sftp()
        except Exception:
            pass
        try:
            if self.sftp:
                self.sftp.close()
        finally:
            self.sftp = None
        try:
            if self.client:
                self.client.close()
        finally:
            self.client = None
        # Jump resources last: the direct-tcpip channel, then the client.
        self._close_jump_connection()
        self.log("SSH: closed")

    @property
    def _listing_sftp(self):
        """Persistent listing channel (facade over the channel manager)."""
        return self._sftp_channels.listing_channel

    def open_transfer_sftp(self):
        """Open an isolated SFTP channel for one upload or download."""
        return self._sftp_channels.open_transfer_sftp()

    def _drop_listing_sftp(self) -> None:
        self._sftp_channels.drop_listing_sftp()

    @contextlib.contextmanager
    def listing_sftp(self):
        """Lend the long-lived SFTP channel used for directory browsing."""
        with self._sftp_channels.listing_sftp() as sftp:
            yield sftp

    def supports_transfer_sftp_channels(self) -> bool:
        """Probe whether the active connection can create isolated channels."""
        return self._sftp_channels.supports_transfer_sftp_channels()

    def run(
        self,
        command: str,
        *,
        timeout_s: Optional[float] = None,
        log_output: bool = True,
    ) -> Tuple[int, str, str]:
        if not self.client:
            raise RuntimeError("SSH client not connected")
        t0 = timed()
        # Never echo secrets into the UI/logs.
        if is_sensitive_command(command):
            self.log("SSH$ <redacted>")
        else:
            self.log(f"SSH$ {command}")
        stdin, stdout, stderr = self.client.exec_command(command)
        if timeout_s is None and getattr(self.info, "timeout", None) is not None:
            timeout_s = self.info.timeout
        if timeout_s is not None:
            try:
                stdout.channel.settimeout(timeout_s)
                stderr.channel.settimeout(timeout_s)
            except Exception:
                pass
        try:
            out = _decode_remote_text(stdout.read())
            err = _decode_remote_text(stderr.read())
            code = stdout.channel.recv_exit_status()
            timed_out = False
        except socket.timeout:
            out = ""
            err = ""
            code = 124
            timed_out = True
        if log_output and out.strip():
            self.log(_sanitize_terminal_text(out).rstrip("\n"))
        if log_output and err.strip():
            self.log("STDERR:\n" + _sanitize_terminal_text(err).rstrip("\n"))
        dt = timed() - t0
        if timed_out:
            self.log(f"[timeout after {dt:.1f}s exit={code}]")
        else:
            self.log(f"[exit={code} duration={dt:.2f}s]")
        return code, out, err
