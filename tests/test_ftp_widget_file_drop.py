"""Focused FTP widget tests for file drop behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import datetime
from pathlib import Path
from unittest.mock import patch
import pytest
from PySide6.QtCore import QMimeData, QUrl
from hpc_gui.services.transfer_conflict_policy import clear_session_conflict_action
from hpc_gui.ui.dialogs.transfer_conflict_dialog import (
    TransferConflictDecision,
    TransferConflictDialog,
    TransferConflictInfo,
)
from hpc_gui.ui.widgets.directories_widget import DirectoriesWidget
from hpc_gui.ui.widgets.remote_dir_panel import (
    MIME_REMOTE_PATHS,
    RemoteDirPanel,
    _DragPayload,
    _encode_payload,
)
from ftp_widget_test_support import FtpWidgetTestCase, _FakeDropEvent, _Files


class FtpWidgetFileDropTests(FtpWidgetTestCase):
    @pytest.mark.gui
    @pytest.mark.qt
    def test_conflict_dialog_exposes_requested_actions_and_checks(self) -> None:
        dialog = TransferConflictDialog(
            source=TransferConflictInfo("/source/file.txt", size=10, mtime=2),
            target=TransferConflictInfo("/target/file.txt", size=5, mtime=1),
        )
        try:
            self.assertEqual(
                set(dialog.action_buttons),
                {
                    "overwrite",
                    "overwrite_if_newer",
                    "overwrite_if_size_differs",
                    "overwrite_if_size_differs_or_newer",
                    "resume",
                    "rename",
                    "skip",
                },
            )
            dialog.action_buttons["skip"].setChecked(True)
            dialog.cb_always.setChecked(True)
            decision = dialog.decision()
            self.assertEqual(decision.action, "skip")
            self.assertTrue(decision.always_use)
            self.assertEqual(dialog.windowTitle(), "Target file already exists")
            local_ts = int(datetime.datetime(2025, 11, 16, 11, 26, 39).timestamp())
            self.assertEqual(
                TransferConflictDialog._format_time(local_ts),
                "11/16/2025 11:26:39 AM",
            )
        finally:
            dialog.deleteLater()

    @pytest.mark.unit
    def test_conditional_conflict_actions_are_resolved_safely(self) -> None:
        source = TransferConflictInfo("/source", size=10, mtime=20)
        target = TransferConflictInfo("/target", size=10, mtime=10)
        self.assertEqual(
            RemoteDirPanel._normalize_conflict_decision(
                TransferConflictDecision("overwrite_if_newer"),
                source,
                target,
            ),
            "overwrite",
        )
        self.assertEqual(
            RemoteDirPanel._normalize_conflict_decision(
                TransferConflictDecision("overwrite_if_size_differs"),
                source,
                target,
            ),
            "skip",
        )
        self.assertEqual(
            RemoteDirPanel._normalize_conflict_decision(
                TransferConflictDecision("resume"),
                source,
                target,
            ),
            "resume",
        )

    @pytest.mark.integration
    def test_always_use_conflict_action_lasts_only_for_current_process(self) -> None:
        source = TransferConflictInfo("/source", size=10, mtime=20)
        target = TransferConflictInfo("/target", size=10, mtime=10)
        first_panel = RemoteDirPanel()
        second_panel = RemoteDirPanel()
        # Reset directly rather than via patch.object: patch.object restores
        # whatever value was present on entry when its own `with` exits, which
        # would silently wipe out the session state _resolve_conflict sets
        # during the block below before the second panel gets a chance to see it.
        clear_session_conflict_action()
        try:
            with patch.object(
                TransferConflictDialog,
                "get_decision",
                return_value=TransferConflictDecision("overwrite_if_newer", always_use=True),
            ) as get_decision:
                with patch.object(first_panel, "_conflict_info", side_effect=[source, target]):
                    self.assertEqual(
                        first_panel._resolve_conflict("/target", src="/source"), "overwrite_all"
                    )

                with patch.object(second_panel, "_conflict_info", side_effect=[source, target]):
                    self.assertEqual(
                        second_panel._resolve_conflict("/target", src="/source"), "overwrite"
                    )

            self.assertEqual(get_decision.call_count, 1)
        finally:
            clear_session_conflict_action()
            first_panel.deleteLater()
            second_panel.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_local_file_drop_on_remote_panel_uploads_to_current_remote_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "drop-me.txt")
            source.write_text("drop", encoding="utf-8")
            panel = self.widget.panel_scratch
            panel.current_dir = "/remote/target"
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(source))])
            event = _FakeDropEvent(mime)

            with patch.object(
                panel, "_apply_local_upload_incremental", return_value=True
            ) as upload:
                panel.views["all"].dropEvent(event)

                upload.assert_not_called()
                self.app.processEvents()

            upload.assert_called_once()
            uploaded_paths, target_dir = upload.call_args.args
            self.assertEqual([Path(path) for path in uploaded_paths], [source])
            self.assertEqual(target_dir, "/remote/target")
            self.assertTrue(event.accepted)
            self.assertFalse(event.ignored)

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_directories_widget_accepts_local_file_drop_for_remote_upload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "drop-dir.txt")
            source.write_text("drop", encoding="utf-8")
            widget = DirectoriesWidget()
            try:
                widget.panel_scratch.current_dir = "/scratch/drop-target"
                mime = QMimeData()
                mime.setUrls([QUrl.fromLocalFile(str(source))])
                event = _FakeDropEvent(mime)

                with patch.object(
                    widget.panel_scratch,
                    "_apply_local_upload",
                    return_value=True,
                ) as upload:
                    widget.dropEvent(event)

                    upload.assert_not_called()
                    self.app.processEvents()

                upload.assert_called_once()
                uploaded_paths, target_dir = upload.call_args.args
                self.assertEqual([Path(path) for path in uploaded_paths], [source])
                self.assertEqual(target_dir, "/scratch/drop-target")
                self.assertTrue(event.accepted)
                self.assertFalse(event.ignored)
            finally:
                widget.shutdown()
                widget.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_remote_panel_accepts_local_file_drop_on_panel_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "panel-drop.txt")
            source.write_text("drop", encoding="utf-8")
            panel = self.widget.panel_scratch
            panel.current_dir = "/remote/body-target"
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(source))])
            event = _FakeDropEvent(mime)

            with patch.object(
                panel, "_apply_local_upload_incremental", return_value=True
            ) as upload:
                panel.dropEvent(event)

                upload.assert_not_called()
                self.app.processEvents()

            upload.assert_called_once()
            uploaded_paths, target_dir = upload.call_args.args
            self.assertEqual([Path(path) for path in uploaded_paths], [source])
            self.assertEqual(target_dir, "/remote/body-target")
            self.assertTrue(event.accepted)
            self.assertFalse(event.ignored)

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_remote_file_drop_on_local_panel_downloads_after_drop_event(self) -> None:
        panel = self.widget.panel_scratch
        panel.current_dir = "/remote"
        remote_path = "/remote/result.txt"
        mime = QMimeData()
        mime.setData(
            MIME_REMOTE_PATHS,
            _encode_payload(_DragPayload(paths=[remote_path], src_panel_id=panel.panel_id)),
        )
        event = _FakeDropEvent(mime)

        with patch.object(
            panel,
            "_apply_remote_download_incremental",
            return_value=True,
        ) as download:
            self.widget.local_panel.tree.dropEvent(event)

            download.assert_not_called()
            self.app.processEvents()

        download.assert_called_once_with([remote_path], self.widget.local_panel.current_dir)
        self.assertTrue(event.accepted)
        self.assertFalse(event.ignored)

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
