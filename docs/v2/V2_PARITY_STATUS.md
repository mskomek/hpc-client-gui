# V2 Parity Status

Automated evidence only; manual-only behavior is never marked covered.

| ID | Status | Qt evidence | wx evidence | Tests |
|---|---|---|---|---|
| GUI-SHELL-001 | COVERED | app.py | wx_shell.py | test_cli_entrypoint.py |
| GUI-SHELL-002 | COVERED | main_window.py | wx_lifecycle.py | test_app_updater.py |
| GUI-SHELL-003 | COVERED | main_window.py | wx_shell.py; wx_jobs.py; wx_lifecycle.py; wx_transfer_workspace.py | test_wx_shell_p0.py; test_wx_shell_p0_stress.py |
| GUI-I18N-001 | COVERED | main_window.py | wx_shell.py; wx_jobs.py; wx_local_files.py; wx_remote_files_view.py; wx_transfer_workspace.py | test_wx_shell_i18n.py; test_wx_shell_p0.py; test_wx_shell_p0_stress.py; test_wx_file_context_i18n.py |
| GUI-CONN-001 | COVERED | login_widget.py | wx_connection.py | test_wx_connection.py |
| GUI-CONN-002 | COVERED | connection_dialog.py | wx_connection.py | test_optional_ssh_credentials.py |
| GUI-CONN-003 | COVERED | connection_dialog.py | wx_connection.py | test_provider_capabilities.py |
| GUI-CONN-004 | COVERED | quota_monitor.py | wx_connection.py | test_quota_monitor.py |
| GUI-CONN-005 | COVERED | login_widget.py | wx_connection.py | test_linux_x11.py; test_macos_x11.py |
| GUI-TERM-001 | COVERED | terminal_widget.py | wx_terminal.py | test_wx_terminal.py |
| GUI-TERM-002 | PARTIAL | main_window.py | wx_terminal.py | test_editor_flow.py |
| GUI-FILE-001 | COVERED | local_dir_panel.py | wx_local_files.py | test_wx_local_files.py |
| GUI-FILE-002 | COVERED | main_window.py | wx_shell.py; wx_editor_windows.py; wx_editor_view.py; wx_remote_files_view.py | test_wx_editor.py; test_wx_editor_window_parity.py; test_wx_remote_editor_flow.py; test_wx_editor_cross_view_actions.py |
| GUI-FILE-003 | COVERED | local_dir_panel.py; remote_dir_panel.py | wx_local_files.py; wx_remote_files_view.py; wx_transfer_workspace.py; wx_shell.py | test_wx_file_context_matrix.py; test_wx_file_keyboard_parity.py; test_wx_file_browser_tabs.py; test_wx_file_actions_lifecycle.py; test_wx_remote_move_undo.py; test_wx_file_transfer_integration.py; test_wx_transfer_conflict_ui.py; test_wx_transfer_ui_lifecycle.py; test_transfer_resume_semantics.py; test_wx_file_context_i18n.py; test_wx_file003_final_stress.py |
| GUI-XFER-001 | COVERED | transfer_dialog.py | wx_transfer_workspace.py | test_transfer_concurrency.py |
| GUI-XFER-002 | COVERED | ftp_widget.py | wx_transfer_workspace.py | test_local_transfer_gate.py |
| GUI-JOBS-001 | COVERED | jobs_widget.py | wx_jobs.py | test_wx_jobs.py |
| GUI-JOBS-002 | COVERED | jobs_outputs_widget.py | wx_jobs.py | test_jobs_outputs_scroll.py; test_wx_jobs.py; test_wx_jobs_behavior.py |
| GUI-JOBS-003 | COVERED | services/ | wx_jobs.py | test_job_history_dashboard.py |
| GUI-JOBS-004 | COVERED | walltime_suggestions.py | wx_jobs.py | test_walltime_suggestions.py |
| GUI-EDIT-001 | COVERED | editor_widget.py | wx_editor.py | test_wx_editor.py |
| GUI-EDIT-002 | PARTIAL | main_window.py | wx_editor.py | test_editor_flow.py |
| GUI-PLUGIN-001 | COVERED | plugin_manager_dialog.py | wx_plugins.py | test_wx_plugins.py |
| GUI-PLUGIN-002 | COVERED | ansys_lint_results_dialog.py | wx_ansys.py | test_wx_ansys.py |
| GUI-SET-001 | COVERED | settings_dialog.py | wx_settings.py | test_wx_settings.py |
| GUI-LOG-001 | COVERED | logs_widget.py | wx_logs.py | test_wx_logs.py |
| GUI-HELP-001 | COVERED | help_dialog.py | wx_help.py | test_wx_help.py |
