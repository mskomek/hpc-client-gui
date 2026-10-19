"""Session and queue scope controls layered onto the wx conflict dialog."""

from __future__ import annotations

from hpc_gui.core.i18n import t


def create_wx_transfer_conflict_dialog(parent, files, item):
    """Create the shared conflict dialog with an apply-to-this-queue option."""
    import wx

    from hpc_gui.wx_transfer_workspace import create_transfer_conflict_dialog

    dialog = create_transfer_conflict_dialog(parent, files, item)
    if dialog is None:
        return None

    controls = getattr(dialog, "_wx_conflict_controls", None)
    overwrite = controls.get("overwrite") if isinstance(controls, dict) else None
    if overwrite is None:
        # Keep lightweight dialog replacements usable by callers and adapters.
        return dialog

    panel = overwrite.GetParent()
    panel_sizer = panel.GetSizer()
    if panel_sizer is None:
        return dialog

    queue_checkbox = wx.CheckBox(
        panel, label=t("transfer.conflict_current_queue_only")
    )
    session_checkbox = wx.CheckBox(
        panel, label=t("transfer.conflict_always_use")
    )
    downloads_checkbox = wx.CheckBox(
        panel, label=t("transfer.conflict_downloads_only")
    )
    panel_sizer.Insert(1, queue_checkbox, 0, wx.ALL | wx.EXPAND, 12)
    panel_sizer.Insert(2, session_checkbox, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)
    panel_sizer.Insert(3, downloads_checkbox, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)
    panel_sizer.Layout()
    panel.Layout()
    dialog.Layout()
    dialog.Fit()
    dialog._wx_conflict_apply_all = queue_checkbox
    dialog._wx_conflict_always_use = session_checkbox
    dialog._wx_conflict_downloads_only = downloads_checkbox
    return dialog


__all__ = ["create_wx_transfer_conflict_dialog"]
