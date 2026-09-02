"""Optional wx profile screen backed by the shared connection controller."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Thread
from typing import Any, Callable

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change

from hpc_gui.services.connection_controller import (
    ConnectionController, HostKeyRequest, KeyboardInteractiveRequest,
)
from hpc_gui.ssh.client import SSHConnInfo, HostKeyInfo
from hpc_gui.services.files_ssh import SSHFilesBackend
from hpc_gui.services.slurm_ssh import SSHSlurmBackend
from hpc_gui.ssh.client import SSHClientWrapper


@dataclass(frozen=True)
class ProfileSummary:
    name: str
    host: str
    username: str
    provider: str = ""


def ssh_info_from_profile(profile: dict[str, Any], model: "WxConnectionModel") -> SSHConnInfo:
    """Build the shared SSH request without copying secrets into UI state."""
    def host_key(info: HostKeyInfo) -> str:
        return model.decide_host_key(HostKeyRequest(info.hostname, info.fingerprint, info.role))

    def keyboard(title: str, instructions: str, prompts: list[tuple[str, bool]]) -> list[str]:
        request = KeyboardInteractiveRequest(title, instructions, tuple(prompt for prompt, _echo in prompts))
        return model.answer_keyboard_interactive(request)

    return SSHConnInfo(
        host=str(profile.get("host", "")),
        port=int(profile.get("port", 22) or 22),
        username=str(profile.get("username", "")),
        password=str(profile.get("password", "")),
        key_path=str(profile.get("key_path", "") or profile.get("ssh_key", "")),
        host_key_policy=str(profile.get("host_key_policy", "accept-new") or "accept-new"),
        host_key_decision=host_key,
        keyboard_interactive_handler=keyboard,
    )


def connect_profile(profile: dict[str, Any], model: "WxConnectionModel") -> dict[str, Any]:
    """Open the shared SSH/files/Slurm session for one selected profile."""
    ssh = SSHClientWrapper(ssh_info_from_profile(profile, model))
    try:
        ssh.connect()
        return {
            "connected": True,
            "ssh": ssh,
            "files": SSHFilesBackend(ssh),
            "slurm": SSHSlurmBackend(ssh, profile.get("system") or {}),
            "profile_name": str(profile.get("name", "")),
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
            ProfileSummary(str(item.get("name", "")), str(item.get("host", "")), str(item.get("username", "")), str((item.get("system") or {}).get("provider", "")))
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
        session = self._connect(dict(profile))
        if isinstance(session, dict):
            self.controller.finish(session)
        return True

    def decide_host_key(self, request: HostKeyRequest) -> str:
        """Return an explicit policy; unknown keys are never trusted silently."""
        return self._host_key_decision(request) if self._host_key_decision else "reject"

    def answer_keyboard_interactive(self, request: KeyboardInteractiveRequest) -> list[str]:
        """Delegate MFA prompts without retaining or logging responses."""
        return list(self._keyboard_interactive(request)) if self._keyboard_interactive else []


def show_connection(parent=None, profiles=None, *, connect=None, lifecycle=None, on_connected=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = WxConnectionModel(profiles, connect=connect)
    if connect is None:
        model._connect = lambda profile: connect_profile(profile, model)
    frame = wx.Frame(parent, title=t("tabs.connection"), size=(720, 520))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    choices = wx.ListBox(panel, choices=[item.name for item in model.summaries()])
    connect_button = wx.Button(panel, label=t("login.connect"))
    status = wx.StaticText(panel, label=t("login.status_disconnected"))
    root.Add(choices, 1, wx.EXPAND | wx.ALL, 8)
    root.Add(status, 0, wx.LEFT | wx.RIGHT, 8)
    root.Add(connect_button, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
    panel.SetSizer(root)

    def host_key_dialog(request: HostKeyRequest) -> str:
        message = t("connection.host_key_prompt_message").format(
            role=request.role, host=request.hostname, key_type="SSH", fingerprint=request.fingerprint
        )
        dialog = wx.MessageDialog(frame, message, t("connection.host_key_prompt_title"), wx.YES_NO | wx.CANCEL | wx.ICON_WARNING)
        try:
            result = dialog.ShowModal()
        finally:
            dialog.Destroy()
        return "save" if result == wx.ID_YES else "once" if result == wx.ID_NO else "reject"

    def mfa_dialog(request: KeyboardInteractiveRequest) -> list[str]:
        answers = []
        for prompt in request.prompts:
            dialog = wx.TextEntryDialog(frame, f"{request.instructions}\n\n{prompt}", request.title)
            try:
                if dialog.ShowModal() != wx.ID_OK:
                    return []
                answers.append(dialog.GetValue())
            finally:
                dialog.Destroy()
        return answers

    model._host_key_decision = host_key_dialog
    model._keyboard_interactive = mfa_dialog

    def select(_event):
        model.select(choices.GetStringSelection())

    def refresh_labels(_language=None):
        frame.SetTitle(t("tabs.connection"))
        connect_button.SetLabel(t("login.connect"))
        if model.controller.state.value == "connected":
            status.SetLabel(t("login.status_connected"))
        elif model.controller.state.value != "connecting":
            status.SetLabel(t("login.status_disconnected"))

    def connect_selected(_event=None):
        if not model.select(choices.GetStringSelection()) or not model._connect:
            return
        connect_button.Enable(False)
        status.SetLabel(t("login.status_connecting"))

        def worker():
            try:
                model.connect_selected()
                wx.CallAfter(done, None)
            except Exception as error:
                wx.CallAfter(done, error)

        def done(error):
            connect_button.Enable(True)
            if error:
                model.controller.fail()
                status.SetLabel(t("login.error"))
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                status.SetLabel(t("login.status_connected"))
                if on_connected and model.controller.session:
                    on_connected(model.controller.session)

        Thread(target=worker, daemon=True).start()

    choices.Bind(wx.EVT_LISTBOX, select)
    choices.Bind(wx.EVT_LISTBOX_DCLICK, connect_selected)
    connect_button.Bind(wx.EVT_BUTTON, connect_selected)
    subscribe_language_change(refresh_labels)
    frame.Bind(wx.EVT_CLOSE, lambda event: (unsubscribe_language_change(refresh_labels), event.Skip()))
    frame.Show()
    return wx.ID_OK


__all__ = ["HostKeyRequest", "KeyboardInteractiveRequest", "ProfileSummary", "WxConnectionModel", "connect_profile", "show_connection", "ssh_info_from_profile"]
