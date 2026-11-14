"""Layout construction for the wx plugins view (widgets only, no behavior)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hpc_gui.core.i18n import t
from hpc_gui.wx_host import make_host

VIEW_IDS = ("discover", "installed", "updates")


def view_label(view: str) -> str:
    mapping = {
        "discover": t("plugins.tab_discover"),
        "installed": t("plugins.tab_installed"),
        "updates": t("plugins.tab_updates"),
    }
    label = mapping.get(view, view)
    return label if label and not label.startswith("[plugins.") else view


def status_label_for_source(source: str) -> str:
    if source == "network":
        text = t("plugins.status_online")
        return text if text != "[plugins.status_online]" else "Online"
    if source == "cache":
        text = t("plugins.status_cached")
        return text if text != "[plugins.status_cached]" else "Cached"
    text = t("plugins.status_offline")
    return text if text != "[plugins.status_offline]" else "Offline"


def loading_label() -> str:
    text = t("plugins.status_loading")
    return text if text != "[plugins.status_loading]" else "Loading..."


@dataclass(frozen=True)
class PluginsChrome:
    """Widgets and lifecycle handles produced by build_plugins_chrome."""

    host: Any
    finish: Any
    title: Any
    search: Any
    status: Any
    view: Any
    listing: Any
    effect_note: Any
    refresh: Any
    install: Any
    disable: Any
    remove: Any
    close: Any


def build_plugins_chrome(
    wx,
    parent,
    *,
    embedded: bool,
    normalized_tab: str,
) -> PluginsChrome:
    # Spec §91: Plugins 800×600 resizable, §92 split 30-35% / 65-70%
    host, finish = make_host(
        parent,
        title=t("plugins.dialog_title"),
        size=(800, 600),
        embedded=embedded,
    )
    panel = wx.Panel(host)
    root_sizer = wx.BoxSizer(wx.VERTICAL)

    title = wx.StaticText(panel, label=t("plugins.dialog_title"))
    title.SetFont(title.GetFont().Bold())

    search = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
    try:
        search.SetHint(t("plugins.search_placeholder"))
    except Exception:
        pass
    status = wx.StaticText(panel, label="")

    view_choice = wx.Choice(panel, choices=[view_label(v) for v in VIEW_IDS])
    try:
        view_choice.SetSelection(VIEW_IDS.index(normalized_tab))
    except Exception:
        try:
            view_choice.SetSelection(0)
        except Exception:
            pass

    list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    list_ctrl.InsertColumn(0, t("plugins.action"))
    list_ctrl.InsertColumn(1, t("common.details"))

    btn_refresh = wx.Button(panel, label=t("plugins.refresh"))
    btn_install = wx.Button(panel, label=t("plugins.install"))
    btn_disable = wx.Button(panel, label=t("plugins.disable"))
    btn_remove = wx.Button(panel, label=t("plugins.remove"))
    btn_close = wx.Button(panel, label=t("common.close"))

    top = wx.BoxSizer(wx.HORIZONTAL)
    top.Add(title, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 12)
    top.AddStretchSpacer(1)
    top.Add(view_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 12)
    top.Add(search, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 12)
    top.Add(status, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 12)

    btn_row = wx.BoxSizer(wx.HORIZONTAL)
    btn_row.Add(btn_refresh, 0, wx.RIGHT, 8)
    btn_row.Add(btn_install, 0, wx.RIGHT, 8)
    btn_row.Add(btn_disable, 0, wx.RIGHT, 8)
    btn_row.Add(btn_remove, 0, wx.RIGHT, 8)
    btn_row.AddStretchSpacer(1)
    btn_row.Add(btn_close, 0)

    root_sizer.Add(top, 0, wx.EXPAND)
    root_sizer.Add(list_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    # W33 (HPC-W08-LIFE-005): state the real enable/disable behavior where
    # the toggle is offered; a bare checkbox is misleading.
    effect_note = wx.StaticText(
        panel,
        label=t("plugins.lifecycle_effect_note"),
    )
    try:
        effect_note.Wrap(760)
    except Exception:
        pass
    root_sizer.Add(effect_note, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    # Spec §16 footer 12-16px
    root_sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 16)
    panel.SetSizer(root_sizer)
    return PluginsChrome(
        host=host,
        finish=finish,
        title=title,
        search=search,
        status=status,
        view=view_choice,
        listing=list_ctrl,
        effect_note=effect_note,
        refresh=btn_refresh,
        install=btn_install,
        disable=btn_disable,
        remove=btn_remove,
        close=btn_close,
    )


def attach_plugins_state(host, chrome: PluginsChrome, model, state) -> None:
    """Publish the widgets and model state the host keeps for later lookups."""
    host._wx_plugins_controls = {
        "title": chrome.title,
        "search": chrome.search,
        "status": chrome.status,
        "view": chrome.view,
        "listing": chrome.listing,
        "lifecycle_note": chrome.effect_note,
        "refresh": chrome.refresh,
        "install": chrome.install,
        "disable": chrome.disable,
        "remove": chrome.remove,
        "close": chrome.close,
    }
    host._wx_plugins_model = model
    host._wx_plugins_state = state
