from __future__ import annotations

from support.ftp_widget_test_support import (
    FtpWidgetTestCase,
    Path,
    QApplication,
    QDialog,
    SimpleNamespace,
    TransferDialog,
    TransferItem,
    TransferPreflightDialog,
    _Files,
    _PlannedOp,
    patch,
    pytest,
    tempfile,
    threading,
    time,
)

class FtpWidgetTests(FtpWidgetTestCase):
    @pytest.mark.gui
    @pytest.mark.qt
    def test_upload_preflight_shows_counts_and_source_destination_rows(self) -> None:
        items = [
            TransferItem("mkdir_remote", "", "/remote/folder"),
            TransferItem("upload", "C:/local/a.txt", "/remote/folder/a.txt"),
            TransferItem("upload", "C:/local/b.txt", "/remote/folder/b.txt"),
        ]
        dialog = TransferPreflightDialog(
            title="Upload",
            items=items,
            parallel_limit=2,
        )
        try:
            self.assertIn("2 files", dialog.lbl_summary.text())
            self.assertIn("1 folder", dialog.lbl_summary.text())
            self.assertIn("3 total steps", dialog.lbl_summary.text())
            self.assertIn("2 transfers", dialog.lbl_summary.text())
            self.assertEqual(dialog.plan_list.topLevelItemCount(), 3)
            upload_row = dialog.plan_list.topLevelItem(1)
            self.assertEqual(upload_row.text(1), "C:/local/a.txt")
            self.assertEqual(upload_row.text(2), "/remote/folder/a.txt")
            self.assertEqual(dialog.btn_start.text(), "Start transfer")
            self.assertEqual(dialog.cb_dont_ask_again.text(), "Don't ask again")
            self.assertFalse(dialog.cb_dont_ask_again.isChecked())
        finally:
            dialog.deleteLater()
    @pytest.mark.gui
    @pytest.mark.qt
    def test_upload_preflight_bounds_plan_rows_without_truncating_items(self) -> None:
        items = [
            TransferItem(
                "upload",
                f"C:/local/file-{index}.bin",
                f"/remote/folder/file-{index}.bin",
            )
            for index in range(250)
        ]
        dialog = TransferPreflightDialog(
            title="Upload",
            items=items,
            parallel_limit=2,
        )
        try:
            self.assertEqual(len(dialog._items), 250)
            self.assertEqual(dialog.plan_list.topLevelItemCount(), 201)
            remaining_row = dialog.plan_list.topLevelItem(200)
            self.assertEqual(remaining_row.text(0), "Remaining: 50")
            self.assertEqual(dialog.plan_list.topLevelItem(0).text(1), "C:/local/file-0.bin")
            self.assertIn("250 files", dialog.lbl_summary.text())
            self.assertIn("250 total steps", dialog.lbl_summary.text())
            self.assertEqual(dialog.btn_start.text(), "Start transfer")
        finally:
            dialog.deleteLater()
    @pytest.mark.unit
    def test_upload_preflight_dont_ask_persists_only_when_accepted(self) -> None:
        panel = self.widget.panel_scratch
        item = TransferItem("upload", "C:/local/a.txt", "/remote/a.txt")

        class FakeCheckBox:
            def isChecked(self) -> bool:
                return True

        class FakePreflightDialog:
            result = QDialog.DialogCode.Accepted

            def __init__(self, *_args, **_kwargs) -> None:
                self.cb_dont_ask_again = FakeCheckBox()

            def exec(self):
                return self.result

            def deleteLater(self) -> None:
                pass

        with patch(
            "hpc_gui.ui.widgets.remote_dir_panel.get_upload_preflight_confirmation_enabled",
            return_value=True,
        ), patch(
            "hpc_gui.ui.widgets.remote_dir_panel.TransferPreflightDialog",
            FakePreflightDialog,
        ), patch(
            "hpc_gui.ui.widgets.remote_dir_panel.set_upload_preflight_confirmation_enabled"
        ) as persist:
            self.assertTrue(panel._confirm_transfer_plan([item], "Upload", 1))
        persist.assert_called_once_with(False)

        FakePreflightDialog.result = QDialog.DialogCode.Rejected
        with patch(
            "hpc_gui.ui.widgets.remote_dir_panel.get_upload_preflight_confirmation_enabled",
            return_value=True,
        ), patch(
            "hpc_gui.ui.widgets.remote_dir_panel.TransferPreflightDialog",
            FakePreflightDialog,
        ), patch(
            "hpc_gui.ui.widgets.remote_dir_panel.set_upload_preflight_confirmation_enabled"
        ) as persist:
            self.assertFalse(panel._confirm_transfer_plan([item], "Upload", 1))
        persist.assert_not_called()
    @pytest.mark.unit
    def test_disabled_upload_preflight_skips_dialog(self) -> None:
        panel = self.widget.panel_scratch
        item = TransferItem("mkdir_remote", "", "/remote/empty")
        with patch(
            "hpc_gui.ui.widgets.remote_dir_panel.get_upload_preflight_confirmation_enabled",
            return_value=False,
        ), patch(
            "hpc_gui.ui.widgets.remote_dir_panel.TransferPreflightDialog"
        ) as dialog:
            self.assertTrue(panel._confirm_transfer_plan([item], "Upload", 1))
        dialog.assert_not_called()
    @pytest.mark.integration
    def test_disabled_upload_preflight_still_executes_local_upload(self) -> None:
        class Files:
            supports_parallel_transfers = False

            def __init__(self) -> None:
                self.created: list[str] = []

            def exists(self, _path: str) -> bool:
                return False

            def mkdir(self, path: str) -> None:
                self.created.append(path)

            def listdir_entries(self, _path: str):
                return []

        files = Files()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        completed = threading.Event()
        panel.set_transfer_activity_callback(
            lambda event, _items, _title: completed.set()
            if event == "completed"
            else None
        )

        with tempfile.TemporaryDirectory() as tmp:
            empty_folder = Path(tmp) / "empty"
            empty_folder.mkdir()
            with patch(
                "hpc_gui.ui.widgets.remote_dir_panel.get_upload_preflight_confirmation_enabled",
                return_value=False,
            ), patch(
                "hpc_gui.ui.widgets.remote_dir_panel.TransferPreflightDialog"
            ) as dialog:
                self.assertTrue(
                    panel._apply_local_upload([str(empty_folder)], "/remote")
                )
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline and not completed.is_set():
                    QApplication.processEvents()
                    time.sleep(0.01)

        dialog.assert_not_called()
        self.assertTrue(completed.is_set())
        self.assertEqual(files.created, ["/remote/empty"])
    @pytest.mark.integration
    @pytest.mark.concurrency
    def test_upload_preflight_cancel_starts_no_worker_or_activity(self) -> None:
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": _Files()}
        source = str(Path(__file__).resolve())
        destination = "/remote/test_ftp_widget.py"
        events = []
        panel.set_transfer_activity_callback(
            lambda event, items, title: events.append((event, items, title))
        )

        with patch.object(
            panel,
            "_confirm_transfer_plan",
            return_value=False,
        ) as confirm, patch.object(TransferDialog, "start") as start:
            self.assertFalse(
                panel._run_plan_with_progress(
                    [_PlannedOp("upload", source, destination)],
                    "Upload",
                    confirm_before_start=True,
                )
            )

        confirm.assert_called_once()
        start.assert_not_called()
        self.assertEqual(events, [])
        self.assertNotIn(
            ("upload", source, destination),
            panel._active_transfer_keys,
        )
    @pytest.mark.integration
    def test_empty_folder_upload_requires_preflight_before_mkdir_worker(self) -> None:
        class EmptyFolderFiles:
            supports_parallel_transfers = False

            def __init__(self) -> None:
                self.created: list[str] = []

            def exists(self, _path: str) -> bool:
                return False

            def mkdir(self, _path: str) -> None:
                self.created.append(_path)

            def listdir_entries(self, _path: str):
                return []

        panel = self.widget.panel_scratch
        files = EmptyFolderFiles()
        panel.session = {"connected": True, "files": files}
        controllers: list[TransferDialog] = []
        completed = threading.Event()

        def record_activity(event, items, _title):
            if event == "controller":
                controllers.extend(items)
            elif event == "completed":
                completed.set()

        panel.set_transfer_activity_callback(record_activity)

        with tempfile.TemporaryDirectory() as tmp:
            empty_folder = Path(tmp) / "empty"
            empty_folder.mkdir()

            with patch.object(
                panel,
                "_confirm_transfer_plan",
                return_value=False,
            ) as confirm, patch.object(TransferDialog, "start") as start:
                self.assertFalse(
                    panel._apply_local_upload([str(empty_folder)], "/remote")
                )
            confirm_items = confirm.call_args.args[0]
            self.assertEqual(
                [(item.op, item.src, item.dst) for item in confirm_items],
                [("mkdir_remote", "", "/remote/empty")],
            )
            start.assert_not_called()
            self.assertEqual(controllers, [])

            with patch.object(
                panel,
                "_confirm_transfer_plan",
                return_value=True,
            ) as confirm:
                self.assertTrue(
                    panel._apply_local_upload([str(empty_folder)], "/remote")
                )
                confirm.assert_called_once()
                self.assertEqual(len(controllers), 1)
                controller = controllers[0]
                self.assertEqual(
                    [(item.op, item.src, item.dst) for item in controller._items],
                    [("mkdir_remote", "", "/remote/empty")],
                )
                self.assertEqual(controller._parallel_limit, 1)

                deadline = time.monotonic() + 3
                while time.monotonic() < deadline and not completed.is_set():
                    QApplication.processEvents()
                    time.sleep(0.01)

        self.assertTrue(completed.is_set())
        self.assertEqual(files.created, ["/remote/empty"])
    @pytest.mark.integration
    @pytest.mark.concurrency
    def test_single_connection_multi_folder_upload_runs_sequentially(self) -> None:
        class SingleConnectionFiles:
            supports_parallel_transfers = False

            def __init__(self) -> None:
                self.active = 0
                self.max_active = 0
                self.uploaded: list[str] = []
                self.lock = threading.Lock()

            def exists(self, _path: str) -> bool:
                return False

            def is_dir(self, _path: str) -> bool:
                return False

            def listdir_entries(self, _path: str):
                return []

            def mkdir(self, _path: str) -> None:
                self._run_operation()

            def upload(self, _local_path: str, remote_path: str, progress_cb=None) -> None:
                self._run_operation()
                self.uploaded.append(remote_path)
                if progress_cb is not None:
                    progress_cb(1, 1)

            def _run_operation(self) -> None:
                with self.lock:
                    self.active += 1
                    self.max_active = max(self.max_active, self.active)
                time.sleep(0.01)
                with self.lock:
                    self.active -= 1

        files = SingleConnectionFiles()
        panel = self.widget.panel_scratch
        panel.set_session(
            {
                "connected": True,
                "files": files,
                "cfg": SimpleNamespace(transfer_parallelism=5),
            }
        )
        controllers: list[TransferDialog] = []
        completed = threading.Event()

        def record_activity(event, items, _title):
            if event == "controller":
                controllers.extend(items)
            elif event == "completed":
                completed.set()

        panel.set_transfer_activity_callback(record_activity)
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            panel, "_confirm_transfer_plan", return_value=True
        ) as confirm:
            roots = []
            for name in ("first", "second"):
                root = Path(tmp) / name
                root.mkdir()
                (root / "input.txt").write_text(name, encoding="utf-8")
                roots.append(str(root))

            self.assertTrue(panel._apply_local_upload(roots, "/remote"))
            confirm.assert_called_once()
            self.assertEqual(len(controllers), 1)
            self.assertEqual(controllers[0]._parallel_limit, 1)

            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not completed.is_set():
                QApplication.processEvents()
                time.sleep(0.01)

        self.assertTrue(completed.is_set())
        self.assertEqual(files.max_active, 1)
        self.assertCountEqual(
            files.uploaded,
            ["/remote/first/input.txt", "/remote/second/input.txt"],
        )
    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.performance
    def test_upload_planning_uses_worker_and_returns_before_slow_probe(self) -> None:
        class SlowFiles:
            supports_parallel_transfers = False

            def __init__(self) -> None:
                self.started = threading.Event()
                self.release = threading.Event()
                self.thread_id = None

            def exists(self, _path: str) -> bool:
                self.thread_id = threading.get_ident()
                self.started.set()
                self.release.wait(3)
                return False

        files = SlowFiles()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            panel,
            "_run_plan_with_progress",
            return_value=True,
        ) as run_plan:
            local_file = Path(tmp, "input.bin")
            local_file.write_bytes(b"input")
            started_at = time.monotonic()
            self.assertTrue(
                panel._apply_local_upload_incremental(
                    [str(local_file)],
                    "/remote",
                )
            )
            elapsed = time.monotonic() - started_at

            self.assertLess(elapsed, 0.2)
            self.assertTrue(files.started.wait(1))
            self.assertNotEqual(files.thread_id, threading.get_ident())
            run_plan.assert_not_called()

            files.release.set()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not run_plan.called:
                self.app.processEvents()
                time.sleep(0.01)
            self.assertTrue(run_plan.called)
