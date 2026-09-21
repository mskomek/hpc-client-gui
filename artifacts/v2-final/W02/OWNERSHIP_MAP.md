# W02 — Action Ownership Map (TRACE-001)

**Pinned implementation SHA:** `f94adb640136181dbaafa84f62c753b013f0b94e` (`develop`)
**Authority:** `waves/pending/W02.md` + `HPC-W01-TRACE-001` + Workstream B (`WAVE_V2_FINAL_01.md` §218–226)
**Method:** static trace of `src/hpc_gui/wx_shell.py::_dispatch` branches + view/service
ownership, locked by `tests/test_wx_dispatch_error_gov.py`
(`test_dispatch__reaches_canonical_owner`, 16 routes, PASS).

## 1. Dispatch routes (menu → owner)

| # | Surface (menu item) | Dispatch ID | wx view / module | Canonical owner (function/class) | Downstream service/backend | Failure path (W02) |
|---|---|---|---|---|---|---|
| 1 | Menu > Settings | `APP-SETTINGS` | `wx_settings_view` | `show_settings()` → `WxSettingsModel` (`wx_settings.py`) → `config/storage.py` | `model.apply_callback` → persistence | `report_wx_action_error(area=SETTINGS)` + `settings.open_failed`; `Apply` staging/persist failures → `settings.apply_failed` (DEF-W02-003) |
| 2 | Menu > Check for Updates | `APP-UPDATE-CHECK` | `wx_updater_view` | `WxUpdateDialog` (`STATE_CHECKING`) | update service / release feed | `report_wx_action_error(area=UPDATE)` + `updates.open_failed` |
| 3 | Help > Send Logs | `APP-SEND-LOGS` | `wx_send_logs_view` | `show_send_logs()` | diagnostics bundle writer | `report_wx_action_error(area=LOGS)` + `logs.send_open_failed` |
| 4 | Help > About | `APP-ABOUT` | `wx_about` | `show_about()` → real `wx.Dialog` (W01 FIX-W01-002) | none (informational) | `report_wx_action_error(area=ABOUT)` + `about.open_failed` |
| 5 | Plugins > Browse/Manage/Updates | `PLUGIN-BROWSE/MANAGE/UPDATES` | `wx_plugins_view` | `show_plugins(initial_tab=…)` → plugin registry | plugin root / registry | `report_wx_action_error(area=PLUGIN)` + `plugins.open_failed`; legacy no-`initial_tab` signature falls back without error |
| 6 | Plugins > Request Plugin | `PLUGIN-REQUEST` | `ui.dialogs.plugin_manager_dialog` | `PLUGIN_REQUEST_URL` + `webbrowser.open()` | external browser | `opened == False` and exceptions both → `report_wx_action_error(area=PLUGIN)` + `plugins.request_plugin_failed` (DEF-W02-002) |
| 7 | Help > Help Center | `APP-HELP` | `wx_help` | `show_help()` → `WxHelpModel` | help index / shortcuts | unguarded: propagates, never silent |
| 8 | Connection tab | `APP-CONNECT` | `wx_connection` | `show_connection()` | ssh/session callbacks | unguarded: propagates, never silent |
| 9 | Files tab | `NAV-FILES` | `wx_local_files` | `show_local_files()` | local fs + transfer queue | unguarded: propagates, never silent |
| 10 | Directories tab | `NAV-DIRECTORIES` | `wx_directories_view` | `show_directories()` | files service | unguarded: propagates, never silent |
| 11 | Logs tab | `NAV-LOGS` | `wx_logs_view` | `show_logs()` | log bundle service | unguarded: propagates, never silent |
| 12 | Jobs tab | `NAV-JOBS` | `wx_jobs` | `show_jobs()` | slurm service | unguarded: propagates, never silent |
| 13 | Terminal tab | `NAV-TERMINAL` | `wx_terminal` | `show_terminal()` | ssh PTY | unguarded: propagates, never silent |
| 14 | Editor tab | `NAV-EDITOR` | `wx_shell` editor manager | `WxEditorWindowManager.open_primary()` | §2 save paths | unguarded: propagates, never silent |

## 2. Editor save paths (kept separate per TRACE-001)

- **Local save:** `wx_editor_view.save_document()` → `Path(snapshot.path).write_text()`
  (local filesystem). Failure → inline `status` label (visible, truthful);
  `mark_saved()` runs only when `saved` is true — no success-looking UI.
- **Remote (SFTP) save:** `wx_shell._editor_action_factory().save_remote()` →
  `files.write_text(path, content)` (session file service / SFTP backend).
  `save_remote` lives only in `wx_shell.py`, never in the local view
  (locked by `test_editor_save__local_and_remote_paths_have_distinct_owners`).
- **Submit/Run:** `submit()` / `run()` raise typed `RuntimeError` when the
  backend (`slurm`/`ssh`/`files`) is unavailable; surfaced inline, never swallowed.

## 3. Duplicate authorities (recorded, not hidden)

- **D1 — two dispatch authorities:** `_dispatch` (menu/tab routes) vs
  `_wx_dispatch_plugin_action` (dynamic per-plugin root submenus). Both audited;
  per-plugin actions route through the single plugin-action dispatcher.
- **D2 — header vs panel transfer path:** Files header Upload/Download call the
  same panel `run_action("upload"/"download")` (W01 `HPC-W01-TODO-021`: one
  truthful transfer path at the wx action layer, intentional, not divergent).
- **D3 — Qt vs wx error paths:** Qt `core.ui_errors.show_exception`
  (`QMessageBox`) vs wx `core.wx_errors.report_wx_action_error` (`wx.MessageBox`).
  Framework error display is intentionally duplicated per runtime; Qt helper
  untouched by W02 (out of wx scope).
- **D4 — local vs remote editor save:** separate rows in §2 by requirement.
- **D5 — chrome/header handlers vs `_dispatch`:** shell chrome handlers
  (`_on_plugins`, `_on_send_logs`, `_on_settings`) route through the governed
  `_dispatch` chokepoint instead of duplicating silent handler paths (locked by
  `test_chrome_handler__routes_through_dispatch`, FIX-W02-A2 post-green review).

## 4. ERROR-GOV-001 inventory (pass-only `except` handlers in `wx_*.py`)

Scanner: AST pass-only `except` bodies at HEAD. Total **390** sites.
W02 remediated the mandatory user-visible ones; the rest are classified below.

| File(s) | Sites | Disposition |
|---|---|---|
| `wx_shell.py` dispatch branches (6 + `PLUGIN-REQUEST`) | 7 | **FIXED** — `report_wx_action_error` with stable `AREA-XXXXXX` codes (DEF-W02-001/002) |
| `wx_settings_view.py::apply_settings` staging (4) | 4 | **FIXED** — accumulated, coded error, never `OK` (DEF-W02-003) |
| teardown/lifecycle guards (`close_host`, `Destroy`, timer stop, `unsubscribe`, `CallAfter` on closed host) | ~40 (across `wx_settings_view`, `wx_updater_view`, `wx_editor_view`, `wx_lifecycle`, `wx_shell` teardown) | **JUSTIFIED best-effort** — destroyed-control safety; logging there would create second failures |
| cosmetic fallbacks (`Wrap`, `SetMinSize`, `SetTitle`, `SetSize`, flag bitmap, `SetFocusIgnoringChildren`) | ~70 (`wx_updater_view`, `wx_shell`, splash) | **JUSTIFIED best-effort** — presentation-only, layout still completes |
| `wx_connection.py` (17), `wx_connection_dialog.py` (7) | 24 | **ROUTED** — connection/auth domain owner (W18/W19); no silent success-looking UI asserted here |
| `wx_terminal.py` (13), `wx_terminal_webview.py` (55) | 68 | **ROUTED** — terminal domain owner (W20/W21 incl. `LIFECYCLE-NATIVE-002`) |
| `wx_jobs.py` (22), `wx_transfer_workspace.py` (33), `wx_local_files.py` (19), `wx_remote_files_view.py` (13), `wx_directories_view.py` (4) | 91 | **ROUTED** — files/jobs/transfers domain owners (W23–W26) |
| `wx_updater_view.py` remainder (~50), `wx_plugins_view.py` (5), `wx_send_logs_view.py` (2), `wx_about.py` (3), `wx_splash.py` (29), misc | ~119 | **ROUTED** — updater (W41/W42), plugins (W35), diagnostics (W39), or justified teardown/cosmetic guards per site |

Cross-scope residuals carry no W02 fix; each routes to its owning Wave above.
No mandatory W02-owned action fails silently at HEAD.
