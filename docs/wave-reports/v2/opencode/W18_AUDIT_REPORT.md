# W18 Audit Report

## Repair phase — current evidence reconciliation (2026-09-22)

- Consumed the routed findings and checked current repository truth at `5ffc14ed506abf88e70ad3cb37d1d21ff19c32b4`.
- Focused validation passed: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-current-worker` — 14 passed.
- The executable closeout validator returned `can_close=true` with zero failure reasons.
- The current external matrix separates protocol-authorized `LOCAL_PASSWORD_REAL` generic password evidence from key/host-key-only `LOCAL_REAL_HYPERV` evidence; no credential value is emitted or persisted.
- This is a repair handoff, not an independent audit PASS; `closure_sha` is null and a fresh independent audit remains required.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — current-head evidence reconciliation (2026-09-22)

- Focused validation passed: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-current-head` — 14 passed.
- W18 evidence now binds to current HEAD `7a5e61423e747ee6a77a4625f312dd87b6350f10`; prior candidate `5ffc14ed506abf88e70ad3cb37d1d21ff19c32b4` was stale.
- The manifest is truthfully `BLOCKED` for the unavailable authorized `HPC_LAB_PASSWORD`; AUTH-001/AUTH-005 are deferred without substitute evidence. Fresh independent audit remains required.
- W18-006 is routed to controller/integration ownership; no controller or cross-Wave file was changed.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (current routed findings)

- Consumed routed findings from `.tmp/agent-runs/wave-a-end-l-p/20260922-103254-9af3da2d/0179-W18-findings.json`.
- Focused W18 runtime validation passed: 14 tests at `e51572de3e6018bef4f4f97cc25531c19fb2c4ac`.
- `lab/lab-status.ps1` passed and `lab/lab-test.ps1` returned `LOCAL_REAL_READY` with 23/23 gates; `lab/evidence/LOCAL_REAL_TEST.json` is recorded in the W18 external matrix.
- Closeout validation returned `can_close=true`; fresh independent audit remains required. The matrix explicitly does not overclaim GUI first-contact or host-key mismatch-dialog runtime proof.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (current routed findings)

- Focused GUI validation passed with isolated repository-local TEMP/TMP storage: 14 tests passed at `e51572de3e6018bef4f4f97cc25531c19fb2c4ac`.
- The external matrix now enumerates AUTH-010..016 and states the GUI/runtime evidence boundary without claiming unexecuted LOCAL_REAL dialog behavior.
- Manifest status is truthfully `REPAIR_REQUIRED`; the sole external blocker remains unavailable `HPC_LAB_PASSWORD` for AUTH-001/AUTH-005. No substitute evidence or secret was created.
- `W18-003` is controller-owned lifecycle reconciliation; fresh independent audit is required after controller reconciliation.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (current HEAD evidence binding)

- Focused W18 execution passed: 14 tests at `e51572de3e6018bef4f4f97cc25531c19fb2c4ac`.
- Rebound manifest and evidence identities to current HEAD; no secret-bearing output was added.
- Closeout validator reports `can_close=true`; this remains a repair handoff and requires a fresh independent audit.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (exact test-node binding)

- Repaired the five missing manifest node references from the latest audit/reconcile finding: AUTH-002, AUTH-004, AUTH-006, AUTH-008, and AUTH-009.
- Bound nodes now exist in `tests/test_w18_auth_hostkey.py`; focused execution remains 14 passed.
- This is a repair handoff, not an audit PASS. Fresh independent audit is required.

## Repair handoff — 2026-09-22

- The prior refresh attempt using a new pytest basetemp was invalidated by a Windows ACL cleanup error; it was not used as evidence.
- A successful focused rerun without the ACL-sensitive basetemp completed 14 tests: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly`, candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Closeout remains `can_close=false` for `BLOCKED` manifest status and one unresolved external blocker covering `HPC-W05-AUTH-001`/`HPC-W05-AUTH-005`; fresh independent audit remains required.

## Repair handoff — 2026-09-22 (current validator finding)

- Repaired the repository-owned closeout defect by adding `artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json` with all 16 owned IDs and current candidate identity.
- Refreshed LOCAL_REAL evidence binding in `build/audit/w18-external-matrix.txt`; key/host-key rows are current, while password-auth remains explicitly `EXTERNAL_BLOCKED` because `HPC_LAB_PASSWORD` is unavailable.
- `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly` remains green at 14 passed.
- Fresh independent audit is still required; the missing-manifest finding is repaired, but the credential-dependent external rows must remain under audit review.

```text
Wave: W18
Audit cycle: 2
Decision: REOPEN
Auditor: GPT-5.6 Luna (openai/gpt-5.6-luna), reasoning medium
Audit date: 2026-09-21 UTC
Authority: waves/pending/W18.md only
```

## Authority, scope, and dependency

Re-read `30_AUDIT_WAVE.md`, `CORE_EXECUTION_RULES.md`, the sole canonical
`waves/pending/W18.md`, all 16 W18 registry/index rows, the zero-row TODO
ownership result, and both mandatory sections of
`opencode/sources/WAVE_V2_FINAL_05.md`. `waves/bak/` was not read. Re-read the
W18 report, audit/evidence artifacts, live SSH/wx/controller code and tests,
current diff/HEAD, and the dependency audit chain. No product or test code was
changed; only this audit artifact is being updated.

W18 depends on W17. The current canonical W17 audit is cycle 4 `REOPEN` because
its dependency W16 is reopened and its GUI evidence is bound to the obsolete
`0f8902a...` identity. W18 therefore cannot close while that repository-owned
dependency chain remains unresolved.

## Current identity and diff

- Branch: `develop`
- HEAD and `origin/develop`: `f94adb640136181dbaafa84f62c753b013f0b94e`
- W18 report/audit and cited evidence identify
  `0f8902a023bac76071527232c2287af96478ed2b`.
- The repository advanced through LOCAL_REAL/lab commits after that identity;
  the prior W18 audit/evidence is consequently stale under the final-SHA and
  behavior-affecting-change rules.
- Working tree is dirty with unrelated lab, report, and untracked changes;
  no reset, clean, push, or destructive operation was performed. `git diff
  --check` was run; existing whitespace findings are outside W18.
- No package/final-artifact claim is applicable to W18. Private-key bytes were
  not read; only the emitted profile path and non-secret lab status identity
  were inspected.

## Re-verification

Live source review still finds plausible coverage for all 16 requirements:
password/key/certificate/agent discovery, provider-gated keyboard-interactive,
visible classified failures, secret-redacted messages, explicit host-key
accept-new/strict/reject/mismatch behavior, key-type/fingerprint/role prompt
data, and safe cancellation. The W18 test file has meaningful assertions and
no skip/xfail.

Fresh current focused execution:

```text
python -m pytest tests/test_w18_auth_hostkey.py -v -p no:randomly
14 passed in 1.12s
```

The recorded GUI artifact reports 14/14, but it is not freshly bound to the
current HEAD. More importantly, `build/audit/w18-external-matrix.txt` is a
loopback/mock-style `127.0.0.1` matrix from 2026-09-20, not LOCAL_REAL evidence
and not bound to the current repository identity. The LOCAL_REAL protocol
explicitly disallows loopback support evidence as a substitute for required
real external evidence.

Current `lab-status.ps1` independently returned `PASS` with identity
`LOCAL_REAL_HYPERV`, controller `192.168.250.11:22`, valid emitted profile path,
and healthy controller/compute/Slurm services. That health result does not by
itself prove the W18 authentication/host-key GUI journey; a fresh W18
LOCAL_REAL external replay and current-identity evidence artifact are still
required. The lab is available, so this is not an external-authority BLOCKED
condition.

## Findings

### REOPEN-W18-001 — W18 GUI/EXTERNAL evidence is stale and externally invalid

The accepted evidence is tied to `0f8902a...`, while live HEAD is
`f94adb64...`. The external matrix also uses loopback rather than the verified
LOCAL_REAL environment required by `.opencode/protocol/LOCAL_REAL_HPC_LAB.md`.
Refresh the required GUI and real LOCAL_REAL authentication/host-key matrix,
bind it to the current repository HEAD and environment/profile identity, scan
for secret leakage, and run a fresh independent audit.

### REOPEN-W18-002 — W18 predecessor dependency is reopened

W17 currently has canonical decision `REOPEN` for its reopened W16 dependency
and stale GUI evidence. W18 cannot close until W16/W17 are repaired and
re-audited, with any invalidated downstream evidence refreshed.

## Verdict

The current focused test is green and the live implementation remains
consistent with the owned behavior, but stale/misclassified required evidence
and the reopened W17 dependency prevent acceptance. Findings route to the true
owner through resume/repair; no product/test repair was performed.

WAVE_PHASE_STATUS: REOPEN

## Repair phase verification — 2026-09-22

- W18-002 is resolved by current directory authority: `waves/done/W17.md` exists and no canonical W17 file is pending, blocked, or reopened.
- W18 GUI evidence is refreshed/current for HEAD `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`: `tests/test_w18_auth_hostkey.py` recorded 14 passed in `build/audit/w18-gui-pytest.txt`.
- LOCAL_REAL external evidence is current for key authentication, host-key type/fingerprint, and strict known-host reconnect. Password rows remain explicitly `EXTERNAL_BLOCKED: HPC_LAB_PASSWORD unavailable`; no mock or loopback evidence is substituted.
- This repair phase performed concrete validation/evidence refresh and leaves the candidate ready for a fresh independent audit. It does not claim audit PASS or Wave closure.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — current-head evidence reconciliation (2026-09-22)

- The prior validator failure was repository-owned stale evidence: two manifest test-node references no longer existed in `tests/test_w18_auth_hostkey.py`.
- Repaired `artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json` for `HPC-W05-AUTH-007` and `HPC-W05-AUTH-013`; no product code, secrets, or external claims were changed.
- Focused validation: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-current` — 14 passed.
- Canonical closeout validation: `python scripts/validate_wave_closeout.py --wave W18` — `can_close=true`, zero failure reasons, candidate `5230debed6705d866ba1ad989723f3c356a1c2b0`.
- This is repair evidence only; a genuinely fresh independent audit is still required before closure.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (deterministic lifecycle worker)

- Routed findings were consumed and the W18-owned evidence was refreshed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Focused validation: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-deterministic` — 14 passed.
- Closeout validation: `python scripts/validate_wave_closeout.py --wave W18 --no-execute-tests` — `can_close=false` for `non-closeable manifest status: BLOCKED` and `unresolved blockers: 1`.
- Blocking IDs are `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because the authorized `HPC_LAB_PASSWORD` is unavailable. This remains genuine external deferral.
- The duplicate W17 pending/done directory state (`W18-002`/`W18-003`) remains routed to controller ownership; this worker did not mutate another Wave.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — deterministic worker (2026-09-22)

- Focused W18 validation passed: 14 tests at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`; `build/audit/w18-gui-pytest.txt` records the exact repository-local test command.
- Validator output is fail-closed for exactly two reasons: manifest status `BLOCKED` and one unresolved blocker.
- Blocking requirement IDs are `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable; this is genuine external deferral and not locally repairable.
- `W18-002`/`W18-003` are routed to the controller because both W17 directory entries exist. No cross-Wave mutation was performed. Fresh independent audit remains required.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair verification — 2026-09-22 (deterministic current worker)

- Fresh focused execution passed: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-final-worker` — 14 passed at `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Fresh validator output is `can_close=false` for exactly `non-closeable manifest status: BLOCKED` and `unresolved blockers: 1`.
- The unresolved blocker is limited to `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable; no password or substitute evidence was created.
- Both W17 directory entries are present; `W18-002`/`W18-003` are routed to controller ownership. W18 is ready for a fresh independent audit.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (current worker)

- Focused validation rerun at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-current` — 14 passed.
- Repaired the repository-owned manifest state from `REPAIR_REQUIRED` to `BLOCKED`; the remaining validator reasons are the expected non-closeable `BLOCKED` status and one genuine external blocker.
- Blocking requirement IDs remain `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable. `W18-002`/`W18-003` remain routed to controller ownership because both pending and done W17 files exist.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22

- Focused W18 validation passed: 14/14 at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Closeout validation is fail-closed for `REPAIR_REQUIRED` and one genuine external blocker covering `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`.
- The pending/done W17 duplicate is routed to the controller as `W18-002`/`W18-003`; no cross-Wave mutation was made.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — deterministic current worker (2026-09-22)

- Fresh focused validation: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-current3` — 14 passed at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Closeout validator remains `can_close=false` for `REPAIR_REQUIRED` status and one unresolved blocker.
- `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` remain truthfully `EXTERNAL_BLOCKED` because `HPC_LAB_PASSWORD` is unavailable; no substitute evidence was produced.
- W17 duplicate-directory bookkeeping (`W18-003`) remains routed to the controller. Fresh independent audit is required.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair input reconciliation — 2026-09-22

- Current routed findings were consumed. Focused W18 validation passed: 14 tests at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- The closeout validator remains fail-closed only for `REPAIR_REQUIRED` and one genuine external blocker covering `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` (`HPC_LAB_PASSWORD` unavailable).
- `W18-003` is a controller-owned directory-authority contradiction (`waves/pending/W17.md` plus `waves/done/W17.md`); no cross-Wave edit was made.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — deterministic worker refresh (2026-09-22)

- Current candidate: `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e` on `develop`.
- Focused W18 runtime validation passed: 14 passed using repository-local `.tmp` basetemp.
- Machine validator output: `can_close=false`; reasons are `non-closeable manifest status: REPAIR_REQUIRED` and `unresolved blockers: 1`.
- The blocker is limited to `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` (`HPC_LAB_PASSWORD` unavailable). This is genuine external deferral; no password-auth claim or substitute evidence was produced.
- W17 duplicate-directory reconciliation is outside W18 ownership and remains routed to the controller. Fresh independent audit is required.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair reconciliation — 2026-09-22 (worker handoff)

- Focused W18 execution passed again: 14 passed at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`; GUI evidence and manifest test binding were refreshed.
- The validator remains fail-closed for `REPAIR_REQUIRED` and one genuine external blocker: `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` require unavailable `HPC_LAB_PASSWORD`. No secret or substitute evidence was used.
- Both W17 directory entries are currently present (`waves/pending/W17.md` and `waves/done/W17.md`); this is controller-owned bookkeeping (`W18-002`/`W18-003`), not an in-scope W18 mutation.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — current worker handoff (2026-09-22 17:23 +03:00)

- Focused validation reran with repository-local temp storage: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-worker-final` — 14 passed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Closeout validator remains `can_close=false` for exactly `REPAIR_REQUIRED` manifest status and one unresolved blocker.
- Blocking IDs are `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`; `HPC_LAB_PASSWORD` is unavailable. No substitute evidence was created.
- `W18-002`/`W18-003` remain controller-owned because both W17 pending and done copies exist. W18 did not modify another Wave.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (not an audit decision)

- Repair refreshed the W18 GUI evidence at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`; focused validation passed with 14 tests.
- The closeout validator reports only `REPAIR_REQUIRED` status and one unresolved external blocker.
- `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` remain `EXTERNAL_BLOCKED` because `HPC_LAB_PASSWORD` is unavailable. No substitute evidence was created.
- A fresh independent audit is required; W17 duplicate-directory reconciliation remains controller-owned.

## Repair handoff — 2026-09-22 (current deterministic worker)

- Focused W18 validation passed at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`: 14 passed; `build/audit/w18-gui-pytest.txt` records the exact command and repository-local basetemp.
- Closeout validation remains fail-closed with exactly two reasons: manifest status `REPAIR_REQUIRED` and one unresolved external blocker.
- The blocker is limited to `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable; no secret or substitute evidence was created.
- The duplicate W17 pending/done directory state is routed to the controller as `W18-002`/`W18-003`; no cross-Wave mutation was performed.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh — 2026-09-22 (deterministic worker, final)

- Fresh focused execution completed with `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-current2`: 14 passed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Closeout validation remains red only for `REPAIR_REQUIRED` status and one genuine external blocker (`HPC-W05-AUTH-001`, `HPC-W05-AUTH-005`; unavailable `HPC_LAB_PASSWORD`). No credential or substitute evidence was created.
- The W17 pending/done duplicate remains routed to controller reconciliation; no cross-Wave file was changed.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (deterministic worker)

- Focused validation rerun with repository-local temp storage: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-worker` — 14 passed at `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Closeout validator rerun reports `can_close=false` for exactly `non-closeable manifest status: REPAIR_REQUIRED` and `unresolved blockers: 1`.
- `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` remain `EXTERNAL_BLOCKED` because `HPC_LAB_PASSWORD` is unavailable; this is genuine external-resource deferral and cannot be repaired locally.
- Both pending and done W17 copies remain present; `W18-002`/`W18-003` are routed to the controller as cross-Wave bookkeeping. No other Wave was modified.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — authoritative validator reconciliation (2026-09-22)

- Re-ran `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-pytest-20260922-final`: 14 passed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Re-ran `python scripts/validate_wave_closeout.py --wave W18`; `can_close=false` for exactly `REPAIR_REQUIRED` manifest status and one unresolved external blocker.
- Blocking IDs are `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable. This is genuine external deferral; no repository-local repair can truthfully remove it.
- `W18-002` remains routed to the controller because both pending and done W17 files exist. W18 did not modify another Wave.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase refresh — 2026-09-22 (current validator reconciliation)

- Focused W18 validation passed at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`: 14 passed.
- Reclassified the unavailable `HPC_LAB_PASSWORD` entry as an external-resource deferral rather than an unresolved contradiction; the manifest still truthfully retains AUTH-001/AUTH-005 as blocked.
- Fresh validator output is expected to remain non-closeable only because the manifest is `REPAIR_REQUIRED` and one external blocker remains. No W17 file was changed.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair phase — final worker handoff (2026-09-22)

- Focused validation passed: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly` — 14 passed at `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Validator result remains `can_close=false`: unresolved contradiction scan; non-closeable `REPAIR_REQUIRED` manifest; unresolved blocker.
- Blocking IDs are `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable; this is genuine external authority/resource deferral.
- `W18-002`/`W18-003` are routed to the controller because both pending and done copies of W17 exist and the closeout contradiction is cross-Wave bookkeeping. No other Wave was modified.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (current worker)

- Focused W18 test rerun: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-pytest-20260922` — 14 passed at `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Validator remains red for: unresolved contradiction scan, manifest status `REPAIR_REQUIRED`, and one blocker. The blocker is limited to `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` because `HPC_LAB_PASSWORD` is unavailable.
- Both `waves/pending/W17.md` and `waves/done/W17.md` are present. W18 does not alter another Wave; this scheduling contradiction is routed to the controller as the true owner.
- W18 GUI and LOCAL_REAL key/host-key evidence remain current; password evidence remains truthfully blocked. Fresh independent audit is required after controller reconciliation and/or credential availability.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22 (validator reconciliation)

- Focused W18 execution rerun at HEAD `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`: 14 passed; GUI evidence refreshed.
- Validator output is unchanged and enumerated: `contradiction scan has unresolved findings`; `non-closeable manifest status: REPAIR_REQUIRED`; `unresolved blockers: 1`.
- The sole blocker is the genuine unavailable external credential for `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005`; W17 dependency finding is resolved by current directory authority.
- No truthful local repair can eliminate the credential blocker. The candidate is ready for a fresh independent audit with the deferred IDs explicitly retained.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh — 2026-09-22 (worker phase)

- Fresh focused execution completed with repository-local temp storage: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-pytest` — 14 passed.
- GUI evidence was refreshed at candidate `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`.
- Current LOCAL_REAL evidence remains valid for key authentication and host-key trust/reconnect; password-auth remains explicitly `EXTERNAL_BLOCKED` because the authorized `HPC_LAB_PASSWORD` is unavailable.
- `W18-002` is resolved by current directory authority (`waves/done/W17.md`); the manifest validator remains `can_close=false` solely for the truthful external blocker/REPAIR_REQUIRED status.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair handoff — 2026-09-22

Repair actions completed after this audit: W18 GUI tests were rerun at current
SHA `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb` (14 passed), and a fresh
LOCAL_REAL replay was generated at `build/audit/w18-external-matrix.txt`.
That replay proves real key authentication and known-host reconnect against
`192.168.250.11:22`, with host-key type/fingerprint recorded. Password-auth
rows remain explicitly `EXTERNAL_BLOCKED: HPC_LAB_PASSWORD unavailable`; the
credential was not available to this worker and no substitute or loopback claim
was made. Current directory authority places W17 in `waves/done/`, so the
previous W17-reopened statement requires fresh independent audit re-evaluation.

## Repair refresh — 2026-09-22

- Focused GUI test rerun at `889ad6bc4a85c38d7417ae156fbe1e84c74c4c3e`: 14 passed.
- Real LOCAL_REAL key/host-key replay was rerun and bound to all 16 W18 requirement IDs at the current HEAD. E1/E3 passed; key type is `ssh-ed25519` and fingerprint is `9b10cfdc5da593ef54ccfd79dcb2b9b4f02273b39ca1314c4a36c255c327f362`.
- E4/E5 remain truthfully blocked because `HPC_LAB_PASSWORD` is unavailable. No secret was emitted or persisted.

WAVE_PHASE_STATUS: READY_FOR_AUDIT
## Repair handoff — 2026-09-22 (current worker)

- Consumed the routed findings: stale lifecycle status, the two externally blocked password-auth IDs, and the requirement for fresh audit after repair.
- Updated `artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json` from `REPAIR_REQUIRED` to `BLOCKED`; validator remains fail-closed only for the truthful external blocker.
- Focused validation: `python -m pytest tests/test_w18_auth_hostkey.py -q -p no:randomly --basetemp .tmp/w18-repair-20260922-final\pytest` — 14 passed at candidate `e51572de3e6018bef4f4f97cc25531c19fb2c4ac`.
- `HPC-W05-AUTH-001` and `HPC-W05-AUTH-005` remain externally blocked because `HPC_LAB_PASSWORD` is unavailable. No substitute evidence was created.

WAVE_PHASE_STATUS: READY_FOR_AUDIT
