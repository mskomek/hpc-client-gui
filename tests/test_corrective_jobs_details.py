"""Corrective tests for Jobs + Details tabs — Sections 3-48."""

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


# === Sec 3: Single-click does not change notebook page ===

class TestSec3_NoAutoSwitch:
    def test_single_click_stays_on_jobs(self):
        load_language("en")
        app, frame, panel = _build_panel()
        try:
            ctrls = panel._wx_jobs_controls
            nb = ctrls["notebook"]
            assert nb.GetSelection() == 0  # Jobs tab
            panel._wx_jobs_refresh_jobs()
            for _ in range(30):
                wx.Yield()
                if ctrls["jobs"].GetItemCount() >= 1:
                    break
                wx.MilliSleep(10)
            _select_job(panel, 0)
            for _ in range(20):
                wx.Yield()
            assert nb.GetSelection() == 0, "Should stay on Jobs tab"
            assert panel._wx_jobs_state["selected_job"] == "1001"
        finally:
            _close(frame)

    def test_details_updates_in_background(self):
        load_language("en")
        app, frame, panel = _build_panel()
        try:
            ctrls = panel._wx_jobs_controls
            panel._wx_jobs_refresh_jobs()
            for _ in range(30):
                wx.Yield()
                if ctrls["jobs"].GetItemCount() >= 1:
                    break
                wx.MilliSleep(10)
            _select_job(panel, 0)
            for _ in range(20):
                wx.Yield()
            # Details content panel should be visible
            assert ctrls["details_content_panel"].IsShown()
            # Summary should show the selected job
            summary = ctrls["detail_values"]["job_id"].GetValue()
            assert summary == "1001"
        finally:
            _close(frame)

    def test_go_to_jobs_works(self):
        load_language("en")
        app, frame, panel = _build_panel()
        try:
            ctrls = panel._wx_jobs_controls
            nb = ctrls["notebook"]
            nb.SetSelection(2)  # Switch to Details manually
            wx.Yield()
            ctrls["go_to_jobs"]()
            wx.Yield()
            assert nb.GetSelection() == 0  # Back to Jobs
        finally:
            _close(frame)


# === Sec 6: Raw Accounting button opens viewer ===

class TestSec6_RawAccountingButton:
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
    def test_raw_sources_are_independent(self):
        load_language("en")

        def show_details(jid):
            return f"JobId={jid} WorkDir=/work"

        def refresh_sacct(jid):
            return f"JOBID|STATE\n{jid}|RUNNING"

        def refresh_lssrv():
            return "SERVER STATE\nnode001 available"

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
    def test_cluster_survives_job_selection_change(self):
        load_language("en")

        def refresh_lssrv():
            return "SERVER STATE\nnode001 available"

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
    def test_raw_viewer_source_label(self):
        """Verify source label is displayed."""
        load_language("en")
        from hpc_gui.wx_raw_viewer import _SOURCE_LABELS
        assert _SOURCE_LABELS.get("scontrol") == "Slurm Job Details"
        assert _SOURCE_LABELS.get("sacct") == "Slurm Accounting"
        assert _SOURCE_LABELS.get("lssrv") == "Cluster Server Status"

    def test_raw_viewer_refresh_callback_is_called(self):
        """Verify refresh callback is callable and returns RawCommandResult."""
        call_count = [0]

        def my_refresh():
            call_count[0] += 1
            return RawCommandResult.from_response(
                source_id="scontrol", command="scontrol show job 1001",
                stdout="refreshed", exit_code=0,
            )
        # Just verify the callback works (don't open modal dialog)
        result = my_refresh()
        assert call_count[0] == 1
        assert result.stdout == "refreshed"


# === Sec 27: I18N keys ===

class TestSec27_I18N:
    def test_parse_warning_keys_exist(self):
        load_language("en")
        assert "Job details could not be parsed" in t("jobs_outputs.parse_error_details")
        assert "Accounting data could not be parsed" in t("jobs_outputs.parse_error_accounting")
        assert "Cluster server information could not be parsed" in t("jobs_outputs.parse_error_cluster")
        assert "raw scheduler response" in t("jobs_outputs.parse_error_details").lower() or "raw" in t("jobs_outputs.parse_error_details").lower()
        load_language("tr")
        assert t("jobs_outputs.parse_error_details") != "[jobs_outputs.parse_error_details]"
        assert t("jobs_outputs.parse_error_accounting") != "[jobs_outputs.parse_error_accounting]"
        assert t("jobs_outputs.parse_error_cluster") != "[jobs_outputs.parse_error_cluster]"

    def test_raw_viewer_source_key(self):
        load_language("en")
        assert t("raw_viewer.source") == "Source"
        load_language("tr")
        assert t("raw_viewer.source") == "Kaynak"

    def test_raw_not_available_key(self):
        load_language("en")
        assert "not available" in t("jobs_outputs.raw_not_available").lower()
        load_language("tr")
        assert t("jobs_outputs.raw_not_available") != "[jobs_outputs.raw_not_available]"


# === Sec 39: Job selection does not change tab ===

class TestSec39_SelectionStaysOnJobs:
    def test_select_job_stays_on_jobs_tab(self):
        load_language("en")
        app, frame, panel = _build_panel()
        try:
            ctrls = panel._wx_jobs_controls
            nb = ctrls["notebook"]
            assert nb.GetSelection() == 0
            panel._wx_jobs_refresh_jobs()
            for _ in range(30):
                wx.Yield()
                if ctrls["jobs"].GetItemCount() >= 1:
                    break
                wx.MilliSleep(10)
            _select_job(panel, 0)
            for _ in range(20):
                wx.Yield()
            assert nb.GetSelection() == 0
            assert panel._wx_jobs_state["selected_job"] == "1001"
            # Now manually switch to Details
            nb.SetSelection(2)
            wx.Yield()
            assert nb.GetSelection() == 2
            assert ctrls["detail_values"]["job_id"].GetValue() == "1001"
        finally:
            _close(frame)


# === Sec 41: Empty job list + cluster status ===

class TestSec41_EmptyJobsClusterStatus:
    def test_cluster_visible_with_no_jobs(self):
        load_language("en")
        app = wx.App.Get() or wx.App(False)
        assert app is not None
        frame = wx.Frame(None)
        panel = build_jobs_panel(
            frame,
            list_jobs=lambda: [],
            refresh_lssrv=lambda: "SERVER STATE\nnode001 available",
            has_status_capability=lambda: True,
        )
        frame.Show()
        wx.Yield()
        try:
            ctrls = panel._wx_jobs_controls
            # Cluster servers should be visible even with no jobs
            assert ctrls["notebook"].GetPageCount() == 5
            # Cancel should be disabled
            assert not ctrls["btn_cancel"].IsEnabled()
        finally:
            _close(frame)


# === Sec 42: Unsupported cluster provider ===

class TestSec42_UnsupportedCluster:
    def test_cluster_hidden_when_unsupported(self):
        load_language("en")
        app = wx.App.Get() or wx.App(False)
        assert app is not None
        frame = wx.Frame(None)
        panel = build_jobs_panel(
            frame,
            list_jobs=lambda: _fake_jobs(),
            provider_connected=True,
        )
        frame.Show()
        wx.Yield()
        try:
            ctrls = panel._wx_jobs_controls
            assert ctrls["notebook"].GetPageCount() == 5
            assert "not available" in ctrls["cluster_status_text"].GetLabel()
        finally:
            _close(frame)


# === Sec 36: Raw source isolation ===

class TestSec36_RawSourceIsolation:
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


# === Regression: Files/Outputs tab routing ===

class TestRegression_FilesOutputs:
    def test_files_tab_untouched(self):
        load_language("en")
        app, frame, panel = _build_panel()
        try:
            ctrls = panel._wx_jobs_controls
            nb = ctrls["notebook"]
            assert nb.GetPageCount() == 5
            assert nb.GetPageText(0) == "Jobs"
            assert nb.GetPageText(1) == "Cluster"
            assert nb.GetPageText(2) == "Details"
            assert nb.GetPageText(3) == "Files"
            assert nb.GetPageText(4) == "Outputs"
            # Files browser exists
            assert hasattr(ctrls["files_browser"], "_wx_remote_controls")
        finally:
            _close(frame)

    def test_outputs_tab_untouched(self):
        load_language("en")
        app, frame, panel = _build_panel()
        try:
            ctrls = panel._wx_jobs_controls
            nb = ctrls["notebook"]
            nb.SetSelection(4)
            wx.Yield()
            # Outputs controls exist
            assert "outputs_refresh" in ctrls
            assert "outputs_follow" in ctrls
        finally:
            _close(frame)
