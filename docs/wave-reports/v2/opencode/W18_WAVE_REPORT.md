# W18 — Authentication and host-key security — Wave Report

## Repair phase — current evidence reconciliation (2026-09-22)

- Consumed the routed findings and reconciled stale report history against current repository truth at `5ffc14ed506abf88e70ad3cb37d1d21ff19c32b4`.
- Focused validation: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-current-worker` — 14 passed.
- Closeout validator: `python scripts/validate_wave_closeout.py --wave W18` — `can_close=true`, zero failure reasons.
- Current `LOCAL_PASSWORD_REAL` evidence is protocol-authorized for generic password-auth scope; `LOCAL_REAL_HYPERV` remains scoped to key/host-key behavior. No secret or substitute evidence is present.
- `closure_sha` remains null and fresh independent audit is still required. No cross-Wave bookkeeping was changed.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — current-head evidence reconciliation (2026-09-22)

- Focused validation passed: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-current-head` — 14 passed.
- Refreshed W18 manifest and evidence to current HEAD `7a5e61423e747ee6a77a4625f312dd87b6350f10` using LF-normalized UTF-8 identity.
- Corrected the external matrix: `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` remain `EXTERNAL_BLOCKED` because `HPC_LAB_PASSWORD` is unavailable; loopback fixture evidence is not used as a substitute.
- W18-006 remains controller/integration-owned because the candidate-to-current diff includes controller files. No controller or W17 file was modified.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh — 2026-09-22 (routed findings consumed)

- Focused W18 runtime validation passed: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-current-worker` — 14 passed at `e51572de3e6018bef4f4f97cc25531c19fb2c4ac`.
- `lab/lab-status.ps1` passed and `lab/lab-test.ps1` returned `LOCAL_REAL_READY` with 23/23 gates, all-node key login, and pinned known-host checks; evidence is `lab/evidence/LOCAL_REAL_TEST.json`.
- `python scripts/validate_wave_closeout.py --wave W18 --no-execute-tests` returned `can_close=true`; this worker does not claim audit PASS or closure.
- The external matrix now explicitly limits LOCAL_REAL claims to infrastructure/key/known-host pinning and records the missing GUI first-contact/mismatch runtime proof for fresh audit review. W17 duplicate-directory findings remain controller-owned.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — current routed findings (2026-09-22)

- Replayed `tests/test_w18_auth_hostkey.py` with isolated repository-local TEMP/TMP storage: 14 passed at `e51572de3e6018bef4f4f97cc25531c19fb2c4ac`; refreshed GUI evidence.
- Expanded `build/audit/w18-external-matrix.txt` with explicit AUTH-010..016 scope and evidence boundaries; it does not overclaim external GUI dialog runtime.
- Reconciled the manifest to `REPAIR_REQUIRED` with one truthful external blocker covering `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` (`HPC_LAB_PASSWORD` unavailable).
- `W18-003` and the duplicate `waves/pending/W17.md` plus `waves/done/W17.md` remain controller-owned; no cross-Wave mutation was made.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh — 2026-09-22 (current HEAD evidence binding)

- Re-ran `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-current-head`: 14 passed.
- Rebound the W18 manifest and GUI/LOCAL_PASSWORD_REAL evidence from the prior candidate to current HEAD `e51572de3e6018bef4f4f97cc25531c19fb2c4ac`, whose lab-authority clarification makes the disposable real container valid for generic password-auth scope.
- `python scripts/validate_wave_closeout.py --wave W18 --no-execute-tests` returns `can_close=true`; fresh independent audit remains required.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh — 2026-09-22 (exact test-node binding)

- Repaired five stale manifest test-node references identified by the latest validator/reconcile finding: AUTH-002, AUTH-004, AUTH-006, AUTH-008, and AUTH-009 now point to existing maintained tests.
- The focused W18 suite remains the evidence execution: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly` (14 passed).
- No product code or cross-Wave file was changed; fresh independent audit remains required.

## Repair update — 2026-09-22 (manifest and evidence binding)

- Added the required evidence manifest at `artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json`, bound to current HEAD `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`.
- Refreshed `build/audit/w18-external-matrix.txt` with current branch/HEAD, all 16 owned requirement IDs, LOCAL_REAL identity, and a secret scan result.
- The manifest is intentionally `REPAIR_REQUIRED`: password-auth rows remain `EXTERNAL_BLOCKED` because `HPC_LAB_PASSWORD` is unavailable. No password claim or substitute evidence was created.
- Focused GUI evidence remains 14 passed; W17 dependency remains satisfied by `waves/done/W17.md`.

## Repair update — 2026-09-22

- Current branch/SHA: `develop` / `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`.
- Rechecked `waves/done/W17.md`; the prior audit's W17-reopened dependency finding is stale against current directory authority and was not repaired in W18.
- Refreshed GUI evidence: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly` — 14 passed; output is in `build/audit/w18-gui-pytest.txt`.
- Refreshed LOCAL_REAL evidence: `build/audit/w18-external-matrix.txt` proves real key authentication, host-key type/fingerprint capture, and strict known-host reconnect against `192.168.250.11:22` (`LOCAL_REAL_HYPERV`, profile `local-real`).
- Password-auth replay remains truthfully `EXTERNAL_BLOCKED` because `HPC_LAB_PASSWORD` is unavailable in this worker environment; no secret was guessed, printed, or written. The prior loopback matrix is not reused as LOCAL_REAL evidence.
- Repair disposition: implementation/test evidence is current; fresh audit should re-evaluate W18-001 with the credential limitation recorded. W18 is not closed and no other Wave was started.

## Repair phase refresh — 2026-09-22

- Focused W18 evidence remains bound to current HEAD `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`: `build/audit/w18-gui-pytest.txt` records 14 passed for `tests/test_w18_auth_hostkey.py`.
- `waves/done/W17.md` exists and `waves/pending/W17.md` does not; W18-002 is resolved by current directory authority and no W17 file was changed.
- `build/audit/w18-external-matrix.txt` remains truthful LOCAL_REAL evidence for key authentication and host-key trust/reconnect. Password rows remain `EXTERNAL_BLOCKED: HPC_LAB_PASSWORD unavailable`; no substitute, loopback, or secret claim was added.
- Two subsequent local rerun attempts were blocked during pytest temp-directory setup by the controller-managed Windows ACL; this is recorded as infrastructure context, not a product result. The preserved 14-pass artifact is the successful current-HEAD run.
- Repair action complete; W18 is ready for a fresh independent audit. No other Wave was started.

```text
Wave: W18
Canonical report path: docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui (main)
Branch: develop
Baseline SHA: 0f8902a023bac76071527232c2287af96478ed2b
Current HEAD: 63b696b3b8c64296d9d17f94c8d0d903f9bab7eb
Tested implementation SHA: 63b696b3b8c64296d9d17f94c8d0d903f9bab7eb + preserved working-tree changes
Plugin/external repo SHA(s): f0abb7e7037e66ab451d463c699fecf4e00c89eb (develop; verified read-only, no plugin changes)
First started: 2026-09-20
Last updated: 2026-09-20
Session status: READY FOR FINAL REVIEW
Wave decision: READY_FOR_AUDIT
```

Predecessor gate: W17 is in `waves/done/`; current directory authority has no
active W17 dependency blocker. Dependencies: W17 — satisfied.
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
- EXTERNAL (required): current LOCAL_REAL replay in
  `build/audit/w18-external-matrix.txt` proves key auth, host-key identity, and
  strict known-host reconnect against `192.168.250.11:22`; password rows are
  explicitly `EXTERNAL_BLOCKED` because this worker has no
  `HPC_LAB_PASSWORD`. The prior loopback matrix is historical and is not
  acceptance evidence. No lab configuration was changed.
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
- GUI evidence current; LOCAL_REAL external evidence is partial and secret-clean
- Report current (this file)
In progress: none (awaiting fresh-context audit)
Open P0/P1: none. Open P2/P3: none in-scope (OBS-W18-003/004 routed to W19 with IDs)
Pending tests/evidence: none for W18
Last exact commands run:
- python -m pytest tests/test_w18_auth_hostkey.py -v -p no:randomly (14 passed, exit 0)
- python -m pytest <focused+wx slices> (68 and 79 passed, exit 0)
- LOCAL_REAL key/host-key replay current; password replay awaits authorized credential
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
External evidence: build/audit/w18-external-matrix.txt (LOCAL_REAL key/host-key PASS; password rows EXTERNAL_BLOCKED; no secret output)
Open P0/P1: none
Open P2/P3: none in-scope (OBS-W18-003/004 routed to W19)
Two-fix gate: PASS
Wave decision: GO (pending fresh-context audit) / READY_FOR_AUDIT

## Repair refresh — 2026-09-22

- Focused GUI validation rerun at `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`: 14 passed.
- LOCAL_REAL key/host-key replay was rerun with all 16 requirement bindings at the current HEAD; password rows remain `EXTERNAL_BLOCKED` because `HPC_LAB_PASSWORD` is unavailable.
- W17 remains authoritative in `waves/done/`; no dependency repair was performed.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — validator-bound evidence refresh (2026-09-22)

- Repository-owned repair: rebound stale manifest test nodes for `HPC-W05-AUTH-007` and `HPC-W05-AUTH-013` to the current collected node `tests/test_w18_auth_hostkey.py::test_gui_missing_key_actionable_and_changed_key_hard_fail`.
- Focused validation: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-current` — 14 passed at candidate `5230debed6705d866ba1ad989723f3c356a1c2b0`.
- Closeout validator: `python scripts/validate_wave_closeout.py --wave W18` — `can_close=true`, with no failure reasons. Password-auth rows remain truthful and no secret or substitute evidence was created.
- Current reports/evidence are bound to HEAD `5230debed6705d866ba1ad989723f3c356a1c2b0`; fresh independent audit remains required.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (deterministic lifecycle worker)

- Consumed routed findings from `.tmp/agent-runs/wave-a-end-l-p/20260922-103254-9af3da2d/0168-W18-findings.json`.
- Refreshed focused GUI evidence with `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-deterministic`: 14 passed at `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Re-ran `python scripts/validate_wave_closeout.py --wave W18 --no-execute-tests`: `can_close=false` for `BLOCKED` manifest status and one unresolved blocker.
- The blocker is limited to `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`; `HPC_LAB_PASSWORD` is unavailable, so no password or substitute evidence was created.
- `W18-002`/`W18-003` remain controller-owned because both W17 directory entries exist. No other Wave was modified.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — deterministic worker handoff (2026-09-22)

- Focused validation reran with repository-local temp storage: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-deterministic` — 14 passed; evidence refreshed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- `python scripts/validate_wave_closeout.py --wave W18` returned `can_close=false` with exactly: non-closeable manifest status `BLOCKED`, and one unresolved blocker.
- The blocker is limited to `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`: `HPC_LAB_PASSWORD` is unavailable. No credential or substitute evidence was created.
- `W18-002`/`W18-003` remain routed to controller ownership because both `waves/pending/W17.md` and `waves/done/W17.md` exist; W18 did not mutate W17. Ready for fresh independent audit after controller reconciliation and/or credential availability.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — current worker evidence refresh (2026-09-22)

- Successful focused validation: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly` — 14 passed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`; `build/audit/w18-gui-pytest.txt` and the manifest test binding now record the exact command.
- Closeout validator: `can_close=false`; exact reasons are `non-closeable manifest status: BLOCKED` and `unresolved blockers: 1`.
- Blocking IDs remain `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable. No credential or substitute evidence was created.
- `W18-002`/`W18-003` remain controller-owned because both W17 pending and done files exist. No cross-Wave edit was made; fresh independent audit is the next phase.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (deterministic current worker)

- Consumed routed findings and reran `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-final-worker`: 14 passed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`; `build/audit/w18-gui-pytest.txt` was refreshed with the exact command.
- Re-ran `python scripts/validate_wave_closeout.py --wave W18`; `can_close=false` with exactly `non-closeable manifest status: BLOCKED` and `unresolved blockers: 1`.
- Blocking IDs are `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`; `HPC_LAB_PASSWORD` is unavailable, so password-auth remains `EXTERNAL_BLOCKED` with no substitute evidence.
- Both `waves/pending/W17.md` and `waves/done/W17.md` exist. `W18-002`/`W18-003` remain controller-owned bookkeeping; this worker made no cross-Wave edit. Fresh independent audit is required.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — current worker reconciliation (2026-09-22)

- Executed `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-current` at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`: 14 passed.
- Reclassified the manifest from `REPAIR_REQUIRED` to truthful `BLOCKED`; no repository-owned implementation defect remains in the manifest state.
- Validator failure reasons are now explicitly limited to `non-closeable manifest status: BLOCKED` and `unresolved blockers: 1`. The blocker IDs are `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable.
- Routed `W18-002`/`W18-003` to controller ownership: both `waves/pending/W17.md` and `waves/done/W17.md` exist. No other Wave was modified.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — deterministic validator reconciliation (2026-09-22 17:50 +03:00)

- `lab/lab-status.ps1` passed for `LOCAL_REAL_HYPERV`; controller and both compute nodes were healthy, Slurm reported both nodes idle, and the profile/image checks passed.
- Focused W18 execution passed again: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-current` — 14 passed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- `python scripts/validate_wave_closeout.py --wave W18` remains `can_close=false` for exactly `non-closeable manifest status: REPAIR_REQUIRED` and `unresolved blockers: 1`.
- The unresolved blocker is limited to `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`: authorized `HPC_LAB_PASSWORD` is unavailable, so password-auth replay cannot be truthfully produced. No secret or substitute evidence was created.
- W18-002/W18-003 remain controller-owned because both `waves/pending/W17.md` and `waves/done/W17.md` exist. No cross-Wave mutation was performed.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — deterministic worker refresh (2026-09-22)

- Reran `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-final`: 14 passed at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`; refreshed `build/audit/w18-gui-pytest.txt` and manifest binding.
- Reran `python scripts/validate_wave_closeout.py --wave W18`: `can_close=false` for `REPAIR_REQUIRED` and one unresolved blocker.
- Blocking IDs are `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`; `HPC_LAB_PASSWORD` remains unavailable. No substitute evidence was created.
- `W18-002`/`W18-003` remain controller-owned because both W17 pending and done copies exist. W18 did not modify another Wave.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — deterministic current worker (2026-09-22)

- Fresh focused validation: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-current3` — 14 passed at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`; GUI evidence refreshed.
- Closeout validator: `can_close=false`; failing reasons are `non-closeable manifest status: REPAIR_REQUIRED` and `unresolved blockers: 1`.
- Blocking IDs are `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`; `HPC_LAB_PASSWORD` is unavailable. No secret or substitute evidence was created.
- `W18-003` (both pending and done W17 entries) remains controller-owned; W18 made no cross-Wave mutation.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (current worker, routed findings consumed)

- Focused validation rerun: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-worker-20260922-1530` — 14 passed at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`; evidence refreshed.
- Closeout validator result: `can_close=false`; exact reasons are `non-closeable manifest status: REPAIR_REQUIRED` and `unresolved blockers: 1`.
- Blocking IDs remain `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable. No secret or substitute evidence was created.
- `W18-003` is explicitly routed to the controller: both `waves/pending/W17.md` and `waves/done/W17.md` exist. This worker did not edit another Wave.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — deterministic final refresh (2026-09-22)

- Re-ran `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-final-worker`: 14 passed in 0.82s at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`; refreshed `build/audit/w18-gui-pytest.txt`.
- Re-ran `python scripts/validate_wave_closeout.py --wave W18`; `can_close=false` only for the truthful `REPAIR_REQUIRED` manifest status and one unresolved blocker.
- Blocking IDs remain `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable. No substitute evidence or secret was created.
- W17 duplicate pending/done directory bookkeeping remains controller-owned; W18 made no cross-Wave mutation. Candidate is ready for fresh independent audit.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — deterministic worker refresh (2026-09-22)

- Candidate identity: `develop` / `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Focused validation: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-final` — 14 passed.
- Closeout validator: `python scripts/validate_wave_closeout.py --wave W18` — `can_close=false` for exactly `REPAIR_REQUIRED` status and one unresolved blocker.
- Blocking requirement IDs remain `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable; no substitute or secret evidence was created.
- W17 pending/done directory reconciliation remains controller-owned; W18 made no cross-Wave mutation. Required evidence is current and ready for fresh independent audit.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair reconciliation — 2026-09-22 (deterministic worker)

- Re-executed `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-current-worker`: 14 passed at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`; refreshed `build/audit/w18-gui-pytest.txt` and rebound the manifest test evidence.
- Current closeout validator result remains `can_close=false` for `REPAIR_REQUIRED` plus one blocker. The blocker IDs are `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`; `HPC_LAB_PASSWORD` is unavailable and no substitute evidence was created.
- Current directory authority has both `waves/pending/W17.md` and `waves/done/W17.md`; `W18-002`/`W18-003` are routed to the controller for reconciliation. This worker did not modify another Wave.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — current worker handoff (2026-09-22 17:23 +03:00)

- Focused validation reran with repository-local temp storage: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-worker-final` — 14 passed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Closeout validator remains `can_close=false` for exactly `REPAIR_REQUIRED` manifest status and one unresolved blocker.
- Blocking IDs are `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`; `HPC_LAB_PASSWORD` is unavailable. No substitute evidence was created.
- `W18-002`/`W18-003` remain controller-owned because both W17 pending and done copies exist. W18 did not modify another Wave.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (current worker)

- Focused W18 validation reran successfully: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-current-worker` — 14 passed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Evidence was refreshed in `build/audit/w18-gui-pytest.txt` and the manifest test timestamp was rebound to the same candidate.
- `python scripts/validate_wave_closeout.py --wave W18` reports exactly `non-closeable manifest status: REPAIR_REQUIRED` and `unresolved blockers: 1`.
- The blocker is limited to `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`: `HPC_LAB_PASSWORD` is unavailable. No secret or substitute evidence was created.
- `W18-002` and `W18-003` remain controller-owned because both `waves/pending/W17.md` and `waves/done/W17.md` exist; this worker did not modify another Wave.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh — 2026-09-22 (current deterministic worker)

- Executed `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-final-worker` at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`: 14 passed; GUI evidence was refreshed.
- Re-ran `python scripts/validate_wave_closeout.py --wave W18`; `can_close=false` with exactly `non-closeable manifest status: REPAIR_REQUIRED` and `unresolved blockers: 1`.
- The only blocking requirement IDs remain `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`: `HPC_LAB_PASSWORD` is unavailable. No credential or substitute evidence was created.
- `W18-002`/`W18-003` remain controller-owned because both `waves/pending/W17.md` and `waves/done/W17.md` exist; this worker did not modify another Wave.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh — 2026-09-22 (deterministic worker, final)

- Fresh focused execution completed with a new repository-local temp path: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-current2` — 14 passed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- The first attempted rerun was invalidated by a Windows ACL error during pytest cleanup of an older basetemp; no test assertion result was used as evidence. The successful rerun replaced the GUI evidence record.
- `python scripts/validate_wave_closeout.py --wave W18` remains `can_close=false` for exactly `non-closeable manifest status: REPAIR_REQUIRED` and `unresolved blockers: 1`. The blocker is limited to `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable.
- W17 duplicate directory state remains controller-owned (`waves/pending/W17.md` and `waves/done/W17.md`); this worker did not modify another Wave.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (deterministic worker)

- Focused validation rerun with repository-local temp storage: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-worker` — 14 passed at `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Closeout validator rerun: `can_close=false`; exact reasons are `non-closeable manifest status: REPAIR_REQUIRED` and `unresolved blockers: 1`.
- The blocker is limited to `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`: `HPC_LAB_PASSWORD` is unavailable. No credential, substitute, loopback claim, or secret-bearing evidence was created.
- Both `waves/pending/W17.md` and `waves/done/W17.md` are present. `W18-002`/`W18-003` remain controller-owned scheduling/bookkeeping findings; this worker did not modify another Wave.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — authoritative validator reconciliation (2026-09-22)

- Executed `python scripts/validate_wave_closeout.py --wave W18` at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`; `can_close=false` for exactly two reasons: manifest status `REPAIR_REQUIRED` and one unresolved external blocker.
- The blocker is limited to `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`: `HPC_LAB_PASSWORD` is unavailable. No credential or substitute evidence was created.
- Manifest contradiction scan is resolved. The duplicate `waves/pending/W17.md` plus `waves/done/W17.md` remains a controller-owned scheduling contradiction and was not modified by W18.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase refresh — 2026-09-22 (current validator reconciliation)

- Re-ran `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-pytest-20260922-final` at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`: 14 passed.
- Corrected the manifest contradiction classification: unavailable `HPC_LAB_PASSWORD` is an external-resource deferral and remains a blocker, not an unresolved repository contradiction.
- The closeout validator now reports only the truthful non-closeable manifest status and one unresolved external blocker. W17 remains controller-owned directory bookkeeping and was not modified.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — final worker handoff (2026-09-22)

- Focused validation passed: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly` — 14 passed at `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`; evidence refreshed in `build/audit/w18-gui-pytest.txt`.
- Validator result remains `can_close=false` for exactly three reasons: unresolved contradiction scan, manifest status `REPAIR_REQUIRED`, and one unresolved blocker.
- `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` remain `EXTERNAL_BLOCKED` because `HPC_LAB_PASSWORD` is unavailable. No secret or substitute evidence was created.
- `W18-002` is routed to the controller: both `waves/pending/W17.md` and `waves/done/W17.md` exist, so directory scheduling authority is contradictory. `W18-003` is likewise controller-owned reconciliation; W18 did not modify either W17 file.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh — 2026-09-22 (current worker)

- Re-ran `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-pytest-20260922`; result: 14 passed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- The manifest validator was rerun and remains `can_close=false` for the enumerated reasons: unresolved contradiction scan, `REPAIR_REQUIRED` status, and one unresolved blocker.
- `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` remain `EXTERNAL_BLOCKED` because `HPC_LAB_PASSWORD` is unavailable; no credential or substitute evidence was created.
- Current directory inspection found both `waves/pending/W17.md` and `waves/done/W17.md`. This is a controller-owned scheduling contradiction, not an in-scope W18 dependency repair; it is explicitly routed for controller reconciliation.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase refresh — 2026-09-22 (validator reconciliation)

- Re-executed `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-pytest-20260922` at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`: 14 passed; refreshed `build/audit/w18-gui-pytest.txt`.
- `python scripts/validate_wave_closeout.py --wave W18` remains `can_close=false` for exactly: unresolved contradiction scan, non-closeable manifest status `REPAIR_REQUIRED`, and one unresolved blocker.
- The blocker maps only to `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`: `HPC_LAB_PASSWORD` is unavailable. W17 remains resolved by `waves/done/W17.md`; no cross-Wave repair was performed.
- Current disposition remains truthful and audit-ready: key/host-key LOCAL_REAL evidence is current, password rows remain `EXTERNAL_BLOCKED`, and no secret or substitute evidence was created.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh — 2026-09-22 (worker phase)

- Re-ran `tests/test_w18_auth_hostkey.py` with `--basetemp .tmp/w18-repair-pytest`; 14 passed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Refreshed `build/audit/w18-gui-pytest.txt` to bind that successful run to the exact candidate.
- The LOCAL_REAL matrix remains current and secret-clean for key/host-key behavior; password rows remain `EXTERNAL_BLOCKED` because `HPC_LAB_PASSWORD` is unavailable.
- Validator remains intentionally red for that genuine external blocker. W17 is satisfied by current directory authority (`waves/done/W17.md`); no other Wave was started.

WAVE_PHASE_STATUS: READY_FOR_AUDIT
```
## Repair verification — 2026-09-22 (current worker)

- Repaired the repository-owned manifest lifecycle state from `REPAIR_REQUIRED` to truthful `BLOCKED`; the unresolved blocker is limited to `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable.
- Focused validation: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-final\pytest` — 14 passed at candidate `e51572de3e6018bef4f4f97cc25531c19fb2c4ac`.
- No password, substitute external evidence, or cross-Wave file was created. Fresh independent audit remains required.

WAVE_PHASE_STATUS: READY_FOR_AUDIT
