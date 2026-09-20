# W18 — Authentication and host-key security — Wave Report

```text
Wave: W18
Canonical report path: docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui (main)
Branch: develop
Baseline SHA: 0f8902a023bac76071527232c2287af96478ed2b
Current HEAD: 0f8902a023bac76071527232c2287af96478ed2b
Tested implementation SHA: 0f8902a023bac76071527232c2287af96478ed2b + working-tree W18 modifications listed below (no commit created; no product change after evidence runs)
Plugin/external repo SHA(s): f0abb7e7037e66ab451d463c699fecf4e00c89eb (develop; verified read-only, no plugin changes)
First started: 2026-09-20
Last updated: 2026-09-20
Session status: READY FOR FINAL REVIEW
Wave decision: READY_FOR_AUDIT
```

Predecessor gate: W17 closed PASS (W17_AUDIT_REPORT.md cycle 3, Decision PASS,
2026-09-20; no REOPEN/BLOCKED). Dependencies: W17 — satisfied.
Required evidence: GUI, EXTERNAL. Execution model:
`opencode-go/muse-spark-1.3-contributor`.

## Baseline capture

```text
git branch --show-current: develop
git rev-parse HEAD: 0f8902a023bac76071527232c2287af96478ed2b
git rev-parse origin/develop: 0f8902a023bac76071527232c2287af96478ed2b (equal; no divergence)
git diff --check: clean (only pre-existing CRLF warnings on unrelated files)
git status: dirty — pre-existing unrelated working-tree changes preserved byte-for-byte
  (CONTRIBUTING.md, README.md, W01 artefacts/reports, scripts, core/paths.py,
   i18n en/tr.json, plugins loader/validator, profile/connection/files/slurm
   services, wx_connection/wx_settings_view/wx_shell, assorted tests incl.
   W03/W04/W08/W09/W11-W15 suites, plus untracked W15/W16/W17 audit artefacts
   and helper scripts). No reset/clean/destructive git; nothing pushed.
Plugin: D:/Projeler/hpc-client-gui-plugins develop f0abb7e7037e66ab451d463c699fecf4e00c89eb
```

`waves/pending/` contains exactly one copy of each W01–W61 file (verified by
listing; W18.md is the single canonical copy). `waves/bak/` never read.
No `.env`/credentials/tokens/keys exposed; fixture passwords only via
`HPC_LAB_PASSWORD` env at runtime, never written to files/logs/evidence
(evidence log scanned: zero matches for the fixture username/password).

## Authority reads (all completed before implementation)

1. `opencode/protocol/CORE_EXECUTION_RULES.md` — read.
2. `waves/pending/W18.md` — read (16 owned IDs, 0 TODOs, evidence GUI+EXTERNAL).
3. Owned registry rows `HPC-W05-AUTH-001..016` — read (all MANDATORY).
4. `REQUIREMENT_WAVE_INDEX.md` + `TODO_OWNERSHIP_MAP.md` — 0 TODO rows for W18.
5. `opencode/sources/WAVE_V2_FINAL_05.md` Workstream 0.1 + 0.2 — read, exact semantics preserved.
6. Live code truth rediscovered (see Discovery). 7. W17 close truth as predecessor background only.

Owned requirements trace:

```text
AUTH-001 password path -> ssh_info_from_profile password resolution + _ConnectionAuthStrategy/_PasswordSource + dialog TE_PASSWORD + resolve_password_for_connect
AUTH-002 private-key path -> key_path/ssh_key mapping + load_private_key_with_certificate + key-file error mapping (FIX-A)
AUTH-003 agent/keyring/master-backed path -> allow_agent/look_for_keys always-on discovery + decrypt/resolve master flows (verified, EXTERNAL E8)
AUTH-004 provider prerequisite -> keyboard-interactive gating on provider auth_methods (contract test)
AUTH-005 invalid credentials fail visibly -> mapped error_authentication (FIX-A) + GUI/EXTERNAL proof
AUTH-006 no secret in logs/evidence -> repr=False, run() redaction, done() redaction, probe 0 leaks, evidence scan clean
AUTH-007 missing key actionable -> mapped error_key_file + technical detail (FIX-A) + GUI/EXTERNAL proof
AUTH-008 cancel safe state -> dialog cancel/reject FAILED-safe + master_cancelled no-dialog + visible cancel status (FIX-A) + GUI proof
AUTH-009 unsupported method not offered -> no method selector; GSSAPI/Kerberos absent; kbd-interactive gated (contract test)
AUTH-010 first contact/unknown host -> _KnownHostsPolicy + prompt save/once/reject (GUI proof)
AUTH-011 accept-new/confirmation semantics -> host_key_policy accept-new|strict + dialog mapping (GUI + EXTERNAL E1/E5/E6)
AUTH-012 known host success -> known_hosts load + reconnect without prompt (EXTERNAL E3)
AUTH-013 host-key mismatch hard fail -> BadHostKeyException -> HostKeyChangedError, mapped message (FIX-A) + GUI/EXTERNAL E4 proof
AUTH-014 cancel/reject -> reject/once semantics + FAILED-safe (GUI proof)
AUTH-015 reconnect after accept -> persisted known_hosts reuse (EXTERNAL E3 + mock probe F)
AUTH-016 prompt identifies decision, no secrets -> host/type/fingerprint/role shown, key_type now real (FIX-B) + GUI proof
W11 transport internals used as background only; no W11 scope re-owned.
```

## Narrow baseline (pre-edit)

```text
Command: python -m pytest tests/test_ssh_credential_flow.py tests/test_optional_ssh_credentials.py tests/test_connection_controller.py -q
Result: 34 passed, 9 subtests passed
Command (wx profile slice): 87 passed (test_wx_connection*.py + hardening + profiles)
```

## Discovery Pass + WAVE_FINDINGS

Live anchors rediscovered: `src/hpc_gui/ssh/client.py` (strategy, policy,
error types), `src/hpc_gui/wx_connection.py` (panel/model/dialogs/done),
`src/hpc_gui/wx_connection_dialog.py` (password+key fields, no method
selector), `src/hpc_gui/services/connection_controller.py` (state machine,
HostKeyRequest), `src/hpc_gui/services/connection_profile_service.py`
(resolve/decrypt), `src/hpc_gui/ssh/jump.py` (jump key/agent-only),
`src/hpc_gui/core/ui_errors.py` (shared classifier), Qt
`login_widget._on_connect_failed` (parity reference), `tests/support/mock_ssh_server.py`.

Runtime probes (mock server, fixture credential): wrong-password ->
`AuthenticationException: Authentication failed.` (visible, raw); missing key
-> raw `FileNotFoundError`; encrypted key w/o passphrase -> visible failure;
same-port key rotation -> `HostKeyChangedError` (hard fail OK); strict-unknown
-> reject OK; no-credential -> `NoAuthenticationCredentialError` OK; log
capture 0 secret leaks; different ports correctly treated as distinct
`[host]:port` identities (paramiko 3.5.1, OpenSSH-compatible).

```text
Finding ID | Severity | Surface | Evidence | Root cause | Impact | Countable fix? | Status
DEF-W18-001 | P1 | wx connect failure/cancel feedback | probe raw outputs + Qt-vs-wx source trace (login_widget maps, wx done() showed str(error)) | wx done() bypassed shared classifier + dedicated host-key messages; cancel status raced controller repaint | users got untranslated raw errors; cancel looked identical to failure | YES -> FIX-W18-001 | CLOSED
DEF-W18-002 | P2 | host-key trust prompt | source trace: dialog formatted key_type="SSH" literally; HostKeyRequest lacked the field though transport knew it | key-type signal dropped between _KnownHostsPolicy callback and prompt | weaker security decision (algorithm change invisible) | YES -> FIX-W18-002 | CLOSED
OBS-W18-003 | P3 | mid-connect Cancel button | panel disables buttons while connecting, no Cancel control | W19 CONN-003 owns "Cancel while connecting" | none in W18 scope | NO (routed W19) | ROUTED
OBS-W18-004 | P3 | host-key/MFA modal shown from SSH worker thread | worker Thread -> decide/answer -> ShowModal without GUI-thread rendezvous | threading Workstream H lifecycle owner | none fixed here (no crash observed) | NO (routed W19) | ROUTED
VERIFIED-OK | — | rotation/strict/reject/reconnect/no-leak/method-offer | probes + E-matrix | — | sound, no change | NO | VERIFIED
```

## Second-Defect Search (12 dimensions)

1. negative paths — checked: wrong pw, missing key, encrypted key, no credential, strict-unknown, DNS/refused/timeout classifier (shared, reused) / defects FIX-W18-001.
2. lifecycle — checked: connect/fail/reconnect-after-accept/cancel-safe (GUI + E3); mid-connect cancel -> W19.
3. stale state — checked: reconnect supersede teardown pre-existing (W17 PROF-013), untouched.
4. identity — checked: `[host]:port` scoping verified; wrong-profile path W17-owned.
5. concurrency/race — checked: single worker + disabled buttons; cancel-status race FIXED (FIX-W18-001); off-thread modal -> routed W19.
6. boundary values — checked: empty password (key-auth path OK), unicode/fingerprint formats pass through; nothing actionable found.
7. capability absence — checked: agent-absent falls through cleanly (E8); no saved secret -> actionable `saved_password_unavailable` (kept).
8. persistence — checked: known_hosts save/once (no save)/reject; 0600 on posix; reconnect reuse E3.
9. packaging — NOT APPLICABLE: required evidence is GUI+EXTERNAL only; no build/package logic, dependencies, or resources touched.
10. error visibility — checked: FIX-W18-001; no error claims success.
11. secondary entry points — checked: button/double-click/context-menu share `connect_selected`; dialog save&connect shares path.
12. adjacent boundary — checked: Qt/wx parity restored via shared classifier (no duplication of business logic); transport error types preserved with hostname.

## Fixes

### FIX-W18-001 (DEF-W18-001): truthful wx failure/cancel feedback

Root cause: the wx panel `done()` rendered `str(error)` directly while Qt
routed the same failures through dedicated host-key messages and the shared
`describe_connection_error` classifier; additionally the cancel-status write
lost a race against the already-queued controller-fail repaint, so
cancellation was indistinguishable from failure. Fix reuses (not duplicates)
the framework-neutral classifier: new `describe_wx_connect_failure()`
(host-key dedicated messages first, saved-secret/master states kept,
classifier fallback, secret redaction) used by `done()`; cancel status
deferred with `wx.CallAfter` so the author's intended "Authentication
cancelled" survives the repaint.

```text
Fix ID: FIX-W18-001
Defect ID: DEF-W18-001
Severity: P1
Independent root cause: yes (failure-message routing + cancel repaint ordering; distinct from prompt-data plumbing of FIX-W18-002)
Before behavior: raw "Authentication failed." / raw FileNotFoundError / raw "Server ... not found in known_hosts" / "Connection failed" on cancel
Before evidence ID: EV-W18-001 (probe console outputs pre-fix; Qt-vs-wx source trace)
Files changed: src/hpc_gui/wx_connection.py (helper + done + cancel deferral)
Behavioral contract changed: wx failure dialogs now show translated actionable guidance identical in kind to Qt; cancel shows "Authentication cancelled" with no error popup
Regression test(s): tests/test_w18_auth_hostkey.py (7 mapping/redaction unit + 3 GUI failure/cancel tests)
Sensitivity proof: fault-injection revert of mapped branches -> 6 fix-proving tests fail for expected reasons; restore -> green
Negative test: wrong-pw / missing-key / changed-key / no-credential cases
Narrow-suite result: 14 passed (new file)
Broader-suite result: 68 + 79 passed (wx/ssh/controller/profile slices, solo-sequenced); W11 solo 14; W15 solo 11
Runtime/manual result: GUI pytest log build/audit/w18-gui-pytest.txt (exit 0)
Package result (if applicable): NOT APPLICABLE (no packaging change; required classes GUI+EXTERNAL only)
External result (if applicable): build/audit/w18-external-matrix.txt E1-E8 8/8 PASS, hpclab healthy before+after
Residual risk: unknown future error classes fall back to classifier + technical detail (by design, truthful)
```

### FIX-W18-002 (DEF-W18-002): real key type reaches the trust prompt

Root cause: `HostKeyRequest` had no `key_type` field, so `ssh_info_from_profile`
dropped `key.get_name()` and the dialog hardcoded `Type: SSH`. Fix adds
defaulted `key_type` to the frozen request, forwards it in the decision
closure, and renders it via `format_host_key_prompt()` (fallback "SSH" only
when absent). Transport (`_KnownHostsPolicy`) already supplied the type;
jump-host path benefits automatically.

```text
Fix ID: FIX-W18-002
Defect ID: DEF-W18-002
Severity: P2
Independent root cause: yes (prompt data plumbing; failure-message routing untouched)
Before behavior: prompt always showed "Type: SSH" regardless of offered algorithm
Before evidence ID: EV-W18-002 (source trace wx_connection.py:365 pre-fix + probe)
Files changed: src/hpc_gui/services/connection_controller.py (field), src/hpc_gui/wx_connection.py (forward + format)
Behavioral contract changed: unknown-host prompt names the real algorithm (e.g. ssh-ed25519/ssh-rsa) alongside host/fingerprint/role
Regression test(s): key_type forwarding + prompt identity unit tests + GUI accept/reject/cancel prompt test
Sensitivity proof: fault-injection revert (drop forward + hardcode) -> key-type tests fail; restore -> green
Negative test: absent key_type still renders "SSH" fallback (covered in formatter default)
Narrow-suite result: 14 passed (new file)
Broader-suite result: same as FIX-W18-001 (shared suites)
Runtime/manual result: build/audit/w18-gui-pytest.txt; TR sanity check PASS (both languages render type/host/fingerprint)
Package result (if applicable): NOT APPLICABLE
External result (if applicable): E-matrix host-key rows use real server keys (rsa) through the same prompt path
Residual risk: none known (additive defaulted field; all existing constructors compatible)
```

## Tests

New: `tests/test_w18_auth_hostkey.py` — 14 tests, each with REQ/DEF/CON/NEG
purpose IDs, behavioral assertions, stated mock boundaries
(transport/dialog-chrome only), no skips/xfails/weakening:

```text
Exact counts (final, solo-sequenced):
- new file: 14 passed, 0 failed, 0 skipped, 0 xfailed, exit 0 (build/audit/w18-gui-pytest.txt)
- focused slice (w18 + wx_connection + controller + profile-service + ssh-credential + optional): 68 passed, 9 subtests passed, exit 0
- wider wx slice (71_2..71_5 + hardening + profiles): 79 passed, exit 0
- W11 lifecycle solo: 14 passed; W15 fresh-user solo: 11 passed; profile-patch + optional: 25 passed, 9 subtests
- combined-run note: W11+W15+patch in one process shows 2 W15 failures also present WITHOUT this Wave's changes (pre-existing wx singleton/timing interference; each file green solo). Not caused by, not touched by, this Wave.
Post-green review: no duplicate path (resolve-step errors keep dedicated mapping; jump errors flow through classifier); alternate entries share connect_selected; no silent fallback added (accept-new auto-save is configured CLI semantics, wx always prompts); stale-state teardown untouched (W17); no secrets in diff; no dead branch (moved master_wrong/saved_password branches locked by new unit test); no provider hardcoding; no success-claiming errors; no packaging divergence.
POST_GREEN_REVIEW: complete, no new defect kept open (OBS items routed, not absorbed).
```

Test-quality checklist: counted fixes have regression tests YES; sensitivity
proven YES (fault injection); negative paths YES; lifecycle/cancel YES;
behavioral assertions YES; mocks at transport/chrome boundary only YES; no new
skips/xfails YES; isolated fixtures YES; deterministic cleanup YES;
package/external honestly classified YES; impacted slices pass YES; revert
would fail YES.

## Evidence

- GUI (required): real wx App/panel/controller event runs —
  `build/audit/w18-gui-pytest.txt` (14/14, exit 0): wrong-password visible
  FAILED + guidance; missing-key actionable; changed-key mapped hard fail;
  host-key prompt accept(YES->save)/once(NO)/reject(CANCEL) with real key
  type in text; master-cancel safe state (FAILED, no dialog, "Authentication
  cancelled", buttons re-enabled); no secret echo (TE_PASSWORD controls +
  redaction proof + 0-leak probe).
- EXTERNAL (required): real authorized lab, loopback container `hpclab`
  (healthy before AND after; image hpc-client-gui-lab; remote environment
  class: local containerized single-node Slurm; provider direct SSH;
  password auth via env-only fixture; timestamps +03:00 2026-09-20) —
  `build/audit/w18-external-matrix.txt`: E1 auth+echo PASS, E2 wrong-pw
  PASS, E3 reconnect-after-accept PASS, E4 poisoned-key hard fail PASS
  (HostKeyChangedError), E5 reject PASS, E6 strict PASS, E7 missing-key
  PASS, E8 agent-absent PASS; cleanup PASS (temp known_hosts removed; lab
  unmodified — auth attempts only). Secret scan of log: clean.
- PACKAGE: N/A — required classes for W18 are GUI+EXTERNAL; no build,
  dependency, resource, or runtime-config change was made.

## Diff review

```text
git diff --check: clean (unrelated CRLF warnings only, pre-existing)
W18-owned changes only:
  M src/hpc_gui/wx_connection.py (helpers + closure forward + dialog + done/cancel; pre-existing W17 hunks preserved)
  M src/hpc_gui/services/connection_controller.py (defaulted key_type field only)
  ?? tests/test_w18_auth_hostkey.py (new, 14 tests)
  ?? build/audit/w18-gui-pytest.txt, build/audit/w18-external-matrix.txt (evidence)
  ?? docs/wave-reports/v2/opencode/ (this report path; directory untracked pre-existing)
No secrets, no generated/binary noise, no weakened tests, no unrelated-file edits (all other dirty files byte-identical to session start).
```

## Resume state

```text
Completed and verified:
- Discovery + findings + 12-dim second-defect search
- FIX-W18-001 + FIX-W18-002 with sensitivity proofs
- 14-test regression file green; impacted slices green (solo)
- GUI + EXTERNAL evidence current, secret-clean
- Report current (this file)
In progress: none (awaiting fresh-context audit)
Open P0/P1: none. Open P2/P3: none in-scope (OBS-W18-003/004 routed to W19 with IDs)
Pending tests/evidence: none for W18
Last exact commands run:
- python -m pytest tests/test_w18_auth_hostkey.py -v -p no:randomly (14 passed, exit 0)
- python -m pytest <focused+wx slices> (68 and 79 passed, exit 0)
- EXTERNAL matrix via HPC_LAB_PASSWORD env (8/8 PASS, log saved)
Next actions:
1. Fresh-context audit of W18 (separate session/model)
2. On PASS, W19 may be planned only after dependency revalidation (do NOT auto-start)
Evidence/artifact identities:
- main 0f8902a023bac76071527232c2287af96478ed2b (develop == origin/develop)
- plugin f0abb7e7037e66ab451d463c699fecf4e00c89eb
- build/audit/w18-gui-pytest.txt, build/audit/w18-external-matrix.txt
```

## Final adversarial self-audit

1. FIX-A: shared-mapping failure/cancel feedback; FIX-B: key-type plumbing to prompt.
2. Independent: message routing/ordering vs prompt data — different files, failure modes, tests.
3. Before evidence: mock-server probes (raw outputs) + Qt-vs-wx trace + hardcoded "SSH" line.
4. Revert test: fault injection fails exactly the 6 proving tests; restore greens.
5. Negative paths: wrong-pw, missing-key, changed-key, no-credential, strict-unknown, cancel.
6. Bypass paths: none — all wx connect failures funnel through `done()`; all prompts through the decision closure.
7. Mocks: transport + dialog chrome only; controller/model/panel/i18n/classifier real. Do NOT prove: native dialog rendering, real-network auth (covered by EXTERNAL instead).
8. Manual/runtime: real wx event runs + real lab matrix (no manual checklist needed beyond).
9. Uncertainties: combined-process wx test pollution (pre-existing, documented, unrelated).
10. Cosmetic/duplicate/test-only? No — both change user-visible security behavior with failing-before proofs.

```text
FIX-A: FIX-W18-001
DEF: DEF-W18-001
Root cause: wx done() bypassed shared classifier + dedicated host-key messages; cancel status raced repaint
Before EV: EV-W18-001 (raw probe outputs + Qt-vs-wx trace)
After EV: build/audit/w18-gui-pytest.txt (14 passed) + build/audit/w18-external-matrix.txt (8/8)
Regression test: tests/test_w18_auth_hostkey.py (mapping + GUI failure/cancel tests)
Sensitivity proof: fault-injection revert -> 6 fail; restore -> green

FIX-B: FIX-W18-002
DEF: DEF-W18-002
Root cause: HostKeyRequest lacked key_type; dialog hardcoded "SSH"
Before EV: EV-W18-002 (pre-fix source line + probe)
After EV: same logs as above
Regression test: tests/test_w18_auth_hostkey.py (forwarding + prompt + GUI prompt tests)
Sensitivity proof: fault-injection revert -> key-type tests fail; restore -> green

Additional fixes: none (minimum-two floor met; no other in-scope P0/P1 found)
Post-green review: complete (see checklist above)
New/modified tests: tests/test_w18_auth_hostkey.py (14 new, 0 modified elsewhere)
Skipped/xfail changes: none
Package evidence: N/A (justified above)
External evidence: build/audit/w18-external-matrix.txt (E1-E8 PASS, cleanup PASS, secret scan clean)
Open P0/P1: none
Open P2/P3: none in-scope (OBS-W18-003/004 routed to W19)
Two-fix gate: PASS
Wave decision: GO (pending fresh-context audit) / READY_FOR_AUDIT
```
