# WAVE 09 — Splash, Updater and Dialogs

Status: **WAVE_COMPLETE** on the isolated integration branch. The local `develop` worktree and remote branches were not changed.

## Source identity

- Wave start: `3b58c8f08a458d05b263ac9ffcd9daf9438291a0`.
- Source commit: `4c8232a746643350f29affa8b6c621c1303364e2`; tree `3c9238647ea871553a0340949e609ebcafeb0370`.
- Fingerprint for the 27 changed Python blobs, using sorted `path + NUL + SHA-256(blob) + newline` records: `ef2d598529b1de60d1fbd98999932c8e02c7b26584f5f9eb99d9dcfb1c4c77d2`.
- Jobs source SHA: `713949fb752b90601e007812ebf2bd765da5ad52`.
- V2 source SHA: `c0c6d0e956c9283f0c05f25b799e1b1f57ecb240`.
- Protected V2 dirty-worktree snapshot fingerprint: `889fb7432500705ff44281ad2c76407d5ec334de17f2ab777128e33ad0d4980b`; the snapshot was not modified.

## Changes and compatibility

The 1,213-line wx updater view now has a 487-line facade and six UI mixins for update state, text, available releases, progress, actions, and lifecycle. Its public entry points and dialog class remain available. The 664-line app updater is now 488 lines; the PowerShell installer script builder is in a separate 236-line module, while its facade retains the existing updater patch hooks.

The 1,031-line connection dialog is now a 409-line facade backed by five modules for profile actions, lifecycle, profile loading, storage editing, and templates. Thin facade wrappers pass the existing module-level template functions and `QInputDialog.getText` into the template implementation, so existing patch targets continue to work. The 529-line settings dialog is now exactly 500 lines, with separate transfer actions and file-association behavior; its `update_settings` patch target remains available. The 805-line transfer dialog is now a 273-line facade backed by support, presentation, execution, and queue modules. All 33 original dialog methods remain callable through the public classes; the transfer facade also retains `time`, `_WorkerThread`, and the prior module-level API symbols.

The updater tests were split into a 356-line view/download suite and a 325-line installation/lifecycle suite, with shared fixtures in a 55-line support module. AST comparison retained all 23 previous updater test functions. No assertions were removed or weakened.

The first post-WAVE 08 integration run found that `JobsOutputsWidget.request_show_directories` had been dropped from the extracted facade even though `MainWindow` connects to it. The signal is restored. The isolated `test_ftp_widget.py` suite covers that connection during `MainWindow` creation.

## Python line counts

| File | Start | End |
|---|---:|---:|
| `src/hpc_gui/services/app_updater.py` | 664 | 488 |
| `src/hpc_gui/services/_app_updater_script.py` | 0 | 236 |
| `src/hpc_gui/wx_updater_view.py` | 1,213 | 487 |
| `src/hpc_gui/_wx_updater_actions.py` | 0 | 189 |
| `src/hpc_gui/_wx_updater_available_views.py` | 0 | 343 |
| `src/hpc_gui/_wx_updater_lifecycle.py` | 0 | 89 |
| `src/hpc_gui/_wx_updater_progress_views.py` | 0 | 246 |
| `src/hpc_gui/_wx_updater_state.py` | 0 | 32 |
| `src/hpc_gui/_wx_updater_text.py` | 0 | 63 |
| `src/hpc_gui/ui/dialogs/connection_dialog.py` | 1,031 | 409 |
| `src/hpc_gui/ui/dialogs/_connection_dialog_actions.py` | 0 | 149 |
| `src/hpc_gui/ui/dialogs/_connection_dialog_lifecycle.py` | 0 | 52 |
| `src/hpc_gui/ui/dialogs/_connection_dialog_profile.py` | 0 | 164 |
| `src/hpc_gui/ui/dialogs/_connection_dialog_storage.py` | 0 | 326 |
| `src/hpc_gui/ui/dialogs/_connection_dialog_templates.py` | 0 | 98 |
| `src/hpc_gui/ui/dialogs/settings_dialog.py` | 529 | 500 |
| `src/hpc_gui/ui/dialogs/_settings_dialog_file_associations.py` | 0 | 53 |
| `src/hpc_gui/ui/dialogs/_settings_dialog_transfer_actions.py` | 0 | 92 |
| `src/hpc_gui/ui/dialogs/transfer_dialog.py` | 805 | 273 |
| `src/hpc_gui/ui/dialogs/_transfer_dialog_execution.py` | 0 | 241 |
| `src/hpc_gui/ui/dialogs/_transfer_dialog_queue.py` | 0 | 152 |
| `src/hpc_gui/ui/dialogs/_transfer_dialog_support.py` | 0 | 117 |
| `src/hpc_gui/ui/dialogs/_transfer_dialog_views.py` | 0 | 89 |
| `src/hpc_gui/ui/widgets/jobs_outputs_widget.py` | 407 | 408 |
| `tests/support/test_wx_updater_shared.py` | 0 | 55 |
| `tests/test_wx_updater_installation.py` | 0 | 325 |
| `tests/test_wx_updater_spec.py` | 684 | 356 |

Eighteen application modules were added. Every changed Python file is at or below 500 lines. The global over-limit count fell from 39 to 33.

## Verification at source commit `4c8232a7`

The four final regression batches ran in separate processes with `PYTHONPATH` pointed at this worktree's `src` directory:

| Check | Result | Exit | Evidence |
|---|---|---:|---|
| Updater, splash, update routing and installation regressions | 89 passed, 0 failed, 0 skipped | 0 | `.tmp/wave09-committed-updater.log` |
| FTP widget and transfer-dialog GUI regressions | 168 passed, 0 failed, 0 skipped | 0 | `.tmp/wave09-committed-ftp-widget.log` |
| Connection, settings, profile, plugin-template and persistence regressions | 101 passed, 0 failed, 0 skipped | 0 | `.tmp/wave09-committed-dialogs.log` |
| Transfer controller, recovery, conflict, speed and concurrency regressions | 96 passed, 0 failed, 0 skipped; 3 subtests passed | 0 | `.tmp/wave09-committed-transfer.log` |
| **Committed-source regression total** | **454 passed, 0 failed, 0 skipped; 3 subtests passed** | **0** | Four logs above; source identity in `.tmp/wave09-source-identity.txt` |
| Ruff on all 27 changed Python files | passed | 0 | `.tmp/wave09-committed-ruff.log` |
| `compileall -q src/hpc_gui tests` | passed | 0 | `.tmp/wave09-committed-compileall.log` |
| Public method and patch-hook comparison | 29 connection, 10 settings, and 33 transfer dialog methods retained; all checked patch hooks present | 0 | committed-source runtime API probe |
| Changed-source architecture gate, base `3b58c8f0` | PASS; 887 Python files scanned; 33 over-limit files remain; no new LOC, dependency, API, or cycle errors | 0 | `.tmp/wave09-committed-architecture.json`, `.md`, and `.log` |
| `git diff --check` | passed before commit | 0 | source commit diff |

The committed-source test commands ran with `$env:PYTHONPATH = (Resolve-Path 'src').Path` and the project `.venv` Python:

```powershell
python -m pytest tests/test_app_updater.py tests/test_wx_updater_spec.py tests/test_wx_updater_installation.py tests/test_w41_updater_routing.py tests/test_w43_restart_package_policy.py tests/test_splash_update_real_release.py tests/test_wx_dispatch_error_gov.py tests/test_w04_menu_actions.py -q
python -m pytest tests/test_ftp_widget.py -x -q
python -m pytest tests/test_connection_advanced_settings.py tests/test_local_provider_storage.py tests/test_master_password_dialog.py tests/test_plugin_template_integration.py tests/test_profile_patch_preservation.py tests/test_w37_settings_plugin_gui.py tests/test_w37_settings_persistence.py tests/test_w40_localization_window_settings.py -q
python -m pytest tests/test_transfer_cancel_recovery.py tests/test_transfer_wave17.py tests/test_transfer_tab_selection.py tests/test_transfer_resume_semantics.py tests/test_transfer_resume_identity.py tests/test_transfer_performance_scenarios.py tests/test_transfer_parallelism_migration.py tests/test_transfer_key_release.py tests/test_transfer_integrity.py tests/test_transfer_controller.py tests/test_transfer_conflict_session_scope.py tests/test_transfer_concurrency.py tests/test_transfer_directory_controllers.py tests/test_local_transfer_gate.py tests/test_transfer_speed_test.py -q
$paths = git diff --name-only 3b58c8f08a458d05b263ac9ffcd9daf9438291a0 4c8232a746643350f29affa8b6c621c1303364e2 -- '*.py'
python -m ruff check $paths
python -m compileall -q src/hpc_gui tests
python scripts/check_source_architecture.py --mode gate --base 3b58c8f08a458d05b263ac9ffcd9daf9438291a0 --json-report .tmp/wave09-committed-architecture.json --markdown-report .tmp/wave09-committed-architecture.md
```

An earlier mixed-domain pytest invocation terminated with Windows native access violation `0xC000041D` during `test_ftp_widget.py` teardown at `QApplication.processEvents()`. That invocation overlapped source edits and is not counted as committed-source evidence. The updater, FTP/Qt, dialog, and transfer batches above all passed separately against the committed source. The mixed-domain crash remains recorded for final release-runner and GUI teardown acceptance; no test was skipped to hide it.

The full release acceptance suite, Windows11 guest GUI acceptance, Ubuntu/Linux package acceptance, artifact identity checks, and GitHub Actions remain for WAVE 12.

## Integration state

Source commit `4c8232a746643350f29affa8b6c621c1303364e2` is on `codex/integration/v2-jobs-staged-20261021`. Local `develop` is still held in another worktree and remains unchanged. No push, PR, or release was created.
