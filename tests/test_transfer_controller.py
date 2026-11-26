from __future__ import annotations

import threading
import time

import pytest

from hpc_gui.services.transfer_controller import TransferController, TransferItem


@pytest.mark.unit
def test_controller_runs_parallel_and_bounds_history() -> None:
    events = []

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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
@pytest.mark.concurrency
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


@pytest.mark.unit
@pytest.mark.parametrize("direction", ["upload", "download"])
def test_failed_directory_blocks_descendants_until_successful_retry(tmp_path, direction):
    mkdir_op = "mkdir_remote" if direction == "upload" else "mkdir_local"
    root = "/work" if direction == "upload" else str(tmp_path)
    bad = root + "/bad"
    parent = TransferItem(mkdir_op, "", bad)
    child = TransferItem(mkdir_op, "", bad + "/nested")
    nested = TransferItem(direction, "source", bad + "/nested/file")
    direct = TransferItem(direction, "source", bad + "/file")
    sibling = TransferItem(direction, "source", root + "/bad-sibling/file")
    called = []
    fail = True

    def run(item, progress):
        called.append(item)
        if item is parent and fail:
            raise PermissionError("mkdir denied")
        progress(1, 1)

    controller = TransferController([parent, child, nested, direct, sibling], run, parallel_limit=3)
    controller.start()
    assert controller.wait(5)
    assert called == [parent, sibling]
    assert controller.completed == [sibling]
    errors = {item.dst: error for item, error in controller.failed}
    assert errors[bad] == "mkdir denied"
    for item in (child, nested, direct):
        assert "Destination directory prerequisite failed:" in errors[item.dst]

    # Retrying only a child must not bypass the failed directory.
    assert controller.retry_failed_items([nested]) == 1
    controller.start()
    assert controller.wait(5)
    assert called == [parent, sibling]
    assert len(controller.failed) == 4

    # Retrying the prerequisites and descendants recovers the queue without
    # repeating the independent transfer that already completed.
    fail = False
    assert controller.retry_failed() == 4
    controller.start()
    assert controller.wait(5)
    assert not controller.failed and not controller.pending
    assert called[:4] == [parent, sibling, parent, child]
    assert set(id(item) for item in called[4:]) == {id(nested), id(direct)}
    assert len(controller.completed) == 5


@pytest.mark.unit
def test_forgotten_directory_failure_does_not_unlock_descendants():
    parent = TransferItem("mkdir_remote", "", "/work/fail")
    child = TransferItem("upload", "source", "/work/fail/data")
    called = []

    def run(item, progress):
        called.append(item)
        raise OSError("denied")

    controller = TransferController([parent, child], run)
    controller.start()
    assert controller.wait(5)
    assert controller.remove_failed_items([parent]) == 1
    assert controller.retry_failed() == 1
    controller.start()
    assert controller.wait(5)
    assert called == [parent]
    assert "prerequisite failed" in controller.failed[0][1]


@pytest.mark.unit
@pytest.mark.concurrency
def test_recursive_plan_prepares_all_mkdirs_before_parallel_upload_phase():
    prepared = []
    started = []
    release = threading.Event()
    all_started = threading.Event()
    lock = threading.Lock()
    items = [
        TransferItem("mkdir_remote", "", "/remote/root"),
        TransferItem("mkdir_remote", "", "/remote/root/one"),
        TransferItem("upload", "one.bin", "/remote/root/one/one.bin"),
        TransferItem("mkdir_remote", "", "/remote/root/two"),
        TransferItem("upload", "two.bin", "/remote/root/two/two.bin"),
        TransferItem("upload", "root.bin", "/remote/root/root.bin"),
    ]

    def run(item, progress):
        if item.op == "mkdir_remote":
            prepared.append(item.dst)
        else:
            with lock:
                assert prepared == ["/remote/root", "/remote/root/one", "/remote/root/two"]
                started.append(item.src)
                if len(started) == 3:
                    all_started.set()
            assert release.wait(5)
        progress(1, 1)

    controller = TransferController(items, run, parallel_limit=3)
    try:
        controller.start()
        assert all_started.wait(5), started
    finally:
        release.set()
        assert controller.wait(5)
    assert not controller.failed
    assert len(controller.completed) == len(items)
    assert set(started) == {"one.bin", "two.bin", "root.bin"}
