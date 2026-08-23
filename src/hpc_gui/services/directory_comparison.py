"""Pure immediate-directory metadata comparison.

No Qt, no network, no filesystem access. O(n) dictionary-based diff of
local and remote entry snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class CompareStatus(str, Enum):
    SAME = "same"
    LOCAL_ONLY = "local_only"
    REMOTE_ONLY = "remote_only"
    TYPE_MISMATCH = "type_mismatch"
    SIZE_DIFFERENT = "size_different"
    LOCAL_NEWER = "local_newer"
    REMOTE_NEWER = "remote_newer"


@dataclass(frozen=True)
class ComparableEntry:
    name: str
    is_dir: bool
    size: int = 0
    mtime: int = 0


@dataclass(frozen=True)
class ComparisonResult:
    local: dict[str, CompareStatus]
    remote: dict[str, CompareStatus]


def _pair_status(local: ComparableEntry, remote: ComparableEntry, *, mtime_tolerance_seconds: int) -> CompareStatus:
    if local.is_dir != remote.is_dir:
        return CompareStatus.TYPE_MISMATCH
    if local.is_dir:
        return CompareStatus.SAME
    if int(local.size) != int(remote.size):
        return CompareStatus.SIZE_DIFFERENT
    tolerance = max(0, int(mtime_tolerance_seconds))
    if int(local.mtime) > int(remote.mtime) + tolerance:
        return CompareStatus.LOCAL_NEWER
    if int(remote.mtime) > int(local.mtime) + tolerance:
        return CompareStatus.REMOTE_NEWER
    return CompareStatus.SAME


def compare_directory_entries(
    local_entries: Iterable[ComparableEntry],
    remote_entries: Iterable[ComparableEntry],
    *,
    mtime_tolerance_seconds: int = 2,
) -> ComparisonResult:
    """Compare two entry snapshots by exact name in O(n) time/memory."""
    local_by_name = {entry.name: entry for entry in local_entries}
    remote_by_name = {entry.name: entry for entry in remote_entries}

    local_statuses: dict[str, CompareStatus] = {}
    remote_statuses: dict[str, CompareStatus] = {}

    for name, local in local_by_name.items():
        remote = remote_by_name.get(name)
        if remote is None:
            status = CompareStatus.LOCAL_ONLY
        else:
            status = _pair_status(
                local,
                remote,
                mtime_tolerance_seconds=mtime_tolerance_seconds,
            )
        local_statuses[name] = status

    for name in remote_by_name:
        if name not in local_by_name:
            remote_statuses[name] = CompareStatus.REMOTE_ONLY

    return ComparisonResult(local=local_statuses, remote=remote_statuses)
