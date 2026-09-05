"""Wave 51 multi-document real-event tests."""
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.wx_editor_view import build_editor_panel

def _make_panel():
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    panel = build_editor_panel(frame, path="/tmp/a.sh", content="hello", is_local=True)
    frame.Show()
    wx.Yield()
    return app, frame, panel

def _close_panel(frame):
    try:
        frame.Close()
    except: pass
    for _ in range(3):
        wx.Yield()
    try:
        if not frame.IsBeingDeleted():
            frame.Destroy()
    except: pass
    for _ in range(3):
        wx.Yield()

def test_wx_editor_open_second_document_creates_tab():
    app, frame, panel = _make_panel()
    try:
        tabs = panel._wx_editor_controls["doc_tabs"]
        assert tabs.GetPageCount() == 1
        panel._wx_editor_load_document("/tmp/b.sh", "world", is_local=True)
        wx.Yield()
        assert tabs.GetPageCount() == 2
        assert tabs.GetPageText(1) == "b.sh"
    finally:
        _close_panel(frame)

def test_wx_editor_open_third_document_preserves_existing_tabs():
    app, frame, panel = _make_panel()
    try:
        tabs = panel._wx_editor_controls["doc_tabs"]
        panel._wx_editor_load_document("/tmp/b.sh", "b", is_local=True)
        wx.Yield()
        panel._wx_editor_load_document("/tmp/c.sh", "c", is_local=True)
        wx.Yield()
        assert tabs.GetPageCount() == 3
        assert tabs.GetPageText(0) == "a.sh"
        assert tabs.GetPageText(1) == "b.sh"
        assert tabs.GetPageText(2) == "c.sh"
    finally:
        _close_panel(frame)

def test_wx_editor_switch_tab_updates_active_document():
    app, frame, panel = _make_panel()
    try:
        panel._wx_editor_load_document("/tmp/b.sh", "b-content", is_local=True)
        wx.Yield()
        tabs = panel._wx_editor_controls["doc_tabs"]
        model = panel._wx_editor_model
        # switch to first tab via notebook event
        tabs.SetSelection(0)
        evt = wx.BookCtrlEvent(wx.wxEVT_NOTEBOOK_PAGE_CHANGED, tabs.GetId())
        evt.SetSelection(0)
        evt.SetOldSelection(1)
        tabs.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        assert model.controller.active.path == "/tmp/a.sh"
        assert panel._wx_editor_controls["editor"].GetValue() == "hello"
        # switch to second
        tabs.SetSelection(1)
        evt2 = wx.BookCtrlEvent(wx.wxEVT_NOTEBOOK_PAGE_CHANGED, tabs.GetId())
        evt2.SetSelection(1)
        evt2.SetOldSelection(0)
        tabs.GetEventHandler().ProcessEvent(evt2)
        wx.Yield()
        assert model.controller.active.path == "/tmp/b.sh"
        assert panel._wx_editor_controls["editor"].GetValue() == "b-content"
    finally:
        _close_panel(frame)

def test_wx_editor_dirty_state_updates_tab_caption():
    app, frame, panel = _make_panel()
    try:
        tabs = panel._wx_editor_controls["doc_tabs"]
        editor = panel._wx_editor_controls["editor"]
        assert tabs.GetPageText(0) == "a.sh"
        editor.SetValue("hello modified")
        # trigger EVT_TEXT
        evt = wx.CommandEvent(wx.wxEVT_TEXT, editor.GetId())
        editor.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        assert "*" in tabs.GetPageText(0)
    finally:
        _close_panel(frame)

def test_wx_editor_save_clears_dirty_marker(monkeypatch):
    app, frame, panel = _make_panel()
    try:
        tabs = panel._wx_editor_controls["doc_tabs"]
        editor = panel._wx_editor_controls["editor"]
        editor.SetValue("modified")
        evt = wx.CommandEvent(wx.wxEVT_TEXT, editor.GetId())
        editor.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        assert "*" in tabs.GetPageText(0)
        # save via model mark_saved (simulate save)
        model = panel._wx_editor_model
        model.controller.mark_saved()
        panel._wx_editor_refresh_tabs()
        wx.Yield()
        assert "*" not in tabs.GetPageText(0)
    finally:
        _close_panel(frame)

def test_wx_editor_close_dirty_tab_save(monkeypatch):
    app, frame, panel = _make_panel()
    try:
        panel._wx_editor_load_document("/tmp/b.sh", "b", is_local=True)
        wx.Yield()
        tabs = panel._wx_editor_controls["doc_tabs"]
        # make first tab dirty
        tabs.SetSelection(0)
        evt = wx.BookCtrlEvent(wx.wxEVT_NOTEBOOK_PAGE_CHANGED, tabs.GetId())
        evt.SetSelection(0)
        tabs.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        editor = panel._wx_editor_controls["editor"]
        editor.SetValue("dirty a")
        evt2 = wx.CommandEvent(wx.wxEVT_TEXT, editor.GetId())
        editor.GetEventHandler().ProcessEvent(evt2)
        wx.Yield()
        assert "*" in tabs.GetPageText(0)
        monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)
        # close first tab (dirty) with save
        result = panel._wx_editor_close_tab(0)
        wx.Yield()
        assert result is True
        assert tabs.GetPageCount() == 1
        # remaining should be b.sh
        assert "b.sh" in tabs.GetPageText(0)
    finally:
        _close_panel(frame)

def test_wx_editor_close_dirty_tab_discard(monkeypatch):
    app, frame, panel = _make_panel()
    try:
        panel._wx_editor_load_document("/tmp/b.sh", "b", is_local=True)
        wx.Yield()
        tabs = panel._wx_editor_controls["doc_tabs"]
        tabs.SetSelection(0)
        evt = wx.BookCtrlEvent(wx.wxEVT_NOTEBOOK_PAGE_CHANGED, tabs.GetId())
        evt.SetSelection(0)
        tabs.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        editor = panel._wx_editor_controls["editor"]
        editor.SetValue("dirty")
        evt2 = wx.CommandEvent(wx.wxEVT_TEXT, editor.GetId())
        editor.GetEventHandler().ProcessEvent(evt2)
        wx.Yield()
        monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.NO)
        result = panel._wx_editor_close_tab(0)
        wx.Yield()
        assert result is True
        assert tabs.GetPageCount() == 1
    finally:
        _close_panel(frame)

def test_wx_editor_close_dirty_tab_cancel(monkeypatch):
    app, frame, panel = _make_panel()
    try:
        panel._wx_editor_load_document("/tmp/b.sh", "b", is_local=True)
        wx.Yield()
        tabs = panel._wx_editor_controls["doc_tabs"]
        tabs.SetSelection(0)
        evt = wx.BookCtrlEvent(wx.wxEVT_NOTEBOOK_PAGE_CHANGED, tabs.GetId())
        evt.SetSelection(0)
        tabs.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        editor = panel._wx_editor_controls["editor"]
        editor.SetValue("dirty2")
        evt2 = wx.CommandEvent(wx.wxEVT_TEXT, editor.GetId())
        editor.GetEventHandler().ProcessEvent(evt2)
        wx.Yield()
        monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.CANCEL)
        result = panel._wx_editor_close_tab(0)
        wx.Yield()
        assert result is False
        assert tabs.GetPageCount() == 2
    finally:
        _close_panel(frame)

def test_wx_editor_duplicate_path_reuses_existing_tab():
    app, frame, panel = _make_panel()
    try:
        tabs = panel._wx_editor_controls["doc_tabs"]
        panel._wx_editor_load_document("/tmp/b.sh", "b", is_local=True)
        wx.Yield()
        assert tabs.GetPageCount() == 2
        # open same path again
        panel._wx_editor_load_document("/tmp/b.sh", "b-new", is_local=True)
        wx.Yield()
        assert tabs.GetPageCount() == 2  # not duplicated
        # active should be b.sh tab
        assert panel._wx_editor_model.controller.active.path == "/tmp/b.sh"
    finally:
        _close_panel(frame)

def test_wx_editor_reorder_tabs_preserves_document_identity():
    app, frame, panel = _make_panel()
    try:
        panel._wx_editor_load_document("/tmp/b.sh", "b", is_local=True)
        panel._wx_editor_load_document("/tmp/c.sh", "c", is_local=True)
        wx.Yield()
        tabs = panel._wx_editor_controls["doc_tabs"]
        assert tabs.GetPageText(0) == "a.sh"
        # reorder 0->2
        panel._wx_editor_reorder_tabs(0, 2)
        wx.Yield()
        assert tabs.GetPageText(0) == "b.sh"
        assert tabs.GetPageText(2) == "a.sh"
        # identity preserved: active should still be c.sh (last opened)
        assert panel._wx_editor_model.controller.active.path == "/tmp/c.sh"
    finally:
        _close_panel(frame)

def test_wx_editor_standalone_window_is_independent():
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    panel = build_editor_panel(frame, path="/tmp/a.sh", content="a", is_local=True)
    frame.Show()
    wx.Yield()
    # standalone via show_editor
    from hpc_gui.wx_editor_view import show_editor
    standalone = show_editor(parent=frame, path="/tmp/standalone.sh", content="solo", is_local=True)
    wx.Yield()
    try:
        # embedded model should still have a.sh
        assert panel._wx_editor_model.controller.active.path == "/tmp/a.sh"
        # standalone should have solo
        assert standalone._wx_editor_model.controller.active.path == "/tmp/standalone.sh"
        # editing standalone should not affect embedded
        standalone._wx_editor_controls["editor"].SetValue("changed solo")
        evt = wx.CommandEvent(wx.wxEVT_TEXT, standalone._wx_editor_controls["editor"].GetId())
        standalone._wx_editor_controls["editor"].GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        assert panel._wx_editor_controls["editor"].GetValue() == "a"
    finally:
        try:
            standalone.Destroy()
        except: pass
        _close_panel(frame)
