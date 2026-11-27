"""Framework-neutral formatting for trusted linter findings."""
from __future__ import annotations

from hpc_gui.core.i18n import t


def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if value.startswith("[") else value


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


def diagnostic_totals(run_result):
    totals = {"error": 0, "warning": 0, "info": 0}
    for result in run_result.files:
        for key in totals:
            totals[key] += result.summary.get(key, 0)
    return totals
