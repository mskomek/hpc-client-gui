# Test Suite Cleanup Wave — 2026-09-12

Status: IN_PROGRESS

Frozen baseline: 12ce79935bf076e1062c57dc7dbd148bad2bfae1

Remediation baseline: 54f7376f3e3e1fccd672f121e33b68d2e8df2652
Remediation collection: 2,678 nodes (five added, zero removed from frozen)

Current packet: D
Dependency: Phase 1 test-suite audit completed

This is an executable cleanup Wave and implementation plan. The repository has no root ACTIVE_WAVE/WAVES execution system; this document does not claim to be its official active Wave ledger.

## Global rules

Unless a packet explicitly authorizes otherwise, forbidden paths during cleanup packets are:

- src/hpc_gui/**
- .github/workflows/**
- docs/v2/WX_MIGRATION_WAVE_STATUS.md
- migration/parity completion ledgers
- local protected guidance files

If a truthful test rewrite exposes a product defect, keep the failing truthful test, do not weaken it, do not silently fix production, mark the packet DEFECT_FOUND, and stop that packet.

Call a failure pre-existing only when the same frozen baseline, same node, and same outcome/signature match the recorded evidence.

Execute one packet at a time. Do not broaden a packet into general cleanup. Duplicate and weak-test rewrites are explicitly not part of Packet B.

## Packets

### A. Frozen baseline + inventory — DONE

Freeze 12ce79935bf076e1062c57dc7dbd148bad2bfae1, collect the baseline nodeids, preserve the truthful full-suite limitation and isolated failures, and archive deterministic Phase 1 evidence at audit/archive/12ce7993/test-suite-baseline/.

### B. Taxonomy registry + architecture + checker REPORT — DONE
  - Registered all nine primary categories and all qualifiers while retaining `packaging`.
  - REPORT reads `item.iter_markers()` and emits JSON; unmarked legacy nodes remain `zero-primary`.
  - Focused validation: 9 checker tests passed; collection moved from 2,678 to 2,687 with nine added audit nodes and no removals.
  - Current debt: 2,678 zero-primary, zero multi-primary. REPORT is non-gating; no hard enforcement is enabled.

Register primary and qualifier markers; add this architecture specification and the taxonomy REPORT checker with focused tests. Report only actual pytest marker state. Do not add primary markers to existing tests. Do not enable strict markers, change production, edit CI selectors, clean duplicates, or rewrite weak GUI tests.

### C. RATCHET + lane comparison — DONE
  - Frozen the Packet B taxonomy state at `89245cd4`: 2,687 exact nodeids, 2,678 accepted zero-primary nodes, nine classified audit nodes, and zero multi-primary nodes.
  - `--mode ratchet` passes after Packet C: 2,691 nodes, no new zero-primary nodes, no lost classifications, no multi-primary nodes, and no new catch-all files. Four new ratchet tests each have exactly one primary.
  - Exact selected-node manifests compare frozen, remediation, and Packet C sets for release suite, packaging, explicit macOS release, macOS developer, compat, CLI, SSH, Windows, and contract lanes. The Windows manifest separately records 13 unittest discovery IDs.
  - The release suite selection changed only by the 18 reviewed additions (5 updater + 9 REPORT + 4 ratchet nodes); no selected node was removed. Other recorded lane sets are unchanged. Automatic CI remains disabled; no workflow or selector was changed.
### D. Exact duplicate groups / false gates — DONE

All D1–D7 owners and mappings are recorded in [DUPLICATE_GROUP_REVIEW_D1-D7.md](DUPLICATE_GROUP_REVIEW_D1-D7.md). Three nodeids were added and eight retired, with no unrelated node delta. The exact node changes, unique assertions, canonical owners, targeted/file/neighborhood results, and CI/script reference search are recorded there. Packet D introduced no production changes. Translation catalog checks remain contract evidence; visible GUI localization is deferred to Packet F.

### E. Weak lifecycle tests — NOT STARTED

Review these exact high-risk candidates; rewrite only in this packet, after recording their assertion and observable lifecycle:

- tests/test_wx_updater_spec.py::test_update_cancel_prevents_install
- tests/test_wx_updater_spec.py::test_update_close_in_flight_safe
- tests/test_wx_updater_spec.py::test_update_late_callback_after_close_safe
- tests/test_wx_terminal_behavioral.py::test_fallback_panel_sets_non_parity
- tests/test_wx_terminal_webview.py::test_wx_terminal_fallback_sets_non_parity
- tests/test_about_dialog.py::test_about_shows_version_and_no_network
- tests/test_app_updater.py::test_manual_update_check_shows_splash_before_worker_starts
- tests/test_wx_packaged_smoke.py::test_packaged_wx_smoke_gate_reports_critical_stages

Also carry the Wave78 no-selection node from D3 and tests/test_wave80_files_outputs.py::TestWave80Audit::test_files_context_menu_localized from D5. No rewrite is in scope here.

### F. GUI truthfulness — NOT STARTED

Audit event-to-visible-result evidence in tests/test_wave80_files_outputs.py, tests/test_wave78_jobs_details.py, tests/test_wx_terminal_webview.py, tests/test_wx_terminal_behavioral.py, tests/test_wx_updater_spec.py, tests/test_about_dialog.py, tests/test_app_updater.py, tests/test_corrective_jobs_details.py, and tests/test_wave2_wx_ui_parity.py. Keep static API-existence checks under audit/contract claims; require a real framework object/action/event and visible state for GUI claims.

### G. Historical/Wave ownership review — NOT STARTED

Review ownership and distinct assertions in tests/test_wave0_unicode_baseline.py, tests/test_wave1_unicode_core_policy.py, tests/test_wave2_directories_local_files.py, tests/test_wave2_wx_ui_parity.py, tests/test_wave3_remote_sftp_ssh.py, tests/test_wave9_ci_unicode_matrix.py, tests/test_wave10_release_gate.py, and the newer tests/test_wave78_jobs_details.py, tests/test_wave79_audit.py, tests/test_wave79_provider_contract.py, and tests/test_wave80_files_outputs.py. Wave names alone do not establish obsolete ownership; Waves78–80 are collected though the migration ledger ends at Wave77.

### H. Settings/config isolation — NOT STARTED

Start with the known deterministic test-setup hang:
tests/test_connection_advanced_settings.py::ParallelismSourceOfTruthTests::test_settings_dialog_has_no_global_parallelism_editor

Phase 1 reproduced an infinite loop when the test patches Path.home with a default MagicMock, making Path.exists truthy in src/hpc_gui/config/storage.py::_next_config_backup. Keep the test-setup behavior distinct from a production defect. Review adjacent settings/config ownership in tests/test_connection_advanced_settings.py, tests/test_config_storage_atomic.py, tests/test_profile_transfer_settings.py, and tests/test_transfer_parallelism_migration.py.

### I. Source-text behavior rewrites — NOT STARTED

For each source-text candidate, preserve legitimate audit/contract/policy checks but do not treat source text as runtime proof. Start with tests/test_about_dialog.py::test_about_shows_version_and_no_network, tests/test_app_updater.py::test_manual_update_check_shows_splash_before_worker_starts, tests/test_command_palette_regression.py::test_command_palette_not_wired_to_help, tests/test_connection_controller.py::test_secret_cleanup_and_no_qt_import, tests/test_editor_controller.py::test_editor_models_have_no_qt_imports, tests/test_job_context.py::test_parser_never_executes_content, tests/test_lint_engine.py::test_engine_module_has_no_execution_primitives, tests/test_macos_signing.py::test_signing_source_has_cleanup_and_no_secret_echo, and the D1/D2 Unicode boundary candidates. The archived Phase 1 static scan records 69 source-text candidates.

### J. Resource/concurrency cleanup — NOT STARTED

Review real acquisition/release, ordering, ownership, cancellation, and bounded waits in:
- tests/test_connection_advanced_settings.py::TransferChannelSafetyTests::test_workers_receive_distinct_channels
- tests/test_selected_job_context.py::TestSelectedJobStoreThreadSafety::test_concurrent_subscribe_and_select
- tests/test_transfer_concurrency.py::test_two_ftp_transfers_overlap_with_distinct_connections
- tests/test_transfer_concurrency.py::test_cancelled_transfer_releases_isolated_backend
- tests/test_ftp_widget.py::FtpWidgetTests::test_transfer_dialog_runs_up_to_parallel_limit
- tests/test_wx_jobs_stress.py::test_wx_jobs_stress_backend_workers_and_reads_are_bounded
- tests/test_wx_terminal_webview.py::test_wx_terminal_100_reconnects_no_leak

The Phase 1 static scan found 61 literal sleep call sites, 10 hasattr assertions, and 8 thread/process construction sites; inspect call evidence rather than bulk rewriting.

### K. Reporting/E2E reclassification — NOT STARTED

Review the one composed user workflow tests/test_plugin_e2e.py::test_full_clean_user_lifecycle against the E2E definition. Review evidence and validator ownership in tests/test_gui_audit_screenshots.py::test_manifest_exists_and_commit_current, tests/test_gui_audit_screenshots.py::test_hashes_match_and_no_unexplained_duplicate, tests/test_reproducibility_bundle.py::test_offline_export_contains_versioned_job_script_and_readme, tests/test_release_manifest.py, tests/test_capability_report.py, and tests/test_wave79_audit.py. Report evidence does not by itself make a test E2E.

### L. Legacy static/migration ownership review — NOT STARTED

Review, do not blanket-delete, tests/test_parity_matrix.py, tests/test_gui_feature_parity_baseline.py, tests/test_qt_removal_gate.py, tests/test_wx_terminal_parity_evidence.py, tests/test_wave2_wx_ui_parity.py, tests/test_wave9_ci_unicode_matrix.py, and tests/test_wave10_release_gate.py against the Qt/PySide6 production runtime, actively tested optional wxPython implementation, and docs/v2/WX_MIGRATION_WAVE_STATUS.md. Do not update completion ledgers in unrelated packets.

### M. Full-suite classification — NOT STARTED

Classify all nodes from audit/archive/12ce7993/test-suite-baseline/inventory-enriched.json using reviewed marker state, not keyword proposals. Resolve ambiguity from behavior and canonical ownership. Preserve the current zero-primary report as actual state until reviewed markers are applied. The heuristic proposed-taxonomy artifact is a proposal only.

### N. CI marker migration — NOT STARTED

No migration in Packet B. Frozen HEAD has no automatic PR/push CI; .github/workflows/ contains release.yml, and scripts/ci.py plus scripts/release_test_suite.py remain local selectors. Review archived docs/ci-disabled/ci.yml and the lane inventory before any separately authorized CI migration. Do not restore .github/workflows/ci.yml from this plan.

### O. Reporting integration + closeout — NOT STARTED

After marker review and a separately authorized CI decision, integrate the taxonomy report where appropriate, verify JSON/report ownership with tests/test_gui_audit_screenshots.py and tests/test_reproducibility_bundle.py, compare all baseline nodeids, record the final mapping and remaining exceptions, then close the Wave. This packet does not authorize full-suite/CI integration now.
