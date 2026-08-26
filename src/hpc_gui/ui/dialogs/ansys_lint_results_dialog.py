"""Results dialog for Plugin API v2 linter tools.

Pure formatting lives in :func:`format_run_entries` so it is testable
without Qt; the dialog only renders those lines.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from hpc_gui.core.i18n import t


def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if value.startswith("[") else value


_SEVERITY_COLORS = {
    "error": "#c0392b",
    "warning": "#e67e22",
    "info": "#2980b9",
}


def format_file_entries(file_result) -> list[str]:
    """Human-readable lines for one FileResult (no Qt)."""
    lines: list[str] = []
    detection = file_result.detection
    meta = []
    if detection.product != "unknown":
        meta.append(detection.product)
    if detection.detected_version:
        meta.append(f"v{detection.detected_version}")
    summary = file_result.summary
    meta.append(
        f"{summary.get('error', 0)}E / {summary.get('warning', 0)}W / {summary.get('info', 0)}I"
    )
    header = file_result.file_path or "<memory>"
    if meta:
        header += f"  [{', '.join(meta)}]"
    lines.append(header)
    if not file_result.diagnostics:
        lines.append("   " + _tr("ansyslint.no_findings", "no findings"))
    for diag in file_result.sorted_diagnostics():
        location = "?" if diag.line is None else f"{diag.line}:{diag.column or 1}"
        marker = "!" if diag.severity.value == "error" else ("~" if diag.severity.value == "warning" else "-")
        lines.append(f"  [{marker} {location}] {diag.code}: {diag.message}")
        if diag.suggested_fix:
            lines.append(f"      fix: {diag.suggested_fix}")
        if diag.source_url:
            lines.append(f"      src: {diag.source_url}")
    return lines


def format_run_entries(run_result) -> list[tuple[str, list[str]]]:
    """Grouped (file_header, lines) entries for a full run result."""
    groups: list[tuple[str, list[str]]] = []
    for file_result in sorted(run_result.files, key=lambda r: r.file_path):
        groups.append((file_result.file_path, format_file_entries(file_result)))
    return groups


def show_ansys_lint_results(parent, title: str, run_result) -> None:
    """Modal results window grouped by file with severity colors."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(900, 560)
    layout = QVBoxLayout(dialog)

    totals = {"error": 0, "warning": 0, "info": 0}
    for file_result in run_result.files:
        for key in totals:
            totals[key] += file_result.summary.get(key, 0)
    summary_label = QLabel(
        _tr("ansyslint.summary_label", "{e} error(s), {w} warning(s), {i} info")
        .replace("{e}", str(totals["error"]))
        .replace("{w}", str(totals["warning"]))
        .replace("{i}", str(totals["info"]))
    )
    layout.addWidget(summary_label)

    list_widget = QListWidget(dialog)
    list_widget.setWordWrap(True)
    for _header, lines in format_run_entries(run_result):
        for line_index, line in enumerate(lines):
            item = QListWidgetItem(line)
            stripped = line.strip()
            if line_index > 0 and stripped.startswith(("!", "~", "-")):
                severity = {"!": "error", "~": "warning", "-": "info"}[stripped[0]]
                item.setForeground(QColor(_SEVERITY_COLORS[severity]))
            elif line_index == 0:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            item.setData(Qt.ItemDataRole.UserRole, line_index == 0)
            list_widget.addItem(item)
    layout.addWidget(list_widget, 1)

    buttons = QHBoxLayout()
    buttons.addStretch(1)

    def copy_all() -> None:
        from PySide6.QtWidgets import QApplication

        parts: list[str] = []
        for _header, lines in format_run_entries(run_result):
            parts.extend(lines)
        QApplication.clipboard().setText("\n".join(parts))

    btn_copy = QPushButton(_tr("common.copy", "Copy"))
    btn_copy.clicked.connect(copy_all)
    buttons.addWidget(btn_copy)
    btn_close = QPushButton(_tr("common.close", "Close"))
    btn_close.clicked.connect(dialog.accept)
    buttons.addWidget(btn_close)
    layout.addLayout(buttons)

    dialog.exec()
