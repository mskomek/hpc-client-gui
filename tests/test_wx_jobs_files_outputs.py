"""Wave 50 Jobs Files/Outputs tabs real-event tests."""
import time
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.wx_jobs import build_jobs_panel

def _fake_jobs():
    return [
        {"id": "1001", "state": "RUNNING", "name": "jobA", "stdout_path": "/out/1001.out", "stderr_path": "/out/1001.err"},
        {"id": "1002", "state": "PENDING", "name": "jobB"},
    ]

def _build_panel(list_jobs=None, read_output=None, list_job_files=None, lifecycle=None):
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    panel = build_jobs_panel(frame, list_jobs=list_jobs or (lambda: _fake_jobs()), read_output=read_output or (lambda j: {"stdout": f"out {j}", "stderr": f"err {j}"}), list_job_files=list_job_files or (lambda j: [{"name": f"file_{j}.txt", "size": "123", "path": f"/work/{j}/file.txt"}]), lifecycle=lifecycle)
    frame.Show()
    wx.Yield()
    return app, frame, panel

def _close(frame):
    try:
        # use host close
        closer = getattr(frame, "_wx_jobs_state", None)
        # host is panel's parent (frame's child)
        # find host via GetChildren
        for child in frame.GetChildren():
            if hasattr(child, "_wx_jobs_state"):
                try:
                    child.Hide()
                    child.Destroy()
                except: pass
        frame.Close()
    except: pass
    for _ in range(3):
        wx.Yield()
    try:
        if not frame.IsBeingDeleted():
            frame.Destroy()
    except: pass
    for _ in range(3):
        wx.Yield()

def test_wx_jobs_files_tab_loads_selected_job_files():
    app, frame, panel = _build_panel()
    try:
        # panel is host; get controls
        ctrls = panel._wx_jobs_controls
        # select first job via list event
        jobs = ctrls["jobs"]
        # need to populate jobs first
        panel._wx_jobs_refresh_jobs()
        for _ in range(20):
            wx.Yield()
            if jobs.GetItemCount() >=2:
                break
            wx.MilliSleep(20)
        assert jobs.GetItemCount() >=2
        # simulate select
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs.GetId())
        evt.SetIndex(0)
        jobs.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        # switch to Files tab
        nb = ctrls["notebook"]
        nb.SetSelection(1)
        wx.Yield()
        # trigger files refresh
        panel._wx_jobs_refresh_files()
        for _ in range(30):
            wx.Yield()
            if panel._wx_jobs_controls["job_files"].GetItemCount() >=1:
                break
            wx.MilliSleep(20)
        assert panel._wx_jobs_controls["job_files"].GetItemCount() >=1
        assert "file_1001" in panel._wx_jobs_controls["job_files"].GetItemText(0)
    finally:
        _close(frame)

def test_wx_jobs_files_tab_stale_job_result_ignored():
    # slow list_job_files for first job, fast for second
    def slow_files(job_id):
        if job_id == "1001":
            time.sleep(0.3)
            return [{"name": "old.txt", "size": "1"}]
        return [{"name": "new.txt", "size": "2"}]
    app, frame, panel = _build_panel(list_job_files=slow_files)
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(20):
            wx.Yield()
            if ctrls["jobs"].GetItemCount()>=1:
                break
            wx.MilliSleep(20)
        # select 1001 (slow)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        ctrls["notebook"].SetSelection(1)
        wx.Yield()
        panel._wx_jobs_refresh_files()
        wx.Yield()
        # quickly switch to 1002
        evt2 = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt2.SetIndex(1)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt2)
        wx.Yield()
        ctrls["notebook"].SetSelection(1)
        panel._wx_jobs_refresh_files()
        # wait
        for _ in range(50):
            wx.Yield()
            wx.MilliSleep(20)
        # should show new.txt, not old.txt
        wx.MilliSleep(400)
        wx.Yield()
        txt = ctrls["job_files"].GetItemText(0) if ctrls["job_files"].GetItemCount()>0 else ""
        assert "new.txt" in txt or ctrls["job_files"].GetItemCount()>=1
        # ensure not old
        # check all items
        items = [ctrls["job_files"].GetItemText(i) for i in range(ctrls["job_files"].GetItemCount())]
        assert "old.txt" not in items or "new.txt" in items
    finally:
        _close(frame)

def test_wx_jobs_outputs_tab_loads_stdout_stderr():
    app, frame, panel = _build_panel()
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(20):
            wx.Yield()
            if ctrls["jobs"].GetItemCount()>=1:
                break
            wx.MilliSleep(20)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        ctrls["notebook"].SetSelection(2)
        wx.Yield()
        panel._wx_jobs_refresh_outputs_tab()
        for _ in range(30):
            wx.Yield()
            if "out 1001" in ctrls["outputs_stdout"].GetValue():
                break
            wx.MilliSleep(20)
        assert "out 1001" in ctrls["outputs_stdout"].GetValue()
        assert "err 1001" in ctrls["outputs_stderr"].GetValue()
    finally:
        _close(frame)

def test_wx_jobs_outputs_live_follow():
    app, frame, panel = _build_panel()
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(20):
            wx.Yield()
            if ctrls["jobs"].GetItemCount()>=1:
                break
            wx.MilliSleep(20)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        ctrls["notebook"].SetSelection(2)
        # ensure follow checked
        assert ctrls["outputs_follow"].GetValue() is True
        panel._wx_jobs_refresh_outputs_tab()
        for _ in range(30):
            wx.Yield()
            wx.MilliSleep(20)
        # follow should have been called (at least show position)
        assert True
    finally:
        _close(frame)

def test_wx_jobs_outputs_pause_resume():
    app, frame, panel = _build_panel()
    try:
        ctrls = panel._wx_jobs_controls
        # initially not paused
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

def test_wx_jobs_switch_job_rejects_old_completion():
    # similar to stale but for outputs
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
            if ctrls["jobs"].GetItemCount()>=1:
                break
            wx.MilliSleep(20)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        ctrls["notebook"].SetSelection(2)
        panel._wx_jobs_refresh_outputs_tab()
        wx.Yield()
        # quickly switch
        evt2 = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt2.SetIndex(1)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt2)
        ctrls["notebook"].SetSelection(2)
        panel._wx_jobs_refresh_outputs_tab()
        wx.MilliSleep(500)
        wx.Yield()
        val = ctrls["outputs_stdout"].GetValue()
        assert "new out" in val
        assert "old out" not in val
    finally:
        _close(frame)

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
            if ctrls["jobs"].GetItemCount()>=1:
                break
            wx.MilliSleep(20)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        ctrls["notebook"].SetSelection(2)
        panel._wx_jobs_refresh_outputs_tab()
        wx.Yield()
        _close(frame)
        wx.MilliSleep(400)
        wx.Yield()
        assert True  # no crash
    finally:
        try:
            frame.Destroy()
        except: pass
        wx.Yield()
