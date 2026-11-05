"""Conflict-aware best-effort case saves with staged files and rollback evidence."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import tempfile
import uuid
from typing import Mapping

from .models import CaseDocument, SaveConflictError, SaveReport
from hpc_gui.openfoam_core import safe_relative_path


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def save_local_case(root: str | Path, documents: Mapping[str, CaseDocument]) -> SaveReport:
    case_root = Path(root).resolve(strict=True)
    if any(document.read_only for document in documents.values()):
        return SaveReport(False, False, (), errors=("case workspace is a read-only snapshot",))
    changed = {key: doc for key, doc in documents.items() if doc.modified and not doc.remote}
    if not changed:
        return SaveReport(True, False, ())
    staged: dict[str, Path] = {}
    backups: dict[str, Path] = {}
    swapped: list[str] = []
    try:
        targets: dict[str, Path] = {}
        for relative, document in changed.items():
            if not safe_relative_path(relative):
                raise ValueError(f"unsafe case-relative path: {relative}")
            target = case_root.joinpath(*Path(relative).parts)
            if target.is_symlink() or not target.is_file() or case_root not in target.resolve(strict=True).parents:
                raise OSError(f"refusing unsafe save target: {relative}")
            if not os.access(target, os.W_OK):
                raise PermissionError(f"file is not writable: {relative}")
            if _digest(target) != document.expected_sha256:
                raise SaveConflictError(f"file changed after it was opened: {relative}")
            targets[relative] = target

        token = uuid.uuid4().hex
        for relative, target in targets.items():
            backup = target.with_name(f".{target.name}.{token}.backup")
            if backup.exists():
                raise FileExistsError(f"backup path unexpectedly exists for {relative}")
            fd, name = tempfile.mkstemp(prefix=f".{target.name}.{token}.", suffix=".stage", dir=target.parent)
            staged[relative] = Path(name)
            with os.fdopen(fd, "wb") as stream:
                stream.write(changed[relative].to_bytes())
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.chmod(name, stat.S_IMODE(target.stat().st_mode))
            except OSError:
                pass
            backups[relative] = backup

        # Recheck all fingerprints immediately before the first replacement.
        for relative, target in targets.items():
            if target.is_symlink() or _digest(target) != changed[relative].expected_sha256:
                raise SaveConflictError(f"file changed during save preparation: {relative}")
        for relative, target in targets.items():
            os.replace(target, backups[relative])
            swapped.append(relative)
            os.replace(staged[relative], target)
        recovery: list[str] = []
        for backup in backups.values():
            try:
                backup.unlink()
            except OSError:
                recovery.append(str(backup))
        for relative, document in changed.items():
            document.mark_saved(targets[relative].read_bytes())
        return SaveReport(True, False, tuple(targets), errors=("backup cleanup failed",) if recovery else (), recovery_paths=tuple(recovery))
    except SaveConflictError as exc:
        return SaveReport(False, False, (), conflicts=(str(exc),))
    except Exception as exc:
        errors = [str(exc)]
        recovery: list[str] = []
        for relative in reversed(swapped):
            target = case_root.joinpath(*Path(relative).parts)
            backup = backups.get(relative)
            try:
                if target.exists():
                    target.unlink()
                if backup and backup.exists():
                    os.replace(backup, target)
            except OSError as rollback_error:
                errors.append(f"rollback failed for {relative}: {rollback_error}")
                if backup and backup.exists():
                    recovery.append(str(backup))
        return SaveReport(False, bool(swapped or recovery), (), errors=tuple(errors), recovery_paths=tuple(recovery))
    finally:
        for temporary in staged.values():
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
