# Test Suite Integration Closeout — 2026-09-13

Status: **DEFECT_FOUND — NOT READY TO MERGE INTO DEVELOP.** The governance Wave is complete. The current release runner reached the end of its broad pytest process without a native process termination, but that process reported an unresolved wx application-order failure and a confirmed remote Logs-filter product defect. Since the broad process failed, the runner did not execute its later isolated groups. Coverage was therefore not run.

*Historical status. Superseded by [Continuation — 2026-09-14](#continuation--2026-09-14).*

The work was performed on `test-suite-governance-integration-closeout-20260913`, in `D:/Projeler/hpc-client-gui-integration-closeout`, from governance SHA `18e59fff3d8ebfa47666347a0d9cfc4d137b43c1`. The completed governance worktree and the original dirty `develop` worktree were left untouched. This report describes closeout evidence and readiness, not merge or publication status.

## Native process findings

The earlier native termination is no longer reproduced by the latest official run. The release runner keeps the following process boundaries, with every test still selected:

| Boundary | Evidence | Runner treatment |
| --- | --- | --- |
| Corrective Jobs wx setup followed by Jobs-scroll | The combined wx/Qt sequence previously terminated with Windows `0xC000041D`; each test owner passes alone. | `tests/test_corrective_jobs_details.py` runs in its own pytest process. |
| WebView2 after the broad mixed-GUI process | The broad run previously hit heap corruption `0xC0000374` in `test_wx_terminal_external_navigation_blocked`; the exact node and 29-node module pass in isolation, and the terminal neighborhood passed 65 nodes. | `tests/test_wx_terminal_webview.py` runs in its own pytest process. |
| Embedded TextCtrl fallback | The controls suite had selected WebView2 but asserted the fallback model. Its detached/embedded owner also left a detached frame open. | The fallback suite explicitly disables WebView2, exercises the visible TextCtrl controls, closes the actual detached frame, and passes 9 tests with exit 0. |

The first two are documented native process boundaries, not skipped suites. The Jobs predecessor set is a reproduced candidate rather than a fully minimized polluter; the WebView2 predecessor set is also not fully minimized. Their evidence is in [`native-order-dependence-minimization.json`](../../audit/test-governance/integration-closeout-20260913/native-order-dependence-minimization.json). The ordered current runner groups are in [`release-process-order.json`](../../audit/test-governance/integration-closeout-20260913/release-process-order.json): 2,653 non-packaging nodes across the broad process and five isolated files.

The remaining broad-run wx error is different from the earlier process termination:

```text
tests/test_wx_files_sync_compare.py::test_wx_compare_close_in_flight_is_safe
PyNoAppError: The wx.App object must be created first!
```

It fails only in the broad process. The whole file passes alone (8 passed), and `test_wx_editor.py` followed by the file passes (22 passed). The exact polluting predecessor is not minimized, so this remains an unresolved order-dependent test-infrastructure failure. No selector change was used to hide it. The earlier broad-run editor close failure did not recur in the latest run.

## Confirmed product and lifecycle defects

| Defect | Current status | Evidence |
| --- | --- | --- |
| Local directory permission handling | Fixed in `src/hpc_gui/wx_local_files.py`; metadata is read once and a denied `stat` yields an unreadable entry without a second stat. | `test_list_entries_permission_error` passes and asserts one stat attempt. |
| Rename selection preservation | Passes; successful rename refresh selects the new path rather than relying on the old row index. | `test_rename_preserves_selection` passed in the current broad run. |
| Callback after destroyed remote Notebook | Fixed with closed-owner guarding and destroy-time unsubscribe. | `test_wx_embedded_remote_callback_after_notebook_destroy_is_ignored` added; lifecycle module passed 17 tests. |
| Jobs remote-read overlap | Fixed with per-output ownership and coalesced pending refresh. | Jobs-focused modules passed 50 tests; the invariant remains at most one active reader per output owner. |
| Plugin menu connected-to-hidden rebuild hang | Fixed through menu rebuild ownership/cleanup. | The isolated lifecycle owner passed twice; its 25-cycle rebuild test passed. |
| Remote provider Logs filter | **Confirmed, unfixed product defect.** | `test_wx_remote_navigation_sort_and_provider_filter_are_visible` expects visible `run.log` but the list is empty after selecting `logs`. `_entry_name` in `file_filter_registry.py` prefers `RemoteEntry.name == ""` to its populated path, so suffix matching sees no filename. Production changes for this new defect were not authorized. |

The Logs-filter failure is the first product fix required before merge. The test remains truthful and is not skipped or weakened.

## Screenshot and disabled-CI contracts

`audit/current-gui/MANIFEST.json` is explicitly historical at commit `3a7294079b992d3ddcabc349bbeadf6988312b64`; it is no longer required to match the current checkout SHA. The manifest gate verifies the historical commit exists and labels the evidence historical. The screenshot suite passes (5 passed).

Automatic GitHub Actions CI remains intentionally disabled; `.github/workflows/ci.yml` remains absent and `docs/ci-disabled/ci.yml` remains archival. The Wave 9 check now inspects that archived definition without claiming it is active. The manual release workflow remains `workflow_dispatch` only. No workflow was restored.

## Collection and taxonomy

| Measure | Count |
| --- | ---: |
| Frozen audit baseline | 2,673 |
| Previous remediation baseline | 2,678 |
| Completed governance snapshot | 2,656 |
| Current closeout collection | 2,657 |
| Collection errors | 0 |
| Net change from governance snapshot | +1 |

From the 2,656-node governance mapping, 15 nodeids have truthful successor names and one callback-lifecycle node was added. There are no unmapped removed nodeids. The exact list is in [`collection-delta.json`](../../audit/test-governance/integration-closeout-20260913/collection-delta.json).

| Primary category | Nodes |
| --- | ---: |
| unit | 760 |
| integration | 362 |
| gui | 673 |
| e2e | 7 |
| runtime_smoke | 6 |
| contract | 566 |
| audit | 159 |
| reporting | 22 |
| release | 102 |
| zero-primary | 0 |
| multi-primary | 0 |

The prior six zero-primary exceptions are absent from the current collection. The closeout ratchet uses an empty zero-primary allowlist and passes. No collected test is exempted.

Qualifier counts: `semantic=964`, `regression=163`, `performance=17`, `resource=120`, `concurrency=121`, `slow=15`, `subprocess=57`, `windows=4`, `linux=0`, `macos=0`, `hardware=0`, `synthetic_hardware=0`, `license=2`, `acceptance=1`, `artifact_dependent=25`, `wx=571`, `qt=270`, `packaging=4`.

## Latest authoritative release attempt

Command:

```text
python -X faulthandler scripts/release_test_suite.py
```

The runner exited **1** after its broad child completed in **1,401.99 seconds** (23m 21s): **2,399 passed, 2 failed, 20 skipped, 4 deselected, 29 subtests passed**. The two failures were:

1. `tests/test_wx_files_sync_compare.py::test_wx_compare_close_in_flight_is_safe` — unresolved broad-process wx App state/order failure described above.
2. `tests/test_wx_remote_file_actions_behavior.py::test_wx_remote_navigation_sort_and_provider_filter_are_visible` — confirmed Logs-filter product defect.

The runner stopped after the broad child failed. It did not execute the five later isolated file groups as one complete authoritative release run. No `--coverage` run was started because the normal release command did not exit 0. Coverage percentage and threshold result are therefore unavailable.

## Validation evidence

| Command or owner | Result |
| --- | --- |
| `python -m pytest tests --collect-only -q` | Exit 0; 2,657 collected in 4.16s. |
| `python scripts/check_test_taxonomy.py --mode report` | Exit 0; zero-primary 0, multi-primary 0; counts above. |
| `python scripts/check_test_taxonomy.py --mode ratchet --baseline audit/test-governance/integration-closeout-20260913/taxonomy-ratchet-strict.json` | Exit 0; zero-debt baseline, current zero 0, multi 0. |
| `python -m compileall -q src/hpc_gui` | Exit 0. |
| `python -m ruff check src tests scripts` | Exit 0 after correcting two lint findings in the closeout tests. |
| `python scripts/check_i18n.py` | Exit 0. |
| `python scripts/smoke_test.py` | Exit 0. |
| `git diff --cached --check` | Exit 0 for each staged changeset before its commit. |
| Screenshot audit suite | 5 passed. |
| Release-runner selector tests | 2 passed. |
| Archived Wave 9 wx smoke contract | 1 passed. |
| Embedded terminal fallback module | 9 passed; exit 0, no heap-corruption shutdown. |
| File-sync compare module alone | 8 passed in 25.60s; broad order remains unresolved. |
| Remote provider Logs filter | 1 failed as expected for the confirmed product defect. |

No current category median or p95 timing distribution was captured. The latest broad release duration and isolated file/module timings above are current evidence; older category timing data is not presented as final-SHA performance evidence.

## Release truth and decision

| Evidence area | Status |
| --- | --- |
| Automatic CI | Disabled intentionally. |
| Manual release workflow | Present, `workflow_dispatch` only. |
| Windows packaged smoke | FAIL/PARTIAL; no new artifact run. |
| GUI-TERM-001 parity | PARTIAL. |
| Linux packaged runtime | NOT EVIDENCED. |
| macOS packaged runtime | NOT EVIDENCED. |
| Live cluster | NOT EVIDENCED. |
| Manual packaged GUI sign-off | NOT EVIDENCED. |

**Merge readiness: NOT READY TO MERGE INTO DEVELOP.** The confirmed provider-filter defect and the broad-process wx App failure prevent an authoritative release-suite pass; coverage is not complete. Release readiness remains a separate NO-GO because packaged, cross-platform, cluster, and manual GUI evidence is incomplete.

## Continuation — 2026-09-14

Status: **READY TO MERGE INTO DEVELOP.** Both closeout blockers are resolved, the authoritative release suite and the coverage gate both exit 0, and the previously fixed defects are revalidated on the continuation HEAD. Release readiness remains a separate NO-GO (see below).

The continuation resumed the interrupted closeout on `test-suite-governance-integration-closeout-20260913` in `D:\Projeler\hpc-client-gui-integration-closeout`. Three commits were inherited from the interrupted run before this continuation started: `d47d04f9` (remote name fallback), `31a2aca4` (stress app ownership), and `09a4c014` (stress window cleanup). The historical sections above are preserved as recorded; the facts below supersede their decision.

### Remote provider Logs filter (resolved)

`_entry_name` in `src/hpc_gui/services/file_filter_registry.py` now returns a meaningful non-empty name when one exists and otherwise derives the display/filter name from the entry path (backslash-normalized, trailing slashes trimmed, basename only). Empty and whitespace-only names fall back to the path; Unicode and spaces are preserved and directory semantics are unchanged. The failing node was not modified and no special case was added for `run.log` or the Logs filter. `tests/test_file_filter_registry.py` adds dict-entry assertions for `{"name": "", "path": "/var/log/run.log"}` and a whitespace-name Windows path with a space and Unicode. The targeted node passes and all four broad/isolated release runs since include it in the passing set.

### wx application ownership (resolved)

Root cause: the C++ `wxApp` is process-global, and wxPython destroys that global object when any `wx.App` wrapper is deallocated by garbage collection, even when a newer app has replaced it. `tests/test_wx_files_sync_compare.py` created its app inside `_get_files_page()` without any owner, so the wrapper survived only through shell-frame cycles; a collection pass during a later test deallocated it, the live application was torn down, and `create_shell_frame` raised `wx._core.PyNoAppError: The wx.App object must be created first!`. An instrumented broad run recorded the application present at test setup and gone at teardown with no `wx.App.Destroy` call between, confirming the deallocation path. The interrupted run's stress-test ownership commits were necessary but not sufficient because they never gave the target module an owner; a run with only the target-module fixture still failed in two other modules, proving the pollution is suite-wide.

Fix, all in test infrastructure:

- `tests/conftest.py`: before a new `wx.App` is constructed, the app that is about to be replaced is destroyed while it is still the current app. This keeps at most one live native application and removes the abandoned-wrapper time bomb. No test is skipped, renamed, retried, or weakened.
- `tests/test_wx_files_sync_compare.py`: a module-scoped autouse `wx_app` fixture owns and destroys the application for the module and cleans up module-created windows; `_get_files_page()` requires the fixture-owned application instead of creating an unowned one.
- Regression node `tests/test_wx_files_sync_compare.py::test_wx_files_sync_app_survives_forced_collection` (`gui` primary; `regression`, `resource`, `semantic`, `wx` qualifiers) builds a shell, closes it, drops every strong reference, forces `gc.collect()`, asserts the module-owned application is still current, then builds a second shell. Removing the module fixture restores ad-hoc creation and fails the ownership regression. Evidence is in [`wx-app-order-minimization.json`](../../audit/test-governance/integration-closeout-20260914/wx-app-order-minimization.json).

### Previously confirmed defects revalidated on continuation HEAD

| Defect | Owner run | Result |
| --- | --- | --- |
| Local directory permission handling | `test_list_entries_permission_error` (+ rename selection and destroyed-Notebook callback) | 3 passed, exit 0 |
| Rename selection preservation | same focused run | 3 passed, exit 0 |
| Callback after destroyed remote Notebook | same focused run | 3 passed, exit 0 |
| Jobs remote-read overlap | `test_wx_jobs_behavior`, `test_wx_jobs_files_outputs`, `test_wx_jobs_final_fix`, `test_wx_jobs_stress` | 50 passed, exit 0 |
| Plugin-menu rebuild hang | `tests/test_hardening_additional.py` (includes the 25-cycle rebuild owner) | 12 passed, exit 0 |
| Remote empty-name filtering | targeted node + `tests/test_file_filter_registry.py` | 23 passed, exit 0 |

### Latest authoritative release attempt (continuation)

Command:

```text
python -X faulthandler scripts/release_test_suite.py
```

Exit **0**; `[release-test-suite] all release preflight gates passed`. Preflight: `compileall`, `check_i18n.py`, `smoke_test.py` all exit 0.

| Group | Result |
| --- | --- |
| Broad pytest (`-m "not packaging"`, five isolated files ignored) | **2,402 passed, 0 failed, 20 skipped, 4 deselected, 29 subtests passed** in 1,484.25 s (24m 44s) |
| `tests/test_ftp_widget.py` | 168 passed in 14.63 s |
| `tests/test_download_cancel_wire.py` | 4 passed in 13.39 s |
| `tests/test_editor_flow.py` | 14 passed in 0.50 s |
| `tests/test_corrective_jobs_details.py` | 17 passed in 8.67 s |
| `tests/test_wx_terminal_webview.py` | 29 passed in 24.14 s |

### Authoritative coverage (continuation)

Command:

```text
python scripts/release_test_suite.py --coverage
```

Exit **0**; `Required test coverage of 65% reached. Total coverage: 66.38%`. Broad child: 2,402 passed, 0 failed, 20 skipped, 4 deselected, 29 subtests passed in 1,470.31 s; isolated groups passed with coverage appended (168 / 4 / 14 / 17 / 29). Coverage artifacts `coverage.json` and `coverage.xml` were written by the runner.

### Collection and taxonomy (continuation)

| Measure | Count |
| --- | ---: |
| 2026-09-13 closeout collection | 2,657 |
| 2026-09-14 continuation collection | 2,658 |
| Net delta | +1 |
| Zero-primary | 0 |
| Multi-primary | 0 |
| Semantic qualifier | 965 |
| Collection errors | 0 |

The only added node is the ownership regression described above; nothing was removed or renamed. The zero-debt ratchet against [`taxonomy-ratchet-strict.json`](../../audit/test-governance/integration-closeout-20260913/taxonomy-ratchet-strict.json) passes. The exact delta is in [`collection-delta.json`](../../audit/test-governance/integration-closeout-20260914/collection-delta.json).

### Validation evidence (continuation)

| Command or owner | Result |
| --- | --- |
| `python -m pytest tests --collect-only -q` | Exit 0; 2,658 collected in 2.69 s. |
| `python scripts/check_test_taxonomy.py --mode report` | Exit 0; zero-primary 0, multi-primary 0, warnings 0. |
| `python scripts/check_test_taxonomy.py --mode ratchet --baseline audit/test-governance/integration-closeout-20260913/taxonomy-ratchet-strict.json` | Exit 0; RATCHET: PASS. |
| `python -m compileall -q src/hpc_gui` | Exit 0. |
| `python -m ruff check src tests scripts` | Exit 0; all checks passed. |
| `python scripts/check_i18n.py` | Exit 0. |
| `python scripts/smoke_test.py` | Exit 0. |
| `git diff --check` | Exit 0. |
| Ownership regression with aggressive GC plugin | 9 passed, exit 0 (target module). |
| Affected-module neighborhood with the suite guard | 78 passed, exit 0. |

### Release truth and decision (continuation)

| Evidence area | Status |
| --- | --- |
| Automatic CI | Disabled intentionally; not restored. |
| Manual release workflow | Present, `workflow_dispatch` only. |
| Windows packaged smoke | FAIL/PARTIAL; no new artifact run. |
| GUI-TERM-001 parity | PARTIAL. |
| Linux packaged runtime | NOT EVIDENCED. |
| macOS packaged runtime | NOT EVIDENCED. |
| Live cluster | NOT EVIDENCED. |
| Manual packaged GUI sign-off | NOT EVIDENCED. |

**Merge readiness: READY TO MERGE INTO DEVELOP.** The authoritative release suite exits 0, the coverage gate exits 0 at 66.38% against the 65% threshold, collection is clean with zero-primary 0 and multi-primary 0, both closeout blockers are fixed with regression evidence, and all previously confirmed defects remain fixed on the continuation HEAD. Release readiness remains a separate NO-GO because packaged, cross-platform, cluster, and manual GUI evidence is still incomplete.
