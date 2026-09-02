"""Optional wx profile screen backed by the shared connection controller."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

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


def show_connection(parent=None, profiles=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = WxConnectionModel(profiles)
    frame = wx.Frame(parent, title="Connections", size=(720, 520))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    choices = wx.ListBox(panel, choices=[item.name for item in model.summaries()])
    root.Add(choices, 1, wx.EXPAND | wx.ALL, 8)
    panel.SetSizer(root)
    frame.Show()
    return wx.ID_OK


__all__ = ["HostKeyRequest", "KeyboardInteractiveRequest", "ProfileSummary", "WxConnectionModel", "show_connection"]
