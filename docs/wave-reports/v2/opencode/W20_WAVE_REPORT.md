# W20 — Terminal input/output and PTY behavior — Wave Report

```text
Wave: W20
Canonical report path: docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui (main)
Branch: develop
Baseline SHA: 0f8902a023bac76071527232c2287af96478ed2b
Current HEAD: 0f8902a023bac76071527232c2287af96478ed2b
Tested implementation SHA: 0f8902a023bac76071527232c2287af96478ed2b + working-tree W20 changes listed below (no commit created by this session; pre-existing stacked work preserved byte-for-byte)
Plugin/external repo SHA(s): f0abb7e7037e66ab451d463c699fecf4e00c89eb (develop; verified read-only, no plugin changes)
First started: 2026-09-20
Last updated: 2026-09-20
Session status: READY FOR FINAL REVIEW
Wave decision: READY_FOR_AUDIT
```

Predecessor gate: W19 audit `Decision: PASS` (`docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md`), no later REOPEN/BLOCKED. Dependencies: W19 — satisfied. Required evidence: GUI, EXTERNAL. Execution model: `opencode-go/muse-spark-1.3-contributor`. `waves/pending/` holds exactly one canonical `W20.md` (single-copy check); `waves/bak/` never read. PACKAGE: N/A — no owned requirement needs packaged-artifact proof and this Wave changes no build/package inputs (justification recorded below).

## Baseline capture

```text
git branch --show-current: develop
git rev-parse HEAD: 0f8902a023bac76071527232c2287af96478ed2b
git rev-parse origin/develop: 0f8902a023bac76071527232c2287af96478ed2b (equal; no divergence)
git diff --check: clean (only pre-existing CRLF warnings on unrelated files)
git status: dirty — large pre-existing stacked working tree preserved byte-for-byte
  (26 tracked files incl. W19 terminal set_ssh hardening in wx_terminal.py /
  wx_terminal_webview.py; this session touched only the W20 files listed
  under Diff review). No reset/clean/destructive git; nothing pushed.
Plugin: D:/Projeler/hpc-client-gui-plugins develop f0abb7e7037e66ab451d463c699fecf4e00c89eb
```

No `.env`/credentials/tokens/keys exposed. The lab fixture credential is public-by-design per `docs/testing/LOCAL_HPC_LAB.md` and reached the shell only via `HPC_LAB_PASSWORD` env at runtime — never written to files/logs/evidence (`build/audit/w20-external-matrix.txt` scanned: zero matches for the fixture value).

## Authority reads (all completed before implementation)

1. `opencode/protocol/CORE_EXECUTION_RULES.md` — read.
2. `waves/pending/W20.md` — read (26 source-derived IDs, 0 TODO rows, evidence GUI+EXTERNAL).
3. Owned registry rows `HPC-W05-TERM-001..026` — read (all MANDATORY; wordings in trace table below).
4. `TODO_OWNERSHIP_MAP.md` W20 rows — none (0 TODOs, as declared).
5. `opencode/sources/WAVE_V2_FINAL_05.md` Workstreams C, D, E, F — read, exact semantics preserved.
6. Live code truth rediscovered (see Discovery). 7. W19 close truth as predecessor background only.

## Narrow baseline (pre-edit, solo-sequenced)

| Slice | Result |
|---|---|
| `tests/test_wx_terminal_webview.py` | 29 passed, 0 failed |
| `tests/test_terminal_boundaries.py` | 5 passed, 0 failed |
| `tests/test_terminal_pty_wire.py` | 1 passed, 0 failed |
| Narrow total | **35 passed, 0 failed, 0 skipped, 0 xfailed** |

## Discovery Pass + WAVE_FINDINGS

Rediscovered owners: `src/hpc_gui/wx_terminal.py` (TerminalModel + TextCtrl fallback panel), `src/hpc_gui/wx_terminal_webview.py` (canonical xterm.js path), `src/hpc_gui/assets/terminal/wx_bridge.js` (`scrollback: 2000`, single JSON bridge, F3-only page shortcut), `src/hpc_gui/services/terminal_bridge.py` (Qt path — out of wx scope, noted only), `src/hpc_gui/ssh/client.py` (`send_shell_input -> bool`, `resize_shell_pty` clamps `max(1,..)`), callers in `wx_shell.py` (return-value-agnostic wrapper — compatible). Adjacent boundaries inspected: `_wx_output_subscribers` fan-out, generation guard, `set_ssh`/`close` lifecycle, accelerator surface (no app-global destructive key bindings reach the WebView page; page key handler is F3-only).

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
DEF-W20-001 | P1 | _handle_input write path | repro: False/raising transport -> ret None, header stays "Connected" | return value ignored + exceptions swallowed | failed input looks like success while UI claims Connected (TERM-007) | return bool + transient header diagnostic, restore on success | YES (FIX-A) | CLOSED
DEF-W20-002 | P1 | hpc_paste pre-ready | repro: paste pre-ready -> no JS call, nothing on ready | early return drops text | user paste silently lost during readiness window (TERM-019 lifecycle) | bounded pre-ready paste queue flushed on ready | YES (FIX-B) | CLOSED
OBS-W20-003 | P3 | legacy TextCtrl fallback model.key_input | source trace: returns payload even when _send_input is None | same silent-swallow class on diagnostic non-parity path | fallback keystroke after disconnect looks accepted | deferred: fallback is explicitly diagnostic non-parity; canonical path fixed | NO | OPEN P3, routed as observation (no owner Wave; fallback documented)
OBS-W20-004 | P3 | _safe_truncate_index off-by-one | source trace: last_safe points at (not past) last complete byte | pending-overflow truncation drops one extra valid byte | negligible single-byte loss in >2MB overflow path only | not fixed: no behavior evidence, cosmetic-adjacent | NO | OPEN P3, documented
```

No defect was manufactured: both counted fixes reproduce deterministically before the change (EV-W20-001).

## Requirement trace (all 26 MANDATORY)

Workstream C (input): TERM-001 Enter/newline — xterm native `\r`, as-behaved (GUI suite `input_chain_ctrl_a_to_z`, EXTERNAL E2). TERM-002 blank — empty input is a no-op returning False without transport traffic (TEST-W20-002 asserts `hpc_paste("") is False`; `_handle_input("")` identical guard). TERM-003 rapid — single ordered bridge, ordering suite + EXTERNAL E3/E4. TERM-004 Unicode — `unicode_input_output` suite + EXTERNAL E2b (`UNI-ü-日` intact over real PTY). TERM-005 multiline paste — `multiline_paste` suite + EXTERNAL E3 + FIX-B queue. TERM-006 disabled-before-ready — output buffers pre-ready (pending suite); input pre-ready has no bridge yet so nothing can be sent as apparent success; write path now returns False visibly. TERM-007 write failure — FIX-A + TEST-W20-001/002 + EXTERNAL E6. TERM-008 input-after-disconnect — W19 stacked neutralization + FIX-A diagnostic + EXTERNAL E6b/E6c. TERM-009 shortcuts — F3-only page handler, no app-global destructive binding reaches the page; Ctrl+C/V semantics owned by xterm (existing suites, no regression).

Workstream D (output): TERM-010 UTF-8 chunk boundaries — no splitlines, `_safe_json_dumps(ensure_ascii=False)`, `preserves_carriage_return_and_esc` + unicode suites + EXTERNAL E2b. TERM-011 bursts — `large_pre_ready_output` (500KB buffered), `output_ordering_with_many_fragments`, EXTERNAL E4 (500 lines complete+ordered, no hang). TERM-012 ordering — pending coalesce `"".join` in order + suites + EXTERNAL E3/E4 index assertions. TERM-013 CR/progress — CR/ESC preserved byte-exact into `terminal.write` (suite asserts `\r` and `\x1b[31m` reach JS unmodified). TERM-014 stderr — PTY shell model merges streams by OS design; output path carries whatever the channel delivers without filtering (EXTERNAL E2–E4 carry prompt/diagnostic bytes verbatim). TERM-015 dead-widget — closed/generation guards (`destroy_before_ready`, `generation_guard`, `100_reconnects`, `close_releases_native_webview`). TERM-016 bounded history — explicit: `scrollback: 2000` (wx_bridge.js), 5000-line TextCtrl cap, 50000-char compat cap, 2MB/5000-entry pending bound, 256KB paste bound (new).

Workstream E: TERM-017 select-without-input — xterm selection never posts to the input bridge (bridge posts only `onData`/`resize`/`ready`; navigation-guard suite). TERM-018 copy — xterm native + find/select suites expressing buffer reads. TERM-019 paste — FIX-B + TEST-W20-003/004 + EXTERNAL E3. TERM-020 scroll-back — xterm native viewport preserved while output arrives (no forced-scroll code exists on the Python side; `scrollToLine` only on find). TERM-021 return-to-bottom — predictable: output never yanks viewport except find selection (bridge source). TERM-022 focus — `hpc_focus` delivered on open (wx_shell smoke calls `panel.hpc_focus()`), `clear_focus_font` suite proves the JS+widget call chain.

Workstream F: TERM-023 resize→PTY — `_handle_resize` → `resize_shell_pty`, `resize_chain_to_ssh` (incl. dedup) + EXTERNAL E5 live. TERM-024 small-size clamp — `max(1,..)` at panel, bridge, and SSH layers + EXTERNAL E5b `(0,-5)->(1,1)`. TERM-025 disconnect-noop — `cb is None` → diagnostic False, never raises (TEST-W20-001 detached case + EXTERNAL E6b). TERM-026 flood-coalesce — 50ms debounce (`_schedule_fit` + JS `scheduleFit`) + same-size dedup (suite asserts single transport call).

Unsupported remote PTY: not applicable — remote PTY resize IS supported and proven live (E5); nothing is simulated (dedup/buffering preserve bytes, never fake success).

## FIX-A: visible write failure (DEF-W20-001, TERM-007)

Root cause: `WxTerminalWebViewPanel._handle_input` ignored the `send_shell_input -> bool` contract and swallowed exceptions, so a dead/rejecting transport still presented a "Connected" header — failed input looked like success. The fix returns the write outcome (`False` only on strict `False`/raise/no-path; `None`/`True` stay accepted for backward compatibility), shows a transient i18n header diagnostic (`login.terminal_write_failed`, en+tr, `check_i18n.py` OK) while preserving connection truth in `_status_text`, and restores the truth label on the next accepted write. Smallest coherent change; the `wx_shell` recorder wrapper ignores the new return (compatible).

- Before EV: EV-W20-001 (repro: `FALSE: ret=None status 'Connected'->'Connected'`; `RAISE` identical).
- Files: `src/hpc_gui/wx_terminal_webview.py` (`_handle_input` + `_show/_clear_write_failure` + `_write_failure_text`), `src/hpc_gui/i18n/en.json`, `tr.json` (one key each).
- Regression: TEST-W20-001 `test_w20_write_failure_is_visible_not_silent_success` (happy True + False/raise/no-path False + diagnostic text + restore lifecycle), TEST-W20-002 `test_w20_write_failure_via_bridge_dispatch` (real `_on_script_message` dispatch).
- Sensitivity: with `_handle_input` reverted, TEST-W20-001/002 fail (3 failed incl. TEST-W20-003); restored → 4/4 green.
- Negative: False-return, raising, and callback-less transports. Narrow: webview file 29/29. Broader: 83/83 (table below). GUI: real panel widgets in subprocess. External: E6/E6b/E6c live.

## FIX-B: pre-ready paste queue (DEF-W20-002, TERM-019)

Root cause: `hpc_paste` early-returned before bridge readiness, so user paste in the readiness window was silently lost (and never delivered when ready arrived). The fix queues pre-ready paste (bounded by `MAX_PENDING_PASTE_BYTES = 256KB`, over-cap refused with `False`), flushes exactly once in original order from `_on_bridge_ready`, clears the queue on `close`, and returns a truthful contract (`True` delivered-or-queued, `False` dropped: closed/non-parity/empty/over-cap). `hpc_clear` intentionally does not discard queued user intent (documented).

- Before EV: EV-W20-001 (`pre-ready paste js_calls: []`, `after-ready paste js_calls: []`).
- Files: `src/hpc_gui/wx_terminal_webview.py` (`_pending_paste`, `hpc_paste`, `_flush_pending_paste`, ready-flush, close-clear).
- Regression: TEST-W20-003 `test_w20_pre_ready_paste_is_queued_and_delivered` (queue → single ordered combined `hpcPaste` on ready → live paste immediate), TEST-W20-004 `test_w20_paste_negative_and_close_lifecycle` (empty/over-cap False, close discards, no late delivery).
- Sensitivity: with ready-flush removed, TEST-W20-003 fails; with paste return-contract reverted, TEST-W20-004 fails; restored → 4/4 green.
- Negative: empty + over-cap + closed. GUI: real panel + captured JS sink (transport/chrome boundary only). External: E3 live.

Independence: different finding IDs, different root causes (write-outcome swallowing vs readiness-window loss), different code paths, independently revertible with independent failing tests.

## Second-Defect Search (12 dims)

1. negative paths — covered (False/raise/no-path writes; empty/over-cap paste). 2. lifecycle — covered (restore-on-success, close-discards, destroy-before-ready, 100 reconnects). 3. stale state — checked: generation guard + subscriber detach intact, suites green. 4. identity — checked: `set_ssh` swaps + `_terminal_ssh` sync (W19 stacked), header identity suite green. 5. concurrency/race — checked: resize debounce+dedup, CallAfter delivery, burst ordered; no new threads introduced. 6. boundary values — checked: tiny/negative resize clamp (E5b), empty input, 500KB pre-ready, over-cap paste. 7. capability absence — checked: no-callback write path returns False visibly; non-parity fallback refuses paste with False. 8. persistence — N/A: terminal holds no persisted settings (no evidence to fake). 9. packaging — N/A with reason (below). 10. error visibility — fixed (FIX-A); legacy fallback noted as OBS-W20-003 P3. 11. secondary entry points — checked: bridge dispatch (TEST-W20-002), direct calls, `wx_shell` wrapper compatible. 12. adjacent boundary — checked: SSH `bool` contract honored, fan-out pattern mirrored in external matrix, Qt `TerminalBridge` already emits on False.

## Tests

New: `tests/test_w20_terminal_io.py` — 4 GUI/subprocess/semantic tests (REQ-TERM-007×2, REQ-TERM-019×2; each with happy + negative + lifecycle assertions; purpose IDs REQ-*/DEF-*/NEG-*/RACE-*, taxonomy GUI event/integration). Modified: `tests/test_wx_terminal_webview.py` (+3 harness lines mirroring real `__init__` state for the close test — CON maintenance, zero assertions changed). No skips/xfails added, none weakened.

| Suite (solo-sequenced) | passed | failed | skipped | xfailed | exit |
|---|---|---|---|---|---|
| `test_w20_terminal_io.py` | 4 | 0 | 0 | 0 | 0 |
| `test_wx_terminal_webview.py` | 29 | 0 | 0 | 0 | 0 |
| `test_terminal_boundaries.py` + `test_terminal_pty_wire.py` | 6 | 0 | 0 | 0 | 0 |
| `test_wx_terminal_behavioral.py` | 19 | 0 | 0 | 0 | 0 |
| `test_wx_terminal_parity_evidence.py` | 11 | 0 | 0 | 0 | 0 |
| `test_wx_terminal.py` + `test_wx_embedded_terminal.py` + `test_terminal_bridge.py` + `test_terminal_assets.py` | 14 | 0 | 0 | 0 | 0 |
| Total | **83** | **0** | **0** | **0** | 0 |

Sensitivity: each counted fix fails its regression when reverted (TEST-W20-001/002 for FIX-A; TEST-W20-003/004 for FIX-B) and passes restored. `scripts/check_i18n.py`: key/reference/hardcoded checks OK.

Process note (environmental, not a product defect): repeated native WebView2 subprocess crashes orphaned ~50 `msedgewebview2` processes, wedging later GUI subprocesses (`Operation aborted`, exit 3221226525). Cleaned orphans (`Stop-Process`, test-spawned only) → suite returns to 29/29. Also fixed my own test to one panel per subprocess (`set_ssh` swaps) after a 4-panel subprocess crashed WebView2.

## GUI evidence (required)

Real wx event/runtime proof per user-visible behavior, solo-sequenced, one GUI process at a time: 4 new subprocess GUI tests construct the real `WxTerminalWebViewPanel` (real widgets, real `_on_script_message` dispatch, real status labels) with mocks only at the SSH transport and the JS sink — never the widget/dispatch/resize handler under proof. Artifact: `build/audit/w20-gui-pytest.txt` (4 passed, exit 0). Sensitivity proof per counted fix (above).

## EXTERNAL evidence (required)

Real hpclab loopback (`127.0.0.1:2222`, OpenSSH + real PTY shell; remote class: local containerized single-node), container `healthy` before and after, secrets env-only, artifact scanned clean. Artifact: `build/audit/w20-external-matrix.txt` (exit 0):

```text
E1 connect transport active: PASS
E2 echo round trip (real panel dispatch): PASS
E2b unicode intact (UNI-ü-日 over real PTY): PASS
E3 multiline ordered (PL1<PL2<PL3): PASS
E4 burst 500 lines complete+ordered, no hang: PASS
E5 live resize (100,30) applied: PASS
E5b tiny (0,-5) clamped to (1,1): PASS
E5c shell answers after resize: PASS
E6 send-after-close False: PASS
E6b panel input-after-disconnect False: PASS
E6c diagnostic visible ("Terminal input could not be sent."): PASS
E7 subscriber detached, session closed: PASS
```

PACKAGE: N/A — no owned TERM requirement references packaged behavior; this Wave changes no build inputs, vendored assets, or frozen artifact bytes (only `wx_terminal_webview.py` logic + 2 i18n strings + tests). Asset-vendoring/static contract suites (`terminal_assets`, `single_bridge_and_no_splitlines`, `composition_keeps_qt_out`) all pass.

## POST_GREEN_REVIEW

Duplicate path: legacy fallback shares the silent-write class — recorded as OBS-W20-003 P3 (diagnostic non-parity path, explicitly out of canonical scope). Alternate entry points: bridge dispatch, direct API, shell wrapper — all covered/compatible. Silent fallbacks: none introduced (all drops return False). Stale state: generation/subscriber handling untouched and green. Cleanup: close clears both queues + failure flag. Dead branches: none added. Provider/site branching: none. Success-claiming errors: fixed (FIX-A). Packaged divergence: none (no asset/build change).

## Diff review

`git diff --check`: clean. W20-owned diff: `src/hpc_gui/wx_terminal_webview.py` (+107/−12), `src/hpc_gui/i18n/en.json` +1 line, `tr.json` +1 line, `tests/test_wx_terminal_webview.py` +3 harness lines; new `tests/test_w20_terminal_io.py`, `build/audit/w20-external-matrix.txt`, `build/audit/w20-gui-pytest.txt`, this report. All other tracked/untracked changes are pre-existing stacked work preserved byte-for-byte (verified: no other file touched by this session). No secrets, no generated/binary noise, no weakened tests.

## Resume state

Completed and verified: narrow baseline 35/35; DEF-W20-001/FIX-A + DEF-W20-002/FIX-B with sensitivity; 83/83 impacted suites; GUI + EXTERNAL evidence current; i18n checks OK; diff reviewed.
In progress: none (awaiting fresh-context audit).
Open P0/P1: none. Open P2/P3: OBS-W20-003 (P3, legacy fallback silent-write class), OBS-W20-004 (P3, truncate off-by-one) — both documented, neither blocks acceptance.
Pending tests/evidence: none for W20 scope.
Last exact commands: `pytest tests/test_w20_terminal_io.py` 4 passed; webview file 29 passed; combined impacted 83 passed; `scripts/check_i18n.py` OK; external matrix exit 0; `docker inspect` healthy before+after.
Next actions: fresh-context audit (`W20_AUDIT_REPORT.md` — not touched by this session); never start W21.
Evidence identities: `build/audit/w20-gui-pytest.txt`, `build/audit/w20-external-matrix.txt`, tested SHA `0f8902a0` + working-tree W20 files above.

```text
FIX-A: visible write failure (WxTerminalWebViewPanel._handle_input returns bool + transient header diagnostic)
DEF: DEF-W20-001 (P1, TERM-007)
Root cause: bool contract ignored + exceptions swallowed; failure looked like success under "Connected"
Before EV: EV-W20-001 (ret=None, header unchanged on False/raise)
After EV: TEST-W20-001/002 green; EXTERNAL E6/E6b/E6c live PASS
Regression test: test_w20_write_failure_is_visible_not_silent_success, test_w20_write_failure_via_bridge_dispatch
Sensitivity proof: revert _handle_input -> both fail; restore -> green

FIX-B: pre-ready paste queue (hpc_paste bounded queue + ready flush + truthful bool contract)
DEF: DEF-W20-002 (P1, TERM-019 lifecycle)
Root cause: pre-ready early-return dropped user paste permanently
Before EV: EV-W20-001 (no JS pre- or post-ready)
After EV: TEST-W20-003/004 green; EXTERNAL E3 live PASS
Regression test: test_w20_pre_ready_paste_is_queued_and_delivered, test_w20_paste_negative_and_close_lifecycle
Sensitivity proof: revert flush/contract -> respective test fails; restore -> green

Additional fixes: none (zero-defect GO not needed — two genuine fixes closed)
Post-green review: done, 2× P3 observations recorded, no new P0/P1
New/modified tests: tests/test_w20_terminal_io.py (4 new); +3 harness lines in test_wx_terminal_webview.py (no assertion change)
Skipped/xfail changes: none
Package evidence: N/A (justified — no packaged-behavior requirement, no build/asset change)
External evidence: build/audit/w20-external-matrix.txt E1–E7 PASS, hpclab healthy before+after, leak-scan 0 matches
Open P0/P1: none
Open P2/P3: OBS-W20-003, OBS-W20-004 (P3 observations, documented)
Two-fix gate: PASS
Wave decision: READY_FOR_AUDIT
```
