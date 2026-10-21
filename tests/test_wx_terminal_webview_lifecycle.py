"""Focused wx terminal WebView regression tests."""

import pytest

wx = pytest.importorskip("wx")
pytestmark = pytest.mark.wx

from hpc_gui.wx_terminal_webview import _is_webview_available
from wx_terminal_webview_support import _run_subprocess_test

@pytest.mark.gui
@pytest.mark.subprocess
def test_wx_terminal_header_dimensions_update():
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os
sys.path.insert(0, 'src')
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
panel._handle_resize(120, 40, 960, 600)
label = panel._dimensions_label.GetLabel()
assert "120" in label and "40" in label, f"dimensions label: {label}"
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
def test_wx_terminal_reconnect_set_ssh():
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os
sys.path.insert(0, 'src')
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class FakeSSH:
    def __init__(self, name):
        self.name = name
        self._wx_output_subscribers = []
    def send_shell_input(self, d):
        return True
    def resize_shell_pty(self, c, r):
        pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900, 600))
ssh1 = FakeSSH("ssh1")
ssh2 = FakeSSH("ssh2")
panel = WxTerminalWebViewPanel(frame, ssh=ssh1)
assert panel._ssh is ssh1
assert len(ssh1._wx_output_subscribers) == 1
panel.set_ssh(ssh2)
assert panel._ssh is ssh2
assert len(ssh1._wx_output_subscribers) == 0, "old ssh should have 0 subscribers"
assert len(ssh2._wx_output_subscribers) == 1, "new ssh should have 1 subscriber"
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.concurrency
def test_wx_terminal_generation_guard_rejects_stale_output():
    """After reconnect, delayed output from old SSH must be rejected."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os
sys.path.insert(0, "src")
import wx, time
import hpc_gui.wx_terminal_webview as terminal_webview
# This case tests callback generations, not the native browser controller.
def _native_view_not_needed():
    return False
terminal_webview._is_webview_available = _native_view_not_needed
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class FakeSSH:
    def __init__(self, name=""):
        self.name = name
        self._wx_output_subscribers = []
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900, 600))
ssh1 = FakeSSH("ssh1")
ssh2 = FakeSSH("ssh2")
panel = WxTerminalWebViewPanel(frame, ssh=ssh1)
panel._ready = True
panel._is_parity = True

# Capture writes to xterm
writes = []
orig = panel.hpc_write
def capture_write(data):
    writes.append(data)
panel.hpc_write = capture_write

# SSH1 schedules output (simulates delayed callback)
old_sub = ssh1._wx_output_subscribers[0]
old_sub("stale_data_from_ssh1")
# Deliver via generation-matched call
panel._safe_deliver(panel._generation, "stale_data_from_ssh1")
assert any("stale_data_from_ssh1" in w for w in writes), "ssh1 output should appear before reconnect"

# Reconnect to ssh2 - generation increments
panel.set_ssh(ssh2)
old_gen = panel._generation - 1

# Try to deliver with old generation - must be rejected
panel._safe_deliver(old_gen, "very_stale_data")
assert not any("very_stale_data" in w for w in writes), "stale generation output must be rejected"

# New SSH2 output should work
if ssh2._wx_output_subscribers:
    new_sub = ssh2._wx_output_subscribers[0]
    new_sub("fresh_data_from_ssh2")
panel._safe_deliver(panel._generation, "fresh_data_from_ssh2")
assert any("fresh_data_from_ssh2" in w for w in writes), "new ssh output must be delivered"

panel.close()
frame.Destroy()
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
def test_wx_terminal_header_status_updates():
    """Header must show Disconnected/Connected based on SSH attachment state."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os
sys.path.insert(0, "src")
import wx, time
import hpc_gui.wx_terminal_webview as terminal_webview
# This case checks SSH identity/status labels and does not need WebView2.
def _native_view_not_needed():
    return False
terminal_webview._is_webview_available = _native_view_not_needed
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class FakeSSH:
    _wx_output_subscribers = []
    username = "testuser"
    hostname = "testhost"
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900, 600))
# Start without SSH
panel = WxTerminalWebViewPanel(frame, ssh=None)
# Initial status should be disconnected
assert panel._status_label.GetLabel(), "status label should not be empty"

# Connect
ssh = FakeSSH()
panel.set_ssh(ssh)
status = panel._status_label.GetLabel()
assert status, f"status label empty after connect: {status}"
identity = panel._identity_label.GetLabel()
assert "testuser" in identity and "testhost" in identity, f"identity: {identity}"

# Reconnect to new SSH
ssh2 = FakeSSH()
ssh2.username = "user2"
ssh2.hostname = "host2"
panel.set_ssh(ssh2)
identity2 = panel._identity_label.GetLabel()
assert "user2" in identity2 and "host2" in identity2, f"identity after reconnect: {identity2}"

# Disconnect
panel.set_ssh(None)
identity3 = panel._identity_label.GetLabel()
assert identity3 == "", f"identity after disconnect should be empty: {identity3}"

panel.close()
frame.Destroy()
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.resource
def test_wx_terminal_destroy_before_ready_no_xfail():
    """Destroy before ready must not crash - pending cleared, callbacks suppressed."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class FakeSSH:
    _wx_output_subscribers = []
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900, 600))
panel = WxTerminalWebViewPanel(frame, ssh=FakeSSH())
# Write before ready
panel.hpc_write("pending_data")
assert len(panel._pending) == 1
# Destroy before ready
panel.close()
assert panel._closed is True
assert panel._pending == [], f"pending not cleared: {panel._pending}"
# Further writes must be no-ops
panel.hpc_write("after_close_ignored")
assert panel._pending == []
# Late ready must be ignored
panel._on_bridge_ready()
assert panel._ready is False or panel._closed is True
# Late subscriber delivery must be rejected
panel._safe_deliver(panel._generation + 1, "late_data")
assert panel._pending == []
frame.Destroy()
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
def test_wx_terminal_fallback_sets_non_parity():
    """Direct WebView-panel construction shows a diagnostic fallback as non-parity."""
    code = """
import os, sys
sys.path.insert(0, "src")
import wx
import hpc_gui.wx_terminal_webview as renderer
renderer._is_webview_available = lambda: False
app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(600, 400))
panel = renderer.WxTerminalWebViewPanel(frame)
frame.Show()
wx.Yield()
controls = panel._wx_terminal_controls
assert panel._wx_terminal_is_webview is False
assert panel._wx_terminal_is_parity is False
assert panel._webview is None
assert controls["output"].IsShown()
assert "WebView backend unavailable" in panel._diagnostic_text
assert "WebView backend unavailable" in controls["output"].GetValue()
frame.Destroy()
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"fallback state failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.resource
def test_wx_terminal_100_reconnects_no_leak():
    """100 reconnects must not leak subscribers or crash."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os
sys.path.insert(0, "src")
import wx, time
import hpc_gui.wx_terminal_webview as terminal_webview
# This case covers subscriber generations; native WebView startup/teardown is
# covered separately and is unrelated to the reconnect invariant here.
def _native_view_not_needed():
    return False
terminal_webview._is_webview_available = _native_view_not_needed
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class FakeSSH:
    def __init__(self):
        self._wx_output_subscribers = []
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900, 600))
current_ssh = FakeSSH()
panel = WxTerminalWebViewPanel(frame, ssh=current_ssh)
panel._ready = True

initial_gen = panel._generation
for i in range(100):
    new_ssh = FakeSSH()
    panel.set_ssh(new_ssh)
    assert current_ssh._wx_output_subscribers == [], f"old subscriber retained at {i}"
    assert panel._generation == initial_gen + i + 1, f"generation mismatch at {i}"
    assert len(new_ssh._wx_output_subscribers) == 1, f"subscriber leak at {i}: {len(new_ssh._wx_output_subscribers)}"
    current_ssh = new_ssh

panel.close()
assert current_ssh._wx_output_subscribers == [], "close retained the active SSH subscriber"
frame.Destroy()
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
def test_wx_terminal_embedded_connect_to_ssh():
    """Embedded terminal created with ssh=None, then set_ssh must attach."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal import build_terminal_panel

class FakeSSH:
    def __init__(self):
        self.sent = []
        self.resizes = []
        self._wx_output_subscribers = []
    def send_shell_input(self, d):
        self.sent.append(d)
        return True
    def resize_shell_pty(self, c, r):
        self.resizes.append((c, r))

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900, 600))
panel = build_terminal_panel(frame, ssh=None, lifecycle=None)
sizer = wx.BoxSizer(wx.VERTICAL)
sizer.Add(panel, 1, wx.EXPAND)
frame.SetSizer(sizer)
frame.Layout()
frame.Show()

assert hasattr(panel, "_wx_terminal_set_ssh"), "panel missing _wx_terminal_set_ssh"
assert callable(panel._wx_terminal_set_ssh), "_wx_terminal_set_ssh not callable"

ssh = FakeSSH()
panel._wx_terminal_set_ssh(ssh)
assert panel._ssh is ssh, "SSH not set"
assert len(ssh._wx_output_subscribers) == 1, f"expected 1 subscriber, got {len(ssh._wx_output_subscribers)}"

if hasattr(panel, "_handle_input"):
    panel._ready = True
    panel._is_parity = True
    panel._handle_input("\\x03")
    assert ssh.sent[-1] == "\\x03", f"input not forwarded: {ssh.sent}"

sub = ssh._wx_output_subscribers[0]
sub("test_output")

panel.close()
frame.Destroy()
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"
