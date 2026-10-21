"""Connect-lifecycle leaf for the wx connection panel.

Owns the threaded connect worker, mid-connect cancel, and graceful
disconnect. Operates only on explicitly passed host/model/widget handles;
never imports the connection facade or the profile-CRUD leaf.
"""

from __future__ import annotations

from threading import Thread
from typing import Callable


def cancel_connect(model, status, update_button_states: Callable[[], None], progress_view=None) -> None:
    """Invalidate the current attempt and return to DISCONNECTED."""
    from hpc_gui.core.i18n import t

    try:
        model._wx_attempt += 1
    except Exception:
        pass
    try:
        model.controller.cancel_connect()
    except Exception:
        pass
    cancelled_msg = t("connection.auth_cancelled") if t("connection.auth_cancelled") != "[connection.auth_cancelled]" else "Authentication cancelled"
    model.progress_callback = None
    if progress_view is not None:
        progress_view.set_stage(t("connection.progress_cancelled"))
    status.SetLabel(cancelled_msg)
    update_button_states()


def invalidate_host_lifetime(model) -> None:
    """Invalidate in-flight work when its wx host begins teardown."""
    if getattr(model, "_wx_host_closed", False):
        return
    model._wx_host_closed = True
    model._wx_attempt += 1
    if getattr(model.controller.state, "value", None) not in {"connecting", "authenticating"}:
        return
    try:
        model.controller.cancel_token.set()
    except Exception:
        pass


def disconnect_session(model, status, update_button_states: Callable[[], None], on_disconnected=None) -> bool:
    """Tear down the live transport and notify the shell."""
    from hpc_gui.core.i18n import t
    from hpc_gui.services.connection_controller import close_session

    session = model.controller.session
    if session is None and model.controller.state.value != "connected":
        return False
    if isinstance(session, dict):
        try:
            close_session(session)
        except Exception:
            pass
    try:
        model.controller.begin_disconnect()
    except Exception:
        pass
    try:
        model.controller.finish_disconnect()
    except Exception:
        pass
    status.SetLabel(t("login.status_disconnected"))
    update_button_states()
    if on_disconnected is not None:
        try:
            on_disconnected(session)
        except Exception:
            pass
    return True


def run_connect_selected(host, model, get_selection: Callable[[], str], load_live_profiles: Callable[[], list], widgets: dict, status, active_label, update_button_states: Callable[[], None], on_connected=None, progress_view=None) -> bool:
    """Resolve credentials on the GUI thread, then connect on a worker."""
    from hpc_gui.core.i18n import t
    from hpc_gui.services.connection_controller import close_session
    from hpc_gui.wx_connection_model import connect_profile as _model_connect
    from hpc_gui.wx_connection_model import describe_wx_connect_failure

    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    sel = get_selection()
    if not sel:
        return False
    if not model.select(sel):
        return False
    stored = next((p for p in model.profiles if p.get("name") == sel), None)
    if stored is None:
        try:
            stored = next((p for p in load_live_profiles() if p.get("name") == sel), None)
        except Exception:
            stored = None
    if stored is None:
        wx.MessageBox(t("connection.profile_not_found").format(name=sel), t("login.err_title"), wx.OK | wx.ICON_WARNING)
        return False
    from hpc_gui.wx_connection_model import build_master_ask_factory

    ask_master_conn = build_master_ask_factory(host)
    try:
        from hpc_gui.services.connection_profile_service import resolve_password_for_connect

        typed_for_connect = str(stored.get("password", "") or "")
        resolved_password = resolve_password_for_connect(
            stored, typed_password=typed_for_connect, ask_master=ask_master_conn
        )
    except RuntimeError as exc:
        msg = str(exc)
        if "master_cancelled" in msg:
            status.SetLabel(t("connection.auth_cancelled"))
            update_button_states()
            return False
        elif "master_wrong" in msg:
            wx.MessageBox(t("login.err_master_wrong"), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            status.SetLabel(t("connection.status_failed"))
            try:
                model.controller.fail()
            except Exception:
                pass
            update_button_states()
            return False
        elif "saved_password_unavailable" in msg:
            wx.MessageBox(t("connection.saved_password_unavailable"), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            status.SetLabel(t("connection.status_failed"))
            try:
                model.controller.fail()
            except Exception:
                pass
            update_button_states()
            return False
        else:
            wx.MessageBox(msg, t("login.err_title"), wx.OK | wx.ICON_ERROR)
            status.SetLabel(t("connection.status_failed"))
            try:
                model.controller.fail()
            except Exception:
                pass
            update_button_states()
            return False
    except Exception as exc:
        wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR)
        status.SetLabel(t("connection.status_failed"))
        try:
            model.controller.fail()
        except Exception:
            pass
        update_button_states()
        return False
    if resolved_password is None:
        wx.MessageBox(t("connection.saved_password_unavailable"), t("login.err_title"), wx.OK | wx.ICON_ERROR)
        status.SetLabel(t("connection.status_failed"))
        try:
            model.controller.fail()
        except Exception:
            pass
        update_button_states()
        return False
    transient = dict(stored)
    transient["password"] = resolved_password if resolved_password is not None else ""
    if model.controller.session is not None:
        close_session(model.controller.session)
        model.controller.session = None
    connect_button = widgets.get("connect")
    edit_button = widgets.get("edit")
    duplicate_button = widgets.get("duplicate")
    delete_button = widgets.get("delete")
    add_button = widgets.get("add")
    disconnect_button = widgets.get("disconnect")
    cancel_button = widgets.get("cancel")
    for btn in (connect_button, edit_button, duplicate_button, delete_button, add_button, disconnect_button):
        try:
            if btn is not None:
                btn.Enable(False)
        except Exception:
            pass
    try:
        if cancel_button is not None:
            cancel_button.Enable(True)
    except Exception:
        pass
    status.SetLabel(t("login.status_connecting"))
    if progress_view is not None:
        model.progress_callback = progress_view.on_ssh_message
        progress_view.set_stage(t("connection.progress_network"), 18)
    try:
        active_label.SetLabel("")
    except Exception:
        pass
    try:
        model.controller.begin_connect()
    except Exception:
        try:
            model.controller.fail()
        except Exception:
            pass
        try:
            transient["password"] = ""
        except Exception:
            pass
        status.SetLabel(t("connection.status_failed"))
        model.progress_callback = None
        if progress_view is not None:
            progress_view.set_stage(t("connection.progress_failed"))
        update_button_states()
        return False
    model._wx_attempt += 1
    attempt = model._wx_attempt

    def worker():
        try:
            connect_fn = model._connect
            if connect_fn is None:
                def _default(profile):
                    return _model_connect(profile, model)

                connect_fn = _default
            session = connect_fn(dict(transient))
            if session is False:
                raise RuntimeError(t("login.error") if t("login.error") != "[login.error]" else "Connection failed")
            if getattr(model, "_wx_host_closed", False):
                if isinstance(session, dict):
                    close_session(session)
                transient["password"] = ""
                return
            wx.CallAfter(done, None, attempt, session)
        except Exception as error:
            if getattr(model, "_wx_host_closed", False):
                transient["password"] = ""
                return
            wx.CallAfter(done, error, attempt, None)

    def done(error, tag, session):
        try:
            transient["password"] = ""
        except Exception:
            pass
        if getattr(model, "_wx_host_closed", False) or tag != model._wx_attempt:
            if error is None and isinstance(session, dict):
                try:
                    close_session(session)
                except Exception:
                    pass
            return
        if model.controller.cancel_token.is_set():
            try:
                if isinstance(session, dict):
                    close_session(session)
            except Exception:
                pass
            try:
                model.controller.cancel_connect()
            except Exception:
                pass
            cancelled_msg = t("connection.auth_cancelled") if t("connection.auth_cancelled") != "[connection.auth_cancelled]" else "Authentication cancelled"
            model.progress_callback = None
            if progress_view is not None:
                progress_view.set_stage(t("connection.progress_cancelled"))
            status.SetLabel(cancelled_msg)
            update_button_states()
            return
        if error is None and isinstance(session, dict):
            try:
                model.controller.finish(session)
            except Exception as finish_error:
                error = finish_error
        if error:
            try:
                model.controller.fail()
            except Exception:
                pass
            status.SetLabel(t("connection.status_failed"))
            model.progress_callback = None
            if progress_view is not None:
                progress_view.set_stage(t("connection.progress_failed"))
            update_button_states()
            try:
                msg = describe_wx_connect_failure(error, resolved_password=resolved_password or "")
            except Exception:
                msg = "Connection failed"
            if "master_cancelled" in str(error):
                msg = t("connection.auth_cancelled") if t("connection.auth_cancelled") != "[connection.auth_cancelled]" else "Authentication cancelled"

                def _show_cancelled():
                    try:
                        status.SetLabel(msg)
                    except Exception:
                        pass

                try:
                    wx.CallAfter(_show_cancelled)
                except Exception:
                    status.SetLabel(msg)
                return
            wx.MessageBox(msg, t("login.err_title"), wx.OK | wx.ICON_ERROR)
            if progress_view is not None:
                progress_view.set_stage(msg)
        else:
            status.SetLabel(t("login.status_connected"))
            model.progress_callback = None
            if progress_view is not None:
                progress_view.set_stage(t("connection.progress_ready"), 100)
            update_button_states()
            if on_connected and model.controller.session:
                on_connected(model.controller.session)

    try:
        Thread(target=worker, daemon=True).start()
    except Exception:
        try:
            model.controller.fail()
        except Exception:
            pass
        try:
            transient["password"] = ""
        except Exception:
            pass
        status.SetLabel(t("connection.status_failed"))
        model.progress_callback = None
        if progress_view is not None:
            progress_view.set_stage(t("connection.progress_failed"))
        update_button_states()
        return False
    return True


__all__ = ["cancel_connect", "disconnect_session", "invalidate_host_lifetime", "run_connect_selected"]
