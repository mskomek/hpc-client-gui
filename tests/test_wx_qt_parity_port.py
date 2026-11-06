"""Qt→wx parity port: X11 forwarding, dir cache toggle, jobs interval, shortcuts."""

from __future__ import annotations

import socket
import struct
import threading
from types import SimpleNamespace

import pytest

from hpc_gui.ssh import x11_forward
from hpc_gui.ssh.x11_forward import (
    LocalDisplay,
    X11Forwarder,
    parse_display,
    rewrite_setup_auth,
)

pytestmark = pytest.mark.unit

COOKIE = b"MIT-MAGIC-COOKIE-1"


def _setup_packet(order: bytes, name: bytes, data: bytes, tail: bytes = b"") -> bytes:
    fmt = ">" if order == b"B" else "<"
    pad = lambda n: b"\0" * ((4 - n % 4) % 4)  # noqa: E731
    return order + b"\0" + struct.pack(fmt + "HHHH", 11, 0, len(name), len(data)) + b"\0\0" + name + pad(len(name)) + data + pad(len(data)) + tail


# ---------------- DISPLAY parsing ----------------

@pytest.mark.parametrize(
    "value, platform, expected",
    [
        (None, "win32", ("127.0.0.1", 0, "")),
        ("localhost:0.0", "win32", ("127.0.0.1", 0, "")),
        (":1", "win32", ("127.0.0.1", 1, "")),
        (":0", "linux", ("", 0, "/tmp/.X11-unix/X0")),
        ("10.0.0.5:2.1", "linux", ("10.0.0.5", 2, "")),
        ("/private/tmp/com.apple.launchd.x/org.xquartz:0", "darwin", ("", 0, "/private/tmp/com.apple.launchd.x/org.xquartz:0")),
    ],
)
def test_parse_display(value, platform, expected):
    d = parse_display(value, platform=platform)
    assert (d.host, d.display, d.unix_path) == expected


# ---------------- setup-packet auth rewrite ----------------

@pytest.mark.parametrize("order", [b"B", b"l"])
def test_rewrite_strips_fake_cookie_for_host_based_server(order):
    fake = bytes(range(16))
    out = rewrite_setup_auth(_setup_packet(order, COOKIE, fake, b"REST"), fake, None)
    fmt = ">" if order == b"B" else "<"
    assert struct.unpack(fmt + "HH", out[6:10]) == (0, 0)
    assert out[12:] == b"REST"


def test_rewrite_substitutes_real_cookie():
    fake, real = b"f" * 16, b"r" * 16
    out = rewrite_setup_auth(_setup_packet(b"l", COOKIE, fake), fake, real)
    assert out == _setup_packet(b"l", COOKIE, real)


def test_rewrite_partial_and_mismatch():
    fake = b"f" * 16
    pkt = _setup_packet(b"l", COOKIE, fake)
    assert rewrite_setup_auth(pkt[:5], fake, None) == b""
    assert rewrite_setup_auth(pkt[:-3], fake, None) == b""
    assert rewrite_setup_auth(_setup_packet(b"l", COOKIE, b"x" * 16), fake, None) is None
    assert rewrite_setup_auth(b"Q" + pkt[1:], fake, None) is None


# ---------------- relay end to end ----------------

class _FakeX11Channel:
    """Socket-backed stand-in for a paramiko X11 channel (selectable)."""

    def __init__(self):
        self.remote, self._sock = socket.socketpair()

    def fileno(self):
        return self._sock.fileno()

    def settimeout(self, value):
        self._sock.settimeout(value)

    def recv(self, n):
        return self._sock.recv(n)

    def sendall(self, data):
        self._sock.sendall(data)

    def close(self):
        self._sock.close()


def test_forwarder_relays_channel_to_local_display():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    received = []

    def fake_x_server():
        conn, _ = server.accept()
        with conn:
            buf = b""
            while len(buf) < 16:
                buf += conn.recv(4096)
            received.append(buf)
            conn.sendall(b"HELLO-FROM-X")

    t = threading.Thread(target=fake_x_server, daemon=True)
    t.start()
    display = LocalDisplay(display=port - 6000, host="127.0.0.1", name="test")
    fwd = X11Forwarder(display, cookie_reader=lambda _d: None)

    calls = {}
    channel_stub = SimpleNamespace(request_x11=lambda **kw: calls.update(kw))
    fwd.request(channel_stub)
    assert calls["auth_protocol"] == COOKIE.decode()
    assert calls["single_connection"] is False

    chan = _FakeX11Channel()
    calls["handler"](chan, ("127.0.0.1", 1234))
    chan.remote.sendall(_setup_packet(b"l", COOKIE, bytes.fromhex(fwd.fake_cookie_hex), b"DATA"))
    chan.remote.settimeout(5)
    assert chan.remote.recv(64) == b"HELLO-FROM-X"
    t.join(5)
    assert received and received[0] == _setup_packet(b"l", b"", b"", b"DATA")
    fwd.close()
    chan.remote.close()
    server.close()


def test_read_local_cookie_parses_xauth_output(monkeypatch):
    monkeypatch.setattr(x11_forward.shutil, "which", lambda _n: "/usr/bin/xauth")
    out = "host/unix:0  MIT-MAGIC-COOKIE-1  00112233445566778899aabbccddeeff\n"
    runner = lambda *a, **k: SimpleNamespace(stdout=out)  # noqa: E731
    assert x11_forward.read_local_cookie(LocalDisplay(name=":0"), runner=runner) == bytes.fromhex("00112233445566778899aabbccddeeff")


# ---------------- SSH client wiring ----------------

class _FakeShellChannel:
    def __init__(self, log):
        self.log = log

    def get_pty(self, term, width, height):
        self.log.append(("pty", term, width, height))

    def request_x11(self, **kw):
        self.log.append(("x11", kw["screen_number"]))

    def invoke_shell(self):
        self.log.append(("shell",))


def _client_with(x11: bool, monkeypatch, ready=True):
    from hpc_gui.services import xserver_manager
    from hpc_gui.ssh.client import SSHClientWrapper
    from hpc_gui.ssh.contracts import SSHConnInfo

    log = []
    transport = SimpleNamespace(open_session=lambda: _FakeShellChannel(log))
    plain = SimpleNamespace(invoke_shell=lambda **kw: log.append(("plain",)) or "plain", get_transport=lambda: transport)
    wrapper = SSHClientWrapper(SSHConnInfo(host="h", port=22, x11_forwarding=x11))
    wrapper.client = plain
    monkeypatch.setattr(xserver_manager, "_is_windows", lambda: True)
    monkeypatch.setattr(xserver_manager, "ensure_x_server_running", lambda *a, **k: ready)
    monkeypatch.setattr(x11_forward, "read_local_cookie", lambda _d: None)
    return wrapper, log


def test_shell_requests_x11_before_shell(monkeypatch):
    wrapper, log = _client_with(True, monkeypatch)
    wrapper._invoke_shell(term="xterm-256color", width=100, height=30)
    assert log == [("pty", "xterm-256color", 100, 30), ("x11", 0), ("shell",)]
    assert wrapper._x11_forwarder is not None
    wrapper._close_x11_forwarder()
    assert wrapper._x11_forwarder is None


def test_shell_without_x11_or_without_local_server(monkeypatch):
    wrapper, log = _client_with(False, monkeypatch)
    wrapper._invoke_shell(term="xterm")
    assert log == [("plain",)]
    wrapper, log = _client_with(True, monkeypatch, ready=False)
    wrapper._invoke_shell(term="xterm")
    assert log == [("plain",)]


# ---------------- remote directory cache toggle ----------------

def test_remote_directory_cache_setting_is_honoured(monkeypatch):
    from hpc_gui import wx_remote_files
    from hpc_gui.config import storage

    model = wx_remote_files.WxRemoteDirectoryModel("/")
    calls = []
    loader = lambda path: calls.append(path) or [wx_remote_files.RemoteEntry(path + "/a")]  # noqa: E731

    monkeypatch.setattr(storage, "get_remote_directory_cache_enabled", lambda default=True: True)
    model.list_entries(loader, "/x")
    model.list_entries(loader, "/x")
    assert calls == ["/x"]

    monkeypatch.setattr(storage, "get_remote_directory_cache_enabled", lambda default=True: False)
    model.list_entries(loader, "/x")
    model.list_entries(loader, "/x")
    assert calls == ["/x", "/x", "/x"]


# ---------------- jobs outputs interval ----------------

def test_outputs_refresh_interval_reads_setting(monkeypatch):
    wx_jobs = pytest.importorskip("hpc_gui.wx_jobs")
    from hpc_gui.config import storage

    monkeypatch.setattr(storage, "get_jobs_outputs_refresh_interval_seconds", lambda default=15: 42)
    assert wx_jobs.outputs_refresh_interval_seconds() == 42

    def boom(default=15):
        raise OSError("settings unreadable")

    monkeypatch.setattr(storage, "get_jobs_outputs_refresh_interval_seconds", boom)
    assert wx_jobs.outputs_refresh_interval_seconds() == 15


# ---------------- shortcut preferences -> accelerators ----------------

_FAKE_WX = SimpleNamespace(
    ACCEL_NORMAL=0, ACCEL_ALT=1, ACCEL_CTRL=2, ACCEL_SHIFT=4,
    WXK_F1=340, WXK_F5=344, WXK_RETURN=13, WXK_DELETE=127,
)


def test_parse_and_convert_bindings():
    from hpc_gui.wx_shortcuts import parse_binding, to_wx_accel

    assert parse_binding("Ctrl+Shift+N") == (frozenset({"ctrl", "shift"}), "N")
    assert parse_binding("Ctrl++") == (frozenset({"ctrl"}), "+")
    assert parse_binding("Hyper+X") is None
    assert to_wx_accel(_FAKE_WX, "F1") == (0, 340)
    assert to_wx_accel(_FAKE_WX, "Cmd+,") == (2, ord(","))
    assert to_wx_accel(_FAKE_WX, "Alt+Enter") == (1, 13)
    assert to_wx_accel(_FAKE_WX, "Ctrl+Bogus") is None


def test_shell_bindings_follow_user_preferences():
    from hpc_gui.services.shortcut_preferences import ShortcutPreferences
    from hpc_gui.wx_shortcuts import shell_accelerators, shell_bindings

    prefs = ShortcutPreferences("windows", {})
    prefs.set_binding("APP-HELP", "F5")
    settings = {"shortcut_preferences": prefs.serialize()}
    accels = shell_accelerators(_FAKE_WX, shell_bindings("windows", settings))
    assert ("APP-HELP", 0, 344) in accels
    assert all(cmd != "APP-HELP" or key != 340 for cmd, _f, key in accels)
