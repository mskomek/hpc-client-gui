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
    *, allow_resume: bool = True, stage_remote: bool = True, verify_bytes=None,
    require_valid_resume: bool = False, cleanup_legacy_metadata: bool = True,
    atomic_overwrite: bool = False, no_replace: bool = False,
) -> None:
    """Upload to a server-side ``<remote>.part`` and rename once when the
    backend can rename; otherwise upload directly to the final name.

    The ``.part`` name keeps a partially uploaded file from shadowing the
    destination and still lets rename-capable backends resume against the
    same server-side partial on a retry.
    """
    atomic_replace = getattr(files, "atomic_replace_upload", None)
    if atomic_overwrite and callable(atomic_replace):
        atomic_replace(local_path, remote_path, progress_cb=progress_cb, verify_bytes=verify_bytes)
        return
    rename = getattr(files, "rename", None)
    if not stage_remote or not callable(rename):
        if no_replace:
            raise ValueError("Backend cannot stage a renamed upload")
        if require_valid_resume:
            raise ValueError("Backend cannot resume a staged upload")
        _upload_file(files, local_path, remote_path, progress_cb=progress_cb)
        if verify_bytes is not None:
            verify_bytes(local_path, remote_path)
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
        if cleanup_legacy_metadata:
            try:
                if files.exists(meta_remote):
                    files.remove(meta_remote)
            except Exception:
                pass
        if files.exists(temp_remote):
            if no_replace:
                raise FileExistsError(temp_remote)
            resume = bool(
                allow_resume
                and registry
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
                if require_valid_resume:
                    raise ValueError("Upload partial identity does not match; choose Overwrite to restart")
                files.remove(temp_remote)
        elif require_valid_resume:
            raise FileNotFoundError(temp_remote)
        if registry:
            try:
                registry.save(key, identity, temp_remote, partial_size if resume else 0)
            except Exception:
                if require_valid_resume:
                    raise
                registry = None
                if resume:
                    files.remove(temp_remote)
                resume = complete = False
    except (AttributeError, NotImplementedError):
        if require_valid_resume:
            raise
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
    if verify_bytes is not None:
        try:
            verify_bytes(local_path, temp_remote)
        except Exception:
            if registry:
                try:
                    registry.remove(key)
                except Exception:
                    pass
            raise
    if no_replace and files.exists(remote_path):
        raise FileExistsError(remote_path)
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
    except (TypeError, ValueError):
        signature = None
    if signature is not None and "progress_cb" in signature.parameters:
        method(local_path, remote_path, progress_cb=progress_cb)
    else:
        method(local_path, remote_path)


def upload_with_mode(
    files,
    local_path: str,
    remote_path: str,
    requested: str,
    progress_cb=None,
    *, allow_resume: bool = True, stage_remote: bool = True, verify_bytes=None,
    require_valid_resume: bool = False, cleanup_legacy_metadata: bool = True,
    atomic_overwrite: bool = False, no_replace: bool = False,
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
            allow_resume=allow_resume, stage_remote=stage_remote, verify_bytes=verify_bytes,
            require_valid_resume=require_valid_resume, cleanup_legacy_metadata=cleanup_legacy_metadata,
            atomic_overwrite=atomic_overwrite, no_replace=no_replace,
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
            allow_resume=allow_resume, stage_remote=stage_remote, verify_bytes=verify_bytes,
            require_valid_resume=require_valid_resume, cleanup_legacy_metadata=cleanup_legacy_metadata,
            atomic_overwrite=atomic_overwrite, no_replace=no_replace,
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
    except (TypeError, ValueError):
        signature = None
    if signature is not None and "progress_cb" in signature.parameters:
        method(remote_path, local_path, progress_cb=progress_cb)
    else:
        method(remote_path, local_path)


def _publish_download(source: Path, destination: Path, *, no_replace: bool) -> None:
    if no_replace:
        # Atomic create-if-absent on the same filesystem. Do not fall back
        # to replace() if hard links are unsupported or the name was taken.
        os.link(source, destination)
        source.unlink()
    else:
        os.replace(source, destination)


def download_with_mode(
    files,
    remote_path: str,
    local_path: str,
    requested: str,
    progress_cb=None,
    *, allow_resume: bool = True, verify_bytes=None,
    require_valid_resume: bool = False, cleanup_legacy_metadata: bool = True,
    no_replace: bool = False,
) -> str:
    destination = Path(local_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    part_path = Path(str(destination) + PARTIAL_SUFFIX)
    if part_path.is_symlink():
        raise ValueError(f"Refusing symlink as transfer partial: {part_path}")
    if no_replace and (part_path.exists() or destination.exists() or destination.is_symlink()):
        raise FileExistsError(str(destination))
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
        if cleanup_legacy_metadata:
            try:
                meta_path.unlink(missing_ok=True)
            except OSError:
                pass
        if part_path.exists():
            if no_replace:
                raise FileExistsError(str(part_path))
            resume = bool(
                allow_resume
                and registry
                and record
                and record.get("identity") == identity
                and record.get("partial_path") == part_identity
            )
            if resume:
                partial_size = part_path.stat().st_size
                resume = 0 < partial_size <= remote_size
                complete = resume and partial_size == remote_size
            if not resume:
                if require_valid_resume:
                    raise ValueError("Download partial identity does not match; choose Overwrite to restart")
                part_path.unlink(missing_ok=True)
        elif require_valid_resume:
            raise FileNotFoundError(str(part_path))
        if registry:
            try:
                registry.save(
                    key, identity, part_identity,
                    part_path.stat().st_size if resume else 0,
                )
            except Exception:
                if require_valid_resume:
                    raise
                registry = None
                resume = complete = False
                part_path.unlink(missing_ok=True)
    else:
        if require_valid_resume:
            raise ValueError("Remote metadata is unavailable for safe resume")
        identity = {
            "direction": "download",
            "remote_path": str(remote_path),
            "local_path": str(destination.expanduser().resolve()),
            "mode": normalize_transfer_mode(requested),
        }
        part_identity = str(part_path.resolve())
        key = transfer_record_key("download", str(destination))
        try:
            if cleanup_legacy_metadata:
                meta_path.unlink(missing_ok=True)
            if part_path.exists():
                if no_replace:
                    raise FileExistsError(str(part_path))
                part_path.unlink()
        except FileExistsError:
            raise
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
    if verify_bytes is not None:
        try:
            verify_bytes(str(part_path), remote_path)
        except Exception:
            if registry:
                try:
                    registry.remove(key)
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
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".hpc-convert-", delete=False) as temp:
            converted_path = Path(temp.name)
        try:
            _stream_utf8_lines(str(part_path), str(converted_path), os.linesep)
            _publish_download(converted_path, destination, no_replace=no_replace)
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
        _publish_download(part_path, destination, no_replace=no_replace)
    if registry:
        try:
            registry.remove(key)
        except Exception:
            pass
    return effective
