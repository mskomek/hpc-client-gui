from __future__ import annotations

from support.ftp_widget_test_support import (
    FtpWidgetTestCase,
    QPoint,
    TransferDialog,
    TransferItem,
    patch,
    pytest,
)

class FtpWidgetTests(FtpWidgetTestCase):
    @pytest.mark.gui
    @pytest.mark.qt
    def test_bottom_transfer_activity_tabs_are_visible(self) -> None:
        tabs = self.widget.transfer_activity.tabs
        self.assertEqual(tabs.tabPosition(), tabs.TabPosition.South)
        self.assertEqual(
            [tabs.tabText(index) for index in range(tabs.count())],
            ["Queued files (0)", "Failed transfers (0)", "Successful transfers (0)"],
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
            TransferItem("download", f"/remote/{index}.bin", f"{index}.bin")
            for index in range(5)
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
                visible_before = [
                    panel.queue_list.topLevelItem(index) for index in range(3)
                ]

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
