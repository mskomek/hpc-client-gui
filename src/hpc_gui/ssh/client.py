from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional, Protocol, Tuple

import socket

from hpc_gui.core.debug_support import timed

import paramiko
from paramiko.auth_strategy import AuthSource, AuthStrategy, InMemoryPrivateKey

from hpc_gui.core.logging import get_logger
from hpc_gui.core.paths import app_data_dir
from hpc_gui.services.command_history_store import is_sensitive_command
from hpc_gui.ssh.sftp_channels import (
    SFTPChannelManager,
    _SFTP_LISTING_TIMEOUT_SECONDS,  # noqa: F401  (re-exported facade constant)
    _SFTP_TRANSFER_TIMEOUT_SECONDS,  # noqa: F401  (re-exported facade constant)
)
from hpc_gui.ssh.shell_session import InteractiveShellSession, _sanitize_terminal_text

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for typing only
    from hpc_gui.ssh.jump import SSHJumpInfo


class SocketLike(Protocol):
    """Minimal socket-like surface Paramiko needs from a preconnected channel."""

    def send(self, data: bytes) -> int: ...

    def recv(self, size: int) -> bytes: ...

    def settimeout(self, timeout: float | None) -> None: ...

    def close(self) -> None: ...


# (Terminal ACS map and sanitizer live in hpc_gui.ssh.shell_session.)

# Paramiko uses ``timeout`` both for the TCP connection and for waiting for
# the initial SSH key exchange.  Clusters behind VPNs or busy login nodes can
# legitimately take longer than the former 15-second limit.
_SSH_CONNECT_AND_KEX_TIMEOUT_SECONDS = 45
_SSH_BANNER_TIMEOUT_SECONDS = 45
_SSH_AUTH_TIMEOUT_SECONDS = 30
_SSH_CHANNEL_TIMEOUT_SECONDS = 30
# Generous relative to the interactive-shell timeout: a transfer channel
# only needs to detect a truly dead connection, not bound normal chunk
# pacing on a slow HPC link.
# (Timeout constants live in hpc_gui.ssh.sftp_channels now; they are
# re-exported above so existing imports keep working.)

_KEEPALIVE_INTERVAL_DEFAULT = 30


def coerce_keepalive_interval(
    value: object, default: int = _KEEPALIVE_INTERVAL_DEFAULT
) -> int:
    """Return a profile interval clamped to 0..3600 seconds."""
    try:
        return max(0, min(3600, int(value)))  # type: ignore[arg-type]
    except (OverflowError, TypeError, ValueError):
        return default


@dataclass(frozen=True)
class HostKeyInfo:
    hostname: str
    key_type: str
    fingerprint: str
    role: str = "target"  # target | jump


class HostKeyChangedError(paramiko.SSHException):
    def __init__(self, hostname: str, role: str = "target"):
        self.hostname = hostname
        self.role = role
        super().__init__(f"Host key changed for {hostname}; connection cancelled.")


class HostKeyRejectedError(paramiko.SSHException):
    def __init__(self, hostname: str, role: str = "target"):
        self.hostname = hostname
        self.role = role
        super().__init__(f"Unknown host key rejected for {hostname}.")


class _KnownHostsPolicy(paramiko.MissingHostKeyPolicy):
    def __init__(
        self,
        path: Path,
        decide: Optional[Callable[[HostKeyInfo], str]],
        role: str = "target",
    ) -> None:
        self.path = path
        self.decide = decide
        self.role = role

    def missing_host_key(self, client, hostname, key) -> None:
        fingerprint = getattr(key, "fingerprint", "") or key.get_fingerprint().hex()
        decision = self.decide(
            HostKeyInfo(hostname, key.get_name(), fingerprint, role=self.role)
        ) if self.decide else "save"
        if decision == "once":
            return
        if decision != "save":
            raise HostKeyRejectedError(hostname)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        client.get_host_keys().add(hostname, key.get_name(), key)
        # ponytail: single-process write; add locking if parallel profile connects arrive.
        client.save_host_keys(str(self.path))
        if os.name == "posix" and self.path.exists():
            self.path.chmod(0o600)


@dataclass
class SSHConnInfo:
    host: str
    port: int
    username: str = ""
    password: str = ""
    key_path: str = ""
    host_key_policy: str = "accept-new"  # accept-new | strict
    x11_forwarding: bool = False  # UI flag; actual X11 is handled separately
    timeout: Optional[float] = None  # None keeps the per-knob defaults below
    keepalive_interval_seconds: int = _KEEPALIVE_INTERVAL_DEFAULT  # 0 disables
    known_hosts_path: str = ""
    host_key_decision: Optional[Callable[[HostKeyInfo], str]] = None
    preconnected_socket: Optional[SocketLike] = None
    jump: Optional["SSHJumpInfo"] = None
    keyboard_interactive_handler: Optional[Callable[[str, str, list[tuple[str, bool]]], list[str]]] = None


class _KeyboardInteractiveSource(AuthSource):
    def __init__(self, username, handler):
        super().__init__(username)
        self.handler = handler

    def __repr__(self):
        return self._repr(user=self.username)

    def authenticate(self, transport):
        return transport.auth_interactive(self.username, self.handler)


class _ConnectionAuthStrategy(AuthStrategy):
    def __init__(self, info: SSHConnInfo, pkey=None):
        super().__init__(ssh_config=None)
        self.info = info
        self.pkey = pkey

    def get_sources(self):
        username = self.info.username
        if self.pkey is not None:
            yield InMemoryPrivateKey(username, self.pkey)
        if self.info.password:
            yield _PasswordSource(username, lambda: self.info.password)
        if self.info.keyboard_interactive_handler is not None:
            yield _KeyboardInteractiveSource(
                username, self.info.keyboard_interactive_handler
            )


class _PasswordSource(AuthSource):
    def __init__(self, username, password_getter):
        super().__init__(username)
        self.password_getter = password_getter

    def __repr__(self):
        return self._repr(user=self.username)

    def authenticate(self, transport):
        return transport.auth_password(self.username, self.password_getter())


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
        self.client.load_system_host_keys()
        if known_hosts_path.exists():
            self.client.load_host_keys(str(known_hosts_path))
        policy = (getattr(info, "host_key_policy", "accept-new") or "accept-new").strip().lower()
        if policy == "strict":
            self.client.set_missing_host_key_policy(paramiko.RejectPolicy())
            self.log("SSH: host key policy = strict")
        else:
            self.client.set_missing_host_key_policy(
                _KnownHostsPolicy(known_hosts_path, info.host_key_decision)
            )
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
                pkey = paramiko.PKey.from_path(info.key_path)
            auth_strategy = None
            if info.keyboard_interactive_handler is not None:
                auth_strategy = _ConnectionAuthStrategy(info, pkey)
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
                    allow_agent=True,
                    look_for_keys=True,
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
                    allow_agent=True,
                    look_for_keys=True,
                    **connection_kwargs,
                )
        except paramiko.BadHostKeyException as exc:
            # Target host-key change: drop the partial target client and
            # all jump resources before propagating.
            try:
                if self.client is not None:
                    close = getattr(self.client, "close", None)
                    if callable(close):
                        close()
            finally:
                self.client = None
            self._close_jump_connection()
            raise HostKeyChangedError(exc.hostname) from exc
        except Exception:
            # Target connect/auth failure after a jump channel exists:
            # drop the partial target client and all jump resources.
            try:
                if self.client is not None:
                    close = getattr(self.client, "close", None)
                    if callable(close):
                        close()
            finally:
                self.client = None
            self._close_jump_connection()
            raise
        transport = self.client.get_transport()
        if transport is not None:
            banner = transport.get_banner()
            if banner:
                if isinstance(banner, bytes):
                    banner = banner.decode(errors="replace")
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
        )
        if not session.start():
            return
        self._shell_session = session

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
            self._disconnect_cb(reason or "SSH bağlantısı kesildi.")
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
            out = stdout.read().decode(errors="replace")
            err = stderr.read().decode(errors="replace")
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
