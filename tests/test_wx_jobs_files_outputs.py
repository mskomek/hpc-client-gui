"""Wave 50 Jobs Files/Outputs tabs real-event tests."""
import time
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.core.i18n import t
from mock_hpc_files import MockRemoteFilesBackend
from support.wx_jobs_outputs_harness import _build_panel, _close

@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_files_tab_loads_selected_job_files():
    backend = MockRemoteFilesBackend()
    app, frame, panel = _build_panel(session_state={"session": {"files": backend, "profile": {"profile_id": "jobs-files-test"}}})
    try:
        ctrls = panel._wx_jobs_controls
        jobs = ctrls["jobs"]
        panel._wx_jobs_refresh_jobs()
        for _ in range(20):
            wx.Yield()
            if jobs.GetItemCount() >= 2:
                break
            wx.MilliSleep(20)
        assert jobs.GetItemCount() >= 2
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs.GetId())
        evt.SetIndex(0)
        jobs.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        nb = ctrls["notebook"]
        nb.SetSelection(3)
        wx.Yield()
        for _ in range(30):
            wx.Yield()
            wx.MilliSleep(10)
        browser = ctrls["files_browser"]
        assert browser._wx_remote_model.current_path == "/work"
        names = [browser._wx_remote_controls["listing"].GetItemText(i) for i in range(browser._wx_remote_controls["listing"].GetItemCount())]
        assert "a.txt" in names and "b.txt" in names
    finally:
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
def test_wx_jobs_files_tab_stale_job_result_ignored():
    class DelayedBackend(MockRemoteFilesBackend):
        def iterdir_entries(self, path):
            if path == "/work/A":
                time.sleep(0.25)
            return super().iterdir_entries(path)

    backend = DelayedBackend()
    backend.entries.update({"/work/A": True, "/work/A/a.txt": False, "/work/B": True, "/work/B/b.txt": False})
    jobs = [{"id": "1001", "state": "RUNNING", "name": "A", "workdir": "/work/A"}, {"id": "1002", "state": "RUNNING", "name": "B", "workdir": "/work/B"}]
    app, frame, panel = _build_panel(list_jobs=lambda: jobs, session_state={"session": {"files": backend, "profile": {"profile_id": "jobs-files-race"}}})
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(20):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 1:
                break
            wx.MilliSleep(20)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        ctrls["notebook"].SetSelection(4)
        wx.Yield()
        # Quickly switch to second job while A's directory request is slow.
        evt2 = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt2.SetIndex(1)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt2)
        wx.Yield()
        ctrls["notebook"].SetSelection(4)
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
        listing = ctrls["files_browser"]._wx_remote_controls["listing"]
        names = [listing.GetItemText(i) for i in range(listing.GetItemCount())]
        assert ctrls["files_browser"]._wx_remote_model.current_path == "/work/B"
        assert "b.txt" in names
        assert "a.txt" not in names
    finally:
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_outputs_tab_loads_stdout_stderr():
    app, frame, panel = _build_panel()
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(20):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 1:
                break
            wx.MilliSleep(20)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        ctrls["notebook"].SetSelection(4)
        wx.Yield()
        panel._wx_jobs_refresh_outputs()
        for _ in range(30):
            wx.Yield()
            # Dynamic output channels should be populated
            channels = ctrls.get("output_channels", {})
            if any(tc.GetValue() for tc in channels.values()):
                break
            wx.MilliSleep(20)
        # At least one channel should have content
        channels = ctrls.get("output_channels", {})
        has_content = any(tc.GetValue() for tc in channels.values())
        assert channels
        assert has_content
    finally:
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_outputs_live_follow():
    contents = {"value": "first\n"}
    app, frame, panel = _build_panel(read_output=lambda _job: {"stdout": contents["value"], "stderr": ""})
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(20):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 1:
                break
            wx.MilliSleep(20)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        ctrls["notebook"].SetSelection(4)
        assert ctrls["outputs_follow"].GetValue() is True
        panel._wx_jobs_refresh_outputs()
        for _ in range(30):
            wx.Yield()
            wx.MilliSleep(20)
        assert any("first" in tc.GetValue() for tc in ctrls["output_channels"].values())
        contents["value"] += "second\n"
        panel._wx_jobs_refresh_outputs()
        for _ in range(30):
            wx.Yield()
            wx.MilliSleep(20)
        assert any("second" in tc.GetValue() for tc in ctrls["output_channels"].values())
    finally:
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_outputs_pause_resume():
    app, frame, panel = _build_panel()
    try:
        ctrls = panel._wx_jobs_controls
        assert panel._wx_jobs_state["outputs_paused"] is False
        evt = wx.CommandEvent(wx.wxEVT_BUTTON)
        evt.SetEventObject(ctrls["outputs_pause"])
        ctrls["outputs_pause"].GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        assert panel._wx_jobs_state["outputs_paused"] is True
        ctrls["outputs_pause"].GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        assert panel._wx_jobs_state["outputs_paused"] is False
    finally:
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_provider_status_is_visible_only_when_backend_supports_it():
    app, frame, panel = _build_panel(
        has_status_capability=lambda: True,
        refresh_lssrv=lambda _job_id: (
            "Slurm partitions state\n"
            "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
            "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
            "short 8 32 0 1 2 1-00:00:00 1 2 16 4096"
        ),
    )
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(30):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 1:
                break
            wx.MilliSleep(10)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        for _ in range(50):
            wx.Yield()
            if ctrls["cluster_status_text"].GetLabel() == t("jobs_outputs.cluster_status_loaded"):
                break
            wx.MilliSleep(10)
        assert ctrls["cluster_status_text"].GetLabel() == t("jobs_outputs.cluster_status_loaded")
    finally:
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
def test_wx_jobs_switch_job_rejects_old_completion():
    def slow_output(job_id):
        if job_id == "1001":
            time.sleep(0.3)
            return {"stdout": "old out", "stderr": ""}
        return {"stdout": "new out", "stderr": ""}
    app, frame, panel = _build_panel(read_output=slow_output)
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(20):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 1:
                break
            wx.MilliSleep(20)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        ctrls["notebook"].SetSelection(4)
        panel._wx_jobs_refresh_outputs()
        wx.Yield()
        # Quickly switch
        evt2 = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt2.SetIndex(1)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt2)
        ctrls["notebook"].SetSelection(4)
        panel._wx_jobs_refresh_outputs()
        wx.MilliSleep(500)
        wx.Yield()
        # Check dynamic output channels
        channels = ctrls.get("output_channels", {})
        all_text = " ".join(tc.GetValue() for tc in channels.values())
        assert "new out" in all_text
        assert "old out" not in all_text
    finally:
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_outputs_close_in_flight_safe():
    def slow_output(job_id):
        time.sleep(0.3)
        return {"stdout": "x", "stderr": ""}
    app, frame, panel = _build_panel(read_output=slow_output)
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(20):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 1:
                break
            wx.MilliSleep(20)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        ctrls["notebook"].SetSelection(4)
        panel._wx_jobs_refresh_outputs()
        wx.Yield()
        _close(frame)
        wx.MilliSleep(400)
        wx.Yield()
        assert panel._wx_jobs_state["closed"] is True
    finally:
        try:
            frame.Destroy()
        except Exception:
            pass
        wx.Yield()


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
def test_wx_jobs_details_latest_selection_wins_over_slow_scontrol():
    def show_details(job_id):
        if job_id == "1001":
            time.sleep(0.25)
        return f"JobId={job_id} JobName={'old' if job_id == '1001' else 'new'} WorkDir=/work/{job_id} StdOut=/out/{job_id}.out"

    app, frame, panel = _build_panel(show_job_details=show_details)
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(30):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 2:
                break
            wx.MilliSleep(10)
        for index in (0, 1):
            evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
            evt.SetIndex(index)
            ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
            wx.Yield()
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
        values = ctrls["detail_values"]
        assert values["job_id"].GetValue() == "1002"
        assert values["workdir"].GetValue() == "/work/1002"
        raw_result = panel._wx_jobs_state.get("raw_details_result")
        if raw_result is not None:
            assert "1001" not in raw_result.stdout
    finally:
        _close(frame)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
def test_wx_jobs_accounting_latest_selection_wins_over_slow_sacct():
    def refresh_sacct(job_id):
        if job_id == "1001":
            time.sleep(0.25)
        return f"JOBID|STATE|ELAPSED\n{job_id}|{'OLD' if job_id == '1001' else 'NEW'}|00:01:00"

    app, frame, panel = _build_panel(refresh_sacct=refresh_sacct)
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(30):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 2:
                break
            wx.MilliSleep(10)
        for index in (0, 1):
            evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
            evt.SetIndex(index)
            ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
            wx.Yield()
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
        table = ctrls["accounting_table"]
        assert table.GetItemCount() >= 1
        assert table.GetItemText(0, 0) == "1002"
        assert "OLD" not in " ".join(table.GetItemText(0, column) for column in range(table.GetColumnCount()))
    finally:
        _close(frame)
