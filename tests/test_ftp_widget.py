from __future__ import annotations

from support.ftp_widget_test_support import (
    BINARY,
    FtpWidgetTestCase,
    MainWindow,
    MockFilesBackend,
    Path,
    QEvent,
    QKeyEvent,
    Qt,
    SSHFilesBackend,
    SimpleNamespace,
    TransferDialog,
    TransferItem,
    _Files,
    download_with_mode,
    patch,
    pytest,
    tempfile,
    upload_with_mode,
)


class FtpWidgetTests(FtpWidgetTestCase):
    @pytest.mark.gui
    @pytest.mark.qt
    def test_layout_and_exclusive_remote_sections(self) -> None:
        self.assertEqual(self.widget.splitter.count(), 2)
        self.assertEqual(self.widget.accordion.active_key, "scratch")
        self.widget.accordion.set_active("home")
        self.assertEqual(self.widget.active_remote_panel(), self.widget.panel_home)
        self.assertFalse(self.widget.panel_scratch.isVisible())
    @pytest.mark.gui
    @pytest.mark.qt
    def test_multi_folder_download_queue_caps_rows_without_truncating_plan(self) -> None:
        items = [
            TransferItem(
                "download",
                f"/remote/folder-{index % 2}/file-{index}.bin",
                f"file-{index}.bin",
            )
            for index in range(5)
        ]
        dialog = TransferDialog(
            title="Download",
            items=items,
            run_item=lambda _item, _progress=None: None,
        )
        try:
            with patch.object(
                self.widget.transfer_activity,
                "_MAX_VISIBLE_TRANSFER_ROWS",
                3,
            ):
                self.widget.transfer_activity.record(
                    "controller",
                    [dialog],
                    "Download",
                )

            self.assertEqual(len(dialog._items), 5)
            self.assertEqual(len(dialog._pending), 5)
            self.assertEqual(
                self.widget.transfer_activity.queue_list.topLevelItemCount(),
                4,
            )
            info_row = self.widget.transfer_activity.queue_list.topLevelItem(3)
            self.assertEqual(info_row.text(2), "Remaining: 2")
            self.assertIsNone(
                self.widget.transfer_activity.queue_list.itemWidget(info_row, 4)
            )
            self.assertIn(
                "5 files.",
                self.widget.transfer_activity.summary_label.text(),
            )
        finally:
            dialog.deleteLater()
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_ssh_resumed_upload_reports_existing_offset_before_copy(self) -> None:
        class RemoteWriter:
            def __init__(self) -> None:
                self.data = bytearray(b"abc")

            def __enter__(self):
                return self

            def __exit__(self, *_args) -> None:
                return None

            def write(self, data: bytes) -> None:
                self.data.extend(data)

        class TransferChannel:
            def __init__(self) -> None:
                self.writer = RemoteWriter()
                self.closed = False

            def stat(self, _path: str):
                return SimpleNamespace(st_size=3)

            def open(self, _path: str, mode: str):
                self.assert_mode = mode
                return self.writer

            def close(self) -> None:
                self.closed = True

        channel = TransferChannel()
        ssh = SimpleNamespace(sftp=object(), open_transfer_sftp=lambda: channel)
        backend = SSHFilesBackend(ssh)
        progress: list[tuple[int, int]] = []
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "resume.bin"
            source.write_bytes(b"abcdefgh")
            backend.resume_upload(
                str(source),
                "/remote/resume.bin",
                progress_cb=lambda done, total: progress.append((done, total)),
            )

        self.assertEqual(progress, [(3, 8), (8, 8)])
        self.assertEqual(channel.assert_mode, "ab")
        self.assertEqual(bytes(channel.writer.data), b"abcdefgh")
        self.assertTrue(channel.closed)
    @pytest.mark.integration
    def test_both_remote_panels_forward_open_and_submit_signals(self) -> None:
        opened = []
        submitted = []
        shell_runs = []
        self.widget.openFileRequested.connect(opened.append)
        self.widget.submitRequested.connect(submitted.append)
        self.widget.runShellRequested.connect(shell_runs.append)

        self.widget.panel_scratch.open_file.emit("/scratch/readme.txt")
        self.widget.panel_home.open_file.emit("/home/script.slurm")
        self.widget.panel_scratch.submit_requested.emit("/scratch/a.slurm")
        self.widget.panel_home.submit_requested.emit("/home/b.sbatch")
        self.widget.panel_scratch.run_shell_requested.emit("/scratch/run.sh")

        self.assertEqual(
            opened,
            ["/scratch/readme.txt", "/home/script.slurm"],
        )
        self.assertEqual(
            submitted,
            ["/scratch/a.slurm", "/home/b.sbatch"],
        )
        self.assertEqual(shell_runs, ["/scratch/run.sh"])
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_submission_follow_modes_route_to_the_requested_destination(self) -> None:
        with patch("hpc_gui.ui.main_window.QTimer.singleShot"):
            window = MainWindow()
        try:
            for mode, shows_jobs_page in {
                "none": False,
                "outputs_tab": True,
                "new_tabs_split": True,
                "new_window_combined": False,
                "new_windows_split": False,
            }.items():
                window.tabs.setCurrentWidget(window.ftp)
                with patch.object(window.jobs_outputs, "focus_job") as focus, patch(
                    "hpc_gui.ui.main_window.get_sbatch_follow_mode",
                    return_value=mode,
                ):
                    window.on_script_submitted("123", "/remote/job.sbatch")
                self.assertIs(
                    window.tabs.currentWidget(),
                    window.jobs_outputs if shows_jobs_page else window.ftp,
                )
                focus.assert_called_once_with(
                    "123",
                    "/remote/job.sbatch",
                    switch_to_outputs=shows_jobs_page,
                    follow_mode=mode,
                )
        finally:
            window.graceful_shutdown()
            window.deleteLater()
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_generic_new_window_follower_is_one_single_file_window(self) -> None:
        from hpc_gui.ui.widgets.jobs_outputs_widget import (
            JobsOutputsWidget,
            _SingleFileFollowerWidget,
        )

        jobs_widget = JobsOutputsWidget()
        try:
            window = jobs_widget.open_file_follow_window("/remote/run.log")
            self.assertIsNotNone(window)
            self.assertEqual(len(jobs_widget._single_file_follow_windows), 1)
            self.assertEqual(len(jobs_widget._follow_windows), 0)
            self.assertIsInstance(window.centralWidget(), _SingleFileFollowerWidget)
            self.assertIn("run.log", window.windowTitle())
            self.assertNotIn("Output 1", window.windowTitle())
            self.assertNotIn("Output 2", window.windowTitle())
            follower = window.centralWidget()
            self.assertFalse(follower.err_box.isVisible())
            self.assertEqual(follower.out_box.title(), "run.log")
            self.assertNotIn("Output 1", follower.out_box.title())
            self.assertNotIn("Output 2", follower.out_box.title())
        finally:
            jobs_widget.shutdown()
            jobs_widget.deleteLater()
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_upload_and_download_route_to_active_remote_panel(self) -> None:
        local_file = Path(__file__).resolve()
        self.widget.panel_scratch.current_dir = "/remote"
        self.widget.session = {"connected": True}
        with (
            patch.object(
                self.widget.local_panel,
                "selected_paths",
                return_value=[str(local_file)],
            ),
            patch.object(
                self.widget.panel_scratch,
                "_apply_local_upload_incremental",
                return_value=True,
            ) as upload,
        ):
            self.assertTrue(self.widget.upload_selected())
        upload.assert_called_once_with([str(local_file)], "/remote")

        with (
            patch.object(
                self.widget, "_selected_remote_paths", return_value=["/remote/out.txt"]
            ),
            patch.object(
                self.widget.panel_scratch,
                "_apply_remote_download_incremental",
                return_value=True,
            ) as download,
        ):
            self.assertTrue(self.widget.download_selected())
        download.assert_called_once_with(["/remote/out.txt"], self.widget.local_panel.current_dir)
    @pytest.mark.gui
    @pytest.mark.qt
    def test_ftp_transfer_area_is_resizable_with_directory_area(self) -> None:
        self.assertIs(self.widget.transfer_splitter.widget(0), self.widget.splitter)
        self.assertIs(self.widget.transfer_splitter.widget(1), self.widget.transfer_activity)
        self.assertEqual(self.widget.transfer_splitter.orientation(), Qt.Orientation.Vertical)
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_double_click_activation_routes_to_transfer_targets(self) -> None:
        local_file = Path(__file__).resolve()
        self.widget.panel_scratch.current_dir = "/remote"
        self.widget.session = {"connected": True}

        with patch.object(
            self.widget.panel_scratch,
            "_apply_local_upload_incremental",
            return_value=True,
        ) as upload:
            self.widget.local_panel.fileActivated.emit(str(local_file))
        upload.assert_called_once_with([str(local_file)], "/remote")

        with patch.object(
            self.widget.panel_scratch,
            "_apply_remote_download_incremental",
            return_value=True,
        ) as download:
            self.widget.panel_scratch.file_activated.emit("/remote/out.txt")
        download.assert_called_once_with(["/remote/out.txt"], self.widget.local_panel.current_dir)
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_double_click_activation_does_not_start_duplicate_upload(self) -> None:
        local_file = Path(__file__).resolve()
        self.widget.panel_scratch.current_dir = "/remote"
        self.widget.session = {"connected": True}

        with (
            patch(
                "hpc_gui.ui.widgets.ftp_widget.monotonic",
                side_effect=[10.0, 10.1, 11.2],
            ),
            patch.object(
                self.widget.panel_scratch,
                "_apply_local_upload_incremental",
                return_value=True,
            ) as upload,
        ):
            self.widget.local_panel.fileActivated.emit(str(local_file))
            self.widget.local_panel.fileActivated.emit(str(local_file))
            self.widget.local_panel.fileActivated.emit(str(local_file))

        self.assertEqual(upload.call_count, 2)
        upload.assert_called_with([str(local_file)], "/remote")
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.resource
    @pytest.mark.regression
    def test_resume_rejects_stale_download_part_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp, "large.bin")
            part = Path(str(destination) + ".part")
            part.write_bytes(b"stale")
            Path(str(part) + ".meta").write_text("{}", encoding="utf-8")
            files = MockFilesBackend()
            files.write_text("/remote/large.bin", "fresh-content")

            download_with_mode(files, "/remote/large.bin", str(destination), BINARY)

            self.assertEqual(destination.read_bytes(), b"fresh-content")
            self.assertFalse(Path(str(part) + ".meta").exists())
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.resource
    @pytest.mark.regression
    def test_resume_rejects_stale_upload_part_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "payload.bin")
            source.write_bytes(b"fresh-content")
            files = MockFilesBackend()
            stale = Path(tmp, "stale.bin")
            stale.write_bytes(b"stale")
            files.upload(str(stale), "/remote/payload.bin.part")
            files.write_text("/remote/payload.bin.part.meta", "{}")

            upload_with_mode(files, str(source), "/remote/payload.bin", BINARY)

            self.assertEqual(files.read_text("/remote/payload.bin"), "fresh-content")
            self.assertFalse(files.exists("/remote/payload.bin.part.meta"))
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
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_download_resume_keeps_partial_target_and_plans_one_transfer(self) -> None:
        files = _Files()
        files.remote["/remote/existing.txt"] = b"remote"
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, "existing.txt")
            target.write_text("part", encoding="utf-8")
            with (
                patch.object(panel, "_resolve_conflict", return_value="resume"),
                patch.object(panel, "_run_plan_with_progress", return_value=True) as run_plan,
            ):
                self.assertTrue(
                    panel._apply_remote_download(
                        ["/remote/existing.txt", "/remote/existing.txt"],
                        tmp,
                    )
                )

            plan = run_plan.call_args.args[0]
            self.assertEqual([(item.op, item.src, item.dst) for item in plan], [
                ("download", "/remote/existing.txt", str(target)),
            ])
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_upload_resume_keeps_remote_target_and_plans_one_transfer(self) -> None:
        files = _Files()
        files.remote["/remote/existing.txt"] = b"part"
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "existing.txt")
            source.write_text("remote", encoding="utf-8")
            with (
                patch.object(panel, "_resolve_conflict", return_value="resume"),
                patch.object(panel, "_run_plan_with_progress", return_value=True) as run_plan,
            ):
                self.assertTrue(
                    panel._apply_local_upload(
                        [str(source), str(source)],
                        "/remote",
                    )
                )

            plan = run_plan.call_args.args[0]
            self.assertEqual([(item.op, item.src, item.dst) for item in plan], [
                ("upload", str(source), "/remote/existing.txt"),
            ])
