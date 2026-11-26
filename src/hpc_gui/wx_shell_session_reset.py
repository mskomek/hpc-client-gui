"""Reset connection-scoped GUI views when the active SSH session ends."""

from __future__ import annotations

from threading import Thread


def _clear_transfer_workspace(session_state) -> None:
    panel = (session_state or {}).get("embedded_transfers_panel")
    if panel is None:
        return
    view = getattr(panel, "_wx_transfer_state", {})
    owner = view.get("controller") if isinstance(view, dict) else None
    engine = getattr(owner, "engine", None)
    if engine is not None:
        engine.cancel_all()
        engine.clear_pending()
    setter = getattr(panel, "_wx_transfer_set_controller", None)
    if callable(setter):
        setter(None)
    elif isinstance(view, dict):
        view["controller"] = None
    for key in ("queue_map", "failed_map", "completed_map", "row_token"):
        mapping = view.get(key) if isinstance(view, dict) else None
        if isinstance(mapping, dict):
            mapping.clear()
    controls = getattr(panel, "_wx_transfer_controls", {}) or {}
    for key in ("queue", "failed", "completed"):
        listing = controls.get(key)
        if listing is not None:
            try:
                listing.DeleteAllItems()
            except (AttributeError, RuntimeError):
                pass
    notebook = controls.get("notebook")
    if notebook is not None:
        from hpc_gui._wx_transfer_common import update_tab_counts

        update_tab_counts(notebook, view)
    status = controls.get("status")
    if status is not None:
        try:
            from hpc_gui.core.i18n import t

            status.SetLabel(t("transfer.no_active_transfer"))
        except (AttributeError, RuntimeError):
            pass


def reset_connection_views(session_state) -> None:
    """Clear the old host's terminal, remote browser and transfer history."""
    state = session_state if isinstance(session_state, dict) else {}
    terminal = state.get("_embedded_terminal_panel")
    if terminal is not None:
        model = getattr(terminal, "_wx_terminal_model", None)
        clear = getattr(model, "clear", None)
        if callable(clear):
            try:
                clear()
            except Exception:
                pass
    remote = state.get("_embedded_remote_files_panel")
    reset_remote = getattr(remote, "_wx_remote_reset", None)
    if callable(reset_remote):
        try:
            reset_remote()
        except Exception:
            pass

    _clear_transfer_workspace(state)
    generation = state.get("generation")
    controllers = tuple(state.get("transfer_sessions") or ())
    if not controllers:
        return

    def clear_after_cancel():
        for controller in controllers:
            engine = getattr(controller, "engine", None)
            wait = getattr(engine, "wait", None)
            if callable(wait):
                try:
                    wait()
                except Exception:
                    pass
        def clear_if_current():
            panel = state.get("embedded_transfers_panel")
            view = getattr(panel, "_wx_transfer_state", {}) or {}
            if state.get("generation") == generation and view.get("controller") is None:
                _clear_transfer_workspace(state)

        try:
            import wx

            wx.CallAfter(clear_if_current)
        except Exception:
            clear_if_current()

    Thread(target=clear_after_cancel, daemon=True).start()
