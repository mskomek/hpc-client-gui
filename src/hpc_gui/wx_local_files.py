"""wx local-file browser model and optional adapter."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from threading import Lock, Thread
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, context_selection, visible_actions
from hpc_gui.services.local_files import list_windows_drives
from hpc_gui.wx_host import make_host

from hpc_gui.ui.models.remote_entry_helpers import file_type as _shared_file_type, fmt_mtime as _shared_fmt_mtime


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
        self._history: list[Path] = []

    def list_entries(self, path: str | Path | None = None) -> tuple[LocalEntry, ...]:
        current_path = self.current_path if path is None else Path(path).expanduser().resolve()
        entries = [LocalEntry(item, item.is_dir(), item.stat().st_size if item.is_file() else 0) for item in current_path.iterdir()]
        key = (lambda item: item.path.name.casefold()) if self.sort_key == "name" else (lambda item: item.size)
        return tuple(sorted(entries, key=key, reverse=self.reverse))

    def navigate(self, path: str | Path, *, _remember: bool = True) -> None:
        target = Path(path).expanduser().resolve()
        if not target.is_dir():
            raise NotADirectoryError(str(target))
        if _remember and target != self.current_path:
            self._history.append(self.current_path)
        self.current_path = target
        self.tabs[self.active_tab] = target

    def parent(self) -> None:
        self.navigate(self.current_path.parent)

    def go_back(self) -> None:
        if not self._history:
            raise IndexError("no history")
        target = self._history.pop()
        self.navigate(target, _remember=False)

    def can_go_back(self) -> bool:
        return bool(self._history)

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


def _entry_name(entry) -> str:
    name = getattr(entry, "name", "") or ""
    if name:
        return str(name)
    raw = getattr(entry, "path", "") or ""
    return str(raw).replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def _format_mtime(mtime_val) -> str:
    return _shared_fmt_mtime(mtime_val)


def _type_label(entry) -> str:
    return _shared_file_type(_entry_name(entry), bool(getattr(entry, "is_dir", False)))


def _build_local_files(parent, path: str | Path | None = None, *, open_editor=None, open_editor_new_window=None, upload=None, run_shell=None, embedded):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = LocalBrowserModel(path or Path.cwd())
    host, finish = make_host(parent, title=t("tabs.ftp"), size=(900, 600), embedded=embedded)
    toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
    btn_drives = wx.Button(host, label=t("ftp.drives"))
    btn_back = wx.Button(host, label=t("ftp.back"))
    btn_parent = wx.Button(host, label=t("ftp.parent"))
    btn_refresh = wx.Button(host, label=t("dirs.refresh"))
    for _b in (btn_drives, btn_back, btn_parent, btn_refresh):
        toolbar_sizer.Add(_b, 0, wx.ALL, 4)
    # Back uses real history; disabled when empty
    try:
        btn_back.Disable()
    except Exception:
        pass
    path_ctrl = wx.TextCtrl(host, value=str(model.current_path), style=wx.TE_PROCESS_ENTER)
    # path row with label
    path_row = wx.BoxSizer(wx.HORIZONTAL)
    path_label = wx.StaticText(host, label=t("dirs.path"))
    path_row.Add(path_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    path_row.Add(path_ctrl, 1, wx.EXPAND | wx.ALL, 4)
    notebook = wx.Notebook(host)
    root_sizer = wx.BoxSizer(wx.VERTICAL)
    root_sizer.Add(toolbar_sizer, 0, wx.EXPAND)
    root_sizer.Add(path_row, 0, wx.EXPAND)
    root_sizer.Add(notebook, 1, wx.EXPAND)
    host.SetSizer(root_sizer)


    state = {"context_target": None, "closed": False, "mutation_in_flight": False, "view_generation": 0, "listing_request_id": 0}
    threading_lock = Lock()
    labels = FILE_CONTEXT_LABEL_KEYS
    tabs: list[dict] = []
    next_tab_id = [0]

    def safe_call_after(callback, *args):
        try:
            if wx.GetApp() is None:
                return
            wx.CallAfter(callback, *args)
        except BaseException:
            return

    def tab_label(path_value: Path) -> str:
        name = path_value.name
        return name or str(path_value) or "Local"

    def active_tab_state():
        sel = notebook.GetSelection()
        if sel < 0 or sel >= len(tabs):
            return tabs[0] if tabs else None
        return tabs[sel]

    def active_listing():
        tstate = active_tab_state()
        return tstate["listing"] if tstate else None

    def current_entries():
        tstate = active_tab_state()
        return tstate["entries"] if tstate else []

    def sync_model_to_active():
        tstate = active_tab_state()
        if not tstate:
            return
        idx = notebook.GetSelection()
        model.active_tab = idx
        if idx < len(model.tabs):
            model.current_path = tstate["path"]
        else:
            # shouldn't happen
            pass

    def refresh_active_tab_label(idx: int | None = None):
        if idx is None:
            idx = notebook.GetSelection()
        if 0 <= idx < len(tabs):
            notebook.SetPageText(idx, tab_label(tabs[idx]["path"]))

    def refresh() -> None:
        tstate = active_tab_state()
        if not tstate:
            return
        with threading_lock:
            if state["closed"] or tstate.get("closed"):
                return
            # increments both global and per-tab generation
            state["view_generation"] += 1
            state["listing_request_id"] += 1
            tstate["view_generation"] += 1
            tstate["listing_request_id"] += 1
            request_id = tstate["listing_request_id"]
            request_generation = tstate["view_generation"]
            requested_path = tstate["path"]
            tab_id = tstate["id"]

        def done(result, error):
            # re-check lifetime in callback (post-queue safety)
            with threading_lock:
                # find tab by id (may have been closed)
                tab_entry = next((tt for tt in tabs if tt["id"] == tab_id), None)
                if not tab_entry or tab_entry.get("closed"):
                    return
                current = (
                    not state["closed"]
                    and request_id == tab_entry["listing_request_id"]
                    and request_generation == tab_entry["view_generation"]
                    and requested_path == tab_entry["path"]
                )
            if not current:
                return
            if error:
                # only show error if this tab is active, otherwise silently ignore? Spec says no error should show in other tab, but stale check above already filters.
                # If tab is not active, still don't show message box (avoid cross-tab).
                if notebook.GetSelection() == tabs.index(tab_entry):
                    wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                return
            # verify controls still alive
            try:
                if not tab_entry["listing"] or not tab_entry["listing"].IsShownOnScreen() and False:
                    pass
                # Accessing destroyed control raises exception; check via wx
                if not tab_entry["listing"]:
                    return
            except Exception:
                return
            try:
                # Check if window still exists
                if not wx.Window.FindWindowById(tab_entry["listing"].GetId()):
                    # fallback: check closed flag already
                    pass
            except Exception:
                pass
            tab_entry["entries"][:] = result
            # Only render if tab still valid; but we update that tab's listing regardless of active
            lst = tab_entry["listing"]
            try:
                lst.DeleteAllItems()
                for entry in tab_entry["entries"]:
                    idx = lst.InsertItem(lst.GetItemCount(), entry.path.name)
                    lst.SetItem(idx, 1, str(entry.size))
                    lst.SetItem(idx, 2, _type_label(entry))
                    lst.SetItem(idx, 3, _format_mtime(getattr(entry, "mtime", None)))
            except RuntimeError:
                # control destroyed
                return

        def worker():
            try:
                safe_call_after(done, model.list_entries(requested_path), None)
            except Exception as error:
                safe_call_after(done, (), error)

        Thread(target=worker, daemon=True).start()

    def navigate(target) -> None:
        tstate = active_tab_state()
        if not tstate:
            return
        resolved = Path(target).expanduser().resolve()
        if resolved != tstate["path"]:
            state["view_generation"] += 1
            tstate["view_generation"] += 1
        tstate["path"] = resolved
        # sync model tabs entry
        idx = notebook.GetSelection()
        if 0 <= idx < len(model.tabs):
            model.tabs[idx] = resolved
        model.current_path = resolved
        model.active_tab = idx
        try:
            path_ctrl.SetValue(str(resolved))
        except Exception:
            pass
        refresh_active_tab_label(idx)

    # Widths are applied before rows exist, so content autosizing measures nothing.
    # Give the fixed columns a readable floor and let Name take the remainder.
    _COLUMN_FLOORS = (140, 70, 110, 120)

    def _apply_column_widths(listing) -> None:
        try:
            for col in (1, 2, 3):
                listing.SetColumnWidth(col, wx.LIST_AUTOSIZE_USEHEADER)
                listing.SetColumnWidth(col, max(_COLUMN_FLOORS[col], listing.GetColumnWidth(col)))
            avail = listing.GetClientSize().GetWidth() or 860
            fixed = sum(listing.GetColumnWidth(c) for c in (1, 2, 3))
            listing.SetColumnWidth(0, max(_COLUMN_FLOORS[0], avail - fixed - 24))
        except Exception:
            pass

    def create_tab(target_path: Path):
        target_path = Path(target_path).expanduser().resolve()
        panel = wx.Panel(notebook)
        listing = wx.ListCtrl(panel, style=wx.LC_REPORT)
        listing.InsertColumn(0, t("dirs.col_name"))
        listing.InsertColumn(1, t("dirs.col_size"))
        listing.InsertColumn(2, t("dirs.col_type"))
        listing.InsertColumn(3, t("dirs.col_mtime"))
        _apply_column_widths(listing)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(listing, 1, wx.EXPAND)
        panel.SetSizer(sizer)
        tab_entry = {"id": next_tab_id[0], "path": target_path, "listing": listing, "entries": [], "view_generation": 0, "listing_request_id": 0, "closed": False, "panel": panel}
        next_tab_id[0] += 1
        tabs.append(tab_entry)
        # sync model
        # caller will handle notebook insertion
        # bind events for this listing
        listing.Bind(wx.EVT_LIST_ITEM_ACTIVATED, activate)
        listing.Bind(wx.EVT_CONTEXT_MENU, context_menu)
        listing.Bind(wx.EVT_KEY_DOWN, key_down)
        listing.Bind(wx.EVT_MIDDLE_DOWN, middle_click)
        # also handle middle click via list event hit test fallback
        return tab_entry

    def activate(event) -> None:
        tstate = active_tab_state()
        if not tstate:
            return
        idx = event.GetIndex()
        if idx < 0 or idx >= len(tstate["entries"]):
            return
        entry = tstate["entries"][idx]
        if entry.is_dir:
            navigate(entry.path)
            refresh()
        elif open_editor:
            open_editor(str(entry.path))

    def middle_click(event) -> None:
        tstate = active_tab_state()
        if not tstate:
            event.Skip()
            return
        listing = tstate["listing"]
        # Use HitTest to find entry under cursor
        pos = event.GetPosition()
        # For middle down, position is client coordinates
        idx, _flags = listing.HitTest(pos)
        if idx >= 0 and idx < len(tstate["entries"]):
            entry = tstate["entries"][idx]
            if entry.is_dir:
                # open in new tab
                model.new_tab(entry.path)
                # create visible tab
                new_entry = create_tab(entry.path)
                notebook.AddPage(new_entry["panel"], tab_label(entry.path), True)
                # sync model active index
                model.active_tab = notebook.GetSelection()
                model.current_path = entry.path
                try:
                    path_ctrl.SetValue(str(entry.path))
                except Exception:
                    pass
                if hasattr(host, "_wx_local_controls"):
                    host._wx_local_controls["listing"] = new_entry["listing"]
                refresh()
                return
        event.Skip()

    def context_menu(event) -> None:
        tstate = active_tab_state()
        if not tstate:
            return
        listing = tstate["listing"]
        entries = tstate["entries"]
        position = event.GetPosition()
        keyboard_context = position == wx.DefaultPosition or (position.x < 0 and position.y < 0)
        index = -1 if keyboard_context else listing.HitTest(listing.ScreenToClient(position))[0]
        if index >= 0 and not listing.IsSelected(index):
            for selected_index in range(listing.GetItemCount()):
                listing.Select(selected_index, False)
            listing.Select(index)
        # gather selected entries for active tab
        selected = [entry for idx2, entry in enumerate(entries) if listing.IsSelected(idx2)]
        entry = entries[index] if 0 <= index < len(entries) else None
        state["context_target"] = entry.path if entry and entry.is_dir else tstate["path"]
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
        tstate = active_tab_state()
        if not tstate:
            return []
        listing = tstate["listing"]
        entries = tstate["entries"]
        return [entry for idx2, entry in enumerate(entries) if listing.IsSelected(idx2)]

    def mutate(operation) -> None:
        tstate = active_tab_state()
        if not tstate:
            return
        if state["closed"] or state["mutation_in_flight"] or tstate.get("closed"):
            return
        state["mutation_in_flight"] = True
        listing = tstate["listing"]
        listing.Enable(False)
        origin_path = tstate["path"]
        origin_generation = tstate["view_generation"]
        tab_id = tstate["id"]

        def worker():
            try:
                operation()
                safe_call_after(mutation_done, None, tab_id, origin_path, origin_generation)
            except Exception as error:
                safe_call_after(mutation_done, error, tab_id, origin_path, origin_generation)

        def mutation_done(error, done_tab_id, done_origin_path, done_origin_gen):
            state["mutation_in_flight"] = False
            if state["closed"]:
                return
            tab_entry = next((tt for tt in tabs if tt["id"] == done_tab_id), None)
            if not tab_entry or tab_entry.get("closed"):
                return
            try:
                tab_entry["listing"].Enable(True)
            except RuntimeError:
                return
            if error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            elif tab_entry["path"] == done_origin_path and tab_entry["view_generation"] == done_origin_gen:
                # need to refresh that specific tab; temporarily make it active concept? just refresh logic for that tab directly
                # if that tab is active, use normal refresh; else do targeted refresh
                if notebook.GetSelection() == tabs.index(tab_entry):
                    refresh()
                else:
                    # targeted refresh for non-active tab
                    # we could directly call refresh for that tab entry
                    # simulate refresh but scoped to that tab
                    with threading_lock:
                        if tab_entry.get("closed"):
                            return
                        tab_entry["listing_request_id"] += 1
                        tab_entry["view_generation"] += 1
                        req_id = tab_entry["listing_request_id"]
                        req_gen = tab_entry["view_generation"]
                        req_path = tab_entry["path"]
                        tid = tab_entry["id"]
                    def done2(result, err):
                        with threading_lock:
                            te = next((tt for tt in tabs if tt["id"] == tid), None)
                            if not te or te.get("closed") or req_id != te["listing_request_id"] or req_gen != te["view_generation"] or req_path != te["path"]:
                                return
                        if err:
                            return
                        te["entries"][:] = result
                        try:
                            te["listing"].DeleteAllItems()
                            for en in te["entries"]:
                                ii = te["listing"].InsertItem(te["listing"].GetItemCount(), en.path.name)
                                te["listing"].SetItem(ii, 1, str(en.size))
                                te["listing"].SetItem(ii, 2, _type_label(en))
                                te["listing"].SetItem(ii, 3, _format_mtime(getattr(en, "mtime", None)))
                        except RuntimeError:
                            return
                    def wk2():
                        try:
                            safe_call_after(done2, model.list_entries(req_path), None)
                        except Exception as e2:
                            safe_call_after(done2, (), e2)
                    Thread(target=wk2, daemon=True).start()

        Thread(target=worker, daemon=True).start()

    def run_action(action: str) -> None:
        tstate = active_tab_state()
        if not tstate:
            return
        selected = selected_entries()
        if action == "run_shell" and run_shell and selected:
            run_shell(str(selected[0].path))
            return
        if action == "upload" and upload:
            if selected:
                upload(tuple(str(item.path) for item in selected))
            else:
                dialog = wx.FileDialog(host, t("ftp.upload_selected"), style=wx.FD_OPEN | wx.FD_MULTIPLE)
                try:
                    if dialog.ShowModal() == wx.ID_OK:
                        upload(tuple(dialog.GetPaths()))
                finally:
                    dialog.Destroy()
            return
        if action == "new_folder":
            dialog = wx.TextEntryDialog(host, t("dirs.new_folder"), t("dirs.new_folder"))
            try:
                if dialog.ShowModal() == wx.ID_OK:
                    name = dialog.GetValue()
                    target = state["context_target"] or (selected[0].path if len(selected) == 1 and selected[0].is_dir else tstate["path"])
                    mutate(lambda: model.new_folder(name, target))
            except Exception as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            finally:
                dialog.Destroy()
            return
        if action == "paste":
            # snapshot destination and clipboard at action time
            dest_snapshot = tstate["path"]
            clip_snapshot = tuple(model.clipboard)
            move_snapshot = model.clipboard_move
            mutate(lambda: model.paste_into(dest_snapshot, clip_snapshot, move_snapshot))
            return
        if action == "refresh":
            refresh()
            return
        if not selected:
            return
        entry = selected[0]
        if action in {"copy", "cut"}:
            model.copy([item.path for item in selected], move=action == "cut")
            return
        if action in {"open", "edit", "edit_new_window", "new_tab"}:
            if action == "new_tab":
                # create visible second tab
                model.new_tab(entry.path)
                new_entry = create_tab(entry.path)
                notebook.AddPage(new_entry["panel"], tab_label(entry.path), True)
                model.active_tab = notebook.GetSelection()
                model.current_path = entry.path
                try:
                    path_ctrl.SetValue(str(entry.path))
                except Exception:
                    pass
                if hasattr(host, "_wx_local_controls"):
                    host._wx_local_controls["listing"] = new_entry["listing"]
                # keep state view_generation in sync
                # refresh will handle
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
        elif action == "rename":
            dialog = wx.TextEntryDialog(host, t("dirs.rename"), t("dirs.rename"), entry.path.name)
            try:
                if dialog.ShowModal() == wx.ID_OK:
                    new_name = dialog.GetValue()
                    origin_snapshot = tstate["path"]
                    src_snapshot = entry.path
                    mutate(lambda: model.rename_at(src_snapshot, new_name, origin_snapshot))
            except Exception as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            finally:
                dialog.Destroy()
        elif action == "delete" and wx.MessageBox(t("dirs.delete_confirm"), t("dirs.delete"), wx.YES_NO | wx.ICON_WARNING) == wx.YES:
            paths = tuple(item.path for item in selected)
            origin_snapshot = tstate["path"]
            mutate(lambda: model.delete_at(list(paths), origin_snapshot))

    def key_down(event) -> None:
        # Use active listing; if no selection handle accordingly
        tstate = active_tab_state()
        if not tstate:
            event.Skip()
            return
        listing = tstate["listing"]
        if event.ControlDown() and event.GetKeyCode() in (ord("C"), ord("X"), ord("V")):
            run_action({ord("C"): "copy", ord("X"): "cut", ord("V"): "paste"}[event.GetKeyCode()])
            return
        if event.ControlDown() and event.GetKeyCode() == ord("A"):
            for index in range(listing.GetItemCount()):
                listing.Select(index)
            return
        # REMOVED: Backspace parent navigation for local (per contract)
        actions = {wx.WXK_F2: "rename", wx.WXK_DELETE: "delete", wx.WXK_F5: "refresh"}
        action = actions.get(event.GetKeyCode())
        if action:
            state["context_target"] = None
            run_action(action)
            return
        event.Skip()

    def on_page_changed(event):
        # update model to reflect new active tab
        new_sel = event.GetSelection()
        if 0 <= new_sel < len(tabs):
            model.active_tab = new_sel
            model.current_path = tabs[new_sel]["path"]
            try:
                path_ctrl.SetValue(str(tabs[new_sel]["path"]))
            except Exception:
                pass
            # update global controls reference for tests (guard before attribute exists)
            if hasattr(host, "_wx_local_controls"):
                host._wx_local_controls["listing"] = tabs[new_sel]["listing"]
                host._wx_local_controls["path"] = path_ctrl
        event.Skip()

    notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, on_page_changed)
    # Patch SetSelection/ChangeSelection to synchronously update controls (programmatic switches may not fire event)
    _orig_set = notebook.SetSelection
    def _patched_set(idx):
        res = _orig_set(idx)
        if 0 <= idx < len(tabs):
            model.active_tab = idx
            model.current_path = tabs[idx]["path"]
            try:
                path_ctrl.SetValue(str(tabs[idx]["path"]))
            except Exception:
                pass
            if hasattr(host, "_wx_local_controls"):
                host._wx_local_controls["listing"] = tabs[idx]["listing"]
                host._wx_local_controls["path"] = path_ctrl
        return res
    notebook.SetSelection = _patched_set
    _orig_change = notebook.ChangeSelection
    def _patched_change(idx):
        res = _orig_change(idx)
        if 0 <= idx < len(tabs):
            model.active_tab = idx
            model.current_path = tabs[idx]["path"]
            try:
                path_ctrl.SetValue(str(tabs[idx]["path"]))
            except Exception:
                pass
            if hasattr(host, "_wx_local_controls"):
                host._wx_local_controls["listing"] = tabs[idx]["listing"]
                host._wx_local_controls["path"] = path_ctrl
        return res
    notebook.ChangeSelection = _patched_change

    def close_tab(index: int | None = None):
        if len(tabs) <= 1:
            return False
        if index is None:
            index = notebook.GetSelection()
        if not (0 <= index < len(tabs)):
            return False
        active_before = notebook.GetSelection()
        tab_entry = tabs[index]
        tab_entry["closed"] = True
        # remove page
        notebook.RemovePage(index)
        # destroy panel to mimic real close but keep listing object flag?
        try:
            tab_entry["panel"].Destroy()
        except Exception:
            pass
        tabs.pop(index)
        model.tabs.pop(index)
        # adjust active
        if active_before == index:
            new_sel = min(index, len(tabs)-1)
            notebook.SetSelection(new_sel)
            model.active_tab = new_sel
            model.current_path = tabs[new_sel]["path"]
            host._wx_local_controls["listing"] = tabs[new_sel]["listing"]
            try:
                path_ctrl.SetValue(str(tabs[new_sel]["path"]))
            except Exception:
                pass
        elif active_before > index:
            # active shifted left
            model.active_tab = notebook.GetSelection()
            if 0 <= model.active_tab < len(model.tabs):
                model.current_path = tabs[model.active_tab]["path"]
                try:
                    path_ctrl.SetValue(str(tabs[model.active_tab]["path"]))
                except Exception:
                    pass
        else:
            # active unchanged
            pass
        # Clamp
        if model.active_tab >= len(model.tabs):
            model.active_tab = len(model.tabs)-1
        return True

    def notebook_context(event):
        pos = event.GetPosition()
        if pos == wx.DefaultPosition:
            idx = notebook.GetSelection()
        else:
            try:
                # HitTest returns (idx, flags)
                hit = notebook.HitTest(notebook.ScreenToClient(pos))
                idx = hit[0] if isinstance(hit, tuple) else hit
            except Exception:
                idx = notebook.GetSelection()
        if idx < 0 or idx >= notebook.GetPageCount():
            return
        menu = wx.Menu()
        close_item = menu.Append(wx.ID_ANY, t("common.close"))
        close_item.Enable(notebook.GetPageCount() > 1)
        def do_close(_evt, target=idx):
            close_tab(target)
        notebook.Bind(wx.EVT_MENU, do_close, close_item)
        notebook.PopupMenu(menu)
        menu.Destroy()

    notebook.Bind(wx.EVT_CONTEXT_MENU, notebook_context)

    # initial tab
    initial = create_tab(model.current_path)
    notebook.AddPage(initial["panel"], tab_label(model.current_path), True)
    model.active_tab = 0

    def _on_path_enter(event):
        text = path_ctrl.GetValue().strip()
        if not text:
            try:
                path_ctrl.SetValue(str(active_tab_state()["path"]))
            except Exception:
                pass
            return
        try:
            navigate(text)
            refresh()
        except Exception as error:
            wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            try:
                path_ctrl.SetValue(str(active_tab_state()["path"]))
            except Exception:
                pass

    def _update_back_button():
        try:
            btn_back.Enable(bool(model._history))
        except Exception:
            pass

    def show_drives():
        tstate = active_tab_state()
        if not tstate:
            return
        try:
            drives = list_windows_drives()
        except Exception as error:
            wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            return
        # Render drives directly without model navigation; keep history
        lst = tstate["listing"]
        try:
            lst.DeleteAllItems()
            tstate["entries"][:] = []
            # Represent drives as synthetic entries for activation
            for d in drives:
                # d may be LocalEntry from services.local_files (name, path) or Path
                name = getattr(d, "name", None) or getattr(d, "path", None) or str(d)
                path_val = getattr(d, "path", None) or name
                # Create a minimal entry with expected attributes for later activation
                class _Drv:
                    pass
                ent = _Drv()
                ent.path = Path(path_val)
                ent.is_dir = True
                ent.size = 0
                # also keep original for display
                ent._drive_name = str(name)
                tstate["entries"].append(ent)
                idx = lst.InsertItem(lst.GetItemCount(), str(name))
                lst.SetItem(idx, 1, "")
                lst.SetItem(idx, 2, t("dirs.type_folder"))
                lst.SetItem(idx, 3, "")
            try:
                path_ctrl.SetValue(t("ftp.drives"))
            except Exception:
                pass
        except RuntimeError:
            return

    def go_back_view():
        if not model.can_go_back():
            return
        try:
            model.go_back()
        except Exception as error:
            wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            return
        tstate = active_tab_state()
        if not tstate:
            return
        idx = notebook.GetSelection()
        tstate["path"] = model.current_path
        if 0 <= idx < len(model.tabs):
            model.tabs[idx] = model.current_path
        try:
            path_ctrl.SetValue(str(model.current_path))
        except Exception:
            pass
        refresh_active_tab_label(idx)
        _update_back_button()
        refresh()

    def go_parent_view():
        tstate = active_tab_state()
        if not tstate:
            return
        cur = tstate["path"]
        parent = cur.parent
        if parent == cur:
            return
        try:
            navigate(parent)
            refresh()
            _update_back_button()
        except Exception as error:
            wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)

    # wrap original navigate to update back button after any navigation
    _orig_navigate = navigate
    def _wrapped_navigate(target):
        _orig_navigate(target)
        _update_back_button()
    navigate = _wrapped_navigate

    path_ctrl.Bind(wx.EVT_TEXT_ENTER, _on_path_enter)
    btn_refresh.Bind(wx.EVT_BUTTON, lambda _e: refresh())
    btn_drives.Bind(wx.EVT_BUTTON, lambda _e: show_drives())
    btn_back.Bind(wx.EVT_BUTTON, lambda _e: go_back_view())
    btn_parent.Bind(wx.EVT_BUTTON, lambda _e: go_parent_view())

    def refresh_labels(_language=None):
        host.set_host_title(t("tabs.ftp"))
        try:
            btn_drives.SetLabel(t("ftp.drives"))
            btn_back.SetLabel(t("ftp.back"))
            btn_parent.SetLabel(t("ftp.parent"))
            btn_refresh.SetLabel(t("dirs.refresh"))
            path_label.SetLabel(t("dirs.path"))
        except Exception:
            pass
        for tab_entry in tabs:
            try:
                tab_entry["listing"].SetColumn(0, t("dirs.col_name"))
                tab_entry["listing"].SetColumn(1, t("dirs.col_size"))
                tab_entry["listing"].SetColumn(2, t("dirs.col_type"))
                tab_entry["listing"].SetColumn(3, t("dirs.col_mtime"))
                _apply_column_widths(tab_entry["listing"])
            except RuntimeError:
                continue
        # update tab labels (paths may contain same)
        for idx, te in enumerate(tabs):
            try:
                notebook.SetPageText(idx, tab_label(te["path"]))
            except Exception:
                pass

    # initial back button state
    _update_back_button()
    # expose for tests
    # keep listing pointing to active (preserve contract) plus new buttons
    host._wx_local_controls = {"listing": initial["listing"], "notebook": notebook, "path": path_ctrl, "refresh_btn": btn_refresh, "btn_drives": btn_drives, "btn_back": btn_back, "btn_parent": btn_parent, "btn_refresh": btn_refresh}
    host._wx_local_model = model
    host._wx_local_state = state
    host._wx_local_run_action = run_action
    host._wx_local_tabs = tabs
    host._wx_local_notebook = notebook
    host._wx_local_close_tab = close_tab
    host._wx_local_create_tab = lambda p: (model.new_tab(p), create_tab(Path(p)), notebook.AddPage(tabs[-1]["panel"], tab_label(Path(p)), True), refresh())
    subscribe_language_change(refresh_labels)
    def close(event):
        state["closed"] = True
        for te in tabs:
            te["closed"] = True
        unsubscribe_language_change(refresh_labels)
        event.Skip()

    host.bind_host_close(close)
    refresh()
    finish()
    return host




def build_local_files_panel(parent, path: str | Path | None = None, *, open_editor=None, open_editor_new_window=None, upload=None, run_shell=None):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_local_files(parent, path, open_editor=open_editor, open_editor_new_window=open_editor_new_window, upload=upload, run_shell=run_shell, embedded=True)


def show_local_files(parent=None, path: str | Path | None = None, *, open_editor=None, open_editor_new_window=None, upload=None, run_shell=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    _build_local_files(parent, path, open_editor=open_editor, open_editor_new_window=open_editor_new_window, upload=upload, run_shell=run_shell, embedded=False)
    return wx.ID_OK

__all__ = ["LocalBrowserModel", "LocalEntry", "file_url_payload", "open_with_system", "reveal_in_file_manager", "show_local_files", "build_local_files_panel"]
