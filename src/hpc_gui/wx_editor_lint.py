"""Native editor diagnostics with snapshot-safe navigation."""
from __future__ import annotations

from threading import Thread
from urllib.parse import urlsplit

from hpc_gui.core.i18n import t
from hpc_gui.services.editor_lint import EditorLintPipeline


def _https_url(value):
    try:
        url = urlsplit(value)
        return bool(url.scheme == "https" and url.hostname and not url.username and not url.password)
    except ValueError:
        return False


def create_editor_lint_dialog(parent, issues, diagnostics, *, navigate=None):
    import wx

    dialog = wx.Dialog(parent, title=t("editor.lint_results_title"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    ordered = sorted(diagnostics, key=lambda d: (d.line or 0, d.column or 0))
    labels, positions = EditorLintPipeline._lint_result_entries(issues, ordered)
    listing = wx.ListBox(dialog, choices=labels)
    root.Add(listing, 1, wx.ALL | wx.EXPAND, 8)
    detail = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
    root.Add(detail, 1, wx.ALL | wx.EXPAND, 8)
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    copy = wx.Button(dialog, label=t("common.copy"))
    docs = wx.Button(dialog, label=t("ansyslint.open_documentation"))
    close = wx.Button(dialog, wx.ID_CLOSE, label=t("common.close"))
    for button in (copy, docs, close):
        buttons.Add(button, 0, wx.ALL, 4)
    root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 4)

    def selected():
        index = listing.GetSelection() - len(issues)
        return ordered[index] if 0 <= index < len(ordered) else None

    def refresh(_event=None):
        diag = selected()
        lines = []
        if diag is not None:
            lines = [diag.message, diag.explanation, diag.suggested_fix, diag.documentation_url,
                     " / ".join(filter(None, (diag.plugin_id, diag.plugin_version)))]
        detail.ChangeValue("\n".join(line for line in lines if line))
        docs.Enable(diag is not None and _https_url(diag.documentation_url))

    def copy_text(_event):
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject("\n".join(labels + [detail.GetValue()])))
            finally:
                wx.TheClipboard.Close()

    def open_docs(_event):
        diag = selected()
        if diag and _https_url(diag.documentation_url):
            wx.LaunchDefaultBrowser(diag.documentation_url)

    def activate(_event):
        index = listing.GetSelection()
        if navigate and 0 <= index < len(positions) and positions[index] >= 0:
            dialog.EndModal(wx.ID_OK)
            navigate(positions[index])

    listing.Bind(wx.EVT_LISTBOX, refresh)
    listing.Bind(wx.EVT_LISTBOX_DCLICK, activate)
    copy.Bind(wx.EVT_BUTTON, copy_text)
    docs.Bind(wx.EVT_BUTTON, open_docs)
    close.Bind(wx.EVT_BUTTON, lambda _event: dialog.EndModal(wx.ID_CLOSE))
    if labels:
        listing.SetSelection(0)
    refresh()
    dialog.SetSizer(root)
    dialog.SetMinSize((620, 380))
    dialog.SetSize((800, 540))
    dialog.CentreOnParent()
    dialog._wx_lint_controls = dict(listing=listing, detail=detail, copy=copy, docs=docs, close=close)
    return dialog


def run_editor_lint(ctx, *, plugin_id=None):
    import wx

    state, model, editor, host = ctx["state"], ctx["model"], ctx["editor"], ctx["host"]
    if state["closed"] or state["in_flight"] or state.get("lint_running") or state["binary_refused"]:
        return False
    active = model.controller.active
    path = ctx["remote_path"].GetValue().strip() or (active.suggested_filename if active else "")
    if not path:
        wx.MessageBox(t("editor.lint_need_path"), t("editor.lint_results_title"), wx.OK | wx.ICON_INFORMATION, host)
        return False
    content = editor.GetValue()
    state["lint_running"] = True
    ctx["update_header_enabled"]()

    def current():
        return (not state["closed"] and not state["in_flight"]
                and model.controller.active is active and editor.GetValue() == content
                and (ctx["remote_path"].GetValue().strip() or active.suggested_filename) == path)

    def done(issues, diagnostics, error):
        state["lint_running"] = False
        if state["closed"]:
            return
        ctx["update_header_enabled"]()
        if not current():
            return
        if error is not None:
            ctx["status"].SetLabel(str(error))
            return
        if not issues and not diagnostics:
            wx.MessageBox(t("editor.lint_ok"), t("editor.lint_results_title"), wx.OK | wx.ICON_INFORMATION, host)
            return

        def navigate(line):
            if not current() or line >= editor.GetNumberOfLines():
                return
            start = editor.XYToPosition(0, line)
            if start != wx.NOT_FOUND:
                editor.SetSelection(start, start + editor.GetLineLength(line))
                editor.ShowPosition(start)
                editor.SetFocus()

        dialog = create_editor_lint_dialog(host, issues, diagnostics, navigate=navigate)
        try:
            dialog.ShowModal()
        finally:
            dialog.Destroy()

    def worker():
        try:
            issues, diagnostics = EditorLintPipeline().collect(path, content, plugin_id=plugin_id)
            wx.CallAfter(done, issues, diagnostics, None)
        except Exception as exc:
            wx.CallAfter(done, [], [], exc)

    Thread(target=worker, daemon=True).start()
    return True
