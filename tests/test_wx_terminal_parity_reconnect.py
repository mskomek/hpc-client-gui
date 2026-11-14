"""Wave 76 — terminal panel reconnect/font/close bridge checks (split).

Subprocesses isolate WebView2; fake SSH and a captured JS runner expose the
panel's bridge payloads without claiming that xterm rendered visible output.
"""

import os
import pathlib
import subprocess
import sys
import textwrap

import pytest

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.wx, pytest.mark.subprocess]

from hpc_gui.wx_terminal_webview import _is_webview_available

ASSETS = pathlib.Path(__file__).parents[1] / "src" / "hpc_gui" / "assets" / "terminal"


def _run(code, timeout=15):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=timeout, env=env,
    )


def _wrap(code):
    return textwrap.dedent(code)


def test_reconnect_replaces_output_subscriber():
    """Replacing SSH adapters detaches the old and retains one new subscriber."""
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
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): pass

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
for i in range(100):
    new = Fake()
    panel.set_ssh(new)
    assert len(new._wx_output_subscribers) == 1
assert len(ssh._wx_output_subscribers) == 0
panel.close(); frame.Destroy(); os._exit(0)
"""))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"


@pytest.mark.unit
@pytest.mark.semantic
def test_repeated_font_find_clear_bridge_calls_stay_bounded():
    """Repeated font, find, and clear commands remain within font limits."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    r = _run(_wrap("""
import sys, os
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
assert panel._ready
for i in range(100):
    panel.hpc_set_font_size(10 + (i % 20))
    panel.hpc_find(f"q{i}")
    panel.hpc_clear()
assert 6 <= panel._font_size <= 32
panel.close(); frame.Destroy(); os._exit(0)
"""))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"


@pytest.mark.unit
@pytest.mark.resource
@pytest.mark.semantic
def test_close_after_queued_output_is_idempotent():
    """Closing after output calls leaves the panel closed and is idempotent."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    r = _run(_wrap("""
import sys, os
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
assert panel._ready
for i in range(100):
    panel.hpc_write(f"data_{i}\\n")
panel.close()
assert panel._closed
panel.close()  # idempotent
assert panel._closed
os._exit(0)
"""))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"
