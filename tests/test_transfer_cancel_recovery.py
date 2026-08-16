"""Regression tests for cancelling an in-flight transfer.

Cancelling used to strand the running item: the dialog's cancelled branch
returned before the shared cleanup, so the item stayed in ``_active_items``
(its "Running: ..." row never cleared, and ``start``/``process_queue``
refused to run again), and the controller abandoned the rest of a parallel
batch without reporting those items at all.
"""

from __future__ import annotations

import os
import threading
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from hpc_gui.services.transfer_controller import TransferController, TransferItem
from hpc_gui.ui.dialogs.transfer_dialog import TransferDialog


class TransferControllerCancelTests(unittest.TestCase):
    def test_cancel_reports_every_item_of_a_parallel_batch(self) -> None:
        started = threading.Barrier(3, timeout=5)
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


class TransferDialogCancelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, items, run_item, parallel_limit: int = 1) -> TransferDialog:
        dialog = TransferDialog(
            title="test",
            items=items,
            run_item=run_item,
            parallel_limit=parallel_limit,
        )
        self.addCleanup(dialog.deleteLater)
        return dialog

    def _pump(self, predicate, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return
            time.sleep(0.005)
        self.app.processEvents()

    def test_cancelled_item_leaves_the_active_list_and_can_be_restarted(self) -> None:
        attempts: list[str] = []

        def run(item, progress=None):
            attempts.append(item.src)
            # Only the first attempt stalls; progress() is what observes the
            # cancel, so nothing else may end the loop or the race is lost.
            if progress is None or len(attempts) > 1:
                return
            for _ in range(2000):
                progress(1, 2)
                time.sleep(0.005)

        item = TransferItem("download", "/remote/big.bin", "big.bin")
        dialog = self._dialog([item], run)
        dialog.start()
        self._pump(lambda: bool(dialog._active_items))
        self.assertEqual(dialog._active_items, [item])

        dialog.cancel_all()
        self._pump(lambda: not dialog._running and not dialog._active_items)

        # It must not stay pinned as the running transfer...
        self.assertEqual(dialog._active_items, [])
        self.assertIsNone(dialog._active_item)
        self.assertEqual(dialog._completed, [])
        # ...and it must land somewhere retryable.
        self.assertEqual([failed for failed, _err in dialog._errors], [item])

        self.assertEqual(dialog.retry_all_errors(), 1)
        self._pump(lambda: len(attempts) >= 2)
        self.assertEqual(attempts, ["/remote/big.bin", "/remote/big.bin"])

    def test_cancel_does_not_wedge_process_queue(self) -> None:
        def run(item, progress=None):
            if progress is None:
                return
            for _ in range(2000):
                progress(1, 2)
                time.sleep(0.005)

        items = [
            TransferItem("download", "/remote/a", "a"),
            TransferItem("download", "/remote/b", "b"),
        ]
        dialog = self._dialog(items, run)
        dialog.start()
        self._pump(lambda: bool(dialog._active_items))
        dialog.cancel_all()
        self._pump(lambda: not dialog._running and not dialog._active_items)

        dialog._pending = [items[1]]
        self.assertTrue(dialog.process_queue())


if __name__ == "__main__":
    unittest.main()
