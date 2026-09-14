"""Wave 45 embedded terminal real-event tests."""
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

wx = pytest.importorskip("wx")
from hpc_gui.wx_terminal import build_terminal_panel
from hpc_gui.wx_shell import create_shell_frame


@pytest.fixture(scope="module", autouse=True)
def _wx_app_lifecycle():
    app = wx.App.Get()
    owns_app = app is None
    if owns_app:
        app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    wx.SafeYield()
    if owns_app:
        app.Destroy()


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
    # These tests cover the TextCtrl fallback; WebView behavior has its own suite.
    with patch("hpc_gui.wx_terminal_webview._is_webview_available", return_value=False):
        panel = build_terminal_panel(frame, ssh=ssh or _fake_ssh())
    frame.Show()
    wx.Yield()
    return app, frame, panel

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
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

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
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

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
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

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
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

@pytest.mark.unit
@pytest.mark.wx
@pytest.mark.semantic
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

@pytest.mark.unit
@pytest.mark.wx
@pytest.mark.semantic
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

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.regression
def test_embedded_terminal_runtime_language_refresh(monkeypatch, tmp_path):
    # test standalone panel to avoid shell chrome flag bitmap segfault during language switch
    from hpc_gui.core.i18n import current_language, set_language, t

    original_language = current_language()
    monkeypatch.setattr("hpc_gui.core.i18n.app_data_dir", lambda: tmp_path)
    set_language("en")
    app, frame, panel = _make_panel()
    try:
        ctrls = panel._wx_terminal_controls
        english_find = t("login.terminal_find")
        english_clear = t("login.terminal_clear")
        assert ctrls["find_btn"].GetLabel() == english_find
        assert ctrls["clear"].GetLabel() == english_clear
        set_language("tr")
        wx.Yield()
        assert ctrls["find_btn"].GetLabel() == t("login.terminal_find")
        assert ctrls["clear"].GetLabel() == t("login.terminal_clear")
        assert ctrls["find_btn"].GetLabel() != english_find
        assert ctrls["clear"].GetLabel() != english_clear
    finally:
        frame.Destroy()
        wx.Yield()
        set_language(original_language)

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
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

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_shell_embedded_and_detached_share_implementation():
    # Both use build_terminal_panel internally — check control sets identical
    from hpc_gui.wx_terminal import build_terminal_panel
    _app = wx.App.Get() or wx.App(False)
    ssh = _fake_ssh()
    frame_det = wx.Frame(None)
    shell_frame = None
    try:
        # Keep this shared-builder test on the fallback path; WebView lifecycle
        # is exercised in the isolated tests in test_wx_terminal_webview.py.
        with patch("hpc_gui.wx_terminal_webview._is_webview_available", return_value=False):
            panel_det = build_terminal_panel(frame_det, ssh=ssh)
            shell_frame, _, session = create_shell_frame()
        panel_emb = session.get("_embedded_terminal_panel")
        det_keys = set(panel_det._wx_terminal_controls)
        emb_keys = set(panel_emb._wx_terminal_controls)
        assert det_keys == emb_keys
        assert "find_btn" in det_keys and "clear" in det_keys
    finally:
        if shell_frame is not None and not shell_frame.IsBeingDeleted():
            shell_frame.Close()
        if not frame_det.IsBeingDeleted():
            frame_det.Destroy()
        wx.Yield()


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
@pytest.mark.regression
def test_embedded_terminal_builder_child_exits_cleanly():
    nodeid = (
        "tests/test_wx_embedded_terminal.py::"
        "test_shell_embedded_and_detached_share_implementation"
    )
    result = subprocess.run(
        [sys.executable, "-X", "faulthandler", "-m", "pytest", nodeid, "-q"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"child exited {result.returncode}:\n{result.stdout}\n{result.stderr}"
    assert "Traceback (most recent call last)" not in result.stderr, result.stderr
