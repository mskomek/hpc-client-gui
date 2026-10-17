# V2 Final Repair Status — 2026-10-17

**Verdict: `V2_FAILED`**

## Repository identity

- Repair worktree: `D:\Projeler\.tmp\hpc-client-gui\v2-master-repair-20261017`
- Branch: `codex/v2-master-repair-20261017`
- Initial HEAD: `79fec4776066d9e0759adcbeb3f90430d4fc0955`
- Final HEAD: `79fec4776066d9e0759adcbeb3f90430d4fc0955` (no commit)
- Current worktree: 33 changed/untracked entries; changes are uncommitted.
- Main checkout was not modified. The previously recorded 35-to-34 dirty-entry discrepancy remains unresolved; no retained status snapshot was examined in this run.

## Native crash investigation

The retained raw release log is `.tmp/v2-final-architecture-20261017/ci-release-current.log` (75,361 bytes). It records Python 3.14, pytest 9.1.1, wxPython 4.3.1 (wxWidgets 3.3.3), PySide6/Qt 6.11.2 on Windows 11 build 26300. The suite terminated with Windows native exit `0xC000041D` and a fatal access violation in the Qt FTP test teardown after a wx test had run in the same process.

The smallest reproduced sequence was:

1. `tests/test_corrective_jobs_details_i18n_and_regression.py::TestRegression_FilesOutputs::test_files_tab_untouched`
2. `tests/test_ftp_widget_activity_queue_controls.py::FtpWidgetTests::test_completion_action_persists_and_never_runs_system_action`

Each test passed alone; the pair crashed. The refactor had split previously process-isolated wx and Qt test files, but the release runner's isolation lists still named only the old files. The fix adds the split corrective wx module to `ISOLATED_NATIVE_GUI_FILES` and all 19 split FTP modules to `ISOLATED_WIRE_FILES`, with runner regression assertions in `tests/test_release_test_suite.py`. The affected 20 modules were then executed in isolated processes: 165 tests passed, with no native crash. This is process-boundary evidence; a full post-fix release run has not been completed, so the broad-suite exit requirement remains open.

## Refactor and focused verification

Completed during this repair:

- `src/hpc_gui/cli/main.py` was reduced to a facade; parser, shared CLI contracts, and profile/doctor/remote/file/job command responsibilities were moved into eight focused modules under `src/hpc_gui/cli/`.
- `src/hpc_gui/ui/widgets/jobs_outputs_widget.py` was split into lifecycle, jobs, followers, live output, follower views, and output-text modules.
- Tests were updated to patch implementation owners after the extraction.

Focused verification on Python 3.14:

- CLI, CLI entrypoint, release-runner, and FTP settings/profile tests: **185 passed**.
- Jobs output scrolling, LSSRV auto-refresh, and FTP output-following tests: **34 passed, 4 subtests passed**.
- The 20 process-isolated split GUI modules: **165 passed** (recorded in `.tmp/v2-final-architecture-20261017/run-gui-split-partitions.py`; no raw combined log was retained).
- `compileall` succeeded for the changed JobsOutputs modules.

The canonical source architecture validator still reports **10 first-party files over 500 lines** and zero dependency errors. The two repaired files are CLI and JobsOutputs; the remaining over-limit files are listed in `V2_FINAL_REPAIR_STATUS_2026-10-17.json`. Therefore Phase 2 is incomplete.

## Release and package gates

- The existing full release log is a **pre-fix failure** (`0xC000041D`). No full post-fix release run was performed.
- The current environment cannot import Ruff (`No module named ruff`); the earlier retained Ruff log predates the latest edits and is not proof for this source state.
- No fresh accepted wheel, Windows onedir EXE, or Linux `.deb` was built from the current source. No final SHA-256 values are available.
- Windows 11 guest profile creation/save/reopen and reconnect acceptance was not performed.
- Ubuntu install/upgrade/rollback/GUI/purge acceptance was not performed.
- Independent Audit A and Audit B were not rerun for this source state; existing audit files describe earlier evidence and are stale for this repair.

## Remaining architecture files

See the JSON companion for the exact current validator counts. They are `plugin_manager_dialog.py`, `main_window.py`, `ftp_widget.py`, `local_dir_panel.py`, `login_widget.py`, `remote_dir_panel.py`, `wx_connection.py`, `wx_editor_view.py`, `wx_jobs.py`, and `wx_transfer_workspace.py`.

## Delivery state

This report is a progress/failure record, not a release acceptance claim. The requested release deliverables and gates are incomplete. No commit or push was made. The attached task prompt says “Do not push”; the direct request also asked for a push, so this report is left local pending resolution of that conflict and completion of the required gates.
