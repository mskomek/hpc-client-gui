# W39 Wave Report — Logs and diagnostics functional closure

```text
Wave: W39
Canonical report path: docs/wave-reports/v2/opencode/W39_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (working-tree changes uncommitted; controller owns commit/integration)
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W39 run phase)
Last updated: 2026-09-24
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W39.md` (wave_id W39, execution, 10 source rows + 11 TODO rows, start gate NONE).
2. `opencode/REQUIREMENT_REGISTRY.md` rows owning Wave W39: `HPC-W09-DIAG-001`..`010`.
3. `opencode/TODO_OWNERSHIP_MAP.md` rows owning Wave W39: `HPC-W09-TODO-LOGS-LIFECYCLE-001`, `-008`, `-009`, `-010`, `-011`, `-012`, `-013`, `-MIGRATION-SECRET-001`, `-051`, `-055`, `-057`.
4. `waves/bak/WAVE_V2_FINAL_09.md` → Workstream E0 — Logs and diagnostics functional surface (mandatory list of 10 behaviors).
5. Live code before edits: `src/hpc_gui/wx_logs.py`, `src/hpc_gui/wx_logs_view.py`, `src/hpc_gui/core/diagnostics.py`, `src/hpc_gui/core/log_redaction.py`, `src/hpc_gui/core/logging.py`, `src/hpc_gui/core/logging_setup.py`, `src/hpc_gui/core/paths.py`, `src/hpc_gui/i18n/{en,tr}.json`.
6. Live tests before edits: `tests/test_wx_logs.py`, `tests/test_diagnostics.py`, `tests/test_log_redaction.py`, `tests/test_wave7_editor_terminal_logs.py`, `tests/test_wave37_diagnostics.py`.

## Baseline capture

```text
Evidence ID: EV-W39-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files preserved untouched; W39 adds 5 modified files + 1 new test file, see diff review)
```

Baseline focused tests (before edits): `test_wx_logs.py + test_diagnostics.py + test_log_redaction.py` → **9 passed**.
wxPython available in `.venv`: `4.3.1 msw (phoenix) wxWidgets 3.3.3`.

Pre-existing dirty files NOT owned by W39 (preserved untouched): README.md, core/ui_errors, core/wx_errors, docs HELP/PLUGINS, plugins/*, services/command_history_store, files_ssh, output_follower, shortcut_preferences, slurm_models, plugin_manager_dialog, wx_editor_view, wx_jobs, wx_plugins(+view), wx_settings(+view), wx_shell. W39 touched only: `core/diagnostics.py`, `wx_logs.py`, `wx_logs_view.py`, `i18n/en.json` (2 keys), `i18n/tr.json` (2 keys).

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
DEF-W39-001 | P1 | diagnostics runtime truthfulness | _runtime_summary() returned "ui_framework": "Qt / PySide6" + qt_version/qt_platform on a wxPython app | stale Qt-era summary never updated during wx migration | untruthful diagnostics bundle (DIAG-006) | report wxPython + live wx.version() | YES (FIX-A) | FIXED+VERIFIED
DEF-W39-002 | P1 | Open Logs Folder missing | no open-folder control/handler anywhere in wx logs surface; DIAG-004 requires it | never implemented in wx port | user cannot reach the active log dir from the GUI (DIAG-004) | Open-Logs-Folder button + lazily resolved logs_dir() | YES (FIX-B) | FIXED+VERIFIED
DEF-W39-003 | P1 | close-during-refresh lifetime | _refresh_done and export MessageBox lambdas touched controls unconditionally via CallAfter; no alive-guard; close handler only unsubscribed i18n | callbacks written before lifecycle requirement | destroyed-control update / crash on tab/app close during pending refresh/export (DIAG-010, LOGS-LIFECYCLE-001, TODO-008) | _alive guard set false on host close, checked in every CallAfter target | YES (FIX-C) | FIXED+VERIFIED
OBS-W39-004 | N/A | clear/delete action | full-text search: no clear/delete control in wx logs surface | not exposed | DIAG-005 conditional ("if exposed") vacuously satisfied; no unconfirmed wipe exists | none | NO | VERIFIED (test asserts absence + file intact)
OBS-W39-005 | N/A | advanced logs UI (TODO-011/012) | mandatory source Workstream E0 lists no search/filter/severity/Only-Important/Hide-Routine-Polling/collapse/summary-bar; no W01 inventory decision found making them mandatory | planned-TODO UI, never promoted to mandatory scope | explicit classification below (DEC-W39-ADV-LOGS) instead of undocumented planned UI | none (code) | NO | CLASSIFIED
OBS-W39-006 | N/A | raw-log completeness (TODO-013) | WxLogsModel.refresh returns full bounded tail with no collapsing transform | no collapsing exists | satisfied by construction; covered by test | none | NO | VERIFIED
```

Second-defect search (12 dimensions): negative paths checked (missing log file, export raising OSError, LaunchDefaultApplication raising, logs_dir on odd paths); lifecycle checked (close→late callbacks swallowed; FIX-C); stale state checked (logs_dir/resolve_active_logs_dir evaluated at call time, never cached); identity checked (model path preserved; resolve does not mutate); concurrency checked (daemon threads + CallAfter marshalled; alive-flag is the only shared state); boundary values checked (200-line repetition intact, 5100-line tail bound pre-existing); capability absence checked (wx import failure → "unknown" framework string, no crash); persistence checked (first-run setup_logging probe); packaging checked (N/A — no packaged claim); error visibility checked (folder-open failure → MessageBox; export failure → MessageBox; read failure → inline text); secondary entry checked (show_logs dialog path shares _build_logs, same guards); adjacent boundary checked (diagnostics bundle redaction unchanged; i18n keys added en+tr, no raw-key leakage). Result: no further defects beyond DEF-W39-001..003.

## Implementation

### FIX-A — truthful runtime summary (DEF-W39-001, DIAG-006)

- `src/hpc_gui/core/diagnostics.py::_runtime_summary`: `ui_framework` is now `f"wxPython ({wx.version()})"` with safe `"unknown"` fallback when wx is not importable; stale `qt_version`/`qt_platform` keys removed (zero consumers in src/tests/docs — verified by search).
- Root cause: Qt-era summary text survived the wx migration untouched. The bundle's `runtime.json` therefore misidentified the UI framework on every export.

### FIX-B — Open Logs Folder (DEF-W39-002, DIAG-004)

- `src/hpc_gui/wx_logs.py::WxLogsModel.logs_dir()`: lazily resolved `log_path.parent` (expanduser + resolve at call time, never cached) so the value tracks runtime migration/isolated-root switches.
- `src/hpc_gui/wx_logs.py::resolve_active_logs_dir()`: fresh `default_log_path().parent` helper for the current runtime.
- `src/hpc_gui/wx_logs_view.py`: new `Open Logs Folder` button bound to `open_logs_folder`, which ensures the directory exists, reveals it via `wx.LaunchDefaultApplication`, and shows a truthful `folder_open_failed` MessageBox (never silent, never crashing) if the OS open fails.
- `src/hpc_gui/i18n/en.json` / `tr.json`: `logs.open_folder` + `logs.folder_open_failed` (both languages; missing-key raw leakage avoided).

### FIX-C — lifetime-safe callbacks (DEF-W39-003, DIAG-010, LOGS-LIFECYCLE-001, TODO-008)

- `src/hpc_gui/wx_logs_view.py`: `_alive` flag set `False` in the host-close handler (which still unsubscribes the i18n listener); `_refresh_done` and the new `_export_done` return immediately when dead. Export success/failure MessageBoxes are now named CallAfter targets (also exception-guarded) instead of bare lambdas, so the dead-host path and TODO-009 visibility path share one guarded funnel.

### Explicit classifications (no code change)

- `DEC-W39-ADV-LOGS` (TODO-011/012): advanced Logs UI — search/filter, severity presentation, `Only Important`, `Hide Routine Polling`, polling collapse (`×N`), summary bar — is classified **NOT mandatory V2 scope**. Justification: the mandatory authority (Workstream E0) enumerates the complete functional surface and contains none of these items; no W01 inventory record promotes them; the current viewer (title/copy/copy-path/open-folder/export/refresh + full redacted tail) satisfies every mandatory row. Raw logs remain complete by construction (TODO-013, tested). If a future Wave promotes any of these, that Wave owns the new requirement IDs.
- `DIAG-005`: clear/delete is **not exposed** in the wx logs surface (verified by control-label scan + test); the conditional requirement is satisfied without adding a destructive action.
- `TODO-051/057`: acceptance evidence for the GUI workflows is this report + `tests/test_w39_logs_diagnostics.py` (13 tests, incl. 4 real-wx runtime tests) + the retained focused-test logs below. No screenshots are produced by the headless harness; equivalent runtime readback assertions are retained as evidence files (test file + report).

## Tests and evidence

New: `tests/test_w39_logs_diagnostics.py` — **13 passed** (real wx runtime where GUI is claimed).

| Requirement | Test | Evidence |
|---|---|---|
| DIAG-001 | test_w39_diag001_logs_initialize_on_first_run | isolated `HPC_GUI_CONFIG_ROOT`; log dir created + first line written |
| DIAG-002 | test_w39_diag002_diag003 (part 1) | real wx panel opens; `boot line 1` read back from live TextCtrl |
| DIAG-003 | test_w39_diag002_diag003 (part 2) | appended `fresh line w39` visible after real Refresh button event |
| DIAG-004 | test_w39_diag004_logs_dir_resolves_active_directory + open_folder_button_exists_and_resolves | `logs_dir()` == resolved parent; click event → `LaunchDefaultApplication(resolved parent)` |
| DIAG-005 | test_w39_diag005_no_unconfirmed_clear_delete_exposed | no clear/delete label; log file byte-identical |
| DIAG-006 | test_w39_diag006_runtime_summary_truthful | `ui_framework` contains wxPython, no Qt/PySide6; version matches package |
| DIAG-007 + TODO-010 | test_w39_diag007_copy_and_export_redact | `-pw`/Bearer/private-key absent from copy + bundle zip bytes |
| DIAG-008 | test_w39_diag008_bundle_survives_missing_optional_files | empty home → bundle with manifest/runtime/plugins; no config.json |
| DIAG-009 | test_w39_diag009_usable_offline_after_connection_failure | no-connection panel refreshes local file |
| TODO-009 | test_w39_todo009_export_failure_raises_without_crashing_app | OSError surfaces (view shows it via guarded MessageBox) |
| DIAG-010 + LOGS-LIFECYCLE-001 + TODO-008 | test_w39_lifecycle_pending_refresh_safe_after_close | close → late refresh callback; no exception, no destroyed-control touch |
| TODO-013 | test_w39_todo013_raw_logs_complete_no_collapse | 200 repeated lines all present; no collapse markers |
| MIGRATION-SECRET-001 + TODO-055 | test_w39_migration_secret_redaction | host/user/password/Bearer redacted from migration-like text |

Regression sweep (after edits): `test_wx_logs + test_diagnostics + test_log_redaction + test_w39_logs_diagnostics + test_wave7_editor_terminal_logs + test_wave37_diagnostics + test_w38_migration_secrets` → **46 passed**. Plus `test_reproducibility_bundle + test_security_hardening_wave` → **12 passed, 2 skipped** (skips pre-existing). `git diff --check` → clean (exit 0; only standard LF→CRLF notices).

Evidence classes: `GUI` (required) → FULL via real wx runtime tests above. Package → N/A (no artifact built or claimed). External HPC → N/A (no external system touched; logs surface is connection-independent).

## Diff review

```text
Evidence ID: EV-W39-DIFF
git diff --check: clean
Files changed by W39 (5 modified + 1 new):
  src/hpc_gui/core/diagnostics.py   (FIX-A: truthful wx runtime summary)
  src/hpc_gui/wx_logs.py            (FIX-B model: logs_dir + resolve_active_logs_dir)
  src/hpc_gui/wx_logs_view.py       (FIX-B view button + FIX-C lifetime guards)
  src/hpc_gui/i18n/en.json          (+2 logs keys only; sibling hunks preserved)
  src/hpc_gui/i18n/tr.json          (+2 logs keys only; sibling hunks preserved)
  tests/test_w39_logs_diagnostics.py (new, 13 tests)
```

Secrets scan: no credentials, tokens, keys, or user/host literals added; diff contains only UI strings, path logic, and test fixtures with synthetic secrets (`SuperSecret123`, `leaked-value-here`) that are asserted-absent post-redaction. No binary/generated noise. No weakened tests (all assertions are positive behavioral checks; modal popups auto-neutered by `tests/conftest.py`, with explicit monkeypatched capture for the folder-open path).

## Cross-scope routing

No cross-scope defects found. Sibling dirty files were not touched. `qt_version`/`qt_platform` removal verified consumer-free before deleting.

## Handoff

Worker requests independent audit. Resume point: none — work is complete; candidate is the current working tree on `develop` at base `c8293d3c` plus the W39 files listed above (uncommitted; commit/integration is controller-owned).

```text
Candidate identity: working tree on develop @ c8293d3ca309526ed250c794c3b294f7c54ef369 + W39 diff (EV-W39-DIFF)
Focused tests: 46 passed (logs/diagnostics cluster) + 12 passed/2 skipped (bundle/hardening) + 13 new W39 tests included above
GUI runtime: wxPython 4.3.1 msw — 4 real-wx tests (open/refresh/folder-click/no-clear/lifecycle/offline)
```
