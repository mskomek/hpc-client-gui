"""Create-only, verified storage for generated case-local OpenFOAM scripts."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import tempfile
import uuid

from hpc_gui.openfoam_core.remote_paths import remote_lstat_entry, require_remote_directory, require_remote_regular_file
from hpc_gui.openfoam_core.local_paths import require_local_path_without_links


MAX_SCRIPT_BYTES = 1024 * 1024


def create_local_allrun(root: str, content: str) -> str:
    payload = _payload(content)
    case_root = require_local_path_without_links(root).resolve(strict=True)
    if not case_root.is_dir():
        raise ValueError("case root is not a directory")
    target = case_root / "Allrun"
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


def create_remote_allrun(root: str, files, content: str) -> str:
    payload = _payload(content)
    case_root = _remote_root(root)
    if not files.is_dir(str(case_root)):
        raise ValueError("remote case root is not a directory")
    require_remote_directory(files, str(case_root))
    rename_noreplace = getattr(files, "rename_noreplace", None)
    upload_exclusive = getattr(files, "upload_exclusive", None)
    if not callable(rename_noreplace) or not callable(upload_exclusive):
        raise NotImplementedError("remote backend lacks exclusive upload/no-replace rename required for Allrun")
    target = case_root / "Allrun"
    try:
        remote_lstat_entry(files, str(target))
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError("Allrun already exists in the case; preserve or rename it before generating another")

    token = uuid.uuid4().hex
    stage = target.with_name(f".Allrun.{token}.stage")
    expected = hashlib.sha256(payload).digest()
    with tempfile.TemporaryDirectory(prefix="hpc-openfoam-allrun-") as directory:
        local_source = Path(directory) / "Allrun"
        local_check = Path(directory) / "verify"
        local_source.write_bytes(payload)
        try:
            upload_exclusive(str(local_source), str(stage))
            files.download(str(stage), str(local_check))
            if hashlib.sha256(local_check.read_bytes()).digest() != expected:
                raise IOError("uploaded Allrun failed SHA-256 verification")
            if files.exists(str(target)):
                raise FileExistsError("Allrun appeared in the case while generating the script")
            rename_noreplace(str(stage), str(target))
        except Exception as exc:
            # Avoid deleting an ambiguous pathname on a remote account. The
            # unique stage is left available for explicit recovery/inspection.
            try:
                exc.add_note(f"Any staged bytes were preserved for inspection at {stage}")
            except Exception:
                pass
            raise
    return str(target)


def _payload(content: str) -> bytes:
    if not isinstance(content, str):
        raise TypeError("Allrun content must be text")
    payload = content.encode("utf-8")
    if not payload or len(payload) > MAX_SCRIPT_BYTES:
        raise ValueError("Allrun content is empty or exceeds the configured size limit")
    return payload


def _remote_root(value: str) -> PurePosixPath:
    root = PurePosixPath(value)
    if not root.is_absolute() or ".." in root.parts:
        raise ValueError("remote case root must be an absolute safe POSIX path")
    return root


def remote_allrun_matches(root: str, files, expected_sha256: str) -> bool:
    """Compare bounded bytes only after lstat has rejected links/non-files."""
    case_root = _remote_root(root)
    target = case_root / "Allrun"
    try:
        require_remote_regular_file(files, str(target), maximum_bytes=MAX_SCRIPT_BYTES)
    except Exception:
        return False
    with tempfile.TemporaryDirectory(prefix="hpc-openfoam-allrun-check-") as directory:
        local_copy = Path(directory) / "Allrun"
        try:
            files.download(str(target), str(local_copy))
            data = local_copy.read_bytes()
        except Exception:
            return False
        if len(data) > MAX_SCRIPT_BYTES:
            return False
        return hashlib.sha256(data).hexdigest() == expected_sha256
