import threading
import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language
from hpc_gui.wx_jobs import show_jobs


def _pump(app, predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            app.ProcessPendingEvents()
        except Exception:
            pass
        try:
            wx.SafeYield()
        except Exception:
            pass
        if predicate():
            return
        wx.MilliSleep(10)
    try:
        app.ProcessPendingEvents()
    except Exception:
        pass
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


def _stdout(frame):
    return frame._wx_jobs_controls.get("output_channels", {}).get("stdout")


@pytest.fixture
def wx_jobs():
    load_language("en")
    app = wx.App.Get() or wx.App(False)
    yield app
    try:
        for window in list(wx.GetTopLevelWindows()):
            try:
                if window:
                    window.Destroy()
            except Exception:
                pass
        for _ in range(5):
            try:
                app.ProcessPendingEvents()
                wx.SafeYield()
            except Exception:
                break
            wx.MilliSleep(10)
    except Exception:
        pass
    # Do not Destroy the global App – other tests reuse it. Only destroy if we created it and no other TopLevelWindows remain.
    try:
        if not wx.GetTopLevelWindows():
            # Keep App alive for reuse; do not Destroy here to avoid UnregisterClass 0x584
            pass
    except Exception:
        pass


@pytest.mark.wx
@pytest.mark.gui
def test_wx_job_output_pause_freezes_and_resume_updates_output(wx_jobs):
    values = [{"stdout": "line 1", "stderr": "err 1"}, {"stdout": "line 1\nline 2", "stderr": "err 2"}, {"stdout": "line 1\nline 2\nline 3", "stderr": "err 3"}]
    reads = 0

    def read(_job):
        nonlocal reads
        value = values[min(reads, len(values) - 1)]
        reads += 1
        return value

    frame = None
    frame = _open(wx_jobs, lambda: [{"id": "42", "state": "RUNNING"}], read)
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    _pump(wx_jobs, lambda: _stdout(frame) is not None and "line 1" in _stdout(frame).GetValue())
    _stdout(frame).SetInsertionPoint(0)
    _click(frame._wx_jobs_controls["pause"])
    frame._wx_jobs_refresh_outputs()
    _pump(
        wx_jobs,
        lambda: reads >= 2 and frame._wx_jobs_state["outputs_requests"] == 0,
    )
    assert frame._wx_jobs_state["user_paused"]
    assert frame._wx_jobs_state["selected_job"] == "42"
    assert _stdout(frame).GetValue() == "line 1\n"
    assert _stdout(frame).GetInsertionPoint() < _stdout(frame).GetLastPosition()
    _click(frame._wx_jobs_controls["pause"])
    frame._wx_jobs_refresh_outputs()
    _pump(wx_jobs, lambda: _stdout(frame).GetValue() == "line 1\nline 2\nline 3\n")


@pytest.mark.wx
@pytest.mark.gui
def test_wx_job_output_minimize_suspends_follow_and_restore_resumes_it(wx_jobs):
    list_calls = []
    values = [{"stdout": "output-1"}, {"stdout": "output-2"}, {"stdout": "output-3"}]
    reads = 0

    def read(_job):
        nonlocal reads
        value = values[min(reads, len(values) - 1)]
        reads += 1
        return value

    frame = _open(wx_jobs, lambda: list_calls.append(1) or [{"id": "42", "state": "RUNNING"}], read)
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    _pump(wx_jobs, lambda: _stdout(frame) is not None and _stdout(frame).GetValue() == "output-1\n")
    event = wx.IconizeEvent(frame.GetId(), True)
    frame.ProcessEvent(event)
    assert frame._wx_jobs_state["minimized"]
    before = len(list_calls)
    frame._wx_jobs_refresh_jobs()
    assert len(list_calls) == before
    frame._wx_jobs_refresh_outputs()
    _pump(wx_jobs, lambda: _stdout(frame).GetValue() == "output-2\n")
    assert frame._wx_jobs_state["minimized"]
    frame.ProcessEvent(wx.IconizeEvent(frame.GetId(), False))
    assert not frame._wx_jobs_state["minimized"]
    frame._wx_jobs_refresh_jobs()
    _pump(wx_jobs, lambda: len(list_calls) > before)
    frame._wx_jobs_refresh_outputs()
    _pump(wx_jobs, lambda: _stdout(frame).GetValue() == "output-3\n")
    assert not frame._wx_jobs_state["user_paused"]


@pytest.mark.wx
@pytest.mark.gui
def test_wx_job_output_pause_survives_minimize_restore(wx_jobs):
    list_calls = []
    frame = _open(wx_jobs, lambda: list_calls.append(1) or [{"id": "42", "state": "RUNNING"}], lambda _job: {"stdout": "next"})
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    _pump(wx_jobs, lambda: any(tc.GetValue() for tc in frame._wx_jobs_controls.get("output_channels", {}).values()) if frame._wx_jobs_controls.get("output_channels") else True)
    _click(frame._wx_jobs_controls["pause"])
    assert frame._wx_jobs_state["user_paused"]
    frame.ProcessEvent(wx.IconizeEvent(frame.GetId(), True))
    before = len(list_calls)
    frame._wx_jobs_refresh_jobs()
    assert len(list_calls) == before
    frame.ProcessEvent(wx.IconizeEvent(frame.GetId(), False))
    _pump(wx_jobs, lambda: not frame._wx_jobs_state["minimized"])
    assert frame._wx_jobs_state["user_paused"]
    assert frame._wx_jobs_controls["pause"].GetLabel() == "Resume All"


@pytest.mark.wx
@pytest.mark.gui
def test_wx_job_output_does_not_overlap_remote_reads(wx_jobs):
    started = threading.Event()
    release = threading.Event()
    calls = []
    read_threads = []
    lock = threading.Lock()
    active = 0
    peak = 0

    def read(_job):
        nonlocal active, peak
        with lock:
            calls.append(1)
            read_threads.append(threading.get_ident())
            active += 1
            peak = max(peak, active)
        started.set()
        try:
            release.wait(3)
            return {"stdout": "done"}
        finally:
            with lock:
                active -= 1

    frame = _open(wx_jobs, lambda: [{"id": "42", "state": "RUNNING"}], read)
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    assert started.wait(2)
    try:
        for _ in range(5):
            frame._wx_jobs_refresh_outputs_tab()
        with lock:
            assert peak == 1
            assert active == 1
        release.set()

        def _check_output():
            channels = frame._wx_jobs_controls.get("output_channels", {})
            return any("done" in tc.GetValue() for tc in channels.values())

        _pump(wx_jobs, _check_output)
        with lock:
            assert peak == 1
            assert active == 0
            assert len(calls) >= 1
            assert read_threads and read_threads[0] != threading.get_ident()
    finally:
        release.set()


@pytest.mark.wx
@pytest.mark.gui
def test_wx_job_output_discards_stale_result_after_job_selection_changes(wx_jobs):
    release_a = threading.Event()
    release_b = threading.Event()
    started_a = threading.Event()
    started_b = threading.Event()
    calls = []

    def read(job_id):
        calls.append(job_id)
        if job_id == "A":
            started_a.set()
            release_a.wait(3)
        else:
            started_b.set()
            release_b.wait(3)
        return {"stdout": f"output-{job_id}"}

    frame = _open(wx_jobs, lambda: [{"id": "A", "state": "RUNNING"}, {"id": "B", "state": "RUNNING"}], read)
    try:
        _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 2)
        _select(frame, 0)
        assert started_a.wait(2)
        _select(frame, 1)
        release_a.set()
        assert started_b.wait(3)
        wx.SafeYield()
        assert _stdout(frame) is not None
        assert _stdout(frame).GetValue() != "output-A\n"
        release_b.set()
        _pump(wx_jobs, lambda: _stdout(frame) is not None and _stdout(frame).GetValue() == "output-B\n")
        assert calls[:2] == ["A", "B"]
    finally:
        release_a.set()
        release_b.set()


def _open(app, list_jobs, read_output):
    show_jobs(list_jobs=list_jobs, read_output=read_output)
    frames = [window for window in wx.GetTopLevelWindows() if window.GetTitle() == "Jobs"]
    assert frames
    return frames[-1]
