# Test Taxonomy Final Report

Status: Packet O DONE. Integration-closeout census on 2026-09-13: 2,657 collected; every collected node has exactly one primary category; zero-primary 0; multi-primary 0; strict zero-debt ratchet PASS. The release suite still has two failures, so this taxonomy result does not establish integration or release readiness.

This closeout census supersedes the historical 2,656-node / six-exception snapshot below. The prior packet record is retained as history. See [TEST_SUITE_INTEGRATION_CLOSEOUT_2026-09-13.md](TEST_SUITE_INTEGRATION_CLOSEOUT_2026-09-13.md) and [the strict ratchet baseline](../../audit/test-governance/integration-closeout-20260913/taxonomy-ratchet-strict.json) for current evidence.

Frozen baseline: `12ce79935bf076e1062c57dc7dbd148bad2bfae1`
Taxonomy snapshot SHA: `6cad198dca6c0f69bc8196f5030a7aebcba9d696`
Governance branch: `test-suite-governance-20260912`
Final governance HEAD: reported after the closeout commit in the execution response and same status document.

This report uses actual pytest collection and `iter_markers()` data. It does not use the Phase 1 heuristic proposal as marker truth. The per-node machine mapping, exact removal evidence, and all marker/qualifier values are in [`taxonomy-final-mapping.json`](../../audit/test-taxonomy/taxonomy-final-mapping.json).

## Final taxonomy

| Primary category | Count |
| --- | ---: |
| `audit` | 156 |
| `contract` | 566 |
| `e2e` | 7 |
| `gui` | 671 |
| `integration` | 362 |
| `release` | 101 |
| `reporting` | 21 |
| `runtime_smoke` | 6 |
| `unit` | 760 |

Total collected: **2,656**
Zero-primary: **6**
Multi-primary: **0**
Direct test-calling-test warnings: **0**
Catch-all filename warnings: **0**
RATCHET: **PASS** — six exact allowlisted zero-primary nodes, zero new zero-primary, zero multi-primary.

Qualifier counts:
- `acceptance`: 1
- `artifact_dependent`: 25
- `concurrency`: 119
- `hardware`: 0
- `license`: 2
- `linux`: 0
- `macos`: 0
- `packaging`: 4
- `performance`: 17
- `qt`: 270
- `regression`: 161
- `resource`: 118
- `semantic`: 958
- `slow`: 14
- `subprocess`: 57
- `synthetic_hardware`: 0
- `windows`: 4
- `wx`: 569

The six zero-primary nodes are retained baseline-failure exceptions. No marker was added to disguise a false gate. The full node set is in [`ZERO_PRIMARY_DISPOSITION.md`](ZERO_PRIMARY_DISPOSITION.md) and the machine registry.

## Frozen-to-final node mapping

| Measure | Count |
| --- | ---: |
| Frozen baseline nodes | 2,673 |
| Final nodes | 2,656 |
| Current additions (includes renamed successors) | 36 |
| Frozen nodes absent by exact nodeid (includes renamed predecessors) | 53 |
| Explicit old→current rename mappings | 19 |
| Unchanged exact nodeids | 2,620 |
| Net collection change | -17 |

The 36 current additions comprise 17 new nodes plus 19 renamed successors. The 53 absent frozen nodeids comprise 19 renamed predecessors plus 34 deletions. The full baseline list remains [`nodeids.txt`](../../audit/archive/12ce7993/test-suite-baseline/nodeids.txt).

### Added nodes

| Nodeid | Primary | Qualifiers | Owner packet | Purpose / canonical owner |
| --- | --- | --- | --- | --- |
| `tests/test_connection_profile_service.py::ConnectionProfileServiceTests::test_typed_password_precedes_saved_secret` | `unit` | `regression` | D | Canonical saved-secret versus typed-password precedence service behavior; primary unit/regression. |
| `tests/test_ssh_files_byte_preservation.py::test_sftp_download_upload_roundtrip_preserves_arbitrary_bytes` | `unit` | `regression` | D | Isolated SFTP backend byte-preservation behavior and channel cleanup; primary unit/regression. |
| `tests/test_test_taxonomy_checker.py::test_catch_all_filename_is_warning_only` | `audit` | — | B | Focused synthetic-record tests for actual-marker reporting, warning heuristics, infrastructure errors, and ratchet logic; primary audit. |
| `tests/test_test_taxonomy_checker.py::test_collection_failure_returns_nonzero` | `audit` | — | B | Focused synthetic-record tests for actual-marker reporting, warning heuristics, infrastructure errors, and ratchet logic; primary audit. |
| `tests/test_test_taxonomy_checker.py::test_direct_test_call_warning_finds_imported_test_function` | `audit` | — | B | Focused synthetic-record tests for actual-marker reporting, warning heuristics, infrastructure errors, and ratchet logic; primary audit. |
| `tests/test_test_taxonomy_checker.py::test_json_keeps_exact_nodeids` | `audit` | — | B | Focused synthetic-record tests for actual-marker reporting, warning heuristics, infrastructure errors, and ratchet logic; primary audit. |
| `tests/test_test_taxonomy_checker.py::test_qualifiers_do_not_count_as_primaries` | `audit` | — | B | Focused synthetic-record tests for actual-marker reporting, warning heuristics, infrastructure errors, and ratchet logic; primary audit. |
| `tests/test_test_taxonomy_checker.py::test_ratchet_allows_only_recorded_zero_primary_debt` | `audit` | — | B | Focused synthetic-record tests for actual-marker reporting, warning heuristics, infrastructure errors, and ratchet logic; primary audit. |
| `tests/test_test_taxonomy_checker.py::test_ratchet_rejects_new_zero_primary_and_multi_primary_debt` | `audit` | — | B | Focused synthetic-record tests for actual-marker reporting, warning heuristics, infrastructure errors, and ratchet logic; primary audit. |
| `tests/test_test_taxonomy_checker.py::test_report_mode_succeeds_with_taxonomy_debt` | `audit` | — | B | Focused synthetic-record tests for actual-marker reporting, warning heuristics, infrastructure errors, and ratchet logic; primary audit. |
| `tests/test_test_taxonomy_checker.py::test_single_primary_is_counted_once` | `audit` | — | B | Focused synthetic-record tests for actual-marker reporting, warning heuristics, infrastructure errors, and ratchet logic; primary audit. |
| `tests/test_test_taxonomy_checker.py::test_two_primary_markers_are_reported` | `audit` | — | B | Focused synthetic-record tests for actual-marker reporting, warning heuristics, infrastructure errors, and ratchet logic; primary audit. |
| `tests/test_test_taxonomy_checker.py::test_unmarked_record_is_zero_primary` | `audit` | — | B | Focused synthetic-record tests for actual-marker reporting, warning heuristics, infrastructure errors, and ratchet logic; primary audit. |
| `tests/test_wx_jobs_behavior.py::test_wx_job_output_close_discards_pending_refresh` | `gui` | `regression`, `resource`, `concurrency`, `wx` | M | Actual wx Jobs output refresh coalescing, follower, error recovery, and close lifecycle coverage; primary gui/wx. |
| `tests/test_wx_jobs_behavior.py::test_wx_job_output_coalesces_pending_refreshes` | `gui` | `semantic`, `regression`, `resource`, `concurrency`, `wx` | M | Actual wx Jobs output refresh coalescing, follower, error recovery, and close lifecycle coverage; primary gui/wx. |
| `tests/test_wx_jobs_behavior.py::test_wx_job_output_read_error_releases_in_flight_state` | `gui` | `regression`, `resource`, `concurrency`, `wx` | M | Actual wx Jobs output refresh coalescing, follower, error recovery, and close lifecycle coverage; primary gui/wx. |
| `tests/test_wx_jobs_behavior.py::test_wx_job_remote_follower_coalesces_reads` | `gui` | `semantic`, `regression`, `resource`, `concurrency`, `wx` | M | Actual wx Jobs output refresh coalescing, follower, error recovery, and close lifecycle coverage; primary gui/wx. |

### Renamed nodeids

| Frozen nodeid | Current nodeid | Owner packet |
| --- | --- | --- |
| `tests/test_macos_signing.py::test_signing_source_has_cleanup_and_no_secret_echo` | `tests/test_macos_signing.py::test_signing_cleans_keychain_without_echoing_secrets` | I |
| `tests/test_wave2_directories_local_files.py::TestClipboardOperations::test_paste_into_itself_guard` | `tests/test_wave2_directories_local_files.py::TestClipboardOperations::test_paste_directory_into_itself_is_rejected` | M (final taxonomy census) |
| `tests/test_wave2_wx_ui_parity.py::TestContextMenuEventWiring::test_context_menu_open_wired` | `tests/test_wave2_wx_ui_parity.py::TestContextMenuEventWiring::test_context_menu_edit_opens_editor` | F |
| `tests/test_wave2_wx_ui_parity.py::TestPaneLabels::test_toolbar_button_tooltips` | `tests/test_wave2_wx_ui_parity.py::TestPaneLabels::test_toolbar_buttons_are_present_and_labeled` | F |
| `tests/test_wave2_wx_ui_parity.py::TestSelectionPreservation::test_rename_error_shows_unicode_filename` | `tests/test_wave2_wx_ui_parity.py::TestSelectionPreservation::test_invalid_rename_preserves_unicode_filename` | F |
| `tests/test_wave2_wx_ui_parity.py::TestStatusFeedback::test_listing_shows_file_count` | `tests/test_wave2_wx_ui_parity.py::TestDirectoryListing::test_listing_displays_all_files` | F |
| `tests/test_wave2_wx_ui_parity.py::TestToolbarAlignment::test_up_button_disabled_at_root` | `tests/test_wave2_wx_ui_parity.py::TestToolbarAlignment::test_parent_button_navigates_to_parent` | F |
| `tests/test_wx_jobs_behavior.py::test_wx_job_output_minimize_suspends_follow_and_restore_resumes_it` | `tests/test_wx_jobs_behavior.py::test_wx_job_minimize_suspends_job_refresh_and_restores_it` | M |
| `tests/test_wx_jobs_behavior.py::test_wx_job_output_pause_keeps_refreshing_but_stops_live_follow` | `tests/test_wx_jobs_behavior.py::test_wx_job_output_pause_freezes_until_resume` | M |
| `tests/test_wx_terminal_parity_evidence.py::test_close_while_output_in_flight` | `tests/test_wx_terminal_parity_evidence.py::test_close_after_queued_output_is_idempotent` | F |
| `tests/test_wx_terminal_parity_evidence.py::test_multiline_paste` | `tests/test_wx_terminal_parity_evidence.py::test_panel_sends_multiline_paste_to_bridge` | F |
| `tests/test_wx_terminal_parity_evidence.py::test_resize_updates_dimensions_and_pty` | `tests/test_wx_terminal_parity_evidence.py::test_panel_forwards_resize_to_ssh_seam` | F |
| `tests/test_wx_terminal_parity_evidence.py::test_stress_100_reconnects` | `tests/test_wx_terminal_parity_evidence.py::test_reconnect_replaces_output_subscriber` | F |
| `tests/test_wx_terminal_parity_evidence.py::test_stress_500_inputs` | `tests/test_wx_terminal_parity_evidence.py::test_repeated_input_forwarding_preserves_order` | F |
| `tests/test_wx_terminal_parity_evidence.py::test_stress_500_resizes` | `tests/test_wx_terminal_parity_evidence.py::test_repeated_resize_requests_are_deduplicated` | F |
| `tests/test_wx_terminal_parity_evidence.py::test_stress_repeated_font_find_clear` | `tests/test_wx_terminal_parity_evidence.py::test_repeated_font_find_clear_bridge_calls_stay_bounded` | F |
| `tests/test_wx_terminal_parity_evidence.py::test_unicode_round_trip` | `tests/test_wx_terminal_parity_evidence.py::test_panel_preserves_unicode_output_payload` | F |
| `tests/test_wx_terminal_parity_evidence.py::test_vt_carriage_return_overwrite` | `tests/test_wx_terminal_parity_evidence.py::test_panel_preserves_carriage_return_bridge_payload` | F |
| `tests/test_wx_terminal_parity_evidence.py::test_vt_sgr_normal_color_bold_reset` | `tests/test_wx_terminal_parity_evidence.py::test_panel_sends_sgr_payload_to_terminal_bridge` | F |

### Removed-node audit

There are 34 true deletions: 12 duplicate owner, 9 false gate, 12 stdlib only, 1 test helper only. The 19 renamed predecessors are listed above. For each of all 53 absent frozen nodeids, the machine mapping records disposition, reason, canonical replacement owner or why none exists, exact active workflow/script reference search, selector impact, evidence that behavior was preserved or was not independently present, and packet owner.

| Deletion disposition | Count |
| --- | ---: |
| `DUPLICATE_OWNER` | 12 |
| `FALSE_GATE` | 9 |
| `STDLIB_ONLY` | 12 |
| `TEST_HELPER_ONLY` | 1 |

### Rewritten test bodies

AST comparison against the frozen source identified **64** collected nodes whose test-function body changed; marker/decorator-only changes are excluded. These are the exact old/current pairs:

- `tests/test_about_dialog.py::test_about_shows_version_and_no_network`
- `tests/test_app_updater.py::test_manual_update_check_shows_splash_before_worker_starts`
- `tests/test_command_palette_regression.py::test_command_palette_not_wired_to_help`
- `tests/test_connection_advanced_settings.py::ParallelismSourceOfTruthTests::test_settings_dialog_has_no_global_parallelism_editor`
- `tests/test_connection_controller.py::test_secret_cleanup_and_no_qt_import`
- `tests/test_connection_profile_service.py::ConnectionProfileServiceTests::test_mfa_transient_not_stored`
- `tests/test_corrective_jobs_details.py::TestSec23_RawViewerClose::test_raw_viewer_refresh_callback_is_called`
- `tests/test_editor_controller.py::test_editor_models_have_no_qt_imports`
- `tests/test_editor_flow.py::EditorFlowTests::test_save_targets_active_document`
- `tests/test_hardening_additional.py::test_wx_separator_lifecycle_offscreen`
- `tests/test_job_context.py::test_parser_never_executes_content`
- `tests/test_lint_engine.py::test_engine_module_has_no_execution_primitives`
- `tests/test_macos_signing.py::test_signing_source_has_cleanup_and_no_secret_echo` → `tests/test_macos_signing.py::test_signing_cleans_keychain_without_echoing_secrets`
- `tests/test_security_hardening_wave.py::test_python_plugin_payload_and_legacy_engine_fail_closed`
- `tests/test_transfer_directory_controllers.py::test_controllers_have_no_qt_imports`
- `tests/test_wave2_directories_local_files.py::TestClipboardOperations::test_paste_into_itself_guard` → `tests/test_wave2_directories_local_files.py::TestClipboardOperations::test_paste_directory_into_itself_is_rejected`
- `tests/test_wave2_wx_ui_parity.py::TestContextMenuEventWiring::test_background_new_folder_wired`
- `tests/test_wave2_wx_ui_parity.py::TestContextMenuEventWiring::test_background_refresh_wired`
- `tests/test_wave2_wx_ui_parity.py::TestContextMenuEventWiring::test_context_menu_copy_clipboard`
- `tests/test_wave2_wx_ui_parity.py::TestContextMenuEventWiring::test_context_menu_copy_path`
- `tests/test_wave2_wx_ui_parity.py::TestContextMenuEventWiring::test_context_menu_cut_clipboard`
- `tests/test_wave2_wx_ui_parity.py::TestContextMenuEventWiring::test_context_menu_open_wired` → `tests/test_wave2_wx_ui_parity.py::TestContextMenuEventWiring::test_context_menu_edit_opens_editor`
- `tests/test_wave2_wx_ui_parity.py::TestContextMenuEventWiring::test_context_menu_rename_wired`
- `tests/test_wave2_wx_ui_parity.py::TestPaneLabels::test_toolbar_button_tooltips` → `tests/test_wave2_wx_ui_parity.py::TestPaneLabels::test_toolbar_buttons_are_present_and_labeled`
- `tests/test_wave2_wx_ui_parity.py::TestSelectionPreservation::test_rename_error_shows_unicode_filename` → `tests/test_wave2_wx_ui_parity.py::TestSelectionPreservation::test_invalid_rename_preserves_unicode_filename`
- `tests/test_wave2_wx_ui_parity.py::TestSelectionPreservation::test_rename_preserves_selection`
- `tests/test_wave2_wx_ui_parity.py::TestStatusFeedback::test_listing_shows_file_count` → `tests/test_wave2_wx_ui_parity.py::TestDirectoryListing::test_listing_displays_all_files`
- `tests/test_wave2_wx_ui_parity.py::TestTextFieldLabels::test_path_bar_editable`
- `tests/test_wave2_wx_ui_parity.py::TestTextFieldLabels::test_path_bar_exists`
- `tests/test_wave2_wx_ui_parity.py::TestToolbarAlignment::test_refresh_button_always_enabled`
- `tests/test_wave2_wx_ui_parity.py::TestToolbarAlignment::test_up_button_disabled_at_root` → `tests/test_wave2_wx_ui_parity.py::TestToolbarAlignment::test_parent_button_navigates_to_parent`
- `tests/test_wave78_jobs_details.py::test_cluster_servers_visible_without_selected_job_when_provider_supports`
- `tests/test_wave78_jobs_details.py::test_raw_server_status_opens`
- `tests/test_wave79_audit.py::TestSchemaV4Audit::test_v4_optional_sections_ok`
- `tests/test_wave7_editor_terminal_logs.py::TestLogs::test_logs_model_unicode_read`
- `tests/test_wx_a11y.py::test_wx_a11y_terminal_limits_documented`
- `tests/test_wx_ansys_view.py::test_wx_ansys_close_in_flight_safe`
- `tests/test_wx_embedded_terminal.py::test_embedded_terminal_runtime_language_refresh`
- `tests/test_wx_files_sync_compare.py::test_wx_compare_close_in_flight_is_safe`
- `tests/test_wx_jobs_behavior.py::test_wx_job_output_discards_stale_result_after_job_selection_changes`
- `tests/test_wx_jobs_behavior.py::test_wx_job_output_does_not_overlap_remote_reads`
- `tests/test_wx_jobs_behavior.py::test_wx_job_output_minimize_suspends_follow_and_restore_resumes_it` → `tests/test_wx_jobs_behavior.py::test_wx_job_minimize_suspends_job_refresh_and_restores_it`
- `tests/test_wx_jobs_behavior.py::test_wx_job_output_pause_keeps_refreshing_but_stops_live_follow` → `tests/test_wx_jobs_behavior.py::test_wx_job_output_pause_freezes_until_resume`
- `tests/test_wx_jobs_stress.py::test_wx_jobs_stress_blocked_reads_never_overlap`
- `tests/test_wx_jobs_stress.py::test_wx_jobs_stress_pause_resume_state_never_desynchronizes`
- `tests/test_wx_packaged_smoke.py::test_packaged_wx_smoke_gate_reports_critical_stages`
- `tests/test_wx_terminal_behavioral.py::test_fallback_panel_sets_non_parity`
- `tests/test_wx_terminal_parity_evidence.py::test_close_while_output_in_flight` → `tests/test_wx_terminal_parity_evidence.py::test_close_after_queued_output_is_idempotent`
- `tests/test_wx_terminal_parity_evidence.py::test_generate_parity_evidence`
- `tests/test_wx_terminal_parity_evidence.py::test_multiline_paste` → `tests/test_wx_terminal_parity_evidence.py::test_panel_sends_multiline_paste_to_bridge`
- `tests/test_wx_terminal_parity_evidence.py::test_resize_updates_dimensions_and_pty` → `tests/test_wx_terminal_parity_evidence.py::test_panel_forwards_resize_to_ssh_seam`
- `tests/test_wx_terminal_parity_evidence.py::test_stress_100_reconnects` → `tests/test_wx_terminal_parity_evidence.py::test_reconnect_replaces_output_subscriber`
- `tests/test_wx_terminal_parity_evidence.py::test_stress_500_inputs` → `tests/test_wx_terminal_parity_evidence.py::test_repeated_input_forwarding_preserves_order`
- `tests/test_wx_terminal_parity_evidence.py::test_stress_500_resizes` → `tests/test_wx_terminal_parity_evidence.py::test_repeated_resize_requests_are_deduplicated`
- `tests/test_wx_terminal_parity_evidence.py::test_stress_repeated_font_find_clear` → `tests/test_wx_terminal_parity_evidence.py::test_repeated_font_find_clear_bridge_calls_stay_bounded`
- `tests/test_wx_terminal_parity_evidence.py::test_unicode_round_trip` → `tests/test_wx_terminal_parity_evidence.py::test_panel_preserves_unicode_output_payload`
- `tests/test_wx_terminal_parity_evidence.py::test_vt_carriage_return_overwrite` → `tests/test_wx_terminal_parity_evidence.py::test_panel_preserves_carriage_return_bridge_payload`
- `tests/test_wx_terminal_parity_evidence.py::test_vt_sgr_normal_color_bold_reset` → `tests/test_wx_terminal_parity_evidence.py::test_panel_sends_sgr_payload_to_terminal_bridge`
- `tests/test_wx_terminal_webview.py::test_wx_terminal_100_reconnects_no_leak`
- `tests/test_wx_terminal_webview.py::test_wx_terminal_fallback_sets_non_parity`
- `tests/test_wx_terminal_webview.py::test_wx_terminal_find_next_and_prev`
- `tests/test_wx_updater_spec.py::test_update_cancel_prevents_install`
- `tests/test_wx_updater_spec.py::test_update_close_in_flight_safe`
- `tests/test_wx_updater_spec.py::test_update_late_callback_after_close_safe`

## Baseline failures and newly fixed defects

### ARCHIVED_BASELINE_FAILURE — seven Packet A failures

- `tests/test_macos_ci.py::test_macos_ci_matrix_covers_both_native_architectures`
- `tests/test_macos_ci.py::test_macos_ci_has_no_release_upload_or_signing_step`
- `tests/test_macos_release_workflow.py::test_release_preflight_shares_the_ci_test_suite`
- `tests/test_wave9_ci_unicode_matrix.py::TestResultsVerification::test_wx_unicode_smoke_cannot_fail_open`
- `tests/test_workflow_action_pins.py::test_every_workflow_exists`
- `tests/test_wx_packaged_smoke.py::test_packaged_wx_smoke_gate_reports_critical_stages`
- `tests/test_gui_audit_screenshots.py::test_manifest_exists_and_commit_current`

### SUPPLEMENTAL_BASELINE_FAILURE

- `tests/test_wx_shell_p0_stress.py::test_wx_shell_p0_stress_real_wx_paths` — same `KeyError: 'update'` before stress assertions at the frozen SHA.
- `tests/test_wx_file_action_policy.py::test_remote_policy_exact_matrix[one_file-selection1-expected1]` — frozen baseline has the same missing expected action.
- `tests/test_wx_file_action_policy.py::test_remote_policy_exact_matrix[one_dir-selection2-expected2]` — frozen baseline has the same missing expected action.

The original deterministic settings-dialog test-setup hang is also preserved in Packet A evidence; Packet H repaired the test’s MagicMock `Path.home()` setup. The current setup test and adjacent modules pass.

### LATENT_PRODUCT_DEFECT_DISCOVERED_BY_STRONGER_TEST — fixed

- **Jobs output overlap:** the actual wx refresh path started a second remote read during an active read for the same selected-job/output generation. `src/hpc_gui/wx_jobs.py` now serializes by owner generation, coalesces requests, preserves one pending refresh, validates stale results, and releases state on errors/close. The truthful no-overlap test passes; four focused new tests cover coalescing/follower/error/close. Commit: `38ada4c7`.
- **Plugin menu hang:** dynamic rebuild detached a menu item with `Remove`, then destroyed its submenu separately. The code now deletes items through `DestroyItem`, inserts the submenu once through the documented overload, and unbinds stale dynamic handlers. The exact lifecycle test passes twice and covers 25 Unicode visible/hidden cycles. Commit: `b083d67d`.

### Environment/order-dependent native test-run failure

The official release suite’s broad pytest child exits with Windows native code `3221226525` while entering `tests/test_jobs_outputs_scroll.py::JobsOutputsScrollTests::setUp`. This recurred with and without coverage; `tests/test_jobs_outputs_scroll.py` passes alone (20 passed plus 4 subtests). The raw exit is recorded without diagnosing the native exit type. It is not classed as a baseline failure or a proven product defect. The interrupted release run has no authoritative whole-suite pass/fail/skip/duration totals.

The archived ratchet file records `collection_total: 2654` and snapshot `repository_sha: 13f1f9a8…`. Those are historical snapshot metadata; the current taxonomy REPORT and collection both reconcile at 2,656. The ratchet uses the archived exact six-node allowlist and validates current zero-primary and multi-primary state; it does not use the archived collection count as a current total.

A separate test-harness error in `test_raw_viewer_refresh_callback_is_called` was found during fail-fast validation and fixed by retaining the `wx.App` reference. The exact test passes and its module passes 17 tests.

## Skip and xfail record

- No xfail declarations/usages remain in `tests/`; the historical terminal XPASS decorators were removed and the exact cases passed after removal.
- Observed platform skip: `tests/test_deb_installer.py::test_stage_is_private_and_rejects_symlink` skips after staging assertions because this Windows host cannot create symlinks.
- Artifact-dependent skip: all 10 collected nodes in `tests/test_plugin_contract.py` were skipped in the isolated validation because `HPC_GUI_CONTRACT_REPO` is unset; the adjacent official plugin checkout was not used.
- The interrupted full suite does not provide authoritative total skip/xfail counts. Other conditional WebView/platform skips therefore remain uncounted here.

## Validation

| Command | Result | Pass | Fail | Skip | XFail | XPass | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `python -m compileall -q src/hpc_gui` | PASS | — | — | — | — | — | Also completed in release preflight. |
| `python -m ruff check src tests scripts` | PASS | — | — | — | — | — | All checks passed. |
| `python scripts/check_i18n.py` | PASS | — | — | — | — | — | Keys, references, and hardcoded UI text passed. |
| `python scripts/smoke_test.py` | PASS | — | — | — | — | — | Smoke test OK. |
| Taxonomy REPORT | PASS | 2,656 collected | 0 | 0 | 0 | 0 | Actual markers; zero direct-test-call and filename warnings. |
| Taxonomy RATCHET | PASS | 6 allowed | 0 new debt | 0 | 0 | 0 | Six exact baseline exceptions; no multi-primary. |
| `python -m pytest tests --collect-only -q` | PASS | 2,656 collected | 0 | 0 | 0 | 0 | Collection exit 0. |
| Frozen/current node-set comparison | PASS | +36 current | −53 frozen | — | — | — | 19 old→current rename mappings. |
| `python -m pytest tests/test_test_taxonomy_checker.py -q` | PASS | 11 | 0 | 0 | 0 | 0 | New audit tests. |
| Four wx Jobs modules | PASS | 50 | 0 | 0 | 0 | 0 | Includes truthful no-overlap path. |
| Exact plugin lifecycle twice; hardening module | PASS | 14 runs + module | 0 | 0 | 0 | 0 | 2 isolated lifecycle passes; module 12 passed. |
| Plugin contribution/menu modules | PASS | 75 | 0 | 0 | 0 | 0 | No teardown warning. |
| Seven-module sequential wx resource sweep | PASS | 52 | 0 | 0 | 0 | 0 | No UnregisterClass/open-window warning. |
| Raw viewer callback exact node / module | PASS | 1 / 17 | 0 | 0 | 0 | 0 | Test-owned wx.App lifetime fix. |
| `tests/test_jobs_outputs_scroll.py` alone | PASS | 20 + 4 subtests | 0 | 0 | 0 | 0 | Same module fails natively only in broad-suite order. |
| Fail-fast release-selector diagnostic (`-rs -x`) | BASELINE FAILURE | 345 | 1 archived | 1 | 0 | 0 | 22.63s; screenshot-manifest stale SHA; not a full-suite run. |
| `python scripts/release_test_suite.py --coverage` | INCOMPLETE | unknown | unknown | unknown | unknown | unknown | Native exit 3221226525 in broad pytest process; no final summary. |
| `python scripts/release_test_suite.py` | INCOMPLETE | unknown | unknown | unknown | unknown | unknown | Same native exit before final summary. |

The full release suite is not claimed as passing. The fail-fast result is partial and its single failure matches the archived baseline signature.

## Packet and integration state

A–M: DONE. N: NOT APPLICABLE. O: DONE. Independent read-only audit: **PASS WITH FOLLOW-UP**. The audit’s two documentation findings have been corrected: the Windows native exit is described without an unsupported diagnosis, and the archived ratchet’s old collection count is explicitly historical snapshot metadata.

Automatic GitHub Actions CI: **DISABLED**. `.github/workflows/ci.yml` is absent, no `push`/`pull_request` trigger exists, and `.github/workflows/release.yml` is manual `workflow_dispatch` only. Local and release selectors are unchanged.

At closeout review, `origin/develop` is the frozen baseline and the governance branch is 14 commits ahead, 0 behind. Before the Packet O push, `origin/test-suite-governance-20260912` was at `7a45496b4929a578db9a77b8a051e822fadc9011`. The complete diff from `develop` is 267 test files, 3 production files, 6 documentation files, 13 audit files, one script, and `pyproject.toml`; workflow changes: 0; CI selector changes: 0. Push only to `test-suite-governance-20260912`. No push or merge to `develop` is authorized by this closeout.

Develop integration recommendation: **NOT READY TO MERGE** until a supported broad release-suite run completes. The governance Wave can close with the full-suite limitation recorded; this report does not claim that the interrupted suite passed.

Wave verdict: **WAVE COMPLETE**. The final commit SHA and post-push remote verification are recorded in the execution response; the taxonomy snapshot remains `6cad198dca6c0f69bc8196f5030a7aebcba9d696`.
