from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QRadioButton,
    QSpinBox,
)

from hpc_gui.core.i18n import t
from hpc_gui.services.slurm_arrays import SlurmArraySpec, apply_array_mode, get_array, parse_array


def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if value.startswith("[") else value


def edit_slurm_array(parent, script_text: str) -> str | None:
    dialog = QDialog(parent)
    dialog.setWindowTitle(_tr("editor.array_title", "Slurm job array"))
    form = QFormLayout(dialog)
    single = QRadioButton(_tr("editor.array_single", "Single job"))
    array = QRadioButton(_tr("editor.array_mode", "Array job"))
    form.addRow(single)
    form.addRow(array)
    start = QSpinBox()
    start.setRange(0, 1_000_000)
    end = QSpinBox()
    end.setRange(0, 1_000_000)
    end.setValue(1)
    step = QSpinBox()
    step.setRange(1, 1_000_000)
    step.setValue(1)
    maximum = QSpinBox()
    maximum.setRange(0, 1_000_000)
    maximum.setSpecialValueText(_tr("editor.array_unlimited", "unlimited"))
    directive = QLineEdit()
    directive.setPlaceholderText(_tr("editor.array_placeholder", "Array directive"))
    for label, widget in (
        (_tr("editor.array_start", "Start"), start),
        (_tr("editor.array_end", "End"), end),
        (_tr("editor.array_step", "Step"), step),
        (_tr("editor.array_max", "Max concurrent"), maximum),
        (_tr("editor.array_directive", "Final directive"), directive),
    ):
        form.addRow(label, widget)

    try:
        existing = get_array(script_text)
    except ValueError:
        existing = None
    if existing is not None:
        array.setChecked(True)
        start.setValue(existing.start)
        end.setValue(existing.end)
        step.setValue(existing.step)
        maximum.setValue(existing.max_concurrent or 0)
    else:
        single.setChecked(True)

    def refresh() -> None:
        enabled = array.isChecked()
        for widget in (start, end, step, maximum, directive):
            widget.setEnabled(enabled)
        if enabled:
            try:
                directive.setText(SlurmArraySpec(start.value(), end.value(), step.value(), maximum.value() or None).directive())
            except ValueError:
                directive.clear()

    for widget in (start, end, step, maximum):
        widget.valueChanged.connect(refresh)
    single.toggled.connect(refresh)
    refresh()
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    if not array.isChecked():
        return apply_array_mode(script_text, False)
    value = directive.text().strip().removeprefix("#SBATCH").strip()
    value = value.removeprefix("--array=").strip()
    return apply_array_mode(script_text, True, parse_array(value))
