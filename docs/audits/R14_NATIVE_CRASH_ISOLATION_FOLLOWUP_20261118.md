# R14 Native Crash Isolation — Follow-up 2

Date: 2026-11-18  
Repository: `mskomek/hpc-client-gui`  
Worktree: `D:\Projeler\.tmp\hpc-client-gui\x11-kole-acceptance`  
Branch: `codex/x11-active-terminal-kole-20261114`  
Diagnostic source snapshot SHA-256: `0b45fac5182937d28024ae203a9ffff205c4ae6e73fc1f16fd95a689accf2e87`

## Outcome

The candidate wx Jobs timer callback is **not supported as the cause** by the new controlled runs. Adding a temporary guard that returned when the lifecycle state was closed did not stabilize the sequence: all five guarded A+B+C+WebView runs still crashed (four heap-corruption exceptions `0xC0000374`, one access violation `0xC0000005`). In a separate logged variant, two runs passed and one crashed; neither passing process invoked the instrumented timer callback (`open=0`, `closed=0`). No production source was changed.

The exact native ownership or callback root cause remains **OPEN**. The evidence still points to same-process wx/WebView2 lifecycle/order sensitivity and does not identify the offending native reference.

## WebView2 process/profile check

A sanitized inventory found 12 pre-existing `msedgewebview2.exe` processes in Session 1. Six descend from `SearchHost.exe` and six from a Python process belonging to the pre-existing W65 probe. Their process start dates were 2026-11-11 and 2026-11-12. The process command lines were inspected in memory only; their `--user-data-dir` values were hashed and not logged.

The expected default profile path was derived from the app's current `app_data_dir() / "webview2"` behavior for the `home` account, then hashed. None of the 12 process profile hashes matched that expected default hash. This rules out a match to that specific default path for this inventory, but does not rule out other WebView2 interactions or prove which profile was used by each diagnostic process. No pre-existing process was terminated.

## Diagnostic inventory and cleanup

- Session 1 / Python 3.14.7 / wx WebView2.
- Guarded sequence: 5 runs, all native crashes; no readiness-assertion workaround accepted.
- Guard-logging sequence: 1 access violation, 2 passes; successful cases reported zero timer callback invocations.
- Owned scheduled tasks remaining: 0.
- Owned diagnostic processes remaining: 0.
- Temporary WER LocalDumps setting: absent.
- Owned diagnostic temp folder and probe scripts: removed after evidence collection.
- Unrelated `SearchHost` and W65 WebView2 processes: left untouched.
- ProcDump was not run; no EULA was accepted and no dump was captured. A native C++ stack is therefore still unavailable.

## Evidence

The new raw result files and archives are in [controlled-loop-variants-20261118/guarded](evidence/r14-final-repair/native-crash-debug-20261118/followup-20261118/controlled-loop-variants-20261118/guarded/). `SHA256SUMS.txt` in that directory covers every retained file. `followup-guarded-profile-summary.json` contains the sanitized run counts, exception codes, profile hashes, and cleanup result. It deliberately excludes raw profile paths and credentials.

Earlier 38-run matrix remains documented in [R14_NATIVE_CRASH_ISOLATION_20261118.md](R14_NATIVE_CRASH_ISOLATION_20261118.md). The original evidence verdict remains `EVIDENCE_INCONSISTENT`; this update does not establish a full pytest pass or X11 acceptance.

## Close-before-destroy probe

A temporary copy of the WebView navigation test was changed only for diagnosis to call `panel.close()` before `frame.Destroy()`. The same A+B+C prefix was followed by this variant in five independent Session 1 processes. All five still crashed in `_wait_for_ready` while waiting for WebView readiness (one `0xC0000005`, four `0xC0000374`). Because the test never reached its readiness assertion or cleanup lines, this result cannot determine whether explicit close-before-destroy would fix a teardown-only crash. It does establish that this prefix can crash before the test's close/destroy teardown is reached. The temporary test copy and remote runner were removed after collecting the evidence. Raw outputs are in [close-before-destroy](evidence/r14-final-repair/native-crash-debug-20261118/followup-20261118/controlled-loop-variants-20261118/close-before-destroy/), with hashes in its `SHA256SUMS.txt`.

## Next step

The event-loop dispatch/readiness path remains the narrowest failure location visible to Python faulthandler, but the underlying native frame is unknown. A native dump or a lower-level backend reduction is required to identify the C++ failure. ProcDump remains unused pending the user's explicit response to the EULA/dump question. Do not claim the root cause is fixed until a stable minimal reproduction and relevant wx/WebView regression group pass.

## Test isolation repair

The same A+B+C order was then run with the external-navigation test performing its real WebView creation, ready handshake, and navigation assertions in a child Python process. The diagnostic version passed 5/5. The repository test now uses this isolation pattern via the existing subprocess helper; it preserves the checks for WebView readiness, blocking an external URL, and allowing the local terminal page. Kole Windows11-New Session 1 ran the modified test after A+B+C five times: **5/5 parent sequences passed**, each reporting `4 passed`. The transferred test file SHA-256 was `f57d51d7e5540fe981e4c288541175ea6ee031a9ea8a7c07ada88362865f5155`; Ruff passed for the modified test file.

This is a test-harness isolation repair for the observed same-process order failure. It does not prove the exact native C++ cause or rule out other same-process WebView lifecycle defects in the application. The full pytest suite has not yet been run against the current worktree.

Evidence is in [repaired-subprocess-test](evidence/r14-final-repair/native-crash-debug-20261118/followup-20261118/controlled-loop-variants-20261118/repaired-subprocess-test/). The summary binds the five Session 1 results to the modified test SHA, and the folder's `SHA256SUMS.txt` covers all retained files.

The full changed WebView bridge test module then passed in the same Kole Session 1 environment: **9 collected, 9 passed, 0 failed, 0 skipped, exit code 0** in 2.26 seconds. Its JUnit XML and complete output are in [webview-module](evidence/r14-final-repair/native-crash-debug-20261118/followup-20261118/controlled-loop-variants-20261118/webview-module/). The test source SHA matches the repeated order-regression run above. Ruff passed for that exact file on the worktree.

## Current status

- Source change: external-navigation GUI test now isolates its native WebView in a child process.
- Candidate Jobs timer callback hypothesis: not supported by the logged run sample.
- WebView2 profile collision with the expected default path: not observed among 12 pre-existing processes.
- Native crash: still reproducible, root cause open.
- Focused order regression: 5/5 pass with the modified test.
- WebView bridge module: 9/9 pass in Kole Session 1.
- Full pytest: not run.
- GitHub writes: none.
