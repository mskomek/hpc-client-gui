"""Results dialog for Plugin API v2 linter tools.

Pure formatting lives in :func:`format_run_entries` so it is testable
without Qt; the dialog only renders those lines.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
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
        lines.extend(format_diagnostic_explanation(diag))
    return lines


def format_diagnostic_explanation(diag) -> list[str]:
    """Format only fields supplied by the lint engine; never invent advice."""
    lines = [f"      {_tr('ansyslint.why_flagged', 'why flagged')}: {getattr(diag, 'explanation', '') or diag.message}"]
    confidence = "heuristic" if getattr(diag, "is_heuristic", False) else "structural"
    lines.append(f"      {_tr('ansyslint.confidence', 'confidence')}: {confidence}")
    if diag.suggested_fix:
        lines.append(f"      fix: {diag.suggested_fix}")
        lines.append(f"      {_tr('ansyslint.suggested_action', 'suggested action')}: {diag.suggested_fix}")
    if diag.source_url:
        lines.append(f"      src: {diag.source_url}")
        lines.append(f"      {_tr('ansyslint.documentation', 'documentation')}: {diag.source_url}")
    return lines


def format_run_entries(run_result) -> list[tuple[str, list[str]]]:
    """Grouped (file_header, lines) entries for a full run result."""
    groups: list[tuple[str, list[str]]] = []
    for file_result in sorted(run_result.files, key=lambda r: r.file_path):
        groups.append((file_result.file_path, format_file_entries(file_result)))
    return groups


def build_ansys_lint_results_dialog(parent, title: str, run_result, open_in_tool=None):
    """Build the modal results window grouped by file with severity colors.

    ``open_in_tool`` is an optional zero-argument callback that redirects
    the user into the full linter tool ("Fix"); the button only appears
    when it is supplied.
    """
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
    for file_result in sorted(run_result.files, key=lambda result: result.file_path):
        header = QListWidgetItem(format_file_entries(file_result)[0])
        font = header.font()
        font.setBold(True)
        header.setFont(font)
        list_widget.addItem(header)
        for diag in file_result.sorted_diagnostics():
            marker = "!" if diag.severity.value == "error" else ("~" if diag.severity.value == "warning" else "-")
            location = "?" if diag.line is None else f"{diag.line}:{diag.column or 1}"
            item = QListWidgetItem(f"  [{marker} {location}] {diag.code}: {diag.message}")
            item.setForeground(QColor(_SEVERITY_COLORS[diag.severity.value]))
            item.setData(Qt.ItemDataRole.UserRole, diag)
            list_widget.addItem(item)
            for line in format_diagnostic_explanation(diag):
                list_widget.addItem(QListWidgetItem(line))
    layout.addWidget(list_widget, 1)

    buttons = QHBoxLayout()
    buttons.addStretch(1)

    def copy_all() -> None:
        parts: list[str] = []
        for _header, lines in format_run_entries(run_result):
            parts.extend(lines)
        QApplication.clipboard().setText("\n".join(parts))

    def selected_diagnostic():
        item = list_widget.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def copy_selected() -> None:
        diag = selected_diagnostic()
        if diag is not None:
            QApplication.clipboard().setText("\n".join(format_diagnostic_explanation(diag)))

    def copy_suggestion() -> None:
        diag = selected_diagnostic()
        if diag is not None and diag.suggested_fix:
            QApplication.clipboard().setText(diag.suggested_fix)

    def open_documentation() -> None:
        diag = selected_diagnostic()
        url = str(getattr(diag, "source_url", "") or "") if diag is not None else ""
        if url.startswith("https://"):
            QDesktopServices.openUrl(QUrl(url))

    if open_in_tool is not None:
        btn_fix = QPushButton(_tr("ansyslint.fix_open_tool", "Fix (open in tool)"))

        def open_tool() -> None:
            dialog.accept()
            open_in_tool()

        btn_fix.clicked.connect(open_tool)
        buttons.addWidget(btn_fix)

    btn_copy = QPushButton(_tr("common.copy", "Copy"))
    btn_copy.clicked.connect(copy_all)
    buttons.addWidget(btn_copy)
    for key, callback in (
        ("ansyslint.copy_diagnostic", copy_selected),
        ("ansyslint.copy_suggestion", copy_suggestion),
        ("ansyslint.open_documentation", open_documentation),
    ):
        button = QPushButton(_tr(key, key.rsplit(".", 1)[-1]))
        button.clicked.connect(callback)
        buttons.addWidget(button)
    btn_close = QPushButton(_tr("common.close", "Close"))
    btn_close.clicked.connect(dialog.accept)
    buttons.addWidget(btn_close)
    layout.addLayout(buttons)

    return dialog


def show_ansys_lint_results(parent, title: str, run_result, open_in_tool=None) -> None:
    """Build and exec the modal results window."""
    build_ansys_lint_results_dialog(
        parent, title, run_result, open_in_tool=open_in_tool
    ).exec()
