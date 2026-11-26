"""Legacy upload entry points sharing one traversal and conflict planner.

The active wx runtime uses services.upload_plan and wx_shell_upload.
This remaining legacy adapter uses its existing worker bridge for conflicts
rather than scheduling filesystem or network probes on the GUI thread.
"""

from __future__ import annotations

import os
from typing import List, Optional

from hpc_gui.core.i18n import t
from hpc_gui.services.transfer_conflict_policy import read_conflict_metadata
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.ui.widgets._remote_mutations import _PlannedOp


class RemoteTransferUploadMixin:
    """Local→remote upload flow ownership (mixed into the legacy panel)."""

    session: object

    @staticmethod
    def _normalize_upload_destination(dest_dir: str) -> str:
        dest_dir = (dest_dir or "/").strip()
        if not dest_dir.startswith("/"):
            dest_dir = "/" + dest_dir
        return dest_dir.rstrip("/") or "/"

    @staticmethod
    def _build_local_upload_plan(files, local_paths, dest_dir, resolve, rename,
                                 *, current=lambda: True):
        """Return a mutation-free plan, or None for cancellation."""
        plan: List[_PlannedOp] = []
        policy: Optional[str] = None

        seen_sources: set[str] = set()
        for lp in local_paths:
            if not current():
                return None
            if not lp:
                continue
            lp = os.path.abspath(lp)
            if lp in seen_sources:
                continue
            seen_sources.add(lp)
            name = os.path.basename(lp.rstrip(os.sep))
            rp_base = dest_dir.rstrip("/") + "/" + name
            is_dir = os.path.isdir(lp)

            # conflict resolution on remote target
            while True:
                if not current():
                    return None
                try:
                    exists = bool(files.exists(rp_base))
                except Exception:
                    exists = False

                if exists and is_dir:
                    try:
                        target_is_dir = bool(files.is_dir(rp_base))
                    except Exception:
                        target_is_dir = False
                    if target_is_dir:
                        # Merge matching directories; nested file conflicts
                        # are handled below while building the upload plan.
                        break

                if exists:
                    if policy is None:
                        action = resolve(lp, rp_base)
                        if action.endswith("_all"):
                            policy = action.replace("_all", "")
                        action_simple = action.replace("_all", "")
                    else:
                        action_simple = policy

                    if action_simple == "cancel":
                        return None
                    if action_simple == "skip":
                        rp_base = None
                        break
                    if action_simple == "rename":
                        new_dst = rename(dest_dir, name)
                        if not new_dst:
                            rp_base = None
                            break
                        rp_base = new_dst
                        continue
                    if action_simple == "overwrite":
                        try:
                            isdir_remote = bool(files.is_dir(rp_base))
                        except Exception:
                            isdir_remote = False
                        plan.append(_PlannedOp(op="delete", src="", dst=rp_base, recursive=isdir_remote))
                    elif action_simple == "resume":
                        pass
                break

            if not rp_base:
                continue

            if not is_dir:
                plan.append(_PlannedOp(op="upload", src=lp, dst=rp_base))
            else:
                # mkdir base
                plan.append(_PlannedOp(op="mkdir_remote", src="", dst=rp_base))
                # walk local dir
                for root, dirs, files_ls in os.walk(lp):
                    if not current():
                        return None
                    rel_root = os.path.relpath(root, lp)
                    rel_root = "" if rel_root == "." else rel_root
                    for d in dirs:
                        rdir = rp_base + ("/" + rel_root if rel_root else "") + "/" + d
                        plan.append(_PlannedOp(op="mkdir_remote", src="", dst=rdir))
                    for fn in files_ls:
                        lfile = os.path.join(root, fn)
                        rfile = rp_base + ("/" + rel_root if rel_root else "") + "/" + fn
                        while True:
                            if not current():
                                return None
                            try:
                                exists = bool(files.exists(rfile))
                            except Exception:
                                exists = False
                            if not exists:
                                break

                            if policy is None:
                                action = resolve(lfile, rfile)
                                if action.endswith("_all"):
                                    policy = action.replace("_all", "")
                                action_simple = action.replace("_all", "")
                            else:
                                action_simple = policy

                            if action_simple == "cancel":
                                return None
                            if action_simple == "skip":
                                rfile = None
                                break
                            if action_simple == "rename":
                                new_dst = rename(rfile.rsplit("/", 1)[0], fn)
                                if not new_dst:
                                    rfile = None
                                    break
                                rfile = new_dst
                                continue
                            if action_simple == "overwrite":
                                try:
                                    isdir_remote = bool(files.is_dir(rfile))
                                except Exception:
                                    isdir_remote = False
                                plan.append(_PlannedOp(op="delete", src="", dst=rfile, recursive=isdir_remote))
                                break
                            if action_simple == "resume":
                                break
                            break
                        if not rfile:
                            continue
                        plan.append(_PlannedOp(op="upload", src=lfile, dst=rfile))

        return plan if current() else None

    def _apply_local_upload(self, local_paths: List[str], dest_dir: str) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        dest_dir = self._normalize_upload_destination(dest_dir)
        plan = self._build_local_upload_plan(
            self.session["files"], local_paths, dest_dir,
            lambda src, dst: self._resolve_conflict(
                dst, src=src, source_is_local=True, target_is_local=False),
            self._prompt_rename,
        )
        if plan is None:
            return False
        if not plan:
            return True
        return self._run_plan_with_progress(
            plan, t("dirs.uploading"),
            after_finished=lambda: self._finish_remote_directory_mutation([dest_dir]),
            confirm_before_start=True,
        )

    def _build_local_upload_plan_background(self, worker, files, local_paths, dest_dir, *, session=None):
        session = self.session if session is None else session

        def current():
            return (not worker.cancelled and self.session is session
                    and session and session.get("files") is files)

        def resolve(src, dst):
            if not current():
                return "cancel"
            source, target = read_conflict_metadata(files, TransferItem("upload", src, dst))
            if not current():
                return "cancel"
            return worker.request_conflict_decision(source, target, direction="upload")

        def rename(directory, name):
            return worker.request_rename(directory, name) if current() else None

        plan = self._build_local_upload_plan(
            files, local_paths, dest_dir, resolve, rename, current=current,
        )
        if not plan or not current():
            return {}
        return {
            "plan": plan,
            "title": t("dirs.uploading"),
            "affected_dirs": [self._normalize_remote_dir(dest_dir)],
            "confirm_before_start": True,
            "session_owner": session,
            "files_owner": files,
        }

    def _apply_local_upload_incremental(self, local_paths: List[str], dest_dir: str) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        normalized_dest = self._normalize_upload_destination(dest_dir)
        clean_paths = [path for path in local_paths if path]
        if not clean_paths:
            return True
        session = self.session
        files = session["files"]
        return self._start_transfer_planning(
            "upload",
            lambda worker: self._build_local_upload_plan_background(
                worker, files, clean_paths, normalized_dest, session=session),
        )


__all__ = ["RemoteTransferUploadMixin"]
