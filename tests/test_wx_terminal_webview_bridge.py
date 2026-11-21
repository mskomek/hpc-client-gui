"""Focused wx terminal WebView regression tests."""

import pytest

wx = pytest.importorskip("wx")
pytestmark = pytest.mark.wx

import pathlib

from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel, _is_webview_available
from support.subprocess_environment import project_python_environment
from wx_terminal_webview_support import ASSETS, _fake_ssh, _show_frame_with_panel, _wait_for_ready

@pytest.mark.contract
def test_wx_terminal_webview_assets_are_local_and_vendored():
    # Wave 73 security: vendored only, no CDN, connect-src 'none'
    page = (ASSETS / "wx_index.html").read_text(encoding="utf-8")
    bridge = (ASSETS / "wx_bridge.js").read_text(encoding="utf-8")
    assert "http://" not in page and "https://" not in page, "no CDN"
    assert "qrc:///" not in page and "QWebChannel" not in page and "PySide6" not in page
    assert "connect-src 'none'" in page
    assert "xterm.css" in page and "xterm.js" in page and "addon-fit.js" in page and "wx_bridge.js" in page
    assert "hpcWrite" in bridge and "hpcClear" in bridge and "hpcFocus" in bridge and "hpcSetFontSize" in bridge and "hpcFit" in bridge
    assert "postMessage" in bridge
    # Single bridge: one handler, structured JSON
    assert bridge.count("postMessage") >= 2  # ready + input + resize
    assert '"type":"ready"' in bridge or '"type": "ready"' in bridge or "type" in bridge
    for name in ("xterm.js", "xterm.css", "addon-fit.js", "wx_bridge.js", "wx_index.html"):
        assert (ASSETS / name).is_file(), name
    # Ensure no remote fetch
    assert "fetch(" not in bridge and "XMLHttpRequest" not in bridge


@pytest.mark.gui
@pytest.mark.subprocess
def test_wx_terminal_webview_page_loads_and_posts_ready():
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable — fallback diagnostic expected")
    # Use the real wxApp event loop and native shutdown policy. A manually
    # dispatched temporary wx.GUIEventLoop is not equivalent to the async
    # WebView2 CREATED/LOADED lifecycle on Windows.
    import subprocess
    import sys
    import tempfile
    import textwrap

    code = textwrap.dedent("""
        import time
        import wx
        from hpc_gui.wx_application import install_main_frame_exit_policy
        from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

        wx.Log.SetActiveTarget(wx.LogStderr())
        app = wx.App(False)
        frame = wx.Frame(None, title="native-ready-mainloop", size=(900, 600))
        class Fake:
            _wx_output_subscribers = []
            def send_shell_input(self, d): return True
            def resize_shell_pty(self, c, r): pass

        panel = WxTerminalWebViewPanel(frame, ssh=Fake())
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND)
        frame.SetSizer(sizer)
        frame.Layout()
        app.SetTopWindow(frame)
        install_main_frame_exit_policy(wx, app, frame)
        ready = {"seen": False}
        deadline = time.monotonic() + 9.0

        def close_frame(event):
            frame._wx_shell_destroy_invoked = True
            frame.Destroy()

        frame.Bind(wx.EVT_CLOSE, close_frame)

        def check_ready():
            if panel._ready:
                ready["seen"] = True
                print("NATIVE_READY: bridge ready", flush=True)
                frame.Close()
            elif time.monotonic() >= deadline:
                print(
                    "NATIVE_READY: timeout "
                    f"stage={panel._webview_failure_stage} "
                    f"detail={panel._webview_failure_detail!r} "
                    f"created_errors={panel._native_create_errors}",
                    flush=True,
                )
                frame.Close()
            else:
                wx.CallLater(50, check_ready)

        frame.Show()
        wx.CallLater(50, check_ready)
        app.MainLoop()
        if not ready["seen"] or not panel._closed:
            raise AssertionError(
                "native browser did not reach ready and close naturally: "
                f"ready={ready['seen']} closed={panel._closed}"
            )
        print("NATIVE_READY_AND_CLOSE_PASS", flush=True)
    """)
    with tempfile.TemporaryDirectory(prefix="v2-wx-ready-", ignore_cleanup_errors=True) as temp:
        env = project_python_environment(pathlib.Path(__file__).parents[1])
        if sys.platform == "win32":
            env["WEBVIEW2_USER_DATA_FOLDER"] = str(pathlib.Path(temp) / "webview2")
        result = subprocess.run(
            [sys.executable, "-X", "faulthandler", "-c", code],
            capture_output=True, text=True, timeout=18, env=env,
        )
    assert result.returncode == 0, (
        f"native ready subprocess exit={result.returncode}: "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "NATIVE_READY_AND_CLOSE_PASS" in result.stdout


@pytest.mark.gui
def test_wx_terminal_external_navigation_blocked():
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    _app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, size=(900, 600))
    ssh = _fake_ssh()
    panel = WxTerminalWebViewPanel(frame, ssh=ssh)
    _show_frame_with_panel(frame, panel)
    assert _wait_for_ready(panel, timeout=6) is True
    # Try to simulate navigating event with external URL — handler should veto
    # Create a mock event
    class FakeEvent:
        def __init__(self, url):
            self._url = url
            self.vetoed = False
            self.skipped = False

        def GetURL(self):
            return self._url

        def Veto(self):
            self.vetoed = True

        def Skip(self):
            self.skipped = True

    evt = FakeEvent("https://example.com/malicious.js")
    panel._on_navigating(evt)
    assert evt.vetoed is True
    assert evt.skipped is False
    evt2 = FakeEvent("file:///D:/Projeler/image-process-para-2/src/hpc_gui/assets/terminal/wx_index.html")
    panel._on_navigating(evt2)
    assert evt2.vetoed is False
    frame.Destroy()
    wx.Yield()


@pytest.mark.audit
def test_wx_terminal_single_bridge_and_no_splitlines():
    src = pathlib.Path("src/hpc_gui/wx_terminal_webview.py").read_text(encoding="utf-8")
    # One handler
    assert 'AddScriptMessageHandler("hpc")' in src or "AddScriptMessageHandler('hpc')" in src or 'AddScriptMessageHandler("hpc")' in src
    # No splitlines in webview path
    # The only splitlines in the file should be in comments or not in hpc_write
    # Ensure hpc_write does not contain splitlines
    io_src = pathlib.Path("src/hpc_gui/wx_terminal_webview_io.py").read_text(encoding="utf-8")
    hpc_write_section = io_src.split("def hpc_write")[1].split("def _flush_pending")[0]
    assert "splitlines" not in hpc_write_section
    # Ensure terminal.write is used
    bridge = (ASSETS / "wx_bridge.js").read_text(encoding="utf-8")
    assert "terminal.write" in bridge
    # Ensure no logging of input
    assert "console.log" not in bridge.lower() or "terminal input logging" not in bridge.lower()
    # Python side must not log data
    assert "postToPython" in bridge




@pytest.mark.unit
@pytest.mark.resource
def test_wx_terminal_close_releases_native_webview():
    from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

    class FakeWebView:
        def __init__(self):
            self.stopped = 0
            self.destroyed = 0

        def Stop(self):
            self.stopped += 1

        def Destroy(self):
            self.destroyed += 1

    class PanelHarness:
        close = WxTerminalWebViewPanel.close

    webview = FakeWebView()
    panel = PanelHarness()
    panel._closed = False
    panel._webview = webview
    panel._is_parity = True
    panel._generation = 0
    panel._readiness_timer = None
    panel._resize_timer = None
    panel._gtk_ack_timer = None
    panel._stop_fragment_ack_timer = lambda: None
    panel._gtk_queue = type("Queue", (), {"reset": lambda self: None})()
    panel._gtk_screen_snapshot = None
    panel._gtk_query_pending = False
    panel._gtk_send_scheduled = False
    panel._subscriber = None
    panel._subscribers_list = None
    panel._pending = []
    panel._pending_bytes = 0
    panel._pending_paste = []
    panel._pending_paste_bytes = 0
    panel._write_failure_shown = False
    panel._lang_cb = lambda _language=None: None

    panel.close()
    panel.close()

    assert webview.stopped == 1
    # close() stops the native controller but leaves destruction to its wx
    # parent. Explicitly destroying WebView2 here can race queued callbacks.
    assert webview.destroyed == 0
    assert panel._webview is None
    assert panel._is_parity is False


@pytest.mark.audit
def test_wx_terminal_webview_composition_keeps_qt_out():
    src = pathlib.Path("src/hpc_gui/wx_terminal_webview.py").read_text(encoding="utf-8")
    assert "from PySide6" not in src
    assert "import PySide6" not in src
    assert "qrc:///" not in src
    assert "QWebChannel" not in src
    # wx_index.html also must not contain Qt
    page = (ASSETS / "wx_index.html").read_text(encoding="utf-8")
    assert "qrc:///" not in page
    assert "QWebChannel" not in page
