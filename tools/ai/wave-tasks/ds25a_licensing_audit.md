# DS-25A — Licensing and ownership implementation audit (Wave 25)

Read-only audit. Do not edit, commit, push, or run any release/GitHub action.

## Task

Reconfirm every license, copyright, author, SPDX, README, metadata, packaging,
workflow, release-note, source-header, dependency, and vendored source
reference in this repository. Reconfirm contributor identity evidence from
local Git history only (do not read secrets or rewrite history). Map the
exact list of files that must change to transition the project from MIT to
PolyForm Noncommercial License 1.0.0 for v1.2.0, with copyright holder
`Mehmed Sinan KÖMEK`, and identify any unresolved ownership or
dependency-license blocker.

## Known context

- Current license: MIT, in `LICENSE`.
- Current version: 1.1.21; target: 1.2.0.
- README has a minimal license/contributions section.
- Both `pyproject.toml` files (root and `src/truba_gui/`) lack explicit
  license metadata.
- PyInstaller Windows packaging does not currently bundle license documents.
- Git history may show one human contributor under more than one identity —
  list the distinct author identities and commit counts you find via
  `git log`, do not speculate beyond that.
- Direct dependencies keep their own licenses; note any that impose
  obligations not currently satisfied by packaging.

## Output

A structured report: (1) full file list requiring changes with one-line
reason each, (2) contributor identity summary from git log, (3) dependency
license notice gaps, (4) any blocker requiring a legal/user decision before
DS-25B can proceed.

Allowed: read-only repository, local Git, package metadata, existing release
config. Forbidden: edits, commits, pushes, release/asset operations,
secrets access, real cluster actions.
