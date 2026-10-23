"""Corrective tests for Jobs + Details tabs — Sections 3-48."""

import pytest
wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language, t
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
    @pytest.mark.gui
    @pytest.mark.wx
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

    @pytest.mark.gui
    @pytest.mark.wx
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

    @pytest.mark.gui
    @pytest.mark.wx
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


# === Sec 27: I18N keys ===

class TestSec27_I18N:
    @pytest.mark.contract
    def test_parse_warning_keys_exist(self):
        load_language("en")
        assert "Job details could not be parsed" in t("jobs_outputs.parse_error_details")
        assert "Accounting data could not be parsed" in t("jobs_outputs.parse_error_accounting")
        assert "Cluster partition information could not be parsed" in t("jobs_outputs.parse_error_cluster")
        assert "raw scheduler response" in t("jobs_outputs.parse_error_details").lower() or "raw" in t("jobs_outputs.parse_error_details").lower()
        load_language("tr")
        assert t("jobs_outputs.parse_error_details") != "[jobs_outputs.parse_error_details]"
        assert t("jobs_outputs.parse_error_accounting") != "[jobs_outputs.parse_error_accounting]"
        assert t("jobs_outputs.parse_error_cluster") != "[jobs_outputs.parse_error_cluster]"

    @pytest.mark.contract
    def test_raw_viewer_source_key(self):
        load_language("en")
        assert t("raw_viewer.source") == "Source"
        load_language("tr")
        assert t("raw_viewer.source") == "Kaynak"

    @pytest.mark.contract
    def test_raw_not_available_key(self):
        load_language("en")
        assert "not available" in t("jobs_outputs.raw_not_available").lower()
        load_language("tr")
        assert t("jobs_outputs.raw_not_available") != "[jobs_outputs.raw_not_available]"


# === Sec 39: Job selection does not change tab ===

class TestSec39_SelectionStaysOnJobs:
    @pytest.mark.gui
    @pytest.mark.wx
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
    @pytest.mark.gui
    @pytest.mark.wx
    def test_cluster_visible_with_no_jobs(self):
        load_language("en")
        app = wx.App.Get() or wx.App(False)
        assert app is not None
        frame = wx.Frame(None)
        panel = build_jobs_panel(
            frame,
            list_jobs=lambda: [],
            refresh_lssrv=lambda: (
                "Slurm partitions state\n"
                "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
                "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
                "short 8 32 0 1 2 1-00:00:00 1 2 16 4096"
            ),
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
    @pytest.mark.gui
    @pytest.mark.wx
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


# === Regression: Files/Outputs tab routing ===

class TestRegression_FilesOutputs:
    @pytest.mark.gui
    @pytest.mark.wx
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

    @pytest.mark.contract
    @pytest.mark.wx
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
