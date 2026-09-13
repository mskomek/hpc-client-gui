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

### M. Full-suite classification — PARTIAL (structural ENFORCE passes)

The dirty governance worktree now collects **2,685** nodes with **zero-primary = 0** and **multi-primary = 0**. Classifications are real pytest markers read from `item.iter_markers()`; mixed modules use node-level marks, and class marks are limited to the Wave 2 local-file behavior classes that share one owner. The local report remains non-mutating and emits JSON.

`python scripts/check_test_taxonomy.py --mode enforce` passed: all collected items have exactly one primary, and the configured pytest taxonomy registry matches the checker registry. `python scripts/check_test_taxonomy.py --mode ratchet --baseline audit/archive/54f7376f/test-suite-baseline/taxonomy-ratchet.json` also passed: 12 nodes added, 14 removed since the frozen Packet C marker snapshot, no new zero-primary nodes, no lost prior classifications, and no multi-primary nodes. The additions/removals are intentional Packet D–M behavior-owner changes and are enumerated in the final report; they include the truthful Packet F failing Outputs localization test and remove the hard-coded terminal evidence writer. The two new enforce-mode checker tests are marked `audit`.

Current primary counts: unit 634; integration 294; GUI 899; E2E 1; runtime smoke 36; contract 576; audit 100; reporting 22; release 123. RATCHET remains a developer check and is not wired into automatic CI.

The structural zero/multi-primary debt is cleared, but semantic review is not complete: most remaining legacy nodes were initially decorated from the archived per-node heuristic candidate field, with source-based corrections in selected mixed/high-risk modules. The archive explicitly labels those candidates heuristic-only. ENFORCE proves marker cardinality and registry consistency, not that every legacy category matches its exercised behavior. Do not treat Packet M or the overall program as DONE until the remaining category-fidelity review is completed.

### Continuation on governance v3

The continuation uses remediation base `87e1e709a879b52300a5eec660bfae04e700ee29` and governance branch `test-suite-governance-20260912-v3`; the original `develop` worktree remains preserved. Current collection is 2,676 nodes after removing one stdlib-only false owner, `tests/test_wave2_directories_local_files.py::TestCRUDActions::test_create_file_unicode`; unicode file enumeration and directory creation remain owned by the production-backed listing and folder tests. Its body only called `Path.write_text()` and asserted `Path.exists()`.

The Wave 78 GUI suite now dispatches real control events and checks visible state for the unsupported-provider, raw-details, raw-accounting, and stale-selection cases; all 16 nodes passed. Wave 80’s 45-node Files/Outputs module passed with per-test temporary localization storage. The confirmed Outputs localization defect was fixed in the authorized remediation and the regression test checks both English→Turkish and Turkish→English while preserving selected channel and output content.

During Wave 2 semantic review, `test_list_entries_permission_error` was changed from a no-error normal listing into a deterministic `Path.stat()` denial case. It now fails because `LocalBrowserModel.list_entries()` calls `item.is_dir()` in its error handler, which raises the same `PermissionError`. This is a newly confirmed product defect in `src/hpc_gui/wx_local_files.py`; the truthful failing test is retained and production code was not changed. It does not stop unrelated taxonomy review, but it prevents an overall DONE result until separately authorized.

The Wave 2 wx parity test `test_rename_preserves_selection` was also rewritten to dispatch the actual local context-menu rename and assert selection on the refreshed wx row. The new test fails because the renamed row is not selected. This is a second confirmed GUI product defect in the local-file refresh path; the node is marked `gui`/`regression`/`wx` and retained without a production change. The old `test_forward_button_disabled_when_no_forward` silently passed because the local toolbar has no Forward button; it was removed while model-level forward navigation remains covered by Wave 2 model tests. `test_up_button_disabled_at_root`, whose conditional never reached a root path, now verifies the supported visible Parent action from a nested folder; the button’s root-enabled state is not treated as a required product defect without an independent specification.

Wave 5 review removed five nodes that tested only Python string or `shlex.quote` behavior, or whose Unicode job-name assertion only checked the supplied job ID. The production-backed directive test now verifies Unicode comments survive `set_directive`; the SSH backend test owns shell quoting; parsed job names remain covered by `parse_squeue` and `parse_job_name` owners. `test_parse_squeue_unicode_name` now checks exact parsed fields, `test_output_metadata_unicode` exercises `JobTrackingController.set_output_metadata`, and the composed script case is classified `integration`. The Wave 5 module passed 18 tests; at that checkpoint collection was 2,671 nodes with 733 reviewed rows and no nodeid/marker mismatch.

Wave 10 review removed three local-filesystem roundtrips that only exercised `pathlib`, and removed `test_no_lossy_user_path_conversion`, an exact subset of the broader `test_no_errors_ignore_on_user_paths` source audit. The application-backed Unicode filesystem behavior remains in Wave 2 service/model tests. `test_no_p0_unicode_bugs` was renamed to `test_critical_paths_declare_utf8_handling` to describe its actual static assertion, while favorites persistence is `integration` and the Slurm directive boundary is `contract`. Wave 10 passed 13 tests.

### N. Marker-based lane review — DONE; no selector changes

Exact current selector/candidate node sets are recorded in [MARKER_LANE_REVIEW_N.md](MARKER_LANE_REVIEW_N.md) and `audit/archive/ea1002bc/test-suite-baseline/marker-lane-reconciliation.json`. The release suite's existing `-m "not packaging"` selection remains exact. Removing the packaging lane's file constraint would add the artifact-dependent wx smoke node; category unions for compat/CLI/SSH and the global contract marker do not match their existing file-owned lanes. The macOS and Windows qualifiers currently select no tests, so those selectors cannot migrate by markers. No selector or workflow changed; automatic CI remains disabled and the archived workflow remains archival.

### O. Reporting integration + closeout — NOT STARTED

After semantic marker review, integrate taxonomy counts and test outcomes into reporting without changing automatic CI, verify JSON/report ownership with tests/test_gui_audit_screenshots.py and tests/test_reproducibility_bundle.py, compare all baseline nodeids, record the final mapping and remaining exceptions, then close the Wave.

### Continuation revalidation on v3 (2026-09-13)

The current test tree now collects **2,666 nodes**. Semantic review is now **1,521/2,666** evidence-backed nodes, leaving 1,145 unreviewed. Packet M is still partial; structural taxonomy remains zero-primary 0 and multi-primary 0. The latest checker run reports no marker mismatches. No heuristic-only entries were promoted.

Fresh exact node-list comparison: frozen audit **2,673 → 2,666** (63 added, 70 removed); previous remediation SHA `54f7376f` **2,678 → 2,666** (58 added, 70 removed); archived new remediation SHA `87e1e709` **2,679 → 2,666** (56 added, 69 removed); prior governance snapshot `2b4c675f` **2,685 → 2,666** (38 added, 57 removed). The archived remediation README resolves the count distinction: 2,678 is the previous remediation base, while the new remediation baseline is 2,679. The lower current count comes from reviewed behavior-owner removals; additions and removals are exact nodeid set differences, not presumed renames.

All 17 Wave 6 plugin/provider Unicode nodes were read against their actual test bodies and reviewed: model/validator/provider/UI schema boundaries are contracts; the composed manifest/profile/settings path is integration. The module passed **17 tests**. The remote wx file-action module now restores the global language and shared clipboard in its fixture, drains deferred window destruction, and qualifies its worker-thread assertion as concurrency; all 28 nodes were semantically reviewed and **28 passed**. The terminal behavioral file now distinguishes adapter integration, bridge contracts, buffer unit behavior, and visible GUI/lifecycle evidence; all 19 nodes were reviewed and **19 passed**.

Revalidation of previous failure reports on this branch:

| Node or group | Current result | Classification |
|---|---|---|
| Wave 3 directory type language node | Isolated node and 44-node Wave 3/file-action bundle passed | Resolved by locale restoration in the test module |
| Two remote action-policy matrix cases | Both passed; action-policy and Wave 3 bundle passed 44 tests | Resolved on the reconciled branch; no expectation weakening |
| Remote navigation/sort/provider-filter GUI node | Node passed; full 28-node module passed | Resolved on the reconciled branch; teardown warning also removed by draining deferred wx destruction |
| Shell completion/deduplication node | Passed alone | Resolved on the reconciled branch |
| 65A integrated stress | Passed in 214.57s with all measured invariants zero | Resolved; WebView2 emitted operation-aborted diagnostics during rapid close cycles, but process and assertions passed |
| Seven formerly reported embedded-terminal native nodes | Full embedded-terminal module passed 10/10 | Resolved on this branch; fallback-only compatibility tests do not establish packaged WebView parity |
| Terminal find-next/previous lifecycle node | Node passed; 19-node terminal behavioral module passed | Resolved on this run; prior native failure remains historical evidence, not a current failure |
| Separator lifecycle subprocess | Reproduced `subprocess.TimeoutExpired` at 30 seconds | Unresolved native wx timeout |
| wx shell P0 stress close callback | Repeatedly raised `RuntimeError` from `notebook.GetSelection()` after the Notebook was destroyed; run stopped after capturing repeated tracebacks | Confirmed product lifecycle defect in `wx_remote_files_view.py`; no production edit authorized |
| Local-files permission-error and wx rename-selection nodes | Previously reproduced on this same v3 branch and remain the two Wave 2 product defects | Confirmed product defects; retained truthful tests, no production edit |
| Outputs runtime language switch | Isolated node passed on this branch after the authorized fix | Resolved; the visible language-switch regression now passes |

Rebased duplicate cleanup was also revalidated: the D1/D2/D4/D5/D6/D7 owner bundle passed **189 tests**, and the D3 Wave 78/password-precedence GUI bundle passed **36 tests**. The three updater lifecycle tests passed **3/3**, actual terminal fallback passed **1/1**, and packaged-smoke reporting passed **1/1**. The packaged test validates fail-closed report construction only, not artifact runtime.

The 10-node terminal parity-evidence suite passed after its categories were corrected: nine nodes assert panel-to-bridge/SSH integration and one asserts the visible resize label. `test_unicode_round_trip` was renamed to `test_unicode_output_reaches_terminal_bridge` because it only sends output through the bridge and does not exercise input or rendered terminal output. All 19 terminal behavioral nodes and all 10 embedded-terminal compatibility nodes also pass; none of these results claims packaged WebView parity.

Packet J is therefore **PARTIAL**, not done: the separator timeout and wx shell callback defect remain open. Packet M remains partial until all nodes receive semantic review. Packet O has not started.


All 156 nodes in `tests/test_cli.py` now have body-based semantic evidence. Direct helper/diagnostic and isolated CLI branch checks are unit; real temporary configuration persistence and composed profile/scheduler command flows are integration; text/JSON shape, stage, Unicode-preservation, and serializer-parity checks are contract. Fake sessions and fake backends remain explicit test seams and do not count as runtime smoke. The CLI module passed **156 tests** after this classification update.


All 168 nodes in `tests/test_ftp_widget.py` have body-based evidence. Framework-neutral transfer/candidate helpers are unit; transfer mode/backend compositions are integration; API/construction compatibility is contract; GUI controls and user actions remain GUI. Backend-only parallelism and worker planning were separated from GUI-only claims. Concurrency is attached to tested ordering, cancellation, thread ownership, or duplicate-work prevention; performance appears only on bounded nonblocking-return assertions; resource appears on channel/QObject/worker cleanup. The module passed **168 tests** after taxonomy updates.


All 20 nodes in `tests/test_wave8_i18n_ui_ergonomics.py` are reviewed: catalog key/placeholder/resource checks are contract, direct translator calls are unit, loader-plus-catalog switching is integration, and source-text scans are audit rather than GUI. The module passed **20 tests**. Its tests now save and restore the process-global language after each case.

All 37 nodes in `tests/test_plugin_manager_ui.py` are reviewed. Visible dialog/card/status/filter behavior remains GUI; helper summaries and URL policy remain unit; i18n keys are contract. The module fixture restores the prior language. The rollback test now uses the real Qt global thread pool and verifies the activation callback runs off the GUI thread; the node and complete module passed, **1** and **37 tests** respectively. An attempted global deferred-delete flush at qapp teardown caused a Windows access violation; that flush was removed, and the module then completed cleanly.

All 48 nodes in `tests/test_plugin_installer.py` are reviewed. Contract/security input boundaries, isolated lookup/downloader units, stateful cache/install integration, and the service-level valid-install E2E path are distinct. The E2E case uses generated temporary package content and injected fetch responses, not a live registry. Resource qualifiers are limited to actual cache/staging/package retention or cleanup assertions. The module passed **48 tests**.

The 22-node `tests/test_plugin_security.py` suite now verifies actual persisted user-profile and system-template survival across plugin removal; it passed **22 tests**. The 12 security-hardening nodes now distinguish runtime storage checks, contract validators, narrow helper behavior, release handoff, and static trusted-loader policy; **10 passed and 2 were skipped** by POSIX/platform gates. The ineffective `create_plugin(` presence check was replaced by a static assertion that dynamic module execution exists only in the approved adapter and follows its identity/entrypoint checks.

The 33 synchronized-browsing, 25 output-channel resolver, 19 selected-job context, and 12 remote-entry helper nodes now have body-derived evidence. The synchronized suite uses real Qt widget state and events; path-mapping helpers are unit behavior, persisted setting normalization is contract, and remote-entry formatting/classification is unit behavior. The selected-job node names no longer claim to reject late callbacks when they only verify generation changes and metadata clearing. The combined four-module run passed **90 tests with 1 platform skip**.

All **29** wx transfer tests are semantically reviewed. Only visible progress and cancel controls remain GUI; the controller/backend transfer paths are integration with wx qualifiers. Session cleanup, cancel/shutdown ownership, and protocol-byte cases carry resource/concurrency qualifiers only where their assertions support them. The module passed **29 tests**. Full collection remains **2,666 nodes** with zero errors; taxonomy enforce still fails only because 1,257 node reviews remain incomplete (zero-primary 0, multi-primary 0, marker mismatches 0).

All **29** connection-profile nodes are now reviewed. Real panel/dialog state, validation, and button-event behavior is GUI; profile persistence, connection orchestration, and quota monitoring are integration; external profile/SSH and i18n shapes are contracts; pure duplication/quota lookup is unit; source policy is audit. Replaced the no-op cancel test with a real Cancel button event, split storage validation from visible list behavior, and added module-scoped language restoration. The module passed **29 tests**. Collection increased by one because the mixed storage test was split into a GUI list test and a separate contract test; no existing behavior owner was removed.

At the connection-profile checkpoint, collection was **2,667 tests with zero collection errors**. Taxonomy enforce had zero-primary 0, multi-primary 0, unknown/missing markers 0, and marker mismatches 0; semantic review remained incomplete.

All **26** wx file-browser tab tests are reviewed as GUI because they create real wx frames/notebooks, dispatch tab and mouse/context actions, and assert visible pages, paths, and listings. Seven late/stale worker-completion owners additionally carry concurrency. The module passed **26 tests** and emitted a non-failing Windows `UnregisterClass` warning about open windows during teardown; this remains a native cleanup observation for Packet J. Semantic review is **1,464/2,667** with 1,203 nodes still pending.

The connection-hardening module now has **19 reviewed nodes**: actual wx connection/Test Cluster/event paths are GUI, storage/password/host-key compositions are integration, language payload checks are contract, quota gating is unit, and password-dialog source policy is audit. Its provider-name source scan was removed because the same exact genericity assertion already has one canonical audit owner in `test_wx_connection_profiles.py`. The module passed **19 tests**; collection returns to **2,666 nodes** and semantic review is **1,483/2,666** at that checkpoint.

The 17 keyboard-parity tests use actual wx key events and visible or filesystem/backend results; the 16 file-action lifecycle tests verify asynchronous ownership/stale completion and frame cleanup; the 5 file-context tests dispatch real menus and assert English/Turkish labels. Both locale-mutating wx fixtures restore their previous language. The combined set passed **38 tests**. A Windows wxWidgets `UnregisterClass` warning still reports open windows after teardown; it is a non-failing native cleanup observation to resolve in Packet J. Current semantic review is **1,521/2,666**, with 1,145 nodes pending.

## 2026-09-13 continuation recovery

The preceding 1,521/2,666 value is a historical checkpoint only. During continuation, the uncommitted semantic-review JSON was accidentally truncated by a failed file-open call. No recoverable copy was found in Git refs, unreachable Git blobs, the sibling worktrees, or the temporary directory. The current review file was rebuilt against the exact current 2,666-node pytest collection; six evidence-bearing entries from HEAD were retained and 59 nodes were re-read and recorded. Current machine-readable evidence is therefore **65/2,666 reviewed**, with 2,601 unreviewed. Taxonomy enforce correctly remains FAIL for incomplete semantic review; zero-primary, multi-primary, unknown-marker, and marker-mismatch counts are all zero. Do not treat the prior 1,521 entries as currently evidenced.

The settings-dialog hang node passed alone in 0.28 seconds and its 20-node module passed. The SSH jump-host and profile-patch modules passed 39/39; the three-modules-together validation passed 59/59. Two SSH test names were clarified to match sequential channel reuse and partial resource close; neither is claimed as proof of simultaneous transfers or worker cancellation. Their exact old/new node mappings and evidence are in `audit/archive/87e1e709/test-suite-baseline/semantic-taxonomy-review.json`.

Since that recovery checkpoint, body-level review added `test_job_context.py` (20), `test_file_filter_registry.py` (22), `test_lint_engine.py` (28), `test_transfer_resume_semantics.py` (28), and `test_wx_jobs_files_outputs.py` (16). Their combined targeted suite passed **157/157**; the Jobs Files/Outputs wx module passed **16/16** in 24.50 seconds. Current review evidence is **179/2,666**; taxonomy enforce remains incomplete with zero-primary 0, multi-primary 0, unknown markers 0, and marker mismatches 0.

The current About dialog owner passed alone (1/1) and asserts visible version plus no external URL opening before the explicit button action. The updater ordering owner passed alone and the full updater module passed **18/18**; splash visibility is observed before the worker starts in a subprocess. All 10 official plugin-contract tests correctly skipped because `HPC_GUI_CONTRACT_REPO` is unset; each is now marked `artifact_dependent`, so this absence is visible in taxonomy and is not reported as a pass. Current semantic evidence is **229/2,666** (2,437 pending); taxonomy structure remains clean with zero marker mismatches.

## 2026-09-13 current failure recheck

On the current reconciled branch, `test_list_entries_permission_error` again fails because `Path.is_dir()` repeats the denied `stat()` and leaks `PermissionError`; `test_rename_preserves_selection` again fails because the renamed row is not selected after refresh. Both remain confirmed product defects and production code was left untouched. The separator lifecycle test again fails when its child wx process exceeds the test's 30-second timeout. The wx shell P0 stress node exceeded an outer 60-second subprocess bound without captured output; this is a current hang observation, while the earlier repeated destroyed-Notebook callback traceback remains the evidence for its separately confirmed callback defect. Neither native result is treated as a pass or blanket flakiness.

The continuation semantic-review recovery is now at **339/2,666**: the Wave 80 Files/Outputs module added 45 body-reviewed nodes and passed **45/45**. The latest `--mode enforce` confirms zero-primary 0, multi-primary 0, unknown/missing registered markers 0, and marker mismatches 0; it correctly remains FAIL because 2,327 nodes still lack valid evidence-backed review entries. The prior 1,521 count above remains only a historical checkpoint and was not restored.

The screenshot-audit module is now body-reviewed as **reporting** (5 nodes), distinct from GUI behavior and runtime evidence. Its four manifest/artifact integrity checks passed; `test_manifest_exists_and_commit_current` skipped because its recorded capture commit is historical for this governance HEAD. No pixel comparison or fresh screenshot capture is claimed. Semantic evidence is **344/2,666**; enforce remains incomplete only for 2,322 unreviewed nodes, with structural counts and marker matching still clean.

Seven more nodes now have body-backed review across the parity report, parity-baseline inventory, and release-manifest builder. The targeted modules passed **7/7**. Current semantic evidence is **351/2,666**, with 2,315 nodes pending; latest enforce still shows no structural or marker-matching violations.

The two release-runner selection tests and 13 release-gate/security metadata cases now have semantic evidence. These assert command planning and synthetic release-policy/metadata behavior only; they do not claim platform signing or artifact verification. Both modules passed **15/15**. Semantic evidence is **366/2,666**, and enforce still has no structural or marker mismatch but remains incomplete.

The 28 Wave 9 CI/Unicode nodes were source-reviewed and passed. Static source inventory remains `audit`, localization-file integrity is `contract`, and the archived-workflow branch reflects that automatic CI is disabled. Weak source-substring/count assertions are explicitly documented as non-runtime evidence. Current semantic review is **394/2,666**, with zero marker mismatches and no primary/registry debt.

The Wave 4 persistence module review found an exact semantic duplicate: `TestFavorites::test_duplicate_ignored` and `TestFavorites::test_toggle_removes` had identical setup, actions, and assertions. Removed the former and retained `test_toggle_removes` as owner; the module passed **19/19**. Mapping: `tests/test_wave4_favorites_history_persistence.py::TestFavorites::test_duplicate_ignored` → `...::test_toggle_removes`. Collection is now **2,665**; evidence is **413/2,665**.

The current Wave 5 module was re-audited and passed **16/16**. Two weak/redundant nodes were removed: `test_parse_scontrol_unicode_workdir` was a strict subset of `test_unicode_scontrol_parsing`, and `test_job_name_roundtrip` exercised partition access already covered by `test_directives_roundtrip_unicode`; the composed workflow now explicitly asserts no job name is parsed when that directive is absent. Collection is **2,663**, with **429** evidence-backed semantic reviews. The exact old/new mappings are recorded in the machine-readable review notes.

Wave 1 is now semantically reviewed and passed **12/12**. Its locale-mutating tests restore the prior language; the JSON roundtrip assertion now compares the complete parsed catalogs. Removed seven nodes that duplicated stronger catalog checks or exercised only Python stdlib behavior; renamed the editor source check to describe its real negative assertion. Current collection is **2,656** and evidence is **441/2,656**. Removed/renamed node mappings are recorded in the review notes.

All 17 Wave 2 wx local-file parity nodes are semantically reviewed. The fixture checks window cleanup, so these carry `resource` as well as `wx`. The truthful rename-selection test again fails after the renamed row appears; it remains a confirmed product defect, and no production file was touched. The other 16 passed in the isolated remainder run. Current evidence is **458/2,656**.

Wave 6’s 17 provider/plugin nodes are now reviewed; the module passed **17/17**. The two Unicode UI-contribution cases now submit valid `plugins_menu` schemas and require the entire validator error list to be empty (their previous wrappers bypassed label validation). The composed settings path remains integration, not installed-plugin E2E. Collection stayed at **2,656**; semantic evidence is **475/2,656**.

Wave 0 now has 33 body-reviewed nodes and passed **33/33**. Duplicate Favorites/config/i18n/SSH checks and one vacuous nonempty-file assertion were removed in favor of stronger Wave 1/Wave 6 owners. UTF-8 SFTP/shell/plugin-loader static checks now assert the actual source pattern and fail if the source file is absent. Fixture and host-filesystem checks are explicitly not counted as application runtime evidence. Collection is **2,647**, semantic evidence **508/2,647**.

Wave 7 has 14 current body-reviewed nodes and passed **14/14**. Editor/terminal models and output-follower behavior are unit; controller/log-file composition is integration. ZIP nodes are retained as format/stdlib contracts but explicitly do not count as app archive behavior; the remaining archive workflow node is not considered equivalent to the removed full-workflow owner. Current semantic review is **522/2,647**.

All 29 wx terminal WebView nodes are semantically reviewed. Native WebView readiness/queue collaboration is `integration`; visible xterm buffer/header/fallback state is `gui`; bridge payloads are `contract`; static asset/security checks are `audit`. Reclassified page-ready and two pre-ready queue owners to integration. Targeted page-ready, both queue cases, and actual visible fallback each passed 1/1. Fallback success does not establish packaged WebView parity. Current semantic evidence is **547/2,647**.

Updater lifecycle review checkpoint (2026-09-13): isolated i18n persistence in tests/test_wx_updater_spec.py with pytest tmp_path; module passes 22/22. Removed exact duplicate test_show_update_available_wrapper_returns_false_for_close; retained test_show_update_available_wrapper_returns_false_for_cancel. Renamed test_update_ready_requires_install_confirmation → test_ready_to_install_exposes_primary_install_action because the assertion only proves a bold visible Install action exists. Reclassified direct state-only unverified-artifact and synthetic close-handler tests as unit. The three lifecycle tests (cancel, close while in flight, late callback after close) remain GUI/concurrency/resource tests with real wx actions and worker ownership assertions. This module's previous run wrote the user-profile language.json at 2026-09-13 07:45; the original value is unknown and was not overwritten/restored by this reconciliation. Future runs are isolated.


File-action review checkpoint (2026-09-13): current service candidate matrix cases pass 6/6 and the policy module passes 16/16. The remote action behavior module passes 28/28 after semantic reclassification; backend-only compositions are integration, while visible wx state/event owners remain gui. Delete-confirmation cancellation now selects a visible row and asserts the row remains selected. The earlier file-action exact-matrix failures do not reproduce on this current governance tree.

Develop/governance base reconciliation (2026-09-13): develop HEAD and governance-v3 merge-base are both 87e1e709a879b52300a5eec660bfae04e700ee29, so the existing governance branch is already rooted on the intended remediation base. Apparent status-only changes to the packaged smoke report and wx remote view hash exactly to HEAD. The dirty develop parity test is a report writer intentionally removed from governance ownership; the tracked GUI-TERM-001 JSON already contains the same current FAIL/PARTIAL record in both worktrees, with unchanged SHA-1 970755ee1eaffb6dea91c23d18c5f151e6d737c3. Develop's two removed WebView xfails are body-exact matches for current governance nodes test_pre_ready_pending_queue_retains_chunks_until_bridge_ready and test_pre_ready_write_queue_preserves_fragment_order; both pass 1/1 on develop, so no duplicate is transplanted. No additional remediation commit is needed; all untracked archives, helpers, report, recovery directory, and prompt file remain untouched.
