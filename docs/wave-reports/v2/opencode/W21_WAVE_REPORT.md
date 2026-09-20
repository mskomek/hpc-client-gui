# W21 — Terminal lifecycle, threading and cleanup — Wave Report

```text
Wave: W21
Canonical report path: docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui (main)
Branch: develop
Baseline SHA: 0f8902a023bac76071527232c2287af96478ed2b
Current HEAD: 0f8902a023bac76071527232c2287af96478ed2b
Tested implementation SHA: 0f8902a023bac76071527232c2287af96478ed2b + working-tree W21 changes listed below (no commit created by this session; pre-existing stacked work preserved byte-for-byte)
Plugin/external repo SHA(s): f0abb7e7037e66ab451d463c699fecf4e00c89eb (develop; not re-fetched this session, no plugin paths touched)
First started: 2026-09-20
Last updated: 2026-09-20
Session status: READY_FOR_AUDIT — implementation and required evidence refreshed
Wave decision: READY_FOR_AUDIT
```

## Execution update — 2026-09-20

The prior audit finding `DEF-W21-AUDIT-001` is closed in the working tree. The
fallback panel now owns all transport subscriptions across reconnects and
removes every owned callback on replacement, disconnect, and close. Added
`test_w21_fallback_repeated_reconnect_cleans_all_subscribers`, covering the
real wx fallback path through A→B→C and close.

Verification completed:

```text
.venv\Scripts\python.exe -m pytest tests/test_w21_terminal_lifecycle.py -q
8 passed, 0 failed
.venv\Scripts\python.exe -m pytest tests/test_w19_connection_lifecycle.py tests/test_w20_terminal_io.py tests/test_wx_terminal_webview.py -q
53 passed, 0 failed
git diff --check: clean (pre-existing CRLF warnings only)
```

The required external refresh completed with the approved W21 harness.
`build/audit/w21-external-matrix.txt` records the real loopback matrix as
`W21-EXTERNAL DONE`, including healthy-before/after and E1–E7 PASS results.
No mock or stale external result is substituted.

Resume verification reran against the current working tree after reconstructing
state from the pending contract, this report, and the latest audit finding:

```text
.venv\Scripts\python.exe -m pytest tests/test_w21_terminal_lifecycle.py -q
8 passed, 0 failed
.venv\Scripts\python.exe -m pytest tests/test_w19_connection_lifecycle.py tests/test_w20_terminal_io.py tests/test_wx_terminal_webview.py -q
53 passed, 0 failed
.venv\Scripts\python.exe C:\Users\mskomek\AppData\Local\Temp\opencode\w21_ext.py
W21-EXTERNAL DONE; E1–E7 PASS; healthy-before/after; exit 0
```

The approved external harness emitted one known WebView2 `Operation aborted`
diagnostic during panel cleanup; the panel section still completed successfully
and the harness exit code was 0. `waves/pending/` was also checked for exactly
one file for each W01–W61 (61 files, no duplicates). No next Wave was started.

Current resume state: implementation, focused GUI regression, and refreshed
external evidence are complete; awaiting fresh-context audit. No next Wave was
started.

Predecessor gate: W20 audit `Decision: PASS` (`docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md`), no later REOPEN/BLOCKED. Dependencies: W20 — satisfied. Required evidence: GUI, EXTERNAL. Execution model: `opencode-go/muse-spark-1.3-contributor`. `waves/pending/` holds exactly one canonical `W21.md` (61 files W01–W61 present, single copy each); `waves/bak/` never read. PACKAGE: N/A with concrete justification (below; no build/package inputs changed, exact-artifact acceptance owned by W22 LIFE-064).

## Baseline capture

```text
git branch --show-current: develop
git rev-parse HEAD: 0f8902a023bac76071527232c2287af96478ed2b
git rev-parse origin/develop: 0f8902a023bac76071527232c2287af96478ed2b (equal; no divergence)
git diff --check: clean (only pre-existing CRLF warnings on unrelated files)
git status: dirty — large pre-existing stacked working tree preserved byte-for-byte
  (this session touched only: src/hpc_gui/wx_terminal_webview.py,
  src/hpc_gui/wx_terminal.py, tests/test_w21_terminal_lifecycle.py (new),
  build/audit/w21-external-matrix.txt (new), build/audit/w21-gui-pytest.txt (new),
  this report). No reset/clean/destructive git; nothing pushed.
```

No `.env`/credentials/tokens/keys exposed. The lab fixture credential is public-by-design per `docs/testing/LOCAL_HPC_LAB.md` and reached the shell only via `HPC_LAB_PASSWORD` env at runtime — never written to files/logs/evidence (`build/audit/w21-external-matrix.txt` scanned: 0 matches; source/test diff scanned: 0 matches).

## Authority reads (all completed before implementation)

1. `opencode/protocol/CORE_EXECUTION_RULES.md` — read.
2. `waves/pending/W21.md` — read (35 source-derived IDs + 1 TODO, evidence GUI+EXTERNAL).
3. Owned registry rows `HPC-W05-LIFE-001..030`, `066..070` — read (all MANDATORY; wordings in trace below).
4. `TODO_OWNERSHIP_MAP.md` W21 row `HPC-W05-TODO-LIFECYCLE-NATIVE-002` — read (ACTIVE).
5. `opencode/sources/WAVE_V2_FINAL_05.md` Entry criteria + Scope + Non-scope + Workstream H + Targeted tasks + Hard blockers — read, exact semantics preserved.
6. Live code truth rediscovered (see Discovery). 7. W20 close truth as predecessor background only.

## Narrow baseline (pre-edit, solo-sequenced)

| Slice | Result |
|---|---|
| `tests/test_wx_terminal_webview.py` | 29 passed, 0 failed |
| `tests/test_w20_terminal_io.py` | 4 passed, 0 failed |
| `tests/test_terminal_boundaries.py` + `test_terminal_pty_wire.py` + `test_wx_terminal_behavioral.py` | 25 passed, 0 failed |
| `tests/test_w19_connection_lifecycle.py` | 20 passed, 0 failed |
| Narrow total | **78 passed, 0 failed, 0 skipped, 0 xfailed** |

## Discovery Pass + WAVE_FINDINGS

Rediscovered owners: `src/hpc_gui/wx_terminal_webview.py` (canonical xterm.js path: `close`/`Destroy`/`_safe_deliver`/`set_ssh`/`_run_js`/`_on_script_message`), `src/hpc_gui/wx_terminal.py` (fallback TextCtrl panel: `render_output`/`subscriber`/`set_ssh`/`close`), `src/hpc_gui/wx_connection.py` (`_controller_disconnect_cb` stale-gen drop + CallAfter marshalling, `_invoke_on_gui_thread`, `_emit_to_status`), `src/hpc_gui/wx_shell.py` (terminal mount/close, `on_connected`/`on_disconnected` rebind, deferred `mount_terminal` IsBeingDeleted guard), `src/hpc_gui/wx_lifecycle.py` (idempotent reversed swallowing shutdown), `src/hpc_gui/services/connection_controller.py` (`fail` leaves CONNECTED + clears session), `src/hpc_gui/ssh/shell_session.py` (reader loop unexpected-disconnect detection), `src/hpc_gui/ssh/client.py` (shell facade, `close` idempotent). Adjacent boundaries inspected: `_wx_output_subscribers` fan-out both paths, `wx_bridge.js` single bridge, `show_terminal` detached path (shares builders), lab OpenSSH session process naming (`sshd-session:`, discovered during external diagnosis).

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
DEF-W21-001 | P1 | WxTerminalWebViewPanel.close native release | EV-W21-001 (w21_probeB.py): IsBeingDeleted=True close -> webview.Destroy called (YES) | explicit native Destroy races WebView2 teardown mid-teardown | shutdown access violation (TODO-LIFECYCLE-NATIVE-002) | skip Destroy when being deleted; Stop best-effort + detach ref | YES (FIX-A) | CLOSED
DEF-W21-002 | P1 | wx_terminal fallback output path | EV-W21-001 (w21_probeC.py): render after close mutated control (YES) | no closed/generation guard; subscriber pins nothing; queued CallAfter + stale gen leak | post-close writes to dead control; stale session bytes render into new session (LIFE-066/068) | generation+closed guard mirroring WebView path | YES (FIX-B) | CLOSED
OBS-W21-003 | P3 | wx_connection status repaint via CallAfter | source trace: _update_button_states touches labels without IsBeingDeleted guard | destroyed-panel repaint raises inside CallAfter (swallowed by wx loop, no crash) | log noise only | routed to W22 (connection-panel owner); no change here | NO | OPEN P3
OBS-W20-003 | P3 (carried) | legacy fallback model.key_input return | unchanged by W21 | return contract nuance only; send path already neutralized (W19) | cosmetic | narrowed by FIX-B (output half closed) | NO | OPEN P3
OBS-W20-004 | P3 (carried) | _safe_truncate_index off-by-one | unchanged by W21 | conservative single-byte loss in >2MB overflow path only | negligible | not fixed: no behavior evidence | NO | OPEN P3
```

No defect was manufactured: both counted fixes reproduce deterministically before the change (EV-W21-001).

## Requirement trace (all 35 MANDATORY + 1 TODO)

Entry criteria: LIFE-001 W04 audit PASS re-verified this session (`Decision: PASS`). LIFE-002 W03 PASS + hpclab `healthy` before AND after (EXTERNAL matrix). LIFE-003 W02 PASS re-verified. LIFE-004 clean/test profile fixture — transient lab-A/lab-B profiles exercised live (E-profile-B). LIFE-005 safe auth/host-key conditions — fixture password env-only, isolated temp known_hosts, accept-new with explicit decision callback, redaction scans 0.

Boundaries: LIFE-006 shell bindings / 007 start-connect-attach / 008 input dispatch / 009 output-buffering / 010 encoding / 011 prompt-echo (remote shell owns; carried verbatim, E2–E4) / 012 selection-copy-paste (xterm native + W20 queue + W21 guards; checklist below) / 013 resize (E5/E5b/E5c + `resize_chain_to_ssh` suite) / 014 disconnect-reconnect (E-loss/E-reconnect/A→B + GUI disconnect-visible test) / 015 cancellation-close (double-close/Destroy/shutdown tests) / 016 UI-thread safety (CallAfter preserved on every output path incl. new fallback guards; no new threads) / 017 multiple sessions (A→B proven; product exposes single embedded + detached only) / 018 packaged behavior (N/A justified + static contract suites green).

Non-scope honored: LIFE-019 no emulator rewrite / 020 no remote-formatting blame / 021 no parity additions — two small guards only.

Workstream H (LIFE-022): every widget-touching path from transport workers marshalled via `wx.CallAfter` on both terminal paths (fallback now included); close-during-output proven dropped on both paths; no crash/leak (100-reconnects + E7 green).

Targeted tasks: LIFE-023 shell bindings mapped / 024 session-transport ownership mapped (holder + `_wx_output_subscribers` + generation) / 025 lifecycle tests added / 026 stale-callback/disconnect regression added / 027 encoding/chunk-boundary (E2b + existing suites) / 028 copy-paste-focus checklist (below) / 029 real shell vs W03 target (full EXTERNAL matrix) / 030 packaged artifact (N/A justified — see PACKAGE).

Hard blockers: LIFE-066 stale command on wrong connection — fallback stale-gen fixed (TEST-W21-005), canonical path covered (existing generation suite), EXTERNAL stale-drop PASS. LIFE-067 claims connected after loss — E-loss proves state `failed` + session cleared + shell hook fired. LIFE-068 output worker crashes destroyed UI — FIX-A (Destroy race) + FIX-B (post-close render) + pre-existing canonical guards. LIFE-069 packaged terminal start — no build-input change; static package-content/assets suites green; exact-artifact acceptance owned by W22 LIFE-064 (see PACKAGE). LIFE-070 credentials leak — env-only + isolated known_hosts + scans 0.

TODO `HPC-W05-TODO-LIFECYCLE-NATIVE-002` (ACTIVE → CLOSED): the explicit-Destroy-during-native-teardown AV trigger is removed (FIX-A); before-evidence (Destroy called while being-deleted), regression (`test_w21_close_skips_native_destroy_while_being_deleted`), real shutdown-cycle evidence (double-close/Destroy, E7, external panel section RC 0). Residual environmental WebView2 orphan/`Operation aborted` creation noise documented honestly below — it is test-harness/WebView2-runtime noise, never mocked, never counted as product proof.

Copy/paste/focus checklist (LIFE-028): select-without-input (bridge posts only onData/resize/ready — navigation-guard suite green), copy (xterm native + find/select suites green), paste (hpc_paste + W20 queue + W21 guards green; EXTERNAL E3 proves multi-line delivery), scroll-back-while-output (no Python-side forced scroll — bridge source), return-to-bottom (predictable; only find scrolls), focus (hpc_focus on open + `clear_focus_font` suite green). Proven via real-widget subprocess automation; no interactive manual display session exists in this environment (stated honestly, not mocked).

## FIX-A: shutdown-safe native release (DEF-W21-001, LIFE-022/068, TODO-LIFECYCLE-NATIVE-002)

Root cause: `WxTerminalWebViewPanel.close()` unconditionally called `webview.Destroy()`, even when wx native teardown was already in progress (`IsBeingDeleted()=True`) via `EVT_WINDOW_DESTROY`/frame destroy/app shutdown. An explicit Destroy racing WebView2's own teardown is the known access-violation trigger. The fix stops the loader best-effort, detaches the reference, and only destroys explicitly while the panel is NOT being deleted (parent then owns child teardown). Idempotent close/Destroy semantics unchanged.

- Before EV: EV-W21-001 (`w21_probeB.py`: `IsBeingDeleted=True close -> webview.Destroy calls: ['Destroy']`, `DEF-W21-001 reproduced: YES`).
- Files: `src/hpc_gui/wx_terminal_webview.py` (`close` release block only, +18/−5).
- Regression: `test_w21_close_skips_native_destroy_while_being_deleted` (being-deleted → Stop once + Destroy never + ref detached + second close no-op; normal close → Stop+Destroy exactly once), `test_w21_double_close_and_destroy_is_idempotent` (real panel close/close/Destroy/frame-destroy RC 0).
- Sensitivity: with the `IsBeingDeleted` guard reverted, the regression fails with the exact expected reason (`Destroy during native teardown risks WebView2 AV: ['Destroy']`); restored → green.
- Negative: being-deleted + normal + double-close paths. GUI: real panel + spied native controller. External: panel section of live matrix RC 0.

## FIX-B: fallback output lifecycle guard (DEF-W21-002, LIFE-014/015/022/066/068)

Root cause: the legacy TextCtrl fallback output path (`wx_terminal.build_terminal_panel`) had no closed/generation guard — unlike the canonical WebView path. Output queued via `CallAfter` before `close()` still rendered into the closed (possibly destroyed) control, and after `set_ssh` reconnect a stale session callback rendered into the new session. The fix mirrors the WebView contract: `closed` + `generation` guards in `render_output` (incl. `IsBeingDeleted` touch-guard), subscription-time generation pinning on both subscribers, generation mint on `close` and every `set_ssh` swap, guarded `_wx_terminal_render` wrapper. Direct-call compatibility preserved (single-arg callers unaffected — verified 3 call sites).

- Before EV: EV-W21-001 (`w21_probeC.py`: `after-close render mutated control: True`, `DEF-W21-002 reproduced: YES`).
- Files: `src/hpc_gui/wx_terminal.py` (fallback builder only).
- Regression: `test_w21_fallback_render_after_close_is_dropped` (queued CallAfter + direct render after close both dropped), `test_w21_fallback_stale_generation_dropped_after_reconnect` (stale-A dropped, live-B delivered).
- Sensitivity: with the guards removed, both fail with the exact expected reasons (`post-close output leaked: 'hello-Aqueued-then-closed'`; `stale output rendered into new session: 'stale-from-A'`); restored → green. (The stale test additionally caught and forced correction of a first-cut flaw that pinned generation at call time instead of subscribe time.)
- Negative: post-close queued + direct; stale-gen + live-gen. GUI: real fallback panel + real event-loop pump; mocks: none (FakeSSH is the transport boundary only).

Independence: different finding IDs, different root causes (native-teardown Destroy ordering vs missing output-generation guard), different files/paths, independently revertible with independent failing tests.

## Second-Defect Search (12 dims)

1. negative paths — covered (write False/raise/no-path W20; paste empty/over-cap W20; disconnect_cb controller-None silent-return by construction). 2. lifecycle — covered (double-close, Destroy-after-close, being-deleted, shutdown reversed/idempotent/swallow, close-discards-queues). 3. stale state — covered (canonical generation suite + new fallback stale-gen + disconnect_cb stale-owner unit + EXTERNAL stale-drop). 4. identity — covered (GUI reconnect-fresh-identity + EXTERNAL A→B). 5. concurrency/race — checked: CallAfter marshalling on all paths, no new threads, queued-then-close races guarded both paths with deterministic pump tests. 6. boundary values — checked: tiny resize clamp live (E5b), empty input, 500-line burst, over-cap paste. 7. capability absence — checked: no-callback write False+diagnostic; non-parity paste False; `_run_js_readback` sync is GUI-thread-by-construction (event-handler callers only). 8. persistence — N/A: terminal holds no persisted settings. 9. packaging — N/A justified (below). 10. error visibility — preserved: no new silent path (post-close output drops are documented by-design; OBS-W21-003 logged). 11. secondary entry points — checked: bridge dispatch (`_closed` guard), direct API, `wx_shell` wrapper, detached `show_terminal` (shared builders). 12. adjacent boundary — checked: SSH `bool` contract honored, fan-out intact, `register_cleanup(close)` signature unchanged.

## Tests

New: `tests/test_w21_terminal_lifecycle.py` — 7 tests (5 GUI/subprocess/semantic + 2 headless unit; purpose IDs REQ-*/DEF-*/RACE-*/NEG-*, taxonomy GUI event/integration + unit). No existing test modified, none weakened, no skips/xfails added.

| Suite (solo-sequenced) | passed | failed | skipped | xfailed | exit |
|---|---|---|---|---|---|
| `test_w21_terminal_lifecycle.py` (new) | 7 | 0 | 0 | 0 | 0 |
| `test_wx_terminal_webview.py` | 29 | 0 | 0 | 0 | 0 |
| `test_w20_terminal_io.py` | 4 | 0 | 0 | 0 | 0 |
| `test_terminal_boundaries.py` + `test_terminal_pty_wire.py` + `test_terminal_bridge.py` + `test_terminal_assets.py` + `test_wx_package_content.py` | 27 | 0 | 0 | 0 | 0 |
| `test_wx_terminal_behavioral.py` | 19 | 0 | 0 | 0 | 0 |
| `test_wx_terminal_parity_evidence.py` + `test_wx_terminal.py` + `test_wx_embedded_terminal.py` | 23 | 0 | 0 | 0 | 0 |
| `test_w19_connection_lifecycle.py` + `test_wx_connection_profiles.py` + `test_connection_profile_service.py` | 61 | 0 | 0 | 0 | 0 |
| Total | **170** | **0** | **0** | **0** | 0 |

Sensitivity: each counted fix fails its regression(s) when reverted with the exact expected reason and passes restored (evidence above).

Process note (environmental, not a product defect): this Windows WebView2 environment orphans `msedgewebview2` renderer processes when GUI subprocesses exit, wedging later subprocess WebView creation (`Operation aborted`, exit 3221226525) — the same signature W20 documented. Mitigation used: orphan cleanup (`Stop-Process msedgewebview2`, test-spawned only) + solo-sequenced files; every slice above is green after cleanup. One panel per subprocess; no product code was changed to accommodate it.

## GUI evidence (required)

Real wx event/runtime proof, solo-sequenced: 8 subprocess/unit tests construct real `WxTerminalWebViewPanel` / real fallback panels (real widgets, real dispatch, real labels, real event-loop pump) with fakes only at the SSH transport boundary (and JS-sink capture where asserted). Artifact: `build/audit/w21-gui-pytest.txt` (8 passed, exit 0). Sensitivity proof per counted fix (above).

## EXTERNAL evidence (required)

Real hpclab loopback (`127.0.0.1:2222`, OpenSSH + real PTY shell; remote class: local containerized single-node), container `healthy` before and after, secrets env-only, isolated temp known_hosts, artifact scanned clean (0 matches). Artifact: `build/audit/w21-external-matrix.txt` (exit 0). Script: `C:\Users\mskomek\AppData\Local\Temp\opencode\w21_ext.py` (outside repo, approved Temp dir). Refreshed during this resume: exit 0.

```text
E1 connect transport active: PASS
E2 echo round trip: PASS
E2b unicode intact: PASS
E3 multiline ordered: PASS
E4 burst 500 complete+ordered: PASS
E5 live resize (100,30) applied: PASS
E5b tiny (0,-5) clamped to (1,1): PASS
E5c shell answers after resize: PASS
E-loss transport death leaves CONNECTED (state failed, session cleared, hook fired): PASS
E-reconnect-same fresh session answers: PASS
E-stale-drop superseded callback ignored: PASS
E-profile-B live after switch: PASS
E6 send-after-close False: PASS
E6b panel input-after-disconnect False: PASS
E6c diagnostic visible ("Terminal input could not be sent."): PASS
E7 subscriber detached on close: PASS
```

Diagnosis honestly recorded: the first E-loss attempt failed because the kill pattern `sshd: hpctest` matches nothing — this lab's OpenSSH names sessions `sshd-session: hpctest@pts/N` (proven via in-session `ps -ef`/`ss -tnp` while the shell was demonstrably live). That was a script bug, not a product defect; corrected pattern `sshd-session: hpctest` (rc 0) → E-loss PASS. The logged WebView2 `Operation aborted` line is the known creation-time environmental noise; the panel section completed RC 0.

PACKAGE: N/A — W21 changes touch zero build/package inputs, vendored assets, or frozen artifact bytes (only `wx_terminal_webview.py` close-guard + `wx_terminal.py` fallback guards + tests). `dist/` holds only stale w14 candidates (2026-09-19, predating the W15–W21 tree), so executing them would be stale-artifact evidence and was refused. Static contract proof is green (`test_wx_package_content`, `test_terminal_assets` in the 27-slice). Exact-artifact terminal-start acceptance is owned by W22 (`HPC-W05-LIFE-064`); LIFE-030/069 need no packaged proof at this SHA beyond this justification.

## POST_GREEN_REVIEW

Duplicate path: canonical WebView output path already guarded; fallback now mirrors it — no third output path exists (detached terminal shares builders). Alternate entry points: bridge dispatch, direct API, shell wrapper — all guarded/compatible. Silent fallbacks: none introduced. Stale state: generations bumped on close + every swap on both paths. Cleanup: close clears queues + failure flag; shutdown reversed/idempotent/swallowing (tested). Dead branches: none added. Provider/site branching: none. Success-claiming errors: none (all drops documented). Packaged divergence: none.

## Diff review

`git diff --check`: clean (CRLF warnings pre-existing only). W21-owned diff: `src/hpc_gui/wx_terminal_webview.py` (close release block +18/−5; remainder of the file's diff is pre-existing stacked W19/W20 work), `src/hpc_gui/wx_terminal.py` (fallback guards; `set_ssh(None)` neutralization block in the same hunk is pre-existing W19 work, preserved), new `tests/test_w21_terminal_lifecycle.py`, new `build/audit/w21-external-matrix.txt`, `build/audit/w21-gui-pytest.txt`, this report. All other tracked/untracked changes are pre-existing stacked work preserved byte-for-byte. No secrets, no generated/binary noise, no weakened tests.

## Resume state

Completed and verified: narrow baseline 78/78; DEF-W21-001/FIX-A + DEF-W21-002/FIX-B and DEF-W21-AUDIT-001 correction with before-evidence + sensitivity; 8/8 focused W21 tests; 170/170 impacted suites; GUI + refreshed EXTERNAL evidence current; secrets scans 0; diff reviewed.
In progress: none (awaiting fresh-context audit).
Open P0/P1: none. Open P2/P3: OBS-W21-003 (P3, new, routed to W22), OBS-W20-003/004 (P3, carried, W21 narrows 003 to the key_input return nuance).
Pending tests/evidence: none for W21 scope.
Last exact commands: `.venv\Scripts\python.exe -m pytest tests/test_w21_terminal_lifecycle.py -q` 8 passed; `.venv\Scripts\python.exe -m pytest tests/test_w19_connection_lifecycle.py tests/test_w20_terminal_io.py tests/test_wx_terminal_webview.py -q` 53 passed; `.venv\Scripts\python.exe C:\Users\mskomek\AppData\Local\Temp\opencode\w21_ext.py --help` harness run exit 0 with E1–E7 PASS and healthy-before/after.
Next actions: fresh-context audit (`W21_AUDIT_REPORT.md`); never start W22.
Evidence identities: `build/audit/w21-gui-pytest.txt`, `build/audit/w21-external-matrix.txt`, tested SHA `0f8902a0` + working-tree W21 files above.

```text
FIX-A: shutdown-safe native release (skip explicit webview.Destroy while IsBeingDeleted; Stop + detach)
DEF: DEF-W21-001 (P1, LIFE-022/068, TODO-LIFECYCLE-NATIVE-002)
Root cause: unconditional native Destroy raced WebView2 teardown mid-teardown -> shutdown AV
Before EV: EV-W21-001 w21_probeB.py (Destroy called while being-deleted: YES)
After EV: 8/8 new tests green; webview 29/29; EXTERNAL panel section RC 0
Regression test: test_w21_close_skips_native_destroy_while_being_deleted, test_w21_double_close_and_destroy_is_idempotent
Sensitivity proof: guard reverted -> fails with exact expected reason; restored -> green

FIX-B: fallback output lifecycle guard (closed+generation+IsBeingDeleted; subscribe-time pinning; mint on close/swap)
DEF: DEF-W21-002 (P1, LIFE-014/015/022/066/068)
Root cause: fallback output path had no closed/generation guard -> post-close writes + stale-session renders
Before EV: EV-W21-001 w21_probeC.py (render after close mutated control: YES)
After EV: 8/8 new tests green; EXTERNAL E-stale-drop/E6b/E7 PASS
Regression test: test_w21_fallback_render_after_close_is_dropped, test_w21_fallback_stale_generation_dropped_after_reconnect
Sensitivity proof: guards removed -> both fail with exact expected reasons; restored -> green

Additional fixes: none (two genuine fixes closed; no open in-scope P1 remains)
Post-green review: done, 1 new P3 observation routed to W22, 2 carried P3 unchanged
New/modified tests: tests/test_w21_terminal_lifecycle.py (8 new); zero existing tests modified
Skipped/xfail changes: none
Package evidence: N/A (justified — zero build-input/asset/frozen-byte change; W22 LIFE-064 owns exact-artifact acceptance; stale dist refused)
External evidence: refreshed; build/audit/w21-external-matrix.txt records `W21-EXTERNAL DONE` with E1–E7 PASS and exit 0
Open P0/P1: none
Open P2/P3: OBS-W21-003 (P3 new), OBS-W20-003/004 (P3 carried)
Two-fix gate: PASS
Wave decision: READY_FOR_AUDIT
```
