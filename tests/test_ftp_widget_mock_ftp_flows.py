"""Focused FTP widget tests for mock ftp flows behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from hpc_gui.services.files_mock import MockFilesBackend
from hpc_gui.ui.widgets.login_widget import (
    FTP_TEST_MODE_ENV,
    LoginWidget,
    is_ftp_mock_host,
    is_ftp_test_mode_enabled,
)
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel, _PlannedOp
from hpc_gui.services.files_base import RemoteEntry
from ftp_widget_test_support import FtpWidgetTestCase, _Files


class FtpWidgetMockFtpFlowsTests(FtpWidgetTestCase):
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
            self.assertEqual(
                [(item.op, item.src, item.dst) for item in plan],
                [
                    ("download", "/remote/existing.txt", str(target)),
                ],
            )

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
            self.assertEqual(
                [(item.op, item.src, item.dst) for item in plan],
                [
                    ("upload", str(source), "/remote/existing.txt"),
                ],
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

    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_active_download_plan_is_not_queued_twice(self) -> None:
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": _Files()}
        source = "/remote/existing.txt"
        target = str(Path(tempfile.gettempdir(), "existing.txt"))
        panel._active_transfer_keys.add(("download", source, target))
        events = []
        panel.set_transfer_activity_callback(
            lambda event, items, title: events.append((event, items, title))
        )

        self.assertTrue(
            panel._run_plan_with_progress(
                [_PlannedOp("download", source, target)],
                "İndiriliyor...",
            )
        )

        self.assertEqual(events, [])

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

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.regression
    @pytest.mark.qt
    def test_ftp_mock_round_trips_turkish_file_and_directory_names(self) -> None:
        files = MockFilesBackend()
        panel = self.widget.panel_scratch
        panel.set_session({"connected": True, "files": files})
        remote_dir = "/arf/scratch/user/klasör_çğışü"

        with tempfile.TemporaryDirectory() as tmp:
            local_dir = Path(tmp, "yerel_klasör_İçerik")
            local_dir.mkdir()
            local_file = local_dir / "dosya_çığöşü.txt"
            content = "Türkçe içerik: ÇĞİÖŞÜ çğıöşü\n".encode("utf-8")
            local_file.write_bytes(content)

            with patch.object(
                RemoteDirPanel,
                "_run_plan_with_progress",
                self._run_plan_synchronously,
            ):
                self.assertTrue(panel._apply_local_upload([str(local_dir)], remote_dir))

            remote_file = remote_dir + "/yerel_klasör_İçerik/dosya_çığöşü.txt"
            self.assertEqual(files._files[remote_file], content)

            target_dir = Path(tmp, "indirilenler_İstanbul")
            target_dir.mkdir()
            with patch.object(
                RemoteDirPanel,
                "_run_plan_with_progress",
                self._run_plan_synchronously,
            ):
                self.assertTrue(
                    panel._apply_remote_download(
                        [remote_dir + "/yerel_klasör_İçerik"],
                        str(target_dir),
                    )
                )

            self.assertEqual(
                (target_dir / "yerel_klasör_İçerik" / "dosya_çığöşü.txt").read_bytes(),
                content.replace(b"\n", os.linesep.encode("utf-8")),
            )

    @pytest.mark.contract
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_ftp_mock_connection_is_environment_gated(self) -> None:
        with patch.dict(os.environ, {FTP_TEST_MODE_ENV: ""}):
            self.assertFalse(is_ftp_test_mode_enabled())
            self.assertTrue(is_ftp_mock_host("mock"))

        with patch.dict(os.environ, {FTP_TEST_MODE_ENV: "1"}):
            login = LoginWidget()
            try:
                login.host.setText("mock")
                login.username.setText("user")
                emitted = []
                login.session_changed.connect(lambda session: emitted.append(session))
                self.assertTrue(login.connect_clicked())
                self.assertTrue(emitted[-1]["connected"])
                self.assertIsInstance(emitted[-1]["files"], MockFilesBackend)
                self.assertTrue(emitted[-1]["cfg"].dry_run)
            finally:
                login.deleteLater()
