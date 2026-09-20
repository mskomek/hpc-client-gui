"""Optional wx profile screen backed by the shared connection controller."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Event, Thread
from typing import Any, Callable

from hpc_gui.config.storage import coerce_profile_ssh_timeout, load_profiles
from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.connection_controller import ConnectionController, HostKeyRequest, KeyboardInteractiveRequest, close_session
from hpc_gui.ssh.client import (
    HostKeyChangedError,
    HostKeyInfo,
    HostKeyRejectedError,
    SSHConnInfo,
    coerce_keepalive_interval,
)
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


def _invoke_on_gui_thread(call: Callable[[], Any]) -> Any:
    """Run ``call`` on the wx GUI thread and return its result.

    Transport/host-key/MFA callbacks execute on the SSH worker thread, but
    wx dialogs must live on the GUI thread (OBS-W18-004). When already on
    the GUI thread — or when no live wx application exists (headless model
    tests) — the callable runs inline. Otherwise the call is marshalled via
    ``wx.CallAfter`` and the worker blocks until the GUI thread completes
    it. If the application disappears while waiting, a ``RuntimeError`` is
    raised so the worker fails visibly instead of hanging forever.
    """
    try:
        import wx
    except ImportError:
        return call()
    try:
        app_alive = wx.App.Get() is not None
    except Exception:
        app_alive = False
    if not app_alive:
        return call()
    try:
        if wx.IsMainThread():
            return call()
    except Exception:
        return call()
    box: dict[str, Any] = {}
    finished = Event()

    def _run() -> None:
        try:
            box["value"] = call()
        except Exception as exc:  # never strand the worker thread
            box["error"] = exc
        finally:
            finished.set()

    try:
        wx.CallAfter(_run)
    except Exception as exc:
        raise RuntimeError("cannot marshal dialog to the GUI thread") from exc
    while not finished.wait(timeout=0.2):
        try:
            if wx.App.Get() is None:
                raise RuntimeError("GUI thread unavailable while waiting for dialog")
        except RuntimeError:
            raise
        except Exception:
            break
    if "error" in box:
        raise box["error"]
    return box.get("value")


def format_host_key_prompt(request: HostKeyRequest) -> str:
    """Render the unknown-host security prompt without exposing secrets.

    The request carries only public key material (hostname, key type,
    fingerprint); the caller must never attach passwords or tokens to it.
    """
    role_label = t("connection.host_key_role_jump") if request.role == "jump" else t("connection.host_key_role_target")
    key_type = request.key_type or "SSH"
    return t("connection.host_key_prompt_message").format(
        role=role_label, host=request.hostname, key_type=key_type, fingerprint=request.fingerprint
    )


def describe_wx_connect_failure(error: BaseException, *, resolved_password: str = "") -> str:
    """Map a connect failure to the translated actionable message.

    Mirrors the Qt ``login_widget._on_connect_failed`` contract so both shells
    stay truthful for the same failure: host-key decisions keep their
    dedicated security messages, saved-secret/master states keep theirs, and
    everything else goes through the shared
    ``core.ui_errors.describe_connection_error`` classifier. Any accidental
    secret content is redacted before the text reaches a dialog or log.
    """
    from hpc_gui.core.ui_errors import describe_connection_error

    if isinstance(error, HostKeyChangedError):
        message = t("connection.host_key_changed").format(host=error.hostname)
    elif isinstance(error, HostKeyRejectedError):
        message = t("connection.host_key_rejected").format(host=error.hostname)
    else:
        raw = str(error)
        if "saved_password_unavailable" in raw:
            message = t("connection.saved_password_unavailable")
        elif "master_wrong" in raw:
            message = t("login.err_master_wrong")
        elif "master_cancelled" in raw:
            message = t("connection.auth_cancelled")
        else:
            message = describe_connection_error(error, raw)
        if resolved_password and resolved_password in message:
            message = message.replace(resolved_password, "<redacted>")
    return message


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
    """Build the shared SSH request without copying secrets into UI state.

    Resolution order:
      typed password (``profile["password"]``) if present
        ↓ saved keychain / OS secret via shared service (no prompt)
        ↓ master-encrypted requires prior GUI-thread resolution – this
           helper never prompts; it raises ``saved_password_unavailable``
           when a master-encrypted secret is present but no typed password
           was supplied. Callers that need interactive master unlock must
           resolve via ``resolve_password_for_connect`` on the GUI thread
           before constructing the transient profile.
    """

    def host_key(info: HostKeyInfo) -> str:
        return model.decide_host_key(
            HostKeyRequest(info.hostname, info.fingerprint, info.role, info.key_type)
        )

    def keyboard(title: str, instructions: str, prompts: list[tuple[str, bool]]) -> list[str]:
        request = KeyboardInteractiveRequest(
            title,
            instructions,
            tuple(prompt for prompt, _echo in prompts),
            tuple(bool(echo) for _prompt, echo in prompts),
        )
        return model.answer_keyboard_interactive(request)

    # Resolve password securely; wx stored secrets are never in plaintext ``password`` field.
    # Typed password (transient) takes precedence – this is the path used after
    # the GUI thread has already resolved any master-encrypted secret via
    # ``resolve_password_for_connect``.
    password = str(profile.get("password", "") or "")
    if not password and profile.get("save_password"):
        from hpc_gui.services.connection_profile_service import decrypt_profile_password

        # Use shared service without prompting – keychain/DPAPI succeed,
        # master-encrypted returns None (no prompt) and will be surfaced as
        # saved_password_unavailable. The GUI handler is expected to have
        # resolved master secrets beforehand and supplied them as typed
        # password in the transient profile.
        resolved = decrypt_profile_password(profile, allow_prompt=False)
        if isinstance(resolved, str) and resolved != "":
            password = resolved
        elif resolved is None and any(
            profile.get(key)
            for key in ("password_keychain_ref", "password_dpapi", "password_enc", "password_salt")
        ):
            raise RuntimeError("saved_password_unavailable")
        elif isinstance(resolved, str):
            # Empty means no saved secret – keep empty (key auth)
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


def _controller_disconnect_cb(
    model: "WxConnectionModel",
    session_probe: Callable[[], Any] | None = None,
) -> Callable[[str], None]:
    """Build the transport-failure callback for sessions owned by ``model``.

    The SSH wrapper invokes this when its shell reader observes an
    unexpected transport death (idle or mid-operation). The controller must
    leave ``CONNECTED`` so the status indicator can never masquerade a dead
    transport as a live session. A stale callback from a superseded session
    (RECON-006/007) is dropped: it only fails the controller when the
    controller's current session still owns the reporting transport.
    Delivery is marshalled to the GUI thread when wx is available;
    otherwise the controller fails synchronously (headless/service use).
    """
    def _on_transport_failure(_reason: str) -> None:
        controller = getattr(model, "controller", None)
        if controller is None:
            return
        if session_probe is not None:
            try:
                current = controller.session
                if current is None:
                    # No live session (connecting or already torn down):
                    # the connect worker's done() owns the outcome.
                    return
                owner = current.get("ssh") if isinstance(current, dict) else None
                if owner is not session_probe():
                    # Stale callback from a previous generation; never fail
                    # the new session for the old transport's death.
                    return
            except Exception:
                return
        # Marshal to the GUI thread only when a live wx application
        # exists; otherwise fail synchronously (headless/service use and
        # contexts where CallAfter could never be dispatched). The shell
        # invalidation hook (if any) runs in the same unit so the session
        # model, terminal, and domain panels all observe the loss together.
        def _apply() -> None:
            try:
                controller.fail()
            except Exception:
                pass
            hook = getattr(model, "_session_invalidated_hook", None)
            if callable(hook):
                try:
                    hook()
                except Exception:
                    pass

        try:
            import wx

            app_alive = wx.App.Get() is not None
        except Exception:
            app_alive = False
        try:
            if app_alive:
                wx.CallAfter(_apply)
            else:
                _apply()
        except Exception:
            pass

    return _on_transport_failure


def connect_profile(profile: dict[str, Any], model: "WxConnectionModel") -> dict[str, Any]:
    """Open the shared SSH/files/Slurm session for one selected profile."""
    output_subscribers: list[Callable[[str], None]] = []
    holder: dict[str, Any] = {}
    ssh = SSHClientWrapper(
        ssh_info_from_profile(profile, model),
        shell_output_cb=lambda text: [callback(text) for callback in tuple(output_subscribers)],
        disconnect_cb=_controller_disconnect_cb(model, lambda: holder.get("ssh")),
    )
    holder["ssh"] = ssh
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
        # Monotonic connect-attempt identity. The threaded panel worker tags
        # each attempt so a late/cancelled worker can never apply a stale
        # result over a newer attempt's state (CONN-002/CONN-003).
        self._wx_attempt = 0

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
        # A reconnect supersedes the previous live session: tear it down
        # first so no orphaned transport/shell/SFTP outlives the new
        # attempt and no queued action can execute against the old session.
        # If the new attempt then fails, the honest end state is FAILED /
        # DISCONNECTED rather than a silently revived stale session.
        if self.controller.session is not None:
            close_session(self.controller.session)
            self.controller.session = None
        self._wx_attempt += 1
        self.controller.begin_connect()
        try:
            session = self._connect(dict(profile))
        except Exception:
            self.controller.fail()
            raise
        if self.controller.cancel_token.is_set():
            # Cancelled while connecting: never resurrect the just-opened
            # session; return to the safe DISCONNECTED state (CONN-003).
            if isinstance(session, dict):
                close_session(session)
            self.controller.cancel_connect()
            return False
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


def _build_connection(parent, profiles, *, connect, lifecycle, on_connected, embedded, add_connection=None, on_disconnected=None, **kwargs):
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
    cancel_button = wx.Button(panel, label=t("common.cancel"))
    disconnect_button = wx.Button(panel, label=t("login.disconnect"))
    # Accessibility: set names
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

    # Host-key and MFA dialogs (model callbacks). These callbacks execute on
    # the SSH worker thread; wx dialogs must run on the GUI thread, so both
    # rendezvous through _invoke_on_gui_thread (OBS-W18-004).
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
                # Explicit echo wins; fallback heuristic only when echo is None
                if echo is True:
                    is_secret = False
                elif echo is False:
                    is_secret = True
                else:
                    is_secret = any(word in prompt.lower() for word in ("password", "token", "code", "otp", "pin"))
                # Use robust wx API: PasswordEntryDialog for secret, TextEntryDialog for visible
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
        is_connected = model.controller.state.value == "connected"
        edit_button.Enable(has_selection and not is_connecting)
        duplicate_button.Enable(has_selection and not is_connecting)
        # Delete handling: if active is same as selected, may disable if connected? Wave says handle safely; we allow but warn.
        delete_button.Enable(has_selection and not is_connecting)
        connect_button.Enable(has_selection and not is_connecting)
        # Mid-connect Cancel is only meaningful while connecting (CONN-003);
        # graceful Disconnect only while a live session exists (CONN-004).
        cancel_button.Enable(is_connecting)
        disconnect_button.Enable(is_connected)
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

    # Controller transitions (including background transport-failure
    # reports via disconnect_cb) must repaint the status indicator even
    # when they originate off the GUI thread; otherwise the panel can
    # keep showing "Connected" for a dead transport.
    def _emit_to_status(_state) -> None:
        # Never touch wx controls off the GUI thread: queue the repaint
        # and drop it (rather than risk a cross-thread UI call) if the
        # application object is unavailable.
        try:
            import wx as _wx

            if _wx.App.Get() is None:
                return
            _wx.CallAfter(_update_status_from_controller)
        except Exception:
            pass

    model.controller._emit = _emit_to_status

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

    def _handle_save(profile: dict[str, Any], original_name: str | None = None) -> dict[str, Any] | None:
        # profile is collected dict from dialog (including password plain)
        # Use shared service
        try:
            from hpc_gui.services.connection_profile_service import save_profile as svc_save
        except Exception as exc:
            wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            return None
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
        # Refresh using the canonical saved profile name
        saved_name = str(saved.get("name", ""))
        _refresh_list(select_name=saved_name)
        return saved

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
                        dlg = wx.PasswordEntryDialog(host, t("connection.edit_auth_prompt"), t("connection.edit_auth_title"))
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
            return _handle_save(collected, original_name=original_name) is not None

        def on_save_and_connect(collected: dict[str, Any]) -> bool:
            saved = _handle_save(collected, original_name=original_name)
            if saved is None:
                return False
            # Save & Connect owns exactly one save, then starts the normal path.
            # Use the authoritative canonical name from the saved profile.
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

    def _cancel_connect(_event=None):
        # Mid-connect Cancel (CONN-003): invalidate this attempt so the late
        # worker result is dropped, signal the controller back to the safe
        # DISCONNECTED state, and keep the app alive with a visible status.
        # The worker itself may still be blocked in transport/host-key/MFA;
        # its eventual result is discarded via the attempt tag in done().
        try:
            model._wx_attempt += 1
        except Exception:
            pass
        try:
            model.controller.cancel_connect()
        except Exception:
            pass
        cancelled_msg = t("connection.auth_cancelled") if t("connection.auth_cancelled") != "[connection.auth_cancelled]" else "Authentication cancelled"
        status.SetLabel(cancelled_msg)
        _update_button_states()

    def _disconnect_session(_event=None):
        # Graceful disconnect (CONN-004/RECON-001): tear down the live
        # transport, return the controller to DISCONNECTED, and notify the
        # shell so every domain rebinds to "no session" instead of showing
        # stale connected state or hitting a dead transport.
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
        _update_button_states()
        if on_disconnected is not None:
            try:
                on_disconnected(session)
            except Exception:
                pass
        return True

    def connect_selected(_event=None) -> bool:
        sel = choices.GetStringSelection()
        if not sel:
            return False
        if not model.select(sel):
            return False
        # Resolve credentials on GUI thread before starting worker
        stored = next((p for p in model.profiles if p.get("name") == sel), None)
        if stored is None:
            try:
                stored = next((p for p in _load_live_profiles() if p.get("name") == sel), None)
            except Exception:
                stored = None
        if stored is None:
            wx.MessageBox(t("connection.profile_not_found").format(name=sel), t("login.err_title"), wx.OK | wx.ICON_WARNING)
            return False
        # Typed password for Connect Selected is empty (wx panel has no typed field);
        # stored["password"] is always empty for persisted profiles, so we rely on
        # shared resolver. For typed-override tests the caller may have set
        # stored["password"] transiently – resolve will treat that as typed.
        ask_master_conn = _master_ask_factory()
        try:
            from hpc_gui.services.connection_profile_service import resolve_password_for_connect

            typed_for_connect = str(stored.get("password", "") or "")
            resolved_password = resolve_password_for_connect(
                stored, typed_password=typed_for_connect, ask_master=ask_master_conn
            )
        except RuntimeError as exc:
            msg = str(exc)
            if "master_cancelled" in msg:
                status.SetLabel(t("connection.auth_cancelled") if t("connection.auth_cancelled") != "[connection.auth_cancelled]" else "Authentication cancelled")
                _update_button_states()
                return False
            elif "master_wrong" in msg:
                wx.MessageBox(t("login.err_master_wrong"), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                status.SetLabel(t("connection.status_failed"))
                try:
                    model.controller.fail()
                except Exception:
                    pass
                _update_button_states()
                return False
            elif "saved_password_unavailable" in msg:
                wx.MessageBox(t("connection.saved_password_unavailable"), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                status.SetLabel(t("connection.status_failed"))
                try:
                    model.controller.fail()
                except Exception:
                    pass
                _update_button_states()
                return False
            else:
                wx.MessageBox(msg, t("login.err_title"), wx.OK | wx.ICON_ERROR)
                status.SetLabel(t("connection.status_failed"))
                try:
                    model.controller.fail()
                except Exception:
                    pass
                _update_button_states()
                return False
        except Exception as exc:
            wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            status.SetLabel(t("connection.status_failed"))
            try:
                model.controller.fail()
            except Exception:
                pass
            _update_button_states()
            return False
        if resolved_password is None:
            wx.MessageBox(t("connection.saved_password_unavailable"), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            status.SetLabel(t("connection.status_failed"))
            try:
                model.controller.fail()
            except Exception:
                pass
            _update_button_states()
            return False
        # Build transient profile with resolved password – never persisted
        transient = dict(stored)
        transient["password"] = resolved_password if resolved_password is not None else ""
        # A reconnect supersedes the previous live session (same guarantee
        # as WxConnectionModel.connect_selected): tear it down up-front so
        # no orphaned transport outlives the new attempt.
        if model.controller.session is not None:
            close_session(model.controller.session)
            model.controller.session = None
        # Disable conflicting while connecting
        connect_button.Enable(False)
        edit_button.Enable(False)
        duplicate_button.Enable(False)
        delete_button.Enable(False)
        add_button.Enable(False)
        disconnect_button.Enable(False)
        cancel_button.Enable(True)
        status.SetLabel(t("login.status_connecting"))
        active_label.SetLabel("")
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
            _update_button_states()
            return False
        # Tag this attempt: a late worker from a cancelled or superseded
        # attempt must never apply its result over newer state (CONN-002/003).
        model._wx_attempt += 1
        attempt = model._wx_attempt
        def worker():
            try:
                # Use the transient profile so ssh_info_from_profile sees the typed password
                # and does not need to re-resolve master secrets on the worker thread.
                connect_fn = model._connect
                if connect_fn is None:
                    from hpc_gui.wx_connection import connect_profile as _default_connect

                    def _default(profile):
                        return _default_connect(profile, model)

                    connect_fn = _default
                session = connect_fn(dict(transient))
                if session is False:
                    raise RuntimeError(t("login.error") if t("login.error") != "[login.error]" else "Connection failed")
                # Never finish the controller on the worker thread: the GUI
                # thread owns the attempt check in done(), so a stale or
                # cancelled attempt can be dropped before it touches state.
                wx.CallAfter(done, None, attempt, session)
            except Exception as error:
                wx.CallAfter(done, error, attempt, None)
        def done(error, tag, session):
            # Clear transient password from memory best-effort
            try:
                transient["password"] = ""
            except Exception:
                pass
            if tag != model._wx_attempt:
                # Superseded attempt: drop the stale result without touching
                # newer state; tear down anything the stale worker opened.
                if error is None and isinstance(session, dict):
                    try:
                        close_session(session)
                    except Exception:
                        pass
                return
            if model.controller.cancel_token.is_set():
                # Cancelled while connecting: close anything the worker
                # opened and stay visibly cancelled, never failed (CONN-003).
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
                status.SetLabel(cancelled_msg)
                _update_button_states()
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
                _update_button_states()
                # Actionable, translated failure text shared with the Qt path;
                # secrets are redacted inside the helper, never shown or logged.
                try:
                    msg = describe_wx_connect_failure(error, resolved_password=resolved_password or "")
                except Exception:
                    msg = "Connection failed"
                # Map safe known errors to translated messages
                if "master_cancelled" in str(error):
                    msg = t("connection.auth_cancelled") if t("connection.auth_cancelled") != "[connection.auth_cancelled]" else "Authentication cancelled"
                    # The controller.fail() repaint is already queued via
                    # CallAfter; write the cancel status after it so the
                    # cancellation stays visibly distinct from a failure.
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
            else:
                status.SetLabel(t("login.status_connected"))
                _update_button_states()
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
            _update_button_states()
            return False
        return True

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
    cancel_button.Bind(wx.EVT_BUTTON, _cancel_connect)
    disconnect_button.Bind(wx.EVT_BUTTON, _disconnect_session)
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


__all__ = ["HostKeyRequest", "KeyboardInteractiveRequest", "ProfileSummary", "WxConnectionModel", "connect_profile", "show_connection", "build_connection_panel", "ssh_info_from_profile", "describe_wx_connect_failure", "format_host_key_prompt"]
