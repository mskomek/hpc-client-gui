"""wx local-file browser model and optional adapter."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from threading import Thread
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, context_selection, visible_actions


@dataclass(frozen=True)
class LocalEntry:
    path: Path
    is_dir: bool
    size: int


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
        pasted = []
        for source in self.clipboard:
            if not source.exists():
                raise FileNotFoundError(str(source))
            if source.is_dir() and (self.current_path == source or source in self.current_path.parents):
                raise ValueError("cannot paste a directory into itself")
            target = self.current_path / source.name
            if target.exists() or target == source:
                raise FileExistsError(str(target))
            if self.clipboard_move:
                shutil.move(str(source), str(target))
            elif source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
            pasted.append(target)
        if self.clipboard_move:
            self.clipboard = ()
        return tuple(pasted)

    def delete(self, paths: list[str | Path]) -> tuple[Path, ...]:
        removed = []
        for value in paths:
            target = Path(value).expanduser().resolve()
            if target == self.current_path or self.current_path not in target.parents:
                raise ValueError("local delete target must be inside the current directory")
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
        actions = ("open", "open_with", "edit", "edit_new_window", "rename", "delete", "copy", "cut", "paste", "copy_path", "refresh")
        return actions + (("new_tab",) if is_dir else ())


def show_local_files(parent=None, path: str | Path | None = None, *, open_editor=None, open_editor_new_window=None, upload=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = LocalBrowserModel(path or Path.cwd())
    frame = wx.Frame(parent, title=t("tabs.ftp"), size=(900, 600))
    listing = wx.ListCtrl(frame, style=wx.LC_REPORT)
    listing.InsertColumn(0, t("dirs.col_name"))
    listing.InsertColumn(1, t("dirs.col_size"))
    entries = []
    state = {"context_target": None, "closed": False, "mutation_in_flight": False, "view_generation": 0}
    labels = FILE_CONTEXT_LABEL_KEYS

    def safe_call_after(callback, *args):
        try:
            wx.CallAfter(callback, *args)
        except (AssertionError, RuntimeError):
            return

    def refresh() -> None:
        entries[:] = model.list_entries()
        listing.DeleteAllItems()
        for entry in entries:
            index = listing.InsertItem(listing.GetItemCount(), entry.path.name)
            listing.SetItem(index, 1, str(entry.size))

    def navigate(target) -> None:
        resolved = Path(target).expanduser().resolve()
        if resolved != model.current_path:
            state["view_generation"] += 1
        model.navigate(resolved)

    def refresh_labels(_language=None):
        frame.SetTitle(t("tabs.ftp"))
        listing.SetColumn(0, t("dirs.col_name"))
        listing.SetColumn(1, t("dirs.col_size"))

    def activate(event) -> None:
        entry = entries[event.GetIndex()]
        if entry.is_dir:
            navigate(entry.path)
            refresh()
        elif open_editor:
            open_editor(str(entry.path))

    def context_menu(event) -> None:
        position = event.GetPosition()
        keyboard_context = position == wx.DefaultPosition or (position.x < 0 and position.y < 0)
        index = -1 if keyboard_context else listing.HitTest(listing.ScreenToClient(position))[0]
        if index >= 0 and not listing.IsSelected(index):
            for selected_index in range(listing.GetItemCount()):
                listing.Select(selected_index, False)
            listing.Select(index)
        selected = selected_entries()
        entry = entries[index] if index >= 0 else None
        state["context_target"] = entry.path if entry and entry.is_dir else model.current_path
        selection = context_selection(
            str(entry.path) if entry else None,
            entry.is_dir if entry else None,
            tuple(str(item.path) for item in selected),
            tuple(item.is_dir for item in selected),
            background=index < 0 and not keyboard_context,
        )
        menu = wx.Menu()
        actions = tuple(action for action in visible_actions(selection, remote=False) if action != "upload" or upload)
        for action in actions:
            item = menu.Append(wx.ID_ANY, t(labels.get(action, "help.help_title")))
            listing.Bind(wx.EVT_MENU, lambda _event, action=action: run_action(action), item)
        listing.PopupMenu(menu)
        menu.Destroy()

    def selected_entries() -> list[LocalEntry]:
        return [entry for index, entry in enumerate(entries) if listing.IsSelected(index)]

    def mutate(operation) -> None:
        if state["closed"] or state["mutation_in_flight"]:
            return
        state["mutation_in_flight"] = True
        listing.Enable(False)
        origin_path = model.current_path
        origin_generation = state["view_generation"]

        def worker():
            try:
                operation()
                safe_call_after(mutation_done, None)
            except Exception as error:
                safe_call_after(mutation_done, error)

        def mutation_done(error):
            state["mutation_in_flight"] = False
            if state["closed"]:
                return
            listing.Enable(True)
            if error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            elif model.current_path == origin_path and state["view_generation"] == origin_generation:
                refresh()

        Thread(target=worker, daemon=True).start()

    def run_action(action: str) -> None:
        selected = selected_entries()
        if action == "upload" and upload:
            if selected:
                upload(tuple(str(item.path) for item in selected))
            else:
                dialog = wx.FileDialog(frame, t("ftp.upload_selected"), style=wx.FD_OPEN | wx.FD_MULTIPLE)
                try:
                    if dialog.ShowModal() == wx.ID_OK:
                        upload(tuple(dialog.GetPaths()))
                finally:
                    dialog.Destroy()
            return
        if action == "new_folder":
            dialog = wx.TextEntryDialog(frame, t("dirs.new_folder"), t("dirs.new_folder"))
            try:
                if dialog.ShowModal() == wx.ID_OK:
                    name = dialog.GetValue()
                    target = state["context_target"] or (selected[0].path if len(selected) == 1 and selected[0].is_dir else model.current_path)
                    mutate(lambda: model.new_folder(name, target))
            except Exception as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            finally:
                dialog.Destroy()
            return
        if action == "paste":
            mutate(model.paste)
            return
        if not selected:
            return
        entry = selected[0]
        if action in {"copy", "cut"}:
            model.copy([item.path for item in selected], move=action == "cut")
            return
        if action in {"open", "edit", "edit_new_window", "new_tab"}:
            if action == "new_tab":
                model.new_tab(entry.path)
                state["view_generation"] += 1
                refresh()
            elif action == "open":
                if entry.is_dir:
                    navigate(entry.path)
                    refresh()
                else:
                    try:
                        reveal_in_file_manager(entry.path)
                    except OSError as error:
                        wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            elif action == "edit_new_window" and open_editor_new_window:
                open_editor_new_window(str(entry.path))
            else:
                if open_editor:
                    for item in selected:
                        open_editor(str(item.path))
        elif action == "open_with":
            try:
                open_with_system(entry.path)
            except OSError as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
        elif action == "copy_path":
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(str(entry.path)))
                wx.TheClipboard.Close()
        elif action == "refresh":
            refresh()
        elif action == "rename":
            dialog = wx.TextEntryDialog(frame, t("dirs.rename"), t("dirs.rename"), entry.path.name)
            try:
                if dialog.ShowModal() == wx.ID_OK:
                    new_name = dialog.GetValue()
                    mutate(lambda: model.rename(entry.path, new_name))
            except Exception as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            finally:
                dialog.Destroy()
        elif action == "delete" and wx.MessageBox(t("dirs.delete_confirm"), t("dirs.delete"), wx.YES_NO | wx.ICON_WARNING) == wx.YES:
            paths = tuple(item.path for item in selected)
            mutate(lambda: model.delete(list(paths)))

    def key_down(event) -> None:
        if event.ControlDown() and event.GetKeyCode() in (ord("C"), ord("X"), ord("V")):
            run_action({ord("C"): "copy", ord("X"): "cut", ord("V"): "paste"}[event.GetKeyCode()])
            return
        if event.ControlDown() and event.GetKeyCode() == ord("A"):
            for index in range(listing.GetItemCount()):
                listing.Select(index)
            return
        if event.GetKeyCode() == wx.WXK_BACK:
            navigate(model.current_path.parent)
            refresh()
            return
        actions = {wx.WXK_F2: "rename", wx.WXK_DELETE: "delete", wx.WXK_F5: "refresh"}
        action = actions.get(event.GetKeyCode())
        if action:
            state["context_target"] = None
            run_action(action)
            return
        event.Skip()

    listing.Bind(wx.EVT_LIST_ITEM_ACTIVATED, activate)
    listing.Bind(wx.EVT_CONTEXT_MENU, context_menu)
    listing.Bind(wx.EVT_KEY_DOWN, key_down)
    frame._wx_local_controls = {"listing": listing}
    frame._wx_local_model = model
    frame._wx_local_state = state
    frame._wx_local_run_action = run_action
    subscribe_language_change(refresh_labels)
    def close(event):
        state["closed"] = True
        unsubscribe_language_change(refresh_labels)
        event.Skip()

    frame.Bind(wx.EVT_CLOSE, close)
    refresh()
    frame.Show()
    return wx.ID_OK


__all__ = ["LocalBrowserModel", "LocalEntry", "file_url_payload", "open_with_system", "reveal_in_file_manager", "show_local_files"]
