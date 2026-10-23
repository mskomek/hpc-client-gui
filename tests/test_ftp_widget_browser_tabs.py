"""Focused FTP widget tests for browser tabs behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from PySide6.QtCore import QPoint, Qt
from hpc_gui.services.files_mock import MockFilesBackend
from ftp_widget_test_support import FtpWidgetTestCase


class FtpWidgetBrowserTabsTests(FtpWidgetTestCase):
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

        with (
            patch.object(
                view,
                "itemAt",
                return_value=folder,
            ),
            patch.object(
                panel,
                "open_directory_in_new_tab",
                return_value=True,
            ) as open_tab,
        ):
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

            with (
                patch.object(
                    local.tree,
                    "itemAt",
                    return_value=item,
                ),
                patch.object(
                    local,
                    "open_directory_in_new_tab",
                    return_value=True,
                ) as open_tab,
            ):
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
