"""Remote copy/move-transfer leaf for the file-manager remote panel.

Owns ``RemoteTransferCopyMoveMixin``: synchronous remote→remote copy/move
plan building with conflict handling, its ``_run_plan_with_progress``
hand-off (including move-only undo recording), and the drag-and-drop apply
entry. Planning-job lifecycle and the GUI-thread conflict/rename bridge live
in ``_remote_transfer_plan``; execution lives in ``_remote_transfer_exec``;
all are reached via ``self``.

Imports Qt-core-free stdlib plus lower-level core/services only — never the
local panel, FTP widget, controllers, or another branch's private
implementation. Shared plan vocabulary (``_PlannedOp``, ``_UndoRecord``) is
imported from the sibling ``_remote_mutations`` module: same remote-panel
branch, one-directional edge, no cycle.
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

from hpc_gui.core.i18n import t
from hpc_gui.core.ui_errors import show_exception
from hpc_gui.ui.widgets._remote_mutations import _PlannedOp, _UndoRecord


class RemoteTransferCopyMoveMixin:
    """Remote→remote copy/move flow ownership (mixed into ``RemoteDirPanel``)."""

    session: object

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
                        action = self._resolve_conflict(  # type: ignore[attr-defined]
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
                        new_dst = self._prompt_rename(dst_dir, name)  # type: ignore[attr-defined]
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

        affected_dirs = {self._normalize_remote_dir(dest_dir)}  # type: ignore[attr-defined]
        if op == "move":
            for src in src_paths:
                affected_dirs.add(self._parent_remote_dir(src))  # type: ignore[attr-defined]

        ok = self._run_plan_with_progress(  # type: ignore[attr-defined]
            plan,
            title,
            after_finished=lambda: self._finish_remote_directory_mutation(affected_dirs),  # type: ignore[attr-defined]
        )
        if not ok:
            return False

        # store undo for move only
        if op == "move":
            moves: List[Tuple[str, str]] = [(p.src, p.dst) for p in plan if p.op == "move"]
            if moves:
                self._set_last_undo(_UndoRecord(kind="move", moves=moves))  # type: ignore[attr-defined]
        return True

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
            show_exception(self, title=t("common.error"), user_message=str(e), exc=e, area="FILES")  # type: ignore[arg-type]
            return False


__all__ = [
    "RemoteTransferCopyMoveMixin",
]
