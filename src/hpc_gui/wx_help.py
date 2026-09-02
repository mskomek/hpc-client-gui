"""Native wx Help Center backed by the shared catalog and search index."""

from __future__ import annotations

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.core.platform import current_os
from hpc_gui.services.command_palette import CommandPalette
from hpc_gui.services.help_catalog import HELP_CATALOG, is_allowed_external_url
from hpc_gui.services.help_search import HelpSearchIndex
from hpc_gui.services.shortcut_preferences import ShortcutPreferences


class WxHelpModel:
    def __init__(self, platform: str | None = None, settings=None) -> None:
        self.platform = platform or current_os()
        self.shortcuts = ShortcutPreferences(self.platform, settings)
        self.palette = CommandPalette()
        self.catalog = HELP_CATALOG
        self.search_index = HelpSearchIndex(self.catalog)
        self.current_topic_id = self.catalog.navigation()[0].id

    def navigation(self):
        return self.catalog.navigation()

    def select_topic(self, topic_id: str) -> str:
        if topic_id not in {item.id for item in self.navigation()}:
            raise KeyError(topic_id)
        self.current_topic_id = topic_id
        return self.page()

    def page(self) -> str:
        def binding(command_id):
            return next((item.binding for item in self.shortcuts.bindings() if item.command_id == command_id), None)

        return self.catalog.render_page(self.current_topic_id, self.platform, binding)

    def search_help(self, query: str):
        return self.search_index.search(query, platform=self.platform)

    def navigate_result(self, result):
        if result.kind == "topic" and result.id in {item.id for item in self.navigation()}:
            self.current_topic_id = result.id
        elif result.kind == "static":
            self.current_topic_id = "help.library.truba" if "TRUBA" in result.id else "help.library.generic" if "GENERIC" in result.id else self.current_topic_id
        return self.page()

    def palette_search(self, query: str = ""):
        return self.palette.search(query)

    def set_binding(self, command_id: str, binding: str) -> None:
        self.shortcuts.set_binding(command_id, binding)

    def reset_binding(self, command_id: str) -> None:
        self.shortcuts.reset_command(command_id)

    def external_url_allowed(self, url: str, domains: set[str]) -> bool:
        return is_allowed_external_url(url, domains)


def show_help(parent=None, topic_id: str | None = None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = WxHelpModel()
    if topic_id:
        model.select_topic(topic_id)
    frame = wx.Frame(parent, title=t("help.help_title"), size=(980, 700))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    search = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
    search.SetHint(t("help.search_placeholder"))
    split = wx.SplitterWindow(panel)
    sidebar = wx.ListBox(split)
    content = wx.TextCtrl(split, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    split.SplitVertically(sidebar, content, 260)
    split.SetMinimumPaneSize(180)
    close = wx.Button(panel, label=t("common.close"))
    root.Add(search, 0, wx.EXPAND | wx.ALL, 8)
    root.Add(split, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
    root.Add(close, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
    panel.SetSizer(root)
    navigation = model.navigation()

    def refresh(_lang=None):
        sidebar.Set([item.title() for item in navigation])
        sidebar.SetSelection(next((index for index, item in enumerate(navigation) if item.id == model.current_topic_id), 0))
        content.SetValue(model.page())
        frame.SetTitle(t("help.help_title"))

    def choose(_event):
        model.select_topic(navigation[sidebar.GetSelection()].id)
        refresh()

    def search_changed(_event):
        results = model.search_help(search.GetValue())
        if results:
            model.navigate_result(results[0])
            refresh()

    sidebar.Bind(wx.EVT_LISTBOX, choose)
    search.Bind(wx.EVT_TEXT, search_changed)
    close.Bind(wx.EVT_BUTTON, lambda _event: frame.Close())
    def on_language(lang):
        wx.CallAfter(refresh, lang)

    subscribe_language_change(on_language)
    frame.Bind(wx.EVT_CLOSE, lambda event: (unsubscribe_language_change(on_language), event.Skip()))
    refresh()
    frame.Show()
    return wx.ID_OK


__all__ = ["WxHelpModel", "show_help"]
