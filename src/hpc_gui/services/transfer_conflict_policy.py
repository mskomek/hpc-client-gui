"""Process-session conflict choices shared by the Qt and wx file surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from threading import RLock
import os

_LOCK = RLock()
_SESSION_ACTION: tuple[str, bool] | None = None


def destination_path(direction: str, destination: str):
    """Interpret local downloads with host path rules, uploads with POSIX rules."""
    if direction == "download":
        return Path(destination)
    if direction == "upload":
        return PurePosixPath(destination)
    raise ValueError(f"Unsupported transfer direction: {direction}")


def rename_destination(direction: str, destination: str, name: str) -> str:
    """A rename must stay within the original destination directory."""
    if (
        not name or name in {".", ".."} or "/" in name or "\\" in name
        or "\x00" in name
        or (direction == "download" and os.name == "nt"
            and (PureWindowsPath(name).drive or ":" in name or name.endswith((".", " "))))
    ):
        raise ValueError("Invalid destination filename")
    return str(destination_path(direction, destination).with_name(name))


def destination_exists(files, direction: str, destination: str) -> bool:
    if direction == "download":
        try:
            os.lstat(destination)
        except FileNotFoundError:
            return False
        return True
    if direction == "upload":
        return bool(files.exists(destination))
    raise ValueError(f"Unsupported transfer direction: {direction}")


def conflict_target(files, direction: str, destination: str, *, include_partial: bool = False) -> str | None:
    if destination_exists(files, direction, destination):
        return destination
    if include_partial and destination_exists(files, direction, destination + ".part"):
        return destination + ".part"
    return None


def available_rename_destination(files, direction: str, destination: str, *, include_partial: bool = False) -> str | None:
    target = destination_path(direction, destination)
    for index in range(1, 10000):
        candidate = rename_destination(
            direction, destination, f"{target.stem} ({index}){target.suffix}"
        )
        if conflict_target(files, direction, candidate, include_partial=include_partial) is None:
            return candidate
    return None


@dataclass(frozen=True)
class ConflictFileInfo:
    path: str
    size: int | None = None
    mtime: int | None = None


def read_conflict_metadata(files, item, *, target_path=None) -> tuple[ConflictFileInfo, ConflictFileInfo]:
    """Read metadata on the transfer worker, never on the GUI thread."""
    def read(path, local):
        try:
            if local:
                info = os.stat(path)
                size, mtime = info.st_size, info.st_mtime
            else:
                size, mtime = files.stat(path)
            return ConflictFileInfo(path, int(size), int(mtime))
        except Exception:
            return ConflictFileInfo(path)

    return read(item.src, item.op == "upload"), read(target_path or item.dst, item.op == "download")


def format_conflict_metadata(info: ConflictFileInfo) -> tuple[str, str]:
    size = "-" if info.size is None else f"{info.size:,} B"
    try:
        mtime = datetime.fromtimestamp(info.mtime).isoformat(sep=" ", timespec="seconds") if info.mtime else "-"
    except (ValueError, OSError, OverflowError):
        mtime = "-"
    return size, mtime


def resolve_conflict_action(
    action: str,
    *,
    source_size: int | None = None,
    target_size: int | None = None,
    source_mtime: int | None = None,
    target_mtime: int | None = None,
) -> str:
    """Resolve conditional overwrite choices using only known metadata."""
    try:
        size_differs = (
            source_size is not None
            and target_size is not None
            and int(source_size) != int(target_size)
        )
    except (TypeError, ValueError):
        size_differs = False
    try:
        source_time = int(source_mtime) if source_mtime is not None else 0
        target_time = int(target_mtime) if target_mtime is not None else 0
        source_newer = source_time > 0 and target_time > 0 and source_time > target_time
    except (TypeError, ValueError):
        source_newer = False

    if action == "overwrite_if_newer":
        return "overwrite" if source_newer else "skip"
    if action == "overwrite_if_size_differs":
        return "overwrite" if size_differs else "skip"
    if action == "overwrite_if_size_differs_or_newer":
        return "overwrite" if size_differs or source_newer else "skip"
    if action in {"overwrite", "resume", "skip", "rename", "cancel"}:
        return action
    return "cancel"


def set_session_conflict_action(action: str, *, downloads_only: bool = False) -> None:
    """Use ``action`` for later conflicts until the application exits."""
    global _SESSION_ACTION
    with _LOCK:
        _SESSION_ACTION = (str(action), bool(downloads_only))


def get_session_conflict_action(direction: str) -> str | None:
    """Return the session choice when it applies to this transfer direction."""
    with _LOCK:
        preference = _SESSION_ACTION
    if preference is None:
        return None
    action, downloads_only = preference
    if downloads_only and direction != "download":
        return None
    return action


def clear_session_conflict_action() -> None:
    """Forget the current application's conflict choice."""
    global _SESSION_ACTION
    with _LOCK:
        _SESSION_ACTION = None


__all__ = [
    "ConflictFileInfo",
    "read_conflict_metadata",
    "format_conflict_metadata",
    "available_rename_destination",
    "destination_exists",
    "conflict_target",
    "destination_path",
    "rename_destination",
    "clear_session_conflict_action",
    "get_session_conflict_action",
    "resolve_conflict_action",
    "set_session_conflict_action",
]
