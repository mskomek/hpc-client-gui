"""Fail-closed SFTP path metadata helpers for OpenFOAM case operations."""

from __future__ import annotations

import stat
from pathlib import PurePosixPath
from typing import Any


def remote_lstat_entry(files: Any, path: str):
    """Read an SFTP path entry without following its final symlink."""
    probe = getattr(files, "lstat_entry", None)
    if not callable(probe):
        raise ValueError("remote backend cannot inspect paths without following symbolic links")
    try:
        return probe(path)
    except NotImplementedError as exc:
        raise ValueError("remote backend cannot inspect paths without following symbolic links") from exc


def require_remote_directory(files: Any, root: str) -> None:
    """Require each component of an absolute remote directory to be a real directory."""
    path = PurePosixPath(root)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("remote directory must be an absolute safe POSIX path")
    current = PurePosixPath("/")
    parts = tuple(part for part in path.parts if part != "/")
    for part in (None, *parts):
        if part is not None:
            current = current / part
        entry = remote_lstat_entry(files, str(current))
        mode = int(getattr(entry, "mode", 0) or 0)
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise ValueError(f"remote case path traverses a link or non-directory: {current}")


def require_remote_regular_file(files: Any, path: str, *, maximum_bytes: int) -> None:
    """Require a bounded regular remote file whose parent path is link-free."""
    target = PurePosixPath(path)
    if not target.is_absolute() or ".." in target.parts:
        raise ValueError("remote file must use an absolute safe POSIX path")
    require_remote_directory(files, str(target.parent))
    entry = remote_lstat_entry(files, str(target))
    mode = int(getattr(entry, "mode", 0) or 0)
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise ValueError(f"remote path is not a regular non-link file: {target}")
    if int(getattr(entry, "size", 0) or 0) > maximum_bytes:
        raise ValueError(f"remote file exceeds the configured byte limit: {target}")
