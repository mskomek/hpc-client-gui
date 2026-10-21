"""Optional wx profile screen backed by the shared connection controller.

Facade: panel composition, wx event ownership, and public re-exports.
Model/session logic lives in wx_connection_model; profile CRUD in
_wx_connection_profiles; connect lifecycle in _wx_connection_worker.
"""

from __future__ import annotations

from threading import Thread as Thread

from hpc_gui.core._legacy_patch_targets import enable_legacy_patch_targets
from hpc_gui._wx_connection_profiles import delete_selected_profile, open_profile_dialog
from hpc_gui._wx_connection_worker import cancel_connect, disconnect_session, invalidate_host_lifetime, run_connect_selected
from hpc_gui.config.storage import load_profiles
from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.wx_connection_model import (
    HostKeyRequest,
    KeyboardInteractiveRequest,
    ProfileSummary,
    WxConnectionModel,
    _controller_disconnect_cb,  # noqa: F401 — compat re-export for tests
    _invoke_on_gui_thread,
    _provider_name,
    connect_profile,
    describe_wx_connect_failure,
    format_host_key_prompt,
    ssh_info_from_profile,
)
from hpc_gui.wx_host import make_host


def _build_connection(parent, profiles, *, connect, lifecycle, on_connected, embedded, add_connection=None, on_disconnected=None, **kwargs):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = WxConnectionModel(profiles, connect=connect)
    if connect is None:
        model._connect = lambda profile: connect_profile(profile, model)

    def _load_live_profiles() -> list:
        try:
            live = load_profiles()
            return live if isinstance(live, list) else []
        except Exception:
            return list(profiles or [])

    try:
        model.profiles = _load_live_profiles()
    except Exception:
        pass

    host, finish = make_host(parent, title=t("tabs.connection"), size=(840, 520), embedded=embedded)
    panel = wx.Panel(host)
    root = wx.BoxSizer(wx.VERTICAL)
    profiles_label = wx.StaticText(panel, label=t("connection.saved_profiles"))
    list_and_detail = wx.BoxSizer(wx.HORIZONTAL)
    list_panel = wx.Panel(panel)
    list_sizer = wx.BoxSizer(wx.VERTICAL)
    choices = wx.ListBox(list_panel, choices=[item.name for item in model.summaries()], style=wx.LB_SINGLE | wx.LB_NEEDED_SB)
    choices.SetMinSize(wx.Size(320, 240))
    list_sizer.Add(choices, 1, wx.EXPAND)
    list_panel.SetSizer(list_sizer)
    detail_panel = wx.Panel(panel)
    detail_sizer = wx.BoxSizer(wx.VERTICAL)
    detail_title = wx.StaticText(detail_panel, label=t("common.details"))
    detail_title.SetFont(detail_title.GetFont().MakeBold())
    detail_name = wx.StaticText(detail_panel, label="")
    detail_host = wx.StaticText(detail_panel, label="")
    detail_provider = wx.StaticText(detail_panel, label="")
    for lbl in (detail_name, detail_host, detail_provider):
        lbl.Wrap(360)
    detail_sizer.Add(detail_title, 0, wx.BOTTOM, 8)
    detail_sizer.Add(detail_name, 0, wx.BOTTOM, 4)
    detail_sizer.Add(detail_host, 0, wx.BOTTOM, 4)
    detail_sizer.Add(detail_provider, 0, wx.BOTTOM, 4)
    detail_panel.SetSizer(detail_sizer)
    list_and_detail.Add(list_panel, 1, wx.EXPAND | wx.RIGHT, 12)
    list_and_detail.Add(detail_panel, 1, wx.EXPAND)
    root.Add(profiles_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
    root.Add(list_and_detail, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
    status = wx.StaticText(panel, label=t("login.status_disconnected"))
    active_label = wx.StaticText(panel, label="")
    active_label.SetForegroundColour(wx.Colour(70, 70, 70))
    status_row = wx.BoxSizer(wx.HORIZONTAL)
    status_row.Add(status, 0, wx.RIGHT, 12)
    status_row.Add(active_label, 1, wx.EXPAND)
    root.Add(status_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
    from hpc_gui.wx_connection_progress import ConnectionProgressView

    connection_progress = ConnectionProgressView(wx, panel, root)
    button_row = wx.BoxSizer(wx.HORIZONTAL)
    add_button = wx.Button(panel, label=t("login.add_connection"))
    edit_button = wx.Button(panel, label=t("connection.edit_action"))
    duplicate_button = wx.Button(panel, label=t("login.duplicate"))
    delete_button = wx.Button(panel, label=t("connection.delete_action"))
    connect_button = wx.Button(panel, label=t("login.connect_selected"))
    cancel_button = wx.Button(panel, label=t("common.cancel"))
    disconnect_button = wx.Button(panel, label=t("login.disconnect"))
    for btn, name in ((add_button, "AddConnection"), (edit_button, "EditConnection"), (duplicate_button, "DuplicateProfile"), (delete_button, "DeleteProfile"), (connect_button, "ConnectSelected"), (cancel_button, "CancelConnect"), (disconnect_button, "DisconnectSession")):
        try:
            btn.SetName(name)
        except Exception:
            pass
    button_row.Add(add_button, 0, wx.RIGHT, 8)
    button_row.Add(edit_button, 0, wx.RIGHT, 8)
    button_row.Add(duplicate_button, 0, wx.RIGHT, 8)
    button_row.Add(delete_button, 0, wx.RIGHT, 8)
    button_row.AddStretchSpacer(1)
    button_row.Add(cancel_button, 0, wx.RIGHT, 8)
    button_row.Add(disconnect_button, 0, wx.RIGHT, 8)
    button_row.Add(connect_button, 0)
    root.Add(button_row, 0, wx.EXPAND | wx.ALL, 12)
    panel.SetSizer(root)

    def host_key_dialog(request: HostKeyRequest) -> str:
        def _ask() -> str:
            message = format_host_key_prompt(request)
            dialog = wx.MessageDialog(host, message, t("connection.host_key_prompt_title"), wx.YES_NO | wx.CANCEL | wx.ICON_WARNING)
            try:
                result = dialog.ShowModal()
            finally:
                dialog.Destroy()
            return "save" if result == wx.ID_YES else "once" if result == wx.ID_NO else "reject"

        return _invoke_on_gui_thread(_ask)

    def mfa_dialog(request: KeyboardInteractiveRequest) -> list[str]:
        def _ask() -> list[str]:
            answers = []
            for index, prompt in enumerate(request.prompts):
                echo = request.echo[index] if index < len(request.echo) else None
                if echo is True:
                    is_secret = False
                elif echo is False:
                    is_secret = True
                else:
                    is_secret = any(word in prompt.lower() for word in ("password", "token", "code", "otp", "pin"))
                message = f"{request.instructions}\n\n{prompt}" if request.instructions else prompt
                if is_secret:
                    dlg = wx.PasswordEntryDialog(host, message, request.title)
                else:
                    dlg = wx.TextEntryDialog(host, message, request.title)
                try:
                    if dlg.ShowModal() != wx.ID_OK:
                        return []
                    answers.append(dlg.GetValue())
                finally:
                    dlg.Destroy()
            return answers

        return _invoke_on_gui_thread(_ask)

    model._host_key_decision = host_key_dialog
    model._keyboard_interactive = mfa_dialog

    def _refresh_list(select_name=None) -> None:
        try:
            live = _load_live_profiles()
        except Exception:
            live = []
        model.profiles = live
        choices.Clear()
        for item in model.summaries():
            choices.Append(item.name)
        target = select_name or model.selected_name
        if target:
            idx = choices.FindString(target)
            if idx != wx.NOT_FOUND:
                choices.SetSelection(idx)
                model.selected_name = target
            else:
                if choices.GetCount() > 0 and select_name is None:
                    pass
                else:
                    model.selected_name = ""
                    choices.SetSelection(wx.NOT_FOUND)
        _update_detail()
        _update_button_states()

    def _update_detail() -> None:
        sel = choices.GetStringSelection()
        if not sel:
            detail_name.SetLabel("")
            detail_host.SetLabel("")
            detail_provider.SetLabel("")
            return
        prof = next((p for p in model.profiles if p.get("name") == sel), None)
        if not prof:
            detail_name.SetLabel("")
            detail_host.SetLabel("")
            detail_provider.SetLabel("")
            return
        name = str(prof.get("name", ""))
        host_val = str(prof.get("host", ""))
        user = str(prof.get("username", ""))
        identity = f"{user}@{host_val}" if user and host_val else host_val or user or ""
        provider = _provider_name(prof)
        detail_name.SetLabel(f"{t('login.profile_name_label')}: {name}")
        if identity:
            detail_host.SetLabel(f"{t('login.host')}: {identity}")
        else:
            detail_host.SetLabel("")
        if provider:
            detail_provider.SetLabel(f"{t('connection.provider')}: {provider}")
        else:
            detail_provider.SetLabel("")
        detail_panel.Layout()

    def _update_button_states() -> None:
        has_selection = bool(choices.GetStringSelection())
        is_connecting = model.controller.state.value == "connecting"
        is_connected = model.controller.state.value == "connected"
        edit_button.Enable(has_selection and not is_connecting)
        duplicate_button.Enable(has_selection and not is_connecting)
        delete_button.Enable(has_selection and not is_connecting)
        connect_button.Enable(has_selection and not is_connecting)
        cancel_button.Enable(is_connecting)
        disconnect_button.Enable(is_connected)
        add_button.Enable(not is_connecting)
        state = model.controller.state.value
        if state == "connected":
            status.SetLabel(t("login.status_connected"))
            active_name = ""
            try:
                active_name = str((model.controller.session or {}).get("profile_name") or "")
            except Exception:
                active_name = ""
            if active_name:
                sel = choices.GetStringSelection()
                if sel and sel != active_name:
                    active_label.SetLabel(f"{t('login.status_connected')}: {active_name}  —  {t('common.details') if t('common.details') != '[common.details]' else 'Selected'}: {sel}")
                else:
                    active_label.SetLabel(f"{t('login.status_connected')}: {active_name}")
            else:
                active_label.SetLabel("")
        elif state == "connecting":
            status.SetLabel(t("login.status_connecting"))
            active_label.SetLabel("")
        elif state == "failed":
            status.SetLabel(t("connection.status_failed"))
            active_label.SetLabel("")
        else:
            status.SetLabel(t("login.status_disconnected"))
            active_label.SetLabel("")

    def _update_status_from_controller():
        _update_button_states()

    def _emit_to_status(_state) -> None:
        try:
            import wx as _wx

            if _wx.App.Get() is None:
                return
            _wx.CallAfter(_update_status_from_controller)
        except Exception:
            pass

    model.controller._emit = _emit_to_status

    def select(_event):
        sel = choices.GetStringSelection()
        if sel:
            model.select(sel)
        _update_detail()
        _update_button_states()

    def refresh_labels(_language=None):
        try:
            host.set_host_title(t("tabs.connection"))
        except Exception:
            pass
        add_button.SetLabel(t("login.add_connection"))
        edit_button.SetLabel(t("connection.edit_action"))
        duplicate_button.SetLabel(t("login.duplicate"))
        delete_button.SetLabel(t("connection.delete_action"))
        connect_button.SetLabel(t("login.connect_selected"))
        cancel_button.SetLabel(t("common.cancel"))
        disconnect_button.SetLabel(t("login.disconnect"))
        profiles_label.SetLabel(t("connection.saved_profiles"))
        detail_title.SetLabel(t("common.details"))
        _update_button_states()
        _update_detail()
        if model.controller.state.value == "connected":
            status.SetLabel(t("login.status_connected"))
        elif model.controller.state.value == "connecting":
            status.SetLabel(t("login.status_connecting"))
        elif model.controller.state.value == "failed":
            status.SetLabel(t("connection.status_failed"))
        else:
            status.SetLabel(t("login.status_disconnected"))

    def _get_selection() -> str:
        try:
            return choices.GetStringSelection()
        except Exception:
            return ""

    widgets = {"connect": connect_button, "edit": edit_button, "duplicate": duplicate_button, "delete": delete_button, "add": add_button, "disconnect": disconnect_button, "cancel": cancel_button}

    def _open_dialog(mode: str, initial_name=None) -> None:
        open_profile_dialog(host, model, mode, initial_name, _get_selection, _refresh_list, connect_selected)

    def _add_connection(_event=None):
        _open_dialog("add")

    def _edit_selected(_event=None):
        _open_dialog("edit", choices.GetStringSelection())

    def _duplicate_selected(_event=None):
        _open_dialog("duplicate", choices.GetStringSelection())

    def _delete_selected(_event=None):
        delete_selected_profile(host, model, _get_selection, _refresh_list, _update_detail, _update_button_states)

    def _cancel_connect(_event=None):
        cancel_connect(model, status, _update_button_states, connection_progress)

    def _disconnect_session(_event=None):
        return disconnect_session(model, status, _update_button_states, on_disconnected)

    def connect_selected(_event=None) -> bool:
        return run_connect_selected(
            host,
            model,
            _get_selection,
            _load_live_profiles,
            widgets,
            status,
            active_label,
            _update_button_states,
            on_connected,
            connection_progress,
        )

    def on_context_menu(event):
        sel = choices.GetStringSelection()
        if not sel:
            try:
                pos = event.GetPosition()
                if pos == wx.DefaultPosition:
                    return
            except Exception:
                pass
            return
        menu = wx.Menu()
        connect_item = menu.Append(wx.ID_ANY, t("login.connect"))
        edit_item = menu.Append(wx.ID_ANY, t("connection.edit_action"))
        dup_item = menu.Append(wx.ID_ANY, t("login.duplicate"))
        menu.AppendSeparator()
        del_item = menu.Append(wx.ID_ANY, t("connection.delete_action"))
        def on_menu_connect(_e): connect_selected()
        def on_menu_edit(_e): _edit_selected()
        def on_menu_dup(_e): _duplicate_selected()
        def on_menu_del(_e): _delete_selected()
        host.Bind(wx.EVT_MENU, on_menu_connect, connect_item)
        host.Bind(wx.EVT_MENU, on_menu_edit, edit_item)
        host.Bind(wx.EVT_MENU, on_menu_dup, dup_item)
        host.Bind(wx.EVT_MENU, on_menu_del, del_item)
        host.PopupMenu(menu)
        menu.Destroy()

    choices.Bind(wx.EVT_LISTBOX, select)
    choices.Bind(wx.EVT_LISTBOX_DCLICK, connect_selected)
    choices.Bind(wx.EVT_CONTEXT_MENU, on_context_menu)
    connect_button.Bind(wx.EVT_BUTTON, connect_selected)
    add_button.Bind(wx.EVT_BUTTON, _add_connection)
    edit_button.Bind(wx.EVT_BUTTON, _edit_selected)
    duplicate_button.Bind(wx.EVT_BUTTON, _duplicate_selected)
    delete_button.Bind(wx.EVT_BUTTON, _delete_selected)
    cancel_button.Bind(wx.EVT_BUTTON, _cancel_connect)
    disconnect_button.Bind(wx.EVT_BUTTON, _disconnect_session)

    def on_right_down(event):
        try:
            index = choices.HitTest(event.GetPosition())
            if isinstance(index, tuple):
                index = index[0]
            if isinstance(index, int) and index != wx.NOT_FOUND:
                choices.SetSelection(index)
                select(None)
        except (AttributeError, TypeError):
            pass
        on_context_menu(event)
        event.Skip()

    choices.Bind(wx.EVT_RIGHT_DOWN, on_right_down)
    subscribe_language_change(refresh_labels)
    def _on_host_close(event):
        invalidate_host_lifetime(model)
        unsubscribe_language_change(refresh_labels)
        event.Skip()

    host.bind_host_close(_on_host_close)

    def _on_host_destroy(event):
        if event.GetEventObject() is host:
            invalidate_host_lifetime(model)
        event.Skip()

    host.Bind(wx.EVT_WINDOW_DESTROY, _on_host_destroy)
    _update_detail()
    _update_button_states()
    host._wx_connection_controls = {
        "choices": choices,
        "status": status,
        "active_label": active_label,
        "detail_name": detail_name,
        "detail_host": detail_host,
        "detail_provider": detail_provider,
        "connect": connect_button,
        "connect_selected": connect_button,
        "add_connection": add_button,
        "add": add_button,
        "edit": edit_button,
        "duplicate": duplicate_button,
        "delete": delete_button,
        "cancel": cancel_button,
        "disconnect": disconnect_button,
    }
    host._wx_connection_add_button = add_button
    host._wx_connection_connect_button = connect_button
    host._wx_connection_cancel_button = cancel_button
    host._wx_connection_disconnect_button = disconnect_button
    host._wx_connection_edit_button = edit_button
    host._wx_connection_duplicate_button = duplicate_button
    host._wx_connection_delete_button = delete_button
    host._wx_connection_model = model
    host._wx_connection_refresh = _refresh_list
    host._wx_connection_open_dialog = _open_dialog
    host._wx_connection_connect_selected = connect_selected
    host._wx_connection_cancel = _cancel_connect
    host._wx_connection_disconnect = _disconnect_session
    finish()
    return host


def build_connection_panel(parent, profiles=None, *, connect=None, lifecycle=None, on_connected=None, on_disconnected=None, add_connection=None, **kwargs):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_connection(parent, profiles, connect=connect, lifecycle=lifecycle, on_connected=on_connected, on_disconnected=on_disconnected, embedded=True, add_connection=add_connection, **kwargs)


def show_connection(parent=None, profiles=None, *, connect=None, lifecycle=None, on_connected=None, on_disconnected=None, add_connection=None, **kwargs) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    _build_connection(parent, profiles, connect=connect, lifecycle=lifecycle, on_connected=on_connected, on_disconnected=on_disconnected, embedded=False, add_connection=add_connection, **kwargs)
    return wx.ID_OK


__all__ = ["HostKeyRequest", "KeyboardInteractiveRequest", "ProfileSummary", "WxConnectionModel", "Thread", "connect_profile", "show_connection", "build_connection_panel", "ssh_info_from_profile", "describe_wx_connect_failure", "format_host_key_prompt"]

enable_legacy_patch_targets(
    __name__,
    {"Thread": (("hpc_gui._wx_connection_worker", "Thread"),)},
)
