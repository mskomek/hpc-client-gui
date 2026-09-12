# Test Suite Cleanup Wave — 2026-09-12

Status: IN_PROGRESS

Frozen baseline: 12ce79935bf076e1062c57dc7dbd148bad2bfae1

Current packet: E
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

Register primary and qualifier markers; add this architecture specification and the taxonomy REPORT checker with focused tests. Report only actual pytest marker state. Do not add primary markers to existing tests. Do not enable strict markers, change production, edit CI selectors, clean duplicates, or rewrite weak GUI tests.

### C. RATCHET + lane comparison — DONE

Add a local `--mode ratchet --baseline audit/archive/12ce7993/test-suite-baseline/taxonomy-ratchet.json` gate. The baseline was captured from the real marker report at Phase B commit `058c83bb3318ddaee85bf98ba430079a4acd4a02`: 2,682 collected, 2,673 zero-primary nodeids, zero multi-primary. RATCHET permits only those exact existing zero-primary nodeids; any new zero-primary nodeid or any multi-primary item fails. After a legacy node is classified, remove its nodeid from the allowlist in the same reviewed change. REPORT remains non-gating. RATCHET is not wired into CI.

The reproducible lane comparison is archived at `audit/archive/12ce7993/test-suite-baseline/lane-comparison-phase2.json`. It uses collected nodeids and actual `iter_markers()` data filtered by each recorded file/marker selector. All frozen lane counts reproduce. The 11 Packet B/C checker tests are the only added nodeids; none were removed. Current broad release selectors collect 2,682 nodes (2,671 frozen non-packaging nodes plus 11 audit nodes); explicit frozen subsets retain their audited counts, including 54 nodes per release macOS architecture list.

| Selector | Frozen nodes | Current nodes | Current zero-primary | Current audit |
| --- | ---: | ---: | ---: | ---: |
| `scripts/ci.py packaging` | 1 | 1 | 1 | 0 |
| `scripts/ci.py compat` | 202 | 202 | 202 | 0 |
| `scripts/ci.py cli` | 164 | 164 | 164 | 0 |
| `scripts/ci.py ssh` | 45 | 45 | 45 | 0 |
| `scripts/ci.py windows` pytest selector | 6 | 6 | 6 | 0 |
| `scripts/ci.py macos` | 55 | 55 | 55 | 0 |
| `scripts/ci.py contract` | 10 | 10 | 10 | 0 |
| shared release suite; release workflow Linux/Windows; archived GUI lane | 2,671 | 2,682 | 2,671 | 11 |
| release workflow macOS arm64 | 54 | 54 | 54 | 0 |
| release workflow macOS x86_64 | 54 | 54 | 54 | 0 |
| archived CI compat / cli / ssh_sftp | 286 / 164 / 45 | 286 / 164 / 45 | same as count | 0 |
| archived CI macos / windows / contract / packaging / wx-smoke | 69 / 41 / 10 / 1 / 59 | same as frozen | same as count | 0 |

The active `.github/workflows/release.yml` is `workflow_dispatch` only. Its test-job union leaves these two packaging-marked tests outside the collected pytest selectors:

- `tests/test_wheel_packaging.py::test_built_wheel_contains_required_assets`
- `tests/test_wx_packaged_smoke.py::test_packaged_wx_smoke_gate_reports_critical_stages`

The union of local `scripts/ci.py` pytest selectors and the shared release suite also leaves the packaged wx smoke node above uncovered; `ci.py windows` additionally invokes two `unittest discover` commands, which are outside pytest nodeid comparison. These are recorded lane facts, not permission to change selectors. Automatic PR/push CI remains absent; no CI files or selectors were changed.

### D. Exact duplicate groups / false gates — DONE

Deletion gate evidence was reviewed for each removal: inventory and assertions are recorded above; the retained or replacement owner is named; node references and CI/report selector references were searched; targeted replacements passed. No CI selector pointed at a removed node. The exact nodeid mapping is in `docs/testing/PHASE_2_EXECUTION_REPORT.md`.

- D1: removed `TestEncodingBoundaryJustification::test_ssh_client_decode_justified`; retained `TestEncodingBoundaryInventory::test_errors_replace_in_ssh` as canonical owner of the shared `errors="replace"` boundary claim.
- D2: replaced source-text-only SFTP encoding claims with `tests/test_ssh_files_byte_preservation.py::test_sftp_download_upload_roundtrip_preserves_arbitrary_bytes`. It exercises real `SSHFilesBackend.download` and `upload` behavior through a fake SFTP seam, verifies arbitrary bytes survive, and verifies channel cleanup. Removed both duplicate source-text nodes.
- D3: `test_cluster_servers_visible_without_selected_job_when_provider_supports` now keeps the job unselected, triggers the refresh action, and verifies visible loaded table state. `test_raw_server_status_opens` independently triggers the raw-status action and checks the `lssrv` result through the viewer seam.
- D4: `TestSchemaV4Audit::test_v4_optional_sections_ok` now supplies valid job-details, accounting, and cluster-status sections; the minimal-schema case remains in `test_v4_valid`.
- D5/D6: removed the two Wave80 audit duplicates; retained `TestFilesBehavior::test_context_menu_labels_localized` and `TestOutputsBehavior::test_standard_output_localized` as canonical owners.
- D7: moved typed-password precedence to marked unit/regression test `tests/test_connection_profile_service.py::ConnectionProfileServiceTests::test_typed_password_precedes_saved_secret`; removed duplicate nodes from 71.2 and 71.3. Retained `tests/test_wx_connection_hardening.py::test_typed_password_precedence`, which additionally covers ssh_info, GUI connection, and storage invariants.

Collection changed by exactly 7 removals and 2 additions relative to Packet C; no unrelated old node disappeared. The ratchet allowlist was reviewed and reduced by exactly the seven removed legacy nodeids. Packet D did not change production, CI, migration ledgers, or protected guidance.

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
