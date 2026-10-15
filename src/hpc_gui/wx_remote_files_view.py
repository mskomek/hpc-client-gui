"""Native wx remote browser adapter."""

from __future__ import annotations

from threading import Lock
from pathlib import PurePosixPath
from types import SimpleNamespace


from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.file_context_actions import visible_actions
from hpc_gui.services.remote_move_history import RemoteMoveHistory
from hpc_gui.services.file_filter_registry import build_core_registry
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_host import make_host
from hpc_gui.wx_remote_files_support import (
    _delete_confirm_text as _delete_confirm_text,
    _entry_name as _entry_name,
    _fmt_size as _fmt_size,
    _format_mtime as _format_mtime,
    _remote_category as _remote_category,
    _type_label as _type_label,
)
from hpc_gui.wx_remote_files_listing import install_listing
from hpc_gui.wx_remote_files_navigation import install_navigation
from hpc_gui.wx_remote_files_interactions import install_interactions
from hpc_gui.wx_remote_files_actions import install_actions
from hpc_gui.wx_remote_files_operations import install_operations


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


    state = {"closed": False, "editor_request_id": 0, "view_generation": 0, "listing_request_id": 0, "busy": False, "listing_busy": False}
    # state kept for backward compat but per-tab has own
    lock = Lock()
    move_history = RemoteMoveHistory()
    tabs: list[dict] = []
    next_tab_id = [0]

    def safe_call_after(callback, *args):
        try:
            with lock:
                if state["closed"]:
                    return
            if wx.GetApp() is None:
                return
            wx.CallAfter(callback, *args)
        except BaseException:
            return

    def confirm_remote_delete(names, location):
        prompt = _delete_confirm_text(
            names,
            location,
            generic_prompt=t("dirs.delete_confirm"),
            detail_template=t("dirs.delete_confirm_detail"),
        )
        return wx.MessageBox(
            prompt, t("dirs.delete"), wx.YES_NO | wx.ICON_WARNING
        ) == wx.YES

    def _live_visible_actions(*args, **kwargs):
        return visible_actions(*args, **kwargs)

    # Components share this private view context; each module owns one UI concern.
    _remote_view = SimpleNamespace(**locals())
    _remote_view.visible_actions = _live_visible_actions
    _remote_component_names = (
        '_apply_sort', '_commit_navigation', '_external_filter_defs', '_filter_label', '_filtered_entries', '_follow_in_existing', '_follow_in_new_tab', '_follow_in_new_window', '_get_existing_followers', '_go_back', '_go_forward', '_go_up', '_is_file_followed', 'key_down', '_populate_listing', '_rebuild_filter_pages', '_registry_filter_ids', '_registry_matches', '_restore_navigation', '_show_follow_menu', '_update_navigation_buttons', 'activate', 'active_tab_state', 'context', 'create_tab', 'load', 'middle_click', 'navigate', 'open_in_editor', 'refresh_labels', 'refresh_provider_filters', 'render_for_tab', 'run_action', 'run_direct_operation', 'run_operation', 'sync_model_active', 'tab_label'
    )
    for _component_name in _remote_component_names:
        setattr(
            _remote_view,
            _component_name,
            lambda *args, _name=_component_name, **kwargs: getattr(_remote_view, _name)(*args, **kwargs),
        )
    install_listing(_remote_view)
    install_navigation(_remote_view)
    install_operations(_remote_view)
    install_actions(_remote_view)
    install_interactions(_remote_view)
    active_tab_state = _remote_view.active_tab_state
    tab_label = _remote_view.tab_label
    refresh_labels = _remote_view.refresh_labels
    refresh_provider_filters = _remote_view.refresh_provider_filters
    create_tab = _remote_view.create_tab
    _update_navigation_buttons = _remote_view._update_navigation_buttons
    navigate = _remote_view.navigate
    _go_back = _remote_view._go_back
    _go_forward = _remote_view._go_forward
    _go_up = _remote_view._go_up
    render_for_tab = _remote_view.render_for_tab
    load = _remote_view.load
    run_action = _remote_view.run_action


    def close(_event):
        _mark_closed()
        host.Destroy()

    def _mark_closed():
        with lock:
            state["closed"] = True
            for te in tabs:
                te["closed"] = True

    def on_host_destroy(event):
        if event.GetEventObject() is host:
            unsubscribe_language_change(refresh_labels)
            _mark_closed()
        event.Skip()

    host.Bind(wx.EVT_WINDOW_DESTROY, on_host_destroy)

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
        _remote_view.provider_filters = defs
        _remote_view.plugin_filters = plugins
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
