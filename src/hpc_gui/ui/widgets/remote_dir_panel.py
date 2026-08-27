from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import stat as pystat
import threading
import weakref
from time import monotonic
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Generator, Iterable, List, Optional, Tuple

from shiboken6 import isValid

from PySide6.QtCore import (
    QEvent,
    Q_ARG,
    QMetaObject,
    QMimeData,
    QObject,
    QPoint,
    QRunnable,
    QThread,
    QThreadPool,
    QTimer,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QDrag, QIcon, QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QListWidget,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStyle,
    QTabBar,
    QToolButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hpc_gui.core.debug_telemetry import is_source_run
from hpc_gui.core.i18n import t
from hpc_gui.core.logging import get_logger
from hpc_gui.core.ui_errors import show_exception
from hpc_gui.config.storage import (
    get_remote_directory_cache_enabled,
    coerce_profile_transfer_parallelism,
    get_upload_preflight_confirmation_enabled,
    get_transfer_checksum_verification_enabled,
    get_profile_conflict_action,
    get_profile_id,
    set_profile_conflict_action,
    clear_profile_conflict_action,
    set_upload_preflight_confirmation_enabled,
)
from hpc_gui.services.file_clipboard import get_file_clipboard
from hpc_gui.services.files_base import RemoteEntry
from hpc_gui.services.directory_comparison import CompareStatus, ComparableEntry
from hpc_gui.services.remote_navigation_store import navigation_store_for_profile
from hpc_gui.services.transfer_mode import (
    BINARY,
    PARTIAL_SUFFIX as PARTIAL_DOWNLOAD_SUFFIX,
    download_with_mode,
    normalize_transfer_mode,
    upload_with_mode,
)
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
from hpc_gui.ui.models.remote_entry_helpers import (
    category as _category,
    file_type as _file_type,
    fmt_mtime as _fmt_mtime,
    fmt_size as _fmt_size,
    natural_sort_key as _natural_sort_key,
)

logger = logging.getLogger(__name__)


MIME_REMOTE_PATHS = "application/x-truba-remote-paths"
# Short enough that a directory a running job writes into does not stay stale
# on screen; long enough that back/up navigation is still instant.
DIRECTORY_CACHE_TTL_SECONDS = 60.0

# Flush a partial listing to the tree at whichever limit trips first, so a
# slow directory paints early without one repaint per entry.
LISTING_BATCH_SIZE = 200
LISTING_BATCH_INTERVAL_SECONDS = 0.05


class _DirectoryListingSignals(QObject):
    batch = Signal(object, object)
    finished = Signal(object)
    failed = Signal(object, object)
    # Always emitted once the run ends, cancelled or not, so the panel knows
    # the shared listing channel is free and a coalesced request may start.
    settled = Signal(object)


class _DirectoryListingWorker(QRunnable):
    """Stream one remote directory listing off the GUI thread.

    Cancelling abandons the backend iterator, which releases the shared
    listing channel, so a fast A->B->C navigation does not keep paying for
    A's traffic.
    """

    def __init__(self, token: object, files, remote_dir: str) -> None:
        super().__init__()
        self.token = token
        self.signals = _DirectoryListingSignals()
        self._files = files
        self._remote_dir = remote_dir
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    @Slot()
    def run(self) -> None:
        try:
            self._run()
        finally:
            self.signals.settled.emit(self.token)

    def _run(self) -> None:
        batch: List[RemoteEntry] = []
        try:
            deadline = monotonic() + LISTING_BATCH_INTERVAL_SECONDS
            for entry in self._files.iterdir_entries(self._remote_dir):
                if self._cancelled.is_set():
                    return
                batch.append(entry)
                if len(batch) >= LISTING_BATCH_SIZE or monotonic() >= deadline:
                    self.signals.batch.emit(self.token, batch)
                    batch = []
                    deadline = monotonic() + LISTING_BATCH_INTERVAL_SECONDS
        except Exception as exc:
            if not self._cancelled.is_set():
                self.signals.failed.emit(self.token, exc)
            return
        if self._cancelled.is_set():
            return
        if batch:
            self.signals.batch.emit(self.token, batch)
        self.signals.finished.emit(self.token)


class _RemoteLintSignals(QObject):
    finished = Signal(object)
    failed = Signal(object)


class _RemoteLintWorker(QRunnable):
    """Read and lint a remote folder without blocking the Qt event loop."""

    # ponytail: cap remote scans at 200 files; add paged/cancellable scanning if needed.
    MAX_FILES = 200

    def __init__(self, files, remote_dir: str) -> None:
        super().__init__()
        self.files = files
        self.remote_dir = remote_dir.rstrip("/") or "/"
        self.signals = _RemoteLintSignals()

    @Slot()
    def run(self) -> None:
        try:
            from hpc_gui.plugins.linter_tools import lint_text_with_tool, supported_suffixes

            supported = supported_suffixes()
            paths: list[str] = []
            pending = [self.remote_dir]
            while pending and len(paths) < self.MAX_FILES:
                current = pending.pop()
                for entry in self.files.listdir_entries(current):
                    path = entry.path.rstrip("/")
                    if entry.is_dir:
                        pending.append(path)
                    elif RemoteDirPanel._remote_suffix(path) in supported:
                        paths.append(path)
                        if len(paths) >= self.MAX_FILES:
                            break
            results = [
                lint_text_with_tool(self.files.read_text(path), file_name=path)
                for path in paths
            ]
            self.signals.finished.emit((paths, results))
        except Exception as exc:
            self.signals.failed.emit(exc)


REMOTE_CONTEXT_MENU_LABELS = [
    "Download",
    "Add files to queue",
    "View/Edit",
    "Open in new tab",
    "---",
    "Create directory",
    "Create directory and enter it",
    "Create new file",
    "Refresh",
    "---",
    "Delete",
    "Rename",
    "Copy URL(s) to clipboard",
    "File permissions...",
]

_SORT_NAME_ROLE = Qt.ItemDataRole.UserRole + 10
_SORT_SIZE_ROLE = Qt.ItemDataRole.UserRole + 11
_SORT_TYPE_ROLE = Qt.ItemDataRole.UserRole + 12
_SORT_MTIME_ROLE = Qt.ItemDataRole.UserRole + 13
_FILE_MODE_ROLE = Qt.ItemDataRole.UserRole + 20


def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if value == f"[{key}]" else value


class _PermissionsDialog(QDialog):
    _GROUPS = (
        ("dirs.permissions_owner", "Owner"),
        ("dirs.permissions_group", "Group"),
        ("dirs.permissions_others", "Others"),
    )
    _PERMISSIONS = (
        ("dirs.permissions_read", "Read", 0o4),
        ("dirs.permissions_write", "Write", 0o2),
        ("dirs.permissions_execute", "Execute", 0o1),
    )
    _SPECIAL_PERMISSIONS = (
        ("dirs.permissions_setuid", "Set-user-ID", 0o4000),
        ("dirs.permissions_setgid", "Set group-ID", 0o2000),
        ("dirs.permissions_sticky", "Sticky bit", 0o1000),
    )

    def __init__(self, parent: QWidget, initial_mode: Optional[int], target_name: str = "") -> None:
        super().__init__(parent)
        self._syncing = False
        self._boxes: Dict[Tuple[int, int], QCheckBox] = {}
        self._special_boxes: Dict[int, QCheckBox] = {}
        self.setWindowTitle(_tr("dirs.permissions_change_title", "Change file attributes"))
        self.setModal(True)

        layout = QVBoxLayout(self)

        intro = QLabel(
            _tr(
                "dirs.permissions_intro",
                'Please select the new attributes for the selected item "{name}".',
            ).format(name=target_name or _tr("dirs.permissions_selected_items", "selected items"))
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        for group_index, (group_key, group_fallback) in enumerate(self._GROUPS):
            box_group = QGroupBox(
                _tr("dirs.permissions_group_title", "{group} permissions").format(
                    group=_tr(group_key, group_fallback)
                )
            )
            row = QHBoxLayout(box_group)
            for permission_index, (key, fallback, _bit) in enumerate(self._PERMISSIONS):
                box = QCheckBox()
                box.setText(_tr(key, fallback))
                box.stateChanged.connect(self._update_code_from_checks)
                row.addWidget(box)
                self._boxes[(permission_index, group_index)] = box
            row.addStretch(1)
            layout.addWidget(box_group)

        special_group = QGroupBox(_tr("dirs.permissions_special_title", "Public permissions"))
        special_row = QHBoxLayout(special_group)
        for key, fallback, bit in self._SPECIAL_PERMISSIONS:
            box = QCheckBox(_tr(key, fallback))
            box.stateChanged.connect(self._update_code_from_checks)
            special_row.addWidget(box)
            self._special_boxes[bit] = box
        special_row.addStretch(1)
        layout.addWidget(special_group)

        code_row = QHBoxLayout()
        code_row.addWidget(QLabel(_tr("dirs.permissions_chmod_label", "Chmod:")))
        self.mode_edit = QLineEdit()
        self.mode_edit.setMaxLength(5)
        self.mode_edit.setPlaceholderText("00755")
        self.mode_edit.textEdited.connect(self._update_checks_from_code)
        code_row.addWidget(self.mode_edit)
        layout.addLayout(code_row)

        help_label = QLabel(
            _tr(
                "dirs.permissions_help",
                "You can enter a textual mode change (chmod), or the new mode bits in octal.",
            )
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        self.recurse_check = QCheckBox(_tr("dirs.permissions_recurse", "Recurse into subdirectories"))
        self.recurse_check.setEnabled(False)
        layout.addWidget(self.recurse_check)
        self.recurse_all_radio = QRadioButton(
            _tr("dirs.permissions_recurse_all", "Apply to all files and directories")
        )
        self.recurse_files_radio = QRadioButton(
            _tr("dirs.permissions_recurse_files", "Apply to files only")
        )
        self.recurse_dirs_radio = QRadioButton(
            _tr("dirs.permissions_recurse_dirs", "Apply to directories only")
        )
        self.recurse_all_radio.setChecked(True)
        for radio in (self.recurse_all_radio, self.recurse_files_radio, self.recurse_dirs_radio):
            radio.setEnabled(False)
            layout.addWidget(radio)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._set_checks_from_mode(0o644 if initial_mode is None else pystat.S_IMODE(initial_mode))
        self._update_code_from_checks()

    def _mode_from_checks(self) -> int:
        mode = 0
        for group_index in range(3):
            digit = 0
            for permission_index, (_key, _fallback, bit) in enumerate(self._PERMISSIONS):
                if self._boxes[(permission_index, group_index)].isChecked():
                    digit |= bit
            mode = (mode << 3) | digit
        for bit, box in self._special_boxes.items():
            if box.isChecked():
                mode |= bit
        return mode

    def _set_checks_from_mode(self, mode: int) -> None:
        self._syncing = True
        try:
            plain_mode = mode & 0o7777
            for bit, box in self._special_boxes.items():
                box.setChecked(bool(plain_mode & bit))
            for group_index in range(3):
                shift = (2 - group_index) * 3
                digit = (plain_mode >> shift) & 0o7
                for permission_index, (_key, _fallback, bit) in enumerate(self._PERMISSIONS):
                    self._boxes[(permission_index, group_index)].setChecked(bool(digit & bit))
        finally:
            self._syncing = False

    def _update_code_from_checks(self) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            self.mode_edit.setText(f"0{self._mode_from_checks():04o}")
        finally:
            self._syncing = False

    def _update_checks_from_code(self, value: str) -> None:
        if self._syncing:
            return
        mode = RemoteDirPanel._parse_chmod_mode(value)
        if mode is None:
            return
        self._set_checks_from_mode(mode)

    def selected_mode(self) -> Optional[int]:
        return RemoteDirPanel._parse_chmod_mode(self.mode_edit.text())

    def accept(self) -> None:
        if self.selected_mode() is None:
            QMessageBox.warning(
                self,
                t("common.error"),
                _tr("dirs.permissions_invalid", "Enter a valid octal mode such as 755 or 0644."),
            )
            return
        super().accept()


@dataclass
class _DragPayload:
    paths: List[str]
    src_panel_id: str


def _encode_payload(payload: _DragPayload) -> bytes:
    return json.dumps({"paths": payload.paths, "src_panel_id": payload.src_panel_id}).encode("utf-8")


def _decode_payload(raw: bytes) -> Optional[_DragPayload]:
    try:
        obj = json.loads(raw.decode("utf-8"))
        paths = [str(p) for p in obj.get("paths", []) if p]
        src_panel_id = str(obj.get("src_panel_id", ""))
        if not paths or not src_panel_id:
            return None
        return _DragPayload(paths=paths, src_panel_id=src_panel_id)
    except Exception:
        return None


@dataclass
class _PlannedOp:
    op: str  # "copy" | "move" | "delete"
    src: str
    dst: str
    recursive: Optional[bool] = False
    size: Optional[int] = None  # known size, only when the listing already carries it


@dataclass
class _LocalUploadPlanJob:
    steps: Generator[None, None, Optional[List[_PlannedOp]]]
    dest_dir: str


class _TransferPlanWorker(QObject):
    finished = Signal(int, str, object)
    failed = Signal(int, str, object)

    def __init__(self, job_id: int, kind: str, planner, panel: "RemoteDirPanel") -> None:
        super().__init__()
        self.job_id = job_id
        self.kind = kind
        self._planner = planner
        self._panel = panel
        self.cancelled = False
        self._pending_source = None
        self._pending_target = None
        self._pending_partial = False
        self._pending_decision = "cancel"
        self._pending_rename_dir = ""
        self._pending_rename_name = ""
        self._pending_rename_result = None

    @Slot()
    def run(self) -> None:
        try:
            result = self._planner(self)
        except Exception as exc:
            self.failed.emit(self.job_id, self.kind, exc)
            return
        self.finished.emit(self.job_id, self.kind, result)

    def request_conflict_decision(self, source, target, *, partial: bool = False) -> str:
        """Show the conflict dialog on the GUI thread and return the raw action.

        Called from the worker thread while planning. Blocks until the GUI
        thread has shown the decision dialog and normalized the result, so all
        remote stat probes stay off the GUI event loop.
        """
        self._pending_source = source
        self._pending_target = target
        self._pending_partial = bool(partial)
        self._pending_decision = "cancel"
        QMetaObject.invokeMethod(
            self._panel,
            "_resolve_conflict_from_worker",
            Qt.ConnectionType.BlockingQueuedConnection,
            Q_ARG("int", self.job_id),
        )
        return self._pending_decision

    def request_rename(self, dst_dir: str, current_name: str) -> Optional[str]:
        """Prompt for a new target name on the GUI thread and return it."""
        self._pending_rename_dir = dst_dir
        self._pending_rename_name = current_name
        self._pending_rename_result = None
        QMetaObject.invokeMethod(
            self._panel,
            "_prompt_rename_from_worker",
            Qt.ConnectionType.BlockingQueuedConnection,
            Q_ARG("int", self.job_id),
        )
        return self._pending_rename_result


@dataclass
class _UndoRecord:
    kind: str  # currently only "move"
    moves: List[Tuple[str, str]]  # (src, dst) executed


class _FileOpWorker(QObject):
    progress = Signal(int, str)  # step, label
    finished = Signal(bool, str)  # cancelled, message

    def __init__(self, files_backend, plan: List[_PlannedOp]):
        super().__init__()
        self._files = files_backend
        self._plan = plan
        self._cancel = False

    @Slot()
    def cancel(self) -> None:
        self._cancel = True

    @Slot()
    def run(self) -> None:
        total = len(self._plan)
        for i, op in enumerate(self._plan, start=1):
            if self._cancel:
                self.finished.emit(True, "İptal edildi.")
                return
            label = f"{i}/{total}: {os.path.basename((op.dst or op.src).rstrip('/'))}"
            self.progress.emit(i, label)
            try:
                if op.op == "delete":
                    # delete remote path (dst)
                    self._files.remove(op.dst, recursive=op.recursive)
                elif op.op == "copy":
                    self._files.copy(op.src, op.dst, recursive=op.recursive)
                elif op.op == "move":
                    self._files.move(op.src, op.dst)
                elif op.op == "upload":
                    # upload local (src) -> remote (dst)
                    self._files.upload(op.src, op.dst)
                elif op.op == "download":
                    # download remote (src) -> local (dst)
                    self._files.download_toggle(op.src, op.dst) if hasattr(self._files, 'download_toggle') else self._files.download(op.src, op.dst)
                elif op.op == "mkdir_remote":
                    self._files.mkdir(op.dst)
                elif op.op == "mkdir_local":
                    os.makedirs(op.dst, exist_ok=True)
                elif op.op == "delete_local":
                    # delete local path (dst)
                    if os.path.isdir(op.dst):
                        shutil.rmtree(op.dst, ignore_errors=True)
                    else:
                        try:
                            os.remove(op.dst)
                        except FileNotFoundError:
                            pass
                else:
                    raise RuntimeError(f"Unknown op: {op.op}")
            except Exception as e:
                self.finished.emit(False, f"{label}\n{e}")
                return
        self.finished.emit(False, "")


class _RemoteTree(QTreeWidget):
    """A QTreeWidget that supports drag/drop between RemoteDirPanel instances."""

    def __init__(self, panel: "RemoteDirPanel"):
        super().__init__()
        self._panel = panel
        self._sort_column: Optional[int] = None
        self._sort_order = Qt.SortOrder.AscendingOrder

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.header().setSectionsClickable(True)
        self.header().setSortIndicatorShown(False)
        self.header().sectionClicked.connect(self._on_header_clicked)

    def _on_header_clicked(self, column: int) -> None:
        if column < 0 or column >= 4:
            return
        if self._sort_column == column:
            self._sort_order = (
                Qt.SortOrder.DescendingOrder
                if self._sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self._sort_column = column
            self._sort_order = Qt.SortOrder.AscendingOrder
        self.header().setSortIndicatorShown(True)
        self.header().setSortIndicator(column, self._sort_order)
        self.apply_sort()

    def apply_sort(self) -> None:
        if self.topLevelItemCount() < 2:
            return
        # Entries stream in arrival order, so an untouched header still has to
        # impose the default name-ascending grouping once the listing lands.
        column = 0 if self._sort_column is None else self._sort_column
        reverse = (
            self._sort_column is not None
            and self._sort_order == Qt.SortOrder.DescendingOrder
        )

        items = [self.takeTopLevelItem(0) for _ in range(self.topLevelItemCount())]
        parent_items = [item for item in items if bool(item.data(0, Qt.ItemDataRole.UserRole + 2))]
        folders = [
            item
            for item in items
            if item not in parent_items and bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
        ]
        files = [
            item
            for item in items
            if item not in parent_items and not bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
        ]

        def key(item: QTreeWidgetItem):
            role = (
                _SORT_NAME_ROLE,
                _SORT_SIZE_ROLE,
                _SORT_TYPE_ROLE,
                _SORT_MTIME_ROLE,
            )[column]
            value = item.data(0, role)
            if column in (0, 2):
                return _natural_sort_key(str(value or ""))
            return int(value or 0)

        self.addTopLevelItems(
            parent_items
            + sorted(folders, key=key, reverse=reverse)
            + sorted(files, key=key, reverse=reverse)
        )

    def startDrag(self, supportedActions: Qt.DropActions) -> None:  # type: ignore[override]
        paths = self._panel._selected_paths_from_view(self)
        if not paths:
            return
        mime = QMimeData()
        mime.setData(MIME_REMOTE_PATHS, _encode_payload(_DragPayload(paths=paths, src_panel_id=self._panel.panel_id)))

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.MiddleButton:
            item = self.itemAt(event.position().toPoint())
            if item is not None:
                remote_path = str(
                    item.data(0, Qt.ItemDataRole.UserRole) or ""
                )
                is_dir = bool(
                    item.data(0, Qt.ItemDataRole.UserRole + 1)
                )
                is_parent = bool(
                    item.data(0, Qt.ItemDataRole.UserRole + 2)
                )
                if remote_path and is_dir and not is_parent:
                    self._panel.open_directory_in_new_tab(remote_path)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):  # type: ignore[override]
        md = event.mimeData()
        if md.hasFormat(MIME_REMOTE_PATHS):
            event.acceptProposedAction()
            return
        if self._panel._local_paths_from_mime(md):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):  # type: ignore[override]
        md = event.mimeData()
        if md.hasFormat(MIME_REMOTE_PATHS):
            event.acceptProposedAction()
            return
        if self._panel._local_paths_from_mime(md):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):  # type: ignore[override]
        md = event.mimeData()
        # 1) Remote->Remote drag payload
        if md.hasFormat(MIME_REMOTE_PATHS):
            raw = bytes(md.data(MIME_REMOTE_PATHS))
            payload = _decode_payload(raw)
            if not payload:
                return

            # Determine destination directory: drop on folder => into that folder, else current dir.
            dest_dir = self._panel.current_dir or "/"
            item = self.itemAt(event.position().toPoint())  # Qt6
            if item is not None:
                clicked_path = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
                clicked_is_dir = bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
                if clicked_path and clicked_is_dir:
                    dest_dir = clicked_path.rstrip("/")

            # Decide copy vs move: Ctrl => copy, else move.
            is_copy = bool(event.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier)

            event.acceptProposedAction()
            QTimer.singleShot(
                0,
                lambda paths=list(payload.paths), target=dest_dir, copy=is_copy, source=payload.src_panel_id: (
                    self._panel._apply_drag_drop(paths, target, is_copy=copy, src_panel_id=source)
                ),
            )
            return

        # 2) Local->Remote OS drag (upload)
        local_paths = self._panel._local_paths_from_mime(md)
        if local_paths:
            dest_dir = self._panel._drop_dest_dir_for_item(
                self.itemAt(event.position().toPoint())
            )
            event.acceptProposedAction()
            QTimer.singleShot(
                0,
                lambda paths=list(local_paths), target=dest_dir: self._panel._apply_local_upload_incremental(paths, target),
            )
            return

        return super().dropEvent(event)


class RemoteDirPanel(QWidget):
    open_file = Signal(str)  # remote path (file double click)
    open_file_in_new_window = Signal(str)
    file_activated = Signal(str)
    download_requested = Signal(list)  # remote paths -> FTP widget's local panel
    save_as_requested = Signal(list)  # remote paths -> user-selected local folder
    open_in_slot = Signal(int, str)  # slot_index(0/1), remote path
    open_in_slot_new_window = Signal(int, str)
    open_in_slot_new_tab = Signal(int, str)
    open_in_existing_follower = Signal(str, int, str)
    open_file_follow_new_window = Signal(str)
    submit_requested = Signal(str)  # remote Slurm script path
    batch_submit_requested = Signal(list)  # remote Slurm script paths (sorted, case-insensitive)
    batch_shell_requested = Signal(list)  # remote shell script paths (sorted, case-insensitive)
    run_shell_requested = Signal(str)  # remote shell script path
    set_default_requested = Signal()
    directoryChanged = Signal(str)
    directoryLoaded = Signal(str)

    # registry to refresh source/target panels on move
    _instances: Dict[str, "RemoteDirPanel"] = {}

    # single-level undo (last operation)
    _last_undo: Optional[_UndoRecord] = None

    # This is deliberately process-local.  "Always use this action" is a
    # convenience for the current run, not a persisted preference: a fresh
    # application launch must ask about the first conflict again.
    _session_conflict_action: Optional[str] = None

    @classmethod
    def clear_all_directory_caches(cls) -> None:
        """Drop cached listings for every currently open remote panel."""
        for panel in list(cls._instances.values()):
            try:
                panel._directory_cache.clear()
            except RuntimeError:
                continue

    def __init__(self, title: str = ""):
        super().__init__()
        self.session = None
        self.enable_output_menu = False  # JobsOutputsWidget can turn this on
        self.default_location_label = ""
        self.current_dir = ""
        self._category_dir = ""
        self.title = title
        self._snapshot_dir = ""
        self._snapshot_entries: List[ComparableEntry] = []
        self._comparison_statuses: Optional[dict] = None
        self._transfer_mode_provider: Optional[Callable[[str], str]] = None
        self._output_target_provider: Optional[
            Callable[[], List[Tuple[str, str]]]
        ] = None
        self._transfer_activity_callback: Optional[
            Callable[[str, List[TransferItem], str], None]
        ] = None
        self._local_target_refresh_callback: Optional[Callable[[str], None]] = None
        self._transfer_dialogs: List[TransferDialog] = []
        self._active_transfer_keys: set[tuple[str, str, str]] = set()
        self._local_upload_plan_jobs: Dict[int, _LocalUploadPlanJob] = {}
        self._next_local_upload_plan_id = 0
        self._planning_jobs: Dict[int, Tuple[QThread, _TransferPlanWorker]] = {}
        self._next_planning_job_id = 0
        self._show_transfer_dialog = True
        self._directory_cache: Dict[str, Tuple[float, List[RemoteEntry]]] = {}
        self._listing_generation = 0
        self._listing_worker: Optional[_DirectoryListingWorker] = None
        self._remote_lint_worker: Optional[_RemoteLintWorker] = None
        self._pending_listing: Optional[Tuple[object, str]] = None
        self._dirty_views: set[str] = set()
        self._navigation_store = None
        self._pending_select_name = ""
        self._streaming_key = ""
        self._streaming_entries: List[RemoteEntry] = []

        self.panel_id = str(id(self))
        RemoteDirPanel._instances[self.panel_id] = self
        panel_ref = weakref.ref(self)
        self.destroyed.connect(
            lambda _object=None, panel_id=self.panel_id, expected_ref=panel_ref: (
                RemoteDirPanel._unregister_instance_ref(
                    panel_id,
                    expected_ref,
                )
            )
        )
        self.setAcceptDrops(True)

        self.lbl = QLabel(title)
        self.path = QLineEdit()
        self.path.returnPressed.connect(self._open_path_field)

        self.btn_upload = QPushButton(t("dirs.upload") if t("dirs.upload") != "[dirs.upload]" else "Yükle")
        self.btn_upload.clicked.connect(self.upload_files)

        self.btn_new_folder = QPushButton(
            t("dirs.new_folder") if t("dirs.new_folder") != "[dirs.new_folder]" else "Yeni Klasör"
        )
        self.btn_new_folder.clicked.connect(self.create_new_folder)

        self.btn_new_file = QPushButton(
            t("dirs.new_file") if t("dirs.new_file") != "[dirs.new_file]" else "Yeni Dosya"
        )
        self.btn_new_file.clicked.connect(self.create_new_file)

        self.btn_template_upload = QPushButton(
            t("dirs.template_upload") if t("dirs.template_upload") != "[dirs.template_upload]" else "Template Upload"
        )
        self.btn_template_upload.clicked.connect(self.show_template_upload_menu)

        self.btn_download = QPushButton(
            t("dirs.download_selected") if t("dirs.download_selected") != "[dirs.download_selected]" else "Seçilenleri İndir"
        )
        self.btn_download.clicked.connect(self.download_selected)

        self.btn_delete = QPushButton(t("dirs.delete") if t("dirs.delete") != "[dirs.delete]" else "Sil")
        self.btn_delete.clicked.connect(self.delete_selected)

        self.btn_undo = QPushButton(t("dirs.undo") if t("dirs.undo") != "[dirs.undo]" else "Geri Al")
        self.btn_undo.clicked.connect(self.undo_last)

        self.btn_parent = QToolButton()
        self.btn_parent.setAutoRaise(False)
        self.btn_parent.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btn_parent.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.btn_parent.clicked.connect(self.go_parent)
        self.btn_parent.setEnabled(False)

        self.btn_favorites = QToolButton()
        self.btn_favorites.setText(
            t("dirs.favorites") if t("dirs.favorites") != "[dirs.favorites]" else "★ Favoriler"
        )
        self.btn_favorites.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_favorites.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.btn_favorites.setMenu(QMenu(self.btn_favorites))
        self.btn_favorites.menu().aboutToShow.connect(self._populate_favorites_menu)

        self.btn_history = QToolButton()
        self.btn_history.setText(
            t("dirs.history") if t("dirs.history") != "[dirs.history]" else "Geçmiş"
        )
        self.btn_history.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_history.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.btn_history.setMenu(QMenu(self.btn_history))
        self.btn_history.menu().aboutToShow.connect(self._populate_history_menu)

        self.btn_refresh = QPushButton(t("dirs.refresh") if t("dirs.refresh") != "[dirs.refresh]" else "Yenile")
        self.btn_refresh.clicked.connect(lambda: self._refresh_from_ui(force=True))

        self.refresh_shortcut = QShortcut(QKeySequence.Refresh, self)
        self.refresh_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.refresh_shortcut.activated.connect(lambda: self._refresh_from_ui(force=True))

        top = QHBoxLayout()
        top.addWidget(self.lbl)
        top.addStretch(1)
        top.addWidget(self.btn_new_folder)
        top.addWidget(self.btn_new_file)
        top.addWidget(self.btn_upload)
        top.addWidget(self.btn_template_upload)
        top.addWidget(self.btn_download)
        top.addWidget(self.btn_delete)
        top.addWidget(self.btn_undo)
        top.addWidget(self.btn_parent)
        top.addWidget(self.btn_favorites)
        top.addWidget(self.btn_history)
        top.addWidget(self.btn_refresh)

        self.directory_tabs = QTabBar()
        self.directory_tabs.setExpanding(False)
        self.directory_tabs.setMovable(True)
        self.directory_tabs.setTabsClosable(True)
        self.directory_tabs.tabCloseRequested.connect(self._close_directory_tab)
        self.directory_tabs.currentChanged.connect(self._on_directory_tab_changed)

        self.tabs = QTabWidget()
        self.views: Dict[str, _RemoteTree] = {
            "all": self._make_view(),
            "folders": self._make_view(),
            "iso": self._make_view(),
            "archives": self._make_view(),
            "slurm": self._make_view(),
            "shell": self._make_view(),
            "other": self._make_view(),
        }
        self.tabs.addTab(self.views["all"], t("dirs.tab_all") if t("dirs.tab_all") != "[dirs.tab_all]" else "Tümü")
        self.tabs.addTab(self.views["folders"], t("dirs.tab_folders") if t("dirs.tab_folders") != "[dirs.tab_folders]" else "Klasörler")
        self.tabs.addTab(self.views["iso"], t("dirs.tab_iso") if t("dirs.tab_iso") != "[dirs.tab_iso]" else "ISO")
        self.tabs.addTab(
            self.views["archives"], t("dirs.tab_archives") if t("dirs.tab_archives") != "[dirs.tab_archives]" else "Arşivler"
        )
        self.tabs.addTab(self.views["slurm"], t("dirs.tab_slurm") if t("dirs.tab_slurm") != "[dirs.tab_slurm]" else "Slurm")
        self.tabs.addTab(self.views["shell"], t("dirs.tab_shell") if t("dirs.tab_shell") != "[dirs.tab_shell]" else "SH")
        self.tabs.addTab(self.views["other"], t("dirs.tab_other") if t("dirs.tab_other") != "[dirs.tab_other]" else "Diğer")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        self.path_label = QLabel(t("dirs.path"))
        lay.addWidget(self.path_label)
        lay.addWidget(self.path)
        lay.addWidget(self.directory_tabs)
        lay.addWidget(self.tabs)

        # Transfer queue (batch view)
        self.queue_group = QGroupBox(t("dirs.queue_title") if t("dirs.queue_title") != "[dirs.queue_title]" else "İşlem Kuyruğu")
        qlay = QVBoxLayout(self.queue_group)
        self.queue_current = QLabel("-")
        self.queue_list = QListWidget()
        self.queue_list.setMinimumHeight(80)
        self.queue_current_label = QLabel(t("dirs.queue_current"))
        qlay.addWidget(self.queue_current_label)

        # ---- active batch tracking (for graceful shutdown / diagnostics)
        self._active_thread: Optional[QThread] = None
        self._active_worker: Optional[_FileOpWorker] = None
        self._active_plan: List[_PlannedOp] = []
        self._active_step: int = 0
        self._active_title: str = ""
        qlay.addWidget(self.queue_current)
        self.queue_next_label = QLabel(t("dirs.queue_pending"))
        qlay.addWidget(self.queue_next_label)
        qlay.addWidget(self.queue_list)
        self.queue_group.setVisible(False)
        lay.addWidget(self.queue_group)

        self._update_undo_enabled()
        self._update_navigation_controls()

    def retranslate_ui(self) -> None:
        self.btn_new_folder.setText(t("dirs.new_folder"))
        self.btn_new_file.setText(t("dirs.new_file"))
        self.btn_upload.setText(t("dirs.upload"))
        self.btn_template_upload.setText(t("dirs.template_upload"))
        self.btn_download.setText(t("dirs.download_selected"))
        self.btn_delete.setText(t("dirs.delete"))
        self.btn_undo.setText(t("dirs.undo"))
        self.btn_refresh.setText(t("dirs.refresh"))
        self.path_label.setText(t("dirs.path"))
        self.queue_group.setTitle(t("dirs.queue_title"))
        self.queue_current_label.setText(t("dirs.queue_current"))
        self.queue_next_label.setText(t("dirs.queue_pending"))
        tab_keys = ("all", "folders", "iso", "archives", "slurm", "shell", "other")
        for index, key in enumerate(tab_keys):
            self.tabs.setTabText(index, t(f"dirs.tab_{key}"))
        for index in range(self.directory_tabs.count()):
            directory = str(self.directory_tabs.tabData(index) or "")
            if directory:
                self.directory_tabs.setTabText(index, self._directory_tab_label(directory))
        headers = [
            t("dirs.col_name"),
            t("dirs.col_size"),
            t("dirs.col_type"),
            t("dirs.col_mtime"),
            t("ftp.comparison_column")
            if t("ftp.comparison_column") != "[ftp.comparison_column]"
            else "Comparison",
        ]
        for view in self.views.values():
            view.setHeaderLabels(headers)

    def _make_view(self) -> _RemoteTree:
        w = _RemoteTree(panel=self)
        w.setColumnCount(5)
        w.setHeaderLabels(
            [
                t("dirs.col_name") if t("dirs.col_name") != "[dirs.col_name]" else "Filename",
                t("dirs.col_size") if t("dirs.col_size") != "[dirs.col_size]" else "Filesize",
                t("dirs.col_type") if t("dirs.col_type") != "[dirs.col_type]" else "Filetype",
                t("dirs.col_mtime") if t("dirs.col_mtime") != "[dirs.col_mtime]" else "Last modified",
                t("ftp.comparison_column") if t("ftp.comparison_column") != "[ftp.comparison_column]" else "Comparison",
            ]
        )
        w.hideColumn(4)
        w.setRootIsDecorated(False)
        w.setAlternatingRowColors(True)
        w.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        w.itemDoubleClicked.connect(self._handle_item_double_clicked)
        w.header().setStretchLastSection(True)
        w.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        w.customContextMenuRequested.connect(lambda pos, view=w: self._on_context_menu(view, pos))
        w.installEventFilter(self)
        return w

    @staticmethod
    def _directory_tab_label(remote_dir: str) -> str:
        cleaned = (remote_dir or "/").rstrip("/") or "/"
        return cleaned.rsplit("/", 1)[-1] or cleaned

    def _on_tab_changed(self, index: int) -> None:
        self._settle_current_view()
        self._update_navigation_controls()

    def _on_directory_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        remote_dir = str(self.directory_tabs.tabData(index) or "")
        if not remote_dir:
            return
        previous = self.current_dir
        self.current_dir = remote_dir
        self._category_dir = remote_dir
        self.path.setText(remote_dir)
        if remote_dir != previous:
            self.directoryChanged.emit(remote_dir)
        self._refresh_from_ui()

    def _close_directory_tab(self, index: int) -> None:
        """Close only additional directory tabs; keep one working tab open."""
        if self.directory_tabs.count() <= 1 or index < 0:
            return
        self.directory_tabs.removeTab(index)

    def open_directory_in_new_tab(self, remote_dir: str) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        target = (remote_dir or "").rstrip("/") or "/"
        if not target:
            return False
        index = self._find_directory_tab(target)
        if index < 0:
            index = self.directory_tabs.addTab(self._directory_tab_label(target))
            self.directory_tabs.setTabData(index, target)
        changed = self.directory_tabs.currentIndex() != index
        self.directory_tabs.setCurrentIndex(index)
        previous = self.current_dir
        self.current_dir = target
        self._category_dir = target
        self.path.setText(target)
        if not changed:
            self._refresh_from_ui()
        if self.current_dir != previous:
            self.directoryChanged.emit(self.current_dir)
        self._update_navigation_controls()
        return True

    def _find_directory_tab(self, remote_dir: str) -> int:
        target = (remote_dir or "").rstrip("/") or "/"
        for index in range(self.directory_tabs.count()):
            if self.directory_tabs.tabData(index) == target:
                return index
        return -1

    def _open_path_field(self) -> None:
        self.set_dir(self.path.text())

    def eventFilter(self, watched, event):
        # Delete / Paste / Undo key support on directory views
        if isinstance(watched, QTreeWidget) and event.type() == QEvent.Type.KeyPress:
            e: QKeyEvent = event  # type: ignore
            if e.key() == Qt.Key.Key_Backspace and not e.modifiers():
                self.go_parent()
                return True
            if e.key() == Qt.Key.Key_Delete:
                self.delete_selected()
                return True
            if e.key() == Qt.Key.Key_F5 and not e.modifiers():
                self._refresh_from_ui(force=True)
                return True
            if e.key() == Qt.Key.Key_F2 and not e.modifiers():
                if self.rename_selected(watched):
                    return True
            if (e.modifiers() & Qt.KeyboardModifier.ControlModifier) and e.key() == Qt.Key.Key_C:
                paths = self._selected_paths_from_view(watched)
                if paths:
                    get_file_clipboard().set("copy", paths)
                    return True
            if (e.modifiers() & Qt.KeyboardModifier.ControlModifier) and e.key() == Qt.Key.Key_X:
                paths = self._selected_paths_from_view(watched)
                if paths:
                    get_file_clipboard().set("move", paths)
                    return True
            if (e.modifiers() & Qt.KeyboardModifier.ControlModifier) and e.key() == Qt.Key.Key_V:
                # Do not start a transfer/dialog while QTreeWidget is still
                # processing its key event.  In particular, pasting from one
                # remote directory tab into another can refresh/delete items
                # underneath the active view and crash frozen Qt builds.
                dest_dir = self.current_dir or "/"
                QTimer.singleShot(
                    0,
                    lambda target=dest_dir: self._paste_from_clipboard_into(target),
                )
                return True
            if (e.modifiers() & Qt.KeyboardModifier.ControlModifier) and e.key() == Qt.Key.Key_Z:
                self.undo_last()
                return True
        return super().eventFilter(watched, event)

    def _paste_from_clipboard_into(self, dest_dir: str) -> None:
        """Start a paste after the originating tree key event has finished."""
        try:
            if self._paste_system_clipboard_into(dest_dir):
                return
            self._paste_remote_clipboard_into(dest_dir)
        except Exception as exc:
            # The delayed callback is outside the caller's event stack, so
            # keep the last safety net here as well as in the paste helpers.
            show_exception(self, title=t("common.error"), user_message=str(exc), exc=exc, area="FILES")

    def set_session(self, session):
        self.session = session
        self._directory_cache.clear()
        self._navigation_store = None
        self._update_navigation_controls()

    # ---- favorites and history -----------------------------------------
    def _navigation(self):
        """The active profile's favorites/history store, or None."""
        store = getattr(self, "_navigation_store", None)
        if store is not None:
            return store
        profile_name = str((self.session or {}).get("profile_name", "")).strip()
        if not profile_name:
            return None
        store = navigation_store_for_profile(get_profile_id(profile_name) or "")
        self._navigation_store = store
        return store

    def _record_navigation_visit(self, remote_dir: str) -> None:
        """Remember a directory that actually opened."""
        store = self._navigation()
        if store is not None and remote_dir:
            store.record_visit(remote_dir)

    def _navigate_to_favorite(self, path: str, kind: str) -> None:
        # A favorite means "take me there", not "open it": a file favorite
        # lands in its parent directory with the file selected.
        if kind == "file":
            self.set_dir(self._parent_remote_dir(path))
            self._pending_select_name = self._basename(path)
        else:
            self.set_dir(path)

    @staticmethod
    def _basename(path: str) -> str:
        clean = (path or "/").rstrip("/") or "/"
        return clean.rsplit("/", 1)[-1] or clean

    def _populate_favorites_menu(self) -> None:
        menu = self.btn_favorites.menu()
        menu.clear()
        store = self._navigation()
        if store is None:
            menu.addAction(
                t("dirs.favorites_unavailable")
                if t("dirs.favorites_unavailable") != "[dirs.favorites_unavailable]"
                else "Favoriler kullanılamıyor (güvenli depolama yok)"
            ).setEnabled(False)
            return
        favorites = store.favorites()
        for item in favorites:
            path = str(item.get("path", ""))
            kind = str(item.get("kind", "directory"))
            action = menu.addAction(f"{item.get('label') or self._basename(path)}\t{path}")
            action.triggered.connect(
                lambda _checked=False, p=path, k=kind: self._navigate_to_favorite(p, k)
            )
        if favorites:
            menu.addSeparator()
        current = self._category_dir or self.current_dir
        if store.is_favorite(current):
            label = (
                t("dirs.favorite_remove")
                if t("dirs.favorite_remove") != "[dirs.favorite_remove]"
                else "Bu dizini favorilerden kaldır"
            )
            menu.addAction(label).triggered.connect(
                lambda _checked=False, p=current: store.remove_favorite(p)
            )
        else:
            label = (
                t("dirs.favorite_add")
                if t("dirs.favorite_add") != "[dirs.favorite_add]"
                else "Mevcut dizini favorilere ekle"
            )
            menu.addAction(label).triggered.connect(
                lambda _checked=False, p=current: store.add_favorite(p, "directory")
            )

    def _populate_history_menu(self) -> None:
        menu = self.btn_history.menu()
        menu.clear()
        store = self._navigation()
        if store is None:
            menu.addAction(
                t("dirs.history_unavailable")
                if t("dirs.history_unavailable") != "[dirs.history_unavailable]"
                else "Geçmiş kullanılamıyor (güvenli depolama yok)"
            ).setEnabled(False)
            return
        entries = store.history()
        for item in entries:
            path = str(item.get("path", ""))
            action = menu.addAction(f"{self._basename(path)}\t{path}")
            action.triggered.connect(lambda _checked=False, p=path: self.set_dir(p))
        if entries:
            menu.addSeparator()
        label = (
            t("dirs.history_clear")
            if t("dirs.history_clear") != "[dirs.history_clear]"
            else "Geçmişi temizle"
        )
        menu.addAction(label).triggered.connect(lambda _checked=False: store.clear_history())

    def set_transfer_mode_provider(
        self, provider: Optional[Callable[[str], str]]
    ) -> None:
        self._transfer_mode_provider = provider

    def set_output_target_provider(
        self,
        provider: Optional[Callable[[], List[Tuple[str, str]]]],
    ) -> None:
        self._output_target_provider = provider

    def set_transfer_activity_callback(
        self,
        callback: Optional[Callable[[str, List[TransferItem], str], None]],
    ) -> None:
        self._transfer_activity_callback = callback

    def set_local_target_refresh_callback(
        self,
        callback: Optional[Callable[[str], None]],
    ) -> None:
        """Set a callback used to refresh local transfer targets after success."""
        self._local_target_refresh_callback = callback

    def set_transfer_dialog_visible(self, visible: bool) -> None:
        self._show_transfer_dialog = bool(visible)

    def _requested_transfer_mode(self, path: str) -> str:
        if self._transfer_mode_provider is None:
            return BINARY
        try:
            return normalize_transfer_mode(self._transfer_mode_provider(path), BINARY)
        except Exception:
            return BINARY

    def set_dir(self, remote_dir: str):
        target = (remote_dir or "").rstrip("/") or "/"
        previous = self.current_dir
        self.current_dir = target
        self._category_dir = target
        signals_were_blocked = self.directory_tabs.blockSignals(True)
        if self.directory_tabs.count() == 0:
            index = self.directory_tabs.addTab(self._directory_tab_label(target))
            self.directory_tabs.setTabData(index, target)
            self.directory_tabs.setCurrentIndex(index)
        else:
            index = max(0, self.directory_tabs.currentIndex())
            self.directory_tabs.setTabText(index, self._directory_tab_label(target))
            self.directory_tabs.setTabData(index, target)
        self.directory_tabs.blockSignals(signals_were_blocked)
        self.path.setText(target)
        if target != previous:
            self.directoryChanged.emit(target)
        self._update_navigation_controls()
        if bool(getattr(self.session.get("files"), "supports_progressive_listing", False)):
            self.refresh_async()
        else:
            self.refresh()

    def _refresh_from_ui(self, *, force: bool = False) -> None:
        files = (self.session or {}).get("files")
        if bool(getattr(files, "supports_progressive_listing", False)):
            self.refresh_async(force=force)
        else:
            self.refresh(force=force)

    def _cancel_listing_worker(self) -> None:
        """Abandon the in-flight listing but keep the reference until it settles.

        The worker still owns the shared listing channel until its run ends, so
        dropping the reference here would let the next request start a second
        listing that only blocks on the channel lock.
        """
        worker = self._listing_worker
        if worker is not None:
            worker.cancel()

    def _listing_token_is_current(self, token: object) -> bool:
        return isValid(self) and token == ("directory", self._listing_generation)

    def refresh_async(self, force: bool = False) -> bool:
        """Stream a directory into the tree; stale navigations are cancelled."""
        if not self.session or not self.session.get("files"):
            return False
        self._cancel_listing_worker()
        self._pending_listing = None
        self._listing_generation += 1
        token = ("directory", self._listing_generation)
        category_dir = self._category_dir or self.current_dir
        key = self._cache_key(category_dir)
        if not force and get_remote_directory_cache_enabled():
            cached = self._directory_cache.get(key)
            if cached is not None and monotonic() - cached[0] <= DIRECTORY_CACHE_TTL_SECONDS:
                self._listing_override = (category_dir, list(cached[1]))
                self.refresh()
                return True
        # Clear up front: leaving the previous directory's rows under the new
        # path invites a click on a row that is no longer there.
        self._begin_render(category_dir)
        if self._listing_worker is not None:
            # Only the newest request survives: an A->B->C burst never pays for
            # B's traffic, it is replaced before it ever starts.
            self._pending_listing = (token, key)
            return True
        self._start_listing_worker(token, key)
        return True

    def _start_listing_worker(self, token: object, key: str) -> None:
        self._streaming_key = key
        self._streaming_entries = []
        worker = _DirectoryListingWorker(token, self.session["files"], key)
        self._listing_worker = worker
        worker.signals.batch.connect(self._on_listing_batch)
        worker.signals.finished.connect(self._on_listing_finished)
        worker.signals.failed.connect(self._on_listing_failed)
        worker.signals.settled.connect(self._on_listing_settled)
        QThreadPool.globalInstance().start(worker)

    def _on_listing_settled(self, token: object) -> None:
        if not isValid(self):
            return
        worker = self._listing_worker
        if worker is None or worker.token != token:
            return
        self._listing_worker = None
        pending, self._pending_listing = self._pending_listing, None
        if pending is not None and self._listing_token_is_current(pending[0]):
            self._start_listing_worker(*pending)

    def _on_listing_batch(self, token: object, entries: object) -> None:
        if not self._listing_token_is_current(token):
            return
        self._streaming_entries.extend(entries)
        self._append_entries(entries)

    def _on_listing_finished(self, token: object) -> None:
        if not self._listing_token_is_current(token):
            return
        self._directory_cache[self._streaming_key] = (
            monotonic(),
            list(self._streaming_entries),
        )
        self._finish_render()
        self._record_navigation_visit(self._streaming_key)
        self._commit_snapshot(self._streaming_key, self._streaming_entries)
        if self._cache_key(self.current_dir) == self._streaming_key:
            self.directoryLoaded.emit(self.current_dir)

    # ---- comparison snapshot --------------------------------------------
    @staticmethod
    def _comparable_entry(entry: RemoteEntry) -> ComparableEntry:
        return ComparableEntry(
            name=entry.name,
            is_dir=bool(entry.is_dir),
            size=int(entry.size or 0),
            mtime=int(entry.mtime or 0),
        )

    def _commit_snapshot(
        self, remote_dir: str, entries: Iterable[RemoteEntry]
    ) -> None:
        """Commit the final listing of a finished generation as the
        comparison source; pending/abandoned streams never reach here."""
        self._snapshot_dir = self._cache_key(remote_dir)
        self._snapshot_entries = [
            self._comparable_entry(entry) for entry in entries
        ]

    def current_entries_snapshot(self) -> tuple[str, List[ComparableEntry]]:
        """Return (path, entries) only when committed for current_dir."""
        key = self._cache_key(self.current_dir or "/")
        if self._snapshot_dir != key:
            return "", []
        return self._snapshot_dir, list(self._snapshot_entries)

    def _on_listing_failed(self, token: object, error: object) -> None:
        if not self._listing_token_is_current(token):
            return
        self._show_op_error(
            f"{t('dirs.load_failed') if t('dirs.load_failed') != '[dirs.load_failed]' else 'Dizin okunamadı'}: {error}"
        )
        self._finish_render()

    @staticmethod
    def _cache_key(remote_dir: str) -> str:
        return (remote_dir or "/").rstrip("/") or "/"

    @classmethod
    def _normalize_remote_dir(cls, remote_dir: Optional[str]) -> str:
        return cls._cache_key(remote_dir or "/")

    @classmethod
    def _parent_remote_dir(cls, remote_path: str) -> str:
        clean = (remote_path or "/").rstrip("/") or "/"
        if clean == "/":
            return "/"
        return cls._normalize_remote_dir("/".join(clean.split("/")[:-1]) or "/")

    def _invalidate_directory_cache(self, remote_dir: Optional[str] = None) -> None:
        if remote_dir is None:
            self._directory_cache.clear()
            return
        self._directory_cache.pop(self._cache_key(remote_dir), None)

    def _unregister_instance(self, *_args) -> None:
        if RemoteDirPanel._instances.get(self.panel_id) is self:
            RemoteDirPanel._instances.pop(self.panel_id, None)

    @staticmethod
    def _unregister_instance_ref(panel_id: str, expected_ref) -> None:
        expected = expected_ref()
        if (
            expected is not None
            and RemoteDirPanel._instances.get(panel_id) is expected
        ):
            RemoteDirPanel._instances.pop(panel_id, None)

    def _finish_remote_directory_mutation(self, remote_dirs: Iterable[str]) -> None:
        affected = {
            self._normalize_remote_dir(remote_dir)
            for remote_dir in remote_dirs
            if remote_dir
        }
        if not affected:
            return

        panels: List[Tuple[str, "RemoteDirPanel"]] = []
        for panel_id, panel in list(RemoteDirPanel._instances.items()):
            if RemoteDirPanel._instances.get(panel_id) is not panel:
                continue
            try:
                for remote_dir in affected:
                    panel._invalidate_directory_cache(remote_dir)
            except RuntimeError:
                if RemoteDirPanel._instances.get(panel_id) is panel:
                    RemoteDirPanel._instances.pop(panel_id, None)
                continue
            panels.append((panel_id, panel))

        for panel_id, panel in panels:
            try:
                current = self._normalize_remote_dir(panel.current_dir or "/")
                if current in affected:
                    panel._refresh_from_ui(force=True)
            except RuntimeError:
                if RemoteDirPanel._instances.get(panel_id) is panel:
                    RemoteDirPanel._instances.pop(panel_id, None)

    def _listdir_entries_cached(
        self,
        remote_dir: str,
        *,
        force: bool = False,
    ) -> List[RemoteEntry]:
        if not self.session or not self.session.get("files"):
            return []
        key = self._cache_key(remote_dir)
        if not get_remote_directory_cache_enabled():
            return list(self.session["files"].listdir_entries(key))
        now = monotonic()
        cached = self._directory_cache.get(key)
        if not force and cached is not None:
            cached_at, entries = cached
            if now - cached_at <= DIRECTORY_CACHE_TTL_SECONDS:
                return list(entries)
        entries = list(self.session["files"].listdir_entries(key))
        self._directory_cache[key] = (now, entries)
        return list(entries)

    @staticmethod
    def _local_paths_from_mime(mime) -> List[str]:
        if not mime or not mime.hasUrls():
            return []
        return [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]

    def _drop_dest_dir_for_item(self, item: Optional[QTreeWidgetItem]) -> str:
        dest_dir = self.current_dir or "/"
        if item is not None:
            clicked_path = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
            clicked_is_dir = bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
            if clicked_path and clicked_is_dir:
                dest_dir = clicked_path.rstrip("/") or "/"
        return dest_dir

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if self._local_paths_from_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._local_paths_from_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        paths = self._local_paths_from_mime(event.mimeData())
        if not paths:
            super().dropEvent(event)
            return
        target_dir = self.current_dir or "/"
        event.acceptProposedAction()
        QTimer.singleShot(
            0,
            lambda dropped_paths=list(paths), target=target_dir: self._apply_local_upload_incremental(dropped_paths, target),
        )

    def _remote_parent_dir(self, remote_dir: str) -> str:
        cleaned = (remote_dir or "").rstrip("/")
        if not cleaned or cleaned == "/":
            return ""
        parent = cleaned.rsplit("/", 1)[0]
        return parent or "/"

    def _update_navigation_controls(self) -> None:
        has_session = bool(self.session and self.session.get("connected"))
        has_parent = bool(self._remote_parent_dir(self.current_dir)) if has_session else False
        if hasattr(self, "btn_parent"):
            self.btn_parent.setEnabled(has_parent)
        if hasattr(self, "btn_new_folder"):
            self.btn_new_folder.setEnabled(bool(has_session and self.current_dir))
        if hasattr(self, "btn_new_file"):
            self.btn_new_file.setEnabled(bool(has_session and self.current_dir))
        if hasattr(self, "btn_template_upload"):
            self.btn_template_upload.setEnabled(bool(has_session and self.current_dir))

    @staticmethod
    def _child_path(parent_dir: str, name: str) -> str:
        return (parent_dir.rstrip("/") or "") + "/" + name

    def _prompt_new_name(self, *, kind: str) -> str:
        is_folder = kind == "folder"
        title_key = "dirs.new_folder_title" if is_folder else "dirs.new_file_title"
        label_key = "dirs.new_folder_label" if is_folder else "dirs.new_file_label"
        name, ok = QInputDialog.getText(self, t(title_key), t(label_key))
        if not ok:
            return ""
        name = (name or "").strip()
        if not name:
            return ""
        if name in (".", "..") or "/" in name or "\\" in name:
            QMessageBox.warning(self, t("common.error"), t("dirs.invalid_new_name"))
            return ""
        return name

    def _create_remote_item(self, *, kind: str, parent_dir: Optional[str] = None) -> bool:
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return False
        raw_target_dir = parent_dir or self.current_dir or ""
        if not raw_target_dir:
            QMessageBox.warning(self, t("common.error"), t("dirs.no_directory_selected"))
            return False
        target_dir = raw_target_dir.rstrip("/") or "/"

        name = self._prompt_new_name(kind=kind)
        if not name:
            return False
        target_path = self._child_path(target_dir, name)
        files = self.session["files"]
        try:
            if files.exists(target_path):
                QMessageBox.warning(
                    self,
                    t("dirs.conflict_title"),
                    t("dirs.new_item_exists").format(path=target_path),
                )
                return False
            if kind == "folder":
                files.mkdir(target_path)
            else:
                files.write_text(target_path, "")
            self._finish_remote_directory_mutation([target_dir])
            return True
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=str(e), exc=e, area="FILES")
            return False

    def create_new_folder(self, parent_dir: Optional[str] = None) -> bool:
        return self._create_remote_item(kind="folder", parent_dir=parent_dir)

    def create_new_folder_and_enter(self, parent_dir: Optional[str] = None) -> bool:
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return False
        raw_target_dir = parent_dir or self.current_dir or ""
        if not raw_target_dir:
            QMessageBox.warning(self, t("common.error"), t("dirs.no_directory_selected"))
            return False
        target_dir = raw_target_dir.rstrip("/") or "/"
        name = self._prompt_new_name(kind="folder")
        if not name:
            return False
        target_path = self._child_path(target_dir, name)
        files = self.session["files"]
        try:
            if files.exists(target_path):
                QMessageBox.warning(
                    self,
                    t("dirs.conflict_title"),
                    t("dirs.new_item_exists").format(path=target_path),
            )
                return False
            files.mkdir(target_path)
            self._finish_remote_directory_mutation([target_dir])
            self.set_dir(target_path)
            return True
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=str(e), exc=e, area="FILES")
            return False

    def create_new_file(self, parent_dir: Optional[str] = None) -> bool:
        return self._create_remote_item(kind="file", parent_dir=parent_dir)

    def _handle_item_double_clicked(self, item, col):
        path = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        if not path:
            return
        is_dir = bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
        if is_dir:
            self.set_dir(path.rstrip("/") or "/")
            return
        self.file_activated.emit(path)

    def go_parent(self):
        parent = self._remote_parent_dir(self.current_dir)
        if not parent:
            return
        self.set_dir(parent)

    def _icon_for(self, entry: RemoteEntry) -> QIcon:
        st = self.style()
        if entry.is_dir:
            return st.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        lower = entry.name.lower()
        if lower.endswith(".iso"):
            return st.standardIcon(QStyle.StandardPixmap.SP_DriveDVDIcon)
        return st.standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    def _make_entry_item(self, entry: RemoteEntry) -> QTreeWidgetItem:
        it = QTreeWidgetItem()
        it.setText(0, entry.name)
        it.setIcon(0, self._icon_for(entry))
        it.setText(1, "" if entry.is_dir else _fmt_size(entry.size))
        file_type = _file_type(entry.name, entry.is_dir)
        it.setText(2, file_type)
        it.setText(3, _fmt_mtime(entry.mtime))
        it.setData(0, Qt.ItemDataRole.UserRole, entry.path)
        it.setData(0, Qt.ItemDataRole.UserRole + 1, bool(entry.is_dir))
        it.setData(0, _SORT_NAME_ROLE, entry.name)
        it.setData(0, _SORT_SIZE_ROLE, int(entry.size or 0))
        it.setData(0, _SORT_TYPE_ROLE, file_type)
        it.setData(0, _SORT_MTIME_ROLE, int(entry.mtime or 0))
        it.setData(0, _FILE_MODE_ROLE, int(entry.mode or 0))
        return it

    def _make_parent_item(self, parent_dir: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        item.setText(0, "..")
        item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        item.setText(1, "")
        item.setText(2, _file_type("..", True))
        item.setText(3, "")
        item.setData(0, Qt.ItemDataRole.UserRole, parent_dir)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, True)
        item.setData(0, Qt.ItemDataRole.UserRole + 2, True)
        item.setData(0, _SORT_NAME_ROLE, "..")
        item.setData(0, _SORT_SIZE_ROLE, 0)
        item.setData(0, _SORT_TYPE_ROLE, _file_type("..", True))
        item.setData(0, _SORT_MTIME_ROLE, 0)
        item.setData(0, _FILE_MODE_ROLE, 0)
        return item

    def _begin_render(self, category_dir: str) -> None:
        """Empty every view and seed the ".." row for a new listing."""
        for v in self.views.values():
            v.clear()
        parent_dir = self._remote_parent_dir(category_dir)
        if parent_dir:
            self.views["all"].addTopLevelItem(self._make_parent_item(parent_dir))
            if "folders" in self.views:
                self.views["folders"].addTopLevelItem(self._make_parent_item(parent_dir))
        self._update_navigation_controls()

    def _append_entries(self, entries: Iterable[RemoteEntry]) -> None:
        """Add one batch. Never clears: rebuilding per batch is quadratic."""
        views = list(self.views.values())
        for v in views:
            v.setUpdatesEnabled(False)
        try:
            for e in entries:
                self.views["all"].addTopLevelItem(self._make_entry_item(e))
                cat = _category(e)
                if cat in self.views:
                    self.views[cat].addTopLevelItem(self._make_entry_item(e))
        finally:
            for v in views:
                v.setUpdatesEnabled(True)

    def _finish_render(self) -> None:
        """Sort and size the visible category now, the rest when first shown.

        Sorting and measuring all seven trees costs 28 column scans per
        navigation, and six of them are for tabs nobody is looking at.
        """
        self._dirty_views = set(self.views)
        self._settle_current_view()
        self._select_pending_name()
        self._update_undo_enabled()
        self._update_navigation_controls()

    def _select_pending_name(self) -> None:
        """Highlight the row a file favorite asked for, once it exists."""
        name, self._pending_select_name = self._pending_select_name, ""
        if not name:
            return
        view = self.views["all"]
        for index in range(view.topLevelItemCount()):
            item = view.topLevelItem(index)
            if item.text(0) == name:
                view.setCurrentItem(item)
                view.scrollToItem(item)
                return

    def _settle_current_view(self) -> None:
        current = self.tabs.currentWidget()
        for key, view in self.views.items():
            if view is not current or key not in self._dirty_views:
                continue
            self._dirty_views.discard(key)
            view.apply_sort()
            for column in range(4):
                view.resizeColumnToContents(column)

    def refresh(self, force: bool = False):
        if not self.session or not self.session.get("files"):
            for v in self.views.values():
                v.clear()
            self._update_navigation_controls()
            return

        category_dir = self._category_dir or self.current_dir
        override = getattr(self, "_listing_override", None)
        if override is not None and override[0] == category_dir:
            entries = list(override[1])
            self._listing_override = None
        else:
            try:
                entries = self._listdir_entries_cached(category_dir, force=bool(force))
            except Exception as e:
                self._show_op_error(
                    f"{t('dirs.load_failed') if t('dirs.load_failed') != '[dirs.load_failed]' else 'Dizin okunamadı'}: {e}"
                )
                for v in self.views.values():
                    v.clear()
                return

        self._begin_render(category_dir)
        self._append_entries(entries)
        self._finish_render()
        self._record_navigation_visit(category_dir)
        self._commit_snapshot(category_dir, entries)
        self.directoryLoaded.emit(self.current_dir)

    # ---- comparison column ----------------------------------------------
    def set_comparison_visible(self, visible: bool) -> None:
        for view in list(getattr(self, "views", {}).values()):
            try:
                if visible:
                    view.showColumn(4)
                else:
                    view.hideColumn(4)
            except RuntimeError:
                continue
        if not visible:
            self.clear_comparison_statuses()

    def clear_comparison_statuses(self) -> None:
        self._comparison_statuses = None
        for view in list(getattr(self, "views", {}).values()):
            try:
                for index in range(view.topLevelItemCount()):
                    item = view.topLevelItem(index)
                    item.setText(4, "")
                    item.setToolTip(4, "")
            except RuntimeError:
                continue

    def _comparison_status_labels(self) -> dict[CompareStatus, str]:
        return {
            CompareStatus.SAME: t("ftp.cmp_same"),
            CompareStatus.LOCAL_ONLY: t("ftp.cmp_local_only"),
            CompareStatus.REMOTE_ONLY: t("ftp.cmp_remote_only"),
            CompareStatus.TYPE_MISMATCH: t("ftp.cmp_type_differs"),
            CompareStatus.SIZE_DIFFERENT: t("ftp.cmp_size_different"),
            CompareStatus.LOCAL_NEWER: t("ftp.cmp_local_newer"),
            CompareStatus.REMOTE_NEWER: t("ftp.cmp_remote_newer"),
        }

    def _render_comparison_statuses(self) -> None:
        statuses = self._comparison_statuses or {}
        labels = self._comparison_status_labels()
        for view in list(self.views.values()):
            try:
                items = [view.topLevelItem(i) for i in range(view.topLevelItemCount())]
            except RuntimeError:
                continue
            for item in items:
                if bool(item.data(0, Qt.ItemDataRole.UserRole + 2)):
                    continue
                name = str(item.data(0, _SORT_NAME_ROLE) or "")
                status = statuses.get(name)
                if status is None:
                    item.setText(4, "")
                    item.setToolTip(4, "")
                    continue
                label = labels.get(status, str(status.value))
                item.setText(4, "=" if status is CompareStatus.SAME else label)
                item.setToolTip(4, label)

    def apply_comparison_statuses(
        self, statuses: dict[str, CompareStatus]
    ) -> None:
        self._comparison_statuses = dict(statuses)
        self._render_comparison_statuses()

    # ---------- selection helpers ----------
    def _selected_paths_from_view(self, view: QTreeWidget) -> List[str]:
        paths: List[str] = []
        for it in view.selectedItems():
            if bool(it.data(0, Qt.ItemDataRole.UserRole + 2)):
                continue
            p = it.data(0, Qt.ItemDataRole.UserRole)
            if p:
                paths.append(str(p))
        return paths

    def _selected_entries_from_view(self, view: QTreeWidget) -> List[Tuple[str, bool]]:
        entries: List[Tuple[str, bool]] = []
        for it in view.selectedItems():
            if bool(it.data(0, Qt.ItemDataRole.UserRole + 2)):
                continue
            path = str(it.data(0, Qt.ItemDataRole.UserRole) or "")
            if path:
                entries.append((path, bool(it.data(0, Qt.ItemDataRole.UserRole + 1))))
        return entries

    @staticmethod
    def _ansys_lint_supported(remote_path: str) -> bool:
        from hpc_gui.plugins.linter_tools import supported_suffixes

        name = remote_path.rstrip("/").rsplit("/", 1)[-1]
        dot = name.rfind(".")
        if dot < 0:
            return False
        return name[dot:].lower() in supported_suffixes()

    @staticmethod
    def _remote_file_name(remote_path: str) -> str:
        return remote_path.rstrip("/").rsplit("/", 1)[-1]

    @staticmethod
    def _remote_suffix(remote_path: str) -> str:
        name = RemoteDirPanel._remote_file_name(remote_path)
        dot = name.rfind(".")
        return name[dot:].lower() if dot >= 0 else ""

    def _build_send_to_plugin_menu(self, menu, remote_path: str | None):
        """Attach a "send to plugin" submenu when a tool supports the file."""
        if not remote_path:
            return None
        from hpc_gui.plugins.linter_tools import tools_supporting_suffix

        try:
            tools = tools_supporting_suffix(self._remote_suffix(remote_path))
        except Exception:  # defensive: menu building never breaks the panel
            logger.warning("Tool lookup failed for %s", remote_path, exc_info=True)
            return None
        if not tools:
            return None
        send_menu = menu.addMenu(t("files.send_to_plugin"))
        for tool in tools:
            action = send_menu.addAction(tool.title)
            action.triggered.connect(
                lambda _=False, tl=tool, p=remote_path: self.open_in_tool(tl, p)
            )
        return send_menu

    def open_in_tool(self, tool, remote_path: str) -> None:
        """Open a linter-tool page pre-loaded with one remote file.

        Tool pages re-read paths from disk, so the current content is
        materialized into a suffixed temporary file for the lifetime of
        the modal page and removed afterwards.
        """
        from hpc_gui.plugins.linter_tools import (
            remove_temp_copy,
            temp_copy_for_tool,
        )
        from hpc_gui.ui.dialogs.linter_tool_host import host_tool_page

        files = (self.session or {}).get("files")
        if not files:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        temp_path = None
        try:
            text = files.read_text(remote_path)
            temp_path = temp_copy_for_tool(text, self._remote_file_name(remote_path))
        except Exception as exc:  # network or disk failure stays contained
            logger.warning("Could not fetch %s for tool", remote_path, exc_info=exc)
            QMessageBox.warning(
                self, t("ansyslint.title"), f"{type(exc).__name__}: {exc}"
            )
            return
        try:
            host_tool_page(
                self,
                tool,
                initial_paths=[str(temp_path)],
                title=f"{tool.title} — {self._remote_file_name(remote_path)}",
            )
        finally:
            remove_temp_copy(temp_path)

    def run_ansys_lint(self, remote_path: str) -> None:
        from hpc_gui.plugins.linter_tools import (
            ToolLoadError,
            lint_text_with_tool,
        )
        from hpc_gui.ui.dialogs.ansys_lint_results_dialog import (
            show_ansys_lint_results,
        )

        def open_in_tool() -> None:
            from hpc_gui.plugins.linter_tools import first_linter_tool

            try:
                self.open_in_tool(first_linter_tool(), remote_path)
            except Exception as exc:  # already messaged by the fetch/host path
                logger.warning("Fix redirect failed for %s", remote_path, exc_info=exc)

        files = (self.session or {}).get("files")
        if not files:
            QMessageBox.warning(
                self, t("common.error"), t("common.no_connection")
            )
            return
        try:
            text = files.read_text(remote_path)
            run = lint_text_with_tool(text, file_name=remote_path)
        except ToolLoadError as exc:
            QMessageBox.warning(self, t("ansyslint.title"), str(exc))
            return
        except Exception as exc:  # defensive: network/engine failures stay contained
            logger.warning(
                "ANSYS lint failed for %s", remote_path, exc_info=exc
            )
            QMessageBox.warning(
                self,
                t("ansyslint.title"),
                f"{type(exc).__name__}: {exc}",
            )
            return
        show_ansys_lint_results(
            self,
            f"{t('ansyslint.title')} — "
            f"{self._remote_file_name(remote_path)}",
            run,
            open_in_tool=open_in_tool,
        )

    def open_in_tool_batch(self, tool, remote_paths: list[str]) -> None:
        """Open a linter-tool page pre-loaded with multiple remote files."""
        from hpc_gui.plugins.linter_tools import (
            remove_temp_copy,
            temp_copy_for_tool,
        )
        from hpc_gui.ui.dialogs.linter_tool_host import host_tool_page

        files = (self.session or {}).get("files")
        if not files:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        temp_paths: list[Path] = []
        try:
            for remote_path in remote_paths:
                text = files.read_text(remote_path)
                temp_paths.append(
                    temp_copy_for_tool(text, self._remote_file_name(remote_path))
                )
        except Exception as exc:  # network or disk failure stays contained
            for p in temp_paths:
                remove_temp_copy(p)
            logger.warning("Could not fetch %s for tool", remote_paths, exc_info=exc)
            QMessageBox.warning(
                self, t("ansyslint.title"), f"{type(exc).__name__}: {exc}"
            )
            return
        try:
            names = ", ".join(self._remote_file_name(p) for p in remote_paths[:3])
            if len(remote_paths) > 3:
                names += f" +{len(remote_paths) - 3}"
            host_tool_page(
                self,
                tool,
                initial_paths=[str(p) for p in temp_paths],
                title=f"{tool.title} — {names}",
            )
        finally:
            for p in temp_paths:
                remove_temp_copy(p)

    def run_ansys_lint_batch(self, remote_paths: list[str]) -> None:
        from hpc_gui.plugins.linter_tools import ToolLoadError, lint_text_with_tool
        from hpc_gui.ui.dialogs.ansys_lint_results_dialog import (
            show_ansys_lint_results,
        )
        import types

        def open_in_tool() -> None:
            from hpc_gui.plugins.linter_tools import tools_supporting_all_suffixes

            try:
                suffixes = [self._remote_suffix(p) for p in remote_paths]
                tools = tools_supporting_all_suffixes(suffixes)
                if not tools:
                    return
                self.open_in_tool_batch(tools[0], remote_paths)
            except Exception as exc:
                logger.warning("Fix redirect failed for %s", remote_paths, exc_info=exc)

        files = (self.session or {}).get("files")
        if not files:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        file_results = []
        try:
            for remote_path in remote_paths:
                text = files.read_text(remote_path)
                file_results.append(lint_text_with_tool(text, file_name=remote_path))
        except ToolLoadError as exc:
            QMessageBox.warning(self, t("ansyslint.title"), str(exc))
            return
        except Exception as exc:  # defensive: network/engine failures stay contained
            logger.warning("ANSYS lint failed for %s", remote_paths, exc_info=exc)
            QMessageBox.warning(
                self, t("ansyslint.title"), f"{type(exc).__name__}: {exc}"
            )
            return
        # Build a LintRunResult-like object for the dialog.
        totals = {"error": 0, "warning": 0, "info": 0}
        for fr in file_results:
            for key in totals:
                totals[key] += fr.summary.get(key, 0) if hasattr(fr, "summary") else 0
        run = types.SimpleNamespace(files=file_results, summary=totals)
        names = ", ".join(self._remote_file_name(p) for p in remote_paths[:3])
        if len(remote_paths) > 3:
            names += f" +{len(remote_paths) - 3}"
        show_ansys_lint_results(
            self,
            f"{t('ansyslint.title')} — {names}",
            run,
            open_in_tool=open_in_tool,
        )

    def run_ansys_lint_folder(self, remote_path: str) -> None:
        files = (self.session or {}).get("files")
        if not files:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        if self._remote_lint_worker is not None:
            return
        worker = _RemoteLintWorker(files, remote_path)
        self._remote_lint_worker = worker
        worker.signals.finished.connect(self._on_remote_lint_finished)
        worker.signals.failed.connect(self._on_remote_lint_failed)
        QThreadPool.globalInstance().start(worker)

    def _on_remote_lint_failed(self, error: object) -> None:
        self._remote_lint_worker = None
        logger.warning("Remote folder lint failed: %r", error)
        QMessageBox.warning(self, t("ansyslint.title"), f"{type(error).__name__}: {error}")

    def _on_remote_lint_finished(self, payload: object) -> None:
        from hpc_gui.ui.dialogs.ansys_lint_results_dialog import (
            show_ansys_lint_results,
        )

        self._remote_lint_worker = None
        remote_paths, file_results = payload
        if not remote_paths:
            QMessageBox.information(
                self, t("ansyslint.title"), t("files.no_supported_remote_lint_files")
            )
            return
        import types

        totals = {"error": 0, "warning": 0, "info": 0}
        for result in file_results:
            for key in totals:
                totals[key] += result.summary.get(key, 0)
        run = types.SimpleNamespace(files=file_results, summary=totals)

        def open_in_tool() -> None:
            from hpc_gui.plugins.linter_tools import tools_supporting_all_suffixes

            tools = tools_supporting_all_suffixes(
                [self._remote_suffix(path) for path in remote_paths]
            )
            if tools:
                self.open_in_tool_batch(tools[0], remote_paths)

        show_ansys_lint_results(
            self,
            f"{t('ansyslint.title')} — {self._remote_file_name(remote_paths[0])} +{len(remote_paths) - 1}",
            run,
            open_in_tool=open_in_tool,
        )

    @staticmethod
    def _submit_candidate(entries: List[Tuple[str, bool]]) -> str:
        if len(entries) != 1:
            return ""
        path, is_dir = entries[0]
        if is_dir or not path.lower().endswith((".slurm", ".sbatch")):
            return ""
        return path

    @classmethod
    def _batch_submit_candidates(cls, entries: List[Tuple[str, bool]]) -> List[str]:
        """Reuse the single-file candidate rule for each selected entry."""
        paths: List[str] = []
        for entry in entries:
            path = cls._submit_candidate([entry])
            if path:
                paths.append(path)
        return paths

    @staticmethod
    def _shell_run_candidate(entries: List[Tuple[str, bool]]) -> str:
        if len(entries) != 1:
            return ""
        path, is_dir = entries[0]
        if is_dir or not path.lower().endswith(".sh"):
            return ""
        return path

    @staticmethod
    def _batch_shell_candidates(entries: List[Tuple[str, bool]]) -> List[str]:
        return sorted(
            (path for path, is_dir in entries if not is_dir and path.lower().endswith(".sh")),
            key=str.casefold,
        )

    def selected_paths(self, tab_key: str = "all") -> List[str]:
        view = self.views.get(tab_key, self.views["all"])
        return self._selected_paths_from_view(view)

    # ---------- undo ----------
    def _update_undo_enabled(self) -> None:
        self.btn_undo.setEnabled(bool(RemoteDirPanel._last_undo))

    def _set_last_undo(self, rec: Optional[_UndoRecord]) -> None:
        RemoteDirPanel._last_undo = rec
        # reflect on all panels
        for p in list(RemoteDirPanel._instances.values()):
            try:
                p._update_undo_enabled()
            except Exception:
                pass

    def undo_last(self) -> None:
        if not self.session or not self.session.get("files"):
            return
        rec = RemoteDirPanel._last_undo
        if not rec:
            return
        if rec.kind != "move" or not rec.moves:
            self._set_last_undo(None)
            return

        files = self.session["files"]
        # reverse order for safety
        moves = list(reversed(rec.moves))
        affected_dirs = set()

        # build undo plan (dst -> src)
        plan: List[_PlannedOp] = []
        policy: Optional[str] = None

        for src, dst in moves:
            # undo means: move dst back to src
            undo_src = dst.rstrip("/")
            undo_dst = src.rstrip("/")
            affected_dirs.add(self._parent_remote_dir(undo_src))
            affected_dirs.add(self._parent_remote_dir(undo_dst))

            # if destination already exists, resolve
            try:
                exists = bool(files.exists(undo_dst))
            except Exception:
                try:
                    files.listdir(undo_dst)
                    exists = True
                except Exception:
                    exists = False

            if exists:
                if policy is None:
                    action = self._resolve_conflict(
                        undo_dst,
                        src=undo_src,
                        source_is_local=False,
                        target_is_local=False,
                    )
                    if action.endswith("_all"):
                        policy = action.replace("_all", "")
                    action_simple = action.replace("_all", "")
                else:
                    action_simple = policy

                if action_simple == "cancel":
                    return
                if action_simple == "skip":
                    continue
                if action_simple == "rename":
                    dst_dir = os.path.dirname(undo_dst) or "/"
                    current_name = os.path.basename(undo_dst)
                    new_dst = self._prompt_rename(dst_dir, current_name)
                    if not new_dst:
                        continue
                    undo_dst = new_dst
                if action_simple == "overwrite":
                    # delete existing target before moving back
                    try:
                        isdir = bool(files.is_dir(undo_dst))
                    except Exception:
                        isdir = False
                    plan.append(_PlannedOp(op="delete", src="", dst=undo_dst, recursive=isdir))

            plan.append(_PlannedOp(op="move", src=undo_src, dst=undo_dst, recursive=False))

        if not plan:
            self._set_last_undo(None)
            return

        def after_finished() -> None:
            self._set_last_undo(None)
            self._finish_remote_directory_mutation(affected_dirs)

        ok = self._run_plan_with_progress(plan, "Geri alınıyor...", after_finished=after_finished)
        if not ok:
            return

    # ---------- context menu ----------
    def _on_context_menu(self, view: QTreeWidget, pos: QPoint):
        if not self.session or not self.session.get("files"):
            return

        files = self.session.get("files")

        item = view.itemAt(pos)
        clicked_path: Optional[str] = None
        clicked_is_dir = False
        if item is not None:
            if not bool(item.data(0, Qt.ItemDataRole.UserRole + 2)):
                clicked_path = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
                clicked_is_dir = bool(item.data(0, Qt.ItemDataRole.UserRole + 1))

        selected_items = view.selectedItems()
        selected_entries = self._selected_entries_from_view(view)
        if clicked_path and item is not None and not item.isSelected():
            selected_entries = [(clicked_path, clicked_is_dir)]
            selected_items = [item]
        elif not selected_items and clicked_path:
            selected_entries = [(clicked_path, clicked_is_dir)]
        sel_paths = [path for path, _is_dir in selected_entries]
        submit_path = self._submit_candidate(selected_entries)
        batch_submit_paths = self._batch_submit_candidates(selected_entries)
        batch_shell_paths = self._batch_shell_candidates(selected_entries)
        shell_run_path = self._shell_run_candidate(selected_entries)

        menu = QMenu(self)
        clipboard = get_file_clipboard()

        new_parent_dir = clicked_path if clicked_path and clicked_is_dir else (self.current_dir or "/")
        act_download = menu.addAction(REMOTE_CONTEXT_MENU_LABELS[0])
        act_save_as = menu.addAction(_tr("dirs.save_as", "Save as..."))
        act_add_queue = menu.addAction(REMOTE_CONTEXT_MENU_LABELS[1])
        act_view_edit = menu.addAction(REMOTE_CONTEXT_MENU_LABELS[2])
        act_open_new_tab = menu.addAction(REMOTE_CONTEXT_MENU_LABELS[3])
        act_favorite = None
        navigation = self._navigation()
        if navigation is not None and clicked_path:
            act_favorite = menu.addAction(
                _tr("dirs.favorite_remove_item", "Favorilerden kaldır")
                if navigation.is_favorite(clicked_path)
                else _tr("dirs.favorite_add_item", "Favorilere ekle")
            )
        act_submit = None
        if submit_path:
            act_submit = menu.addAction(_tr("dirs.submit_sbatch", "Submit with sbatch"))
        act_batch_submit = None
        if len(batch_submit_paths) >= 2:
            act_batch_submit = menu.addAction(
                _tr("dirs.submit_sbatch_batch", "Submit all with sbatch")
            )
        act_run_shell = None
        if shell_run_path:
            act_run_shell = menu.addAction(_tr("dirs.run_shell_terminal", "Run in terminal"))
        act_batch_shell = None
        if len(batch_shell_paths) >= 2:
            act_batch_shell = menu.addAction(
                _tr("dirs.run_shell_batch_terminal", "Run all in terminal")
            )
        act_open_out1 = None
        act_open_out2 = None
        act_open_file_new_window = None
        act_open_out1_new_window = None
        act_open_out2_new_window = None
        act_open_out1_new_tab = None
        act_open_out2_new_tab = None
        existing_output_actions: Dict[object, Tuple[str, int]] = {}
        if self.enable_output_menu:
            act_open_out1 = menu.addAction(
                _tr("jobs_outputs.open_out1", "Follow in Output 1")
            )
            act_open_out2 = menu.addAction(
                _tr("jobs_outputs.open_out2", "Follow in Output 2")
            )
            act_open_file_new_window = menu.addAction(
                _tr(
                    "jobs_outputs.open_file_new_window",
                    "Follow file in new window",
                )
            )
            act_open_out1_new_window = menu.addAction(
                _tr(
                    "jobs_outputs.open_out1_new_window",
                    "Follow in Output 1 in new window",
                )
            )
            act_open_out2_new_window = menu.addAction(
                _tr(
                    "jobs_outputs.open_out2_new_window",
                    "Follow in Output 2 in new window",
                )
            )
            act_open_out1_new_tab = menu.addAction(
                _tr(
                    "jobs_outputs.open_out1_new_tab",
                    "Follow in Output 1 in new tab",
                )
            )
            act_open_out2_new_tab = menu.addAction(
                _tr(
                    "jobs_outputs.open_out2_new_tab",
                    "Follow in Output 2 in new tab",
                )
            )
            output_targets: List[Tuple[str, str]] = []
            if self._output_target_provider is not None:
                try:
                    output_targets = list(self._output_target_provider() or [])
                except Exception:
                    output_targets = []
            if output_targets:
                menu.addSeparator()
                for target_id, target_label in output_targets:
                    existing_out1 = menu.addAction(
                        _tr(
                            "jobs_outputs.assign_existing_out1",
                            "Assign to {target} Output 1",
                        ).format(target=target_label)
                    )
                    existing_out2 = menu.addAction(
                        _tr(
                            "jobs_outputs.assign_existing_out2",
                            "Assign to {target} Output 2",
                        ).format(target=target_label)
                    )
                    existing_output_actions[existing_out1] = (target_id, 0)
                    existing_output_actions[existing_out2] = (target_id, 1)
        menu.addSeparator()
        act_new_folder = menu.addAction(REMOTE_CONTEXT_MENU_LABELS[5])
        act_new_folder_enter = menu.addAction(REMOTE_CONTEXT_MENU_LABELS[6])
        act_new_file = menu.addAction(REMOTE_CONTEXT_MENU_LABELS[7])
        act_refresh = menu.addAction(REMOTE_CONTEXT_MENU_LABELS[8])
        menu.addSeparator()
        sys_clip = QApplication.clipboard().mimeData()
        has_local_urls = bool(self._local_paths_from_mime(sys_clip))
        clip = clipboard.get()
        act_paste_local_here = None
        act_paste_local_into = None
        act_paste_here = None
        act_paste_into = None
        act_paste_to_local = None
        act_undo = None
        if has_local_urls:
            act_paste_local_here = menu.addAction(
                _tr("dirs.paste_from_local", "Paste from local")
            )
            if clicked_path and clicked_is_dir:
                act_paste_local_into = menu.addAction(
                    _tr("dirs.paste_from_local_into", "Paste from local into folder")
                )
        if clip and clip.paths:
            act_paste_here = menu.addAction(_tr("dirs.paste", "Paste"))
            if clicked_path and clicked_is_dir:
                act_paste_into = menu.addAction(_tr("dirs.paste_into", "Paste into folder"))
            act_paste_to_local = menu.addAction(
                _tr("dirs.paste_to_local", "Paste to local (download)")
            )
        if RemoteDirPanel._last_undo is not None:
            act_undo = menu.addAction(_tr("dirs.undo", "Undo"))
        if any(
            action is not None
            for action in (
                act_paste_local_here,
                act_paste_here,
                act_undo,
            )
        ):
            menu.addSeparator()
        act_delete = menu.addAction(REMOTE_CONTEXT_MENU_LABELS[10])
        act_rename = menu.addAction(REMOTE_CONTEXT_MENU_LABELS[11])
        act_copy_path = menu.addAction(REMOTE_CONTEXT_MENU_LABELS[12])
        act_copy = menu.addAction(_tr("dirs.copy", "Copy"))
        act_move = menu.addAction(_tr("dirs.move", "Move"))
        act_permissions = menu.addAction(REMOTE_CONTEXT_MENU_LABELS[13])

        has_selection = bool(sel_paths)
        single_selection = len(sel_paths) == 1
        single_selection_is_dir = bool(selected_entries[0][1]) if single_selection else False
        act_download.setEnabled(has_selection)
        act_save_as.setEnabled(has_selection)
        act_add_queue.setEnabled(False)
        act_view_edit.setEnabled(single_selection and not single_selection_is_dir)
        # Batch-aware quick lint: 1-10 files and a common tool exists.
        lint_batch_ok = False
        if has_selection:
            all_files = all(not is_dir for _, is_dir in selected_entries)
            if all_files and 1 <= len(sel_paths) <= 10:
                try:
                    from hpc_gui.plugins.linter_tools import tools_supporting_all_suffixes

                    suffixes = [self._remote_suffix(p) for p in sel_paths]
                    lint_batch_ok = bool(tools_supporting_all_suffixes(suffixes))
                except Exception:
                    lint_batch_ok = False
            elif single_selection and single_selection_is_dir and self.session:
                # The recursive remote scan runs only after the user chooses it.
                lint_batch_ok = True
        act_ansys_lint = menu.addAction(_tr("files.ansys_lint", "ANSYS Journal Lint"))
        act_ansys_lint.setEnabled(lint_batch_ok)
        if single_selection and not single_selection_is_dir:
            self._build_send_to_plugin_menu(
                menu, sel_paths[0] if single_selection and not single_selection_is_dir else None
            )
        elif lint_batch_ok:
            try:
                from hpc_gui.plugins.linter_tools import tools_supporting_all_suffixes

                suffixes = [self._remote_suffix(p) for p in sel_paths]
                batch_tools = tools_supporting_all_suffixes(suffixes)
            except Exception:
                batch_tools = []
            if batch_tools:
                send_menu = menu.addMenu(t("files.send_to_plugin"))
                for tool in batch_tools:
                    action = send_menu.addAction(tool.title)
                    action.triggered.connect(
                        lambda _=False, tl=tool, ps=list(sel_paths): self.open_in_tool_batch(tl, ps)
                    )
        act_open_new_tab.setEnabled(single_selection and single_selection_is_dir)
        if act_open_out1 is not None:
            act_open_out1.setEnabled(single_selection and not single_selection_is_dir)
        if act_open_out2 is not None:
            act_open_out2.setEnabled(single_selection and not single_selection_is_dir)
        for action in (
            act_open_file_new_window,
            act_open_out1_new_window,
            act_open_out2_new_window,
            act_open_out1_new_tab,
            act_open_out2_new_tab,
            *existing_output_actions.keys(),
        ):
            if action is not None:
                action.setEnabled(single_selection and not single_selection_is_dir)
        act_delete.setEnabled(has_selection)
        act_rename.setEnabled(single_selection)
        act_copy_path.setEnabled(has_selection)
        act_copy.setEnabled(has_selection)
        act_move.setEnabled(has_selection)
        act_permissions.setEnabled(has_selection)

        chosen = menu.exec(view.viewport().mapToGlobal(pos))
        if not chosen:
            return

        if chosen == act_new_folder:
            self.create_new_folder(new_parent_dir)
            return
        if chosen == act_new_folder_enter:
            self.create_new_folder_and_enter(new_parent_dir)
            return
        if chosen == act_new_file:
            self.create_new_file(new_parent_dir)
            return
        if chosen == act_refresh:
            self._refresh_from_ui(force=True)
            return

        if act_paste_local_here is not None and chosen == act_paste_local_here:
            self._paste_system_clipboard_into(self.current_dir or "/")
            return
        if act_paste_local_into is not None and chosen == act_paste_local_into and clicked_path:
            self._paste_system_clipboard_into(clicked_path)
            return
        if act_paste_here is not None and chosen == act_paste_here:
            self._paste_remote_clipboard_into(self.current_dir or "/")
            return
        if act_paste_into is not None and chosen == act_paste_into and clicked_path:
            self._paste_remote_clipboard_into(clicked_path)
            return
        if act_paste_to_local is not None and chosen == act_paste_to_local:
            self._paste_remote_to_local()
            return
        if act_undo is not None and chosen == act_undo:
            self.undo_last()
            return

        if not sel_paths:
            return

        if act_favorite is not None and chosen == act_favorite and clicked_path:
            navigation.toggle_favorite(
                clicked_path, "directory" if clicked_is_dir else "file"
            )
            return
        if act_submit is not None and chosen == act_submit:
            self.submit_requested.emit(submit_path)
            return

        if act_batch_submit is not None and chosen == act_batch_submit:
            ordered_paths = sorted(batch_submit_paths, key=lambda path: path.casefold())
            self.batch_submit_requested.emit(list(ordered_paths))
            return

        if act_batch_shell is not None and chosen == act_batch_shell:
            self.batch_shell_requested.emit(list(batch_shell_paths))
            return

        if act_run_shell is not None and chosen == act_run_shell:
            self.run_shell_requested.emit(shell_run_path)
            return

        if chosen == act_ansys_lint:
            if len(sel_paths) == 1:
                if single_selection_is_dir:
                    self.run_ansys_lint_folder(sel_paths[0])
                else:
                    self.run_ansys_lint(sel_paths[0])
            else:
                self.run_ansys_lint_batch(sel_paths)
            return

        if chosen == act_view_edit:
            rp = sel_paths[0]
            try:
                files.listdir(rp.rstrip("/"))
                QMessageBox.information(self, t("common.info"), t("dirs.folder_not_editable"))
                return
            except Exception:
                pass
            self.open_file.emit(rp)
            return

        if chosen == act_open_new_tab and single_selection_is_dir:
            self.open_directory_in_new_tab(sel_paths[0])
            return

        if act_open_out1 is not None and chosen == act_open_out1:
            self.open_in_slot.emit(0, sel_paths[0])
            return

        if act_open_out2 is not None and chosen == act_open_out2:
            self.open_in_slot.emit(1, sel_paths[0])
            return

        if act_open_file_new_window is not None and chosen == act_open_file_new_window:
            self.open_file_follow_new_window.emit(sel_paths[0])
            return

        if act_open_out1_new_window is not None and chosen == act_open_out1_new_window:
            self.open_in_slot_new_window.emit(0, sel_paths[0])
            return

        if act_open_out2_new_window is not None and chosen == act_open_out2_new_window:
            self.open_in_slot_new_window.emit(1, sel_paths[0])
            return

        if act_open_out1_new_tab is not None and chosen == act_open_out1_new_tab:
            self.open_in_slot_new_tab.emit(0, sel_paths[0])
            return

        if act_open_out2_new_tab is not None and chosen == act_open_out2_new_tab:
            self.open_in_slot_new_tab.emit(1, sel_paths[0])
            return

        if chosen in existing_output_actions:
            target_id, slot = existing_output_actions[chosen]
            self.open_in_existing_follower.emit(target_id, slot, sel_paths[0])
            return

        if chosen == act_download:
            # The FTP container owns the two-pane transfer target.  Do not
            # open a local-folder dialog here: that used to make the release
            # build's right-click path diverge from toolbar/double-click FTP.
            self.download_requested.emit(list(sel_paths))
            return

        if chosen == act_save_as:
            self.save_as_requested.emit(list(sel_paths))
            return

        if chosen == act_delete:
            self._delete_paths(sel_paths, selected_entries)
            return

        if chosen == act_rename:
            self._rename_paths(sel_paths)
            return

        if chosen == act_copy_path:
            QApplication.clipboard().setText("\n".join(sel_paths))
            return

        if chosen == act_copy:
            clipboard.set("copy", sel_paths)
            return

        if chosen == act_move:
            clipboard.set("move", sel_paths)
            return

        if chosen == act_permissions:
            self.change_permissions(sel_paths, selected_items)
            return

    @staticmethod
    def _parse_chmod_mode(value: str) -> Optional[int]:
        text = (value or "").strip()
        if text.startswith("0"):
            text = text[1:]
        if not re.fullmatch(r"[0-7]{3,4}", text):
            return None
        return int(text, 8)

    def change_permissions(
        self,
        paths: Optional[List[str]] = None,
        selected_items: Optional[List[QTreeWidgetItem]] = None,
    ) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        if paths is None:
            current = self.tabs.currentWidget()
            view = current if isinstance(current, QTreeWidget) else self.views["all"]
            paths = self._selected_paths_from_view(view)
            selected_items = view.selectedItems()
        paths = [path for path in (paths or []) if path]
        if not paths:
            QMessageBox.information(self, t("common.info"), t("dirs.no_file_selected"))
            return False

        initial_mode: Optional[int] = None
        target_name = ""
        if len(paths) == 1 and selected_items:
            try:
                mode = int(selected_items[0].data(0, _FILE_MODE_ROLE) or 0)
            except Exception:
                mode = 0
            if mode:
                initial_mode = pystat.S_IMODE(mode)
            target_name = selected_items[0].text(0)

        dialog = _PermissionsDialog(self, initial_mode, target_name)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        mode = dialog.selected_mode()
        if mode is None:
            QMessageBox.warning(
                self,
                t("common.error"),
                _tr("dirs.permissions_invalid", "Enter a valid octal mode such as 755 or 0644."),
            )
            return False

        files = self.session["files"]
        try:
            for path in paths:
                files.chmod(path, mode)
        except Exception as exc:
            self._show_op_error(
                _tr("dirs.permissions_failed", "Permission update failed: {err}").format(err=exc)
            )
            return False

        self._refresh_from_ui(force=True)
        return True

    def rename_selected(self, view: Optional[QTreeWidget] = None) -> bool:
        if view is None:
            current = self.tabs.currentWidget()
            view = current if isinstance(current, QTreeWidget) else self.views["all"]
        return self._rename_paths(self._selected_paths_from_view(view))

    def _rename_paths(self, paths: List[str]) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        if len(paths) != 1:
            QMessageBox.information(self, t("common.info"), t("dirs.rename_single_required"))
            return False
        old = paths[0].rstrip("/")
        base = old.split("/")[-1]
        new_name, ok = QInputDialog.getText(
            self,
            t("dirs.rename") if t("dirs.rename") != "[dirs.rename]" else "Yeniden Adlandır",
            t("dirs.rename_label"),
            text=base,
        )
        if not ok or not new_name.strip():
            return False
        parent = "/".join(old.split("/")[:-1]) or "/"
        dst = parent.rstrip("/") + "/" + new_name.strip()
        try:
            self.session["files"].rename(old, dst)
            self._finish_remote_directory_mutation([parent])
            return True
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=str(e), exc=e, area="FILES")
            return False

    # ---------- delete / paste ----------
    def _delete_paths(
        self,
        paths: List[str],
        selected_entries: Optional[List[Tuple[str, bool]]] = None,
    ) -> bool:
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return False
        if not paths:
            return False
        msg = t("dirs.delete_confirm") + "\n" + "\n".join([p.split("/")[-1] for p in paths[:10]])
        if len(paths) > 10:
            msg += f"\n... (+{len(paths)-10})"
        if QMessageBox.question(
            self,
            t("common.confirm") if t("common.confirm") != "[common.confirm]" else "Onay",
            msg,
        ) != QMessageBox.StandardButton.Yes:
            return False
        known_directories = {
            path.rstrip("/"): is_dir
            for path, is_dir in (selected_entries or [])
        }
        plan: List[_PlannedOp] = []
        affected_dirs = set()
        for rp in paths:
            clean_path = rp.rstrip("/") or "/"
            recursive = known_directories.get(clean_path)
            if recursive is None and rp.endswith("/"):
                recursive = True
            plan.append(_PlannedOp("delete", "", clean_path, recursive=recursive))
            affected_dirs.add(self._parent_remote_dir(rp))
        affected_dirs.add(self.current_dir or "/")
        return self._run_plan_with_progress(
            plan,
            _tr("transfer.delete_title", "Deleting..."),
            after_finished=lambda dirs=sorted(affected_dirs): self._finish_remote_directory_mutation(dirs),
        )

    def delete_selected(self):
        tab = self.tabs.currentWidget()
        tab_key = "all"
        for k, v in self.views.items():
            if v is tab:
                tab_key = k
                break
        sel = self.selected_paths(tab_key)
        if not sel:
            QMessageBox.information(self, t("common.info"), t("dirs.no_file_selected"))
            return
        self._delete_paths(sel, self._selected_entries_from_view(tab))

    # ---------- conflict dialogs ----------
    def _resolve_conflict(
        self,
        dst: str,
        *,
        src: str = "",
        source_is_local: bool | None = None,
        target_is_local: bool | None = None,
    ):
        """Return one of: overwrite|resume|skip|rename|cancel (optionally applied to all)."""
        source = self._conflict_info(src or dst, is_local=source_is_local)
        target = self._conflict_info(dst, is_local=target_is_local)
        return self._conflict_decision(source, target)

    def reset_conflict_preference(self) -> None:
        """Forget the persisted always-use choice for the active profile."""
        profile_name = str((self.session or {}).get("profile_name", "")).strip() if self.session else ""
        if profile_name:
            clear_profile_conflict_action(profile_name)
        RemoteDirPanel._session_conflict_action = None

    def _conflict_decision(
        self,
        source: TransferConflictInfo,
        target: TransferConflictInfo,
        *,
        partial: bool = False,
    ) -> str:
        """Turn already-known conflict info into a decision.

        Applies the process-wide "always use" action when one is set, otherwise
        shows the conflict dialog. Must run on the GUI thread because it shows a
        modal dialog. Returns the normalized action string, optionally suffixed
        with "_all".
        """
        profile_name = str((self.session or {}).get("profile_name", "")).strip() if self.session else ""
        session_action = get_profile_conflict_action(profile_name) if profile_name else RemoteDirPanel._session_conflict_action
        if session_action is not None:
            return self._normalize_conflict_decision(
                TransferConflictDecision(action=session_action), source, target
            )

        decision = TransferConflictDialog.get_decision(
            self,
            source=source,
            target=target,
            partial=partial,
        )
        action = self._normalize_conflict_decision(decision, source, target)
        if decision.always_use:
            # Keep the selected action (rather than its result) so conditional
            # actions are evaluated against each later conflicting file.
            if profile_name:
                set_profile_conflict_action(profile_name, decision.action)
            else:
                RemoteDirPanel._session_conflict_action = decision.action
        apply_all = bool(decision.always_use or decision.apply_current_queue_only)
        return action + "_all" if apply_all else action

    @Slot(int)
    def _resolve_conflict_from_worker(self, job_id: int) -> None:
        """GUI-thread half of the plan worker's conflict bridge.

        Runs inside a blocking call from the planning thread: shows the conflict
        dialog and leaves the normalized decision on the worker object so the
        planner can continue building the plan off the GUI thread.
        """
        current = self._planning_jobs.get(job_id)
        if current is None:
            return
        worker = current[1]
        try:
            worker._pending_decision = self._conflict_decision(
                worker._pending_source,
                worker._pending_target,
                partial=getattr(worker, "_pending_partial", False),
            )
        except Exception:
            worker._pending_decision = "cancel"

    @Slot(int)
    def _prompt_rename_from_worker(self, job_id: int) -> None:
        """GUI-thread half of the plan worker's rename bridge."""
        current = self._planning_jobs.get(job_id)
        if current is None:
            return
        worker = current[1]
        try:
            worker._pending_rename_result = self._prompt_rename(
                worker._pending_rename_dir,
                worker._pending_rename_name,
            )
        except Exception:
            worker._pending_rename_result = None

    def _conflict_info(
        self,
        path: str,
        *,
        is_local: bool | None = None,
    ) -> TransferConflictInfo:
        if is_local is True:
            try:
                st = os.stat(path)
                return TransferConflictInfo(
                    path=path,
                    size=int(st.st_size),
                    mtime=int(st.st_mtime),
                )
            except Exception:
                return TransferConflictInfo(path=path)
        if is_local is False and self.session and self.session.get("files"):
            try:
                size, mtime = self.session["files"].stat(path)
                return TransferConflictInfo(
                    path=path,
                    size=int(size),
                    mtime=int(mtime),
                )
            except Exception:
                return TransferConflictInfo(path=path)
        try:
            if os.path.exists(path):
                st = os.stat(path)
                return TransferConflictInfo(
                    path=path,
                    size=int(st.st_size),
                    mtime=int(st.st_mtime),
                )
        except Exception:
            pass
        if self.session and self.session.get("files"):
            try:
                size, mtime = self.session["files"].stat(path)
                return TransferConflictInfo(
                    path=path,
                    size=int(size),
                    mtime=int(mtime),
                )
            except Exception:
                pass
        return TransferConflictInfo(path=path)

    @staticmethod
    def _normalize_conflict_decision(
        decision: TransferConflictDecision,
        source: TransferConflictInfo,
        target: TransferConflictInfo,
    ) -> str:
        action = decision.action
        if action in {"overwrite", "resume", "skip", "rename", "cancel"}:
            return action
        source_newer = (
            source.mtime is not None
            and target.mtime is not None
            and int(source.mtime) > int(target.mtime)
        )
        size_differs = (
            source.size is not None
            and target.size is not None
            and int(source.size) != int(target.size)
        )
        if action == "overwrite_if_newer":
            return "overwrite" if source_newer else "skip"
        if action == "overwrite_if_size_differs":
            return "overwrite" if size_differs else "skip"
        if action == "overwrite_if_size_differs_or_newer":
            return "overwrite" if (size_differs or source_newer) else "skip"
        return "cancel"

    def _prompt_rename(self, dst_dir: str, current_name: str) -> str | None:
        new_name, ok = QInputDialog.getText(self, "Yeniden adlandır", "Yeni ad:", text=current_name)
        if not ok:
            return None
        new_name = (new_name or "").strip()
        if not new_name:
            return None
        return dst_dir.rstrip("/") + "/" + new_name

    # ---------- friendly errors (permission/quota UX) ----------
    def _humanize_error(self, raw: str) -> Tuple[str, str]:
        """Return (title, short_message), raw goes to details."""
        text = (raw or "").strip()
        lo = text.lower()

        if "permission denied" in lo or "access is denied" in lo:
            return "İzin yok (Permission denied)", "Bu işlem için gerekli izinlerin yok. (chmod/chown veya doğru dizin?)"

        if "no space left on device" in lo or "disk quota exceeded" in lo or "quota exceeded" in lo:
            return "Disk dolu / Kota aşıldı", "Hedef tarafta boş alan kalmamış veya kota limitine ulaşıldı."

        if "read-only file system" in lo:
            return "Salt okunur dosya sistemi", "Hedef dosya sistemi read-only. Yazma işlemi yapılamaz."

        # fallback
        return t("common.error"), "İşlem başarısız oldu. Detaylar aşağıda."

    def _show_op_error(self, raw: str) -> None:
        title, short = self._humanize_error(raw)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle(title)
        box.setText(short)
        box.setDetailedText(raw)
        box.exec()

    # ---------- queue UI ----------
    def _queue_set(self, plan: List[_PlannedOp]) -> None:
        self.queue_list.clear()
        for op in plan:
            name = os.path.basename((op.dst or op.src).rstrip("/"))
            label = f"{op.op}: {name}"
            self.queue_list.addItem(label)
        self.queue_current.setText("-")
        self.queue_group.setVisible(True)

    def _queue_progress(self, step: int, label: str) -> None:
        self.queue_current.setText(label)
        # Worker emits progress *before* executing the step, so we remove the
        # previous item when step advances.
        if step > 1 and self.queue_list.count() > 0:
            self.queue_list.takeItem(0)

    def _queue_clear(self) -> None:
        self.queue_current.setText("-")
        self.queue_list.clear()
        self.queue_group.setVisible(False)

    def _journal_transfer(self, event: str, **fields) -> None:
        """Append transfer operation events for diagnostics/audit."""
        try:
            import json
            from datetime import datetime

            from hpc_gui.core.paths import app_data_dir

            p = app_data_dir() / "transfer_journal.jsonl"
            p.parent.mkdir(parents=True, exist_ok=True)
            payload = {"ts": datetime.now().isoformat(timespec="seconds"), "event": event}
            payload.update(fields or {})
            with p.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # ---------- plan runner ----------
    @staticmethod
    def _transfer_items_from_plan(plan: List[_PlannedOp]) -> List[TransferItem]:
        """Convert a plan into transfer items, keeping any already-known size."""
        return [
            TransferItem(
                op=p.op,
                src=p.src,
                dst=p.dst,
                recursive=p.recursive,
                cached_size=p.size,
            )
            for p in plan
        ]

    def _run_plan_with_progress(
        self,
        plan: List[_PlannedOp],
        title: str,
        after_finished=None,
        *,
        confirm_before_start: bool = False,
    ) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        if not plan:
            return True
        active_keys: set[tuple[str, str, str]] = set()
        filtered_plan: List[_PlannedOp] = []
        for op in plan:
            key = self._transfer_key(op)
            if key is not None:
                if key in self._active_transfer_keys or key in active_keys:
                    continue
                active_keys.add(key)
            filtered_plan.append(op)
        if not filtered_plan:
            return True
        plan = filtered_plan
        transfer_items = self._transfer_items_from_plan(plan)
        files = self.session["files"]
        # The per-profile value is the single authority. A legacy profile
        # without the field safely defaults to 1; the stored *global*
        # "transfer_parallelism" settings key is never used here.
        configured_parallel_limit = coerce_profile_transfer_parallelism(
            getattr(self.session.get("cfg"), "transfer_parallelism", None),
            1,
        )
        backend_parallel_limit = (
            configured_parallel_limit
            if bool(getattr(files, "supports_parallel_transfers", False))
            else 1
        )
        effective_parallel_limit = min(
            configured_parallel_limit,
            backend_parallel_limit,
        )
        if confirm_before_start and not self._confirm_transfer_plan(
            transfer_items,
            title,
            effective_parallel_limit,
        ):
            return False

        for dlg in list(self._transfer_dialogs):
            if not dlg.is_active():
                continue
            if dlg.enqueue(transfer_items):
                dlg._truba_active_keys.update(active_keys)
                dlg._truba_plans.append(plan)
                dlg._truba_after_finished.append(after_finished)
                self._active_transfer_keys.update(active_keys)
                if self._transfer_activity_callback is not None:
                    self._transfer_activity_callback("queued", transfer_items, title)
                return True

        self._active_transfer_keys.update(active_keys)
        if self._transfer_activity_callback is not None:
            self._transfer_activity_callback("queued", transfer_items, title)
        dlg = TransferDialog(
            self,
            title=title,
            items=transfer_items,
            run_item=self._execute_transfer_item,
            parallel_limit=effective_parallel_limit,
            max_parallel_limit=backend_parallel_limit,
            configured_limit=configured_parallel_limit,
            backend_context_factory=self._transfer_backend_context,
        )
        if self._transfer_activity_callback is not None:
            self._transfer_activity_callback("controller", [dlg], title)
        self._active_plan = list(plan)
        self._active_step = 0
        self._active_title = title
        dlg._truba_active_keys = active_keys
        dlg._truba_plans = [plan]
        dlg._truba_after_finished = [after_finished]
        def handle_finished(_result: int) -> None:
            try:
                if self._transfer_activity_callback is not None:
                    event = "completed" if dlg.finished_cleanly() else "failed"
                    event_items = (
                        list(dlg._completed)
                        if event == "completed"
                        else [item for item, _error in dlg._errors]
                    )
                    self._transfer_activity_callback(event, event_items, title)
                if dlg.finished_cleanly():
                    for callback in dlg._truba_after_finished:
                        if callback is not None:
                            callback()
                    for queued_plan in dlg._truba_plans:
                        self._refresh_local_transfer_targets(queued_plan)
            finally:
                self._active_transfer_keys.difference_update(dlg._truba_active_keys)
                try:
                    self._transfer_dialogs.remove(dlg)
                except ValueError:
                    pass
                dlg.deleteLater()

        def release_reserved_keys() -> None:
            # The queue is done; stop treating these transfers as in flight.
            # Waiting for `finished` used to hold them forever after a cancel,
            # because a cancelled dialog stays open and never emits it - so
            # re-downloading the same files planned them and then filtered
            # every one of them out again as a duplicate.
            self._active_transfer_keys.difference_update(dlg._truba_active_keys)

        dlg.queueFinished.connect(release_reserved_keys)
        dlg.finished.connect(handle_finished)
        self._transfer_dialogs.append(dlg)
        dlg.start()
        if self._show_transfer_dialog:
            dlg.show()
        self._active_plan = []
        self._active_step = 0
        self._active_title = ""
        return True

    def _refresh_local_transfer_targets(self, plan: List[_PlannedOp]) -> None:
        """Refresh local folders affected by a completed transfer plan."""
        callback = self._local_target_refresh_callback
        if callback is None:
            return
        target_dirs = {
            os.path.dirname(os.path.abspath(op.dst))
            for op in plan
            if op.op in {"download", "mkdir_local", "delete_local"} and op.dst
        }
        for target_dir in sorted(target_dirs):
            try:
                callback(target_dir)
            except Exception:
                # Refreshing a view must never turn a successful transfer into
                # a failed one.
                pass

    def _confirm_transfer_plan(
        self,
        transfer_items: List[TransferItem],
        title: str,
        parallel_limit: int,
    ) -> bool:
        if not get_upload_preflight_confirmation_enabled():
            return True
        dialog = TransferPreflightDialog(
            self,
            title=title,
            items=transfer_items,
            parallel_limit=parallel_limit,
        )
        try:
            accepted = dialog.exec() == QDialog.DialogCode.Accepted
            if accepted and dialog.cb_dont_ask_again.isChecked():
                set_upload_preflight_confirmation_enabled(False)
            return accepted
        finally:
            dialog.deleteLater()

    @staticmethod
    def _transfer_key(op: _PlannedOp) -> tuple[str, str, str] | None:
        if op.op not in {"upload", "download"}:
            return None
        return (op.op, op.src, op.dst)

    def _transfer_backend_context(self):
        """Return an isolated files backend for one parallel transfer worker.

        Only backends that declare ``supports_parallel_transfers`` and expose
        ``open_transfer_backend`` qualify; the transfer queue closes whatever
        this returns after each item (success, failure, or cancellation).
        """
        files = self.session.get("files") if self.session else None
        if files is None or not bool(getattr(files, "supports_parallel_transfers", False)):
            return None
        opener = getattr(files, "open_transfer_backend", None)
        return opener() if callable(opener) else None

    def _execute_transfer_item(self, item: TransferItem, progress_cb=None, *, files=None) -> None:
        if not self.session or not self.session.get("files"):
            raise RuntimeError(t("common.no_connection"))
        files = files or self.session["files"]
        op = item.op
        if op == "delete":
            recursive = item.recursive
            if recursive is None:
                try:
                    recursive = bool(files.is_dir(item.dst))
                except Exception:
                    try:
                        files.listdir(item.dst)
                        recursive = True
                    except Exception:
                        recursive = False
            files.remove(item.dst, recursive=bool(recursive))
        elif op == "copy":
            files.copy(item.src, item.dst, recursive=item.recursive)
        elif op == "move":
            files.move(item.src, item.dst)
        elif op == "upload":
            upload_with_mode(
                files,
                item.src,
                item.dst,
                self._requested_transfer_mode(item.src),
                progress_cb=progress_cb,
            )
            self._verify_transfer_item(item, files=files)
        elif op == "download":
            download_with_mode(
                files,
                item.src,
                item.dst,
                self._requested_transfer_mode(item.src),
                progress_cb=progress_cb,
            )
            self._verify_transfer_item(item, files=files)
        elif op == "mkdir_remote":
            files.mkdir(item.dst)
        elif op == "mkdir_local":
            os.makedirs(item.dst, exist_ok=True)
        elif op == "delete_local":
            if os.path.isdir(item.dst):
                shutil.rmtree(item.dst, ignore_errors=True)
            else:
                try:
                    os.remove(item.dst)
                except FileNotFoundError:
                    pass
        else:
            raise RuntimeError(f"Unknown op: {op}")

    @staticmethod
    def _sha256_local(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _verify_transfer_item(self, item: TransferItem, *, files=None) -> None:
        if not get_transfer_checksum_verification_enabled():
            return
        files = files or self.session["files"]
        remote_hash = getattr(files, "sha256", None)
        if not callable(remote_hash):
            raise RuntimeError(
                "SHA-256 verification is enabled, but this backend does not provide remote checksums."
            )
        local_path = item.src if item.op == "upload" else item.dst
        remote_path = item.dst if item.op == "upload" else item.src
        local_digest = self._sha256_local(local_path)
        remote_digest = str(remote_hash(remote_path) or "").strip().lower()
        if not remote_digest or local_digest != remote_digest:
            raise RuntimeError(
                f"SHA-256 verification failed for {remote_path}: "
                f"local={local_digest}, remote={remote_digest or '<missing>'}"
            )

    def shutdown(self) -> None:
        """Cancel any in-flight batch operation (best-effort).

        This does not add new UX; it only prevents orphan threads and
        persists remaining steps as a diagnostic artifact.
        """
        still_running: Dict[int, Tuple[QThread, _TransferPlanWorker]] = {}
        try:
            if self._active_worker is not None:
                try:
                    self._active_worker.cancel()
                except Exception:
                    pass
            if self._active_thread is not None:
                try:
                    self._active_thread.quit()
                except Exception:
                    pass
                try:
                    self._active_thread.wait(1500)
                except Exception:
                    pass
            planning_jobs = list(self._planning_jobs.items())
            for _job_id, (_thread, worker) in planning_jobs:
                worker.cancelled = True
            # Interrupt a planner blocked in the shared browsing SFTP channel
            # before the SSH transport is closed by MainWindow shutdown.
            try:
                files = (self.session or {}).get("files")
                ssh = getattr(files, "ssh", None)
                sftp = getattr(ssh, "sftp", None)
                if sftp is not None:
                    sftp.close()
            except Exception:
                pass
            for job_id, (thread, worker) in planning_jobs:
                try:
                    thread.quit()
                    thread.wait(1500)
                except Exception:
                    pass
                # A worker can still be alive here (e.g. blocked on a
                # synchronous SFTP call, or on a BlockingQueuedConnection
                # back to this now-shutting-down GUI thread). Never drop the
                # last Python reference to a QThread whose OS thread is still
                # running: PySide6 destroying it in that state is a fatal
                # native crash ("QThread: Destroyed while thread is still
                # running"). Keep it referenced; the `thread.finished` signal
                # already wired at creation calls `_planning_job_finished`,
                # which pops and `deleteLater()`s it once it actually stops.
                if thread.isRunning():
                    still_running[job_id] = (thread, worker)
            # Persist remaining plan if any.
            try:
                if self._active_plan:
                    remaining = self._active_plan[max(0, self._active_step - 1):]
                    if remaining:
                        self._persist_batch_state(remaining, title=self._active_title or "shutdown")
            except Exception:
                pass
        finally:
            self._unregister_instance()
            self._local_upload_plan_jobs.clear()
            self._planning_jobs = still_running
            self._active_thread = None
            self._active_worker = None
            self._active_plan = []
            self._active_step = 0
            self._active_title = ""

    def _persist_batch_state(self, remaining: List[_PlannedOp], *, title: str) -> None:
        """Write remaining batch operations to ~/.truba_slurm_gui/last_batch.json.

        This is *logs-only* / diagnostics; it does not auto-resume.
        """
        try:
            import json
            import time

            from hpc_gui.core.paths import app_data_dir

            out_path = app_data_dir() / "last_batch.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "ts": int(time.time()),
                "title": title,
                "remaining": [
                    {
                        "op": op.op,
                        "src": op.src,
                        "dst": op.dst,
                        "recursive": bool(op.recursive),
                    }
                    for op in remaining
                ],
            }
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    # ---------- copy/move helpers ----------
    def _build_copy_move_plan_with_conflicts(self, op: str, src_paths: List[str], dest_dir: str) -> List[_PlannedOp] | None:
        if not self.session or not self.session.get("files"):
            return None
        files = self.session.get("files")

        plan: List[_PlannedOp] = []
        policy: Optional[str] = None  # overwrite/skip/rename/cancel

        for src in src_paths:
            src_clean = src.rstrip("/")
            name = os.path.basename(src_clean)
            dst_dir = dest_dir.rstrip("/") or "/"
            dst = dst_dir.rstrip("/") + "/" + name

            recursive = False
            if op == "copy":
                try:
                    recursive = bool(files.is_dir(src_clean))
                except Exception:
                    try:
                        files.listdir(src_clean)
                        recursive = True
                    except Exception:
                        recursive = False

            while True:
                try:
                    exists = bool(files.exists(dst))
                except Exception:
                    try:
                        files.listdir(dst)
                        exists = True
                    except Exception:
                        exists = False

                if exists:
                    if policy is None:
                        action = self._resolve_conflict(
                            dst,
                            src=src_clean,
                            source_is_local=False,
                            target_is_local=False,
                        )
                        if action.endswith("_all"):
                            policy = action.replace("_all", "")
                        action_simple = action.replace("_all", "")
                    else:
                        action_simple = policy

                    if action_simple == "cancel":
                        return None
                    if action_simple == "skip":
                        break
                    if action_simple == "rename":
                        new_dst = self._prompt_rename(dst_dir, name)
                        if not new_dst:
                            break
                        dst = new_dst
                        continue
                    if action_simple == "overwrite":
                        try:
                            isdir = bool(files.is_dir(dst))
                        except Exception:
                            isdir = False
                        plan.append(_PlannedOp(op="delete", src="", dst=dst, recursive=isdir))

                plan.append(_PlannedOp(op=op, src=src_clean, dst=dst, recursive=recursive))
                break

        return plan

    def _apply_copy_move_with_conflicts(self, op: str, src_paths: List[str], dest_dir: str) -> bool:
        plan = self._build_copy_move_plan_with_conflicts(op, src_paths, dest_dir)
        if plan is None:
            return False

        title = "İşlem yapılıyor..."
        if op == "copy":
            title = "Kopyalanıyor..."
        elif op == "move":
            title = "Taşınıyor..."

        affected_dirs = {self._normalize_remote_dir(dest_dir)}
        if op == "move":
            for src in src_paths:
                affected_dirs.add(self._parent_remote_dir(src))

        ok = self._run_plan_with_progress(
            plan,
            title,
            after_finished=lambda: self._finish_remote_directory_mutation(affected_dirs),
        )
        if not ok:
            return False

        # store undo for move only
        if op == "move":
            moves: List[Tuple[str, str]] = [(p.src, p.dst) for p in plan if p.op == "move"]
            if moves:
                self._set_last_undo(_UndoRecord(kind="move", moves=moves))
        return True

    def _paste_remote_clipboard_into(self, dest_dir: str) -> None:
        if not self.session or not self.session.get("files"):
            return
        clipboard = get_file_clipboard()
        clip = clipboard.get()
        if not clip or not clip.paths:
            return

        dest_dir = (dest_dir or "/").strip()
        if not dest_dir.startswith("/"):
            dest_dir = "/" + dest_dir
        dest_dir = dest_dir.rstrip("/") or "/"

        try:
            op = "copy" if clip.op == "copy" else "move"
            ok = self._apply_copy_move_with_conflicts(op, [s for s in clip.paths], dest_dir)
            if ok and clip.op == "move":
                clipboard.clear()
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=str(e), exc=e, area="FILES")


    def _paste_system_clipboard_into(self, dest_dir: str) -> bool:
        """If OS clipboard contains local file urls, upload them into dest_dir."""
        cb = QApplication.clipboard().mimeData()
        if not cb or not cb.hasUrls():
            return False
        local_paths = [u.toLocalFile() for u in cb.urls() if u.isLocalFile()]
        if not local_paths:
            return False
        return self._apply_local_upload_incremental(local_paths, dest_dir)

    def _paste_remote_to_local(self) -> None:
        """Download internal remote clipboard items into a chosen local directory."""
        if not self.session or not self.session.get("files"):
            return
        clip = get_file_clipboard().get()
        if not clip or not clip.paths:
            return
        target_dir = QFileDialog.getExistingDirectory(
            self, t("dirs.select_local_folder")
        )
        if not target_dir:
            return
        ok = self._apply_remote_download_incremental(clip.paths, target_dir)
        if ok and clip.op == "move":
            # move doesn't make sense for remote->local; keep clipboard as-is
            pass

    def _remote_walk(self, base_remote: str) -> List[Tuple[str, str, bool]]:
        """Return list of (remote_path, rel_path, is_dir) under base_remote including base."""
        files = self.session["files"]
        base_remote = base_remote.rstrip("/")
        out: List[Tuple[str, str, bool]] = []

        def rec(cur: str, rel: str):
            try:
                entries = files.listdir_entries(cur)
            except Exception:
                return
            for e in entries:
                epath = e.path.rstrip("/")
                erel = (rel + "/" if rel else "") + e.name
                if e.is_dir:
                    out.append((epath, erel, True))
                    rec(epath, erel)
                else:
                    out.append((epath, erel, False))

        out.append((base_remote, "", True))
        rec(base_remote, "")
        return out

    def _apply_remote_download(self, src_paths: List[str], target_dir: str) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        files = self.session["files"]
        target_dir = os.path.abspath(target_dir)

        plan: List[_PlannedOp] = []
        policy: Optional[str] = None

        seen_sources: set[str] = set()
        for src in src_paths:
            src_clean = src.rstrip("/")
            if not src_clean or src_clean in seen_sources:
                continue
            seen_sources.add(src_clean)
            name = os.path.basename(src_clean)
            local_dst = os.path.join(target_dir, name)

            # detect if remote is dir
            try:
                is_dir = bool(files.is_dir(src_clean))
            except Exception:
                is_dir = src.endswith("/")

            # conflict resolution on local target
            while os.path.exists(local_dst):
                # A directory selected for download merges into an existing
                # directory of the same name.  Individual files below it are
                # still checked for conflicts during the recursive walk.
                if is_dir and os.path.isdir(local_dst):
                    break
                if policy is None:
                    action = self._resolve_conflict(
                        local_dst,
                        src=src_clean,
                        source_is_local=False,
                        target_is_local=True,
                    )
                    if action.endswith("_all"):
                        policy = action.replace("_all", "")
                    action_simple = action.replace("_all", "")
                else:
                    action_simple = policy

                if action_simple == "cancel":
                    return False
                if action_simple == "skip":
                    local_dst = None
                    break
                if action_simple == "rename":
                    new_dst = self._prompt_rename(target_dir, name)
                    if not new_dst:
                        local_dst = None
                        break
                    local_dst = new_dst
                    continue
                if action_simple == "overwrite":
                    plan.append(_PlannedOp(op="delete_local", src="", dst=local_dst, recursive=is_dir))
                    break
                if action_simple == "resume":
                    break

            if not local_dst:
                continue

            if not is_dir:
                plan.append(_PlannedOp(op="download", src=src_clean, dst=local_dst))
            else:
                # mkdir base local
                plan.append(_PlannedOp(op="mkdir_local", src="", dst=local_dst, recursive=False))
                # walk remote dir and download files
                for rpath, rel, r_is_dir in self._remote_walk(src_clean):
                    if rel == "":
                        continue
                    lp = os.path.join(local_dst, rel)
                    if r_is_dir:
                        plan.append(_PlannedOp(op="mkdir_local", src="", dst=lp))
                    else:
                        while os.path.exists(lp):
                            if policy is None:
                                action = self._resolve_conflict(
                                    lp,
                                    src=rpath,
                                    source_is_local=False,
                                    target_is_local=True,
                                )
                                if action.endswith("_all"):
                                    policy = action.replace("_all", "")
                                action_simple = action.replace("_all", "")
                            else:
                                action_simple = policy

                            if action_simple == "cancel":
                                return False
                            if action_simple == "skip":
                                lp = None
                                break
                            if action_simple == "rename":
                                new_dst = self._prompt_rename(
                                    os.path.dirname(lp),
                                    os.path.basename(lp),
                                )
                                if not new_dst:
                                    lp = None
                                    break
                                lp = new_dst
                                continue
                            if action_simple == "overwrite":
                                plan.append(_PlannedOp(op="delete_local", src="", dst=lp, recursive=False))
                                break
                            if action_simple == "resume":
                                break
                            break
                        if not lp:
                            continue
                        plan.append(_PlannedOp(op="download", src=rpath, dst=lp))

        if not plan:
            return True
        ok = self._run_plan_with_progress(plan, "İndiriliyor...")
        return ok

    def _apply_remote_download_incremental(
        self,
        src_paths: List[str],
        target_dir: str,
    ) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        files = self.session["files"]
        clean_paths = [path for path in src_paths if path]
        absolute_target = os.path.abspath(target_dir)
        if not clean_paths:
            return True
        return self._start_transfer_planning(
            "download",
            lambda worker: self._build_remote_download_plan_background(
                worker,
                files,
                clean_paths,
                absolute_target,
            ),
        )

    def _start_transfer_planning(self, kind: str, planner) -> bool:
        job_id = self._next_planning_job_id
        self._next_planning_job_id += 1
        thread = QThread()
        worker = _TransferPlanWorker(job_id, kind, planner, panel=self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_transfer_plan_finished)
        worker.failed.connect(self._on_transfer_plan_failed)
        worker.finished.connect(lambda *_args, current=thread: current.quit())
        worker.failed.connect(lambda *_args, current=thread: current.quit())
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(
            lambda current_job_id=job_id: self._planning_job_finished(
                current_job_id
            )
        )
        self._planning_jobs[job_id] = (thread, worker)
        thread.start()
        return True

    @Slot(int, str, object)
    def _on_transfer_plan_finished(
        self,
        job_id: int,
        kind: str,
        result,
    ) -> None:
        if not isValid(self):
            return
        if job_id not in self._planning_jobs or not result:
            return
        if result.get("conflict"):
            # Only upload planning defers conflict resolution to the bounded
            # GUI-thread planner. Remote download planning resolves conflicts
            # on the worker thread and therefore never returns this sentinel.
            self._apply_local_upload_incremental_gui(
                result["paths"],
                result["directory"],
            )
            return
        plan = result.get("plan") or []
        if not plan:
            return
        affected_dirs = list(result.get("affected_dirs") or [])
        self._run_plan_with_progress(
            plan,
            result["title"],
            after_finished=lambda dirs=affected_dirs: (
                self._finish_remote_directory_mutation(dirs)
            ),
            confirm_before_start=bool(result.get("confirm_before_start")),
        )

    @Slot(int, str, object)
    def _on_transfer_plan_failed(
        self,
        job_id: int,
        _kind: str,
        exc,
    ) -> None:
        if not isValid(self):
            return
        if job_id not in self._planning_jobs:
            return
        show_exception(
            self,
            title=t("common.error"),
            user_message=str(exc),
            exc=exc,
            area="FILES",
        )

    def _planning_job_finished(self, job_id: int) -> None:
        if not isValid(self):
            # The panel's underlying C++ QWidget can already be gone by the
            # time a background planning QThread we deliberately kept alive
            # (see shutdown()) finally emits `finished` during app teardown.
            # Touching `self` past that point corrupts native heap state
            # instead of raising a clean Python error. There is nothing left
            # to clean up on a destroyed panel; let `thread`/`worker` be
            # garbage-collected once the signal-connection reference drops.
            return
        current = self._planning_jobs.pop(job_id, None)
        if current is not None:
            thread, _worker = current
            thread.deleteLater()

    def _build_remote_download_plan_background(
        self,
        worker: _TransferPlanWorker,
        files,
        src_paths: List[str],
        target_dir: str,
    ) -> dict:
        plan: List[_PlannedOp] = []
        affected_dirs: set[str] = set()
        seen: set[str] = set()
        policy: Optional[str] = None
        if is_source_run():
            get_logger("hpc_gui.debug.transfer").info(
                "plan.download started sources=%d target=%r session_policy=%r",
                len(src_paths), target_dir,
                RemoteDirPanel._session_conflict_action,
            )
        for src in src_paths:
            if worker.cancelled:
                return {}
            src_clean = src.rstrip("/")
            if not src_clean or src_clean in seen:
                continue
            seen.add(src_clean)
            try:
                is_dir = bool(files.is_dir(src_clean))
            except Exception:
                is_dir = src.endswith("/")
            if is_source_run():
                get_logger("hpc_gui.debug.transfer").info(
                    "plan.source remote=%r is_dir=%s", src_clean, is_dir,
                )
            affected_dirs.add(self._parent_remote_dir(src_clean))
            if is_dir:
                affected_dirs.add(self._normalize_remote_dir(src_clean))
            local_dst = os.path.join(target_dir, os.path.basename(src_clean))
            local_dst, policy = self._resolve_download_target_conflict_worker(
                worker,
                local_dst,
                src_clean,
                is_dir=is_dir,
                policy=policy,
                plan=plan,
            )
            if local_dst is None:
                return {}
            if not local_dst:
                continue
            if not is_dir:
                plan.append(_PlannedOp("download", src_clean, local_dst))
                continue
            plan.append(_PlannedOp("mkdir_local", "", local_dst))
            stack: List[Tuple[str, str]] = [(src_clean, "")]
            while stack:
                if worker.cancelled:
                    return {}
                remote_dir, rel_dir = stack.pop()
                # Do not swallow this. A failed listing here used to leave the
                # directory out of the plan silently, so the queue ran only the
                # mkdirs and reported success while nothing was downloaded.
                entries = list(files.listdir_entries(remote_dir))
                if is_source_run():
                    get_logger("hpc_gui.debug.transfer").info(
                        "plan.walk remote_dir=%r entries=%d dirs=%d",
                        remote_dir, len(entries),
                        sum(1 for entry in entries if entry.is_dir),
                    )
                child_dirs: List[Tuple[str, str]] = []
                for entry in entries:
                    rel_path = f"{rel_dir}/{entry.name}" if rel_dir else entry.name
                    local_path = os.path.join(local_dst, rel_path)
                    remote_path = entry.path.rstrip("/")
                    if entry.is_dir:
                        plan.append(_PlannedOp("mkdir_local", "", local_path))
                        child_dirs.append((remote_path, rel_path))
                        continue
                    resolved, policy = self._resolve_download_target_conflict_worker(
                        worker,
                        local_path,
                        remote_path,
                        is_dir=False,
                        policy=policy,
                        plan=plan,
                    )
                    if resolved is None:
                        return {}
                    if not resolved:
                        continue
                    plan.append(
                        _PlannedOp(
                            "download",
                            remote_path,
                            resolved,
                            size=int(entry.size or 0),
                        )
                    )
                stack.extend(reversed(child_dirs))
        if is_source_run():
            counts: Dict[str, int] = {}
            for op in plan:
                counts[op.op] = counts.get(op.op, 0) + 1
            get_logger("hpc_gui.debug.transfer").info(
                "plan.download finished ops=%d breakdown=%r policy=%r",
                len(plan), counts, policy,
            )
        return {
            "plan": plan,
            "title": "İndiriliyor...",
            "affected_dirs": sorted(affected_dirs),
            "confirm_before_start": False,
        }

    def _resolve_download_target_conflict_worker(
        self,
        worker: _TransferPlanWorker,
        local_path: str,
        remote_path: str,
        *,
        is_dir: bool,
        policy: Optional[str],
        plan: List[_PlannedOp],
    ) -> Tuple[Optional[str], Optional[str]]:
        """Resolve a download destination conflict while planning off the GUI thread.

        Remote stat probes for the conflict dialog run on the worker thread;
        only the decision and rename dialogs are shown on the GUI thread via
        the worker's blocking bridge. Returns the resolved local target path
        (None = cancel, "" = skip) together with the updated policy, and appends
        delete_local ops to `plan` for overwrite choices.
        """
        while True:
            part_path = local_path + PARTIAL_DOWNLOAD_SUFFIX
            # A leftover ".part" from a cancelled attempt is prior state the
            # user has to rule on too: resuming it or throwing it away is not
            # a decision this planner gets to make silently.
            partial = (
                not is_dir
                and not os.path.exists(local_path)
                and os.path.exists(part_path)
            )
            if not partial and not os.path.exists(local_path):
                return local_path, policy
            # Do not treat the selected directory itself as a conflict: merge
            # it, then resolve conflicts for its contained files.
            if is_dir and os.path.isdir(local_path):
                return local_path, policy
            if policy is None:
                source = self._conflict_info(remote_path, is_local=False)
                target = self._conflict_info(
                    part_path if partial else local_path, is_local=True
                )
                raw_action = worker.request_conflict_decision(
                    source, target, partial=partial
                )
                if raw_action.endswith("_all"):
                    policy = raw_action.replace("_all", "")
                action_simple = raw_action.replace("_all", "")
            else:
                action_simple = policy
            if is_source_run():
                get_logger("hpc_gui.debug.transfer").info(
                    "plan.conflict remote=%r local=%r partial=%s action=%s policy=%r",
                    remote_path, local_path, partial, action_simple, policy,
                )
            if action_simple == "cancel":
                return None, policy
            if action_simple == "skip":
                return "", policy
            if action_simple == "rename":
                renamed = worker.request_rename(
                    os.path.dirname(local_path),
                    os.path.basename(local_path),
                )
                if not renamed:
                    return "", policy
                local_path = renamed
                continue
            if action_simple == "overwrite":
                # Overwrite means start over, so drop the leftover chunk as
                # well - otherwise the transfer would quietly resume from it.
                plan.append(
                    _PlannedOp(
                        op="delete_local",
                        src="",
                        dst=part_path if partial else local_path,
                        recursive=False if partial else is_dir,
                    )
                )
            # "resume" falls through unchanged: the partial stays, and
            # download_with_mode continues from it once its identity matches.
            return local_path, policy

    def _apply_local_upload(self, local_paths: List[str], dest_dir: str) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        files = self.session["files"]

        dest_dir = (dest_dir or "/").strip()
        if not dest_dir.startswith("/"):
            dest_dir = "/" + dest_dir
        dest_dir = dest_dir.rstrip("/") or "/"

        plan: List[_PlannedOp] = []
        policy: Optional[str] = None

        seen_sources: set[str] = set()
        for lp in local_paths:
            if not lp:
                continue
            lp = os.path.abspath(lp)
            if lp in seen_sources:
                continue
            seen_sources.add(lp)
            name = os.path.basename(lp.rstrip(os.sep))
            rp_base = dest_dir.rstrip("/") + "/" + name
            is_dir = os.path.isdir(lp)

            # conflict resolution on remote target
            while True:
                try:
                    exists = bool(files.exists(rp_base))
                except Exception:
                    exists = False

                if exists and is_dir:
                    try:
                        target_is_dir = bool(files.is_dir(rp_base))
                    except Exception:
                        target_is_dir = False
                    if target_is_dir:
                        # Merge matching directories; nested file conflicts
                        # are handled below while building the upload plan.
                        break

                if exists:
                    if policy is None:
                        action = self._resolve_conflict(
                            rp_base,
                            src=lp,
                            source_is_local=True,
                            target_is_local=False,
                        )
                        if action.endswith("_all"):
                            policy = action.replace("_all", "")
                        action_simple = action.replace("_all", "")
                    else:
                        action_simple = policy

                    if action_simple == "cancel":
                        return False
                    if action_simple == "skip":
                        rp_base = None
                        break
                    if action_simple == "rename":
                        new_dst = self._prompt_rename(dest_dir, name)
                        if not new_dst:
                            rp_base = None
                            break
                        rp_base = new_dst
                        continue
                    if action_simple == "overwrite":
                        try:
                            isdir_remote = bool(files.is_dir(rp_base))
                        except Exception:
                            isdir_remote = False
                        plan.append(_PlannedOp(op="delete", src="", dst=rp_base, recursive=isdir_remote))
                    elif action_simple == "resume":
                        pass
                break

            if not rp_base:
                continue

            if not is_dir:
                plan.append(_PlannedOp(op="upload", src=lp, dst=rp_base))
            else:
                # mkdir base
                plan.append(_PlannedOp(op="mkdir_remote", src="", dst=rp_base))
                # walk local dir
                for root, dirs, files_ls in os.walk(lp):
                    rel_root = os.path.relpath(root, lp)
                    rel_root = "" if rel_root == "." else rel_root
                    for d in dirs:
                        rdir = rp_base + ("/" + rel_root if rel_root else "") + "/" + d
                        plan.append(_PlannedOp(op="mkdir_remote", src="", dst=rdir))
                    for fn in files_ls:
                        lfile = os.path.join(root, fn)
                        rfile = rp_base + ("/" + rel_root if rel_root else "") + "/" + fn
                        while True:
                            try:
                                exists = bool(files.exists(rfile))
                            except Exception:
                                exists = False
                            if not exists:
                                break

                            if policy is None:
                                action = self._resolve_conflict(
                                    rfile,
                                    src=lfile,
                                    source_is_local=True,
                                    target_is_local=False,
                                )
                                if action.endswith("_all"):
                                    policy = action.replace("_all", "")
                                action_simple = action.replace("_all", "")
                            else:
                                action_simple = policy

                            if action_simple == "cancel":
                                return False
                            if action_simple == "skip":
                                rfile = None
                                break
                            if action_simple == "rename":
                                new_dst = self._prompt_rename(
                                    rfile.rsplit("/", 1)[0],
                                    fn,
                                )
                                if not new_dst:
                                    rfile = None
                                    break
                                rfile = new_dst
                                continue
                            if action_simple == "overwrite":
                                try:
                                    isdir_remote = bool(files.is_dir(rfile))
                                except Exception:
                                    isdir_remote = False
                                plan.append(_PlannedOp(op="delete", src="", dst=rfile, recursive=isdir_remote))
                                break
                            if action_simple == "resume":
                                break
                            break
                        if not rfile:
                            continue
                        plan.append(_PlannedOp(op="upload", src=lfile, dst=rfile))

        if not plan:
            return True

        return self._run_plan_with_progress(
            plan,
            "Yükleniyor...",
            after_finished=lambda: self._finish_remote_directory_mutation([dest_dir]),
            confirm_before_start=True,
        )

    def _apply_local_upload_incremental(self, local_paths: List[str], dest_dir: str) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        normalized_dest = (dest_dir or "/").strip()
        if not normalized_dest.startswith("/"):
            normalized_dest = "/" + normalized_dest
        normalized_dest = normalized_dest.rstrip("/") or "/"
        clean_paths = [path for path in local_paths if path]
        if not clean_paths:
            return True
        files = self.session["files"]
        return self._start_transfer_planning(
            "upload",
            lambda worker: self._build_local_upload_plan_background(
                worker,
                files,
                clean_paths,
                normalized_dest,
            ),
        )

    def _build_local_upload_plan_background(
        self,
        worker: _TransferPlanWorker,
        files,
        local_paths: List[str],
        dest_dir: str,
    ) -> dict:
        plan: List[_PlannedOp] = []
        seen: set[str] = set()
        for local_path in local_paths:
            if worker.cancelled:
                return {}
            absolute_path = os.path.abspath(local_path)
            if absolute_path in seen:
                continue
            seen.add(absolute_path)
            name = os.path.basename(absolute_path.rstrip(os.sep))
            remote_base = dest_dir.rstrip("/") + "/" + name
            try:
                base_exists = bool(files.exists(remote_base))
            except Exception:
                base_exists = False
            if base_exists:
                return {
                    "conflict": True,
                    "paths": local_paths,
                    "directory": dest_dir,
                }
            if not os.path.isdir(absolute_path):
                plan.append(
                    _PlannedOp("upload", absolute_path, remote_base)
                )
                continue
            plan.append(_PlannedOp("mkdir_remote", "", remote_base))
            for root, dirs, filenames in os.walk(absolute_path):
                if worker.cancelled:
                    return {}
                rel_root = os.path.relpath(root, absolute_path)
                rel_root = "" if rel_root == "." else rel_root
                remote_root = remote_base + (
                    "/" + rel_root.replace(os.sep, "/")
                    if rel_root
                    else ""
                )
                for dirname in dirs:
                    plan.append(
                        _PlannedOp(
                            "mkdir_remote",
                            "",
                            remote_root + "/" + dirname,
                        )
                    )
                for filename in filenames:
                    local_file = os.path.join(root, filename)
                    remote_file = remote_root + "/" + filename
                    try:
                        file_exists = bool(files.exists(remote_file))
                    except Exception:
                        file_exists = False
                    if file_exists:
                        return {
                            "conflict": True,
                            "paths": local_paths,
                            "directory": dest_dir,
                        }
                    plan.append(_PlannedOp("upload", local_file, remote_file))
        return {
            "plan": plan,
            "title": "Yükleniyor...",
            "affected_dirs": [self._normalize_remote_dir(dest_dir)],
            "confirm_before_start": True,
        }

    def _apply_local_upload_incremental_gui(self, local_paths: List[str], dest_dir: str) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        dest_dir = (dest_dir or "/").strip()
        if not dest_dir.startswith("/"):
            dest_dir = "/" + dest_dir
        dest_dir = dest_dir.rstrip("/") or "/"

        job_id = self._next_local_upload_plan_id
        self._next_local_upload_plan_id += 1
        self._local_upload_plan_jobs[job_id] = _LocalUploadPlanJob(
            steps=self._iter_local_upload_plan(local_paths, dest_dir),
            dest_dir=dest_dir,
        )
        QTimer.singleShot(0, lambda current_job_id=job_id: self._advance_local_upload_plan(current_job_id))
        return True

    def _advance_local_upload_plan(self, job_id: int) -> None:
        job = self._local_upload_plan_jobs.get(job_id)
        if job is None:
            return
        try:
            # One traversal/probe step per callback prevents slow remote exists
            # calls or large local trees from monopolizing the GUI event loop.
            next(job.steps)
        except StopIteration as finished:
            self._local_upload_plan_jobs.pop(job_id, None)
            plan = finished.value
            if not plan:
                return
            self._run_plan_with_progress(
                plan,
                "Yükleniyor...",
                after_finished=lambda dest=job.dest_dir: self._finish_remote_directory_mutation([dest]),
                confirm_before_start=True,
            )
            return
        QTimer.singleShot(0, lambda current_job_id=job_id: self._advance_local_upload_plan(current_job_id))

    def _iter_local_upload_plan(
        self,
        local_paths: List[str],
        dest_dir: str,
    ) -> Generator[None, None, Optional[List[_PlannedOp]]]:
        if not self.session or not self.session.get("files"):
            return None
        files = self.session["files"]
        plan: List[_PlannedOp] = []
        policy: Optional[str] = None

        seen_sources: set[str] = set()
        for lp in local_paths:
            if not lp:
                yield
                continue
            lp = os.path.abspath(lp)
            if lp in seen_sources:
                yield
                continue
            seen_sources.add(lp)
            name = os.path.basename(lp.rstrip(os.sep))
            rp_base = dest_dir.rstrip("/") + "/" + name
            is_dir = os.path.isdir(lp)

            while True:
                try:
                    exists = bool(files.exists(rp_base))
                except Exception:
                    exists = False
                yield

                if exists and is_dir:
                    try:
                        target_is_dir = bool(files.is_dir(rp_base))
                    except Exception:
                        target_is_dir = False
                    if target_is_dir:
                        # Keep the target directory and resolve only nested
                        # file conflicts while building the upload plan.
                        break

                if exists:
                    if policy is None:
                        action = self._resolve_conflict(
                            rp_base,
                            src=lp,
                            source_is_local=True,
                            target_is_local=False,
                        )
                        if action.endswith("_all"):
                            policy = action.replace("_all", "")
                        action_simple = action.replace("_all", "")
                    else:
                        action_simple = policy

                    if action_simple == "cancel":
                        return None
                    if action_simple == "skip":
                        rp_base = None
                        break
                    if action_simple == "rename":
                        new_dst = self._prompt_rename(dest_dir, name)
                        if not new_dst:
                            rp_base = None
                            break
                        rp_base = new_dst
                        yield
                        continue
                    if action_simple == "overwrite":
                        try:
                            isdir_remote = bool(files.is_dir(rp_base))
                        except Exception:
                            isdir_remote = False
                        plan.append(_PlannedOp(op="delete", src="", dst=rp_base, recursive=isdir_remote))
                    elif action_simple == "resume":
                        pass
                break

            if not rp_base:
                yield
                continue

            if not is_dir:
                plan.append(_PlannedOp(op="upload", src=lp, dst=rp_base))
                yield
                continue

            plan.append(_PlannedOp(op="mkdir_remote", src="", dst=rp_base))
            yield
            for root, dirs, files_ls in os.walk(lp):
                yield
                rel_root = os.path.relpath(root, lp)
                rel_root = "" if rel_root == "." else rel_root
                for d in dirs:
                    rdir = rp_base + ("/" + rel_root if rel_root else "") + "/" + d
                    plan.append(_PlannedOp(op="mkdir_remote", src="", dst=rdir))
                    yield
                for fn in files_ls:
                    lfile = os.path.join(root, fn)
                    rfile = rp_base + ("/" + rel_root if rel_root else "") + "/" + fn
                    while True:
                        try:
                            exists = bool(files.exists(rfile))
                        except Exception:
                            exists = False
                        yield
                        if not exists:
                            break

                        if policy is None:
                            action = self._resolve_conflict(
                                rfile,
                                src=lfile,
                                source_is_local=True,
                                target_is_local=False,
                            )
                            if action.endswith("_all"):
                                policy = action.replace("_all", "")
                            action_simple = action.replace("_all", "")
                        else:
                            action_simple = policy

                        if action_simple == "cancel":
                            return None
                        if action_simple == "skip":
                            rfile = None
                            break
                        if action_simple == "rename":
                            new_dst = self._prompt_rename(
                                rfile.rsplit("/", 1)[0],
                                fn,
                            )
                            if not new_dst:
                                rfile = None
                                break
                            rfile = new_dst
                            yield
                            continue
                        if action_simple == "overwrite":
                            try:
                                isdir_remote = bool(files.is_dir(rfile))
                            except Exception:
                                isdir_remote = False
                            plan.append(_PlannedOp(op="delete", src="", dst=rfile, recursive=isdir_remote))
                            break
                        if action_simple == "resume":
                            break
                        break
                    if not rfile:
                        yield
                        continue
                    plan.append(_PlannedOp(op="upload", src=lfile, dst=rfile))
                    yield

        return plan

    def _template_upload_path(self) -> Path:
        return Path(__file__).resolve().parents[4] / "templates" / "extract_iso.py"

    def show_template_upload_menu(self) -> None:
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        if not self.current_dir:
            QMessageBox.warning(self, t("common.error"), t("dirs.no_directory_selected"))
            return

        menu = QMenu(self)
        act_extract_iso = menu.addAction(
            t("dirs.template_extract_iso") if t("dirs.template_extract_iso") != "[dirs.template_extract_iso]" else "extract_iso.py"
        )
        chosen = menu.exec(self.btn_template_upload.mapToGlobal(self.btn_template_upload.rect().bottomLeft()))
        if chosen != act_extract_iso:
            return
        self.upload_template_file(self._template_upload_path())

    def upload_template_file(self, template_path: Path) -> bool:
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return False
        if not self.current_dir:
            QMessageBox.warning(self, t("common.error"), t("dirs.no_directory_selected"))
            return False
        if not template_path.exists():
            QMessageBox.warning(
                self,
                t("common.error"),
                t("dirs.template_missing").format(path=str(template_path))
                if t("dirs.template_missing") != "[dirs.template_missing]"
                else f"Template file not found: {template_path}",
            )
            return False
        return self._apply_local_upload_incremental(
            [str(template_path)],
            self.current_dir,
        )

    # ---------- upload / download ----------
    def upload_files(self):
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        if not self.current_dir:
            QMessageBox.warning(self, t("common.error"), t("dirs.no_directory_selected"))
            return
        paths, _ = QFileDialog.getOpenFileNames(self, t("dirs.upload") if t("dirs.upload") != "[dirs.upload]" else "Yükle")
        if not paths:
            return
        self._apply_local_upload_incremental(paths, self.current_dir)

    def download_selected(self):
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        tab = self.tabs.currentWidget()
        tab_key = "all"
        for k, v in self.views.items():
            if v is tab:
                tab_key = k
                break
        sel = self.selected_paths(tab_key)
        if not sel:
            QMessageBox.information(self, t("common.info"), t("dirs.no_file_selected"))
            return
        target_dir = QFileDialog.getExistingDirectory(
            self, t("dirs.download_selected") if t("dirs.download_selected") != "[dirs.download_selected]" else "Seçilenleri İndir"
        )
        if not target_dir:
            return
        self._apply_remote_download_incremental(sel, target_dir)

    # ---------- drag/drop apply ----------
    def _apply_drag_drop(self, src_paths: List[str], dest_dir: str, *, is_copy: bool, src_panel_id: str) -> bool:
        if not self.session or not self.session.get("files"):
            return False

        dest_dir = (dest_dir or "/").strip()
        if not dest_dir.startswith("/"):
            dest_dir = "/" + dest_dir
        dest_dir = dest_dir.rstrip("/") or "/"

        try:
            op = "copy" if is_copy else "move"
            return self._apply_copy_move_with_conflicts(op, src_paths, dest_dir)
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=str(e), exc=e, area="FILES")
            return False
