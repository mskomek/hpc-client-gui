"""Optional wxPython migration shell; Qt remains the default runtime."""

from __future__ import annotations

import os

from hpc_gui import __version__
from hpc_gui.core.i18n import load_saved_language, set_language, subscribe_language_change, system_default_language, t, unsubscribe_language_change
from hpc_gui.services.command_registry import COMMAND_REGISTRY
from hpc_gui.wx_lifecycle import WxLifecycleController
from hpc_gui.wx_runtime import environment_without_qt_graphics


def main() -> int:
    clean_environment = environment_without_qt_graphics()
    for name in set(os.environ) - set(clean_environment):
        os.environ.pop(name, None)
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed; use the default Qt runtime") from exc
    load_saved_language(system_default_language())
    app = wx.App(False)
    lifecycle = WxLifecycleController()
    frame = wx.Frame(None, title=f"HPC Client GUI {__version__}", size=(960, 640))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    menu = wx.Menu()
    for command in COMMAND_REGISTRY.by_context("shell"):
        item = menu.Append(wx.ID_ANY, command.label())
        frame.Bind(wx.EVT_MENU, lambda _event, command_id=command.id: _dispatch(command_id, frame, lifecycle), item)
    frame.SetMenuBar(wx.MenuBar())
    frame.GetMenuBar().Append(menu, t("help.help_title"))
    language_menu = wx.Menu()
    language_items = {}
    for language, key in (("en", "english"), ("tr", "turkish")):
        item = language_menu.Append(wx.ID_ANY, t(f"help.{key}"))
        language_items[language] = item
        frame.Bind(wx.EVT_MENU, lambda _event, language=language: set_language(language), item)
    frame.GetMenuBar().Append(language_menu, t("help.language"))
    root.Add(wx.StaticText(panel, label=f"HPC Client GUI {__version__}"), 0, wx.ALL, 12)
    root.Add(wx.StaticText(panel, label="wx migration shell"), 0, wx.LEFT | wx.BOTTOM, 12)
    panel.SetSizer(root)
    frame.CreateStatusBar()
    frame.SetStatusText(t("common.ready"))

    def refresh_labels(_language=None):
        frame.SetTitle(f"{t('app.title')} {__version__}")
        frame.SetStatusText(t("common.ready"))
        frame.GetMenuBar().SetLabelTop(0, t("help.help_title"))
        frame.GetMenuBar().SetLabelTop(1, t("help.language"))
        for language, item in language_items.items():
            language_menu.SetLabel(item.GetId(), t("help.english" if language == "en" else "help.turkish"))

    subscribe_language_change(refresh_labels)

    tray = None
    try:
        import wx.adv

        class TrayIcon(wx.adv.TaskBarIcon):
            def CreatePopupMenu(self):
                menu = wx.Menu()
                close = menu.Append(wx.ID_EXIT, "Exit")
                self.Bind(wx.EVT_MENU, lambda _event: frame.Close(), close)
                return menu

        tray = TrayIcon()
        tray.SetIcon(wx.ArtProvider.GetIcon(wx.ART_INFORMATION), "HPC Client GUI")
        lifecycle.set_tray_notifier(lambda message: tray.ShowBalloon(t("login.job_notification_title"), message, 5000))
    except (ImportError, RuntimeError):
        pass

    def close(_event):
        unsubscribe_language_change(refresh_labels)
        lifecycle.set_tray_notifier(None)
        lifecycle.shutdown()
        if tray:
            tray.Destroy()
        frame.Destroy()

    frame.Bind(wx.EVT_CLOSE, close)
    frame.Show()
    app.MainLoop()
    return 0


def _dispatch(command_id: str, parent=None, lifecycle=None) -> None:
    if command_id in {"APP-HELP", "APP-COMMAND-PALETTE"}:
        from hpc_gui.wx_help import show_help

        show_help(parent)
    elif command_id == "APP-CONNECT":
        from hpc_gui.wx_connection import show_connection

        show_connection(parent)
    elif command_id == "NAV-FILES":
        from hpc_gui.wx_local_files import show_local_files

        show_local_files(parent)
    elif command_id == "NAV-EDITOR":
        from hpc_gui.wx_editor_view import show_editor

        show_editor(parent)
    elif command_id == "NAV-JOBS":
        from hpc_gui.wx_jobs import show_jobs

        show_jobs(parent, lifecycle=lifecycle)


__all__ = ["main"]
