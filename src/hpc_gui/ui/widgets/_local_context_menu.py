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
        from hpc_gui.services.openfoam_file_dispatch import (
            active_linter,
            supports_local_targets,
        )

        openfoam_plugin = None
        openfoam_allowed = False
        openfoam_reason = ""
        if supports_local_targets(paths):
            openfoam_plugin = active_linter()
            if openfoam_plugin is not None:
                from hpc_gui.services.plugin_menu_actions import can_execute_action

                openfoam_allowed, openfoam_reason = can_execute_action(
                    "openfoam.validate", openfoam_plugin
                )
        plugin_menu = menu.addMenu(t("files.plugins")) if lint_batch_ok or openfoam_plugin else None
        act_ansys_lint = (
            plugin_menu.addAction(t("files.ansys_lint"))
            if plugin_menu is not None
            else None
        )
        if act_ansys_lint is not None:
            act_ansys_lint.setEnabled(lint_batch_ok)
        act_openfoam_lint = (
            plugin_menu.addAction(t("openfoam.linter_title"))
            if plugin_menu is not None and openfoam_plugin is not None
            else None
        )
        if act_openfoam_lint is not None:
            act_openfoam_lint.setEnabled(openfoam_allowed)
            if openfoam_reason:
                act_openfoam_lint.setToolTip(openfoam_reason)
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
        if act_openfoam_lint is not None and chosen == act_openfoam_lint:
            from hpc_gui.services.openfoam_file_dispatch import dispatch_linter

            dispatch_linter(paths, host_window=self.window())
            return
