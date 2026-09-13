"""Tests for wx update flow per spec 37 — real wx events, fixed changelog, real progress."""

import time
from threading import Event

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.services.app_updater import UpdateRelease
from hpc_gui.wx_updater_view import WxUpdateDialog, _format_bytes, show_update_available


def _make_release(version="1.9.0", body="- Demo update\n- New features\n- Fixes", size=184*1024*1024):
    return UpdateRelease(version=version, tag=f"v{version}", zip_name="a.zip", zip_url="https://example.com/a.zip", sha_name="a.sha", sha_url="https://example.com/a.sha", html_url="https://example.com", body=body, size=size)


class _WrapperDialog:
    class _Wx:
        ID_OK = 5100
        ID_CANCEL = 5101

    wx = _Wx()

    def __init__(self, _parent, _release):
        self.destroyed = False

    def _build_for_state(self, _state):
        pass

    def _start_download(self):
        pass

    def Destroy(self):
        self.destroyed = True


@pytest.mark.unit
def test_show_update_available_wrapper_returns_true_when_download_starts(monkeypatch):
    class DownloadDialog(_WrapperDialog):
        def ShowModal(self):
            self._start_download()
            return self.wx.ID_OK

    monkeypatch.setattr("hpc_gui.wx_updater_view.WxUpdateDialog", DownloadDialog)
    assert show_update_available(None, "1.0.0", "1.1.0") is True


@pytest.mark.unit
def test_show_update_available_wrapper_returns_false_for_cancel(monkeypatch):
    class CancelDialog(_WrapperDialog):
        def ShowModal(self):
            return self.wx.ID_CANCEL

    monkeypatch.setattr("hpc_gui.wx_updater_view.WxUpdateDialog", CancelDialog)
    assert show_update_available(None, "1.0.0", "1.1.0") is False


@pytest.fixture(autouse=True)
def _reset_update_language(monkeypatch, tmp_path):
    from hpc_gui.core import i18n

    previous = i18n.current_language()
    monkeypatch.setattr(i18n, "app_data_dir", lambda: tmp_path)
    i18n.load_language("en")
    try:
        yield
    finally:
        i18n.load_language(previous if previous in {"en", "tr"} else "tr")


@pytest.mark.wx
@pytest.mark.gui
def test_update_available_shows_versions_and_download_size():
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


@pytest.mark.wx
@pytest.mark.gui
def test_update_release_notes_preserve_unicode():
    app = wx.App(False)
    rel = _make_release(body="- Türkçe_日本語\n- 研究 ★ ✓")
    dlg = WxUpdateDialog(None, rel)
    assert "Türkçe_日本語" in dlg._changelog_ctrl.GetValue()
    assert "研究 ★ ✓" in dlg._changelog_ctrl.GetValue()
    dlg.Destroy()
    app.Destroy()


@pytest.mark.wx
@pytest.mark.gui
def test_update_changelog_is_fixed_height_scrollable_readonly():
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


@pytest.mark.wx
@pytest.mark.gui
def test_long_changelog_does_not_resize_dialog():
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


@pytest.mark.wx
@pytest.mark.gui
@pytest.mark.concurrency
@pytest.mark.resource
def test_update_available_download_button_starts_download(monkeypatch):
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
    download_entered = Event()
    release_worker = Event()
    try:
        import hpc_gui.services.app_updater as au

        def fake_download(_release, progress_cb=None, cancelled=None):
            download_entered.set()
            release_worker.wait(5)
            return None

        monkeypatch.setattr(au, "download_and_verify_release", fake_download)
        # Click download via real wx event
        evt = wx.CommandEvent(wx.wxEVT_BUTTON, dl_btn.GetId())
        dl_btn.GetEventHandler().ProcessEvent(evt)
        app.ProcessPendingEvents()
        assert download_entered.wait(3), "download button did not start updater worker"
        assert dlg.state == "DOWNLOADING"
    finally:
        dlg.Destroy()
        release_worker.set()
        if dlg._worker is not None:
            dlg._worker.join(3)
        app.Destroy()


@pytest.mark.wx
@pytest.mark.gui
@pytest.mark.concurrency
def test_update_download_progress_shows_real_bytes_and_percentage(monkeypatch):
    import hpc_gui.services.app_updater as app_updater

    app = wx.App(False)
    rel = _make_release(size=184 * 1024 * 1024)
    dlg = WxUpdateDialog(None, rel)
    progress_queued = Event()
    release_worker = Event()

    def fake_download(_release, progress_cb=None, cancelled=None):
        progress_cb(37, "downloading", 68 * 1024 * 1024, 184 * 1024 * 1024)
        progress_queued.set()
        release_worker.wait(5)
        return None

    monkeypatch.setattr(app_updater, "download_and_verify_release", fake_download)
    try:
        dlg.dlg.Show()
        dlg._start_download()
        assert progress_queued.wait(3), "download worker did not publish progress"

        deadline = time.monotonic() + 3
        while dlg._downloaded != 68 * 1024 * 1024 and time.monotonic() < deadline:
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
            time.sleep(0.01)

        pct = int(68 * 1024 * 1024 * 100 / (184 * 1024 * 1024))
        assert dlg._byte_label.GetLabel() == (
            f"{_format_bytes(68 * 1024 * 1024)} / {_format_bytes(184 * 1024 * 1024)}"
        )
        assert dlg._gauge.GetValue() == pct
        assert dlg._percent_label.GetLabel() == f"{pct}%"
    finally:
        dlg.Destroy()
        release_worker.set()
        if dlg._worker is not None:
            dlg._worker.join(3)
        app.Destroy()


@pytest.mark.wx
@pytest.mark.gui
@pytest.mark.concurrency
@pytest.mark.resource
def test_update_unknown_total_uses_indeterminate_progress(monkeypatch):
    import hpc_gui.services.app_updater as app_updater

    app = wx.App(False)
    rel = _make_release(size=None)
    dlg = WxUpdateDialog(None, rel)
    progress_queued = Event()
    release_worker = Event()

    def fake_download(_release, progress_cb=None, cancelled=None):
        progress_cb(0, "downloading", 68 * 1024 * 1024, 0)
        progress_queued.set()
        release_worker.wait(5)
        return None

    monkeypatch.setattr(app_updater, "download_and_verify_release", fake_download)
    try:
        dlg.dlg.Show()
        dlg._start_download()
        assert progress_queued.wait(3), "download worker did not publish progress"

        deadline = time.monotonic() + 3
        while dlg._downloaded != 68 * 1024 * 1024 and time.monotonic() < deadline:
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
            time.sleep(0.01)

        assert dlg._byte_label.GetLabel() == f"{_format_bytes(68 * 1024 * 1024)} downloaded"
        assert dlg._percent_label.GetLabel() == ""
        assert dlg._pulse_timer.IsRunning()
    finally:
        dlg.Destroy()
        release_worker.set()
        if dlg._worker is not None:
            dlg._worker.join(3)
        app.Destroy()


@pytest.mark.wx
@pytest.mark.gui
def test_update_cancel_button_transitions_to_cancelled_state():
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


@pytest.mark.wx
@pytest.mark.gui
@pytest.mark.concurrency
@pytest.mark.resource
def test_update_cancel_prevents_install(monkeypatch, tmp_path):
    import hpc_gui.services.app_updater as app_updater
    import hpc_gui.wx_updater_view as updater_view

    app = wx.App(False)
    rel = _make_release()
    dlg = WxUpdateDialog(None, rel)
    download_entered = Event()
    finish_download = Event()
    cancel_observed = Event()
    install_calls = []
    artifact = tmp_path / "verified-update.zip"

    def fake_download(_release, progress_cb=None, cancelled=None):
        download_entered.set()
        if not finish_download.wait(5):
            return artifact
        if cancelled():
            cancel_observed.set()
        return artifact

    monkeypatch.setattr(app_updater, "download_and_verify_release", fake_download)
    monkeypatch.setattr(app_updater, "launch_update_installer", lambda *a, **k: install_calls.append(a))
    monkeypatch.setattr(updater_view, "show_installing_splash", lambda *a, **k: install_calls.append(a))
    try:
        dlg.dlg.Show()
        dlg._start_download()
        assert download_entered.wait(3), "download worker did not reach the updater seam"

        cancel = dlg._cancel_btn
        assert cancel is not None
        event = wx.CommandEvent(wx.wxEVT_BUTTON, cancel.GetId())
        cancel.GetEventHandler().ProcessEvent(event)
        assert dlg._cancelled is True
        finish_download.set()
        dlg._worker.join(3)
        assert not dlg._worker.is_alive(), "download worker did not stop"

        deadline = time.monotonic() + 3
        while dlg.state != "DOWNLOAD_CANCELLED" and time.monotonic() < deadline:
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
            time.sleep(0.01)

        assert cancel_observed.is_set()
        assert dlg.state == "DOWNLOAD_CANCELLED"
        assert dlg._artifact_verified is False
        assert dlg._zip_path is None
        labels = []
        for index in range(dlg.footer_sizer.GetItemCount()):
            window = dlg.footer_sizer.GetItem(index).GetWindow()
            if window:
                labels.append(window.GetLabel())
        assert not any("Install" in label for label in labels)
        assert install_calls == []
    finally:
        finish_download.set()
        if dlg._worker is not None:
            dlg._worker.join(3)
        dlg.Destroy()
        app.Destroy()


@pytest.mark.wx
@pytest.mark.gui
def test_update_verification_state_visible():
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


@pytest.mark.wx
@pytest.mark.gui
def test_ready_to_install_exposes_primary_install_action():
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


@pytest.mark.wx
@pytest.mark.unit
def test_install_without_verified_artifact_stays_failed():
    app = wx.App(False)
    dlg = WxUpdateDialog(None, _make_release())
    dlg._build_for_state("READY_TO_INSTALL")
    dlg._start_install()
    assert dlg.state == "FAILED"
    assert "verified update artifact" in dlg._error_message.lower()
    dlg.Destroy()
    app.Destroy()


@pytest.mark.wx
@pytest.mark.gui
def test_update_install_opens_installation_splash():
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


@pytest.mark.wx
@pytest.mark.gui
def test_installation_progress_uses_real_backend_progress():
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


@pytest.mark.wx
@pytest.mark.gui
def test_installation_current_item_visible_when_available():
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


@pytest.mark.wx
@pytest.mark.gui
@pytest.mark.concurrency
@pytest.mark.resource
def test_update_close_in_flight_safe(monkeypatch):
    import hpc_gui.services.app_updater as app_updater

    app = wx.App(False)
    rel = _make_release()
    dlg = WxUpdateDialog(None, rel)
    download_entered = Event()
    finish_download = Event()
    message_responses = []

    def fake_download(_release, progress_cb=None, cancelled=None):
        download_entered.set()
        finish_download.wait(5)
        return None

    def answer_close(*_args, **_kwargs):
        response = wx.NO if not message_responses else wx.YES
        message_responses.append(response)
        return response

    monkeypatch.setattr(app_updater, "download_and_verify_release", fake_download)
    monkeypatch.setattr(wx, "MessageBox", answer_close)
    try:
        dlg.dlg.Show()
        dlg._start_download()
        assert download_entered.wait(3), "download worker did not start"

        # Close() dispatches the dialog's bound wx close event.
        dlg.dlg.Close()
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()
        assert message_responses == [wx.NO]
        assert dlg.dlg.IsShown()
        assert dlg.state == "DOWNLOADING"
        assert dlg._worker.is_alive(), "declined close must retain worker ownership"
        assert dlg._cancelled is False
        assert dlg._closed is False

        dlg.dlg.Close()
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()
        assert message_responses == [wx.NO, wx.YES]
        assert dlg.dlg.IsShown()
        assert dlg._cancelled is True
        finish_download.set()
        dlg._worker.join(3)
        assert not dlg._worker.is_alive(), "accepted cancellation did not release worker"
        deadline = time.monotonic() + 3
        while dlg.state != "DOWNLOAD_CANCELLED" and time.monotonic() < deadline:
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
            time.sleep(0.01)
        assert dlg.state == "DOWNLOAD_CANCELLED"
    finally:
        finish_download.set()
        if dlg._worker is not None:
            dlg._worker.join(3)
        dlg.Destroy()
        app.Destroy()


@pytest.mark.wx
@pytest.mark.gui
@pytest.mark.concurrency
@pytest.mark.resource
def test_update_late_callback_after_close_safe(monkeypatch, tmp_path):
    import hpc_gui.services.app_updater as app_updater

    app = wx.App(False)
    rel = _make_release()
    dlg = WxUpdateDialog(None, rel)
    progress_queued = Event()
    finish_download = Event()
    artifact = tmp_path / "verified-update.zip"

    def fake_download(_release, progress_cb=None, cancelled=None):
        progress_cb(50, "downloading", 50, 100)
        progress_queued.set()
        finish_download.wait(5)
        return artifact

    monkeypatch.setattr(app_updater, "download_and_verify_release", fake_download)
    try:
        dlg._start_download()
        assert progress_queued.wait(3), "real progress callback was not queued"
        finish_download.set()
        dlg._worker.join(3)
        assert not dlg._worker.is_alive(), "download worker did not finish"
        assert dlg._artifact_verified is True
        assert dlg._downloaded == 0  # queued progress has not run yet

        # Destroy closes the actual wx dialog while the worker's real CallAfter
        # progress and completion callbacks are still queued in wx.
        dlg.Destroy()
        for _ in range(5):
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
            time.sleep(0.01)

        assert dlg._closed is True
        assert dlg.state == "DOWNLOADING"
        assert dlg._downloaded == 0
        assert dlg._zip_path is None
    finally:
        finish_download.set()
        if dlg._worker is not None:
            dlg._worker.join(3)
        dlg.Destroy()
        app.Destroy()


@pytest.mark.wx
@pytest.mark.gui
def test_mandatory_update_has_no_later_button():
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


@pytest.mark.wx
@pytest.mark.unit
def test_mandatory_dialog_close_marks_dialog_closed():
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


@pytest.mark.wx
@pytest.mark.gui
def test_new_update_dialog_uses_current_runtime_language():
    app = wx.App(False)
    from hpc_gui.core.i18n import load_language, set_language

    load_language("en")
    rel = _make_release()
    dlg = WxUpdateDialog(None, rel)
    dlg._build_for_state("UPDATE_AVAILABLE")
    dlg.dlg.Show()
    english_labels = [
        dlg.footer_sizer.GetItem(index).GetWindow().GetLabel()
        for index in range(dlg.footer_sizer.GetItemCount())
        if dlg.footer_sizer.GetItem(index).GetWindow()
    ]
    assert "Later" in english_labels

    set_language("tr")
    dlg2 = WxUpdateDialog(None, rel)
    dlg2._build_for_state("UPDATE_AVAILABLE")
    dlg2.dlg.Show()
    turkish_labels = [
        dlg2.footer_sizer.GetItem(index).GetWindow().GetLabel()
        for index in range(dlg2.footer_sizer.GetItemCount())
        if dlg2.footer_sizer.GetItem(index).GetWindow()
    ]
    assert "Daha sonra" in turkish_labels
    assert dlg2.dlg.IsShown()

    dlg.Destroy()
    dlg2.Destroy()
    app.Destroy()
