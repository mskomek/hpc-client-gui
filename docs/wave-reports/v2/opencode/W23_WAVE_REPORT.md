# W23 — Files navigation and context actions - Wave Report

```text
Wave: W23
Canonical report: docs/wave-reports/v2/opencode/W23_WAVE_REPORT.md
Branch: develop
HEAD: ccaf871ffc139973db826363859ca2933b216e9c
Working tree: dirty; unrelated and stacked changes preserved (pre-existing multi-wave dirty tree, untouched)
Decision: READY_FOR_AUDIT
```

## Scope

W23 owns `HPC-W06-FILE-001..040` plus TODO-details
`HPC-W06-TODO-LIFECYCLE-NATIVE-001, 024, 025, 026, 027, 028, 029, 030, 031, 033`
per `waves/pending/W23.md` frontmatter. Mandatory authority read before edits:
all `REQUIREMENT_REGISTRY.md` W23 rows (40 FILE + 10 TODO detail rows),
all `TODO_OWNERSHIP_MAP.md` W23 rows (10 ACTIVE), and the mandatory
`WAVE_V2_FINAL_06.md` sections (Entry criteria; Scope Local/Remote; Non-scope;
Workstream A/B/C; Handoff). Live code inspected before editing; no cross-Wave
worktree/report/temp edits; no user prompting (unattended contract).

## Requirement trace (requirement -> live owner -> test -> evidence)

- FILE-001..005 (entry prerequisites): integration-order hints only per Wave
  independence contract; no start gate. Disposable fixtures exist via `tmp_path`
  / `tempfile` in the focused tests; real-SFTP representative coverage rides the
  existing `test_wave3_remote_sftp_ssh.py` / remote-action suites (not re-run
  here; no external creds requested).
- FILE-006..013 (local scope: navigation/refresh/open/reveal/rename/mkdir/
  delete/context-menus/error-states): owner `src/hpc_gui/wx_local_files.py`
  (`LocalBrowserModel`, `delete_at`/`rename_at`, context `run_action`) —
  covered by `test_w23_files_navigation.py` (7 nodes) + `test_wx_local_files.py`
  + `test_wx_file_context_matrix.py` (all green in broad run).
- FILE-014..021 (remote scope: SFTP navigation/refresh/upload/download/rename/
  mkdir/delete/permissions/errors/context-menus): owner
  `src/hpc_gui/wx_remote_files_view.py` + `src/hpc_gui/wx_remote_files.py`
  (`WxRemoteDirectoryModel`, `PurePosixPath` remote semantics) — covered by
  `test_wx_remote_file_actions_behavior.py` + context-matrix remote nodes
  (green).
- FILE-022..024 (non-scope: no general IDE, no hex editing, no silent remote
  auto-overwrite): no code path added; overwrite/conflict stays explicit via
  existing conflict-matrix UI (`conflict_message`, transfer controller).
- FILE-025 (Workstream A context-menu parity): owner
  `src/hpc_gui/services/file_context_actions.py` (`visible_actions`,
  `FILE_CONTEXT_LABEL_KEYS`) — covered by context-matrix tests
  (targets-unselected-row, preserves-multiselection, plus behavior suites).
- FILE-026..034 (Workstream B path semantics): local uses `pathlib`/`os`
  paths; remote uses `PurePosixPath` exclusively (verified by source read;
  14 `PurePosixPath` call sites in `wx_remote_files_view.py`); covered by
  `test_paths.py` + `test_provider_path_resolver.py` (green).
- FILE-035/036 (Workstream C confirmation identity): **defect found and fixed
  this run.** Both views used generic `t("dirs.delete_confirm")`
  ("Delete the selected items?") with no target identity. Fix: shared
  `summarize_delete_targets` / `delete_confirm_message` in
  `file_context_actions.py`, per-view `_delete_confirm_text(names, location)`
  with `dirs.delete_confirm_detail` i18n template (`{count}/{location}/{names}`,
  en+tr), wired into both delete branches:
  local passes `[item.path.name] + str(tstate["path"])`, remote passes
  `[_entry_name(item)] + str(tstate["path"])`. Empty selection falls back to
  the generic string; over-long selections truncate with "+N more".
- FILE-037 (cancel side-effect free): cancel returns before `mutate`/`operation`
  in both views (early `return` on non-YES / dialog cancel) — no new test
  needed; behavior suites green.
- FILE-038/039 (error keeps row; refresh reflects backend): `mutate` shows
  `MessageBox` on error without row removal and refreshes only on success;
  `delete_at` raises on out-of-origin targets (wrong-side P0 guard) — behavior
  suites green.
- FILE-040 (handoff): no shared SFTP/session change made here (edit surface is
  files-context + i18n only); nothing to flag for W03/W05/W07 retest beyond
  this note.
- TODO-LIFECYCLE-NATIVE-001: guards present (`wx_local_files.py:419`,
  `wx_remote_files_view.py:574` `done` guards, `notebook.GetSelection()`
  probe, >=2 `except Exception`) — contract tests in `test_w23_files_navigation`
  green.
- TODO-024/025 (initial dir fallback, no source-checkout default):
  `safe_initial_local_directory` order saved->home->cwd with
  `_is_source_checkout` rejection — tests green.
- TODO-026/027/028 (mtime, human sizes, blank folder size): `LocalEntry.mtime`,
  `format_local_size` — tests green.
- TODO-029/030 (Forward exposed + deterministic Back/Forward/Up per tab):
  `LocalBrowserModel` history/forward + `btn_forward` wired with deterministic
  enable state — model tests green.
- TODO-031 (balanced splitter): `wx_shell.py` `top_splitter` uses
  `SetSashGravity(0.5)` + `SetMinimumPaneSize(300)` (initial sash 340 hint
  only) — read-verified, no change needed.
- TODO-033 (transfer-type/effective-mode): `wx_shell.py` header
  (`transfer_choice`, `effective_label`, `_current_effective_mode`) over
  `services/transfer_mode.py` (`AUTO/BINARY/ASCII`, `normalize_transfer_mode`)
  — read-verified + `test_transfer_controller.py` / `test_wx_transfer_workspace.py`
  green.

## Change set (this run only; stacked dirty tree otherwise preserved)

- `src/hpc_gui/services/file_context_actions.py`: +`summarize_delete_targets`,
  +`delete_confirm_message`, extended `__all__`.
- `src/hpc_gui/wx_local_files.py`: import extension, +`_delete_confirm_text`,
  delete branch uses target-specific confirmation.
- `src/hpc_gui/wx_remote_files_view.py`: import extension,
  +`_delete_confirm_text`, delete branch uses target-specific confirmation.
- `src/hpc_gui/i18n/en.json`, `tr.json`: +`dirs.delete_confirm_detail`.
- `tests/test_w23_delete_confirm.py`: new, 5 nodes (summary/message/truncation/
  fallback/wiring).

## Tests executed (exact, fresh, at HEAD ccaf871f + working tree)

- Focused: `tests/test_w23_delete_confirm.py tests/test_w23_files_navigation.py`
  -> `14 passed in 1.36s` (`.tmp/w23-run/w23-focused-fresh.txt`; rerun
  2026-09-24 confirms prior `14 passed in 0.67s` in `.tmp/w23-run/w23-focused.txt`).
- Broad: file/path/transfer selection (10 files: file-actions behavior,
  context-matrix, provider-path-resolver, paths, wx-local-files,
  wx-remote-files, transfer-controller, transfer-workspace, file-filter-registry,
  remote-file-actions-behavior)
  -> `96 passed, 1 skipped in 19.20s` (`.tmp/w23-run/w23-broad-fresh.txt`;
  confirms prior `96 passed, 1 skipped in 18.14s` in `.tmp/w23-run/w23-broad.txt`).
- Baseline before edits: `test_w23_files_navigation.py` 9 passed (pre-fix);
  fix adds 5 new nodes, all green after.
- `git diff --check` on the five source/i18n paths + new test: clean (exit 0).
- `scripts/validate_wave_closeout.py --wave W23`: `can_close=false` with sole
  reason missing `artifacts/wave_W23/WAVE_W23_EVIDENCE_MANIFEST.json` —
  expected at RUN phase (manifest/closeout is controller-owned); not a product
  defect.

## Diff review

`git diff --stat` on owned paths shows only the intended hunks (verified via
`git diff` grep for `delete_confirm`/`_delete_confirm_text`/`summarize_delete`
in all three source files). No secrets, no binary noise, no weakened tests
(no skip/xfail added; 1 skip is pre-existing in the broad suite), no
unrelated-file edits by this worker. Pre-existing dirty tree left intact.

## Findings / routing

- W23-owned defect FILE-035/036 repaired here (changed hypothesis:
  generic-confirm -> target-naming confirm). No cross-scope defects found;
  nothing routed to another owner.
- No `AWAITING_INPUT`, no `EXTERNAL_BLOCKED` (all required evidence is
  local/package/GUI-harness based; real-SFTP representative coverage already
  exists in-tree).

## Resume state

Implementation complete; evidence current at candidate HEAD `ccaf871f` (+
targeted working-tree fix described above). Fresh rerun 2026-09-24 at the
same HEAD re-confirmed 14 focused + 96 broad (1 pre-existing skip) with
`git diff --check` clean on owned paths. Next: controller-owned fresh
independent audit against this report + the exact tested identity, then
controller-owned manifest/closeout. This worker starts no downstream Wave.

WAVE_PHASE_STATUS: READY_FOR_AUDIT
