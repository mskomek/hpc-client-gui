"""Remote tree control: sorting and file drag/drop events."""

from __future__ import annotations

from PySide6.QtCore import QMimeData, QTimer, Qt
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget
from hpc_gui.ui.models.remote_entry_helpers import natural_sort_key as _natural_sort_key
from hpc_gui.ui.widgets._fm_dnd_contract import MIME_REMOTE_PATHS, _DragPayload, _decode_payload, _encode_payload
from typing import Optional

_SORT_NAME_ROLE = Qt.ItemDataRole.UserRole + 10
_SORT_SIZE_ROLE = Qt.ItemDataRole.UserRole + 11
_SORT_TYPE_ROLE = Qt.ItemDataRole.UserRole + 12
_SORT_MTIME_ROLE = Qt.ItemDataRole.UserRole + 13
_FILE_MODE_ROLE = Qt.ItemDataRole.UserRole + 20

class _RemoteTree(QTreeWidget):
    """A QTreeWidget that supports drag/drop between RemoteDirPanel instances."""

    def __init__(self, panel: QWidget):
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
