# W12 Audit Report

**Decision: PASS**

Audited exactly `W12` against canonical `waves/pending/W12.md` and
`.opencode/prompts/30_AUDIT_WAVE.md`. The pending definition is present and
unambiguous; `waves/bak/` was not used.

## Authority and current truth

- Read the core rules, W12 contract, all 15 owned registry rows
  `HPC-W03-SFTP-001..015`, the W12 index, mandatory Workstream B, W12
  report/audit, current source/tests, dependency report, and current diff.
- Main repository: `develop`, HEAD
  `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`.
- Repair refreshed the canonical W12 report and current raw evidence identity.
- `lab/lab-status.ps1` → PASS for `LOCAL_REAL_HYPERV`.
- `W12_REPO_HEAD=63b696b3b8c64296d9d17f94c8d0d903f9bab7eb python .tmp/probes/w12_local_real_replay.py` → **14/14 PASS**, cleanup verified.
- Focused regression: `python -m pytest tests/test_w12_sftp_semantics.py tests/test_wave3_remote_sftp_ssh.py tests/test_sftp_channel_manager.py -q` → **54 passed**.
- The working tree is dirty with unrelated changes. No product/test change
  was made by this audit.

## Findings

### REOPEN-W12-001 — resolved by repair

`EV-W12-EXT-001` was run against `127.0.0.1:2222`, a containerized `hpclab`
environment. `.opencode/protocol/LOCAL_REAL_HPC_LAB.md` requires LOCAL_REAL
by default for this generic real SFTP requirement: `LOCAL_REAL_HYPERV`,
controller `192.168.250.11:22`, profile/provider `local-real`, and SSH-key
authentication. The emitted profile JSON was inspected for identity only;
private-key bytes were not read.

The repair reran the complete W12 matrix against `LOCAL_REAL_HYPERV`
(`192.168.250.11:22`, `local-real`, emitted SSH-key profile), recorded all
owned requirement IDs, bound the raw artifact to current HEAD/worktree truth,
and verified disposable-root cleanup. The new artifact is
`.tmp/probes/W12_LOCAL_REAL_EXTERNAL.json` (`EV-W12-EXT-003`).

### REOPEN-W12-002 — resolved by repair

The canonical W12 report now records current HEAD
`63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`, the current replay timestamp,
focused validation, and `EV-W12-EXT-003`. W11/dependency history is not a W12
owner and was not modified.

## Verdict

Repair is complete with no new product defect. The fresh independent audit
accepted the current evidence/report package; W12 is ready for serial closeout.

WAVE_PHASE_STATUS: PASS
