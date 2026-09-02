"""Optional wx profile screen backed by the shared connection controller."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Thread
from typing import Any, Callable

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change

from hpc_gui.services.connection_controller import (
    ConnectionController, HostKeyRequest, KeyboardInteractiveRequest,
)


@dataclass(frozen=True)
class ProfileSummary:
    name: str
    host: str
    username: str
    provider: str = ""


class WxConnectionModel:
    def __init__(self, profiles: list[dict[str, Any]] | None = None, *, connect: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.profiles = list(profiles or [])
        self.selected_name = ""
        self.controller = ConnectionController()
        self._connect = connect

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
        self._connect(dict(profile))
        return True


def show_connection(parent=None, profiles=None, *, connect=None, lifecycle=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = WxConnectionModel(profiles, connect=connect)
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

        Thread(target=worker, daemon=True).start()

    choices.Bind(wx.EVT_LISTBOX, select)
    choices.Bind(wx.EVT_LISTBOX_DCLICK, connect_selected)
    connect_button.Bind(wx.EVT_BUTTON, connect_selected)
    subscribe_language_change(refresh_labels)
    frame.Bind(wx.EVT_CLOSE, lambda event: (unsubscribe_language_change(refresh_labels), event.Skip()))
    frame.Show()
    return wx.ID_OK


__all__ = ["HostKeyRequest", "KeyboardInteractiveRequest", "ProfileSummary", "WxConnectionModel", "show_connection"]
