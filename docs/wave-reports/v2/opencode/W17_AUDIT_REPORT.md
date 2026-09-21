# W17 Audit Report

```text
Wave: W17
Audit cycle: 4
Decision: REOPEN
Auditor: GPT-5.6 Luna (openai/gpt-5.6-luna), reasoning medium
Audit date: 2026-09-21 UTC
Authority: waves/pending/W17.md only
```

## Scope and authority read

Audited exactly the canonical `waves/pending/W17.md`; it is present and
unambiguous. Re-read `30_AUDIT_WAVE.md`, `CORE_EXECUTION_RULES.md`, all 14
W17 registry rows, the W17 index, zero W17 TODO rows, and the mandatory
`WAVE_V2_FINAL_05.md` Workstream 0. Re-read the W17 report, current profile
implementation/tests, raw GUI/service evidence, current diff/HEAD, and the
dependency audit chain. `waves/bak/` was not read. No product or test finding
was fixed; only this audit artifact was written.

## Current repository and dependency truth

- Main repository is `develop` at current HEAD
  `f94adb640136181dbaafa84f62c753b013f0b94e`. The working tree is dirty with
  unrelated lab, report, and untracked-file changes. The W17 report instead
  records implementation/evidence identity `0f8902a023bac76071527232c2287af96478ed2b`.
- W17 depends on W16. The canonical current W16 audit is `REOPEN`: its
  mandatory package/final-SHA evidence is bound to obsolete main SHA
  `0f8902a...` and does not match the current artifact; W16 also reports its
  dependency W15 as reopened. W17 is therefore not dependency-eligible for
  close.
- W17 evidence is GUI-only as required; no EXTERNAL evidence is claimed, so
  `LOCAL_REAL_HPC_LAB.md` is not applicable and no private-key bytes were read.
- The current W17 implementation contains the reported rename-collision guard
  and Add-path stable-ID synchronization. The focused current profile suite
  was independently run: `61 passed` (exit 0). This does not override the
  unresolved dependency or stale identity findings.

## Independent evidence verification

- The cited GUI raw evidence exists, is non-empty, reports exit 0 and overall
  true with 17/17 real-wx event steps passing. The service before/after probes
  also exist and are non-empty.
- The evidence/report identity is not current: the report binds the tested
  implementation to `0f8902a...`, while live HEAD is `f94adb64...`. The current
  repository has advanced since the accepted W17 evidence, and the report does
  not provide a fresh evidence binding to the current final identity.
- `git diff --check` was run. Reported whitespace is in unrelated existing
  files; no W17 product/test change was made by this audit.

## Findings

### REOPEN-W17-001 — Declared dependency W16 is currently reopened

W17 declares W16 as its dependency. W16's canonical audit is `REOPEN` for
stale package/final-SHA evidence and its reopened W15 dependency. W17 cannot
close until the dependency chain is repaired, freshly audited, and any
invalidated downstream evidence is refreshed.

### REOPEN-W17-002 — W17 GUI evidence is stale against current repository identity

The W17 report and raw GUI/service evidence identify main SHA
`0f8902a023bac76071527232c2287af96478ed2b`, while live repository truth is
`f94adb640136181dbaafa84f62c753b013f0b94e`. Although the current focused
profile tests pass and the W17 implementation paths are present, the required
GUI proof is not freshly bound to the current accepted identity. After the
dependency repair, rerun the W17 GUI matrix and service checks as needed and
record evidence bound to the current final identity, then perform a fresh
independent audit.

## Verdict

The current focused profile suite is green and the implementation appears to
cover the 14 owned requirements, but W17 is not closeable while W16 is
reopened and W17's accepted GUI evidence remains bound to an obsolete SHA.
These are repository/evidence and dependency findings, not unavailable
external authority.

WAVE_PHASE_STATUS: REOPEN
