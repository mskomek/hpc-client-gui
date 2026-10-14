# Candidate 5 Final Closure — 2026-10-09

## Final verdict

`FINAL_BLOCKED_EXTERNAL_WINDOWS11_GUEST_ACCEPTANCE`

The repair and native test gates completed. The repair-validation build was created and hashed. The canonical Windows11 runner confirms the guest is reachable as `test\home`, but its non-default remote scriptblock used to run the packaged fresh-user acceptance did not return within the bounded invocation. No guest GUI acceptance, ordinary packaged repetition, or Candidate 6 freeze is claimed. Candidate 5 remains unchanged. No push was made.

## Identity

- Verified baseline: `b0c6c65e2d9832937a5fd841573a0a99dc1f7a2f`
- Main checkout: `develop`, HEAD remains the baseline above; unrelated dirty files were left untouched.
- Final branch/worktree: `codex/c5-final-closure`, `D:\Projeler\.worktrees\hpc-c5-final`
- Candidate 5 EXE SHA-256: `2966a977edc0fe5525c8591df6108e731cd944e2b9d396ee72847792afca654c`
- Candidate 5 archive SHA-256: `7ae23f2d6cea49d4c4b422dacdf88cbac8eba7f43aff58a44e0c92a041d7e953`
- Candidate 5 original source HEAD: `1292e89b0d383d2cd08cdae759ee57d336dfb070`

## Root cause

- Primary fresh-user defect: the connection worker invoked shell `on_connected` and mutated wx-backed terminal/jobs/files/directories state off the GUI thread. The repair keeps transport/session creation on the worker and transfers the result with `wx.CallAfter`; GUI attach and cleanup are guarded to happen once.
- Native AV: best supported classification is `TEST_PROCESS_ISOLATION_ROOT_CAUSE`. W19 was in the broad pytest interpreter despite using real wx/WebView lifecycle and intentionally avoiding shared `wx.App.Destroy()`. Moving W19 to the existing isolated partition passed 3/3 fresh processes and the canonical isolated W19 partition also passed. No product native lifecycle fault was established.
- WebView harness: terminal child processes reused the same inherited WebView2 data folder. S2 gave each native child a unique profile; all three modified runs passed. This was test-harness hygiene, not a product timing fix.
- B/C/D timing ablations were not integrated.

## Subagents

- S1: `S1_ISOLATION_JUSTIFIED` — W19 meets existing native process-isolation criteria; added isolated selector and partition regression.
- S2: `S2_HYGIENE_FIX_READY` — unique WebView2 profile per child; three supervisor runs passed.
- S3: `KEEP` — no correctness defect found in the common repair; no timing changes.
- S4: prepared ownership diagnostics. PowerShell event-query/launch behavior was unreliable, so the final gate used a Python `psutil` evidence wrapper (`scripts/run_native_gui_gate.py`) that attributes WER only to observed process ancestry or the exact unique profile. No product files were changed by S4.

## Changes and commits

1. `15377b05` — `fix: marshal fresh smoke session attach to wx thread`
   - `src/hpc_gui/wx_shell_smoke_session.py`
   - `src/hpc_gui/wx_shell_fresh_smoke.py`
   - `src/hpc_gui/wx_shell_connections.py`
   - `tests/test_wx_smoke_session_thread_affinity.py`
2. `602ed9985634994a4d48655ae1fd4e37e8c9dd43` — `test: isolate native wx lifecycle boundaries`
   - `scripts/release_test_suite.py` and `tests/test_release_test_suite.py`: W19 is excluded from bulk and selected as its own isolated process; regression checks the partition contract.
   - `tests/test_wx_terminal_webview.py`: each child receives a unique WebView2 profile.
   - `scripts/run_native_gui_gate.py`: run-scoped process/profile/WER evidence wrapper, outside product runtime.

## Native ownership and tests

All wx/WebView tests ran serially under the supervisor. Cleanup targeted only observed WebView2 processes carrying the exact run profile path; unrelated Edge and other applications were not touched.

- Reference terminal suite: 29/29 PASS.
- S2 terminal hygiene: 29/29 PASS in each of 3 fresh processes; `E_ABORT=0`, readiness failures=0, run-owned WER=0.
- Release partition + thread-affinity tests: 6 passed.
- W19 isolated: 20/20 PASS in each of 3 fresh processes; run-owned WER=0.
- Packaged/fresh parent and raw runtime tests: 16 passed.
- W15 fresh-user suite: 11 passed.
- Canonical release suite: run once. Native-owned WER `0`; `0xC0000005=0`, `0xC000041D=0`, `0xC0000409=0`; no `E_ABORT`, `wxRecursionGuard`, or `WindowDestroyEvent` findings. Bulk collection was blocked by an existing Wave import error (`phase_job` missing from `tests/test_wave_controller_regressions.py`). `tests/test_download_cancel_wire.py` had 2 failures / 2 passes because the server connection dropped before cancellation triggered. Other completed partitions passed, including terminal 29/29 and isolated W19 20/20. These unrelated non-native failures were not changed.
- Bounded fallback bisection: not used; no canonical native crash occurred.

## Repair-validation build

- Name: `candidate5-repair-validation`
- Source commit: `602ed9985634994a4d48655ae1fd4e37e8c9dd43`
- EXE: `D:\Projeler\.tmp\hpc-client-gui\candidate5-repair-validation\dist\hpc-client-gui\hpc-client-gui.exe`
- EXE SHA-256: `bcaf831603c3526d9a801f91c72b670b915bcacf0eab0643fd421026b68d4f63`
- Archive: `D:\Projeler\.tmp\hpc-client-gui\candidate5-repair-validation\candidate5-repair-validation.zip`
- Archive SHA-256: `d21a7be26635632b97923423af58e15bc95c7bfced35c3eed6399b5f6d99bd97`
- Python 3.12.4; PyInstaller 6.19.0; wxPython 4.3.1 / wxWidgets 3.3.3.
- Manifest: `D:\Projeler\.tmp\hpc-client-gui\candidate5-repair-validation\manifest.json`

## Windows11 guest and packaged acceptance

- Canonical runner basic identity check passed: hostname `test`, identity `test\home`.
- Full guest fresh-user GUI harness did not complete through the bounded custom PowerShell Direct scriptblock invocation. Therefore guest runs 1–3 are `NOT RUN`; no guest PASS is claimed.
- Ordinary packaged repetition: `NOT RUN` because fresh guest acceptance was not completed.
- Candidate 6: not created; its acceptance prerequisites are unmet.

## Cleanup and evidence

- Archived local repair-ablation and native-ablation evidence before cleanup; SHA-256 values are retained in the local evidence directory and archive report.
- S1–S4 reports and native run manifests/logs are retained under `D:\Projeler\.tmp\hpc-client-gui\candidate5-final\`.
- Test-owned WebView2 survivors under unique run profiles were terminated after each run; unrelated WebView2 processes were left alone.
- WPR was idle; no WPR trace or LocalDumps override was created by this turn.
- Final branch/worktree is retained. S1–S4 temporary worktrees and branches were removed after the report bundle was archived.
- Combined evidence bundle: `D:\Projeler\.tmp\hpc-client-gui\candidate5-final\CANDIDATE5_FINAL_EVIDENCE_20261009.zip`.
- Main checkout unrelated dirty state remains unchanged; no merge/cherry-pick was performed.
- Push: `NO`.
