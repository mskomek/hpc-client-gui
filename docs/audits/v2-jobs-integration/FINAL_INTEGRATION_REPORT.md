# Final Integration Report — V2 + Jobs

## Current result

VM release acceptance and platform package checks passed for the exact r17 source overlay. The integration code is committed locally on `codex/integration/v2-jobs-staged-20261021`; the local `develop` branch remains at its tested base because its separate checkout contains the r17 validation overlay and unrelated untracked files.

**Current checkpoint: `READY_FOR_DEVELOP_MERGE`.** This records a merge-ready local integration branch, not a claim that the r17 commit has already been merged into `develop`. No push, PR, GitHub Release, or GitHub Actions run occurred.

## Source and branch state

- Validation base / current local `develop`: `48ac62334b398bbc95b4d14ca9ef23dc83c356f3`.
- r17 source commit/tree: `5861ec6b296e8a48236aaa72c87abe9ec59edd4f` / `de8b888771db5ba71d74278d5f3598e5481e5942`.
- r17 overlay fingerprint: `325593c807cab38278a93b45986f38ac3152c426421084780bc06ef99c201765` (39 files); archive SHA-256 `aafce9d620856696318fd7f7438449f6c2b0cd552d35aa147c7662038fbfb986`.
- Jobs source SHA: `713949fb752b90601e007812ebf2bd765da5ad52`.
- V2 source SHA: `c0c6d0e956c9283f0c05f25b799e1b1f57ecb240`.
- `origin/develop` tracking ref is `d91c84f1d784fd3391bf132a54134faef44e63c9`; it was not modified.
- The main user checkout and V2 WIP source were preserved. Branch/worktree details are in [the source map](BRANCH_SOURCE_MAP.md).

## Acceptance summary

| Area | Result |
|---|---|
| Global architecture | PASS: 1,020 Python files; 0 over 500 lines; 0 dependency/API/cycle errors |
| Ruff | PASS on Ubuntu-Test and Windows11-New |
| Linux release suite | PASS: 3,506 passed, 0 failed, 33 skipped, 46 deselected; exit 0 |
| Linux GUI/Xvfb/D-Bus | PASS: 3,477 passed plus 29 subtests, 0 failed; 69.56% coverage against 65% floor |
| Windows release acceptance | PASS: 3,504 passed plus 29 subtests, 0 failed, 35 skipped, 46 deselected; exit 0 |
| Windows package | PASS: build, GUI/CLI smoke, guide coverage, and mocked transfer gate |
| Ubuntu packages | PASS: AppImage, Debian, and Flatpak build/checksum/launcher smoke; cleanup verified |
| GitHub Actions | NOT RUN; no hosted CI result is claimed |

Test counts are reported per run, not added into a unique total, because GUI and release suites overlap. See [the test matrix](TEST_MATRIX.md) and [r17 VM record](VM_ACCEPTANCE_2026-10-24.md) for commands, skips, warnings, exit files, and log hashes.

## Architecture and parity

The historical baseline contained 52 first-party Python files above 500 physical lines. The latest full VM architecture scan covers 1,020 Python files with zero over-limit files, zero dependency/API errors, and zero cycles. The baseline allowlist was removed earlier; there is no active LOC exception. Jobs persistence/history/workspace behavior and the Qt/wx parity contracts remain covered by the existing wave regressions and the final release runs.

The r17 overlay changes 38 Python files plus one PowerShell source file; it adds one application module (`wx_shell_notebook.py`), one test-support module, and two focused test modules. The four added files are included in the 39-file source identity manifest.

## Artifacts

| Artifact | SHA-256 |
|---|---|
| Windows onedir ZIP | `cd1de871ca0d2c53220e39329f3b65e7008d342a06817e5b4bbf85d50218503a` |
| Linux AppImage | `dd4ac4d7c460744d085593717cd09d5cd532a8e5b09b1780c44922be9827e75f` |
| Linux Debian package | `d9df05ce86b49246b2aecf54dc13d927c35db7ff96632c6ee904ce31dc1bce1b` |
| Linux Flatpak | `2f51e5812acab18ee3df5205b3da539a468d71f95b7e3121d02d827c1b1bd1d3` |

All four artifacts were built from the base SHA plus the r17 overlay fingerprint recorded above. Non-fatal warnings are retained in the VM record: Ubuntu SQLite `ResourceWarning`s and Flatpak document-portal/FUSE messages, plus Windows wx shutdown diagnostics. The relevant commands still exited 0 and the smoke checks completed.

## Commits and pending action

- r17 source commit `5861ec6b296e8a48236aaa72c87abe9ec59edd4f` is locally committed on the isolated integration branch.
- Local `develop` remains at `48ac62334b398bbc95b4d14ca9ef23dc83c356f3`; merging r17 into it is pending because that branch is checked out in a separate worktree with existing dirty validation files. That worktree was preserved.
- The documentation checkpoint is committed separately after the source commit. The current report checkpoint SHA is provided in the task completion summary; this report avoids a self-referential commit hash.
- No changes were pushed or made to any remote.
