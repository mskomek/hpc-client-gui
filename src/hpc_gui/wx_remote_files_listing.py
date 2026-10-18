"""Private wx remote-file listing component."""

from pathlib import PurePosixPath
from hpc_gui.core.i18n import current_language, t
from hpc_gui.services.files_base import RemoteEntry
from hpc_gui.services.file_filter_registry import FileFilter
from hpc_gui.services.remote_entry_format import natural_sort_key as _shared_natural_sort_key
from hpc_gui.wx_remote_files_support import _format_mtime, _fmt_size, _type_label
from hpc_gui.wx_file_list_style import alternate_row_colour
from hpc_gui.wx_file_type_icons import file_type_icon_index, install_file_type_icons


def install_listing(view):
    _available = view._available
    _current_navigation_store = view._current_navigation_store
    activate = view.activate
    btn_back = view.btn_back
    btn_delete = view.btn_delete
    btn_download = view.btn_download
    btn_favorites = view.btn_favorites
    btn_forward = view.btn_forward
    btn_history = view.btn_history
    btn_new_file = view.btn_new_file
    btn_new_folder = view.btn_new_folder
    btn_refresh = view.btn_refresh
    btn_undo = view.btn_undo
    btn_up = view.btn_up
    btn_upload = view.btn_upload
    context = view.context
    file_filter_registry = view.file_filter_registry
    host = view.host
    key_down = view.key_down
    middle_click = view.middle_click
    model = view.model
    next_tab_id = view.next_tab_id
    notebook = view.notebook
    operation = view.operation
    operation_supported = view.operation_supported
    path = view.path
    path_label = view.path_label
    render_for_tab = view.render_for_tab
    tabs = view.tabs
    wx = view.wx

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
        for source, provider in (("provider", view.provider_filters), ("plugin", view.plugin_filters)):
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

    def _registry_filter_ids():
        return file_filter_registry.visible_filter_ids()

    def _registry_matches(entry, filter_id):
        return file_filter_registry.matches(entry, filter_id)

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
            # Initial remote listings need a stable directory-first order too.
            # The server may return entries in arbitrary/mixed order.
            col = 0
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
        stripe = alternate_row_colour(wx)
        current_path = PurePosixPath(tab_entry.get("path") or "/")
        parent_path = current_path.parent
        has_parent = parent_path != current_path
        parent_entry = RemoteEntry("..", str(parent_path), True) if has_parent else None
        visible_entries = ([parent_entry] if parent_entry else []) + list(entries)
        tab_entry["entries"] = visible_entries
        for row_index, entry in enumerate(visible_entries):
            is_parent = parent_entry is not None and row_index == 0
            name = ".." if is_parent else (PurePosixPath(entry.path).name or entry.path)
            idx = listing.InsertItem(listing.GetItemCount(), name)
            listing.SetItemImage(
                idx,
                file_type_icon_index(
                    name,
                    bool(getattr(entry, "is_dir", False)),
                ),
            )
            listing.SetItem(idx, 1, _fmt_size(entry))
            listing.SetItem(idx, 2, _type_label(entry))
            listing.SetItem(idx, 3, _format_mtime(getattr(entry, "mtime", None)))
            if row_index % 2:
                listing.SetItemBackgroundColour(idx, stripe)
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
        image_list = install_file_type_icons(wx, listing)
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
            "image_list": image_list,
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
                base = tab_entry.get("_sorted_entries", tab_entry.get("full_entries", tab_entry.get("entries", [])))
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

    try:
        file_filter_registry.replace_external(_external_filter_defs())
    except ValueError:
        file_filter_registry.replace_external(())

    view._filter_label = _filter_label
    view._external_filter_defs = _external_filter_defs
    view._rebuild_filter_pages = _rebuild_filter_pages
    view.refresh_provider_filters = refresh_provider_filters
    view._registry_filter_ids = _registry_filter_ids
    view._registry_matches = _registry_matches
    view.tab_label = tab_label
    view.active_tab_state = active_tab_state
    view.sync_model_active = sync_model_active
    view.refresh_labels = refresh_labels
    view._filtered_entries = _filtered_entries
    view._apply_sort = _apply_sort
    view._populate_listing = _populate_listing
    view.create_tab = create_tab
