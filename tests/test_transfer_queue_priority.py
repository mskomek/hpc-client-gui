"""Priority and selected retry/history actions do not alter filesystem barriers."""
from __future__ import annotations

from threading import Event

import pytest

from hpc_gui.services.transfer_controller import TransferController, TransferItem


def item(name, op="upload"):
    return TransferItem(op, name, f"/{name}")


@pytest.mark.unit
def test_priority_is_stable_and_cannot_cross_filesystem_barrier():
    first, low, high, barrier, last, urgent = (
        item("first"), item("low"), item("high"), item("mkdir", "mkdir_remote"),
        item("last"), item("urgent"),
    )
    calls, events = [], []
    entered, release = Event(), Event()

    def run(it, progress):
        calls.append(it)
        if it is first:
            entered.set()
            assert release.wait(5)
        progress(1, 1)

    # Include a delete barrier to prevent the initial mkdir normalization.
    barrier.op = "delete"
    ctrl = TransferController([first, low, high, barrier, last, urgent], run,
                              on_queue=lambda event, it: events.append((event, it)))
    ctrl.start()
    try:
        assert entered.wait(5)
        assert ctrl.set_pending_priorities([first, barrier], "Highest") == 0
        assert ctrl.set_pending_priorities([low], "bogus") == 0
        assert ctrl.set_pending_priorities([high, urgent], "Highest") == 2
        assert ctrl.pending == [high, low, barrier, urgent, last]
        assert first.priority == barrier.priority == "Normal"
        assert [it for event, it in events if event == "priority"] == [high, urgent]
    finally:
        release.set()
        assert ctrl.wait(5)
    assert calls == [first, high, low, barrier, urgent, last]


@pytest.mark.unit
def test_selected_retry_and_history_removal_do_not_replay_or_delete_files():
    a, b, c = item("a"), item("b"), item("c")
    calls, events = [], []

    def run(it, progress):
        calls.append(it)
        if it in (a, b) and calls.count(it) == 1:
            raise OSError("synthetic error")
        progress(1, 1)

    ctrl = TransferController([a, b, c], run,
                              on_queue=lambda event, it: events.append((event, it)))
    ctrl.start()
    assert ctrl.wait(5)
    assert [it for it, _ in ctrl.failed] == [a, b]
    assert ctrl.retry_failed_items([b, c]) == 1
    assert ctrl.pending == [b]
    assert [it for it, _ in ctrl.failed] == [a]
    ctrl.start()
    assert ctrl.wait(5)
    assert calls == [a, b, c, b]
    assert ctrl.remove_failed_items([a]) == 1
    assert ctrl.remove_completed_items([c]) == 1
    assert not ctrl.failed
    assert ctrl.completed == [b]
    assert ctrl.remove_completed_items() == 1
    assert not ctrl.completed
    assert ("forgotten_failed", a) in events
    assert ("forgotten_completed", c) in events
    assert calls == [a, b, c, b]
