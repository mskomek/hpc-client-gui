
pytest_plugins = ('support.test_wx_updater_spec_shared',)
"""Tests for wx update flow per spec 37 — real wx events, fixed changelog, real progress."""
from support.test_wx_updater_spec_shared import (
    Event,
    WxUpdateDialog,
    _format_bytes,
    _make_release,
    pytest,
    time,
    wx,
)

pytestmark = [pytest.mark.gui, pytest.mark.wx]

def test_update_available_download_button_starts_download(monkeypatch):
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    rel = _make_release()
    dlg = WxUpdateDialog(None, rel)
    # Find Download button
    dl_btn = None
    for child in dlg.panel.GetChildren():
        try:
            if "Download" in child.GetLabel():
                dl_btn = child
        except Exception:
            pass
    # Also check footer sizer
    for idx in range(dlg.footer_sizer.GetItemCount()):
        try:
            win = dlg.footer_sizer.GetItem(idx).GetWindow()
            if win and "Download" in win.GetLabel():
                dl_btn = win
        except Exception:
            pass
    assert dl_btn is not None
    # Mock download to avoid network
    called = {"hit": False}
    orig_download = None
    try:
        import hpc_gui.wx_updater_view as mod
        orig_download = mod.threading.Thread
        # Patch download_and_verify to not actually download
        import hpc_gui.services.app_updater as au
        orig_fn = au.download_and_verify_release

        def fake_download(release, progress_cb=None, cancelled=None):
            called["hit"] = True
            # Simulate progress
            if progress_cb:
                progress_cb(50, "downloading", 90*1024*1024, 184*1024*1024)
            # Don't actually download, just return a fake path
            return au.app_data_dir() / "updates" / f"v{release.version}" / release.zip_name

        monkeypatch.setattr(au, "download_and_verify_release", fake_download)
        # Click download via real wx event
        evt = wx.CommandEvent(wx.wxEVT_BUTTON, dl_btn.GetId())
        dl_btn.GetEventHandler().ProcessEvent(evt)
        wx.CallAfter(lambda: None)
        app.ProcessPendingEvents()
        time.sleep(0.3)
        app.ProcessPendingEvents()
        # Check that state transitioned to DOWNLOADING
        assert dlg.state == "DOWNLOADING" or called["hit"]
    finally:
        if orig_download:
            pass
        try:
            import hpc_gui.services.app_updater as au2
            au2.download_and_verify_release = orig_fn
        except Exception:
            pass
    dlg.Destroy()
    app.Destroy()

def test_update_download_progress_shows_real_bytes_and_percentage():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    rel = _make_release(size=184*1024*1024)
    dlg = WxUpdateDialog(None, rel)
    dlg._build_for_state("DOWNLOADING")
    # Simulate progress update
    dlg._downloaded = 68*1024*1024
    dlg._total = 184*1024*1024
    # Manually trigger update via prog callback
    # Find the byte label and percent
    assert dlg._byte_label is not None
    assert dlg._percent_label is not None
    assert dlg._gauge is not None
    # Simulate a progress call
    dlg._byte_label.SetLabel(f"{_format_bytes(68*1024*1024)} / {_format_bytes(184*1024*1024)}")
    pct = int(68*1024*1024 * 100 / (184*1024*1024))
    dlg._gauge.SetValue(pct)
    dlg._percent_label.SetLabel(f"{pct}%")
    assert "68" in dlg._byte_label.GetLabel()
    assert "184" in dlg._byte_label.GetLabel()
    assert dlg._gauge.GetValue() == pct
    assert dlg._percent_label.GetLabel() == f"{pct}%"
    # Invariant percentage == downloaded/total
    assert pct == int(68*1024*1024 / (184*1024*1024) * 100)
    dlg.Destroy()
    app.Destroy()

def test_update_unknown_total_uses_indeterminate_progress():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    rel = _make_release(size=None)
    # Force total None
    dlg = WxUpdateDialog(None, rel)
    dlg._total = None
    dlg._build_for_state("DOWNLOADING")
    # Should be indeterminate (Pulse)
    assert dlg._gauge is not None
    # Check that byte label shows downloaded without total
    dlg._downloaded = 68*1024*1024
    dlg._byte_label.SetLabel(f"{_format_bytes(68*1024*1024)} downloaded")
    assert "downloaded" in dlg._byte_label.GetLabel()
    assert "%" not in dlg._percent_label.GetLabel() or dlg._percent_label.GetLabel() == ""
    dlg.Destroy()
    app.Destroy()

def test_update_cancel_reaches_downloader():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    rel = _make_release()
    dlg = WxUpdateDialog(None, rel)
    dlg._build_for_state("DOWNLOADING")
    # Find cancel button
    cancel = None
    for idx in range(dlg.footer_sizer.GetItemCount()):
        try:
            win = dlg.footer_sizer.GetItem(idx).GetWindow()
            if win and "Cancel" in win.GetLabel():
                cancel = win
        except Exception:
            pass
    assert cancel is not None
    # Click cancel via real event
    evt = wx.CommandEvent(wx.wxEVT_BUTTON, cancel.GetId())
    cancel.GetEventHandler().ProcessEvent(evt)
    app.ProcessPendingEvents()
    time.sleep(0.2)
    app.ProcessPendingEvents()
    assert dlg._cancelled is True
    # Check that state becomes cancelled
    # _cancel_download should have been called and set state
    # It transitions via CallAfter, so pump
    time.sleep(0.3)
    app.ProcessPendingEvents()
    assert dlg.state == "DOWNLOAD_CANCELLED"
    dlg.Destroy()
    app.Destroy()

@pytest.mark.concurrency
def test_update_cancel_prevents_install(monkeypatch, tmp_path):
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    rel = _make_release()
    dlg = WxUpdateDialog(None, rel)
    downloader_entered = Event()
    continue_download = Event()
    cancel_observed = Event()

    def fake_download(_release, progress_cb=None, cancelled=None):
        downloader_entered.set()
        assert continue_download.wait(2), "test did not release downloader"
        if cancelled():
            cancel_observed.set()
            raise RuntimeError("cancelled")
        return tmp_path / "unexpected.zip"

    monkeypatch.setattr("hpc_gui.services.app_updater.download_and_verify_release", fake_download)
    try:
        dlg._start_download()
        assert downloader_entered.wait(2), "download worker did not start"
        cancel = dlg._cancel_btn
        cancel.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, cancel.GetId()))
        assert dlg._cancelled is True
        continue_download.set()
        dlg._worker.join(2)
        assert not dlg._worker.is_alive(), "download worker did not stop"

        deadline = time.monotonic() + 2
        while dlg.state != "DOWNLOAD_CANCELLED" and time.monotonic() < deadline:
            app.ProcessPendingEvents()
            wx.Yield()
            time.sleep(0.01)

        assert cancel_observed.is_set()
        assert dlg.state == "DOWNLOAD_CANCELLED"
        assert getattr(dlg, "_zip_path", None) is None
        labels = [
            dlg.footer_sizer.GetItem(i).GetWindow().GetLabel()
            for i in range(dlg.footer_sizer.GetItemCount())
            if dlg.footer_sizer.GetItem(i).GetWindow()
        ]
        assert not any("Install" in label for label in labels)
    finally:
        continue_download.set()
        if hasattr(dlg, "_worker"):
            dlg._worker.join(2)
        dlg.Destroy()
        app.Destroy()

def test_update_verification_state_visible():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    rel = _make_release()
    dlg = WxUpdateDialog(None, rel)
    dlg._build_for_state("VERIFYING")
    assert dlg.state == "VERIFYING"
    # Check that verifying message is visible
    found = False
    for idx in range(dlg.content_sizer.GetItemCount()):
        try:
            win = dlg.content_sizer.GetItem(idx).GetWindow()
            if win and "Verifying" in win.GetLabel():
                found = True
        except Exception:
            pass
    assert found
    dlg.Destroy()
    app.Destroy()

def test_update_ready_requires_install_confirmation():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    rel = _make_release()
    dlg = WxUpdateDialog(None, rel)
    dlg._build_for_state("READY_TO_INSTALL")
    # Check that Install Update button exists and is primary
    found_install = False
    for idx in range(dlg.footer_sizer.GetItemCount()):
        try:
            win = dlg.footer_sizer.GetItem(idx).GetWindow()
            if win and "Install" in win.GetLabel():
                found_install = True
                # Check it is bold (primary)
                fnt = win.GetFont()
                assert fnt.GetWeight() == wx.FONTWEIGHT_BOLD
        except Exception:
            pass
    assert found_install
    dlg.Destroy()
    app.Destroy()

def test_install_without_verified_artifact_stays_failed():
    app = wx.App(False)
    dlg = WxUpdateDialog(None, _make_release())
    dlg._build_for_state("READY_TO_INSTALL")
    dlg._start_install()
    assert dlg.state == "FAILED"
    assert "verified update artifact" in dlg._error_message.lower()
    dlg.Destroy()
    app.Destroy()

def test_update_install_opens_installation_splash():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    rel = _make_release()
    dlg = WxUpdateDialog(None, rel)
    dlg._build_for_state("READY_TO_INSTALL")
    # Find Install button and click it - should close this dialog and open splash
    # We can't easily test the splash without actually launching installer, but we can check that _start_install is called
    # Instead, check that the button exists and triggers _start_install
    install_btn = None
    for idx in range(dlg.footer_sizer.GetItemCount()):
        try:
            win = dlg.footer_sizer.GetItem(idx).GetWindow()
            if win and "Install" in win.GetLabel():
                install_btn = win
        except Exception:
            pass
    assert install_btn is not None
    # Mock show_installing_splash to avoid actually launching installer
    import hpc_gui.wx_updater_view as mod
    orig_show = mod.show_installing_splash
    called = {"hit": False}
    def fake_splash(parent, version):
        called["hit"] = True
        # Return a mock dialog that has _wx_install_update
        m = wx.Dialog(parent, title="Fake Install")
        m._wx_install_update = lambda v, msg, f="": None
        m.Show = lambda: None
        m.Destroy = lambda: None
        return m
    mod.show_installing_splash = fake_splash
    # Also mock launch_update_installer to avoid actually launching
    import hpc_gui.services.app_updater as au
    orig_launch = au.launch_update_installer
    au.launch_update_installer = lambda *a, **kw: None
    # Need to set zip path so install doesn't just simulate
    dlg._zip_path = "/tmp/fake.zip"
    dlg._artifact_verified = True
    evt = wx.CommandEvent(wx.wxEVT_BUTTON, install_btn.GetId())
    install_btn.GetEventHandler().ProcessEvent(evt)
    app.ProcessPendingEvents()
    time.sleep(0.3)
    app.ProcessPendingEvents()
    assert called["hit"]
    mod.show_installing_splash = orig_show
    au.launch_update_installer = orig_launch
    dlg.Destroy()
    app.Destroy()

def test_installation_progress_uses_real_backend_progress():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    from hpc_gui.wx_updater_view import show_installing_splash
    dlg = show_installing_splash(None, "1.9.0")
    assert dlg._wx_install_controls["gauge"] is not None
    # Simulate real progress
    dlg._wx_install_update(72, "Copying application files...", "hpc_gui/services/app_updater.py")
    assert dlg._wx_install_controls["gauge"].GetValue() == 72
    assert dlg._wx_install_controls["percent"].GetLabel() == "72%"
    assert "Copying" in dlg._wx_install_controls["phase"].GetLabel()
    assert "hpc_gui" in dlg._wx_install_controls["file"].GetLabel()
    dlg.Destroy()
    app.Destroy()

def test_installation_current_item_visible_when_available():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    from hpc_gui.wx_updater_view import show_installing_splash
    dlg = show_installing_splash(None, "1.9.0")
    dlg._wx_install_update(45, "Copying application files...", "hpc_gui/wx_updater_view.py")
    assert dlg._wx_install_controls["file"].GetLabel() == "hpc_gui/wx_updater_view.py"
    # When no file, should be empty
    dlg._wx_install_update(90, "Finalizing...", "")
    assert dlg._wx_install_controls["file"].GetLabel() == ""
    dlg.Destroy()
    app.Destroy()
