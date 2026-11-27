"""Read-only recursive remote download planning, independent of any GUI."""
from __future__ import annotations

import os
import posixpath
import stat
from pathlib import Path, PureWindowsPath

from hpc_gui.services.transfer_controller import TransferCancelled, TransferItem


def _windows_reserved(name):
    checker = getattr(os.path, "isreserved", None)
    return checker(name) if checker is not None else PureWindowsPath(name).is_reserved()


def _local_name(name):
    name = str(name)
    if not name or name in {".", ".."} or any(c in name for c in ("/", "\\", "\x00")):
        raise ValueError(f"Unsafe remote filename: {name!r}")
    if os.name == "nt" and (
        PureWindowsPath(name).drive or any(c in name for c in '<>:"|?*')
        or name.endswith((".", " ")) or _windows_reserved(name)
        or any(ord(c) < 32 for c in name)
    ):
        raise ValueError(f"Unsafe Windows filename: {name!r}")
    return name


def _entry_kind(entry):
    mode = stat.S_IFMT(int(getattr(entry, "mode", 0) or 0))
    if mode not in (0, stat.S_IFDIR, stat.S_IFREG):
        raise ValueError(f"Unsupported remote file type: {entry.path}")
    return bool(entry.is_dir)


def _root_info(files, source):
    lstat = getattr(files, "lstat_entry", None)
    if callable(lstat):
        entry = lstat(source)
        return _entry_kind(entry), getattr(entry, "size", None)
    is_dir = bool(files.is_dir(source))
    if is_dir:
        return True, None
    size, _ = files.stat(source)
    return False, int(size)


def build_download_plan(files, paths, destination, *, current=lambda: True):
    """Discover the whole tree before any local or remote mutation.

    Directory merges are allowed; a file blocking a directory is rejected
    rather than silently deleted. Reject symlinks/special remote entries when
    metadata identifies them, and never follow a local destination symlink.
    """
    root = Path(destination).resolve()
    if root.exists() and not root.is_dir():
        raise NotADirectoryError(str(root))
    items = []
    seen_sources = set()
    claimed = set()

    def check():
        if not current():
            raise TransferCancelled()

    def add(remote, local, is_dir, size=None):
        check()
        for parent in (local, *local.parents):
            if parent == root:
                break
            if parent.is_symlink():
                raise ValueError(f"Unsafe local symlink: {parent}")
        key = os.path.normcase(str(local))
        if key in claimed:
            raise ValueError(f"Multiple remote entries target {local}")
        claimed.add(key)
        if is_dir:
            if local.exists() and not local.is_dir():
                raise NotADirectoryError(str(local))
            items.append(TransferItem("mkdir_local", "", str(local)))
        else:
            if local.is_dir():
                raise IsADirectoryError(str(local))
            items.append(TransferItem("download", remote, str(local), cached_size=size))

    for value in paths:
        check()
        source = posixpath.normpath(str(value))
        if not source.startswith("/") or source == "/":
            raise ValueError(f"Invalid remote download source: {value!r}")
        if source in seen_sources:
            continue
        seen_sources.add(source)
        local = root / _local_name(posixpath.basename(source))
        directory, size = _root_info(files, source)
        add(source, local, directory, size)
        if not directory:
            continue
        stack = [(source, local)]
        while stack:
            check()
            remote_dir, local_dir = stack.pop()
            child_dirs = []
            for entry in files.listdir_entries(remote_dir):
                check()
                name = _local_name(entry.name)
                remote = posixpath.join(remote_dir, name)
                if posixpath.normpath(str(entry.path)) != remote:
                    raise ValueError(f"Remote listing path mismatch: {entry.path!r}")
                local_path = local_dir / name
                directory = _entry_kind(entry)
                add(remote, local_path, directory, getattr(entry, "size", None))
                if directory:
                    child_dirs.append((remote, local_path))
            stack.extend(reversed(child_dirs))
    return items
