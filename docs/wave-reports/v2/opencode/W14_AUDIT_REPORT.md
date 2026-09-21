# W14 Audit Report

```text
Wave: W14
Decision: REOPEN
Auditor: GPT-5.6 Luna (openai/gpt-5.6-luna)
Audit date: 2026-09-21 UTC
Authority: waves/pending/W14.md
```

## Scope and authority read

Audited exactly the canonical `waves/pending/W14.md`; it is present and
unambiguous. Re-read the audit prompt, core execution rules, all eight W14
registry rows, the W14 index slice, the mandatory Workstream A/B/F source
sections, the W14 report/evidence, current implementation/tests, dependency
truth, current diff/status, and final artifact identity. No `waves/bak/`
material was used. No product or test finding was fixed; only this audit
artifact was updated.

## Current repository and plugin truth

- Main repository: `develop`, HEAD
  `f94adb640136181dbaafa84f62c753b013f0b94e`; working tree dirty with
  unrelated lab/report changes and untracked files.
- Plugin repository: `develop`, HEAD
  `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; only an unrelated untracked
  `.github/social-preview.jpg` was observed.
- The W14 report and candidate artifact identify main SHA
  `0f8902a023bac76071527232c2287af96478ed2b`, not current HEAD. The current
  history contains subsequent changes to W14-owned implementation/test paths
  (`scripts/artifact_identity.py`, `scripts/capture_build_provenance.py`,
  `scripts/generate_release_manifest.py`, `scripts/wx_packaged_smoke.py`,
  and `tests/test_w14_provenance_manifest.py`). This invalidates the old
  package evidence under `HPC-W04-IDENTITY-002`; it cannot be accepted as
  current final-SHA evidence.
- `git diff --check` was run; it reports existing trailing whitespace in
  other audit files, not in this report. No private-key bytes were read.

## Independent verification

- Exact W14 command rerun:
  `python -m pytest tests/test_w14_provenance_manifest.py tests/test_release_manifest.py tests/test_version_consistency.py tests/test_release_surface.py tests/test_sync_version.py tests/test_wave10_release_gate.py tests/test_release_test_suite.py -q`
  → **43 passed, 0 failed, exit 0**.
- Current provenance capture reports main SHA `f94adb64...`, plugin SHA
  `f0abb7e7...`, Python `3.12.4`, Windows/AMD64, and the current dirty
  worktree. This contradicts the candidate manifest's recorded main SHA and
  Python `3.14.0` build identity as a current acceptance identity.
- Candidate wheel hash independently recomputed as
  `3b2849b7916741455aaff47625043ee343b32a921cfb713e8c80bb8c66fcda48`,
  matching its manifest and smoke header, but those records remain bound to
  obsolete main SHA `0f8902a...`.
- The smoke JSON truthfully records `.whl` as unsupported by the wx smoke
  harness; this does not repair the stale package identity.

## Findings

### REOPEN-W14-001 — PACKAGE evidence is stale against current final identity

The required package evidence is bound to main SHA `0f8902a...`, while live
repository truth is `f94adb64...`. Moreover, W14-owned paths changed between
those identities. A matching wheel hash alone does not prove the artifact was
built from the current exact source identity. Rebuild the candidate and
manifest from the current accepted main/plugin identities, rerun the required
package checks, and obtain a fresh audit.

### REOPEN-W14-002 — prerequisite W13 is not currently eligible

W14 declares `W13` as its dependency. The current canonical W13 audit is
`REOPEN` because its mandatory generic EXTERNAL evidence used the wrong
containerized environment and retained the obsolete `0f8902a...` identity.
W12 is likewise currently `REOPEN`, so the dependency chain is not GO. W14
cannot close until the prerequisite truth is repaired and freshly audited.

## Verdict

The implementation-focused W14 suite is green and the existing wheel hash is
internally consistent, but mandatory PACKAGE evidence is stale against live
source/final-SHA identity and the W13 dependency is reopened. These are
repository/evidence repair findings, not an unavailable external blocker.

WAVE_PHASE_STATUS: REOPEN
