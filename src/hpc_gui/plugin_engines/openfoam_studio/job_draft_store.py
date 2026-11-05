"""Create-only, verified storage for generated Slurm job wrappers.

Mirrors the Allrun store: existing files are preserved, symlink targets
are refused, payloads are size-bounded, and remote staged bytes are
hash-verified before rename. Failures report recovery paths clearly.
"""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import uuid
from pathlib import Path, PurePosixPath

from hpc_gui.openfoam_core.remote_paths import (
    remote_lstat_entry,
    require_remote_directory,
    require_remote_regular_file,
)
from hpc_gui.openfoam_core.local_paths import require_local_path_without_links
from .run_script_store import MAX_SCRIPT_BYTES


MAX_JOB_BYTES = 256 * 1024
DEFAULT_JOB_FILENAME = "job.slurm"


def _payload(content: str) -> bytes:
    if not isinstance(content, str):
        raise TypeError("job wrapper content must be text")
    payload = content.encode("utf-8")
    if not payload or len(payload) > MAX_JOB_BYTES:
        raise ValueError("job wrapper content is empty or exceeds the configured size limit")
    return payload


def _safe_filename(name: str) -> str:
    if not isinstance(name, str):
        raise TypeError("job wrapper name must be text")
    clean = name.strip()
    if not clean or clean in {".", ".."}:
        raise ValueError("job wrapper name is unsafe")
    if "/" in clean or "\\" in clean or "\x00" in clean:
        raise ValueError("job wrapper name is unsafe")
    if Path(clean).name != clean or len(clean) > 128:
        raise ValueError("job wrapper name is unsafe")
    if clean.startswith("."):
        raise ValueError("job wrapper name is unsafe")
    return clean


def create_local_job(root: str, content: str, *, filename: str = DEFAULT_JOB_FILENAME) -> str:
    payload = _payload(content)
    leaf = _safe_filename(filename)
    case_root = require_local_path_without_links(root).resolve(strict=True)
    if not case_root.is_dir():
        raise ValueError("case root is not a directory")
    target = case_root / leaf
    if target.is_symlink() or target.exists():
        raise FileExistsError("job wrapper already exists; preserve or rename it before generating another")
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return str(target)


def create_remote_job(root: str, files, content: str, *, filename: str = DEFAULT_JOB_FILENAME) -> str:
    payload = _payload(content)
    leaf = _safe_filename(filename)
    case_root = _remote_root(root)
    if not files.is_dir(str(case_root)):
        raise ValueError("remote case root is not a directory")
    require_remote_directory(files, str(case_root))
    rename_noreplace = getattr(files, "rename_noreplace", None)
    upload_exclusive = getattr(files, "upload_exclusive", None)
    if not callable(rename_noreplace) or not callable(upload_exclusive):
        raise NotImplementedError("remote backend lacks exclusive upload/no-replace rename required for a job wrapper")
    target = case_root / leaf
    try:
        remote_lstat_entry(files, str(target))
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError("job wrapper already exists; preserve or rename it before generating another")
    token = uuid.uuid4().hex
    stage = target.with_name(f".{target.name}.{token}.stage")
    expected = hashlib.sha256(payload).digest()
    with tempfile.TemporaryDirectory(prefix="hpc-openfoam-job-") as directory:
        local_source = Path(directory) / leaf
        local_check = Path(directory) / "verify"
        local_source.write_bytes(payload)
        try:
            upload_exclusive(str(local_source), str(stage))
            files.download(str(stage), str(local_check))
            if hashlib.sha256(local_check.read_bytes()).digest() != expected:
                raise IOError("uploaded job wrapper failed SHA-256 verification")
            if files.exists(str(target)):
                raise FileExistsError("job wrapper appeared in the case while generating the script")
            rename_noreplace(str(stage), str(target))
        except Exception as exc:
            # Do not delete an ambiguous remote pathname: another writer may
            # have replaced a failed/partial stage. Leave it for recovery and
            # attach the exact path to the original failure.
            try:
                exc.add_note(f"Any staged bytes were preserved for inspection at {stage}")
            except Exception:
                pass
            raise
    return str(target)


def local_allrun_matches(root: str, expected_sha256: str) -> bool:
    try:
        case_root = require_local_path_without_links(root).resolve(strict=True)
        target = case_root / "Allrun"
        if target.is_symlink() or not target.is_file() or target.stat().st_size > MAX_SCRIPT_BYTES:
            return False
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(target, flags)
        with os.fdopen(descriptor, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_SCRIPT_BYTES:
                return False
            stream.seek(0)
            data = stream.read(MAX_SCRIPT_BYTES + 1)
        return len(data) <= MAX_SCRIPT_BYTES and hashlib.sha256(data).hexdigest() == expected_sha256
    except (OSError, ValueError):
        return False


def remote_allrun_matches(root: str, files, expected_sha256: str) -> bool:
    case_root = _remote_root(root)
    target = case_root / "Allrun"
    try:
        require_remote_regular_file(files, str(target), maximum_bytes=MAX_SCRIPT_BYTES)
    except Exception:
        return False
    with tempfile.TemporaryDirectory(prefix="hpc-openfoam-job-check-") as directory:
        local_copy = Path(directory) / "Allrun"
        try:
            files.download(str(target), str(local_copy))
        except Exception:
            return False
        data = local_copy.read_bytes()
        return len(data) <= MAX_SCRIPT_BYTES and hashlib.sha256(data).hexdigest() == expected_sha256


def allrun_matches(workspace, expected_sha256: str) -> bool:
    """True only when the on-disk Allrun bytes match the reviewed digest."""
    if workspace is None:
        return False
    try:
        if workspace.remote:
            if workspace.files is None:
                return False
            return remote_allrun_matches(workspace.root, workspace.files, expected_sha256)
        return local_allrun_matches(workspace.root, expected_sha256)
    except Exception:
        return False


def _remote_root(value: str) -> PurePosixPath:
    root = PurePosixPath(value)
    if not root.is_absolute() or ".." in root.parts:
        raise ValueError("remote case root must be an absolute safe POSIX path")
    return root
