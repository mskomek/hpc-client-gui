from __future__ import annotations

import datetime
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QPoint, QMimeData, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QDrag
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QMenu,
    QPushButton,
    QStyle,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hpc_gui.core.i18n import t
from hpc_gui.config.storage import (
    get_file_association,
    set_file_association,
)
from hpc_gui.services.directory_comparison import CompareStatus, ComparableEntry
from hpc_gui.services.local_files import (
    list_local_entries,
    list_windows_drives,
    safe_initial_local_directory,
)
from hpc_gui.services.file_clipboard import get_file_clipboard
from hpc_gui.ui.widgets.remote_dir_panel import MIME_REMOTE_PATHS

LOCAL_CONTEXT_MENU_LABELS = [
    "Upload",
    "Add files to queue",
    "---",
    "Open",
    "Open with...",
    "Open in new tab",
    "Edit",
    "---",
    "Create directory",
    "Create directory and enter it",
    "Refresh",
    "---",
    "Delete",
    "Rename",
]

_SORT_NAME_ROLE = Qt.ItemDataRole.UserRole + 10
_SORT_SIZE_ROLE = Qt.ItemDataRole.UserRole + 11
_SORT_TYPE_ROLE = Qt.ItemDataRole.UserRole + 12
_SORT_MTIME_ROLE = Qt.ItemDataRole.UserRole + 13


def _format_size(value: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    size = float(value)
    unit = 0
    while size >= 1024 and unit < len(units) - 1:
        size /= 1024
        unit += 1
    return f"{int(size)} {units[unit]}" if unit == 0 else f"{size:.1f} {units[unit]}"


def _natural_sort_key(value: str) -> tuple:
    return tuple(
        (1, int(part)) if part.isdigit() else (0, part.casefold())
        for part in re.split(r"(\d+)", value or "")
        if part
    )


class _LocalTree(QTreeWidget):
    remotePathsDropped = Signal(list, str)

    def __init__(self, panel: "LocalDirPanel") -> None:
        super().__init__(panel)
        self._panel = panel
        self._sort_column: int | None = None
        self._sort_order = Qt.SortOrder.AscendingOrder
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
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
        if self._sort_column is None or self.topLevelItemCount() < 2:
            return
        items = [self.takeTopLevelItem(0) for _ in range(self.topLevelItemCount())]
        parent_items = [
            item for item in items if bool(item.data(0, Qt.ItemDataRole.UserRole + 2))
        ]
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
        reverse = self._sort_order == Qt.SortOrder.DescendingOrder

        def key(item: QTreeWidgetItem):
            role = (
                _SORT_NAME_ROLE,
                _SORT_SIZE_ROLE,
                _SORT_TYPE_ROLE,
                _SORT_MTIME_ROLE,
            )[self._sort_column or 0]
            value = item.data(0, role)
            if self._sort_column == 0:
                return _natural_sort_key(str(value or ""))
            if self._sort_column == 2:
                return str(value or "").casefold()
            return int(value or 0)

        self.addTopLevelItems(
            parent_items
            + sorted(folders, key=key, reverse=reverse)
            + sorted(files, key=key, reverse=reverse)
        )

    def startDrag(self, supported_actions) -> None:  # type: ignore[override]
        paths = self._panel.selected_paths()
        if not paths:
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path) for path in paths])
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasFormat(MIME_REMOTE_PATHS):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasFormat(MIME_REMOTE_PATHS):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        mime = event.mimeData()
        if not mime.hasFormat(MIME_REMOTE_PATHS):
            super().dropEvent(event)
            return
        try:
            payload = json.loads(bytes(mime.data(MIME_REMOTE_PATHS)).decode("utf-8"))
            paths = [str(path) for path in payload.get("paths", []) if path]
            source = str(payload.get("src_panel_id", ""))
        except Exception:
            paths, source = [], ""
        if paths and source:
            event.acceptProposedAction()
            QTimer.singleShot(
                0,
                lambda dropped_paths=list(paths), source_panel=source: (
                    self.remotePathsDropped.emit(dropped_paths, source_panel)
                ),
            )
        else:
            event.ignore()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_F5 and not event.modifiers():
            self._panel.refresh()
            event.accept()
            return
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_C:
                if self._panel.copy_selected():
                    event.accept()
                    return
            if event.key() == Qt.Key.Key_X:
                if self._panel.cut_selected():
                    event.accept()
                    return
            if event.key() == Qt.Key.Key_V:
                if self._panel.paste_into_current_dir():
                    event.accept()
                    return
        if event.key() == Qt.Key.Key_F2 and not event.modifiers():
            if self._panel.rename_selected():
                event.accept()
                return
        if event.key() == Qt.Key.Key_Delete and not event.modifiers():
            if self._panel.delete_selected():
                event.accept()
                return
        super().keyPressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.MiddleButton:
            item = self.itemAt(event.position().toPoint())
            if item is not None:
                path = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
                is_dir = bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
                is_parent = bool(item.data(0, Qt.ItemDataRole.UserRole + 2))
                if path and is_dir and not is_parent:
                    self._panel.open_directory_in_new_tab(path)
            event.accept()
            return
        super().mouseReleaseEvent(event)


logger = logging.getLogger(__name__)


class LocalDirPanel(QWidget):
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
            t("ftp.comparison_column") if t("ftp.comparison_column") != "[ftp.comparison_column]" else "Comparison",
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
            if t("ftp.comparison_column") != "[ftp.comparison_column]"
            else "Comparison"
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

    def _selected_items(self) -> list[QTreeWidgetItem]:
        return [
            item
            for item in self.tree.selectedItems()
            if item.data(0, Qt.ItemDataRole.UserRole)
            and not bool(item.data(0, Qt.ItemDataRole.UserRole + 2))
        ]

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

    def show_drives(self) -> None:
        self.tree.clear()
        self.path.setText(t("ftp.drives"))
        for entry in list_windows_drives():
            self._add_entry(entry.name, entry.path, True, 0, 0)
        self.tree.apply_sort()

    def go_back(self) -> None:
        if self._history:
            self.set_dir(self._history.pop(), remember=False)

    def go_parent(self) -> None:
        parent = str(Path(self.current_dir).parent)
        if parent != self.current_dir:
            self.set_dir(parent)

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

    # ---- comparison column ----------------------------------------------
    def set_comparison_visible(self, visible: bool) -> None:
        for tree in list(self._tab_dirs):
            try:
                tree.showColumn(4) if visible else tree.hideColumn(4)
            except RuntimeError:
                continue
        if not visible:
            self.clear_comparison_statuses()

    def clear_comparison_statuses(self) -> None:
        self._comparison_statuses = None
        for tree in list(self._tab_dirs):
            try:
                for index in range(tree.topLevelItemCount()):
                    tree.topLevelItem(index).setText(4, "")
                    tree.topLevelItem(index).setToolTip(4, "")
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
        try:
            items = [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]
        except RuntimeError:
            return
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

    def selected_paths(self) -> list[str]:
        return [
            str(item.data(0, Qt.ItemDataRole.UserRole))
            for item in self._selected_items()
        ]

    def _set_system_file_clipboard(self, paths: list[str]) -> None:
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path) for path in paths])
        QApplication.clipboard().setMimeData(mime)

    def copy_selected(self) -> bool:
        paths = self.selected_paths()
        if not paths:
            return False
        self._local_clipboard = ("copy", paths)
        self._set_system_file_clipboard(paths)
        return True

    def cut_selected(self) -> bool:
        paths = self.selected_paths()
        if not paths:
            return False
        self._local_clipboard = ("move", paths)
        self._set_system_file_clipboard(paths)
        return True

    @staticmethod
    def _unique_destination(target: Path) -> Path:
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix
        parent = target.parent
        for index in range(1, 1000):
            candidate = parent / f"{stem} ({index}){suffix}"
            if not candidate.exists():
                return candidate
        return parent / f"{stem} copy{suffix}"

    def paste_into_current_dir(self) -> bool:
        remote_clip = get_file_clipboard().get()
        if remote_clip and remote_clip.paths:
            self.remoteClipboardPasteRequested.emit(
                list(remote_clip.paths),
                self.current_dir,
            )
            return True

        if not self._local_clipboard:
            return False
        op, paths = self._local_clipboard
        target_dir = Path(self.current_dir)
        if not target_dir.is_dir():
            return False

        changed = False
        for source_text in paths:
            source = Path(source_text)
            if not source.exists():
                continue
            if source.parent == target_dir and op == "move":
                continue
            destination = self._unique_destination(target_dir / source.name)
            try:
                if op == "move":
                    shutil.move(str(source), str(destination))
                elif source.is_dir():
                    shutil.copytree(source, destination)
                else:
                    shutil.copy2(source, destination)
            except OSError as exc:
                QMessageBox.warning(self, t("common.error"), str(exc))
                return changed
            changed = True
        if changed:
            if op == "move":
                self._local_clipboard = None
            self.refresh()
        return changed

    def open_selected_in_file_explorer(self) -> bool:
        selected = self._selected_items()
        if len(selected) == 1:
            path = Path(str(selected[0].data(0, Qt.ItemDataRole.UserRole)))
            target = path if path.is_dir() else path.parent
        else:
            target = Path(self.current_dir)
        if not target.exists():
            return False
        if os.name == "nt":
            subprocess.Popen(["explorer", str(target)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        return True

    def create_directory(self, *, enter: bool = False) -> bool:
        name, ok = QInputDialog.getText(
            self,
            t("dirs.new_folder") if t("dirs.new_folder") != "[dirs.new_folder]" else "Yeni Klasör",
            t("dirs.new_folder_label") if t("dirs.new_folder_label") != "[dirs.new_folder_label]" else "Klasör adı:",
        )
        if not ok or not name.strip():
            return False
        target = Path(self.current_dir, name.strip())
        try:
            target.mkdir()
        except OSError as exc:
            QMessageBox.warning(self, t("common.error"), str(exc))
            return False
        if enter:
            return self.set_dir(str(target))
        self.refresh()
        return True

    def delete_selected(self) -> bool:
        paths = [Path(path) for path in self.selected_paths()]
        if not paths:
            return False
        if QMessageBox.question(self, t("common.confirm"), t("dirs.delete_confirm")) != QMessageBox.StandardButton.Yes:
            return False
        for path in paths:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            except OSError as exc:
                QMessageBox.warning(self, t("common.error"), str(exc))
                return False
        self.refresh()
        return True

    def _on_context_menu(self, pos: QPoint) -> None:
        item = self.tree.itemAt(pos)
        if item is not None and not item.isSelected():
            self.tree.clearSelection()
            item.setSelected(True)
        paths = self.selected_paths()
        one_selected = len(paths) == 1
        one_is_dir = one_selected and Path(paths[0]).is_dir()

        menu = QMenu(self)
        act_upload = menu.addAction(LOCAL_CONTEXT_MENU_LABELS[0])
        act_add_queue = menu.addAction(LOCAL_CONTEXT_MENU_LABELS[1])
        act_add_queue.setEnabled(False)
        menu.addSeparator()
        act_open = menu.addAction(LOCAL_CONTEXT_MENU_LABELS[3])
        act_open_with = menu.addAction(t("files.open_with"))
        act_open_new_tab = menu.addAction(LOCAL_CONTEXT_MENU_LABELS[5])
        act_edit = menu.addAction(
            t("dirs.edit") if t("dirs.edit") != "[dirs.edit]" else "Edit"
        )
        act_edit_new_window = menu.addAction(
            t("dirs.edit_new_window")
            if t("dirs.edit_new_window") != "[dirs.edit_new_window]"
            else "Edit in new window"
        )
        menu.addSeparator()
        act_create_dir = menu.addAction(LOCAL_CONTEXT_MENU_LABELS[8])
        act_create_dir_enter = menu.addAction(LOCAL_CONTEXT_MENU_LABELS[9])
        act_refresh = menu.addAction(LOCAL_CONTEXT_MENU_LABELS[10])
        menu.addSeparator()
        act_delete = menu.addAction(LOCAL_CONTEXT_MENU_LABELS[12])
        act_rename = menu.addAction(LOCAL_CONTEXT_MENU_LABELS[13])

        act_upload.setEnabled(bool(paths))
        act_open.setEnabled(not paths or one_selected)
        act_open_with.setEnabled(one_selected and not one_is_dir)
        act_open_new_tab.setEnabled(one_is_dir)
        act_edit.setEnabled(one_selected and not one_is_dir)
        act_edit_new_window.setEnabled(one_selected and not one_is_dir)
        act_create_dir_enter.setEnabled(bool(self.current_dir))
        act_delete.setEnabled(bool(paths))
        act_rename.setEnabled(one_selected)
        # Batch-aware lint: 1-10 files with a common tool, or a single folder
        # containing at least one supported file.
        lint_batch_ok = False
        folder_lint_path: str | None = None
        if paths:
            if one_selected and one_is_dir:
                try:
                    if self._folder_contains_supported_file(str(paths[0])):
                        lint_batch_ok = True
                        folder_lint_path = str(paths[0])
                except Exception:
                    lint_batch_ok = False
            else:
                all_files = all(not Path(str(p)).is_dir() for p in paths)
                if all_files and paths:
                    suffixes = [Path(str(p)).suffix.lower() for p in paths]
                    lint_batch_ok = self._local_lint_supports_suffixes(suffixes)
        plugin_menu = menu.addMenu(t("files.plugins")) if paths else None
        act_ansys_lint = (
            plugin_menu.addAction(t("files.ansys_lint"))
            if plugin_menu is not None
            else None
        )
        if act_ansys_lint is not None:
            act_ansys_lint.setEnabled(lint_batch_ok)
        if one_selected and one_is_dir and folder_lint_path:
            tools = self._tools_for_folder(folder_lint_path)
            if tools:
                send_menu = plugin_menu.addMenu(t("files.send_to_plugin")) if plugin_menu else None
                if send_menu is None:
                    tools = []
                for tool in tools:
                    action = send_menu.addAction(tool.title)
                    action.triggered.connect(
                        lambda _=False, tl=tool, p=folder_lint_path: self.open_in_tool(tl, p)
                    )
        elif len(paths) == 1 and not one_is_dir:
            self._build_send_to_plugin_menu(
                plugin_menu, str(paths[0]) if one_selected and not one_is_dir else None
            )
        elif lint_batch_ok:
            # Batch submenu: tools supporting every selected file.
            try:
                from hpc_gui.plugins.linter_tools import tools_supporting_all_suffixes

                suffixes = [Path(str(p)).suffix.lower() for p in paths]
                batch_tools = tools_supporting_all_suffixes(suffixes)
            except Exception:
                batch_tools = []
            if batch_tools:
                send_menu = plugin_menu.addMenu(t("files.send_to_plugin")) if plugin_menu else None
                if send_menu is None:
                    batch_tools = []
                for tool in batch_tools:
                    action = send_menu.addAction(tool.title)
                    action.triggered.connect(
                        lambda _=False, tl=tool, ps=list(paths): self.open_in_tool_batch(tl, ps)
                    )
        if one_selected and item is not None and bool(item.data(0, Qt.ItemDataRole.UserRole + 2)):
            act_upload.setEnabled(False)
            act_open.setEnabled(True)
            act_open_with.setEnabled(False)
            act_open_new_tab.setEnabled(False)
            act_delete.setEnabled(False)
            act_rename.setEnabled(False)

        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if not chosen:
            return
        if chosen == act_upload:
            self.uploadRequested.emit(paths)
            return
        if chosen == act_open:
            self.open_selected_in_file_explorer()
            return
        if chosen == act_open_with:
            self.open_selected_with_program()
            return
        if chosen == act_open_new_tab and one_is_dir:
            self.open_directory_in_new_tab(paths[0])
            return
        if chosen == act_edit:
            self._edit_selected(new_window=False)
            return
        if chosen == act_edit_new_window:
            self._edit_selected(new_window=True)
            return
        if chosen == act_create_dir:
            self.create_directory(enter=False)
            return
        if chosen == act_create_dir_enter:
            self.create_directory(enter=True)
            return
        if chosen == act_refresh:
            self.refresh()
            return
        if chosen == act_delete:
            self.delete_selected()
            return
        if chosen == act_rename:
            self.rename_selected()
            return
        if act_ansys_lint is not None and chosen == act_ansys_lint:
            if len(paths) == 1:
                self.run_ansys_lint(Path(str(paths[0])))
            else:
                self.run_ansys_lint_batch([Path(str(p)) for p in paths])
            return

    def _folder_contains_supported_file(self, folder: str) -> bool:
        try:
            supported = self._local_lint_suffixes()
            if not supported:
                return False
            count = 0
            for p in Path(folder).rglob("*"):
                if p.is_file() and p.suffix.lower() in supported:
                    return True
                count += 1
                if count > 200:
                    break
        except Exception:
            return False
        return False

    @staticmethod
    def _local_lint_suffixes() -> set[str]:
        """Return suffixes supported by installed declarative or v2 linters."""
        suffixes: set[str] = set()
        try:
            from hpc_gui.plugins.linter_tools import list_linter_tools, tool_supported_suffixes

            for tool in list_linter_tools():
                suffixes.update(tool_supported_suffixes(tool))
        except Exception:
            pass
        try:
            from hpc_gui.lint.rulepack import load_lint_packs

            for pack in load_lint_packs():
                for pattern in pack.file_patterns:
                    suffix = Path(pattern).suffix.lower()
                    if suffix and not any(char in suffix for char in "*?["):
                        suffixes.add(suffix)
        except Exception:
            pass
        return suffixes

    @classmethod
    def _local_lint_supports_suffixes(cls, suffixes: list[str]) -> bool:
        supported = cls._local_lint_suffixes()
        return bool(suffixes) and all(suffix.lower() in supported for suffix in suffixes)

    def _tools_for_folder(self, folder: str) -> list:
        from hpc_gui.plugins.linter_tools import list_linter_tools, tool_supported_suffixes

        try:
            supported = set()
            for p in Path(folder).rglob("*"):
                if p.is_file():
                    sfx = p.suffix.lower()
                    if sfx:
                        supported.add(sfx)
                    if len(supported) > 20:
                        break
            if not supported:
                return []
            tools = []
            for tool in list_linter_tools():
                declared = tool_supported_suffixes(tool)
                if declared & supported:
                    tools.append(tool)
            return tools
        except Exception:
            logger.warning("Tool lookup failed for folder %s", folder, exc_info=True)
            return []

    @staticmethod
    def _ansys_lint_supported(suffix: str) -> bool:
        from hpc_gui.plugins.linter_tools import supported_suffixes

        return suffix in supported_suffixes()

    def _edit_selected(self, new_window: bool) -> None:
        selected = self._selected_items()
        if len(selected) != 1:
            return
        path = str(selected[0].data(0, Qt.ItemDataRole.UserRole))
        if not path or Path(path).is_dir():
            return
        self.editRequested.emit(path, new_window)

    def _build_send_to_plugin_menu(self, plugin_menu, path_str: str | None):
        """Attach a "send to plugin" submenu when a tool supports the file."""
        if not path_str:
            return None
        from hpc_gui.plugins.linter_tools import tools_supporting_suffix

        try:
            tools = tools_supporting_suffix(Path(path_str).suffix.lower())
        except Exception:  # defensive: menu building never breaks the panel
            logger.warning("Tool lookup failed for %s", path_str, exc_info=True)
            return None
        if not tools:
            return None
        if plugin_menu is None:
            return None
        send_menu = plugin_menu.addMenu(t("files.send_to_plugin"))
        for tool in tools:
            action = send_menu.addAction(tool.title)
            action.triggered.connect(
                lambda _=False, tl=tool, p=path_str: self.open_in_tool(tl, p)
            )
        return send_menu

    def open_in_tool(self, tool, path_str: str) -> None:
        """Open a linter-tool page pre-loaded with one local file."""
        from hpc_gui.ui.dialogs.linter_tool_host import host_tool_page

        host_tool_page(
            self,
            tool,
            initial_paths=[path_str],
            title=f"{tool.title} — {Path(path_str).name}",
        )

    def open_in_tool_batch(self, tool, paths: list[str]) -> None:
        """Open a linter-tool page pre-loaded with multiple local files."""
        from hpc_gui.ui.dialogs.linter_tool_host import host_tool_page

        names = ", ".join(Path(str(p)).name for p in paths[:3])
        if len(paths) > 3:
            names += f" +{len(paths) - 3}"
        host_tool_page(
            self,
            tool,
            initial_paths=[str(p) for p in paths],
            title=f"{tool.title} — {names}",
        )

    def run_ansys_lint(self, path: Path) -> None:
        from hpc_gui.plugins.linter_tools import ToolLoadError, lint_paths_with_tool
        from hpc_gui.ui.dialogs.ansys_lint_results_dialog import (
            show_ansys_lint_results,
        )

        def open_in_tool() -> None:
            from hpc_gui.plugins.linter_tools import first_linter_tool

            try:
                self.open_in_tool(first_linter_tool(), str(path))
            except Exception as exc:  # already messaged by the host
                logger.warning("Fix redirect failed for %s", path, exc_info=exc)

        try:
            run = lint_paths_with_tool([path])
        except ToolLoadError as exc:
            diagnostics = self._run_local_rulepack_lint(path)
            if diagnostics is None:
                QMessageBox.warning(self, t("ansyslint.title"), str(exc))
            else:
                self._show_local_lint_results(path, diagnostics)
            return
        except Exception as exc:  # defensive: engine failures stay contained
            logger.warning("ANSYS lint failed for %s", path, exc_info=exc)
            QMessageBox.warning(
                self, t("ansyslint.title"), f"{type(exc).__name__}: {exc}"
            )
            return
        show_ansys_lint_results(
            self, f"{t('ansyslint.title')} — {path.name}", run, open_in_tool=open_in_tool
        )

    @staticmethod
    def _run_local_rulepack_lint(path: Path) -> list | None:
        from hpc_gui.lint.engine import lint_text
        from hpc_gui.lint.rulepack import load_lint_packs

        try:
            text = path.read_text(encoding="utf-8")
            packs = [pack for pack in load_lint_packs() if pack.matches(str(path))]
            if not packs:
                return None
            diagnostics = []
            for pack in packs:
                diagnostics.extend(lint_text(text, file_name=str(path), rule_pack=pack))
            return diagnostics
        except (OSError, UnicodeError):
            return None

    def _show_local_lint_results(self, path: Path, diagnostics: list) -> None:
        if not diagnostics:
            QMessageBox.information(
                self, t("ansyslint.title"), f"{path.name}: {t('editor.lint_ok')}"
            )
            return
        lines = []
        for diagnostic in diagnostics:
            location = f"{diagnostic.line}:{diagnostic.column or 1}" if diagnostic.line else "-"
            severity = getattr(diagnostic.severity, "value", diagnostic.severity)
            lines.append(f"[{location}] {severity}: {diagnostic.message} ({diagnostic.rule_id})")
        QMessageBox.warning(self, t("ansyslint.title"), "\n".join(lines))

    def run_ansys_lint_batch(self, paths: list[Path]) -> None:
        from hpc_gui.plugins.linter_tools import ToolLoadError, lint_paths_with_tool
        from hpc_gui.ui.dialogs.ansys_lint_results_dialog import (
            show_ansys_lint_results,
        )

        if not paths:
            return

        def open_in_tool() -> None:
            from hpc_gui.plugins.linter_tools import tools_supporting_all_suffixes

            try:
                suffixes = [p.suffix.lower() for p in paths]
                tools = tools_supporting_all_suffixes(suffixes)
                if not tools:
                    return
                self.open_in_tool_batch(tools[0], [str(p) for p in paths])
            except Exception as exc:
                logger.warning("Fix redirect failed for %s", paths, exc_info=exc)

        try:
            run = lint_paths_with_tool(paths)
        except ToolLoadError as exc:
            results = [(path, self._run_local_rulepack_lint(path)) for path in paths]
            if any(diagnostics is not None for _path, diagnostics in results):
                lines = []
                for path, diagnostics in results:
                    lines.append(f"{path.name}:")
                    if diagnostics:
                        lines.extend(
                            f"  [{d.line}:{d.column or 1}] {d.message} ({d.rule_id})"
                            for d in diagnostics
                        )
                    else:
                        lines.append(f"  {t('editor.lint_ok')}")
                QMessageBox.warning(self, t("ansyslint.title"), "\n".join(lines))
            else:
                QMessageBox.warning(self, t("ansyslint.title"), str(exc))
            return
        except Exception as exc:  # defensive: engine failures stay contained
            logger.warning("ANSYS lint failed for %s", paths, exc_info=exc)
            QMessageBox.warning(
                self, t("ansyslint.title"), f"{type(exc).__name__}: {exc}"
            )
            return
        names = ", ".join(p.name for p in paths[:3])
        if len(paths) > 3:
            names += f" +{len(paths) - 3}"
        show_ansys_lint_results(
            self, f"{t('ansyslint.title')} — {names}", run, open_in_tool=open_in_tool
        )

    def rename_selected(self) -> bool:
        selected = self._selected_items()
        if len(selected) != 1:
            return False
        old = Path(str(selected[0].data(0, Qt.ItemDataRole.UserRole)))
        new_name, ok = QInputDialog.getText(
            self,
            t("dirs.rename") if t("dirs.rename") != "[dirs.rename]" else "Yeniden Adlandır",
            t("dirs.rename_label"),
            text=old.name,
        )
        if not ok or not new_name.strip():
            return False
        target = old.with_name(new_name.strip())
        try:
            old.rename(target)
        except OSError as exc:
            QMessageBox.warning(self, t("common.error"), str(exc))
            return False
        self.refresh()
        return True

    def open_selected_with_program(self) -> bool:
        selected = self._selected_items()
        if len(selected) != 1:
            return False
        target = Path(str(selected[0].data(0, Qt.ItemDataRole.UserRole)))
        if not target.is_file():
            return False
        program = get_file_association(target.suffix)
        if not program or not Path(program).exists():
            program, _ = QFileDialog.getOpenFileName(
                self,
                t("files.open_with_select_program"),
                "",
                t("files.open_with_program_filter"),
            )
            program = str(program or "").strip()
            if not program:
                return False
            if target.suffix:
                answer = QMessageBox.question(
                    self,
                    t("files.open_with_save_title"),
                    t("files.open_with_save_prompt").format(
                        extension=target.suffix.lower()
                    ),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if answer == QMessageBox.StandardButton.Yes:
                    set_file_association(target.suffix, program)
        try:
            subprocess.Popen([program, str(target)])
        except OSError as exc:
            QMessageBox.warning(self, t("common.error"), str(exc))
            return False
        return True
