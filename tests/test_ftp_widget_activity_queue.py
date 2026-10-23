"""Focused FTP widget tests for activity queue behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication
from hpc_gui.ui.dialogs.transfer_dialog import TransferDialog, TransferItem
from hpc_gui.core.i18n import load_language
from ftp_widget_test_support import FtpWidgetTestCase


class FtpWidgetActivityQueueTests(FtpWidgetTestCase):
    @pytest.mark.gui
    @pytest.mark.qt
    def test_bottom_transfer_activity_tabs_are_visible(self) -> None:
        self.assertFalse(hasattr(self.widget, "btn_upload"))
        self.assertFalse(hasattr(self.widget, "btn_download"))
        tabs = self.widget.transfer_activity.tabs
        self.assertEqual(tabs.tabPosition(), tabs.TabPosition.South)
        self.assertEqual(
            [tabs.tabText(index) for index in range(tabs.count())],
            ["Queue (0)", "Failed (0)", "Completed (0)"],
        )
        self.assertEqual(
            [
                self.widget.transfer_activity.queue_list.headerItem().text(index)
                for index in range(self.widget.transfer_activity.queue_list.columnCount())
            ],
            [
                "Server/Local file",
                "Direction",
                "Remote file",
                "Size",
                "Progress",
                "Priority",
                "Status",
            ],
        )

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_activity_records_queue_failed_and_completed(self) -> None:
        item = SimpleNamespace(op="upload", src="a.txt", dst="/remote/a.txt")

        self.widget.transfer_activity.record("queued", [item], "Upload")
        self.assertEqual(self.widget.transfer_activity.queue_list.topLevelItemCount(), 1)
        self.assertEqual(
            self.widget.transfer_activity.queue_list.topLevelItem(0).text(1),
            "-->",
        )

        self.widget.transfer_activity.record("failed", [item], "Upload")
        self.assertEqual(self.widget.transfer_activity.failed_list.topLevelItemCount(), 1)

        self.widget.transfer_activity.record("completed", [item], "Upload")
        self.assertEqual(self.widget.transfer_activity.completed_list.topLevelItemCount(), 1)

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_activity_attaches_controller_without_popup(self) -> None:
        dialog = TransferDialog(
            title="Download",
            items=[TransferItem("download", "/remote/a.txt", "a.txt")],
            run_item=lambda _item, _progress=None: None,
        )
        try:
            self.widget.transfer_activity.record("controller", [dialog], "Download")
            self.assertTrue(self.widget.transfer_activity.btn_cancel.isEnabled())
            dialog.transferStatsChanged.emit("speed 1 KB/s remaining 0:10")
            self.assertEqual(
                self.widget.transfer_activity.status_label.text(),
                "speed 1 KB/s remaining 0:10",
            )
            dialog.transferListsChanged.emit(
                [TransferItem("download", "/remote/a.txt", "a.txt")],
                [],
                [],
            )
            self.assertEqual(self.widget.transfer_activity.queue_list.topLevelItemCount(), 1)
            with patch.object(dialog, "clear_pending") as clear_pending:
                self.widget.transfer_activity.btn_clear_pending.click()
            clear_pending.assert_called_once()
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_activity_buttons_route_to_live_controller(self) -> None:
        dialog = TransferDialog(
            title="Download",
            items=[TransferItem("download", "/remote/a.txt", "a.txt")],
            run_item=lambda _item, _progress=None: None,
        )
        try:
            dialog._running = True
            self.widget.transfer_activity.attach_controller(dialog)
            with patch.object(dialog, "cancel_all") as cancel:
                self.widget.transfer_activity.btn_stop.click()
                self.widget.transfer_activity.btn_cancel.click()
            with patch.object(dialog, "clear_pending") as clear:
                self.widget.transfer_activity.btn_clear_pending.click()
            self.assertEqual(cancel.call_count, 2)
            clear.assert_called_once()
        finally:
            dialog.deleteLater()

    @pytest.mark.integration
    @pytest.mark.concurrency
    def test_transfer_dialog_process_queue_starts_only_when_no_worker_is_active(self) -> None:
        dialog = TransferDialog(
            title="Download",
            items=[TransferItem("download", "/remote/a.txt", "a.txt")],
            run_item=lambda _item, _progress=None: None,
        )
        try:
            dialog._running = True
            with patch.object(dialog, "start") as start:
                self.assertFalse(dialog.process_queue())
            start.assert_not_called()

            dialog._running = False
            dialog._active_items = []
            dialog._active_item = None
            dialog._stopped = True
            dialog._cancelled = True
            with patch.object(dialog, "start") as start:
                self.assertTrue(dialog.process_queue())
            start.assert_called_once()
            self.assertFalse(dialog._stopped)
            self.assertFalse(dialog._cancelled)
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_activity_process_queue_context_routes_to_controller(self) -> None:
        dialog = TransferDialog(
            title="Download",
            items=[TransferItem("download", "/remote/a.txt", "a.txt")],
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

            def setCheckable(self, _checked: bool) -> None:
                pass

            def setChecked(self, _checked: bool) -> None:
                pass

        class FakeMenu:
            def __init__(self, _parent=None) -> None:
                self.actions = []

            def addAction(self, text: str):
                action = FakeAction(text)
                self.actions.append(action)
                return action

            def addSeparator(self) -> None:
                pass

            def addMenu(self, _text: str):
                return self

            def exec(self, _pos):
                return self.actions[0]

        try:
            panel = self.widget.transfer_activity
            panel.attach_controller(dialog)
            with (
                patch.object(dialog, "process_queue") as process,
                patch(
                    "hpc_gui.ui.widgets.ftp_widget.QMenu",
                    FakeMenu,
                ),
            ):
                panel._show_queue_menu(QPoint(0, 0))
            process.assert_called_once()
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_activity_queue_context_removes_only_selected_row(self) -> None:
        items = [
            TransferItem("download", f"/remote/{name}.txt", f"{name}.txt")
            for name in ("a", "b", "c")
        ]
        dialog = TransferDialog(
            title="Download",
            items=items,
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

            def setCheckable(self, _checked: bool) -> None:
                pass

            def setChecked(self, _checked: bool) -> None:
                pass

        class FakeMenu:
            def __init__(self, _parent=None) -> None:
                self.actions = []

            def addAction(self, text: str):
                action = FakeAction(text)
                self.actions.append(action)
                return action

            def addSeparator(self) -> None:
                pass

            def addMenu(self, _text: str):
                return self

            def exec(self, _pos):
                return self.actions[2]

        try:
            panel = self.widget.transfer_activity
            panel.attach_controller(dialog)
            panel.queue_list.topLevelItem(1).setSelected(True)
            with patch("hpc_gui.ui.widgets.ftp_widget.QMenu", FakeMenu):
                panel._show_queue_menu(QPoint(0, 0))

            self.assertEqual(dialog._pending, [items[0], items[2]])
            self.assertEqual(panel.queue_list.topLevelItemCount(), 2)
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_queue_menu_matches_filezilla_structure(self) -> None:
        load_language("en")
        dialog = TransferDialog(
            title="Download",
            items=[TransferItem("download", "/remote/a.txt", "a.txt")],
            run_item=lambda _item, _progress=None: None,
        )

        class FakeAction:
            def __init__(self, text: str) -> None:
                self.text = text
                self.enabled = True
                self.tooltip = ""

            def setEnabled(self, enabled: bool) -> None:
                self.enabled = enabled

            def isEnabled(self) -> bool:
                return self.enabled

            def setToolTip(self, tooltip: str) -> None:
                self.tooltip = tooltip

            def setCheckable(self, _value: bool) -> None:
                pass

            def setChecked(self, _value: bool) -> None:
                pass

        class FakeMenu:
            instance = None

            def __init__(self, _parent=None, text: str = "") -> None:
                self.text = text
                self.entries = []
                if FakeMenu.instance is None:
                    FakeMenu.instance = self

            def addAction(self, text: str):
                action = FakeAction(text)
                self.entries.append(("action", action))
                return action

            def addSeparator(self) -> None:
                self.entries.append(("separator", None))

            def addMenu(self, text: str):
                submenu = FakeMenu(text=text)
                self.entries.append(("menu", submenu))
                return submenu

            def exec(self, _pos):
                return None

        try:
            panel = self.widget.transfer_activity
            panel.attach_controller(dialog)
            with patch("hpc_gui.ui.widgets.ftp_widget.QMenu", FakeMenu):
                panel._show_queue_menu(QPoint(0, 0))
            root = FakeMenu.instance
            self.assertEqual(
                [kind if kind == "separator" else value.text for kind, value in root.entries],
                [
                    "Process Queue",
                    "Stop and remove all",
                    "separator",
                    "Remove selected",
                    "Default file exists action...",
                    "Set Priority",
                    "Action after queue completion",
                    "Export...",
                ],
            )
            self.assertEqual(
                [action.text for kind, action in root.entries[5][1].entries if kind == "action"],
                ["Highest", "High", "Normal", "Low", "Lowest"],
            )
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.concurrency
    def test_stop_button_cancels_immediately_and_clears_paused_queue(self) -> None:
        items = [
            TransferItem("download", "/remote/a.txt", "a.txt"),
            TransferItem("download", "/remote/b.txt", "b.txt"),
        ]
        dialog = TransferDialog(
            title="Download",
            items=items,
            run_item=lambda _item, _progress=None: None,
        )
        try:
            panel = self.widget.transfer_activity
            panel.attach_controller(dialog)
            self.assertTrue(panel.btn_stop.isEnabled())
            panel.btn_stop.click()
            self.assertTrue(dialog._cancelled)
            self.assertEqual(dialog._pending, [])
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_priority_reorders_pending_execution_and_priority_column(self) -> None:
        items = [
            TransferItem("download", "/remote/low", "low"),
            TransferItem("download", "/remote/normal", "normal"),
            TransferItem("download", "/remote/high", "high"),
        ]
        started: list[str] = []
        dialog = TransferDialog(
            title="Download",
            items=items,
            run_item=lambda item, _progress=None: started.append(item.src),
            parallel_limit=1,
        )
        try:
            self.assertEqual(dialog.set_pending_priority([items[0]], "Lowest"), 1)
            self.assertEqual(dialog.set_pending_priority([items[2]], "Highest"), 1)
            panel = self.widget.transfer_activity
            panel.attach_controller(dialog)
            self.assertEqual(panel.queue_list.topLevelItem(0).text(5), "Highest")
            dialog.start()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not dialog.finished_cleanly():
                QApplication.processEvents()
                time.sleep(0.01)
            self.assertTrue(dialog.finished_cleanly())
            self.assertEqual(started, ["/remote/high", "/remote/normal", "/remote/low"])
        finally:
            dialog.cancel_all()
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_completion_action_persists_and_never_runs_system_action(self) -> None:
        panel = self.widget.transfer_activity
        with (
            patch(
                "hpc_gui.ui.widgets.ftp_widget.set_transfer_completion_action",
                return_value="play_sound",
            ) as save,
            patch("hpc_gui.ui.widgets.ftp_widget.QApplication.beep") as beep,
        ):
            panel._set_completion_action("play_sound")
        save.assert_called_once_with("play_sound")
        beep.assert_called_once()
        self.assertIn("play_sound", panel.status_label.text())

        with patch(
            "hpc_gui.ui.widgets.ftp_widget.set_transfer_completion_action",
            return_value="shutdown_once",
        ) as save:
            panel._set_completion_action("shutdown_once")
        save.assert_called_once_with("shutdown_once")
        self.assertIn("not executed", panel.status_label.text())
