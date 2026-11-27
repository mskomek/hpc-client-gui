"""Native result presentation for the shared read-only cluster self-test."""
from __future__ import annotations

from hpc_gui.core.i18n import t
from hpc_gui.core.log_redaction import redact_text
from hpc_gui.services.cluster_self_test import format_self_test_result
from hpc_gui.services.provider_capabilities import build_provider_capability_view, observed_from_self_test

RUN_AGAIN_ID = 6101


def create_self_test_result_dialog(parent, result, *, provider=None, project="", account=""):
    import wx

    dialog = wx.Dialog(parent, title=t("cluster_self_test.title"),
                       style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    summary = wx.StaticText(dialog, label=t("cluster_self_test.summary").format(status=result.status))
    root.Add(summary, 0, wx.ALL | wx.EXPAND, 12)
    view = build_provider_capability_view(
        provider, observed_from_self_test(result), project=project, account=account,
    )
    lines = [
        t("cluster_self_test.declared_header").format(provider=view.provider),
        t("cluster_self_test.observed_header"),
    ]
    lines.extend(f"  {cap.id}: {cap.declared} / {cap.observed}" for cap in view.capabilities)
    lines.extend(("", format_self_test_result(result)))
    content = wx.TextCtrl(dialog, value="\n".join(lines),
                          style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    content.SetName(t("cluster_self_test.results"))
    root.Add(content, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    again = wx.Button(dialog, RUN_AGAIN_ID, t("cluster_self_test.run_again"))
    copy = wx.Button(dialog, label=t("cluster_self_test.copy"))
    close = wx.Button(dialog, wx.ID_OK, t("common.close"))
    close.SetDefault()

    def copy_result(_event):
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(redact_text(format_self_test_result(result))))
            finally:
                wx.TheClipboard.Close()

    again.Bind(wx.EVT_BUTTON, lambda event: dialog.EndModal(RUN_AGAIN_ID))
    copy.Bind(wx.EVT_BUTTON, copy_result)
    buttons.AddStretchSpacer()
    for button in (again, copy, close):
        buttons.Add(button, 0, wx.LEFT, 8)
    root.Add(buttons, 0, wx.ALL | wx.EXPAND, 12)
    dialog.SetSizer(root)
    dialog.SetMinSize((500, 400))
    dialog.SetSize((680, 520))
    dialog.CentreOnParent()
    dialog._wx_self_test_controls = {
        "summary": summary, "content": content, "again": again,
        "copy": copy, "close": close,
    }
    return dialog
