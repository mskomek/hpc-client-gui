from __future__ import annotations

from support.ftp_widget_test_support import (
    FtpWidgetTestCase,
    MockFilesBackend,
    Path,
    QApplication,
    QEvent,
    QKeyEvent,
    QPoint,
    Qt,
    RemoteDirPanel,
    patch,
    pytest,
    tempfile,
)

class FtpWidgetTests(FtpWidgetTestCase):
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_remote_ctrl_c_then_ctrl_v_in_another_directory_tab_copies_file(self) -> None:
        from hpc_gui.services.file_clipboard import get_file_clipboard

        files = MockFilesBackend()
        source = "/arf/scratch/user/project/input.dat"
        destination = "/arf/scratch/user/project/nested"
        panel = RemoteDirPanel()
        clipboard = get_file_clipboard()
        try:
            panel.set_session({"connected": True, "files": files})
            panel.set_dir("/arf/scratch/user/project")
            source_view = panel.views["all"]
            for index in range(source_view.topLevelItemCount()):
                if source_view.topLevelItem(index).text(0) == "input.dat":
                    source_view.topLevelItem(index).setSelected(True)
                    break
            QApplication.sendEvent(
                source_view,
                QKeyEvent(
                    QEvent.Type.KeyPress,
                    Qt.Key.Key_C,
                    Qt.KeyboardModifier.ControlModifier,
                ),
            )
            self.assertEqual(clipboard.get().paths, [source])

            self.assertTrue(panel.open_directory_in_new_tab(destination))
            destination_view = panel.views["all"]
            with patch.object(
                panel,
                "_run_plan_with_progress",
                side_effect=lambda plan, title, after_finished=None, **kwargs: self._run_plan_synchronously(
                    panel,
                    plan,
                    title,
                    after_finished,
                    **kwargs,
                ),
            ):
                QApplication.sendEvent(
                    destination_view,
                    QKeyEvent(
                        QEvent.Type.KeyPress,
                        Qt.Key.Key_V,
                        Qt.KeyboardModifier.ControlModifier,
                    ),
                )
                self.app.processEvents()

            self.assertTrue(files.exists(destination + "/input.dat"))
            self.assertEqual(files._files[destination + "/input.dat"], b"1 2 3\n")
        finally:
            clipboard.clear()
            panel.deleteLater()
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_local_panel_has_parent_entry_not_selected_for_upload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            child = Path(tmp, "child")
            child.mkdir()
            local = self.widget.local_panel
            self.assertTrue(local.set_dir(str(child)))

            parent_item = local.tree.topLevelItem(0)
            self.assertEqual(parent_item.text(0), "..")
            parent_item.setSelected(True)
            self.assertEqual(local.selected_paths(), [])

            local._open_item(parent_item, 0)
            self.assertEqual(Path(local.current_dir), Path(tmp))
    @pytest.mark.integration
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_local_context_menu_opens_directory_in_new_tab(self) -> None:
        class FakeAction:
            def __init__(self, text: str) -> None:
                self.text = text
                self.enabled = True

            def setEnabled(self, enabled: bool) -> None:
                self.enabled = enabled

        class FakeMenu:
            def __init__(self, _parent=None) -> None:
                self.actions: list[FakeAction | None] = []

            def addAction(self, text: str) -> FakeAction:
                action = FakeAction(text)
                self.actions.append(action)
                return action

            def addSeparator(self) -> None:
                self.actions.append(None)

            def exec(self, _pos):
                for action in self.actions:
                    if action is not None and action.text == "Open in new tab":
                        return action
                return None

        with tempfile.TemporaryDirectory() as tmp:
            child = Path(tmp, "child")
            child.mkdir()
            local = self.widget.local_panel
            self.assertTrue(local.set_dir(tmp))
            target_item = None
            for index in range(local.tree.topLevelItemCount()):
                item = local.tree.topLevelItem(index)
                if item.text(0) == "child":
                    target_item = item
                    item.setSelected(True)
                    break
            self.assertIsNotNone(target_item)

            with patch("hpc_gui.ui.widgets.local_dir_panel.QMenu", FakeMenu):
                local._on_context_menu(local.tree.visualItemRect(target_item).center())

            self.assertEqual(local.tabs.count(), 2)
            self.assertEqual(Path(local.current_dir), child)
    @pytest.mark.integration
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_remote_context_menu_opens_directory_in_new_tab(self) -> None:
        class FakeAction:
            def __init__(self, text: str) -> None:
                self.text = text
                self.enabled = True

            def setEnabled(self, enabled: bool) -> None:
                self.enabled = enabled

        class FakeMenu:
            def __init__(self, _parent=None) -> None:
                self.actions: list[FakeAction | None] = []

            def addAction(self, text: str) -> FakeAction:
                action = FakeAction(text)
                self.actions.append(action)
                return action

            def addSeparator(self) -> None:
                self.actions.append(None)

            def exec(self, _pos):
                for action in self.actions:
                    if action is not None and action.text == "Open in new tab":
                        return action
                return None

        files = MockFilesBackend()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        panel.set_dir("/arf/scratch/user")
        view = panel.views["all"]
        for index in range(view.topLevelItemCount()):
            item = view.topLevelItem(index)
            if item.text(0) == "project":
                item.setSelected(True)
                break

        with patch("hpc_gui.ui.widgets.remote_dir_panel.QMenu", FakeMenu):
            panel._on_context_menu(view, QPoint(0, 0))

        self.assertEqual(panel.tabs.count(), 7)
        self.assertEqual(panel.directory_tabs.count(), 2)
        self.assertEqual(panel.current_dir, "/arf/scratch/user/project")
        opened = panel.views["all"]
        self.assertTrue(
            any(
                opened.topLevelItem(i).text(0) == "input.dat"
                for i in range(opened.topLevelItemCount())
            )
        )
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_remote_directory_tabs_sit_above_filter_tabs(self) -> None:
        files = MockFilesBackend()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        panel.set_dir("/arf/scratch/user")

        self.assertTrue(panel.open_directory_in_new_tab("/arf/scratch/user/project"))
        self.assertEqual(panel.tabs.count(), 7)
        self.assertEqual(panel.directory_tabs.count(), 2)
        self.assertEqual(panel.current_dir, "/arf/scratch/user/project")

        panel.tabs.setCurrentWidget(panel.views["folders"])
        self.assertEqual(panel.current_dir, "/arf/scratch/user/project")
        self.assertEqual(panel.path.text(), "/arf/scratch/user/project")

        panel.directory_tabs.setCurrentIndex(0)
        self.assertEqual(panel.current_dir, "/arf/scratch/user")
        self.assertTrue(
            any(
                panel.views["all"].topLevelItem(index).text(0) == "project"
                for index in range(panel.views["all"].topLevelItemCount())
            )
        )
    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_folder_middle_click_opens_new_directory_tab(self) -> None:
        class FakePosition:
            @staticmethod
            def toPoint() -> QPoint:
                return QPoint(1, 1)

        class FakeMiddleRelease:
            accepted = False

            @staticmethod
            def button():
                return Qt.MouseButton.MiddleButton

            @staticmethod
            def position() -> FakePosition:
                return FakePosition()

            def accept(self) -> None:
                self.accepted = True

        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": MockFilesBackend()}
        panel.set_dir("/arf/scratch/user")
        view = panel.views["all"]
        folder = next(
            view.topLevelItem(index)
            for index in range(view.topLevelItemCount())
            if view.topLevelItem(index).text(0) == "project"
        )
        event = FakeMiddleRelease()

        with patch.object(
            view,
            "itemAt",
            return_value=folder,
        ), patch.object(
            panel,
            "open_directory_in_new_tab",
            return_value=True,
        ) as open_tab:
            view.mouseReleaseEvent(event)

        open_tab.assert_called_once_with("/arf/scratch/user/project")
        self.assertTrue(event.accepted)
    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_middle_click_ignores_file_parent_and_blank_space(self) -> None:
        class FakePosition:
            @staticmethod
            def toPoint() -> QPoint:
                return QPoint(1, 1)

        class FakeMiddleRelease:
            accepted = False

            @staticmethod
            def button():
                return Qt.MouseButton.MiddleButton

            @staticmethod
            def position() -> FakePosition:
                return FakePosition()

            def accept(self) -> None:
                self.accepted = True

        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": MockFilesBackend()}
        panel.set_dir("/arf/scratch/user")
        view = panel.views["all"]
        parent_item = next(
            view.topLevelItem(index)
            for index in range(view.topLevelItemCount())
            if view.topLevelItem(index).text(0) == ".."
        )
        file_item = next(
            view.topLevelItem(index)
            for index in range(view.topLevelItemCount())
            if not bool(
                view.topLevelItem(index).data(
                    0,
                    Qt.ItemDataRole.UserRole + 1,
                )
            )
        )

        with patch.object(
            panel,
            "open_directory_in_new_tab",
            return_value=True,
        ) as open_tab:
            for clicked_item in (file_item, parent_item, None):
                event = FakeMiddleRelease()
                with patch.object(view, "itemAt", return_value=clicked_item):
                    view.mouseReleaseEvent(event)
                self.assertTrue(event.accepted)

        open_tab.assert_not_called()
    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_local_folder_middle_click_opens_new_directory_tab(self) -> None:
        class FakePosition:
            @staticmethod
            def toPoint() -> QPoint:
                return QPoint(1, 1)

        class FakeMiddleRelease:
            accepted = False

            @staticmethod
            def button():
                return Qt.MouseButton.MiddleButton

            @staticmethod
            def position() -> FakePosition:
                return FakePosition()

            def accept(self) -> None:
                self.accepted = True

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp, "project")
            folder.mkdir()
            local = self.widget.local_panel
            self.assertTrue(local.set_dir(tmp))
            item = next(
                local.tree.topLevelItem(index)
                for index in range(local.tree.topLevelItemCount())
                if local.tree.topLevelItem(index).text(0) == "project"
            )
            event = FakeMiddleRelease()

            with patch.object(
                local.tree,
                "itemAt",
                return_value=item,
            ), patch.object(
                local,
                "open_directory_in_new_tab",
                return_value=True,
            ) as open_tab:
                local.tree.mouseReleaseEvent(event)

            open_tab.assert_called_once_with(str(folder))
            self.assertTrue(event.accepted)
    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_local_middle_click_ignores_file_parent_and_blank_space(self) -> None:
        class FakePosition:
            @staticmethod
            def toPoint() -> QPoint:
                return QPoint(1, 1)

        class FakeMiddleRelease:
            accepted = False

            @staticmethod
            def button():
                return Qt.MouseButton.MiddleButton

            @staticmethod
            def position() -> FakePosition:
                return FakePosition()

            def accept(self) -> None:
                self.accepted = True

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp, "file.txt")).write_text("data", encoding="utf-8")
            local = self.widget.local_panel
            self.assertTrue(local.set_dir(tmp))
            parent_item = next(
                local.tree.topLevelItem(index)
                for index in range(local.tree.topLevelItemCount())
                if local.tree.topLevelItem(index).text(0) == ".."
            )
            file_item = next(
                local.tree.topLevelItem(index)
                for index in range(local.tree.topLevelItemCount())
                if not bool(
                    local.tree.topLevelItem(index).data(
                        0,
                        Qt.ItemDataRole.UserRole + 1,
                    )
                )
            )

            with patch.object(
                local,
                "open_directory_in_new_tab",
                return_value=True,
            ) as open_tab:
                for clicked_item in (file_item, parent_item, None):
                    event = FakeMiddleRelease()
                    with patch.object(local.tree, "itemAt", return_value=clicked_item):
                        local.tree.mouseReleaseEvent(event)
                    self.assertTrue(event.accepted)

            open_tab.assert_not_called()
