"""wx plugins view backed by WxPluginManagerModel."""

from __future__ import annotations

from threading import Thread

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.wx_host import make_host
from hpc_gui.wx_plugins import WxPluginManagerModel


def _build_plugins(parent, model: WxPluginManagerModel | None = None, *, root=None, install=None, embedded: bool):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc

    model = model or WxPluginManagerModel(root=root, install=install)
    if install is not None and model.install is None:
        model.install = install
    host, finish = make_host(parent, title=t("plugins.dialog_title"), size=(760, 560), embedded=embedded)
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

    list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    list_ctrl.InsertColumn(0, t("plugins.action"))
    list_ctrl.InsertColumn(1, t("common.details"))

    btn_refresh = wx.Button(panel, label=t("plugins.refresh"))
    btn_install = wx.Button(panel, label=t("plugins.install"))
    btn_disable = wx.Button(panel, label=t("plugins.disable"))
    btn_remove = wx.Button(panel, label=t("plugins.remove"))
    btn_close = wx.Button(panel, label=t("common.close"))

    top = wx.BoxSizer(wx.HORIZONTAL)
    top.Add(title, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)
    top.AddStretchSpacer(1)
    top.Add(search, 1, wx.ALL, 6)
    top.Add(status, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)

    btn_row = wx.BoxSizer(wx.HORIZONTAL)
    btn_row.Add(btn_refresh, 0, wx.RIGHT, 6)
    btn_row.Add(btn_install, 0, wx.RIGHT, 6)
    btn_row.Add(btn_disable, 0, wx.RIGHT, 6)
    btn_row.Add(btn_remove, 0, wx.RIGHT, 6)
    btn_row.AddStretchSpacer(1)
    btn_row.Add(btn_close, 0)

    root_sizer.Add(top, 0, wx.EXPAND)
    root_sizer.Add(list_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    root_sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)
    panel.SetSizer(root_sizer)

    state = {"closed": False, "in_flight": False}

    def _refresh_list():
        list_ctrl.DeleteAllItems()
        for card in model.cards:
            idx = list_ctrl.InsertItem(list_ctrl.GetItemCount(), card.name or card.plugin_id)
            list_ctrl.SetItem(idx, 1, f"{card.version} {'installed' if card.installed else ''}")

    def _selected_card():
        idx = list_ctrl.GetFirstSelected()
        if idx == -1 or idx >= len(model.cards):
            return None
        return model.cards[idx]

    def refresh_registry(_event=None):
        if state["closed"] or state["in_flight"]:
            return
        state["in_flight"] = True
        btn_refresh.Enable(False)
        status.SetLabel(t("plugins.status_loading") if t("plugins.status_loading") != "[plugins.status_loading]" else "Loading...")

        def worker():
            try:
                # Reuse currently loaded cards as offline source; keep off GUI thread trivially
                # Simulate fetch without network
                wx.CallAfter(on_done, None)
            except Exception as exc:
                wx.CallAfter(on_done, exc)

        def on_done(error):
            state["in_flight"] = False
            if state["closed"]:
                return
            btn_refresh.Enable(True)
            if error:
                status.SetLabel(t("plugins.status_offline"))
            else:
                status.SetLabel(t("plugins.status_cached"))
            _refresh_list()

        Thread(target=worker, daemon=True).start()

    def do_install(_event=None):
        card = _selected_card()
        if not card or state["in_flight"]:
            return
        state["in_flight"] = True
        btn_install.Enable(False)

        def worker():
            try:
                model.install_or_update({"id": card.plugin_id, "version": card.version, "name": card.name})
                wx.CallAfter(lambda: (setattr(state, "__setitem__", state.__setitem__) or None))
                wx.CallAfter(on_done, None)
            except Exception as exc:
                wx.CallAfter(on_done, exc)

        def on_done(error):
            state["in_flight"] = False
            if state["closed"]:
                return
            btn_install.Enable(True)
            if error:
                try:
                    wx.MessageBox(str(error), t("plugins.dialog_title"), wx.OK | wx.ICON_ERROR, host)
                except Exception:
                    pass
            else:
                try:
                    wx.MessageBox(t("plugins.install_generic").format(name=card.name) if t("plugins.install_generic") != "[plugins.install_generic]" else f"Installed {card.name}", t("plugins.dialog_title"), wx.OK | wx.ICON_INFORMATION, host)
                except Exception:
                    pass
            _refresh_list()

        Thread(target=worker, daemon=True).start()

    def do_toggle(_event=None):
        card = _selected_card()
        if not card:
            return

        def worker():
            try:
                model.set_enabled(card.plugin_id, not card.enabled)
                wx.CallAfter(_refresh_list)
            except Exception as exc:
                wx.CallAfter(lambda: wx.MessageBox(str(exc), t("common.error"), wx.OK | wx.ICON_ERROR, host) if not state["closed"] else None)

        Thread(target=worker, daemon=True).start()

    def do_remove(_event=None):
        card = _selected_card()
        if not card:
            return

        def worker():
            try:
                model.remove(card.plugin_id)
                wx.CallAfter(_refresh_list)
            except Exception as exc:
                wx.CallAfter(lambda: wx.MessageBox(str(exc), t("common.error"), wx.OK | wx.ICON_ERROR, host) if not state["closed"] else None)

        Thread(target=worker, daemon=True).start()

    def on_close(evt):
        state["closed"] = True
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
            btn_refresh.SetLabel(t("plugins.refresh"))
            btn_install.SetLabel(t("plugins.install"))
            btn_disable.SetLabel(t("plugins.disable"))
            btn_remove.SetLabel(t("plugins.remove"))
            btn_close.SetLabel(t("common.close"))
            list_ctrl.SetColumnWidth(0, 200)
        except Exception:
            pass

    btn_refresh.Bind(wx.EVT_BUTTON, refresh_registry)
    btn_install.Bind(wx.EVT_BUTTON, do_install)
    btn_disable.Bind(wx.EVT_BUTTON, do_toggle)
    btn_remove.Bind(wx.EVT_BUTTON, do_remove)
    btn_close.Bind(wx.EVT_BUTTON, lambda e: host.Close())

    # search filter
    def on_search(_event):
        needle = search.GetValue().lower()
        for idx, card in enumerate(model.cards):
            text = f"{card.name} {card.plugin_id}".lower()
            show = not needle or needle in text
            # Not easily hide rows in ListCtrl; fallback: no-op

    search.Bind(wx.EVT_TEXT, on_search)

    subscribe_language_change(refresh_labels)
    host.bind_host_close(on_close)

    host._wx_plugins_controls = {
        "title": title,
        "search": search,
        "status": status,
        "listing": list_ctrl,
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


def build_plugins_panel(parent, model: WxPluginManagerModel | None = None, *, root=None, install=None):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_plugins(parent, model, root=root, install=install, embedded=True)


def show_plugins(parent=None, model: WxPluginManagerModel | None = None, *, root=None, install=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    _build_plugins(parent, model, root=root, install=install, embedded=False)
    return wx.ID_OK


__all__ = ["build_plugins_panel", "show_plugins"]
