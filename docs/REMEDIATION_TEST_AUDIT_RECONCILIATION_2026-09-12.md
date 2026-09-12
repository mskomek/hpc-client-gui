# Remediation / Test-Audit Reconciliation Report

Date: 2026-09-12
Repository: D:/Projeler/hpc-client-gui
Frozen audit baseline: 12ce79935bf076e1062c57dc7dbd148bad2bfae1

This report records a read-only reconciliation of the remediation work against the frozen test-suite audit. It uses the checked-out worktree content for current behavior and records staged-versus-unstaged differences separately. No commit, push, reset, checkout, clean, stash, or discard was performed.

## Current state

| Field | Result |
|---|---|
| HEAD | 12ce79935bf076e1062c57dc7dbd148bad2bfae1 |
| Branch | develop |
| Worktree | Dirty; final status matched the status recorded at reconciliation start |
| Current collection | 2,678 nodes |
| Collection errors | 0 |
| Release suite | Not rerun in this read-only pass |

Collection ran for 21.27 seconds with pytest's cache plugin disabled. The settings-hang node was run alone with a 60-second external timeout: PASS, one passed; 5.56 seconds wall time (pytest reported 0.59 seconds).

The release suite was not rerun because its preflight calls scripts/smoke_test.py, which creates and deletes a diagnostic bundle under build/ci-smoke. That would write inside the repository. The existing remediation report records 1,896 passed, 21 skipped, and 2 deselected; this pass did not independently verify that result. The release runner excludes packaging tests, so its reported pass does not validate packaged smoke.

The remediation evidence records the latest packaged Windows attempt as FAIL for artifact SHA-256 c83c1b05c157a97b040c705efe722855cd1511ee3b59de19c87341e18a38394f. Foreground activation failed, so no keys were sent. A preceding artifact accepted 36 input events but produced no terminal output. Neither is a packaged success. The full remediation results are in docs/FINAL_REMEDIATION_REPORT_2026-09-12.md; the frozen findings are in docs/TEST_SUITE_AUDIT_REPORT_12ce7993.md.

## Relevant changed test files

M means unstaged; MM means staged and unstaged changes both exist. Node deltas below compare current working files with the frozen baseline.

| File | Baseline to current worktree; node delta | Assertion, skip/xfail, and audit effect |
|---|---|---|
| tests/test_connection_advanced_settings.py (M) | Path.home changed from an unconfigured MagicMock to a concrete temporary directory. No node change. | Existing assertion remains. The reproduced settings hang is fixed; isolated run passed. |
| tests/test_gui_audit_screenshots.py (M) | Same node; manifest SHA mismatch now skips. | Assertion weakened and a historical-evidence skip added. The stale screenshot evidence is not resolved. |
| tests/test_macos_ci.py (M) | Same two nodes; if active CI is absent, each verifies the archived workflow and returns. | No skip; matrix and signing assertions are bypassed for the archived case. Addresses the two missing-workflow failures under the current disabled-CI state. |
| tests/test_macos_release_workflow.py (M) | Same node; accepts the archived workflow if active CI is absent. | No skip; archived-file existence replaces the old active-workflow assertion. Addresses its missing-workflow failure. |
| tests/test_performance_probe.py (M) | Same node; deliberate event-loop blocking now follows the monitor's first heartbeat. | Timing setup is more deterministic; no skip change. |
| tests/test_release_test_suite.py (M) | Same node; checks command membership instead of relying on list positions. | Generalizes the runner assertions; no skip change. |
| tests/test_remote_directory_listing.py (M) | Same node; stress input reduced from 20,000 entries to 4,000. | Reduces stress magnitude but retains the cancellation scenario. |
| tests/test_wave3_remote_sftp_ssh.py (M) | Same node; explicitly loads English before a localized-label assertion. | Stabilizes locale-dependent behavior; no skip change. |
| tests/test_wave9_ci_unicode_matrix.py (M) | Same node; accepts archived CI when active CI is absent. | Bypasses old workflow-content assertions in that case. Addresses its missing-workflow failure. |
| tests/test_workflow_action_pins.py (M) | Same node; requires active release.yml and archived ci.yml rather than active ci.yml and release.yml. | Adjusts the contract to disabled CI; does not validate an active CI workflow. Addresses its missing-workflow failure. |
| tests/test_wx_65a_stress.py (M) | Same node; reads labels from language menu items. | Better targets the visible labels; no skip change. |
| tests/test_wx_embedded_terminal.py (M) | Removes test_shell_embedded_and_detached_share_implementation and adds test_embedded_and_detached_share_terminal_controls. | Probable rename. The replacement constructs both panels directly through the same builder and no longer exercises the shell's embedded path; this narrows coverage. |
| tests/test_wx_file_action_policy.py (M) | Same nodes; expected action sets now include additional file and directory actions. | Strengthens the expected action matrix; no skip change. |
| tests/test_wx_jobs_stress.py (M) | Same node; compares pause label to its translation instead of a hard-coded English string. | Removes locale brittleness; no skip change. |
| tests/test_wx_packaged_smoke.py (MM) | Current worktree matches the frozen file; no current node delta. | The staged version changes assertions to a stages field; the unstaged version restores the baseline result/checks assertions. The staged version does not match the current smoke-runner schema and is not commit-ready. |
| tests/test_wx_shell_p0.py (M) | Same node; reads completion status from column 2 instead of column 1. | Tracks the current table layout; no skip change. |
| tests/test_wx_shell_p0_stress.py (M) | Same node; adds menu-title checks but makes some control-label checks conditional on control presence. | Conditional checks can omit missing controls, weakening that portion of the test. |
| tests/test_wx_terminal_parity_evidence.py (MM) | Same node; expected report now separates historical PASS from current FAIL and lists screen-state coverage. | Improves evidence accuracy; it reports failure and does not establish packaged parity. |
| tests/test_wx_terminal_webview.py (MM) | Same nodeids; removes two non-strict xfail decorators. | Nodes may still skip when WebView is unavailable. The staged version deletes 131 lines that the worktree restores. Remediation documentation reports 70 focused terminal tests passed; this reconciliation did not rerun that set. |
| tests/test_wx_updater_spec.py (M) | Adds five nodes: three wrapper-result cases, missing verified artifact, and Unicode release notes. No removals or renames. | Adds adjacent behavior coverage but does not rewrite the three weak lifecycle tests. |

The updater install test now sets _artifact_verified to true in its simulated successful-install setup, matching the added product guard.

## Other relevant implementation, selectors, and evidence

- scripts/release_test_suite.py (M) discovers wx test files using source-text patterns and runs them in separate pytest processes. It also isolates test_remote_directory_listing.py. Packaging exclusion remains unchanged. This changes process grouping, not collection. Compare the resulting selected node set against the previous release selection before relying on the discovery heuristic.
- scripts/wx_packaged_smoke.py (MM) in the working tree retains artifact-owned runtime evidence and adds diagnostic fields plus another artifact candidate. The staged snapshot replaces this with --help and output heuristics, which could falsely report runtime evidence. The staged version is not the checked-out working behavior.
- src/hpc_gui/wx_shell.py (MM) changes terminal initialization and packaged-smoke input diagnostics. Its staged snapshot removes smoke instrumentation that remains in the worktree.
- src/hpc_gui/wx_terminal_webview.py (MM) adds WebView creation, navigation, and bridge failure-stage diagnostics. It does not make either fallback test exercise fallback behavior.
- src/hpc_gui/wx_terminal.py (M) creates a terminal model for the WebView adapter path.
- src/hpc_gui/wx_updater_view.py (M) adds download/install artifact verification, cancellation guards, timer cleanup, and wrapper return handling. The three weak updater test bodies remain unchanged.
- src/hpc_gui/wx_jobs.py (M) changes refresh coalescing and output-channel refresh/status handling. Recheck Wave78 jobs assertions against this implementation.
- Other changed wx implementation files include src/hpc_gui/wx_editor_view.py, src/hpc_gui/wx_remote_files_view.py, and src/hpc_gui/services/file_filter_registry.py.
- docs/v2/GUI_TERM_001_EXECUTION_EVIDENCE.json, docs/v2/WX_PACKAGED_SMOKE_GATE.md, docs/v2/WX_MIGRATION_WAVE_STATUS.md, docs/REMEDIATION_STATUS_2026-09-11.md, and build/audit/wx-packaged-smoke-windows.json update migration and runtime evidence. The latest recorded packaged result is a failure, not a pass.

## Audit findings invalidated by remediation

- The settings hang: Path.home now returns a concrete temporary path, and the isolated test passes.
- Five missing-workflow failures: both macOS CI nodes, the macOS release-preflight node, the Wave9 workflow node, and the workflow-existence node now recognize archived disabled CI. This addresses the tests for the current disabled-CI state; it does not restore CI.
- The two non-strict xfail findings: both decorators are gone. The nodes no longer silently XPASS under non-strict xfail; the remediation report says the focused terminal suite passed.

The GUI screenshot manifest finding is not substantively invalidated. Its SHA mismatch now skips, and current screenshots were not reproduced.

## Audit findings still valid

- D1–D7 remain duplicate groups; none of their nodeids changed.
- The three named updater lifecycle tests remain weak.
- Both terminal fallback tests still prove symbol existence only.
- The packaged-smoke test still lacks an explicit artifact fixture or path. The current runner correctly fails when the artifact is missing, but the test expects PASS from a no-argument invocation. It is environment-dependent and does not itself establish packaged success. The release suite excludes it with the packaging marker.
- The five suspicious “flaky/polluted” skips remain unchanged.
- The About dialog source-text test and updater source-order test remain static implementation checks.
- Wave80 localization duplicate pairs remain unchanged and test translation lookups, not visible menus.

## Duplicate groups current state

| Group | Exact current nodeids | Status |
|---|---|---|
| D1 | test_wave0_unicode_baseline.py::TestEncodingBoundaryInventory.test_errors_replace_in_ssh; test_wave1_unicode_core_policy.py::TestEncodingBoundaryJustification.test_ssh_client_decode_justified | Still exact and semantic duplicate |
| D2 | test_wave0_unicode_baseline.py::TestRiskClassification.test_p0_sftp_roundtrip_risks_documented; test_wave1_unicode_core_policy.py::TestEncodingBoundaryJustification.test_files_ssh_utf8_justified | Still exact and semantic duplicate |
| D3 | test_wave78_jobs_details.py::test_cluster_servers_visible_without_selected_job_when_provider_supports; test_wave78_jobs_details.py::test_raw_server_status_opens | Exact duplicate remains; re-audit semantics after wx_jobs.py changes |
| D4 | test_wave79_audit.py::TestSchemaV4Audit.test_v4_valid; test_wave79_audit.py::TestSchemaV4Audit.test_v4_optional_sections_ok | Still exact and semantic duplicate |
| D5 | test_wave80_files_outputs.py::TestFilesBehavior.test_context_menu_labels_localized; test_wave80_files_outputs.py::TestWave80Audit.test_files_context_menu_localized | Still exact and semantic duplicate; translation-only |
| D6 | test_wave80_files_outputs.py::TestOutputsBehavior.test_standard_output_localized; test_wave80_files_outputs.py::TestWave80Audit.test_outputs_standard_output_error_localized | Still exact and semantic duplicate; translation-only |
| D7 | test_wx_connection_71_2.py::test_typed_password_precedence; test_wx_connection_71_3.py::test_typed_password_precedence | Still exact and semantic duplicate |

No duplicate group is resolved.

## Weak-test current state

| Original finding | Frozen baseline status | Current dirty-tree status | Still actionable? |
|---|---|---|---|
| Updater: test_update_cancel_prevents_install | Manually sets cancellation/state and includes an assertion ending in “or True” | Same node, setup, action, and vacuous assertion; updater product code changed underneath it | Yes |
| Updater: test_update_close_in_flight_safe | Calls close handler with a mocked dialog response; limited state assertion | Same test; updater callbacks and timer lifecycle changed | Yes |
| Updater: test_update_late_callback_after_close_safe | Sets _closed directly and never invokes the real callback | Same test; updater product code changed underneath it | Yes |
| Settings: ParallelismSourceOfTruthTests::test_settings_dialog_has_no_global_parallelism_editor | Hung with default MagicMock for Path.home | Concrete temporary home; PASS in 5.56 seconds wall time | No; hang fixed |
| Terminal: test_wx_terminal_webview.py::test_wx_terminal_fallback_sets_non_parity | Only checks class/callable existence | Same assertions; does not instantiate or force fallback | Yes |
| Terminal: test_wx_terminal_behavioral.py::test_fallback_panel_sets_non_parity | Only checks class/callable existence | Same assertions; no fallback state or visible behavior | Yes |
| Packaged smoke: test_packaged_wx_smoke_gate_reports_critical_stages | Expects PASS without arranging a packaged artifact | Current worktree invokes default artifact search; test supplies no artifact | Yes |
| Wave78: test_wave78_jobs_details.py::test_no_selection_state_shows_empty_state | Checks visible empty-state panel, hidden details panel, and localized label | Unchanged test; wx_jobs.py changed, so recheck against the new implementation | Re-audit; useful GUI assertion |
| Wave80 localization tests | D5/D6 duplicates; translation lookups, no menu construction | Unchanged; exact duplicate groups persist | Yes; merge/reclassify |
| About dialog: test_about_shows_version_and_no_network | Reads source text for version, URL, and network-call spellings | Unchanged; adjacent instantiation test checks creation/version | Yes; reclassify or add runtime behavior evidence |
| Updater source order: test_manual_update_check_shows_splash_before_worker_starts | Uses inspect.getsource and source.index ordering | Unchanged; product path is not executed | Yes; static contract or runtime rewrite |
| Five suspicious skips | One hardening test and four wx jobs tests cite “flaky”/“polluted” | All five reasons unchanged | Yes |
| Two non-strict xfails | Pending-output and many-fragment ordering nodes were non-strict xfails | Decorators removed; remediation report says focused terminal set passed 70 tests | No as an xfail finding; retain platform coverage review |

The five unchanged suspicious skips are test_hardening_additional.py::test_wx_separator_lifecycle_offscreen and four nodes in test_wx_jobs_behavior.py: pause/resume follow, minimize/restore follow, overlapping remote reads, and stale results after job selection changes.

## Collection delta

```text
baseline: 2,673
current:  2,678
added:    6
removed:  1
errors:   0
```

Added nodeids:

```text
tests/test_wx_embedded_terminal.py::test_embedded_and_detached_share_terminal_controls
tests/test_wx_updater_spec.py::test_install_without_verified_artifact_stays_failed
tests/test_wx_updater_spec.py::test_show_update_available_wrapper_returns_false_for_cancel
tests/test_wx_updater_spec.py::test_show_update_available_wrapper_returns_false_for_close
tests/test_wx_updater_spec.py::test_show_update_available_wrapper_returns_true_when_download_starts
tests/test_wx_updater_spec.py::test_update_release_notes_preserve_unicode
```

Removed nodeid:

```text
tests/test_wx_embedded_terminal.py::test_shell_embedded_and_detached_share_implementation
```

The removed embedded-terminal node and the new controls node are a probable rename, not an established one-to-one replacement.

## Taxonomy foundation impact

No new primary or qualifier taxonomy markers were introduced. The updater adds a test-local _WrapperDialog helper. The release runner adds _wx_test_files() and per-file wx process isolation. The GUI manifest test adds dynamic skip behavior; the two terminal xfail decorators are removed.

The existing packaging marker and -m “not packaging” release selection predate this remediation. Under the proposed taxonomy, packaging is a qualifier, so packaging tests need a primary marker such as release before enforcing exactly one primary marker. No workflow introduces marker selectors; automatic CI remains disabled.

## Recommended governance base

**OPTION B — commit reviewed remediation work first, then branch test-governance from that commit.**

The remediation overlaps tests, product paths, release selection, skip behavior, and evidence that Phase 2 would classify or clean up. The separate hpc-client-gui-test-governance worktree remains on the frozen baseline and is useful as a reference, but taxonomy work there would use stale tests and selectors. The staged index is also not safe to commit as-is.

## Proposed prerequisite commit groups

These are recommendations only; no commits were created.

1. **Settings hang:** tests/test_connection_advanced_settings.py.
2. **Release-suite isolation:** scripts/release_test_suite.py, tests/test_release_test_suite.py, tests/test_remote_directory_listing.py.
3. **Updater lifecycle:** src/hpc_gui/wx_updater_view.py, tests/test_wx_updater_spec.py.
4. **wx jobs/files/editor behavior:** src/hpc_gui/services/file_filter_registry.py, src/hpc_gui/wx_editor_view.py, src/hpc_gui/wx_jobs.py, src/hpc_gui/wx_remote_files_view.py, tests/test_wx_65a_stress.py, tests/test_wx_file_action_policy.py, tests/test_wx_jobs_stress.py, tests/test_wx_shell_p0.py, tests/test_wx_shell_p0_stress.py, tests/test_wave3_remote_sftp_ssh.py.
5. **Terminal and packaged-runtime evidence:** src/hpc_gui/__main__.py, src/hpc_gui/wx_shell.py, src/hpc_gui/wx_terminal.py, src/hpc_gui/wx_terminal_webview.py, scripts/wx_packaged_smoke.py, tests/test_wx_embedded_terminal.py, tests/test_wx_terminal_parity_evidence.py, tests/test_wx_terminal_webview.py, and the matching build and docs/v2 evidence files.
6. **Disabled-CI contract updates:** tests/test_macos_ci.py, tests/test_macos_release_workflow.py, tests/test_wave9_ci_unicode_matrix.py, tests/test_workflow_action_pins.py.
7. **Visual/migration evidence:** tests/test_gui_audit_screenshots.py, scripts/capture_current_gui_wx.py, scripts/qt_removal_gate.py, and the matching remediation/migration documents.

Keep the untracked recovery directory, archives, localization helper scripts, and prompt file out of these groups unless they receive separate review. Reconcile staged-versus-unstaged snapshots before preparing any commit.

## Safe next action

The prepared Phase-2 Packet A+B prompt must be revised. Run it from the reviewed remediation commit, keep 12ce7993 as the frozen comparison baseline, and refresh the inventory and node mapping first. Include the 2,678-node collection, the probable embedded-terminal rename, updater additions, changed release process grouping, and the current failed packaged-terminal evidence.

At reconciliation completion, the recorded git status matched its starting state and HEAD remained 12ce79935bf076e1062c57dc7dbd148bad2bfae1. This report file was added afterward at the user's explicit request; no other file was changed for report authoring. No commit or push was made.

## Execution follow-up

The later master execution prompt authorized local commits and further work. Five commits were subsequently created on `develop`: settings isolation (`ccfeb1b8`), release-suite process isolation (`2c808f41`), updater lifecycle hardening (`1ff36589`), disabled-CI contract alignment (`a0b57b8e`), and remediation evidence reconciliation (`9e7e2ce1`). None was pushed.

Focused revalidation after the read-only pass found two unresolved runtime failures: a remote-files callback accessed a destroyed wx Notebook in `test_wx_shell_p0_stress_real_wx_paths`, and WebView2 close caused a native access violation in `test_find_next_prev_advances_through_matches`. The implicated production changes remain untouched. Related wx/terminal remediation files are preserved as local dirty work and were not included in the reviewed commit base. Overall status is `DEFECT_FOUND`; taxonomy packets have not yet been completed.
