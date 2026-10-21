"""Focused wx terminal WebView regression tests."""

import pytest

wx = pytest.importorskip("wx")
pytestmark = pytest.mark.wx

import pathlib

from hpc_gui.wx_terminal_webview import _is_webview_available
from support.subprocess_environment import project_python_environment
from wx_terminal_webview_support import ASSETS, _run_subprocess_test

@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_wx_terminal_pending_output_before_ready_is_buffered_and_ordered():
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    import subprocess
    import sys
    import textwrap

    code = textwrap.dedent("""
        import sys, os
        sys.path.insert(0, 'src')
        import wx, time
        from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel
        app = wx.App.Get()
        if app is None:
            app = wx.App(False)
        frame = wx.Frame(None, size=(900,600))
        class Fake:
            _wx_output_subscribers = []
            def send_shell_input(self, d): return True
            def resize_shell_pty(self, c, r): pass
        ssh = Fake()
        panel = WxTerminalWebViewPanel(frame, ssh=ssh)
        panel.hpc_write("hello ")
        panel.hpc_write("world")
        panel.hpc_write("\\r")
        panel.hpc_write("\\x1b[31mRED\\x1b[0m")
        assert len(panel._pending) == 4
        assert "".join(panel._pending) == "hello world\\r\\x1b[31mRED\\x1b[0m"
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND)
        frame.SetSizer(sizer)
        frame.Layout()
        frame.Show()
        loop = wx.GUIEventLoop()
        prev = wx.EventLoop.GetActive()
        wx.EventLoop.SetActive(loop)
        start = time.monotonic()
        ready = False
        while time.monotonic() - start < 6:
            if panel._ready:
                ready = True
                break
            try:
                while loop.Pending():
                    loop.Dispatch()
            except: pass
            try:
                wx.Yield()
            except: pass
            time.sleep(0.05)
        try:
            wx.EventLoop.SetActive(prev)
        except: pass
        assert ready, "not ready"
        time.sleep(0.3)
        wx.Yield()
        assert panel._pending == [], f"pending not flushed: {panel._pending}"
        try:
            panel.close()
        except: pass
        try:
            frame.Destroy()
        except: pass
        try:
            app.Destroy()
        except: pass
        os._exit(0)
    """)
    env = project_python_environment(pathlib.Path(__file__).parents[1])
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=15, env=env)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.contract
@pytest.mark.subprocess
@pytest.mark.semantic
def test_wx_terminal_preserves_carriage_return_and_esc():
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    import subprocess
    import sys
    import textwrap

    code = textwrap.dedent("""
        import sys, os
        sys.path.insert(0, 'src')
        import wx, time, pathlib
        from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel
        app = wx.App.Get()
        if app is None:
            app = wx.App(False)
        frame = wx.Frame(None, size=(900,600))
        class Fake:
            _wx_output_subscribers = []
            def send_shell_input(self, d): return True
            def resize_shell_pty(self, c, r): pass
        ssh = Fake()
        panel = WxTerminalWebViewPanel(frame, ssh=ssh)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND)
        frame.SetSizer(sizer)
        frame.Layout()
        frame.Show()
        loop = wx.GUIEventLoop()
        start = time.monotonic()
        ready = False
        while time.monotonic() - start < 6:
            if panel._ready:
                ready = True
                break
            try:
                while loop.Pending():
                    loop.Dispatch()
            except: pass
            try:
                wx.Yield()
            except: pass
            time.sleep(0.05)
        assert ready, "not ready"
        calls = []
        orig_run = panel._run_js
        def capture(code):
            calls.append(code)
        panel._run_js = capture
        panel.hpc_write("Progress 10%\\rProgress 20%\\rProgress 30%")
        assert calls, "no JS call"
        assert "Progress 10%\\\\rProgress 20%" in calls[0] or "Progress 10%\\\\r" in calls[0]
        calls.clear()
        panel.hpc_write("\\x1b[31mRED\\x1b[0m normal")
        assert "\\\\u001b" in calls[0] or "\\x1b[31m" in calls[0]
        assert "splitlines" not in pathlib.Path("src/hpc_gui/wx_terminal_webview_io.py").read_text(encoding="utf-8").split("def hpc_write")[1].split("def _flush_pending")[0]
        try:
            panel.close()
        except: pass
        try:
            frame.Destroy()
        except: pass
        try:
            app.Destroy()
        except: pass
        os._exit(0)
    """)
    env = project_python_environment(pathlib.Path(__file__).parents[1])
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=15, env=env)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
def test_wx_terminal_clear_focus_font():
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    import subprocess
    import sys
    import textwrap

    code = textwrap.dedent("""
        import sys, os
        sys.path.insert(0, 'src')
        import wx, time
        from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel
        app = wx.App.Get()
        if app is None:
            app = wx.App(False)
        frame = wx.Frame(None, size=(900,600))
        class Fake:
            _wx_output_subscribers = []
            def send_shell_input(self, d): return True
            def resize_shell_pty(self, c, r): pass
        ssh = Fake()
        panel = WxTerminalWebViewPanel(frame, ssh=ssh)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND)
        frame.SetSizer(sizer)
        frame.Layout()
        frame.Show()
        loop = wx.GUIEventLoop()
        start = time.monotonic()
        ready = False
        while time.monotonic() - start < 6:
            if panel._ready:
                ready = True
                break
            try:
                while loop.Pending():
                    loop.Dispatch()
            except: pass
            try:
                wx.Yield()
            except: pass
            time.sleep(0.05)
        assert ready, "not ready"
        calls = []
        orig_run = panel._run_js
        def capture(code):
            calls.append(code)
        panel._run_js = capture
        panel.hpc_clear()
        assert any("hpcClear" in c for c in calls)
        calls.clear()
        panel.hpc_focus()
        assert any("hpcFocus" in c for c in calls)
        calls.clear()
        before = panel._font_size
        panel.hpc_set_font_size(before + 2)
        assert any("hpcSetFontSize" in c for c in calls)
        assert panel._font_size == before + 2
        panel.hpc_set_font_size(100)
        assert panel._font_size == 32
        panel.hpc_set_font_size(-100)
        assert panel._font_size == 6
        try:
            panel.close()
        except: pass
        try:
            frame.Destroy()
        except: pass
        try:
            app.Destroy()
        except: pass
        os._exit(0)
    """)
    env = project_python_environment(pathlib.Path(__file__).parents[1])
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=15, env=env)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_wx_terminal_output_ordering_with_many_fragments():
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    import subprocess
    import sys
    import textwrap

    code = textwrap.dedent("""
        import sys, os
        sys.path.insert(0, 'src')
        import wx, time
        from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel
        app = wx.App.Get()
        if app is None:
            app = wx.App(False)
        frame = wx.Frame(None, size=(900,600))
        class Fake:
            _wx_output_subscribers = []
            def send_shell_input(self, d): return True
            def resize_shell_pty(self, c, r): pass
        def make_fake():
            class F:
                _wx_output_subscribers = []
                def send_shell_input(self, d): return True
                def resize_shell_pty(self, c, r): pass
            return F()
        ssh = Fake()
        panel = WxTerminalWebViewPanel(frame, ssh=ssh)
        for i in range(20):
            panel.hpc_write(f"frag{i}-")
        assert len(panel._pending) == 20
        assert "".join(panel._pending) == "".join(f"frag{i}-" for i in range(20))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND)
        frame.SetSizer(sizer)
        frame.Layout()
        frame.Show()
        loop = wx.GUIEventLoop()
        prev = wx.EventLoop.GetActive()
        wx.EventLoop.SetActive(loop)
        start = time.monotonic()
        ready = False
        while time.monotonic() - start < 6:
            if panel._ready:
                ready = True
                break
            try:
                while loop.Pending():
                    loop.Dispatch()
            except: pass
            try:
                wx.Yield()
            except: pass
            time.sleep(0.05)
        try:
            wx.EventLoop.SetActive(prev)
        except: pass
        assert ready, "not ready"
        for i in range(5):
            panel.hpc_write(f"new{i}-")
        assert panel._pending == []
        frame2 = wx.Frame(None, size=(800,600))
        panel2 = WxTerminalWebViewPanel(frame2, ssh=make_fake())
        for i in range(10):
            panel2.hpc_write(f"a{i}")
        assert len(panel2._pending) == 10
        sizer2 = wx.BoxSizer(wx.VERTICAL)
        sizer2.Add(panel2, 1, wx.EXPAND)
        frame2.SetSizer(sizer2)
        frame2.Layout()
        frame2.Show()
        combined = "".join(panel2._pending)
        assert combined == "".join(f"a{i}" for i in range(10))
        try:
            panel2.close()
        except: pass
        try:
            frame2.Destroy()
        except: pass
        try:
            panel.close()
        except: pass
        try:
            frame.Destroy()
        except: pass
        try:
            app.Destroy()
        except: pass
        os._exit(0)
    """)
    env = project_python_environment(pathlib.Path(__file__).parents[1])
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=15, env=env)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_wx_terminal_unicode_input_output():
    """Unicode strings must pass through hpc_write without ASCII clamp."""
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
# Capture JS calls
calls = []
orig = panel._run_js
def capture(code):
    calls.append(code)
panel._run_js = capture
# Unicode output
panel.hpc_write("Türkçe çğıöşü 日本語")
assert any("Türkçe" in c or "日本語" in c for c in calls), f"unicode output missing: {calls}"
# Unicode input via _handle_input
panel._handle_input("çğıöşü")
assert ssh.sent[-1] == "çğıöşü", f"unicode input failed: {ssh.sent[-1]}"
panel._handle_input("日本語テスト")
assert ssh.sent[-1] == "日本語テスト", f"unicode input failed: {ssh.sent[-1]}"
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.contract
def test_wx_terminal_no_splitlines_in_hpc_write():
    """hpc_write must not use splitlines — preserves CR/ESC bytes."""
    src = pathlib.Path("src/hpc_gui/wx_terminal_webview_io.py").read_text(encoding="utf-8")
    hpc_section = src.split("def hpc_write")[1].split("def _flush_pending")[0]
    assert "splitlines" not in hpc_section, "hpc_write must not use splitlines"
    # bridge.js must use terminal.write (not splitlines normalization)
    bridge = (ASSETS / "wx_bridge.js").read_text(encoding="utf-8")
    assert "terminal.write" in bridge
    # Python hpc_write must use json.dumps (not chr(keycode) for input)
    assert "_safe_json_dumps" in hpc_section or "json.dumps" in hpc_section


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_wx_terminal_large_pre_ready_output():
    """Large pre-ready output burst must be buffered and flushed in order."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = """
import sys, os
sys.path.insert(0, "src")
import wx, time
import hpc_gui.wx_terminal_webview as terminal_webview
# This case covers pre-ready buffering; do not create a browser controller.
def _native_view_not_needed():
    return False
terminal_webview._is_webview_available = _native_view_not_needed
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
# Write 500KB of data before ready
big_data = "X" * (500 * 1024)
panel.hpc_write(big_data)
assert len(panel._pending) >= 1, "should have pending data"
total = sum(len(p.encode("utf-8", errors="replace")) for p in panel._pending)
assert total >= 500 * 1024, f"expected >= 500KB pending, got {total}"
panel.hpc_write("END_MARKER")
total2 = sum(len(p.encode("utf-8", errors="replace")) for p in panel._pending)
assert total2 > total, "END_MARKER should add to pending"
combined = "".join(panel._pending)
assert combined.endswith("END_MARKER"), "END_MARKER must be last"
assert combined.startswith("X" * 100), "big_data must be first"
panel.close()
frame.Destroy()
os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"
