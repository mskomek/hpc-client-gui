from __future__ import annotations

from support.ftp_widget_test_support import (
    FtpWidgetTestCase,
    Path,
    QApplication,
    RemoteDirPanel,
    RemoteEntry,
    SimpleNamespace,
    TransferConflictDecision,
    TransferConflictDialog,
    patch,
    pytest,
    tempfile,
    threading,
    time,
)

class FtpWidgetTests(FtpWidgetTestCase):
    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.performance
    @pytest.mark.resource
    def test_remote_multi_folder_download_pipeline_stays_off_gui_thread(self) -> None:
        class PipelineFiles:
            supports_parallel_transfers = True

            def __init__(self) -> None:
                self.discovery_threads: list[int] = []
                self.download_threads: list[int] = []
                self.active = 0
                self.max_active = 0
                self.lock = threading.Lock()
                self.parallel_started = threading.Event()
                self.release = threading.Event()

            def is_dir(self, _path: str) -> bool:
                self.discovery_threads.append(threading.get_ident())
                return True

            def listdir_entries(self, path: str):
                self.discovery_threads.append(threading.get_ident())
                return [
                    RemoteEntry(
                        name="payload.bin",
                        path=f"{path}/payload.bin",
                        is_dir=False,
                        size=7,
                        mtime=0,
                    )
                ]

            def download(self, _remote_path, local_path, progress_cb=None) -> None:
                self.download_threads.append(threading.get_ident())
                with self.lock:
                    self.active += 1
                    self.max_active = max(self.max_active, self.active)
                    if self.active >= 2:
                        self.parallel_started.set()
                self.release.wait(3)
                Path(local_path).write_bytes(b"payload")
                if progress_cb is not None:
                    progress_cb(7, 7)
                with self.lock:
                    self.active -= 1

        files = PipelineFiles()
        panel = self.widget.panel_scratch
        session = {
            "connected": True,
            "files": files,
            "cfg": SimpleNamespace(transfer_parallelism=2),
        }
        panel.session = session
        panel._show_transfer_dialog = False
        gui_thread = threading.get_ident()
        dialog = None
        try:
            with tempfile.TemporaryDirectory() as tmp:
                started_at = time.monotonic()
                self.assertTrue(
                    panel._apply_remote_download_incremental(
                        ["/remote/folder-a", "/remote/folder-b"],
                        tmp,
                    )
                )
                self.assertLess(time.monotonic() - started_at, 0.2)

                deadline = time.monotonic() + 4
                while time.monotonic() < deadline:
                    QApplication.processEvents()
                    if panel._transfer_dialogs:
                        dialog = panel._transfer_dialogs[-1]
                    if files.parallel_started.is_set():
                        break
                    time.sleep(0.01)

                self.assertIsNotNone(dialog)
                self.assertTrue(files.parallel_started.is_set())
                self.assertEqual(dialog._parallel_limit, 2)
                self.assertTrue(files.discovery_threads)
                self.assertTrue(files.download_threads)
                self.assertTrue(
                    all(thread_id != gui_thread for thread_id in files.discovery_threads)
                )
                self.assertTrue(
                    all(thread_id != gui_thread for thread_id in files.download_threads)
                )
                self.assertGreaterEqual(files.max_active, 2)

                files.release.set()
                deadline = time.monotonic() + 4
                while time.monotonic() < deadline and not dialog.finished_cleanly():
                    QApplication.processEvents()
                    time.sleep(0.01)
                self.assertTrue(dialog.finished_cleanly())
        finally:
            files.release.set()
            if dialog is not None:
                dialog.cancel_all()
                dialog.deleteLater()
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.concurrency
    @pytest.mark.performance
    def test_download_conflict_planning_keeps_remote_probes_off_gui_thread(self) -> None:
        class ProbeGuardingFiles:
            supports_parallel_transfers = False

            def __init__(self, gui_thread: int) -> None:
                self.gui_thread = gui_thread
                self.probe_threads: list[int] = []
                self.dirs = {"/remote", "/remote/child"}
                self.entries = {
                    "/remote": [
                        RemoteEntry("child", "/remote/child", True, 0, 1),
                        RemoteEntry("root.txt", "/remote/root.txt", False, 4, 1),
                    ],
                    "/remote/child": [
                        RemoteEntry("nested.txt", "/remote/child/nested.txt", False, 6, 1),
                    ],
                }

            def _probe(self) -> int:
                thread_id = threading.get_ident()
                if thread_id == self.gui_thread:
                    raise AssertionError(
                        "remote download planning must not probe the remote backend "
                        "on the GUI thread, even for a conflict"
                    )
                self.probe_threads.append(thread_id)
                return thread_id

            def is_dir(self, path: str) -> bool:
                self._probe()
                return path.rstrip("/") in self.dirs

            def listdir_entries(self, path: str):
                self._probe()
                return list(self.entries.get((path or "/").rstrip("/") or "/", []))

            def stat(self, _path: str):
                self._probe()
                return (0, 1)

        gui_thread = threading.get_ident()
        files = ProbeGuardingFiles(gui_thread)
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        panel._show_transfer_dialog = False
        RemoteDirPanel._session_conflict_action = None
        try:
            with tempfile.TemporaryDirectory() as tmp:
                conflict_target = Path(tmp, "remote", "root.txt")
                conflict_target.parent.mkdir()
                conflict_target.write_text("local", encoding="utf-8")

                with (
                    patch.object(
                        TransferConflictDialog,
                        "get_decision",
                        return_value=TransferConflictDecision("skip"),
                    ) as decision,
                    patch.object(panel, "_run_plan_with_progress") as run_plan,
                ):
                    started_at = time.monotonic()
                    self.assertTrue(
                        panel._apply_remote_download_incremental(["/remote"], tmp)
                    )
                    self.assertLess(time.monotonic() - started_at, 0.2)

                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline and not run_plan.called:
                        QApplication.processEvents()
                        time.sleep(0.01)

            self.assertTrue(run_plan.called)
            decision.assert_called_once()
            self.assertTrue(files.probe_threads)
            self.assertTrue(
                all(thread_id != gui_thread for thread_id in files.probe_threads)
            )
            plan = run_plan.call_args.args[0]
            self.assertNotIn(
                str(conflict_target),
                [op.dst for op in plan if op.op == "download"],
            )
            self.assertEqual(
                [(op.op, op.src) for op in plan if op.op == "download"],
                [("download", "/remote/child/nested.txt")],
            )
        finally:
            RemoteDirPanel._session_conflict_action = None
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_transfer_completion_invalidates_upload_target_and_download_sources(self) -> None:
        class Files:
            supports_parallel_transfers = False

            @staticmethod
            def exists(_path: str) -> bool:
                return False

            @staticmethod
            def is_dir(_path: str) -> bool:
                return True

            @staticmethod
            def listdir_entries(_path: str):
                return []

        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": Files()}
        callbacks = []

        def capture(_plan, _title, after_finished=None, **_kwargs):
            callbacks.append(after_finished)
            return True

        with tempfile.TemporaryDirectory() as tmp, patch.object(
            panel,
            "_run_plan_with_progress",
            side_effect=capture,
        ):
            local_file = Path(tmp, "upload.bin")
            local_file.write_bytes(b"data")
            self.assertTrue(
                panel._apply_local_upload_incremental(
                    [str(local_file)],
                    "/remote/target",
                )
            )
            self.assertTrue(
                panel._apply_remote_download_incremental(
                    ["/remote/source/folder"],
                    tmp,
                )
            )
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and len(callbacks) < 2:
                self.app.processEvents()
                time.sleep(0.01)

        self.assertEqual(len(callbacks), 2)
        for key in (
            "/remote/target",
            "/remote/source",
            "/remote/source/folder",
        ):
            panel._directory_cache[key] = (0.0, [])
        for callback in callbacks:
            self.assertIsNotNone(callback)
            callback()
        self.assertNotIn("/remote/target", panel._directory_cache)
        self.assertNotIn("/remote/source", panel._directory_cache)
        self.assertNotIn("/remote/source/folder", panel._directory_cache)
