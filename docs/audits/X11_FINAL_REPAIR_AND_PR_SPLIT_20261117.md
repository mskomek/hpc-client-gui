# X11 Final Repair and PR Split

Date: 2026-11-18  
Worktree: `D:\Projeler\.tmp\hpc-client-gui\x11-kole-acceptance`  
Branch: `codex/x11-active-terminal-kole-20261114`  
HEAD: `c26fcac1cea56e37bd2683c73b11a5a5240be984`  
Base: `339b86bada84504d2d02af002fad6b6af13777a5`

## Decision

**Delivery remains BLOCKED.** The shutdown failure reported by the earlier harness was not reproduced when `WM_CLOSE` was sent to the confirmed main window: three idle runs and one connected/reconnected GUI run exited naturally with native exit code 0. I made no production shutdown changes. The integrated full pytest run collected 3,983 tests but ended with two test failures and a Windows native access violation at 96%, without a final summary or JUnit file. PR #67 also has an unresolved relay-shutdown review concern. No commit, push, PR update, or merge was performed.

## 1. Packaged Windows shutdown

The same onedir executable used for the R13 measurement was used again:

| Check | Result |
|---|---|
| EXE SHA-256 | `4714eec9e6a16bee9f82e4e50204d58477bd34205b153cf730b00b25ceaa9c14` |
| Confirmed main window | `HPC Client GUI 1.5.9`; Session 1 in the three-run baseline |
| Idle runs | PIDs 1472, 23976, 12112; each `WM_CLOSE` accepted, `WaitForExit(30000)=true`, native exit code 0, no force stop |
| Connected GUI run | PID 19920; WebView/terminal was opened, an X11-off SSH profile was connected and reconnected, then the app closed naturally with native exit code 0 |
| WebView2 child processes after close | None remained in the connected run |
| Package rebuilt | No. Production source was unchanged in this continuation; the R13 package hash was checked and reused |

R13's `STILL_ACTIVE` observation came from the earlier harness sending close before it had observed the main window title. That measurement may have closed the splash window, so it did not establish that the main application had received `WM_CLOSE`. The corrected runs establish normal close for the scenarios above; they do not cover every one of the seven requested shutdown sequences. In particular, no valid thread-stack/native-thread snapshot was captured, and X11-on shutdown was not repeated in R14. The original seven-thread report therefore remains unexplained at the thread level, but it is not reproduced by the corrected main-window measurement. There is no evidence to justify a production shutdown patch.

The first connected-run harness attempt timed out before a valid close and force-stopped its own test PID. It is excluded from the shutdown result. One JSON harness had a PowerShell closure issue that left thread/window arrays empty; process exit, HWND and native exit-code observations are retained, but those arrays are not treated as evidence.

## 2. Source identity and worktree preservation

R12g baseline archive SHA-256: `13995a19a0ef331ba2132ab29254c7c1781d5c43ec81fbd425d8f7dfec0d093b`.

The R14 integration test source was the c26 source snapshot plus the AST-based Qt/wx ordering correction:

- c26 source archive SHA-256: `0b45fac5182937d28024ae203a9ffff205c4ae6e73fc1f16fd95a689accf2e87`
- composite source ID: `1a6b6e1f447d5daab8673fa7027067b988b34f562529c97cccf9e563a94b09ba`
- `tests/conftest.py`: `8385bb07f844ec05f314ceefd2d808166905a264cc073ecae56b3e60bb44961c`
- `tests/support/qt_wx_ordering.py`: `7d6246b25023d405a752011a01367a81702afcd7e8972fbd8134eacddfdcc5c5`
- `tests/test_qt_wx_collection_order.py`: `63bedb59280ea941fc0815e93e50e979a6dd44db339eeaf02574f5165717ad0b`

The ordering fix replaces a substring search for `PySide6` with Python AST import detection. A string literal mentioning `PySide6` had caused a wx-only test module to be classified as Qt. The corrected D group passed 107 tests in 10.33 seconds on Kole Windows11-New; the recorded JUnit SHA-256 is `48fc1312775b23c51f6a4314f94d872ce2872fdf6c1e4b3e63d7201dd75c0e59`. The helper and its two focused tests are uncommitted and included in the current worktree.

The first fresh inventory during this continuation, after initial evidence capture and before this report/final cleanup receipts, showed 2 modified tracked files, 123 untracked files and no staged files. The tracked files were the pre-existing user ledger `docs/v2/V2_MAIN_TO_DEVELOP_CHANGE_LEDGER.md` and the Qt/wx ordering change in `tests/conftest.py`. The ledger was not edited. This report and later evidence add untracked files; the final `git status` still has zero staged files. No reset, clean, stash, branch switch, staging, or commit was performed.

## 3. Tests and static checks

Checks were run on Kole Windows11-New, Python 3.14.7, against the c26 integration snapshot and AST ordering overlay:

| Check | Result |
|---|---|
| Ruff | PASS — “All checks passed!” |
| compileall | PASS |
| i18n | PASS — key/reference/UI checks |
| Source architecture | PASS — 1,104 Python files, zero files over 500 LOC |
| WebView focused group | 56 passed; latest recorded JUnit SHA-256 `37a218137d89d11df414c8829190bb5875e7a3ec6e6c2819fd8e79360def998c` |
| GUI profile/SSH/X11 focused group | 80 passed on the integrated snapshot; JUnit was not retained in the local evidence bundle |
| Qt/wx order regression group | 107 passed; JUnit SHA-256 above |
| PR #67 forwarder contract tests | 21 passed; JUnit SHA-256 `01deb381f839bc01911c8761983f9cf9eee900036d853edf22448a6fb405991b` |

These are focused results on the combined integration tree; they are not proof that independently extracted PR trees pass. PR #67's local contract test artifact was run against its old 339 source. The full suite is the blocker:

- 3,983 tests collected.
- At the crash, 3,790 had printed `PASSED`, 46 had printed `SKIPPED`, and two tests had printed `FAILED`: `tests/test_docs_references.py::test_referenced_local_files_exist` and `tests/test_wx_a11y.py::test_wx_a11y_terminal_limits_documented`.
- Approximately 145 remaining items were not reached; the run did not produce a final pytest summary, JUnit XML, or successful exit code.
- Duration: 1,008.37 seconds; process exit `-1073741819` (`0xC0000005`).
- The crash occurred at `tests/test_wx_terminal_webview_bridge.py::test_wx_terminal_external_navigation_blocked`. Faulthandler showed the preceding `test_wx_layout_resize` event pump and then `_wait_for_ready` in `tests/wx_terminal_webview_support.py`. The external-navigation test passed alone and passed after the resize test in a two-test isolation run. This narrows the sequence-sensitive native failure but does not establish its native root cause.
- The A11Y test still encodes an old `wx.TextCtrl`/`EVT_CHAR` terminal contract while V2 uses WebView+xterm.js. Its exact assertion traceback was lost when Python crashed. The docs-link failure likewise has no final missing-target list. Both remain unresolved failures, not skips.

An earlier archive-only full run is excluded: that test copy lacked required Git/history and historical artifacts and used an invalid temp layout. The corrected checkout included those prerequisites, and its prerequisite fixture group passed 27 tests. The current corrected full run is therefore meaningful failure evidence, but not a complete test report.

## 4. X11 acceptance and package

The Windows real X11, reconnect, untrusted-cookie, X11-off SSH, terminal encoding, and relay/channel cleanup results from R12/R13 remain historical acceptance evidence. Ubuntu real GUI terminal, trusted X11/xclock reconnect, and X11-off results from R10/R12 remain historical acceptance evidence. No production X11 or terminal source was changed during R14. These earlier results were not rerun and do not resolve the current full-suite blocker.

The existing onedir package hash is `4714eec9e6a16bee9f82e4e50204d58477bd34205b153cf730b00b25ceaa9c14`. No new package was built because this continuation changed test infrastructure only. R13's 21/21 packaged GUI smoke remains historical; this turn added a real packaged main-window close measurement, not a new packaged X11 session.

## 5. PR #67 security review and PR split

Read-only GitHub inspection found PR #67 OPEN and DRAFT, four commits, three files, head `codex/audit-x11-paramiko-forwarder-20261114` at `339b86bada84504d2d02af002fad6b6af13777a5`, base `develop` at `2be856dbc3d7a75f7149b1c6243e25af005de799`. Its five successful CI checks apply to that old head only. No review decision was present.

The protocol review confirmed loopback/Unix local display limits, fail-closed cookie validation, fake-cookie rewriting, distinct trusted/untrusted handling without automatic trusted fallback, unauthenticated mode disabled by default, no `-ac`/`xhost +`, bounded relay concurrency, and timeout-aware ordinary cleanup. One unresolved lifecycle risk remains: active relay sockets/channels are not explicitly tracked and closed by `close()`. A blocking `sendall()` under backpressure could delay relay-thread cleanup. Existing tests cover ordinary cleanup and channel limits, not a blocked active relay during close. Therefore PR #67 is **BLOCKED**, not merge-candidate, pending focused evidence or a fix and CI on the exact updated head.

| PR | Scope and hunk boundary | Dependency / current disposition |
|---|---|---|
| **A — PR #67: X11 protocol/security** | Existing `.github/workflows/ci.yml`, `src/hpc_gui/ssh/x11_forward.py`, and `tests/test_x11_forwarder_contracts.py`; related Xauthority/cookie/display/firewall/relay lifecycle hunks and X11-only docs/tests. In mixed `ssh/client.py`, take only forwarder/controller protocol creation, delegation and close hunks. | Independent of B/D. **BLOCKED** by active relay close/backpressure uncertainty and old-head-only CI. If merged alone, it delivers the protocol layer but not user-visible GUI profile/terminal integration. |
| **B — WebView terminal/lifecycle** | `wx_terminal_webview*.py`, environment/labels/diagnostics helpers, bridge/I/O/lifecycle and terminal tests. Only the deferred mount plus output activation/attach hunk in `wx_shell_frame.py` belongs here. | Does not require A. 56 focused tests passed on the integrated tree. **MERGE CANDIDATE** after extracting the exact patch and testing that PR tree; no GitHub CI/review yet. |
| **D — wx/Qt and independent regressions** | AST ordering in `tests/conftest.py`, `tests/support/qt_wx_ordering.py`, `tests/test_qt_wx_collection_order.py`; owned fixture/FTP/Plugin Manager/W55/native repaint regressions. In `wx_shell_frame.py`, only accelerator ID lifetime belongs here. In `wx_shell_events.py`, only native repaint binding belongs here. | Independent in design. 107 focused tests passed on the integrated tree. **MERGE CANDIDATE** after exact isolated PR tests; the full-suite documentation/A11Y failures and native crash still block overall delivery. |
| **C — active Paramiko/X11 GUI integration** | Profile model/dialog/i18n, `x11_trusted` propagation, SSH session/terminal attachment, reconnect and fail-closed X11 behavior. In `ssh/client.py`, take only profile/session-info storage hunks; in `ssh/contracts.py`, keep the optional contract field with the owner agreed during extraction. | Depends on **A and B**. 80 focused tests passed on the integrated tree and prior GUI acceptance is historical. **BLOCKED** until A/B exact APIs are merged or tested together and the independent C patch is validated. |

`wx_shell_frame.py`, `ssh/client.py`, `ssh/contracts.py`, `tests/test_linux_x11.py`, and `tests/test_security_hardening_wave.py` need function/hunk-level extraction. Non-X11 wiki content, the user ledger, build artifacts, lab probes, screenshots with host data, private keys, profiles, and runner temp output must remain outside PR code. Proposed merge order remains **A → B → D → C**, but A is currently blocked, so no merge order is actionable yet.

## 6. Cleanup, approvals, and outstanding work

Test-owned credentials were cleaned up:

- Exactly one R14-tagged Ubuntu `authorized_keys` line was removed; the file remains mode `0600`, and a post-cleanup SHA-256 was recorded without exposing key content.
- Kole-side R14 private/public key files and the exact temporary GUI profile directory were removed and verified absent.
- The Windows11-New cleanup receipt found no remaining matching scheduled tasks or matching processes; the two R14 temporary test checkout directories were already absent.

W61.1 provenance receipt hash reconciliation and NVDA/Orca accessibility evaluation remain separate follow-ups. They are not treated as X11 protocol defects or new release gates here.

No commit, push, PR modification, or merge occurred. This task did not grant that authority; repository instructions require approval before commit and prohibit push without approval. Before delivery can proceed:

1. Diagnose or repair the repeatable full-suite native crash and resolve the two observed failed tests without skips or relaxed assertions.
2. Run an integrated full pytest to exit 0 with JUnit and final counts on the exact final source.
3. Build and smoke the final onedir package if production code changes; if not, document the production-source/package identity.
4. Extract A/B/D/C patches into isolated branches and run each PR's tests, static checks, architecture gate and CI on its exact source.
5. Resolve the active X11 relay shutdown/backpressure review concern; then obtain required review, branch-protection checks, and explicit user authorization before GitHub writes.

Evidence saved under `docs/audits/evidence/r14-final-repair/`. Sensitive screenshots and credential material were intentionally excluded. R1–R13 reports were not modified.

## R14 continuation — native crash narrowing (2026-11-18)

The focused native-crash investigation used the reconstructed source archive `0B45FAC5182937D28024AE203A9FFFF205C4AE6E73FC1F16FD95A689ACCF2E87` plus the test-only Qt/wx AST collection-order overlay. No production source was modified in this continuation.

| Session 1 group | Result | Evidence |
|---|---|---|
| Last 500 exact predecessor IDs + external-navigation target | 501 passed (previous checkpoint) | Existing R14 task log |
| Last 750 predecessor IDs + external-navigation target | 750 collected, 750 passed, 0 failed, 0 skipped; exit 0; 712.38 s | `evidence/r14-final-repair/native-crash-debug-20261118/last750.xml`; JUnit SHA-256 `8f29b9ae33b3daea0c195b8b878d5f39e5b3d0f567cc4dd4930beba13c9b20e1` |
| Last 1,000 predecessor IDs + external-navigation target | Native process exit `0xC0000005` while entering `test_wx_terminal_external_navigation_blocked`; no pytest/JUnit final summary | `last1000e.stdout`; Task Scheduler result `-1073741819` |
| First 250 predecessor IDs + external-navigation target | Same native process exit `0xC0000005` at the target; no final pytest summary | `first250.stdout`; Task Scheduler result `-1073741819` |
| wx tests at positions 217–250 + target | Started as task `HPC_GUI_R14_DEBUG_WX217_250_20261118`; result not collected | Kole/VM connectivity was lost immediately after launch |

This narrows the trigger to state accumulated by an earlier predecessor set: the last 750 tests plus target pass, while the first 250 and last 1,000 subsets crash at the same native test. The first 250 include `test_wx_65a_integrated_stress` at position 217, followed by A11Y, ANSYS, clipboard, and connection GUI tests. This is correlation only; it does not yet prove which test or native lifetime boundary causes the access violation.

At the time the 217–250 isolation task was started, the Kole Tailscale peer remained listed as active through a relay, but SSH to both `kole-win11-new` and the Kole host timed out. Tailscale also reported a DERP TLS certificate interception health warning. No VM restart, process termination, service change, or additional test launch was attempted. The isolation task's completion, WER record, and output remain unverified until Kole access returns.

### Current status

- Native crash root cause: **OPEN**; narrowed to GUI state in the first 250 predecessor IDs, not yet localized.
- Full pytest: **NOT PASS**; this continuation did not run an integrated full suite.
- Source changes: none; only this report and sanitized pytest evidence were added.
- Next: regain verified Kole SSH access; inspect the exact task, result files and WER; then isolate the wx stress/GUI predecessor subset in Session 1. Do not rerun the full suite until the trigger and native lifetime issue are understood.

Evidence files are checksummed in `evidence/r14-final-repair/native-crash-debug-20261118/SHA256SUMS.txt`.

### R14 continuation — Session 1 event-loop diagnostics (2026-11-18)

The prior runner/result mismatch was traced to a stale XML file and a runner that wrote its JSON result before Windows completed process teardown. A run is now treated as valid only when the interactive Task Scheduler result, Python process exit, JUnit test count, and pytest summary agree. An earlier exploratory invocation through SSH ran in Session 0 and was excluded from GUI evidence.

| Kole Windows11-New Session 1 run | Result | Evidence |
|---|---|---|
| `tests/test_wx_terminal_webview_bridge.py` using a retained active `wx.GUIEventLoop` and `EventLoopActivator` with `Dispatch()` only | **9 passed**, exit 0, 3.00 s | `followup-20261118/r14_bridge_module_dispatchonly.xml`; JUnit SHA-256 `b367dad40893551e7225f2350bd26db61cf0f56b523fefd23e7ffb130cf58bcf` |
| Three ordered Wave80 wx GUI predecessors followed by `test_wx_terminal_external_navigation_blocked` using that helper | Intermittent: one instrumented 4/4 pass, five later native crashes, then another 4/4 pass. The failures included `0xC0000005` and `0xC0000374`; one failed run stopped after `shown` and before WebView `ready`. | `followup-20261118/r14_threeprior_diag.xml` is the later passing diagnostic run; `r14_state_observer.wxstate.log` and the corresponding stdout capture the failing run. Hashes are in `followup-20261118/SHA256SUMS.txt`. |

At the target test's setup, the same `wx.App` wrapper remained alive, no top-level wx windows or Python worker threads remained, and there was no active wx event loop. The intermittent fault therefore was not explained by an obvious leaked frame or Python worker. The `GUIEventLoop.Dispatch()` plus `wx.Yield()` double-pump was removed from the test helper because it dispatches through two event-loop paths; the dispatch-only variant passed the whole bridge module. However, the ordered stress repetitions still crashed, so that helper change is **not** claimed as the native-crash root-cause fix.

Windows Application Error events confirmed native `python.exe` faults in wxbase/ntdll and `0xC0000005`/`0xC0000374`. A temporary per-user WER LocalDumps setting produced no dump; the setting was removed and the created dump folder was empty. ProcDump was downloaded from the official Sysinternals URL and its binary SHA-256 was `22C2A2B09ADE73A342A18DAB838354385F73FC98E324B9903FD61FFF949C5124`; it was not run and its EULA was not accepted. The downloaded files were removed. No native stack dump is available.

The current worktree changes remain test-only: `tests/conftest.py` retains a strong reference to the marked wx test app, and `tests/wx_terminal_webview_support.py` uses an activated, retained event loop and dispatches it without also calling `wx.Yield()` from the readiness loop. No production file changed. The test helper change is supported by the 9/9 bridge-module result, but its effect on the ordered crash remains inconclusive. The previous WER key is absent; no test Python process or newly started WebView2 process was left running by the last verified process check. Four older Python processes in Session 1 predate this continuation and were not touched.

**Current status:** native crash root cause **OPEN**; full pytest **NOT RUN / NOT PASS**; X11 source, package, and PR results remain historical and were not revalidated against these test-only changes. Do not merge or claim R14 acceptance until the intermittent wx/WebView crash is understood, the full suite exits 0 on the final source, and the packaged acceptance gates are confirmed.

An additional five-run Session 1 repetition used the same activated dispatch-only helper: runs 1, 2, and 4 exited 0; runs 3 and 5 ended in native process exceptions (`0xC0000005` and `0xC0000374`). A later 4-test run passed. This confirms intermittency rather than a stable fix. A short machine-scope WER LocalDumps attempt also produced no dump; its key was absent beforehand and removed immediately afterward, with no other LocalDumps keys affected. ProcDump was not run. Exact results and JUnit files are in `followup-20261118/`; failed native runs correctly have no completed JUnit result.

### GitHub delivery scope

The 2026-11-18 report push includes this audit report and `evidence/r14-final-repair/native-crash-debug-20261118/` only. Experimental working-tree changes in `tests/conftest.py` and `tests/wx_terminal_webview_support.py` are excluded from that delivery; their hashes describe the local diagnostic source used for the reported test runs. No X11 source change, PR edit, merge, or full-suite PASS is included in this report push.
