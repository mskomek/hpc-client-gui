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

@pytest.mark.contract
@pytest.mark.semantic
def test_panel_sends_sgr_payload_to_terminal_bridge():
    """The wx panel preserves an SGR sequence for the terminal bridge."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    r = _run(_wrap("""
import sys, os, pathlib
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class Fake:
    _wx_output_subscribers = []
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900,600))
panel = WxTerminalWebViewPanel(frame, ssh=Fake())
sizer = wx.BoxSizer(wx.VERTICAL); sizer.Add(panel,1,wx.EXPAND)
frame.SetSizer(sizer); frame.Layout(); frame.Show()
sys.path.insert(0, 'tests/support')
from wx_webview_probe import wait_until_ready
wait_until_ready(wx, lambda: panel._ready, timeout=6)
assert panel._ready, "not ready"
calls = []
panel._run_js = lambda c: calls.append(c)
panel.hpc_write("\\x1b[31mRED\\x1b[0m")
assert any("\\\\u001b[31m" in c for c in calls), f"SGR not preserved: {calls}"
bridge = pathlib.Path("src/hpc_gui/assets/terminal/wx_bridge.js").read_text(encoding="utf-8")
assert "terminal.write" in bridge
panel.close(); frame.Destroy()
os._exit(0)
"""))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

@pytest.mark.contract
@pytest.mark.semantic
def test_panel_preserves_carriage_return_bridge_payload():
    """The panel preserves CR in each output payload sent to the bridge."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    r = _run(_wrap("""
import sys, os, pathlib
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class Fake:
    _wx_output_subscribers = []
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900,600))
panel = WxTerminalWebViewPanel(frame, ssh=Fake())
sizer = wx.BoxSizer(wx.VERTICAL); sizer.Add(panel,1,wx.EXPAND)
frame.SetSizer(sizer); frame.Layout(); frame.Show()
sys.path.insert(0, 'tests/support')
from wx_webview_probe import wait_until_ready
wait_until_ready(wx, lambda: panel._ready, timeout=6)
assert panel._ready, "not ready"
calls = []
panel._run_js = lambda c: calls.append(c)
panel.hpc_write("Progress 10%\\r")
panel.hpc_write("Progress 20%\\r")
panel.hpc_write("Progress 30%")
assert len(calls) == 3, f"CR split into {len(calls)} calls: {calls}"
assert "\\\\r" in calls[0] or "\\\\u000d" in calls[0], f"CR not preserved: {calls[0]}"
panel.close(); frame.Destroy()
os._exit(0)
"""))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

@pytest.mark.contract
@pytest.mark.semantic
def test_panel_preserves_unicode_output_payload():
    """The panel sends Unicode output through the terminal bridge unchanged."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    r = _run(_wrap("""
import sys, os, pathlib
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class Fake:
    _wx_output_subscribers = []
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900,600))
panel = WxTerminalWebViewPanel(frame, ssh=Fake())
sizer = wx.BoxSizer(wx.VERTICAL); sizer.Add(panel,1,wx.EXPAND)
frame.SetSizer(sizer); frame.Layout(); frame.Show()
sys.path.insert(0, 'tests/support')
from wx_webview_probe import wait_until_ready
wait_until_ready(wx, lambda: panel._ready, timeout=6)
assert panel._ready, "not ready"
calls = []
panel._run_js = lambda c: calls.append(c)
panel.hpc_write("Türkçe çğıöşü 日本語")
assert any("Türkçe" in c or "日本語" in c for c in calls), f"unicode missing: {calls}"
panel.close(); frame.Destroy()
os._exit(0)
"""))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

@pytest.mark.contract
@pytest.mark.semantic
def test_panel_sends_multiline_paste_to_bridge():
    """The panel serializes multiline paste to the terminal bridge."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    r = _run(_wrap("""
import sys, os, pathlib
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class Fake:
    _wx_output_subscribers = []
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900,600))
panel = WxTerminalWebViewPanel(frame, ssh=Fake())
sizer = wx.BoxSizer(wx.VERTICAL); sizer.Add(panel,1,wx.EXPAND)
frame.SetSizer(sizer); frame.Layout(); frame.Show()
sys.path.insert(0, 'tests/support')
from wx_webview_probe import wait_until_ready
wait_until_ready(wx, lambda: panel._ready, timeout=6)
assert panel._ready, "not ready"
calls = []
panel._run_js = lambda c: calls.append(c)
panel.hpc_paste("line1\\nline2\\nline3")
assert any("hpcPaste" in c and "line1" in c for c in calls), f"paste not called: {calls}"
bridge = pathlib.Path("src/hpc_gui/assets/terminal/wx_bridge.js").read_text(encoding="utf-8")
assert "terminal.paste" in bridge
panel.close(); frame.Destroy()
os._exit(0)
"""))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"
