import threading
import time

import pytest

wx = pytest.importorskip("wx")

from mock_hpc_jobs import MockHPCJobs

from hpc_gui.core.i18n import load_language
from hpc_gui.wx_jobs import WxJobsModel, show_jobs


def _pump(app, predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    assert predicate()


def _open(list_jobs=None, read_output=None):
    show_jobs(list_jobs=list_jobs, read_output=read_output)
    frames = [window for window in wx.GetTopLevelWindows() if window.GetTitle() == "Jobs"]
    assert frames
    return frames[-1]


def _select(frame, index):
    jobs = frame._wx_jobs_controls["jobs"]
    jobs.Select(index)
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs.GetId())
    event.SetIndex(index)
    jobs.ProcessEvent(event)


def _click(control):
    control.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, control.GetId()))


def _close(frame, app):
    title = frame.GetTitle()
    frame.Close()
    app.ProcessPendingEvents()
    wx.Yield()
    return title


@pytest.fixture
def wx_app():
    load_language("en")
    app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def test_wx_jobs_stress_rapid_selection_never_shows_stale_output(wx_app):
    backend = MockHPCJobs(25)
    backend.stdout = {job_id: f"output-{job_id}" for job_id in backend.jobs}
    frame = _open(backend.list_jobs, backend.read_output)
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 25)
    for index in range(200):
        selected = index % 25
        _select(frame, selected)
        job_id = str(selected + 1)
        _pump(wx_app, lambda job_id=job_id: frame._wx_jobs_state["selected_job"] == job_id)
        _pump(wx_app, lambda job_id=job_id: frame._wx_jobs_controls["stdout"].GetValue() == f"output-{job_id}\n")
    assert frame._wx_jobs_state["selected_job"] == "25"
    assert frame._wx_jobs_controls["stdout"].GetValue() == "output-25\n"
    _close(frame, wx_app)


def test_wx_jobs_stress_repeated_minimize_restore_keeps_polling_lifecycle_stable(wx_app):
    backend = MockHPCJobs(1)
    frame = _open(backend.list_jobs, backend.read_output)
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame, 0)
    _pump(wx_app, lambda: frame._wx_jobs_controls["stdout"].GetValue())
    for cycle in range(100):
        frame.ProcessEvent(wx.IconizeEvent(frame.GetId(), True))
        before = backend.list_calls
        backend.set_output("1", f"minimized-{cycle}")
        frame._wx_jobs_refresh_jobs()
        frame._wx_jobs_refresh_outputs()
        _pump(wx_app, lambda cycle=cycle: f"minimized-{cycle}" in frame._wx_jobs_controls["stdout"].GetValue())
        assert backend.list_calls == before
        frame.ProcessEvent(wx.IconizeEvent(frame.GetId(), False))
        _pump(wx_app, lambda: not frame._wx_jobs_state["minimized"])
        frame._wx_jobs_refresh_jobs()
        _pump(wx_app, lambda: backend.list_calls > before)
    assert backend.list_calls < 210
    assert not frame._wx_jobs_state["minimized"]
    _close(frame, wx_app)


def test_wx_jobs_stress_pause_resume_state_never_desynchronizes(wx_app):
    backend = MockHPCJobs(1)
    frame = _open(backend.list_jobs, backend.read_output)
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame, 0)
    _pump(wx_app, lambda: frame._wx_jobs_controls["stdout"].GetValue())
    for transition in range(100):
        _click(frame._wx_jobs_controls["pause"])
        backend.set_output("1", f"pause-{transition}")
        frame._wx_jobs_refresh_outputs()
        _pump(wx_app, lambda transition=transition: f"pause-{transition}" in frame._wx_jobs_controls["stdout"].GetValue())
        paused = transition % 2 == 0
        assert frame._wx_jobs_state["user_paused"] is paused
        if not paused:
            assert frame._wx_jobs_state["follow_calls"] > 0
    assert not frame._wx_jobs_state["user_paused"]
    assert frame._wx_jobs_controls["pause"].GetLabel() == "Pause Live Follow"
    _close(frame, wx_app)


def test_wx_jobs_stress_out_of_order_output_completions_are_safe(wx_app):
    backend = MockHPCJobs(3)
    gates = {job_id: threading.Event() for job_id in backend.jobs}
    started = {job_id: threading.Event() for job_id in backend.jobs}

    def read(job_id):
        job_id = str(job_id)
        started[job_id].set()
        gates[job_id].wait(3)
        return {"stdout": f"output-{job_id}"}

    frame = _open(backend.list_jobs, read)
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 3)
    for _ in range(100):
        started["1"].clear()
        gates["1"].clear()
        gates["2"].set()
        _select(frame, 0)
        _pump(wx_app, lambda: started["1"].is_set())
        _select(frame, 1)
        gates["1"].set()
        _pump(wx_app, lambda: frame._wx_jobs_controls["stdout"].GetValue() == "output-2\n")
        _pump(wx_app, lambda: not frame._wx_jobs_state["output_in_flight"])
    _close(frame, wx_app)


def test_wx_jobs_stress_blocked_reads_never_overlap(wx_app):
    backend = MockHPCJobs(1)
    gates = []
    started = []
    active_reads = 0
    peak_reads = 0
    read_lock = threading.Lock()

    def read(_job_id):
        nonlocal active_reads, peak_reads
        gate = threading.Event()
        with read_lock:
            index = len(gates)
            gates.append(gate)
            started.append(threading.Event())
            active_reads += 1
            peak_reads = max(peak_reads, active_reads)
            started[index].set()
        try:
            gate.wait(3)
            return {"stdout": f"round-{index}"}
        finally:
            with read_lock:
                active_reads -= 1

    frame = _open(backend.list_jobs, read)
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame, 0)
    for index in range(50):
        _pump(wx_app, lambda index=index: len(started) > index and started[index].is_set())
        for _ in range(5):
            frame._wx_jobs_refresh_outputs()
        assert peak_reads == 1
        gates[index].set()
        _pump(wx_app, lambda index=index: f"round-{index}" in frame._wx_jobs_controls["stdout"].GetValue())
        if index < 49:
            frame._wx_jobs_refresh_outputs()
    assert peak_reads == 1
    _close(frame, wx_app)


def test_wx_jobs_stress_large_output_remains_bounded_and_responsive(wx_app):
    backend = MockHPCJobs(1)
    backend.set_output("1", "\n".join(f"line-{index}" for index in range(100_000)))
    frame = _open(backend.list_jobs, backend.read_output)
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame, 0)
    _pump(wx_app, lambda: "line-99999" in frame._wx_jobs_controls["stdout"].GetValue(), timeout=5)
    lines = frame._wx_jobs_controls["stdout"].GetValue().splitlines()
    assert len(lines) == 5000
    assert lines[0] == "line-95000"
    assert lines[-1] == "line-99999"
    _close(frame, wx_app)


def test_wx_jobs_stress_close_while_output_read_in_flight_is_safe(wx_app):
    backend = MockHPCJobs(1)
    started, release = threading.Event(), threading.Event()

    def read(_job_id):
        started.set()
        release.wait(3)
        return {"stdout": "late"}

    frame = _open(backend.list_jobs, read)
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select(frame, 0)
    assert started.wait(1)
    title = _close(frame, wx_app)
    release.set()
    wx_app.ProcessPendingEvents()
    assert not [window for window in wx.GetTopLevelWindows() if window and window.GetTitle() == title]


def test_wx_jobs_stress_close_during_job_list_refresh_is_safe(wx_app):
    started, release = threading.Event(), threading.Event()

    def list_jobs():
        started.set()
        release.wait(3)
        return [{"id": "1", "state": "RUNNING"}]

    frame = _open(list_jobs, None)
    assert started.wait(1)
    title = _close(frame, wx_app)
    release.set()
    wx_app.ProcessPendingEvents()
    assert not [window for window in wx.GetTopLevelWindows() if window and window.GetTitle() == title]


def test_wx_jobs_stress_open_close_repeatedly_does_not_leak_windows_or_timers(wx_app):
    for _ in range(50):
        frame = _open()
        _close(frame, wx_app)
    assert not [window for window in wx.GetTopLevelWindows() if window and window.GetTitle() == "Jobs"]


def test_wx_jobs_stress_multi_job_update_pressure():
    backend = MockHPCJobs(50)
    model = WxJobsModel()
    states = ("PENDING", "RUNNING", "COMPLETING", "COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY")
    for cycle in range(250):
        job_id = str(cycle % 50 + 1)
        backend.transition(job_id, states[cycle % len(states)])
        for row in backend.list_jobs():
            model.update_job_state(row["id"], row["state"])
    assert all(model._job_states[job_id] == backend.jobs[job_id]["state"] for job_id in backend.jobs)
    assert backend.list_calls == 250


def test_wx_jobs_stress_missing_output_recovery_pressure():
    backend = MockHPCJobs(5)
    for cycle in range(50):
        job_id = str(cycle % 5 + 1)
        backend.missing.add(job_id)
        with pytest.raises(FileNotFoundError):
            backend.read_output(job_id)
        backend.missing.clear()
        assert backend.read_output(job_id)["stdout"] == "line 1"


def test_wx_jobs_stress_backend_workers_and_reads_are_bounded():
    backend = MockHPCJobs(50)
    gui_thread = threading.get_ident()
    for cycle in range(250):
        backend.transition(str(cycle % 50 + 1), "RUNNING")
        worker = threading.Thread(target=backend.read_output, args=(str(cycle % 50 + 1),))
        worker.start()
        worker.join(2)
        assert not worker.is_alive()
    assert backend.peak_reads == 1
    assert gui_thread not in backend.worker_threads
