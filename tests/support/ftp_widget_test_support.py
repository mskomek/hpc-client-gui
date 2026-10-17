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
from hpc_gui.ui.dialogs.settings_dialog import SettingsDialog
from hpc_gui.ui.main_window import MainWindow
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
from hpc_gui.services.files_base import RemoteEntry
from hpc_gui.services.files_ssh import SSHFilesBackend
from hpc_gui.core.i18n import load_language


class _Files:
    def __init__(self) -> None:
        self.remote: dict[str, bytes] = {}

    def listdir_entries(self, _path: str):
        return [
            RemoteEntry(
                name=Path(path).name,
                path=path,
                is_dir=False,
                size=len(data),
                mtime=1,
            )
            for path, data in self.remote.items()
        ]

    def exists(self, path: str) -> bool:
        return path in self.remote

    def is_dir(self, _path: str) -> bool:
        return False

    def upload(self, local_path: str, remote_path: str) -> None:
        self.remote[remote_path] = Path(local_path).read_bytes()

    def download(self, remote_path: str, local_path: str) -> None:
        Path(local_path).write_bytes(self.remote[remote_path])

    def stat(self, remote_path: str):
        data = self.remote.get(remote_path, b"")
        return len(data), 1

    def rename(self, old_path: str, new_path: str) -> None:
        self.remote[new_path] = self.remote.pop(old_path, b"")


class _CountingFiles:
    def __init__(self) -> None:
        self.calls: list[str] = []
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

    def listdir_entries(self, path: str):
        key = (path or "/").rstrip("/") or "/"
        self.calls.append(key)
        return list(self.entries.get(key, []))

    def exists(self, path: str) -> bool:
        key = (path or "/").rstrip("/") or "/"
        return key in self.dirs

    def is_dir(self, path: str) -> bool:
        key = (path or "/").rstrip("/") or "/"
        return key in self.dirs


class _ResumableFiles:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.calls: list[str] = []

    def download(self, _remote_path: str, local_path: str, progress_cb=None) -> None:
        self.calls.append(local_path)
        existing = Path(local_path).read_bytes() if Path(local_path).exists() else b""
        Path(local_path).write_bytes(existing + self.data[len(existing):])
        if progress_cb is not None:
            progress_cb(len(self.data), len(self.data))


class _ProgressUploadFiles:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def upload(self, local_path: str, remote_path: str, progress_cb=None) -> None:
        self.calls.append((local_path, remote_path))
        size = Path(local_path).stat().st_size
        if progress_cb is not None:
            progress_cb(size, size)


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
    'os',
    'sys',
    'stat',
    'tempfile',
    'threading',
    'time',
    'unittest',
    'datetime',
    'Path',
    'SimpleNamespace',
    'patch',
    'pytest',
    'QEvent',
    'QMimeData',
    'QPoint',
    'Qt',
    'QUrl',
    'QKeyEvent',
    'QApplication',
    'QDialog',
    'QPlainTextEdit',
    'QMessageBox',
    'MockFilesBackend',
    'ASCII',
    'AUTO',
    'BINARY',
    '_ascii_bytes_for_local',
    '_ascii_bytes_for_remote',
    'download_with_mode',
    'resolve_transfer_mode',
    'upload_with_mode',
    'GENERIC_SLURM_DEFAULTS',
    'save_user_system_template',
    't',
    'ConnectionDialog',
    'TransferConflictDecision',
    'TransferConflictDialog',
    'TransferConflictInfo',
    'TransferDialog',
    'TransferItem',
    'TransferPreflightDialog',
    'SettingsDialog',
    'MainWindow',
    'DirectoriesWidget',
    '_BatchSubmitWorker',
    '_ShellRunWorker',
    'FtpWidget',
    'LOCAL_CONTEXT_MENU_LABELS',
    'FTP_TEST_MODE_ENV',
    'LoginWidget',
    'is_ftp_mock_host',
    'is_ftp_test_mode_enabled',
    'DIRECTORY_CACHE_TTL_SECONDS',
    'MIME_REMOTE_PATHS',
    'REMOTE_CONTEXT_MENU_LABELS',
    'RemoteDirPanel',
    '_DragPayload',
    '_PlannedOp',
    '_PermissionsDialog',
    '_encode_payload',
    'RemoteEntry',
    'SSHFilesBackend',
    'load_language',
    '_Files',
    '_CountingFiles',
    '_ResumableFiles',
    '_ProgressUploadFiles',
    '_DropPosition',
    '_FakeDropEvent',
    'FtpWidgetTestCase',
]
