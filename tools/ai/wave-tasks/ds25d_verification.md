# DS-25D — Verification and stale-reference review (Wave 25)

DS-25B/DS-25C already landed (committed on this worktree branch): LICENSE
replaced with PolyForm Noncommercial 1.0.0, COMMERCIAL_LICENSE.md and
THIRD_PARTY_NOTICES.md added, README licensing section, pyproject metadata,
version bumped to 1.2.0 everywhere, docs/CHANGELOG.md licensing section,
dist/hpc-client-cli untracked. Do not redo that work.

## Task (verification only, do not change licensing content)

1. Run the existing test suite, compile/import checks, and lint/static checks
   the project already defines: `python -m pytest tests/ -q --tb=short -rf
   --ignore=tests/test_runner_ollama.py`, `python -m compileall
   src/truba_gui`, and `python scripts/smoke_test.py` (set PYTHONPATH=src as
   needed). Record exit codes.

2. Run `scripts/check_release_consistency.ps1 -Version 1.2.0` and
   `scripts/test_release_consistency.ps1`. Record output and exit codes.

3. Perform a full local dry build: `scripts/release.ps1 -Version 1.2.0`.
   After it completes, verify `LICENSE`, `COMMERCIAL_LICENSE.md`, and
   `THIRD_PARTY_NOTICES.md` are present inside both the GUI and CLI release
   zips under `dist/releases/v1.2.0/` and inside both `_internal` bundle
   directories. Record the exact paths checked.

4. Search the entire repository (tracked files, excluding
   `dist/releases/` and `.agent-runs/`) for stale `MIT`, `license`,
   `copyright`, `SPDX`, `OSI` references. Classify each hit as either
   "intentional historical reference" (e.g. changelog entries describing past
   MIT releases, this wave's own PolyForm text mentioning the MIT boundary)
   or "stale — needs a follow-up fix". Report both lists.

5. Confirm no dependency license changed: diff `pyproject.toml` dependency
   version constraints against the pre-wave baseline (git show
   42c40f3:pyproject.toml) and confirm only `license`/`authors`/`version`
   fields differ, not the `dependencies` list.

6. Run `git diff --check` and `git status --short` in this worktree and
   report the output verbatim.

7. Produce an explicit list of old GitHub releases/assets that could be
   considered for removal later (read-only inspection of existing release
   tooling/config only — do not query GitHub's API or perform any GitHub
   action). Note this is informational only.

## Output

A structured verification report covering all seven points above with exact
commands run, exit codes, and file paths checked.

## Allowed

Running the listed local/offline commands (including the release dry build,
which produces new files under `dist/releases/v1.2.0/` — that is expected
output, not a forbidden edit) and reading repository files. Local build
output under `dist/` is expected and fine.

Forbidden: weakening or skipping any test, changing LICENSE/COMMERCIAL_LICENSE/
THIRD_PARTY_NOTICES/README licensing content, any live remote-cluster or file
transfer operation, publishing/deleting/rewriting anything on GitHub, and any
commit, stage-beyond-required, or push.
