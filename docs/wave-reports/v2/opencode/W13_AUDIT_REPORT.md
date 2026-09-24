# W13 Audit Report

**Decision: REPAIR COMPLETE — FRESH AUDIT REQUIRED**

This is the repair handoff for exactly `W13`; it is not an independent audit
and does not claim `PASS`. W14 was not started.

## Authority and current truth

- Re-read `.opencode/prompts/30_AUDIT_WAVE.md`, the core protocol, the W13
  contract, all 55 owned registry rows, the W13 index, and every mandatory
  section of `opencode/sources/WAVE_V2_FINAL_03.md`.
- Re-read the canonical W13 report, current implementation and test source,
  current diff/status, dependency audit, and available lab evidence.
- Main repository is `develop` at
  `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`.
- Plugin repository is `develop` at
  `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; its unrelated untracked
  `.github/social-preview.jpg` was not inspected as evidence.
- The W13 report and this handoff now cite the current HEAD. The working tree
  remains dirty with unrelated changes; only W13 reports and `.tmp` replay
  evidence were changed in repair.

## Independent checks

- `python -m pytest tests/test_w13_slurm_state.py -q` → **14 passed**, exit 0.
- Current source inspection confirms the parser and empty-success changes are
  present, and the W13 test module contains behavioral assertions, not skips
  or xfails. Green unit/GUI-support tests do not refresh EXTERNAL evidence.
- Current `lab/evidence/health.json` identifies healthy `LOCAL_REAL_HYPERV`
  at `192.168.250.11`, with valid emitted profile path/hash and idle Slurm
  compute nodes. No private-key bytes were read.

## Repair disposition

### REOPEN-W13-001 — addressed

W13 is a generic real SSH/SFTP/Slurm requirement; it does not name a site.
`.opencode/protocol/LOCAL_REAL_HPC_LAB.md` therefore requires the verified
LOCAL_REAL lab by default and explicitly disallows loopback/mock support as a
substitute. The canonical W13 evidence instead runs against the containerized
`hpclab` at `127.0.0.1:2222` (environment class `local containerized
single-node Slurm`, password fixture). That evidence cannot satisfy the W13
EXTERNAL class under the current protocol, even though the current LOCAL_REAL
health truth is available and healthy.

`python .tmp/w13_local_real_replay.py` ran the real product path against
`LOCAL_REAL_HYPERV` (`local-real`, `192.168.250.11:22`, emitted SSH-key
profile) and passed connect, submit/query/output, invalid-job failure,
permission denial, cancellation/accounting, reconnect and cleanup. The old
loopback artifacts are historical context only.

### REOPEN-W13-002 — addressed

The canonical report and this handoff now bind to current HEAD
`63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`; no product/test files changed.

### REOPEN-W13-003 — resolved in current dependency truth

The current W12 audit is `PASS` with its own LOCAL_REAL replay. W12 was not
modified by this W13 worker.

## Durable evidence refresh

The repair generated `.tmp/probes/W13_LOCAL_REAL_EXTERNAL.json` for
`EV-W13-EXT-003` and refreshed `lab/evidence/LOCAL_REAL_TEST.json` for
`EV-W13-EXT-004`. Both retain current environment identity, command/result
data, cleanup status, and requirement bindings/checks; the replay exited `0`
and the lab ledger reports `LOCAL_REAL_READY` with `23/23` checks.

## Verdict

Repair is complete. `EV-W13-EXT-003` is the current LOCAL_REAL replay identity,
bound to the current HEAD and explicitly mapped to the W13 requirement IDs in
the canonical wave report. `EV-W13-EXT-004` is the current LOCAL_REAL lab
baseline for SFTP/hash/fixture evidence. The prior loopback evidence is
historical only. Focused validation remains 14 passed. Fresh independent audit
must verify the refreshed evidence and GUI evidence before close.

WAVE_PHASE_STATUS: READY_FOR_AUDIT
