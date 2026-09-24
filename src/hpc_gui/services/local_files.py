from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class LocalEntry:
    name: str
    path: str
    is_dir: bool
    size: int = 0
    mtime: int = 0


def list_windows_drives() -> List[LocalEntry]:
    entries: List[LocalEntry] = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        root = f"{letter}:\\"
        if os.path.exists(root):
            entries.append(LocalEntry(root, root, True))
    if entries:
        return entries
    root = Path.home().anchor or os.path.abspath(os.sep)
    return [LocalEntry(root, root, True)]


def list_local_entries(directory: str) -> List[LocalEntry]:
    path = Path(directory).expanduser()
    entries: List[LocalEntry] = []
    with os.scandir(path) as iterator:
        for item in iterator:
            try:
                stat = item.stat(follow_symlinks=False)
                is_dir = item.is_dir(follow_symlinks=False)
                entries.append(
                    LocalEntry(
                        name=item.name,
                        path=os.path.abspath(item.path),
                        is_dir=is_dir,
                        size=0 if is_dir else int(stat.st_size),
                        mtime=int(stat.st_mtime),
                    )
                )
            except (OSError, PermissionError):
                continue
    entries.sort(key=lambda entry: (not entry.is_dir, entry.name.casefold()))
    return entries


def _is_source_checkout(path_value: str) -> bool:
    """True when a directory looks like a development/source checkout (TODO-025)."""
    try:
        root = Path(os.path.expanduser(path_value)).resolve()
    except Exception:
        return False
    try:
        if (root / "src" / "hpc_gui").is_dir():
            return True
        marker = root / "pyproject.toml"
        if marker.is_file():
            try:
                text = marker.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                return False
            return "hpc-client-gui" in text or "hpc_gui" in text
        return False
    except OSError:
        return False


def safe_initial_local_directory(saved: str = "") -> str:
    home = str(Path.home())
    cwd = os.getcwd()
    # Order: last valid user location -> user home -> safe cwd -> platform fallback.
    # A development/source checkout is never a safe cwd default (TODO-025).
    candidates = [saved, home, cwd]
    for candidate in candidates:
        if not candidate:
            continue
        expanded = os.path.expanduser(candidate)
        if not os.path.isdir(expanded):
            continue
        if candidate == cwd and _is_source_checkout(expanded):
            continue
        return os.path.abspath(expanded)
    return os.path.abspath(os.sep)
