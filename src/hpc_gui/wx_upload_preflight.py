"""Native read-only confirmation before any upload queue or folder creation."""
from __future__ import annotations

from hpc_gui.config.storage import (
    get_upload_preflight_confirmation_enabled,
    set_upload_preflight_confirmation_enabled,
)
from hpc_gui.core.i18n import t
from hpc_gui.services.upload_plan import summarize_upload_plan


def create_upload_preflight(parent, items, parallel_limit: int):
    import wx

    summary = summarize_upload_plan(items, parallel_limit)
    dialog = wx.Dialog(parent, title=t("transfer.preflight_title"),
                       style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    label = wx.StaticText(dialog, label=t("transfer.preflight_summary").format(
        files=summary.files, folders=summary.folders,
        steps=summary.steps, parallel=summary.parallel,
    ))
    label.Wrap(760)
    root.Add(label, 0, wx.ALL | wx.EXPAND, 12)
    listing = wx.ListCtrl(dialog, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    for index, (key, width) in enumerate((
        ("operation", 160), ("source", 300), ("destination", 300),
    )):
        listing.InsertColumn(index, t("transfer.preflight_" + key), width=width)
    labels = {
        "upload": t("transfer.preflight_upload"),
        "mkdir_remote": t("transfer.preflight_create_folder"),
        "delete": t("transfer.preflight_delete"),
    }
    for item in summary.visible:
        row = listing.InsertItem(listing.GetItemCount(), labels.get(item.op, item.op))
        listing.SetItem(row, 1, item.src or "—")
        listing.SetItem(row, 2, item.dst or "—")
    if summary.hidden:
        listing.InsertItem(listing.GetItemCount(), t("transfer.remaining").format(hidden=summary.hidden))
    root.Add(listing, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 12)
    dont_ask = wx.CheckBox(dialog, label=t("transfer.preflight_dont_ask_again"))
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    start = wx.Button(dialog, wx.ID_OK, t("transfer.preflight_start"))
    cancel = wx.Button(dialog, wx.ID_CANCEL, t("common.cancel"))
    buttons.Add(dont_ask, 0, wx.ALIGN_CENTER_VERTICAL)
    buttons.AddStretchSpacer()
    buttons.Add(start, 0, wx.RIGHT, 8)
    buttons.Add(cancel, 0)
    root.Add(buttons, 0, wx.ALL | wx.EXPAND, 12)
    dialog.SetSizer(root)
    dialog.SetSize((850, 480))
    dialog.CentreOnParent()
    # Enter defaults to cancellation rather than a destructive transfer.
    cancel.SetDefault()
    dialog._wx_upload_preflight_controls = {
        "summary": label, "listing": listing, "dont_ask": dont_ask,
        "start": start, "cancel": cancel,
    }
    return dialog


def confirm_upload_plan(parent, items, parallel_limit: int, *, still_current=lambda: True) -> bool:
    if not still_current():
        return False
    if not get_upload_preflight_confirmation_enabled():
        return True
    import wx

    dialog = create_upload_preflight(parent, items, parallel_limit)
    try:
        if dialog.ShowModal() != wx.ID_OK or not still_current():
            return False
        if dialog._wx_upload_preflight_controls["dont_ask"].GetValue():
            set_upload_preflight_confirmation_enabled(False)
        return True
    finally:
        dialog.Destroy()
