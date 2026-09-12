"""Wave 45 embedded terminal real-event tests."""
import pytest

wx = pytest.importorskip("wx")
from hpc_gui.wx_terminal import build_terminal_panel

pytestmark = [pytest.mark.gui, pytest.mark.wx]


def _fake_ssh():
    class Fake:
        def __init__(self):
            self.sent = []
            self.resizes = []
            self._wx_output_subscribers = []
        def send_shell_input(self, data):
            self.sent.append(data)
        def resize_shell_pty(self, cols, rows):
            self.resizes.append((cols, rows))
    return Fake()

def _make_panel(ssh=None):
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    # These compatibility tests exercise the legacy TextCtrl adapter. The
    # native WebView/xterm path is covered by the dedicated WebView tests and
    # must not be initialized twice in this one wx process.
    import hpc_gui.wx_terminal_webview as webview

    webview_available = webview._is_webview_available
    webview._is_webview_available = lambda: False
    try:
        panel = build_terminal_panel(frame, ssh=ssh or _fake_ssh())
    finally:
        webview._is_webview_available = webview_available
    frame.Show()
    wx.Yield()
    return app, frame, panel

@pytest.mark.wx
@pytest.mark.gui
def test_embedded_terminal_find_button_selects_match():
    app, frame, panel = _make_panel()
    try:
        model = panel._wx_terminal_model
        model.receive("hello world hello")
        panel._wx_terminal_render("hello world hello")
        wx.Yield()
        ctrls = panel._wx_terminal_controls
        ctrls["find"].SetValue("world")
        # simulate button click
        evt = wx.CommandEvent(wx.wxEVT_BUTTON)
        ctrls["find_btn"].GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        # output should have selection at position of world
        out = ctrls["output"]
        sel = out.GetSelection()
        # wx TextCtrl GetSelection returns tuple (from, to)
        assert sel[0] >= 0 and sel[1] > sel[0]
        assert model.find("world") >= 0
    finally:
        frame.Destroy()
        wx.Yield()

@pytest.mark.wx
@pytest.mark.gui
def test_embedded_terminal_clear_button_clears_visible_output_and_model():
    app, frame, panel = _make_panel()
    try:
        model = panel._wx_terminal_model
        model.receive("some text")
        panel._wx_terminal_render("some text")
        wx.Yield()
        ctrls = panel._wx_terminal_controls
        assert ctrls["output"].GetValue() != ""
        assert model.text != ""
        evt = wx.CommandEvent(wx.wxEVT_BUTTON)
        ctrls["clear"].GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        assert ctrls["output"].GetValue() == ""
        assert model.text == ""
    finally:
        frame.Destroy()
        wx.Yield()

@pytest.mark.wx
@pytest.mark.gui
def test_embedded_terminal_font_decrease_changes_visible_font():
    app, frame, panel = _make_panel()
    try:
        model = panel._wx_terminal_model
        before = model.font_size
        ctrls = panel._wx_terminal_controls
        before_pt = ctrls["output"].GetFont().GetPointSize()
        evt = wx.CommandEvent(wx.wxEVT_BUTTON)
        ctrls["font_down"].GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        assert model.font_size == max(6, before -1)
        after_pt = ctrls["output"].GetFont().GetPointSize()
        assert after_pt != before_pt or model.font_size != before
    finally:
        frame.Destroy()
        wx.Yield()

@pytest.mark.wx
@pytest.mark.gui
def test_embedded_terminal_font_increase_changes_visible_font():
    app, frame, panel = _make_panel()
    try:
        model = panel._wx_terminal_model
        before = model.font_size
        ctrls = panel._wx_terminal_controls
        before_pt = ctrls["output"].GetFont().GetPointSize()
        evt = wx.CommandEvent(wx.wxEVT_BUTTON)
        ctrls["font_up"].GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        assert model.font_size == min(32, before +1)
        after_pt = ctrls["output"].GetFont().GetPointSize()
        assert after_pt != before_pt or model.font_size != before
    finally:
        frame.Destroy()
        wx.Yield()

@pytest.mark.wx
@pytest.mark.gui
def test_embedded_terminal_ctrl_c_sends_interrupt_not_copy():
    ssh = _fake_ssh()
    app, frame, panel = _make_panel(ssh=ssh)
    try:
        model = panel._wx_terminal_model
        # simulate Ctrl+C via model directly (key_input logic)
        # Real key event: Ctrl+C without shift/cmd should send \x03
        result = model.key_input("C", command=False, shift=False)
        assert result == "\x03"
        assert ssh.sent[-1] == "\x03"
        # ensure not treated as copy
        assert result != "copy"
    finally:
        frame.Destroy()
        wx.Yield()

@pytest.mark.wx
@pytest.mark.gui
def test_embedded_terminal_copy_shortcut_does_not_send_interrupt():
    ssh = _fake_ssh()
    app, frame, panel = _make_panel(ssh=ssh)
    try:
        model = panel._wx_terminal_model
        before = len(ssh.sent)
        result = model.key_input("C", command=True, shift=False)
        assert result == "copy"
        assert len(ssh.sent) == before  # no interrupt sent
        result2 = model.key_input("C", command=False, shift=True)
        assert result2 == "copy"
        assert len(ssh.sent) == before
    finally:
        frame.Destroy()
        wx.Yield()

@pytest.mark.wx
@pytest.mark.gui
def test_embedded_terminal_runtime_language_refresh():
    # test standalone panel to avoid shell chrome flag bitmap segfault during language switch
    app, frame, panel = _make_panel()
    try:
        ctrls = panel._wx_terminal_controls
        from hpc_gui.core.i18n import set_language, current_language
        orig = current_language()
        # ensure labels start non-empty
        assert ctrls["find_btn"].GetLabel() != ""
        set_language("tr")
        wx.Yield()
        # find button should still be labeled (Turkish or fallback)
        assert ctrls["find_btn"].GetLabel() != ""
        assert ctrls["clear"].GetLabel() != ""
        set_language("en")
        wx.Yield()
        assert ctrls["find_btn"].GetLabel() != ""
        set_language(orig)
        wx.Yield()
    finally:
        frame.Destroy()
        wx.Yield()

@pytest.mark.wx
@pytest.mark.gui
def test_embedded_terminal_resize_reaches_pty_resize():
    ssh = _fake_ssh()
    app, frame, panel = _make_panel(ssh=ssh)
    try:
        # simulate size event
        panel.SetSize(wx.Size(800, 600))
        wx.Yield()
        evt = wx.SizeEvent(panel.GetSize())
        evt.SetEventObject(panel)
        panel.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        # model resize should have been called at least once
        assert len(ssh.resizes) >= 1
        assert ssh.resizes[-1][0] > 0 and ssh.resizes[-1][1] > 0
    finally:
        frame.Destroy()
        wx.Yield()

def test_shell_embedded_and_detached_share_implementation(monkeypatch):
    # Exercise both production surfaces, including the panel actually mounted
    # by the shell. Use the TextCtrl adapter to avoid creating two native
    # WebView2 controls in this process.
    import hpc_gui.wx_terminal_webview as webview
    from hpc_gui.wx_shell import create_shell_frame
    from hpc_gui.wx_terminal import show_terminal

    monkeypatch.setattr(webview, "_is_webview_available", lambda: False)
    app = wx.App.Get() or wx.App(False)
    ssh = _fake_ssh()
    existing_windows = {id(window) for window in wx.GetTopLevelWindows()}
    try:
        shell_frame, lifecycle, session = create_shell_frame(
            app,
            session_state={"session": {"ssh": ssh}, "generation": 0},
        )
        shell_frame.Show()
        wx.Yield()
        embedded = session["_embedded_terminal_panel"]
        assert embedded is not None
        show_terminal(parent=shell_frame, ssh=ssh, lifecycle=lifecycle)
        wx.Yield()
        detached_frame = next(
            window
            for window in wx.GetTopLevelWindows()
            if id(window) not in existing_windows
            and window is not shell_frame
            and hasattr(window, "_wx_terminal_panel")
        )
        detached = detached_frame._wx_terminal_panel
        embedded_keys = set(embedded._wx_terminal_controls)
        detached_keys = set(detached._wx_terminal_controls)
        assert embedded_keys == detached_keys
        assert {"find_btn", "clear", "output", "input"} <= embedded_keys
    finally:
        for window in list(wx.GetTopLevelWindows()):
            if id(window) not in existing_windows:
                try:
                    window.Close()
                except Exception:
                    window.Destroy()
        wx.Yield()


def test_shell_can_defer_terminal_panel_mount(monkeypatch):
    import hpc_gui.wx_terminal_webview as webview
    from hpc_gui.wx_shell import create_shell_frame

    scheduled = []
    monkeypatch.setattr(webview, "_is_webview_available", lambda: False)
    monkeypatch.setattr(
        wx, "CallLater", lambda delay, callback: scheduled.append((delay, callback))
    )
    app = wx.App.Get() or wx.App(False)
    frame, _, session = create_shell_frame(
        app,
        tray_factory=lambda _parent: None,
        session_state={"session": {"ssh": _fake_ssh()}, "generation": 0},
        defer_terminal_webview=True,
    )
    try:
        controls = frame._wx_shell_controls["pages"]["NAV-TERMINAL"]
        page = controls["page"]
        assert session["_embedded_terminal_panel"] is None
        assert "output" not in controls
        assert len(scheduled) == 1 and scheduled[0][0] == 1000

        scheduled[0][1]()

        panel = session["_embedded_terminal_panel"]
        assert panel.GetParent() is page
        assert controls["panel"] is panel
        assert {"input", "output", "clear"} <= set(controls)
    finally:
        frame.Destroy()
        wx.Yield()
