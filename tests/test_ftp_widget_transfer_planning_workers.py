"""Focused FTP widget tests for transfer planning workers behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch
import pytest
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel
from ftp_widget_test_support import FtpWidgetTestCase, _CountingFiles


class FtpWidgetTransferPlanningWorkersTests(FtpWidgetTestCase):
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_local_context_upload_routes_selected_folder_to_incremental_planner(self) -> None:
        self.widget.panel_scratch.current_dir = "/remote"
        self.widget.session = {"connected": True}
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp, "folder")
            folder.mkdir()
            with (
                patch.object(
                    self.widget.panel_scratch,
                    "_apply_local_upload_incremental",
                    return_value=True,
                ) as incremental,
                patch.object(
                    self.widget.panel_scratch,
                    "_apply_local_upload",
                    return_value=True,
                ) as synchronous,
            ):
                self.widget.local_panel.uploadRequested.emit([str(folder)])

        incremental.assert_called_once_with([str(folder)], "/remote")
        synchronous.assert_not_called()
        RemoteDirPanel._instances.pop(self.widget.panel_scratch.panel_id, None)
        RemoteDirPanel._instances.pop(self.widget.panel_home.panel_id, None)

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

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(
                self.widget,
                "_selected_remote_paths",
                return_value=["/remote"],
            ),
            patch.object(
                panel,
                "_apply_remote_download",
                return_value=True,
            ) as synchronous,
            patch.object(
                panel,
                "_run_plan_with_progress",
                return_value=True,
            ) as run_plan,
        ):
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
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(
                panel,
                "_run_plan_with_progress",
                return_value=True,
            ) as run_plan,
        ):
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

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.performance
    def test_download_planning_uses_worker_and_returns_before_slow_probe(self) -> None:
        class SlowFiles:
            supports_parallel_transfers = False

            def __init__(self) -> None:
                self.started = threading.Event()
                self.release = threading.Event()
                self.thread_id = None

            def is_dir(self, _path: str) -> bool:
                self.thread_id = threading.get_ident()
                self.started.set()
                self.release.wait(3)
                return False

        files = SlowFiles()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(
                panel,
                "_run_plan_with_progress",
                return_value=True,
            ) as run_plan,
        ):
            started_at = time.monotonic()
            self.assertTrue(
                panel._apply_remote_download_incremental(
                    ["/remote/output.bin"],
                    tmp,
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

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.concurrency
    def test_remote_panel_drop_upload_planning_yields_before_transfer_start(self) -> None:
        class Files:
            supports_parallel_transfers = True

            def exists(self, _path: str) -> bool:
                return False

        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": Files()}
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp, "folder")
            folder.mkdir()
            for index in range(30):
                (folder / f"file-{index}.txt").write_text("x", encoding="utf-8")

            with patch.object(panel, "_run_plan_with_progress", return_value=True) as run_plan:
                self.assertTrue(panel._apply_local_upload_incremental([str(folder)], "/remote"))
                run_plan.assert_not_called()

                deadline = time.monotonic() + 3
                while time.monotonic() < deadline and not run_plan.called:
                    self.app.processEvents()
                    time.sleep(0.01)

            self.assertTrue(run_plan.called)
            plan = run_plan.call_args.args[0]
            self.assertEqual(
                len([item for item in plan if item.op == "upload"]),
                30,
            )
