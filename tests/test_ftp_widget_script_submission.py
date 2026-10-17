from __future__ import annotations

from support.ftp_widget_test_support import (
    DirectoriesWidget,
    FtpWidgetTestCase,
    MainWindow,
    QPlainTextEdit,
    RemoteDirPanel,
    _BatchSubmitWorker,
    _ShellRunWorker,
    patch,
    pytest,
)

class FtpWidgetTests(FtpWidgetTestCase):
    @pytest.mark.integration
    def test_both_remote_panels_forward_batch_submit_signals(self) -> None:
        batches = []
        shell_batches = []
        self.widget.batchSubmitRequested.connect(batches.append)
        self.widget.batchShellRequested.connect(shell_batches.append)

        self.widget.panel_scratch.batch_submit_requested.emit(
            ["/scratch/a.slurm", "/scratch/B.slurm"]
        )
        self.widget.panel_home.batch_submit_requested.emit(["/home/c.sbatch"])
        self.widget.panel_scratch.batch_shell_requested.emit(
            ["/scratch/Z.sh", "/scratch/a.sh"]
        )

        self.assertEqual(
            batches,
            [
                ["/scratch/a.slurm", "/scratch/B.slurm"],
                ["/home/c.sbatch"],
            ],
        )
        self.assertEqual(shell_batches, [["/scratch/Z.sh", "/scratch/a.sh"]])
    @pytest.mark.unit
    @pytest.mark.semantic
    def test_batch_submit_candidates_reuse_single_file_rule(self) -> None:
        self.assertEqual(
            RemoteDirPanel._batch_submit_candidates(
                [
                    ("/arf/scratch/alice/a.slurm", False),
                    ("/arf/scratch/alice/b.sbatch", False),
                ]
            ),
            ["/arf/scratch/alice/a.slurm", "/arf/scratch/alice/b.sbatch"],
        )
        self.assertEqual(
            RemoteDirPanel._batch_submit_candidates(
                [
                    ("/arf/scratch/alice/a.slurm", False),
                    ("/arf/scratch/alice/run.sh", False),
                    ("/arf/scratch/alice/folder.slurm", True),
                ]
            ),
            ["/arf/scratch/alice/a.slurm"],
        )
        self.assertEqual(
            RemoteDirPanel._batch_submit_candidates(
                [
                    ("/arf/scratch/alice/run.sh", False),
                    ("/arf/scratch/alice/notes.txt", False),
                ]
            ),
            [],
        )
        self.assertEqual(
            RemoteDirPanel._batch_shell_candidates(
                [
                    ("/remote/Z.sh", False),
                    ("/remote/a.sh", False),
                    ("/remote/folder.sh", True),
                ]
            ),
            ["/remote/a.sh", "/remote/Z.sh"],
        )
        mixed = [
            ("/remote/job.slurm", False),
            ("/remote/run.sh", False),
        ]
        self.assertEqual(
            RemoteDirPanel._batch_submit_candidates(mixed),
            ["/remote/job.slurm"],
        )
        self.assertEqual(
            RemoteDirPanel._batch_shell_candidates(mixed),
            ["/remote/run.sh"],
        )
    @pytest.mark.unit
    @pytest.mark.semantic
    def test_submit_candidate_requires_one_slurm_file(self) -> None:
        self.assertEqual(
            RemoteDirPanel._submit_candidate(
                [("/arf/scratch/alice/job.slurm", False)]
            ),
            "/arf/scratch/alice/job.slurm",
        )
        self.assertEqual(
            RemoteDirPanel._submit_candidate(
                [("/arf/home/alice/job.sbatch", False)]
            ),
            "/arf/home/alice/job.sbatch",
        )
        self.assertEqual(
            RemoteDirPanel._submit_candidate(
                [
                    ("/arf/scratch/alice/a.slurm", False),
                    ("/arf/scratch/alice/b.slurm", False),
                ]
            ),
            "",
        )
        self.assertEqual(
            RemoteDirPanel._submit_candidate(
                [("/arf/scratch/alice/folder.slurm", True)]
            ),
            "",
        )
        self.assertEqual(
            RemoteDirPanel._submit_candidate(
                [("/arf/scratch/alice/run.sh", False)]
            ),
            "",
        )
    @pytest.mark.unit
    @pytest.mark.semantic
    def test_shell_run_candidate_requires_one_shell_file(self) -> None:
        self.assertEqual(
            RemoteDirPanel._shell_run_candidate(
                [("/arf/scratch/alice/run.sh", False)]
            ),
            "/arf/scratch/alice/run.sh",
        )
        self.assertEqual(
            RemoteDirPanel._shell_run_candidate(
                [("/arf/scratch/alice/job.slurm", False)]
            ),
            "",
        )
        self.assertEqual(
            RemoteDirPanel._shell_run_candidate(
                [
                    ("/arf/scratch/alice/a.sh", False),
                    ("/arf/scratch/alice/b.sh", False),
                ]
            ),
            "",
        )
        self.assertEqual(
            RemoteDirPanel._shell_run_candidate(
                [("/arf/scratch/alice/folder.sh", True)]
            ),
            "",
        )
    @pytest.mark.unit
    @pytest.mark.semantic
    def test_shell_run_worker_quotes_script_command(self) -> None:
        self.assertEqual(
            _ShellRunWorker.command_for("/arf/scratch/alice/my script.sh"),
            "cd /arf/scratch/alice && bash './my script.sh'",
        )
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_shell_run_result_dialog_is_scrollable_and_screen_bounded(self) -> None:
        widget = DirectoriesWidget()
        dialog = None
        try:
            output = "\n".join(f"line {index}" for index in range(2000))
            dialog = widget._create_shell_run_result_dialog(
                "/remote/very-long-script.sh",
                "Script completed in terminal.",
                output,
            )
            output_view = dialog.findChild(QPlainTextEdit, "shellRunOutput")
            self.assertIsNotNone(output_view)
            self.assertTrue(output_view.isReadOnly())
            self.assertEqual(
                output_view.lineWrapMode(),
                QPlainTextEdit.LineWrapMode.NoWrap,
            )
            self.assertEqual(output_view.toPlainText(), output)
            available = widget.screen().availableGeometry()
            self.assertLessEqual(
                dialog.maximumHeight(),
                max(240, int(available.height() * 0.85)),
            )
            dialog.show()
            self.app.processEvents()
            self.assertGreater(output_view.verticalScrollBar().maximum(), 0)
        finally:
            if dialog is not None:
                dialog.close()
                dialog.deleteLater()
            widget.shutdown()
            widget.deleteLater()
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_main_window_routes_ftp_actions_to_existing_directories_handlers(self) -> None:
        opened = []
        submitted = []
        shell_batches = []

        def record_open(_self, path):
            opened.append(path)

        def record_submit(_self, path):
            submitted.append(path)

        def record_shell_run(_self, path):
            shell_runs.append(path)

        def record_shell_batch(_self, paths):
            shell_batches.append(paths)

        shell_runs = []

        with (
            patch("hpc_gui.ui.main_window.QTimer.singleShot"),
            patch.object(DirectoriesWidget, "on_open_file", record_open),
            patch.object(DirectoriesWidget, "submit_script", record_submit),
            patch.object(DirectoriesWidget, "run_shell_script", record_shell_run),
            patch.object(MainWindow, "run_shell_batch_in_terminal", record_shell_batch),
        ):
            window = MainWindow()
            try:
                window.ftp.panel_scratch.open_file.emit("/scratch/file.txt")
                window.ftp.panel_home.submit_requested.emit("/home/job.slurm")
                window.ftp.panel_home.run_shell_requested.emit("/home/run.sh")
                window.ftp.panel_scratch.batch_shell_requested.emit(
                    ["/scratch/Z.sh", "/scratch/a.sh"]
                )

                self.assertEqual(opened, ["/scratch/file.txt"])
                self.assertEqual(submitted, ["/home/job.slurm"])
                self.assertEqual(shell_runs, ["/home/run.sh"])
                self.assertEqual(shell_batches, [["/scratch/Z.sh", "/scratch/a.sh"]])
            finally:
                window.graceful_shutdown()
                window.deleteLater()
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_main_window_batch_shell_uses_login_terminal_order(self) -> None:
        with patch("hpc_gui.ui.main_window.QTimer.singleShot"):
            window = MainWindow()
        try:
            with (
                patch.object(window.tabs, "setCurrentWidget") as select_tab,
                patch.object(window.login, "run_command_text") as run_command,
            ):
                window.run_shell_batch_in_terminal(
                    ["/remote/Z name.sh", "/remote/a.sh"]
                )
            select_tab.assert_called_once_with(window.login)
            run_command.assert_called_once_with(
                "bash '/remote/Z name.sh'\n" "bash /remote/a.sh"
            )
        finally:
            window.graceful_shutdown()
            window.deleteLater()
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_batch_submit_worker_orders_sequentially_and_continues_after_failure(self) -> None:
        class RecordingSlurm:
            def __init__(self) -> None:
                self.calls: list[str] = []
                self.fail_on = {"/remote/broken.slurm"}

            def sbatch(self, script_path: str) -> str:
                self.calls.append(script_path)
                if script_path in self.fail_on:
                    raise RuntimeError("simulated failure")
                return f"Submitted batch job {1000 + self.calls.index(script_path)}"

        slurm = RecordingSlurm()
        worker = _BatchSubmitWorker(
            slurm,
            ["/remote/a.slurm", "/remote/broken.slurm", "/remote/c.slurm"],
        )
        finished_files: list[tuple[str, str]] = []
        failed_files: list[tuple[str, str]] = []
        done: list = []
        worker.signals.file_finished.connect(
            lambda _worker, path, output: finished_files.append((path, output))
        )
        worker.signals.file_failed.connect(
            lambda _worker, path, error: failed_files.append((path, error))
        )
        worker.signals.finished.connect(done.append)

        worker.run()

        self.assertEqual(
            slurm.calls,
            ["/remote/a.slurm", "/remote/broken.slurm", "/remote/c.slurm"],
        )
        self.assertEqual(
            [path for path, _output in finished_files],
            ["/remote/a.slurm", "/remote/c.slurm"],
        )
        self.assertEqual(
            [path for path, _error in failed_files],
            ["/remote/broken.slurm"],
        )
        self.assertEqual(len(done), 1)
    @pytest.mark.gui
    @pytest.mark.qt
    def test_main_window_contains_top_level_ftp_tab(self) -> None:
        with patch("hpc_gui.ui.main_window.QTimer.singleShot"):
            window = MainWindow()
        try:
            labels = [
                window.tabs.tabText(index)
                for index in range(window.tabs.count())
            ]
            self.assertIn("Files", labels)
            self.assertIs(window.ftp, window.tabs.widget(labels.index("Files")))
        finally:
            window.graceful_shutdown()
            window.deleteLater()
