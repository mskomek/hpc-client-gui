# Test-suite cleanup final report — 2026-09-12

**Continuation snapshot: 2026-09-13. Overall status: DEFECT_FOUND.** Taxonomy and ownership cleanup are complete, but the authoritative release runner is blocked by a confirmed local-file permission-handling product defect. Two additional wx product defects remain confirmed, and native lifecycle failures remain unresolved. This report supersedes earlier v2/v3 checkpoints where noted.

## Repository state and reconciliation

| Item | SHA / state |
| --- | --- |
| Frozen audit baseline | `12ce79935bf076e1062c57dc7dbd148bad2bfae1` |
| Previous committed remediation base | `54f7376f3e3e1fccd672f121e33b68d2e8df2652` |
| New remediation base | `1de2dce3aa8af037033882b26029fb33f39f9f57` |
| Previous governance snapshot | `2b4c675f31ae5aba4b1a2cf9b005b919c53be208` |
| v4 validated test tree | `fe1943dbf18c3fb46f8510f1c5667cb5204361ba` (identical to v3 SHA `2a24d1d0b3ef4d5f91e4b46e0a92306916c18d7c`) |
| Governance branch | `test-suite-governance-20260912-v4` |
| Push | None |
| Automatic CI | Intentionally disabled; no workflow was restored |

The original `develop` worktree was `87e1e709…` and had two modified tracked files at reconciliation start. `tests/test_wx_terminal_webview.py` contained only removals of two resolved non-strict xfails; both nodes passed on develop. The change was committed as `1de2dce3 test: remove resolved terminal WebView xfails` and did not change collection. `tests/test_wx_terminal_parity_evidence.py` contained an obsolete test-local generator that writes hardcoded packaged-runtime evidence; it was left untouched. Recovery patches and state capture were saved outside the repository under `C:\Users\mskomek\AppData\Local\Temp\hpc-client-gui-continuation-recovery-20260913`. Ten untracked local paths were also left untouched: `.integration-recovery/`, `audit.zip`, `docs/TEST_SUITE_AUDIT_REPORT_12ce7993.md`, `scripts/check_keys.py`, `scripts/check_line.py`, `scripts/find_mojibake.py`, `scripts/fix_missing_keys.py`, `scripts/fix_mojibake.py`, `tests/WAVE2_REMAINING_TEST_PROMPTS.md`, and `waves.zip`.

The v4 governance branch was created from the new remediation base. Governance-only commits were cherry-picked; the duplicate xfail-removal patch was omitted because it is now in the base. Conflicts were resolved semantically: WebView retained `wx`/`gui` markers and no xfail; concurrency history retained both sides' evidence. The resulting tree exactly matches v3, and the release run plus focused checks below were executed on v4.

## Collection evolution

| Baseline | Nodes | Collection errors |
| --- | ---: | ---: |
| Frozen audit `12ce7993` | 2,673 | 0 |
| Previous remediation `54f7376f` | 2,678 | 0 |
| New remediation `1de2dce3` | 2,679 | 0 |
| Previous governance `2b4c675f` | 2,685 | 0 |
| Current v4 governance | 2,649 | 0 |

The archived exact list for intermediate SHA `87e1e709` and a fresh clean-worktree collection both contain 2,679 nodes; an earlier summary field incorrectly said 2,678. From frozen audit to remediation base: +7 / −1, net +6. From new remediation base to current governance: +89 / −119, net −30. Frozen to current: +95 / −119, net −24. Exact node sets and comparisons are in `audit/archive/794226e/test-suite-final/nodeid-delta.json`; the new remediation baseline and list are under `audit/archive/1de2dce3/test-suite-baseline/`.

Significant mappings: the old packaged-smoke false-positive reporting node was replaced by a fail-closed missing-artifact report check (not equivalent runtime evidence); D2 byte-preservation source assertions were replaced by a byte-roundtrip owner; D3 raw server status gained a truthful action owner and is not an equivalent rename of the old selected-job test; D7 precedence has a canonical service owner plus a broader wx owner. The embedded-shell shared-implementation test remains. The dirty develop `test_embedded_and_detached_share_terminal_controls` alternative was not committed or treated as equivalent. Detailed behavior mappings are recorded in `DUPLICATE_GROUP_REVIEW_D1-D7.md` and Packet review documents.

## Confirmed Outputs localization fix

Root cause: output-channel state retained a resolved localized display label. On runtime locale change it kept the old English label even though semantic channel identity remained `stdout`. The wx Jobs view now preserves channel identity and resolves the visible label with current localization at render/update time; no Turkish label was hardcoded. `tests/test_wave80_files_outputs.py::TestWave80Audit::test_runtime_language_switch_updates_outputs` exercises visible language refresh and stable output state. It passed on v4 as part of **62 passed** across the taxonomy checker and Wave80 module; the complete Wave80 module's focused result is **45 passed**. English→Turkish now renders `Standart Çıktı`; output content, selection, and channel identity remain stable. Reusing the old translated label would fail the test.

## Re-evaluated findings

| Finding / node | Current result and classification | Action |
| --- | --- | --- |
| `tests/test_wave2_directories_local_files.py::TestErrorHandling::test_list_entries_permission_error` | **CONFIRMED_PRODUCT_DEFECT**; authoritative release runner fails. After catching `Path.stat()` permission denial, `src/hpc_gui/wx_local_files.py:77` calls `item.is_dir()`, which repeats `stat()` and leaks the error. | Truthful failing assertion retained; not fixed. |
| `tests/test_wave2_wx_ui_parity.py::TestSelectionPreservation::test_rename_preserves_selection` | **CONFIRMED_PRODUCT_DEFECT** in the current diagnostic sweep: the refreshed renamed row is not selected. | Test retained; not fixed. |
| `tests/test_wx_shell_p0_stress.py::test_wx_shell_p0_stress_real_wx_paths` | Assertions passed in the current timing run, but a real async completion callback was observed raising `RuntimeError` after the wx `Notebook` was destroyed (`wx_remote_files_view.py`, `GetSelection()`). **CONFIRMED_PRODUCT_DEFECT** despite a later passing run. | Evidence retained; not fixed. |
| `tests/test_hardening_additional.py::test_wx_separator_lifecycle_offscreen` | **NATIVE_RUNTIME_FAILURE / UNRESOLVED**: isolated child exceeded 30 seconds; later module run exited `0xC0000374` heap corruption. | Not called flaky or passing. |
| About dialog/no-network runtime test | Isolated child passed 1/1. A combined Qt/WebView process produced Windows access violation at this node after the updater and WebView modules. **ORDER_DEPENDENCE / NATIVE_RUNTIME_FAILURE**; not a confirmed product defect. | No retry in main process; native lifecycle evidence retained. |
| `tests/test_wave3_remote_sftp_ssh.py::TestRemoteEntryHelpers::test_file_type_directory` | **RESOLVED_BY_REMEDIATION**; scoped locale save/restore fixture, Wave3 module 28 passed. | No further change. |
| `test_remote_policy_exact_matrix` (two cases) | **RESOLVED_BY_REMEDIATION**; current policy module 16 passed. | Service candidate and visible-menu filtering remain separate owners. |
| `tests/test_wx_65a_stress.py::test_wx_65a_integrated_stress` | Passed current isolated diagnostic in 160.02s; measured invariants were zero. Earlier WebView abort diagnostics did not reproduce as heap corruption in that run. | No skip or retry added. |
| Remote navigation/sort/provider-filter visible test | Current behavior module 28 passed. | Visible behavior evidence retained. |
| Shell P0 completion/deduplication tests | Current module 13 passed. | Retained. |
| Embedded-terminal/WebView close and ordering cases | WebView module 29 and embedded module 10 passed in bounded runs; earlier native abort did not reproduce. | Historical abort remains historical evidence; no packaged parity claim. |
| `tests/test_performance_probe.py::test_qt_event_loop_block_is_detected` | Rewritten to schedule an explicit blocking callback and test the actual heartbeat; it passed alone, the module, and the authoritative release run. | Resolved by test remediation. |

## Test taxonomy

Every collected node has exactly one actual pytest primary marker. The semantic review used test bodies and evidence paths, not filename heuristics. Machine review records `reviewed=true` for **2,649/2,649** nodes at `audit/archive/794226e/test-suite-final/semantic-taxonomy-review.json`.

The previous 2,685-node governance snapshot had structural zero-primary 0 and multi-primary 0, but its semantic review was incomplete. Its category counts below are the prior marker assignment distribution, not accepted semantic truth.

| Primary | Previous snapshot (unverified) | Final reviewed |
| --- | ---: | ---: |
| unit | 634 | 659 |
| integration | 294 | 387 |
| gui | 899 | 654 |
| e2e | 1 | 15 |
| runtime_smoke | 36 | 4 |
| contract | 576 | 621 |
| audit | 100 | 175 |
| reporting | 22 | 47 |
| release | 123 | 87 |
| **Total** | **2,685** | **2,649** |

| Category | Count | Total node work (s) | Median (s) | p95 (s) |
| --- | ---: | ---: | ---: | ---: |
| unit | 659 | 18.917 | 0.0090 | 0.0447 |
| integration | 387 | 38.776 | 0.0237 | 0.4142 |
| gui | 654 | 950.536 | 0.1651 | 2.0764 |
| e2e | 15 | 25.247 | 0.1116 | 7.0437 |
| runtime_smoke | 4 | 2.884 | 0.7855 | 1.2086 |
| contract | 621 | 25.897 | 0.0079 | 0.0361 |
| audit | 175 | 9.725 | 0.0086 | 0.3345 |
| reporting | 47 | 1.266 | 0.0076 | 0.0426 |
| release | 87 | 21.749 | 0.0060 | 0.0697 |
| **Total** | **2,649** | **1,094.998** | — | — |

Taxonomy ENFORCE passes: zero-primary 0, multi-primary 0, unknown registered markers 0, missing markers 0, semantic-review gaps 0. Checker warnings for direct test calls and generic catch-all filenames are both zero.

| Qualifier | Count | Qualifier | Count |
| --- | ---: | ---: | ---: |
| semantic | 92 | regression | 62 |
| performance | 20 | resource | 289 |
| concurrency | 157 | slow | 4 |
| subprocess | 61 | windows | 13 |
| linux | 61 | macos | 52 |
| hardware | 0 | synthetic_hardware | 0 |
| license | 1 | acceptance | 1 |
| artifact_dependent | 29 | wx | 558 |
| qt | 349 | packaging | 50 |

Hardware and synthetic-hardware qualifiers are both zero; fake SSH/Slurm providers are not described as real hardware evidence.

## Cleanup status

- D1–D7 were re-audited and remain resolved on v4. Focused owners passed 4/4 static/service, 4/4 Wave78/visible Files, and 3/3 Outputs/D7 wx tests.
- Three updater lifecycle tests exercise cancellation, in-flight close, and queued late completion behavior. Updater spec module passed 22/22 in a bounded child.
- Terminal fallback cases create visible fallback UI and assert non-parity; WebView module passed 29/29. This is not packaged WebView parity evidence.
- About and updater ordering claims now use runtime behavior. About isolated passed 1/1; updater ordering isolated passed 1/1. Mixed-process native access violation is recorded above.
- Wave80 Files/Outputs visible localization evidence passed; the Outputs defect is fixed.
- Source-text runtime claims were rewritten to runtime evidence; legitimate audit/contract checks remain static.
- Packaged smoke is a fail-closed reporting gate and does not count as packaged-runtime or E2E evidence. Plugin E2E remains because it crosses the expected boundaries.
- Five suspicious skip sites were reviewed; none was converted into a pass merely because of flakiness. The two resolved non-strict WebView xfails were removed. Current timing sweep and authoritative release summary report xfail 0 / xpass 0.
- Catch-all ownership has no current warning. Migration and historical evidence remain documented rather than deleted by filename.

## Lane comparison (Packet N)

| Lane | Existing | Marker candidate | Added / removed | Exact |
| --- | ---: | ---: | ---: | :---: |
| cli | 164 | 1671 | 1510 / 3 | no |
| compat | 202 | 1667 | 1470 / 5 | no |
| contract | 10 | 621 | 618 / 7 | no |
| macos_explicit | 55 | 52 | 28 / 31 | no |
| packaging | 3 | 50 | 47 / 0 | no |
| release_suite | 2599 | 2599 | 0 / 0 | yes |
| ssh | 45 | 1008 | 975 / 12 | no |
| windows_pytest | 6 | 13 | 13 / 6 | no |

Only release suite has exact parity. Existing file selectors remain; automatic CI was not re-enabled.

## Validation

| Command | Exit | Result |
| --- | ---: | --- |
| `python -m compileall -q src/hpc_gui` | 0 | PASS |
| `python -m ruff check src scripts tests` | 0 | PASS |
| `python scripts/check_i18n.py` | 0 | PASS |
| `python scripts/smoke_test.py` | 0 | PASS |
| `python scripts/check_test_taxonomy.py --mode report` | 0 | 2,649 nodes reported |
| `python scripts/check_test_taxonomy.py --mode enforce --semantic-review ...` | 0 | PASS, 2,649/2,649 reviewed |
| `python -m pytest tests --collect-only -q` | 0 | 2,649 collected; 0 errors |
| Taxonomy checker + Wave80 module | 0 | 62 passed in 8.85s |
| D1/D2/D4/D7 service-focused owners | 0 | 4 passed |
| Wave78 status + visible Files locale owners | 0 | 4 passed |
| Outputs contract/runtime + wx password owner | 0 | 3 passed |
| `tests/test_wx_updater_spec.py` isolated | 0 | 22 passed in 3.08s |
| `tests/test_wx_terminal_webview.py` isolated | 0 | 29 passed in 22.88s |
| About no-network node isolated | 0 | 1 passed; mixed-process access violation recorded separately |
| Updater splash-before-worker node isolated | 0 | 1 passed |
| `python scripts/release_test_suite.py` | 1 | 1 failed, 1,825 passed, 19 skipped, 50 deselected; confirmed product defect above |
| `python scripts/release_test_suite.py --coverage` | 1 | Same defect; coverage 46%, partial gate |
| `git diff --check` | 0 | PASS before documentation commit |

Authoritative release result is not green. It stopped at the permission-denial failure before later isolated groups. Coverage reached 46% in the same failed group and did not complete downstream coverage gates.

## Outcomes and performance

Authoritative release-suite group: passed 1,825; failed 1; skipped 19; xfail 0; xpass 0; deselected 50; 29 subtests passed. Pytest time 95.06s; runner wall time 101.03s. Coverage run: same test outcomes, 46%, pytest 167.93s, runner 175.55s, incomplete. Separate 2,649-node process-group timing sweep: 2,625 passed, 3 failed, 21 skipped, 0 xfail/xpass; this is diagnostic and is not combined with the release result.

The timing report covers all 2,649 nodes and the exact validated source tree. It sums test body work (not one-process wall time): **1094.998s**. Category totals, median, and p95:

| Category | Count | Sum (s) | Median (s) | p95 (s) |
| --- | ---: | ---: | ---: | ---: |
| unit | 659 | 18.917 | 0.0090 | 0.0447 |
| integration | 387 | 38.776 | 0.0237 | 0.4142 |
| gui | 654 | 950.536 | 0.1651 | 2.0764 |
| e2e | 15 | 25.247 | 0.1116 | 7.0437 |
| runtime_smoke | 4 | 2.884 | 0.7855 | 1.2086 |
| contract | 621 | 25.897 | 0.0079 | 0.0361 |
| audit | 175 | 9.725 | 0.0086 | 0.3345 |
| reporting | 47 | 1.266 | 0.0076 | 0.0426 |
| release | 87 | 21.749 | 0.0060 | 0.0697 |

Slowest 20 test nodes:

| # | Seconds | Node | Outcome |
| ---: | ---: | --- | --- |
| 1 | 195.588 | `tests/test_wx_shell_p0_stress.py::test_wx_shell_p0_stress_real_wx_paths` | passed |
| 2 | 160.020 | `tests/test_wx_65a_stress.py::test_wx_65a_integrated_stress` | passed |
| 3 | 132.980 | `tests/test_wx_layout_resize.py::test_wx_layout_resize` | passed |
| 4 | 37.933 | `tests/test_wx_file003_final_stress.py::test_stress_e_navigate_completion_races` | passed |
| 5 | 30.055 | `tests/test_hardening_additional.py::test_wx_separator_lifecycle_offscreen` | failed |
| 6 | 29.126 | `tests/test_wx_file003_final_stress.py::test_stress_b_local_mutations` | passed |
| 7 | 27.599 | `tests/test_wx_file003_final_stress.py::test_stress_c_remote_mutations` | passed |
| 8 | 26.842 | `tests/test_wx_file003_final_stress.py::test_stress_i_unicode_and_space_names` | passed |
| 9 | 22.833 | `tests/test_wx_jobs_stress.py::test_wx_jobs_stress_open_close_repeatedly_does_not_leak_windows_or_timers` | passed |
| 10 | 21.389 | `tests/test_wx_file003_final_stress.py::test_stress_d_target_switches` | passed |
| 11 | 19.759 | `tests/test_wheel_packaging.py::test_built_wheel_contains_required_assets` | passed |
| 12 | 13.542 | `tests/test_wx_file003_final_stress.py::test_stress_f_browser_open_close` | passed |
| 13 | 10.960 | `tests/test_wx_terminal_webview.py::test_wx_terminal_screen_state_readback_and_alternate_buffer` | passed |
| 14 | 9.873 | `tests/test_wx_file003_final_stress.py::test_stress_g_blocked_close_in_flight` | passed |
| 15 | 7.050 | `tests/test_wx_editor_window_parity.py::test_wx_editor_window_manager_repeated_open_close_does_not_leak_frames` | passed |
| 16 | 7.044 | `tests/test_mock_cluster_roundtrip.py::MockClusterRoundTripTests::test_files_round_trip_over_real_ssh_wire` | passed |
| 17 | 6.461 | `tests/test_wx_file_actions_stress.py::test_wx_local_mutation_stress_uses_real_actions` | passed |
| 18 | 5.609 | `tests/test_wx_file_actions_stress.py::test_wx_remote_mutation_stress_uses_real_actions` | passed |
| 19 | 5.265 | `tests/test_download_cancel_wire.py::DownloadCancelWireTests::test_overwriting_a_partial_discards_it_before_downloading` | passed |
| 20 | 4.660 | `tests/test_mock_cluster_roundtrip.py::MockClusterRoundTripTests::test_jobs_commands_round_trip_over_real_ssh_wire` | passed |

Slowest GUI nodes:

| # | Seconds | Node |
| ---: | ---: | --- |
| 1 | 195.588 | `tests/test_wx_shell_p0_stress.py::test_wx_shell_p0_stress_real_wx_paths` |
| 2 | 160.020 | `tests/test_wx_65a_stress.py::test_wx_65a_integrated_stress` |
| 3 | 132.980 | `tests/test_wx_layout_resize.py::test_wx_layout_resize` |
| 4 | 37.933 | `tests/test_wx_file003_final_stress.py::test_stress_e_navigate_completion_races` |
| 5 | 30.055 | `tests/test_hardening_additional.py::test_wx_separator_lifecycle_offscreen` |
| 6 | 29.126 | `tests/test_wx_file003_final_stress.py::test_stress_b_local_mutations` |
| 7 | 27.599 | `tests/test_wx_file003_final_stress.py::test_stress_c_remote_mutations` |
| 8 | 26.842 | `tests/test_wx_file003_final_stress.py::test_stress_i_unicode_and_space_names` |
| 9 | 22.833 | `tests/test_wx_jobs_stress.py::test_wx_jobs_stress_open_close_repeatedly_does_not_leak_windows_or_timers` |
| 10 | 21.389 | `tests/test_wx_file003_final_stress.py::test_stress_d_target_switches` |

Slowest E2E nodes:

| # | Seconds | Node |
| ---: | ---: | --- |
| 1 | 7.044 | `tests/test_mock_cluster_roundtrip.py::MockClusterRoundTripTests::test_files_round_trip_over_real_ssh_wire` |
| 2 | 5.265 | `tests/test_download_cancel_wire.py::DownloadCancelWireTests::test_overwriting_a_partial_discards_it_before_downloading` |
| 3 | 4.660 | `tests/test_mock_cluster_roundtrip.py::MockClusterRoundTripTests::test_jobs_commands_round_trip_over_real_ssh_wire` |
| 4 | 4.089 | `tests/test_download_cancel_wire.py::DownloadCancelWireTests::test_resuming_after_a_cancel_completes_the_file` |
| 5 | 2.032 | `tests/test_download_cancel_wire.py::DownloadCancelWireTests::test_cancel_keeps_the_partial_and_leaves_the_session_usable` |
| 6 | 1.746 | `tests/test_download_cancel_wire.py::DownloadCancelWireTests::test_skipping_a_partial_leaves_it_alone` |
| 7 | 0.181 | `tests/test_plugin_e2e.py::test_full_clean_user_lifecycle` |
| 8 | 0.112 | `tests/test_fluent_plugin_integration.py::test_registry_entry_installs_via_exact_file_protocol` |
| 9 | 0.077 | `tests/test_fluent_plugin_integration.py::test_latest_fluent_template_renders_after_install` |
| 10 | 0.042 | `tests/test_plugin_installer.py::test_valid_install_end_to_end` |

Full phase durations, diagnostic outcomes, lane node sets, taxonomy reports, exact node deltas, and authoritative release outcomes are archived under `audit/archive/794226e/test-suite-final/`.

## Release truth

| Evidence area | Status |
| --- | --- |
| Automatic GitHub CI | Intentionally disabled |
| Windows packaged smoke | FAIL |
| GUI-TERM-001 packaged terminal parity | PARTIAL |
| Linux packaged wx/WebKit runtime | NOT EVIDENCED |
| macOS packaged runtime | NOT EVIDENCED |
| Live-cluster evidence | NOT EVIDENCED |
| Manual GUI sign-off | NOT EVIDENCED |
| Test taxonomy correctness | PASS |
| Release readiness | NO-GO while confirmed defects and evidence gaps remain |

## Packet status

| Packet | Status |
| --- | --- |
| A — baseline and inventory | PASS; corrected 2,679 remediation count |
| B — taxonomy/report checker | PASS |
| C — ratchet/lane manifests | PASS |
| D — D1–D7 duplicates | PASS |
| E — updater lifecycle | PASS |
| F — GUI truthfulness | PASS; authorized Outputs product defect fixed |
| G — wave ownership | PASS |
| H — settings isolation | PASS |
| I — source-text behavior rewrites | PASS |
| J — resource/concurrency | PARTIAL; unresolved separator native failure and callback defect evidence |
| K — reporting/E2E reclassification | PASS |
| L — static/migration ownership | PASS |
| M — semantic full-suite taxonomy | PASS, 2,649/2,649 |
| N — lane migration | KEEP current selectors; exact marker parity unavailable for seven lanes |
| O — reporting integration/closeout | DEFECT_FOUND; report is truthful, authoritative release gate fails |

## Remaining issues

1. Confirmed product defects: permission-denied local directory listing, renamed-row selection preservation, and an asynchronous wx callback accessing a destroyed Notebook. None was modified here except the separately authorized Outputs localization defect.
2. Native wx separator lifecycle timeout/heap corruption remains unresolved. The About dialog node passes alone but had one combined-process native access violation.
3. Windows packaged terminal parity remains FAIL/PARTIAL; Linux/macOS packaged runtime and live-cluster evidence are absent.

No push was performed.
