"""Bounded local and remote case-file discovery (W65 LINT-COMPAT).

Read-only, fail-closed scans. Local walks reject symlinks on every path
component and enforce per-file/total byte and file-count budgets before
and during reads. Remote scans use the same budgets against an SFTP-like
adapter and never execute remote content.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
import stat as _stat

from hpc_gui.openfoam_core.limits import (
    MAX_CASE_BYTES,
    MAX_CASE_FILES,
    MAX_DICTIONARY_BYTES,
    MAX_MESH_BOUNDARY_BYTES,
    MAX_REMOTE_CASE_BYTES,
    MAX_REMOTE_CASE_DEPTH,
    MAX_REMOTE_CASE_FILES,
    MAX_REMOTE_DICTIONARY_BYTES,
    REMOTE_CASE_SKIP_DIRS,
)
from hpc_gui.openfoam_core.paths import (
    is_dictionary_name,
    is_mesh_boundary_path,
    safe_relative_path,
)
from hpc_gui.openfoam_core.local_paths import require_local_path_without_links
from hpc_gui.openfoam_core.remote_paths import remote_lstat_entry, require_remote_directory, require_remote_regular_file
from hpc_gui.openfoam_core.cancellation import raise_if_cancelled

_SCAN_ROOTS = ("system", "constant", "0", "0.orig")


@dataclass(frozen=True, slots=True)
class DiscoveredFile:
    relative_path: str
    absolute_path: Path
    data: bytes


@dataclass(frozen=True, slots=True)
class FilePayload:
    relative_path: str
    absolute_path: Path
    data: bytes


def _check_budget(total: int, count: int) -> None:
    if count > MAX_CASE_FILES:
        raise ValueError("case scan exceeds the file-count limit")
    if total > MAX_CASE_BYTES:
        raise ValueError("case scan exceeds the case-bytes limit")


def _read_regular_bounded(path: Path, maximum: int, *, label: str) -> bytes:
    """Read a regular non-link file with an in-stream byte ceiling."""
    try:
        if path.is_symlink() or (callable(getattr(path, "is_junction", None)) and path.is_junction()):
            raise ValueError(f"{label} is a symbolic link or junction")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not _stat.S_ISREG(before.st_mode):
                raise ValueError(f"{label} is not a regular file")
            if before.st_size > maximum:
                raise ValueError(f"{label} exceeds the size limit")
            data = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
            ):
                raise ValueError(f"{label} changed while it was being read")
    except OSError as exc:
        raise ValueError(f"{label} could not be read") from exc
    if len(data) > maximum:
        raise ValueError(f"{label} exceeds the size limit")
    return data


def _safe_join(root: Path, relative: str) -> Path | None:
    if not safe_relative_path(relative):
        return None
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    try:
        cursor = candidate
        while cursor != root:
            if cursor.is_symlink():
                return None
            cursor = cursor.parent
        resolved = candidate.resolve(strict=True)
    except OSError:
        return None
    if root not in resolved.parents:
        return None
    return candidate


def discover_case_files(root: str | Path, *, cancel_event=None) -> list[DiscoveredFile]:
    """Collect bounded dictionary payloads under a local case root."""
    base = require_local_path_without_links(root).resolve(strict=True)
    if not base.is_dir():
        raise ValueError("case root is not a directory")
    found: list[DiscoveredFile] = []
    total = 0
    for anchor in _SCAN_ROOTS:
        raise_if_cancelled(cancel_event)
        top = base / anchor
        if top.is_symlink() or not top.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(top, followlinks=False):
            raise_if_cancelled(cancel_event)
            current = Path(dirpath)
            if current.is_symlink():
                dirnames[:] = []
                continue
            dirnames[:] = sorted(
                name for name in dirnames
                if not (current / name).is_symlink() and not name.startswith(".")
            )
            for name in sorted(filenames):
                raise_if_cancelled(cancel_event)
                candidate = current / name
                try:
                    relative = candidate.resolve(strict=False).relative_to(base).as_posix()
                except ValueError:
                    continue
                if not safe_relative_path(relative) or not is_dictionary_name(relative):
                    continue
                if is_mesh_boundary_path(relative):
                    continue
                target = _safe_join(base, relative)
                if target is None or not target.is_file():
                    continue
                data = _read_regular_bounded(
                    target, MAX_DICTIONARY_BYTES, label=f"dictionary {relative}"
                )
                total += len(data)
                _check_budget(total, len(found) + 1)
                found.append(DiscoveredFile(relative, target, data))
    return found


def discover_mesh_boundaries(
    root: str | Path,
    *,
    maximum_case_bytes: int = MAX_CASE_BYTES,
    maximum_files: int = MAX_CASE_FILES,
    cancel_event=None,
) -> dict[str, bytes]:
    """Collect bounded ``polyMesh/boundary`` payloads keyed by relpath."""
    base = require_local_path_without_links(root).resolve(strict=True)
    if not base.is_dir():
        raise ValueError("case root is not a directory")
    out: dict[str, bytes] = {}
    total = 0
    for dirpath, dirnames, filenames in os.walk(base / "constant", followlinks=False):
        raise_if_cancelled(cancel_event)
        current = Path(dirpath)
        if current.is_symlink():
            dirnames[:] = []
            continue
        dirnames[:] = sorted(
            name for name in dirnames
            if not (current / name).is_symlink() and not name.startswith(".")
        )
        for name in sorted(filenames):
            raise_if_cancelled(cancel_event)
            candidate = current / name
            try:
                relative = candidate.resolve(strict=False).relative_to(base).as_posix()
            except ValueError:
                continue
            if not is_mesh_boundary_path(relative):
                continue
            target = _safe_join(base, relative)
            if target is None or not target.is_file():
                continue
            try:
                data = _read_regular_bounded(
                    target, MAX_MESH_BOUNDARY_BYTES, label=f"mesh boundary {relative}"
                )
            except (OSError, ValueError):
                continue
            if total + len(data) > maximum_case_bytes or len(out) + 1 > maximum_files:
                return out
            total += len(data)
            out[relative] = data
    return out


def read_dictionary_file(path: str | Path) -> FilePayload:
    """Read one dictionary with symlink and size guards."""
    target = require_local_path_without_links(path)
    if not target.is_file():
        raise ValueError("selected path is not a readable dictionary file")
    try:
        resolved = target.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"selected path could not be resolved: {exc}") from exc
    data = _read_regular_bounded(
        target, MAX_DICTIONARY_BYTES, label="dictionary"
    )
    cursor = resolved
    while cursor.parent != cursor:
        if cursor.is_symlink():
            raise ValueError("dictionary path traverses a symbolic link")
        cursor = cursor.parent
    return FilePayload(resolved.name, resolved, data)


def _remote_names(files: Any, directory: str) -> list[str]:
    entries = None
    for method in ("listdir_entries", "listdir"):
        lookup = getattr(files, method, None)
        if callable(lookup):
            try:
                entries = lookup(directory)
                break
            except (OSError, NotImplementedError):
                continue
    if entries is None:
        raise OSError(f"remote directory cannot be listed: {directory}")
    names: list[str] = []
    for entry in entries:
        name = getattr(entry, "name", entry)
        if isinstance(name, str) and name not in ("", ".", ".."):
            names.append(name)
    return sorted(names)


def remote_entry_names(
    files: Any, directory: str, *, maximum_entries: int | None = None,
) -> tuple[list[str], bool]:
    """Sorted names of one remote directory; the flag reports truncation."""
    names = _remote_names(files, directory)
    if maximum_entries is None or len(names) <= maximum_entries:
        return names, False
    return names[:maximum_entries], True


def _remote_read(files: Any, path: str, *, maximum: int) -> bytes:
    import tempfile

    try:
        require_remote_regular_file(files, path, maximum_bytes=maximum)
        entry = remote_lstat_entry(files, path)
    except OSError as exc:
        raise OSError(f"remote file cannot be safely stated: {path}") from exc
    except ValueError as exc:
        raise ValueError(f"remote file is not a safe regular file: {path}") from exc
    if int(getattr(entry, "size", 0) or 0) > maximum:
        raise ValueError("remote dictionary exceeds the size limit")
    with tempfile.TemporaryDirectory(prefix="hpc-openfoam-scan-") as directory:
        target = Path(directory) / "payload"
        files.download(path, str(target))
        data = target.read_bytes()
    if len(data) > maximum:
        raise ValueError("downloaded dictionary exceeds the size limit")
    return data


def _scan_remote(
    root: str,
    files: Any,
    *,
    want_mesh: bool,
    maximum_file_bytes: int,
    maximum_case_bytes: int,
    maximum_files: int,
    maximum_depth: int,
    skip_dirs: Any,
    cancel_event=None,
) -> dict[str, bytes]:
    if not isinstance(root, str) or not root.startswith("/") or ".." in PurePosixPath(root).parts:
        raise ValueError("remote case root must be a safe absolute POSIX path")
    require_remote_directory(files, root)
    skip = {str(name) for name in (skip_dirs or ())}
    out: dict[str, bytes] = {}
    total = 0
    queue: list[tuple[str, int]] = [(root.rstrip("/") or "/", 0)]
    seen = {queue[0][0]}
    while queue:
        raise_if_cancelled(cancel_event)
        directory, depth = queue.pop(0)
        if depth > maximum_depth:
            continue
        try:
            require_remote_directory(files, directory)
        except (OSError, ValueError):
            continue
        try:
            names = _remote_names(files, directory)
        except OSError:
            continue
        for name in names:
            raise_if_cancelled(cancel_event)
            if name.startswith(".") or name in skip:
                continue
            child = directory.rstrip("/") + "/" + name
            relative = PurePosixPath(child).relative_to(root.rstrip("/") or "/").as_posix()
            if not safe_relative_path(relative):
                continue
            try:
                mode = int(getattr(remote_lstat_entry(files, child), "mode", 0) or 0)
            except (OSError, ValueError):
                continue
            if _stat.S_ISLNK(mode):
                continue
            is_dir = _stat.S_ISDIR(mode)
            if not is_dir and not _stat.S_ISREG(mode):
                continue
            if is_dir:
                if child not in seen:
                    seen.add(child)
                    queue.append((child, depth + 1))
                continue
            matches = is_mesh_boundary_path(relative) if want_mesh else (
                is_dictionary_name(relative) and not is_mesh_boundary_path(relative)
            )
            if not matches:
                continue
            try:
                raise_if_cancelled(cancel_event)
                data = _remote_read(files, child, maximum=maximum_file_bytes)
            except (OSError, ValueError):
                continue
            raise_if_cancelled(cancel_event)
            if total + len(data) > maximum_case_bytes or len(out) + 1 > maximum_files:
                return out
            total += len(data)
            out[relative] = data
    return out


def scan_remote_dictionaries(
    root: str,
    files: Any,
    *,
    maximum_file_bytes: int = MAX_REMOTE_DICTIONARY_BYTES,
    maximum_case_bytes: int = MAX_REMOTE_CASE_BYTES,
    maximum_files: int = MAX_REMOTE_CASE_FILES,
    maximum_depth: int = MAX_REMOTE_CASE_DEPTH,
    skip_dirs: Any = REMOTE_CASE_SKIP_DIRS,
    cancel_event=None,
) -> dict[str, bytes]:
    """Bounded read-only remote dictionary scan keyed by case-relpath."""
    return _scan_remote(
        root, files, want_mesh=False,
        maximum_file_bytes=maximum_file_bytes,
        maximum_case_bytes=maximum_case_bytes,
        maximum_files=maximum_files,
        maximum_depth=maximum_depth,
        skip_dirs=skip_dirs,
        cancel_event=cancel_event,
    )


def scan_remote_mesh_boundaries(
    root: str,
    files: Any,
    *,
    maximum_case_bytes: int = MAX_REMOTE_CASE_BYTES,
    maximum_files: int = MAX_REMOTE_CASE_FILES,
    maximum_depth: int = MAX_REMOTE_CASE_DEPTH,
    skip_dirs: Any = REMOTE_CASE_SKIP_DIRS,
    cancel_event=None,
) -> dict[str, bytes]:
    """Bounded read-only remote mesh-boundary scan keyed by case-relpath."""
    return _scan_remote(
        root, files, want_mesh=True,
        maximum_file_bytes=MAX_REMOTE_DICTIONARY_BYTES,
        maximum_case_bytes=maximum_case_bytes,
        maximum_files=maximum_files,
        maximum_depth=maximum_depth,
        skip_dirs=skip_dirs,
        cancel_event=cancel_event,
    )
