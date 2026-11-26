"""Native trusted-tool controls for the installed plugin manager."""
from __future__ import annotations

from hpc_gui.core.i18n import t
from hpc_gui.plugins.trusted_tools import APPROVED_TRUSTED_TOOLS


def install_trusted_tool_controls(wx, panel, host, root_sizer, button_row, model, state, selected_card):
    note = wx.StaticText(panel, label="")
    note.Hide()
    root_sizer.Insert(3, note, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    button = wx.Button(panel, label=t("plugins.open_tool"))
    button_row.Insert(4, button, 0, wx.RIGHT, 8)

    def candidate(card):
        return bool(card and card.plugin_id in APPROVED_TRUSTED_TOOLS
                    and card.installed and card.enabled and card.active_version and not card.problem)

    def refresh(card):
        if state["closed"]:
            return
        disclose = bool(card and ("linter-tool" in card.capabilities
                                  or card.plugin_id in APPROVED_TRUSTED_TOOLS))
        note.SetLabel(t("plugins.trusted_tool_disclosure_short") if disclose else "")
        if disclose:
            note.Wrap(max(200, panel.GetClientSize().width - 24))
        note.Show(disclose)
        button.SetLabel(t("plugins.open_tool"))
        button.Enable(candidate(card) and not state["in_flight"])
        panel.Layout()

    def open_tool(_event):
        card = selected_card()
        if state["closed"] or state["in_flight"] or not candidate(card):
            return
        try:
            # Resolve from live installed state; registry/card data cannot grant trust.
            plugin = model.resolve_trusted_tool(card.plugin_id, card.active_version)
            from hpc_gui.services.wx_plugin_menu_host import WxPluginMenuHost

            if not WxPluginMenuHost(parent=host).open_trusted_tool(plugin):
                raise RuntimeError(t("plugins.action_failed"))
        except Exception as exc:
            wx.MessageBox(str(exc), t("common.error"), wx.OK | wx.ICON_ERROR, host)

    button.Bind(wx.EVT_BUTTON, open_tool)
    return {"open_tool": button, "trusted_tool_note": note}, refresh
