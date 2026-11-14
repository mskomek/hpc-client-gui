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
import shutil
import socket
import struct
import subprocess
import sys
import threading
from dataclasses import dataclass
from typing import Callable, Optional

_X11_BASE_PORT = 6000
_MIT_COOKIE = b"MIT-MAGIC-COOKIE-1"


@dataclass(frozen=True)
class LocalDisplay:
    """Where to connect for the local X server."""

    display: int = 0
    screen: int = 0
    host: str = "127.0.0.1"  # empty -> unix socket
    unix_path: str = ""
    name: str = "localhost:0.0"

    def connect(self, timeout: float = 5.0) -> socket.socket:
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
        return LocalDisplay()
    host = match.group("host")
    display = int(match.group("display"))
    screen = int(match.group("screen") or 0)
    if host.startswith("/"):
        # macOS XQuartz launchd socket: "/private/tmp/.../org.xquartz:0"
        return LocalDisplay(display, screen, "", host + ":" + str(display), raw)
    if host in ("", "unix") and not plat.startswith("win"):
        return LocalDisplay(display, screen, "", f"/tmp/.X11-unix/X{display}", raw)
    if host in ("", "unix", "localhost"):
        host = "127.0.0.1"
    return LocalDisplay(display, screen, host, "", raw)


def local_display_from_env(*, platform: Optional[str] = None) -> LocalDisplay:
    return parse_display(os.environ.get("DISPLAY"), platform=platform)


def read_local_cookie(display: LocalDisplay, *, runner=subprocess.run) -> Optional[bytes]:
    """Return the local MIT-MAGIC-COOKIE-1 for ``display`` (None if absent)."""

    xauth = shutil.which("xauth") or ("/opt/X11/bin/xauth" if os.path.exists("/opt/X11/bin/xauth") else None)
    if not xauth or not display.name:
        return None
    try:
        proc = runner([xauth, "list", display.name], capture_output=True, text=True, timeout=3)
    except Exception:
        return None
    for line in (getattr(proc, "stdout", "") or "").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == _MIT_COOKIE.decode():
            try:
                return bytes.fromhex(parts[2])
            except ValueError:
                continue
    return None


def _pad(n: int) -> int:
    return (4 - n % 4) % 4


def rewrite_setup_auth(packet: bytes, fake_cookie: bytes, real_cookie: Optional[bytes]) -> Optional[bytes]:
    """Rewrite the X11 connection-setup packet's auth fields.

    Returns the rewritten packet, ``b""`` when more bytes are needed, or
    ``None`` when the cookie does not match (connection must be refused).
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
    else:
        new_name, new_data = b"", b""
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
    ) -> None:
        self.display = display or local_display_from_env()
        self._log = log or (lambda _msg: None)
        self._fake_cookie = secrets.token_bytes(16)
        self._real_cookie = cookie_reader(self.display)
        self._threads: list[threading.Thread] = []
        self._closed = threading.Event()

    @property
    def fake_cookie_hex(self) -> str:
        return self._fake_cookie.hex()

    def request(self, channel) -> None:
        """Send ``x11-req`` on ``channel`` (must precede the shell request)."""

        channel.request_x11(
            screen_number=self.display.screen,
            auth_protocol=_MIT_COOKIE.decode(),
            auth_cookie=self.fake_cookie_hex,
            single_connection=False,
            handler=self._on_x11_channel,
        )

    def close(self) -> None:
        self._closed.set()

    # Called on the paramiko transport thread: hand off immediately.
    def _on_x11_channel(self, channel, origin) -> None:
        thread = threading.Thread(target=self._relay, args=(channel,), name="hpc_gui_x11_relay", daemon=True)
        self._threads = [t for t in self._threads if t.is_alive()]
        self._threads.append(thread)
        thread.start()

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
            channel.settimeout(None)
            setup = b""
            while True:
                chunk = channel.recv(65536)
                if not chunk:
                    return
                setup += chunk
                rewritten = rewrite_setup_auth(setup, self._fake_cookie, self._real_cookie)
                if rewritten is None:
                    self._log("X11: sahte çerez eşleşmedi; bağlantı reddedildi.")
                    return
                if rewritten:
                    local.sendall(rewritten)
                    break
                if len(setup) > 65536:
                    return
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
