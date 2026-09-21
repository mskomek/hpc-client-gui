# W11 Audit Report — fresh-context audit

Wave: `W11`  
Subject: `docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md`  
Audit date: 2026-09-21
Auditor: GPT-5.6 Luna (`openai/gpt-5.6-luna`)

## Verdict

**REOPEN**

## Authority and scope

- Audited exactly `waves/pending/W11.md`; it is present and unambiguous. No
  `waves/bak/` material was used.
- Re-read `CORE_EXECUTION_RULES.md`, `LOCAL_REAL_HPC_LAB.md`, all eleven
  `HPC-W03-SSH-001..011` registry rows, `TODO_OWNERSHIP_MAP.md`, and
  Workstream A of `opencode/sources/WAVE_V2_FINAL_03.md`. W11 owns no TODO
  detail rows. Required evidence classes are `GUI,EXTERNAL`.
- Workstream A requires valid/unreachable/invalid-auth SSH, first-contact and
  mismatch host-key behavior, idle and in-operation disconnect, reconnect,
  repeated lifecycle, Unicode, and truthful post-transport-failure UI state.

## Blocking findings

### FND-W11-AUDIT-002 — prior audit/evidence is stale against current repository

The subject report binds its implementation and evidence to main SHA
`0f8902a023bac76071527232c2287af96478ed2b`, but current repository HEAD is
`f94adb640136181dbaafa84f62c753b013f0b94e`. The reported SHA is not an
ancestor of current HEAD. The range contains broad behavior/source/test and
lab changes, including changes to `src/hpc_gui/wx_connection.py`,
`src/hpc_gui/services/connection_controller.py`, and
`tests/test_w11_ssh_lifecycle.py`. Therefore the earlier W11 audit and its
final-SHA/evidence claims cannot be accepted for the current tree; a fresh
audit/evidence capture is required after the current integration state is
established.

Current focused test replay was run independently:

```text
python -m pytest -q tests/test_w11_ssh_lifecycle.py
14 passed, exit 0
```

This is supporting current-tree test truth only and does not cure stale
external evidence or bind the GUI/external acceptance claims to the current
repository identity.

### FND-W11-AUDIT-003 — EXTERNAL evidence uses the wrong generic lab identity

W11 is generic real SSH lifecycle validation and does not name `hpclab`,
TRUBA, or another site. Under `LOCAL_REAL_HPC_LAB.md`, generic EXTERNAL
evidence must use and identify LOCAL_REAL by default when it satisfies the
requirement. The prior report instead accepts `EV-W11-EXT-001` against a
container at `127.0.0.1:2222` with password authentication and records it as
the accepted external environment. That is not the declared LOCAL_REAL
environment and is not current evidence for the changed repository.

Independent current lab verification found LOCAL_REAL available and healthy:

- `lab/lab-status.ps1`: `PASS`;
- environment identity: `LOCAL_REAL_HYPERV`, controller
  `192.168.250.11:22`, profile ID `local-real`, user `hpctest`;
- generated profile path inspected (no private-key bytes read), profile valid;
- controller and both compute-node transports/services: PASS;
- Slurm nodes `compute01` and `compute02`: `idle`;
- status timestamp: `2026-09-21T14:16:33.8060327Z`.

Because the verified LOCAL_REAL lab truthfully satisfies this generic SSH
requirement, an old alternate-container result must not be preserved as the
accepted EXTERNAL evidence or as `EXTERNAL_BLOCKED`. Re-run the W11 external
matrix against LOCAL_REAL, including environment identity, current repository
HEAD/worktree identity, owned requirement IDs, and cleanup. GUI evidence must
also be refreshed against the current implementation state.

## Current diff and safety review

The working tree is dirty with unrelated user/repository changes, including
lab files, reports, and an untracked `new 4.ps1`; these were not modified.
`git diff --check` reported pre-existing trailing whitespace in other audit
reports and CRLF notices. No product/test changes were made by this audit.
The current W11 focused test is green, but that result is insufficient to
accept a stale SHA-bound external/GUI evidence set.

## Required resume actions

1. Reconcile the W11 implementation/test state at current HEAD and record the
   exact current main/plugin identities.
2. Replay all W11 EXTERNAL scenarios against declared LOCAL_REAL without
   reading or copying private-key contents; inspect only the emitted profile
   path/metadata as needed.
3. Refresh real wx GUI semantic evidence and bind all evidence to current
   HEAD/worktree identity.
4. Run a fresh independent W11 audit after those evidence/report updates.

No product or test finding was repaired by this audit.

WAVE_PHASE_STATUS: REOPEN
