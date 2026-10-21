"""Wave 50 Jobs Files/Outputs tabs real-event tests."""

import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_jobs import build_jobs_panel

from mock_hpc_files import MockRemoteFilesBackend

from hpc_gui.services.output_channel_resolver import definitions_from_provider

def _fake_jobs():
    return [
        {"id": "1001", "state": "RUNNING", "name": "jobA", "workdir": "/work", "stdout_path": "/out/1001.out", "stderr_path": "/out/1001.err"},
        {"id": "1002", "state": "PENDING", "name": "jobB", "workdir": "/work"},
    ]

def _build_panel(list_jobs=None, read_output=None, list_job_files=None, lifecycle=None, **kwargs):
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    session_state = kwargs.get("session_state")
    if isinstance(session_state, dict) and "remote_files_callbacks" not in kwargs:
        from hpc_gui.wx_shell import _remote_files_callbacks
        kwargs["remote_files_callbacks"] = _remote_files_callbacks(session_state, frame, lifecycle)
    panel = build_jobs_panel(frame, list_jobs=list_jobs or (lambda: _fake_jobs()), read_output=read_output or (lambda j: {"stdout": f"out {j}", "stderr": f"err {j}"}), list_job_files=list_job_files or (lambda j: [{"name": f"file_{j}.txt", "size": "123", "path": f"/work/{j}/file.txt"}]), lifecycle=lifecycle, **kwargs)
    frame.Show()
    wx.Yield()
    return app, frame, panel

def _close(frame):
    try:
        for child in frame.GetChildren():
            if hasattr(child, "_wx_jobs_state"):
                try:
                    child.Hide()
                    child.Destroy()
                except Exception:
                    pass
        frame.Close()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()
    try:
        if not frame.IsBeingDeleted():
            frame.Destroy()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()

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

@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_provider_output_definitions_refresh_after_reconnect():
    definitions = [{
        "streams": [{
            "id": "stdout", "role": "stdout", "labels": {"en": "Output"},
            "resolver": "slurm.stdout", "order": 0,
        }, {
            "id": "stderr", "role": "stderr", "labels": {"en": "Error"},
            "resolver": "slurm.stderr", "order": 1,
        }],
    }]

    def current_defs():
        return definitions_from_provider(definitions[0])

    app, frame, panel = _build_panel(output_channel_defs_provider=current_defs)
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
        panel._wx_jobs_refresh_outputs()
        for _ in range(30):
            wx.Yield()
            wx.MilliSleep(10)
            if set(ctrls["output_channels"]) == {"stdout", "stderr"}:
                break
        assert set(ctrls["output_channels"]) == {"stdout", "stderr"}

        definitions[0] = {"streams": []}
        panel._wx_jobs_refresh_outputs()
        for _ in range(30):
            wx.Yield()
            wx.MilliSleep(10)
            if ctrls["output_channel_notebook"].GetPageCount() == 1:
                break
        assert ctrls["output_channel_notebook"].GetPageCount() == 1

        definitions[0] = None
        panel._wx_jobs_refresh_outputs()
        for _ in range(30):
            wx.Yield()
            wx.MilliSleep(10)
            if set(ctrls["output_channels"]) == {"stdout", "stderr"}:
                break
        assert set(ctrls["output_channels"]) == {"stdout", "stderr"}
    finally:
        _close(frame)
