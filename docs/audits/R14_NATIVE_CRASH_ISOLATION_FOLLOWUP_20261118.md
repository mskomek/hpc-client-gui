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
## 2026-11-18 Tailscale follow-up addendum

This addendum supersedes the earlier “Full pytest: NOT RUN” and “ProcDump was not run / EULA pending” statements above. Those statements were accurate when written but became stale after the additional Kole Session 1 runs below. Earlier diagnostic observations remain historical evidence.

### Full pytest result received from Kole over Tailscale

The suite completed on Kole Windows11-New, interactive Session 1, Python 3.14.7 / pytest 9.1.1, using the diagnostic source archive SHA-256 `0b45fac5182937d28024ae203a9ffff205c4ae6e73fc1f16fd95a689accf2e87` with overlay hashes in `evidence/r14-final-repair/native-crash-debug-20261118/full-pytest-20261118/diagnostic-summary.json`.

- Collected 4,012; passed 3,921; failed 15; errors 0; skipped 47; passing subtests 29.
- Duration 1,037.33 seconds (17:17). JUnit confirms 15 failures and 0 errors.
- The wrapper did not persist the process exit code (`null`). Evidence proves failure but not the native pytest exit code. This is not a PASS.
- No native process crash occurred during this suite run.

Failure classification from `failure-index.md`:

1. One docs-reference test: current source tree lacks `TODO_V2_REMAINING.md`, referenced by the change ledger.
2. Five GUI audit screenshot tests: `audit/current-gui/MANIFEST.json` is absent locally and from the diagnostic snapshot.
3. One temp-root policy failure: basetemp was outside the repository `.tmp` policy.
4. One taxonomy report test and three W14 provenance tests: the diagnostic source archive had no `.git` metadata; the taxonomy test also failed 3/3 in isolation for that reason.
5. One W31 package artifact test: runner omitted `HPC_GUI_W31_PACKAGE_WHEEL`.
6. One W61.1 handoff test and one wx A11Y test: the archive omitted the historical receipt and `audit/A11Y_AUDIT.md`; both exist in the local worktree.
7. One W11 transport lifecycle test: integrated failure, but five isolated Session 1 runs passed; test-order/global-state interaction remains unresolved.

This is diagnostic evidence, not a valid whole-worktree acceptance run: the snapshot omitted Git metadata and required files and used a noncompliant basetemp. Failures include runner/source packaging issues and one unresolved integrated-order failure. The 47 skips were not individually reclassified.

### ProcDump and native crash update

After the user's explicit EULA authorization, ProcDump 12.02 (Microsoft Authenticode verified) was run only against the test-owned Python process in Session 1. Five A+B+C+target attempts and three A+C+target attempts were monitored (eight total). All completed without a dump; the corresponding test runs passed and no exception-triggered dump was produced. The crash did not reproduce in these eight ProcDump-monitored attempts. Evidence is in `procdump-attempt-20261118/` and `procdump-ac-attempt-20261118/`.

No native dump or C++ stack was captured. Root cause remains OPEN: older controlled runs reproduced crashes, newest monitored attempts did not. The accepted per-user EULA value remains as authorized. The downloaded tool, owned tasks, diagnostic processes, and transient directories were cleaned. Unrelated SearchHost/W65 processes were untouched.

### Focused isolation results

- Modified WebView bridge module: 9 passed, 0 failed, exit 0, 2.26 seconds; source SHA `f57d51d7e5540fe981e4c288541175ea6ee031a9ea8a7c07ada88362865f5155`.
- A+B+C plus modified WebView navigation: five repeated Session 1 sequences passed, each four tests.
- W11 transport lifecycle: five isolated Session 1 runs passed (exit 0); integrated-order failure unresolved.
- Taxonomy report: three isolated attempts failed due absent Git metadata; not a valid product-level verdict.

### Evidence integrity and status

Full pytest outputs, JUnit, sanitized failure index, and result summary are in `evidence/r14-final-repair/native-crash-debug-20261118/full-pytest-20261118/`. User-specific paths have been replaced. No raw dump is retained. SHA-256 manifests are regenerated after sanitation.

Verdict: focused WebView workaround is green; full pytest is FAIL/INVALID-AS-ACCEPTANCE due 15 failures and source/runner limitations; native root cause OPEN; X11 acceptance unchanged and not rerun. Remote logs were retrieved over the existing Tailscale-backed Kole SSH/SCP route. No GitHub writes or pushes occurred.

## 2026-11-18 final-source full-suite and W11 follow-up

The earlier 4,012-test diagnostic run (3,921 passed / 15 failed) was superseded by a complete run using the exact committed source plus the recorded worktree overlays and required historical receipts. The final run completed on Kole Windows11-New, interactive Session 1, Python 3.14.7 / pytest 9.1.1. Source commit: `48d5f54fb555907b2804b146d854c303874a96ab`; source tree: `bafcf64065b8b86ec75d8ec95ee2c260a24b6988`.

- Collected 4,012; passed 3,931; failed 5; errors 0; skipped 47; 29 passing subtests; duration 1,076.567 seconds; pytest exit code **1**.
- All five failures are `tests.test_gui_audit_screenshots`: the test snapshot lacks `audit/current-gui/MANIFEST.json` and its registered screenshot files. The expected historical manifest commit `3a7294079b992d3ddcabc349bbeadf6988312b64` is not available in this branch repository. No substitute manifest or screenshots were fabricated or imported. This remains a full-suite **FAIL**, not PASS.
- The 47 skips were preserved as reported by pytest and were not individually reclassified.
- The final suite did not reproduce a native crash. The native C++ root cause remains **OPEN** because no dump or native stack was captured.

JUnit, complete stdout/stderr, process result, timestamps, and source identity are retained in [full-pytest-final-48d5](evidence/r14-final-repair/native-crash-debug-20261118/full-pytest-final-48d5/). The JUnit records the five screenshot audit failures; `exit_code.txt` records `1`.

### W11 transport lifecycle regression

The integrated W11 failure was caused by the test helper waiting with `sleep` while a live `wx.App` had deferred `wx.CallAfter(controller.fail)` onto the event queue. In isolation, with no live wx app, the callback ran synchronously, which is why the previous isolated test passed. The regression test now optionally pumps wx events while waiting; the production controller behavior was not changed. This repair is committed as `48d5f54fb555907b2804b146d854c303874a96ab`.

The complete W11 lifecycle module then passed in five fresh Kole Session 1 processes: 14/14 each, zero failures/errors, exit code 0 each. The tested test-source SHA-256 is recorded in `source-identity.json`. Per-run JUnit and console results are in [w11-module-pumpfix-48d5](evidence/r14-final-repair/native-crash-debug-20261118/w11-module-pumpfix-48d5/).

### Final-source artifact-focused checks

A wheel built from commit `48d5f54` completed successfully (SHA-256 `6294946ca07fc2e54c6f82d79d104472c46246abcfa7ef46e996238fe052fd96`). Three focused checks passed against it: W31 package resource, W61.1 historical CLI repair receipt, and the wx A11Y audit document (3 passed, exit 0). Build and test outputs are retained under [wheel-build-final-48d5-summary.json](evidence/r14-final-repair/native-crash-debug-20261118/wheel-build-final-48d5-summary.json) and [artifact-isolation-final-48d5](evidence/r14-final-repair/native-crash-debug-20261118/artifact-isolation-final-48d5/). These focused passes do not alter the full-suite FAIL above.

The R14 diagnosis used Tailscale-backed SSH/SCP to retrieve Kole's logs. No push or merge was performed. The earlier ProcDump approval was used only for the previously documented owned-process attempts; those attempts produced no dump. No unrelated process was terminated.

**Current verdict:** W11 lifecycle regression repaired and repeatedly verified; artifact-focused checks PASS; full pytest FAIL due five absent historical GUI audit fixtures; native C++ crash root cause OPEN; GitHub delivery remains blocked on the required full-suite acceptance and remaining native diagnosis.

## 2026-11-19 final regression closeout

This section supersedes the preceding full-suite FAIL statements. It records the final run on the corrected historical fixture and the exact committed source identified below. Earlier outcomes remain in this report as historical diagnostics.

### Historical GUI audit fixture and focused failures

The five screenshot-audit failures were caused by the test snapshot missing the authentic historical fixture. The recovered archive is from GUI audit follow-up commit `c59e536e14ac09a0432bb8421a717ad518a684e9`; its manifest records product source commit `3a7294079b992d3ddcabc349bbeadf6988312b64`, marks the evidence `historical`, and its screenshots match the recorded hashes. The archive SHA-256 is `59A1B3CA5A3A8B4013260D90B5501E0399B3816319521591A02E50C984352771`. The earlier capture commit `598352492a329dcf0379fceffd402117f2af4fb0` predates the manifest's historical-status amendment and was not used as the final fixture. No screenshot or manifest was fabricated.

With the corrected fixture, the GUI audit module passed **5/5** in Kole Session 1. The report-reference issue was corrected in commit `2fb1497527ed05dd2dd66e3d31c43d4743afb6d1` by linking the tracked wheel summary JSON rather than an ignored build directory. The W31 wheel test's earlier `PermissionError` was an artifact ACL issue: the wheel was rebuilt from the same source commit in the task-owned temp area and read access was granted only to the test account for that temporary file. Focused docs-reference and W31 checks then passed **2/2**. Wheel SHA-256: `c9c4b7a533c8ffe4551bd2c665420bc1e4c7cccf3cccbcb9d802ea3665c8df1f`.

### Integrated full pytest

The final run used Kole Windows11-New's interactive Session 1, Python 3.14.7 and pytest 9.1.1. The test source was commit `2fb1497527ed05dd2dd66e3d31c43d4743afb6d1` (Git tree `36b64c56e6ee865857a99a5294f0759654ea049c`) plus the exact worktree overlays listed in `source-identity.json`.

- Collected: **4,012**; passed: **3,936**; failed: **0**; errors: **0**; skipped: **47**; passing subtests: **29**.
- Pytest summary duration: **1,117.92 s** (18:37); JUnit duration: **1,117.863 s**.
- Persisted pytest exit code: **0**; wrapper exit code: **0**.
- The run's launcher, runner and pytest process were all recorded in Windows Session 1. JUnit hostname is `Windows11-New` and records zero failures/errors.

Complete sanitized stdout/stderr, JUnit XML, process result, timestamps, source identity, focused GUI/W31 results, wheel build log, and `SHA256SUMS.txt` are retained in [full-pytest-final-2fb1497](evidence/r14-final-repair/native-crash-debug-20261118/full-pytest-final-2fb1497/). The 47 skips are pytest-reported skips; this run did not add skips or alter assertions. This is an integrated full-suite **PASS** for the recorded source plus overlays, rather than a sum of partitioned results.

### Remaining status

- The full suite did not reproduce a native crash. The previously observed wx/WebView native access violations still have no captured dump or native C++ stack, so their root cause remains **OPEN**; the full-suite pass does not prove that the intermittent native defect is fixed.
- The actual X11 acceptance remains the historical R13/R10 evidence and was not rerun in this regression closeout.
- GitHub was not updated: no push, PR edit, or merge occurred. No product runtime change was made in this closeout; commit `2fb1497` is the report-link correction.

**Updated verdict:** final integrated pytest **PASS** on the source/overlay identity above; historical GUI audit and W31 focused checks **PASS**; native C++ crash root cause **OPEN**; X11 evidence unchanged; GitHub delivery remains pending the separately required native diagnosis and repository delivery steps.

