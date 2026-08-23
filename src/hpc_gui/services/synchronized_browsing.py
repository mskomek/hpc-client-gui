"""Pure synchronized-browsing path mapping.

No Qt, no network, no filesystem mutation. Containment uses component
comparison (never naive ``startswith``) so sibling prefixes such as
``C:\\foo\\bar`` vs ``C:\\foo\\bar2`` cannot collide.
"""

from __future__ import annotations

import ntpath
import os
import posixpath
from dataclasses import dataclass


@dataclass(frozen=True)
class SyncRoots:
    local_root: str = ""
    remote_root: str = ""


def _looks_like_windows_path(path: str) -> bool:
    """Detect Windows-style local paths regardless of host OS.

    The GUI runs on Windows while tests (and CI) may run on Linux, so
    ``C:\\...`` roots must parse with Windows semantics everywhere.
    """
    text = str(path or "")
    if "\\" in text:
        return True
    return bool(ntpath.splitdrive(text)[0])


def normalize_local_root(path: str) -> str:
    text = str(path or "").strip()
    if _looks_like_windows_path(text):
        return ntpath.normpath(text)
    return os.path.abspath(os.path.expanduser(text))


def normalize_remote_root(path: str) -> str:
    clean = posixpath.normpath(str(path or "").strip())
    return clean if clean not in {"", "."} else "/"


def _absolute_local(path: str) -> str:
    text = str(path or "").strip()
    if _looks_like_windows_path(text):
        return ntpath.normpath(text)
    return os.path.normpath(os.path.abspath(os.path.expanduser(text)))


def _split_local(absolute_path: str) -> tuple[str, list[str]]:
    if _looks_like_windows_path(absolute_path):
        drive, tail = ntpath.splitdrive(absolute_path)
    else:
        drive, tail = os.path.splitdrive(absolute_path)
    parts = [part for part in tail.replace("\\", "/").split("/") if part and part != "."]
    return drive.casefold(), parts


def _local_relative_components(local_path: str, local_root: str) -> list[str] | None:
    """Return components of ``local_path`` under ``local_root``.

    ``[]`` means the root itself; ``None`` means outside the root or an
    invalid root. Windows containment is case-insensitive.
    """
    target_root = str(local_root or "").strip()
    if not target_root:
        return None
    target_drive, target_parts = _split_local(_absolute_local(local_path))
    root_drive, root_parts = _split_local(_absolute_local(target_root))
    if target_drive != root_drive:
        return None
    case_insensitive = os.name == "nt" or bool(root_drive)
    if len(target_parts) < len(root_parts):
        return None

    def same(left: str, right: str) -> bool:
        return left.casefold() == right.casefold() if case_insensitive else left == right

    for target_part, root_part in zip(target_parts, root_parts):
        if not same(target_part, root_part):
            return None
    return target_parts[len(root_parts):]


def _remote_parts(path: str) -> list[str]:
    normalized = normalize_remote_root(path)
    return [part for part in normalized.split("/") if part]


def _remote_relative_components(remote_path: str, remote_root: str) -> list[str] | None:
    """POSIX-semantics relative components of ``remote_path`` under root."""
    root = str(remote_root or "").strip()
    if not root:
        return None
    target_parts = _remote_parts(remote_path)
    root_parts = _remote_parts(root)
    if len(target_parts) < len(root_parts):
        return None
    for target_part, root_part in zip(target_parts, root_parts):
        if target_part != root_part:
            return None
    return target_parts[len(root_parts):]


def local_to_remote(local_path: str, roots: SyncRoots) -> str | None:
    remote_root = str(roots.remote_root or "").strip()
    if not remote_root:
        return None
    components = _local_relative_components(local_path, roots.local_root)
    if components is None:
        return None
    base = normalize_remote_root(remote_root)
    if not components:
        return base
    return normalize_remote_root(base.rstrip("/") + "/" + "/".join(components))


def remote_to_local(remote_path: str, roots: SyncRoots) -> str | None:
    local_root = str(roots.local_root or "").strip()
    if not local_root:
        return None
    components = _remote_relative_components(remote_path, roots.remote_root)
    if components is None:
        return None
    normalized_root = normalize_local_root(local_root)
    if not components:
        return normalized_root
    if _looks_like_windows_path(normalized_root):
        return ntpath.join(normalized_root, *components)
    return os.path.join(normalized_root, *components)
