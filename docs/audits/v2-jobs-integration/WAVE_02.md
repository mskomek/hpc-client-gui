# WAVE 02 — Jobs Workspace and wx UI

Status: **WAVE_COMPLETE** on the isolated integration branch.

## Source identity

- Wave start: `7c3ee2260aac03eea2e6aebf7d9f3e7a39ee55e3`.
- Integration source commit: `d12a752c1557b2cff7ea5a21bbf2d391c13b5fa3` (`refactor(jobs): integrate modular wx workspace controllers`).
- Integration source tree: `5d55eded058af41d3d2b3d213ba90a4798556706`.
- Jobs source branch: `codex/jobs-workspace-recovery-merge` at `713949fb752b90601e007812ebf2bd765da5ad52`.
- Selected Jobs source commits: `32aae234c3360172cc1d40592f3e7427912384eb`, `f96ec99debbe29d2930a6ff8fad9fe957d5b9820`, `90876b1aa2d9eb02f930dde5f9735d58f2902aec`, and path-selected changes from `753db9f69eaf053a4e2bced63411543cc24d4e0c`.
- This wave changed 49 files, including 46 Python files. Its sorted path/content fingerprint is `fc4a9d5cd19ca175b1557b80a5d9757961ac469cce73b542b835ef9fcd0f2d91`.
- 29 first-party implementation modules were added (28 Jobs/wx modules and one architecture API helper); six test/support modules were added. The remaining changed Python files are existing facades/tests.

## V2 dirty source review

The V2 worktree remains untouched. Its preserved dirty snapshot has 173 files (145 Python) and fingerprint `889fb7432500705ff44281ad2c76407d5ec334de17f2ab777128e33ad0d4980b`. Its `src/hpc_gui/wx_jobs.py` is a separate 397-line facade with SHA-256 `e248e4c655c4abba0af93a10df6867fa4dda69edca7c94eae9f6d7c1e2244392` and its own `_wx_jobs_*` modules. WAVE 02 uses the Jobs branch’s controller architecture and 485-line `wx_jobs.py` (source SHA-256 `38d22c5f0e114d004b93308b7d2d22bce450ec1204dce936593d93186b3456c5`); the V2 facade was not copied over it. Muse reports were treated as source-navigation hints, not test evidence.

## Physical line counts

Counts include blank lines, comments, and docstrings, computed from exact file bytes. New files start at zero. All changed Python files are at or below 500 lines.

| File | Start | End |
|---|---:|---:|
| `scripts/check_source_architecture.py` | 399 | 373 |
| `scripts/source_architecture_api.py` | 0 | 56 |
| `src/hpc_gui/jobs/__init__.py` | 0 | 1 |
| `src/hpc_gui/jobs/cancel_job_controller.py` | 0 | 133 |
| `src/hpc_gui/jobs/details_controller.py` | 0 | 439 |
| `src/hpc_gui/jobs/details_presenter.py` | 0 | 101 |
| `src/hpc_gui/jobs/files_controller.py` | 0 | 111 |
| `src/hpc_gui/jobs/job_list_controller.py` | 0 | 99 |
| `src/hpc_gui/jobs/job_rows.py` | 0 | 51 |
| `src/hpc_gui/jobs/job_selection_controller.py` | 0 | 211 |
| `src/hpc_gui/jobs/jobs_refresh_controller.py` | 0 | 166 |
| `src/hpc_gui/jobs/manual_output_followers.py` | 0 | 114 |
| `src/hpc_gui/jobs/output_channels_controller.py` | 0 | 206 |
| `src/hpc_gui/jobs/output_panel_interactions.py` | 0 | 197 |
| `src/hpc_gui/jobs/output_refresh_controller.py` | 0 | 318 |
| `src/hpc_gui/jobs/output_request_coordinator.py` | 0 | 76 |
| `src/hpc_gui/jobs/output_workspace.py` | 0 | 283 |
| `src/hpc_gui/jobs/provider_status_controller.py` | 0 | 235 |
| `src/hpc_gui/jobs/workspace_callbacks.py` | 0 | 49 |
| `src/hpc_gui/jobs/workspace_lifecycle.py` | 0 | 277 |
| `src/hpc_gui/jobs/workspace_localization.py` | 0 | 194 |
| `src/hpc_gui/jobs/workspace_navigation.py` | 0 | 14 |
| `src/hpc_gui/jobs/workspace_state.py` | 0 | 81 |
| `src/hpc_gui/jobs/workspace_test_access.py` | 0 | 104 |
| `src/hpc_gui/jobs/workspace_views.py` | 0 | 490 |
| `src/hpc_gui/wx_jobs.py` | 3216 | 485 |
| `src/hpc_gui/wx_shell_jobs.py` | 427 | 36 |
| `src/hpc_gui/wx_shell_jobs_context.py` | 0 | 127 |
| `src/hpc_gui/wx_shell_jobs_details.py` | 0 | 142 |
| `src/hpc_gui/wx_shell_jobs_files.py` | 0 | 67 |
| `src/hpc_gui/wx_shell_jobs_history.py` | 0 | 216 |
| `src/hpc_gui/wx_shell_jobs_persistence.py` | 0 | 94 |
| `tests/support/wx_jobs_test_harness.py` | 0 | 71 |
| `tests/support/wx_window_cleanup.py` | 0 | 76 |
| `tests/test_job_rows.py` | 0 | 43 |
| `tests/test_jobs_history.py` | 114 | 115 |
| `tests/test_jobs_history_mock_wire.py` | 183 | 181 |
| `tests/test_jobs_workspace_controllers.py` | 0 | 114 |
| `tests/test_source_architecture_gate.py` | 89 | 98 |
| `tests/test_w28_jobs_identity_refresh.py` | 493 | 480 |
| `tests/test_wx_jobs.py` | 62 | 70 |
| `tests/test_wx_jobs_behavior.py` | 457 | 437 |
| `tests/test_wx_jobs_bulk_delete.py` | 0 | 52 |
| `tests/test_wx_jobs_final_fix.py` | 500 | 323 |
| `tests/test_wx_jobs_provider_status.py` | 0 | 161 |
| `tests/test_wx_jobs_stress.py` | 336 | 324 |

The two near-boundary implementation files, `wx_jobs.py` (485) and `jobs/workspace_views.py` (490), were reviewed as composition/view modules and not extended beyond their Jobs branch responsibilities. The global source gate enforces the hard 500-line limit; neither has an exception.

## Behavior and verification

- The wx Jobs facade now composes the Jobs controllers for selection/listing, refresh, Details, Files, Outputs, provider status, cancellation, lifecycle, localization, and page navigation.
- The shell Jobs facade delegates context, Details, Files, history, and persistence callbacks to extracted modules.
- Profile/job identity and stale-result rejection remain wired through the selected-job store and request coordinator.
- Bulk Delete Details remains distinct from Cancel Job; the new wx test checks target IDs and selection behavior. Store tombstones from WAVE 01 still prevent deleted details from resurfacing.
- History cache patch targets and wx cleanup fixtures were updated to point at the extracted modules. `wx_jobs.py` keeps its declared six-symbol `__all__` and the private `_parse_job_row` compatibility import used by existing tests.
- `python -m pytest` over the WAVE 02 controller, workspace, bulk-delete, history, identity, and selected-context suites — **95 passed, 0 failed, 0 skipped**, exit 0 at commit `d12a752c1557b2cff7ea5a21bbf2d391c13b5fa3`.
- Additional `test_wx_jobs_files_outputs.py`, `test_wave78_jobs_details.py`, `test_corrective_jobs_details.py`, `test_wx_jobs_stress.py`, `test_jobs_auto_refresh_toggle.py`, and `test_job_history_dashboard.py` — **64 passed**, exit 0. This run printed wxWidgets `UnregisterClass` error `0x00000584` at shutdown. The stress fixture was destroying a shared wx.App while windows were still registered; it now uses `cleanup_wx_windows` and no longer destroys the shared app. The post-fix stress module passed 10/10, and a prior Jobs Files window followed by the rapid-selection stress case passed 2/2 without the warning.
- `tests/test_w13_slurm_state.py` — 14 passed; this confirms the existing `_parse_job_row` import target remains available.
- Architecture gate unit tests — 6 passed. Ruff on all changed Python code and `compileall` on changed implementation modules passed.
- Changed-source architecture gate against WAVE 01 start `7c3ee2260aac03eea2e6aebf7d9f3e7a39ee55e3` — **PASS**, exit 0; 817 Python files scanned and no new LOC, import, cycle, or API errors.
- Full project architecture check — **FAIL, exit 1**, with 51 over-limit files, 2 inherited unresolved internal imports, 8 inherited cycles, and 0 public API errors. This wave removed one over-limit file (`wx_jobs.py`) but did not complete the remaining global debt.
- No `0xC000041D` crash appeared in the recorded test outputs. GitHub Actions, Windows11 guest acceptance, and Ubuntu/Linux acceptance were not run.

The first changed-source gate run flagged incidental imports as public symbols. The checker now reads explicit `__all__` declarations for facade contracts, keeps the API contract in `public-api-contracts.json`, and checks shell consumers through import/dependency analysis. The old `wx_shell_jobs.py` accidental import list is no longer treated as a user-facing API. This removed the false positives without dropping the declared wx Jobs API or test import compatibility.

## Integration state

WAVE 02 is committed on `codex/integration/v2-jobs-staged-20261021`. `develop` remains unchanged in its separate worktree. No remote branch, PR, or release was modified.
