"""Background and incremental planning for local-to-remote uploads."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Generator, List, Optional

from hpc_gui.core.i18n import t
from hpc_gui.ui.widgets._remote_mutations import _PlannedOp
if TYPE_CHECKING:
    from hpc_gui.ui.widgets._remote_transfer_plan import _TransferPlanWorker


class RemoteTransferUploadPlanMixin:
    """Own remote upload planning while the upload facade owns execution."""

    session: object
    _local_upload_plan_jobs: dict
    _next_local_upload_plan_id: int

    def _build_local_upload_plan_background(
        self,
        worker: _TransferPlanWorker,
        files,
        local_paths: List[str],
        dest_dir: str,
    ) -> dict:
        plan: List[_PlannedOp] = []
        seen: set[str] = set()
        for local_path in local_paths:
            if worker.cancelled:
                return {}
            absolute_path = os.path.abspath(local_path)
            if absolute_path in seen:
                continue
            seen.add(absolute_path)
            name = os.path.basename(absolute_path.rstrip(os.sep))
            remote_base = dest_dir.rstrip("/") + "/" + name
            try:
                base_exists = bool(files.exists(remote_base))
            except Exception:
                base_exists = False
            if base_exists:
                return {
                    "conflict": True,
                    "paths": local_paths,
                    "directory": dest_dir,
                }
            if not os.path.isdir(absolute_path):
                plan.append(
                    _PlannedOp("upload", absolute_path, remote_base)
                )
                continue
            plan.append(_PlannedOp("mkdir_remote", "", remote_base))
            for root, dirs, filenames in os.walk(absolute_path):
                if worker.cancelled:
                    return {}
                rel_root = os.path.relpath(root, absolute_path)
                rel_root = "" if rel_root == "." else rel_root
                remote_root = remote_base + (
                    "/" + rel_root.replace(os.sep, "/")
                    if rel_root
                    else ""
                )
                for dirname in dirs:
                    plan.append(
                        _PlannedOp(
                            "mkdir_remote",
                            "",
                            remote_root + "/" + dirname,
                        )
                    )
                for filename in filenames:
                    local_file = os.path.join(root, filename)
                    remote_file = remote_root + "/" + filename
                    try:
                        file_exists = bool(files.exists(remote_file))
                    except Exception:
                        file_exists = False
                    if file_exists:
                        return {
                            "conflict": True,
                            "paths": local_paths,
                            "directory": dest_dir,
                        }
                    plan.append(_PlannedOp("upload", local_file, remote_file))
        return {
            "plan": plan,
            "title": t("dirs.uploading"),
            "affected_dirs": [self._normalize_remote_dir(dest_dir)],  # type: ignore[attr-defined]
            "confirm_before_start": True,
        }

    def _iter_local_upload_plan(
        self,
        local_paths: List[str],
        dest_dir: str,
    ) -> Generator[None, None, Optional[List[_PlannedOp]]]:
        if not self.session or not self.session.get("files"):
            return None
        files = self.session["files"]
        plan: List[_PlannedOp] = []
        policy: Optional[str] = None

        seen_sources: set[str] = set()
        for lp in local_paths:
            if not lp:
                yield
                continue
            lp = os.path.abspath(lp)
            if lp in seen_sources:
                yield
                continue
            seen_sources.add(lp)
            name = os.path.basename(lp.rstrip(os.sep))
            rp_base = dest_dir.rstrip("/") + "/" + name
            is_dir = os.path.isdir(lp)

            while True:
                try:
                    exists = bool(files.exists(rp_base))
                except Exception:
                    exists = False
                yield

                if exists and is_dir:
                    try:
                        target_is_dir = bool(files.is_dir(rp_base))
                    except Exception:
                        target_is_dir = False
                    if target_is_dir:
                        # Keep the target directory and resolve only nested
                        # file conflicts while building the upload plan.
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
                        return None
                    if action_simple == "skip":
                        rp_base = None
                        break
                    if action_simple == "rename":
                        new_dst = self._prompt_rename(dest_dir, name)  # type: ignore[attr-defined]
                        if not new_dst:
                            rp_base = None
                            break
                        rp_base = new_dst
                        yield
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
                yield
                continue

            if not is_dir:
                plan.append(_PlannedOp(op="upload", src=lp, dst=rp_base))
                yield
                continue

            plan.append(_PlannedOp(op="mkdir_remote", src="", dst=rp_base))
            yield
            for root, dirs, files_ls in os.walk(lp):
                yield
                rel_root = os.path.relpath(root, lp)
                rel_root = "" if rel_root == "." else rel_root
                for d in dirs:
                    rdir = rp_base + ("/" + rel_root if rel_root else "") + "/" + d
                    plan.append(_PlannedOp(op="mkdir_remote", src="", dst=rdir))
                    yield
                for fn in files_ls:
                    lfile = os.path.join(root, fn)
                    rfile = rp_base + ("/" + rel_root if rel_root else "") + "/" + fn
                    while True:
                        try:
                            exists = bool(files.exists(rfile))
                        except Exception:
                            exists = False
                        yield
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
                            return None
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
                            yield
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
                        yield
                        continue
                    plan.append(_PlannedOp(op="upload", src=lfile, dst=rfile))
                    yield

        return plan
