"""Focused FTP widget tests for local panel behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QMessageBox
from hpc_gui.ui.widgets.local_dir_panel import LOCAL_CONTEXT_MENU_LABELS
from ftp_widget_test_support import FtpWidgetTestCase


class FtpWidgetLocalPanelTests(FtpWidgetTestCase):
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

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_local_panel_f2_renames_single_selected_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp, "old.txt")
            src.write_text("data", encoding="utf-8")
            local = self.widget.local_panel
            self.assertTrue(local.set_dir(tmp))
            for index in range(local.tree.topLevelItemCount()):
                item = local.tree.topLevelItem(index)
                if item.text(0) == "old.txt":
                    item.setSelected(True)
                    break
            with patch(
                "hpc_gui.ui.widgets.local_dir_panel.QInputDialog.getText",
                return_value=("new.txt", True),
            ):
                event = QKeyEvent(
                    QEvent.Type.KeyPress, Qt.Key.Key_F2, Qt.KeyboardModifier.NoModifier
                )
                local.tree.keyPressEvent(event)
            self.assertFalse(src.exists())
            self.assertTrue(Path(tmp, "new.txt").exists())

    @pytest.mark.contract
    def test_local_context_menu_matches_requested_layout(self) -> None:
        self.assertEqual(
            LOCAL_CONTEXT_MENU_LABELS,
            [
                "Upload",
                "Add files to queue",
                "---",
                "Open",
                "Open with...",
                "Open in new tab",
                "Edit",
                "---",
                "Create directory",
                "Create directory and enter it",
                "Refresh",
                "---",
                "Delete",
                "Rename",
            ],
        )

    @unittest.skipUnless(sys.platform == "win32", "Windows Explorer integration")
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.windows
    def test_local_context_open_uses_file_explorer_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp, "old.txt")
            src.write_text("data", encoding="utf-8")
            local = self.widget.local_panel
            self.assertTrue(local.set_dir(tmp))
            for index in range(local.tree.topLevelItemCount()):
                item = local.tree.topLevelItem(index)
                if item.text(0) == "old.txt":
                    item.setSelected(True)
                    break
            with patch("hpc_gui.ui.widgets.local_dir_panel.subprocess.Popen") as popen:
                self.assertTrue(local.open_selected_in_file_explorer())
            popen.assert_called_once_with(["explorer", str(Path(tmp))])

    @pytest.mark.integration
    @pytest.mark.semantic
    def test_local_context_open_on_linux_invokes_file_manager(self) -> None:
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp, "old.txt")
            src.write_text("data", encoding="utf-8")
            local = self.widget.local_panel
            self.assertTrue(local.set_dir(tmp))
            for index in range(local.tree.topLevelItemCount()):
                item = local.tree.topLevelItem(index)
                if item.text(0) == "old.txt":
                    item.setSelected(True)
                    break

            # Patch only the os module the widget sees, so pathlib's flavour
            # (bound at import from the real os.name) is not disturbed.
            class _PosixOsStub:
                name = "posix"
                environ = {}

            with mock.patch("hpc_gui.ui.widgets.local_dir_panel.os", _PosixOsStub()):
                with mock.patch(
                    "hpc_gui.ui.widgets.local_dir_panel.QDesktopServices.openUrl"
                ) as open_url:
                    self.assertTrue(local.open_selected_in_file_explorer())
            open_url.assert_called_once()
            arg_url = open_url.call_args.args[0]
            self.assertEqual(
                arg_url.toLocalFile().replace("\\", "/").rstrip("/"),
                str(Path(tmp)).replace("\\", "/").rstrip("/"),
            )

    @pytest.mark.integration
    @pytest.mark.semantic
    def test_local_open_with_chooses_program_and_saves_association(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp, "job.slurm")
            src.write_text("echo ok", encoding="utf-8")
            program = Path(tmp, "editor.exe")
            program.write_text("", encoding="utf-8")
            local = self.widget.local_panel
            self.assertTrue(local.set_dir(tmp))
            for index in range(local.tree.topLevelItemCount()):
                item = local.tree.topLevelItem(index)
                if item.text(0) == "job.slurm":
                    item.setSelected(True)
                    break
            with (
                patch(
                    "hpc_gui.ui.widgets.local_dir_panel.get_file_association",
                    return_value="",
                ),
                patch(
                    "hpc_gui.ui.widgets.local_dir_panel.QFileDialog.getOpenFileName",
                    return_value=(str(program), ""),
                ),
                patch(
                    "hpc_gui.ui.widgets.local_dir_panel.QMessageBox.question",
                    return_value=QMessageBox.StandardButton.Yes,
                ),
                patch("hpc_gui.ui.widgets.local_dir_panel.set_file_association") as set_assoc,
                patch("hpc_gui.ui.widgets.local_dir_panel.subprocess.Popen") as popen,
            ):
                self.assertTrue(local.open_selected_with_program())

            set_assoc.assert_called_once_with(".slurm", str(program))
            popen.assert_called_once_with([str(program), str(src)])

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

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_local_create_directory_and_enter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            local = self.widget.local_panel
            self.assertTrue(local.set_dir(tmp))
            with patch(
                "hpc_gui.ui.widgets.local_dir_panel.QInputDialog.getText",
                return_value=("child", True),
            ):
                self.assertTrue(local.create_directory(enter=True))
            self.assertEqual(Path(local.current_dir), Path(tmp, "child"))
