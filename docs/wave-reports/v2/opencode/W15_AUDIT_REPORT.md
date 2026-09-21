# W15 Audit Report

```text
Wave: W15
Decision: REOPEN
Auditor: GPT-5.6 Luna (openai/gpt-5.6-luna), reasoning medium
Audit date: 2026-09-21 UTC
Authority: waves/pending/W15.md only
```

## Scope and authority read

Audited exactly the canonical `waves/pending/W15.md`; it is present and
unambiguous. Re-read `30_AUDIT_WAVE.md`, `CORE_EXECUTION_RULES.md`, all 14
W15 registry rows, the W15 index slice, zero W15 TODO rows, Workstream C0 and
Workstream E, the W15 report and raw evidence, current source/tests, current
diff/HEAD, plugin identity, and dependency W14. No `waves/bak/` material was
used. No product or test finding was fixed; only this audit artifact was
written.

## Current repository and dependency truth

- Main repository is `develop`, current HEAD
  `f94adb640136181dbaafa84f62c753b013f0b94e`; the working tree is dirty with
  unrelated lab/report changes and untracked files. Plugin repository is on
  `develop` at `f0abb7e7037e66ab451d463c699fecf4e00c89eb`.
- W15 declares dependency `W14`. The canonical current W14 audit is
  `REOPEN`; it reports stale package/final-SHA evidence and an unresolved W13
  dependency. W15 is therefore not dependency-eligible for close.
- The W15 report/evidence are bound to main SHA
  `0f8902a023bac76071527232c2287af96478ed2b`, not current HEAD. W15-owned
  implementation/test paths differ between that identity and current HEAD
  (`git diff 0f8902a..HEAD` shows changes in `paths.py`, `wx_shell.py`,
  `wx_packaged_smoke.py`, and `test_w15_fresh_user_startup.py`). This is a
  behavior-affecting history change and invalidates the prior audit/evidence.

## Independent verification

- `python -m pytest tests/test_w15_fresh_user_startup.py -q` → **11 passed**.
  This does not substitute for current exact-package GUI/PACKAGE proof.
- The cited evidence file exists and reports `result=PASS`, 10/10 checks,
  exit codes `[0,0]`, and artifact SHA
  `d2aab99d998a1dd0d912098f319f9bbf6c227ba0b4b82c9db9303bcf6c863cfd`, but its
  identity header remains bound to obsolete main SHA `0f8902a...`.
- Independent current disk hashing gives the available
  `dist/hpc-client-gui/hpc-client-gui.exe` SHA
  `ff050baf26fd73f59d46c6a7ed5290913e1669b67cecbbfa13bb29e5c0122876`,
  which does not match the evidence SHA. The accepted artifact is therefore
  not the current exact artifact and final-SHA/package parity is not proven.
- W15 requires GUI and PACKAGE only. Its loopback fixture is not EXTERNAL
  evidence, so `LOCAL_REAL_HPC_LAB.md` is not applicable; no private-key bytes
  were read.
- `git diff --check` was run; existing trailing whitespace is present in
  unrelated prior audit reports. No W15 test weakening, skip, or xfail was
  accepted.

## Findings

### REOPEN-W15-001 — PACKAGE/GUI evidence is stale against current identity

The sole accepted PKG-GJ-01 evidence is bound to main SHA `0f8902a...` and
artifact SHA `d2aab99d...`, while live repository truth is
`f94adb640136181dbaafa84f62c753b013f0b94e` and the artifact currently present
on disk hashes to `ff050baf...`. W15-owned behavior paths also changed after
the evidence identity. Rebuild the exact package from the current accepted
main/plugin identities, rerun the required solo GUI fresh-user flow, and
produce fresh evidence with matching artifact and final-SHA identity.

### REOPEN-W15-002 — Dependency W14 is currently reopened

W15 depends on W14, whose canonical audit is currently `REOPEN` for stale
package/final-SHA evidence and an unresolved prerequisite chain. W15 cannot
close until dependency truth is repaired and freshly audited; downstream
evidence must then be revalidated as needed.

## Verdict

The focused W15 unit suite is green, but the mandatory GUI/PACKAGE evidence is
not current or bound to the live final identity, and the declared dependency is
reopened. These are repository/evidence findings, not unavailable external
authority. Do not close W15 until the findings are repaired and a fresh
independent audit is performed.

WAVE_PHASE_STATUS: REOPEN
