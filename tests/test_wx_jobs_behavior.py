import threading
import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language
from hpc_gui.wx_jobs import show_jobs


def _pump(app, predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(10)
    app.ProcessPendingEvents()
    assert predicate()


def _select(frame, index=0):
    jobs = frame._wx_jobs_controls["jobs"]
    jobs.Select(index)
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs.GetId())
    event.SetIndex(index)
    jobs.ProcessEvent(event)


def _click(control):
    event = wx.CommandEvent(wx.wxEVT_BUTTON, control.GetId())
    control.ProcessEvent(event)


@pytest.fixture
def wx_jobs():
    load_language("en")
    app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def test_wx_job_output_pause_keeps_refreshing_but_stops_live_follow(wx_jobs):
    values = [{"stdout": "line 1", "stderr": "err 1"}, {"stdout": "line 1\nline 2", "stderr": "err 2"}]
    frame = None
    frame = _open(wx_jobs, lambda: [{"id": "42", "state": "RUNNING"}], lambda _job: values.pop(0))
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    _pump(wx_jobs, lambda: "line 1" in frame._wx_jobs_controls["stdout"].GetValue())
    _click(frame._wx_jobs_controls["pause"])
    frame._wx_jobs_refresh_outputs()
    _pump(wx_jobs, lambda: "line 2" in frame._wx_jobs_controls["stdout"].GetValue())
    assert frame._wx_jobs_state["user_paused"]
    assert frame._wx_jobs_state["selected_job"] == "42"
    assert frame._wx_jobs_controls["stdout"].GetValue().endswith("line 2\n")


def test_wx_job_output_minimize_suspends_follow_and_restore_resumes_it(wx_jobs):
    list_calls = []
    frame = _open(wx_jobs, lambda: list_calls.append(1) or [{"id": "42", "state": "RUNNING"}], lambda _job: {"stdout": "output"})
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["stdout"].GetValue())
    event = wx.IconizeEvent(frame.GetId(), True)
    frame.ProcessEvent(event)
    assert frame._wx_jobs_state["minimized"]
    before = len(list_calls)
    frame._wx_jobs_refresh_jobs()
    assert len(list_calls) == before
    assert frame._wx_jobs_controls["stdout"].GetValue() == "output\n"
    frame.ProcessEvent(wx.IconizeEvent(frame.GetId(), False))
    assert not frame._wx_jobs_state["minimized"]
    frame._wx_jobs_refresh_jobs()
    _pump(wx_jobs, lambda: len(list_calls) > before)


def test_wx_job_output_does_not_overlap_remote_reads(wx_jobs):
    started = threading.Event()
    release = threading.Event()
    calls = []

    def read(_job):
        calls.append(1)
        started.set()
        release.wait(2)
        return {"stdout": "done"}

    frame = _open(wx_jobs, lambda: [{"id": "42", "state": "RUNNING"}], read)
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    assert started.wait(1)
    frame._wx_jobs_refresh_outputs()
    assert len(calls) == 1
    release.set()
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["stdout"].GetValue() == "done\n")


def test_wx_job_output_discards_stale_result_after_job_selection_changes(wx_jobs):
    release_a = threading.Event()
    calls = []

    def read(job_id):
        calls.append(job_id)
        if job_id == "A":
            release_a.wait(2)
        return {"stdout": f"output-{job_id}"}

    frame = _open(wx_jobs, lambda: [{"id": "A", "state": "RUNNING"}, {"id": "B", "state": "RUNNING"}], read)
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 2)
    _select(frame, 0)
    _pump(wx_jobs, lambda: calls == ["A"])
    _select(frame, 1)
    release_a.set()
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["stdout"].GetValue() == "output-B\n")
    assert calls[:2] == ["A", "B"]


def _open(app, list_jobs, read_output):
    show_jobs(list_jobs=list_jobs, read_output=read_output)
    frames = [window for window in wx.GetTopLevelWindows() if window.GetTitle() == "Jobs"]
    assert frames
    return frames[-1]
