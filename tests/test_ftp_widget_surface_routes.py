"""Focused FTP widget tests for surface routes behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import time
from pathlib import Path
from unittest.mock import patch
import pytest
from PySide6.QtCore import Qt
from hpc_gui.ui.widgets.remote_dir_panel import _PlannedOp
from ftp_widget_test_support import FtpWidgetTestCase, _Files


class FtpWidgetSurfaceRoutesTests(FtpWidgetTestCase):
    @pytest.mark.gui
    @pytest.mark.qt
    def test_layout_and_exclusive_remote_sections(self) -> None:
        self.assertEqual(self.widget.splitter.count(), 2)
        self.assertEqual(self.widget.accordion.active_key, "scratch")
        self.widget.accordion.set_active("home")
        self.assertEqual(self.widget.active_remote_panel(), self.widget.panel_home)
        self.assertFalse(self.widget.panel_scratch.isVisible())

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
            patch.object(self.widget, "_selected_remote_paths", return_value=["/remote/out.txt"]),
            patch.object(
                self.widget.panel_scratch,
                "_apply_remote_download_incremental",
                return_value=True,
            ) as download,
        ):
            self.assertTrue(self.widget.download_selected())
        download.assert_called_once_with(["/remote/out.txt"], self.widget.local_panel.current_dir)

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

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(
                panel,
                "_run_plan_with_progress",
                side_effect=capture,
            ),
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
