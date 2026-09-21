# W13 Audit Report

**Decision: REOPEN**

Fresh independent audit of exactly `W13` against `waves/pending/W13.md`.
`waves/bak/` was not used and W14 was not started.

## Authority and current truth

- Re-read `.opencode/prompts/30_AUDIT_WAVE.md`, the core protocol, the W13
  contract, all 55 owned registry rows, the W13 index, and every mandatory
  section of `opencode/sources/WAVE_V2_FINAL_03.md`.
- Re-read the canonical W13 report, current implementation and test source,
  current diff/status, dependency audit, and available lab evidence.
- Main repository is `develop` at
  `f94adb640136181dbaafa84f62c753b013f0b94e`.
- Plugin repository is `develop` at
  `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; its unrelated untracked
  `.github/social-preview.jpg` was not inspected as evidence.
- The W13 report/evidence claim main SHA
  `0f8902a023bac76071527232c2287af96478ed2b`, which is no longer current.
  Repository history advanced through subsequent commits, including the
  W13 implementation snapshot. The working tree is also dirty with unrelated
  lab/report changes; no files were changed by this audit.

## Independent checks

- `python -m pytest tests/test_w13_slurm_state.py -q` → **14 passed**, exit 0.
- Current source inspection confirms the parser and empty-success changes are
  present, and the W13 test module contains behavioral assertions, not skips
  or xfails. Green unit/GUI-support tests do not refresh EXTERNAL evidence.
- Current `lab/evidence/health.json` identifies healthy `LOCAL_REAL_HYPERV`
  at `192.168.250.11`, with valid emitted profile path/hash and idle Slurm
  compute nodes. No private-key bytes were read.

## Findings

### REOPEN-W13-001 — mandatory EXTERNAL evidence uses the wrong environment

W13 is a generic real SSH/SFTP/Slurm requirement; it does not name a site.
`.opencode/protocol/LOCAL_REAL_HPC_LAB.md` therefore requires the verified
LOCAL_REAL lab by default and explicitly disallows loopback/mock support as a
substitute. The canonical W13 evidence instead runs against the containerized
`hpclab` at `127.0.0.1:2222` (environment class `local containerized
single-node Slurm`, password fixture). That evidence cannot satisfy the W13
EXTERNAL class under the current protocol, even though the current LOCAL_REAL
health truth is available and healthy.

Re-run the complete W13 external acceptance against LOCAL_REAL, including the
Slurm lifecycle, failure/recovery and state-coherency scenarios, and bind raw
evidence to `LOCAL_REAL_HYPERV`, the emitted profile/provider identity, exact
W13 requirement IDs, cleanup, and the current main/plugin identities. Do not
read or record private-key bytes.

### REOPEN-W13-002 — stale evidence/report identity

The W13 report, audit, and all cited W13 external artifacts are bound to
`0f8902a...`, while live repository truth is `f94adb6...`. A later repository
history change invalidates those prior audit/evidence claims under the Wave
contract. The report must be reconciled after the LOCAL_REAL replay and a
fresh audit must follow.

### REOPEN-W13-003 — dependency is not currently GO

W13 depends on W12. The current W12 audit is `REOPEN` for the same stale
containerized external evidence and obsolete SHA identity. W13 therefore
cannot close until W12's dependency truth is repaired and re-audited, in
addition to refreshing W13's own evidence.

## Verdict

The implementation-focused W13 tests pass, but mandatory EXTERNAL evidence is
not bound to the required LOCAL_REAL environment, is stale against current
repository identity, and its W12 prerequisite is reopened. This is a
repository/evidence repair finding, not an unavailable external blocker;
LOCAL_REAL is currently reported healthy.

WAVE_PHASE_STATUS: REOPEN
