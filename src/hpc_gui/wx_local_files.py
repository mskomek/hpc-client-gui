"""wx local-file browser model and optional adapter."""

from __future__ import annotations

import os
import shutil
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

    @staticmethod
    def delete(paths: list[str | Path]) -> tuple[Path, ...]:
        removed = []
        for value in paths:
            target = Path(value).expanduser().resolve()
            if not target.exists():
                continue
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            removed.append(target)
        return tuple(removed)

    @staticmethod
    def file_action(action: str, path: str | Path, value: str = "") -> tuple[str, str, str]:
        if action not in {"open", "open_with", "edit", "edit_new_window", "rename", "delete"}:
            raise ValueError(action)
        return action, str(Path(path)), value

    @staticmethod
    def context_actions(is_dir: bool) -> tuple[str, ...]:
        return ("open", "open_with", "edit", "edit_new_window", "new_tab", "rename", "delete") if is_dir else ("open", "open_with", "edit", "edit_new_window", "rename", "delete")


def show_local_files(parent=None, path: str | Path | None = None, *, open_editor=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = LocalBrowserModel(path or Path.cwd())
    frame = wx.Frame(parent, title="Files", size=(900, 600))
    listing = wx.ListCtrl(frame, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    listing.InsertColumn(0, "Name")
    listing.InsertColumn(1, "Size")
    entries = []

    def refresh() -> None:
        entries[:] = model.list_entries()
        listing.DeleteAllItems()
        for entry in entries:
            index = listing.InsertItem(listing.GetItemCount(), entry.path.name)
            listing.SetItem(index, 1, str(entry.size))

    def activate(event) -> None:
        entry = entries[event.GetIndex()]
        if model.activate(entry.path, open_editor=open_editor) == "navigate":
            refresh()

    def context_menu(event) -> None:
        index, _flags = listing.HitTest(event.GetPosition())
        if index < 0:
            return
        entry = entries[index]
        menu = wx.Menu()
        for action in model.context_actions(entry.is_dir):
            item = menu.Append(wx.ID_ANY, action.replace("_", " ").title())
            listing.Bind(wx.EVT_MENU, lambda _event, action=action: run_action(action, entry), item)
        listing.PopupMenu(menu)
        menu.Destroy()

    def run_action(action: str, entry: LocalEntry) -> None:
        if action in {"open", "edit", "edit_new_window", "new_tab"}:
            if action == "new_tab":
                model.new_tab(entry.path)
            elif action == "open":
                model.activate(entry.path, open_editor=open_editor)
            else:
                if open_editor:
                    open_editor(str(entry.path))
        elif action == "open_with":
            os.startfile(str(entry.path))
        elif action == "rename":
            dialog = wx.TextEntryDialog(frame, "New name", "Rename", entry.path.name)
            try:
                if dialog.ShowModal() == wx.ID_OK:
                    model.rename(entry.path, dialog.GetValue())
                    refresh()
            finally:
                dialog.Destroy()
        elif action == "delete" and wx.MessageBox(f"Delete {entry.path.name}?", "Confirm", wx.YES_NO | wx.ICON_WARNING) == wx.YES:
            model.delete([entry.path])
            refresh()

    listing.Bind(wx.EVT_LIST_ITEM_ACTIVATED, activate)
    listing.Bind(wx.EVT_CONTEXT_MENU, context_menu)
    refresh()
    frame.Show()
    return wx.ID_OK


__all__ = ["LocalBrowserModel", "LocalEntry", "file_url_payload", "show_local_files"]
