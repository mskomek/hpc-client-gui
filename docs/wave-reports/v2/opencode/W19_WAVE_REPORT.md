# W19 — Connection/session lifecycle and profile switching — Wave Report

```text
Wave: W19
Canonical report path: docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui (main)
Branch: develop
Baseline SHA: 0f8902a023bac76071527232c2287af96478ed2b
Current HEAD: 0f8902a023bac76071527232c2287af96478ed2b
Tested implementation SHA: 0f8902a023bac76071527232c2287af96478ed2b + working-tree W19 changes listed below (no commit created; 1-line fix by this session, remainder pre-existing stacked work preserved byte-for-byte)
Plugin/external repo SHA(s): f0abb7e7037e66ab451d463c699fecf4e00c89eb (develop; verified read-only, no plugin changes)
First started: 2026-09-20
Last updated: 2026-09-20
Session status: READY FOR FINAL REVIEW
Wave decision: READY_FOR_AUDIT
```

Predecessor gate: W18 closed PASS (W18_AUDIT_REPORT.md, Decision PASS,
2026-09-20; OBS-W18-003/OBS-W18-004 routed into W19 scope as discovery
inputs). Dependencies: W18 — satisfied. Required evidence: GUI, EXTERNAL.
Execution model: `opencode-go/muse-spark-1.3-contributor` (infra retry
attempt 2; attempt 1 failed before any repo change with a provider
`tool_choice` error — no debug cycle consumed, no state carried).

## Baseline capture

```text
git branch --show-current: develop
git rev-parse HEAD: 0f8902a023bac76071527232c2287af96478ed2b
git rev-parse origin/develop: 0f8902a023bac76071527232c2287af96478ed2b (equal; no divergence)
git diff --check: clean (only pre-existing CRLF warnings on unrelated files)
git status: dirty — large pre-existing working-tree stack preserved byte-for-byte
  (CONTRIBUTING.md, README.md, W01 artefacts/reports, scripts, core/paths.py,
   i18n en/tr.json, plugins loader/validator, profile/connection/files/slurm
   services, wx_connection/wx_settings_view/wx_shell/wx_terminal*, assorted
   tests incl. W03/W04/W08/W09/W11-W15 suites, plus untracked audit artefacts,
   helper scripts, and the W19 implementation+test stack listed under Diff
   review). No reset/clean/destructive git; nothing pushed.
Plugin: D:/Projeler/hpc-client-gui-plugins develop f0abb7e7037e66ab451d463c699fecf4e00c89eb
```

`waves/pending/` contains exactly one copy of each W01–W61 file (verified by
listing; W19.md is the single canonical copy). `waves/bak/` never read.
No `.env`/credentials/tokens/keys exposed; the lab fixture credential is
public-by-design per owning commit `2c1c7ce9` (hpctest, loopback-only) and
reached this session's shell only via `HPC_LAB_PASSWORD` env at runtime —
never written to files/logs/evidence (both evidence logs scanned: zero
matches for the fixture username/password).

## Authority reads (all completed before implementation)

1. `opencode/protocol/CORE_EXECUTION_RULES.md` — read.
2. `waves/pending/W19.md` — read (27 source-derived IDs + 7 TODO-detail IDs, evidence GUI+EXTERNAL).
3. Owned registry rows `HPC-W05-CONN-001..020`, `HPC-W05-RECON-001..007` — read (all MANDATORY).
4. `TODO_OWNERSHIP_MAP.md` W19 rows (`SHELL-NAV-001/002`, `SHELL-TABS-001/002`, `TODO-006`, `W02-TODO-002`, `TODO-007`) — read (all ACTIVE).
5. `opencode/sources/WAVE_V2_FINAL_05.md` Workstreams 0.3, 0.4, A, B, G — read, exact semantics preserved.
6. Live code truth rediscovered (see Discovery). 7. W18 close truth as predecessor background only.

Owned requirements trace:

```text
CONN-001 truthful shell states -> ConnectionController states (DISCONNECTED/CONNECTING/AUTHENTICATING/CONNECTED/FAILED/DISCONNECTING) + panel Cancel/Disconnect enablement + status indicator (GUI proof)
CONN-002 repeated Connect supersedes -> connect_selected closes previous session first + attempt tagging; generation differs (unit + GUI proof)
CONN-003 Cancel while connecting -> Cancel control + cancel_token + late-worker drop to DISCONNECTED (GUI proof)
CONN-004 disconnect invalidates remote-only -> Disconnect control + close_session + on_disconnected + gated send path (GUI proof)
CONN-005 transport loss updates UI -> _controller_disconnect_cb live-probe + FAILED + invalidation hook (GUI + EXTERNAL E5 proof)
CONN-006 reconnect fresh identity -> finish() mints session_generation (unit + EXTERNAL E3 proof)
CONN-007 profile switch no stale reuse -> supersede teardown + per-profile navigation stores/filters (EXTERNAL E4 + unit proof)
CONN-008 indicator agrees with truth -> status repaint on every transition incl. failure/loss paths (GUI proof)
CONN-009 recoverable failure never kills app -> failure re-arms panel, app alive assertion (GUI proof)
CONN-010..013 terminal/files/jobs surfaces -> embedded notebook pages APP-CONNECT/NAV-* (GUI proof)
CONN-014 rebinding via canonical session model -> _connection_callbacks on_connected/on_disconnected rebinding for all domains (GUI proof)
CONN-015..019 trace lifecycle (session object/reader/write/stop-signal/widget lifetime) -> ownership mapped in connect_profile/controller/panel/shell; dialogs marshalled (GUI proof)
CONN-020 no ambiguous dead-session input -> disconnect clears attached ssh + neutralizes _send_input; key_input after disconnect sends nothing (GUI proof)
RECON-001 graceful disconnect -> Disconnect control + begin/finish_disconnect (GUI + EXTERNAL E2 proof)
RECON-002 remote close -> abrupt transport death detected on next op + FAILED (EXTERNAL E5 proof)
RECON-003 network loss -> same path as RECON-002 (EXTERNAL E5 proof)
RECON-004 reconnect same profile -> fresh generation (EXTERNAL E3 proof)
RECON-005 reconnect different profile -> supersede + new generation (EXTERNAL E4 proof)
RECON-006 old reader callback after new session -> stale-probe drop (unit + EXTERNAL E6 proof)
RECON-007 generation/session identity -> _session_generation_counter on every finish (unit + EXTERNAL proof)
SHELL-NAV-001 canonical tab order -> CANONICAL_TAB_ORDER frozen + inventory (GUI proof)
SHELL-NAV-002 NAV-* to embedded page -> _dispatch selects existing page, zero new top-level windows (GUI proof)
SHELL-TABS-001/002 tabs reachable + keyboard/focus -> SetSelection sweep + NAV-TERMINAL focus-inside-page assertion (GUI proof)
TODO-006 stale callbacks/services invalidated -> disconnect_cb probe + terminal output-subscriber detach (GUI + EXTERNAL E6 proof)
W02-TODO-002 profile switch invalidates stores -> navigation_store_for_profile per-profile + filters follow profile (unit proof)
TODO-007 disconnect gates remote actions -> Disconnect control + dead-session send gating, no false success (GUI proof)
```

## Narrow baseline (pre-edit)

```text
Command: python -m pytest tests/test_w19_connection_lifecycle.py -q -p no:randomly
Result: 19 passed, 1 failed (test_host_key_prompt_from_worker_thread_uses_gui_thread)
The 19 green tests proved the stacked working-tree implementation already
satisfied the bulk of W19; the single failure isolated the one remaining
in-scope defect (see DEF-W19-002). No edits had been made by this session
at that point.
```

## Discovery Pass + WAVE_FINDINGS

Live anchors rediscovered: `src/hpc_gui/services/connection_controller.py`
(state machine, generation counter, `close_session`), `src/hpc_gui/wx_connection.py`
(model, `connect_profile`, `_controller_disconnect_cb`,
`_invoke_on_gui_thread`, Cancel/Disconnect controls, host-key/MFA dialogs),
`src/hpc_gui/wx_shell.py` (canonical tab order, `_dispatch`,
`_connection_callbacks`, `_remote_files_callbacks`),
`src/hpc_gui/services/remote_navigation_store.py`
(`navigation_store_for_profile`), `src/hpc_gui/wx_terminal.py`
(output-subscriber detach), `tests/test_w19_connection_lifecycle.py`
(untracked, 20 tests, pre-existing working-tree state).

```text
Finding ID | Severity | Surface | Evidence | Root cause | Impact | Countable fix? | Status
DEF-W19-001 | P2 | mid-connect Cancel control | OBS-W18-003 input + live panel source (cancel_button, cancel_connect, attempt tag) + GUI cancel test green at baseline | already implemented in stacked tree | none remaining | NO (already valid, regression-locked) | VERIFIED-OK
DEF-W19-002 | P2 | host-key dialog thread rendezvous | OBS-W18-004 input + baseline GUI failure (ShowModal ran on worker ident, assertion ident mismatch) | host_key_dialog called _ask() inline while MFA path rendezvoused via _invoke_on_gui_thread | trust prompt created off the GUI thread | YES -> FIX-W19-001 | CLOSED
DEF-W19-003 | P2 | stale transport-loss callback | live _controller_disconnect_cb probe logic + stale-drop tests green at baseline | already implemented in stacked tree | none remaining | NO (already valid, regression-locked) | VERIFIED-OK
DEF-W19-004 | P2 | Disconnect control / dead-session reuse | live disconnect_button + send-path gating + GUI tests green at baseline | already implemented in stacked tree | none remaining | NO (already valid, regression-locked) | VERIFIED-OK
DEF-W19-005 | P3 | NAV detached vs embedded page | live _dispatch + embedded notebook + no-new-window test green at baseline | already implemented in stacked tree | none remaining | NO (already valid, regression-locked) | VERIFIED-OK
VERIFIED-OK | — | generation identity / reconnect / profile-switch stores / tab order / focus | unit+GUI+EXTERNAL proofs | — | sound, no change | NO | VERIFIED
```

Per HPC-GOV-017 no defect was manufactured: four of five discovery defects
were verified already-valid with regression locks; exactly one genuine
remaining defect (DEF-W19-002) was fixed.

## Second-Defect Search (12 dimensions)

1. negative paths — checked: wrong-pw (EXTERNAL E7 AuthFailure), missing-key/no-credential (W18-owned, untouched), changed-key (W18), cancel/reject (GUI), strict-unknown (W18) / defect FIX-W19-001.
2. lifecycle — checked: connect/fail/cancel/disconnect/reconnect/switch (GUI 20 + EXTERNAL E1-E7).
3. stale state — checked: supersede teardown, stale-cb drop, output-subscriber detach, generation monotonicity.
4. identity — checked: generation differs every finish; per-profile navigation stores; profile_name rebinding.
5. concurrency/race — checked: attempt tagging (late worker drop), single worker + button enablement, CallAfter marshal for both worker callbacks; sensitivity revert proves the host-key path is the load-bearing one.
6. boundary values — checked: close_session best-effort on odd inputs (unit); empty/None transports dropped without corrupting CONNECTING.
7. capability absence — checked: no live session + no wx app fall back to synchronous/inline paths (headless external run proves service path).
8. persistence — checked: external run uses host-key decision "once" so no user known_hosts is touched; accept-persistence stays W18-owned.
9. packaging — NOT APPLICABLE: required evidence is GUI+EXTERNAL only; no build/package logic, dependencies, or resources touched.
10. error visibility — checked: failures FAILED with truthful status + dialog; cancel shows cancelled status with no popup; no error claims success.
11. secondary entry points — checked: button/double-click/context-menu share `connect_selected`; save&connect shares the same path (source trace, unchanged).
12. adjacent boundary — checked: remaining ShowModal sites (master-password, edit-auth verify, profile dialog) all run on GUI-thread button handlers, not worker threads — correctly out of scope for the rendezvous fix; Qt parity untouched.

## Fixes

### FIX-W19-001 (DEF-W19-002): host-key trust prompt marshalled to the GUI thread

Root cause: the SSH worker thread invokes both model callbacks
(`host_key_dialog`, `mfa_dialog`). The MFA closure rendezvoused through
`_invoke_on_gui_thread` (OBS-W18-004 fix), but the host-key closure called
`_ask()` inline, so `wx.MessageDialog` was constructed and `ShowModal`-ed
on the worker thread. Fix routes the host-key question through the same
rendezvous; headless/service callers still run inline (no app ->
`call()`), so the controller/model unit path is unchanged.

```text
Fix ID: FIX-W19-001
Defect ID: DEF-W19-002
Severity: P2
Independent root cause: yes (host-key dialog dispatch; MFA path and all other dialog sites untouched — proven by the sensitivity revert where only the host-key test failed)
Before behavior: unknown-host prompt decided on the SSH worker thread (FakeDialog.ShowModal observed worker ident != main ident)
Before evidence ID: EV-W19-001 (narrow-baseline run: 19 passed, 1 failed — test_host_key_prompt_from_worker_thread_uses_gui_thread)
Files changed: src/hpc_gui/wx_connection.py (1 line: `return _ask()` -> `return _invoke_on_gui_thread(_ask)`)
Behavioral contract changed: worker-thread host-key decisions are now created, shown, and destroyed on the wx GUI thread; decision values (save/once/reject) unchanged
Regression test(s): tests/test_w19_connection_lifecycle.py (20 tests; pre-existing file, preserved, not authored by this session)
Sensitivity proof: fault-injection revert of the 1 line -> exactly test_host_key_prompt_from_worker_thread_uses_gui_thread fails (sibling marshal test still passes); restore -> 20/20 green
Negative test: reject path (decision "reject"), cancel-while-connecting, wrong-password, transport-loss cases
Narrow-suite result: 20 passed (new-stack file)
Broader-suite result: w18 14 passed; wx_connection_profiles + profile-service 41 passed; remote_navigation_store 11 passed (all solo-sequenced)
Runtime/manual result: GUI pytest log build/audit/w19-gui-pytest.txt (exit 0)
Package result (if applicable): NOT APPLICABLE (no packaging change; required classes GUI+EXTERNAL only)
External result (if applicable): build/audit/w19-external-matrix.txt E1-E7 7/7 PASS + cleanup PASS, hpclab healthy before+after
Residual risk: a worker blocked in _invoke_on_gui_thread raises RuntimeError (visible failure) if the app disappears mid-prompt — by design, never a hang
```

## Tests

Regression file `tests/test_w19_connection_lifecycle.py` — 20 tests, each
with REQ/DEF/CON/NEG purpose IDs, behavioral assertions on live
controller/model/panel/shell objects, mock boundary at transport
(FakeSsh/fake connect_fn) and dialog chrome only; no skips/xfails/weakening
(the sole `skip` token in the file is `pytest.importorskip("wx")`, the
legitimate platform guard):

```text
Exact counts (final, solo-sequenced):
- W19 file: 20 passed, 0 failed, 0 skipped, 0 xfailed, exit 0 (build/audit/w19-gui-pytest.txt)
- W18 regression (adjacent, untouched): 14 passed, exit 0
- wx_connection_profiles + connection_profile_service: 41 passed, exit 0
- remote_navigation_store (profile-switch stores): 11 passed, exit 0
- EXTERNAL matrix: E1-E7 7/7 PASS + cleanup PASS (build/audit/w19-external-matrix.txt)
Post-green review: one-line fix only touches host-key dialog dispatch; MFA path shares the helper but its behavior is unchanged (its GUI test passes with and without the fix); no duplicate path (both worker callbacks now funnel through _invoke_on_gui_thread); alternate connect entries share connect_selected; no silent fallback added ("once"/"reject" semantics unchanged); no secrets in diff; no dead branch; no provider hardcoding; no success-claiming errors; no packaging divergence.
POST_GREEN_REVIEW: complete, no new defect kept open.
```

Test-quality checklist: counted fix has regression test YES; sensitivity
proven YES (fault injection, exactly-1-fails); negative paths YES;
lifecycle/cancel YES; behavioral assertions YES; mocks at transport/chrome
boundary only YES; no new skips/xfails YES; isolated fixtures YES;
deterministic cleanup YES; package/external honestly classified YES;
impacted slices pass YES; revert would fail YES.

## Evidence

- GUI (required): real wx App/panel/controller/shell event runs —
  `build/audit/w19-gui-pytest.txt` (20/20, exit 0): supersede, cancel-safe,
  stale-drop, FAILED-invalidation, fresh generation, best-effort teardown,
  slow-connect Cancel click (no resurrection, no popup, app alive),
  recoverable-failure re-arm, Disconnect gating, shell rebinding +
  dead-input neutralization, stale-output detach, GUI-thread marshal both
  dialogs, transport-loss indicator, canonical tab order, NAV routing with
  zero new windows, keyboard+focus restoration, cross-domain rebind,
  profile-switch stores/filters.
- EXTERNAL (required): real authorized lab, loopback container `hpclab`
  (healthy before AND after; image hpc-client-gui-lab; remote environment
  class: local containerized single-node Slurm; provider direct SSH;
  password auth via env-only public fixture; timestamps +03:00 2026-09-20) —
  `build/audit/w19-external-matrix.txt`: E1 connect+echo PASS (exit=0),
  E2 graceful disconnect PASS, E3 same-profile reconnect fresh generation
  PASS (gen 1 -> 2), E4 profile-switch supersede PASS (gen 2 -> 3), E5
  abrupt transport loss visible failure PASS (op raised SSHException,
  controller FAILED, session cleared), E6 stale callback dropped PASS,
  E7 wrong-password visible failure PASS (AuthFailure, controller FAILED);
  cleanup PASS (sessions closed; lab unmodified — auth/echo attempts only;
  host-key decision "once" so no known_hosts write). Secret scan of both
  logs: clean.
- PACKAGE: N/A — required classes for W19 are GUI+EXTERNAL; no build,
  dependency, resource, or runtime-config change was made.

## Diff review

```text
git diff --check: clean (unrelated CRLF warnings only, pre-existing)
W19-owned changes (this session + preserved pre-existing stack):
  M src/hpc_gui/wx_connection.py (THIS SESSION: 1 line — host-key dialog rendezvous; remainder of the file's working-tree hunks are pre-existing stacked work preserved untouched)
  ?? tests/test_w19_connection_lifecycle.py (pre-existing working-tree stack, preserved; not authored by this session; no weakening)
  ?? build/audit/w19-gui-pytest.txt, build/audit/w19-external-matrix.txt (evidence, this session)
  ?? docs/wave-reports/v2/opencode/ (this report path; directory untracked pre-existing)
No secrets, no generated/binary noise, no weakened tests, no unrelated-file edits by this session (all other dirty files byte-identical to session start; verified via pre/post status comparison).
```

## Resume state

```text
Completed and verified:
- Authority reads (CORE rules, W19 pending, 27 registry rows, 7 TODO rows, Workstreams 0.3/0.4/A/B/G, live code, W18 background)
- Narrow baseline 19/20 isolating exactly one remaining defect
- FIX-W19-001 with sensitivity proof (revert -> exactly-1-fails; restore -> 20/20)
- 12-dimension second-defect search
- GUI + EXTERNAL evidence current, secret-clean
- Report current (this file)
In progress: none (awaiting fresh-context audit)
Open P0/P1: none. Open P2/P3: none in-scope (all five discovery items closed or verified-already-valid)
Pending tests/evidence: none for W19
Last exact commands run:
- python -m pytest tests/test_w19_connection_lifecycle.py -v -p no:randomly (20 passed, exit 0)
- python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly (14 passed, exit 0)
- python -m pytest tests/test_wx_connection_profiles.py tests/test_connection_profile_service.py -q -p no:randomly (41 passed, exit 0)
- python -m pytest tests/test_remote_navigation_store.py -q -p no:randomly (11 passed, exit 0)
- EXTERNAL matrix via HPC_LAB_PASSWORD env (E1-E7 7/7 + cleanup PASS, log saved)
Next actions:
1. Fresh-context audit of W19 (separate session/model)
2. On PASS, W20 may be planned only after dependency revalidation (do NOT auto-start)
Evidence/artifact identities:
- main 0f8902a023bac76071527232c2287af96478ed2b (develop == origin/develop)
- plugin f0abb7e7037e66ab451d463c699fecf4e00c89eb
- build/audit/w19-gui-pytest.txt, build/audit/w19-external-matrix.txt
```

## Final adversarial self-audit

1. FIX: host-key dialog GUI-thread rendezvous (1 line); four sibling discovery defects verified already-valid, not absorbed as fixes.
2. Independent: host-key dispatch vs MFA dispatch — different closures; revert fails exactly one test while the MFA marshal test stays green.
3. Before evidence: narrow-baseline 19/20 with the worker-ident assertion failure (EV-W19-001).
4. Revert test: fault injection fails exactly the 1 proving test; restore greens 20/20.
5. Negative paths: cancel, reject, wrong-pw, missing-session callback, transport loss, stale callback.
6. Bypass paths: none — both worker-thread callbacks funnel through `_invoke_on_gui_thread`; all connects funnel through `connect_selected`; remaining ShowModal sites are GUI-thread handlers.
7. Mocks: transport + dialog chrome only; controller/model/panel/shell/session-state real. Do NOT prove: native dialog rendering, real-network auth (covered by EXTERNAL instead).
8. Manual/runtime: real wx event runs + real lab matrix (no manual checklist needed beyond).
9. Uncertainties: none in-scope; combined-process wx test pollution noted in W18 is pre-existing and all W19-adjacent slices were run solo-sequenced.
10. Cosmetic/duplicate/test-only? No — the fix changes thread-affinity behavior of a security decision with failing-before proof.

```text
FIX: FIX-W19-001
DEF: DEF-W19-002 (discovery input OBS-W18-004)
Root cause: host_key_dialog invoked _ask() inline on the SSH worker thread while the sibling MFA path rendezvoused
Before EV: EV-W19-001 (19 passed, 1 failed narrow baseline)
After EV: build/audit/w19-gui-pytest.txt (20 passed) + build/audit/w19-external-matrix.txt (E1-E7 PASS)
Regression test: tests/test_w19_connection_lifecycle.py (host-key worker-thread GUI test + 19 locks)
Sensitivity proof: fault-injection revert -> exactly 1 fails; restore -> green
Additional fixes: none (four sibling discoveries verified already-valid per HPC-GOV-017 zero-defect rule)
Post-green review: complete (see checklist above)
New/modified tests: none authored by this session (pre-existing 20-test stack preserved, unweakened)
Skipped/xfail changes: none
Package evidence: N/A (justified above)
External evidence: build/audit/w19-external-matrix.txt (E1-E7 PASS, cleanup PASS, secret scan clean)
Open P0/P1: none
Open P2/P3: none in-scope
Wave decision: GO (pending fresh-context audit) / READY_FOR_AUDIT
```
