"""Guard GUI connection switches and keep alternate connect paths consistent."""

from __future__ import annotations

from hpc_gui.wx_shell_session_reset import reset_connection_views


def active_transfer_count(session_state) -> int:
    """Return active plus queued transfer items for the embedded Files view."""
    state = session_state if isinstance(session_state, dict) else {}
    panel = state.get("embedded_transfers_panel")
    view = getattr(panel, "_wx_transfer_state", {}) if panel is not None else {}
    queue = view.get("queue_map", {}) if isinstance(view, dict) else {}
    try:
        visible_count = len(queue)
    except TypeError:
        visible_count = 0

    estimated_count = 0
    for controller in tuple(state.get("transfer_sessions") or ()):
        engine = getattr(controller, "engine", None)
        if engine is None:
            estimated_count += 1
            continue
        try:
            items = len(engine.items)
            finished = len(engine.completed) + len(engine.failed)
            estimated_count += max(0, items - finished)
        except (AttributeError, TypeError):
            try:
                pending = len(engine.pending)
                running = not engine.wait(0)
                estimated_count += pending + int(running and pending == 0)
            except (AttributeError, TypeError, RuntimeError):
                estimated_count += 1
    return max(visible_count, estimated_count)


def _ask_switch_confirmation(wx, parent, count: int) -> bool:
    from hpc_gui.core.i18n import t

    message = t("connection.switch_active_transfer_message").format(count=count)
    dialog = wx.MessageDialog(
        parent,
        message,
        t("connection.switch_active_transfer_title"),
        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
    )
    try:
        return dialog.ShowModal() == wx.ID_YES
    finally:
        dialog.Destroy()


def install_connection_switch_guard(wx, connection_panel, session_state, on_disconnected) -> None:
    """Wrap every user-facing connect route with one preflight and reset hook."""
    controls = getattr(connection_panel, "_wx_connection_controls", {}) or {}
    choices = controls.get("choices")
    button = controls.get("connect")
    model = getattr(connection_panel, "_wx_connection_model", None)
    original_connect = getattr(connection_panel, "_wx_connection_connect_selected", None)
    if model is None or not callable(original_connect):
        return

    pending = {"session": None}

    def before_switch() -> bool:
        session = getattr(getattr(model, "controller", None), "session", None)
        if session is None:
            session = (session_state or {}).get("session")
        pending["session"] = session
        count = active_transfer_count(session_state)
        if session is not None and count and not _ask_switch_confirmation(wx, connection_panel, count):
            pending["session"] = None
            return False
        return True

    def after_switch() -> None:
        session = pending.pop("session", None)
        pending.clear()
        if session is None:
            return
        controller = getattr(model, "controller", None)
        if controller is not None:
            controller.session = None
        if callable(on_disconnected):
            on_disconnected(session)
        reset_connection_views(session_state)

    def guarded_connect(event=None) -> bool:
        if not before_switch():
            return False
        started = bool(original_connect(event))
        if started:
            after_switch()
        else:
            pending.clear()
        return started

    connection_panel._wx_before_connection_switch = before_switch
    connection_panel._wx_after_connection_switch = after_switch
    connection_panel._wx_connection_connect_selected = guarded_connect

    if button is not None:
        button.Unbind(wx.EVT_BUTTON)
        button.Bind(wx.EVT_BUTTON, guarded_connect)
    if choices is not None:
        choices.Unbind(wx.EVT_LISTBOX_DCLICK)
        choices.Bind(wx.EVT_LISTBOX_DCLICK, guarded_connect)
        _install_context_menu(wx, connection_panel, choices, controls, guarded_connect)


def _install_context_menu(wx, connection_panel, choices, controls, connect) -> None:
    """Keep the profile context actions while routing Connect through the guard."""
    from hpc_gui.core.i18n import t

    choices.Unbind(wx.EVT_CONTEXT_MENU)
    choices.Unbind(wx.EVT_RIGHT_DOWN)

    def on_right_down(event):
        try:
            index = choices.HitTest(event.GetPosition())
            if isinstance(index, tuple):
                index = index[0]
            if isinstance(index, int) and index != wx.NOT_FOUND:
                choices.SetSelection(index)
                selection_event = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
                selection_event.SetInt(index)
                selection_event.SetEventObject(choices)
                choices.GetEventHandler().ProcessEvent(selection_event)
        except (AttributeError, TypeError, RuntimeError):
            pass
        event.Skip()

    def trigger_button(key: str) -> None:
        target = controls.get(key)
        if target is None:
            return
        command = wx.CommandEvent(wx.EVT_BUTTON.typeId, target.GetId())
        command.SetEventObject(target)
        target.GetEventHandler().ProcessEvent(command)

    def on_context_menu(event):
        if not choices.GetStringSelection():
            return
        menu = wx.Menu()
        actions = (
            ("connect", "login.connect", connect),
            ("edit", "connection.edit_action", lambda _evt: trigger_button("edit")),
            ("duplicate", "login.duplicate", lambda _evt: trigger_button("duplicate")),
            ("delete", "connection.delete_action", lambda _evt: trigger_button("delete")),
        )
        try:
            for _key, label_key, callback in actions:
                item = menu.Append(wx.ID_ANY, t(label_key))
                menu.Bind(wx.EVT_MENU, callback, item)
            connection_panel.PopupMenu(menu)
        finally:
            menu.Destroy()

    choices.Bind(wx.EVT_RIGHT_DOWN, on_right_down)
    choices.Bind(wx.EVT_CONTEXT_MENU, on_context_menu)
