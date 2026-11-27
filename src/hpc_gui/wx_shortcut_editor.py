"""wx editor for persisted keyboard shortcut preferences."""

from __future__ import annotations

from hpc_gui.core.i18n import t


def build_shortcut_editor(wx, parent, preferences, error_parent):
    """Return a Settings group, its controls and a language refresh callback."""
    group = wx.StaticBoxSizer(wx.VERTICAL, parent, t("settings.shortcuts_section"))
    listing = wx.ListBox(group.GetStaticBox())
    group.Add(listing, 1, wx.EXPAND | wx.ALL, 4)
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    change = wx.Button(group.GetStaticBox(), label=t("settings.shortcut_change"))
    reset = wx.Button(group.GetStaticBox(), label=t("settings.shortcut_reset"))
    reset_all = wx.Button(group.GetStaticBox(), label=t("settings.shortcuts_reset_all"))
    buttons.Add(change, 0, wx.RIGHT, 4)
    buttons.Add(reset, 0, wx.RIGHT, 4)
    buttons.Add(reset_all, 0)
    group.Add(buttons, 0, wx.ALL, 4)

    def refresh():
        selected = listing.GetClientData(listing.GetSelection()) if listing.GetSelection() != wx.NOT_FOUND else None
        listing.Clear()
        selected_index = wx.NOT_FOUND
        for item in sorted(preferences.bindings(), key=lambda row: (row.context, row.command_id, row.binding)):
            listing.Append(f"{item.context}: {item.command_id} — {item.binding}", clientData=item.command_id)
            if item.command_id == selected:
                selected_index = listing.GetCount() - 1
        listing.SetSelection(selected_index)
        enabled = listing.GetSelection() != wx.NOT_FOUND
        change.Enable(enabled)
        reset.Enable(enabled)

    def selected_command():
        index = listing.GetSelection()
        return listing.GetClientData(index) if index != wx.NOT_FOUND else None

    def report_error(exc):
        from hpc_gui.core.wx_errors import report_wx_action_error

        report_wx_action_error(error_parent, area="SETTINGS", message_key="settings.apply_failed", exc=exc)

    def change_binding(_event=None):
        command_id = selected_command()
        if not command_id:
            return
        current = next((item.binding for item in preferences.bindings() if item.command_id == command_id), "")
        dialog = wx.TextEntryDialog(
            error_parent,
            t("settings.shortcut_binding_prompt"),
            t("settings.shortcuts_section"),
            value=current,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            binding = dialog.GetValue().strip()
            from hpc_gui.wx_shortcuts import to_wx_accel

            if to_wx_accel(wx, binding) is None:
                raise ValueError(t("settings.shortcut_invalid_binding"))
            preferences.set_binding(command_id, binding)
            refresh()
        except Exception as exc:
            report_error(exc)
        finally:
            dialog.Destroy()

    def reset_binding(_event=None):
        command_id = selected_command()
        if not command_id:
            return
        try:
            preferences.reset_command(command_id)
            refresh()
        except Exception as exc:
            report_error(exc)

    def reset_all_bindings(_event=None):
        preferences.reset_all()
        refresh()

    def refresh_labels():
        group.GetStaticBox().SetLabel(t("settings.shortcuts_section"))
        change.SetLabel(t("settings.shortcut_change"))
        reset.SetLabel(t("settings.shortcut_reset"))
        reset_all.SetLabel(t("settings.shortcuts_reset_all"))

    listing.Bind(wx.EVT_LISTBOX, lambda _event: (change.Enable(True), reset.Enable(True)))
    change.Bind(wx.EVT_BUTTON, change_binding)
    reset.Bind(wx.EVT_BUTTON, reset_binding)
    reset_all.Bind(wx.EVT_BUTTON, reset_all_bindings)
    refresh()
    return group, {"list": listing, "change": change, "reset": reset, "reset_all": reset_all}, refresh_labels


__all__ = ["build_shortcut_editor"]
