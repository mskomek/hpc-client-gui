from __future__ import annotations

import os
import sys
import stat
import tempfile
import threading
import time
import unittest
import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QDialog, QPlainTextEdit, QMessageBox

from hpc_gui.services.files_mock import MockFilesBackend
from hpc_gui.services.transfer_conflict_policy import clear_session_conflict_action
from hpc_gui.services.transfer_mode import (
    ASCII,
    AUTO,
    BINARY,
    _ascii_bytes_for_local,
    _ascii_bytes_for_remote,
    download_with_mode,
    resolve_transfer_mode,
    upload_with_mode,
)
from hpc_gui.config.system_profile import (
    GENERIC_SLURM_DEFAULTS,
    save_user_system_template,
)
from hpc_gui.core.i18n import t
from hpc_gui.ui.dialogs.connection_dialog import ConnectionDialog
from hpc_gui.ui.dialogs.transfer_conflict_dialog import (
    TransferConflictDecision,
    TransferConflictDialog,
    TransferConflictInfo,
)
from hpc_gui.ui.dialogs.transfer_dialog import (
    TransferDialog,
    TransferItem,
    TransferPreflightDialog,
)
from hpc_gui.ui.widgets.directories_widget import (
    DirectoriesWidget,
    _BatchSubmitWorker,
    _ShellRunWorker,
)
from hpc_gui.ui.widgets.ftp_widget import FtpWidget
from hpc_gui.ui.widgets.local_dir_panel import LOCAL_CONTEXT_MENU_LABELS
from hpc_gui.ui.widgets.login_widget import (
    FTP_TEST_MODE_ENV,
    LoginWidget,
    is_ftp_mock_host,
    is_ftp_test_mode_enabled,
)
from hpc_gui.ui.widgets.remote_dir_panel import (
    DIRECTORY_CACHE_TTL_SECONDS,
    MIME_REMOTE_PATHS,
    REMOTE_CONTEXT_MENU_LABELS,
    RemoteDirPanel,
    _DragPayload,
    _PlannedOp,
    _PermissionsDialog,
    _encode_payload,
)
from hpc_gui.services.files_ssh import SSHFilesBackend
from hpc_gui.core.i18n import load_language
from support.ftp_widget_backend_fakes import (
    RemoteEntry,
    _CountingFiles,
    _Files,
    _ProgressUploadFiles,
    _ResumableFiles,
)


class _DropPosition:
    def toPoint(self) -> QPoint:
        return QPoint(0, 0)


class _FakeDropEvent:
    def __init__(self, mime: QMimeData, pos: QPoint | None = None) -> None:
        self._mime = mime
        self._pos = pos or QPoint(0, 0)
        self.accepted = False
        self.ignored = False

    def mimeData(self) -> QMimeData:
        return self._mime

    def position(self) -> _DropPosition:
        return _DropPosition()

    def pos(self) -> QPoint:
        return self._pos

    def acceptProposedAction(self) -> None:
        self.accepted = True

    def ignore(self) -> None:
        self.ignored = True


class FtpWidgetTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        load_language("en")

    def setUp(self) -> None:
        self.state_patch = patch(
            "hpc_gui.ui.widgets.ftp_widget.get_ftp_state",
            return_value={
                "local_dir": os.getcwd(),
                "active_remote": "scratch",
                "splitter_sizes": [500, 500],
            },
        )
        self.type_patch = patch(
            "hpc_gui.ui.widgets.ftp_widget.get_ftp_transfer_type",
            return_value=AUTO,
        )
        self.update_patch = patch(
            "hpc_gui.ui.widgets.ftp_widget.update_ftp_state",
            return_value={},
        )
        self.state_patch.start()
        self.type_patch.start()
        self.update_patch.start()
        self.widget = FtpWidget()

    @staticmethod
    def _run_plan_synchronously(
        panel: RemoteDirPanel,
        plan,
        _title: str,
        after_finished=None,
        *,
        confirm_before_start: bool = False,
    ) -> bool:
        for item in plan:
            panel._execute_transfer_item(
                SimpleNamespace(
                    op=item.op,
                    src=item.src,
                    dst=item.dst,
                    recursive=item.recursive,
                )
            )
        if after_finished is not None:
            after_finished()
        return True

    def tearDown(self) -> None:
        from hpc_gui.services.file_clipboard import get_file_clipboard

        QApplication.processEvents()
        self.widget.shutdown()
        get_file_clipboard().clear()
        self.widget.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QApplication.processEvents()
        self.update_patch.stop()
        self.type_patch.stop()
        self.state_patch.stop()


__all__ = [
    'ASCII',
    'AUTO',
    'BINARY',
    'ConnectionDialog',
    'DIRECTORY_CACHE_TTL_SECONDS',
    'DirectoriesWidget',
    'FTP_TEST_MODE_ENV',
    'FtpWidget',
    'FtpWidgetTestCase',
    'GENERIC_SLURM_DEFAULTS',
    'LOCAL_CONTEXT_MENU_LABELS',
    'LoginWidget',
    'MIME_REMOTE_PATHS',
    'MockFilesBackend',
    'Path',
    'QApplication',
    'QDialog',
    'QEvent',
    'QKeyEvent',
    'QMessageBox',
    'QMimeData',
    'QPlainTextEdit',
    'QPoint',
    'QUrl',
    'Qt',
    'REMOTE_CONTEXT_MENU_LABELS',
    'RemoteDirPanel',
    'RemoteEntry',
    'SSHFilesBackend',
    'SimpleNamespace',
    'TransferConflictDecision',
    'TransferConflictDialog',
    'TransferConflictInfo',
    'TransferDialog',
    'TransferItem',
    'TransferPreflightDialog',
    '_BatchSubmitWorker',
    '_CountingFiles',
    '_DragPayload',
    '_DropPosition',
    '_FakeDropEvent',
    '_Files',
    '_PermissionsDialog',
    '_PlannedOp',
    '_ProgressUploadFiles',
    '_ResumableFiles',
    '_ShellRunWorker',
    '_ascii_bytes_for_local',
    '_ascii_bytes_for_remote',
    '_encode_payload',
    'annotations',
    'clear_session_conflict_action',
    'datetime',
    'download_with_mode',
    'is_ftp_mock_host',
    'is_ftp_test_mode_enabled',
    'load_language',
    'os',
    'patch',
    'pytest',
    'resolve_transfer_mode',
    'save_user_system_template',
    'stat',
    'sys',
    't',
    'tempfile',
    'threading',
    'time',
    'unittest',
    'upload_with_mode',
]
