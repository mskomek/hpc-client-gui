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


def _output_text(frame):
    return "\n".join(
        control.GetValue()
        for control in frame._wx_jobs_controls["output_channels"].values()
    )


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


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.regression
def test_wx_job_output_pause_freezes_until_resume(wx_jobs):
    values = [{"stdout": "line 1", "stderr": "err 1"}, {"stdout": "line 1\nline 2", "stderr": "err 2"}, {"stdout": "line 1\nline 2\nline 3", "stderr": "err 3"}]
    frame = None
    frame = _open(
        wx_jobs,
        lambda: [{"id": "42", "state": "RUNNING"}],
        lambda _job: values.pop(0) if len(values) > 1 else values[0],
    )
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    _pump(wx_jobs, lambda: "line 1" in _output_text(frame))
    stdout = next(
        control for control in frame._wx_jobs_controls["output_channels"].values()
        if "line 1" in control.GetValue()
    )
    stdout.SetInsertionPoint(0)
    _click(frame._wx_jobs_controls["pause"])
    frame._wx_jobs_refresh_outputs()
    _pump(wx_jobs, lambda: frame._wx_jobs_state["outputs_requests"] == 0)
    assert frame._wx_jobs_state["user_paused"]
    assert frame._wx_jobs_state["selected_job"] == "42"
    assert "line 1" in stdout.GetValue()
    assert "line 2" not in _output_text(frame)
    assert stdout.GetInsertionPoint() < stdout.GetLastPosition()
    assert frame._wx_jobs_controls["pause"].GetLabel() == "Resume All"
    _click(frame._wx_jobs_controls["pause"])
    stdout.SetInsertionPoint(stdout.GetLastPosition())
    frame._wx_jobs_refresh_outputs()
    _pump(wx_jobs, lambda: "line 3" in _output_text(frame))
    assert "line 2" in _output_text(frame)
    assert frame._wx_jobs_controls["pause"].GetLabel() == "Pause All"


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.regression
def test_wx_job_minimize_suspends_job_refresh_and_restores_it(wx_jobs):
    list_calls = []
    values = [{"stdout": "output-1"}, {"stdout": "output-2"}, {"stdout": "output-3"}]
    frame = _open(
        wx_jobs,
        lambda: list_calls.append(1) or [{"id": "42", "state": "RUNNING"}],
        lambda _job: values.pop(0) if len(values) > 1 else values[0],
    )
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    _pump(wx_jobs, lambda: "output-1" in _output_text(frame))
    event = wx.IconizeEvent(frame.GetId(), True)
    frame.ProcessEvent(event)
    assert frame._wx_jobs_state["minimized"]
    before = len(list_calls)
    frame._wx_jobs_refresh_jobs()
    assert len(list_calls) == before
    frame._wx_jobs_refresh_outputs()
    _pump(wx_jobs, lambda: "output-2" in _output_text(frame))
    assert frame._wx_jobs_state["minimized"]
    assert len(list_calls) == before
    stdout = next(
        control for control in frame._wx_jobs_controls["output_channels"].values()
        if "output-2" in control.GetValue()
    )
    stdout.SetInsertionPoint(stdout.GetLastPosition())
    frame.ProcessEvent(wx.IconizeEvent(frame.GetId(), False))
    assert not frame._wx_jobs_state["minimized"]
    frame._wx_jobs_refresh_jobs()
    _pump(wx_jobs, lambda: len(list_calls) > before)
    frame._wx_jobs_refresh_outputs()
    _pump(wx_jobs, lambda: "output-3" in _output_text(frame))
    assert not frame._wx_jobs_state["user_paused"]


@pytest.mark.gui
@pytest.mark.wx
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


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
@pytest.mark.resource
@pytest.mark.semantic
@pytest.mark.regression
def test_wx_job_output_does_not_overlap_remote_reads(wx_jobs):
    started = threading.Event()
    release = threading.Event()
    probe_done = threading.Event()
    lock = threading.Lock()
    calls = 0
    active_reads = 0
    max_active_reads = 0

    def read(_job):
        nonlocal calls, active_reads, max_active_reads
        with lock:
            calls += 1
            call_number = calls
            active_reads += 1
            max_active_reads = max(max_active_reads, active_reads)
        started.set()
        try:
            if call_number == 1:
                release.wait(5)
            return {"stdout": "done"}
        finally:
            with lock:
                active_reads -= 1

    frame = _open(wx_jobs, lambda: [{"id": "42", "state": "RUNNING"}], read)
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    assert started.wait(5)

    try:
        frame._wx_jobs_refresh_outputs()
        wx.CallAfter(probe_done.set)
        _pump(wx_jobs, probe_done.is_set)
        with lock:
            assert active_reads == 1
            assert max_active_reads == 1
    finally:
        release.set()

    _pump(wx_jobs, lambda: "done" in _output_text(frame))
    with lock:
        assert max_active_reads == 1


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
@pytest.mark.resource
@pytest.mark.semantic
@pytest.mark.regression
def test_wx_job_output_coalesces_pending_refreshes(wx_jobs):
    first_started = threading.Event()
    release_first = threading.Event()
    probe_done = threading.Event()
    lock = threading.Lock()
    calls = 0
    active_reads = 0
    max_active_reads = 0

    def read(_job):
        nonlocal calls, active_reads, max_active_reads
        with lock:
            calls += 1
            call_number = calls
            active_reads += 1
            max_active_reads = max(max_active_reads, active_reads)
        try:
            if call_number == 1:
                first_started.set()
                release_first.wait(5)
            return {"stdout": f"stdout-{call_number}", "stderr": f"stderr-{call_number}"}
        finally:
            with lock:
                active_reads -= 1

    frame = _open(wx_jobs, lambda: [{"id": "42", "state": "RUNNING"}], read)
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    assert first_started.wait(5)

    frame._wx_jobs_refresh_outputs()
    frame._wx_jobs_refresh_outputs()
    frame._wx_jobs_refresh_outputs()
    wx.CallAfter(probe_done.set)
    _pump(wx_jobs, probe_done.is_set)
    with lock:
        assert calls == 1
        assert active_reads == 1
        assert max_active_reads == 1

    release_first.set()
    _pump(wx_jobs, lambda: frame._wx_jobs_state["outputs_requests"] == 0)
    with lock:
        assert calls == 2
        assert max_active_reads == 1
    assert "stdout-2" in _output_text(frame)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
@pytest.mark.resource
@pytest.mark.semantic
@pytest.mark.regression
def test_wx_job_remote_follower_coalesces_reads(wx_jobs):
    first_started = threading.Event()
    release_first = threading.Event()
    lock = threading.Lock()
    calls = 0
    active_reads = 0
    max_active_reads = 0

    def read_path(_path):
        nonlocal calls, active_reads, max_active_reads
        with lock:
            calls += 1
            call_number = calls
            active_reads += 1
            max_active_reads = max(max_active_reads, active_reads)
        try:
            if call_number == 1:
                first_started.set()
                release_first.wait(5)
                return "line-1\n"
            return "line-1\nline-2\n"
        finally:
            with lock:
                active_reads -= 1

    frame = _open(
        wx_jobs,
        lambda: [{
            "id": "42",
            "state": "RUNNING",
            "stdout_path": "/work/42.out",
            "stderr_path": "/work/42.out",
        }],
        lambda _job: pytest.fail("remote follower should use read_remote_path"),
        read_remote_path=read_path,
    )
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    assert first_started.wait(5)

    frame._wx_jobs_refresh_outputs()
    frame._wx_jobs_refresh_outputs()
    _pump(wx_jobs, lambda: frame._wx_jobs_state["outputs_requests"] == 1)
    with lock:
        assert calls == 1
        assert active_reads == 1
        assert max_active_reads == 1

    release_first.set()
    _pump(
        wx_jobs,
        lambda: "line-2" in _output_text(frame)
        and frame._wx_jobs_state["outputs_requests"] == 0,
    )
    with lock:
        assert calls == 2
        assert max_active_reads == 1


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
@pytest.mark.resource
@pytest.mark.regression
def test_wx_job_output_read_error_releases_in_flight_state(wx_jobs):
    lock = threading.Lock()
    calls = 0

    def read(_job):
        nonlocal calls
        with lock:
            calls += 1
            call_number = calls
        if call_number == 1:
            raise RuntimeError("remote output read failed")
        return {"stdout": "recovered", "stderr": "recovered"}

    frame = _open(wx_jobs, lambda: [{"id": "42", "state": "RUNNING"}], read)
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    _pump(wx_jobs, lambda: frame._wx_jobs_state["outputs_requests"] == 0)
    assert not frame._wx_jobs_state["outputs_in_flight"]

    frame._wx_jobs_refresh_outputs()
    _pump(
        wx_jobs,
        lambda: "recovered" in _output_text(frame)
        and frame._wx_jobs_state["outputs_requests"] == 0,
    )
    with lock:
        assert calls == 2
    assert not frame._wx_jobs_state["outputs_in_flight"]


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
@pytest.mark.resource
@pytest.mark.regression
def test_wx_job_output_close_discards_pending_refresh(wx_jobs):
    first_started = threading.Event()
    release_first = threading.Event()
    lock = threading.Lock()
    calls = 0

    def read(_job):
        nonlocal calls
        with lock:
            calls += 1
            call_number = calls
        if call_number == 1:
            first_started.set()
            release_first.wait(5)
        return {"stdout": "output", "stderr": "output"}

    frame = _open(wx_jobs, lambda: [{"id": "42", "state": "RUNNING"}], read)
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame)
    assert first_started.wait(5)
    frame._wx_jobs_refresh_outputs()
    state = frame._wx_jobs_state

    frame.Close()
    _pump(wx_jobs, lambda: state["closed"])
    release_first.set()
    _pump(wx_jobs, lambda: state["outputs_requests"] == 0)

    with lock:
        assert calls == 1
    assert not state["outputs_in_flight"]
    assert not state["outputs_pending_generations"]


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
def test_wx_job_output_discards_stale_result_after_job_selection_changes(wx_jobs):
    release_a = threading.Event()
    started_b = threading.Event()
    calls = []

    def read(job_id):
        calls.append(job_id)
        if job_id == "A":
            release_a.wait(5)
        else:
            started_b.set()
        return {"stdout": f"output-{job_id}"}

    frame = _open(wx_jobs, lambda: [{"id": "A", "state": "RUNNING"}, {"id": "B", "state": "RUNNING"}], read)
    _pump(wx_jobs, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 2)
    _select(frame, 0)
    _pump(wx_jobs, lambda: calls == ["A"])
    _select(frame, 1)
    assert started_b.wait(5)
    release_a.set()
    _pump(wx_jobs, lambda: "output-B" in _output_text(frame))
    _pump(wx_jobs, lambda: frame._wx_jobs_state["outputs_requests"] == 0)
    assert "output-A" not in _output_text(frame)
    assert frame._wx_jobs_state["followers"]["stdout"].text == "output-B\n"
    assert calls[:2] == ["A", "B"]


def _open(app, list_jobs, read_output, **kwargs):
    show_jobs(list_jobs=list_jobs, read_output=read_output, **kwargs)
    frames = [window for window in wx.GetTopLevelWindows() if window.GetTitle() == "Jobs"]
    assert frames
    return frames[-1]
