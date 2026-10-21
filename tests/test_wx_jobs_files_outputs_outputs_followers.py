"""Wave 50 Jobs Files/Outputs tabs real-event tests."""

import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_jobs import build_jobs_panel

from hpc_gui.core.i18n import t

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
def test_wx_jobs_manual_follow_reads_its_arbitrary_path():
    contents = {
        "/work/stdout.log": "STDOUT DATA\n",
        "/work/stderr.log": "",
        "/scratch/solver.log": "SOLVER DATA\n",
    }
    jobs = [{"id": "1001", "state": "RUNNING", "name": "solver", "workdir": "/work",
             "stdout_path": "/work/stdout.log", "stderr_path": "/work/stderr.log"}]
    app, frame, panel = _build_panel(
        list_jobs=lambda: jobs,
        read_remote_path=lambda path: contents[path],
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
        for _ in range(40):
            wx.Yield()
            wx.MilliSleep(10)
        ctrls["files_browser"]._follow_callback("/scratch/solver.log")
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
        matching = [tc.GetValue() for cid, tc in ctrls["output_channels"].items()
                    if cid.startswith("follower-")]
        assert matching and any("SOLVER DATA" in text for text in matching)
        assert all("STDOUT DATA" not in text for text in matching)
    finally:
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_detached_follower_updates_after_remote_append():
    contents = {"/work/stdout.log": "first\n"}
    jobs = [{"id": "1001", "state": "RUNNING", "name": "solver", "workdir": "/work",
             "stdout_path": "/work/stdout.log"}]
    app, frame, panel = _build_panel(
        list_jobs=lambda: jobs,
        read_remote_path=lambda path: contents[path],
    )
    detached = None
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
        ctrls["notebook"].SetSelection(4)
        for _ in range(50):
            wx.Yield()
            wx.MilliSleep(10)
            if ctrls["output_channels"]:
                break
        button_event = wx.CommandEvent(wx.wxEVT_BUTTON, ctrls["output_open_window"].GetId())
        ctrls["output_open_window"].ProcessEvent(button_event)
        for _ in range(50):
            wx.Yield()
            wx.MilliSleep(10)
            detached = next((window for window in wx.GetTopLevelWindows()
                             if hasattr(window, "_wx_output_controls") and window is not frame), None)
            if detached is not None and "first" in detached._wx_output_controls["output"].GetValue():
                break
        assert detached is not None
        assert "first" in detached._wx_output_controls["output"].GetValue()
        contents["/work/stdout.log"] += "second\n"
        detached._wx_output_controls["follower"].state.paused = False
        detached._wx_output_refresh()
        for _ in range(150):
            wx.Yield()
            wx.MilliSleep(10)
            if "second" in detached._wx_output_controls["output"].GetValue():
                break
        assert "second" in detached._wx_output_controls["output"].GetValue()
    finally:
        if detached is not None:
            try:
                detached.Close()
            except Exception:
                pass
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_existing_follower_reassigns_to_new_remote_path():
    contents = {"/work/a.log": "A DATA\n", "/work/b.log": "B DATA\n"}
    jobs = [{"id": "1001", "state": "RUNNING", "name": "solver", "workdir": "/work"}]
    app, frame, panel = _build_panel(
        list_jobs=lambda: jobs, read_remote_path=lambda path: contents.get(path, ""),
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
        browser = ctrls["files_browser"]
        browser._follow_callback("/work/a.log")
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
            if any("A DATA" in tc.GetValue() for tc in ctrls["output_channels"].values()):
                break
        tracked_id = panel._wx_jobs_state["tracked_outputs"][0].tracking_id
        assert tracked_id.startswith("follower-")
        browser._follow_callback("/work/b.log", "existing", tracked_id)
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
            if any("B DATA" in tc.GetValue() for tc in ctrls["output_channels"].values()):
                break
        matching = [tc.GetValue() for cid, tc in ctrls["output_channels"].items() if cid == tracked_id]
        assert matching and "B DATA" in matching[0]
        assert "A DATA" not in matching[0]
        assert panel._wx_jobs_state["tracked_outputs"][0].tracking_id == tracked_id
    finally:
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_manual_follow_new_window_is_live():
    contents = {"/work/solver.log": "first\n"}
    jobs = [{"id": "1001", "state": "RUNNING", "name": "solver", "workdir": "/work"}]
    app, frame, panel = _build_panel(
        list_jobs=lambda: jobs, read_remote_path=lambda path: contents.get(path, ""),
    )
    detached = None
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
        ctrls["files_browser"]._follow_callback("/work/solver.log", "new_window")
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
            detached = next((window for window in wx.GetTopLevelWindows()
                             if hasattr(window, "_wx_output_controls") and window is not frame), None)
            if detached is not None and "first" in detached._wx_output_controls["output"].GetValue():
                break
        assert detached is not None
        pause_event = wx.CommandEvent(wx.wxEVT_BUTTON, detached._wx_output_controls["pause"].GetId())
        detached._wx_output_controls["pause"].ProcessEvent(pause_event)
        contents["/work/solver.log"] += "second\n"
        detached._wx_output_refresh()
        for _ in range(20):
            wx.Yield()
            wx.MilliSleep(10)
        assert "second" not in detached._wx_output_controls["output"].GetValue()
        detached._wx_output_controls["pause"].ProcessEvent(pause_event)
        detached._wx_output_refresh()
        for _ in range(100):
            wx.Yield()
            wx.MilliSleep(10)
            if "second" in detached._wx_output_controls["output"].GetValue():
                break
        assert "second" in detached._wx_output_controls["output"].GetValue()
    finally:
        if detached is not None:
            detached.Close()
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_output_scroll_does_not_force_user_back_to_latest():
    contents = {"/work/stdout.log": "".join(f"line-{index}\n" for index in range(300))}
    jobs = [{"id": "1001", "state": "RUNNING", "name": "solver", "workdir": "/work",
             "stdout_path": "/work/stdout.log"}]
    app, frame, panel = _build_panel(
        list_jobs=lambda: jobs, read_remote_path=lambda path: contents.get(path, ""),
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
        ctrls["notebook"].SetSelection(4)
        panel._wx_jobs_refresh_outputs()
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
            if ctrls["output_channels"] and any("line-299" in tc.GetValue() for tc in ctrls["output_channels"].values()):
                break
        output = next(iter(ctrls["output_channels"].values()))
        output.ShowPosition(0)
        contents["/work/stdout.log"] += "line-300\n"
        panel._wx_jobs_refresh_outputs()
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
            if "line-300" in output.GetValue():
                break
        assert "line-300" in output.GetValue()
        assert output.GetScrollPos(wx.VERTICAL) < output.GetScrollRange(wx.VERTICAL)
    finally:
        _close(frame)
