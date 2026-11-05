"""Bounded remote case reads and recoverable multi-file SFTP save."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import uuid

from hpc_gui.openfoam_core import (
    MAX_REMOTE_CASE_BYTES,
    MAX_REMOTE_CASE_DEPTH,
    MAX_REMOTE_CASE_FILES,
    MAX_REMOTE_DICTIONARY_BYTES,
    REMOTE_CASE_SKIP_DIRS,
    safe_relative_path,
    scan_remote_dictionaries,
)

from .models import CaseDocument, SaveConflictError, SaveReport

MAX_FILE_BYTES = MAX_REMOTE_DICTIONARY_BYTES
MAX_CASE_BYTES = MAX_REMOTE_CASE_BYTES
MAX_FILES = MAX_REMOTE_CASE_FILES
MAX_DEPTH = MAX_REMOTE_CASE_DEPTH
SKIP_DIRS = REMOTE_CASE_SKIP_DIRS
_RECOVERY_NAME = re.compile(r"^\.(?P<name>[^/]+)\.(?P<token>[0-9a-f]{32})\.(?P<kind>backup|stage)$")


def _inside(root: PurePosixPath, path: PurePosixPath) -> bool:
    return path == root or root in path.parents


def _root_path(value: str) -> PurePosixPath:
    root = PurePosixPath(value)
    if not root.is_absolute() or ".." in root.parts:
        raise ValueError("remote case root must be a safe absolute POSIX path")
    return root


def _read_remote_bytes(files, path: str, *, maximum: int) -> bytes:
    size, _mtime = files.stat(path)
    if int(size) > maximum:
        raise ValueError("remote dictionary exceeds the configured size limit")
    with tempfile.TemporaryDirectory(prefix="hpc-openfoam-read-") as directory:
        target = Path(directory) / "payload"
        files.download(path, str(target))
        data = target.read_bytes()
    if len(data) > maximum:
        raise ValueError("downloaded dictionary exceeds the configured size limit")
    return data


def scan_remote_case(root: str, files, *, read_only: bool = False) -> dict[str, CaseDocument]:
    remote_root = _root_path(root)
    payloads = scan_remote_dictionaries(
        str(remote_root),
        files,
        maximum_file_bytes=MAX_FILE_BYTES,
        maximum_case_bytes=MAX_CASE_BYTES,
        maximum_files=MAX_FILES,
        maximum_depth=MAX_DEPTH,
        skip_dirs=SKIP_DIRS,
    )
    return {
        relative: CaseDocument.from_bytes(
            relative,
            str(remote_root.joinpath(*PurePosixPath(relative).parts)),
            data,
            remote=True,
            read_only=read_only,
        )
        for relative, data in payloads.items()
    }


def save_remote_case(root: str, files, documents: dict[str, CaseDocument]) -> SaveReport:
    remote_root = _root_path(root)
    if any(document.read_only for document in documents.values()):
        return SaveReport(False, False, (), errors=("case workspace is a read-only snapshot",))
    changed = {name: doc for name, doc in documents.items() if doc.remote and doc.modified}
    if not changed:
        return SaveReport(True, False, ())
    token = uuid.uuid4().hex
    staged: dict[str, str] = {}
    backups: dict[str, str] = {}
    swapped: list[str] = []
    local_temps: list[str] = []
    attempted_stages: set[str] = set()
    attempted_backups: set[str] = set()
    preserve_recovery_artifacts = False
    try:
        targets: dict[str, PurePosixPath] = {}
        for relative, document in changed.items():
            if not safe_relative_path(relative):
                raise ValueError(f"unsafe remote case-relative path: {relative}")
            target = remote_root.joinpath(*PurePosixPath(relative).parts)
            if not _inside(remote_root, target) or not files.exists(str(target)) or files.is_dir(str(target)):
                raise OSError(f"unsafe or missing remote target: {relative}")
            current = _read_remote_bytes(files, str(target), maximum=MAX_FILE_BYTES)
            if hashlib.sha256(current).hexdigest() != document.expected_sha256:
                raise SaveConflictError(f"remote file changed after it was opened: {relative}")
            targets[relative] = target

        for relative, target in targets.items():
            stage = target.with_name(f".{target.name}.{token}.stage")
            backup = target.with_name(f".{target.name}.{token}.backup")
            if files.exists(str(stage)) or files.exists(str(backup)):
                raise FileExistsError(f"temporary remote path unexpectedly exists for {relative}")
            staged[relative] = str(stage)
            backups[relative] = str(backup)

        for relative in targets:
            with tempfile.NamedTemporaryFile(prefix="hpc-openfoam-stage-", delete=False) as local:
                local.write(changed[relative].to_bytes())
                local.flush()
                os.fsync(local.fileno())
                local_temps.append(local.name)
                attempted_stages.add(relative)
                files.upload(local.name, staged[relative])
            uploaded = _read_remote_bytes(files, staged[relative], maximum=MAX_FILE_BYTES)
            if hashlib.sha256(uploaded).hexdigest() != hashlib.sha256(changed[relative].to_bytes()).hexdigest():
                raise IOError(f"staged upload hash mismatch for {relative}")

        for relative, target in targets.items():
            current = _read_remote_bytes(files, str(target), maximum=MAX_FILE_BYTES)
            if hashlib.sha256(current).hexdigest() != changed[relative].expected_sha256:
                raise SaveConflictError(f"remote file changed during save preparation: {relative}")
        for relative, target in targets.items():
            attempted_backups.add(relative)
            files.rename(str(target), backups[relative])
            swapped.append(relative)
            files.rename(staged[relative], str(target))
        cleanup_errors: list[str] = []
        for relative in swapped:
            try:
                files.remove(backups[relative])
            except Exception as exc:
                cleanup_errors.append(f"backup retained at {backups[relative]}: {exc}")
        for relative, document in changed.items():
            document.mark_saved(document.to_bytes())
        return SaveReport(True, False, tuple(targets), errors=tuple(cleanup_errors), recovery_paths=tuple(backups[name] for name in swapped if files.exists(backups[name])))
    except SaveConflictError as exc:
        recovery_paths = tuple(staged[name] for name in sorted(attempted_stages))
        preserve_recovery_artifacts = bool(recovery_paths)
        return SaveReport(
            False,
            False,
            (),
            conflicts=(str(exc),),
            recovery_paths=recovery_paths,
        )
    except Exception as exc:
        errors = [str(exc)]
        recovery: list[str] = []
        for relative in reversed(swapped):
            target = str(remote_root.joinpath(*PurePosixPath(relative).parts))
            backup = backups.get(relative)
            try:
                if files.exists(target):
                    files.remove(target)
                if backup and files.exists(backup):
                    files.rename(backup, target)
            except Exception as rollback_error:
                errors.append(f"rollback failed for {relative}: {rollback_error}")
                if backup:
                    recovery.append(backup)
        for relative in sorted(attempted_backups):
            recovery.append(backups[relative])
        for relative in sorted(attempted_stages):
            recovery.append(staged[relative])
        recovery_paths = tuple(dict.fromkeys(recovery))
        preserve_recovery_artifacts = bool(recovery_paths)
        return SaveReport(
            False,
            bool(swapped or recovery_paths),
            (),
            errors=tuple(errors),
            recovery_paths=recovery_paths,
        )
    finally:
        for temporary in local_temps:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass
        if not preserve_recovery_artifacts:
            for stage in staged.values():
                try:
                    if files.exists(stage):
                        files.remove(stage)
                except Exception:
                    pass


def recover_remote_case(root: str, files, recovery_paths, documents=None) -> SaveReport:
    """Restore interrupted remote saves without replacing a newer target."""
    remote_root = _root_path(root)
    groups: dict[str, dict[str, str]] = {}
    tokens: dict[str, str] = {}
    errors: list[str] = []
    conflicts: list[str] = []
    for raw_path in recovery_paths:
        artifact = PurePosixPath(str(raw_path))
        inside = _inside(remote_root, artifact) and artifact != remote_root
        match = _RECOVERY_NAME.fullmatch(artifact.name)
        if not inside or not match:
            errors.append(f"unsafe remote recovery path: {raw_path}")
            continue
        relative_target = artifact.with_name(match.group("name")).relative_to(remote_root).as_posix()
        if not safe_relative_path(relative_target):
            errors.append(f"unsafe remote recovery target: {relative_target}")
            continue
        token = match.group("token")
        if relative_target in tokens and tokens[relative_target] != token:
            errors.append(f"recovery artifacts use different tokens for {relative_target}")
            continue
        tokens[relative_target] = token
        group = groups.setdefault(relative_target, {})
        kind = match.group("kind")
        if kind in group and group[kind] != str(artifact):
            errors.append(f"duplicate remote recovery {kind} path for {relative_target}")
            continue
        group[kind] = str(artifact)

    if errors:
        return SaveReport(False, False, (), errors=tuple(errors))

    saved: list[str] = []
    remaining: list[str] = []
    for relative, artifacts in groups.items():
        target = str(remote_root.joinpath(*PurePosixPath(relative).parts))
        backup = artifacts.get("backup")
        stage = artifacts.get("stage")
        document = (documents or {}).get(relative)
        try:
            has_backup = bool(backup and files.exists(backup))
            has_target = files.exists(target)
            if has_target:
                target_payload = _read_remote_bytes(files, target, maximum=MAX_FILE_BYTES)
                expected_payload = document.to_bytes() if document is not None else None
                target_matches_editor = (
                    expected_payload is not None
                    and hashlib.sha256(target_payload).digest() == hashlib.sha256(expected_payload).digest()
                )
                if has_backup and not target_matches_editor:
                    conflicts.append(f"remote target exists; preserved backup for {relative}")
                    remaining.extend(artifacts.values())
                    continue
                if target_matches_editor:
                    document.mark_saved(target_payload)
                    saved.append(relative)
                    if backup and files.exists(backup):
                        files.remove(backup)
                    if stage and files.exists(stage):
                        files.remove(stage)
                    continue
            if has_backup:
                files.rename(backup, target)
                saved.append(relative)
            elif not has_target:
                errors.append(f"remote target and recovery backup are both missing for {relative}")
                remaining.extend(artifacts.values())
                continue
            if stage and files.exists(stage):
                files.remove(stage)
        except Exception as exc:
            errors.append(f"recovery failed for {relative}: {exc}")
            remaining.extend(artifacts.values())

    return SaveReport(
        not errors and not conflicts,
        bool(saved and remaining),
        tuple(saved),
        conflicts=tuple(conflicts),
        errors=tuple(errors),
        recovery_paths=tuple(dict.fromkeys(remaining)),
    )
