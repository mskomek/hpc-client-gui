"""Focused FTP widget tests for activity rows behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import threading
import time
from unittest.mock import patch
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QMessageBox
from hpc_gui.ui.dialogs.transfer_dialog import TransferDialog, TransferItem
from ftp_widget_test_support import FtpWidgetTestCase


class FtpWidgetActivityRowsTests(FtpWidgetTestCase):
    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_activity_failed_and_completed_context_actions_work(self) -> None:
        failed = TransferItem("upload", "failed.txt", "/remote/failed.txt")
        completed = TransferItem("download", "/remote/done.txt", "done.txt")
        dialog = TransferDialog(
            title="Transfers",
            items=[],
            run_item=lambda _item, _progress=None: None,
        )

        class FakeAction:
            def __init__(self, text: str) -> None:
                self.text = text
                self.enabled = True

            def setEnabled(self, enabled: bool) -> None:
                self.enabled = enabled

            def isEnabled(self) -> bool:
                return self.enabled

        chosen_index = [0]

        class FakeMenu:
            def __init__(self, _parent=None) -> None:
                self.actions = []

            def addAction(self, text: str):
                action = FakeAction(text)
                self.actions.append(action)
                return action

            def addSeparator(self) -> None:
                pass

            def exec(self, _pos):
                return self.actions[chosen_index[0]]

        try:
            dialog._errors = [(failed, "network")]
            dialog._completed = [completed]
            dialog._running = True
            panel = self.widget.transfer_activity
            panel.attach_controller(dialog)
            panel.failed_list.topLevelItem(0).setSelected(True)
            with patch("hpc_gui.ui.widgets.ftp_widget.QMenu", FakeMenu):
                panel._show_transfer_menu(panel.failed_list, QPoint(0, 0), "failed")
            self.assertEqual(dialog._errors, [])
            self.assertEqual(dialog._pending, [failed])

            chosen_index[0] = 1
            with patch("hpc_gui.ui.widgets.ftp_widget.QMenu", FakeMenu):
                panel._show_transfer_menu(
                    panel.completed_list,
                    QPoint(0, 0),
                    "completed",
                )
            self.assertEqual(dialog._completed, [])
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.concurrency
    def test_transfer_activity_keeps_overlapping_controllers_visible(self) -> None:
        first_item = TransferItem("download", "/remote/a", "a")
        second_item = TransferItem("download", "/remote/b", "b")
        first = TransferDialog(
            title="First",
            items=[first_item],
            run_item=lambda _item, _progress=None: None,
        )
        second = TransferDialog(
            title="Second",
            items=[second_item],
            run_item=lambda _item, _progress=None: None,
        )
        try:
            panel = self.widget.transfer_activity
            panel.attach_controller(first)
            panel.attach_controller(second)
            self.assertEqual(panel.queue_list.topLevelItemCount(), 2)

            first.transferStatsChanged.emit("first still transferring")
            self.assertEqual(panel.status_label.text(), "first still transferring")

            with (
                patch.object(first, "cancel_all") as cancel_first,
                patch.object(second, "cancel_all") as cancel_second,
            ):
                panel._call_controller("cancel_all")
            cancel_first.assert_called_once_with()
            cancel_second.assert_called_once_with()

            first._pending = []
            first._completed = [first_item]
            first.finished.emit(0)
            self.assertIs(panel._controller, second)
            self.assertEqual(panel.queue_list.topLevelItemCount(), 1)
            self.assertEqual(panel.completed_list.topLevelItemCount(), 1)
            self.assertTrue(panel.btn_cancel.isEnabled())

            second.finished.emit(0)
            self.assertIsNone(panel._controller)
            self.assertFalse(panel.btn_stop.isEnabled())
            self.assertFalse(panel.btn_cancel.isEnabled())
            self.assertFalse(panel.btn_clear_pending.isEnabled())
        finally:
            first.deleteLater()
            second.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_clean_accept_keeps_one_clearable_completed_history_row(self) -> None:
        completed = TransferItem("download", "/remote/done.txt", "done.txt")
        dialog = TransferDialog(
            title="Download",
            items=[completed],
            run_item=lambda _item, _progress=None: None,
        )
        dialog._pending = []
        dialog._completed = [completed]

        class FakeAction:
            def __init__(self, text: str) -> None:
                self.text = text
                self.enabled = True

            def setEnabled(self, enabled: bool) -> None:
                self.enabled = enabled

            def isEnabled(self) -> bool:
                return self.enabled

        class FakeMenu:
            def __init__(self, _parent=None) -> None:
                self.actions = []

            def addAction(self, text: str):
                action = FakeAction(text)
                self.actions.append(action)
                return action

            def addSeparator(self) -> None:
                pass

            def exec(self, _pos):
                return self.actions[1]

        try:
            panel = self.widget.transfer_activity
            panel.attach_controller(dialog)
            dialog.finished.connect(
                lambda _result: panel.record("completed", [completed], "Download")
            )

            dialog.accept()

            self.assertIsNone(panel._controller)
            self.assertEqual(panel.completed_list.topLevelItemCount(), 1)
            with patch("hpc_gui.ui.widgets.ftp_widget.QMenu", FakeMenu):
                panel._show_transfer_menu(
                    panel.completed_list,
                    QPoint(0, 0),
                    "completed",
                )
            self.assertEqual(panel.completed_list.topLevelItemCount(), 0)
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_activity_renders_active_progress_child_row(self) -> None:
        item = TransferItem("upload", "local.bin", "/remote/local.bin")
        dialog = TransferDialog(
            title="Upload",
            items=[item],
            run_item=lambda _item, _progress=None: None,
        )
        try:
            dialog._active_item = item
            dialog._pending = []
            self.widget.transfer_activity.record("controller", [dialog], "Upload")
            dialog.transferStatsChanged.emit("00:00:05 elapsed    00:11:19 left    1.3%")

            row = self.widget.transfer_activity.queue_list.topLevelItem(0)
            self.assertEqual(row.text(6), "Transferring")
            self.assertEqual(row.childCount(), 1)
            self.assertIn("1.3%", row.child(0).text(2))
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_activity_shows_progress_bar_percentage(self) -> None:
        item = TransferItem("download", "/remote/a.bin", "a.bin")
        dialog = TransferDialog(
            title="Download",
            items=[item],
            run_item=lambda _item, _progress=None: None,
        )
        try:
            dialog._active_item = item
            dialog._pending = []
            self.widget.transfer_activity.record("controller", [dialog], "Download")

            dialog.transferProgressChanged.emit(item, 25, 100)

            row = self.widget.transfer_activity.queue_list.topLevelItem(0)
            bar = self.widget.transfer_activity.queue_list.itemWidget(row, 4)
            self.assertIsNotNone(bar)
            self.assertEqual(bar.value(), 25)
            self.assertEqual(bar.text(), "25%")
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_progress_updates_use_direct_item_id_row_lookup(self) -> None:
        item = TransferItem("download", "/remote/a.bin", "a.bin")
        dialog = TransferDialog(
            title="Download",
            items=[item],
            run_item=lambda _item, _progress=None: None,
        )
        try:
            dialog._active_item = item
            dialog._pending = []
            panel = self.widget.transfer_activity
            panel.record("controller", [dialog], "Download")

            self.assertIn(id(item), panel._row_by_item_id)
            self.assertIn(id(item), panel._progress_bar_by_item_id)
            registered_bar = panel._progress_bar_by_item_id[id(item)]
            self.assertIsNotNone(registered_bar)

            dialog.transferProgressChanged.emit(item, 30, 100)

            row = panel._row_by_item_id[id(item)]
            bar = panel._progress_bar_by_item_id[id(item)]
            self.assertEqual(bar.value(), 30)
            self.assertEqual(
                panel.queue_list.itemWidget(row, panel._PROGRESS_COLUMN),
                bar,
            )

            dialog.transferListsChanged.emit([], [], [])
            self.assertIn(id(item), panel._row_by_item_id)
            self.assertEqual(panel._progress_bar_by_item_id[id(item)].value(), 30)
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_activity_hides_local_housekeeping_rows(self) -> None:
        items = [
            TransferItem("mkdir_local", "", r"D:\target\folder"),
            TransferItem("download", "/remote/folder/a.txt", r"D:\target\folder\a.txt"),
            TransferItem("delete_local", "", r"D:\target\old.txt"),
        ]

        self.widget.transfer_activity.record("queued", items, "Download")

        self.assertEqual(self.widget.transfer_activity.queue_list.topLevelItemCount(), 1)
        row = self.widget.transfer_activity.queue_list.topLevelItem(0)
        self.assertEqual(row.text(1), "<--")
        self.assertEqual(row.text(2), "/remote/folder/a.txt")

    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.concurrency
    def test_remote_delete_uses_modeless_worker_plan_without_gui_probe(self) -> None:
        class SlowDeleteFiles:
            supports_parallel_transfers = False

            def __init__(self) -> None:
                self.started = threading.Event()
                self.calls: list[tuple[str, bool]] = []
                self.thread_id = None

            def remove(self, path: str, recursive: bool = False) -> None:
                self.thread_id = threading.get_ident()
                self.calls.append((path, recursive))
                self.started.set()
                time.sleep(0.05)

            def is_dir(self, _path: str) -> bool:
                raise AssertionError("directory metadata should avoid GUI type probes")

        files = SlowDeleteFiles()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        panel.current_dir = "/remote"
        panel._show_transfer_dialog = False
        paths = ["/remote/file.txt", "/remote/folder"]
        started_at = time.monotonic()
        with patch(
            "hpc_gui.ui.widgets.remote_dir_panel.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.assertTrue(panel._delete_paths(paths, [(paths[0], False), (paths[1], True)]))
        self.assertLess(time.monotonic() - started_at, 0.2)
        self.assertTrue(files.started.wait(1))
        self.assertNotEqual(files.thread_id, threading.get_ident())
        self.assertEqual(files.calls[0], ("/remote/file.txt", False))
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and len(files.calls) < 2:
            QApplication.processEvents()
            time.sleep(0.01)
        self.assertEqual(files.calls, [("/remote/file.txt", False), ("/remote/folder", True)])

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_activity_renders_multiple_active_transfers(self) -> None:
        items = [
            TransferItem("download", "/remote/a.bin", "a.bin"),
            TransferItem("download", "/remote/b.bin", "b.bin"),
        ]
        dialog = TransferDialog(
            title="Download",
            items=items,
            run_item=lambda _item, _progress=None: None,
            parallel_limit=2,
        )
        try:
            dialog._active_items = list(items)
            dialog._pending = []
            self.widget.transfer_activity.record("controller", [dialog], "Download")
            dialog.transferListsChanged.emit([], [], [])

            self.assertEqual(self.widget.transfer_activity.queue_list.topLevelItemCount(), 2)
            self.assertEqual(
                [
                    self.widget.transfer_activity.queue_list.topLevelItem(index).text(5)
                    for index in range(2)
                ],
                ["Normal", "Normal"],
            )
            self.assertEqual(
                [
                    self.widget.transfer_activity.queue_list.topLevelItem(index).text(6)
                    for index in range(2)
                ],
                ["Transferring", "Transferring"],
            )
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_activity_reuses_unaffected_rows_on_status_transition(self) -> None:
        items = [
            TransferItem("download", "/remote/a.bin", "a.bin"),
            TransferItem("download", "/remote/b.bin", "b.bin"),
            TransferItem("download", "/remote/c.bin", "c.bin"),
        ]
        dialog = TransferDialog(
            title="Download",
            items=items,
            run_item=lambda _item, _progress=None: None,
            parallel_limit=1,
        )
        try:
            panel = self.widget.transfer_activity
            panel.attach_controller(dialog)
            before = [
                panel.queue_list.topLevelItem(index)
                for index in range(panel.queue_list.topLevelItemCount())
            ]
            self.assertEqual(
                [row.text(6) for row in before],
                ["Queued", "Queued", "Queued"],
            )

            dialog._active_items = [items[0]]
            dialog._active_item = items[0]
            dialog._pending = items[1:]
            dialog.transferListsChanged.emit([], [], [])

            self.assertEqual(panel.queue_list.topLevelItemCount(), 3)
            self.assertEqual(
                [panel.queue_list.topLevelItem(index).text(6) for index in range(3)],
                ["Transferring", "Queued", "Queued"],
            )
            self.assertIs(
                panel.queue_list.topLevelItem(0),
                before[0],
            )
            self.assertIs(
                panel.queue_list.topLevelItem(1),
                before[1],
            )
            self.assertIs(
                panel.queue_list.topLevelItem(2),
                before[2],
            )
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_activity_transition_keeps_bounded_cap_and_remaining(self) -> None:
        items = [
            TransferItem("download", f"/remote/{index}.bin", f"{index}.bin") for index in range(5)
        ]
        dialog = TransferDialog(
            title="Download",
            items=items,
            run_item=lambda _item, _progress=None: None,
            parallel_limit=1,
        )
        try:
            panel = self.widget.transfer_activity
            with patch.object(panel, "_MAX_VISIBLE_TRANSFER_ROWS", 3):
                panel.attach_controller(dialog)
                self.assertEqual(panel.queue_list.topLevelItemCount(), 4)
                self.assertEqual(
                    panel.queue_list.topLevelItem(3).text(2),
                    "Remaining: 2",
                )
                visible_before = [panel.queue_list.topLevelItem(index) for index in range(3)]

                dialog._active_items = [items[0]]
                dialog._active_item = items[0]
                dialog._pending = items[1:]
                dialog.transferListsChanged.emit([], [], [])

            self.assertEqual(panel.queue_list.topLevelItemCount(), 4)
            self.assertEqual(
                [panel.queue_list.topLevelItem(index).text(6) for index in range(3)],
                ["Transferring", "Queued", "Queued"],
            )
            self.assertEqual(panel.queue_list.topLevelItem(3).text(2), "Remaining: 2")
            self.assertIs(panel.queue_list.topLevelItem(0), visible_before[0])
            self.assertIs(panel.queue_list.topLevelItem(1), visible_before[1])
            self.assertIs(panel.queue_list.topLevelItem(2), visible_before[2])
        finally:
            dialog.deleteLater()
