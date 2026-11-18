# R14 Evidence Repair & Verification

Date: 2026-11-18
Repository: `mskomek/hpc-client-gui`
Worktree: `D:\Projeler\.tmp\hpc-client-gui\x11-kole-acceptance`
Branch: `codex/x11-active-terminal-kole-20261114`
HEAD: `b336316028495c5ecc8be90948fa1760472a61d0`
Parent: `c26fcac1cea56e37bd2683c73b11a5a5240be984`
Audit commit scope: audit report and R14 evidence only. No production code, experimental test changes or PR #67 changes were included.

## Executive result

**Evidence verdict: `EVIDENCE_INCONSISTENT`.** F-02 was fully repaired and manifests validate. A separate complete `threeprior` run was recovered and correlated to a successful Task Scheduler `LastTaskResult`. The original F-03 artifact set remains internally inconsistent. F-04 is now explained by a duplicated requested node ID. The Task Scheduler Operational event channel is disabled, but live `LastTaskResult` metadata is available for key tasks; 54 R14 tasks remain registered in Ready state. This verdict describes the evidence package only; it is not implementation acceptance, merge approval, or a new test-suite pass.

No full pytest run was made during this repair (`NOT RUN`). Production code and experimental test source files were not edited. No commit, push, PR update, or merge was performed during this task.

## Source and evidence identity

- Current HEAD: `b336316028495c5ecc8be90948fa1760472a61d0`; parent: `c26fcac1cea56e37bd2683c73b11a5a5240be984`.
- Diagnostic source recorded by the prior report: source archive SHA-256 `0b45fac5182937d28024ae203a9ffff205c4ae6e73fc1f16fd95a689accf2e87`; composite ID `1a6b6e1f447d5daab8673fa7027067b988b34f562529c97cccf9e563a94b09ba` (the c26 snapshot plus test-only AST ordering overlay).
- Experimental files remained unchanged during this task: `tests/conftest.py` SHA-256 `9822feaa5c7bf66903d86f3da29041df14af33e97d7a63d27ca4a104aaae5a687`; `tests/wx_terminal_webview_support.py` SHA-256 `972c9f3d0c313a473fab4e2421f0c39c725c37bd1b51ee9a8e0bd49ab99d59ad`.
- No source files under `src/` changed during this task.
- The working tree already contained unrelated/user and experimental changes at entry. They were preserved; no reset, clean, stash, stage or branch switch was used.

## Findings and repairs

### F-02 — missing wxstate log

**Severity: Medium. Result: REPAIRED.** The original file was recovered from Kole Windows11-New at `C:\Users\home\AppData\Local\Temp\hpc-client-gui-r14-debug-20261118\repo\.tmp\debug-r14\r14_state_observer.wxstate.log`. Its byte-level SHA-256 is `3400c0469e9021ad15ed499393340494b97d0e23f66bb019a5267c802994a9c0`, exactly matching the previously recorded expected value and followup manifest. Length: 1,542 bytes. It records test node names, wx App/event-loop observations, and empty windows/threads lists. No credential or private-key material was found. It is now present at `evidence/r14-final-repair/native-crash-debug-20261118/followup-20261118/r14_state_observer.wxstate.log`.

### F-03 — original `threeprior_diag` stdout/JUnit/result mismatch

**Severity: High. Result: ORIGINAL RUN UNVERIFIED; SEPARATE RECOVERED RUN PASS.**

Original evidence at `followup-20261118/r14_threeprior_diag.*` remains byte-for-byte unchanged. Its JSON says exit 0, 4 selected, stdout 2,631 bytes, stdout SHA-256 `56eb81c4...`; actual bundled stdout is 903 bytes, SHA-256 `4a2086b7...`, and terminates as the fourth test starts. The JSON's JUnit SHA matches the XML, which records 4 tests and 4 passes. Thus the JUnit and result JSON support a passing outcome, but the stdout does not; the original run is **UNVERIFIED** under the requested cross-artifact rule.

Kole's later run is stored separately under `followup-20261118/recovered-threeprior-diag-run-20261118/`; the earlier files were preserved. The later result JSON hashes match the 2,631-byte stdout and JUnit XML, and stdout ends `4 passed in 1.50s`. Its wrapper receipt records Session 1 and `python_exit=0` from 11:53:37Z to 11:53:40Z. The registered task `HPC_GUI_R14_MACHINE_WER_20261118` has LastRun 11:53:36Z, LastTaskResult 0, and its action invokes the exact `run-r14-threeprior-diag-session1.ps1` runner. Thus the recovered run is a **PASS**; it does not repair the earlier mismatched artifact set. The Operational event channel is disabled, so no event record exists.

### F-04 — `last750` count discrepancy

**Severity: Medium. Result: RESOLVED.** The original runner and `last1000-nodeids.txt` were recovered. The node file has 1,001 unique IDs. The runner constructs `nodes = allnodes[-750:] + [external_navigation_target]`, so it requests 751 entries. That target already occurs in the last 750, producing exactly one duplicate; requested IDs are 751, unique IDs are 750. Pytest deduplicates the repeated node ID during collection. The result JSON `selected_tests` field is the requested list length, not the unique collected count.

| Measure | Count | Evidence |
|---|---:|---|
| Source node file rows / unique IDs | 1,001 / 1,001 | Recovered `last1000-nodeids.txt`; SHA-256 `01eeabdf…` |
| Requested node IDs | 751 | Runner expression and result JSON |
| Unique requested IDs | 750 | Reconstructed list has the external-navigation node twice and no other duplicate |
| Pytest collected / executed / passed | 750 / 750 / 750 | Stdout and JUnit |
| Failed / skipped / deselected | 0 / 0 / 0 | Complete pytest summary and XML |
| Session / Python exit / Task Scheduler result | Session 1 / 0 / 0 | Wrapper receipt and task `HPC_GUI_R14_DEBUG_LAST750_20261118` metadata |

The recovered source files and task metadata are preserved under `followup-20261118/last750-selection-source-20261118/`; no original JSON was edited.

### F-05 — run provenance, scheduler records and native failures

**Severity: High. Result: PARTIALLY VERIFIED.** The Task Scheduler Operational event channel is disabled (`IsEnabled=false`), so historic event records are unavailable. A read-only live metadata snapshot does provide `LastTaskResult` for first250, last1000e, last750, the later threeprior run, and the repeat wrapper. Their task actions and last-run times match preserved runner scripts. The repeat batch wrapper task itself returned 0 while its per-run receipt records the child native exceptions in repeats 3 and 5.

The live inventory found **54 registered tasks prefixed `HPC_GUI_R14`; all 54 are Ready**. This contradicts the earlier cleanup receipt that said no matching tasks remained. The receipt is not a reliable record of current state. This repair did not alter the tasks. The captured scheduler snapshot and runner scripts/results are in `followup-20261118/last750-selection-source-20261118/` and `followup-20261118/native-crash-run-provenance-20261118/`. Per-run Python PIDs and unique WER Report IDs remain unavailable. Sanitized Application Error 1000 and Windows Error Reporting 1001 records were recovered for all five native-crash runs; their raw messages and paths are excluded.

| Run | Time (UTC) | Session / PID | Process and Scheduler evidence | JUnit / summary | Classification |
|---|---|---|---|---|---|
| `first250` | 08:05:11–08:06:35 | Wrapper Session 1; PID absent | Wrapper `python_exit=-1073741819`; matching task `HPC_GUI_R14_DEBUG_FIRST250_20261118` LastTaskResult `3221225477` (`0xC0000005`) | No completed JUnit or final summary; stdout/stderr retained | `FAIL_NATIVE_CRASH` |
| `last1000e` | 07:35:41–07:48:52 | Wrapper Session 1; PID absent | Wrapper `python_exit=-1073741819`; matching task `HPC_GUI_R14_DEBUG_LAST1000E_20261118` LastTaskResult `3221225477` (`0xC0000005`) | No completed JUnit or final summary; stdout/stderr retained | `FAIL_NATIVE_CRASH` |
| `dispatchonly_repeat1` | 11:54:25–11:54:28 | Batch wrapper Session 1; PID absent | Per-run exit 0; enclosing task LastTaskResult 0 | 4 JUnit cases; JSON/stdout/JUnit hashes match | 4 PASS outcomes |
| `dispatchonly_repeat2` | 11:54:28–11:54:31 | Batch wrapper Session 1; PID absent | Per-run exit 0; enclosing task LastTaskResult 0 | 4 JUnit cases; JSON/stdout/JUnit hashes match | 4 PASS outcomes |
| `dispatchonly_repeat3` | 11:54:31–11:54:34 | Batch wrapper Session 1; PID absent | Per-run exit `-1073741819` (`0xC0000005`); enclosing task LastTaskResult 0 because wrapper completed its batch | No completed JSON/JUnit/final pytest summary; faulthandler stdout/stderr retained | `FAIL_NATIVE_CRASH` |
| `dispatchonly_repeat4` | 11:54:39–11:54:41 | Batch wrapper Session 1; PID absent | Per-run exit 0; enclosing task LastTaskResult 0 | 4 JUnit cases; JSON/stdout/JUnit hashes match | 4 PASS outcomes |
| `dispatchonly_repeat5` | 11:54:41–11:54:44 | Batch wrapper Session 1; PID absent | Per-run exit `-1073740940` (`0xC0000374`); enclosing task LastTaskResult 0 because wrapper completed its batch | No completed JSON/JUnit/final pytest summary; faulthandler stdout/stderr retained | `FAIL_NATIVE_CRASH` |
| `state_observer` | 11:43:07–11:43:14 | Wrapper Session 1; PID absent | Wrapper `python_exit=-1073741819` (`0xC0000005`); no matching currently registered scheduler task metadata found | No completed JUnit/final summary; wxstate/stdout retained | `FAIL_NATIVE_CRASH` |
| Original `threeprior_diag` | Exact time unavailable | Missing | JSON says exit 0; actual stdout length/hash conflict with JSON | XML shows 4 pass cases, but stdout ends before final test result | `UNVERIFIED` |
| Recovered `threeprior_diag` | 11:53:37–11:53:40 | Wrapper Session 1; PID absent | Wrapper exit 0; matching task `HPC_GUI_R14_MACHINE_WER_20261118` LastTaskResult 0; task action invokes the exact runner | 4 JUnit passes; full `4 passed` summary; hashes match | 4 PASS outcomes |
| `bridge_module_dispatchonly` | 11:33:07–11:33:11 | Wrapper Session 1; PID absent | Wrapper exit 0; no registered current task record identified for this run | 9 JUnit passes; complete stdout; hashes match | **9/9 PASS** focused result; scheduler cross-check unavailable |
| `last750` | 07:51:22–08:03:17 | Wrapper Session 1; PID absent | Python exit 0; matching task `HPC_GUI_R14_DEBUG_LAST750_20261118` LastTaskResult 0 | 751 requested entries, one duplicate, 750 unique/collected/executed/passed | **750 PASS outcomes** |

**Outcome counts (executions, including repeats):** **775 PASS case outcomes** are backed by complete matching artifacts: bridge module 9, repeats 1/2/4 12, recovered threeprior 4, and last750 750. They are not 775 unique test IDs. **5 runs are `FAIL_NATIVE_CRASH`:** first250, last1000e, repeat3, state_observer, and repeat5. Four ended with `0xC0000005`; repeat5 ended with `0xC0000374`. **1 run remains `UNVERIFIED`:** the original threeprior artifact set, whose stdout does not match its JSON even though the XML has 4 passing cases. No native root cause was established.

### F-09 — chronology and commit scope

**Severity: Low. Result: CLARIFIED.** Earlier “No commit/push…” statements describe the original report checkpoint before commit `b336316...`. That commit exists on the current branch, parent `c26fcac...`, and its Git tree contains the audit report plus R14 evidence files only. The experimental `tests/conftest.py` and `tests/wx_terminal_webview_support.py` changes were not part of it. PR #67 was not changed by that commit and was not modified during this task. The historical wording in the main report is qualified by an addendum; prior history is preserved.

## Hash, format and privacy verification

- Existing top-level `SHA256SUMS.txt`: 5/5 entries byte-verified.
- Existing `followup-20261118/SHA256SUMS.txt`: 16/16 entries byte-verified, including restored wxstate log.
- Recovered threeprior-run manifest: 4/4 files byte-verified (result, stdout, XML, wrapper receipt).
- Repeat1/2/4 stdout manifest: 3/3 stdout files byte-verified; hashes match their per-run JSON records.
- Repeat3/5 crash-output manifest: 4/4 stdout/stderr files byte-verified.
- Last750 input, runner, wrapper, and scheduler bundle: 14/14 files byte-verified; duplicate construction independently recomputed.
- Native crash runner, process, and task results: 8/8 files byte-verified.
- Sanitized Windows crash-event and WER archive/temp inventory: 3/3 files byte-verified.
- **Total: 57 artifact hashes verified across 8 manifests.** Manifests do not hash themselves.
- JSON parse: all 27 result, wrapper, scheduler and sanitized crash JSON files in the evidence bundle parse successfully.
- JUnit XML parse: all 8 XML files parse; `last750`, recovered threeprior, bridge module and repeats 1/2/4 counts match complete pytest summaries. Original threeprior XML parses but its stdout still conflicts with JSON.
- Evidence file references in this report exist. `r14_state_observer.wxstate.log` now exists at its manifest path.
- Secret scan covered R14 evidence text, JSON, XML, Python/PowerShell runner scripts and this report for private-key headers, bearer/authorization tokens, password assignments, API-token patterns, cookie/session values and credential strings. **No secret material was found.** Runner scripts assign the Session 1 identifier from the current process; this is runtime metadata, not a session credential. The pre-existing PR contract JUnit contains two private-range fixture IP literals for invalid-display validation; these are test inputs, not Kole addresses. No SSH key, cookie content, token, password, or actual Kole/Tailscale host address was found.
- No production or experimental test files were edited in this repair. Full pytest: **NOT RUN**.

## PR #67 isolation

Read-only `gh pr view 67` verification returned:

- State `OPEN`, draft `true`.
- Head branch `codex/audit-x11-paramiko-forwarder-20261114`, exact head `339b86bada84504d2d02af002fad6b6af13777a5`.
- Base `develop` at `2be856dbc3d7a75f7149b1c6243e25af005de799`.
- Title: `security(x11): fail-closed local SSH forwarding protocol (staging only)`.

This matches the expected protocol/security-only PR head. The audit commit `b336316...` is separate. No PR write operation occurred.

## Historical acceptance and remaining blockers

The following status is retained:

- Bridge module: **9/9 PASS**, independent focused JUnit/stdout result; scheduler provenance not independently preserved.
- Ordered GUI/WebView stress: **intermittent native crashes**.
- Native root cause: **OPEN**.
- Integrated full pytest: **NOT PASS** historically; not rerun here.
- R10–R13 X11/package results: **HISTORICAL**.
- Test helper changes: **local experimental**, excluded from `b336316...`.
- PR #67: separate **OPEN/DRAFT** protocol/security PR at expected head.
- Implementation acceptance: **NOT ESTABLISHED**.
- Merge readiness: **NOT EVALUATED**.
- W61.1 receipt SHA reconciliation and NVDA/Orca accessibility review remain separate follow-ups.

Outstanding evidence gaps: the original threeprior stdout conflict, disabled Task Scheduler event history, missing PIDs for most tests, incomplete source identity on some runs, 54 still-registered R14 tasks that conflict with the earlier cleanup receipt, no archived WER dump or unique WER Report IDs, and no complete integrated full-suite result. These prevent `EVIDENCE_COMPLETE`.

## Final verdict

**`EVIDENCE_INCONSISTENT`.** F-02 is repaired. Hashes and structured artifacts validate as stated. The original F-03 artifact set conflicts internally; F-04 is resolved by the duplicated requested node. Recovered evidence is kept separate and does not rewrite history. This verdict is evidence quality only; it does not change X11 acceptance, native-crash status, implementation acceptance, PR review, or merge readiness.

