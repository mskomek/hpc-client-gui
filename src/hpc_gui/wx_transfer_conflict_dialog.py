"""Queue-scoped options layered onto the wx transfer conflict dialog."""

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

    checkbox = wx.CheckBox(panel, label=t("common.apply_all"))
    panel_sizer.Insert(1, checkbox, 0, wx.ALL | wx.EXPAND, 12)
    panel_sizer.Layout()
    panel.Layout()
    dialog.Layout()
    dialog.Fit()
    dialog._wx_conflict_apply_all = checkbox
    return dialog


__all__ = ["create_wx_transfer_conflict_dialog"]
