"""Local tree view leaf for the file-manager local panel.

Owns ``_LocalTree`` (sort, drag-and-drop, keyboard, middle-click) plus the
sort helpers and the comparison-column mixin. Imports only the DnD contract
leaf and Qt — never remote panel, FTP, or controller modules.
"""

from __future__ import annotations

import json

import logging
import re

from PySide6.QtCore import QMimeData, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget

from hpc_gui.core.i18n import t
from hpc_gui.services.directory_comparison import CompareStatus
from hpc_gui.ui.widgets._fm_dnd_contract import MIME_REMOTE_PATHS

logger = logging.getLogger(__name__)

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

    def __init__(self, panel: QWidget) -> None:
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


class LocalDirPanelProtocol:
    """Structural protocol for the panel callbacks used by ``_LocalTree``."""

    def selected_paths(self) -> list[str]: ...  # pragma: no cover
    def refresh(self) -> None: ...  # pragma: no cover
    def copy_selected(self) -> bool: ...  # pragma: no cover
    def cut_selected(self) -> bool: ...  # pragma: no cover
    def paste_into_current_dir(self) -> bool: ...  # pragma: no cover
    def rename_selected(self) -> bool: ...  # pragma: no cover
    def delete_selected(self) -> bool: ...  # pragma: no cover
    def open_directory_in_new_tab(self, directory: str) -> bool: ...  # pragma: no cover


class LocalComparisonMixin:
    """Comparison-column state and rendering for the local panel."""

    _comparison_statuses: dict[str, CompareStatus] | None
    _tab_dirs: dict[_LocalTree, str]
    tree: _LocalTree

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


__all__ = [
    "_LocalTree",
    "_SORT_NAME_ROLE",
    "_SORT_SIZE_ROLE",
    "_SORT_TYPE_ROLE",
    "_SORT_MTIME_ROLE",
    "_format_size",
    "_natural_sort_key",
    "LocalComparisonMixin",
    "LocalDirPanelProtocol",
]
