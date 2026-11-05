"""Typed wx editors that delegate every source patch to the parsed dictionary."""
from __future__ import annotations

from hpc_gui.core.i18n import t

from .inspector_fields import FieldSpec, infer_field, initial_values, validate_values


class WxTypedInspector:
    def __init__(
        self,
        wx,
        *,
        key_list,
        editor_panel,
        editor_sizer,
        type_label,
        apply_button,
        status,
        current_document,
        on_replace,
    ):
        self.wx = wx
        self.key_list = key_list
        self.editor_panel = editor_panel
        self.editor_sizer = editor_sizer
        self.type_label = type_label
        self.apply_button = apply_button
        self.status = status
        self.current_document = current_document
        self.on_replace = on_replace
        self.entries = []
        self.selected_entry = None
        self.selected_spec = FieldSpec("raw")
        self.controls = []
        self.key_list.Bind(wx.EVT_LISTBOX, self._selected)
        self.apply_button.Bind(wx.EVT_BUTTON, self._apply)
        self._clear_editor()

    def refresh(self, document=None, *, selected_key=None):
        document = document or self.current_document()
        previous = selected_key
        if previous is None and self.selected_entry is not None:
            previous = self.selected_entry.qualified_key
        self.entries = [] if document is None else [
            entry for entry in document.parsed.entries
            if not entry.is_dictionary and not entry.dynamic and entry.value_tokens
        ]
        self.key_list.Set([entry.qualified_key for entry in self.entries])
        index = next((i for i, entry in enumerate(self.entries) if entry.qualified_key == previous), 0 if self.entries else -1)
        self.selected_entry = None
        if index >= 0:
            self.key_list.SetSelection(index)
            self._show_entry(self.entries[index])
        else:
            self._clear_editor()

    def _selected(self, event):
        index = self.key_list.GetSelection()
        if 0 <= index < len(self.entries):
            self._show_entry(self.entries[index])
        event.Skip()

    def _clear_editor(self):
        self.editor_sizer.Clear(delete_windows=True)
        self.controls = []
        self.selected_entry = None
        self.selected_spec = FieldSpec("raw")
        self.type_label.SetLabel(t("openfoam.parameter_type_unknown"))
        self.apply_button.Disable()
        self.editor_panel.Layout()

    def _show_entry(self, entry):
        self.editor_sizer.Clear(delete_windows=True)
        self.controls = []
        self.selected_entry = entry
        document = self.current_document()
        spec = infer_field(
            entry,
            dictionary_path=getattr(document, "relative_path", ""),
        )
        self.selected_spec = spec
        type_text = spec.kind
        if spec.component_count:
            type_text = f"{type_text} ({spec.component_count})"
        self.type_label.SetLabel(t("openfoam.parameter_type").format(kind=type_text))
        initial = initial_values(entry, spec)

        if spec.kind in {"boolean", "choice"}:
            choices = list(spec.choices) if spec.kind == "choice" else ["false", "true"]
            control = self.wx.Choice(self.editor_panel, choices=choices)
            control.SetStringSelection(initial[0])
            self.editor_sizer.Add(control, 0, self.wx.EXPAND | self.wx.ALL, 2)
            self.controls.append(control)
        elif spec.kind == "integer":
            control = self.wx.SpinCtrl(
                self.editor_panel, min=-(2**31), max=2**31 - 1, initial=int(initial[0])
            )
            self.editor_sizer.Add(control, 0, self.wx.EXPAND | self.wx.ALL, 2)
            self.controls.append(control)
        elif spec.kind in {"vector", "symmTensor", "tensor"}:
            grid = self.wx.FlexGridSizer(0, 4, 2, 4)
            grid.AddGrowableCol(1, 1)
            grid.AddGrowableCol(3, 1)
            for index, value in enumerate(initial):
                label = self.wx.StaticText(self.editor_panel, label=str(index + 1))
                control = self.wx.TextCtrl(self.editor_panel, value=value)
                grid.Add(label, 0, self.wx.ALIGN_CENTER_VERTICAL | self.wx.LEFT, 2)
                grid.Add(control, 1, self.wx.EXPAND | self.wx.ALL, 2)
                self.controls.append(control)
            self.editor_sizer.Add(grid, 0, self.wx.EXPAND | self.wx.ALL, 2)
        elif spec.kind in {"scalar", "word"}:
            control = self.wx.TextCtrl(self.editor_panel, value=initial[0])
            self.editor_sizer.Add(control, 0, self.wx.EXPAND | self.wx.ALL, 2)
            self.controls.append(control)
        else:
            message = self.wx.StaticText(self.editor_panel, label=t("openfoam.raw_value_locked"))
            self.editor_sizer.Add(message, 0, self.wx.EXPAND | self.wx.ALL, 2)

        can_edit = spec.kind != "raw" and not bool(getattr(self.current_document(), "read_only", False))
        self.apply_button.Enable(can_edit)
        if not can_edit:
            for control in self.controls:
                control.Enable(False)
        self.editor_panel.Layout()

    def _apply(self, _event):
        entry = self.selected_entry
        document = self.current_document()
        if entry is None or document is None:
            self.status.SetLabel(t("openfoam.select_scalar"))
            return
        try:
            values = tuple(self._control_value(control) for control in self.controls)
            normalized = validate_values(self.selected_spec, values)
            if isinstance(normalized, tuple):
                updated = document.parsed.replace_numeric_components(
                    entry.key, normalized, scope=entry.scope
                )
            else:
                updated = document.parsed.replace_scalar(
                    entry.key, normalized, scope=entry.scope
                )
            self.on_replace(document, entry, updated)
            self.refresh(document, selected_key=entry.qualified_key)
            self.status.SetLabel(t("openfoam.parameter_applied"))
        except Exception as exc:
            self.status.SetLabel(t("openfoam.parameter_invalid").format(error=exc))

    def _control_value(self, control) -> str:
        if self.selected_spec.kind in {"boolean", "choice"}:
            return control.GetStringSelection()
        if hasattr(control, "GetValue"):
            return str(control.GetValue())
        return ""
