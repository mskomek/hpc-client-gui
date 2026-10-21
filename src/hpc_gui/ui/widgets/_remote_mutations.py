"""Remote mutation leaf for the file-manager remote panel.

Owns ``RemoteMutationsMixin``: the shared ``_PlannedOp`` / ``_UndoRecord``
plan vocabulary, create/rename/delete flows, single-level undo, clipboard
paste entry points, and cross-panel mutation fan-out
(``_finish_remote_directory_mutation``). All transfer execution
(``_run_plan_with_progress``, ``_apply_copy_move_with_conflicts``,
``_apply_local_upload_incremental``, ``_apply_remote_download_incremental``),
conflict/rename bridges, and shutdown stay owned elsewhere and are reached
via ``self``. Class-level panel state (``_last_undo``, ``_instances``) is
reached via ``type(self)``, which is exactly ``RemoteDirPanel`` for the
single concrete panel class — no leaf→facade import.

Imports Qt and lower-level core/services only — never the local panel, FTP
widget, controllers, or another branch's private implementation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QTreeWidget,
)

from hpc_gui.core.i18n import t, tr as _tr
from hpc_gui.core.ui_errors import show_exception
from hpc_gui.services.file_clipboard import get_file_clipboard


@dataclass
class _PlannedOp:
    op: str  # "copy" | "move" | "delete"
    src: str
    dst: str
    recursive: Optional[bool] = False
    size: Optional[int] = None  # known size, only when the listing already carries it


@dataclass
class _UndoRecord:
    kind: str  # currently only "move"
    moves: List[Tuple[str, str]]  # (src, dst) executed


class RemoteMutationsMixin:
    """CRUD/mutation + undo ownership (mixed into ``RemoteDirPanel``)."""

    session: object
    current_dir: str
    views: dict
    tabs: object
    btn_undo: object

    # ---------- create ----------
    @staticmethod
    def _child_path(parent_dir: str, name: str) -> str:
        return (parent_dir.rstrip("/") or "") + "/" + name

    def _prompt_new_name(self, *, kind: str) -> str:
        is_folder = kind == "folder"
        title_key = "dirs.new_folder_title" if is_folder else "dirs.new_file_title"
        label_key = "dirs.new_folder_label" if is_folder else "dirs.new_file_label"
        name, ok = QInputDialog.getText(self, t(title_key), t(label_key))  # type: ignore[arg-type]
        if not ok:
            return ""
        name = (name or "").strip()
        if not name:
            return ""
        if name in (".", "..") or "/" in name or "\\" in name:
            QMessageBox.warning(self, t("common.error"), t("dirs.invalid_new_name"))  # type: ignore[arg-type]
            return ""
        return name

    def _create_remote_item(self, *, kind: str, parent_dir: Optional[str] = None) -> bool:
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))  # type: ignore[arg-type]
            return False
        raw_target_dir = parent_dir or self.current_dir or ""
        if not raw_target_dir:
            QMessageBox.warning(self, t("common.error"), t("dirs.no_directory_selected"))  # type: ignore[arg-type]
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
            show_exception(self, title=t("common.error"), user_message=str(e), exc=e, area="FILES")  # type: ignore[arg-type]
            return False

    def create_new_folder(self, parent_dir: Optional[str] = None) -> bool:
        return self._create_remote_item(kind="folder", parent_dir=parent_dir)

    def create_new_folder_and_enter(self, parent_dir: Optional[str] = None) -> bool:
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))  # type: ignore[arg-type]
            return False
        raw_target_dir = parent_dir or self.current_dir or ""
        if not raw_target_dir:
            QMessageBox.warning(self, t("common.error"), t("dirs.no_directory_selected"))  # type: ignore[arg-type]
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
            self.set_dir(target_path)  # type: ignore[attr-defined]
            return True
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=str(e), exc=e, area="FILES")  # type: ignore[arg-type]
            return False

    def create_new_file(self, parent_dir: Optional[str] = None) -> bool:
        return self._create_remote_item(kind="file", parent_dir=parent_dir)

    # ---------- rename / delete ----------
    def rename_selected(self, view: Optional[QTreeWidget] = None) -> bool:
        if view is None:
            current = self.tabs.currentWidget()  # type: ignore[union-attr]
            view = current if isinstance(current, QTreeWidget) else self.views["all"]
        return self._rename_paths(self._selected_paths_from_view(view))  # type: ignore[attr-defined]

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
            t("dirs.rename"),
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
            t("common.confirm"),
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
        tab = self.tabs.currentWidget()  # type: ignore[union-attr]
        tab_key = "all"
        for k, v in self.views.items():
            if v is tab:
                tab_key = k
                break
        sel = self.selected_paths(tab_key)  # type: ignore[attr-defined]
        if not sel:
            QMessageBox.information(self, t("common.info"), t("dirs.no_file_selected"))  # type: ignore[arg-type]
            return
        self._delete_paths(sel, self._selected_entries_from_view(tab))  # type: ignore[attr-defined]

    # ---------- undo ----------
    def _update_undo_enabled(self) -> None:
        self.btn_undo.setEnabled(bool(type(self)._last_undo))

    def _set_last_undo(self, rec: Optional[_UndoRecord]) -> None:
        type(self)._last_undo = rec
        # reflect on all panels
        for p in list(type(self)._instances.values()):
            try:
                p._update_undo_enabled()
            except Exception:
                pass

    def undo_last(self) -> None:
        if not self.session or not self.session.get("files"):
            return
        rec = type(self)._last_undo
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

    def _finish_remote_directory_mutation(self, remote_dirs: Iterable[str]) -> None:
        affected = {
            self._normalize_remote_dir(remote_dir)
            for remote_dir in remote_dirs
            if remote_dir
        }
        if not affected:
            return

        panels: List[Tuple[str, object]] = []
        for panel_id, panel in list(type(self)._instances.items()):
            if type(self)._instances.get(panel_id) is not panel:
                continue
            try:
                for remote_dir in affected:
                    panel._invalidate_directory_cache(remote_dir)
            except RuntimeError:
                if type(self)._instances.get(panel_id) is panel:
                    type(self)._instances.pop(panel_id, None)
                continue
            panels.append((panel_id, panel))

        for panel_id, panel in panels:
            try:
                current = self._normalize_remote_dir(panel.current_dir or "/")
                if current in affected:
                    panel._refresh_from_ui(force=True)
            except RuntimeError:
                if type(self)._instances.get(panel_id) is panel:
                    type(self)._instances.pop(panel_id, None)

    # ---------- clipboard paste ----------
    def _paste_from_clipboard_into(self, dest_dir: str) -> None:
        """Start a paste after the originating tree key event has finished."""
        try:
            if self._paste_system_clipboard_into(dest_dir):
                return
            self._paste_remote_clipboard_into(dest_dir)
        except Exception as exc:
            # The delayed callback is outside the caller's event stack, so
            # keep the last safety net here as well as in the paste helpers.
            show_exception(self, title=t("common.error"), user_message=str(exc), exc=exc, area="FILES")  # type: ignore[arg-type]

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
            ok = self._apply_copy_move_with_conflicts(op, [s for s in clip.paths], dest_dir)  # type: ignore[attr-defined]
            if ok and clip.op == "move":
                clipboard.clear()
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=str(e), exc=e, area="FILES")  # type: ignore[arg-type]

    def _paste_system_clipboard_into(self, dest_dir: str) -> bool:
        """If OS clipboard contains local file urls, upload them into dest_dir."""
        cb = QApplication.clipboard().mimeData()
        if not cb or not cb.hasUrls():
            return False
        local_paths = [u.toLocalFile() for u in cb.urls() if u.isLocalFile()]
        if not local_paths:
            return False
        return self._apply_local_upload_incremental(local_paths, dest_dir)  # type: ignore[attr-defined]

    def _paste_remote_to_local(self) -> None:
        """Download internal remote clipboard items into a chosen local directory."""
        if not self.session or not self.session.get("files"):
            return
        clip = get_file_clipboard().get()
        if not clip or not clip.paths:
            return
        target_dir = QFileDialog.getExistingDirectory(
            self, t("dirs.select_local_folder")  # type: ignore[arg-type]
        )
        if not target_dir:
            return
        ok = self._apply_remote_download_incremental(clip.paths, target_dir)  # type: ignore[attr-defined]
        if ok and clip.op == "move":
            # move doesn't make sense for remote->local; keep clipboard as-is
            pass


__all__ = [
    "RemoteMutationsMixin",
    "_PlannedOp",
    "_UndoRecord",
]
