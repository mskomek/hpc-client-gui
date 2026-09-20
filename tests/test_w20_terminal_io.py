"""W20 — Terminal input/output and PTY behavior regressions.

DEF-W20-001 (HPC-W05-TERM-007 write failure): a rejected/raising transport
write must be visible, never silent success while the header claims Connected.
DEF-W20-002 (HPC-W05-TERM-019 paste lifecycle): paste issued before the xterm
bridge is ready must be queued and delivered on ready, never silently lost.

Real code exercised: WxTerminalWebViewPanel._handle_input,
_on_script_message dispatch, hpc_paste, _on_bridge_ready, close.
Mocked boundary: SSH transport (FakeSSH) and the JS invocation sink
(_run_js capture) — the widget, dispatch, decoder and status label are real.
What these tests do NOT prove: actual xterm rendering or a live SSH server
(EXTERNAL covers the live loopback separately).
"""

import pytest

wx = pytest.importorskip("wx")
pytestmark = pytest.mark.wx

from hpc_gui.wx_terminal_webview import _is_webview_available


def _run_subprocess_test(code_str, timeout=20):
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-c", code_str],
        capture_output=True, text=True, timeout=timeout, env=env,
    )


_SETUP = """
import sys, os
sys.path.insert(0, "src")
import wx
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class OkSSH:
    def __init__(self):
        self.sent = []
        self._wx_output_subscribers = []
    def send_shell_input(self, d):
        self.sent.append(d)
        return True
    def resize_shell_pty(self, c, r):
        pass

class FailSSH:
    def __init__(self):
        self.sent = []
        self._wx_output_subscribers = []
    def send_shell_input(self, d):
        self.sent.append(d)
        return False
    def resize_shell_pty(self, c, r):
        pass

class BoomSSH:
    def __init__(self):
        self._wx_output_subscribers = []
    def send_shell_input(self, d):
        raise RuntimeError("transport dead")
    def resize_shell_pty(self, c, r):
        pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
"""


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_w20_write_failure_is_visible_not_silent_success():
    """REQ-HPC-W05-TERM-007 / DEF-W20-001: rejected write shows a diagnostic."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = _SETUP + """
frame = wx.Frame(None, size=(900, 600))
# One real panel; swap transports the way reconnect/disconnect does.
panel = WxTerminalWebViewPanel(frame, ssh=OkSSH())
panel._ready = True
panel._is_parity = True
# Happy path: accepted write returns True, header keeps Connected truth
assert panel._handle_input("echo ok") is True
assert panel._status_label.GetLabel() == panel._status_text
connected = panel._status_text

# Negative: transport returns False -> False + visible diagnostic
panel.set_ssh(FailSSH())
assert panel._handle_input("echo lost") is False
diag = panel._status_label.GetLabel()
assert diag != connected, f"failure must not look Connected: {diag!r}"
assert "gönderilemedi" in diag or "could not be sent" in diag, diag
# Lifecycle: next accepted write restores the connection truth
panel.set_ssh(OkSSH())
assert panel._handle_input("echo back") is True
assert panel._status_label.GetLabel() == connected, panel._status_label.GetLabel()

# Negative: raising transport -> False + visible diagnostic, no exception
panel.set_ssh(BoomSSH())
assert panel._handle_input("echo boom") is False
diag = panel._status_label.GetLabel()
assert "gönderilemedi" in diag or "could not be sent" in diag, diag

# Negative: no write path at all (disconnected, no callback)
panel.set_ssh(None)
assert panel._handle_input("echo nowhere") is False
diag = panel._status_label.GetLabel()
assert "gönderilemedi" in diag or "could not be sent" in diag, diag
panel.close()
frame.Destroy()
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_w20_write_failure_via_bridge_dispatch():
    """REQ-HPC-W05-TERM-007 / DEF-W20-001: real bridge dispatch shows failure."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = _SETUP + """
import json
frame = wx.Frame(None, size=(900, 600))
panel = WxTerminalWebViewPanel(frame, ssh=FailSSH())
panel._ready = True
panel._is_parity = True

class FakeEvent:
    def GetString(self):
        return json.dumps({"type": "input", "data": "echo via bridge"})

panel._on_script_message(FakeEvent())
diag = panel._status_label.GetLabel()
assert "gönderilemedi" in diag or "could not be sent" in diag, diag
# The rejected input must not have been accepted anywhere
assert panel._ssh.sent == ["echo via bridge"], panel._ssh.sent
panel.close()
frame.Destroy()
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_w20_pre_ready_paste_is_queued_and_delivered():
    """REQ-HPC-W05-TERM-019 / DEF-W20-002: pre-ready paste is not lost."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = _SETUP + """
frame = wx.Frame(None, size=(900, 600))
panel = WxTerminalWebViewPanel(frame, ssh=OkSSH())
assert panel._ready is False
calls = []
panel._run_js = calls.append
# Pre-ready paste queues (truthful True) without touching JS yet
assert panel.hpc_paste("first-") is True
assert panel.hpc_paste("second") is True
assert calls == [], f"pre-ready paste must not call JS yet: {calls}"
assert "".join(panel._pending_paste) == "first-second"
# Ready delivers the queued paste in original order
panel._on_bridge_ready()
pastes = [c for c in calls if "hpcPaste" in c]
assert len(pastes) == 1, f"expected one combined paste delivery: {calls}"
assert "first-" in pastes[0] and "second" in pastes[0], pastes[0]
assert pastes[0].index("first-") < pastes[0].index("second")
assert panel._pending_paste == []
# Ready paste delivers immediately
calls.clear()
assert panel.hpc_paste("live-paste") is True
assert any("hpcPaste" in c and "live-paste" in c for c in calls), calls
panel.close()
frame.Destroy()
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_w20_paste_negative_and_close_lifecycle():
    """REQ-HPC-W05-TERM-019 / DEF-W20-002: paste drop contract + close clears."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = _SETUP + """
frame = wx.Frame(None, size=(900, 600))
panel = WxTerminalWebViewPanel(frame, ssh=OkSSH())
calls = []
panel._run_js = calls.append
# Negative: empty paste is dropped
assert panel.hpc_paste("") is False
# Negative: over-cap pre-ready paste is refused, not silently truncated
import hpc_gui.wx_terminal_webview as renderer
big = "P" * (renderer.MAX_PENDING_PASTE_BYTES + 1)
assert panel.hpc_paste(big) is False
assert panel._pending_paste == []
# Lifecycle: queued paste is discarded on close, never delivered late
assert panel.hpc_paste("queued-then-closed") is True
panel.close()
assert panel._pending_paste == []
panel._on_bridge_ready()
assert calls == [], f"late delivery after close: {calls}"
assert panel.hpc_paste("after-close") is False
frame.Destroy()
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"
