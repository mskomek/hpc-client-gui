# WAVE 03 — Release Runner and Test Scope Integration

Status: **WAVE_COMPLETE** on the isolated integration branch. The complete release acceptance suite remains pending for WAVE 12.

## Source identity

- Wave start: `49ce32cc85d9a926542597b33f70dec259e7e2e1`.
- Integration source commit: `4ed2075c072b0cd38ca05249a9670aa96dfc3af1` (`chore(release): merge scoped test runner gates`).
- Integration source tree: `11aea5e0142d715deaeb662b411340e0d9f73143`.
- Jobs source branch: `codex/jobs-workspace-recovery-merge` at `713949fb752b90601e007812ebf2bd765da5ad52`; selected source commits: `f119e2e7`, `4f1179d3`, `8a27b784`, and the release-runner paths from `753db9f6`.
- V2 source branch: `codex/v2-master-repair-20261017` at `c0c6d0e956c9283f0c05f25b799e1b1f57ecb240`; selected release-runner/test paths from `c4d4be9c` and `e6440fbb`.
- V2 dirty snapshot remains preserved and untouched. No `release_test_suite.py`, `native_gui_test_files.py`, `scripts/ci.py`, or `test_release_test_suite.py` path was present in that snapshot.
- Eight files changed, including four Python files. The sorted path/content fingerprint is `99ec909c6802407f6029f4add7069d3c3fb882c3d36072d2f915a58398f9d3e6`, computed as SHA-256 over each sorted `path + NUL + SHA256(raw file bytes) + newline` record.
- The W04 support matrix was restored from the V2 branch because acceptance requires it. Its exact blob and runtime bytes hash to the pinned `6c41e085a1ecaeaedf6261316ea483cccaafc9b3dbea2ba71bda313fc56d6ed5`; `.gitattributes` keeps its LF bytes stable on Windows.

## Physical line counts

Counts include blank lines, comments, and docstrings. New Python files start at zero.

| Python file | Start | End |
|---|---:|---:|
| `scripts/ci.py` | 208 | 216 |
| `scripts/native_gui_test_files.py` | 0 | 94 |
| `scripts/release_test_suite.py` | 205 | 390 |
| `tests/test_release_test_suite.py` | 106 | 307 |

No Python file added or changed by this wave exceeds 500 lines. No exception was added.

## Changes and behavior

- `scripts/ci.py gui` now selects `portable`; `scripts/ci.py release` selects `acceptance`.
- Portable scope reports that supplied-evidence suites were not evaluated. Acceptance requires every evidence file, checks its pinned SHA-256 before starting subprocesses, builds a wheel, then runs those suites.
- GUI and wire-heavy modules run in separate pytest processes. AST discovery picks up new wx/Qt test modules, and filename discovery keeps future `test_ftp_widget_*.py` splits isolated. Isolated selectors are filtered to existing files, so future-wave tests are not silently lost or selected before they exist.
- Pytest reports skip reasons (`-rfs`). Nonzero test subprocess exits, including native process crashes, remain failures.
- Test configuration and user-level state are redirected to a temporary `.tmp/release-test-config-*` root. Windows keeps its existing Python user base so installed GUI test packages remain importable.
- The release lock now includes pinned `build`, `pyproject_hooks`, and Windows `colorama` requirements used by the acceptance wheel step; the duplicate development pin was removed.

## Verification

All results below are from source commit `4ed2075c072b0cd38ca05249a9670aa96dfc3af1`.

| Check | Result | Exit | Evidence |
|---|---|---:|---|
| Release runner focused tests | 13 passed, 0 failed, 0 skipped | 0 | `.tmp/wave03-release-runner-pytest.log` |
| Ruff on changed Python files | passed | 0 | `.tmp/wave03-ruff.log` |
| Compileall on changed Python files | passed | 0 | command output; no diagnostics |
| Pinned evidence hash check | no failures; exact W04 file SHA matched | 0 | `.tmp/wave03-evidence-hash.log` |
| Acceptance wheel build | wheel built successfully in a temporary `.tmp` directory | 0 | command output; non-fatal setuptools TOML license deprecation warning |
| Changed-source architecture gate, base `49ce32cc...` | PASS; 818 Python files scanned, no new LOC/import/cycle/API errors | 0 | `.tmp/wave03-changed-architecture.json` and `.md` |
| Full project architecture gate | FAIL from inherited debt: 51 over-limit files, 2 unresolved internal imports, 8 cycles, 0 API errors | 1 | `.tmp/wave03-full-architecture.json` and `.md` |

The full `--scope acceptance` suite and `scripts/ci.py release` were not run in this wave; they invoke the full native GUI partition matrix and remain part of WAVE 12 acceptance. GitHub Actions, Windows11 guest acceptance, and Ubuntu/Linux acceptance were not run. No test skip was counted as a pass.

## Integration state

WAVE 03 is committed on `codex/integration/v2-jobs-staged-20261021`. Local `develop` remains unchanged in its separate worktree. No remote branch, PR, or release was modified.
