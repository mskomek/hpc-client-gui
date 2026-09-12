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

### K. Reporting/E2E reclassification — DONE

See [REPORTING_E2E_REVIEW_K.md](REPORTING_E2E_REVIEW_K.md) for the node ownership and evidence boundaries. The plugin user lifecycle is E2E; screenshot, reproducibility-bundle, and capability report validators are reporting; the manifest generator is release-specific; Wave 79 tests are split among contract, unit, and integration according to the exercised boundary. The packaged smoke node is an artifact-dependent runtime smoke, not a report-only test. It was not executed because the runner would overwrite the existing Windows FAIL evidence while no discoverable artifact is present. No nodes were added, removed, or renamed.

### L. Legacy static/migration ownership review — DONE

See [LEGACY_MIGRATION_REVIEW_L.md](LEGACY_MIGRATION_REVIEW_L.md). Qt remains present in production and wx remains an actively exercised optional GUI. The suites are retained by behavior; one test-local writer that overwrote terminal evidence with hard-coded claims was removed, the Wave 10 navigation persistence node was strengthened without changing its nodeid, and Wave 2 wx teardown now drains/asserts window cleanup. The migration ledger remains PARTIAL; no runtime or platform evidence was upgraded.

### M. Full-suite classification — DONE

The dirty governance worktree now collects **2,685** nodes with **zero-primary = 0** and **multi-primary = 0**. Classifications are real pytest markers read from `item.iter_markers()`; mixed modules use node-level marks, and class marks are limited to the Wave 2 local-file behavior classes that share one owner. The local report remains non-mutating and emits JSON.

`python scripts/check_test_taxonomy.py --mode enforce` passed: all collected items have exactly one primary, and the configured pytest taxonomy registry matches the checker registry. `python scripts/check_test_taxonomy.py --mode ratchet --baseline audit/archive/54f7376f/test-suite-baseline/taxonomy-ratchet.json` also passed: 12 nodes added, 14 removed since the frozen Packet C marker snapshot, no new zero-primary nodes, no lost prior classifications, and no multi-primary nodes. The additions/removals are intentional Packet D–M behavior-owner changes and are enumerated in the final report; they include the truthful Packet F failing Outputs localization test and remove the hard-coded terminal evidence writer. The two new enforce-mode checker tests are marked `audit`.

Current primary counts: unit 634; integration 294; GUI 899; E2E 1; runtime smoke 36; contract 576; audit 100; reporting 22; release 123. RATCHET remains a developer check and is not wired into automatic CI.

### N. Marker-based lane review — DONE; no selector changes

Exact current selector/candidate node sets are recorded in [MARKER_LANE_REVIEW_N.md](MARKER_LANE_REVIEW_N.md) and `audit/archive/ea1002bc/test-suite-baseline/marker-lane-reconciliation.json`. The release suite's existing `-m "not packaging"` selection remains exact. Removing the packaging lane's file constraint would add the artifact-dependent wx smoke node; category unions for compat/CLI/SSH and the global contract marker do not match their existing file-owned lanes. The macOS and Windows qualifiers currently select no tests, so those selectors cannot migrate by markers. No selector or workflow changed; automatic CI remains disabled and the archived workflow remains archival.

### O. Reporting integration + closeout — NOT STARTED

After marker review and a separately authorized CI decision, integrate the taxonomy report where appropriate, verify JSON/report ownership with tests/test_gui_audit_screenshots.py and tests/test_reproducibility_bundle.py, compare all baseline nodeids, record the final mapping and remaining exceptions, then close the Wave. This packet does not authorize full-suite/CI integration now.
