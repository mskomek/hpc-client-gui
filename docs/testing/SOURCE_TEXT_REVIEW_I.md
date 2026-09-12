# Packet I — source-text test review

The frozen audit inventory recorded 69 source-reading call sites across 59
unique nodeids. Source inspection remains valid evidence for architecture,
security policy, workflow policy, and static contracts; it is not treated as
runtime proof. The following candidates now exercise behavior as well:

| Node | Current evidence |
| --- | --- |
| `tests/test_about_dialog.py::test_about_shows_version_and_no_network` | Shows the real dialog, checks the visible version, verifies initialization opens no URL, then clicks the repository link through an intercepted desktop-URL seam. The duplicate `test_about_instantiates_offscreen` node was removed because the retained runtime test subsumes construction and version visibility. |
| `tests/test_app_updater.py::test_manual_update_check_shows_splash_before_worker_starts` | Runs the real MainWindow orchestration and QThread worker in a subprocess, observing the visible splash before the worker starts. |
| `tests/test_app_updater.py::test_install_handoff_never_shows_complete_before_helper_starts` | Calls the real handoff method and records progress, paint, installer, and quit ordering through external UI/process seams. |
| `tests/test_command_palette_regression.py::test_command_palette_not_wired_to_help` | Inspects the live menu tree, triggers the actual F1 Help action, and observes its handler. |
| `tests/test_job_context.py::test_parser_never_executes_content` | Retains the source-level forbidden-primitive audit and feeds a hostile directive that would write a marker file if executed. |
| `tests/test_macos_signing.py::test_signing_cleans_keychain_without_echoing_secrets` | Exercises the signing failure path with intercepted tools and secrets; checks the created keychain is deleted and the certificate password is absent from output. This replaces the source-text node listed below. |
| `tests/test_wave3_remote_sftp_ssh.py::TestSSHCommandConstruction::test_ssh_backend_uses_shlex_quote` | Calls `SSHFilesBackend.remove` with a Unicode path containing a quote and shell substitution syntax; verifies the shell parses it as one inert path argument. |
| `tests/test_wave5_slurm_jobs_unicode.py::TestSSHRSlurmBackend::test_sbatch_quotes_unicode_path` | Calls `SSHSlurmBackend.sbatch` with Unicode and shell metacharacters and verifies parsed command arguments and returned job output. |

`test_connection_controller.py::test_secret_cleanup_and_no_qt_import` also
has a runtime bytearray-wipe assertion; its no-Qt import check remains a
separate static architecture claim. `test_job_context.py::test_parser_never_executes_content`
likewise intentionally retains its static security-policy scan beside the
hostile-input behavior check.

## Retained source-oriented contracts

These nodes retain source or import-boundary checks because their claim is a
static architecture, security, plugin-contract, or UI wiring policy. Their
success is not presented as runtime behavior:

- `tests/test_connection_controller.py::test_secret_cleanup_and_no_qt_import`
- `tests/test_editor_controller.py::test_editor_models_have_no_qt_imports`
- `tests/test_hardening_additional.py::test_host_adapter_import_boundary`
- `tests/test_hardening_additional.py::test_wx_dispatch_uses_host`
- `tests/test_hardening_additional.py::test_wx_submenu_disable_hide`
- `tests/test_hardening_additional.py::test_dynamic_separators_qt_and_wx`
- `tests/test_job_context.py::test_parser_never_executes_content`
- `tests/test_job_context.py::test_no_truba_constants_in_core_parser`
- `tests/test_job_tracking_controller.py::test_controller_has_no_qt_dependency`
- `tests/test_lint_engine.py::test_engine_module_has_no_execution_primitives`
- `tests/test_luna_fm_integration.py::TransferSourceOfTruthAndSecurityTests::test_no_auto_add_policy_anywhere_in_ssh_layer`
- `tests/test_menu_redesign.py::test_no_hardcoded_ansys_truba_ids`
- `tests/test_menu_redesign.py::test_plugin_manager_semantic_tabs`
- `tests/test_menu_redesign.py::test_plugins_changed_emitted_all_paths`
- `tests/test_menu_redesign.py::test_i18n_keys_exist`
- `tests/test_menu_redesign.py::test_about_dialog_properties`
- `tests/test_plugin_core.py::test_loader_never_executes_payload`
- `tests/test_presentation_models.py::test_boundary_source_has_no_toolkit_imports`
- `tests/test_terminal_boundaries.py::TerminalBoundaryTests::test_hostile_remote_output_crosses_webchannel_as_data`
- `tests/test_wx_connection.py::test_unknown_profile_and_optional_wx_import`
- `tests/test_wx_connection.py::test_wx_connection_view_has_async_selection_and_double_click_connect`
- `tests/test_wx_connection.py::test_connection_view_uses_shared_ssh_session_adapters`
- `tests/test_wx_connection_hardening.py::test_password_dialogs_use_correct_api`
- `tests/test_wx_connection_hardening.py::test_provider_template_no_generic_branch`
- `tests/test_wx_connection_profiles.py::test_wx_add_button_enabled_in_normal_startup`
- `tests/test_wx_connection_profiles.py::test_plugin_templates_without_hardcoded_names`
- `tests/test_wx_directories.py::test_batch_submit_is_deterministic_and_model_has_no_qt`
- `tests/test_wx_editor.py::test_shortcut_routing_and_model_has_no_qt`
- `tests/test_wx_editor.py::test_wx_editor_view_has_async_remote_save_and_distinct_actions`
- `tests/test_wx_help.py::test_wx_help_model_is_toolkit_free`
- `tests/test_wx_jobs.py::test_jobs_model_has_no_qt_import`
- `tests/test_wx_jobs.py::test_job_output_view_has_live_timer_and_resize_hooks`
- `tests/test_wx_local_files.py::test_local_browser_model_has_no_toolkit_import`
- `tests/test_wx_local_files.py::test_local_view_exposes_keyboard_and_context_actions`
- `tests/test_wx_logs.py::test_missing_log_is_empty_and_model_has_no_qt`
- `tests/test_wx_remote_files.py::test_remote_model_has_no_toolkit_import`
- `tests/test_wx_remote_files.py::test_remote_view_runs_operations_off_the_wx_thread`
- `tests/test_wx_shell.py::test_wx_shell_is_optional_and_has_migration_entrypoint`
- `tests/test_wx_shell.py::test_wx_shell_uses_shared_commands_and_responsive_start_size`
- `tests/test_wx_shell.py::test_wx_shell_dispatches_core_views`
- `tests/test_wx_terminal.py::test_wx_terminal_keeps_ssh_renderer_optional`
- `tests/test_wx_terminal_webview.py::test_wx_terminal_single_bridge_and_no_splitlines`
- `tests/test_wx_terminal_webview.py::test_wx_terminal_webview_composition_keeps_qt_out`
- `tests/test_wx_terminal_webview.py::test_wx_terminal_no_splitlines_in_hpc_write`

## Fixture, catalog, and tooling reads

These reads are inputs or generated outputs of the behavior under test; they
are not source-text claims about production runtime:

- `tests/test_lumi_quota.py::test_lumi_quota_parser_reads_project_storage_and_file_limits`
- `tests/test_nersc_quota.py::test_nersc_json_parser_reads_space_and_inode_quota`
- `tests/test_sync_version.py::test_sync_version_updates_all_runtime_declarations`
- `tests/test_version_consistency.py::test_repository_version_views_match`
- `tests/test_wave4_favorites_history_persistence.py::TestFavoritesRendering::test_en_favorites_label`
- `tests/test_wave4_favorites_history_persistence.py::TestFavoritesRendering::test_tr_favorites_label`
- `tests/test_wave4_favorites_history_persistence.py::TestFavoritesRendering::test_favorites_survives_roundtrip`
- `tests/test_wave79_audit.py::TestTrubaLssrvV1Audit::test_documented_box_table_fixture`

The old source-text signing node was
`tests/test_macos_signing.py::test_signing_source_has_cleanup_and_no_secret_echo`;
it is replaced by the runtime failure-path node above. No production files
changed. Focused validation for Packet I: 44 passed across the rewritten
behavior owners and parser/security neighborhood; Ruff and `git diff --check`
passed.
