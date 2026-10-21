"""wx connection model leaf: profiles, SSH session ownership, GUI-thread marshal."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Event
from typing import Any, Callable

from hpc_gui.config.storage import coerce_profile_ssh_timeout
from hpc_gui.core.i18n import t
from hpc_gui.services.connection_controller import (
    ConnectionController,
    HostKeyRequest,
    KeyboardInteractiveRequest,
    close_session,
)
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
from hpc_gui.wx_connection_prompts import format_host_key_prompt


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

    password = str(profile.get("password", "") or "")
    if not password and profile.get("save_password"):
        from hpc_gui.services.connection_profile_service import decrypt_profile_password

        resolved = decrypt_profile_password(profile, allow_prompt=False)
        if isinstance(resolved, str) and resolved != "":
            password = resolved
        elif resolved is None and any(
            profile.get(key)
            for key in ("password_keychain_ref", "password_dpapi", "password_enc", "password_salt")
        ):
            raise RuntimeError("saved_password_unavailable")
        elif isinstance(resolved, str):
            password = resolved

    provider_template = _provider_template(profile)
    auth_methods: list[str] = []
    if isinstance(provider_template, dict):
        access = provider_template.get("access")
        if isinstance(access, dict):
            auth_methods = list(access.get("auth_methods") or [])
    access2 = provider_template.get("access") if isinstance(provider_template, dict) else None
    if isinstance(access2, dict):
        auth_methods = list(access2.get("auth_methods") or auth_methods)
    keyboard_handler = keyboard
    if auth_methods and "keyboard-interactive" not in auth_methods:
        keyboard_handler = None

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
                    return
                owner = current.get("ssh") if isinstance(current, dict) else None
                if owner is not session_probe():
                    return
            except Exception:
                return

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
            try:
                on_main_thread = bool(wx.IsMainThread())
            except Exception:
                on_main_thread = True
        except Exception:
            app_alive = False
            on_main_thread = True
        try:
            if app_alive and not on_main_thread:
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
        self.progress_callback: Callable[[str], None] | None = None
        # Monotonic connect-attempt identity. The threaded panel worker tags
        # each attempt so a late/cancelled worker can never apply a stale
        # result over a newer attempt's state (CONN-002/CONN-003).
        self._wx_attempt = 0
        self._wx_host_closed = False

    def report_connection_progress(self, message: str) -> None:
        callback = self.progress_callback
        if callback is not None:
            callback(str(message))

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


def build_master_ask_factory(host):
    """Return an ``ask_master(confirm)`` promoter bound to ``host``."""
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
        cached = _load_cached()
        if cached:
            return cached
        try:
            import wx
        except ImportError as exc:
            raise RuntimeError("wxPython is not installed") from exc
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

    ask_master._cache = cache  # type: ignore
    return ask_master


__all__ = [
    "HostKeyRequest",
    "KeyboardInteractiveRequest",
    "ProfileSummary",
    "WxConnectionModel",
    "_controller_disconnect_cb",
    "_invoke_on_gui_thread",
    "_provider_name",
    "_provider_template",
    "build_master_ask_factory",
    "connect_profile",
    "describe_wx_connect_failure",
    "format_host_key_prompt",
    "ssh_info_from_profile",
]
