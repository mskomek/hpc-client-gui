"""Mode-aware execution for the native file queue, independent of GUI toolkit."""
from __future__ import annotations

from pathlib import Path
import os
import posixpath
import stat
from contextlib import contextmanager
from threading import Lock

from hpc_gui.services.transfer_conflict_policy import conflict_target, destination_exists
from hpc_gui.services.transfer_mode import (
    BINARY, CHUNK_SIZE, download_with_mode, is_known_text_path,
    normalize_transfer_mode, resolve_transfer_mode, upload_with_mode,
)


_RESERVATION_LOCK = Lock()
_RESERVED = set()


def _path_key(direction, destination):
    if direction == "download":
        return os.path.normcase(os.path.abspath(destination))
    return posixpath.normpath(destination)


def validate_staging_paths(items):
    """Reject plans whose real targets alias another item's staging name."""
    claimed = set()
    partials = set()
    for item in items:
        if item.op not in {"upload", "download", "mkdir_local", "mkdir_remote"}:
            continue
        direction = "download" if item.op in {"download", "mkdir_local"} else "upload"
        key = (direction, _path_key(direction, item.dst))
        if key in claimed or key in partials:
            raise ValueError(f"Overlapping transfer destination: {item.dst}")
        claimed.add(key)
        if item.op in {"upload", "download"}:
            partial = (direction, _path_key(direction, item.dst + ".part"))
            if partial in claimed or partial in partials:
                raise ValueError(f"Transfer staging path overlaps a destination: {item.dst}")
            partials.add(partial)


@contextmanager
def reserve_transfer_paths(owner, item):
    """Never let two active same-session transfers share final/partial paths."""
    if item.op not in {"upload", "download"}:
        yield
        return
    namespace = id(owner) if item.op == "upload" else None
    keys = {(namespace, item.op, _path_key(item.op, item.dst + suffix))
            for suffix in ("", ".part")}
    with _RESERVATION_LOCK:
        if _RESERVED.intersection(keys):
            raise RuntimeError(f"Another transfer owns {item.dst} or its partial")
        _RESERVED.update(keys)
    try:
        yield
    finally:
        with _RESERVATION_LOCK:
            _RESERVED.difference_update(keys)


def _reject_remote_partial_symlink(files, path):
    lstat = getattr(files, "lstat_entry", None)
    if not callable(lstat):
        return
    try:
        entry = lstat(path)
    except FileNotFoundError:
        return
    mode = stat.S_IFMT(int(getattr(entry, "mode", 0) or 0))
    if mode not in (0, stat.S_IFREG):
        raise ValueError(f"Unsafe remote transfer partial: {path}")


def execute_with_mode(files, item, progress, requested, decision, raw_transfer, *, verify_bytes=None):
    """Stage new files; preserve explicitly approved raw final-file resume.

    Standard SFTP rename cannot replace a destination. An approved overwrite
    uses the existing direct backend contract rather than delete+rename.
    """
    requested = normalize_transfer_mode(requested)
    final_exists = destination_exists(files, item.op, item.dst)
    if final_exists and decision == "resume":
        if item.op == "download" and Path(item.dst).is_symlink():
            raise ValueError("Refusing to resume into a local symlink")
        if item.op == "upload":
            with open(item.src, "rb") as stream:
                effective = resolve_transfer_mode(item.src, requested, stream.read(CHUNK_SIZE))
        else:
            effective = requested
            if requested == "auto" and not is_known_text_path(item.src):
                effective = BINARY
        if effective != BINARY:
            raise ValueError("Resume of an existing final file requires Binary mode")
        raw_transfer(files, item, progress, conflict_decision="resume")
        if verify_bytes is not None:
            local, remote = (item.src, item.dst) if item.op == "upload" else (item.dst, item.src)
            verify_bytes(local, remote)
        return BINARY

    if final_exists and decision != "overwrite":
        raise FileExistsError(item.dst)

    if not final_exists:
        if item.op == "upload":
            _reject_remote_partial_symlink(files, item.dst + ".part")
        target = conflict_target(files, item.op, item.dst, include_partial=True)
        if target is not None and decision not in {"resume", "overwrite"}:
            raise FileExistsError(target)
    allow_resume = decision == "resume"
    if item.op == "upload":
        return upload_with_mode(
            files, item.src, item.dst, requested, progress_cb=progress,
            allow_resume=allow_resume, stage_remote=not final_exists, verify_bytes=verify_bytes,
            require_valid_resume=allow_resume, cleanup_legacy_metadata=False,
        )
    if item.op == "download":
        return download_with_mode(
            files, item.src, item.dst, requested, progress_cb=progress,
            allow_resume=allow_resume, verify_bytes=verify_bytes,
            require_valid_resume=allow_resume, cleanup_legacy_metadata=False,
        )
    raise ValueError(f"Unsupported transfer mode operation: {item.op}")
