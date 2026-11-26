"""Native file-linter result viewer; no plugin GUI is imported."""
from __future__ import annotations

from hpc_gui.services.lint_result_format import (
    _tr, diagnostic_totals, format_diagnostic_explanation, format_file_entries,
    format_run_entries,
)
from hpc_gui.wx_editor_lint import _https_url


def create_lint_results(parent, title, run_result, *, open_in_tool=None):
    import wx

    dialog = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    totals = diagnostic_totals(run_result)
    summary = _tr("ansyslint.summary_label", "{e} error(s), {w} warning(s), {i} info").format(
        e=totals["error"], w=totals["warning"], i=totals["info"])
    root.Add(wx.StaticText(dialog, label=summary), 0, wx.ALL, 8)
    labels = []
    owners = []
    for result in sorted(run_result.files, key=lambda item: item.file_path):
        labels.append(format_file_entries(result)[0])
        owners.append(None)
        if not result.diagnostics:
            labels.append("   " + _tr("ansyslint.no_findings", "no findings"))
            owners.append(None)
        for diag in result.sorted_diagnostics():
            location = "?" if diag.line is None else f"{diag.line}:{diag.column or 1}"
            labels.append(f"  [{diag.severity.value} {location}] {diag.code}: {diag.message}")
            owners.append(diag)
            for line in format_diagnostic_explanation(diag):
                labels.append(line)
                owners.append(diag)
    listing = wx.ListBox(dialog, choices=labels, style=wx.LB_HSCROLL)
    root.Add(listing, 1, wx.EXPAND | wx.ALL, 8)
    detail = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
    root.Add(detail, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
    row = wx.WrapSizer(wx.HORIZONTAL)
    controls = {}

    def selected():
        index = listing.GetSelection()
        return owners[index] if 0 <= index < len(owners) else None

    def clipboard(value):
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(value))
            finally:
                wx.TheClipboard.Close()

    def copy_all(_event):
        clipboard("\n".join(line for _, lines in format_run_entries(run_result) for line in lines))

    def copy_diagnostic(_event):
        diag = selected()
        if diag is not None:
            clipboard("\n".join(format_diagnostic_explanation(diag)))

    def copy_suggestion(_event):
        diag = selected()
        if diag is not None and diag.suggested_fix:
            clipboard(diag.suggested_fix)

    def open_docs(_event):
        diag = selected()
        if diag is not None and _https_url(diag.source_url or ""):
            wx.LaunchDefaultBrowser(diag.source_url)

    def add(name, label, handler):
        btn = wx.Button(dialog, label=label)
        btn.Bind(wx.EVT_BUTTON, handler)
        row.Add(btn, 0, wx.ALL, 3)
        controls[name] = btn

    if open_in_tool is not None:
        add("fix", _tr("ansyslint.fix_open_tool", "Fix (open in tool)"),
            lambda _event: dialog.EndModal(wx.ID_APPLY))
    add("copy", _tr("common.copy", "Copy"), copy_all)
    add("diagnostic", _tr("ansyslint.copy_diagnostic", "Copy diagnostic"), copy_diagnostic)
    add("suggestion", _tr("ansyslint.copy_suggestion", "Copy suggestion"), copy_suggestion)
    add("documentation", _tr("ansyslint.open_documentation", "Open documentation"), open_docs)
    add("close", _tr("common.close", "Close"), lambda _event: dialog.EndModal(wx.ID_CLOSE))

    def refresh(_event=None):
        diag = selected()
        detail.ChangeValue("\n".join(format_diagnostic_explanation(diag)) if diag else "")
        controls["diagnostic"].Enable(diag is not None)
        controls["suggestion"].Enable(bool(diag and diag.suggested_fix))
        controls["documentation"].Enable(bool(diag and _https_url(diag.source_url or "")))

    listing.Bind(wx.EVT_LISTBOX, refresh)
    root.Add(row, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizer(root)
    dialog.SetMinSize((680, 400))
    dialog.SetSize((900, 560))
    dialog.CentreOnParent()
    dialog._wx_lint_result_controls = dict(controls, listing=listing, detail=detail, owners=owners)
    refresh()
    return dialog


def show_lint_results(parent, title, run_result, *, open_in_tool=None):
    import wx

    dialog = create_lint_results(parent, title, run_result, open_in_tool=open_in_tool)
    try:
        answer = dialog.ShowModal()
    finally:
        dialog.Destroy()
    if answer == wx.ID_APPLY and open_in_tool is not None:
        open_in_tool()
