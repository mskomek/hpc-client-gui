"""Focused FTP widget tests for clipboard behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import patch
import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication
from hpc_gui.services.files_mock import MockFilesBackend
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel
from ftp_widget_test_support import FtpWidgetTestCase, _Files


class FtpWidgetClipboardTests(FtpWidgetTestCase):
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_jobs_files_context_menu_restores_output_follow_actions(self) -> None:
        class FakeAction:
            def __init__(self, text: str) -> None:
                self.text = text
                self.enabled = True

            def setEnabled(self, enabled: bool) -> None:
                self.enabled = enabled

        class FakeMenu:
            instances: list["FakeMenu"] = []
            choose_text = "Follow in Output 2"

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
                    if action is not None and action.text == self.choose_text:
                        return action
                return None

        files = _Files()
        files.remote["/remote/out.log"] = b"out"
        panel = RemoteDirPanel()
        seen: list[tuple[int, str]] = []
        assigned: list[tuple[str, int, str]] = []
        try:
            panel.enable_output_menu = True
            panel.set_output_target_provider(lambda: [("window:1", "Follow window 1")])
            panel.open_in_slot.connect(lambda slot, path: seen.append((slot, path)))
            panel.open_in_existing_follower.connect(
                lambda target, slot, path: assigned.append((target, slot, path))
            )
            panel.set_session({"connected": True, "files": files})
            panel.set_dir("/remote")
            view = panel.views["all"]
            for index in range(view.topLevelItemCount()):
                item = view.topLevelItem(index)
                if item.text(0) == "out.log":
                    item.setSelected(True)
                    break

            with patch("hpc_gui.ui.widgets.remote_dir_panel.QMenu", FakeMenu):
                panel._on_context_menu(view, QPoint(0, 0))
                FakeMenu.choose_text = "Assign to Follow window 1 Output 2"
                panel._on_context_menu(view, QPoint(0, 0))

            labels = [
                action.text for action in FakeMenu.instances[-1].actions if action is not None
            ]
            self.assertIn("Follow in Output 1", labels)
            self.assertIn("Follow in Output 2", labels)
            self.assertIn("Follow file in new window", labels)
            self.assertIn("Follow in Output 1 in new window", labels)
            self.assertIn("Follow in Output 2 in new window", labels)
            self.assertIn("Follow in Output 1 in new tab", labels)
            self.assertIn("Follow in Output 2 in new tab", labels)
            self.assertIn("Assign to Follow window 1 Output 1", labels)
            self.assertIn("Assign to Follow window 1 Output 2", labels)
            self.assertEqual(seen, [(1, "/remote/out.log")])
            self.assertEqual(
                assigned,
                [("window:1", 1, "/remote/out.log")],
            )
        finally:
            FakeMenu.choose_text = "Follow in Output 2"
            panel.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_remote_ctrl_c_and_ctrl_x_store_selected_paths(self) -> None:
        from hpc_gui.services.file_clipboard import get_file_clipboard

        files = _Files()
        files.remote["/remote/out.txt"] = b"out"
        panel = RemoteDirPanel()
        clipboard = get_file_clipboard()
        try:
            panel.set_session({"connected": True, "files": files})
            panel.set_dir("/remote")
            view = panel.views["all"]
            for index in range(view.topLevelItemCount()):
                item = view.topLevelItem(index)
                if item.text(0) == "out.txt":
                    item.setSelected(True)
                    break

            copy_event = QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key.Key_C,
                Qt.KeyboardModifier.ControlModifier,
            )
            QApplication.sendEvent(view, copy_event)
            clip = clipboard.get()
            self.assertIsNotNone(clip)
            self.assertEqual(clip.op, "copy")
            self.assertEqual(clip.paths, ["/remote/out.txt"])

            cut_event = QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key.Key_X,
                Qt.KeyboardModifier.ControlModifier,
            )
            QApplication.sendEvent(view, cut_event)
            clip = clipboard.get()
            self.assertIsNotNone(clip)
            self.assertEqual(clip.op, "move")
            self.assertEqual(clip.paths, ["/remote/out.txt"])
        finally:
            clipboard.clear()
            panel.deleteLater()

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
                side_effect=lambda plan, title, after_finished=None, **kwargs: (
                    self._run_plan_synchronously(
                        panel,
                        plan,
                        title,
                        after_finished,
                        **kwargs,
                    )
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
    def test_local_ctrl_v_downloads_remote_clipboard_to_current_local_dir(self) -> None:
        from hpc_gui.services.file_clipboard import get_file_clipboard

        clipboard = get_file_clipboard()
        try:
            clipboard.set("copy", ["/remote/out.txt"])
            self.widget.session = {"connected": True}
            with patch.object(
                self.widget.panel_scratch,
                "_apply_remote_download_incremental",
                return_value=True,
            ) as download:
                paste_event = QKeyEvent(
                    QEvent.Type.KeyPress,
                    Qt.Key.Key_V,
                    Qt.KeyboardModifier.ControlModifier,
                )
                QApplication.sendEvent(self.widget.local_panel.tree, paste_event)
                self.app.processEvents()
            download.assert_called_once_with(
                ["/remote/out.txt"],
                self.widget.local_panel.current_dir,
            )
        finally:
            clipboard.clear()
