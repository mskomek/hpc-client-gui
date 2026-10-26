"""Remote context-menu leaf for the file-manager remote panel.

Owns ``REMOTE_CONTEXT_MENU_LABELS``, the submit/shell candidate helpers, and
``RemoteContextMenuMixin._on_context_menu`` (menu construction, enablement
matrix, and dispatch, GUI thread only). Every action callback — mutations,
navigation, lint/tools, output followers, transfers — stays owned elsewhere
and is reached via ``self``.

Imports Qt and lower-level core/services only — never the local panel, FTP
widget, controllers, or another branch's private implementation.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QTreeWidget

from hpc_gui.core.i18n import t, tr as _tr
from hpc_gui.core.platform import current_os
from hpc_gui.services.file_clipboard import get_file_clipboard
from hpc_gui.services.shortcut_preferences import active_binding

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


class RemoteContextMenuMixin:
    """Context-menu dispatch ownership (mixed into ``RemoteDirPanel``)."""

    session: object
    current_dir: str
    enable_output_menu: bool

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
        binding = active_binding("FILE-NEW-FOLDER", current_os())
        create_label = REMOTE_CONTEXT_MENU_LABELS[5] + (f" ({binding})" if binding else "")
        act_new_folder = menu.addAction(create_label)
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
        if type(self)._last_undo is not None:
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
        from hpc_gui.ui.widgets._remote_linter_action import build_remote_linter_action

        act_openfoam_lint = build_remote_linter_action(
            menu,
            sel_paths[0] if single_selection else None,
            is_directory=single_selection_is_dir,
        )
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

        if act_openfoam_lint is not None and chosen == act_openfoam_lint:
            from hpc_gui.ui.widgets._remote_linter_action import dispatch_remote_linter

            dispatch_remote_linter(self, sel_paths, self.session)
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


__all__ = [
    "REMOTE_CONTEXT_MENU_LABELS",
    "RemoteContextMenuMixin",
]
