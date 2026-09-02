"""wx adapter for the shared help, palette, and shortcut models."""

from __future__ import annotations

from hpc_gui.core.platform import current_os
from hpc_gui.core.i18n import t
from hpc_gui.services.command_palette import CommandPalette
from hpc_gui.services.help_catalog import is_allowed_external_url
from hpc_gui.services.help_search import HelpSearchIndex
from hpc_gui.services.shortcut_preferences import ShortcutPreferences


class WxHelpModel:
    """Headless screen model, kept usable for keyboard/accessibility tests."""

    def __init__(self, platform: str | None = None, settings=None) -> None:
        self.platform = platform or current_os()
        self.shortcuts = ShortcutPreferences(self.platform, settings)
        self.palette = CommandPalette()
        self.search_index = HelpSearchIndex()

    def search_help(self, query: str):
        return self.search_index.search(query, platform=self.platform)

    def palette_search(self, query: str = ""):
        return self.palette.search(query)

    def set_binding(self, command_id: str, binding: str) -> None:
        self.shortcuts.set_binding(command_id, binding)

    def reset_binding(self, command_id: str) -> None:
        self.shortcuts.reset_command(command_id)

    def external_url_allowed(self, url: str, domains: set[str]) -> bool:
        return is_allowed_external_url(url, domains)


def show_help(parent=None) -> int:
    """Open a small optional wx help screen; raises clearly if wx is absent."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = WxHelpModel()
    frame = wx.Frame(parent, title="Help", size=(900, 650))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    search = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
    results = wx.ListBox(panel)
    search.SetName(t("help.help_title"))
    results.SetName(t("help.help_title"))
    root.Add(search, 0, wx.EXPAND | wx.ALL, 8)
    root.Add(results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    panel.SetSizer(root)

    def refresh(_event=None):
        results.Set([item.title for item in model.search_help(search.GetValue())])

    search.Bind(wx.EVT_TEXT, refresh)
    refresh()
    search.SetFocus()
    frame.Show()
    return wx.ID_OK


__all__ = ["WxHelpModel", "show_help"]
