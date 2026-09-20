# W13 Audit Report

**Decision: PASS**

Fresh post-repair audit of exactly `W13` against the sole executable contract
`waves/pending/W13.md`. No `waves/bak/` material or W14 work was used.

## Authority and scope

- Re-read `opencode/prompts/30_AUDIT_WAVE.md`,
  `opencode/protocol/CORE_EXECUTION_RULES.md`, and `waves/pending/W13.md`.
- Re-read all 55 owned registry rows (`HPC-W03-SLURM-001..055`); the TODO
  ownership map has no W13 rows.
- Re-read every mandatory W03 source section: Entry criteria, Ownership
  boundary, Scope, Workstreams C/D/E, Test matrix, Acceptance criteria,
  Required evidence, Rollback, and Handoff.
- Re-read the canonical W13 report, W13 regression test, supplemental external
  probe, and routed W11/W12 reports/evidence references.

## Repository and plugin truth

- Main: branch `develop`, SHA
  `0f8902a023bac76071527232c2287af96478ed2b`.
- Plugin: branch `develop`, SHA
  `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; only its pre-existing
  untracked social-preview image is present.
- The W13 implementation diff remains limited to `slurm_models.py`,
  `slurm_ssh.py`, and `tests/test_w13_slurm_state.py`; no product change was
  made during repair cycle 1. Unrelated dirty-tree changes were preserved.
- Scoped full diff and test source were inspected. `git diff --check` is clean;
  no secrets, generated noise, skipped/xfail weakening, or unrelated W13
  change was found.

## Independent verification

- `pytest` focused W13/Slurm/wx/CLI slice: **307 passed**, exit 0.
- Re-ran the authorized real-lab supplemental probe against `hpclab` at
  `127.0.0.1:2222`: **15/15 PASS**, exit 0. It independently confirms
  invalid-credential rejection, two permission-denied cases, two capability
  absence cases, client forced disconnect, stale handle rejection, clean
  reconnect, server-side session kill, recovery, and verified cleanup.
- The canonical report's `EV-W13-EXT-001` / `EV-W13-EXT-001R` evidence remains
  current at the same SHAs: real submit/list/details/output/cancel/accounting,
  SFTP coherency, failures, reconnect/no-stale state, and cleanup (**20/20**).
- Real wx runtime evidence is present in `EV-W13-GUI-001`: real `wx.App`,
  `Frame`, posted button events, worker/event-loop pumping, observable table
  assertions, and teardown. The transport double is correctly identified as
  GUI runtime support, not external-lab evidence.

## Closure review

The repaired canonical trace maps all 55 owned rows requirement-by-requirement
to implementation, tests, and evidence. In particular, rows `017..023` now
have exact `EV-W13-EXT-002` live scenarios, while rows `024..028` and
`037..053` map to exact W13 evidence plus routed W11/W12 evidence at identical
main/plugin SHAs. The prior finding `FND-W13-AUDIT-001` is therefore cured.

GUI and EXTERNAL evidence classes are satisfied; real-lab identity, fixture
confinement, cleanup, environment health, auth method, timestamps, and
secret-safe handling are recorded. Package evidence is correctly N/A under the
Wave contract, with replay scenarios handed to W04. No P0/P1/P2/P3 finding is
open, and no evidence indicates a cross-Wave ownership escape.

## Verdict

`PASS` — W13's 55-row contract, GUI requirement, external requirement,
failure/recovery scenarios, traceability, hygiene, and current diff are
adequately and truthfully evidenced. W14 was not started.
