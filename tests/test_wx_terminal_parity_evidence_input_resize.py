"""Wave 76 — wx terminal panel bridge checks for GUI-TERM-001.

Subprocesses isolate WebView2; fake SSH and a captured JS runner expose the
panel's bridge payloads without claiming that xterm rendered visible output.
"""

import os

import subprocess

import sys

import textwrap

import pytest

from hpc_gui.wx_terminal_webview import _is_webview_available

def _run(code, timeout=15):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=timeout, env=env,
    )

def _wrap(code):
    return textwrap.dedent(code)

@pytest.mark.unit
@pytest.mark.semantic
def test_panel_forwards_resize_to_ssh_seam():
    """The panel forwards changed dimensions once to its SSH adapter."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    r = _run(_wrap("""
import sys, os
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class Fake:
    def __init__(self):
        self._wx_output_subscribers = []
        self.resizes = []
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): self.resizes.append((c, r))

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900,600))
ssh = Fake()
panel = WxTerminalWebViewPanel(frame, ssh=ssh)
sizer = wx.BoxSizer(wx.VERTICAL); sizer.Add(panel,1,wx.EXPAND)
frame.SetSizer(sizer); frame.Layout(); frame.Show()
sys.path.insert(0, 'tests/support')
from wx_webview_probe import wait_until_ready
wait_until_ready(wx, lambda: panel._ready, timeout=6)
assert panel._ready
ssh.resizes.clear()  # Ignore the initial FitAddon geometry notification.
panel._handle_resize(132, 44, 1056, 704)
assert ssh.resizes == [(132, 44)]
label = panel._dimensions_label.GetLabel()
assert "132" in label and "44" in label, f"dim: {label}"
panel._handle_resize(132, 44, 1056, 704)
assert len(ssh.resizes) == 1
panel.close(); frame.Destroy(); os._exit(0)
"""))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

@pytest.mark.unit
@pytest.mark.semantic
def test_repeated_input_forwarding_preserves_order():
    """Repeated panel input calls reach the SSH adapter in order."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    r = _run(_wrap("""
import sys, os
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class Fake:
    _wx_output_subscribers = []
    inputs = []
    def send_shell_input(self, d): self.inputs.append(d); return True
    def resize_shell_pty(self, c, r): pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900,600))
ssh = Fake()
panel = WxTerminalWebViewPanel(frame, ssh=ssh)
sizer = wx.BoxSizer(wx.VERTICAL); sizer.Add(panel,1,wx.EXPAND)
frame.SetSizer(sizer); frame.Layout(); frame.Show()
sys.path.insert(0, 'tests/support')
from wx_webview_probe import wait_until_ready
wait_until_ready(wx, lambda: panel._ready, timeout=6)
assert panel._ready
for i in range(500):
    panel._handle_input(f"input_{i}")
assert len(ssh.inputs) == 500
assert ssh.inputs[0] == "input_0" and ssh.inputs[499] == "input_499"
panel.close(); frame.Destroy(); os._exit(0)
"""))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

@pytest.mark.unit
@pytest.mark.semantic
def test_repeated_resize_requests_are_deduplicated():
    """Repeated equal resize calls are coalesced before SSH forwarding."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    r = _run(_wrap("""
import sys, os
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class Fake:
    _wx_output_subscribers = []
    resizes = []
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): self.resizes.append((c, r))

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900,600))
ssh = Fake()
panel = WxTerminalWebViewPanel(frame, ssh=ssh)
sizer = wx.BoxSizer(wx.VERTICAL); sizer.Add(panel,1,wx.EXPAND)
frame.SetSizer(sizer); frame.Layout(); frame.Show()
sys.path.insert(0, 'tests/support')
from wx_webview_probe import wait_until_ready
wait_until_ready(wx, lambda: panel._ready, timeout=6)
assert panel._ready
ssh.resizes.clear()  # Ignore the initial FitAddon geometry notification.
for i in range(500):
    panel._handle_resize(80, 24, 640, 432)
panel._handle_resize(120, 34, 960, 612)
assert len(ssh.resizes) == 2, f"expected 2 unique, got {len(ssh.resizes)}"
panel.close(); frame.Destroy(); os._exit(0)
"""))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"
