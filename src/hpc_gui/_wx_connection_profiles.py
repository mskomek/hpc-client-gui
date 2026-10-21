"""Profile CRUD leaf for the wx connection panel.

Owns master-password prompting, profile save, and the add/edit/duplicate/
delete dialog dispatch. Operates only on explicitly passed host/model/
widget handles; never imports the connection facade.
"""

from __future__ import annotations

from typing import Any, Callable

from hpc_gui.wx_connection_model import build_master_ask_factory


def handle_save(host, model, profile: dict[str, Any], original_name: str | None, refresh_list: Callable[..., None]):
    """Persist one collected profile via the shared service."""
    from hpc_gui.core.i18n import t

    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    try:
        from hpc_gui.services.connection_profile_service import save_profile as svc_save
    except Exception as exc:
        wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR)
        return None
    plain = str(profile.get("password", "") or "")
    save_pw = bool(profile.get("save_password", False))
    prompt_policy = str(profile.get("password_prompt_policy") or "when-needed")
    initial = next((p for p in model.profiles if p.get("name") == (original_name or profile.get("name", ""))), None) if original_name else next((p for p in model.profiles if p.get("name") == profile.get("name", "")), None)
    if original_name and original_name != profile.get("name"):
        initial = next((p for p in model.profiles if p.get("name") == original_name), None)
    ask_master = build_master_ask_factory(host)
    try:
        saved = svc_save(
            profile,
            initial_profile=initial,
            plain_password=plain,
            save_password=save_pw,
            prompt_policy=prompt_policy,
            ask_master=ask_master,
            original_name_override=original_name,
        )
    except RuntimeError as exc:
        msg = str(exc)
        if "saved_password_unavailable" in msg:
            wx.MessageBox(t("connection.saved_password_unavailable"), t("login.err_title"), wx.OK | wx.ICON_ERROR)
        elif "password_store_failed" in msg:
            wx.MessageBox(t("connection.password_store_failed").format(error=msg.split(":", 1)[-1]), t("login.err_title"), wx.OK | wx.ICON_ERROR)
        elif "master_cancelled" in msg:
            return None
        else:
            wx.MessageBox(msg, t("login.err_title"), wx.OK | wx.ICON_ERROR)
        return None
    except ValueError as exc:
        msg = str(exc)
        if msg.startswith("profile_name_taken:"):
            taken = msg.split(":", 1)[1].strip()
            msg = t("connection.rename_name_taken").format(name=taken)
        wx.MessageBox(msg, t("login.err_title"), wx.OK | wx.ICON_WARNING)
        return None
    except Exception as exc:
        wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR)
        return None
    saved_name = str(saved.get("name", ""))
    refresh_list(select_name=saved_name)
    return saved


def open_profile_dialog(host, model, mode: str, initial_name: str | None, get_selection: Callable[[], str], refresh_list: Callable[..., None], connect_selected: Callable[..., bool]) -> None:
    """Dispatch add/edit/duplicate through the shared WxConnectionDialog."""
    from hpc_gui.core.i18n import t

    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    if mode in ("edit", "duplicate", "delete") and not initial_name:
        initial_name = get_selection()
        if not initial_name:
            return
    initial_profile: dict[str, Any] | None = None
    original_name: str | None = None
    if mode == "add":
        initial_profile = None
    else:
        prof = next((p for p in model.profiles if p.get("name") == initial_name), None)
        if not prof:
            wx.MessageBox(t("connection.profile_not_found").format(name=initial_name), t("login.err_title"), wx.OK | wx.ICON_WARNING)
            return
        if mode == "edit":
            try:
                from hpc_gui.services.connection_profile_service import verify_edit_authorization

                def prompt_verify(expected: str):
                    dlg = wx.PasswordEntryDialog(host, t("connection.edit_auth_prompt"), t("connection.edit_auth_title"))
                    result = dlg.ShowModal()
                    val = dlg.GetValue()
                    dlg.Destroy()
                    return val, result == wx.ID_OK

                ask_master_edit = build_master_ask_factory(host)
                if not verify_edit_authorization(prof, ask_master=ask_master_edit, prompt_verify=prompt_verify):
                    wx.MessageBox(t("connection.edit_auth_failed"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
                    return
            except Exception as exc:
                wx.MessageBox(
                    t("connection.edit_auth_error").format(error=type(exc).__name__),
                    t("login.err_title"),
                    wx.OK | wx.ICON_ERROR,
                )
                return
            initial_profile = prof
            original_name = str(prof.get("name", ""))
        elif mode == "duplicate":
            from hpc_gui.services.profile_duplicate import duplicate_profile as dup_func
            try:
                duplicate = dup_func(prof, [p.get("name", "") for p in model.profiles])
            except Exception as exc:
                wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                return
            initial_profile = duplicate
            original_name = None

    try:
        from hpc_gui.wx_connection_dialog import WxConnectionDialog
    except Exception as exc:
        wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR)
        return

    def on_save(collected: dict[str, Any]) -> bool:
        return handle_save(host, model, collected, original_name, refresh_list) is not None

    def on_save_and_connect(collected: dict[str, Any]) -> bool:
        saved = handle_save(host, model, collected, original_name, refresh_list)
        if saved is None:
            return False
        started = connect_selected(None)
        return bool(started)

    dlg = WxConnectionDialog(
        host,
        initial_profile=initial_profile,
        mode=mode,
        on_save=on_save,
        on_save_and_connect=on_save_and_connect,
    )
    try:
        dlg.ShowModal()
    finally:
        dlg.Destroy()


def delete_selected_profile(host, model, get_selection: Callable[[], str], refresh_list: Callable[..., None], update_detail: Callable[[], None], update_button_states: Callable[[], None]) -> None:
    """Delete the selected profile after active-session and confirm guards."""
    from hpc_gui.core.i18n import t

    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    sel = get_selection()
    if not sel:
        return
    active_name = ""
    try:
        active_name = str((model.controller.session or {}).get("profile_name") or "")
    except Exception:
        active_name = ""
    if active_name and active_name == sel and model.controller.state.value == "connected":
        wx.MessageBox(t("connection.delete_blocked_active"), t("connection.delete_confirm_title"), wx.OK | wx.ICON_WARNING)
        return
    msg = t("connection.delete_confirm_message").format(name=sel)
    title = t("connection.delete_confirm_title")
    confirm = wx.MessageDialog(host, msg, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
    result = confirm.ShowModal()
    confirm.Destroy()
    if result != wx.ID_YES:
        return
    try:
        from hpc_gui.config.storage import delete_profile
        delete_profile(sel)
        refresh_list(select_name=None)
        if model.selected_name == sel:
            model.selected_name = ""
        update_detail()
        update_button_states()
    except Exception as exc:
        wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR)


__all__ = [
    "build_master_ask_factory",
    "delete_selected_profile",
    "handle_save",
    "open_profile_dialog",
]
