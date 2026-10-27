"""Typed Qt editors that delegate every source patch to the parsed dictionary.

Mirrors ``wx_inspector.WxTypedInspector`` on Qt widgets while reusing the
host-owned ``inspector_fields`` helpers for all typing decisions.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QWidget

from hpc_gui.core.i18n import t, tr

from .inspector_fields import FieldSpec, infer_field, initial_values, validate_values


class QtTypedInspector:
    def __init__(
        self,
        *,
        key_list,
        editor_panel: QWidget,
        editor_layout,
        type_label: QLabel,
        apply_button,
        status: QLabel,
        current_document,
        on_replace,
    ):
        self.key_list = key_list
        self.editor_panel = editor_panel
        self.editor_layout = editor_layout
        self.type_label = type_label
        self.apply_button = apply_button
        self.status = status
        self.current_document = current_document
        self.on_replace = on_replace
        self.entries = []
        self.selected_entry = None
        self.selected_spec = FieldSpec("raw")
        self.controls: list = []
        self.key_list.itemClicked.connect(self._selected)
        self.apply_button.clicked.connect(self._apply)
        self._clear_editor()

    def refresh(self, document=None, *, selected_key=None):
        document = document or self.current_document()
        previous = selected_key
        if previous is None and self.selected_entry is not None:
            previous = self.selected_entry.qualified_key
        self.entries = (
            []
            if document is None
            else [
                entry
                for entry in document.parsed.entries
                if not entry.is_dictionary and not entry.dynamic and entry.value_tokens
            ]
        )
        self.key_list.clear()
        self.key_list.addItems([entry.qualified_key for entry in self.entries])
        index = next(
            (i for i, entry in enumerate(self.entries) if entry.qualified_key == previous),
            0 if self.entries else -1,
        )
        self.selected_entry = None
        if index >= 0:
            self.key_list.setCurrentRow(index)
            self._show_entry(self.entries[index])
        else:
            self._clear_editor()

    def _selected(self, _item=None):
        index = self.key_list.currentRow()
        if 0 <= index < len(self.entries):
            self._show_entry(self.entries[index])

    def _clear_editor(self):
        while self.editor_layout.count():
            child = self.editor_layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()
        self.controls = []
        self.selected_entry = None
        self.selected_spec = FieldSpec("raw")
        self.type_label.setText(t("openfoam.parameter_type_unknown"))
        self.apply_button.setEnabled(False)

    def _show_entry(self, entry):
        while self.editor_layout.count():
            child = self.editor_layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()
        self.controls = []
        self.selected_entry = entry
        document = self.current_document()
        spec = infer_field(entry, dictionary_path=getattr(document, "relative_path", ""))
        self.selected_spec = spec
        type_text = spec.kind
        if spec.component_count:
            type_text = f"{type_text} ({spec.component_count})"
        self.type_label.setText(t("openfoam.parameter_type").format(type=type_text))
        initial = initial_values(entry, spec)
        if spec.kind in {"boolean", "choice"}:
            choices = list(spec.choices) if spec.kind == "choice" else ["false", "true"]
            control = QComboBox()
            control.addItems(choices)
            if initial:
                control.setCurrentText(initial[0])
            self.editor_layout.addWidget(control)
            self.controls.append(control)
        elif spec.kind in {"scalar", "integer", "word"}:
            control = QLineEdit(initial[0] if initial else "")
            self.editor_layout.addWidget(control)
            self.controls.append(control)
        elif spec.kind in {"vector", "symmTensor", "tensor"}:
            for value in initial:
                control = QLineEdit(value)
                self.editor_layout.addWidget(control)
                self.controls.append(control)
        else:
            self.editor_layout.addWidget(QLabel(tr("openfoam.raw_locked", "Raw value (read-only)")))
        can_edit = spec.kind != "raw" and not bool(getattr(self.current_document(), "read_only", False))
        self.apply_button.setEnabled(can_edit)
        if not can_edit:
            for control in self.controls:
                control.setEnabled(False)

    def _apply(self, _checked=False):
        entry = self.selected_entry
        document = self.current_document()
        if entry is None or document is None:
            self.status.setText(t("openfoam.select_scalar"))
            return
        try:
            values = tuple(self._control_value(control) for control in self.controls)
            normalized = validate_values(self.selected_spec, values)
            if isinstance(normalized, tuple):
                updated = document.parsed.replace_numeric_components(
                    entry.key, normalized, scope=entry.scope
                )
            else:
                updated = document.parsed.replace_scalar(entry.key, normalized, scope=entry.scope)
            self.on_replace(document, entry, updated)
            self.refresh(document, selected_key=entry.qualified_key)
            self.status.setText(t("openfoam.parameter_applied"))
        except Exception as exc:
            self.status.setText(t("openfoam.parameter_invalid").format(error=exc))

    def _control_value(self, control) -> str:
        if isinstance(control, QComboBox):
            return str(control.currentText())
        if hasattr(control, "text"):
            return str(control.text())
        return ""
