# WAVE_19 / DS-19A implementation

Goal: add the existing offline unit and integration test suite as a strict CI gate.

Allowed files: `.github/workflows/ci.yml` only.

Implement the smallest change supported by the analysis: install pytest in the CI job, then run `python -m pytest tests/ -q --tb=short -rf` with `PYTHONPATH: src`. Preserve the existing compile, i18n, and smoke steps.

Forbidden: application source changes, new dependencies beyond pytest, external environment actions, release publication, and unrelated workflow refactors.

Acceptance: the workflow remains valid YAML, the suite step uses the repository-root invocation and source path setup, failures remain visible, and no other file changes are made. Run a focused syntax or YAML validation available in the worktree and report its exact result.
