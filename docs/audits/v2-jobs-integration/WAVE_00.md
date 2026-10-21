# WAVE 00 — Repository and Architecture Foundation

Status: **IN PROGRESS**. The complete starting baseline is described in [WAVE_00_ARCHITECTURE_BASELINE.md](WAVE_00_ARCHITECTURE_BASELINE.md).

## Starting state

- Starting integration commit: `f61919bad12be5f328cb9db3fee3c8de8563fa5b`.
- Local `develop` was clean but checked out in another worktree, so this wave uses isolated branch `codex/integration/v2-jobs-staged-20261021`.
- Main user checkout changes and V2 dirty source were preserved; V2 tracked/untracked changes were copied to `D:\Projeler\.tmp\hpc-client-gui\v2-wip-snapshot-20261021` and fingerprinted.
- Branch heads, merge bases, live remote advertisements, and divergence counts are recorded in [BRANCH_SOURCE_MAP.md](BRANCH_SOURCE_MAP.md).

## Changes in this wave

- Added `scripts/check_source_architecture.py`, which calls the shared Agent Core LOC validator rather than copying it, then checks internal imports, new cycles, and public exports in the selected facade modules.
- Added focused architecture gate tests and a required architecture job to `.github/workflows/ci.yml`. The CI job checks out shared Agent Core at immutable commit `2dfa726973194305f63b62477a286037f5c0642d`, enforces changed-source LOC, runs the new tests, and publishes the Markdown result to the job summary.
- Recorded the original `develop` source baseline and V2 WIP source manifest. The baseline is not a PASS report: it has 52 LOC violations, 8 pre-existing cycles, and 2 unresolved internal symbol imports.

## Evidence

- Focused tests: 5 passed, exit 0, using the project `.venv`.
- `py_compile`: exit 0 for the new checker and test.
- Changed-source gate against starting SHA: pending final rerun after baseline source correction.
- Full starting architecture check: FAIL, exit 1, with 52 baseline LOC violations. The WAVE 00 working tree still has those 52, the same 2 pre-existing unresolved imports, 8 cycles, and 0 API errors. These are recorded as baseline debt, not acceptance.
- GitHub Actions has not run.

## Completion condition

Before committing WAVE 00, verify the report outputs, rerun the focused suite and changed-source gate, and capture the exact source fingerprint. No wave is marked complete until that checkpoint is committed.
