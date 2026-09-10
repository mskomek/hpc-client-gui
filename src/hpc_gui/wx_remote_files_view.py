"""Native wx remote browser adapter."""

from __future__ import annotations

from threading import Lock, Thread
from pathlib import PurePosixPath


from hpc_gui.core.i18n import current_language, subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, context_selection, visible_actions
from hpc_gui.services.file_clipboard import get_file_clipboard
from hpc_gui.services.remote_move_history import RemoteMoveHistory
from hpc_gui.services.file_filter_registry import build_core_registry, FileFilter
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_host import make_host
from hpc_gui.ui.models.remote_entry_helpers import category as _shared_category, file_type as _shared_file_type, fmt_mtime as _shared_fmt_mtime, fmt_size as _shared_fmt_size, natural_sort_key as _shared_natural_sort_key


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


def _remote_category(entry) -> str:
    try:
        return _shared_category(entry)
    except AttributeError:
        return "folders" if getattr(entry, "is_dir", False) else "other"


def _fmt_size(entry) -> str:
    return _shared_fmt_size(getattr(entry, "size", 0))


def _build_remote_files(parent, model: WxRemoteDirectoryModel | None = None, *, loader=None, operation=None, read_text=None, open_editor=None, open_editor_new_window=None, run_shell=None, chmod=None, submit_slurm=None, operation_supported=None, chmod_supported=None, submit_slurm_supported=None, embedded, navigation_store=None, provider_filters=None, plugin_filters=None):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = model or WxRemoteDirectoryModel()
    host, finish = make_host(parent, title=t("tabs.ftp"), size=(920, 620), embedded=embedded)
    panel = wx.Panel(host)
    root = wx.BoxSizer(wx.VERTICAL)
    # --- toolbar (Qt parity). Only keys existing in both en/tr instantiated.
    # Existing: dirs.new_folder, new_file, upload, download_selected, delete, undo, favorites, history, refresh
    # Missing filter keys (dirs.filter_*) omitted entirely.
    # WrapSizer so the row flows onto a second line in a narrow pane instead of
    # clipping. Hiding buttons to make the row fit would remove functionality.
    toolbar = wx.WrapSizer(wx.HORIZONTAL)
    btn_new_folder = wx.Button(panel, label=t("dirs.new_folder"))
    btn_new_file = wx.Button(panel, label=t("dirs.new_file"))
    btn_upload = wx.Button(panel, label=t("dirs.upload"))
    btn_download = wx.Button(panel, label=t("dirs.download_selected"))
    btn_delete = wx.Button(panel, label=t("dirs.delete"))
    btn_undo = wx.Button(panel, label=t("dirs.undo"))
    btn_favorites = wx.Button(panel, label=t("dirs.favorites"))
    btn_history = wx.Button(panel, label=t("dirs.history"))
    btn_refresh = wx.Button(panel, label=t("dirs.refresh"))
    btn_back = wx.Button(panel, label=t("dirs.back"))
    btn_forward = wx.Button(panel, label=t("dirs.forward"))
    btn_up = wx.Button(panel, label=t("dirs.up"))
    for button, key in ((btn_back, "dirs.back"), (btn_forward, "dirs.forward"), (btn_up, "dirs.up")):
        button.SetToolTip(t(key))
    for b in (btn_back, btn_forward, btn_up, btn_new_folder, btn_new_file, btn_upload, btn_download, btn_delete, btn_undo, btn_favorites, btn_history, btn_refresh):
        toolbar.Add(b, 0, wx.ALL, 3)
    def _available(callback, supported=None):
        if not callable(callback):
            return False
        try:
            return bool(supported() if callable(supported) else True)
        except Exception:
            return False

    btn_new_file.Enable(_available(operation, operation_supported))
    def _current_navigation_store():
        store = navigation_store() if callable(navigation_store) else navigation_store
        return store

    def _navigate_to_path(target_path, kind="directory"):
        """Navigate to a stored path, highlighting files after listing."""
        if not target_path:
            return
        target = str(PurePosixPath(target_path).parent) if kind == "file" else str(target_path)
        navigate(target)
        if kind == "file":
            active_tab_state()["highlight_path"] = str(target_path)
        load()

    # Wire favorites/history; the store can be replaced after connection.
    def _on_favorites(_evt):
        store = _current_navigation_store()
        favs = store.favorites() if store is not None else []
        menu = wx.Menu()
        for fav in favs:
            label = fav.get("label", fav.get("path", "?"))
            path_value = fav.get("path", "")
            item = menu.Append(wx.ID_ANY, label)
            menu.Bind(wx.EVT_MENU, lambda e, p=path_value, k=fav.get("kind", "directory"): _navigate_to_path(p, k), id=item.GetId())
        if not favs:
            menu.Append(wx.ID_NONE, t("dirs.favorites_unavailable"))
        menu.AppendSeparator()
        add_item = menu.Append(wx.ID_ANY, t("dirs.favorite_add"))
        menu.Bind(wx.EVT_MENU, lambda e: store and store.add_favorite(model.current_path, "directory"), add_item)
        panel.PopupMenu(menu)
        menu.Destroy()

    def _on_history(_evt):
        store = _current_navigation_store()
        hist = store.history() if store is not None else []
        menu = wx.Menu()
        for entry in hist[:20]:
            path_value = entry.get("path", "")
            item = menu.Append(wx.ID_ANY, path_value)
            menu.Bind(wx.EVT_MENU, lambda e, p=path_value: _navigate_to_path(p), id=item.GetId())
        if not hist:
            menu.Append(wx.ID_NONE, t("dirs.history_unavailable"))
        menu.AppendSeparator()
        clear_item = menu.Append(wx.ID_ANY, t("dirs.history_clear"))
        menu.Bind(wx.EVT_MENU, lambda e: store and store.clear_history(), clear_item)
        panel.PopupMenu(menu)
        menu.Destroy()

    if _current_navigation_store() is None:
        btn_favorites.Disable()
        btn_history.Disable()
    btn_favorites.Bind(wx.EVT_BUTTON, _on_favorites)
    btn_history.Bind(wx.EVT_BUTTON, _on_history)
    refresh_btn = btn_refresh  # alias for legacy name
    path_label = wx.StaticText(panel, label=t("dirs.path"))
    path = wx.TextCtrl(panel, value=model.current_path, style=wx.TE_PROCESS_ENTER)
    path_row = wx.BoxSizer(wx.HORIZONTAL)
    path_row.Add(path_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    path_row.Add(path, 1, wx.EXPAND | wx.ALL, 4)
    notebook = wx.Notebook(panel)
    root.Add(toolbar, 0, wx.EXPAND)
    root.Add(path_row, 0, wx.EXPAND | wx.ALL, 2)
    root.Add(notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
    panel.SetSizer(root)

    # --- File filter registry (replaces hardcoded categories) ---
    file_filter_registry = build_core_registry()

    def _filter_label(filt):
        if filt is None:
            return ""
        if filt.source == "core":
            translated = t(f"dirs.tab_{filt.id}")
            if not translated.startswith("["):
                return translated
        return filt.label_for(current_language())

    def _external_filter_defs():
        result = []
        for source, provider in (("provider", provider_filters), ("plugin", plugin_filters)):
            defs = provider() if callable(provider) else provider
            if not isinstance(defs, (list, tuple)):
                continue
            for ff in defs:
                if not isinstance(ff, dict):
                    continue
                labels = ff.get("labels") or {}
                fid = str(ff.get("id", "")).strip()
                if not fid or not isinstance(labels, dict):
                    continue
                try:
                    order = int(ff.get("order", 1000))
                except (TypeError, ValueError):
                    continue
                result.append(FileFilter(
                    id=fid,
                    label_en=str(labels.get("en", fid)),
                    label_tr=str(labels.get("tr", labels.get("en", fid))),
                    globs=tuple(str(value) for value in (ff.get("globs") or ())),
                    suffixes=tuple(str(value) for value in (ff.get("suffixes") or ())),
                    order=order,
                    source=source,
                ))
        return result

    def _rebuild_filter_pages(tab_entry):
        filter_nb = tab_entry["filter_notebook"]
        old_filter = tab_entry.get("filter", "all")
        filter_nb.DeleteAllPages()
        filter_ids = _registry_filter_ids()
        tab_entry["filter_ids"] = filter_ids
        for fid in filter_ids:
            filter_nb.AddPage(wx.Panel(filter_nb), _filter_label(file_filter_registry.get(fid)))
        tab_entry["filter"] = old_filter if old_filter in filter_ids else "all"
        try:
            filter_nb.SetSelection(filter_ids.index(tab_entry["filter"]))
        except (ValueError, RuntimeError):
            filter_nb.SetSelection(0)

    def refresh_provider_filters(_event=None):
        try:
            file_filter_registry.replace_external(_external_filter_defs())
        except ValueError:
            # Collision is a trust-boundary failure; retain core filters only.
            file_filter_registry.replace_external(())
        for tab_entry in tabs:
            _rebuild_filter_pages(tab_entry)
            render_for_tab(tab_entry, tab_entry.get("full_entries", ()))
        store = _current_navigation_store()
        btn_favorites.Enable(store is not None)
        btn_history.Enable(store is not None)
        btn_back.Enable(bool(active_tab_state() and active_tab_state().get("back_stack")))
        btn_forward.Enable(bool(active_tab_state() and active_tab_state().get("forward_stack")))
        btn_up.Enable(bool(active_tab_state() and active_tab_state().get("path", "/") != "/"))
        btn_new_file.Enable(_available(operation, operation_supported))

    try:
        file_filter_registry.replace_external(_external_filter_defs())
    except ValueError:
        file_filter_registry.replace_external(())

    def _registry_filter_ids():
        return file_filter_registry.visible_filter_ids()

    def _registry_matches(entry, filter_id):
        return file_filter_registry.matches(entry, filter_id)



    state = {"closed": False, "editor_request_id": 0, "view_generation": 0, "listing_request_id": 0, "busy": False, "listing_busy": False}
    # state kept for backward compat but per-tab has own
    lock = Lock()
    move_history = RemoteMoveHistory()
    tabs: list[dict] = []
    next_tab_id = [0]

    def safe_call_after(callback, *args):
        try:
            if wx.GetApp() is None:
                return
            wx.CallAfter(callback, *args)
        except BaseException:
            return

    def tab_label(remote_path: str) -> str:
        cleaned = (remote_path or "/").rstrip("/") or "/"
        return cleaned.rsplit("/", 1)[-1] or cleaned

    def active_tab_state():
        sel = notebook.GetSelection()
        if sel < 0 or sel >= len(tabs):
            return tabs[0] if tabs else None
        return tabs[sel]

    def sync_model_active():
        tstate = active_tab_state()
        if not tstate:
            return
        idx = notebook.GetSelection()
        model.active_tab = idx
        if idx < len(model.tabs):
            model.current_path = tstate["path"]
        path.SetValue(tstate["path"])

    def refresh_labels(_language=None):
        host.set_host_title(t("tabs.ftp"))
        try:
            btn_new_folder.SetLabel(t("dirs.new_folder"))
            btn_new_file.SetLabel(t("dirs.new_file"))
            btn_upload.SetLabel(t("dirs.upload"))
            btn_download.SetLabel(t("dirs.download_selected"))
            btn_delete.SetLabel(t("dirs.delete"))
            btn_undo.SetLabel(t("dirs.undo"))
            btn_favorites.SetLabel(t("dirs.favorites"))
            btn_history.SetLabel(t("dirs.history"))
            btn_refresh.SetLabel(t("dirs.refresh"))
            path_label.SetLabel(t("dirs.path"))
        except Exception:
            pass
        for te in tabs:
            try:
                te["listing"].SetColumn(0, t("dirs.col_name"))
                te["listing"].SetColumn(1, t("dirs.col_size"))
                te["listing"].SetColumn(2, t("dirs.col_type"))
                te["listing"].SetColumn(3, t("dirs.col_mtime"))
                btn_back.SetLabel(t("dirs.back"))
                btn_forward.SetLabel(t("dirs.forward"))
                btn_up.SetLabel(t("dirs.up"))
                btn_back.SetToolTip(t("dirs.back"))
                btn_forward.SetToolTip(t("dirs.forward"))
                btn_up.SetToolTip(t("dirs.up"))
                # update filter tab labels
                fb = te.get("filter_notebook")
                if fb is not None:
                    for idx2, fid in enumerate(te.get("filter_ids", _registry_filter_ids())):
                        try:
                            fb.SetPageText(idx2, _filter_label(file_filter_registry.get(fid)))
                        except Exception:
                            pass
            except RuntimeError:
                continue
            idx = tabs.index(te)
            try:
                notebook.SetPageText(idx, tab_label(te["path"]))
            except Exception:
                pass

    def _filtered_entries(tab_entry, entries):
        cat = tab_entry.get("filter", "all")
        if cat == "all":
            return list(entries)
        return [e for e in entries if _registry_matches(e, cat)]

    def _apply_sort(tab_entry):
        col = tab_entry.get("sort_col", -1)
        reverse = tab_entry.get("sort_reverse", False)
        base = list(tab_entry.get("full_entries", []))
        if col < 0:
            tab_entry["_sorted_entries"] = base
            return
        def _sort_key(entry):
            name = PurePosixPath(entry.path).name or entry.path
            if col == 0:
                return (0, _shared_natural_sort_key(name))
            elif col == 1:
                return (0, getattr(entry, "size", 0))
            elif col == 2:
                return (0, _type_label(entry).lower())
            elif col == 3:
                return (0, getattr(entry, "mtime", 0) or 0)
            return (0, name)
        def _is_dir(entry):
            return bool(getattr(entry, "is_dir", False))
        # Group folders independently from the sort direction: reverse name
        # or size must never move files above directories.
        directories = [entry for entry in base if _is_dir(entry)]
        files = [entry for entry in base if not _is_dir(entry)]
        directories.sort(key=_sort_key, reverse=reverse)
        files.sort(key=_sort_key, reverse=reverse)
        base = directories + files
        tab_entry["_sorted_entries"] = base

    def _populate_listing(listing, entries, tab_entry):
        listing.DeleteAllItems()
        for entry in entries:
            idx = listing.InsertItem(listing.GetItemCount(), PurePosixPath(entry.path).name or entry.path)
            listing.SetItem(idx, 1, _fmt_size(entry))
            listing.SetItem(idx, 2, _type_label(entry))
            listing.SetItem(idx, 3, _format_mtime(getattr(entry, "mtime", None)))
            if tab_entry.get("highlight_path") and str(entry.path) == tab_entry["highlight_path"]:
                listing.Select(idx)
                listing.Focus(idx)
                listing.EnsureVisible(idx)

    def create_tab(remote_path: str):
        remote_path = str(PurePosixPath(remote_path or "/"))
        remote_path = remote_path or "/"
        tab_panel = wx.Panel(notebook)
        filter_nb = wx.Notebook(tab_panel)
        filter_ids = _registry_filter_ids()
        for fid in filter_ids:
            filt = file_filter_registry.get(fid)
            p = wx.Panel(filter_nb)
            filter_nb.AddPage(p, _filter_label(filt) or fid)

        listing = wx.ListCtrl(tab_panel, style=wx.LC_REPORT | wx.LC_HRULES)
        listing.InsertColumn(0, t("dirs.col_name"))
        listing.InsertColumn(1, t("dirs.col_size"))
        listing.InsertColumn(2, t("dirs.col_type"))
        listing.InsertColumn(3, t("dirs.col_mtime"))
        listing.SetColumnWidth(0, 250)
        listing.SetColumnWidth(1, 90)
        listing.SetColumnWidth(2, 160)
        listing.SetColumnWidth(3, 120)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(filter_nb, 0, wx.EXPAND)
        sizer.Add(listing, 1, wx.EXPAND)
        tab_panel.SetSizer(sizer)
        tab_entry = {
            "id": next_tab_id[0], "path": remote_path, "listing": listing,
            "panel": tab_panel, "entries": [], "full_entries": [], "filter": "all",
            "filter_notebook": filter_nb, "view_generation": 0,
            "listing_request_id": 0, "busy": False, "listing_busy": False,
            "closed": False, "sort_col": -1, "sort_reverse": False,
            "filter_ids": filter_ids, "back_stack": [], "forward_stack": [],
            "pending_navigation": None, "highlight_path": "",
        }
        next_tab_id[0] += 1
        tabs.append(tab_entry)

        def _on_filter_changed(evt):
            sel = filter_nb.GetSelection()
            current_filter_ids = tab_entry.get("filter_ids", ())
            if sel < 0 or sel >= len(current_filter_ids):
                evt.Skip()
                return
            tab_entry["filter"] = current_filter_ids[sel]
            try:
                base = tab_entry.get("full_entries", tab_entry.get("entries", []))
                visible = _filtered_entries(tab_entry, base)
                tab_entry["entries"] = visible
                _populate_listing(listing, visible, tab_entry)
                if notebook.GetSelection() == tabs.index(tab_entry):
                    host._wx_remote_controls["listing"] = listing
            except RuntimeError:
                pass
            evt.Skip()

        def _on_col_click(evt):
            col = evt.GetColumn()
            if col < 0:
                return
            if tab_entry["sort_col"] == col:
                tab_entry["sort_reverse"] = not tab_entry["sort_reverse"]
            else:
                tab_entry["sort_col"] = col
                tab_entry["sort_reverse"] = False
            _apply_sort(tab_entry)
            visible = _filtered_entries(tab_entry, tab_entry.get("_sorted_entries", tab_entry.get("full_entries", [])))
            tab_entry["entries"] = visible
            _populate_listing(listing, visible, tab_entry)
            evt.Skip()

        filter_nb.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, _on_filter_changed)
        listing.Bind(wx.EVT_LIST_COL_CLICK, _on_col_click)
        listing.Bind(wx.EVT_LIST_ITEM_ACTIVATED, activate)
        listing.Bind(wx.EVT_CONTEXT_MENU, context)
        listing.Bind(wx.EVT_KEY_DOWN, key_down)
        listing.Bind(wx.EVT_MIDDLE_DOWN, middle_click)
        return tab_entry

    def _update_navigation_buttons():
        tstate = active_tab_state()
        btn_back.Enable(bool(tstate and tstate.get("back_stack")))
        btn_forward.Enable(bool(tstate and tstate.get("forward_stack")))
        btn_up.Enable(bool(tstate and tstate.get("path", "/") != "/"))

    def navigate(target, *, history_action="new"):
        tstate = active_tab_state()
        if not tstate:
            return
        target = str(PurePosixPath(str(target or "/"))) or "/"
        tstate_path_before = tstate["path"]
        if target != tstate_path_before:
            tstate["pending_navigation"] = (
                tstate_path_before,
                list(tstate.get("back_stack", ())),
                list(tstate.get("forward_stack", ())),
            )
            if history_action == "new":
                tstate["back_stack"].append(tstate_path_before)
                tstate["forward_stack"].clear()
            elif history_action == "back":
                if tstate["back_stack"] and tstate["back_stack"][-1] == target:
                    tstate["back_stack"].pop()
                tstate["forward_stack"].append(tstate_path_before)
            elif history_action == "forward":
                if tstate["forward_stack"] and tstate["forward_stack"][-1] == target:
                    tstate["forward_stack"].pop()
                tstate["back_stack"].append(tstate_path_before)
            state["view_generation"] += 1
            tstate["view_generation"] += 1
        model.navigate(target)
        tstate["path"] = model.current_path
        idx = notebook.GetSelection()
        if 0 <= idx < len(model.tabs):
            model.tabs[idx] = model.current_path
        path.SetValue(model.current_path)
        try:
            notebook.SetPageText(idx, tab_label(model.current_path))
        except Exception:
            pass
        _update_navigation_buttons()
        store = _current_navigation_store()
        if store:
            try:
                store.record_visit(model.current_path)
            except Exception:
                pass

    def _restore_navigation(tstate):
        pending = tstate.get("pending_navigation")
        if not pending:
            return
        old_path, back_stack, forward_stack = pending
        tstate["path"] = old_path
        tstate["back_stack"] = back_stack
        tstate["forward_stack"] = forward_stack
        tstate["pending_navigation"] = None
        model.navigate(old_path)
        path.SetValue(old_path)
        idx = notebook.GetSelection()
        if 0 <= idx < notebook.GetPageCount():
            notebook.SetPageText(idx, tab_label(old_path))
        _update_navigation_buttons()

    def _commit_navigation(tstate):
        tstate["pending_navigation"] = None
        tstate["highlight_path"] = tstate.get("highlight_path", "")
        _update_navigation_buttons()

    def _go_back(_event=None):
        tstate = active_tab_state()
        if not tstate or not tstate.get("back_stack"):
            return
        target = tstate["back_stack"][-1]
        navigate(target, history_action="back")
        load()

    def _go_forward(_event=None):
        tstate = active_tab_state()
        if not tstate or not tstate.get("forward_stack"):
            return
        target = tstate["forward_stack"][-1]
        navigate(target, history_action="forward")
        load()

    def _go_up(_event=None):
        tstate = active_tab_state()
        if tstate and tstate.get("path", "/") != "/":
            navigate(str(PurePosixPath(tstate["path"]).parent))
            load()

    def render_for_tab(tab_entry, entries):
        tab_entry["full_entries"] = list(entries)
        _apply_sort(tab_entry)
        visible = _filtered_entries(tab_entry, tab_entry.get("_sorted_entries", entries))
        tab_entry["entries"] = visible
        try:
            _populate_listing(tab_entry["listing"], visible, tab_entry)
        except RuntimeError:
            return

    def load(_event=None):
        tstate = active_tab_state()
        if not tstate or not loader:
            return
        requested_path_text = path.GetValue().strip()
        if requested_path_text != tstate["path"]:
            try:
                navigate(requested_path_text)
                tstate = active_tab_state()
                requested_path_text = tstate["path"]
            except Exception as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                path.SetValue(tstate["path"])
                return
        else:
            # also ensure navigation sync
            requested_path_text = tstate["path"]
        with lock:
            if state["closed"] or tstate.get("closed"):
                return
            state["listing_busy"] = True
            state["listing_request_id"] += 1
            tstate["listing_busy"] = True
            tstate["listing_request_id"] += 1
            tstate["view_generation"] = tstate.get("view_generation", 0)
            request_id = tstate["listing_request_id"]
            request_generation = tstate["view_generation"]
            requested_path = requested_path_text
            tab_id = tstate["id"]

        def done(entries, error):
            with lock:
                tab_entry = next((tt for tt in tabs if tt["id"] == tab_id), None)
                if not tab_entry or tab_entry.get("closed"):
                    return
                current = (
                    not state["closed"]
                    and request_id == tab_entry["listing_request_id"]
                    and request_generation == tab_entry["view_generation"]
                    and requested_path == tab_entry["path"]
                )
                if current:
                    tab_entry["listing_busy"] = False
                    state["listing_busy"] = False
            if not current:
                return
            if error:
                _restore_navigation(tab_entry)
                # only show error if this tab is active
                if notebook.GetSelection() == tabs.index(tab_entry):
                    wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                _commit_navigation(tab_entry)
                render_for_tab(tab_entry, entries)

        def worker():
            try:
                safe_call_after(done, model.list_entries(loader, path=requested_path, force=True), None)
            except Exception as error:
                safe_call_after(done, (), error)

        Thread(target=worker, daemon=True).start()

    def activate(event):
        tstate = active_tab_state()
        if not tstate:
            return
        idx = event.GetIndex()
        if idx < 0 or idx >= len(tstate["entries"]):
            return
        entry = tstate["entries"][idx]
        if entry.is_dir:
            navigate(entry.path)
            load()
        elif open_editor:
            open_in_editor(entry.path, open_editor)

    def middle_click(event):
        tstate = active_tab_state()
        if not tstate:
            event.Skip()
            return
        listing = tstate["listing"]
        pos = event.GetPosition()
        idx, _ = listing.HitTest(pos)
        if 0 <= idx < len(tstate["entries"]):
            entry = tstate["entries"][idx]
            if entry.is_dir:
                # open in new visible tab
                model.new_tab(entry.path)
                new_entry = create_tab(entry.path)
                notebook.AddPage(new_entry["panel"], tab_label(entry.path), True)
                # sync after creation
                model.active_tab = notebook.GetSelection()
                model.current_path = entry.path
                path.SetValue(entry.path)
                # update controls for tests
                host._wx_remote_controls["listing"] = new_entry["listing"]
                host._wx_remote_controls["path"] = path
                load()
                return
        event.Skip()

    def context(event):
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
        selected_entries = tuple(entry for idx, entry in enumerate(entries) if listing.IsSelected(idx))
        clicked = entries[index] if 0 <= index < len(entries) else None
        selection = context_selection(
            clicked.path if clicked else None,
            clicked.is_dir if clicked else None,
            tuple(entry.path for entry in selected_entries),
            tuple(entry.is_dir for entry in selected_entries),
            background=index < 0 and not keyboard_context,
        )
        selected = selection.effective_paths
        menu = wx.Menu()
        candidate_actions = ("open", "edit", "edit_new_window", "run_shell", "follow_track", "download", "upload", "copy", "move", "rename", "delete", "paste", "copy_path", "refresh", "new_folder", "new_file", "chmod", "submit_slurm", "favorite", "new_tab")
        allowed = visible_actions(selection, remote=True)
        if not callable(getattr(panel, "_follow_callback", None)):
            allowed = tuple(action for action in allowed if action != "follow_track")
        if not _available(chmod, chmod_supported):
            allowed = tuple(action for action in allowed if action != "chmod")
        if not _available(submit_slurm, submit_slurm_supported):
            allowed = tuple(action for action in allowed if action != "submit_slurm")
        if not _available(operation, operation_supported):
            allowed = tuple(action for action in allowed if action != "new_file")
        if _current_navigation_store() is None:
            allowed = tuple(action for action in allowed if action != "favorite")
        actions = tuple(action for action in candidate_actions if action in allowed)
        labels = FILE_CONTEXT_LABEL_KEYS
        for action in actions:
            item = menu.Append(wx.ID_ANY, t(labels.get(action, f"dirs.{action}")))
            target_dir = clicked.path if clicked and clicked.is_dir else tstate["path"]
            listing.Bind(wx.EVT_MENU, lambda _event, action=action, target=target_dir: run_action(action, selected, target), item)
        listing.PopupMenu(menu)
        menu.Destroy()

    def run_action(action, selected, target_dir=None):
        tstate = active_tab_state()
        if not tstate:
            return
        if action == "run_shell" and run_shell and selected:
            run_shell(selected[0])
            return
        if action == "refresh":
            load()
            return
        if action == "new_tab" and selected:
            model.new_tab(selected[0])
            new_entry = create_tab(selected[0])
            notebook.AddPage(new_entry["panel"], tab_label(selected[0]), True)
            model.active_tab = notebook.GetSelection()
            model.current_path = selected[0]
            path.SetValue(model.current_path)
            host._wx_remote_controls["listing"] = new_entry["listing"]
            load()
            return
        if action in {"copy", "cut"} and selected:
            get_file_clipboard().set("move" if action == "cut" else "copy", list(selected))
            return
        if action == "copy_path" and selected:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject("\r\n".join(selected)))
                wx.TheClipboard.Close()
            return
        if action == "follow_track" and selected:
            # Follow/Track: create a submenu with output targets
            _show_follow_menu(selected[0])
            return
        if action == "undo":
            record = move_history.pop_last()
            if not record:
                return
            inverse = tuple((moved, original) for original, moved in record.moves)
            def undo_done(error):
                with lock:
                    # busy per tab?
                    tstate["busy"] = False
                    state["busy"] = False
                if state["closed"] or tstate.get("closed"):
                    return
                try:
                    tstate["listing"].Enable(True)
                except RuntimeError:
                    return
                if error:
                    wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                else:
                    model.invalidate()
                    load()
            def undo_operation():
                completed = 0
                try:
                    for source, destination in inverse:
                        operation("move", (source,), destination.rsplit("/", 1)[0] or "/")
                        completed += 1
                    safe_call_after(undo_done, None)
                except Exception as error:
                    if completed < len(record.moves):
                        move_history.push(type(record)(record.moves[completed:]))
                    safe_call_after(undo_done, error)
            with lock:
                if state["closed"] or tstate.get("closed") or tstate.get("busy") or state.get("busy"):
                    move_history.push(record)
                    return
                state["busy"] = True
                tstate["busy"] = True
            try:
                tstate["listing"].Enable(False)
            except RuntimeError:
                pass
            Thread(target=undo_operation, daemon=True).start()
            return
        if action == "paste":
            clipboard = get_file_clipboard().get()
            if clipboard:
                run_operation(clipboard.op, tuple(clipboard.paths), target_dir or tstate["path"], from_paste=True)
            return
        if action == "new_file" and operation:
            dlg = wx.TextEntryDialog(host, t("dirs.new_file_label"), t("dirs.new_file_title"))
            if dlg.ShowModal() == wx.ID_OK:
                name = dlg.GetValue().strip()
                if name and "/" not in name and "\\" not in name:
                    try:
                        dest = str(PurePosixPath(tstate["path"]) / name)
                        run_operation("new_file", (), dest)
                        load()
                    except Exception as error:
                        wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            dlg.Destroy()
            return
        if action == "chmod" and selected and callable(chmod):
            dlg = wx.TextEntryDialog(host, t("dirs.permissions_mode"), t("dirs.permissions_title"), "644")
            try:
                if dlg.ShowModal() != wx.ID_OK:
                    return
                mode = dlg.GetValue().strip()
                if len(mode) not in (3, 4) or any(char not in "01234567" for char in mode):
                    wx.MessageBox(t("dirs.permissions_invalid"), t("dirs.permissions_title"), wx.OK | wx.ICON_ERROR)
                    return
                run_direct_operation(lambda: chmod(selected[0], int(mode, 8)))
            finally:
                dlg.Destroy()
            return
        if action == "submit_slurm" and selected and callable(submit_slurm):
            run_direct_operation(lambda: submit_slurm(selected[0]))
            return
        if action == "favorite" and _current_navigation_store() and tstate:
            try:
                entry = next((item for item in tstate["entries"] if item.path in selected), None)
                target = entry.path if entry else tstate["path"]
                kind = "file" if entry is not None and not entry.is_dir else "directory"
                _current_navigation_store().toggle_favorite(target, kind)
            except Exception:
                pass
            return
        if action in {"open", "edit"} and open_editor and selected:
            entry = next((item for item in tstate["entries"] if item.path == selected[0]), None)
            if action == "open" and entry and entry.is_dir:
                navigate(selected[0])
                load()
            elif entry and not entry.is_dir:
                open_in_editor(selected[0], open_editor)
        elif action == "edit_new_window" and open_editor_new_window and selected:
            open_in_editor(selected[0], open_editor_new_window)
        else:
            run_operation(action, selected, target_dir or tstate["path"])

    def run_direct_operation(callback):
        """Run a safe application-owned file action off the GUI thread."""
        with lock:
            if state["closed"]:
                return
            state["busy"] = True
        def worker():
            try:
                result = callback()
                safe_call_after(direct_done, None, result)
            except Exception as error:
                safe_call_after(direct_done, error, None)
        def direct_done(error, result):
            state["busy"] = False
            if state["closed"]:
                return
            if error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                model.invalidate()
                load()
                if result is not None:
                    wx.MessageBox(str(result), t("common.info"), wx.OK | wx.ICON_INFORMATION)
        Thread(target=worker, daemon=True).start()

    def open_in_editor(remote_path, callback):
        if not read_text:
            callback(remote_path)
            return
        with lock:
            if state["closed"]:
                return
            state["editor_request_id"] += 1
            request_id = callback._wx_request_started() if getattr(callback, "_wx_request_started", None) else state["editor_request_id"]

        def done(content, error):
            if state["closed"]:
                return
            if error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                if getattr(callback, "_wx_request_aware", False):
                    callback(remote_path, content, request_id)
                else:
                    callback(remote_path, content)

        def worker():
            try:
                safe_call_after(done, read_text(remote_path), None)
            except Exception as error:
                safe_call_after(done, "", error)

        Thread(target=worker, daemon=True).start()

    def _show_follow_menu(remote_path):
        """Show a Follow/Track submenu for the selected file."""
        menu = wx.Menu()
        # Check if file is already being followed
        already_following = _is_file_followed(remote_path)
        if already_following:
            menu.Append(wx.ID_ANY, t("dirs.following") + " ✓").Enable(False)
            menu.AppendSeparator()
        item_new_tab = menu.Append(wx.ID_ANY, t("dirs.follow_new_tab"))
        item_new_window = menu.Append(wx.ID_ANY, t("dirs.follow_new_window"))
        menu.Bind(wx.EVT_MENU, lambda e: _follow_in_new_tab(remote_path), id=item_new_tab.GetId())
        menu.Bind(wx.EVT_MENU, lambda e: _follow_in_new_window(remote_path), id=item_new_window.GetId())
        # "Assign to Existing Follower" submenu
        existing_followers = _get_existing_followers()
        if existing_followers:
            menu.AppendSeparator()
            sub = wx.Menu()
            for fid, flabel in existing_followers:
                item = sub.Append(wx.ID_ANY, flabel)
                menu.Bind(wx.EVT_MENU, lambda e, fp=remote_path, fi=fid: _follow_in_existing(fp, fi), id=item.GetId())
            menu.AppendSubMenu(sub, t("dirs.follow_existing"))
        panel.PopupMenu(menu)
        menu.Destroy()

    def _get_existing_followers():
        """Get list of (tracking_id, label) for active follower tabs."""
        # Try to get from the parent Jobs workspace
        try:
            # Walk up to find the host with _wx_jobs_controls
            p = panel.GetParent()
            while p:
                controls = getattr(p, "_wx_jobs_controls", None)
                if controls and "output_channels" in controls:
                    tracked = getattr(p, "_wx_jobs_state", {}).get("tracked_outputs", ())
                    return [(item.tracking_id, item.label) for item in tracked]
                p = p.GetParent() if hasattr(p, 'GetParent') else None
        except Exception:
            pass
        return []

    def _is_file_followed(remote_path):
        """Check if a specific file path is already being followed."""
        remote_path = str(remote_path)
        try:
            p = panel.GetParent()
            while p:
                controls = getattr(p, "_wx_jobs_controls", None)
                if controls and "output_channels" in controls:
                    tracked = getattr(p, "_wx_jobs_state", {}).get("tracked_outputs", ())
                    followers = getattr(p, "_wx_jobs_state", {}).get("followers", {})
                    for item in tracked:
                        if str(getattr(item, "path", "")) == remote_path:
                            return True
                    for follower in followers.values():
                        fpath = str(getattr(getattr(follower, "state", None), "path", ""))
                        if fpath == remote_path:
                            return True
                    return False
                p = p.GetParent() if hasattr(p, 'GetParent') else None
        except Exception:
            pass
        return False

    def _follow_in_new_tab(remote_path):
        """Follow a file in a new output channel tab."""
        follow_cb = getattr(panel, "_follow_callback", None)
        if follow_cb:
            follow_cb(remote_path, "new_tab")

    def _follow_in_new_window(remote_path):
        """Follow a file in a new output window."""
        follow_cb = getattr(panel, "_follow_callback", None)
        if follow_cb:
            follow_cb(remote_path, "new_window")

    def _follow_in_existing(remote_path, follower_id):
        """Assign a file to an existing follower tab."""
        follow_cb = getattr(panel, "_follow_callback", None)
        if follow_cb:
            follow_cb(remote_path, "existing", follower_id)

    def run_operation(action, selected, target_dir=None, *, from_paste=False):
        tstate = active_tab_state()
        if not tstate:
            return
        if not operation or action in {"open", "edit", "edit_new_window"} or (not selected and action not in {"new_folder", "new_file", "upload", "paste"}):
            return
        if action == "delete" and wx.MessageBox(t("dirs.delete_confirm"), t("dirs.delete"), wx.YES_NO | wx.ICON_WARNING) != wx.YES:
            return
        destination = ""
        operation_paths = selected
        if action == "new_file":
            destination = str(target_dir or "")
        elif action == "new_folder":
            dialog = wx.TextEntryDialog(host, t("dirs.new_folder"), t("dirs.new_folder"))
            try:
                if dialog.ShowModal() != wx.ID_OK:
                    return
                new_name = dialog.GetValue().strip()
                if not new_name or PurePosixPath(new_name).name != new_name or new_name in {".", ".."}:
                    wx.MessageBox(t("dirs.rename_invalid"), t("dirs.new_folder"), wx.OK | wx.ICON_ERROR)
                    return
                destination = str(PurePosixPath(target_dir or tstate["path"]) / new_name)
            finally:
                dialog.Destroy()
        elif action in {"rename", "copy", "move"} and not from_paste:
            title_key = "dirs.rename" if action == "rename" else "dirs.destination"
            default = PurePosixPath(selected[0]).name if action == "rename" else str(PurePosixPath(selected[0]).parent)
            dialog = wx.TextEntryDialog(host, t(title_key), t(title_key), default)
            try:
                if dialog.ShowModal() != wx.ID_OK:
                    return
                new_name = dialog.GetValue().strip()
                if not new_name or (action == "rename" and (PurePosixPath(new_name).name != new_name or new_name in {".", ".."})):
                    wx.MessageBox(t("dirs.rename_invalid"), t("dirs.rename"), wx.OK | wx.ICON_ERROR)
                    return
                destination = str(PurePosixPath(selected[0]).parent / new_name) if action == "rename" else str(PurePosixPath(new_name))
            finally:
                dialog.Destroy()
        elif from_paste:
            destination = str(PurePosixPath(target_dir or tstate["path"]))
        elif action == "download":
            dialog = wx.DirDialog(host, t("dirs.local_destination"))
            try:
                if dialog.ShowModal() != wx.ID_OK:
                    return
                destination = dialog.GetPath()
            finally:
                dialog.Destroy()
        elif action == "upload":
            dialog = wx.FileDialog(host, t("ftp.upload_selected"), style=wx.FD_OPEN | wx.FD_MULTIPLE)
            try:
                if dialog.ShowModal() != wx.ID_OK:
                    return
                operation_paths = tuple(dialog.GetPaths())
                destination = target_dir or tstate["path"]
            finally:
                dialog.Destroy()
        with lock:
            if state["closed"] or tstate.get("closed") or tstate.get("busy") or state.get("busy"):
                return
            state["busy"] = True
            tstate["busy"] = True
            origin_path = tstate["path"]
            origin_generation = tstate["view_generation"]
            tab_id = tstate["id"]
        try:
            tstate["listing"].Enable(False)
        except RuntimeError:
            pass

        def worker():
            try:
                operation(action, operation_paths, destination)
                if action == "move":
                    moved = tuple(
                        (source, str(PurePosixPath(destination) / PurePosixPath(source).name))
                        for source in operation_paths
                    )
                    move_history.record(moved)
                safe_call_after(operation_done, None, tab_id, origin_path, origin_generation)
            except Exception as error:
                safe_call_after(operation_done, error, tab_id, origin_path, origin_generation)

        def operation_done(error, done_tab_id, done_origin_path, done_origin_gen):
            with lock:
                # find tab
                tab_entry = next((tt for tt in tabs if tt["id"] == done_tab_id), None)
                if tab_entry:
                    tab_entry["busy"] = False
                state["busy"] = False
            if state["closed"]:
                return
            if not tab_entry or tab_entry.get("closed"):
                return
            try:
                tab_entry["listing"].Enable(True)
            except RuntimeError:
                return
            if error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                model.invalidate()
                if tab_entry["path"] == done_origin_path and tab_entry["view_generation"] == done_origin_gen:
                    # if this tab is active, normal load, else targeted load that tab only
                    if notebook.GetSelection() == tabs.index(tab_entry):
                        load()
                    else:
                        # targeted refresh for that tab alone
                        # reuse logic: trigger worker for that tab
                        with lock:
                            if tab_entry.get("closed"):
                                return
                            tab_entry["listing_busy"] = True
                            tab_entry["listing_request_id"] += 1
                            rq_id = tab_entry["listing_request_id"]
                            rq_gen = tab_entry["view_generation"]
                            rq_path = tab_entry["path"]
                            t_id = tab_entry["id"]
                        def done2(entries, err):
                            with lock:
                                te2 = next((tt for tt in tabs if tt["id"] == t_id), None)
                                if not te2 or te2.get("closed") or rq_id != te2["listing_request_id"] or rq_gen != te2["view_generation"] or rq_path != te2["path"]:
                                    te2["listing_busy"] = False if te2 else False
                                    return
                                te2["listing_busy"] = False
                                if err:
                                    return
                                render_for_tab(te2, entries)
                            if err and notebook.GetSelection() == tabs.index(te2):
                                wx.MessageBox(str(err), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                        def wk2():
                            try:
                                safe_call_after(done2, model.list_entries(loader, path=rq_path, force=True) if loader else [], None)
                            except Exception as e2:
                                safe_call_after(done2, (), e2)
                        Thread(target=wk2, daemon=True).start()

        Thread(target=worker, daemon=True).start()

    def close(_event):
        state["closed"] = True
        for te in tabs:
            te["closed"] = True
        host.Destroy()

    def _set_navigation_store(store):
        nonlocal navigation_store
        navigation_store = store
        current = _current_navigation_store()
        btn_favorites.Enable(current is not None)
        btn_history.Enable(current is not None)

    def _set_provider_filters(defs=None, plugins=None):
        nonlocal provider_filters, plugin_filters
        provider_filters = defs
        plugin_filters = plugins
        refresh_provider_filters()

    def _reset():
        """Clear visible listings and invalidate every in-flight directory load."""
        state["view_generation"] += 1
        state["listing_request_id"] += 1
        state["busy"] = False
        state["listing_busy"] = False
        model.invalidate()
        model.current_path = "/"
        model.tabs = ["/"]
        model.active_tab = 0
        while notebook.GetPageCount() > 1:
            notebook.DeletePage(notebook.GetPageCount() - 1)
        tabs[:] = [tabs[0]]
        tab = tabs[0]
        tab.update({
            "path": "/", "entries": [], "full_entries": [], "back_stack": [], "forward_stack": [],
            "highlight_path": "", "pending_navigation": None, "busy": False,
        })
        tab["view_generation"] += 1
        tab["listing_request_id"] += 1
        tab["listing"].DeleteAllItems()
        path.SetValue("/")
        host._wx_remote_controls["listing"] = tab["listing"]
        host._wx_remote_controls["path"] = path
        _update_navigation_buttons()

    def key_down(event):
        tstate = active_tab_state()
        if not tstate:
            event.Skip()
            return
        listing = tstate["listing"]
        if event.ControlDown() and event.GetKeyCode() == ord("A"):
            for index in range(listing.GetItemCount()):
                listing.Select(index)
            return
        selected = tuple(entry.path for index, entry in enumerate(tstate["entries"]) if listing.IsSelected(index))
        if event.ControlDown() and event.GetKeyCode() in (ord("C"), ord("X"), ord("V")):
            action = {ord("C"): "copy", ord("X"): "cut", ord("V"): "paste"}[event.GetKeyCode()]
            run_action(action, selected, tstate["path"])
            return
        if event.ControlDown() and event.GetKeyCode() == ord("Z"):
            run_action("undo", selected, tstate["path"])
            return
        if event.GetKeyCode() == wx.WXK_BACK:
            navigate(str(PurePosixPath(tstate["path"]).parent))
            load()
            return
        actions = {wx.WXK_F2: "rename", wx.WXK_DELETE: "delete", wx.WXK_F5: "refresh"}
        action = actions.get(event.GetKeyCode())
        if action:
            run_action(action, selected)
            return
        event.Skip()

    def on_page_changed(event):
        new_sel = event.GetSelection()
        if 0 <= new_sel < len(tabs):
            model.active_tab = new_sel
            model.current_path = tabs[new_sel]["path"]
            path.SetValue(tabs[new_sel]["path"])
            if hasattr(host, "_wx_remote_controls"):
                host._wx_remote_controls["listing"] = tabs[new_sel]["listing"]
                host._wx_remote_controls["path"] = path
            _update_navigation_buttons()
        event.Skip()

    notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, on_page_changed)
    _orig_set = notebook.SetSelection
    def _patched_set(idx):
        res = _orig_set(idx)
        if 0 <= idx < len(tabs):
            model.active_tab = idx
            model.current_path = tabs[idx]["path"]
            path.SetValue(tabs[idx]["path"])
            if hasattr(host, "_wx_remote_controls"):
                host._wx_remote_controls["listing"] = tabs[idx]["listing"]
        return res
    notebook.SetSelection = _patched_set
    _orig_change = notebook.ChangeSelection
    def _patched_change(idx):
        res = _orig_change(idx)
        if 0 <= idx < len(tabs):
            model.active_tab = idx
            model.current_path = tabs[idx]["path"]
            path.SetValue(tabs[idx]["path"])
            if hasattr(host, "_wx_remote_controls"):
                host._wx_remote_controls["listing"] = tabs[idx]["listing"]
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
        notebook.RemovePage(index)
        try:
            tab_entry["panel"].Destroy()
        except Exception:
            pass
        tabs.pop(index)
        if 0 <= index < len(model.tabs):
            model.tabs.pop(index)
        if active_before == index:
            new_sel = min(index, len(tabs)-1)
            notebook.SetSelection(new_sel)
            model.active_tab = new_sel
            model.current_path = tabs[new_sel]["path"]
            path.SetValue(tabs[new_sel]["path"])
            host._wx_remote_controls["listing"] = tabs[new_sel]["listing"]
        elif active_before > index:
            model.active_tab = notebook.GetSelection()
            if 0 <= model.active_tab < len(model.tabs):
                model.current_path = tabs[model.active_tab]["path"]
        return True

    def notebook_context(event):
        pos = event.GetPosition()
        if pos == wx.DefaultPosition:
            idx = notebook.GetSelection()
        else:
            try:
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

    def _selected_paths_for_toolbar():
        tstate = active_tab_state()
        if not tstate:
            return (), tstate
        listing = tstate["listing"]
        return tuple(entry.path for idx, entry in enumerate(tstate["entries"]) if listing.IsSelected(idx)), tstate

    def _on_toolbar_new_folder(_evt):
        _sel, tstate = _selected_paths_for_toolbar()
        # run_operation handles dialog; pass selected and target dir
        target = tstate["path"] if tstate else "/"
        run_action("new_folder", _sel, target)

    def _on_toolbar_new_file(_evt):
        _sel, tstate = _selected_paths_for_toolbar()
        target = tstate["path"] if tstate else "/"
        run_action("new_file", _sel, target)

    def _on_toolbar_upload(_evt):
        sel, tstate = _selected_paths_for_toolbar()
        target = tstate["path"] if tstate else "/"
        run_action("upload", sel, target)

    def _on_toolbar_download(_evt):
        sel, _t = _selected_paths_for_toolbar()
        # Use existing download handling via run_operation; needs selected
        tstate = active_tab_state()
        run_action("download", sel, tstate["path"] if tstate else "/")

    def _on_toolbar_delete(_evt):
        sel, tstate = _selected_paths_for_toolbar()
        run_action("delete", sel, tstate["path"] if tstate else "/")

    def _on_toolbar_undo(_evt):
        sel, tstate = _selected_paths_for_toolbar()
        run_action("undo", sel, tstate["path"] if tstate else "/")

    btn_new_folder.Bind(wx.EVT_BUTTON, _on_toolbar_new_folder)
    btn_new_file.Bind(wx.EVT_BUTTON, _on_toolbar_new_file)
    btn_back.Bind(wx.EVT_BUTTON, _go_back)
    btn_forward.Bind(wx.EVT_BUTTON, _go_forward)
    btn_up.Bind(wx.EVT_BUTTON, _go_up)
    btn_upload.Bind(wx.EVT_BUTTON, _on_toolbar_upload)
    btn_download.Bind(wx.EVT_BUTTON, _on_toolbar_download)
    btn_delete.Bind(wx.EVT_BUTTON, _on_toolbar_delete)
    btn_undo.Bind(wx.EVT_BUTTON, _on_toolbar_undo)
    # Context actions are enabled/disabled at invocation time because the
    # active session and navigation store can change after construction.

    # initial tab
    initial = create_tab(model.current_path)
    notebook.AddPage(initial["panel"], tab_label(model.current_path), True)
    model.active_tab = 0

    refresh_btn.Bind(wx.EVT_BUTTON, load)
    path.Bind(wx.EVT_TEXT_ENTER, load)
    # disable operation-dependent buttons if no operation callback provided
    if not operation:
        for b in (btn_new_folder, btn_new_file, btn_upload, btn_download, btn_delete, btn_undo):
            try:
                b.Disable()
            except Exception:
                pass
    subscribe_language_change(refresh_labels)
    host.bind_host_close(lambda event: (unsubscribe_language_change(refresh_labels), close(event)))
    host._wx_remote_controls = {"listing": initial["listing"], "path": path, "notebook": notebook, "toolbar": toolbar, "btn_back": btn_back, "btn_forward": btn_forward, "btn_up": btn_up, "btn_new_folder": btn_new_folder, "btn_new_file": btn_new_file, "btn_upload": btn_upload, "btn_download": btn_download, "btn_delete": btn_delete, "btn_undo": btn_undo, "btn_favorites": btn_favorites, "btn_history": btn_history, "btn_refresh": btn_refresh, "path_label": path_label, "load": load, "refresh_provider_filters": refresh_provider_filters, "navigate": navigate}
    host._wx_remote_model = model
    host._wx_remote_state = state
    host._wx_remote_run_action = run_action
    host._wx_remote_tabs = tabs
    host._wx_remote_notebook = notebook
    host._wx_remote_close_tab = close_tab
    host._wx_remote_set_navigation_store = lambda store: _set_navigation_store(store)
    host._wx_remote_set_provider_filters = lambda defs=None, plugins=None: _set_provider_filters(defs, plugins)
    host._wx_remote_reset = _reset
    load()
    _update_navigation_buttons()
    finish()
    return host




def build_remote_files_panel(parent, model: WxRemoteDirectoryModel | None = None, *, loader=None, operation=None, read_text=None, open_editor=None, open_editor_new_window=None, run_shell=None, chmod=None, submit_slurm=None, operation_supported=None, chmod_supported=None, submit_slurm_supported=None, navigation_store=None, provider_filters=None, plugin_filters=None):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_remote_files(parent, model, loader=loader, operation=operation, read_text=read_text, open_editor=open_editor, open_editor_new_window=open_editor_new_window, run_shell=run_shell, chmod=chmod, submit_slurm=submit_slurm, operation_supported=operation_supported, chmod_supported=chmod_supported, submit_slurm_supported=submit_slurm_supported, embedded=True, navigation_store=navigation_store, provider_filters=provider_filters, plugin_filters=plugin_filters)


def show_remote_files(parent=None, model: WxRemoteDirectoryModel | None = None, *, loader=None, operation=None, read_text=None, open_editor=None, open_editor_new_window=None, run_shell=None, chmod=None, submit_slurm=None, operation_supported=None, chmod_supported=None, submit_slurm_supported=None, navigation_store=None, provider_filters=None, plugin_filters=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    _build_remote_files(parent, model, loader=loader, operation=operation, read_text=read_text, open_editor=open_editor, open_editor_new_window=open_editor_new_window, run_shell=run_shell, chmod=chmod, submit_slurm=submit_slurm, operation_supported=operation_supported, chmod_supported=chmod_supported, submit_slurm_supported=submit_slurm_supported, embedded=False, navigation_store=navigation_store, provider_filters=provider_filters, plugin_filters=plugin_filters)
    return wx.ID_OK

__all__ = ["show_remote_files", "build_remote_files_panel"]
