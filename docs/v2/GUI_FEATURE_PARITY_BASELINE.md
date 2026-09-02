# Current Qt GUI Feature-Parity Baseline

Adaptive layout and geometry rules: [GUI Adaptive Layout/DPI Contract](GUI_ADAPTIVE_LAYOUT_DPI_CONTRACT.md).

This is the authoritative inventory for a future wx adapter. It describes the
current Qt surface only; it does not define a redesign or authorize wx code.
The inventory was reviewed against `MainWindow`, its six tabs, the top-right
actions, dialogs, and widget context-menu implementations.

| ID | Surface / current behavior | Implementation | Priority | Evidence | V2 status |
| --- | --- | --- | --- | --- | --- |
| GUI-SHELL-001 | App startup, versioned shell, splash/welcome, startup changelog | Qt `QApplication`, `MainWindow`, splash/welcome dialogs | P0 | `app.py`, `main_window.py`, `tests/test_cli_entrypoint.py` | Preserve |
| GUI-SHELL-002 | Update check, progress, cancellation, install handoff | `UpdateSplash`, background `QThread` jobs | P0 | `main_window.py`, `tests/test_app_updater.py` | Preserve |
| GUI-SHELL-003 | System-tray job completion notification and graceful shutdown | `QSystemTrayIcon`, timers, shutdown hooks | P0 | `main_window.py`, release smoke tests | Preserve; tray availability is platform-dependent |
| GUI-CONN-001 | Profile selection, connect/disconnect, saved-profile lifecycle | `LoginWidget`, `ConnectionDialog`, config storage | P0 | `login_widget.py`, `connection_dialog.py`, `tests/test_profile_*` | Preserve |
| GUI-CONN-002 | SSH credentials, optional MFA, jump host, host-key and advanced settings | Connection form and SSH session service | P0 | `connection_dialog.py`, `tests/test_optional_ssh_credentials.py` | Preserve; secrets stay out of logs |
| GUI-CONN-003 | Provider/template selection and declarative capability metadata | plugin template models and connection dialog menus | P0 | `plugins/`, `tests/test_provider_capabilities.py`, `tests/test_plugin_v2.py` | Preserve; no provider names in generic logic |
| GUI-CONN-004 | Quota consent, backend, scope/subject, status and fail-closed gate | quota monitor and connection form | P0 | `quota_monitor.py`, `tests/test_quota_*.py` | Preserve |
| GUI-CONN-005 | Linux/macOS X11 forwarding and Windows-compatible SSH process cleanup | login/session integration | P1 | `tests/test_linux_x11.py`, `tests/test_macos_x11.py` | Preserve; optional capability remains unknown when absent |
| GUI-TERM-001 | Terminal tabs/input, command execution, xterm.js graphics bridge | `TerminalWidget`, `TerminalInput`, terminal assets | P0 | `terminal_widget.py`, `tests/test_terminal*` | Preserve |
| GUI-TERM-002 | Run selected shell/script from file views or editor in terminal | signals from `FtpWidget`, `DirectoriesWidget`, `EditorWidget` | P1 | `main_window.py`, `tests/test_editor_flow.py` | Preserve |
| GUI-FILE-001 | Local/remote directory browsing, refresh, navigation and path state | directory panels and remote accordion | P0 | `local_dir_panel.py`, `remote_dir_panel.py`, `tests/test_remote_directory_listing.py` | Preserve |
| GUI-FILE-002 | Open remote/local files, edit, new-window editor and script submit | directory/editor signal wiring | P0 | `main_window.py`, `tests/test_local_edit_flow.py` | Preserve |
| GUI-FILE-003 | Context actions for open/edit/download/upload/delete/rename | local/remote panel menus | P0 | `local_dir_panel.py`, `remote_dir_panel.py`, `ftp_widget.py` | Preserve; review action parity |
| GUI-XFER-001 | Transfer dialog, conflict handling, progress and cancellation | `TransferDialog`, transfer services | P0 | `transfer_dialog.py`, `tests/test_download_cancel_wire.py` | Preserve |
| GUI-XFER-002 | Batch transfer and local-transfer safety gate | FTP widget and local provider checks | P0 | `ftp_widget.py`, `tests/test_local_transfer_gate.py` | Preserve; fail closed |
| GUI-JOBS-001 | Job list, refresh, submit/cancel controls and state display | `JobsWidget`, `JobsOutputsWidget` | P0 | `jobs_widget.py`, `tests/test_job_context.py` | Preserve |
| GUI-JOBS-002 | Job details, output panes, follow mode and scroll behavior | jobs/output widgets | P0 | `jobs_outputs_widget.py`, `tests/test_jobs_outputs_scroll.py` | Preserve |
| GUI-JOBS-003 | Completed-job history, provenance and reproducibility bundle entry points | history/provenance services plus jobs UI | P1 | `services/`, `tests/test_job_history_dashboard.py` | Preserve; advisory data only |
| GUI-JOBS-004 | Deterministic walltime suggestion from successful local history | `walltime_suggestions.py` service | P1 | `tests/test_walltime_suggestions.py` | New V2 service; never auto-applies |
| GUI-EDIT-001 | Syntax-aware script editor, lint results, dirty-state and save flow | `EditorWidget`, lint services | P0 | `editor_widget.py`, `tests/test_editor_v2_lint.py` | Preserve |
| GUI-EDIT-002 | Submit script, run shell, open local/remote and new editor window | editor signals and main-window adapters | P1 | `main_window.py`, `tests/test_editor_flow.py` | Preserve |
| GUI-PLUGIN-001 | Plugin manager, discovery/install state and template browser | plugin manager/template dialogs | P1 | `plugin_manager_dialog.py`, `template_browser_dialog.py` | Preserve |
| GUI-PLUGIN-002 | ANSYS Trusted Tool lint/explanation surface | allowlisted linter host and result dialog | P1 | `ansys_lint_results_dialog.py`, `tests/test_fluent_plugin_integration.py` | Preserve; explicit allowlist |
| GUI-SET-001 | Settings dialog, language, refresh/live tracking and storage controls | `SettingsDialog`, i18n layer | P0 | `settings_dialog.py`, `tests/test_live_tracking_settings.py` | Preserve |
| GUI-LOG-001 | Application logs, diagnostics, send-logs flow and redaction | `LogsWidget`, diagnostics/send-logs dialogs | P1 | `logs_widget.py`, `send_logs_dialog.py`, `tests/test_log_redaction.py` | Preserve; no secret export |
| GUI-HELP-001 | Help center, quick tour, welcome and contextual help affordances | help/quick-tour/welcome dialogs | P1 | `help_dialog.py`, `quick_tour.py`, `tests/test_docs_references.py` | Preserve |
| GUI-I18N-001 | Turkish/English language menu, flags and runtime label refresh | `i18n` translations and main-window refresh | P0 | `main_window.py`, `tests/test_branding_check.py` | Preserve; new strings require i18n keys |
| GUI-A11Y-001 | Keyboard focus/tab order, visible labels and non-color state cues | Qt widget defaults plus explicit labels/tooltips | P1 | widget tree review | Review during wx port |

## Known inconsistencies to carry explicitly

- The tray icon is optional because the operating system may report no tray;
  the job view remains the source of truth.
- Some legacy tab labels have English fallbacks when a translation key is
  unavailable. The wx port must retain the behavior while adding the missing
  keys, not hardcode new generic labels.
- Context-menu coverage is distributed across local, remote and FTP widgets;
  it must be tested as separate adapters so an action is not silently lost.
- The walltime suggestion is advisory, uses only `COMPLETED` local records,
  and never changes a submitted or edited walltime automatically.

## Review checklist

- [x] Six main tabs, top-right actions, tray, startup/update/shutdown paths
      reviewed against `MainWindow`.
- [x] Connection, terminal, files/transfers, jobs/output, editor, plugins,
      settings, logs/diagnostics, help and localization surfaces inventoried.
- [x] Context-menu owners reviewed in connection, transfer, FTP, local and
      remote directory widgets.
- [x] IDs are stable and unique; no wx implementation or redesign is included.
