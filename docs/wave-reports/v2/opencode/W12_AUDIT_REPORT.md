# W12 Audit Report

**Decision: REOPEN**

Audited exactly `W12` against canonical `waves/pending/W12.md` and
`.opencode/prompts/30_AUDIT_WAVE.md`. The pending definition is present and
unambiguous; `waves/bak/` was not used.

## Authority and current truth

- Read the core rules, W12 contract, all 15 owned registry rows
  `HPC-W03-SFTP-001..015`, the W12 index, mandatory Workstream B, W12
  report/audit, current source/tests, dependency report, and current diff.
- Main repository: `develop`, HEAD
  `f94adb640136181dbaafa84f62c753b013f0b94e`.
- The W12 report and prior audit claim tested/current SHA
  `0f8902a023bac76071527232c2287af96478ed2b`. W12 implementation and tests
  were subsequently committed in snapshot `f3680984`; the current HEAD is
  later still. Prior audit/evidence therefore cannot be accepted as current.
- Current focused checks pass: `python -m pytest
  tests/test_w12_sftp_semantics.py -q` → **13 passed**; W12 + W11 focused
  checks → **27 passed**. These do not refresh external evidence.
- The working tree is dirty with unrelated changes. No product/test change
  was made by this audit.

## Findings

### REOPEN-W12-001 — external evidence uses the wrong environment

`EV-W12-EXT-001` was run against `127.0.0.1:2222`, a containerized `hpclab`
environment. `.opencode/protocol/LOCAL_REAL_HPC_LAB.md` requires LOCAL_REAL
by default for this generic real SFTP requirement: `LOCAL_REAL_HYPERV`,
controller `192.168.250.11:22`, profile/provider `local-real`, and SSH-key
authentication. The emitted profile JSON was inspected for identity only;
private-key bytes were not read.

Current `lab-status.ps1` independently reports LOCAL_REAL `PASS`, healthy
services, idle compute nodes, valid image pin, and a valid emitted profile.
That proves the environment is available, but does not prove W12. No current
W12 raw evidence artifact proves all 15 requirements against LOCAL_REAL or
binds the run to current HEAD/worktree identity. Re-run the complete W12
GUI/EXTERNAL acceptance against LOCAL_REAL, recording exact requirement IDs,
identity, and cleanup, then audit again.

### REOPEN-W12-002 — stale report and dependency identity

The W12 report, prior audit, and W11 dependency report retain the obsolete
`0f8902a...` identity while repository truth is `f94adb6...`. Reconcile the
canonical W12 report and evidence provenance after the LOCAL_REAL replay.

## Verdict

The implementation-focused tests are green and no new product defect was
asserted. Mandatory EXTERNAL evidence is stale, uses the wrong environment
identity, and is not bound to current repository truth. W12 is not eligible
for closeout until evidence/report refresh and a fresh independent audit.

WAVE_PHASE_STATUS: REOPEN
