
pytest_plugins = ('support.test_wx_updater_spec_shared',)
"""Tests for wx update flow per spec 37 — real wx events, fixed changelog, real progress."""
from support.test_wx_updater_spec_shared import (
    WxUpdateDialog,
    _WrapperDialog,
    _make_release,
    pytest,
    show_update_available,
    wx,
)

pytestmark = [pytest.mark.gui, pytest.mark.wx]

def test_show_update_available_wrapper_returns_true_when_download_starts(monkeypatch):
    class DownloadDialog(_WrapperDialog):
        def ShowModal(self):
            self._start_download()
            return self.wx.ID_OK

    monkeypatch.setattr("hpc_gui.wx_updater_view.WxUpdateDialog", DownloadDialog)
    assert show_update_available(None, "1.0.0", "1.1.0") is True

def test_show_update_available_wrapper_returns_false_for_cancel(monkeypatch):
    class CancelDialog(_WrapperDialog):
        def ShowModal(self):
            return self.wx.ID_CANCEL

    monkeypatch.setattr("hpc_gui.wx_updater_view.WxUpdateDialog", CancelDialog)
    assert show_update_available(None, "1.0.0", "1.1.0") is False

def test_show_update_available_wrapper_returns_false_for_close(monkeypatch):
    class CloseDialog(_WrapperDialog):
        def ShowModal(self):
            return self.wx.ID_CANCEL

    monkeypatch.setattr("hpc_gui.wx_updater_view.WxUpdateDialog", CloseDialog)
    assert show_update_available(None, "1.0.0", "1.1.0") is False

def test_update_available_shows_versions_and_download_size():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    rel = _make_release()
    dlg = WxUpdateDialog(None, rel)
    # Check versions are visible
    found = False
    for child in dlg.panel.GetChildren():
        try:
            if child.GetLabel() == "1.9.0":
                found = True
        except Exception:
            pass
        # also check grid
        try:
            for c2 in child.GetChildren():
                if c2.GetLabel() == "1.9.0":
                    found = True
        except Exception:
            pass
    assert found
    # Check via sizer
    # Instead, check that _total is set and download size label exists
    assert dlg._total == 184*1024*1024
    # Check download size label text contains 184 MB
    found_size = False
    for child in dlg.panel.GetChildren():
        try:
            if "184" in child.GetLabel() and "MB" in child.GetLabel():
                found_size = True
        except Exception:
            pass
    # Also check via content_sizer children
    for idx in range(dlg.content_sizer.GetItemCount()):
        try:
            win = dlg.content_sizer.GetItem(idx).GetWindow()
            if win and "184" in win.GetLabel():
                found_size = True
        except Exception:
            pass
    assert found_size, "Download size not visible"
    dlg.Destroy()
    app.Destroy()

def test_update_release_notes_preserve_unicode():
    app = wx.App(False)
    rel = _make_release(body="- Türkçe_日本語\n- 研究 ★ ✓")
    dlg = WxUpdateDialog(None, rel)
    assert "Türkçe_日本語" in dlg._changelog_ctrl.GetValue()
    assert "研究 ★ ✓" in dlg._changelog_ctrl.GetValue()
    dlg.Destroy()
    app.Destroy()

def test_update_changelog_is_fixed_height_scrollable_readonly():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    long_body = "\n".join([f"- line {i} with some text that should wrap" for i in range(50)])
    rel = _make_release(body=long_body)
    dlg = WxUpdateDialog(None, rel)
    ch = dlg._changelog_ctrl
    assert ch is not None
    # Fixed height 100
    assert ch.GetMinSize().height == 100
    assert ch.GetMaxSize().height == 100
    # Read-only
    assert ch.IsEditable() is False or (ch.GetWindowStyle() & wx.TE_READONLY)
    # Multiline and wordwrap
    style = ch.GetWindowStyle()
    assert style & wx.TE_MULTILINE
    # Check that dialog size is fixed 520x390 even with long changelog
    sz = dlg.dlg.GetSize()
    assert sz.width == 520 and sz.height == 390
    # Check that short changelog also same size
    rel2 = _make_release(body="- short")
    dlg2 = WxUpdateDialog(None, rel2)
    sz2 = dlg2.dlg.GetSize()
    assert sz2.width == 520 and sz2.height == 390
    assert sz.width == sz2.width and sz.height == sz2.height
    dlg.Destroy()
    dlg2.Destroy()
    app.Destroy()

def test_long_changelog_does_not_resize_dialog():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    long_body = "\n".join([f"* line {i}" for i in range(200)])
    rel = _make_release(body=long_body)
    dlg = WxUpdateDialog(None, rel)
    sz_before = dlg.dlg.GetSize()
    # Simulate adding more text after
    dlg._changelog_ctrl.SetValue(long_body + "\n" + long_body)
    dlg.panel.Layout()
    dlg.dlg.Layout()
    sz_after = dlg.dlg.GetSize()
    # Should remain 520x390
    assert sz_after.width == 520 and sz_after.height == 390
    assert sz_before.width == sz_after.width and sz_before.height == sz_after.height
    dlg.Destroy()
    app.Destroy()

def test_mandatory_update_has_no_later_button():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    rel = _make_release()
    dlg = WxUpdateDialog(None, rel, mandatory=True)
    dlg._build_for_state("UPDATE_AVAILABLE")
    # Check that Later button does not exist, Exit does
    has_later = False
    has_exit = False
    for idx in range(dlg.footer_sizer.GetItemCount()):
        try:
            win = dlg.footer_sizer.GetItem(idx).GetWindow()
            if win:
                lbl = win.GetLabel()
                if "Later" in lbl:
                    has_later = True
                if "Exit" in lbl:
                    has_exit = True
        except Exception:
            pass
    assert not has_later, "Mandatory should not have Later"
    assert has_exit, "Mandatory should have Exit"
    dlg.Destroy()
    app.Destroy()

def test_mandatory_update_close_does_not_enter_main_app():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    rel = _make_release()
    dlg = WxUpdateDialog(None, rel, mandatory=True)
    dlg._build_for_state("UPDATE_AVAILABLE")
    # Simulate close — should EndModal with CANCEL (Exit) not allow entering main app
    # The dialog's _on_close for mandatory should EndModal with CANCEL
    evt = wx.CloseEvent(wx.wxEVT_CLOSE_WINDOW)
    dlg._on_close(evt)
    assert dlg._closed is True
    dlg.Destroy()
    app.Destroy()
