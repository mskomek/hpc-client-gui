"""Small template browser for plugin-delivered job templates.

Lists installed templates with their declared variables, collects values
with typed form fields, and returns the selection to the editor. Rendering
and any file writing stay in the caller; submission never happens here.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from hpc_gui.core.i18n import t
from hpc_gui.plugins.job_templates import JobTemplate


class TemplateBrowserDialog(QDialog):
    def __init__(self, parent=None, templates=None, provider_template=None):
        super().__init__(parent)
        self._templates = list(templates or [])
        provider = provider_template if isinstance(provider_template, dict) else {}
        hints = provider.get("scheduler_hints", {})
        self._partitions = tuple(str(value) for value in (hints.get("partitions") or []) if str(value).strip()) if isinstance(hints, dict) else ()
        self._account = str(provider.get("account") or "").strip()
        self.result_template: JobTemplate | None = None
        self.result_values: dict[str, object] = {}

        self.setWindowTitle(
            t("templates.dialog_title")
            if t("templates.dialog_title") != "[templates.dialog_title]"
            else "Job Templates"
        )
        self.resize(760, 480)

        layout = QVBoxLayout(self)
        body = QHBoxLayout()
        layout.addLayout(body, 1)

        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.addWidget(QLabel(t("templates.list_label")))
        self.template_list = QListWidget()
        left.addWidget(self.template_list)
        body.addWidget(left_widget, 1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.description = QLabel("")
        self.description.setWordWrap(True)
        right_layout.addWidget(self.description)

        self.form_host = QWidget()
        self.form = QFormLayout(self.form_host)
        self.form.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.form_host)
        right_layout.addStretch(1)
        body.addWidget(right, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        for template in self._templates:
            item = QListWidgetItem(f"{template.name} ({template.plugin_id})")
            item.setData(Qt.ItemDataRole.UserRole, template)
            self.template_list.addItem(item)
        self.template_list.currentRowChanged.connect(self._on_template_selected)
        if self._templates:
            self.template_list.setCurrentRow(0)

    def _selected_template(self) -> JobTemplate | None:
        item = self.template_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _on_template_selected(self, _row: int) -> None:
        while self.form.count():
            item = self.form.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        template = self._selected_template()
        if template is None:
            self.description.setText("")
            return
        self.description.setText(
            f"{template.description}\n\nplugin: {template.plugin_id} "
            f"v{template.plugin_version}"
        )
        for variable in template.variables:
            label = variable.name
            if variable.description:
                label = f"{variable.name}\n  {variable.description}"
            if variable.type == "integer":
                field = QSpinBox()
                field.setMaximum(10**9)
                if variable.minimum is not None:
                    field.setMinimum(variable.minimum)
                if variable.maximum is not None:
                    field.setMaximum(variable.maximum)
                default = variable.default if isinstance(variable.default, int) else 1
                field.setValue(default)
                self.form.addRow(label, field)
            elif variable.type == "boolean":
                field = QCheckBox()
                field.setChecked(bool(variable.default))
                self.form.addRow(label, field)
            elif variable.name == "partition" and self._partitions:
                field = QComboBox()
                field.setEditable(True)
                field.addItems(list(dict.fromkeys((*self._partitions, *variable.choices))))
                default = variable.default if isinstance(variable.default, str) else None
                if default:
                    field.setCurrentText(default)
                self.form.addRow(label, field)
            elif variable.type == "choice" and variable.choices:
                field = QComboBox()
                field.addItems(list(variable.choices))
                default = variable.default if isinstance(variable.default, str) else None
                if default in variable.choices:
                    field.setCurrentText(default)
                self.form.addRow(label, field)
            else:
                field = QLineEdit()
                if isinstance(variable.default, (str, int)) and not isinstance(
                    variable.default, bool
                ):
                    field.setText(str(variable.default))
                elif variable.name == "account" and self._account:
                    field.setText(self._account)
                self.form.addRow(label, field)
        self._update_preview()

    def _collect_values(self) -> dict[str, object]:
        template = self._selected_template()
        values: dict[str, object] = {}
        if template is None:
            return values
        index = 0
        for variable in template.variables:
            field = self.form.itemAt(index, QFormLayout.ItemRole.FieldRole)
            index += 1
            if field is None or field.widget() is None:
                continue
            widget = field.widget()
            if isinstance(widget, QSpinBox):
                values[variable.name] = widget.value()
            elif isinstance(widget, QCheckBox):
                values[variable.name] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                values[variable.name] = widget.currentText()
            elif isinstance(widget, QLineEdit):
                text_value = widget.text().strip()
                values[variable.name] = text_value if text_value != "" else None
        return values

    def _accept_selection(self) -> None:
        self.result_values = self._collect_values()
        self.result_template = self._selected_template()
        self.accept()
