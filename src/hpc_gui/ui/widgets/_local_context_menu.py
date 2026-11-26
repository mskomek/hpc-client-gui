"""Local file context-menu actions and dispatch."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QMenu

from hpc_gui.core.i18n import t
from hpc_gui.core.platform import current_os
from hpc_gui.services.shortcut_preferences import active_binding

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


class LocalContextMenuMixin:
    """Build and dispatch context-menu actions for the local panel."""

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
            t("dirs.edit")
        )
        act_edit_new_window = menu.addAction(
            t("dirs.edit_new_window")
        )
        menu.addSeparator()
        binding = active_binding("FILE-NEW-FOLDER", current_os())
        create_label = LOCAL_CONTEXT_MENU_LABELS[8] + (f" ({binding})" if binding else "")
        act_create_dir = menu.addAction(create_label)
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
