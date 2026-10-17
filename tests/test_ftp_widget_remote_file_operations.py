from __future__ import annotations

from support.ftp_widget_test_support import (
    FtpWidgetTestCase,
    MockFilesBackend,
    QApplication,
    QEvent,
    QKeyEvent,
    QMessageBox,
    QPoint,
    Qt,
    REMOTE_CONTEXT_MENU_LABELS,
    RemoteDirPanel,
    _CountingFiles,
    _Files,
    patch,
    pytest,
    tempfile,
    threading,
    time,
)

class FtpWidgetTests(FtpWidgetTestCase):
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
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.concurrency
    def test_remote_folder_download_returns_before_planning_finishes(self) -> None:
        files = _CountingFiles()
        panel = self.widget.panel_scratch
        session = {"connected": True, "files": files}
        self.widget.session = session
        panel.session = session
        self.widget.panel_scratch.current_dir = "/remote"

        with tempfile.TemporaryDirectory() as tmp, patch.object(
            self.widget,
            "_selected_remote_paths",
            return_value=["/remote"],
        ), patch.object(
            panel,
            "_apply_remote_download",
            return_value=True,
        ) as synchronous, patch.object(
            panel,
            "_run_plan_with_progress",
            return_value=True,
        ) as run_plan:
            self.widget.local_panel.current_dir = tmp

            self.assertTrue(self.widget.download_selected())
            self.assertTrue(panel._planning_jobs)
            run_plan.assert_not_called()
            synchronous.assert_not_called()

            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not run_plan.called:
                self.app.processEvents()
                time.sleep(0.01)

            self.assertTrue(run_plan.called)
            plan = run_plan.call_args.args[0]
            self.assertEqual(files.calls, ["/remote", "/remote/child"])
            self.assertEqual(
                [item.op for item in plan],
                [
                    "mkdir_local",
                    "mkdir_local",
                    "download",
                    "download",
                ],
            )
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
                action.text
                for action in FakeMenu.instances[-1].actions
                if action is not None
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
                action.text
                for action in FakeMenu.instances[-1].actions
                if action is not None
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
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_copy_move_refreshes_affected_cached_dirs_after_finish(self) -> None:
        files = _CountingFiles()
        source_panel = RemoteDirPanel()
        target_panel = self.widget.panel_scratch
        callbacks = []

        try:
            source_panel.session = {"connected": True, "files": files}
            target_panel.session = {"connected": True, "files": files}
            source_panel.set_dir("/remote")
            target_panel.set_dir("/remote/child")
            files.calls.clear()

            def fake_run(_plan, _title, after_finished=None):
                callbacks.append(after_finished)
                return True

            with patch.object(target_panel, "_run_plan_with_progress", side_effect=fake_run):
                self.assertTrue(
                    target_panel._apply_copy_move_with_conflicts(
                        "move",
                        ["/remote/root.txt"],
                        "/remote/child",
                    )
                )

            self.assertEqual(files.calls, [])
            self.assertEqual(len(callbacks), 1)
            self.assertIsNotNone(callbacks[0])

            callbacks[0]()

            self.assertCountEqual(files.calls, ["/remote", "/remote/child"])
        finally:
            source_panel.deleteLater()
