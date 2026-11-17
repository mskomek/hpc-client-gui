"""In-process X11 forwarding for the interactive shell (``ssh -X`` equivalent).

The wx front-end has a single embedded terminal, so GUI programs typed there
(``xclock``, ``glxgears``, ``fluent`` ...) must reach a local X server through
the same SSH session.  This module requests X11 forwarding on the shell
channel and relays every X11 channel the server opens to the local display.

Authentication: the server hands remote clients a random fake cookie (the one
we sent with ``x11-req``).  As OpenSSH does, the first packet of each X11
connection is inspected; when it carries the fake cookie it is replaced with
the real local cookie (from ``xauth list``) or, when the local server uses
host-based access only (VcXsrv on Windows), the auth fields are removed.
"""

from __future__ import annotations

import os
import re
import secrets
import select
import socket
import struct
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from hpc_gui.core.xauthority import (
    create_untrusted_cookie,
    find_xauth_executable,
    read_mit_cookie,
)

_X11_BASE_PORT = 6000
_MAX_X11_DISPLAY = 65535 - _X11_BASE_PORT
_MAX_RELAY_CHANNELS = 8
_MIT_COOKIE = b"MIT-MAGIC-COOKIE-1"
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})


@dataclass(frozen=True)
class LocalDisplay:
    """Where to connect for the local X server."""

    display: int = 0
    screen: int = 0
    host: str = "127.0.0.1"  # empty -> unix socket
    unix_path: str = ""
    name: str = "localhost:0.0"

    def connect(self, timeout: float = 5.0) -> socket.socket:
        # Never use an SSH-originated channel as a TCP pivot to a remote host.
        if not 0 <= self.display <= _MAX_X11_DISPLAY:
            raise ValueError("X11 display outside local TCP port range")
        if not self.unix_path and self.host not in _LOOPBACK_HOSTS:
            raise ValueError("X11 forwarding allows loopback X displays only")
        if self.unix_path and hasattr(socket, "AF_UNIX"):
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect(self.unix_path)
        else:
            sock = socket.create_connection((self.host or "127.0.0.1", _X11_BASE_PORT + self.display), timeout=timeout)
        sock.settimeout(None)
        return sock


_DISPLAY_RE = re.compile(r"^(?P<host>.*):(?P<display>\d+)(?:\.(?P<screen>\d+))?$")


def parse_display(value: Optional[str], *, platform: Optional[str] = None) -> LocalDisplay:
    """Parse a ``DISPLAY`` value; Windows (VcXsrv) defaults to TCP :0."""

    plat = platform or sys.platform
    raw = (value or "").strip()
    if not raw:
        return LocalDisplay()
    match = _DISPLAY_RE.match(raw)
    if not match:
        raise ValueError("Invalid X11 DISPLAY")
    host = match.group("host")
    display = int(match.group("display"))
    screen = int(match.group("screen") or 0)
    if not 0 <= display <= _MAX_X11_DISPLAY:
        raise ValueError("X11 DISPLAY port out of range")
    if host.startswith("/"):
        # macOS XQuartz launchd socket: "/private/tmp/.../org.xquartz:0"
        return LocalDisplay(display, screen, "", host + ":" + str(display), raw)
    if host in ("", "unix") and not plat.startswith("win"):
        return LocalDisplay(display, screen, "", f"/tmp/.X11-unix/X{display}", raw)
    if host in ("", "unix", "localhost"):
        host = "127.0.0.1"
    if host not in _LOOPBACK_HOSTS:
        raise ValueError("Remote X11 DISPLAY hosts are not permitted")
    if host == "[::1]":
        host = "::1"
    return LocalDisplay(display, screen, host, "", raw)


def local_display_from_env(*, platform: Optional[str] = None) -> LocalDisplay:
    return parse_display(os.environ.get("DISPLAY"), platform=platform)


def read_local_cookie(display: LocalDisplay, *, runner=subprocess.run) -> Optional[bytes]:
    """Return the local MIT-MAGIC-COOKIE-1 for ``display`` (None if absent)."""

    xauth = find_xauth_executable()
    if xauth and display.name:
        try:
            proc = runner([xauth, "list", display.name], capture_output=True, text=True, timeout=3)
        except Exception:
            proc = None
        for line in (getattr(proc, "stdout", "") or "").splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[1] == _MIT_COOKIE.decode():
                try:
                    cookie = bytes.fromhex(parts[2])
                except ValueError:
                    continue
                if len(cookie) == 16:
                    return cookie
    authority = os.environ.get("XAUTHORITY") or str(os.path.expanduser("~/.Xauthority"))
    cookie = read_mit_cookie(authority, display.display)
    if cookie:
        return cookie
    return None


def _pad(n: int) -> int:
    return (4 - n % 4) % 4


def rewrite_setup_auth(
    packet: bytes,
    fake_cookie: bytes,
    real_cookie: Optional[bytes],
    *,
    allow_empty_auth: bool = False,
) -> Optional[bytes]:
    """Rewrite the X11 connection-setup packet's auth fields.

    Returns the rewritten packet, ``b""`` for incomplete input, or
    ``None`` for mismatched cookies or absent local credentials. Clearing
    auth requires an explicit opt-in for a trusted loopback X server.
    """

    if len(packet) < 12:
        return b""
    order = packet[0:1]
    if order == b"B":
        fmt = ">"
    elif order == b"l":
        fmt = "<"
    else:
        return None
    major, minor, name_len, data_len = struct.unpack(fmt + "HHHH", packet[2:10])
    name_end = 12 + name_len + _pad(name_len)
    data_end = name_end + data_len + _pad(data_len)
    if len(packet) < data_end:
        return b""
    name = packet[12:12 + name_len]
    data = packet[name_end:name_end + data_len]
    if name != _MIT_COOKIE or data != fake_cookie:
        return None
    if real_cookie:
        new_name, new_data = _MIT_COOKIE, real_cookie
    elif allow_empty_auth:
        new_name, new_data = b"", b""
    else:
        return None
    header = order + packet[1:2] + struct.pack(fmt + "HHHH", major, minor, len(new_name), len(new_data)) + packet[10:12]
    body = new_name + b"\0" * _pad(len(new_name)) + new_data + b"\0" * _pad(len(new_data))
    return header + body + packet[data_end:]


class X11Forwarder:
    """Request X11 on a channel and relay incoming X11 channels locally."""

    def __init__(
        self,
        display: Optional[LocalDisplay] = None,
        *,
        log: Optional[Callable[[str], None]] = None,
        cookie_reader: Callable[[LocalDisplay], Optional[bytes]] = read_local_cookie,
        allow_unauthenticated_loopback: bool = False,
        trusted: bool = False,
        untrusted_cookie_factory=create_untrusted_cookie,
    ) -> None:
        self.display = display or local_display_from_env()
        self._log = log or (lambda _msg: None)
        self._fake_cookie = secrets.token_bytes(16)
        self._authority_copy = None
        if trusted:
            self._real_cookie = cookie_reader(self.display)
        else:
            authority = os.environ.get("XAUTHORITY") or str(Path.home() / ".Xauthority")
            try:
                self._authority_copy, self._real_cookie = untrusted_cookie_factory(
                    authority, self.display.name
                )
            except Exception as exc:
                raise RuntimeError(
                    "Untrusted X11 cookie unavailable; explicitly enable trusted X11 "
                    "only if the remote application may control your display"
                ) from exc
        self._allow_empty_auth = bool(allow_unauthenticated_loopback)
        self._closed = threading.Event()
        self._relay_lock = threading.Lock()
        self._active_relays = 0

    @property
    def fake_cookie_hex(self) -> str:
        return self._fake_cookie.hex()

    def request(self, channel) -> None:
        """Send ``x11-req`` on ``channel`` (must precede the shell request)."""
        if self._closed.is_set():
            raise RuntimeError("X11 forwarding already closed")
        if not self._real_cookie and not self._allow_empty_auth:
            raise RuntimeError("Local X11 cookie unavailable; refusing unauthenticated relay")
        if not self.display.unix_path and self.display.host not in _LOOPBACK_HOSTS:
            raise ValueError("Remote X11 DISPLAY hosts are not permitted")

        accepted = channel.request_x11(
            screen_number=self.display.screen,
            auth_protocol=_MIT_COOKIE.decode(),
            auth_cookie=self.fake_cookie_hex,
            single_connection=False,
            handler=self._on_x11_channel,
        )
        if accepted is False:
            raise RuntimeError("SSH server rejected X11 forwarding")

    def close(self) -> None:
        self._closed.set()
        if self._authority_copy is not None:
            try:
                self._authority_copy.unlink(missing_ok=True)
            except OSError:
                pass
            self._authority_copy = None

    # Called on the Paramiko transport thread: bound concurrency and return.
    def _on_x11_channel(self, channel, origin) -> None:
        with self._relay_lock:
            if self._closed.is_set() or self._active_relays >= _MAX_RELAY_CHANNELS:
                try:
                    channel.close()
                except Exception:
                    pass
                return
            self._active_relays += 1
        try:
            thread = threading.Thread(
                target=self._relay, args=(channel,), name="hpc_gui_x11_relay", daemon=True
            )
            thread.start()
        except Exception:
            with self._relay_lock:
                self._active_relays -= 1
            channel.close()
            raise

    def _relay(self, channel) -> None:
        local = None
        try:
            if self._closed.is_set():
                return
            try:
                local = self.display.connect()
            except OSError as exc:
                self._log(f"X11: yerel X sunucusuna bağlanılamadı ({self.display.name}): {exc}")
                return
            # Avoid keeping an untrusted X11 channel open indefinitely before
            # the setup packet arrives; the steady-state pump has its own poll.
            channel.settimeout(10.0)
            setup = b""
            while True:
                chunk = channel.recv(65536)
                if not chunk:
                    return
                setup += chunk
                rewritten = rewrite_setup_auth(
                    setup, self._fake_cookie, self._real_cookie,
                    allow_empty_auth=self._allow_empty_auth,
                )
                if rewritten is None:
                    self._log("X11: sahte çerez eşleşmedi; bağlantı reddedildi.")
                    return
                if rewritten:
                    local.sendall(rewritten)
                    break
                if len(setup) > 65536:
                    return
            channel.settimeout(None)
            self._pump(channel, local)
        except Exception as exc:  # relay threads must never crash the app
            self._log(f"X11: yönlendirme kanalı hatası: {exc.__class__.__name__}")
        finally:
            for closer in (getattr(channel, "close", None), getattr(local, "close", None)):
                try:
                    if closer:
                        closer()
                except Exception:
                    pass
            with self._relay_lock:
                self._active_relays = max(0, self._active_relays - 1)

    def _pump(self, channel, local: socket.socket) -> None:
        while not self._closed.is_set():
            readable, _, _ = select.select([channel, local], [], [], 1.0)
            if channel in readable:
                data = channel.recv(65536)
                if not data:
                    return
                local.sendall(data)
            if local in readable:
                data = local.recv(65536)
                if not data:
                    return
                channel.sendall(data)
