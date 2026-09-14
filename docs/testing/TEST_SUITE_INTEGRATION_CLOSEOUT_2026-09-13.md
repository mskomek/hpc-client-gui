# Test Suite Integration Closeout — 2026-09-13

Status: **SUPERSEDED BY THE POST-CONSOLIDATION VALIDATION ON 2026-09-14 (below).** The 2026-09-13 state recorded in this document — DEFECT_FOUND, NOT READY TO MERGE — was accurate for that day's closeout branch: the runner reached the end of its broad pytest process without a native process termination, but that process reported an unresolved wx application-order failure and a confirmed remote Logs-filter product defect, and coverage had not been run.

For the current state see [Post-consolidation final validation — 2026-09-14](#post-consolidation-final-validation--2026-09-14).

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

## Post-consolidation final validation — 2026-09-14

The closeout branch (`test-suite-governance-integration-closeout-20260913`, tip `09a4c014`) was merged into `test-suite-governance-20260912` (merge commit `006982d0`), combining the closeout product fixes, workflow/evidence contracts, and native boundaries with the governance remediation commits and its uncommitted lifecycle hardening (committed as `bee43f44`). Follow-up commits on the governance branch: `39ae798c` (order-sensitive owners isolated; layout app ownership fixed), `01225f59` (single-App fixture ownership across 31 test modules), `b018f10b` (Qt event-loop delay probe stabilized). All local; `origin/develop` remains at the frozen baseline.

### Root cause of the roaming `PyNoAppError`

The broad mixed-GUI process failed with `wx._core.PyNoAppError` in different modules across runs (`test_wx_jobs_behavior`, `test_wx_layout_resize`, then `test_wx_files_sync_compare`). The mechanism was reproduced in isolation: creating a second `wx.App` while one is alive, then destroying or garbage-collecting the non-global App, invalidates the global app (`wx.App.Get()` becomes `None`) even though the global Python object still exists. Any later widget creation then raises `PyNoAppError`. Thirty-one test modules had fixtures that unconditionally created `wx.App(False)`; they now adopt the existing App and create one only if none exists, so a single App exists at any time. `tests/test_wx_layout_resize.py` additionally no longer destroys an app it did not create. The Jobs-behavior and layout-owner modules remain process-isolated in the release runner as documented order-sensitive GUI boundaries; every node still runs.

### Final local results

| Run | Result | Detail |
| --- | --- | --- |
| `python -X faulthandler scripts/release_test_suite.py` | **PASS (exit 0)** | Broad pytest: **2,352 passed, 0 failed**, 20 skipped, 6 deselected, 29 subtests in 899.04 s. Isolated partitions: file-actions node 1, shell-p0 stress node 1 (258.87 s), corrective Jobs details 17, WebView 29, jobs behavior 9, layout resize 1 (158.60 s), jobs files outputs 16, jobs final fix 15, jobs stress 10, FTP 168, download-cancel wire 4, editor flow 14. |
| `python -X faulthandler scripts/release_test_suite.py --coverage` | **PASS (exit 0)** | Broad pytest: **2,352 passed, 0 failed**, 20 skipped, 6 deselected, 29 subtests in 778.73 s; `Required test coverage of 65% reached. Total coverage: 66.41%`. |
| Windows native events | None | No `python.exe` Application Error events and no new crash dumps during the final runs (2026-09-14 14:34–15:39). The earlier signatures (`0xC000041D`, `0xC0000005`, `0xC0000374`) did not recur. |
| `python -m compileall -q src/hpc_gui` | PASS | exit 0. |
| `python -m ruff check src tests scripts` | PASS | exit 0. |
| `python scripts/check_i18n.py` | PASS | all three checks OK. |
| `python scripts/smoke_test.py` | PASS | exit 0. |
| Taxonomy REPORT | PASS | **2,661 collected** (unit 762, integration 362, gui 675, e2e 7, runtime_smoke 6, contract 566, audit 159, reporting 22, release 102); **zero-primary 0**, multi-primary 0, warnings 0. Artifact: `audit/test-governance/integration-closeout-20260913/taxonomy-report-post-consolidation.json`. |
| Taxonomy RATCHET (strict zero-debt baseline) | PASS | zero-primary baseline 0, current 0, new 0, multi 0. |
| Full collection | PASS | 2,661 collected in 4.26 s. |

The six prior zero-primary baseline exceptions were directly resolved: their workflow/evidence successors now pass with exactly one primary marker and are no longer exempted, so the strict zero-debt ratchet applies.

### Decision

**Integration verdict: READY TO MERGE INTO DEVELOP** for the test-suite governance and remediation work on `test-suite-governance-20260912`. Release readiness remains a separate NO-GO: packaged smoke, Linux/macOS packaged runtime, live-cluster, and manual packaged GUI evidence are still not evidenced, as in the table above. No merge to `develop` was performed.
