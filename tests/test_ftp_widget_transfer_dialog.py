"""Focused FTP widget tests for transfer dialog behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import threading
import time
from unittest.mock import patch
import pytest
from PySide6.QtWidgets import QApplication
from hpc_gui.ui.dialogs.transfer_dialog import TransferDialog, TransferItem
from ftp_widget_test_support import FtpWidgetTestCase


class FtpWidgetTransferDialogTests(FtpWidgetTestCase):
    @pytest.mark.gui
    @pytest.mark.qt
    def test_multi_folder_download_queue_caps_rows_without_truncating_plan(self) -> None:
        items = [
            TransferItem(
                "download",
                f"/remote/folder-{index % 2}/file-{index}.bin",
                f"file-{index}.bin",
            )
            for index in range(5)
        ]
        dialog = TransferDialog(
            title="Download",
            items=items,
            run_item=lambda _item, _progress=None: None,
        )
        try:
            with patch.object(
                self.widget.transfer_activity,
                "_MAX_VISIBLE_TRANSFER_ROWS",
                3,
            ):
                self.widget.transfer_activity.record(
                    "controller",
                    [dialog],
                    "Download",
                )

            self.assertEqual(len(dialog._items), 5)
            self.assertEqual(len(dialog._pending), 5)
            self.assertEqual(
                self.widget.transfer_activity.queue_list.topLevelItemCount(),
                4,
            )
            info_row = self.widget.transfer_activity.queue_list.topLevelItem(3)
            self.assertEqual(info_row.text(2), "Remaining: 2")
            self.assertIsNone(self.widget.transfer_activity.queue_list.itemWidget(info_row, 4))
            self.assertIn(
                "5 files.",
                self.widget.transfer_activity.summary_label.text(),
            )
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_dialog_is_modeless_and_reports_progress(self) -> None:
        transfer_item = TransferItem("download", "/remote/big.bin", "big.bin")
        dialog = TransferDialog(
            title="Download",
            items=[transfer_item, TransferItem("download", "/remote/next.bin", "next.bin")],
            run_item=lambda _item, _progress=None: None,
        )
        try:
            self.assertFalse(dialog.isModal())
            self.assertEqual(dialog.queue_list.count(), 0)
            dialog._refresh()
            self.assertEqual(dialog.queue_list.count(), 2)

            dialog.clear_pending()
            self.assertEqual(dialog.queue_list.count(), 0)

            dialog._started_at = 1.0
            with patch("hpc_gui.ui.dialogs.transfer_dialog.time.monotonic", return_value=3.0):
                dialog._on_transfer_progress(transfer_item, 2048, 4096)
            detail = dialog.lbl_transfer_stats.text()
            self.assertIn("2.0 KB/4.0 KB", detail)
            self.assertIn("/s", detail)

            dialog._on_transfer_progress(transfer_item, 5 * 1024**3, 8 * 1024**3)
            self.assertIn("5.0 GB/8.0 GB", dialog.lbl_transfer_stats.text())
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.performance
    def test_transfer_dialog_bounds_and_coalesces_large_queue_publication(self) -> None:
        items = [
            TransferItem("download", f"/remote/{index}.bin", f"{index}.bin") for index in range(5)
        ]
        dialog = TransferDialog(
            title="Download",
            items=items,
            run_item=lambda _item, _progress=None: None,
        )
        try:
            published = []
            dialog.transferListsChanged.connect(
                lambda pending, _errors, _completed: published.append(pending)
            )
            with patch.object(dialog, "_MAX_VISIBLE_LIST_ITEMS", 3):
                dialog._refresh()
                self.assertEqual(dialog.queue_list.count(), 4)
                self.assertEqual(dialog.queue_list.item(3).text(), "Remaining: 2")
                self.assertEqual(len(published[-1]), 5)

                dialog._refresh_scheduled = False
                with patch.object(dialog._refresh_timer, "start") as start_timer:
                    dialog._schedule_refresh()
                    dialog._schedule_refresh()
                start_timer.assert_called_once_with()
        finally:
            dialog.deleteLater()

    @pytest.mark.integration
    @pytest.mark.concurrency
    def test_transfer_dialog_runs_up_to_parallel_limit(self) -> None:
        started: list[str] = []
        finished: list[str] = []
        release = threading.Event()
        lock = threading.Lock()
        items = [
            TransferItem("download", "/remote/a.bin", "a.bin"),
            TransferItem("download", "/remote/b.bin", "b.bin"),
            TransferItem("download", "/remote/c.bin", "c.bin"),
        ]

        def run_item(item, _progress=None):
            with lock:
                started.append(item.src)
            release.wait(5)
            with lock:
                finished.append(item.src)

        dialog = TransferDialog(
            title="Download",
            items=items,
            run_item=run_item,
            parallel_limit=2,
        )
        try:
            dialog.start()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                QApplication.processEvents()
                with lock:
                    if len(started) >= 2:
                        break
                time.sleep(0.01)
            with lock:
                self.assertEqual(len(started), 2)
                self.assertEqual(finished, [])

            release.set()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not dialog.finished_cleanly():
                QApplication.processEvents()
                time.sleep(0.01)
            self.assertTrue(dialog.finished_cleanly())
            with lock:
                self.assertCountEqual(started, [item.src for item in items])
                self.assertCountEqual(finished, [item.src for item in items])
        finally:
            dialog.cancel_all()
            dialog.deleteLater()

    @pytest.mark.integration
    @pytest.mark.concurrency
    def test_transfer_dialog_finishes_mkdir_before_parallel_transfer_batch(self) -> None:
        prepared = threading.Event()
        started_uploads: list[str] = []
        lock = threading.Lock()
        items = [
            TransferItem("mkdir_remote", "", "/remote/folder"),
            TransferItem("upload", "first.bin", "/remote/folder/first.bin"),
            TransferItem("upload", "second.bin", "/remote/folder/second.bin"),
        ]

        def run_item(item, _progress=None):
            if item.op == "mkdir_remote":
                time.sleep(0.03)
                prepared.set()
                return
            self.assertTrue(prepared.is_set())
            with lock:
                started_uploads.append(item.src)

        dialog = TransferDialog(
            title="Upload",
            items=items,
            run_item=run_item,
            parallel_limit=2,
        )
        try:
            dialog.start()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not dialog.finished_cleanly():
                QApplication.processEvents()
                time.sleep(0.01)
            self.assertTrue(dialog.finished_cleanly())
            self.assertCountEqual(started_uploads, ["first.bin", "second.bin"])
        finally:
            dialog.cancel_all()
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_dialog_never_exceeds_backend_safe_cap(self) -> None:
        dialog = TransferDialog(
            title="Upload",
            items=[],
            run_item=lambda _item, _progress=None: None,
            parallel_limit=5,
            max_parallel_limit=1,
        )
        try:
            self.assertEqual(dialog._parallel_limit, 1)
            self.assertEqual(dialog.set_parallel_limit(5), 1)
            self.assertEqual(dialog._parallel_limit, 1)
            self.assertIn("1", dialog.lbl_parallel_hint.text())
        finally:
            dialog.deleteLater()

    @pytest.mark.integration
    def test_transfer_dialog_coalesces_burst_progress_and_delivers_final(self) -> None:
        item = TransferItem("upload", "burst.bin", "/remote/burst.bin")
        dialog = TransferDialog(
            title="Upload", items=[item], run_item=lambda _item, _progress=None: None
        )
        try:
            published: list[tuple[int, int]] = []
            dialog.transferProgressChanged.connect(
                lambda _item, done, total: published.append((int(done), int(total)))
            )
            with patch(
                "hpc_gui.ui.dialogs.transfer_dialog.time.monotonic",
                side_effect=[10.0, 10.001, 10.002, 10.100, 10.251, 10.252],
            ):
                dialog._on_transfer_progress(item, 100, 1000)
                dialog._on_transfer_progress(item, 200, 1000)
                dialog._on_transfer_progress(item, 300, 1000)
                dialog._on_transfer_progress(item, 400, 1000)
                self.assertEqual(published, [(100, 1000)])
                dialog._on_transfer_progress(item, 500, 1000)
                dialog._on_transfer_progress(item, 1000, 1000)
            self.assertEqual(published, [(100, 1000), (500, 1000), (1000, 1000)])
            self.assertEqual(dialog._last_progress_by_item[id(item)], (1000, 10.252))
        finally:
            dialog.deleteLater()
