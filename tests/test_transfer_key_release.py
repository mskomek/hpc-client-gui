"""Regression test: cancelling must release the in-flight transfer keys.

`_run_plan_with_progress` reserves a (op, src, dst) key per upload/download
so the same file cannot be queued twice, and released them only from the
dialog's `finished` signal. A cancelled dialog stays open and never emits
it, so the keys were held for the rest of the session: re-downloading the
same folder built a full plan and then filtered every transfer out of it
as a duplicate, leaving only the mkdir ops. The queue then "finished"
instantly with nothing transferred.
"""

from __future__ import annotations

import os
import threading
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel, _PlannedOp


class _Files:
    supports_parallel_transfers = False

    def listdir_entries(self, _path: str):
        return []


class TransferKeyReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.panel = RemoteDirPanel()
        self.panel.set_session({"connected": True, "files": _Files()})
        self.panel.set_transfer_dialog_visible(False)
        self.addCleanup(self.panel.deleteLater)
        self.plan = [
            _PlannedOp("mkdir_local", "", "C:/local/DP_41"),
            _PlannedOp("download", "/remote/DP_41/big.h5", "C:/local/DP_41/big.h5"),
            _PlannedOp("download", "/remote/DP_41/small.dat", "C:/local/DP_41/small.dat"),
        ]

    def tearDown(self) -> None:
        stop = getattr(self, "_stop_event", None)
        if stop is not None:
            stop.set()
        for dialog in list(self.panel._transfer_dialogs):
            dialog.cancel_all()
        self._pump(
            lambda: all(not dialog._running for dialog in self.panel._transfer_dialogs),
            timeout=10.0,
        )

    def _pump(self, predicate, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return
            time.sleep(0.005)
        self.app.processEvents()

    def _stalling_executor(self):
        started = threading.Event()
        stop = threading.Event()

        def execute(item, progress_cb=None):
            if item.op != "download" or progress_cb is None:
                return
            started.set()
            for _ in range(2000):
                if stop.is_set():
                    return
                progress_cb(1, 2)
                time.sleep(0.005)

        # The executor runs on a worker thread; once the dialog is cancelled
        # it must stop emitting progress events, otherwise the thread keeps
        # crossing Qt events into widgets deleted by later tests (segfault).
        self.addCleanup(stop.set)
        self._stop_event = stop
        return execute, started, stop

    def test_cancel_releases_the_keys_so_the_same_files_replan(self) -> None:
        execute, started, stop = self._stalling_executor()
        self.panel._execute_transfer_item = execute  # type: ignore[method-assign]

        self.assertTrue(self.panel._run_plan_with_progress(list(self.plan), "test"))
        self._pump(started.is_set)
        self.assertEqual(len(self.panel._active_transfer_keys), 2)

        dialog = self.panel._transfer_dialogs[-1]
        stop.set()
        dialog.cancel_all()
        self._pump(lambda: not dialog._running)

        # The dialog is still open and never emitted `finished` - this is
        # exactly when the keys used to stay reserved for good.
        self.assertIn(dialog, self.panel._transfer_dialogs)
        self.assertEqual(self.panel._active_transfer_keys, set())

        # A second attempt at the same files must survive the duplicate filter.
        queued: list[list] = []
        self.panel._transfer_activity_callback = lambda event, items, _title: (
            queued.append(list(items)) if event == "queued" else None
        )
        self.panel._execute_transfer_item = lambda item, progress_cb=None: None  # type: ignore[method-assign]
        self.assertTrue(self.panel._run_plan_with_progress(list(self.plan), "test"))
        self.assertEqual(
            sorted(item.op for item in queued[-1]),
            ["download", "download", "mkdir_local"],
        )

    def test_keys_stay_reserved_while_the_queue_is_running(self) -> None:
        execute, started, stop = self._stalling_executor()
        self.panel._execute_transfer_item = execute  # type: ignore[method-assign]

        self.assertTrue(self.panel._run_plan_with_progress(list(self.plan), "test"))
        self._pump(started.is_set)

        # Same plan again while the first is in flight: the transfers are
        # duplicates and must not be queued a second time.
        queued: list[list] = []
        self.panel._transfer_activity_callback = lambda event, items, _title: (
            queued.append(list(items)) if event == "queued" else None
        )
        self.panel._run_plan_with_progress(list(self.plan), "test")
        self.assertTrue(
            all("download" not in [item.op for item in batch] for batch in queued),
            f"a duplicate download was queued: {queued}",
        )

        for dialog in list(self.panel._transfer_dialogs):
            stop.set()
            dialog.cancel_all()
        self._pump(lambda: all(not dialog._running for dialog in self.panel._transfer_dialogs))


if __name__ == "__main__":
    unittest.main()
