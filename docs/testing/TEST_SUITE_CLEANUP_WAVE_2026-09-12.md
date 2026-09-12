# Test Suite Cleanup Wave — 2026-09-12

Status: DEFECT_FOUND (Packet F stopped; unrelated packets continue)

Frozen baseline: 12ce79935bf076e1062c57dc7dbd148bad2bfae1

Remediation baseline: 54f7376f3e3e1fccd672f121e33b68d2e8df2652
Remediation collection: 2,678 nodes (five added, zero removed from frozen)

Current packet: I
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

### E. Weak updater lifecycle tests — DONE

Rewrote the three updater nodes in `tests/test_wx_updater_spec.py` without production changes. Cancellation uses the real wx cancel event and download worker with the downloader mocked at its external seam; a late successful return after cancel must not verify or expose an installable artifact, and installer/splash seams remain uncalled. Removing the worker cancellation guard makes `_artifact_verified is False` fail. Close behavior dispatches the real dialog close event, exercises both veto and accept paths, and checks visibility, state, and worker ownership. Late progress/completion callbacks are queued through real `wx.CallAfter`, then processed after dialog destruction; closed state and UI model values remain unchanged. All three nodes passed alone; the updater/migration neighborhood passed **63 tests**. No test nodeids changed and Packet C RATCHET remains the gate.

### F. GUI truthfulness — DEFECT_FOUND

Both terminal fallback tests now instantiate their actual wx fallback paths. The WebView diagnostic fallback is visible, reports non-parity, and exposes enabled diagnostic controls; the public composition fallback is a visible TextCtrl, renders output, and clears through its real button event. The Files toolbar localization test creates a real remote-files panel and confirms its visible Download and Upload controls change to Turkish. The Wave78 no-selection/status node continues to prove there is no selected job while refreshing provider status; that node and both fallback tests plus the Files test passed together (4 passed).

The Outputs localization test was rewritten to select a real job, create visible stdout/stderr tabs, and switch the live UI from English to Turkish. It **fails truthfully**: the page remains `Standard Output` while the expected translation is `Standart Çıktı`. Exact command: `python -m pytest tests/test_wave80_files_outputs.py::TestWave80Audit::test_runtime_language_switch_updates_outputs -q -p no:cacheprovider --tb=short` (exit 1, 1 failed). This is new GUI evidence; it is not a reproduced Phase-1 failure. `src/hpc_gui/wx_jobs.py:2297` reuses the cached `ch.label` from `state["resolved_channels"]` when refreshing labels, so existing channel labels do not follow the current language. No production code was changed. The truthful failing test is retained and committed; Packet F stopped here with `DEFECT_FOUND`. Independent Packets G–O may proceed under the execution prompt, and overall status remains `DEFECT_FOUND`.

Renamed test node: `tests/test_wave80_files_outputs.py::TestFilesBehavior::test_context_menu_labels_localized` → `tests/test_wave80_files_outputs.py::TestFilesBehavior::test_files_toolbar_visible_labels_localized`. This is a change from translation-string assertions to actual visible Files toolbar behavior, not an equivalent context-menu test.

### G. Historical/Wave ownership review — DONE

See [WAVE_OWNERSHIP_REVIEW_G.md](WAVE_OWNERSHIP_REVIEW_G.md) for module-by-module behavior ownership, static versus runtime evidence, and retention rationale. All reviewed owners were retained; no node delta. Wave names alone do not establish obsolete ownership; Waves78–80 are collected though the migration ledger ends at Wave77.

### H. Settings/config isolation — DONE

Re-audited `tests/test_connection_advanced_settings.py`, `tests/test_config_storage_atomic.py`, `tests/test_profile_storage_areas.py`, and `tests/test_profile_patch_preservation.py`. The settings-dialog hang setup now returns a concrete `Path(temp_dir)` from `Path.home` inside a temporary-directory context; the bounded isolated run passed in 0.23 seconds (2.19 seconds including the external timeout wrapper). There is no unconfigured `MagicMock` filesystem result in this node. Atomic config tests use `tmp_path`, assert temporary-file cleanup on success and failure, and preserve the previous config on replacement failure. Profile patch storage uses a concrete temporary home and registers cleanup; storage-area tests are pure model checks. No extra negative/cleanup test was needed. All four modules passed: **40 passed**. No Packet H test or production files changed.

### I. Source-text behavior rewrites — DONE

Reviewed the 69 archived source-reading call sites across 59 unique test nodes. Runtime evidence now covers the About dialog, updater splash/worker ordering, installer handoff ordering, live F1 Help action, hostile scheduler input, macOS signing cleanup/no-secret output, SSH file-command quoting, and Slurm `sbatch` quoting. The connection secret-wipe check retains its runtime assertion beside its static no-Qt architecture claim. D2 SFTP byte preservation was replaced with the behavioral owner in Packet D. Genuine architecture, security, plugin-contract, and static UI-wiring checks remain explicitly classified as audit/contract evidence; fixture, catalog, and tooling-output reads remain inputs to their respective tests. The complete 59-node disposition is in [SOURCE_TEXT_REVIEW_I.md](SOURCE_TEXT_REVIEW_I.md).

Removed `tests/test_about_dialog.py::test_about_instantiates_offscreen`, whose construction/version checks are subsumed by the strengthened runtime About test. Renamed `tests/test_macos_signing.py::test_signing_source_has_cleanup_and_no_secret_echo` to `test_signing_cleans_keychain_without_echoing_secrets`; this is a runtime behavior owner, not an equivalent static test. The other rewritten owners kept their nodeids. No production code changed. Focused validation passed: 44 tests, Ruff, and `git diff --check`.

### J. Resource/concurrency cleanup — DONE

See [RESOURCE_CONCURRENCY_REVIEW_J.md](RESOURCE_CONCURRENCY_REVIEW_J.md) for the node-by-node review and evidence. The SFTP ownership check now exercises `SFTPChannelManager`; selected-job listener concurrency verifies every ordered snapshot and unsubscribe boundary; FTP overlap records distinct live connections; dialog cancellation dispatches through the real controller worker and verifies backend cleanup; and the real wire cancellation test triggers from observed progress rather than a polling watcher. Five flaky/polluted skips were removed and their behaviors now pass. The wx Jobs blocked-read stress case uses the normal coalescing path and records worker ownership; the old direct test-double-only node was removed after exact selector-reference search. Terminal reconnect now proves each old subscriber and the final active subscriber are released. The pause/resume stress test was corrected to match the current visible Pause All behavior. No production code changed.

Removed `tests/test_wx_jobs_stress.py::test_wx_jobs_stress_backend_workers_and_reads_are_bounded`. Renamed `tests/test_wx_jobs_behavior.py::test_wx_job_output_pause_keeps_refreshing_but_stops_live_follow` to `test_wx_job_output_pause_freezes_and_resume_updates_output`; it is classified `gui`. There are no other Packet J node changes. Focused suites, collection (2,684 nodes, zero errors), taxonomy RATCHET, Ruff, and `git diff --check` passed.

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
