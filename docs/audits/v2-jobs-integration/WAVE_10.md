# WAVE 10 — Files and FTP

Status: **WAVE_COMPLETE** on the isolated integration branch. The local `develop` worktree and remote branches were not changed.

## Source identity

- Wave start: `3e648fbeae29cb2307bbc787288368ce478cb26a`.
- Source commit: `4e5b698653538ceeadb7a2cd16ae593e942b18a4`; tree `61744f64f1e13cc89069a0117ca6d2d15b796eb7`.
- Jobs source SHA: `713949fb752b90601e007812ebf2bd765da5ad52`.
- V2 source SHA: `c0c6d0e956c9283f0c05f25b799e1b1f57ecb240`.
- Protected V2 dirty-worktree snapshot fingerprint: `889fb7432500705ff44281ad2c76407d5ec334de17f2ab777128e33ad0d4980b`; the original dirty worktree remains untouched.
- Fingerprint for 55 changed Python files: `c23796be99577b3a74965ff23dd5e01f2c60a03ec7563ac1579d90d1307265c6`, computed as SHA-256 over sorted `path + NUL + SHA-256(committed blob bytes) + newline` records.

## Changes and compatibility

The 1,781-line FTP facade, 1,328-line local directory panel, and 4,892-line remote directory panel are now facades of 371, 356, and 450 lines. Thirty application modules were added around stable ownership boundaries for FTP sessions and activity, synchronization, comparison, local context menus and filesystem operations, remote listing/navigation/tree/metadata/permissions, and transfer planning/execution/progress. `tr(key, fallback)` was added to the shared i18n module for compatibility with the selected V2 leaves.

The facade classes retain the original methods through their mixin composition. Historical imports and patch targets remain available through facade re-exports and the compatibility hook router. Runtime checks found no missing methods on either local/remote panel class, no missing checked module exports, and no missing legacy FTP facade symbols. The remote tree and local context-menu leaves were separated to avoid conflating view ownership with transfer behavior. The upload planner and executor are separate. No real FTP/SFTP server or remote destructive operation was used.

The original 6,251-line `tests/test_ftp_widget.py` was split into a 422-line facade test and 19 focused test modules plus shared support. All 168 original test function bodies were found in the split tests with matching ASTs; no test function was lost or altered. The release runner discovered all 20 FTP test files for isolated execution.

## Changed-file line counts

| File | Start | End |
|---|---:|---:|
| `src/hpc_gui/ui/widgets/ftp_widget.py` | 1,781 | 379 |
| `src/hpc_gui/ui/widgets/local_dir_panel.py` | 1,165 | 359 |
| `src/hpc_gui/ui/widgets/remote_dir_panel.py` | 4,601 | 473 |
| `tests/test_ftp_widget.py` | 6,251 | 422 |
| `src/hpc_gui/ui/widgets/_remote_context_menu.py` | 0 | 486 |
| `src/hpc_gui/ui/widgets/_remote_transfer_plan.py` | 0 | 447 |
| `src/hpc_gui/ui/widgets/_remote_mutations.py` | 0 | 427 |
| `src/hpc_gui/ui/widgets/_remote_transfer_exec.py` | 0 | 428 |

The source commit changes 55 Python files and adds 30 application modules, 19 split FTP test modules, and one test-support module. Every added or changed Python file is at or below 500 lines. `_remote_context_menu.py` is in the 400–500 warning zone and owns the cohesive remote context-menu construction and dispatch behavior. The global over-limit count fell from 33 to 29.

## Verification at source commit `4e5b6986`

| Check | Result | Exit | Evidence |
|---|---|---:|---|
| Isolated FTP test files | 168 passed, 0 failed, 0 skipped across 20 files | 0 | `.tmp/wave10-test-logs/results.json` and per-file logs |
| Isolated adjacent Files/FTP regressions | 116 passed, 0 failed, 1 skipped across 10 files | 0 | `.tmp/wave10-adjacent-test-logs/results.json` and per-file logs |
| **WAVE 10 regression total** | **284 passed, 0 failed, 1 skipped** | **0** | Both result manifests; 30 individual test processes exited 0 |
| Skip detail | POSIX-only synchronized-browsing case on Windows | — | `test_synchronized_browsing.py` log |
| Ruff | passed on changed FTP, panel, i18n and split test sources | 0 | command output in task execution; no diagnostics |
| `compileall -q src/hpc_gui tests` | passed | 0 | command output in task execution |
| Test AST parity | 168 previous test functions retained; no missing, extra, or changed ASTs | 0 | `.tmp/wave10_compare_tests.py` output |
| Facade method/export/patch API probe | all checked class methods and legacy module symbols present | 0 | `.tmp/wave10_api_probe.py` with worktree `src` on `PYTHONPATH` |
| Changed-source architecture gate, base `3e648fbe` | PASS; 937 Python files scanned; 29 over-limit files remain; no new dependency, cycle or API errors | 0 | `.tmp/wave10-final-architecture.json`, `.md` |
| Global dependency/cycle inventory | 1 inherited unresolved symbol and 8 inherited cycles remain | — | Architecture JSON |
| i18n checker | 7 hardcoded UI strings and 3 missing keys; identical findings on WAVE 10 start source | 1 | `.tmp/wave10-i18n-committed.log`, `.tmp/wave10-i18n-baseline.log` |
| `git diff --check` | passed before source commit | 0 | source commit diff |

The i18n failures predate WAVE 10: the same seven strings and three missing references were reported from the WAVE 10 start commit `3e648fbe`. They remain open for WAVE 11/12 repair and are not counted as a pass. The inherited unresolved architecture symbol is in `scripts/capture_current_gui_qt.py`; its origin and the eight baseline cycle groups still need resolution before final architecture acceptance.

## Integration state

Source commit `4e5b698653538ceeadb7a2cd16ae593e942b18a4` is on `codex/integration/v2-jobs-staged-20261021`. The local `develop` worktree is held elsewhere and remains unchanged. No push, PR, or release was created. WAVE 11 remains pending.
