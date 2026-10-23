"""wx plugins view backed by WxPluginManagerModel (W35 backend-driven GUI)."""

from __future__ import annotations

from threading import Thread

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.plugins.test_catalog import mark_test_catalog_title
from hpc_gui.wx_host import make_host
from hpc_gui.wx_plugins import WxPluginManagerModel
from hpc_gui.wx_plugins_view_actions import PluginLifecycleActions
from hpc_gui.wx_plugins_view_projection import (
    VIEW_IDS,
    PluginListProjection,
    loading_label,
    status_label_for_source,
    view_label,
)


def _build_plugins(
    parent,
    model: WxPluginManagerModel | None = None,
    *,
    root=None,
    install=None,
    fetcher=None,
    initial_tab: str = "discover",
    embedded: bool,
):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc

    model = model or WxPluginManagerModel(root=root, install=install, fetcher=fetcher)
    if install is not None and model.install is None:
        model.install = install
    if fetcher is not None and getattr(model, "fetcher", None) is None:
        model.fetcher = fetcher
    if root is not None and model.root is None:
        model.root = root
    refresh_on_open = not bool(model.cards)
    if refresh_on_open:
        try:
            model.refresh_installed_state()
        except Exception:
            pass
    normalized_tab = str(initial_tab or "discover").strip().lower()
    if normalized_tab not in VIEW_IDS:
        normalized_tab = "discover"
    # Spec §91: Plugins 800×600 resizable, §92 split 30-35% / 65-70%
    host, finish = make_host(parent, title=_plugin_title(), size=(800, 600), embedded=embedded)
    panel = wx.Panel(host)
    root_sizer = wx.BoxSizer(wx.VERTICAL)

    title = wx.StaticText(panel, label=_plugin_title())
    title.SetFont(title.GetFont().Bold())

    search = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
    try:
        search.SetHint(t("plugins.search_placeholder"))
    except Exception:
        pass
    status = wx.StaticText(
        panel, label=loading_label() if refresh_on_open else ""
    )

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
    btn_rollback = wx.Button(panel, label=t("plugins.rollback"))
    btn_disable = wx.Button(panel, label=t("plugins.disable"))
    btn_remove = wx.Button(panel, label=t("plugins.remove"))
    btn_close = wx.Button(panel, label=t("common.close"))

    def fit_list_columns(event=None):
        try:
            width = int(list_ctrl.GetClientSize().width)
            first = min(200, max(120, width // 3))
            list_ctrl.SetColumnWidth(0, first)
            list_ctrl.SetColumnWidth(1, max(100, width - first - 8))
        except Exception:
            pass
        if event is not None:
            event.Skip()

    list_ctrl.Bind(wx.EVT_SIZE, fit_list_columns)

    top = wx.BoxSizer(wx.HORIZONTAL)
    top.Add(title, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 12)
    top.AddStretchSpacer(1)
    top.Add(view_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 12)
    top.Add(search, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 12)
    top.Add(status, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 12)

    btn_row = wx.BoxSizer(wx.HORIZONTAL)
    btn_row.Add(btn_refresh, 0, wx.RIGHT, 8)
    btn_row.Add(btn_install, 0, wx.RIGHT, 8)
    btn_row.Add(btn_rollback, 0, wx.RIGHT, 8)
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
        label=t("plugins.lifecycle_effect_note")
        if t("plugins.lifecycle_effect_note") != "[plugins.lifecycle_effect_note]"
        else "Disabling a plugin stops its profiles, templates, rules and tools "
        "the next time plugins load. No app restart is needed.",
    )
    try:
        effect_note.Wrap(760)
    except Exception:
        pass
    root_sizer.Add(effect_note, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    # Spec §16 footer 12-16px
    root_sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 16)
    panel.SetSizer(root_sizer)

    state = {"closed": False, "in_flight": False, "gen": 0, "view": normalized_tab}
    projection = PluginListProjection(
        model, view_choice, search, list_ctrl, state,
        btn_install, btn_disable, btn_remove, btn_rollback,
    )

    def refresh_registry(_event=None):
        if state["closed"] or state["in_flight"]:
            return
        state["in_flight"] = True
        state["gen"] += 1
        gen = state["gen"]
        btn_refresh.Enable(False)
        status.SetLabel(loading_label())

        def worker():
            try:
                from hpc_gui.plugins.registry_client import fetch_registry_with_cache

                result = fetch_registry_with_cache(
                    root=model.root, fetcher=model.fetcher
                )
                wx.CallAfter(on_done, gen, result, None)
            except Exception as exc:
                wx.CallAfter(on_done, gen, None, exc)

        def on_done(expected_gen, result, error):
            state["in_flight"] = False
            if state["closed"] or expected_gen != state["gen"]:
                return
            btn_refresh.Enable(True)
            if result is not None:
                try:
                    model.build_cards_from_registry(
                        result.registry, result.source, root=model.root
                    )
                except Exception as exc:
                    status.SetLabel(status_label_for_source("offline"))
                    try:
                        wx.MessageBox(
                            str(exc),
                            _plugin_title(),
                            wx.OK | wx.ICON_ERROR,
                            host,
                        )
                    except Exception:
                        pass
                    projection.refresh()
                    return
                status.SetLabel(status_label_for_source(result.source))
            else:
                # fetch_registry_with_cache already falls back to cache; a raise
                # here means neither network nor cache is available (offline).
                status.SetLabel(status_label_for_source("offline"))
                try:
                    model.build_cards_from_registry(None, "offline", root=model.root)
                except Exception:
                    pass
            projection.refresh()

        Thread(target=worker, daemon=True).start()

    actions = PluginLifecycleActions(wx, host, model, state, projection, status, btn_install)

    def on_close(evt):
        state["closed"] = True
        state["gen"] += 1
        state["in_flight"] = False
        unsubscribe_language_change(refresh_labels)
        evt.Skip()

    def refresh_labels(_language=None):
        if state["closed"]:
            return
        try:
            host.set_host_title(_plugin_title())
            title.SetLabel(_plugin_title())
            try:
                search.SetHint(t("plugins.search_placeholder"))
            except Exception:
                pass
            effect_note.SetLabel(t("plugins.lifecycle_effect_note"))
            try:
                effect_note.Wrap(760)
            except Exception:
                pass
            # Keep the view choice truthful across language changes.
            current = projection.current_view()
            try:
                view_choice.Set([view_label(v) for v in VIEW_IDS])
                view_choice.SetSelection(VIEW_IDS.index(current))
            except Exception:
                pass
            btn_refresh.SetLabel(t("plugins.refresh"))
            btn_rollback.SetLabel(t("plugins.rollback"))
            btn_disable.SetLabel(t("plugins.disable"))
            btn_remove.SetLabel(t("plugins.remove"))
            btn_close.SetLabel(t("common.close"))
            fit_list_columns()
            projection.update_buttons()
        except Exception:
            pass

    btn_refresh.Bind(wx.EVT_BUTTON, refresh_registry)
    btn_install.Bind(wx.EVT_BUTTON, actions.install)
    btn_rollback.Bind(wx.EVT_BUTTON, actions.rollback)
    btn_disable.Bind(wx.EVT_BUTTON, actions.toggle)
    btn_remove.Bind(wx.EVT_BUTTON, actions.remove)
    btn_close.Bind(wx.EVT_BUTTON, lambda e: host.Close())
    try:
        list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda _e: projection.update_buttons() or _e.Skip())
        list_ctrl.Bind(wx.EVT_LIST_ITEM_DESELECTED, lambda _e: projection.update_buttons() or _e.Skip())
    except Exception:
        pass

    def on_view_changed(_event):
        if state["closed"]:
            return
        projection.refresh()

    def on_search(_event):
        # Truthful search: rebuild the list from the filtered model subset.
        # ListCtrl rows cannot be hidden, so filtering means rebuilding.
        if state["closed"]:
            return
        projection.refresh()

    view_choice.Bind(wx.EVT_CHOICE, on_view_changed)
    search.Bind(wx.EVT_TEXT, on_search)

    subscribe_language_change(refresh_labels)
    host.bind_host_close(on_close)

    host._wx_plugins_controls = {
        "title": title,
        "search": search,
        "status": status,
        "view": view_choice,
        "listing": list_ctrl,
        "lifecycle_note": effect_note,
        "refresh": btn_refresh,
        "install": btn_install,
        "rollback": btn_rollback,
        "disable": btn_disable,
        "remove": btn_remove,
        "close": btn_close,
    }
    host._wx_plugins_model = model
    host._wx_plugins_state = state

    finish()
    fit_list_columns()
    wx.CallAfter(fit_list_columns)
    projection.refresh()
    if refresh_on_open:
        wx.CallAfter(refresh_registry)
    return host


def build_plugins_panel(
    parent,
    model: WxPluginManagerModel | None = None,
    *,
    root=None,
    install=None,
    fetcher=None,
    initial_tab: str = "discover",
):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_plugins(
        parent,
        model,
        root=root,
        install=install,
        fetcher=fetcher,
        initial_tab=initial_tab,
        embedded=True,
    )


def _plugin_title() -> str:
    """Plugin Manager title; carries the visible TEST CATALOG badge in test mode."""
    return mark_test_catalog_title(t("plugins.dialog_title"), t("plugins.test_catalog_badge"))


def show_plugins(
    parent=None,
    model: WxPluginManagerModel | None = None,
    *,
    root=None,
    install=None,
    fetcher=None,
    initial_tab: str = "discover",
) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    _build_plugins(
        parent,
        model,
        root=root,
        install=install,
        fetcher=fetcher,
        initial_tab=initial_tab,
        embedded=False,
    )
    return wx.ID_OK


__all__ = ["build_plugins_panel", "show_plugins"]
