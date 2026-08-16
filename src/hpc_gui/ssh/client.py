from __future__ import annotations

import contextlib
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple

import socket

from hpc_gui.core.debug_support import timed

import paramiko

from hpc_gui.core.logging import get_logger
from hpc_gui.core.paths import app_data_dir
from hpc_gui.services.command_history_store import is_sensitive_command


_ACS_MAP = {
    "j": "┘",
    "k": "┐",
    "l": "┌",
    "m": "└",
    "n": "┼",
    "q": "─",
    "t": "├",
    "u": "┤",
    "v": "┴",
    "w": "┬",
    "x": "│",
    "o": "█",
    "s": "·",
    "a": "▒",
    "f": "°",
    "g": "±",
    "h": "␋",
    "i": "␌",
    "`": "◆",
}


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
_SFTP_TRANSFER_TIMEOUT_SECONDS = 60
# Directory browsing is interactive: waiting a full transfer timeout on a dead
# link before the panel reports anything is far too long for a click.
_SFTP_LISTING_TIMEOUT_SECONDS = 15

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


class HostKeyChangedError(paramiko.SSHException):
    def __init__(self, hostname: str):
        self.hostname = hostname
        super().__init__(f"Host key changed for {hostname}; connection cancelled.")


class HostKeyRejectedError(paramiko.SSHException):
    def __init__(self, hostname: str):
        self.hostname = hostname
        super().__init__(f"Unknown host key rejected for {hostname}.")


class _KnownHostsPolicy(paramiko.MissingHostKeyPolicy):
    def __init__(
        self,
        path: Path,
        decide: Optional[Callable[[HostKeyInfo], str]],
    ) -> None:
        self.path = path
        self.decide = decide

    def missing_host_key(self, client, hostname, key) -> None:
        fingerprint = getattr(key, "fingerprint", "") or key.get_fingerprint().hex()
        decision = self.decide(
            HostKeyInfo(hostname, key.get_name(), fingerprint)
        ) if self.decide else "save"
        if decision == "once":
            return
        if decision != "save":
            raise HostKeyRejectedError(hostname)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        client.get_host_keys().add(hostname, key.get_name(), key)
        # ponytail: single-process write; add locking if parallel profile connects arrive.
        client.save_host_keys(str(self.path))


def _sanitize_terminal_text(text: str) -> str:
    """Remove terminal control sequences and normalize redraw-heavy output."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out: list[str] = []
    alt_charset = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        code = ord(ch)
        if ch == "\x1b" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "[":
                i += 2
                while i < n and not ("@" <= text[i] <= "~"):
                    i += 1
                i += 1
                continue
            if nxt in "()":
                if i + 2 < n:
                    spec = nxt + text[i + 2]
                    if spec in ("(0", ")0"):
                        alt_charset = True
                    elif spec in ("(B", ")B"):
                        alt_charset = False
                i += 3
                continue
            if nxt in "PX^_":
                i += 2
                while i < n:
                    if text[i] == "\x1b" and i + 1 < n and text[i + 1] == "\\":
                        i += 2
                        break
                    i += 1
                continue
            if "@" <= nxt <= "_":
                i += 2
                continue
            i += 1
            continue
        if ch in ("\x0e", "\x0f"):
            alt_charset = ch == "\x0e"
            i += 1
            continue
        if code < 32 and ch not in ("\n", "\t"):
            i += 1
            continue
        if alt_charset and ch in _ACS_MAP:
            out.append(_ACS_MAP[ch])
        else:
            out.append(ch)
        i += 1
    return "".join(out)


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
    preconnected_socket: Optional[socket.socket] = None


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
        self._listing_sftp = None
        self._listing_lock = threading.RLock()
        self._shell_channel = None
        self._shell_thread: Optional[threading.Thread] = None
        self._shell_stop = threading.Event()
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
        connection_kwargs = ({"sock": info.preconnected_socket} if info.preconnected_socket is not None else {})

        try:
            if info.key_path:
                self.log("SSH: using configured key")
                pkey = paramiko.PKey.from_path(info.key_path)
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
            raise HostKeyChangedError(exc.hostname) from exc
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
        self._start_shell_session()
        self.sftp = self.client.open_sftp()
        self.log("SSH: connected, SFTP ready")

    def _start_shell_session(self) -> None:
        if not self.client:
            return
        self._stop_shell_session()
        try:
            transport = self.client.get_transport()
            if transport is None or not transport.is_active():
                return
            cols, rows = self._shell_geometry
            channel = self.client.invoke_shell(term="xterm", width=cols, height=rows)
            try:
                channel.settimeout(0.2)
            except Exception:
                pass
        except Exception as exc:
            self.log(f"SSH: interactive shell unavailable ({exc})")
            return

        self._shell_channel = channel
        self._shell_stop = threading.Event()
        self._shell_thread = threading.Thread(
            target=self._shell_reader_loop,
            args=(channel,),
            name="hpc_gui_ssh_shell",
            daemon=True,
        )
        self._drain_initial_shell_output(channel)
        self._shell_thread.start()
        self.log("SSH: interactive shell session started")

    def resize_shell_pty(self, cols: int, rows: int) -> None:
        cols = max(1, int(cols))
        rows = max(1, int(rows))
        self._shell_geometry = (cols, rows)
        channel = self._shell_channel
        if channel is None:
            return
        try:
            channel.resize_pty(width=cols, height=rows)
        except Exception:
            pass

    def send_shell_text(self, text: str) -> bool:
        channel = self._shell_channel
        if channel is None or getattr(channel, "closed", False):
            return False
        payload = (text or "").rstrip("\r\n")
        if not payload:
            return True
        try:
            sent = channel.send(payload + "\n")
            return sent > 0
        except Exception:
            return False

    def send_shell_input(self, data: str) -> bool:
        channel = self._shell_channel
        if channel is None or getattr(channel, "closed", False):
            return False
        payload = data or ""
        if not payload:
            return True
        try:
            sent = channel.send(payload)
            return sent > 0
        except Exception:
            return False

    def _drain_initial_shell_output(self, channel, duration: float = 0.35) -> None:
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline and not self._shell_stop.is_set():
            try:
                if not channel.recv_ready():
                    time.sleep(0.05)
                    continue
                data = channel.recv(4096)
                if not data:
                    break
                self._handle_shell_output(data.decode(errors="replace"))
            except socket.timeout:
                continue
            except Exception:
                break

    def _shell_reader_loop(self, channel) -> None:
        unexpected_disconnect = False
        disconnect_reason = ""
        while not self._shell_stop.is_set():
            try:
                if channel.recv_ready():
                    data = channel.recv(4096)
                    if data:
                        self._handle_shell_output(data.decode(errors="replace"))
                    continue
                if getattr(channel, "closed", False) or channel.exit_status_ready():
                    unexpected_disconnect = True
                    disconnect_reason = "SSH shell session ended."
                    break
            except socket.timeout:
                continue
            except Exception as exc:
                if not self._shell_stop.is_set():
                    self.log(f"SSH: shell session read failed ({exc})")
                    unexpected_disconnect = True
                    disconnect_reason = str(exc)
                break
            time.sleep(0.1)
        if unexpected_disconnect and not self._shell_stop.is_set():
            try:
                self.close()
            except Exception:
                pass
            self._notify_disconnect(disconnect_reason or "SSH shell session ended.")

    def _handle_shell_output(self, text: str) -> None:
        if not text:
            return
        if self._shell_output_cb is not None:
            try:
                self._shell_output_cb(text)
                return
            except Exception:
                pass
        sanitized = _sanitize_terminal_text(text)
        if sanitized.strip():
            self.log(sanitized.rstrip("\n"))

    def _stop_shell_session(self) -> None:
        self._shell_stop.set()
        channel = self._shell_channel
        self._shell_channel = None
        thread = self._shell_thread
        self._shell_thread = None
        try:
            if channel is not None:
                try:
                    channel.close()
                except Exception:
                    pass
        finally:
            if thread is not None and thread.is_alive() and thread is not threading.current_thread():
                try:
                    thread.join(timeout=1.0)
                except Exception:
                    pass

    def _notify_disconnect(self, reason: str) -> None:
        if not self._disconnect_cb:
            return
        try:
            self._disconnect_cb(reason or "SSH bağlantısı kesildi.")
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
        self.log("SSH: closed")

    def open_transfer_sftp(self):
        """Open an isolated SFTP channel for one upload or download.

        The browsing channel in ``self.sftp`` is deliberately shared by the
        UI.  Paramiko SFTP clients are not safe to use from several transfer
        worker threads, so file transfers must obtain their own channel from
        the already authenticated transport instead.
        """
        if self.client is None:
            raise RuntimeError("SSH client not connected")
        transport = self.client.get_transport()
        if transport is None or not transport.is_active():
            raise RuntimeError("SSH transport is not active")
        is_authenticated = getattr(transport, "is_authenticated", None)
        if callable(is_authenticated) and not is_authenticated():
            raise RuntimeError("SSH transport is not authenticated")
        sftp = paramiko.SFTPClient.from_transport(transport)
        # Without a channel timeout, a silently dead connection (dropped VPN,
        # NAT/firewall idle-kill, etc.) leaves stat()/read()/write() blocked
        # forever with no way for the worker thread, its QThread, or the app
        # to ever unstick — the transfer row freezes at 100% and, if the app
        # is closed while blocked, can crash on shutdown. Bound every SFTP
        # channel so a dead connection surfaces as a normal socket.timeout
        # (caught and reported as a failed transfer) instead of hanging.
        channel = sftp.get_channel()
        if channel is not None:
            channel.settimeout(_SFTP_TRANSFER_TIMEOUT_SECONDS)
        return sftp

    def _drop_listing_sftp(self) -> None:
        sftp, self._listing_sftp = self._listing_sftp, None
        if sftp is not None:
            try:
                sftp.close()
            except Exception:
                pass

    @contextlib.contextmanager
    def listing_sftp(self):
        """Lend the long-lived SFTP channel used for directory browsing.

        Opening a channel per navigation costs a full round trip on a high-RTT
        link, so one channel is opened lazily and reused.  Access is
        serialized: an abandoned ``listdir_iter`` leaves unread read-ahead
        replies queued, so any non-clean exit discards the channel and the
        next caller opens a fresh one.
        """
        with self._listing_lock:
            if self._listing_sftp is None:
                self._listing_sftp = self.open_transfer_sftp()
                get_channel = getattr(self._listing_sftp, "get_channel", None)
                channel = get_channel() if callable(get_channel) else None
                if channel is not None:
                    channel.settimeout(_SFTP_LISTING_TIMEOUT_SECONDS)
            clean = False
            try:
                yield self._listing_sftp
                clean = True
            finally:
                if not clean:
                    self._drop_listing_sftp()

    def supports_transfer_sftp_channels(self) -> bool:
        """Probe whether the active connection can create isolated channels."""
        channel = None
        try:
            channel = self.open_transfer_sftp()
            return True
        except Exception:
            return False
        finally:
            if channel is not None:
                try:
                    channel.close()
                except Exception:
                    pass

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
