# R14 Native Crash Isolation Follow-up

Date: 2026-11-18  
Repository: `mskomek/hpc-client-gui`  
Worktree: `D:\Projeler\.tmp\hpc-client-gui\x11-kole-acceptance`  
Branch: `codex/x11-active-terminal-kole-20261114`  
HEAD: `669b00be0ab6577fb1684354b7d5de2ee5534fbd`

## Result

The R14 WebView native crash is reproducible as a **same-process wx test-order failure**. The external-navigation WebView test passes repeatedly by itself, then crashes when run after the R14 wx Jobs test sequence. Changing the event-pump variant to `wx.Yield()` avoids the native crash in the recorded sample but never receives WebView2 `ready`, so it is not a passing workaround.

The suspected trigger is the wx Jobs “follow file” UI lifecycle immediately before WebView2 creation. A minimal-prefix matrix points to that test as a contributor, but its effect is intermittent and the complete three-test prefix is the only sequence that crashed in every repeat. The exact C++ ownership/event callback causing the access violation is **not proven**; no native dump or C stack was captured. The native root cause remains **OPEN**. No production or test source was changed during this follow-up.

## Source and environment

- Diagnostic snapshot identity from the R14 report: source archive SHA-256 `0b45fac5182937d28024ae203a9ffff205c4ae6e73fc1f16fd95a689accf2e87`; composite ID `1a6b6e1f447d5daab8673fa7027067b988b34f562529c97cccf9e563a94b09ba`.
- Test overlay identities: `tests/conftest.py` SHA-256 `9822feaa5c7bf66903d86f3da29041df14af33e97d7a63d27ca4a104aaae5a687`; `tests/wx_terminal_webview_support.py` SHA-256 `972c9f3d0c313a473fab4e2421f0c39c725c37bd1b51ee9a8e0bd49ab99d59ad`.
- Runs used Kole Windows11-New in interactive Session 1, Python 3.14.7, and the existing wx WebView2 backend. Every wrapper recorded Session ID 1.
- The test order was: `test_files_follow_menu_has_following_check` in `test_wave80_files_outputs.py` (A), `test_wave78_tabs_still_work` (B), `test_files_follow_menu_has_following_check` in `test_wave80_files_outputs_audit_behavior.py` (C), then `test_wx_terminal_external_navigation_blocked` (target).
- Full pytest was **not run**. These were focused diagnostic runs only.

## Controlled results

| Prefix before the WebView test | Event pump | Runs | Result |
|---|---|---:|---|
| None | Existing `GUIEventLoop` + `EventLoopActivator` | 5 | 5 PASS; each target test exited 0 |
| None | `wx.Yield()` diagnostic variant | 5 | 5 assertion failures because `_ready` stayed false; 0 native crashes |
| A, B, C | Existing nested loop | 5 | 5 native crashes: four `0xC0000005`, one `0xC0000374` |
| A, B, C | `wx.Yield()` diagnostic variant | 5 | 5 assertion failures because WebView2 did not report ready; 0 native crashes |
| A | Existing nested loop | 3 | 2 PASS, 1 `0xC0000005` |
| B | Existing nested loop | 3 | 3 PASS |
| C | Existing nested loop | 3 | 3 PASS |
| A, B | Existing nested loop | 3 | 3 PASS |
| A, C | Existing nested loop | 3 | 2 PASS, 1 `0xC0000374` |
| B, C | Existing nested loop | 3 | 3 PASS |

The isolated target emits `1 passed`; passing prefixes emit 2 or 3 passed as expected. The `wx.Yield()` variant is not accepted as a fix because it fails the WebView readiness assertion. The matrix is evidence of order sensitivity, not proof that any one prefix is the sole root cause.

Faulthandler places the native failures inside `tests/wx_terminal_webview_support.py::_wait_for_ready`, at `GUIEventLoop.Dispatch()` or when the `EventLoopActivator` is released. The three preceding tests create and close wx Jobs windows; the follow-file case also invokes the manual output follower and its asynchronous refresh path. The earlier state observer recorded the same retained `wx.App` and no top-level wx windows or Python threads at target setup. Those observations narrow the failure but do not identify the invalid native reference.

## Dump and remote cleanup

- A per-user WER `LocalDumps` setting was enabled temporarily for the test Python process and removed after the runs. No dump files were produced.
- No ProcDump process was run and no license was accepted. ProcDump is not installed on the guest; the downloaded local package was verified as Microsoft-signed, but execution requires accepting its EULA. User authorization is pending before using it for a one-time diagnostic capture.
- All diagnostic `HPC_GUI_R14CONT_*` scheduled tasks created for this follow-up were unregistered. The temporary WER registry key, diagnostic processes, staged harness directory, and probe scripts were removed. Pre-existing R14 tasks and unrelated Session 1 processes were left untouched.

## Evidence

Raw focused outputs, runner receipts, and reproducible harnesses are in [controlled-loop-variants-20261118](evidence/r14-final-repair/native-crash-debug-20261118/followup-20261118/controlled-loop-variants-20261118/). Its `SHA256SUMS.txt` verifies 132 files. `summary.json` contains per-run exit codes, session IDs, pytest summaries, exception codes, archive hashes, and source identities.

The initial R14 evidence repair is documented in [R14_EVIDENCE_REPAIR_VERIFICATION_20261118.md](R14_EVIDENCE_REPAIR_VERIFICATION_20261118.md). Its earlier verdict remains `EVIDENCE_INCONSISTENT`; this follow-up does not upgrade that verdict or establish X11 implementation acceptance.

## Next debugging step

If ProcDump use is authorized, capture a small crash dump from one controlled A+B+C+target Session 1 run, inspect only exception context and native module/frame data, then remove the raw dump. Otherwise continue with test-level lifecycle instrumentation without claiming a native C++ root cause. Only after the triggering callback/teardown is established should a focused lifecycle change be considered. Then rerun the minimal reproduction and the relevant wx/WebView regression group before any full-suite run.

## Current status

- R14 audit/evidence repair commit: `669b00be0ab6577fb1684354b7d5de2ee5534fbd` (local only; no push).
- Source changes: none in this follow-up.
- Focused WebView tests: **order-sensitive native crash remains**.
- Full pytest: **NOT RUN**.
- Exact native C++ root cause: **OPEN**.
- GitHub/PR state: unchanged.
