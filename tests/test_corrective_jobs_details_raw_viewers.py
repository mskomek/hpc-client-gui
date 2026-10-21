"""Corrective tests for Jobs + Details tabs — Sections 3-48."""

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language, t

from hpc_gui.services.raw_command_result import RawCommandResult

class TestSec23_RawViewerClose:
    @pytest.mark.contract
    @pytest.mark.wx
    def test_raw_viewer_source_label(self):
        """Verify source label is displayed."""
        load_language("en")
        from hpc_gui.wx_raw_viewer import _SOURCE_LABELS
        assert _SOURCE_LABELS.get("scontrol") == "Slurm Job Details"
        assert _SOURCE_LABELS.get("sacct") == "Slurm Accounting"
        assert _SOURCE_LABELS.get("lssrv") == "Cluster Server Status"

    @pytest.mark.gui
    @pytest.mark.wx
    @pytest.mark.semantic
    @pytest.mark.regression
    def test_raw_viewer_refresh_callback_is_called(self, monkeypatch):
        """Refresh button invokes its callback and replaces visible output."""
        import threading
        from hpc_gui.wx_raw_viewer import show_raw_viewer

        _app = wx.App.Get() or wx.App(False)
        parent = wx.Frame(None)
        refreshed = []
        callback_queued = threading.Event()
        pending_callbacks = []
        original_call_after = wx.CallAfter

        def refresh():
            refreshed.append(True)
            return RawCommandResult.from_response(
                source_id="scontrol", command="scontrol show job 1001",
                stdout="new scheduler response", exit_code=0,
            )

        def capture_worker_callback(callback, *args, **kwargs):
            if threading.current_thread() is threading.main_thread():
                return original_call_after(callback, *args, **kwargs)
            pending_callbacks.append((callback, args, kwargs))
            callback_queued.set()

        def show_and_refresh(dialog):
            output = next(
                control for control in dialog.GetChildren()
                if isinstance(control, wx.TextCtrl) and control.GetValue() == "old scheduler response"
            )
            refresh_button = next(
                control for control in dialog.GetChildren()
                if isinstance(control, wx.Button) and control.GetLabel() == t("raw_viewer.refresh")
            )
            event = wx.CommandEvent(wx.wxEVT_BUTTON, refresh_button.GetId())
            refresh_button.GetEventHandler().ProcessEvent(event)
            assert callback_queued.wait(5), "refresh result was not queued"
            assert len(pending_callbacks) == 1
            callback, args, kwargs = pending_callbacks[0]
            callback(*args, **kwargs)
            assert output.GetValue() == "new scheduler response"
            assert refresh_button.IsEnabled()
            return wx.ID_CLOSE

        try:
            monkeypatch.setattr(wx, "CallAfter", capture_worker_callback)
            monkeypatch.setattr(wx.Dialog, "ShowModal", show_and_refresh)
            initial = RawCommandResult.from_response(
                source_id="scontrol", command="scontrol show job 1001",
                stdout="old scheduler response", exit_code=0,
            )
            show_raw_viewer(parent, initial, refresh_callback=refresh)
            assert refreshed == [True]
        finally:
            parent.Destroy()
            wx.Yield()

class TestSec36_RawSourceIsolation:
    @pytest.mark.unit
    @pytest.mark.semantic
    def test_each_viewer_shows_only_its_source(self):
        load_language("en")
        detail_raw = RawCommandResult.from_response(
            source_id="scontrol", command="scontrol show job 1001",
            stdout="DETAIL-X", exit_code=0,
        )
        acct_raw = RawCommandResult.from_response(
            source_id="sacct", command="sacct -j 1001",
            stdout="ACCOUNT-X", exit_code=0,
        )
        status_raw = RawCommandResult.from_response(
            source_id="lssrv", command="lssrv",
            stdout="STATUS-X", exit_code=0,
        )
        # Each has different source_id
        assert detail_raw.source_id == "scontrol"
        assert acct_raw.source_id == "sacct"
        assert status_raw.source_id == "lssrv"
        # Each has different stdout
        assert detail_raw.stdout == "DETAIL-X"
        assert acct_raw.stdout == "ACCOUNT-X"
        assert status_raw.stdout == "STATUS-X"
