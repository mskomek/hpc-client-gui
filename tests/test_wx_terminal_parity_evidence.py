"""Wave 76 — wx terminal bridge payload checks for GUI-TERM-001."""

import pytest

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.wx, pytest.mark.subprocess]

from hpc_gui.wx_terminal_webview import _is_webview_available
from support.terminal_parity import _run, _wrap


# ── Terminal bridge contract/unit checks (subprocess) ──


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
loop = wx.GUIEventLoop(); prev = wx.EventLoop.GetActive(); wx.EventLoop.SetActive(loop)
start = time.monotonic()
while time.monotonic()-start < 6:
    if panel._ready: break
    try:
        while loop.Pending(): loop.Dispatch()
    except: pass
    try: wx.Yield()
    except: pass
    time.sleep(0.05)
wx.EventLoop.SetActive(prev)
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
loop = wx.GUIEventLoop(); prev = wx.EventLoop.GetActive(); wx.EventLoop.SetActive(loop)
start = time.monotonic()
while time.monotonic()-start < 6:
    if panel._ready: break
    try:
        while loop.Pending(): loop.Dispatch()
    except: pass
    try: wx.Yield()
    except: pass
    time.sleep(0.05)
wx.EventLoop.SetActive(prev)
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
loop = wx.GUIEventLoop(); prev = wx.EventLoop.GetActive(); wx.EventLoop.SetActive(loop)
start = time.monotonic()
while time.monotonic()-start < 6:
    if panel._ready: break
    try:
        while loop.Pending(): loop.Dispatch()
    except: pass
    try: wx.Yield()
    except: pass
    time.sleep(0.05)
wx.EventLoop.SetActive(prev)
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
loop = wx.GUIEventLoop(); prev = wx.EventLoop.GetActive(); wx.EventLoop.SetActive(loop)
start = time.monotonic()
while time.monotonic()-start < 6:
    if panel._ready: break
    try:
        while loop.Pending(): loop.Dispatch()
    except: pass
    try: wx.Yield()
    except: pass
    time.sleep(0.05)
wx.EventLoop.SetActive(prev)
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
loop = wx.GUIEventLoop(); prev = wx.EventLoop.GetActive(); wx.EventLoop.SetActive(loop)
start = time.monotonic()
while time.monotonic()-start < 6:
    if panel._ready: break
    try:
        while loop.Pending(): loop.Dispatch()
    except: pass
    try: wx.Yield()
    except: pass
    time.sleep(0.05)
wx.EventLoop.SetActive(prev)
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
