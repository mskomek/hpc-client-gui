from __future__ import annotations

from support.ftp_widget_test_support import (
    ASCII,
    AUTO,
    BINARY,
    FtpWidgetTestCase,
    MockFilesBackend,
    Path,
    RemoteDirPanel,
    RemoteEntry,
    SimpleNamespace,
    _Files,
    _PlannedOp,
    _ProgressUploadFiles,
    _ResumableFiles,
    _ascii_bytes_for_local,
    _ascii_bytes_for_remote,
    download_with_mode,
    patch,
    pytest,
    resolve_transfer_mode,
    tempfile,
    time,
    upload_with_mode,
)


class FtpWidgetTests(FtpWidgetTestCase):
    @pytest.mark.unit
    @pytest.mark.semantic
    def test_active_upload_plan_is_not_queued_twice(self) -> None:
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": _Files()}
        source = str(Path(__file__).resolve())
        target = "/remote/test_ftp_widget.py"
        panel._active_transfer_keys.add(("upload", source, target))
        events = []
        panel.set_transfer_activity_callback(
            lambda event, items, title: events.append((event, items, title))
        )

        self.assertTrue(
            panel._run_plan_with_progress(
                [_PlannedOp("upload", source, target)],
                "Yükleniyor...",
            )
        )

        self.assertEqual(events, [])


    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_download_existing_target_uses_conflict_dialog_decision(self) -> None:
        files = _Files()
        files.remote["/remote/existing.txt"] = b"remote"
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, "existing.txt")
            target.write_text("local", encoding="utf-8")
            with (
                patch.object(panel, "_resolve_conflict", return_value="skip") as resolve,
                patch.object(panel, "_run_plan_with_progress") as run_plan,
            ):
                self.assertTrue(panel._apply_remote_download(["/remote/existing.txt"], tmp))
            resolve.assert_called_once()
            self.assertEqual(resolve.call_args.args[0], str(target))
            self.assertEqual(resolve.call_args.kwargs["src"], "/remote/existing.txt")
            self.assertFalse(run_plan.called)

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_download_folder_conflicts_ask_for_each_nested_file_without_apply_all(self) -> None:
        class TreeFiles:
            def listdir_entries(self, path: str):
                if path.rstrip("/") == "/remote/folder":
                    return [
                        RemoteEntry("a.txt", "/remote/folder/a.txt", False, 5, 1),
                        RemoteEntry("b.txt", "/remote/folder/b.txt", False, 5, 1),
                    ]
                return []

            def exists(self, path: str) -> bool:
                return path.rstrip("/") == "/remote/folder"

            def is_dir(self, path: str) -> bool:
                return path.rstrip("/") == "/remote/folder"

            def stat(self, path: str):
                return (0, 1) if self.is_dir(path) else (5, 1)

        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": TreeFiles()}

        with tempfile.TemporaryDirectory() as tmp:
            local_folder = Path(tmp, "folder")
            local_folder.mkdir()
            (local_folder / "a.txt").write_text("old-a", encoding="utf-8")
            (local_folder / "b.txt").write_text("old-b", encoding="utf-8")

            with (
                patch.object(
                    panel,
                    "_resolve_conflict",
                    side_effect=["overwrite", "overwrite"],
                ) as resolve,
                patch.object(panel, "_run_plan_with_progress", return_value=True) as run_plan,
            ):
                self.assertTrue(panel._apply_remote_download(["/remote/folder"], tmp))

        self.assertEqual(resolve.call_count, 2)
        self.assertEqual(
            sorted(call.args[0] for call in resolve.call_args_list),
            [
                str(local_folder / "a.txt"),
                str(local_folder / "b.txt"),
            ],
        )
        plan = run_plan.call_args.args[0]
        self.assertEqual(
            [(item.op, item.dst) for item in plan if item.op == "delete_local"],
            [
                ("delete_local", str(local_folder / "a.txt")),
                ("delete_local", str(local_folder / "b.txt")),
            ],
        )

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.resource
    def test_download_with_mode_resumes_from_part_and_replaces_final(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp, "large.bin")
            part = Path(str(destination) + ".part")
            part.write_bytes(b"partial-")
            files = _ResumableFiles(b"partial-complete")

            effective = download_with_mode(
                files,
                "/remote/large.bin",
                str(destination),
                BINARY,
            )

            self.assertEqual(effective, BINARY)
            self.assertEqual(files.calls, [str(part)])
            self.assertEqual(destination.read_bytes(), b"partial-complete")
            self.assertFalse(part.exists())

    @pytest.mark.gui
    @pytest.mark.qt
    def test_ftp_transfers_use_embedded_activity_without_showing_popup(self) -> None:
        self.assertFalse(self.widget.panel_scratch._show_transfer_dialog)
        self.assertFalse(self.widget.panel_home._show_transfer_dialog)

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_mock_ftp_download_writes_selected_remote_file(self) -> None:
        files = MockFilesBackend()
        cfg = SimpleNamespace(
            username="user",
            system_settings={
                "scratch_dir": "/arf/scratch/{user}",
                "home_dir": "/arf/home/{user}",
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            self.widget.local_panel.current_dir = tmp
            self.widget.set_session({"connected": True, "files": files, "cfg": cfg})
            with (
                patch.object(
                    self.widget,
                    "_selected_remote_paths",
                    return_value=["/arf/scratch/user/example.txt"],
                ),
                patch.object(
                    RemoteDirPanel,
                    "_run_plan_with_progress",
                    self._run_plan_synchronously,
                ),
            ):
                self.assertTrue(self.widget.download_selected())
                target = Path(tmp, "example.txt")
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline and not target.exists():
                    self.app.processEvents()
                    time.sleep(0.01)

            self.assertEqual(
                Path(tmp, "example.txt").read_text(encoding="utf-8"),
                "Mock file content\nline2\n",
            )

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_mock_ftp_nested_directory_download_and_binary_upload(self) -> None:
        files = MockFilesBackend()
        cfg = SimpleNamespace(
            username="user",
            system_settings={
                "scratch_dir": "/arf/scratch/{user}",
                "home_dir": "/arf/home/{user}",
            },
        )
        self.widget.set_session({"connected": True, "files": files, "cfg": cfg})

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                RemoteDirPanel,
                "_run_plan_with_progress",
                self._run_plan_synchronously,
            ):
                self.assertTrue(
                    self.widget.panel_scratch._apply_remote_download(
                        ["/arf/scratch/user/project"],
                        tmp,
                    )
                )
            self.assertEqual(Path(tmp, "project", "input.dat").read_text(), "1 2 3\n")
            self.assertEqual(
                Path(tmp, "project", "nested", "result.bin").read_bytes(),
                b"\x00\x01\x02mock-binary",
            )

            # Uploading a selected directory preserves its complete nested
            # tree on the remote side as well.
            with patch.object(
                RemoteDirPanel,
                "_run_plan_with_progress",
                self._run_plan_synchronously,
            ):
                self.assertTrue(
                    self.widget.panel_scratch._apply_local_upload(
                        [str(Path(tmp, "project"))],
                        "/arf/scratch/user/uploads",
                    )
                )
            uploaded_nested = Path(tmp, "uploaded-result.bin")
            files.download(
                "/arf/scratch/user/uploads/project/nested/result.bin",
                str(uploaded_nested),
            )
            self.assertEqual(uploaded_nested.read_bytes(), b"\x00\x01\x02mock-binary")

            local_bin = Path(tmp, "payload.bin")
            local_bin.write_bytes(b"\x00\xffraw")
            self.widget.panel_scratch.current_dir = "/arf/scratch/user/uploads"
            with patch.object(
                RemoteDirPanel,
                "_run_plan_with_progress",
                self._run_plan_synchronously,
            ):
                self.assertTrue(
                    self.widget.panel_scratch._apply_local_upload(
                        [str(local_bin)],
                        "/arf/scratch/user/uploads",
                    )
                )
            downloaded = Path(tmp, "roundtrip.bin")
            files.download("/arf/scratch/user/uploads/payload.bin", str(downloaded))
            self.assertEqual(downloaded.read_bytes(), b"\x00\xffraw")

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_transfer_mode_policy_and_conversion(self) -> None:
        self.assertEqual(resolve_transfer_mode("notes.txt", AUTO), ASCII)
        self.assertEqual(resolve_transfer_mode("archive", AUTO), BINARY)
        self.assertEqual(resolve_transfer_mode("image.bin", AUTO, b"\x00x"), BINARY)
        with self.assertRaises(ValueError):
            resolve_transfer_mode("image.bin", ASCII, b"\x00x")

        self.assertEqual(_ascii_bytes_for_remote(b"a\r\nb\r\n"), b"a\nb\n")
        self.assertEqual(
            _ascii_bytes_for_local(b"x\ny\n").decode("utf-8").splitlines(),
            ["x", "y"],
        )

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_upload_folder_conflicts_ask_for_each_nested_file_without_apply_all(self) -> None:
        files = _Files()
        files.remote["/remote/folder/a.txt"] = b"old-a"
        files.remote["/remote/folder/b.txt"] = b"old-b"
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp, "folder")
            folder.mkdir()
            (folder / "a.txt").write_text("new-a", encoding="utf-8")
            (folder / "b.txt").write_text("new-b", encoding="utf-8")

            with (
                patch.object(
                    panel,
                    "_resolve_conflict",
                    side_effect=["overwrite", "overwrite"],
                ) as resolve,
                patch.object(panel, "_run_plan_with_progress", return_value=True) as run_plan,
            ):
                self.assertTrue(panel._apply_local_upload([str(folder)], "/remote"))

        self.assertEqual(resolve.call_count, 2)
        self.assertEqual(
            sorted(call.args[0] for call in resolve.call_args_list),
            ["/remote/folder/a.txt", "/remote/folder/b.txt"],
        )
        plan = run_plan.call_args.args[0]
        self.assertEqual(
            sorted((item.op, item.dst) for item in plan if item.op == "delete"),
            [
                ("delete", "/remote/folder/a.txt"),
                ("delete", "/remote/folder/b.txt"),
            ],
        )

    @pytest.mark.integration
    @pytest.mark.semantic
    def test_upload_with_mode_forwards_progress_callback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "payload.bin")
            source.write_bytes(b"\x00" + b"x" * 4096)
            files = _ProgressUploadFiles()
            progress = []

            effective = upload_with_mode(
                files,
                str(source),
                "/remote/payload.bin",
                BINARY,
                progress_cb=lambda done, total: progress.append((done, total)),
            )

            self.assertEqual(effective, BINARY)
            self.assertEqual(files.calls, [(str(source), "/remote/payload.bin")])
            self.assertEqual(progress[-1], (source.stat().st_size, source.stat().st_size))
