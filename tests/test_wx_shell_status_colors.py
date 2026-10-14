import sys
from types import SimpleNamespace

from hpc_gui.core.i18n import t
from hpc_gui.wx_shell_window_support import _update_shell_status_text


class _StatusBar:
    def __init__(self):
        self.background = "default-background"
        self.foreground = "default-foreground"
        self.text = ""

    def GetBackgroundColour(self):
        return self.background

    def GetForegroundColour(self):
        return self.foreground

    def SetBackgroundColour(self, value):
        self.background = value

    def SetForegroundColour(self, value):
        self.foreground = value

    def SetStatusText(self, value):
        self.text = value

    def Refresh(self):
        pass


class _Frame:
    def __init__(self):
        self.bar = _StatusBar()

    def IsBeingDeleted(self):
        return False

    def GetStatusBar(self):
        return self.bar


def test_status_bar_uses_red_while_connecting_green_when_connected_and_restores_idle(monkeypatch):
    fake_wx = SimpleNamespace(Colour=lambda red, green, blue: (red, green, blue))
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    frame = _Frame()

    _update_shell_status_text(frame, {"connection_status": "connecting"})
    assert frame.bar.text == t("login.status_connecting")
    assert frame.bar.background == (179, 38, 30)

    _update_shell_status_text(frame, {"connection_status": "authenticating"})
    assert frame.bar.text == t("login.status_connecting")
    assert frame.bar.background == (179, 38, 30)

    _update_shell_status_text(
        frame,
        {
            "connection_status": "connected",
            "session": {"connected": True, "profile": {"name": "cluster"}},
        },
    )
    assert "cluster" in frame.bar.text
    assert frame.bar.background == (28, 120, 56)

    _update_shell_status_text(frame, {"connection_status": "disconnected"})
    assert frame.bar.background == "default-background"
    assert frame.bar.foreground == "default-foreground"
