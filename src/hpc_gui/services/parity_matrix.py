"""Small, explicit feature-parity mapping and report generator."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    status: str
    qt: str
    wx: str
    tests: str
    justification: str = ""


FEATURE_EVIDENCE = {
    "GUI-SHELL-001": Evidence("COVERED", "app.py", "wx_shell.py", "test_cli_entrypoint.py"),
    "GUI-SHELL-002": Evidence("COVERED", "main_window.py", "wx_lifecycle.py", "test_app_updater.py"),
    "GUI-SHELL-003": Evidence("PARTIAL", "main_window.py", "wx_shell.py", "test_wx_shell.py"),
    "GUI-CONN-001": Evidence("COVERED", "login_widget.py", "wx_connection.py", "test_wx_connection.py"),
    "GUI-CONN-002": Evidence("COVERED", "connection_dialog.py", "wx_connection.py", "test_optional_ssh_credentials.py"),
    "GUI-CONN-003": Evidence("COVERED", "connection_dialog.py", "wx_connection.py", "test_provider_capabilities.py"),
    "GUI-CONN-004": Evidence("COVERED", "quota_monitor.py", "wx_connection.py", "test_quota_monitor.py"),
    "GUI-CONN-005": Evidence("COVERED", "login_widget.py", "wx_connection.py", "test_linux_x11.py; test_macos_x11.py"),
    "GUI-TERM-001": Evidence("COVERED", "terminal_widget.py", "wx_terminal.py", "test_wx_terminal.py"),
    "GUI-TERM-002": Evidence("PARTIAL", "main_window.py", "wx_terminal.py", "test_editor_flow.py"),
    "GUI-FILE-001": Evidence("COVERED", "local_dir_panel.py", "wx_local_files.py", "test_wx_local_files.py"),
    "GUI-FILE-002": Evidence("COVERED", "main_window.py", "wx_shell.py; wx_editor_windows.py; wx_editor_view.py; wx_remote_files_view.py", "test_wx_editor.py; test_wx_editor_window_parity.py; test_wx_remote_editor_flow.py; test_wx_editor_cross_view_actions.py", "Real wx tests cover shared primary editor reuse, standalone independence, dirty replacement, async remote loading, stale-result rejection, document-aware local/remote Submit/Run, cross-view safety, reconnect backend selection, in-flight session snapshot consistency, and worker-thread backend execution."),
    "GUI-FILE-003": Evidence("COVERED", "local_dir_panel.py; remote_dir_panel.py", "wx_local_files.py; wx_remote_files_view.py; wx_transfer_workspace.py; wx_shell.py", "test_wx_file_context_matrix.py; test_wx_file_keyboard_parity.py; test_wx_file_browser_tabs.py; test_wx_file_actions_lifecycle.py; test_wx_remote_move_undo.py; test_wx_file_transfer_integration.py; test_wx_transfer_conflict_ui.py; test_wx_transfer_ui_lifecycle.py; test_transfer_resume_semantics.py; test_wx_file_context_i18n.py; test_wx_file003_final_stress.py", "Real wx event chains cover context targeting (unselected row, multiselection, background, keyboard), visible local and remote tabs with user-driven closing, off-GUI-thread listings, stale and cross-tab listing rejection, action-time target snapshots, Copy Path as clipboard-only, move history with Ctrl+Z undo, the keyboard matrix, and the TransferItem -> session controller -> backend chain with ask/overwrite/skip/rename/cancel plus direction-specific Resume. FTP and SFTP byte/protocol tests prove Overwrite and Resume differ. The final stress campaign executed 200 right-click retargets, 100 local and 100 remote mutations, 200 target switches, 200 navigate/completion races, 50 browser open/close cycles, 25 blocked close-in-flight cases, 100 FILE transfer items and 50 unicode/space names with every measured invariant at zero and peak non-transfer mutation concurrency of 1 per browser. Measured on Windows only."),
    "GUI-XFER-001": Evidence("COVERED", "transfer_dialog.py", "wx_transfer_workspace.py", "test_transfer_concurrency.py"),
    "GUI-XFER-002": Evidence("COVERED", "ftp_widget.py", "wx_transfer_workspace.py", "test_local_transfer_gate.py"),
    "GUI-JOBS-001": Evidence("COVERED", "jobs_widget.py", "wx_jobs.py", "test_wx_jobs.py"),
    "GUI-JOBS-002": Evidence("COVERED", "jobs_outputs_widget.py", "wx_jobs.py", "test_jobs_outputs_scroll.py; test_wx_jobs.py; test_wx_jobs_behavior.py", "Real wx Jobs frame/event tests cover pause refresh, minimize/restore, non-overlapping reads, and stale-result rejection."),
    "GUI-JOBS-003": Evidence("COVERED", "services/", "wx_jobs.py", "test_job_history_dashboard.py"),
    "GUI-JOBS-004": Evidence("COVERED", "walltime_suggestions.py", "wx_jobs.py", "test_walltime_suggestions.py"),
    "GUI-EDIT-001": Evidence("COVERED", "editor_widget.py", "wx_editor.py", "test_wx_editor.py"),
    "GUI-EDIT-002": Evidence("PARTIAL", "main_window.py", "wx_editor.py", "test_editor_flow.py"),
    "GUI-PLUGIN-001": Evidence("COVERED", "plugin_manager_dialog.py", "wx_plugins.py", "test_wx_plugins.py"),
    "GUI-PLUGIN-002": Evidence("COVERED", "ansys_lint_results_dialog.py", "wx_ansys.py", "test_wx_ansys.py"),
    "GUI-SET-001": Evidence("COVERED", "settings_dialog.py", "wx_settings.py", "test_wx_settings.py"),
    "GUI-LOG-001": Evidence("COVERED", "logs_widget.py", "wx_logs.py", "test_wx_logs.py"),
    "GUI-HELP-001": Evidence("COVERED", "help_dialog.py", "wx_help.py", "test_wx_help.py"),
}


def baseline_ids(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(re.findall(r"GUI-[A-Z]+-\d{3}", text)))


def render_status(baseline: str, mapping: dict[str, Evidence] | None = None) -> str:
    evidence = FEATURE_EVIDENCE if mapping is None else mapping
    ids = baseline_ids(baseline)
    missing = [item for item in ids if item not in evidence]
    if missing:
        raise ValueError("missing parity mapping: " + ", ".join(missing))
    for item in ids:
        row = evidence[item]
        if row.status == "INTENTIONALLY_CHANGED" and not row.justification.strip():
            raise ValueError(f"missing intentional-change justification: {item}")
    lines = ["# V2 Parity Status", "", "Automated evidence only; manual-only behavior is never marked covered.", "", "| ID | Status | Qt evidence | wx evidence | Tests |", "|---|---|---|---|---|"]
    lines.extend(f"| {item} | {evidence[item].status} | {evidence[item].qt} | {evidence[item].wx} | {evidence[item].tests} |" for item in ids)
    return "\n".join(lines) + "\n"


__all__ = ["Evidence", "FEATURE_EVIDENCE", "baseline_ids", "render_status"]
