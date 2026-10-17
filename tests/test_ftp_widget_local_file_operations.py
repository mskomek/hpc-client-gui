from __future__ import annotations

from support.ftp_widget_test_support import (
    FtpWidgetTestCase,
    LOCAL_CONTEXT_MENU_LABELS,
    MockFilesBackend,
    Path,
    QApplication,
    QEvent,
    QKeyEvent,
    QMessageBox,
    Qt,
    RemoteDirPanel,
    patch,
    pytest,
    sys,
    tempfile,
    time,
    unittest,
)

class FtpWidgetTests(FtpWidgetTestCase):
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_local_context_upload_routes_selected_folder_to_incremental_planner(self) -> None:
        self.widget.panel_scratch.current_dir = "/remote"
        self.widget.session = {"connected": True}
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp, "folder")
            folder.mkdir()
            with patch.object(
                self.widget.panel_scratch,
                "_apply_local_upload_incremental",
                return_value=True,
            ) as incremental, patch.object(
                self.widget.panel_scratch,
                "_apply_local_upload",
                return_value=True,
            ) as synchronous:
                self.widget.local_panel.uploadRequested.emit([str(folder)])

        incremental.assert_called_once_with([str(folder)], "/remote")
        synchronous.assert_not_called()
        RemoteDirPanel._instances.pop(self.widget.panel_scratch.panel_id, None)
        RemoteDirPanel._instances.pop(self.widget.panel_home.panel_id, None)
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    @pytest.mark.concurrency
    def test_local_context_folder_upload_attaches_embedded_controller_after_preflight(self) -> None:
        class Files:
            supports_parallel_transfers = False

            def exists(self, _path: str) -> bool:
                return False

        class FakeSignal:
            def __init__(self) -> None:
                self.slots = []

            def connect(self, slot) -> None:
                self.slots.append(slot)

            def disconnect(self, slot) -> None:
                if slot in self.slots:
                    self.slots.remove(slot)

            def emit(self, *args) -> None:
                for slot in list(self.slots):
                    slot(*args)

        class FakeController:
            def __init__(self, _parent=None, *, items, **_kwargs) -> None:
                self._items = list(items)
                self._pending = list(items)
                self._errors = []
                self._completed = []
                self._active_items = []
                self._active_item = None
                self._running = False
                self.transferStatsChanged = FakeSignal()
                self.transferListsChanged = FakeSignal()
                self.transferProgressChanged = FakeSignal()
                self.queueFinished = FakeSignal()
                self.finished = FakeSignal()
                self.started = False

            def start(self) -> None:
                self.started = True

            def finished_cleanly(self) -> bool:
                return False

            def deleteLater(self) -> None:
                pass

        files = Files()
        panel = self.widget.panel_scratch
        session = {"connected": True, "files": files}
        self.widget.session = session
        panel.set_session(session)
        panel.current_dir = "/remote"
        controller = None
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp, "folder")
            folder.mkdir()
            (folder / "input.txt").write_text("input", encoding="utf-8")

            with patch.object(
                panel,
                "_confirm_transfer_plan",
                return_value=True,
            ) as confirm, patch.object(
                panel,
                "_apply_local_upload",
                return_value=True,
            ) as synchronous, patch(
                "hpc_gui.ui.widgets.remote_dir_panel.TransferDialog",
                FakeController,
            ):
                self.widget.local_panel.uploadRequested.emit([str(folder)])
                self.assertIsNone(self.widget.transfer_activity._controller)
                self.assertTrue(panel._planning_jobs)

                deadline = time.monotonic() + 3
                while (
                    time.monotonic() < deadline
                    and self.widget.transfer_activity._controller is None
                ):
                    self.app.processEvents()
                    time.sleep(0.01)

                controller = self.widget.transfer_activity._controller
                self.assertIsNotNone(controller)
                confirm.assert_called_once()
                synchronous.assert_not_called()
                self.assertEqual(
                    self.widget.transfer_activity.queue_list.topLevelItemCount(),
                    1,
                )
                self.assertEqual(
                    [item.op for item in controller._items],
                    ["mkdir_remote", "upload"],
                )
                self.assertTrue(controller.started)

        if controller is not None:
            controller.finished.emit(0)
        RemoteDirPanel._instances.pop(self.widget.panel_scratch.panel_id, None)
        RemoteDirPanel._instances.pop(self.widget.panel_home.panel_id, None)
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
    @pytest.mark.unit
    @pytest.mark.semantic
    def test_mock_backend_exercises_remote_file_operations(self) -> None:
        files = MockFilesBackend()

        self.assertTrue(files.exists("/arf/scratch/user/example.txt"))
        self.assertFalse(files.is_dir("/arf/scratch/user/example.txt"))
        self.assertTrue(files.is_dir("/arf/scratch/user/project"))

        files.mkdir("/arf/scratch/user/newdir/sub")
        files.write_text("/arf/scratch/user/newdir/sub/a.txt", "alpha")
        self.assertIn("sub", files.listdir("/arf/scratch/user/newdir"))
        self.assertEqual(files.read_text("/arf/scratch/user/newdir/sub/a.txt"), "alpha")

        files.copy(
            "/arf/scratch/user/newdir",
            "/arf/scratch/user/copied",
            recursive=True,
        )
        self.assertEqual(files.read_text("/arf/scratch/user/copied/sub/a.txt"), "alpha")

        files.rename("/arf/scratch/user/copied/sub/a.txt", "/arf/scratch/user/copied/sub/b.txt")
        self.assertFalse(files.exists("/arf/scratch/user/copied/sub/a.txt"))
        self.assertTrue(files.exists("/arf/scratch/user/copied/sub/b.txt"))

        files.move("/arf/scratch/user/copied", "/arf/home/user/moved")
        self.assertFalse(files.exists("/arf/scratch/user/copied"))
        self.assertTrue(files.exists("/arf/home/user/moved/sub/b.txt"))

        files.remove("/arf/home/user/moved", recursive=True)
        self.assertFalse(files.exists("/arf/home/user/moved"))
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
                event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_F2, Qt.KeyboardModifier.NoModifier)
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
            with patch(
                "hpc_gui.ui.widgets.local_dir_panel.get_file_association",
                return_value="",
            ), patch(
                "hpc_gui.ui.widgets.local_dir_panel.QFileDialog.getOpenFileName",
                return_value=(str(program), ""),
            ), patch(
                "hpc_gui.ui.widgets.local_dir_panel.QMessageBox.question",
                return_value=QMessageBox.StandardButton.Yes,
            ), patch(
                "hpc_gui.ui.widgets.local_dir_panel.set_file_association"
            ) as set_assoc, patch(
                "hpc_gui.ui.widgets.local_dir_panel.subprocess.Popen"
            ) as popen:
                self.assertTrue(local.open_selected_with_program())

            set_assoc.assert_called_once_with(".slurm", str(program))
            popen.assert_called_once_with([str(program), str(src)])
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
