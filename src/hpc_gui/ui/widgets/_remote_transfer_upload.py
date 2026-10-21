"""Execution flows for local-to-remote uploads.

This leaf owns synchronous upload execution and the incremental GUI-thread
runner. Background and incremental plan construction lives in
_remote_transfer_upload_plan. Conflict handling is coordinated by
_remote_transfer_plan and execution by _remote_transfer_exec through self.
"""

from __future__ import annotations

import os
from typing import List, Optional

from PySide6.QtCore import QTimer

from hpc_gui.core.i18n import t
from hpc_gui.ui.widgets._remote_mutations import _PlannedOp
from hpc_gui.ui.widgets._remote_transfer_plan import (
    _LocalUploadPlanJob,
)


class RemoteTransferUploadMixin:
    """Local→remote upload flow ownership (mixed into ``RemoteDirPanel``)."""

    session: object
    _local_upload_plan_jobs: dict
    _next_local_upload_plan_id: int

    def _apply_local_upload(self, local_paths: List[str], dest_dir: str) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        files = self.session["files"]

        dest_dir = (dest_dir or "/").strip()
        if not dest_dir.startswith("/"):
            dest_dir = "/" + dest_dir
        dest_dir = dest_dir.rstrip("/") or "/"

        plan: List[_PlannedOp] = []
        policy: Optional[str] = None

        seen_sources: set[str] = set()
        for lp in local_paths:
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
                        action = self._resolve_conflict(  # type: ignore[attr-defined]
                            rp_base,
                            src=lp,
                            source_is_local=True,
                            target_is_local=False,
                        )
                        if action.endswith("_all"):
                            policy = action.replace("_all", "")
                        action_simple = action.replace("_all", "")
                    else:
                        action_simple = policy

                    if action_simple == "cancel":
                        return False
                    if action_simple == "skip":
                        rp_base = None
                        break
                    if action_simple == "rename":
                        new_dst = self._prompt_rename(dest_dir, name)  # type: ignore[attr-defined]
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
                    rel_root = os.path.relpath(root, lp)
                    rel_root = "" if rel_root == "." else rel_root
                    for d in dirs:
                        rdir = rp_base + ("/" + rel_root if rel_root else "") + "/" + d
                        plan.append(_PlannedOp(op="mkdir_remote", src="", dst=rdir))
                    for fn in files_ls:
                        lfile = os.path.join(root, fn)
                        rfile = rp_base + ("/" + rel_root if rel_root else "") + "/" + fn
                        while True:
                            try:
                                exists = bool(files.exists(rfile))
                            except Exception:
                                exists = False
                            if not exists:
                                break

                            if policy is None:
                                action = self._resolve_conflict(  # type: ignore[attr-defined]
                                    rfile,
                                    src=lfile,
                                    source_is_local=True,
                                    target_is_local=False,
                                )
                                if action.endswith("_all"):
                                    policy = action.replace("_all", "")
                                action_simple = action.replace("_all", "")
                            else:
                                action_simple = policy

                            if action_simple == "cancel":
                                return False
                            if action_simple == "skip":
                                rfile = None
                                break
                            if action_simple == "rename":
                                new_dst = self._prompt_rename(  # type: ignore[attr-defined]
                                    rfile.rsplit("/", 1)[0],
                                    fn,
                                )
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

        if not plan:
            return True

        return self._run_plan_with_progress(  # type: ignore[attr-defined]
            plan,
            t("dirs.uploading"),
            after_finished=lambda: self._finish_remote_directory_mutation([dest_dir]),  # type: ignore[attr-defined]
            confirm_before_start=True,
        )

    def _apply_local_upload_incremental(self, local_paths: List[str], dest_dir: str) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        normalized_dest = (dest_dir or "/").strip()
        if not normalized_dest.startswith("/"):
            normalized_dest = "/" + normalized_dest
        normalized_dest = normalized_dest.rstrip("/") or "/"
        clean_paths = [path for path in local_paths if path]
        if not clean_paths:
            return True
        files = self.session["files"]
        return self._start_transfer_planning(  # type: ignore[attr-defined]
            "upload",
            lambda worker: self._build_local_upload_plan_background(
                worker,
                files,
                clean_paths,
                normalized_dest,
            ),
        )


    def _apply_local_upload_incremental_gui(self, local_paths: List[str], dest_dir: str) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        dest_dir = (dest_dir or "/").strip()
        if not dest_dir.startswith("/"):
            dest_dir = "/" + dest_dir
        dest_dir = dest_dir.rstrip("/") or "/"

        job_id = self._next_local_upload_plan_id
        self._next_local_upload_plan_id += 1
        self._local_upload_plan_jobs[job_id] = _LocalUploadPlanJob(
            steps=self._iter_local_upload_plan(local_paths, dest_dir),
            dest_dir=dest_dir,
        )
        QTimer.singleShot(0, lambda current_job_id=job_id: self._advance_local_upload_plan(current_job_id))
        return True

    def _advance_local_upload_plan(self, job_id: int) -> None:
        job = self._local_upload_plan_jobs.get(job_id)
        if job is None:
            return
        try:
            # One traversal/probe step per callback prevents slow remote exists
            # calls or large local trees from monopolizing the GUI event loop.
            next(job.steps)
        except StopIteration as finished:
            self._local_upload_plan_jobs.pop(job_id, None)
            plan = finished.value
            if not plan:
                return
            self._run_plan_with_progress(  # type: ignore[attr-defined]
                plan,
                t("dirs.uploading"),
                after_finished=lambda dest=job.dest_dir: self._finish_remote_directory_mutation([dest]),  # type: ignore[attr-defined]
                confirm_before_start=True,
            )
            return
        QTimer.singleShot(0, lambda current_job_id=job_id: self._advance_local_upload_plan(current_job_id))



__all__ = [
    "RemoteTransferUploadMixin",
]
