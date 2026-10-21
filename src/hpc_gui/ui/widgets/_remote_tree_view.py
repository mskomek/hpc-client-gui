"""Remote panel tree-view composition.

RemoteTreeViewMixin owns view construction, item builders, batched rendering,
selection helpers, keyboard handling, and drop routing. The RemoteTree control
and sort-role constants live in the sibling _remote_tree module and are
re-exported here for compatibility. Panel-owned behavior is reached through
self and the tree's panel reference.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QIcon, QKeyEvent
from PySide6.QtWidgets import (
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
)

from hpc_gui.core.i18n import t
from hpc_gui.ui.widgets._remote_tree import (
    _FILE_MODE_ROLE as _FILE_MODE_ROLE,  # noqa: F401 — legacy re-export
    _RemoteTree as _RemoteTree,  # noqa: F401 — legacy re-export
    _SORT_MTIME_ROLE as _SORT_MTIME_ROLE,  # noqa: F401 — legacy re-export
    _SORT_NAME_ROLE as _SORT_NAME_ROLE,  # noqa: F401 — legacy re-export
    _SORT_SIZE_ROLE as _SORT_SIZE_ROLE,  # noqa: F401 — legacy re-export
    _SORT_TYPE_ROLE as _SORT_TYPE_ROLE,  # noqa: F401 — legacy re-export
)
from hpc_gui.services.file_clipboard import get_file_clipboard
from hpc_gui.services.files_base import RemoteEntry
from hpc_gui.ui.models.remote_entry_helpers import (
    category as _category,
    file_type as _file_type,
    fmt_mtime as _fmt_mtime,
    fmt_size as _fmt_size,
)





class RemoteDirPanelProtocol:
    """Structural protocol for the panel callbacks used by ``_RemoteTree``."""

    def _selected_paths_from_view(self, view: QTreeWidget) -> list[str]: ...  # pragma: no cover
    def _local_paths_from_mime(self, mime) -> list[str]: ...  # pragma: no cover
    def _drop_dest_dir_for_item(self, item) -> str: ...  # pragma: no cover
    def _apply_drag_drop(self, src_paths, dest_dir, *, is_copy, src_panel_id) -> bool: ...  # pragma: no cover
    def _apply_local_upload_incremental(self, paths, target) -> bool: ...  # pragma: no cover
    def open_directory_in_new_tab(self, remote_dir: str) -> bool: ...  # pragma: no cover


class RemoteTreeViewMixin:
    """Tree/view/sort/drag-drop ownership (mixed into ``RemoteDirPanel``)."""

    session: object
    current_dir: str
    views: dict
    tabs: object
    _category_dir: str
    _pending_select_name: str
    _dirty_views: set

    def _make_view(self) -> _RemoteTree:
        w = _RemoteTree(panel=self)
        w.setColumnCount(5)
        w.setHeaderLabels(
            [
                t("dirs.col_name"),
                t("dirs.col_size"),
                t("dirs.col_type"),
                t("dirs.col_mtime"),
                t("ftp.comparison_column"),
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

    def _on_tab_changed(self, index: int) -> None:
        self._settle_current_view()
        self._update_navigation_controls()  # type: ignore[attr-defined]

    def eventFilter(self, watched, event):
        # Delete / Paste / Undo key support on directory views
        if isinstance(watched, QTreeWidget) and event.type() == QEvent.Type.KeyPress:
            e: QKeyEvent = event  # type: ignore
            if e.key() == Qt.Key.Key_Backspace and not e.modifiers():
                self.go_parent()  # type: ignore[attr-defined]
                return True
            if e.key() == Qt.Key.Key_Delete:
                self.delete_selected()  # type: ignore[attr-defined]
                return True
            if e.key() == Qt.Key.Key_F5 and not e.modifiers():
                self._refresh_from_ui(force=True)  # type: ignore[attr-defined]
                return True
            if e.key() == Qt.Key.Key_F2 and not e.modifiers():
                if self.rename_selected(watched):  # type: ignore[attr-defined]
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
                    lambda target=dest_dir: self._paste_from_clipboard_into(target),  # type: ignore[attr-defined]
                )
                return True
            if (e.modifiers() & Qt.KeyboardModifier.ControlModifier) and e.key() == Qt.Key.Key_Z:
                self.undo_last()  # type: ignore[attr-defined]
                return True
        return super().eventFilter(watched, event)  # type: ignore[attr-defined]

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
        super().dragEnterEvent(event)  # type: ignore[attr-defined]

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._local_paths_from_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)  # type: ignore[attr-defined]

    def dropEvent(self, event) -> None:  # type: ignore[override]
        paths = self._local_paths_from_mime(event.mimeData())
        if not paths:
            super().dropEvent(event)  # type: ignore[attr-defined]
            return
        target_dir = self.current_dir or "/"
        event.acceptProposedAction()
        QTimer.singleShot(
            0,
            lambda dropped_paths=list(paths), target=target_dir: self._apply_local_upload_incremental(dropped_paths, target),  # type: ignore[attr-defined]
        )

    def _handle_item_double_clicked(self, item, col):
        path = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        if not path:
            return
        is_dir = bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
        if is_dir:
            self.set_dir(path.rstrip("/") or "/")  # type: ignore[attr-defined]
            return
        self.file_activated.emit(path)  # type: ignore[attr-defined]

    def _icon_for(self, entry: RemoteEntry) -> QIcon:
        st = self.style()  # type: ignore[attr-defined]
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
        item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))  # type: ignore[attr-defined]
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
        parent_dir = self._remote_parent_dir(category_dir)  # type: ignore[attr-defined]
        if parent_dir:
            self.views["all"].addTopLevelItem(self._make_parent_item(parent_dir))
            if "folders" in self.views:
                self.views["folders"].addTopLevelItem(self._make_parent_item(parent_dir))
        self._update_navigation_controls()  # type: ignore[attr-defined]

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
        self._update_undo_enabled()  # type: ignore[attr-defined]
        self._update_navigation_controls()  # type: ignore[attr-defined]

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
        current = self.tabs.currentWidget()  # type: ignore[union-attr]
        for key, view in self.views.items():
            if view is not current or key not in self._dirty_views:
                continue
            self._dirty_views.discard(key)
            view.apply_sort()
            for column in range(4):
                view.resizeColumnToContents(column)

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

    def selected_paths(self, tab_key: str = "all") -> List[str]:
        view = self.views.get(tab_key, self.views["all"])
        return self._selected_paths_from_view(view)


__all__ = [
    "RemoteTreeViewMixin",
    "RemoteDirPanelProtocol",
    "_RemoteTree",
    "_SORT_NAME_ROLE",
    "_SORT_SIZE_ROLE",
    "_SORT_TYPE_ROLE",
    "_SORT_MTIME_ROLE",
    "_FILE_MODE_ROLE",
]
