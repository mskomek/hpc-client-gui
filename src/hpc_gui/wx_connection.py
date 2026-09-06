"""Optional wx profile screen backed by the shared connection controller."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Thread
from typing import Any, Callable

from hpc_gui.config.file_manager_profile import normalize_file_manager_settings
from hpc_gui.config.jump_host_profile import normalize_jump_host_settings
from hpc_gui.config.storage import coerce_profile_ssh_timeout, coerce_profile_transfer_parallelism, load_profiles
from hpc_gui.config.system_profile import normalize_system_settings
from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.connection_controller import ConnectionController, HostKeyRequest, KeyboardInteractiveRequest
from hpc_gui.ssh.client import HostKeyInfo, SSHConnInfo, coerce_keepalive_interval
from hpc_gui.services.files_ssh import SSHFilesBackend
from hpc_gui.services.slurm_ssh import SSHSlurmBackend
from hpc_gui.ssh.client import SSHClientWrapper
from hpc_gui.ssh.jump import jump_info_from_settings
from hpc_gui.wx_host import make_host


@dataclass(frozen=True)
class ProfileSummary:
    name: str
    host: str
    username: str
    provider: str = ""


def _provider_template(profile: dict[str, Any]) -> dict[str, Any] | None:
    candidate = profile.get("provider_template")
    if isinstance(candidate, dict):
        return candidate
    system = profile.get("system")
    candidate = system.get("provider_template") if isinstance(system, dict) else None
    return candidate if isinstance(candidate, dict) else None


def _provider_name(profile: dict[str, Any]) -> str:
    template = _provider_template(profile) or {}
    system = profile.get("system") if isinstance(profile.get("system"), dict) else {}
    site = template.get("site") if isinstance(template.get("site"), dict) else {}
    return str(
        system.get("provider")
        or template.get("name")
        or template.get("profile_id")
        or site.get("name")
        or system.get("name", "")
        or ""
    )


def ssh_info_from_profile(profile: dict[str, Any], model: "WxConnectionModel") -> SSHConnInfo:
    """Build the shared SSH request without copying secrets into UI state."""

    def host_key(info: HostKeyInfo) -> str:
        return model.decide_host_key(HostKeyRequest(info.hostname, info.fingerprint, info.role))

    def keyboard(title: str, instructions: str, prompts: list[tuple[str, bool]]) -> list[str]:
        request = KeyboardInteractiveRequest(
            title,
            instructions,
            tuple(prompt for prompt, _echo in prompts),
            tuple(bool(echo) for _prompt, echo in prompts),
        )
        return model.answer_keyboard_interactive(request)

    # Resolve password securely; wx stored secrets are never in plaintext ``password`` field.
    password = str(profile.get("password", "") or "")
    if not password and profile.get("save_password"):
        from hpc_gui.services.connection_profile_service import decrypt_profile_password as resolve_saved_password

        resolved = resolve_saved_password(profile, allow_prompt=False)
        if resolved is None and any(
            profile.get(key)
            for key in ("password_keychain_ref", "password_dpapi", "password_enc")
        ):
            raise RuntimeError("saved_password_unavailable")
        if isinstance(resolved, str):
            password = resolved

    # Provider auth metadata for keyboard-interactive decision
    provider_template = _provider_template(profile)
    # Check if provider declares keyboard-interactive
    auth_methods: list[str] = []
    if isinstance(provider_template, dict):
        access = provider_template.get("access")
        if isinstance(access, dict):
            auth_methods = list(access.get("auth_methods") or [])
    access2 = provider_template.get("access") if isinstance(provider_template, dict) else None
    if isinstance(access2, dict):
        auth_methods = list(access2.get("auth_methods") or auth_methods)
    # If keyboard-interactive declared, keep handler, otherwise still provide handler? Qt only provides when needed, but wx can always provide; server will only invoke when needed.
    # Keep behavior: provide handler if keyboard-interactive in methods OR if no provider declares (fallback to always)
    keyboard_handler = keyboard
    if auth_methods and "keyboard-interactive" not in auth_methods:
        keyboard_handler = None  # no MFA for providers that don't use it; still safe to provide but preserve parity

    # Jump host
    jump = None
    try:
        jump = jump_info_from_settings(profile.get("jump_host"))
    except Exception:
        jump = None

    return SSHConnInfo(
        host=str(profile.get("host", "")),
        port=int(profile.get("port", 22) or 22),
        username=str(profile.get("username", "")),
        password=password,
        key_path=str(profile.get("key_path", "") or profile.get("ssh_key", "")),
        host_key_policy=str(profile.get("host_key_policy", "accept-new") or "accept-new"),
        x11_forwarding=bool(profile.get("x11_forwarding", False)),
        timeout=coerce_profile_ssh_timeout(profile.get("ssh_timeout")),
        keepalive_interval_seconds=coerce_keepalive_interval(profile.get("keepalive_interval_seconds", 30)),
        host_key_decision=host_key,
        jump=jump,
        keyboard_interactive_handler=keyboard_handler,
    )


def connect_profile(profile: dict[str, Any], model: "WxConnectionModel") -> dict[str, Any]:
    """Open the shared SSH/files/Slurm session for one selected profile."""
    output_subscribers: list[Callable[[str], None]] = []
    ssh = SSHClientWrapper(
        ssh_info_from_profile(profile, model),
        shell_output_cb=lambda text: [callback(text) for callback in tuple(output_subscribers)],
    )
    ssh._wx_output_subscribers = output_subscribers  # type: ignore[attr-defined]
    try:
        ssh.connect()
        return {
            "connected": True,
            "ssh": ssh,
            "files": SSHFilesBackend(ssh),
            "slurm": SSHSlurmBackend(ssh, profile.get("system") or {}),
            "profile_name": str(profile.get("name", "")),
            "profile": {**profile, "password": ""},
            "transfer_parallelism": int(profile.get("transfer_parallelism", 1) or 1),
            "output_subscribers": output_subscribers,
        }
    except Exception:
        ssh.close()
        raise


class WxConnectionModel:
    def __init__(self, profiles: list[dict[str, Any]] | None = None, *, connect: Callable[[dict[str, Any]], None] | None = None, host_key_decision: Callable[[HostKeyRequest], str] | None = None, keyboard_interactive: Callable[[KeyboardInteractiveRequest], list[str]] | None = None) -> None:
        self.profiles = list(profiles or [])
        self.selected_name = ""
        self.controller = ConnectionController()
        self._connect = connect
        self._host_key_decision = host_key_decision
        self._keyboard_interactive = keyboard_interactive

    def summaries(self) -> tuple[ProfileSummary, ...]:
        return tuple(
            ProfileSummary(
                str(item.get("name", "")),
                str(item.get("host", "")),
                str(item.get("username", "")),
                _provider_name(item),
            )
            for item in self.profiles
            if item.get("name")
        )

    def select(self, name: str) -> bool:
        if not any(item.get("name") == name for item in self.profiles):
            return False
        self.selected_name = name
        return True

    def connect_selected(self) -> bool:
        profile = next((item for item in self.profiles if item.get("name") == self.selected_name), None)
        if profile is None or self._connect is None:
            return False
        self.controller.begin_connect()
        try:
            session = self._connect(dict(profile))
        except Exception:
            self.controller.fail()
            raise
        if session is False:
            self.controller.fail()
            return False
        if isinstance(session, dict):
            self.controller.finish(session)
        return True

    def decide_host_key(self, request: HostKeyRequest) -> str:
        """Return an explicit policy; unknown keys are never trusted silently."""
        return self._host_key_decision(request) if self._host_key_decision else "reject"

    def answer_keyboard_interactive(self, request: KeyboardInteractiveRequest) -> list[str]:
        """Delegate MFA prompts without retaining or logging responses."""
        return list(self._keyboard_interactive(request)) if self._keyboard_interactive else []


def _build_connection(parent, profiles, *, connect, lifecycle, on_connected, embedded, add_connection=None, **kwargs):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    # ``add_connection`` remains accepted for callers on the old surface, but
    # profile creation is owned by this panel and never delegated.
    model = WxConnectionModel(profiles, connect=connect)
    if connect is None:
        model._connect = lambda profile: connect_profile(profile, model)

    # Load live profiles; fallback to injected list for tests
    def _load_live_profiles() -> list[dict[str, Any]]:
        try:
            live = load_profiles()
            return live if isinstance(live, list) else []
        except Exception:
            return list(profiles or [])

    # Initialize model with live data
    try:
        model.profiles = _load_live_profiles()
    except Exception:
        pass

    host, finish = make_host(parent, title=t("tabs.connection"), size=(840, 520), embedded=embedded)
    panel = wx.Panel(host)

    # Root sizer
    root = wx.BoxSizer(wx.VERTICAL)

    profiles_label = wx.StaticText(panel, label=t("connection.saved_profiles"))

    # Profile list + detail
    list_and_detail = wx.BoxSizer(wx.HORIZONTAL)
    # Left: list
    list_panel = wx.Panel(panel)
    list_sizer = wx.BoxSizer(wx.VERTICAL)
    choices = wx.ListBox(list_panel, choices=[item.name for item in model.summaries()], style=wx.LB_SINGLE | wx.LB_NEEDED_SB)
    choices.SetMinSize(wx.Size(320, 240))
    list_sizer.Add(choices, 1, wx.EXPAND)
    list_panel.SetSizer(list_sizer)

    # Right: detail panel
    detail_panel = wx.Panel(panel)
    detail_sizer = wx.BoxSizer(wx.VERTICAL)
    detail_title = wx.StaticText(detail_panel, label=t("common.details"))
    detail_title.SetFont(detail_title.GetFont().MakeBold())
    detail_name = wx.StaticText(detail_panel, label="")
    detail_host = wx.StaticText(detail_panel, label="")
    detail_provider = wx.StaticText(detail_panel, label="")
    # Wrap for DPI
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

    # Status area
    status = wx.StaticText(panel, label=t("login.status_disconnected"))
    # Active profile distinction
    active_label = wx.StaticText(panel, label="")
    active_label.SetForegroundColour(wx.Colour(70, 70, 70))
    status_row = wx.BoxSizer(wx.HORIZONTAL)
    status_row.Add(status, 0, wx.RIGHT, 12)
    status_row.Add(active_label, 1, wx.EXPAND)
    root.Add(status_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

    # Button row
    button_row = wx.BoxSizer(wx.HORIZONTAL)
    add_button = wx.Button(panel, label=t("login.add_connection"))
    edit_button = wx.Button(panel, label=t("connection.edit_action"))
    duplicate_button = wx.Button(panel, label=t("login.duplicate"))
    delete_button = wx.Button(panel, label=t("connection.delete_action"))
    connect_button = wx.Button(panel, label=t("login.connect_selected"))
    # Accessibility: set names
    for btn, name in ((add_button, "AddConnection"), (edit_button, "EditConnection"), (duplicate_button, "DuplicateProfile"), (delete_button, "DeleteProfile"), (connect_button, "ConnectSelected")):
        try:
            btn.SetName(name)
        except Exception:
            pass
    button_row.Add(add_button, 0, wx.RIGHT, 8)
    button_row.Add(edit_button, 0, wx.RIGHT, 8)
    button_row.Add(duplicate_button, 0, wx.RIGHT, 8)
    button_row.Add(delete_button, 0, wx.RIGHT, 8)
    button_row.AddStretchSpacer(1)
    button_row.Add(connect_button, 0)
    root.Add(button_row, 0, wx.EXPAND | wx.ALL, 12)

    panel.SetSizer(root)

    # Host-key and MFA dialogs (model callbacks)
    def host_key_dialog(request: HostKeyRequest) -> str:
        role_label = t("connection.host_key_role_jump") if request.role == "jump" else t("connection.host_key_role_target")
        message = t("connection.host_key_prompt_message").format(
            role=role_label, host=request.hostname, key_type="SSH", fingerprint=request.fingerprint
        )
        dialog = wx.MessageDialog(host, message, t("connection.host_key_prompt_title"), wx.YES_NO | wx.CANCEL | wx.ICON_WARNING)
        try:
            result = dialog.ShowModal()
        finally:
            dialog.Destroy()
        return "save" if result == wx.ID_YES else "once" if result == wx.ID_NO else "reject"

    def mfa_dialog(request: KeyboardInteractiveRequest) -> list[str]:
        answers = []
        for index, prompt in enumerate(request.prompts):
            echo = request.echo[index] if index < len(request.echo) else None
            is_secret = echo is False or (
                echo is None
                and any(word in prompt.lower() for word in ("password", "token", "code", "otp", "pin"))
            )
            style = wx.TE_PASSWORD if is_secret else 0
            # Create dialog with appropriate style
            dlg = wx.TextEntryDialog(host, f"{request.instructions}\n\n{prompt}", request.title, style=style)
            try:
                if dlg.ShowModal() != wx.ID_OK:
                    return []
                answers.append(dlg.GetValue())
            finally:
                dlg.Destroy()
        return answers

    model._host_key_decision = host_key_dialog
    model._keyboard_interactive = mfa_dialog

    # Helpers
    def _refresh_list(select_name: str | None = None) -> None:
        try:
            live = _load_live_profiles()
        except Exception:
            live = []
        model.profiles = live
        choices.Clear()
        for item in model.summaries():
            choices.Append(item.name)
        # Select requested or preserve current
        target = select_name or model.selected_name
        if target:
            idx = choices.FindString(target)
            if idx != wx.NOT_FOUND:
                choices.SetSelection(idx)
                model.selected_name = target
            else:
                # No selection
                if choices.GetCount() > 0 and select_name is None:
                    # Keep no selection if previously invalid
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
        provider = ""
        provider = _provider_name(prof)
        detail_name.SetLabel(f"{t('login.profile_name_label')}: {name}" if t('login.profile_name_label') != "[login.profile_name_label]" else f"Profile: {name}")
        if identity:
            detail_host.SetLabel(f"{t('login.host')}: {identity}" if t('login.host') != "[login.host]" else f"Host: {identity}")
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
        edit_button.Enable(has_selection and not is_connecting)
        duplicate_button.Enable(has_selection and not is_connecting)
        # Delete handling: if active is same as selected, may disable if connected? Wave says handle safely; we allow but warn.
        delete_button.Enable(has_selection and not is_connecting)
        connect_button.Enable(has_selection and not is_connecting)
        # Add is always enabled unless connecting? Wave says always available unless modal conflicting; we keep enabled always.
        add_button.Enable(not is_connecting)
        # Update status label
        state = model.controller.state.value
        if state == "connected":
            status.SetLabel(t("login.status_connected"))
            # Show active
            active_name = ""
            try:
                active_name = str((model.controller.session or {}).get("profile_name") or "")
            except Exception:
                active_name = ""
            if active_name:
                # Distinguish selected vs active
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

    # Wire selection
    def select(_event):
        sel = choices.GetStringSelection()
        if sel:
            model.select(sel)
        _update_detail()
        _update_button_states()

    # Language refresh
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
        profiles_label.SetLabel(t("connection.saved_profiles"))
        detail_title.SetLabel(t("common.details"))
        _update_button_states()
        _update_detail()
        if model.controller.state.value == "connected":
            status.SetLabel(t("login.status_connected"))
        elif model.controller.state.value == "connecting":
            status.SetLabel(t("login.status_connecting"))
        else:
            status.SetLabel(t("login.status_disconnected"))

    # -- Profile CRUD handlers ---------------------------------------------

    def _master_ask_factory():
        # Simple wx master password promoter for shared service
        cache: dict[str, str] = {"value": ""}
        def _load_cached():
            try:
                from hpc_gui.config.storage import load_settings
                from hpc_gui.core.secret_store import is_available, unprotect_secret
                if cache["value"]:
                    return cache["value"]
                st = load_settings()
                token = st.get("master_password_dpapi")
                if token and is_available():
                    try:
                        cache["value"] = unprotect_secret(str(token))
                        return cache["value"]
                    except Exception:
                        from hpc_gui.config.storage import update_settings
                        update_settings({"master_password_dpapi": ""})
            except Exception:
                pass
            return ""
        def ask_master(confirm: bool) -> str | None:
            # Check cache first
            cached = _load_cached()
            if cached:
                return cached
            # Build wx dialog similar to LoginWidget
            dlg = wx.Dialog(host, title=t("login.master_create_title") if confirm else t("login.master_unlock_title"))
            sizer = wx.BoxSizer(wx.VERTICAL)
            prompt = wx.StaticText(dlg, label=t("login.master_create_prompt") if confirm else t("login.master_unlock_prompt"))
            prompt.Wrap(400)
            sizer.Add(prompt, 0, wx.EXPAND | wx.ALL, 12)
            form = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
            form.AddGrowableCol(1, 1)
            pwd_label = wx.StaticText(dlg, label=t("login.master_password_label"))
            pwd_ctrl = wx.TextCtrl(dlg, style=wx.TE_PASSWORD)
            form.Add(pwd_label, 0, wx.ALIGN_CENTER_VERTICAL)
            form.Add(pwd_ctrl, 1, wx.EXPAND)
            confirm_ctrl = None
            if confirm:
                confirm_label = wx.StaticText(dlg, label=t("login.master_confirm_label"))
                confirm_ctrl = wx.TextCtrl(dlg, style=wx.TE_PASSWORD)
                form.Add(confirm_label, 0, wx.ALIGN_CENTER_VERTICAL)
                form.Add(confirm_ctrl, 1, wx.EXPAND)
            sizer.Add(form, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
            remember_cb = wx.CheckBox(dlg, label=t("connection.remember_master_password"))
            try:
                from hpc_gui.core.secret_store import is_available
                remember_cb.Show(is_available())
            except Exception:
                remember_cb.Hide()
            sizer.Add(remember_cb, 0, wx.ALL, 12)
            btns = dlg.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
            sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 12)
            dlg.SetSizer(sizer)
            dlg.Fit()
            pwd_ctrl.SetFocus()
            result = dlg.ShowModal()
            pwd_val = pwd_ctrl.GetValue().strip()
            confirm_val = confirm_ctrl.GetValue().strip() if confirm_ctrl else ""
            dlg.Destroy()
            if result != wx.ID_OK:
                return None
            if not pwd_val:
                wx.MessageBox(t("login.err_master_empty"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
                return None
            if confirm and confirm_val != pwd_val:
                wx.MessageBox(t("login.err_master_mismatch"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
                return None
            cache["value"] = pwd_val
            if remember_cb.GetValue():
                try:
                    from hpc_gui.core.secret_store import protect_secret
                    from hpc_gui.config.storage import update_settings
                    update_settings({"master_password_dpapi": protect_secret(pwd_val)})
                except Exception as exc:
                    wx.MessageBox(t("connection.master_password_store_failed").format(error=exc), t("login.err_title"), wx.OK | wx.ICON_WARNING)
            return pwd_val
        # expose cache for caller to wipe on failure if needed
        ask_master._cache = cache  # type: ignore
        return ask_master

    def _handle_save(profile: dict[str, Any], original_name: str | None = None) -> bool:
        # profile is collected dict from dialog (including password plain)
        # Use shared service
        try:
            from hpc_gui.services.connection_profile_service import save_profile as svc_save
        except Exception as exc:
            wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            return False
        plain = str(profile.get("password", "") or "")
        save_pw = bool(profile.get("save_password", False))
        prompt_policy = str(profile.get("password_prompt_policy") or "when-needed")
        initial = next((p for p in model.profiles if p.get("name") == (original_name or profile.get("name", ""))), None) if original_name else next((p for p in model.profiles if p.get("name") == profile.get("name", "")), None)
        # For rename, initial is old name
        if original_name and original_name != profile.get("name"):
            initial = next((p for p in model.profiles if p.get("name") == original_name), None)
        ask_master = _master_ask_factory()
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
                wx.MessageBox(t("connection.password_store_failed").format(error=msg.split(":",1)[-1]), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            elif "master_cancelled" in msg:
                return False
            else:
                wx.MessageBox(msg, t("login.err_title"), wx.OK | wx.ICON_ERROR)
            return False
        except ValueError as exc:
            wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_WARNING)
            return False
        except Exception as exc:
            wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            return False
        # Refresh
        saved_name = str(saved.get("name", ""))
        _refresh_list(select_name=saved_name)
        return True

    def _open_dialog(mode: str, initial_name: str | None = None) -> None:
        if mode in ("edit", "duplicate", "delete") and not initial_name:
            initial_name = choices.GetStringSelection()
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
                # Authorization check
                try:
                    from hpc_gui.services.connection_profile_service import verify_edit_authorization
                    # Build verify callback via wx prompt
                    def prompt_verify(expected: str):
                        dlg = wx.TextEntryDialog(host, t("connection.edit_auth_prompt"), t("connection.edit_auth_title"), style=wx.TE_PASSWORD)
                        result = dlg.ShowModal()
                        val = dlg.GetValue()
                        dlg.Destroy()
                        return val, result == wx.ID_OK
                    ask_master_edit = _master_ask_factory()
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
                # Keep duplicate mode so the shared dialog is still the only
                # editor while its title/action semantics remain accurate.

        # Import dialog lazily to avoid circular
        try:
            from hpc_gui.wx_connection_dialog import WxConnectionDialog
        except Exception as exc:
            wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            return

        # on_save and on_save_and_connect callbacks for dialog
        def on_save(collected: dict[str, Any]) -> bool:
            return _handle_save(collected, original_name=original_name)

        def on_save_and_connect(collected: dict[str, Any]) -> bool:
            if not _handle_save(collected, original_name=original_name):
                return False
            # Save & Connect owns exactly one save, then starts the normal path.
            saved_name = str(collected.get("name", "")).strip() or str(collected.get("host", ""))
            try:
                _refresh_list(select_name=saved_name)
                connect_selected(None)
            except Exception as exc:
                wx.MessageBox(
                    t("connection.connect_after_save_failed").format(error=type(exc).__name__),
                    t("login.err_title"),
                    wx.OK | wx.ICON_ERROR,
                )
                return False
            return True

        dlg = WxConnectionDialog(
            host,
            initial_profile=initial_profile,
            mode=mode,
            on_save=on_save,
            on_save_and_connect=on_save_and_connect,
        )
        try:
            result = dlg.ShowModal()
        finally:
            dlg.Destroy()
        # If dialog was closed via Save, refresh already done; otherwise no-op

    def _add_connection(_event=None):
        # Owned Add – always available
        _open_dialog("add")

    def _edit_selected(_event=None):
        _open_dialog("edit", choices.GetStringSelection())

    def _duplicate_selected(_event=None):
        _open_dialog("duplicate", choices.GetStringSelection())

    def _delete_selected(_event=None):
        sel = choices.GetStringSelection()
        if not sel:
            return
        # If connected profile is the target, handle safely: warn and optionally disable delete
        active_name = ""
        try:
            active_name = str((model.controller.session or {}).get("profile_name") or "")
        except Exception:
            active_name = ""
        if active_name and active_name == sel and model.controller.state.value == "connected":
            wx.MessageBox(t("connection.delete_blocked_active"), t("connection.delete_confirm_title"), wx.OK | wx.ICON_WARNING)
            return
        # Confirmation required
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
            # Refresh and clear selection
            _refresh_list(select_name=None)
            # If deleted was selected, clear detail
            if model.selected_name == sel:
                model.selected_name = ""
            _update_detail()
            _update_button_states()
        except Exception as exc:
            wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR)

    def connect_selected(_event=None):
        sel = choices.GetStringSelection()
        if not sel:
            return
        if not model.select(sel):
            return
        # Disable conflicting while connecting
        connect_button.Enable(False)
        edit_button.Enable(False)
        duplicate_button.Enable(False)
        delete_button.Enable(False)
        add_button.Enable(False)
        status.SetLabel(t("login.status_connecting"))
        active_label.SetLabel("")
        def worker():
            try:
                if not model.connect_selected():
                    raise RuntimeError(t("login.error") if t("login.error") != "[login.error]" else "Connection failed")
                wx.CallAfter(done, None)
            except Exception as error:
                wx.CallAfter(done, error)
        def done(error):
            connect_button.Enable(True)
            add_button.Enable(True)
            # Restore other buttons based on selection
            _update_button_states()
            if error:
                model.controller.fail()
                status.SetLabel(t("connection.status_failed"))
                # Show useful error, never with secrets
                try:
                    msg = str(error)
                except Exception:
                    msg = "Connection failed"
                wx.MessageBox(msg, t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                status.SetLabel(t("login.status_connected"))
                _update_button_states()
                if on_connected and model.controller.session:
                    on_connected(model.controller.session)
        Thread(target=worker, daemon=True).start()

    # Context menu
    def on_context_menu(event):
        sel = choices.GetStringSelection()
        if not sel:
            # Try to hit-test where menu was invoked
            try:
                pos = event.GetPosition()
                # For EVT_CONTEXT_MENU, position may be -1,-1; fallback to mouse
                if pos == wx.DefaultPosition:
                    return
                # Find item at point? ListBox doesn't have HitTest easily; just use current selection
                pass
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

    # Bindings
    choices.Bind(wx.EVT_LISTBOX, select)
    choices.Bind(wx.EVT_LISTBOX_DCLICK, connect_selected)
    choices.Bind(wx.EVT_CONTEXT_MENU, on_context_menu)
    connect_button.Bind(wx.EVT_BUTTON, connect_selected)
    add_button.Bind(wx.EVT_BUTTON, _add_connection)
    edit_button.Bind(wx.EVT_BUTTON, _edit_selected)
    duplicate_button.Bind(wx.EVT_BUTTON, _duplicate_selected)
    delete_button.Bind(wx.EVT_BUTTON, _delete_selected)
    # Retarget the selection before opening the menu when the user right-clicks
    # a different row; visible buttons and menu actions share the same handlers.
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
    host.bind_host_close(lambda event: (unsubscribe_language_change(refresh_labels), event.Skip()))

    # Initial refresh
    _update_detail()
    _update_button_states()

    # expose for tests
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
    }
    host._wx_connection_add_button = add_button
    host._wx_connection_connect_button = connect_button
    host._wx_connection_edit_button = edit_button
    host._wx_connection_duplicate_button = duplicate_button
    host._wx_connection_delete_button = delete_button
    host._wx_connection_model = model
    host._wx_connection_refresh = _refresh_list
    host._wx_connection_open_dialog = _open_dialog
    finish()
    return host


def build_connection_panel(parent, profiles=None, *, connect=None, lifecycle=None, on_connected=None, add_connection=None, **kwargs):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_connection(parent, profiles, connect=connect, lifecycle=lifecycle, on_connected=on_connected, embedded=True, add_connection=add_connection, **kwargs)


def show_connection(parent=None, profiles=None, *, connect=None, lifecycle=None, on_connected=None, add_connection=None, **kwargs) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    _build_connection(parent, profiles, connect=connect, lifecycle=lifecycle, on_connected=on_connected, embedded=False, add_connection=add_connection, **kwargs)
    return wx.ID_OK


__all__ = ["HostKeyRequest", "KeyboardInteractiveRequest", "ProfileSummary", "WxConnectionModel", "connect_profile", "show_connection", "build_connection_panel", "ssh_info_from_profile"]
