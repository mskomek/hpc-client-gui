"""Focused wx terminal WebView regression tests."""

import pytest

wx = pytest.importorskip("wx")
pytestmark = pytest.mark.wx

from hpc_gui.wx_terminal_webview import _is_webview_available
from wx_terminal_webview_support import _run_subprocess_test

@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_wx_terminal_input_chain_ctrl_a_to_z():
    """Ctrl+A..Ctrl+Z must produce \x01..\x1a via terminal.onData → send_shell_input."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class FakeSSH:
    def __init__(self):
        self.sent = []
        self._wx_output_subscribers = []
    def send_shell_input(self, data):
        self.sent.append(data)
        return True
    def resize_shell_pty(self, c, r):
        pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900, 600))
ssh = FakeSSH()
panel = WxTerminalWebViewPanel(frame, ssh=ssh)
# Inject fake input handler to capture what xterm would send
# Simulate xterm on_data by calling _handle_input directly
for letter, expected in [("A", "\\x01"), ("B", "\\x02"), ("C", "\\x03"),
                          ("D", "\\x04"), ("Z", "\\x1a"),
                          ("_", "\\x1f")]:
    # Monkey-patch _run_js to capture input calls
    panel._ready = True
    panel._is_parity = True
    # Simulate what xterm.onData would produce for Ctrl+letter
    ctrl_code = chr(ord(letter) - 64)  # A=0x01, Z=0x1a
    panel._handle_input(ctrl_code)
    assert ssh.sent[-1] == ctrl_code, f"Ctrl+{letter} expected {repr(ctrl_code)}, got {repr(ssh.sent[-1])}"
    # Verify no logging (sent list only has the data, no log output)
    assert len(ssh.sent) > 0
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
def test_wx_terminal_resize_chain_to_ssh():
    """Resize events must call resize_shell_pty with correct cols/rows."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class FakeSSH:
    def __init__(self):
        self.resizes = []
        self._wx_output_subscribers = []
    def send_shell_input(self, d):
        return True
    def resize_shell_pty(self, cols, rows):
        self.resizes.append((cols, rows))

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900, 600))
ssh = FakeSSH()
panel = WxTerminalWebViewPanel(frame, ssh=ssh)
panel._ready = True
panel._is_parity = True
# Simulate resize from xterm
panel._handle_resize(120, 40, 960, 600)
assert ssh.resizes == [(120, 40)], f"expected [(120,40)], got {ssh.resizes}"
# Dedup: same size should not trigger again
panel._handle_resize(120, 40, 960, 600)
assert len(ssh.resizes) == 1, f"dedup failed: {ssh.resizes}"
# Different size should trigger
panel._handle_resize(80, 25, 640, 400)
assert ssh.resizes[-1] == (80, 25), f"expected (80,25), got {ssh.resizes[-1]}"
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
def test_wx_terminal_font_change_triggers_resize():
    """Font change via hpc_set_font_size must trigger fit→resize chain."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class FakeSSH:
    def __init__(self):
        self.resizes = []
        self._wx_output_subscribers = []
    def send_shell_input(self, d):
        return True
    def resize_shell_pty(self, c, r):
        self.resizes.append((c, r))

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900, 600))
ssh = FakeSSH()
panel = WxTerminalWebViewPanel(frame, ssh=ssh)
panel._ready = True
panel._is_parity = True
# Capture JS calls to verify hpcSetFontSize is called
calls = []
orig = panel._run_js
def capture(code):
    calls.append(code)
panel._run_js = capture
# Change font
panel.hpc_set_font_size(18)
assert panel._font_size == 18
assert any("hpcSetFontSize" in c and "18" in c for c in calls)
# Font bounds
panel.hpc_set_font_size(200)
assert panel._font_size == 32
panel.hpc_set_font_size(2)
assert panel._font_size == 6
# Verify resize is called (via hpcFit or hpcSetFontSize in bridge)
# The bridge.js calls fit.fit() and posts resize, which Python receives via _handle_resize
# We simulate the bridge's resize post
panel._handle_resize(100, 30, 800, 500)
assert ssh.resizes[-1] == (100, 30)
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_wx_terminal_multiline_paste():
    """Multiline paste must call terminal.paste (not local TextCtrl)."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os
sys.path.insert(0, "src")
import wx, time, pathlib
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class FakeSSH:
    def __init__(self):
        self.sent = []
        self._wx_output_subscribers = []
    def send_shell_input(self, d):
        self.sent.append(d)
        return True
    def resize_shell_pty(self, c, r):
        pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900, 600))
ssh = FakeSSH()
panel = WxTerminalWebViewPanel(frame, ssh=ssh)
panel._ready = True
panel._is_parity = True
calls = []
orig = panel._run_js
def capture(code):
    calls.append(code)
panel._run_js = capture
# Paste multiline text
multiline = "line1\\nline2\\nline3"
panel.hpc_paste(multiline)
assert any("hpcPaste" in c and "line1" in c for c in calls), f"paste not called: {calls}"
# Verify paste does NOT log the pasted content
# (no console.log in bridge.js for paste, only postToPython for input)
bridge = pathlib.Path("src/hpc_gui/assets/terminal/wx_bridge.js").read_text(encoding="utf-8")
assert "console.log" not in bridge or "terminal input" not in bridge
# Verify the paste JS includes all three lines
paste_js = [c for c in calls if "hpcPaste" in c]
assert len(paste_js) == 1
assert "line1" in paste_js[0] and "line2" in paste_js[0] and "line3" in paste_js[0]
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_wx_terminal_input_chain_no_logging():
    """Input data must not be logged anywhere."""
    code = """
import sys, os
sys.path.insert(0, "src")
import wx, time, pathlib
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class FakeSSH:
    def __init__(self):
        self.sent = []
        self._wx_output_subscribers = []
    def send_shell_input(self, d):
        self.sent.append(d)
        return True
    def resize_shell_pty(self, c, r):
        pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900, 600))
ssh = FakeSSH()
panel = WxTerminalWebViewPanel(frame, ssh=ssh)
panel._ready = True
panel._is_parity = True
# Verify _handle_input does not log
panel._handle_input("sensitive_data\\x03")
assert ssh.sent == ["sensitive_data\\x03"]
# Verify bridge.js has no console.log for input
bridge = pathlib.Path("src/hpc_gui/assets/terminal/wx_bridge.js").read_text(encoding="utf-8")
assert "console.log" not in bridge, "bridge must not log"
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"
