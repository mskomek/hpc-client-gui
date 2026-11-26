"""Native details, request URL and installed version switching controls."""
from __future__ import annotations

from threading import Thread

from hpc_gui.core.i18n import t
from hpc_gui.services.plugin_manager_state import is_newer_version
from hpc_gui.services.plugin_request import PLUGIN_REQUEST_URL, is_allowed_plugin_request_url


def install_management_controls(wx, panel, host, root_sizer, model, state, selected_card, refresh_list):
    row = wx.WrapSizer(wx.HORIZONTAL)
    details = wx.Button(panel, label=t("plugins.details"))
    versions = wx.Choice(panel)
    switch = wx.Button(panel, label=t("plugins.version"))
    request = wx.Button(panel, label=t("plugins.request_plugin"))
    for ctrl in (details, versions, switch, request):
        row.Add(ctrl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
    root_sizer.Insert(2, row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

    def show_details(_event):
        card = selected_card()
        if card and not state["closed"]:
            wx.MessageBox(model.details_for(card), f"{card.name} — {t('plugins.details')}", wx.OK | wx.ICON_INFORMATION, host)

    def request_plugin(_event):
        if state["closed"]:
            return
        if not is_allowed_plugin_request_url(PLUGIN_REQUEST_URL) or not wx.LaunchDefaultBrowser(PLUGIN_REQUEST_URL):
            wx.MessageBox(t("plugins.request_plugin_failed"), t("plugins.dialog_title"), wx.OK | wx.ICON_WARNING, host)

    def selected_version():
        idx = versions.GetSelection()
        return versions.GetString(idx) if idx != wx.NOT_FOUND else ""

    def update_switch(_event=None):
        card = selected_card()
        version = selected_version()
        active = card.active_version if card else None
        valid = bool(card and card.installed and card.enabled and active and version and version != active)
        switch.SetLabel(t("plugins.activate") if active and version and is_newer_version(version, active)
                        else t("plugins.rollback"))
        switch.Enable(valid and not state["closed"] and not state["in_flight"])

    def refresh(card):
        if state["closed"]:
            return
        details.SetLabel(t("plugins.details"))
        request.SetLabel(t("plugins.request_plugin"))
        details.Enable(card is not None)
        old = selected_version()
        available = model.installed_versions(card.plugin_id) if card and card.installed else ()
        versions.Set(list(available))
        wanted = old if old in available else card.active_version if card else None
        if wanted in available:
            versions.SetSelection(available.index(wanted))
        versions.Enable(bool(available) and not state["in_flight"])
        update_switch()

    def change_version(_event):
        card = selected_card()
        target = selected_version()
        if not switch.IsEnabled() or not card or state["closed"] or state["in_flight"]:
            return
        current = card.active_version
        key = "plugins.version_activate_confirm_text" if is_newer_version(target, current) else "plugins.version_rollback_confirm_text"
        if wx.MessageBox(t(key).format(name=card.name, version=target, current=current),
                         t("plugins.version_switch_confirm_title"),
                         wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, host) != wx.YES:
            return
        if state["closed"] or state["in_flight"] or selected_card() is not card:
            return
        state["in_flight"] = True
        state["gen"] += 1
        gen = state["gen"]
        refresh_list()

        def done(error):
            if state["closed"] or state["gen"] != gen:
                return
            state["in_flight"] = False
            model.reload_installed()
            key = "plugins.version_switch_failed" if error else "plugins.version_switch_success"
            wx.MessageBox(t(key).format(name=card.name, version=target),
                          t("plugins.version_switch_confirm_title"),
                          wx.OK | (wx.ICON_ERROR if error else wx.ICON_INFORMATION), host)
            refresh_list()

        def worker():
            try:
                model.rollback(card.plugin_id, target)
                wx.CallAfter(done, None)
            except Exception as exc:
                wx.CallAfter(done, exc)

        Thread(target=worker, daemon=True).start()

    details.Bind(wx.EVT_BUTTON, show_details)
    request.Bind(wx.EVT_BUTTON, request_plugin)
    switch.Bind(wx.EVT_BUTTON, change_version)
    versions.Bind(wx.EVT_CHOICE, update_switch)
    return {"details": details, "versions": versions, "switch_version": switch, "request": request}, refresh
