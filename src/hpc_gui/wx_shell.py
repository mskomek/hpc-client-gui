"""Optional wxPython migration shell; Qt remains the default runtime."""

from __future__ import annotations

from hpc_gui import __version__
from hpc_gui.core.i18n import load_saved_language, system_default_language, t
from hpc_gui.services.command_registry import COMMAND_REGISTRY


def main() -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed; use the default Qt runtime") from exc
    load_saved_language(system_default_language())
    app = wx.App(False)
    frame = wx.Frame(None, title=f"HPC Client GUI {__version__}", size=(960, 640))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    menu = wx.Menu()
    for command in COMMAND_REGISTRY.by_context("shell"):
        item = menu.Append(wx.ID_ANY, command.label())
        frame.Bind(wx.EVT_MENU, lambda _event, command_id=command.id: _dispatch(command_id), item)
    frame.SetMenuBar(wx.MenuBar())
    frame.GetMenuBar().Append(menu, t("help.help_title"))
    root.Add(wx.StaticText(panel, label=f"HPC Client GUI {__version__}"), 0, wx.ALL, 12)
    root.Add(wx.StaticText(panel, label="wx migration shell"), 0, wx.LEFT | wx.BOTTOM, 12)
    panel.SetSizer(root)
    frame.CreateStatusBar()
    frame.SetStatusText("Ready")
    frame.Show()
    app.MainLoop()
    return 0


def _dispatch(command_id: str) -> None:
    if command_id in {"APP-HELP", "APP-COMMAND-PALETTE"}:
        from hpc_gui.wx_help import show_help

        show_help()


__all__ = ["main"]
