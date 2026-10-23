"""Focused FTP widget tests for remote panel behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import stat
from unittest.mock import patch
import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QKeyEvent
from hpc_gui.services.files_mock import MockFilesBackend
from hpc_gui.ui.widgets.remote_dir_panel import (
    REMOTE_CONTEXT_MENU_LABELS,
    RemoteDirPanel,
    _PermissionsDialog,
)
from ftp_widget_test_support import FtpWidgetTestCase, _CountingFiles, _Files


class FtpWidgetRemotePanelTests(FtpWidgetTestCase):
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_context_menu_runs_shell_script_action(self) -> None:
        class FakeAction:
            def __init__(self, text: str) -> None:
                self.text = text
                self.enabled = True

            def setEnabled(self, enabled: bool) -> None:
                self.enabled = enabled

        class FakeMenu:
            instances: list["FakeMenu"] = []

            def __init__(self, _parent=None) -> None:
                self.actions: list[FakeAction | None] = []
                FakeMenu.instances.append(self)

            def addAction(self, text: str) -> FakeAction:
                action = FakeAction(text)
                self.actions.append(action)
                return action

            def addSeparator(self) -> None:
                self.actions.append(None)

            def exec(self, _pos):
                for action in self.actions:
                    if action is not None and action.text == "Run in terminal":
                        return action
                return None

        files = _Files()
        files.remote["/remote/run.sh"] = b"#!/bin/bash\necho ok\n"
        panel = RemoteDirPanel()
        shell_runs: list[str] = []
        try:
            panel.run_shell_requested.connect(shell_runs.append)
            panel.set_session({"connected": True, "files": files})
            panel.set_dir("/remote")
            view = panel.views["all"]
            for index in range(view.topLevelItemCount()):
                item = view.topLevelItem(index)
                if item.text(0) == "run.sh":
                    item.setSelected(True)
                    break

            with patch("hpc_gui.ui.widgets.remote_dir_panel.QMenu", FakeMenu):
                panel._on_context_menu(view, QPoint(0, 0))

            labels = [
                action.text for action in FakeMenu.instances[-1].actions if action is not None
            ]
            self.assertIn("Run in terminal", labels)
            self.assertEqual(shell_runs, ["/remote/run.sh"])
        finally:
            panel.deleteLater()

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_context_menu_restores_clipboard_actions(self) -> None:
        from hpc_gui.services.file_clipboard import get_file_clipboard

        class FakeAction:
            def __init__(self, text: str) -> None:
                self.text = text
                self.enabled = True

            def setEnabled(self, enabled: bool) -> None:
                self.enabled = enabled

        class FakeMenu:
            instances: list["FakeMenu"] = []

            def __init__(self, _parent=None) -> None:
                self.actions: list[FakeAction | None] = []
                FakeMenu.instances.append(self)

            def addAction(self, text: str) -> FakeAction:
                action = FakeAction(text)
                self.actions.append(action)
                return action

            def addSeparator(self) -> None:
                self.actions.append(None)

            def exec(self, _pos):
                return None

        files = _Files()
        files.remote["/remote/out.txt"] = b"out"
        panel = RemoteDirPanel()
        clipboard = get_file_clipboard()
        try:
            clipboard.set("copy", ["/remote/old.txt"])
            panel.set_session({"connected": True, "files": files})
            panel.set_dir("/remote")
            view = panel.views["all"]
            for index in range(view.topLevelItemCount()):
                item = view.topLevelItem(index)
                if item.text(0) == "out.txt":
                    item.setSelected(True)
                    break

            with patch("hpc_gui.ui.widgets.remote_dir_panel.QMenu", FakeMenu):
                panel._on_context_menu(view, QPoint(0, 0))

            labels = [
                action.text for action in FakeMenu.instances[-1].actions if action is not None
            ]
            self.assertIn("Paste", labels)
            self.assertIn("Paste to local (download)", labels)
            self.assertIn("Copy", labels)
            self.assertIn("Move", labels)
        finally:
            clipboard.clear()
            panel.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_remote_panel_f2_uses_rename_action_for_single_selection(self) -> None:
        files = _Files()
        files.remote["/remote/old.txt"] = b"data"
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        panel.current_dir = "/remote"
        panel.refresh()
        item = None
        for index in range(panel.views["all"].topLevelItemCount()):
            candidate = panel.views["all"].topLevelItem(index)
            if candidate.text(0) == "old.txt":
                item = candidate
                break
        self.assertIsNotNone(item)
        item.setSelected(True)
        with patch(
            "hpc_gui.ui.widgets.remote_dir_panel.QInputDialog.getText",
            return_value=("new.txt", True),
        ):
            event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_F2, Qt.KeyboardModifier.NoModifier)
            self.assertTrue(panel.eventFilter(panel.views["all"], event))
        self.assertNotIn("/remote/old.txt", files.remote)
        self.assertIn("/remote/new.txt", files.remote)

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_remote_path_field_enter_navigates_and_backspace_goes_parent(self) -> None:
        files = _CountingFiles()
        panel = RemoteDirPanel()
        try:
            panel.set_session({"connected": True, "files": files})
            panel.set_dir("/remote")

            self.assertFalse(panel.path.isReadOnly())
            panel.path.setText("/remote/child")
            panel.path.returnPressed.emit()
            self.assertEqual(panel.current_dir, "/remote/child")
            self.assertEqual(panel.path.text(), "/remote/child")

            event = QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key.Key_Backspace,
                Qt.KeyboardModifier.NoModifier,
            )
            self.assertTrue(panel.eventFilter(panel.views["all"], event))
            self.assertEqual(panel.current_dir, "/remote")
            self.assertEqual(panel.path.text(), "/remote")
        finally:
            panel.deleteLater()

    @pytest.mark.contract
    def test_remote_context_menu_matches_requested_layout(self) -> None:
        self.assertEqual(
            REMOTE_CONTEXT_MENU_LABELS,
            [
                "Download",
                "Add files to queue",
                "View/Edit",
                "Open in new tab",
                "---",
                "Create directory",
                "Create directory and enter it",
                "Create new file",
                "Refresh",
                "---",
                "Delete",
                "Rename",
                "Copy URL(s) to clipboard",
                "File permissions...",
            ],
        )

    @pytest.mark.integration
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_remote_create_directory_and_enter(self) -> None:
        files = MockFilesBackend()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        panel.current_dir = "/arf/scratch/user"
        with patch(
            "hpc_gui.ui.widgets.remote_dir_panel.QInputDialog.getText",
            return_value=("new-job", True),
        ):
            self.assertTrue(panel.create_new_folder_and_enter())
        self.assertEqual(panel.current_dir, "/arf/scratch/user/new-job")
        self.assertTrue(files.is_dir("/arf/scratch/user/new-job"))

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

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_context_menu_changes_file_permissions(self) -> None:
        class FakeAction:
            def __init__(self, text: str) -> None:
                self.text = text
                self.enabled = True

            def setEnabled(self, enabled: bool) -> None:
                self.enabled = enabled

        class FakeMenu:
            instances: list["FakeMenu"] = []

            def __init__(self, _parent=None) -> None:
                self.actions: list[FakeAction | None] = []
                FakeMenu.instances.append(self)

            def addAction(self, text: str) -> FakeAction:
                action = FakeAction(text)
                self.actions.append(action)
                return action

            def addSeparator(self) -> None:
                self.actions.append(None)

            def exec(self, _pos):
                for action in self.actions:
                    if action is not None and action.text == "File permissions...":
                        self.selected_action = action
                        return action
                return None

        files = MockFilesBackend()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        panel.set_dir("/arf/scratch/user")
        view = panel.views["all"]
        for index in range(view.topLevelItemCount()):
            item = view.topLevelItem(index)
            if item.text(0) == "example.txt":
                item.setSelected(True)
                break

        class FakePermissionsDialog:
            def __init__(self, _parent, initial_mode, target_name=""):
                self.initial_mode = initial_mode
                self.target_name = target_name

            def exec(self):
                return _PermissionsDialog.DialogCode.Accepted

            def selected_mode(self):
                return 0o600

        with (
            patch("hpc_gui.ui.widgets.remote_dir_panel.QMenu", FakeMenu),
            patch(
                "hpc_gui.ui.widgets.remote_dir_panel._PermissionsDialog",
                FakePermissionsDialog,
            ),
        ):
            panel._on_context_menu(view, QPoint(0, 0))

        permission_action = getattr(FakeMenu.instances[-1], "selected_action")
        self.assertTrue(permission_action.enabled)
        entry = next(
            entry
            for entry in files.listdir_entries("/arf/scratch/user")
            if entry.name == "example.txt"
        )
        self.assertEqual(stat.S_IMODE(entry.mode), 0o600)

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_change_permissions_rejects_invalid_mode(self) -> None:
        files = MockFilesBackend()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        panel.set_dir("/arf/scratch/user")
        view = panel.views["all"]
        for index in range(view.topLevelItemCount()):
            item = view.topLevelItem(index)
            if item.text(0) == "example.txt":
                item.setSelected(True)
                break

        class FakePermissionsDialog:
            def __init__(self, _parent, _initial_mode, _target_name=""):
                pass

            def exec(self):
                return _PermissionsDialog.DialogCode.Accepted

            def selected_mode(self):
                return None

        with (
            patch(
                "hpc_gui.ui.widgets.remote_dir_panel._PermissionsDialog",
                FakePermissionsDialog,
            ),
            patch("hpc_gui.ui.widgets.remote_dir_panel.QMessageBox.warning") as warning,
        ):
            self.assertFalse(panel.change_permissions())

        warning.assert_called_once()
        entry = next(
            entry
            for entry in files.listdir_entries("/arf/scratch/user")
            if entry.name == "example.txt"
        )
        self.assertEqual(stat.S_IMODE(entry.mode), 0o644)

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_change_permissions_accepts_four_digit_octal_mode(self) -> None:
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

        class FakePermissionsDialog:
            def __init__(self, _parent, _initial_mode, _target_name=""):
                pass

            def exec(self):
                return _PermissionsDialog.DialogCode.Accepted

            def selected_mode(self):
                return 0o1755

        with patch(
            "hpc_gui.ui.widgets.remote_dir_panel._PermissionsDialog",
            FakePermissionsDialog,
        ):
            self.assertTrue(panel.change_permissions())

        entry = next(
            entry for entry in files.listdir_entries("/arf/scratch/user") if entry.name == "project"
        )
        self.assertEqual(stat.S_IMODE(entry.mode), 0o1755)

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_permissions_dialog_syncs_checkboxes_and_mode_field(self) -> None:
        dialog = _PermissionsDialog(self.widget, 0o640, "example.txt")
        try:
            self.assertEqual(dialog.windowTitle(), "Change file attributes")
            self.assertTrue(dialog._boxes[(0, 0)].isChecked())
            self.assertTrue(dialog._boxes[(1, 0)].isChecked())
            self.assertTrue(dialog._boxes[(0, 1)].isChecked())
            self.assertFalse(dialog._boxes[(2, 2)].isChecked())
            self.assertEqual(dialog.mode_edit.text(), "00640")

            dialog._boxes[(2, 2)].setChecked(True)
            self.assertEqual(dialog.mode_edit.text(), "00641")

            dialog._special_boxes[0o1000].setChecked(True)
            self.assertEqual(dialog.mode_edit.text(), "01641")

            dialog.mode_edit.setText("755")
            dialog._update_checks_from_code("755")
            self.assertTrue(dialog._boxes[(0, 0)].isChecked())
            self.assertTrue(dialog._boxes[(1, 0)].isChecked())
            self.assertTrue(dialog._boxes[(2, 0)].isChecked())
            self.assertTrue(dialog._boxes[(0, 1)].isChecked())
            self.assertFalse(dialog._boxes[(1, 1)].isChecked())
            self.assertTrue(dialog._boxes[(2, 2)].isChecked())
            self.assertEqual(dialog.selected_mode(), 0o755)

            dialog.mode_edit.setText("01755")
            dialog._update_checks_from_code("01755")
            self.assertTrue(dialog._special_boxes[0o1000].isChecked())
            self.assertEqual(dialog.selected_mode(), 0o1755)
        finally:
            dialog.deleteLater()
