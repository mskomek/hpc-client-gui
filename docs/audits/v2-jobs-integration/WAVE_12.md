# WAVE 12 — Final Acceptance and r17 Stabilization

Status: **WAVE_COMPLETE** for the r17 source set. VM acceptance and package gates passed on the exact verified source overlay. The isolated integration branch is ready for a safe local merge to `develop`; the `develop` worktree itself remains untouched in this checkpoint.

## Source identity

- Validation base: local `develop` at `48ac62334b398bbc95b4d14ca9ef23dc83c356f3`.
- r17 overlay: 39 files; fingerprint `325593c807cab38278a93b45986f38ac3152c426421084780bc06ef99c201765`.
- Overlay archive SHA-256: `aafce9d620856696318fd7f7438449f6c2b0cd552d35aa147c7662038fbfb986`.
- The 39 overlay files were hash-verified against the source identity manifest in the integration worktree before commit.
- Integration source commit/tree: `5861ec6b296e8a48236aaa72c87abe9ec59edd4f` / `de8b888771db5ba71d74278d5f3598e5481e5942`.
- Jobs source: `713949fb752b90601e007812ebf2bd765da5ad52`; V2 source: `c0c6d0e956c9283f0c05f25b799e1b1f57ecb240`.
- Exact VM commands, logs, result files, and package hashes: [VM acceptance record](VM_ACCEPTANCE_2026-10-24.md), with copied evidence under `.tmp/vm-verification/r17-*`.

## Final VM gates

| Gate | Result | Evidence |
|---|---|---|
| Global architecture | PASS | Kole Ubuntu-Test, Python 3.14.9: 1,020 Python files; 0 over 500 LOC; 0 dependency, public API, or cycle errors |
| Audit documentation references | PASS | Kole Ubuntu-Test, Python 3.14.9: `tests/test_docs_references.py`, 2 passed, exit 0; final tested checkpoint `bdb38acb8ff383841cb2b97eed96e6136b1b25d6`, source archive SHA-256 `97bcb1a71fbc418b9fc8cca112db1d4a43a82aa82c3a8c9c9c34f1ac6432f743`; log SHA-256 `471c77f65875e4c272e08d0f1104f654c2ee63bed8cefdd055594fbb60385d29` |
| Ruff | PASS | Ubuntu-Test and Windows11-New, Ruff 0.17.2, exit 0 |
| Linux release suite | PASS | `scripts/ci.py release`, exit 0; 3,506 passed, 0 failed, 33 skipped, 46 deselected; 244 pytest subprocess commands |
| Linux GUI/Xvfb/D-Bus and coverage | PASS | `scripts/ci.py gui`, exit 0; 3,477 passed plus 29 subtests, 0 failed, 33 skipped, 46 deselected; coverage 69.56% against 65% floor |
| Windows release acceptance | PASS | Python 3.14.7, exit 0; 3,504 passed plus 29 subtests, 0 failed, 35 skipped, 46 deselected |
| Linux package build and launchers | PASS | AppImage, Debian, and Flatpak built; sidecars verified; installed `--help` smoke exits 0; Debian/Flatpak cleanup verified |
| Windows package build and smoke | PASS | PyInstaller GUI/CLI, packaged CLI/GUI smoke, 36-command guide coverage, and mocked transfer gate passed |
| GitHub Actions | NOT RUN | No hosted workflow result is claimed |

Counts are per VM run and are not summed as unique tests because the GUI and release suites overlap. Skips/deselections are retained as reported by each runner. Earlier r14–r16 failures and timeouts remain in the historical sections of the VM record; r17 is the final rerun and did not hide or relabel those attempts.

## Source-matched artifacts

All packages below were built from base `48ac62334b398bbc95b4d14ca9ef23dc83c356f3` plus the r17 overlay fingerprint above.

| Platform / artifact | Size | SHA-256 |
|---|---:|---|
| Windows onedir ZIP | 36,453,374 bytes | `cd1de871ca0d2c53220e39329f3b65e7008d342a06817e5b4bbf85d50218503a` |
| Linux AppImage | 198,928,888 bytes | `dd4ac4d7c460744d085593717cd09d5cd532a8e5b09b1780c44922be9827e75f` |
| Linux Debian package | 144,702,340 bytes | `d9df05ce86b49246b2aecf54dc13d927c35db7ff96632c6ee904ce31dc1bce1b` |
| Linux Flatpak | 122,532,624 bytes | `2f51e5812acab18ee3df5205b3da539a468d71f95b7e3121d02d827c1b1bd1d3` |

The Windows build used Python 3.14.7; Linux used Python 3.14.9. The package runs used isolated build checkouts and did not contact Slurm or mutate remote files.

## Merge checkpoint

- The integration worktree was fast-forwarded to current local `develop` base `48ac6233` before the r17 commit.
- r17 code commit `5861ec6b` is on `codex/integration/v2-jobs-staged-20261021`.
- Local `develop` remains at `48ac6233`; its separate checkout contains the validation overlay and unrelated untracked `uname` files. It was not changed to avoid disturbing that worktree.
- Status: **READY_FOR_DEVELOP_MERGE**. Nothing was pushed; no PR, release, or hosted workflow was created.
