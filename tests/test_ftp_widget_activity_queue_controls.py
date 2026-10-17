from __future__ import annotations

from support.ftp_widget_test_support import (
    FtpWidgetTestCase,
    QApplication,
    QPoint,
    SimpleNamespace,
    TransferDialog,
    TransferItem,
    load_language,
    patch,
    pytest,
    time,
)

class FtpWidgetTests(FtpWidgetTestCase):
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
            with patch.object(dialog, "process_queue") as process, patch(
                "hpc_gui.ui.widgets.ftp_widget.QMenu",
                FakeMenu,
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
                [
                    kind if kind == "separator" else value.text
                    for kind, value in root.entries
                ],
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
        with patch(
            "hpc_gui.ui.widgets.ftp_widget.set_transfer_completion_action",
            return_value="play_sound",
        ) as save, patch("hpc_gui.ui.widgets.ftp_widget.QApplication.beep") as beep:
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
