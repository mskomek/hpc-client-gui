import threading

from mock_hpc_jobs import MockHPCJobs

from hpc_gui.wx_jobs import WxJobsModel


def test_mock_hpc_refresh_stress_and_rapid_transitions():
    backend = MockHPCJobs(50)
    model = WxJobsModel()
    for index in range(250):
        backend.transition("1", ("PENDING", "RUNNING", "COMPLETING", "COMPLETED")[index % 4])
        rows = backend.list_jobs()
        for row in rows:
            model.update_job_state(row["id"], row["state"])
        backend.append("1", f"line {index}")
        assert backend.read_output("1")["stdout"].endswith(f"line {index}")
    assert backend.list_calls == 250
    assert backend.peak_reads == 1


def test_mock_hpc_missing_output_recovers_and_cancel_is_deterministic():
    backend = MockHPCJobs(1)
    backend.missing.add("1")
    try:
        backend.read_output("1")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing output did not fail")
    backend.missing.clear()
    assert backend.read_output("1")["stdout"] == "line 1"
    backend.cancel("1")
    assert backend.jobs["1"]["state"] == "CANCELLED"


def test_mock_hpc_blocked_reads_are_thread_safe_and_bounded():
    backend = MockHPCJobs(1)
    backend.read_gate = threading.Event()
    first = threading.Thread(target=backend.read_output, args=("1",))
    first.start()
    assert first.is_alive()
    backend.read_gate.set()
    first.join(2)
    assert not first.is_alive()
    assert backend.peak_reads == 1
    assert backend.worker_threads
