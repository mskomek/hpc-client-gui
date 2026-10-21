"""Remote download-transfer leaf for the file-manager remote panel.

Owns ``RemoteTransferDownloadMixin``: synchronous and incremental (background
planning) remote→local download flows, including the off-thread download plan
builder and its worker-thread conflict resolver. Planning-job lifecycle and
the GUI-thread conflict/rename bridge live in ``_remote_transfer_plan``;
execution lives in ``_remote_transfer_exec``; all are reached via ``self``.

Imports Qt-core/threading primitives and lower-level core/config/services
only — never the local panel, FTP widget, controllers, or another branch's
private implementation. The plan worker type is imported from the sibling
``_remote_transfer_plan`` module and shared plan vocabulary from the sibling
``_remote_mutations`` module: same remote-panel branch, one-directional edges
(neither sibling imports this leaf), no cycle.
"""

from __future__ import annotations

from hpc_gui.services.transfer_conflict_policy import get_session_conflict_action

import os
from typing import Dict, List, Optional, Tuple

from hpc_gui.core.debug_telemetry import is_source_run
from hpc_gui.core.logging import get_logger
from hpc_gui.services.transfer_mode import PARTIAL_SUFFIX as PARTIAL_DOWNLOAD_SUFFIX
from hpc_gui.ui.widgets._remote_mutations import _PlannedOp
from hpc_gui.ui.widgets._remote_transfer_plan import _TransferPlanWorker


class RemoteTransferDownloadMixin:
    """Remote→local download flow ownership (mixed into ``RemoteDirPanel``)."""

    session: object

    def _remote_walk(self, base_remote: str) -> List[Tuple[str, str, bool]]:
        """Return list of (remote_path, rel_path, is_dir) under base_remote including base."""
        files = self.session["files"]
        base_remote = base_remote.rstrip("/")
        out: List[Tuple[str, str, bool]] = []

        def rec(cur: str, rel: str):
            try:
                entries = files.listdir_entries(cur)
            except Exception:
                return
            for e in entries:
                epath = e.path.rstrip("/")
                erel = (rel + "/" if rel else "") + e.name
                if e.is_dir:
                    out.append((epath, erel, True))
                    rec(epath, erel)
                else:
                    out.append((epath, erel, False))

        out.append((base_remote, "", True))
        rec(base_remote, "")
        return out

    def _apply_remote_download(self, src_paths: List[str], target_dir: str) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        files = self.session["files"]
        target_dir = os.path.abspath(target_dir)

        plan: List[_PlannedOp] = []
        policy: Optional[str] = None

        seen_sources: set[str] = set()
        for src in src_paths:
            src_clean = src.rstrip("/")
            if not src_clean or src_clean in seen_sources:
                continue
            seen_sources.add(src_clean)
            name = os.path.basename(src_clean)
            local_dst = os.path.join(target_dir, name)

            # detect if remote is dir
            try:
                is_dir = bool(files.is_dir(src_clean))
            except Exception:
                is_dir = src.endswith("/")

            # conflict resolution on local target
            while os.path.exists(local_dst):
                # A directory selected for download merges into an existing
                # directory of the same name.  Individual files below it are
                # still checked for conflicts during the recursive walk.
                if is_dir and os.path.isdir(local_dst):
                    break
                if policy is None:
                    action = self._resolve_conflict(  # type: ignore[attr-defined]
                        local_dst,
                        src=src_clean,
                        source_is_local=False,
                        target_is_local=True,
                    )
                    if action.endswith("_all"):
                        policy = action.replace("_all", "")
                    action_simple = action.replace("_all", "")
                else:
                    action_simple = policy

                if action_simple == "cancel":
                    return False
                if action_simple == "skip":
                    local_dst = None
                    break
                if action_simple == "rename":
                    new_dst = self._prompt_rename(target_dir, name)  # type: ignore[attr-defined]
                    if not new_dst:
                        local_dst = None
                        break
                    local_dst = new_dst
                    continue
                if action_simple == "overwrite":
                    plan.append(_PlannedOp(op="delete_local", src="", dst=local_dst, recursive=is_dir))
                    break
                if action_simple == "resume":
                    break

            if not local_dst:
                continue

            if not is_dir:
                plan.append(_PlannedOp(op="download", src=src_clean, dst=local_dst))
            else:
                # mkdir base local
                plan.append(_PlannedOp(op="mkdir_local", src="", dst=local_dst, recursive=False))
                # walk remote dir and download files
                for rpath, rel, r_is_dir in self._remote_walk(src_clean):
                    if rel == "":
                        continue
                    lp = os.path.join(local_dst, rel)
                    if r_is_dir:
                        plan.append(_PlannedOp(op="mkdir_local", src="", dst=lp))
                    else:
                        while os.path.exists(lp):
                            if policy is None:
                                action = self._resolve_conflict(  # type: ignore[attr-defined]
                                    lp,
                                    src=rpath,
                                    source_is_local=False,
                                    target_is_local=True,
                                )
                                if action.endswith("_all"):
                                    policy = action.replace("_all", "")
                                action_simple = action.replace("_all", "")
                            else:
                                action_simple = policy

                            if action_simple == "cancel":
                                return False
                            if action_simple == "skip":
                                lp = None
                                break
                            if action_simple == "rename":
                                new_dst = self._prompt_rename(  # type: ignore[attr-defined]
                                    os.path.dirname(lp),
                                    os.path.basename(lp),
                                )
                                if not new_dst:
                                    lp = None
                                    break
                                lp = new_dst
                                continue
                            if action_simple == "overwrite":
                                plan.append(_PlannedOp(op="delete_local", src="", dst=lp, recursive=False))
                                break
                            if action_simple == "resume":
                                break
                            break
                        if not lp:
                            continue
                        plan.append(_PlannedOp(op="download", src=rpath, dst=lp))

        if not plan:
            return True
        ok = self._run_plan_with_progress(plan, "İndiriliyor...")  # type: ignore[attr-defined]
        return ok

    def _apply_remote_download_incremental(
        self,
        src_paths: List[str],
        target_dir: str,
    ) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        files = self.session["files"]
        clean_paths = [path for path in src_paths if path]
        absolute_target = os.path.abspath(target_dir)
        if not clean_paths:
            return True
        return self._start_transfer_planning(  # type: ignore[attr-defined]
            "download",
            lambda worker: self._build_remote_download_plan_background(
                worker,
                files,
                clean_paths,
                absolute_target,
            ),
        )

    def _build_remote_download_plan_background(
        self,
        worker: _TransferPlanWorker,
        files,
        src_paths: List[str],
        target_dir: str,
    ) -> dict:
        plan: List[_PlannedOp] = []
        affected_dirs: set[str] = set()
        seen: set[str] = set()
        policy: Optional[str] = None
        if is_source_run():
            get_logger("hpc_gui.debug.transfer").info(
                "plan.download started sources=%d target=%r session_policy=%r",
                len(src_paths), target_dir,
                get_session_conflict_action("download"),
            )
        for src in src_paths:
            if worker.cancelled:
                return {}
            src_clean = src.rstrip("/")
            if not src_clean or src_clean in seen:
                continue
            seen.add(src_clean)
            try:
                is_dir = bool(files.is_dir(src_clean))
            except Exception:
                is_dir = src.endswith("/")
            if is_source_run():
                get_logger("hpc_gui.debug.transfer").info(
                    "plan.source remote=%r is_dir=%s", src_clean, is_dir,
                )
            affected_dirs.add(self._parent_remote_dir(src_clean))
            if is_dir:
                affected_dirs.add(self._normalize_remote_dir(src_clean))
            local_dst = os.path.join(target_dir, os.path.basename(src_clean))
            local_dst, policy = self._resolve_download_target_conflict_worker(
                worker,
                local_dst,
                src_clean,
                is_dir=is_dir,
                policy=policy,
                plan=plan,
            )
            if local_dst is None:
                return {}
            if not local_dst:
                continue
            if not is_dir:
                plan.append(_PlannedOp("download", src_clean, local_dst))
                continue
            plan.append(_PlannedOp("mkdir_local", "", local_dst))
            stack: List[Tuple[str, str]] = [(src_clean, "")]
            while stack:
                if worker.cancelled:
                    return {}
                remote_dir, rel_dir = stack.pop()
                # Do not swallow this. A failed listing here used to leave the
                # directory out of the plan silently, so the queue ran only the
                # mkdirs and reported success while nothing was downloaded.
                entries = list(files.listdir_entries(remote_dir))
                if is_source_run():
                    get_logger("hpc_gui.debug.transfer").info(
                        "plan.walk remote_dir=%r entries=%d dirs=%d",
                        remote_dir, len(entries),
                        sum(1 for entry in entries if entry.is_dir),
                    )
                child_dirs: List[Tuple[str, str]] = []
                for entry in entries:
                    rel_path = f"{rel_dir}/{entry.name}" if rel_dir else entry.name
                    local_path = os.path.join(local_dst, rel_path)
                    remote_path = entry.path.rstrip("/")
                    if entry.is_dir:
                        plan.append(_PlannedOp("mkdir_local", "", local_path))
                        child_dirs.append((remote_path, rel_path))
                        continue
                    resolved, policy = self._resolve_download_target_conflict_worker(
                        worker,
                        local_path,
                        remote_path,
                        is_dir=False,
                        policy=policy,
                        plan=plan,
                    )
                    if resolved is None:
                        return {}
                    if not resolved:
                        continue
                    plan.append(
                        _PlannedOp(
                            "download",
                            remote_path,
                            resolved,
                            size=int(entry.size or 0),
                        )
                    )
                stack.extend(reversed(child_dirs))
        if is_source_run():
            counts: Dict[str, int] = {}
            for op in plan:
                counts[op.op] = counts.get(op.op, 0) + 1
            get_logger("hpc_gui.debug.transfer").info(
                "plan.download finished ops=%d breakdown=%r policy=%r",
                len(plan), counts, policy,
            )
        return {
            "plan": plan,
            "title": "İndiriliyor...",
            "affected_dirs": sorted(affected_dirs),
            "confirm_before_start": False,
        }

    def _resolve_download_target_conflict_worker(
        self,
        worker: _TransferPlanWorker,
        local_path: str,
        remote_path: str,
        *,
        is_dir: bool,
        policy: Optional[str],
        plan: List[_PlannedOp],
    ) -> Tuple[Optional[str], Optional[str]]:
        """Resolve a download destination conflict while planning off the GUI thread.

        Remote stat probes for the conflict dialog run on the worker thread;
        only the decision and rename dialogs are shown on the GUI thread via
        the worker's blocking bridge. Returns the resolved local target path
        (None = cancel, "" = skip) together with the updated policy, and appends
        delete_local ops to `plan` for overwrite choices.
        """
        while True:
            part_path = local_path + PARTIAL_DOWNLOAD_SUFFIX
            # A leftover ".part" from a cancelled attempt is prior state the
            # user has to rule on too: resuming it or throwing it away is not
            # a decision this planner gets to make silently.
            partial = (
                not is_dir
                and not os.path.exists(local_path)
                and os.path.exists(part_path)
            )
            if not partial and not os.path.exists(local_path):
                return local_path, policy
            # Do not treat the selected directory itself as a conflict: merge
            # it, then resolve conflicts for its contained files.
            if is_dir and os.path.isdir(local_path):
                return local_path, policy
            if policy is None:
                source = self._conflict_info(remote_path, is_local=False)
                target = self._conflict_info(
                    part_path if partial else local_path, is_local=True
                )
                raw_action = worker.request_conflict_decision(
                    source, target, partial=partial, direction="download"
                )
                if raw_action.endswith("_all"):
                    policy = raw_action.replace("_all", "")
                action_simple = raw_action.replace("_all", "")
            else:
                action_simple = policy
            if is_source_run():
                get_logger("hpc_gui.debug.transfer").info(
                    "plan.conflict remote=%r local=%r partial=%s action=%s policy=%r",
                    remote_path, local_path, partial, action_simple, policy,
                )
            if action_simple == "cancel":
                return None, policy
            if action_simple == "skip":
                return "", policy
            if action_simple == "rename":
                renamed = worker.request_rename(
                    os.path.dirname(local_path),
                    os.path.basename(local_path),
                )
                if not renamed:
                    return "", policy
                local_path = renamed
                continue
            if action_simple == "overwrite":
                # Overwrite means start over, so drop the leftover chunk as
                # well - otherwise the transfer would quietly resume from it.
                plan.append(
                    _PlannedOp(
                        op="delete_local",
                        src="",
                        dst=part_path if partial else local_path,
                        recursive=False if partial else is_dir,
                    )
                )
            # "resume" falls through unchanged: the partial stays, and
            # download_with_mode continues from it once its identity matches.
            return local_path, policy


__all__ = [
    "RemoteTransferDownloadMixin",
]
