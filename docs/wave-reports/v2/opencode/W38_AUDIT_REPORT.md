# W38 Audit Report — Migration, corruption recovery and secret boundaries (fresh-context self-audit)

```text
Wave: W38
Canonical audit path: docs/wave-reports/v2/opencode/W38_AUDIT_REPORT.md
Canonical wave report: docs/wave-reports/v2/opencode/W38_WAVE_REPORT.md
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Tested HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 + W38 scope working-tree diff
New tests: tests/test_w38_migration_secrets.py (12 tests)
Audit context: fresh read of wave file + registry + source + tests + full diff of owned files (no reuse of stale PASS)
```

## Verdict

```text
AUDIT: PASS (worker fresh-context self-audit; controller independent audit still required before close)
```

This audit does not close the Wave. Lifecycle close (pending->done) remains controller-owned.

## Checks

- Owned IDs complete: all 23 source rows + 11 TODO rows dispositioned VERIFIED with evidence in the wave report; no AWAITING_INPUT (no missing concrete input; updater/state fixtures are local/synthetic).
- Evidence identity: binds to Baseline SHA + listed working-tree diff; no stale PASS reused; sensitivity proven by fault runs (EV-W38-SENS-A/B).
- Tests: narrow 12 passed; broader 66 passed (exact counts, exit 0); GUI FULL via real wx MessageBox capture; no skips/xfails/weakening.
- FIX independence: FIX-A (redaction) vs FIX-B (keymap preservation) have different defect IDs, surfaces, root causes, and regression tests; FIX-C is extra hardening, not double-counted.
- Diff quality: owned diff limited to 4 source files + 1 test; `git diff --check` clean; no secrets/noise; unrelated dirty files preserved.
- Contradiction scan: wave report, findings table, dispositions, counts, and SHAs agree; no second W38 report exists.
- STOP conditions: none triggered (no bypassable verification, no private key packaged, no irreversible migration, no silent data loss).
- TODO-061/ARCH-SIZE-001: correctly closed as evidenced no-change (no shim removed, no split warranted).

## Residual notes for the controller independent audit

1. Re-run `tests/test_w38_migration_secrets.py` plus the broader slice at audit time; any behavior-affecting integration change since this report invalidates this self-audit.
2. Confirm no sibling merge touched `ui_errors.py`, `wx_errors.py`, `shortcut_preferences.py`, or `command_history_store.py` before close.
3. Close is lifecycle-only (pending->done + bookkeeping); no product-code change is authorized inside the audit/close step beyond allowlisted report/evidence paths.


## Controller-persisted fresh independent audit — 2026-09-24T18:30:59.531455+00:00

- Wave: `W38`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0017-W38-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0017-W38-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✗ Read .agents/skills/ac-wave-opencode-audit/SKILL.md failed
Error: Offset 31 is out of range for this file (30 lines)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Skill "ac-wave-core" 
→ Read .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md 
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
→ Read .agents/protocol/AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✱ Glob "waves/pending/W*.md" 0 matches
✱ Glob "waves/done/W*.md" 0 matches
✱ Glob "waves/**/W38*" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves 
$ Get-ChildItem -Path waves -Recurse -Filter "*38*" | Select-Object FullName, Length | Format-Table -AutoSize; Write-Host "---DIRS---"; Get-ChildItem -Path waves | Select-Object Name | Format-Table -AutoSize; Write-Host "---GIT---"; git log --oneline -5; git status --short | Select-Object -First 30
/usr/bin/bash: line 1: Get-ChildItem: command not found
/usr/bin/bash: line 1: Select-Object: command not found
/usr/bin/bash: line 1: Format-Table: command not found
/usr/bin/bash: line 1: Write-Host: command not found
/usr/bin/bash: line 1: Get-ChildItem: command not found
/usr/bin/bash: line 1: Select-Object: command not found
/usr/bin/bash: line 1: Format-Table: command not found
/usr/bin/bash: line 1: Write-Host: command not found
c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
/usr/bin/bash: line 1: Select-Object: command not found
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls -R waves | head -n 200; echo "---"; ls waves/pending/ | head -n 100; echo "---DONE---"; ls waves/done/ | head -n 100; echo "---BLOCKED---"; ls waves/blocked/ 2>&1 | head -n 50
waves:
00-START-HERE.md
bak
blocked
done
pending
postponed
waves

waves/bak:
AUDIT_REAUDIT_WAVE_00_10_2026-09-10.md
README_MASTER_PLAN.md
V2_EXECUTION_START_PROMPT.md
V2_FINAL_SPECIFICATION.md
V2_TODOS.md
V2_TODO_WAVE_COVERAGE.md
W16.stale-pending-20260924.md
WAVE_00_BASELINE_AUDIT_INFRASTRUCTURE.md
WAVE_01_UNICODE_CORE_POLICY.md
WAVE_02_DIRECTORIES_LOCAL_FILES.md
WAVE_03_REMOTE_SFTP_SSH.md
WAVE_04_FAVORITES_HISTORY_PERSISTENCE.md
WAVE_05_SLURM_JOBS_UNICODE.md
WAVE_06_PLUGIN_PROVIDER_UNICODE.md
WAVE_07_EDITOR_TERMINAL_LOGS_ARCHIVES.md
WAVE_08_I18N_UI_ERGONOMICS.md
WAVE_09_CI_UNICODE_MATRIX.md
WAVE_10_MIGRATION_DOCS_RELEASE_GATE.md
WAVE_V2_FINAL_01.md
WAVE_V2_FINAL_02.md
WAVE_V2_FINAL_03.md
WAVE_V2_FINAL_04.md
WAVE_V2_FINAL_05.md
WAVE_V2_FINAL_06.md
WAVE_V2_FINAL_07.md
WAVE_V2_FINAL_08.md
WAVE_V2_FINAL_09.md
WAVE_V2_FINAL_10.md
WAVE_V2_FINAL_11.md
WAVE_V2_FINAL_INDEX.md
WAVE_V2_STRICT_EXECUTION_PROTOCOL.md

waves/blocked:
05-macos-production-updates.md
06-appimage-flatpak.md
07-acceptance-and-rollout.md
WAVE-03-release-packaging-verification.md
WAVE-04-publish-release.md
WAVE-07-wiki-readmes-and-release.md
wave_12_registry_release_and_application_integration.md

waves/done:
01-shared-foundation.md
02-verification-and-release-contract.md
03-ubuntu-deb-updates.md
ANSYS_LINTER_WAVES_RESULT.md
ANSYS_LINTER_WAVE_00_README.md
ANSYS_LINTER_WAVE_01_API_V2_CONTRACT.md
ANSYS_LINTER_WAVE_02_CORE_ENGINE.md
ANSYS_LINTER_WAVE_03_FLUENT_WORKBENCH.md
ANSYS_LINTER_WAVE_04_MAPDL_MECHANICAL.md
ANSYS_LINTER_WAVE_05_CCL_ICEM.md
ANSYS_LINTER_WAVE_06_SYSTEM_COUPLING_AND_REMAINING.md
ANSYS_LINTER_WAVE_07_UI_CLI_HPC_RULES.md
ANSYS_LINTER_WAVE_08_ACCEPTANCE_RELEASE.md
ANSYS_LINTER_WAVE_09_PACKAGING_CI_REPAIR.md
UPDATE-03-RESULT.md
W01.md
W02.md
W03.md
W04.md
W05.md
W06.md
W07.md
W08.md
W09.md
W10.md
W11.md
W12.md
W13.md
W14.md
W15.md
W16.md
W17.md
W18.md
W19.md
W20.md
W21.md
W22.md
W23.md
W24.md
W25.md
W26.md
W27.md
W28.md
W29.md
W30.md
W31.md
W32.md
W33.md
W34.md
W35.md
W36.md
W37.md
WAVE-01-RESULT.md
WAVE-01-macos-bundle-inventory.md
WAVE-02-RESULT.md
WAVE-02-safe-pyinstaller-pruning.md
WAVE_72_JOBS_DETAILS_WORKSPACE.md
WAVE_73_JOBS_FILES_EXPLORER_PROVIDER_FILTERS.md
WAVE_74_DYNAMIC_JOB_OUTPUT_CHANNELS.md
WAVE_78_JOBS_DETAILS_RAW_FALLBACK.md
WAVE_79_PROVIDER_PARSER_CONTRACT_TRUBA.md
WAVE_80_FILES_OUTPUTS_UX_I18N.md
wave_00_cross_repo_contract_alignment.md
wave_00_current_release_boundary_baseline_freeze.md
wave_01_provider_schema_extensions.md
wave_01_unified_cluster_self_test_core.md
wave_02_cluster_self_test_gui.md
wave_02_provider_context_model.md
wave_03_dynamic_storage_ui.md
wave_03_provider_capability_view.md
wave_04_diagnostic_bundle_v2.md
wave_04_safe_remote_path_resolvers.md
wave_05_provider_update_diff_freshness.md
wave_05_quota_backend_infrastructure_v2.md
wave_06_nersc_perlmutter_provider.md
wave_06_trusted_tool_disclosure.md
wave_07_ansys_diagnostic_explanation_ux.md
wave_07_lumi_provider.md
wave_08_pawsey_setonix_provider.md
wave_08_slurm_directive_editing_model.md
wave_09_slurm_job_arrays.md
wave_09_tacc_stampede3_provider_and_mfa.md
wave_10_cineca_leonardo_provider_and_certificate_auth.md
wave_10_slurm_job_dependencies.md
wave_11_job_failure_explanation.md
wave_11_provider_validation_and_docs_hardening.md
wave_12_transfer_sha_256_integrity_verification.md
wave_13_profile_export_import.md
wave_14_duplicate_profile.md
wave_15_storage_policy_intelligence.md
wave_16_job_record_store.md
wave_17_job_provenance_capture.md
wave_18_reproducibility_bundle_export.md
wave_19_job_history_dashboard.md
wave_20_smart_walltime_suggestions.md
wave_21_complete_gui_feature_parity_baseline.md
wave_22_pointer_gesture_interaction_contract.md
wave_23_keyboard_interaction_contract.md
wave_24_framework_neutral_command_registry.md
wave_25_focus_aware_command_router.md
wave_26_standard_windows_linux_keymap.md
wave_27_standard_macos_keymap.md
wave_28_editor_shortcut_standardization_dirty_state_safety.md
wave_29_keyboard_shortcut_preferences.md
wave_30_command_palette.md
wave_31_unified_help_architecture.md
wave_32_keyboard_shortcuts_help_reference.md
wave_33_mouse_gesture_help_reference.md
wave_34_help_search_interaction_lookup.md
wave_35_contextual_shortcut_hints_quick_tour_refresh.md
wave_36_jobs_controller_extraction.md
wave_37_transfer_session_remote_directory_controller_extraction.md
wave_38_connection_controller_extraction.md
wave_39_editor_controller_document_model_extraction.md
wave_40_ui_framework_boundary_presentation_models.md
wave_41_adaptive_layout_dpi_window_geometry_contract.md
wave_44_wx_connection_profile_management.md
wave_46_wx_local_file_browser.md
wave_47_wx_remote_directory_browser.md
wave_48_wx_ftp_transfer_workspace.md
wave_50_wx_jobs_output_tracking.md
wave_51_wx_editor_template_lint_workflow.md
wave_53_framework_neutral_ansys_tool_presentation_contract.md
wave_54_wx_ansys_trusted_tool_ui.md

waves/pending:
W38.md
W39.md
W40.md
W41.md
W42.md
W43.md
W44.md
W45.md
W46.md
W47.md
W48.md
W49.md
W50.md
W51.md
W52.md
W53.md
W54.md
W55.md
W56.md
W57.md
W58.md
W59.md
---
W38.md
W39.md
W40.md
W41.md
W42.md
W43.md
W44.md
W45.md
W46.md
W47.md
W48.md
W49.md
W50.md
W51.md
W52.md
W53.md
W54.md
W55.md
W56.md
W57.md
W58.md
W59.md
W60.md
W61.md
---DONE---
01-shared-foundation.md
02-verification-and-release-contract.md
03-ubuntu-deb-updates.md
ANSYS_LINTER_WAVES_RESULT.md
ANSYS_LINTER_WAVE_00_README.md
ANSYS_LINTER_WAVE_01_API_V2_CONTRACT.md
ANSYS_LINTER_WAVE_02_CORE_ENGINE.md
ANSYS_LINTER_WAVE_03_FLUENT_WORKBENCH.md
ANSYS_LINTER_WAVE_04_MAPDL_MECHANICAL.md
ANSYS_LINTER_WAVE_05_CCL_ICEM.md
ANSYS_LINTER_WAVE_06_SYSTEM_COUPLING_AND_REMAINING.md
ANSYS_LINTER_WAVE_07_UI_CLI_HPC_RULES.md
ANSYS_LINTER_WAVE_08_ACCEPTANCE_RELEASE.md
ANSYS_LINTER_WAVE_09_PACKAGING_CI_REPAIR.md
UPDATE-03-RESULT.md
W01.md
W02.md
W03.md
W04.md
W05.md
W06.md
W07.md
W08.md
W09.md
W10.md
W11.md
W12.md
W13.md
W14.md
W15.md
W16.md
W17.md
W18.md
W19.md
W20.md
W21.md
W22.md
W23.md
W24.md
W25.md
W26.md
W27.md
W28.md
W29.md
W30.md
W31.md
W32.md
W33.md
W34.md
W35.md
W36.md
W37.md
WAVE-01-RESULT.md
WAVE-01-macos-bundle-inventory.md
WAVE-02-RESULT.md
WAVE-02-safe-pyinstaller-pruning.md
WAVE_72_JOBS_DETAILS_WORKSPACE.md
WAVE_73_JOBS_FILES_EXPLORER_PROVIDER_FILTERS.md
WAVE_74_DYNAMIC_JOB_OUTPUT_CHANNELS.md
WAVE_78_JOBS_DETAILS_RAW_FALLBACK.md
WAVE_79_PROVIDER_PARSER_CONTRACT_TRUBA.md
WAVE_80_FILES_OUTPUTS_UX_I18N.md
wave_00_cross_repo_contract_alignment.md
wave_00_current_release_boundary_baseline_freeze.md
wave_01_provider_schema_extensions.md
wave_01_unified_cluster_self_test_core.md
wave_02_cluster_self_test_gui.md
wave_02_provider_context_model.md
wave_03_dynamic_storage_ui.md
wave_03_provider_capability_view.md
wave_04_diagnostic_bundle_v2.md
wave_04_safe_remote_path_resolvers.md
wave_05_provider_update_diff_freshness.md
wave_05_quota_backend_infrastructure_v2.md
wave_06_nersc_perlmutter_provider.md
wave_06_trusted_tool_disclosure.md
wave_07_ansys_diagnostic_explanation_ux.md
wave_07_lumi_provider.md
wave_08_pawsey_setonix_provider.md
wave_08_slurm_directive_editing_model.md
wave_09_slurm_job_arrays.md
wave_09_tacc_stampede3_provider_and_mfa.md
wave_10_cineca_leonardo_provider_and_certificate_auth.md
wave_10_slurm_job_dependencies.md
wave_11_job_failure_explanation.md
wave_11_provider_validation_and_docs_hardening.md
wave_12_transfer_sha_256_integrity_verification.md
wave_13_profile_export_import.md
wave_14_duplicate_profile.md
wave_15_storage_policy_intelligence.md
wave_16_job_record_store.md
wave_17_job_provenance_capture.md
wave_18_reproducibility_bundle_export.md
wave_19_job_history_dashboard.md
wave_20_smart_walltime_suggestions.md
wave_21_complete_gui_feature_parity_baseline.md
wave_22_pointer_gesture_interaction_contract.md
wave_23_keyboard_interaction_contract.md
wave_24_framework_neutral_command_registry.md
wave_25_focus_aware_command_router.md
---BLOCKED---
05-macos-production-updates.md
06-appimage-flatpak.md
07-acceptance-and-rollout.md
WAVE-03-release-packaging-verification.md
WAVE-04-publish-release.md
WAVE-07-wiki-readmes-and-release.md
wave_12_registry_release_and_application_integration.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W38.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls -la docs/wave-reports/v2/opencode/ 2>&1 | head -n 80; echo "===ARTIFACTS==="; ls -R artifacts/wave_W38 2>&1 | head -n 100; echo "===W38 tmp==="; find .tmp -maxdepth 5 -iname "*W38*" 2>&1 | head -n 50; echo "===GIT W38==="; git log --oneline --all --grep="W38" | head -n 20; echo "===BRANCH==="; git branch --show-current; git rev-parse HEAD; echo "===STATUS==="; git status --short | head -n 50
total 1448
drwxr-xr-x 1 mskomek 197121      0 Sep 24 21:27 .
drwxr-xr-x 1 mskomek 197121      0 Sep 17 14:55 ..
-rw-r--r-- 1 mskomek 197121   3234 Sep 21 22:44 W01_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  32218 Sep 21 22:44 W01_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3449 Sep 21 22:48 W02_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  29941 Sep 21 22:53 W02_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2873 Sep 21 22:55 W03_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  29088 Sep 21 22:55 W03_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2763 Sep 21 22:59 W04_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  25620 Sep 21 22:58 W04_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2479 Sep 21 23:40 W05_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  25994 Sep 21 23:40 W05_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   4746 Sep 22 06:39 W06_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  27695 Sep 21 23:55 W06_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   5066 Sep 22 07:48 W07_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  35939 Sep 22 07:48 W07_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2881 Sep 22 07:58 W08_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  23038 Sep 22 07:58 W08_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3901 Sep 21 17:11 W09_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  21254 Sep 22 08:27 W09_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3843 Sep 21 17:14 W10_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  21296 Sep 22 11:15 W10_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   4467 Sep 22 12:07 W11_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  22271 Sep 22 12:10 W11_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2365 Sep 22 12:46 W12_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  25872 Sep 22 12:49 W12_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3746 Sep 22 13:07 W13_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  40239 Sep 22 13:08 W13_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3986 Sep 21 17:31 W14_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  24145 Sep 22 13:25 W14_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   5438 Sep 22 13:55 W15_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  24155 Sep 22 13:55 W15_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   5187 Sep 22 14:59 W16_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  25482 Sep 22 14:59 W16_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   4392 Sep 22 15:13 W17_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  24822 Sep 22 15:27 W17_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  27464 Sep 22 22:10 W18_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  49040 Sep 22 22:10 W18_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3721 Sep 22 22:35 W19_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  21978 Sep 22 22:35 W19_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   4425 Sep 22 22:54 W20_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  20567 Sep 22 22:54 W20_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3542 Sep 22 23:15 W21_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  27266 Sep 22 23:21 W21_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  65358 Sep 24 10:19 W22_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  42340 Sep 24 10:06 W22_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   8434 Sep 24 11:19 W23_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121 122117 Sep 24 12:10 W24_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  14775 Sep 24 12:07 W24_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  18892 Sep 24 12:59 W25_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  14732 Sep 24 15:41 W26_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  21521 Sep 24 16:09 W27_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  21169 Sep 24 16:28 W28_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  19590 Sep 24 16:49 W29_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  16662 Sep 24 17:22 W30_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  17597 Sep 24 17:45 W31_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  14440 Sep 24 18:13 W32_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  15382 Sep 24 18:39 W33_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  13844 Sep 24 19:05 W34_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121 111776 Sep 24 20:34 W35_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  16329 Sep 24 19:52 W35_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  18888 Sep 24 20:49 W36_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  21368 Sep 24 21:17 W37_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  20748 Sep 24 21:15 W37_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2547 Sep 24 21:27 W38_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  21429 Sep 24 21:27 W38_WAVE_REPORT.md
===ARTIFACTS===
ls: cannot access 'artifacts/wave_W38': No such file or directory
===W38 tmp===
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0015-W38-plan-controller-context.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0015-W38-plan-dispatch.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0015-W38-plan-job.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0015-W38-plan-normalized.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0015-W38-plan-opencode.log
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0016-W38-run-controller-context.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0016-W38-run-dispatch.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0016-W38-run-job.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0016-W38-run-normalized.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0016-W38-run-opencode.log
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0017-W38-audit-controller-context.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0017-W38-audit-dispatch.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0017-W38-audit-job.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0017-W38-audit-opencode.log
===GIT W38===
===BRANCH===
develop
c8293d3ca309526ed250c794c3b294f7c54ef369
===STATUS===
 M README.md
 M src/hpc_gui/core/ui_errors.py
 M src/hpc_gui/core/wx_errors.py
 M src/hpc_gui/docs/HELP_en.md
 M src/hpc_gui/docs/HELP_tr.md
 M src/hpc_gui/docs/PLUGINS_en.md
 M src/hpc_gui/docs/PLUGINS_tr.md
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/plugins/installer.py
 M src/hpc_gui/plugins/loader.py
 M src/hpc_gui/plugins/models.py
 M src/hpc_gui/plugins/validator.py
 M src/hpc_gui/services/command_history_store.py
 M src/hpc_gui/services/files_ssh.py
 M src/hpc_gui/services/output_follower.py
 M src/hpc_gui/services/shortcut_preferences.py
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/ui/dialogs/plugin_manager_dialog.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_plugins.py
 M src/hpc_gui/wx_plugins_view.py
 M src/hpc_gui/wx_settings.py
 M src/hpc_gui/wx_settings_view.py
 M src/hpc_gui/wx_shell.py
?? ".agent-legacy-backup (1)/"
?? NUL
?? artifacts/opencode/wave_W26/
?? artifacts/opencode/wave_W27/
?? artifacts/opencode/wave_W28/
?? artifacts/opencode/wave_W29/
?? artifacts/opencode/wave_W30/
?? artifacts/opencode/wave_W31/
?? artifacts/opencode/wave_W32/
?? artifacts/opencode/wave_W33/
?? artifacts/opencode/wave_W34/
?? artifacts/opencode/wave_W36/
?? artifacts/wave_W29/
?? artifacts/wave_W32/
?? artifacts/wave_W33/
?? artifacts/wave_W35/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W29_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W30_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W33_WAVE_REPORT.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W38_AUDIT_REPORT.md 
→ Read docs/wave-reports/v2/opencode/W38_WAVE_REPORT.md 
$ cat ".tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0016-W38-run-normalized.json"; echo "===PLAN NORM==="; cat ".tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0015-W38-plan-normalized.json"; echo "===AUDIT CTX==="; cat ".tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0017-W38-audit-controller-context.json"
{
  "status": "READY_FOR_AUDIT",
  "summary": "0c794c3b294f7c54ef369\ndevelop\n## develop\n M README.md\n M src/hpc_gui/core/ui_errors.py\n M src/hpc_gui/core/wx_errors.py\n M src/hpc_gui/docs/HELP_en.md\n M src/hpc_gui/docs/HELP_tr.md\n M src/hpc_gui/docs/PLUGINS_en.md\n M src/hpc_gui/docs/PLUGINS_tr.md\n M src/hpc_gui/i18n/en.json\n M src/hpc_gui/i18n/tr.json\n> ac-wave-opencode-executor · muse-spark-1.3-contributor\n\u001b[0m← \u001b[0mWrite docs/wave-reports/v2/opencode/W38_WAVE_REPORT.md\nCreated file successfully: docs/wave-reports/v2/opencode/W38_WAVE_REPORT.md\n> ac-wave-opencode-executor · muse-spark-1.3-contributor\n\u001b[0m← \u001b[0mWrite docs/wave-reports/v2/opencode/W38_AUDIT_REPORT.md\nCreated file successfully: docs/wave-reports/v2/opencode/W38_AUDIT_REPORT.md\n> ac-wave-opencode-executor · muse-spark-1.3-contributor\n\u001b[0m$ \u001b[0m/d/Python/Python312/python -m pytest tests/test_w38_migration_secrets.py -q 2>&1 | tail -n 3\ngit diff --check 2>&1 | head -n 5 | cat\ngit status --short -- docs/wave-reports/v2/opencode/W38* tests/test_w38* | cat\n............                                                             [100%]\n12 passed in 0.91s\nwarning: in the working copy of 'src/hpc_gui/core/wx_errors.py', LF will be replaced by CRLF the next time Git touches it\nwarning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it\nwarning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it\nwarning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it\nwarning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it\n?? docs/wave-reports/v2/opencode/W38_AUDIT_REPORT.md\n?? docs/wave-reports/v2/opencode/W38_WAVE_REPORT.md\n?? tests/test_w38_migration_secrets.py\n> ac-wave-opencode-executor · muse-spark-1.3-contributor\nAC_WAVE_BRIDGE_STDOUT_BEGIN\nExecuting W38 run phase — loading canonical skill and profile.\nLoaded W38 migration scope — now inspecting repository state and requirements.\nInitial review shows migration foundations exist — now running discovery to find remaining defects.\nDiscovery is surfacing secret-boundary and migration gaps — digging into error paths and updater state.\nI've narrowed two independent fixes — verifying them with reproduction probes.\nProbes confirmed — now implementing the redaction and migration-preservation fixes.\nCore fixes in place — now validating and building regression evidence.\nTest run exposed an additional history-filter gap — applying that correction.\nSensitivity proven — now running broader validation and final checks.\nAll tests green — now compiling the wave report and audit evidence.\nW38 run phase complete. Implementation with two independent substantive fixes plus hardening, 12 new tests green, broader 66-test slice green, sensitivity proven, GUI FULL evidence, reports written.\n\nAC_WAVE_MACHINE_RESULT_BEGIN\nWAVE_PHASE_STATUS: READY_FOR_AUDIT\nAC_WAVE_MACHINE_RESULT_END\n",
  "findings": [],
  "changed_files": [],
  "next_action": "none",
  "phase_log_path": ".tmp\\agent-runs\\ac-wave-opencode-parallel\\20260924-203154-ca45d2b7\\0016-W38-run-opencode.log"
}
===PLAN NORM===
{
  "status": "READY",
  "summary": ", `test_wx_settings`); reproduce gaps; build `WAVE_FINDINGS` table (`Finding ID | Severity | Surface | Evidence | Root cause | Impact | Candidate fix | Countable | Status`).\n4. **Remediation:** smallest coherent fixes tracing requirement→owner→test→evidence; minimum **FIX-A + FIX-B independent root causes** (prefer different domains, e.g. migration/idempotence/recovery vs. secret redaction/export). Second-defect search protocol if <2 legitimate defects; no manufactured fixes; `TWO-FIX-EXCEPTION` needs maintainer approval.\n5. **Tests:** fixture-based migration tests (V1/Qt-era profiles, GUI prefs, shortcuts, updater state, unknown/future keys + Unicode, corrupt/interrupted recovery, re-run idempotence, V1→V2 acceptance TODO-053); secret audit tests (log/export/debug-dump/error-message redaction with synthetic fixtures); each counted fix needs DEF→FIX→TEST→EV chain, before/after evidence, sensitivity proof (fail-before/pass-after or revert/mutation), happy + negative + lifecycle assertions, behavioral (not existence-only) asserts, legitimate mock boundaries, deterministic fixtures, no greenwashing.\n6. **GUI evidence (FULL):** required class `GUI` — exact runtime wx event/action/test/readback for migration-visible effects and redaction surfaces; static-only checks insufficient. Package claims need exact SHA-256; external claims need real infra or truthful `EXTERNAL_BLOCKED`.\n7. **Reviews:** `git status/diff --stat/diff --check`/full diff; secrets/binary noise/unrelated-change/duplicate-logic/weakened-test check; `POST_GREEN_REVIEW` for alternate entry points, silent fallbacks, stale state, cleanup, packaged divergence.\n8. **Reports:** update exactly `docs/wave-reports/v2/opencode/W38_WAVE_REPORT.md` + `W38_AUDIT_REPORT.md` (no suffixed copies); record SHAs, IDs, commands with exact passed/failed/skipped/xfailed/exit, evidence identities, findings, resume state.\n\n## 6. Risks / stop watch\n\n- Dirty `develop` tree + parallel cohort → re-pin at run start; integration-base changes require focused retest + fresh audit.\n- STOP UPD-085: any irreversible-destruction risk = terminal `BLOCKED`, record resume point, exit cleanly, no user prompt.\n- Credentials: synthetic fixtures only; never request/invent secrets; unavailable infra → `EXTERNAL_BLOCKED`, complete remaining safe checks.\n- Destructive Git / unresolved authority / missing mandatory prerequisite → terminal status, not a question.\n\n## 7. Acceptance preview\n\nDoD: all owned non-superseded requirements + TODO details implemented/already-valid, truthful current evidence (incl. GUI FULL), no owned blocking defects, diff reviewed, canonical report current, fresh-context audit `PASS`. No blanket reopen afterwards except fresh current defect in owned IDs or proven regression inside ownership surface.\n\n*Plan phase strictly read-only — no repository or `.tmp` writes performed; plan returned via stdout for controller persistence.*\n\nAC_WAVE_MACHINE_RESULT_BEGIN\nWAVE_PHASE_STATUS: READY\nAC_WAVE_MACHINE_RESULT_END\n",
  "findings": [],
  "changed_files": [],
  "next_action": "none",
  "phase_log_path": ".tmp\\agent-runs\\ac-wave-opencode-parallel\\20260924-203154-ca45d2b7\\0015-W38-plan-opencode.log"
}
===AUDIT CTX===
{
  "target": "W38",
  "phase": "audit",
  "content_identity": "dbe8f473f89a0a9e30b25b85bab42766838f961f307ad8853479ab80180f2d2f",
  "findings_path": null,
  "audit_receipt": {
    "audit_status": "PASS",
    "tested_wave": "W37",
    "tested_content_identity": "4685efb3155347bd0b9f027f208c0c22a08f4172ee3fd543450a0bf978e7cec7",
    "audit_candidate_sha": "c8293d3ca309526ed250c794c3b294f7c54ef369",
    "audit_result_path": ".tmp\\agent-runs\\ac-wave-opencode-parallel\\20260924-203154-ca45d2b7\\0012-W37-audit-normalized.json",
    "audit_passed_at": "2026-09-24T18:17:51.140371+00:00",
    "audit_report_path": "docs\\wave-reports\\v2\\opencode\\W37_AUDIT_REPORT.md"
  }
}
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff --stat HEAD 2>&1 | head -n 60; echo "===DIFF CHECK==="; git diff --check 2>&1 | head -n 20; echo "===W38 SCOPE DIFF STAT==="; git status --short -- src/hpc_gui/core/ui_errors.py src/hpc_gui/core/wx_errors.py src/hpc_gui/services/shortcut_preferences.py src/hpc_gui/services/command_history_store.py tests/test_w38_migration_secrets.py 2>&1; echo "===UNTRACKED TEST EXISTS==="; ls -la tests/test_w38_migration_secrets.py 2>&1
warning: in the working copy of 'src/hpc_gui/core/wx_errors.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/command_history_store.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/shortcut_preferences.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
 README.md                                       |   5 +-
 src/hpc_gui/core/ui_errors.py                   |   8 +-
 src/hpc_gui/core/wx_errors.py                   |   6 +
 src/hpc_gui/docs/HELP_en.md                     |   3 +-
 src/hpc_gui/docs/HELP_tr.md                     |   4 +-
 src/hpc_gui/docs/PLUGINS_en.md                  |  65 +++-
 src/hpc_gui/docs/PLUGINS_tr.md                  |  62 +++-
 src/hpc_gui/i18n/en.json                        |  13 +-
 src/hpc_gui/i18n/tr.json                        |  13 +-
 src/hpc_gui/plugins/installer.py                |   7 +
 src/hpc_gui/plugins/loader.py                   |   7 +
 src/hpc_gui/plugins/models.py                   |   5 +
 src/hpc_gui/plugins/validator.py                |  99 +++++-
 src/hpc_gui/services/command_history_store.py   |   6 +-
 src/hpc_gui/services/files_ssh.py               |  20 +-
 src/hpc_gui/services/output_follower.py         |   5 +
 src/hpc_gui/services/shortcut_preferences.py    |  36 +-
 src/hpc_gui/services/slurm_models.py            |  81 +++++
 src/hpc_gui/ui/dialogs/plugin_manager_dialog.py |   8 +
 src/hpc_gui/wx_editor_view.py                   | 306 ++++++++++++++++-
 src/hpc_gui/wx_jobs.py                          | 315 +++++++++++++++--
 src/hpc_gui/wx_plugins.py                       | 284 +++++++++++++++-
 src/hpc_gui/wx_plugins_view.py                  | 433 +++++++++++++++++++++---
 src/hpc_gui/wx_settings.py                      | 338 +++++++++++++++++-
 src/hpc_gui/wx_settings_view.py                 |  32 +-
 src/hpc_gui/wx_shell.py                         |  63 +++-
 26 files changed, 2078 insertions(+), 146 deletions(-)
===DIFF CHECK===
warning: in the working copy of 'src/hpc_gui/core/wx_errors.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/command_history_store.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/shortcut_preferences.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
===W38 SCOPE DIFF STAT===
 M src/hpc_gui/core/ui_errors.py
 M src/hpc_gui/core/wx_errors.py
 M src/hpc_gui/services/command_history_store.py
 M src/hpc_gui/services/shortcut_preferences.py
?? tests/test_w38_migration_secrets.py
===UNTRACKED TEST EXISTS===
-rw-r--r-- 1 mskomek 197121 12996 Sep 24 21:26 tests/test_w38_migration_secrets.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff HEAD -- src/hpc_gui/core/ui_errors.py src/hpc_gui/core/wx_errors.py src/hpc_gui/services/shortcut_preferences.py src/hpc_gui/services/command_history_store.py 2>&1 | head -n 300
warning: in the working copy of 'src/hpc_gui/core/wx_errors.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/command_history_store.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/shortcut_preferences.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/src/hpc_gui/core/ui_errors.py b/src/hpc_gui/core/ui_errors.py
index fb838815..fa95c59b 100644
--- a/src/hpc_gui/core/ui_errors.py
+++ b/src/hpc_gui/core/ui_errors.py
@@ -63,7 +63,13 @@ def describe_connection_error(exc: BaseException, fallback: str = "") -> str:
 
     explanation = t(key)
     if text and text not in explanation:
-        explanation += f"\n\n{t('common.technical_detail')}: {text}"
+        try:
+            from hpc_gui.core.log_redaction import redact_text
+
+            safe_text = redact_text(text)
+        except Exception:
+            safe_text = text
+        explanation += f"\n\n{t('common.technical_detail')}: {safe_text}"
     return explanation
 
 
diff --git a/src/hpc_gui/core/wx_errors.py b/src/hpc_gui/core/wx_errors.py
index f0618fd5..769e82e9 100644
--- a/src/hpc_gui/core/wx_errors.py
+++ b/src/hpc_gui/core/wx_errors.py
@@ -51,6 +51,12 @@ def report_wx_action_error(
     text = f"{message}\n\n{label}: {err_id}\n{hint}"
     detail = (technical_detail or "").strip()
     if detail and detail not in text:
+        try:
+            from hpc_gui.core.log_redaction import redact_text
+
+            detail = redact_text(detail)
+        except Exception:
+            pass
         text += f"\n\n{t('common.technical_detail')}: {detail}"
 
     try:
diff --git a/src/hpc_gui/services/command_history_store.py b/src/hpc_gui/services/command_history_store.py
index 2da3a07f..83740f88 100644
--- a/src/hpc_gui/services/command_history_store.py
+++ b/src/hpc_gui/services/command_history_store.py
@@ -30,8 +30,10 @@ _SENSITIVE_PATTERNS = [
     r"authorization\s*:\s*bearer\s+",
     # Tools that embed passwords
     r"\bsshpass\b",
-    # PuTTY/Plink password arg (rare, but don't store)
-    r"\b(-pw|--pw)\b",
+    # PuTTY/Plink password arg (rare, but don't store). Leading hyphen is a
+    # non-word char, so \b before it never matches after whitespace; use a
+    # whitespace/start boundary instead (W38 secret-boundary hardening).
+    r"(?<!\S)(?:-pw|--pw|--password)\b",
 ]
 
 
diff --git a/src/hpc_gui/services/shortcut_preferences.py b/src/hpc_gui/services/shortcut_preferences.py
index fce35729..899815e3 100644
--- a/src/hpc_gui/services/shortcut_preferences.py
+++ b/src/hpc_gui/services/shortcut_preferences.py
@@ -35,16 +35,32 @@ def active_binding(command_id: str, platform: str, settings: dict[str, Any] | No
 
 
 class ShortcutPreferences:
+    #: Top-level keys owned by this module. Anything else is a future/
+    #: unknown key that migration must preserve byte-for-byte
+    #: (HPC-W09-MIG-003 / HPC-W09-TODO-MIGRATION-UNKNOWN-001).
+    _KNOWN_TOP_LEVEL_KEYS = frozenset({"version", "platform", "keymap_mode", "bindings"})
+
     def __init__(self, platform: str, settings: dict[str, Any] | None = None) -> None:
         self.platform = platform
         stored = (settings if settings is not None else load_settings()).get(SETTINGS_KEY, {})
         stored = stored if isinstance(stored, dict) else {}
         mode = stored.get("keymap_mode", "standard")
         self._keymap_mode = mode if mode in KEYMAP_MODES else "standard"
+        # Preserve unknown/future top-level keys (newer-version safety):
+        # they survive round-trips even though this version does not interpret
+        # them. Idempotent: re-loading an already-migrated value is a no-op.
+        self._unknown_top_level: dict[str, Any] = {
+            key: value
+            for key, value in stored.items()
+            if key not in self._KNOWN_TOP_LEVEL_KEYS
+        }
         defaults = bindings_for("windows" if self._keymap_mode == "legacy" else platform)
         self._defaults = tuple(defaults)
         self._bindings = list(defaults)
         custom = stored.get("bindings", stored if "version" not in stored else {})
+        # Unknown/future command ids (bindings for commands this version does
+        # not know) must survive migration instead of being dropped.
+        self._unknown_commands: dict[str, Any] = {}
         if isinstance(custom, dict):
             self._bindings = [item for item in defaults if item.command_id not in custom]
             for command_id, value in custom.items():
@@ -52,6 +68,14 @@ class ShortcutPreferences:
                     template = next((item for item in defaults if item.command_id == command_id), None)
                     if template is not None:
                         self._bindings.extend(KeyBinding(command_id, str(binding), template.context) for binding in value if str(binding).strip())
+                    else:
+                        # Future command: keep the raw binding list verbatim.
+                        kept = [str(binding) for binding in value if str(binding).strip()]
+                        if kept:
+                            self._unknown_commands[str(command_id)] = kept
+                elif command_id not in {item.command_id for item in defaults}:
+                    # Non-list future payload: preserve verbatim.
+                    self._unknown_commands[str(command_id)] = value
 
     def bindings(self) -> tuple[KeyBinding, ...]:
         return tuple(self._bindings)
@@ -97,7 +121,17 @@ class ShortcutPreferences:
         grouped: dict[str, list[str]] = {}
         for item in self._bindings:
             grouped.setdefault(item.command_id, []).append(item.binding)
-        return {"version": SCHEMA_VERSION, "platform": self.platform, "keymap_mode": self._keymap_mode, "bindings": grouped}
+        # Re-attach preserved future/unknown command bindings verbatim so a
+        # newer-version keymap round-trips without data loss.
+        for command_id, value in self._unknown_commands.items():
+            if command_id not in grouped:
+                grouped[command_id] = value if isinstance(value, list) else value
+        payload: dict[str, Any] = {"version": SCHEMA_VERSION, "platform": self.platform, "keymap_mode": self._keymap_mode, "bindings": grouped}
+        # Re-attach preserved unknown top-level keys last (never overwrite
+        # owned keys even if a future version reuses the name differently).
+        for key, value in self._unknown_top_level.items():
+            payload.setdefault(key, value)
+        return payload
 
     def persist(self) -> dict[str, Any]:
         value = self.serialize()
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read tests/test_w38_migration_secrets.py 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ /d/Python/Python312/python -m pytest tests/test_w38_migration_secrets.py -q 2>&1 | tail -n 10; echo "EXIT:$?"
............                                                             [100%]
12 passed in 0.71s
EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ /d/Python/Python312/python -m pytest tests/test_w38_migration_secrets.py tests/test_wx_migration.py tests/test_log_redaction.py tests/test_secret_store.py tests/test_profile_exchange.py tests/test_config_storage_atomic.py tests/test_diagnostics.py tests/test_crash_logging_filter.py tests/test_debug_telemetry.py tests/test_w37_settings_persistence.py -q 2>&1 | tail -n 10; echo "EXIT:$?"
...................................................................      [100%]
67 passed in 5.25s
EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ /d/Python/Python312/python -m pytest tests/test_w38_migration_secrets.py tests/test_wx_migration.py tests/test_log_redaction.py tests/test_secret_store.py tests/test_profile_exchange.py tests/test_config_storage_atomic.py tests/test_diagnostics.py tests/test_crash_logging_filter.py tests/test_debug_telemetry.py tests/test_w37_settings_persistence.py --collect-only -q 2>&1 | tail -n 5; echo "==="; /d/Python/Python312/python -m pytest tests/test_w38_migration_secrets.py tests/test_wx_migration.py tests/test_log_redaction.py tests/test_secret_store.py tests/test_profile_exchange.py tests/test_config_storage_atomic.py tests/test_diagnostics.py tests/test_crash_logging_filter.py tests/test_debug_telemetry.py tests/test_w37_settings_persistence.py -q --co 2>&1 | grep -c "::"; echo "===per file==="; for f in test_w38_migration_secrets test_wx_migration test_log_redaction test_secret_store test_profile_exchange test_config_storage_atomic test_diagnostics test_crash_logging_filter test_debug_telemetry test_w37_settings_persistence; do echo -n "$f: "; /d/Python/Python312/python -m pytest tests/$f.py --collect-only -q 2>&1 | tail -n 1; done
tests/test_w37_settings_persistence.py::test_w37_settings_logic_lives_behind_services_not_handlers
tests/test_w37_settings_persistence.py::test_w37_wx_apply_event_persists_to_storage
tests/test_w37_settings_persistence.py::test_w37_wx_failed_persist_shows_error_never_false_ok

67 tests collected in 4.16s
===
67
===per file===
test_w38_migration_secrets: 12 tests collected in 0.29s
test_wx_migration: 4 tests collected in 0.26s
test_log_redaction: 5 tests collected in 0.27s
test_secret_store: 2 tests collected in 0.27s
test_profile_exchange: 4 tests collected in 0.29s
test_config_storage_atomic: 2 tests collected in 0.65s
test_diagnostics: 2 tests collected in 0.51s
test_crash_logging_filter: 4 tests collected in 0.52s
test_debug_telemetry: 1 test collected in 0.63s
test_w37_settings_persistence: 31 tests collected in 0.64s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ echo "===SKIP/XFAIL in new test==="; grep -rn "skip\|xfail" tests/test_w38_migration_secrets.py 2>&1; echo "(none above = clean)"; echo "===SECRETS SCAN W38 diff==="; git diff HEAD -- src/hpc_gui/core/ui_errors.py src/hpc_gui/core/wx_errors.py src/hpc_gui/services/shortcut_preferences.py src/hpc_gui/services/command_history_store.py | grep -in "SuperSecret\|abc123\|private.*key.*BEGIN\|password.*=" | head -n 20; echo "(only comments/code patterns expected)"; echo "===REDACT MODULE==="; /d/Python/Python312/python -c "from hpc_gui.core.log_redaction import redact_text; print(redact_text('pw password=SuperSecret123 token=abc123')); print(redact_text('ssh user@h -pw SuperSecret123'))" 2>&1; echo "===HISTORY REGEX==="; /d/Python/Python312/python -c "from hpc_gui.services.command_history_store import is_sensitive_command; print(is_sensitive_command('ssh user@host -pw SuperSecret123')); print(is_sensitive_command('echo hello'))" 2>&1; echo "===SHORTCUT EXISTING TESTS==="; ls tests/ | grep -i shortcut 2>&1
===SKIP/XFAIL in new test===
318:    wx = pytest.importorskip("wx")
(none above = clean)
===SECRETS SCAN W38 diff===
warning: in the working copy of 'src/hpc_gui/core/wx_errors.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/command_history_store.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/shortcut_preferences.py', LF will be replaced by CRLF the next time Git touches it
(only comments/code patterns expected)
===REDACT MODULE===
pw password=<redacted> token=<redacted>
ssh user@h -pw <redacted>
===HISTORY REGEX===
True
False
===SHORTCUT EXISTING TESTS===
test_editor_shortcut_safety.py
test_help_shortcut_reference.py
test_shortcut_preferences.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ /d/Python/Python312/python -m pytest tests/test_shortcut_preferences.py tests/test_editor_shortcut_safety.py -q 2>&1 | tail -n 5; echo "EXIT:$?"; echo "===QT show_exception path==="; grep -n "show_exception\|def describe_connection_error" src/hpc_gui/core/ui_errors.py | head -n 10; echo "===wx MessageBox real test confirm==="; /d/Python/Python312/python -m pytest tests/test_w38_migration_secrets.py::test_w38_wx_redacted_error_dialog_shows_no_secret -q 2>&1 | tail -n 3
......                                                                   [100%]
6 passed in 2.00s
EXIT:0
===QT show_exception path===
13:def describe_connection_error(exc: BaseException, fallback: str = "") -> str:
76:def show_exception(
===wx MessageBox real test confirm===
.                                                                        [100%]
1 passed in 0.74s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ sed -n '76,110p' src/hpc_gui/core/ui_errors.py; echo "===GIT HEAD==="; git rev-parse HEAD; echo "===W38 REPORT SHAs==="; grep -n "SHA\|HEAD\|Baseline" docs/wave-reports/v2/opencode/W38_WAVE_REPORT.md | head -n 10
def show_exception(
    parent,
    *,
    title: Optional[str] = None,
    user_message: Optional[str] = None,
    exc: Optional[BaseException] = None,
    area: str = "GEN",
) -> None:
    try:
        from PySide6.QtWidgets import QMessageBox
    except Exception:
        return

    if exc is not None:
        err_id = log_exception_with_id(area, exc)
    else:
        err_id = new_error_id(area)

    ttl = title or t("common.error")
    label = t("common.error_code")
    hint = t("common.error_code_hint")
    msg = (user_message or t("common.error")) + f"\n\n{label}: {err_id}\n{hint}"
    QMessageBox.critical(parent, ttl, msg)
===GIT HEAD===
c8293d3ca309526ed250c794c3b294f7c54ef369
===W38 REPORT SHAs===
8:Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
9:Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369
10:Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
26:## Baseline capture
241:- Baseline/HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 + W38 scope working-tree diff (4 source files + tests/test_w38_migration_secrets.py)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
AC_WAVE_BRIDGE_STDOUT_BEGIN
Auditing W38 — loading the canonical skill and wave truth.
W38 spec mapped — now hunting for its implementation evidence.
Core tests green — now digging into the broader evidence and secret handling.
W38 independent audit — fresh context, read-only for product code, no repairs performed.

**Scope verified:** `waves/pending/W38.md` (execution, 23 source + 11 TODO owned IDs), HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369` matches wave-report baseline/HEAD. W38 scope diff is exactly 4 modified source files (`core/ui_errors.py`, `core/wx_errors.py`, `services/shortcut_preferences.py`, `services/command_history_store.py`) + 1 new untracked test (`tests/test_w38_migration_secrets.py`, 12 tests). No existing tests modified. `git diff --check` clean (only LF/CRLF advisories). No secrets in owned diff. Unrelated dirty files from parallel cohort preserved untouched.

**Fix verification (code inspection, no product edits):**
- FIX-A (DEF-W38-001, secret redaction): both UI-error construction points route through `log_redaction.redact_text` with fail-open-to-raw only if the redactor itself raises. Qt `show_exception` shows only user_message + id (no raw exc) — safe. Direct probe: `redact_text('password=SuperSecret123 token=abc123')` → redacted. Distinct root cause from FIX-B.
- FIX-B (DEF-W38-002, unknown/future keymap preservation): `_KNOWN_TOP_LEVEL_KEYS` + `_unknown_top_level` / `_unknown_commands` capture at load, verbatim re-attach in `serialize()` via `setdefault`/merge (owned keys win), `persist()` inherits. Idempotent by construction.
- FIX-C (DEF-W38-003, history `-pw` regex): `(?<!\S)(?:-pw|--pw|--password)\b` replaces `\b(-pw|--pw)\b` which could never match after whitespace. Probe: `is_sensitive_command('ssh user@host -pw SuperSecret123')` → True, benign → False.

**Test evidence (audit-time re-execution, Windows native, wx present):**
- Narrow: `tests/test_w38_migration_secrets.py` → 12 passed, exit 0 (matches report).
- Broad slice (w38 + wx_migration + log_redaction + secret_store + profile_exchange + config_storage_atomic + diagnostics + crash_logging_filter + debug_telemetry + w37_settings_persistence) → 67 passed, exit 0. Report claimed 66; recount is 12+4+5+2+4+2+2+4+1+31 = 67. Drift is +1 green (W37 suite now 31), strictly stronger — documentation drift only, not a product defect. Audit binds to the audit-time 67.
- Existing shortcut suites (`test_shortcut_preferences.py` + `test_editor_shortcut_safety.py`) → 6 passed, no regression from FIX-B.
- GUI FULL `test_w38_wx_redacted_error_dialog_shows_no_secret` → passed at audit time via real wx runtime (wx.App + Frame + real `report_wx_action_error`, MessageBox capture monkeypatched for display isolation only). Redaction `<redacted>` present, raw secrets absent.
- No skips/xfails added or weakened (only `pytest.importorskip("wx")`, which executed since wx is installed).

**Requirement/evidence checks:** all 23 source + 11 TODO IDs dispositioned VERIFIED with matching test/evidence pointers; FIX-A vs FIX-B independent (different defect IDs, surfaces, root causes, regression tests); FIX-C extra hardening not double-counted — two-fix gate satisfied. Contradiction scan clean except the 66→67 count note above. STOP conditions none triggered. Sensitivity is structurally evident from the diffs (redact call, unknown re-attach, boundary fix) and was demonstrated by the worker's fault runs; auditor did not mutate product code to re-fault per read-only role.

**Verdict: PASS.** Binds to HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369` + W38 scope working-tree diff + audit-time 12/67 green. Lifecycle close remains controller-owned.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
