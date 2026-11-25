"""Transfer cancellation and queue recovery regressions on the shared engine."""

from __future__ import annotations

import threading
import time
import unittest

import pytest

from hpc_gui.services.transfer_controller import TransferController, TransferItem


class TransferControllerCancelTests(unittest.TestCase):
    @pytest.mark.unit
    @pytest.mark.concurrency
    def test_cancel_reports_every_item_of_a_parallel_batch(self) -> None:
        started = threading.Barrier(4, timeout=5)
        events: list[tuple[str, str]] = []
        lock = threading.Lock()

        def run(item, progress):
            progress(0, 2)
            started.wait()
            # Spin until the cancel flag makes progress() raise.
            for _ in range(2000):
                progress(1, 2)
                time.sleep(0.001)

        def on_queue(event: str, item: TransferItem) -> None:
            with lock:
                events.append((event, item.src))

        controller = TransferController(
            [TransferItem("download", f"/remote/{i}", str(i)) for i in range(3)],
            run,
            parallel_limit=3,
            on_queue=on_queue,
        )
        controller.start()
        started.wait()
        controller.cancel_all()
        self.assertTrue(controller.wait(5))

        finished = {src for event, src in events if event in ("completed", "failed")}
        self.assertEqual(finished, {"/remote/0", "/remote/1", "/remote/2"})
        self.assertEqual(
            {error for _item, error in controller.failed}, {"cancelled"}
        )


@pytest.mark.unit
@pytest.mark.concurrency
@pytest.mark.parametrize("action", ["stop", "clear", "remove", "cancel"])
def test_queue_recovery_does_not_run_removed_or_completed_items(action):
    entered = threading.Event()
    release = threading.Event()
    calls = []
    first = TransferItem("download", "/first", "first")
    second = TransferItem("download", "/second", "second")
    third = TransferItem("mkdir_remote", "", "/third")

    def run(item, progress):
        calls.append(item)
        if item is first and len(calls) == 1:
            entered.set()
            assert release.wait(5)
        progress(1, 1)

    controller = TransferController([first, second, third], run)
    controller.start()
    try:
        assert entered.wait(5)
        if action == "stop":
            controller.stop_after_current()
        elif action == "clear":
            controller.clear_pending()
        elif action == "remove":
            assert controller.remove_pending_items([second]) == 1
        else:
            controller.cancel_all()
            assert controller.retry_failed() == 0
    finally:
        release.set()
    assert controller.wait(5), "queue failed to terminate"
    if action == "remove":
        assert calls == [first, third]
        assert controller.completed == [first, third]
        assert not controller.pending
    elif action == "clear":
        assert calls == [first]
        assert not controller.pending
        controller.start()
        assert controller.wait(5)
        assert calls == [first]
    elif action == "stop":
        assert calls == [first]
        assert controller.completed == [first]
        assert controller.pending == [second, third]
        controller.start()
        assert controller.wait(5)
        assert calls == [first, second, third]
        assert controller.completed == [first, second, third]
    else:
        assert calls == [first]
        assert controller.failed == [(first, "cancelled")]
        assert not controller.completed
        assert controller.pending == [second, third]
        assert controller.retry_failed() == 1
        controller.start()
        assert controller.wait(5)
        assert calls == [first, first, second, third]
        assert not controller.failed
        assert controller.completed == [first, second, third]
    assert not controller.pending


@pytest.mark.unit
@pytest.mark.concurrency
def test_completed_queue_restart_is_not_a_second_transfer():
    item = TransferItem("download", "/first", "first")
    calls = []
    controller = TransferController([item], lambda item, progress: calls.append(item))
    controller.start()
    assert controller.wait(5)
    controller.start()
    assert controller.wait(5)
    assert calls == [item]
    assert controller.completed == [item]
