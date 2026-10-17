# V2 Muse Findings

## Bootstrap — 2026-10-17

- Required OpenCode route was invoked successfully: `opencode-go/muse-spark-1.3-contributor` (Muse Spark 1.3 Contributor), availability session `ses_eb6866a49ffesqjLDYHurdjqJi`; raw probe `.tmp/muse-v2-bootstrap/model-availability.jsonl`.
- Repair worktree: `D:\Projeler\.tmp\hpc-client-gui\v2-master-repair-20261017`, branch `codex/v2-master-repair-20261017`, HEAD `24b41444a4e68802383ba462b7c359ee9c3ef84a`. The designated branch contains prior repair commit `e6440fbb60c599ef1042a32809340eb0e623b8c4` as an ancestor.
- The main checkout has pre-existing user changes and was not modified. No commit, push, merge, PR, or release was made.
- Historical architecture inventories (10, 12, 55) disagree. The live shared validator after M01 reports 7 over-limit files and 0 dependency errors. The older 12-file architecture log is retained as historical evidence, not current status.
- Historical 3,356-test acceptance predates later source changes. The full post-isolation release suite, current packages, guest acceptance, and final audits remain outstanding.
- A Python 3.12 process building `D:\Projeler\.tmp\build-ai-context-bundle.py` was observed; it was not a project test runner.
- Historical acceptance documents contain conflicting wheel hashes and are not reused without fresh source/artifact identity evidence.

## WAVE-V2-M01

### Implementation and focused verification

- Muse implementation context: `ses_eb67ea41bffe23irJ3nl5AMNbn`, model `opencode-go/muse-spark-1.3-contributor`. An earlier overlapping context `ses_eb684bb6fffe6S72nz8022y042` stalled, was stopped, and made no product changes; its raw record is `.tmp/muse-v2-bootstrap/WAVE-V2-M01-implementation.jsonl`.
- Refactored plugin manager dialog, Qt main window, and login widget. Extracted two plugin modules, seven login modules, and four main-window mixins; updated 11 test/support files. Removed the dead MainWindow hookup to `JobsOutputsWidget.request_show_directories`, after verifying the signal was absent from that widget and no valid owner existed.
- Final M01 working-tree fingerprint: `f572f841725e477870842bad8cc1732a90512c6fc1982b9f9051c422dc8c588c`; HEAD remains `24b41444a4e68802383ba462b7c359ee9c3ef84a`. Identity recipe and independent recomputation are recorded in `.tmp/muse-v2-m01/source-identity-final.json` and `.tmp/muse-v2-m01/compute_source_identity.py`.
- Final focused GUI/profile run: 139 passed, 0 failed, 0 skipped, 0 deselected, 0 subtests; 16.18 seconds, exit 0. Raw log `.tmp/muse-v2-m01/m01-focused-gui-r4.log`; metadata `.tmp/muse-v2-m01/m01-focused-gui-r4.json`.
- M01-scoped Ruff passed (`.tmp/muse-v2-m01/ruff-m01-r2.log`). Python 3.14 compileall passed (`.tmp/muse-v2-m01/compile-m01-r2.log`).
- Earlier collection failure and test failures are retained: `.tmp/muse-v2-m01/m01-focused-gui.log` (exit 2), `m01-focused-gui-r2.log` (133 passed, 6 failed), and `m01-focused-gui-r3.log` (134 passed, 5 failed). They are not represented as passing runs.
- Current shared architecture validation at M01 reports 7 over-limit files and 0 dependency errors (exit 1), all in M02-M04: FTP widget, local and remote directory panels, wx connection, wx editor, wx Jobs, and wx transfer workspace. Evidence: `.tmp/muse-v2-m01/architecture-project-r2.log` and `.json`.
- M01 test-driven repairs restored `_ConnectionWorker` and dialog patch targets on the compatibility facade and `_load_profile_by_name` dispatch. The initial five startup failures were traced to the stale connection to a missing JobsOutputs signal and resolved by removing that dead hookup.

### Finding F-M01-001 — compatibility observation

- Audit A noted removed undocumented `login_widget.<service>` re-exports. In-repository production callers and tests use canonical implementation owners. Audit A did not classify this as a fail-grade defect; preserve the observation for later compatibility review.

### Audit history and provenance correction

- Preliminary Audit A: `.tmp/muse-v2-bootstrap/WAVE-V2-M01-audit-a.jsonl`; it identified that its prompt had an old fingerprint, then actual candidate identity was independently recomputed in the final review.
- Preliminary Audit B: `.tmp/muse-v2-bootstrap/WAVE-V2-M01-audit-b.jsonl`; correctly rejected stale tracker/state/index fingerprint fields. Those fields were corrected.
- Final Audit A: fresh session `ses_eb66b7663ffeaGv9MSS7eq9APL`, required Muse model, report `.tmp/muse-v2-bootstrap/WAVE-V2-M01-audit-a-final.jsonl`. It passed implementation review and independently reran the 16 modules: 139 passed, 0 failed, 15.30 seconds, exit 0. Raw log and metadata are `.tmp/muse-v2-m01/audit-a-final-focused.log` and `.json`.
- First final Audit B: session `ses_eb66b764dffebyE0aQqq8HAEi7`, report `.tmp/muse-v2-bootstrap/WAVE-V2-M01-audit-b-final.jsonl`. It independently recomputed the fingerprint and verified raw r4 evidence, but found one stale short fingerprint (`40ecad3f`) in the tracker M01 table row. The row is corrected to `f572f841`; Audit B must be repeated in a fresh context.
- Audits use separate contexts and independently selected checks, but the same required Muse model. This is procedural separation, not model diversity.

## Resume point

M01 is awaiting a fresh Audit B against corrected tracker/state/index. Once it passes, close M01, set it as the last completed Wave, and start dependency-ready M02. Overall terminal verdict remains `V2_PENDING`; broad release, remaining architecture waves, candidate artifacts, and guest acceptance have not been completed.


## WAVE-V2-M02 discovery

- Muse read-only discovery session `ses_eb6672696ffeXlSll1TQNuoi7d`, model `opencode-go/muse-spark-1.3-contributor`, report `.tmp/muse-v2-bootstrap/WAVE-V2-M02-discovery.md`. It identified the only local-to-remote dependency as `MIME_REMOTE_PATHS`; both panels should depend on a low-level drag-and-drop contract leaf. Remote listing, lint, file operation, and transfer workers remain owned by the remote panel branch; FTP remains a thread-free composition layer.
- Corrected discovery estimate: the report describes `tests/test_ftp_widget.py` as 6,248 LOC, but the live physical-line inventory finds **zero** tests above 500 LOC. Current source has exactly seven files above 500; the 6,248 figure is not a test-file line count. Existing duplicate-suffix FTP regression modules must remain included in isolated GUI test partitions.
- M02 baseline source fingerprint after M01 close: `f572f841725e477870842bad8cc1732a90512c6fc1982b9f9051c422dc8c588c`; HEAD `24b41444a4e68802383ba462b7c359ee9c3ef84a`.


### M02 Slice 0 verified

- Muse session `ses_eb664a62bffewbB32K2Faeh95x` added the 40-line `_fm_dnd_contract.py` leaf and moved drag payload ownership out of `remote_dir_panel.py`. Supervisor focused run: 28 passed, 0 failed/skipped/deselected, 11.53s, exit 0, covering local, remote listing/sorting, and FTP file-drop behavior. Evidence `.tmp/muse-v2-m02/slice0-focused.log/.json`; source fingerprint `e6c612c5cd91338ad057c069eef1f3fa8ced452154efab8414d128f4f90623ea`.

### M02 Slice 1 verified

- Muse session `ses_eb662845dffekeenNTUVXbiMlk` split `local_dir_panel.py` to a 499-line facade and `_local_tree.py` (286), `_local_fs_ops.py` (266), `_local_lint_tools.py` (278); moved implementation patch targets in two test modules without changing assertions.
- Supervisor focused run: 61 passed, 0 failed/skipped/deselected, 5.88s, exit 0. Ruff and compileall passed. Changed-source architecture gate exited 1 because `remote_dir_panel.py` (4611 LOC) remains in active M02 scope; dependency errors were 0. Raw evidence `.tmp/muse-v2-m02/slice1-focused.log`, `ruff-slice1.log`, `compile-slice1.log`, and `architecture-changed-slice1.log`; source fingerprint `dfd934bdf3ea09bd1b8efde60da4b097cdd78167d2fd488903f3954c492537dd`.


### M02 Slice 2 verified after repair

- Muse implementation session `ses_eb65eb214ffe3KMvGJnQgxy0wX` created `_remote_listing.py` (322 LOC) and `_remote_tree_view.py` (499 LOC), and reduced `remote_dir_panel.py` to 3927 LOC. It retargeted four cache-clock patch strings to the listing owner with assertions unchanged. The first independent Ruff run found F821 (undefined panel annotation) and F401 (unused global `json`); Muse repaired both in the same context, then Ruff and compileall passed.
- The seven-module remote listing/tree/navigation/file-drop test group passed **45/45** both before and after that narrow repair; final evidence after repair is `.tmp/muse-v2-m02/slice2-repaired-focused.log/.json`, fingerprint `b2de557d8008cac414c123ca4dff79a183714a1079ca42e87e7b60d5f383b137`. Initial Ruff failure remains at `.tmp/muse-v2-m02/ruff-slice2.log`; final pass `.tmp/muse-v2-m02/ruff-slice2-repaired.log`.
- Current shared project architecture gate: **6 over-limit files, 0 dependency errors** (exit 1), all six in M02-M04; evidence `.tmp/muse-v2-m02/architecture-project-slice2.log`. The changed-source gate similarly reports only the in-progress remote facade (3927 LOC), with zero dependency errors.


### M02 Slice 3 verified

- Muse session `ses_eb65eb214ffe3KMvGJnQgxy0wX` extracted permissions (214 LOC), mutations/undo (427), and context-menu dispatch (486), and reduced the remote facade from 3927 to 2929 LOC. It added `core.i18n.tr` (+10 lines), retained dialog and panel exports, and retargeted 13 test patch paths without assertion changes. The implementation report's first facade reduction figure was corrected from 3928→2929 (−999) to the independently measured 3927→2929 (−998).
- Six isolated test processes passed: `test_ftp_widget.py` 15, remote file ops 8, remote create 3, directory cache/tabs 9, job-output following 5, permissions/path navigation 5; total **45 passed, 0 failed/skipped/deselected**, summed module durations 8.74s, summed process wall durations 26.97s. Per-file raw logs and exact metadata are under `.tmp/muse-v2-m02/slice3/`.
- Ruff, compileall, and `scripts/check_i18n.py` passed. Changed-source architecture reports only the still-in-progress remote facade (2929 LOC) over limit; project architecture reports 6 remaining source violations and 0 dependency errors. Evidence in `.tmp/muse-v2-m02/ruff-slice3.log`, `compile-slice3.log`, `i18n-slice3.log`, and `architecture-project-slice3.log`; code fingerprint `aaae95105db522ebaf2a0fa8ae071b7b0265f9a489bf1d171ee9a1a7f5dffa93`.


### M02 Slice 4 initial regression failures — repair in progress

- Muse session `ses_eb65eb214ffe3KMvGJnQgxy0wX` extracted six transfer leaves (`_remote_transfer_plan` 446 LOC, `_remote_transfer_exec` 427, `_remote_transfer_progress` 108, `_remote_transfer_download` 397, `_remote_transfer_upload` 493, `_remote_transfer_copy_move` 153); remote facade is 1181 LOC. Slice report documents worker/Qt lifecycle ownership.
- Initial supervisor verification ran 13 isolated module processes at fingerprint `ff19b0d8a876f2d31e3948390e4a584f9a7ca4ed75e267d198a4f4a47dfabb77`. Ten process summaries completed without failure (65 tests passed plus 3 subtests); two preflight modules had 3 failing assertions/patches total; `test_ftp_widget_transfer_backend_policy.py` terminated with Windows access violation `0xC0000005`, so its final test count is unavailable. All per-module logs are under `.tmp/muse-v2-m02/slice4/`, with exact outcomes in `results.json`.
- Root trace of the native crash reaches `_TransferPlanWorker.run` → `_on_transfer_plan_finished` → synchronous progress test helper → `_finish_remote_directory_mutation` → `_refresh_from_ui`/Qt tree rendering. This indicates the completion callback entered on the worker thread and touched GUI-owned widgets; Muse is tracing the extracted slot/receiver affinity.
- `test_ftp_widget_transfer_preflight_pipeline.py` has two stale patch paths for `TransferPreflightDialog` (the moved owner is `_remote_transfer_plan`). `test_ftp_widget_transfer_preflight_pipeline_2.py` has one existing assertion failure because the multi-folder download dialog did not complete within its existing timeout. No reruns have been made pending root-cause repair.


### M02 Slice 4 verified after slot repair

- Supervisor reran the 13 isolated transfer/download processes at candidate fingerprint `f58a8881a987e335c1196ef81dba55524d1470e76ed7ae9dc79935ab60a34e33` after the concrete facade QObject dispatcher repair: **81 passed + 3 subtests, 0 failed/skipped/deselected**. `test_ftp_widget_transfer_backend_policy.py` exited normally; the earlier native crash did not recur in this isolated partition. Raw evidence is `.tmp/muse-v2-m02/slice4-slotfix/results.json` and its per-module logs. Initial failing evidence under `.tmp/muse-v2-m02/slice4/` remains preserved.

### M02 Slice 5 implemented and verified

- Muse session `ses_eb65eb214ffe3KMvGJnQgxy0wX` extracted `_remote_navigation` (242 LOC), `_remote_lint_tools` (358), `_remote_transfer_ui` (145), and `_remote_metadata` (156), reducing `remote_dir_panel.py` from 1193 to **432 LOC**. All changed first-party source files are at most 500 lines, and canonical changed-scope architecture validation passes with zero dependency errors.
- **23 distinct isolated modules passed 180 tests + 3 subtests**, with zero skips or deselections. A separate confirmation rerun added 4 more passes. One initial `download_cancel_wire` command returned exit 1 without a captured raw pytest log; two later runs passed, so the initial cause remains unknown. The permissions/navigation process was interrupted while blocked by three stale `_PermissionsDialog` patch targets; retargeting them to `_remote_metadata` made the test module pass (5 passed). Assertions were unchanged. Raw evidence is under `.tmp/muse-v2-m02/slice5/`.
- Ruff, Python compilation, and `scripts/check_i18n.py` passed. Canonical project architecture still reports **5 over-limit files, 0 dependency errors**: `ftp_widget.py` (1803), `wx_connection.py` (1387), `wx_editor_view.py` (1005), `wx_jobs.py` (2967), and `wx_transfer_workspace.py` (921). M02 remains RUNNING; its next action is the FTP extraction. Overall verdict remains `V2_PENDING`.
- Test wrapper output preserved elapsed durations and log modification times. Exact process start/end timestamps were not captured; result records explicitly state this limitation.


### M02 FTP slice implemented and verified

- Muse session `ses_eb65eb214ffe3KMvGJnQgxy0wX` split `ftp_widget.py` 1803 into a 363-line facade plus seven leaves (activity table 307, activity sync 359, activity menus 234, session 199, sync browsing 246, comparison 148, transfer actions 183); every first-party file in scope is now <=500. Ten test patch strings retargeted to true owners (monotonic, activity QMenu/beep/completion); assertions unchanged. One wrong-module import in two new leaves caused 8 first-batch collection errors, caught by the isolated logs and repaired same session (no test changes for the repair).
- 24 isolated module processes: **230 passed, 1 skipped, 0 failed/deselected**; the skip is POSIX-only exact-case in `test_synchronized_browsing.py:103` (re-run with `-rs` recorded the reason). Raw logs plus `results.json`/`source-identity.json` under `.tmp\muse-v2-m02\ftp\; fingerprint `e58ac68752a3a2c8022d8180f4fb9d99d913765dac35224cfc0b28ee55a6de75`.
- Ruff, compile, and `scripts/check_i18n.py` pass; canonical changed-scope architecture validator passes with 0 over-limit and 0 dependency errors; project scope still has four M03/M04 wx violations. Remaining project violations are the four M03/M04 wx files. Audit A passes with observations. Audit B found and required this skip-count correction; an independent Audit B recheck is pending. Broad release suite and native crash verification remain final-source gates.

### Canonical broad release run interrupted during M02 closure

- Command: `D:\Projeler\hpc-client-gui\.venv\Scripts\python.exe scripts/ci.py release`; Python 3.14.0; source SHA `24b41444a4e68802383ba462b7c359ee9c3ef84a`, dirty-tree code fingerprint `e58ac68752a3a2c8022d8180f4fb9d99d913765dac35224cfc0b28ee55a6de75`.
- Raw output: `.tmp/muse-v2-m02/release-postfix.log`. Preflight wheel build, compileall, i18n, and smoke passed. Aggregate pytest emitted 16 `F` progress markers and reached 76%, then the log stopped growing for over three minutes while pytest used negligible CPU. The supervisor interrupted the stalled run; exit 1. The quiet run had not reached its final summary, so failed node IDs, total pass/skip counts, and subtests are unknown.
- Available `py-spy` could not decode the Python 3.14 process (`Failed to find python version from target process`). No `0xC000041D` appeared before interruption, but the broad run did not exit normally; this does not verify the native crash repair.
- M02 remains BLOCKED. Resume with Muse in a diagnostic run that records test node IDs, investigate the F failures and stall, then rerun canonical broad acceptance after fixes. M03 is dependency-blocked until M02 closes. Overall verdict remains `V2_PENDING` because the acceptance determination was interrupted.

- The bounded verbose window `test_wave80_files_outputs.py` plus `test_wave80_files_outputs_audit_behavior.py` completed normally: **45 passed**, zero skipped/deselected, 4.38s, exit 0, Python 3.14.0, code fingerprint `e58ac68752a3a2c8022d8180f4fb9d99d913765dac35224cfc0b28ee55a6de75`; raw `.tmp/muse-v2-m02/diag-wave80-verbose.log`. The aggregate stall did not reproduce in a fresh process; this points to an order/state-dependent interaction or another nearby node, not yet established. Continue with the mapped F-cluster files and capture exact node IDs.

### M02 wave closure and global acceptance carryover

- M02 is closed on its owned evidence: every local/remote/FTP slice passed focused tests (FTP has one documented POSIX-only skip), changed-scope architecture passes with zero over-limit files and zero dependency errors, and separate Muse Audit A/B both pass. M02 introduced no owned defect found by its focused suites or audits.
- The intermediate broad release attempt is not accepted evidence: 16 F markers, interruption at 76%, no final summary, and normal exit unverified. It is carried as a final global gate after M03/M04. No `0xC000041D` was observed before interruption; this does not establish the native crash as resolved.
- Muse's file-cluster diagnostics (session `ses_eb608c3c3ffemLDFqY18bgH1JM`) found six failures in non-M02-oriented files: Linux release version source agreement (1); W37 failed-persist behavior (1); W38 migration/secrets (3); Wave1 Unicode source policy (1). Eight other mapped files passed; none stalled individually. These findings remain for the global regression investigation. Initial invalid exit-4 collection attempts are preserved and excluded from test totals.
- Last completed Wave: M02. Next dependency-ready Wave: M03. Overall verdict remains `V2_PENDING`.

### M03 closure

- M03 is DONE at code fingerprint `704127a4c43542a9472ae63b883856e3d0dbfb32d4eeb7d6a0e9c50e236db65b`. Facades and leaves are all <=500 LOC; changed-scope architecture has 0 over-limit and 0 dependency errors. Ruff, compile, and i18n passed.
- Focused evidence is 38 isolated processes: 272 passed, 1 failed, 0 skipped/deselected/subtests. The sole failure is W25 checksum persistence (storage default True versus expected False), independently verified non-M03 by both audits. It remains an open global/M04 carryover and is not counted as a pass.
- Separate Muse Audit A and B passed in distinct sessions. Audit B's scoped closure clarification is `.tmp/muse-v2-m03/audit-b-scope-clarification.jsonl`; it confirms M03 may close under the user's wave rules while final global acceptance remains pending.
- Next dependency-ready Wave: M04. Terminal verdict remains `V2_PENDING`.

## WAVE-V2-M04

### M04 FTP byte-verification failures, unresolved (2026-10-17; owner candidate FTP backend/global triage, not M04)

- Scope: `tests/test_wx_file_transfer_integration_conflict_policy.py` full module after the M04 test-seam repair (stale mock retargeted to `hpc_gui._wx_transfer_conflict.create_transfer_conflict_dialog`; assertions unchanged). Full-module result: 15 passed, 4 failed, exit 1 in 1.92s. Raw log `.tmp/muse-v2-m04/diag-conflict-policy-full.log` (+ `.json`/`.nodes`). Pre-fix hang evidence (exit 124, 7 passed then stall at the seam node; faulthandler stack worker `src/hpc_gui/wx_shell_file_transfer.py:200` `ready.wait`, UI `src/hpc_gui/wx_shell_file_transfer.py:173` `dlg.ShowModal` via `wx.CallAfter`, invoked by test line 83) retained at `.tmp/muse-v2-m04/conflict-policy-postrepair.log`.
- Exact failing nodes and symptoms (assertion diffs, all FTP backend byte paths via `_run_decision`/`ftp_backend`, no M04-owned GUI file on the path):
  - `test_conflict_decision_drives_ftp_upload_bytes[overwrite-ABCDEF]`: `assert ['STOR', 'RETR'] == ['STOR']` (extra `RETR`).
  - `test_conflict_decision_drives_ftp_upload_bytes[resume-XYZDEF]`: `assert ['APPE', 'RETR'] == ['APPE']` (extra `RETR`).
  - `test_conflict_decision_drives_ftp_download_bytes[overwrite-ABCDEF]`: `assert [None, None] == [None]` (extra `None` in `rest_offsets`).
  - `test_conflict_decision_drives_ftp_download_bytes[resume-XYZDEF]`: `assert [3, None] == [3]` (extra `None` in `rest_offsets`).
- Attribution: `git diff HEAD -- src tests` for M04 touches only the wx Jobs/transfer GUI leaves, facades, and the two test-seam retargets; no FTP backend, shell verify-path, or transfer-controller change. Owner candidate is the FTP backend verify path / global triage, not M04. These 4 are real failures and are never counted as passing.
- Next action: reproduce in WAVE-V2-G01 final global regression with backend/verify-path ownership; diagnose the extra `RETR`/`None` entries; fix outside M04 and re-run the full module. Do not weaken assertions or skip.
- Remaining global gates restated: W25 checksum setting; W37 plugin GUI (2); W38 migration/secrets (3); Wave1 Unicode (1); Linux release/manifest failure clusters; uncompleted broad release and native-crash verification; rebuilds and guest tests. Terminal verdict remains `V2_PENDING`.

## WAVE-V2-G01 repair2 and independent audits (2026-10-17)

- Source identity: HEAD `24b41444a4e68802383ba462b7c359ee9c3ef84a`, fingerprint `c96b01bb35083b5449f421708266a4af997f21d908f570b3d847c7253c10f42b` from `.tmp/muse-v2-m04/fp_after.py`. Required implementation model `opencode-go/muse-spark-1.3-contributor`, session `ses_eb55cb06cffe7kSCgWKWvkp9LT`.
- Audit A (separate Muse context `ses_eb5543d46ffeZKN9jKWWOlx62A`) and Audit B (separate Muse context `ses_eb5543d46ffe7ZKkvNdO0vBVxf`) both returned `PASS_WITH_OBSERVATIONS`, bound to this fingerprint. Procedural separation only; same required model. Reports `.tmp/muse-v2-g01/audit-a2.md` and `audit-b2.md`.
- CLI compatibility issue fixed by restoring `hpc_gui.cli.main._jobs_username`; whole `tests/test_cli.py`: 156 passed, 0 failed, exit 0.
- GUI-FILE-003 ordering issue fixed by extracting the asserted scoreboard to `tests/test_wx_file003_zzz_scoreboard.py`. Canonical broad selection places all contributors and the final scoreboard in one process; fresh five-file run: 11 passed, 0 skipped/deselected, 10 groups measured, all nine zero-invariants 0, duration 210.4s, exit 0.
- Ruff, compileall, i18n and global architecture project/changed scopes pass; 0 over-limit files, 0 dependency errors. Exact raw logs and metadata indexed in `V2_MUSE_EVIDENCE_INDEX.json`.
- Historical broad release remains a FAIL (22 failed, 44 teardown errors) at old fingerprint `90e3eeb0991ecdc1006d74af86e874e3a8ef9144fef2a0daa3319cf5761c4a33`; it is not current-source acceptance. The current full release/native-crash check is pending, as are candidate builds and guest acceptance. No commit/push. Overall terminal verdict remains `V2_PENDING`.

## WAVE-V2-G01 current-source broad release failure (2026-10-17)

- Canonical `scripts/ci.py release` completed normally at source fingerprint `c96b01bb35083b5449f421708266a4af997f21d908f570b3d847c7253c10f42b` (HEAD `24b41444a4e68802383ba462b7c359ee9c3ef84a`, Python 3.14.0, pytest 9.1.1, Windows 11 build 26300). Duration 3160.376s; exit 1. Raw `.tmp/muse-v2-g01/release-current.log`, metadata `.tmp/muse-v2-g01/release-current.json`.
- Bulk suite: 2 failed, 3033 passed, 30 skipped, 65 deselected, 27 teardown errors, 29 passing subtests. Three isolated native nodes passed, including `test_wx_shell_p0_stress_real_wx_paths`. Isolated `tests/test_download_cancel_wire.py`: 2 failed, 2 passed.
- Failed nodes: (1) `tests/test_wx_file_context_matrix.py::test_wx_remote_context_copy_path_writes_clipboard_without_backend`; (2) `tests/test_wx_remote_file_actions_behavior_clipboard_navigation.py::test_wx_remote_copy_path_preserves_multiple_selected_paths`; both failed to read text after production clipboard write. (3) `tests/test_download_cancel_wire.py::DownloadCancelWireTests::test_resuming_after_a_cancel_completes_the_file`; (4) `tests/test_download_cancel_wire.py::DownloadCancelWireTests::test_skipping_a_partial_leaves_it_alone`.
- Teardown errors: 6 `test_wx_file_transfer_*` nodes from `support/test_wx_file_browser_tabs_shared.py:41` (`wx.YieldIfNeeded()` sees no `wx.App`); 20 updater GUI nodes from `support/test_wx_remote_file_actions_behavior_shared.py:66` with surviving `wx.Dialog` instances (stderr shows `PyNoAppError` from `_wx_updater_install_actions.py:131` on close); one `test_windows_audit_core_checks` also reports surviving dialog. Exact 27 nodes and traces are in raw log.
- The release suite reached 100%, its isolated selections ran, and the command returned normally. This is a current repository-owned FAIL; do not classify the clipboard/teardown outcomes as environmental without separate evidence. Do not weaken assertions or convert them to skips. Next: Muse root-cause these defects, focused regressions, fresh Audit A/B, then one new canonical release run. Overall terminal stays `V2_PENDING` while work continues.

## WAVE-V2-G01 MODEL_BLOCKED after current release failure (2026-10-17)

- Attempted implementation session: `ses_eb5198e81ffeqA5FuCC536AFAo`, required model `opencode-go/muse-spark-1.3-contributor`. OpenCode returned `provider.auth` HTTP 401 `api_key_expired` before any implementation tool work. This is recorded in `.tmp/muse-v2-g01/repair3-muse.jsonl`. No other model was substituted and no code changes were made.
- Current source remains at fingerprint `c96b01bb35083b5449f421708266a4af997f21d908f570b3d847c7253c10f42b`; the completed canonical release at that fingerprint failed (details above). Therefore the terminal verdict is `V2_FAILED`; active G01 status is `BLOCKED` specifically on required model authentication.
- Resume step: refresh the OpenCode provider API key outside the repository, verify Muse is accessible, then resume repair3 using `.tmp/muse-v2-g01/repair3-request.md`. Repair the four failed tests and 27 teardown errors, run focused regressions and fresh separate Audit A/B, then run full canonical release again. Recompute source fingerprint before every evidence binding.
