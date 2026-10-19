"""Concurrency regressions for the optional startup update check."""

from threading import Barrier, Thread

from hpc_gui.startup_update_state import StartupUpdateState


def test_normal_completion_exposes_release_and_error():
    state = StartupUpdateState()
    release = object()

    assert state.complete(release) is True
    assert state.status == StartupUpdateState.COMPLETE
    assert state.result() == (release, None)
    assert state.skip() is False


def test_manual_skip_is_idempotent_and_ignores_late_worker_result():
    state = StartupUpdateState()
    release = object()

    assert state.skip() is True
    assert state.skip() is False
    assert state.complete(release) is False
    assert state.status == StartupUpdateState.SKIPPED
    assert state.result() == (None, None)


def test_timeout_ignores_worker_result_that_arrives_later():
    state = StartupUpdateState()
    release = object()

    assert state.timeout() is True
    assert state.complete(release) is False
    assert state.status == StartupUpdateState.TIMED_OUT
    assert state.result() == (None, None)


def test_completion_skip_race_has_one_authoritative_outcome():
    state = StartupUpdateState()
    release = object()
    barrier = Barrier(3)
    outcomes = {}

    def finish_check():
        barrier.wait()
        outcomes["complete"] = state.complete(release)

    def skip_check():
        barrier.wait()
        outcomes["skip"] = state.skip()

    workers = [Thread(target=finish_check), Thread(target=skip_check)]
    for worker in workers:
        worker.start()
    barrier.wait()
    for worker in workers:
        worker.join()

    assert sum(outcomes.values()) == 1
    if outcomes["complete"]:
        assert state.status == StartupUpdateState.COMPLETE
        assert state.result() == (release, None)
    else:
        assert state.status == StartupUpdateState.SKIPPED
        assert state.result() == (None, None)
