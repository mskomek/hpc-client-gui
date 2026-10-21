# WAVE 08 — Qt Jobs Outputs

Status: **WAVE_COMPLETE** on the isolated integration branch. The actual `develop` worktree and remote branches were not changed.

## Source identity

- Wave start: `7f340c3bd9122627deb9fa63b9e1d98e631065f0`.
- Source commit: `abe774525cf93b4f20c810b70e8e19fa7585d762`; tree `460075cd2dbfccdd591ec4f6d376d54f5142a438`.
- Jobs source branch SHA: `713949fb752b90601e007812ebf2bd765da5ad52`.
- V2 source branch SHA: `c0c6d0e956c9283f0c05f25b799e1b1f57ecb240`.
- V2 dirty-worktree snapshot fingerprint: `889fb7432500705ff44281ad2c76407d5ec334de17f2ab777128e33ad0d4980b`; the snapshot was not modified.
- Fingerprint for the 19 changed Python blobs, using sorted `path + NUL + SHA-256(blob) + newline` records: `7fb57948b6bf38da8626992d0d6c94773c81c4a9fd225a2d10ce993c04b3e2a3`.

## Changes and compatibility

The 1,892-line `jobs_outputs_widget.py` was split into a 407-line facade and eight focused application modules for text/rendering, lifecycle, live polling, Jobs actions, follower views, and follower windows. The single-file follower and window lifecycle live in a separate module so the follower-view module remains at 431 lines. The facade retains all 72 declared runtime exports. AST comparison found all 58 pre-refactor widget methods in the facade or its mixins.

The first architecture run found a new dependency cycle in dynamic follower imports. Rendering helpers were moved to `_jobs_output_rendering.py`; the final gate reports no new dependency errors or cycles. The method audit also found that the V2 facade had dropped the Jobs right-click cancel menu. Its context-menu wiring and confirmation handlers were restored, with fake-menu tests covering active and completed jobs. Those tests do not call Slurm.

The old scroll and WAVE 80 test modules were split by behavior and shared support. AST comparison found all 79 prior test functions once, plus two new context-menu tests. Three exact locale expectations were corrected to match the checked-in English and Turkish catalogs (`All files`, `Tüm dosyalar`, `Shell`); the assertions remain exact equality checks.

## Python line counts

| File | Start | End |
|---|---:|---:|
| `src/hpc_gui/ui/widgets/jobs_outputs_widget.py` | 1,892 | 407 |
| `src/hpc_gui/ui/widgets/_jobs_output_follower_views.py` | 0 | 431 |
| `src/hpc_gui/ui/widgets/_jobs_output_follower_windows.py` | 0 | 32 |
| `src/hpc_gui/ui/widgets/_jobs_output_rendering.py` | 0 | 84 |
| `src/hpc_gui/ui/widgets/_jobs_output_text.py` | 0 | 105 |
| `src/hpc_gui/ui/widgets/_jobs_outputs_followers.py` | 0 | 313 |
| `src/hpc_gui/ui/widgets/_jobs_outputs_jobs.py` | 0 | 215 |
| `src/hpc_gui/ui/widgets/_jobs_outputs_lifecycle.py` | 0 | 286 |
| `src/hpc_gui/ui/widgets/_jobs_outputs_live.py` | 0 | 246 |
| `tests/support/test_jobs_outputs_scroll_shared.py` | 0 | 34 |
| `tests/support/test_wave80_files_outputs_shared.py` | 0 | 5 |
| `tests/test_jobs_outputs_context_menu.py` | 0 | 110 |
| `tests/test_jobs_outputs_follow_targets.py` | 0 | 133 |
| `tests/test_jobs_outputs_scroll.py` | 606 | 356 |
| `tests/test_jobs_outputs_scroll_jobs_outputs_scroll_tests_output_selection_rendering.py` | 0 | 185 |
| `tests/test_live_tracking_settings.py` | 17 | 17 |
| `tests/test_lssrv_auto_refresh.py` | 317 | 335 |
| `tests/test_wave80_files_outputs.py` | 609 | 284 |
| `tests/test_wave80_files_outputs_audit_behavior.py` | 0 | 321 |

All changed Python files are below 500 physical lines. Eight application modules were added. The global count of files above 500 fell from 42 at WAVE 07 to 39; those 39 are inherited baseline debt.

## Verification at source commit `abe77452`

The final local regression command was:

```powershell
& 'D:\Projeler\hpc-client-gui\.venv\Scripts\python.exe' -m pytest `
  tests/test_jobs_outputs_scroll.py `
  tests/test_jobs_outputs_follow_targets.py `
  tests/test_jobs_outputs_scroll_jobs_outputs_scroll_tests_output_selection_rendering.py `
  tests/test_jobs_outputs_context_menu.py `
  tests/test_lssrv_auto_refresh.py `
  tests/test_live_tracking_settings.py `
  tests/test_wave80_files_outputs.py `
  tests/test_wave80_files_outputs_audit_behavior.py `
  tests/test_w29_job_outputs.py -q
```

The changed-source architecture command was `python scripts/check_source_architecture.py --mode gate --base 7f340c3bd9122627deb9fa63b9e1d98e631065f0 --json-report .tmp/wave08-architecture-final.json --markdown-report .tmp/wave08-architecture-final.md`. Ruff and `compileall` covered all 19 Python paths in the line-count table above.

| Check | Result | Exit | Evidence |
|---|---|---:|---|
| Focused Qt Outputs, tracking, WAVE 80, W29, and context-menu batch | 97 passed, 0 failed, 0 skipped; 4 subtests passed | 0 | `.tmp/wave08-qt-outputs-tests.log` |
| Ruff on all 19 changed Python files | passed | 0 | `.tmp/wave08-ruff.log` |
| `compileall` on all 19 changed Python files | passed | 0 | `.tmp/wave08-compileall.log` |
| Runtime facade export check | 72 exports present; 0 missing | 0 | `.tmp/wave08-api-runtime.log` |
| Widget method comparison | 58 prior methods retained; 0 missing | 0 | committed-source AST audit |
| Changed-source architecture gate, base `7f340c3b` | PASS; 867 Python files scanned, 39 over-limit baseline files, 0 new dependency/API/cycle errors | 0 | `.tmp/wave08-architecture-final.json`, `.md`, and `.stdout.log` |
| `git diff --check` | passed | 0 | source commit diff |

An earlier full batch had one transient scroll-position subtest failure (`output1` moved 28 pixels); the same test passed on five isolated consecutive runs, and the final post-commit full batch passed all cases. This timing-sensitive observation remains noted for later stress testing; no assertions were weakened or skipped.

The full release acceptance suite, Windows11 guest acceptance, Ubuntu/Linux package acceptance, and GitHub Actions were not run in this wave.

## Integration state

The source commit `abe774525cf93b4f20c810b70e8e19fa7585d762` is on `codex/integration/v2-jobs-staged-20261021`. Local `develop` is still held in another worktree and remains unchanged. WAVE 09 starts from this source commit.
