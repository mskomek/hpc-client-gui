"""wx local-file browser facade and native UI composition."""

from __future__ import annotations

import sys as sys
from pathlib import Path
from threading import Lock
from types import SimpleNamespace

from hpc_gui.core.i18n import subscribe_language_change, t
from hpc_gui.services.file_context_actions import (
    FILE_CONTEXT_LABEL_KEYS as FILE_CONTEXT_LABEL_KEYS,
    context_selection as context_selection,
    delete_confirm_message as delete_confirm_message,
    summarize_delete_targets as summarize_delete_targets,
    visible_actions as visible_actions,
)
from hpc_gui.services.local_files import list_windows_drives as list_windows_drives
from hpc_gui.wx_host import make_host
from hpc_gui.wx_local_files_model import (
    LocalBrowserModel as LocalBrowserModel,
    LocalEntry as LocalEntry,
    file_url_payload as file_url_payload,
    format_local_size as format_local_size,
    open_with_system as open_with_system,
    reveal_in_file_manager as reveal_in_file_manager,
)
from hpc_gui.wx_local_files_support import (
    _delete_confirm_text as _delete_confirm_text,
    _entry_name as _entry_name,
    _format_mtime as _format_mtime,
    _type_label as _type_label,
)
from hpc_gui.wx_local_files_listing import install_listing
from hpc_gui.wx_local_files_interactions import install_interactions
from hpc_gui.wx_local_files_mutations import install_mutations
from hpc_gui.wx_local_files_lifecycle import install_lifecycle


def _build_local_files(parent, path: str | Path | None = None, *, open_editor=None, open_editor_new_window=None, upload=None, run_shell=None, embedded):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    from hpc_gui.services.local_files import safe_initial_local_directory
    model = LocalBrowserModel(path or safe_initial_local_directory(""))
    host, finish = make_host(parent, title=t("tabs.ftp"), size=(900, 600), embedded=embedded)
    toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
    btn_drives = wx.Button(host, label=t("ftp.drives"))
    btn_back = wx.Button(host, label=t("ftp.back"))
    btn_forward = wx.Button(host, label=t("ftp.forward"))
    btn_parent = wx.Button(host, label=t("ftp.parent"))
    btn_refresh = wx.Button(host, label=t("dirs.refresh"))
    for _b in (btn_drives, btn_back, btn_forward, btn_parent, btn_refresh):
        toolbar_sizer.Add(_b, 0, wx.ALL, 4)
    # Back/Forward use real history; disabled when empty (TODO-030 deterministic state)
    try:
        btn_back.Disable()
        btn_forward.Disable()
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

    def confirm_local_delete(names, location):
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

    _orig_set = notebook.SetSelection
    _orig_change = notebook.ChangeSelection
    _local_view = SimpleNamespace(**locals())
    _local_view.visible_actions = _live_visible_actions
    _local_component_names = (
        '_apply_column_widths', '_on_path_enter', '_patched_change', '_patched_set', '_update_back_button', 'activate', 'active_listing', 'active_tab_state', 'close', 'close_tab', 'context_menu', 'create_tab', 'current_entries', 'go_back_view', 'go_forward_view', 'go_parent_view', 'key_down', 'middle_click', 'mutate', 'navigate', 'notebook_context', 'on_page_changed', 'refresh', 'refresh_active_tab_label', 'refresh_labels', 'render_entries', 'run_action', 'selected_entries', 'show_drives', 'sync_model_to_active', 'tab_label'
    )
    for _component_name in _local_component_names:
        setattr(
            _local_view,
            _component_name,
            lambda *args, _name=_component_name, **kwargs: getattr(_local_view, _name)(*args, **kwargs),
        )
    install_listing(_local_view)
    install_mutations(_local_view)
    install_interactions(_local_view)
    install_lifecycle(_local_view)
    _apply_column_widths = _local_view._apply_column_widths
    _on_path_enter = _local_view._on_path_enter
    _patched_change = _local_view._patched_change
    _patched_set = _local_view._patched_set
    _update_back_button = _local_view._update_back_button
    activate = _local_view.activate
    active_listing = _local_view.active_listing
    active_tab_state = _local_view.active_tab_state
    close = _local_view.close
    close_tab = _local_view.close_tab
    context_menu = _local_view.context_menu
    create_tab = _local_view.create_tab
    current_entries = _local_view.current_entries
    go_back_view = _local_view.go_back_view
    go_forward_view = _local_view.go_forward_view
    go_parent_view = _local_view.go_parent_view
    key_down = _local_view.key_down
    middle_click = _local_view.middle_click
    mutate = _local_view.mutate
    navigate = _local_view.navigate
    notebook_context = _local_view.notebook_context
    on_page_changed = _local_view.on_page_changed
    refresh = _local_view.refresh
    refresh_active_tab_label = _local_view.refresh_active_tab_label
    refresh_labels = _local_view.refresh_labels
    render_entries = _local_view.render_entries
    run_action = _local_view.run_action
    selected_entries = _local_view.selected_entries
    show_drives = _local_view.show_drives
    sync_model_to_active = _local_view.sync_model_to_active
    tab_label = _local_view.tab_label










    # Widths are applied before rows exist, so content autosizing measures nothing.
    # Give the fixed columns a readable floor and let Name take the remainder.











    notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, on_page_changed)
    # Patch SetSelection/ChangeSelection to synchronously update controls (programmatic switches may not fire event)
    _orig_set = notebook.SetSelection
    notebook.SetSelection = _patched_set
    _orig_change = notebook.ChangeSelection
    notebook.ChangeSelection = _patched_change



    notebook.Bind(wx.EVT_CONTEXT_MENU, notebook_context)

    # initial tab
    initial = create_tab(model.current_path)
    notebook.AddPage(initial["panel"], tab_label(model.current_path), True)
    model.active_tab = 0







    # wrap original navigate to update back button after any navigation
    _orig_navigate = navigate
    def _wrapped_navigate(target):
        _orig_navigate(target)
        _update_back_button()
    navigate = _wrapped_navigate
    _local_view.navigate = navigate

    path_ctrl.Bind(wx.EVT_TEXT_ENTER, _on_path_enter)
    btn_refresh.Bind(wx.EVT_BUTTON, lambda _e: refresh())
    btn_drives.Bind(wx.EVT_BUTTON, lambda _e: show_drives())
    btn_back.Bind(wx.EVT_BUTTON, lambda _e: go_back_view())
    btn_forward.Bind(wx.EVT_BUTTON, lambda _e: go_forward_view())
    btn_parent.Bind(wx.EVT_BUTTON, lambda _e: go_parent_view())


    # initial back button state
    _update_back_button()
    # expose for tests
    # keep listing pointing to active (preserve contract) plus new buttons
    host._wx_local_controls = {"listing": initial["listing"], "notebook": notebook, "path": path_ctrl, "refresh_btn": btn_refresh, "btn_drives": btn_drives, "btn_back": btn_back, "btn_forward": btn_forward, "btn_parent": btn_parent, "btn_refresh": btn_refresh}
    host._wx_local_model = model
    host._wx_local_refresh = refresh
    host._wx_local_state = state
    host._wx_local_run_action = run_action
    host._wx_local_tabs = tabs
    host._wx_local_notebook = notebook
    host._wx_local_close_tab = close_tab
    host._wx_local_create_tab = lambda p: (model.new_tab(p), create_tab(Path(p)), notebook.AddPage(tabs[-1]["panel"], tab_label(Path(p)), True), refresh())
    subscribe_language_change(refresh_labels)

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
