"""Local directory panel facade built from cohesive file-management leaves.

LocalDirPanel retains the Qt signals, tab state, listing, refresh, selection,
and navigation API. Local context-menu actions are composed from
LocalContextMenuMixin.

- _local_tree owns the local tree control and comparison-column rendering.
- _local_fs_ops owns clipboard, navigation, create/delete/rename, and open flows.
- _local_lint_tools owns lint discovery, plugin menus, and ANSYS lint runs.
- _local_context_menu owns local file action menus.

The facade and leaves depend on service contracts, not remote panels, FTP, or
controllers.
"""

from __future__ import annotations

from hpc_gui.core._legacy_patch_targets import enable_legacy_patch_targets as _enable_legacy_patch_targets

import datetime
import logging
import os
import subprocess  # noqa: F401 — legacy patch target
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDesktopServices as QDesktopServices  # noqa: F401 — legacy patch target
from PySide6.QtWidgets import (
    QFileDialog as QFileDialog,  # noqa: F401 — legacy patch target
    QInputDialog as QInputDialog,  # noqa: F401 — legacy patch target
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu as QMenu,  # noqa: F401 — legacy patch target
    QMessageBox,
    QPushButton,
    QStyle,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hpc_gui.config.storage import (
    get_file_association as get_file_association,  # noqa: F401 — legacy patch target
    set_file_association as set_file_association,  # noqa: F401 — legacy patch target
)
from hpc_gui.core.i18n import t
from hpc_gui.services.directory_comparison import CompareStatus, ComparableEntry
from hpc_gui.services.local_files import list_local_entries, safe_initial_local_directory
from hpc_gui.ui.widgets._fm_dnd_contract import (
    MIME_REMOTE_PATHS as MIME_REMOTE_PATHS,  # noqa: F401 — legacy re-export
    _DragPayload as _DragPayload,  # noqa: F401 — legacy re-export
    _decode_payload as _decode_payload,  # noqa: F401 — legacy re-export
    _encode_payload as _encode_payload,  # noqa: F401 — legacy re-export
)
from hpc_gui.ui.widgets._local_context_menu import (
    LOCAL_CONTEXT_MENU_LABELS as LOCAL_CONTEXT_MENU_LABELS,  # noqa: F401 — legacy re-export
    LocalContextMenuMixin,
)
from hpc_gui.ui.widgets._local_fs_ops import LocalFsOpsMixin
from hpc_gui.ui.widgets._local_lint_tools import LocalLintToolsMixin
from hpc_gui.ui.widgets._local_tree import (
    _LocalTree as _LocalTree,  # noqa: F401 — legacy re-export
    _SORT_MTIME_ROLE as _SORT_MTIME_ROLE,  # noqa: F401 — legacy re-export
    _SORT_NAME_ROLE as _SORT_NAME_ROLE,  # noqa: F401 — legacy re-export
    _SORT_SIZE_ROLE as _SORT_SIZE_ROLE,  # noqa: F401 — legacy re-export
    _SORT_TYPE_ROLE as _SORT_TYPE_ROLE,  # noqa: F401 — legacy re-export
    _format_size as _format_size,  # noqa: F401 — legacy re-export
    _natural_sort_key as _natural_sort_key,  # noqa: F401 — legacy re-export
    LocalComparisonMixin,
)


logger = logging.getLogger(__name__)


class LocalDirPanel(
    LocalComparisonMixin, LocalFsOpsMixin, LocalLintToolsMixin, LocalContextMenuMixin, QWidget
):
    remotePathsDropped = Signal(list, str)
    directoryChanged = Signal(str)
    directoryLoaded = Signal(str)
    selectionChanged = Signal()
    fileActivated = Signal(str)
    uploadRequested = Signal(list)
    remoteClipboardPasteRequested = Signal(list, str)
    editRequested = Signal(str, bool)  # path, new_window

    def __init__(self, initial_directory: str = "", parent=None) -> None:
        super().__init__(parent)
        self.current_dir = safe_initial_local_directory(initial_directory)
        self._history: list[str] = []
        self._tab_dirs: dict[_LocalTree, str] = {}
        self._local_clipboard: tuple[str, list[str]] | None = None
        self._current_entries_snapshot: list[ComparableEntry] = []
        self._snapshot_dir: str = ""
        self._comparison_statuses: dict[str, CompareStatus] | None = None

        self.title_label = QLabel(t("ftp.local_title"))
        self.path = QLineEdit(self.current_dir)
        self.path.returnPressed.connect(self._open_path_field)
        self.btn_drives = QPushButton(t("ftp.drives"))
        self.btn_back = QPushButton(t("ftp.back"))
        self.btn_parent = QPushButton(t("ftp.parent"))
        self.btn_refresh = QPushButton(t("ftp.refresh"))
        self.btn_drives.clicked.connect(self.show_drives)
        self.btn_back.clicked.connect(self.go_back)
        self.btn_parent.clicked.connect(self.go_parent)
        self.btn_refresh.clicked.connect(self.refresh)

        controls = QHBoxLayout()
        controls.addWidget(self.btn_drives)
        controls.addWidget(self.btn_back)
        controls.addWidget(self.btn_parent)
        controls.addWidget(self.btn_refresh)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tree = self._make_tree()
        self._tab_dirs[self.tree] = self.current_dir
        self.tabs.addTab(self.tree, self._tab_label(self.current_dir))
        self.tabs.currentChanged.connect(self._on_tab_changed)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addLayout(controls)
        layout.addWidget(self.path)
        layout.addWidget(self.tabs)
        self.retranslate_ui()
        self.refresh()

    def _make_tree(self) -> _LocalTree:
        tree = _LocalTree(self)
        tree.setColumnCount(5)
        tree.setHeaderLabels([
            t("dirs.col_name"),
            t("dirs.col_size"),
            t("dirs.col_type"),
            t("dirs.col_mtime"),
            t("ftp.comparison_column"),
        ])
        tree.hideColumn(4)
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.itemDoubleClicked.connect(self._open_item)
        tree.itemSelectionChanged.connect(self.selectionChanged)
        tree.remotePathsDropped.connect(self.remotePathsDropped)
        tree.customContextMenuRequested.connect(self._on_context_menu)
        return tree

    @staticmethod
    def _tab_label(directory: str) -> str:
        name = Path(directory).name
        return name or directory or "Local"

    def _on_tab_changed(self, index: int) -> None:
        widget = self.tabs.widget(index)
        if isinstance(widget, _LocalTree):
            self.tree = widget
            self.current_dir = self._tab_dirs.get(widget, self.current_dir)
            self.path.setText(self.current_dir)
            self.refresh()

    def _close_tab(self, index: int) -> None:
        """Keep the original local-directory tab available at all times."""
        if self.tabs.count() <= 1 or index < 0:
            return
        tree = self.tabs.widget(index)
        self.tabs.removeTab(index)
        if isinstance(tree, _LocalTree):
            self._tab_dirs.pop(tree, None)
        tree.deleteLater()

    def open_directory_in_new_tab(self, directory: str) -> bool:
        target = os.path.abspath(os.path.expanduser(directory or ""))
        if not os.path.isdir(target):
            return False
        tree = self._make_tree()
        self._tab_dirs[tree] = target
        index = self.tabs.addTab(tree, self._tab_label(target))
        self.tabs.setCurrentIndex(index)
        return True

    def retranslate_ui(self) -> None:
        self.title_label.setText(t("ftp.local_title"))
        self.btn_drives.setText(t("ftp.drives"))
        self.btn_back.setText(t("ftp.back"))
        self.btn_parent.setText(t("ftp.parent"))
        self.btn_refresh.setText(t("ftp.refresh"))
        comparison_header = (
            t("ftp.comparison_column")
        )
        self.tree.setHeaderLabels(
            [
                t("dirs.col_name"),
                t("dirs.col_size"),
                t("dirs.col_type"),
                t("dirs.col_mtime"),
                comparison_header,
            ]
        )
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            if isinstance(widget, _LocalTree):
                widget.setHeaderLabels(
                    [
                        t("dirs.col_name"),
                        t("dirs.col_size"),
                        t("dirs.col_type"),
                        t("dirs.col_mtime"),
                        comparison_header,
                    ]
                )
                self.tabs.setTabText(index, self._tab_label(self._tab_dirs.get(widget, "")))

    def _open_path_field(self) -> None:
        self.set_dir(self.path.text())

    def _open_item(self, item: QTreeWidgetItem, _column: int) -> None:
        if bool(item.data(0, Qt.ItemDataRole.UserRole + 1)):
            self.set_dir(str(item.data(0, Qt.ItemDataRole.UserRole)))
            return
        path = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        if path:
            self.fileActivated.emit(path)

    def _add_entry(
        self,
        name: str,
        path: str,
        is_dir: bool,
        size: int,
        mtime: int,
        *,
        is_parent: bool = False,
    ) -> None:
        item = QTreeWidgetItem()
        item.setText(0, name)
        item.setIcon(
            0,
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_DirIcon
                if is_dir
                else QStyle.StandardPixmap.SP_FileIcon
            ),
        )
        item.setText(1, "" if is_dir else _format_size(size))
        file_type = t("dirs.type_folder") if is_dir else (Path(name).suffix[1:].upper() or t("ftp.file"))
        item.setText(2, file_type)
        item.setText(
            3,
            datetime.datetime.fromtimestamp(mtime).strftime("%d-%m-%y %H:%M")
            if mtime
            else "",
        )
        item.setData(0, Qt.ItemDataRole.UserRole, path)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, is_dir)
        item.setData(0, Qt.ItemDataRole.UserRole + 2, is_parent)
        item.setData(0, _SORT_NAME_ROLE, name)
        item.setData(0, _SORT_SIZE_ROLE, int(size or 0))
        item.setData(0, _SORT_TYPE_ROLE, file_type)
        item.setData(0, _SORT_MTIME_ROLE, int(mtime or 0))
        self.tree.addTopLevelItem(item)

    def set_dir(self, directory: str, *, remember: bool = True) -> bool:
        target = os.path.abspath(os.path.expanduser(directory or ""))
        if not os.path.isdir(target):
            QMessageBox.warning(self, t("common.error"), t("ftp.invalid_local_path").format(path=target))
            self.path.setText(self.current_dir)
            return False
        if remember and self.current_dir and target != self.current_dir:
            self._history.append(self.current_dir)
        self.current_dir = target
        self._tab_dirs[self.tree] = target
        self.tabs.setTabText(self.tabs.currentIndex(), self._tab_label(target))
        self.path.setText(target)
        self.refresh()
        self.directoryChanged.emit(target)
        return True

    def current_entries_snapshot(self) -> tuple[str, list[ComparableEntry]]:
        """Return the committed (directory, entries) metadata snapshot.

        The snapshot is only valid while it belongs to ``current_dir``;
        a failed refresh never masquerades as a successful one.
        """
        if self._snapshot_dir != self.current_dir:
            return "", []
        return self._snapshot_dir, list(self._current_entries_snapshot)

    def refresh(self) -> None:
        self.tree.clear()
        try:
            entries = list_local_entries(self.current_dir)
        except (OSError, PermissionError) as exc:
            QMessageBox.warning(self, t("common.error"), t("ftp.local_read_failed").format(error=exc))
            return
        self._current_entries_snapshot = [
            ComparableEntry(
                name=entry.name,
                is_dir=bool(entry.is_dir),
                size=int(entry.size or 0),
                mtime=int(entry.mtime or 0),
            )
            for entry in entries
        ]
        self._snapshot_dir = self.current_dir
        self.path.setText(self.current_dir)
        parent = str(Path(self.current_dir).parent)
        if parent and parent != self.current_dir:
            self._add_entry("..", parent, True, 0, 0, is_parent=True)
        for entry in entries:
            self._add_entry(entry.name, entry.path, entry.is_dir, entry.size, entry.mtime)
        self.tree.apply_sort()
        if self._comparison_statuses:
            self._render_comparison_statuses()
        self.directoryLoaded.emit(self.current_dir)



__all__ = [
    "LOCAL_CONTEXT_MENU_LABELS",
    "MIME_REMOTE_PATHS",
    "_DragPayload",
    "_decode_payload",
    "_encode_payload",
    "_LocalTree",
    "_SORT_NAME_ROLE",
    "_SORT_SIZE_ROLE",
    "_SORT_TYPE_ROLE",
    "_SORT_MTIME_ROLE",
    "_format_size",
    "_natural_sort_key",
    "LocalDirPanel",
]


_enable_legacy_patch_targets(
    __name__,
    {
        "os": (("hpc_gui.ui.widgets._local_fs_ops", "os"),),
        "subprocess": (("hpc_gui.ui.widgets._local_fs_ops", "subprocess"),),
        "get_file_association": (("hpc_gui.ui.widgets._local_fs_ops", "get_file_association"),),
        "set_file_association": (("hpc_gui.ui.widgets._local_fs_ops", "set_file_association"),),
        "QDesktopServices": (("hpc_gui.ui.widgets._local_fs_ops", "QDesktopServices"),),
        "QFileDialog": (("hpc_gui.ui.widgets._local_fs_ops", "QFileDialog"),),
        "QInputDialog": (("hpc_gui.ui.widgets._local_fs_ops", "QInputDialog"),),
        "QMessageBox": (
            ("hpc_gui.ui.widgets._local_fs_ops", "QMessageBox"),
            ("hpc_gui.ui.widgets._local_lint_tools", "QMessageBox"),
        ),
        "QMenu": (("hpc_gui.ui.widgets._local_context_menu", "QMenu"),),
    },
)
