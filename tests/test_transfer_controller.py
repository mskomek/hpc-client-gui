from __future__ import annotations

import threading
import time

from hpc_gui.services.transfer_controller import TransferController, TransferItem


def test_controller_runs_parallel_and_bounds_history() -> None:
    events = []
    lock = threading.Lock()

    def run(item, progress):
        progress(1, 2)
        progress(2, 2)

    controller = TransferController(
        [TransferItem("upload", str(i), f"/remote/{i}") for i in range(3)],
        run,
        parallel_limit=2,
        history_limit=2,
        on_queue=lambda event, item: events.append((event, item.src)),
    )
    controller.start()
    assert controller.wait(2)
    assert len(controller.completed) == 2
    assert controller.pending == []
    assert [event for event, _ in events].count("completed") == 3


def test_controller_cancel_keeps_item_failed_without_finalization() -> None:
    cancelled = threading.Event()

    def run(item, progress):
        progress(1, 10)
        while not cancelled.is_set():
            time.sleep(0.001)
        progress(2, 10)

    controller = TransferController(
        [TransferItem("download", "/remote/a", "a")],
        run,
    )
    controller.start()
    time.sleep(0.02)
    controller.cancel_all()
    cancelled.set()
    assert controller.wait(2)
    assert controller.failed[0][1] == "cancelled"
    assert controller.completed == []


def test_controller_retry_failed_requeues_item() -> None:
    attempts = 0

    def run(item, progress):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("temporary")
        progress(1, 1)

    item = TransferItem("upload", "a", "/remote/a")
    controller = TransferController([item], run)
    controller.start()
    assert controller.wait(2)
    assert controller.retry_failed() == 1
    controller.start()
    assert controller.wait(2)
    assert controller.completed == [item]


def test_controller_enqueue_adds_work_while_running() -> None:
    started = threading.Event()
    release = threading.Event()
    completed: list[str] = []

    def run(item, progress):
        started.set()
        release.wait(2)
        completed.append(item.src)

    controller = TransferController(
        [TransferItem("download", "first", "first")],
        run,
    )
    controller.start()
    assert started.wait(1)
    assert controller.enqueue([TransferItem("upload", "second", "second")])
    release.set()
    assert controller.wait(2)
    assert completed == ["first", "second"]
