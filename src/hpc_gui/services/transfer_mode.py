from __future__ import annotations

import os
import inspect
import tempfile
from pathlib import Path

from .transfer_resume_store import (
    local_file_identity,
    progress_with_resume_checkpoints,
    transfer_record_key,
    transfer_resume_store_for_backend,
)


# Re-export mode helpers from the focused text-conversion module for callers.
from .transfer_text_mode import (
    ASCII,
    AUTO as AUTO,
    BINARY,
    CHUNK_SIZE,
    TRANSFER_MODES as TRANSFER_MODES,
    TEXT_EXTENSIONS as TEXT_EXTENSIONS,
    _ASCII_INVALID as _ASCII_INVALID,
    _ascii_bytes_for_local as _ascii_bytes_for_local,
    _ascii_bytes_for_remote as _ascii_bytes_for_remote,
    _flush_normalized_lines as _flush_normalized_lines,
    _is_utf8_prefix as _is_utf8_prefix,
    _stream_utf8_lines,
    _utf8_carry_split as _utf8_carry_split,
    is_known_text_path as is_known_text_path,
    looks_binary as looks_binary,
    normalize_transfer_mode,
    resolve_transfer_mode,
)

# The planner offers this partial to the user after cancellation.
PARTIAL_SUFFIX = ".part"


def _upload_remote(
    files,
    local_path: str,
    remote_path: str,
    progress_cb=None,
    resume_identity=None,
    resume_registry=None,
) -> None:
    """Upload to a server-side ``<remote>.part`` and rename once when the
    backend can rename; otherwise upload directly to the final name.

    The ``.part`` name keeps a partially uploaded file from shadowing the
    destination and still lets rename-capable backends resume against the
    same server-side partial on a retry.
    """
    rename = getattr(files, "rename", None)
    if not callable(rename):
        _upload_file(files, local_path, remote_path, progress_cb=progress_cb)
        return
    temp_remote = remote_path + PARTIAL_SUFFIX
    meta_remote = temp_remote + ".meta"
    source = Path(local_path).stat()
    identity = resume_identity or {
        "direction": "upload",
        "path": str(remote_path),
        "size": source.st_size,
        "mtime_ns": source.st_mtime_ns,
    }
    registry = resume_registry
    key = transfer_record_key("upload", remote_path)
    record = registry.get(key) if registry else None
    resume = False
    complete = False
    partial_size = 0
    try:
        # Remove sidecars created by older releases; resume identity now lives
        # in the encrypted application profile store.
        try:
            if files.exists(meta_remote):
                files.remove(meta_remote)
        except Exception:
            pass
        if files.exists(temp_remote):
            resume = bool(
                registry
                and record
                and record.get("identity") == identity
                and record.get("partial_path") == temp_remote
            )
            if resume:
                try:
                    partial_size, _mtime = files.stat(temp_remote)
                    resume = 0 < partial_size <= source.st_size
                    complete = resume and partial_size == source.st_size
                except Exception:
                    resume = False
            if not resume:
                files.remove(temp_remote)
        if registry:
            try:
                registry.save(key, identity, temp_remote, partial_size if resume else 0)
            except Exception:
                registry = None
                if resume:
                    files.remove(temp_remote)
                resume = complete = False
    except (AttributeError, NotImplementedError):
        registry = None
        resume = complete = False
    try:
        if not complete:
            tracked_progress = progress_with_resume_checkpoints(
                registry, key, identity, temp_remote, progress_cb
            )
            _upload_file(files, local_path, temp_remote, progress_cb=tracked_progress, resume=resume)
    except Exception:
        if registry:
            try:
                partial_size, _mtime = files.stat(temp_remote)
                registry.save(key, identity, temp_remote, partial_size)
            except Exception:
                pass
        raise
    rename(temp_remote, remote_path)
    if registry:
        try:
            registry.remove(key)
        except Exception:
            pass


def _upload_file(files, local_path: str, remote_path: str, progress_cb=None, *, resume: bool = False) -> None:
    method = getattr(files, "resume_upload", None) if resume else None
    if not callable(method):
        method = files.upload
    try:
        signature = inspect.signature(method)
        if "progress_cb" in signature.parameters:
            method(local_path, remote_path, progress_cb=progress_cb)
            return
    except (TypeError, ValueError):
        pass
    method(local_path, remote_path)


def upload_with_mode(
    files,
    local_path: str,
    remote_path: str,
    requested: str,
    progress_cb=None,
) -> str:
    with open(local_path, "rb") as source:
        sample = source.read(CHUNK_SIZE)
    effective = resolve_transfer_mode(local_path, requested, sample)
    resume_registry = (
        transfer_resume_store_for_backend(files)
        if callable(getattr(files, "rename", None))
        else None
    )
    source_identity = local_file_identity(local_path) if resume_registry else {}
    resume_identity = {
        "direction": "upload",
        "remote_path": str(remote_path),
        **source_identity,
        "mode": effective,
    }
    if effective == BINARY:
        _upload_remote(
            files,
            local_path,
            remote_path,
            progress_cb=progress_cb,
            resume_identity=resume_identity,
            resume_registry=resume_registry,
        )
        return effective
    # ASCII conversion streams the source so its line endings can be
    # normalized before the backend upload without ever materializing the
    # whole file in memory.
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp_path = temp.name
        _stream_utf8_lines(local_path, temp_path, "\n")
        _upload_remote(
            files,
            temp_path,
            remote_path,
            progress_cb=progress_cb,
            resume_identity=resume_identity,
            resume_registry=resume_registry,
        )
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    return effective


def _download_file(files, remote_path: str, local_path: str, progress_cb=None, *, resume: bool = False) -> None:
    method = getattr(files, "resume_download", None) if resume else None
    if not callable(method):
        method = files.download
    try:
        signature = inspect.signature(method)
        if "progress_cb" in signature.parameters:
            method(remote_path, local_path, progress_cb=progress_cb)
            return
    except (TypeError, ValueError):
        pass
    method(remote_path, local_path)


def download_with_mode(
    files,
    remote_path: str,
    local_path: str,
    requested: str,
    progress_cb=None,
) -> str:
    destination = Path(local_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    part_path = Path(str(destination) + PARTIAL_SUFFIX)
    meta_path = Path(str(part_path) + ".meta")
    # Persist only identity and byte offset in encrypted per-profile app data.
    # The adjacent .part contains transfer bytes; no metadata sidecar is used.
    resume = False
    complete = False
    partial_size = 0
    registry = transfer_resume_store_for_backend(files)
    remote_stat = getattr(files, "stat", None)
    if callable(remote_stat):
        remote_size, remote_mtime = remote_stat(remote_path)
        identity = {
            "direction": "download",
            "remote_path": str(remote_path),
            "local_path": str(destination.expanduser().resolve()),
            "size": remote_size,
            "mtime": remote_mtime,
            "mode": normalize_transfer_mode(requested),
        }
        part_identity = str(part_path.resolve())
        key = transfer_record_key("download", str(destination))
        record = registry.get(key) if registry else None
        try:
            meta_path.unlink(missing_ok=True)
        except OSError:
            pass
        if part_path.exists():
            resume = bool(
                registry
                and record
                and record.get("identity") == identity
                and record.get("partial_path") == part_identity
            )
            if resume:
                partial_size = part_path.stat().st_size
                resume = 0 < partial_size <= remote_size
                complete = resume and partial_size == remote_size
            if not resume:
                part_path.unlink(missing_ok=True)
        if registry:
            try:
                registry.save(
                    key, identity, part_identity,
                    part_path.stat().st_size if resume else 0,
                )
            except Exception:
                registry = None
                resume = complete = False
                part_path.unlink(missing_ok=True)
    else:
        identity = {
            "direction": "download",
            "remote_path": str(remote_path),
            "local_path": str(destination.expanduser().resolve()),
            "mode": normalize_transfer_mode(requested),
        }
        part_identity = str(part_path.resolve())
        key = transfer_record_key("download", str(destination))
        try:
            meta_path.unlink(missing_ok=True)
            if part_path.exists():
                part_path.unlink()
        except OSError:
            pass
        if registry:
            try:
                registry.save(key, identity, part_identity, 0)
            except Exception:
                registry = None
    try:
        if not complete:
            tracked_progress = progress_with_resume_checkpoints(
                registry, key, identity, part_identity, progress_cb
            )
            _download_file(files, remote_path, str(part_path), progress_cb=tracked_progress, resume=resume)
    except Exception:
        if registry:
            try:
                registry.save(key, identity, part_identity, part_path.stat().st_size)
            except Exception:
                pass
        raise
    try:
        with open(part_path, "rb") as stream:
            sample = stream.read(CHUNK_SIZE)
    except OSError:
        sample = b""
    effective = resolve_transfer_mode(remote_path, requested, sample)
    if effective == ASCII:
        converted_path = Path(str(destination) + ".tmp")
        try:
            _stream_utf8_lines(str(part_path), str(converted_path), os.linesep)
            os.replace(converted_path, destination)
        finally:
            try:
                converted_path.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            part_path.unlink(missing_ok=True)
        except OSError:
            pass
    else:
        os.replace(part_path, destination)
    if registry:
        try:
            registry.remove(key)
        except Exception:
            pass
    return effective
