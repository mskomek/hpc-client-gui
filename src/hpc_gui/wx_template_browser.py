"""Native typed plugin-template browser. Rendering is validation, not execution."""
from __future__ import annotations

from hpc_gui.core.i18n import t
from hpc_gui.plugins.job_templates import render_template


def create_template_browser(parent, templates, *, provider_template=None):
    import wx
    import wx.lib.scrolledpanel

    templates = tuple(templates)
    provider = provider_template or {}
    hints = provider.get("scheduler_hints", {})
    partitions = tuple(str(v) for v in (hints.get("partitions") or []) if str(v).strip()) if isinstance(hints, dict) else ()
    account = str(provider.get("account") or "").strip()
    dialog = wx.Dialog(parent, title=t("templates.dialog_title"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    body = wx.BoxSizer(wx.HORIZONTAL)
    left = wx.BoxSizer(wx.VERTICAL)
    left.Add(wx.StaticText(dialog, label=t("templates.list_label")), 0, wx.BOTTOM, 6)
    listing = wx.ListBox(dialog, choices=[f"{tpl.name} ({tpl.plugin_id})" for tpl in templates])
    left.Add(listing, 1, wx.EXPAND)
    body.Add(left, 1, wx.EXPAND | wx.ALL, 10)
    right = wx.BoxSizer(wx.VERTICAL)
    description = wx.StaticText(dialog, label="")
    right.Add(description, 0, wx.EXPAND | wx.BOTTOM, 10)
    form = wx.lib.scrolledpanel.ScrolledPanel(dialog)
    grid = wx.FlexGridSizer(0, 2, 8, 10)
    grid.AddGrowableCol(1)
    form.SetSizer(grid)
    right.Add(form, 1, wx.EXPAND)
    error = wx.StaticText(dialog, label="")
    right.Add(error, 0, wx.EXPAND | wx.TOP, 8)
    body.Add(right, 2, wx.EXPAND | wx.ALL, 10)
    root.Add(body, 1, wx.EXPAND)
    buttons = wx.StdDialogButtonSizer()
    ok = wx.Button(dialog, wx.ID_OK)
    cancel = wx.Button(dialog, wx.ID_CANCEL)
    buttons.AddButton(ok)
    buttons.AddButton(cancel)
    buttons.Realize()
    root.Add(buttons, 0, wx.ALL | wx.EXPAND, 10)
    fields = {}
    result = {"value": None}

    def selected():
        index = listing.GetSelection()
        return templates[index] if 0 <= index < len(templates) else None

    def rebuild(_event=None):
        grid.Clear(delete_windows=True)
        fields.clear()
        template = selected()
        result["value"] = None
        error.SetLabel("")
        ok.Enable(template is not None)
        if template is None:
            description.SetLabel("")
            return
        description.SetLabel(t("templates.plugin_version_line").format(
            description=template.description, plugin_id=template.plugin_id,
            plugin_version=template.plugin_version,
        ))
        description.Wrap(420)
        for var in template.variables:
            label = var.name + (" *" if var.required else "")
            if var.description:
                label += "\n" + var.description
            if var.type == "boolean":
                field = wx.CheckBox(form)
                field.SetValue(bool(var.default))
                getter = field.GetValue
            elif var.type == "integer":
                # Text preserves arbitrary integer bounds without native C-int truncation.
                field = wx.TextCtrl(form, value=str(var.default) if var.default is not None else "1")
                getter = lambda field=field: field.GetValue().strip() or None
            elif var.name == "partition" and partitions:
                choices = list(dict.fromkeys((*partitions, *var.choices)))
                field = wx.ComboBox(form, choices=choices, value=str(var.default or choices[0]))
                getter = field.GetValue
            elif var.type == "choice" and var.choices:
                field = wx.Choice(form, choices=list(var.choices))
                field.SetSelection(var.choices.index(var.default) if var.default in var.choices else 0)
                getter = field.GetStringSelection
            else:
                initial = var.default if var.default is not None else (account if var.name == "account" else "")
                field = wx.TextCtrl(form, value=str(initial))
                getter = lambda field=field: field.GetValue().strip() or None
            fields[var.name] = (field, getter)
            text = wx.StaticText(form, label=label)
            text.Wrap(180)
            grid.Add(text, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(field, 1, wx.EXPAND)
        form.Layout()
        form.SetupScrolling(scroll_x=False)
        dialog.Layout()

    def accept(_event):
        template = selected()
        if template is None:
            return
        values = {name: getter() for name, (_field, getter) in fields.items()}
        try:
            render_template(template, values)
        except ValueError as exc:
            error.SetLabel(str(exc))
            error.Wrap(420)
            dialog.Layout()
            return
        result["value"] = (template, values)
        dialog.EndModal(wx.ID_OK)

    listing.Bind(wx.EVT_LISTBOX, rebuild)
    ok.Bind(wx.EVT_BUTTON, accept)
    if templates:
        listing.SetSelection(0)
    rebuild()
    dialog.SetSizer(root)
    dialog.SetMinSize((700, 460))
    dialog.SetSize((850, 580))
    dialog.CentreOnParent()
    dialog._wx_template_controls = {"listing": listing, "description": description, "fields": fields, "error": error, "ok": ok}
    dialog._wx_template_result = result
    return dialog


def choose_template(parent, templates, *, provider_template=None):
    import wx

    dialog = create_template_browser(parent, templates, provider_template=provider_template)
    try:
        return dialog._wx_template_result["value"] if dialog.ShowModal() == wx.ID_OK else None
    finally:
        dialog.Destroy()
