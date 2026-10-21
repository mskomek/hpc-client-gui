# WAVE 00 — Repository and Architecture Foundation

Status: **WAVE_COMPLETE**. The complete starting baseline is described in [WAVE_00_ARCHITECTURE_BASELINE.md](WAVE_00_ARCHITECTURE_BASELINE.md).

## Starting state

- Starting integration commit: `f61919bad12be5f328cb9db3fee3c8de8563fa5b`.
- Wave source commit: `718fbd01296793b513526adabedd3e48deea2d4a` (`chore(architecture): establish staged 500-line enforcement`).
- Wave source tree: `bc4297dce73099e4003a93d52d66247b6ecba719`.
- Fingerprint of 30 files changed by this wave (sorted path + SHA-256): `37be9c808f09d80dc5763520d19d8ee756c8cfa2b8ccc20f919f4fb9256f7a07`.
- Local `develop` was clean but checked out in another worktree, so this wave uses isolated branch `codex/integration/v2-jobs-staged-20261021`.
- Main user checkout changes and V2 dirty source were preserved; V2 tracked/untracked changes were copied to `D:\Projeler\.tmp\hpc-client-gui\v2-wip-snapshot-20261021` and fingerprinted.
- Branch heads, merge bases, live remote advertisements, and divergence counts are recorded in [BRANCH_SOURCE_MAP.md](BRANCH_SOURCE_MAP.md).

## Changes in this wave

- Added `scripts/check_source_architecture.py`, which calls the shared Agent Core LOC validator rather than copying it, then checks internal imports, new cycles, and public exports in the selected facade modules.
- Added focused architecture gate tests and a required architecture job to `.github/workflows/ci.yml`. The CI job checks out shared Agent Core at immutable commit `2dfa726973194305f63b62477a286037f5c0642d`, enforces changed-source LOC, runs the new tests, and publishes the Markdown result to the job summary.
- Recorded the original `develop` source baseline and V2 WIP source manifest. The baseline is not a PASS report: it has 52 LOC violations, 8 pre-existing cycles, and 2 unresolved internal symbol imports.

## Evidence

- Focused tests: `python -m pytest tests/test_source_architecture_gate.py -q` — 5 passed, exit 0, using the project `.venv`.
- Ruff: `python -m ruff check scripts/check_source_architecture.py tests/test_source_architecture_gate.py` — passed, exit 0.
- `py_compile`: `python -m py_compile scripts/check_source_architecture.py tests/test_source_architecture_gate.py` — passed, exit 0.
- Changed-source gate against starting SHA: `python scripts/check_source_architecture.py --mode gate --base f61919bad12be5f328cb9db3fee3c8de8563fa5b` — passed, exit 0; 779 Python files scanned, 52 baseline files remain over 500 lines.
- Full project architecture check: FAIL, exit 1, with 52 baseline LOC violations, the same 2 pre-existing unresolved imports, 8 cycles, and 0 API errors. These are recorded as baseline debt, not acceptance.
- GitHub Actions has not run.

## Completion condition

The implementation and evidence checkpoint is committed. A documentation-only closeout commit records this verified report; it does not change the wave source tree or its fingerprint.
