"""Native job-array editor; only an accepted, validated result changes text."""
from __future__ import annotations

from hpc_gui.core.i18n import t
from hpc_gui.services.slurm_arrays import SlurmArraySpec, apply_array_mode, get_array, parse_array


def create_array_dialog(parent, script_text):
    import wx

    dialog = wx.Dialog(parent, title=t("editor.array_title"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    single = wx.RadioButton(dialog, label=t("editor.array_single"), style=wx.RB_GROUP)
    array = wx.RadioButton(dialog, label=t("editor.array_mode"))
    root.Add(single, 0, wx.ALL, 8)
    root.Add(array, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    grid = wx.FlexGridSizer(0, 2, 6, 12)
    grid.AddGrowableCol(1)
    fields = {}
    for name, minimum, value in (("start", 0, 0), ("end", 0, 1), ("step", 1, 1), ("max", 0, 0)):
        label = t("editor.array_" + name)
        if name == "max":
            label += " (0 = " + t("editor.array_unlimited") + ")"
        field = wx.SpinCtrl(dialog, min=minimum, max=1000000, initial=value)
        fields[name] = field
        grid.Add(wx.StaticText(dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(field, 1, wx.EXPAND)
    directive = wx.TextCtrl(dialog)
    directive.SetHint(t("editor.array_placeholder"))
    grid.Add(wx.StaticText(dialog, label=t("editor.array_directive")), 0, wx.ALIGN_CENTER_VERTICAL)
    grid.Add(directive, 1, wx.EXPAND)
    root.Add(grid, 1, wx.ALL | wx.EXPAND, 12)
    error = wx.StaticText(dialog, label="")
    root.Add(error, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 12)
    buttons = wx.StdDialogButtonSizer()
    ok = wx.Button(dialog, wx.ID_OK)
    cancel = wx.Button(dialog, wx.ID_CANCEL)
    buttons.AddButton(ok)
    buttons.AddButton(cancel)
    buttons.Realize()
    root.Add(buttons, 0, wx.ALL | wx.EXPAND, 12)
    result = {"text": None}

    try:
        existing = get_array(script_text)
    except ValueError:
        existing = None
    if existing:
        array.SetValue(True)
        for name, value in (("start", existing.start), ("end", existing.end),
                            ("step", existing.step), ("max", existing.max_concurrent or 0)):
            fields[name].SetValue(value)
    else:
        single.SetValue(True)

    def validate():
        try:
            value = directive.GetValue().strip().removeprefix("#SBATCH").strip().removeprefix("--array=").strip()
            result["text"] = apply_array_mode(script_text, array.GetValue(), parse_array(value) if array.GetValue() else None)
            error.SetLabel("")
            ok.Enable(True)
        except ValueError as exc:
            result["text"] = None
            error.SetLabel(str(exc))
            ok.Disable()

    refreshing = False

    def refresh(_event=None):
        nonlocal refreshing
        if refreshing:
            return
        refreshing = True
        try:
            refresh_fields()
        finally:
            refreshing = False

    def refresh_fields():
        enabled = array.GetValue()
        for field in (*fields.values(), directive):
            if field.IsEnabled() != enabled:
                field.Enable(enabled)
        if enabled:
            try:
                spec = SlurmArraySpec(fields["start"].GetValue(), fields["end"].GetValue(),
                                      fields["step"].GetValue(), fields["max"].GetValue() or None)
                directive.ChangeValue(spec.directive())
            except ValueError:
                directive.ChangeValue("")
        validate()

    for field in fields.values():
        field.Bind(wx.EVT_SPINCTRL, refresh)
        field.Bind(wx.EVT_TEXT, refresh)
    single.Bind(wx.EVT_RADIOBUTTON, refresh)
    array.Bind(wx.EVT_RADIOBUTTON, refresh)
    directive.Bind(wx.EVT_TEXT, lambda event: validate())

    def accept(_event):
        validate()
        if result["text"] is not None:
            dialog.EndModal(wx.ID_OK)

    ok.Bind(wx.EVT_BUTTON, accept)
    refresh()
    dialog.SetSizerAndFit(root)
    dialog.SetMinSize((560, 350))
    dialog.SetSize((600, 380))
    dialog.CentreOnParent()
    dialog._wx_array_controls = dict(fields, single=single, array=array, directive=directive, ok=ok, error=error)
    dialog._wx_array_result = result
    return dialog


def edit_array_native(parent, script_text):
    import wx

    dialog = create_array_dialog(parent, script_text)
    try:
        if dialog.ShowModal() == wx.ID_OK:
            return dialog._wx_array_result["text"]
        return None
    finally:
        dialog.Destroy()
