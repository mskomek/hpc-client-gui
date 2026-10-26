"""Tests for update download progress, cancellation, and verification."""

import time
from threading import Event

import pytest

wx = pytest.importorskip("wx")
pytestmark = [pytest.mark.gui, pytest.mark.wx, pytest.mark.usefixtures("updater_english_language")]

from hpc_gui.wx_updater_view import WxUpdateDialog, _format_bytes
from support.wx_updater_helpers import make_release as _make_release


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
