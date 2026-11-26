"""Transfer conflict dialog (branch-internal leaf, dialog ownership only)."""

from __future__ import annotations

from hpc_gui.services.transfer_conflict_policy import (
    ConflictFileInfo, destination_exists, destination_path, format_conflict_metadata, rename_destination,
)

from hpc_gui.core.i18n import t


def _supports_resume(files, item) -> bool:
    if files is None or item is None:
        return False
    return callable(getattr(files, f"resume_{item.op}", None))


def create_transfer_conflict_dialog(parent, files, item, *, metadata=None):
    """Create a purpose-built native wx conflict dialog."""
    try:
        import wx
    except ImportError:
        return None
    resume_supported = _supports_resume(files, item) if files is not None else False
    title = t("transfer.conflict_title")
    message = t("transfer.conflict_message").format(path=item.dst)
    dlg = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    panel = wx.Panel(dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    msg = wx.StaticText(panel, label=message)
    msg.Wrap(460)
    sizer.Add(msg, 0, wx.ALL | wx.EXPAND, 12)
    source, target = metadata or (ConflictFileInfo(item.src), ConflictFileInfo(item.dst))
    info_controls = {}
    for key, info in (("source", source), ("target", target)):
        size, mtime = format_conflict_metadata(info)
        label = wx.StaticText(panel, label=t("transfer." + key + "_file"))
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        path = wx.TextCtrl(panel, value=info.path, style=wx.TE_READONLY)
        sizer.Add(path, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 12)
        details = wx.StaticText(panel, label=t("transfer.conflict_file_info").format(size=size, mtime=mtime))
        sizer.Add(details, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        info_controls[key] = {"path": path, "details": details}
    btn_sizer = wx.WrapSizer(wx.HORIZONTAL)
    overwrite = wx.Button(panel, label=t("dirs.conflict_overwrite"))
    conditional = {
        action: wx.Button(
            panel,
            label=t(f"transfer.conflict_{action}"),
        )
        for action in (
            "overwrite_if_newer",
            "overwrite_if_size_differs",
            "overwrite_if_size_differs_or_newer",
        )
    }
    skip = wx.Button(panel, label=t("dirs.conflict_skip"))
    rename = wx.Button(panel, label=t("dirs.conflict_rename"))
    cancel = wx.Button(panel, label=t("common.cancel"))
    resume_btn = None
    if resume_supported:
        resume_btn = wx.Button(panel, label=t("transfer.conflict_resume"))
    btn_sizer.Add(overwrite, 0, wx.ALL, 4)
    for button in conditional.values():
        btn_sizer.Add(button, 0, wx.ALL, 4)
    if resume_btn:
        btn_sizer.Add(resume_btn, 0, wx.ALL, 4)
    btn_sizer.Add(skip, 0, wx.ALL, 4)
    btn_sizer.Add(rename, 0, wx.ALL, 4)
    btn_sizer.Add(cancel, 0, wx.ALL, 4)
    sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 8)
    panel.SetSizer(sizer)
    dlg_sizer = wx.BoxSizer(wx.VERTICAL)
    dlg_sizer.Add(panel, 1, wx.EXPAND)
    dlg.SetSizerAndFit(dlg_sizer)
    dlg.SetMinSize((500, 400))
    dlg.SetSize((680, 520))
    cancel.SetDefault()
    dlg._wx_conflict_metadata_controls = info_controls

    result = {"value": "cancel", "rename_target": None}

    def on_overwrite(_event):
        result["value"] = "overwrite"
        dlg.EndModal(wx.ID_OK)

    def on_skip(_event):
        result["value"] = "skip"
        dlg.EndModal(wx.ID_OK)

    def on_conditional(action):
        def choose(_event):
            result["value"] = action
            dlg.EndModal(wx.ID_OK)

        return choose

    def on_cancel(_event):
        result["value"] = "cancel"
        dlg.EndModal(wx.ID_CANCEL)

    def on_resume(_event):
        result["value"] = "resume"
        dlg.EndModal(wx.ID_OK)

    def on_rename(_event):
        current_name = destination_path(item.op, item.dst).name
        while True:
            name_dlg = wx.TextEntryDialog(
                dlg, t("dirs.rename_label"), t("dirs.rename_title"), current_name
            )
            try:
                if name_dlg.ShowModal() != wx.ID_OK:
                    result["value"] = "cancel"
                    dlg.EndModal(wx.ID_CANCEL)
                    return
                new_name = name_dlg.GetValue().strip()
                try:
                    candidate = rename_destination(item.op, item.dst, new_name)
                except ValueError:
                    wx.MessageBox(
                        t("dirs.rename_invalid"),
                        t("login.err_title"),
                        wx.OK | wx.ICON_ERROR,
                    )
                    continue
                try:
                    exists = destination_exists(files, item.op, candidate)
                except Exception:
                    # A failed probe must not be interpreted as a free destination.
                    result["value"] = "cancel"
                    dlg.EndModal(wx.ID_CANCEL)
                    return
                if exists:
                    wx.MessageBox(
                        t("dirs.new_item_exists").format(path=candidate),
                        t("login.err_title"),
                        wx.OK | wx.ICON_ERROR,
                    )
                    continue
                result["value"] = ("rename", candidate)
                dlg.EndModal(wx.ID_OK)
                return
            finally:
                name_dlg.Destroy()

    overwrite.Bind(wx.EVT_BUTTON, on_overwrite)
    for action, button in conditional.items():
        button.Bind(wx.EVT_BUTTON, on_conditional(action))
    skip.Bind(wx.EVT_BUTTON, on_skip)
    cancel.Bind(wx.EVT_BUTTON, on_cancel)
    rename.Bind(wx.EVT_BUTTON, on_rename)
    if resume_btn:
        resume_btn.Bind(wx.EVT_BUTTON, on_resume)
    dlg._wx_conflict_controls = {
        "overwrite": overwrite,
        **conditional,
        "skip": skip,
        "rename": rename,
        "cancel": cancel,
        "resume": resume_btn,
    }
    dlg._wx_conflict_result = result
    dlg._wx_conflict_resume_supported = resume_supported
    return dlg


__all__ = ["_supports_resume", "create_transfer_conflict_dialog"]
