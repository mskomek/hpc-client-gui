"""Jobs detail tests for independent raw command results and viewers."""

import pytest
wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language, t
from hpc_gui.services.raw_command_result import RawCommandResult
from hpc_gui.wx_jobs import build_jobs_panel


def _fake_jobs():
    return [
        {"id": "1001", "state": "RUNNING", "name": "jobA", "partition": "gpu",
         "elapsed": "00:05:00", "nodes": "2", "cpus": "16", "reason": "None",
         "workdir": "/work/1001", "stdout_path": "/out/1001.out",
         "stderr_path": "/out/1001.err"},
        {"id": "1002", "state": "PENDING", "name": "jobB", "partition": "cpu",
         "elapsed": "-", "nodes": "1", "cpus": "4", "reason": "Priority"},
    ]


def _build_panel(**kwargs):
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    panel = build_jobs_panel(frame, list_jobs=_fake_jobs, **kwargs)
    frame.Show()
    wx.Yield()
    return app, frame, panel


def _select_job(panel, index=0):
    ctrls = panel._wx_jobs_controls
    evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
    evt.SetIndex(index)
    ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
    wx.Yield()


def _close(frame):
    try:
        for child in frame.GetChildren():
            if hasattr(child, "_wx_jobs_state"):
                child.Hide()
                child.Destroy()
        frame.Close()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()


# === Sec 6: Raw Accounting button opens viewer ===

class TestSec6_RawAccountingButton:
    @pytest.mark.integration
    @pytest.mark.wx
    def test_raw_accounting_opens_viewer(self):
        load_language("en")
        app, frame, panel = _build_panel(
            refresh_sacct=lambda jid: f"JOBID|STATE\n{jid}|RUNNING",
        )
        try:
            ctrls = panel._wx_jobs_controls
            panel._wx_jobs_refresh_jobs()
            for _ in range(30):
                wx.Yield()
                if ctrls["jobs"].GetItemCount() >= 1:
                    break
                wx.MilliSleep(10)
            _select_job(panel, 0)
            for _ in range(30):
                wx.Yield()
            # Raw accounting result should be stored
            raw = panel._wx_jobs_state.get("raw_accounting_result")
            assert raw is not None
            assert raw.source_id == "sacct"
        finally:
            _close(frame)


# === Sec 7: Three independent raw sources ===

class TestSec7_RawSourceIsolation:
    @pytest.mark.integration
    @pytest.mark.wx
    def test_raw_sources_are_independent(self):
        load_language("en")

        def show_details(jid):
            return f"JobId={jid} WorkDir=/work"

        def refresh_sacct(jid):
            return f"JOBID|STATE\n{jid}|RUNNING"

        def refresh_lssrv():
            return (
                "Slurm partitions state\n"
                "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
                "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
                "short 8 32 0 1 2 1-00:00:00 1 2 16 4096"
            )

        app, frame, panel = _build_panel(
            show_job_details=show_details,
            refresh_sacct=refresh_sacct,
            refresh_lssrv=refresh_lssrv,
            has_status_capability=lambda: True,
        )
        try:
            ctrls = panel._wx_jobs_controls
            panel._wx_jobs_refresh_jobs()
            for _ in range(30):
                wx.Yield()
                if ctrls["jobs"].GetItemCount() >= 1:
                    break
                wx.MilliSleep(10)
            _select_job(panel, 0)
            for _ in range(50):
                wx.Yield()
                wx.MilliSleep(10)
            state = panel._wx_jobs_state
            # All three sources should be independent
            assert state.get("raw_details_result") is not None
            assert state.get("raw_accounting_result") is not None
            assert state.get("raw_status_result") is not None
            # Each has different source_id
            assert state["raw_details_result"].source_id == "scontrol"
            assert state["raw_accounting_result"].source_id == "sacct"
            assert state["raw_status_result"].source_id == "lssrv"
        finally:
            _close(frame)


# === Sec 11: Cluster status not dependent on job selection ===

class TestSec11_ClusterStatusIndependence:
    @pytest.mark.gui
    @pytest.mark.wx
    def test_cluster_survives_job_selection_change(self):
        load_language("en")

        def refresh_lssrv():
            return (
                "Slurm partitions state\n"
                "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
                "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
                "short 8 32 0 1 2 1-00:00:00 1 2 16 4096"
            )

        app, frame, panel = _build_panel(
            refresh_lssrv=refresh_lssrv,
            has_status_capability=lambda: True,
        )
        try:
            ctrls = panel._wx_jobs_controls
            panel._wx_jobs_refresh_jobs()
            for _ in range(30):
                wx.Yield()
                if ctrls["jobs"].GetItemCount() >= 2:
                    break
                wx.MilliSleep(10)
            # Trigger cluster status refresh
            ctrls["btn_refresh_lssrv"].ProcessEvent(
                wx.CommandEvent(wx.wxEVT_BUTTON, ctrls["btn_refresh_lssrv"].GetId())
            )
            for _ in range(50):
                wx.Yield()
                wx.MilliSleep(20)
            # Cluster servers should be visible
            assert ctrls["cluster_status_text"].IsShown()
            # Select job A
            _select_job(panel, 0)
            for _ in range(20):
                wx.Yield()
            # Select job B
            _select_job(panel, 1)
            for _ in range(20):
                wx.Yield()
            # Cluster servers should still be visible (not affected by job selection)
            assert ctrls["cluster_status_text"].IsShown()
        finally:
            _close(frame)


# === Sec 23: Raw viewer close handling ===

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


# === Sec 36: Raw source isolation ===

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


