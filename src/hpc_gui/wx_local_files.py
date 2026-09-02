"""wx local-file browser model and optional adapter."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


@dataclass(frozen=True)
class LocalEntry:
    path: Path
    is_dir: bool
    size: int


def file_url_payload(paths: list[Path]) -> str:
    return "\r\n".join(f"file:///{quote(str(path).replace(os.sep, '/'))}" for path in paths)


class LocalBrowserModel:
    def __init__(self, path: str | Path = Path.cwd()) -> None:
        self.current_path = Path(path).expanduser().resolve()
        self.tabs = [self.current_path]
        self.active_tab = 0
        self.sort_key = "name"
        self.reverse = False

    def list_entries(self) -> tuple[LocalEntry, ...]:
        entries = [LocalEntry(item, item.is_dir(), item.stat().st_size if item.is_file() else 0) for item in self.current_path.iterdir()]
        key = (lambda item: item.path.name.casefold()) if self.sort_key == "name" else (lambda item: item.size)
        return tuple(sorted(entries, key=key, reverse=self.reverse))

    def navigate(self, path: str | Path) -> None:
        target = Path(path).expanduser().resolve()
        if not target.is_dir():
            raise NotADirectoryError(str(target))
        self.current_path = target
        self.tabs[self.active_tab] = target

    def parent(self) -> None:
        self.navigate(self.current_path.parent)

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

    @staticmethod
    def context_actions(is_dir: bool) -> tuple[str, ...]:
        return ("open", "open_with", "edit", "edit_new_window", "new_tab") if is_dir else ("open", "open_with", "edit", "edit_new_window")


def show_local_files(parent=None, path: str | Path | None = None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = LocalBrowserModel(path or Path.cwd())
    frame = wx.Frame(parent, title="Files", size=(900, 600))
    listing = wx.ListCtrl(frame, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    listing.InsertColumn(0, "Name")
    listing.InsertColumn(1, "Size")
    for entry in model.list_entries():
        index = listing.InsertItem(listing.GetItemCount(), entry.path.name)
        listing.SetItem(index, 1, str(entry.size))
    frame.Show()
    return wx.ID_OK


__all__ = ["LocalBrowserModel", "LocalEntry", "file_url_payload", "show_local_files"]
