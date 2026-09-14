# Final Integration Readiness Report — 2026-09-14

Repository: `https://github.com/mskomek/hpc-client-gui`
Working branch: `test-suite-governance-20260912` at `d400b952f88152d333eb15b52995b64830f60a0a` (pushed)
Target integration branch: `develop` at `12ce79935bf076e1062c57dc7dbd148bad2bfae1` (unchanged)
Session scope: local test suite, Windows native process forensics, integration readiness. CI out of scope.

## New-session state recovery

- Last known HEAD from the prior session: `18e59fff3d8ebfa47666347a0d9cfc4d137b43c1`
- Actual starting state (repository was ahead of the prompt):
  - `D:\Projeler\TrubaGUI` (stated working dir): detached at `1ce1421a` — a separate main-line workstream dirty with terminal/update work from 2026-08-27…29. Left untouched.
  - `hpc-client-gui-test-governance` and `hpc-client-gui-final-remediation`: `test-suite-governance-20260912` at `108cf4e8` (13 unpushed remediation commits; 15 uncommitted files, newest 03:57 on 2026-09-14).
  - `hpc-client-gui-integration-closeout`: `test-suite-governance-integration-closeout-20260913` at `09a4c014` (clean; 11 commits after `18e59fff`, 8 pushed as `21ff7d55`, 3 local).
  - `develop` local at `1de2dce3` (11 unpushed commits from 2026-09-12, untouched); `origin/develop` at `12ce7993`.
- Remote governance HEAD before/after this session: `18e59fff` → `d400b952` (fast-forward push). `origin/develop` unchanged.
- Commits discovered after `18e59fff`: 13 governance-line commits (`50f4b001`…`108cf4e8`), 11 closeout-line commits (`06e59b8c`…`09a4c014`), 11 develop-local commits (`ccfeb1b8`…`1de2dce3`), plus v2/v3/v4 baseline branch tips.
- Uncommitted changes discovered (classified complete consolidation work): 15 files in the governance worktree (`wx_jobs.py` and `wx_directories_view.py` close propagation, `release_test_suite.py` extra isolation, 8 test files, 4 docs/evidence files) — committed as `bee43f44`; identical `GUI_TERM_001` edit in the test-governance worktree; closeout clean; develop worktree dirty artifacts left untouched.
- Recovered test/crash artifacts: Windows Error Reporting history, 10 `python.exe.*.dmp` files in `%LOCALAPPDATA%\CrashDumps` (latest 2026-09-14 00:30:16), `.integration-recovery/` source snapshot, `audit.zip`, `waves.zip`, `docs/TEST_SUITE_AUDIT_REPORT_12ce7993.md`, both worktrees' `.pytest_cache/v/cache/lastfailed`, and release-runner logs. `.tmp/` does not exist in any governance worktree and was not modified.

## Interrupted work progress

| Task | Status | Evidence | Remaining work |
|------|--------|----------|----------------|
| A. Reproduce broad-suite native termination | DONE | WER history; runner terminations 22:32/23:20; native pair reproduced this session ×3 | — |
| B. Last successfully completed test | DONE | Final broad runs completed: 2,352 passed / 0 failed (×2) | — |
| C. Active test during crash | DONE | `test_jobs_outputs_scroll.py::test_all_follow_windows_preserve_fake_tail_scroll_positions` (setUp) for the wx→Qt boundary | Exact node for the 23:20 no-WER exit remains unknown |
| D. Pytest phase | DONE | setup (unittest `setUp`, line 32 `processEvents`) | — |
| E. Process exit code | DONE | `-1073740771` (0xC000041D) for the boundary; `0xFFFFFFFF` for the no-WER 23:20 exit | — |
| F. Windows exception code | DONE | 0xC000041D, 0xC0000005, 0xC0000374 | — |
| G. Faulting module | DONE | `wxmsw333u_core_vc140_x64.dll` offset 0x569d1; `ntdll.dll` heap corruption | — |
| H. faulthandler | DONE | `-X faulthandler` plus `PYTHONFAULTHANDLER=1` on all final runs; stack captured | — |
| I. WER / Event Viewer | DONE | Queried; no events during final suites; events only for earlier crashes and deliberate repro | — |
| J. Crash dumps | DONE | 10 dumps recorded; not committed | — |
| K. Test-order bisection | DONE | Roaming failures narrowed to duplicate-`wx.App` aliasing; wx→Qt pair minimized | — |
| L. Contaminating predecessor module | PARTIAL | Native-boundary predecessors documented and isolated; orphan-`App` producer not individually named | Follow-up only |
| M. Contaminating predecessor node | PARTIAL | Not node-minimized; eliminated systemically | Follow-up only |
| N. Minimal reproducer | DONE | Exact commands below; native pair reproduced ×3; alias probe deterministic | — |
| O. wx object lifecycle audit | DONE | 31 modules adopt a single App; owned-only destroy; layout ownership fixed | — |
| P. Qt/wx coexistence audit | DONE | Classified as runtime-isolation defect; runner keeps Qt-before-wx order and isolates proven files | — |
| Q. Production edits | DONE | 5 files consolidated (see Fix) | — |
| R. Test fixture edits | DONE | 31 modules plus layout ownership and runner selectors | — |
| S. Order-dependence regression | DONE | Runner selector contract test with explicit expected isolation tuple; subprocess regressions retained | — |
| T. Reproducer repeated | DONE | Previously failing fixture cluster 3× post-fix; stabilized probe 3/3 | — |
| U. Normal release suite | DONE — PASS (exit 0) | 2,352 passed / 0 failed broad; all isolated partitions pass | — |
| V. Coverage release suite | DONE — PASS (exit 0) | 66.41 % ≥ 65 % gate | — |
| W. Final governance docs | DONE | Closeout report, PHASE_2, taxonomy report, zero-primary disposition, cleanup Wave updated; history preserved | — |
| X. Final merge-readiness audit | DONE | Verdict below | Follow-ups noted |

## Native crash

- Exact reproducer (documented toolkit boundary): `python -X faulthandler -m pytest tests/test_wx_jobs_behavior.py tests/test_jobs_outputs_scroll.py -vv -s` → exit `-1073740771` (0xC000041D), WER faulting module `wxmsw333u_core_vc140_x64.dll` (offset 0x569d1).
- Last completed test: all 9 `test_wx_jobs_behavior` tests passed. Active test: `test_jobs_outputs_scroll.py::JobsOutputsScrollTests::test_all_follow_windows_preserve_fake_tail_scroll_positions`.
- Pytest phase: **setup** (`_NavigableTextEdit` + `app.processEvents()`); crash inside Qt event processing with wx native state live.
- Process exit code: `-1073740771` (0xC000041D). The earlier runner termination `4294967295` (0xFFFFFFFF) produced **no WER event** and is not claimed as a recorded native exception.
- Exception codes: `0xC000041D`, `0xC0000005` (wx core), `0xC0000374` (ntdll heap corruption).
- Faulting modules: `wxmsw333u_core_vc140_x64.dll`; WebView `wxmsw333u_webview_vc140_x64.dll`.
- Crash dump available: yes (10 historical dumps); the deliberate repro generated additional dumps; none committed.

## Minimal contaminating sequence

Native toolkit boundary (unsupported suite order):

```
python -X faulthandler -m pytest tests/test_wx_jobs_behavior.py tests/test_jobs_outputs_scroll.py -vv -s
```

Deterministic `wx.App` alias mechanism (probe, reproduced exactly):

```
python -c "import wx, gc; a=wx.App(False); b=wx.App(False); del a; gc.collect(); print(wx.App.Get()); wx.Frame(None)"
# wx.App.Get() -> None; wx.Frame -> PyNoAppError
```

## Root cause

**MULTIPLE_CAUSES** — no product defect proven:

1. `TEST_FIXTURE_LIFECYCLE_DEFECT` — 31 test modules unconditionally created `wx.App(False)` while an App was alive; destroying or garbage-collecting the orphaned non-global App invalidates the global app (`wx.App.Get()` becomes `None`), producing roaming `PyNoAppError` in different modules across runs. Proven by the probe above.
2. `GUI_RUNTIME_PROCESS_ISOLATION_DEFECT` — wx and Qt in one process; a wx module running before the Qt Jobs-scroll module terminates Windows with 0xC000041D inside wx core despite no live windows. Proven by the minimal pair (×3); mitigated by runner ordering plus documented process isolation.

The 23:20 governance-runner termination had no WER event and is not attributed to a native exception.

## Fix

- Production files (consolidated; unchanged by the final docs commits): `services/file_filter_registry.py`, `wx_local_files.py`, `wx_remote_files_view.py`, `wx_jobs.py`, `wx_directories_view.py`.
- Test files: 46 changed vs `18e59fff`. This session added single-App adoption across 31 modules, `test_wx_layout_resize.py` owned-only teardown, the stabilized Qt delay probe (QEventLoop + explicit `blocked` assertion), and release-runner isolation for `test_wx_jobs_behavior.py` and `test_wx_layout_resize.py`.
- Lifecycle behavior changed: exactly one `wx.App` exists at a time; apps are destroyed only by their owner; order-sensitive GUI owners run in dedicated processes with all nodes still selected.

## Reproducer validation

- Victim alone: `test_jobs_outputs_scroll.py` → 20 passed + 4 subtests.
- Predecessor alone: `test_wx_jobs_behavior.py` → 9 passed.
- Combined: `0xC000041D` native termination — a documented unsupported toolkit order; the release runner never executes it (Qt scroll precedes all wx modules and the owners are isolated).
- 3-run result: previously failing fixture cluster (transfer-integration + file003 + files-sync + jobs-behavior + layout-resize) passed 59/59 three times; stabilized probe 3/3.

## Regression validation

- Jobs output concurrency: 4 modules, 50 passed (no-overlap, coalescing, stale A→B, error recovery, close with queued refresh).
- Plugin menu lifecycle: exact node passed twice; hardening + plugin modules 65 passed (25-cycle Unicode visible/hidden cycles).
- wx resource sweep: 52 passed, no `UnregisterClass`/open-window warnings; merged module batch 63 passed; WebView 29, corrective Jobs 17, stress nodes 1+1, FTP 168, download-cancel 4, editor flow 14.

## Normal release suite

| Result | Passed | Failed | Skipped | XFail | XPass | Duration |
|---|---|---|---|---|---|---|
| PASS (exit 0) | 2,637 (2,352 broad + 285 isolated) | 0 | 20 | 0 | 0 | broad 899.04 s; runner 14:34:03–14:59:57 |

## Coverage release suite

| Result | Passed | Failed | Skipped | XFail | XPass | Duration |
|---|---|---|---|---|---|---|
| PASS (exit 0) | 2,637 | 0 | 20 | 0 | 0 | broad 778.73 s; runner ~29 m 41 s; `Required test coverage of 65% reached. Total coverage: 66.41%` |

## Taxonomy

- Total: 2,661 (unit 762, integration 362, gui 675, e2e 7, runtime_smoke 6, contract 566, audit 159, reporting 22, release 102)
- Zero-primary: 0
- Explicit exceptions: none remaining — the six prior baseline exceptions were directly resolved by passing successor tests with exactly one primary marker
- Multi-primary: 0; direct-test-call and catch-all warnings: 0
- RATCHET: PASS (strict zero-debt baseline, empty allowlist); artifact `audit/test-governance/integration-closeout-20260913/taxonomy-report-post-consolidation.json`

## Remaining non-CI blockers

- Release readiness only (separate from integration): Windows packaged smoke FAIL/PARTIAL, GUI-TERM-001 partial, Linux/macOS packaged runtime not evidenced, live cluster not evidenced, manual packaged GUI sign-off not evidenced.
- Follow-up: no node-minimized predecessor for the orphan-`App` producer (eliminated systemically); the unsupported wx→Qt order remains a documented toolkit boundary; concurrent sessions on the shared Windows host remain a hazard for future runs.

## Independent audit

**PASS WITH FOLLOW-UP** — state reconstruction verified; mechanisms proven; suites complete with 0 failures and no native events; selection completeness verified (2,657 non-packaging = 2,372 broad + 285 isolated, no overlap); no xfail, no sleep workarounds, no broad exception swallowing; branch clean and pushed. The only WER events observed after the suites came from the deliberate forensic re-reproduction of the documented unsupported wx→Qt order (explicitly not a suite run).

## Final integration verdict

**READY TO MERGE** — for `test-suite-governance-20260912` (`d400b952`) into `develop`. No merge or `develop` ref movement was performed; `origin/develop` remains `12ce7993`.
