"""Focused wx terminal WebView regression tests."""

import pytest

wx = pytest.importorskip("wx")
pytestmark = pytest.mark.wx

from hpc_gui.wx_terminal_webview import _is_webview_available
from wx_terminal_webview_support import _run_subprocess_test

@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_wx_terminal_find_in_xterm_buffer():
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os, pathlib
sys.path.insert(0, 'src')
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class FakeSSH:
    def __init__(self):
        self._wx_output_subscribers = []
    def send_shell_input(self, d):
        return True
    def resize_shell_pty(self, c, r):
        pass

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
panel.hpc_find("test query")
assert any("hpcFind" in c and "test query" in c for c in calls), f"find not called: {calls}"
bridge = pathlib.Path("src/hpc_gui/assets/terminal/wx_bridge.js").read_text(encoding="utf-8")
assert "hpcFind" in bridge
assert "buffer.active" in bridge or "getLine" in bridge
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_wx_terminal_screen_state_readback_and_alternate_buffer():
    """Read the real xterm buffer and prove alternate-screen restoration."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import os, sys, time, traceback
sys.path.insert(0, 'src')
import wx
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class FakeSSH:
    _wx_output_subscribers = []
    def send_shell_input(self, data):
        return True
    def resize_shell_pty(self, cols, rows):
        pass

app = wx.App(False)
frame = wx.Frame(None, size=(1000, 700))
panel = WxTerminalWebViewPanel(frame, ssh=FakeSSH())
sizer = wx.BoxSizer(wx.VERTICAL)
sizer.Add(panel, 1, wx.EXPAND)
frame.SetSizer(sizer)
frame.Layout()
frame.Show()
if sys.platform.startswith('linux'):
    def pump(seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            wx.Yield()
            time.sleep(0.02)

    def read_state():
        for _ in range(20):
            state = panel.hpc_get_screen_state()
            if state is not None:
                return state
            pump(0.05)
        raise AssertionError('screen state readback returned None')

    try:
        deadline = time.monotonic() + 8
        while not panel._ready and time.monotonic() < deadline:
            pump(0.02)
        assert panel._ready and panel._is_parity, 'real WebView bridge did not become ready'
        panel.hpc_clear()
        pump(0.5)
        panel.hpc_write('NORMAL-LINE\\r\\n')
        pump(0.5)
        normal = read_state()
        assert normal['bufferType'] == 'normal', normal
        assert panel.hpc_get_line_text(0) == 'NORMAL-LINE'
        assert 'NORMAL-LINE' in (panel.hpc_get_buffer_text() or '')

        panel.hpc_write('\\x1b[?1049h')
        panel.hpc_write('\\x1b[2J\\x1b[HALT-SCREEN\\r\\n')
        pump(0.8)
        alternate = read_state()
        assert alternate['bufferType'] == 'alternate', alternate
        assert panel.hpc_get_line_text(0) == 'ALT-SCREEN'
        assert 'ALT-SCREEN' in (panel.hpc_get_buffer_text() or '')

        panel.hpc_write('\\x1b[?1049l')
        pump(0.8)
        restored = read_state()
        assert restored['bufferType'] == 'normal', restored
        assert panel.hpc_get_line_text(0) == 'NORMAL-LINE'
        assert 'ALT-SCREEN' not in (panel.hpc_get_buffer_text() or '')
    except BaseException:
        traceback.print_exc()
        os._exit(1)
    panel.close()
    frame.Destroy()
    os._exit(0)

failed = [False]

def schedule(milliseconds, callback):
    def run_safely():
        try:
            callback()
        except BaseException:
            failed[0] = True
            traceback.print_exc()
            app.ExitMainLoop()
    wx.CallLater(milliseconds, run_safely)

def read_state(callback, attempts=20):
    state = panel.hpc_get_screen_state()
    if state is not None:
        callback(state)
    elif attempts > 1:
        schedule(50, lambda: read_state(callback, attempts - 1))
    else:
        raise AssertionError('screen state readback returned None')

def verify_normal(state):
    assert state['bufferType'] == 'normal', state
    assert panel.hpc_get_line_text(0) == 'NORMAL-LINE'
    assert 'NORMAL-LINE' in (panel.hpc_get_buffer_text() or '')
    panel.hpc_write('\\x1b[?1049h')
    panel.hpc_write('\\x1b[2J\\x1b[HALT-SCREEN\\r\\n')
    schedule(800, lambda: read_state(verify_alternate))

def verify_alternate(state):
    assert state['bufferType'] == 'alternate', state
    assert panel.hpc_get_line_text(0) == 'ALT-SCREEN'
    assert 'ALT-SCREEN' in (panel.hpc_get_buffer_text() or '')
    panel.hpc_write('\\x1b[?1049l')
    schedule(800, lambda: read_state(verify_restored))

def verify_restored(state):
    assert state['bufferType'] == 'normal', state
    assert panel.hpc_get_line_text(0) == 'NORMAL-LINE'
    assert 'ALT-SCREEN' not in (panel.hpc_get_buffer_text() or '')
    app.ExitMainLoop()

def wait_for_ready(deadline):
    if panel._ready and panel._is_parity:
        panel.hpc_clear()
        schedule(500, lambda: panel.hpc_write('NORMAL-LINE\\r\\n'))
        schedule(1000, lambda: read_state(verify_normal))
    elif time.monotonic() >= deadline:
        raise AssertionError('real WebView bridge did not become ready')
    else:
        schedule(50, lambda: wait_for_ready(deadline))

schedule(0, lambda: wait_for_ready(time.monotonic() + 8))
app.MainLoop()
if failed[0]:
    os._exit(1)
panel.close()
frame.Destroy()
os._exit(0)
"""
    result = _run_subprocess_test(code, timeout=25)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_wx_terminal_find_next_and_prev():
    """Find, FindNext, FindPrev must advance through matches with wraparound."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os, pathlib
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class FakeSSH:
    _wx_output_subscribers = []
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): pass

app = wx.App(False)
frame = wx.Frame(None, size=(900, 600))
current_ssh = FakeSSH()
panel = WxTerminalWebViewPanel(frame, ssh=current_ssh)
panel._ready = True
panel._is_parity = True

# Capture JS calls
calls = []
orig = panel._run_js
def capture(code):
    calls.append(code)
panel._run_js = capture

# hpcFind should call JS hpcFind
panel.hpc_find("test")
assert any("hpcFind" in c and "test" in c for c in calls), f"hpcFind not called: {calls}"
calls.clear()

# hpcFindNext should call JS hpcFindNext
panel.hpc_find_next()
assert any("hpcFindNext" in c for c in calls), f"hpcFindNext not called: {calls}"
calls.clear()

# hpcFindPrev should call JS hpcFindPrev
panel.hpc_find_prev()
assert any("hpcFindPrev" in c for c in calls), f"hpcFindPrev not called: {calls}"
calls.clear()

# Bridge must have hpcFindNext and hpcFindPrev
bridge = pathlib.Path("src/hpc_gui/assets/terminal/wx_bridge.js").read_text(encoding="utf-8")
assert "hpcFindNext" in bridge, "hpcFindNext missing from bridge"
assert "hpcFindPrev" in bridge, "hpcFindPrev missing from bridge"
assert "translateToString" in bridge, "must use translateToString for buffer lines"
assert "hpcResetFindState" in bridge, "hpcResetFindState missing from bridge"

panel.close()
frame.Destroy()
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"
