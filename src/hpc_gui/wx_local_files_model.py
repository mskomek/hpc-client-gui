"""Toolkit-free local file model and operating-system file helpers."""

from __future__ import annotations

import os
import shutil
import stat as stat_module
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

@dataclass(frozen=True)
class LocalEntry:
    path: Path
    is_dir: bool
    size: int
    mtime: float = 0.0

def format_local_size(entry: LocalEntry) -> str:
    """Human-readable size; blank/unknown for directories (TODO-027/028)."""
    if entry.is_dir:
        return ""
    try:
        n = int(entry.size)
    except Exception:
        return ""
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024.0
        i += 1
    return f"{v:.1f} {units[i]}" if i else f"{int(v)} {units[i]}"

def file_url_payload(paths: list[Path]) -> str:
    return "\r\n".join(f"file:///{quote(str(path).replace(os.sep, '/'))}" for path in paths)

def open_with_system(path: str | Path) -> None:



    target = str(Path(path).expanduser().resolve())
    if hasattr(os, "startfile"):
        os.startfile(target)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])

def reveal_in_file_manager(path: str | Path) -> None:
    target = Path(path).expanduser().resolve()
    directory = target if target.is_dir() else target.parent
    if hasattr(os, "startfile"):
        os.startfile(str(directory))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(directory)] if target.is_dir() else ["open", "-R", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(directory)])

class LocalBrowserModel:
    def __init__(self, path: str | Path = Path.cwd()) -> None:
        self.current_path = Path(path).expanduser().resolve()
        self.tabs = [self.current_path]
        self.active_tab = 0
        self.sort_key = "name"
        self.reverse = False
        self.clipboard: tuple[Path, ...] = ()
        self.clipboard_move = False
        self._history: list[Path] = []
        self._forward: list[Path] = []

    def list_entries(self, path: str | Path | None = None) -> tuple[LocalEntry, ...]:
        current_path = self.current_path if path is None else Path(path).expanduser().resolve()
        entries = []
        for item in current_path.iterdir():
            try:
                metadata = item.stat()
            except OSError:
                entries.append(LocalEntry(item, False, 0, 0.0))
            else:
                is_dir = stat_module.S_ISDIR(metadata.st_mode)
                size = metadata.st_size if stat_module.S_ISREG(metadata.st_mode) else 0
                mtime = float(getattr(metadata, "st_mtime", 0.0) or 0.0)
                entries.append(LocalEntry(item, is_dir, size, mtime))
        key = (lambda item: item.path.name.casefold()) if self.sort_key == "name" else (lambda item: item.size)
        directories = [item for item in entries if item.is_dir]
        files = [item for item in entries if not item.is_dir]
        directories.sort(key=key, reverse=self.reverse)
        files.sort(key=key, reverse=self.reverse)
        return tuple(directories + files)

    def navigate(self, path: str | Path, *, _remember: bool = True) -> None:
        target = Path(path).expanduser().resolve()
        if not target.is_dir():
            raise NotADirectoryError(str(target))
        if _remember and target != self.current_path:
            self._history.append(self.current_path)
            self._forward.clear()
        self.current_path = target
        self.tabs[self.active_tab] = target

    def parent(self) -> None:
        self.navigate(self.current_path.parent)

    def go_back(self) -> None:
        if not self._history:
            raise IndexError("no history")
        target = self._history.pop()
        self._forward.append(self.current_path)
        self.navigate(target, _remember=False)

    def can_go_back(self) -> bool:
        return bool(self._history)

    def go_forward(self) -> None:
        if not self._forward:
            raise IndexError("no forward history")
        target = self._forward.pop()
        self._history.append(self.current_path)
        self.navigate(target, _remember=False)

    def can_go_forward(self) -> bool:
        return bool(self._forward)

    def new_tab(self, path: str | Path | None = None) -> int:
        target = Path(path or self.current_path).expanduser().resolve()
        if not target.is_dir():
            raise NotADirectoryError(str(target))
        self.tabs.append(target)
        self.active_tab = len(self.tabs) - 1
        self.current_path = target
        return self.active_tab

    def close_tab(self, index: int | None = None) -> None:
        if len(self.tabs) == 1:
            return
        index = self.active_tab if index is None else index
        self.tabs.pop(index)
        self.active_tab = min(index, len(self.tabs) - 1)
        self.current_path = self.tabs[self.active_tab]

    def sort(self, key: str) -> None:
        if key not in {"name", "size"}:
            raise ValueError(key)
        self.reverse = self.sort_key == key and not self.reverse
        self.sort_key = key

    def search(self, query: str) -> tuple[LocalEntry, ...]:
        """Search entries by name (case-insensitive substring match)."""
        query_lower = query.casefold()
        return tuple(
            entry for entry in self.list_entries()
            if query_lower in entry.path.name.casefold()
        )

    def activate(self, path: str | Path, *, open_editor=None) -> str:
        """Activate an entry without coupling the model to wx widgets."""
        target = Path(path).expanduser().resolve()
        if target.is_dir():
            self.navigate(target)
            return "navigate"
        if open_editor:
            open_editor(str(target))
        return "edit"

    def rename(self, path: str | Path, new_name: str) -> Path:
        source = Path(path).expanduser().resolve()
        name = Path(new_name).name
        if not name or name != new_name or name in {".", ".."}:
            raise ValueError("invalid local name")
        if source.parent != self.current_path or not source.exists():
            raise FileNotFoundError(str(source))
        target = source.with_name(name)
        if target.exists():
            raise FileExistsError(str(target))
        source.rename(target)
        return target

    def new_folder(self, name: str, parent: str | Path | None = None) -> Path:
        name = str(name).strip()
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("invalid local name")
        base = Path(parent).expanduser().resolve() if parent is not None else self.current_path
        target = (base / name).resolve()
        if target.parent != base or target.exists():
            raise FileExistsError(str(target))
        target.mkdir()
        return target

    def copy(self, paths: list[str | Path], *, move: bool = False) -> None:
        self.clipboard = tuple(Path(path).expanduser().resolve() for path in paths)
        self.clipboard_move = bool(move)

    def paste(self) -> tuple[Path, ...]:
        return self.paste_into(self.current_path, self.clipboard, self.clipboard_move)

    def paste_into(self, destination: str | Path, clipboard: tuple[Path, ...] | None = None, move: bool | None = None) -> tuple[Path, ...]:
        dest = Path(destination).expanduser().resolve()
        clip = tuple(Path(p).expanduser().resolve() for p in (clipboard if clipboard is not None else self.clipboard))
        is_move = bool(move if move is not None else self.clipboard_move)
        pasted = []
        for source in clip:
            if not source.exists():
                raise FileNotFoundError(str(source))
            if source.is_dir() and (dest == source or source in dest.parents):
                raise ValueError("cannot paste a directory into itself")
            target = dest / source.name
            if target.exists() or target == source:
                raise FileExistsError(str(target))
            if is_move:
                shutil.move(str(source), str(target))
            elif source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
            pasted.append(target)
        if is_move and clipboard is None:
            self.clipboard = ()
        elif is_move:
            # clear global clipboard only if it matches snapshot
            if tuple(self.clipboard) == clip and self.clipboard_move == is_move:
                self.clipboard = ()
        return tuple(pasted)

    def delete(self, paths: list[str | Path]) -> tuple[Path, ...]:
        return self.delete_at(paths, self.current_path)

    def delete_at(self, paths: list[str | Path], origin_dir: str | Path) -> tuple[Path, ...]:
        origin = Path(origin_dir).expanduser().resolve()
        removed = []
        for value in paths:
            target = Path(value).expanduser().resolve()
            if target == origin or origin not in target.parents:
                raise ValueError("local delete target must be inside the origin directory")
            if not target.exists():
                continue
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            removed.append(target)
        return tuple(removed)

    def rename_at(self, source: str | Path, new_name: str, origin_dir: str | Path) -> Path:
        src = Path(source).expanduser().resolve()
        origin = Path(origin_dir).expanduser().resolve()
        name = Path(new_name).name
        if not name or name != new_name or name in {".", ".."}:
            raise ValueError("invalid local name")
        if src.parent != origin or not src.exists():
            raise FileNotFoundError(str(src))
        target = src.with_name(name)
        if target.exists():
            raise FileExistsError(str(target))
        src.rename(target)
        return target

    @staticmethod
    def file_action(action: str, path: str | Path, value: str = "") -> tuple[str, str, str]:
        if action not in {"open", "open_with", "edit", "edit_new_window", "rename", "delete"}:
            raise ValueError(action)
        return action, str(Path(path)), value

    @staticmethod
    def context_actions(is_dir: bool) -> tuple[str, ...]:
        actions = ("open", "open_with", "edit", "edit_new_window", "rename", "delete", "copy", "cut", "paste", "copy_path", "refresh")
        return actions + (("new_tab",) if is_dir else ())
