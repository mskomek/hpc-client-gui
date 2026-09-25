"""wx plugins view backed by WxPluginManagerModel (W35 backend-driven GUI)."""

from __future__ import annotations

from threading import Thread

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.wx_host import make_host
from hpc_gui.wx_plugins import WxPluginManagerModel

_VIEW_IDS = ("discover", "installed", "updates")


def _view_label(view: str) -> str:
    mapping = {
        "discover": t("plugins.tab_discover"),
        "installed": t("plugins.tab_installed"),
        "updates": t("plugins.tab_updates"),
    }
    label = mapping.get(view, view)
    return label if label and not label.startswith("[plugins.") else view


def _status_label_for_source(source: str) -> str:
    if source == "network":
        text = t("plugins.status_online")
        return text if text != "[plugins.status_online]" else "Online"
    if source == "cache":
        text = t("plugins.status_cached")
        return text if text != "[plugins.status_cached]" else "Cached"
    text = t("plugins.status_offline")
    return text if text != "[plugins.status_offline]" else "Offline"


def _loading_label() -> str:
    text = t("plugins.status_loading")
    return text if text != "[plugins.status_loading]" else "Loading..."


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
    normalized_tab = str(initial_tab or "discover").strip().lower()
    if normalized_tab not in _VIEW_IDS:
        normalized_tab = "discover"
    # Spec §91: Plugins 800×600 resizable, §92 split 30-35% / 65-70%
    host, finish = make_host(parent, title=t("plugins.dialog_title"), size=(800, 600), embedded=embedded)
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

    view_choice = wx.Choice(panel, choices=[_view_label(v) for v in _VIEW_IDS])
    try:
        view_choice.SetSelection(_VIEW_IDS.index(normalized_tab))
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
    visible: list = []

    def _current_view() -> str:
        try:
            selection = view_choice.GetSelection()
        except Exception:
            selection = 0
        if 0 <= selection < len(_VIEW_IDS):
            return _VIEW_IDS[selection]
        return state["view"]

    def _refresh_list():
        del visible[:]
        needle = ""
        try:
            needle = search.GetValue()
        except Exception:
            needle = ""
        view = _current_view()
        state["view"] = view
        try:
            cards = model.filtered_cards(view, needle)
        except Exception:
            cards = tuple(model.cards)
        visible.extend(cards)
        list_ctrl.DeleteAllItems()
        for card in visible:
            idx = list_ctrl.InsertItem(list_ctrl.GetItemCount(), card.name or card.plugin_id)
            # W26 (HPC-W06-TODO-PLUGIN-COMPAT-001): version, install/enabled
            # state and compatibility must be visible where relevant.
            state_bits = []
            state_bits.append("installed" if card.installed else "available")
            state_bits.append("enabled" if card.enabled else "disabled")
            if not card.compatible:
                state_bits.append("incompatible")
            if card.update_available:
                state_bits.append("update-available")
            detail = f"{card.version} {' / '.join(state_bits)}"
            if card.active_version and card.active_version != card.version:
                detail += f" (active {card.active_version})"
            list_ctrl.SetItem(idx, 1, detail)
        _update_buttons()

    def _selected_card():
        idx = list_ctrl.GetFirstSelected()
        if idx == -1 or idx >= len(visible):
            return None
        return visible[idx]

    def _update_buttons():
        card = _selected_card()
        if card is None:
            btn_install.Enable(False)
            try:
                btn_install.SetLabel(t("plugins.install"))
            except Exception:
                pass
            btn_disable.Enable(False)
            btn_remove.Enable(False)
            return
        # Install/Update: fail-closed per selection (incompatible never offered).
        if not card.compatible:
            btn_install.Enable(False)
            try:
                btn_install.SetLabel(t("plugins.incompatible"))
            except Exception:
                pass
        elif card.update_available:
            btn_install.Enable(not state["in_flight"])
            try:
                btn_install.SetLabel(t("plugins.update"))
            except Exception:
                pass
        elif card.installed:
            btn_install.Enable(False)
            try:
                btn_install.SetLabel(t("plugins.installed_badge"))
            except Exception:
                pass
        else:
            btn_install.Enable(not state["in_flight"])
            try:
                btn_install.SetLabel(t("plugins.install"))
            except Exception:
                pass
        btn_disable.Enable(True)
        try:
            btn_disable.SetLabel(t("plugins.enable") if not card.enabled else t("plugins.disable"))
        except Exception:
            pass
        btn_remove.Enable(bool(card.installed))

    def refresh_registry(_event=None):
        if state["closed"] or state["in_flight"]:
            return
        state["in_flight"] = True
        state["gen"] += 1
        gen = state["gen"]
        btn_refresh.Enable(False)
        status.SetLabel(_loading_label())

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
                    status.SetLabel(_status_label_for_source("offline"))
                    try:
                        wx.MessageBox(
                            str(exc),
                            t("plugins.dialog_title"),
                            wx.OK | wx.ICON_ERROR,
                            host,
                        )
                    except Exception:
                        pass
                    _refresh_list()
                    return
                status.SetLabel(_status_label_for_source(result.source))
            else:
                # fetch_registry_with_cache already falls back to cache; a raise
                # here means neither network nor cache is available (offline).
                status.SetLabel(_status_label_for_source("offline"))
                try:
                    model.build_cards_from_registry(None, "offline", root=model.root)
                except Exception:
                    pass
            _refresh_list()

        Thread(target=worker, daemon=True).start()

    def do_install(_event=None):
        card = _selected_card()
        if not card or state["closed"] or state["in_flight"]:
            return
        if not card.compatible:
            try:
                wx.MessageBox(
                    t("plugins.incompatible"),
                    t("plugins.dialog_title"),
                    wx.OK | wx.ICON_ERROR,
                    host,
                )
            except Exception:
                pass
            return
        state["in_flight"] = True
        state["gen"] += 1
        gen = state["gen"]
        btn_install.Enable(False)
        status.SetLabel(_loading_label())
        plugin_id = card.plugin_id

        def worker():
            try:
                entry = model.registry_entry_for(plugin_id)
                payload = dict(entry) if entry is not None else {
                    "id": card.plugin_id,
                    "version": card.version,
                    "name": card.name,
                }
                if model.install is not None:
                    outcome = model.install_or_update(payload)
                else:
                    outcome = model.default_installer(payload)
                # Fail-closed: no backend action (None) is never success.
                if outcome is None:
                    raise RuntimeError("plugin installer produced no backend action")
                wx.CallAfter(on_done, gen, None, plugin_id)
            except Exception as exc:
                wx.CallAfter(on_done, gen, exc, plugin_id)

        def on_done(expected_gen, error, expected_plugin_id):
            state["in_flight"] = False
            if state["closed"] or expected_gen != state["gen"]:
                return
            btn_install.Enable(True)
            if error is not None:
                status.SetLabel(_status_label_for_source(model.registry_source))
                try:
                    wx.MessageBox(
                        str(error),
                        t("plugins.dialog_title"),
                        wx.OK | wx.ICON_ERROR,
                        host,
                    )
                except Exception:
                    pass
            else:
                try:
                    from hpc_gui.plugins.loader import load_installed_plugins

                    loaded = load_installed_plugins(
                        root=model.root, app_version=model.app_version
                    )
                    _ = loaded
                except Exception:
                    pass
                status.SetLabel(_status_label_for_source(model.registry_source))
                try:
                    name = expected_plugin_id
                    for candidate in visible:
                        if candidate.plugin_id == expected_plugin_id:
                            name = candidate.name or candidate.plugin_id
                            break
                    success_text = t("plugins.install_generic")
                    if success_text == "[plugins.install_generic]":
                        success_text = f"Installed {name}"
                    else:
                        try:
                            success_text = success_text.format(name=name)
                        except Exception:
                            pass
                    wx.MessageBox(
                        success_text,
                        t("plugins.dialog_title"),
                        wx.OK | wx.ICON_INFORMATION,
                        host,
                    )
                except Exception:
                    pass
            # Re-read installed state so enable/disable/update readback is live.
            try:
                from hpc_gui.plugins.storage import read_active_versions

                _ = read_active_versions(model.root)
            except Exception:
                pass
            _refresh_list()

        Thread(target=worker, daemon=True).start()

    def do_toggle(_event=None):
        card = _selected_card()
        if not card or state["closed"] or state["in_flight"]:
            return
        state["in_flight"] = True
        state["gen"] += 1
        gen = state["gen"]
        plugin_id = card.plugin_id
        target_enabled = not card.enabled

        def worker():
            try:
                model.set_enabled(plugin_id, target_enabled)
                wx.CallAfter(on_done, gen, None)
            except Exception as exc:
                wx.CallAfter(on_done, gen, exc)

        def on_done(expected_gen, error):
            state["in_flight"] = False
            if state["closed"] or expected_gen != state["gen"]:
                return
            if error is not None:
                try:
                    wx.MessageBox(
                        str(error), t("common.error"), wx.OK | wx.ICON_ERROR, host
                    )
                except Exception:
                    pass
            _refresh_list()

        Thread(target=worker, daemon=True).start()

    def do_remove(_event=None):
        card = _selected_card()
        if not card or state["closed"] or state["in_flight"]:
            return
        if not card.installed:
            return
        state["in_flight"] = True
        state["gen"] += 1
        gen = state["gen"]
        plugin_id = card.plugin_id

        def worker():
            try:
                model.remove(plugin_id)
                wx.CallAfter(on_done, gen, None)
            except Exception as exc:
                wx.CallAfter(on_done, gen, exc)

        def on_done(expected_gen, error):
            state["in_flight"] = False
            if state["closed"] or expected_gen != state["gen"]:
                return
            if error is not None:
                try:
                    wx.MessageBox(
                        str(error), t("common.error"), wx.OK | wx.ICON_ERROR, host
                    )
                except Exception:
                    pass
            _refresh_list()

        Thread(target=worker, daemon=True).start()

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
            host.set_host_title(t("plugins.dialog_title"))
            title.SetLabel(t("plugins.dialog_title"))
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
            current = _current_view()
            try:
                view_choice.Set([_view_label(v) for v in _VIEW_IDS])
                view_choice.SetSelection(_VIEW_IDS.index(current))
            except Exception:
                pass
            btn_refresh.SetLabel(t("plugins.refresh"))
            btn_disable.SetLabel(t("plugins.disable"))
            btn_remove.SetLabel(t("plugins.remove"))
            btn_close.SetLabel(t("common.close"))
            list_ctrl.SetColumnWidth(0, 200)
            _update_buttons()
        except Exception:
            pass

    btn_refresh.Bind(wx.EVT_BUTTON, refresh_registry)
    btn_install.Bind(wx.EVT_BUTTON, do_install)
    btn_disable.Bind(wx.EVT_BUTTON, do_toggle)
    btn_remove.Bind(wx.EVT_BUTTON, do_remove)
    btn_close.Bind(wx.EVT_BUTTON, lambda e: host.Close())
    try:
        list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda _e: (_refresh_list() if False else _update_buttons()) or _e.Skip())
        list_ctrl.Bind(wx.EVT_LIST_ITEM_DESELECTED, lambda _e: _update_buttons() or _e.Skip())
    except Exception:
        pass

    def on_view_changed(_event):
        if state["closed"]:
            return
        _refresh_list()

    def on_search(_event):
        # Truthful search: rebuild the list from the filtered model subset.
        # ListCtrl rows cannot be hidden, so filtering means rebuilding.
        if state["closed"]:
            return
        _refresh_list()

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
        "disable": btn_disable,
        "remove": btn_remove,
        "close": btn_close,
    }
    host._wx_plugins_model = model
    host._wx_plugins_state = state

    _refresh_list()
    finish()
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
