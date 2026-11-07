"""Regression tests for the 2026-11-06/07 X11 forwarding incidents.

* ``xclock``/``glxgears`` on arf showed an empty ``$DISPLAY`` because the
  terminal shell was opened without an ``x11-req`` (stale/other code paths).
* A host-based X server (VcXsrv, no xauth cookie) must still be forwarded.
* After the Qt split, ``ssh/shell_session.py`` imported a module that no
  longer existed; every in-package import must resolve.
"""

from __future__ import annotations

import ast
import socket
import struct
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from hpc_gui.ssh import x11_forward
from hpc_gui.ssh.x11_forward import LocalDisplay, X11Forwarder

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parents[1] / "src"
PKG = SRC / "hpc_gui"


# ---------------- helpers ----------------

class _Channel:
    def __init__(self, log, reject_x11=False):
        self.log = log
        self.reject_x11 = reject_x11
        self.x11_kwargs = None

    def get_pty(self, term, width, height):
        self.log.append("pty")

    def request_x11(self, **kw):
        if self.reject_x11:
            raise RuntimeError("x11 refused")
        self.x11_kwargs = kw
        self.log.append("x11")

    def invoke_shell(self):
        self.log.append("shell")


def _wrapper(monkeypatch, *, x11=True, reject_x11=False, platform="windows"):
    from hpc_gui.services import xserver_manager
    from hpc_gui.ssh.client import SSHClientWrapper
    from hpc_gui.ssh.contracts import SSHConnInfo

    log, messages, calls = [], [], {}
    channel = _Channel(log, reject_x11=reject_x11)
    transport = SimpleNamespace(open_session=lambda: channel)
    plain = SimpleNamespace(
        invoke_shell=lambda **kw: log.append("plain") or "plain",
        get_transport=lambda: transport,
        close=lambda: None,
    )
    wrapper = SSHClientWrapper(SSHConnInfo(host="h", port=22, x11_forwarding=x11))
    wrapper.client = plain
    wrapper.log = messages.append

    def ensure(*args, **kwargs):
        calls["ensure"] = kwargs
        return True

    monkeypatch.setattr(xserver_manager, "_is_windows", lambda: platform == "windows")
    monkeypatch.setattr(xserver_manager, "_is_macos", lambda: platform == "macos")
    monkeypatch.setattr(xserver_manager, "ensure_x_server_running", ensure)
    monkeypatch.setattr(xserver_manager, "is_local_x_available", lambda *_a, **_k: calls.setdefault("linux", True))
    monkeypatch.setattr(x11_forward, "read_local_cookie", lambda _d: None)
    return wrapper, channel, log, messages, calls


# ---------------- empty $DISPLAY regression ----------------

def test_interactive_shell_session_routes_through_x11_aware_invoke(monkeypatch):
    """The terminal must open its channel via the wrapper (x11-req path)."""
    wrapper, _channel, _log, _messages, _calls = _wrapper(monkeypatch)
    session = wrapper._ensure_shell_session()
    assert session._invoke_shell == wrapper._invoke_shell


def test_x11_request_sent_on_shell_channel_before_shell(monkeypatch):
    wrapper, channel, log, messages, _calls = _wrapper(monkeypatch)
    result = wrapper._invoke_shell(term="xterm-256color", width=120, height=40)
    assert result is channel
    assert log == ["pty", "x11", "shell"]
    kw = channel.x11_kwargs
    assert kw["auth_protocol"] == "MIT-MAGIC-COOKIE-1"
    assert len(kw["auth_cookie"]) == 32 and int(kw["auth_cookie"], 16) >= 0
    assert kw["single_connection"] is False  # glxgears/xclock may open several
    assert callable(kw["handler"])
    assert any("yönlendirme etkin" in m for m in messages)
    wrapper.close()


def test_host_based_server_without_cookie_is_still_forwarded(monkeypatch):
    """VcXsrv (-ac / host based) has no xauth cookie; forwarding must not need one."""
    fwd = X11Forwarder(LocalDisplay(host="127.0.0.1", display=0), cookie_reader=lambda _d: None)
    seen = {}
    fwd.request(SimpleNamespace(request_x11=lambda **kw: seen.update(kw)))
    assert seen["auth_cookie"] == fwd.fake_cookie_hex
    name = b"MIT-MAGIC-COOKIE-1"
    packet = b"l\0" + struct.pack("<HHHH", 11, 0, len(name), 16) + b"\0\0" + name + b"\0\0" + bytes.fromhex(fwd.fake_cookie_hex)
    out = x11_forward.rewrite_setup_auth(packet, bytes.fromhex(fwd.fake_cookie_hex), None)
    assert out is not None
    assert struct.unpack("<HH", out[6:10]) == (0, 0)  # auth stripped, not rejected
    fwd.close()


def test_windows_check_never_downloads_or_opens_dialog(monkeypatch):
    wrapper, _channel, _log, _messages, calls = _wrapper(monkeypatch)
    wrapper._invoke_shell(term="xterm")
    assert calls["ensure"] == {"parent": None, "allow_download": False}
    wrapper.close()


def test_server_rejecting_x11_still_opens_terminal(monkeypatch):
    wrapper, _channel, log, messages, _calls = _wrapper(monkeypatch, reject_x11=True)
    wrapper._invoke_shell(term="xterm")
    assert log == ["pty", "shell"]
    assert wrapper._x11_forwarder is None
    assert any("reddetti" in m for m in messages)


def test_reconnect_and_close_release_forwarder(monkeypatch):
    wrapper, _channel, _log, _messages, _calls = _wrapper(monkeypatch)
    wrapper._invoke_shell(term="xterm")
    first = wrapper._x11_forwarder
    wrapper._invoke_shell(term="xterm")
    assert first is not None and first._closed.is_set()
    second = wrapper._x11_forwarder
    wrapper.close()
    assert wrapper._x11_forwarder is None and second._closed.is_set()


def test_forwarder_relays_two_concurrent_x11_channels():
    """single_connection=False: two clients (e.g. two windows) both reach the server."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(4)
    port = server.getsockname()[1]
    accepted = []

    def accept():
        for _ in range(2):
            conn, _ = server.accept()
            accepted.append(conn)

    acceptor = threading.Thread(target=accept, daemon=True)
    acceptor.start()
    display = LocalDisplay(host="127.0.0.1", display=port - 6000)
    fwd = X11Forwarder(display, cookie_reader=lambda _d: None)
    pairs = []
    for _ in range(2):
        a, b = socket.socketpair()
        pairs.append((a, b))
    try:
        for a, _b in pairs:
            fwd._on_x11_channel(_SockChannel(a), ("127.0.0.1", 0))
        acceptor.join(5)
        assert len(accepted) == 2
    finally:
        fwd.close()
        for conn in accepted:
            conn.close()
        for a, b in pairs:
            a.close()
            b.close()
        server.close()


class _SockChannel:
    def __init__(self, sock):
        self._sock = sock
        self.closed = False

    def fileno(self):
        return self._sock.fileno()

    def settimeout(self, value):
        self._sock.settimeout(value)

    def recv(self, n):
        try:
            return self._sock.recv(n)
        except OSError:
            return b""

    def sendall(self, data):
        self._sock.sendall(data)

    def close(self):
        self.closed = True


# ---------------- Qt split / stale import regression ----------------

def _module_exists(dotted: str) -> bool:
    rel = Path(*dotted.split(".")[1:])
    base = PKG / rel
    return base.with_suffix(".py").is_file() or (base / "__init__.py").is_file() or dotted == "hpc_gui"


def _internal_imports():
    for path in sorted(PKG.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] == "hpc_gui":
                        yield path, alias.name, None
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                if node.module.split(".")[0] == "hpc_gui":
                    for alias in node.names:
                        yield path, node.module, alias.name


def test_every_internal_hpc_gui_import_resolves():
    missing = []
    for path, module, name in _internal_imports():
        if _module_exists(module):
            continue
        missing.append(f"{path.relative_to(SRC)}: {module}" + (f" ({name})" if name else ""))
    assert not missing, "imports of non-existent hpc_gui modules:\n" + "\n".join(missing)


def test_ssh_package_uses_only_the_wx_x11_module():
    offenders = [
        f"{path.relative_to(SRC)}: {module}"
        for path, module, name in _internal_imports()
        if module in {"hpc_gui.ssh.x11_forwarding", "hpc_gui.services.x11_runner"}
        or (module == "hpc_gui.ssh" and name == "x11_forwarding")
    ]
    assert not offenders, offenders
    assert not (PKG / "ssh" / "x11_forwarding.py").exists()


@pytest.mark.parametrize("banned", ["PySide6", "shiboken6", "hpc_gui.ui", "hpc_gui.app"])
def test_src_has_no_legacy_qt_imports(banned):
    hits = []
    for path in sorted(PKG.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            if any(n == banned or n.startswith(banned + ".") for n in names):
                hits.append(str(path.relative_to(SRC)))
    assert not hits, f"{banned} imported by: {hits}"
