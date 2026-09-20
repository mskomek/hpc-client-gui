# W02 Wave Report — Action reachability and canonical ownership

Wave: `W02`
Canonical report path: `docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA: `0f8902a023bac76071527232c2287af96478ed2b`
Current HEAD: `0f8902a023bac76071527232c2287af96478ed2b`
Tested implementation state: `HEAD 0f8902a0` + working-tree modifications listed under Diff review (no commit made by this session; every cited suite was run after the final product/test edit)
Plugin/external repo SHA(s): `..\hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin; no plugin change)
First started: 2026-09-18
Last updated: 2026-09-19 (UTC) — repair cycle 1 (AUDIT-W02-001): working-tree/diff accounting refreshed, no product edit
Session status: COMPLETE
Wave decision: PASS
Executable authority: `waves/pending/W02.md` (exactly one copy; `waves/pending/` holds W01–W61, 61 files, no gaps/duplicates; `waves/bak/` never read for execution)
Execution model: `opencode-go/muse-spark-1.3-contributor`
Dependency: `W01` — `docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md` decision `PASS`, audit `PASS`; entry revalidated (pins equal, no owned W01 blocker touches this scope)

## Owned requirements and TODO details

| ID | Kind | Status |
|---|---|---|
| `HPC-W01-TRACE-001` | MANDATORY REQUIREMENT (Workstream B — Build implementation ownership map; keep semantically distinct paths separate, e.g. remote SFTP editor save vs local editor save) | VERIFIED — ownership map below (§Ownership map), 16/16 dispatch→owner contract tests green |
| `HPC-W01-TODO-ERROR-GOV-001` | Inventory production `except Exception: pass` and equivalent silent-failure paths on mandatory workflows | CLOSED — 9 silent paths inventoried and remediated (6 `_dispatch` branches + 3 chrome handlers) |
| `HPC-W01-TODO-018` | Replace silent swallowing with typed handling, visible user error, structured log, or explicitly justified best-effort behavior | CLOSED — helper + typed `TypeError` fallback preserved; residual best-effort guards justified (§Post-green review) |
| `HPC-W01-TODO-ERROR-GOV-002` | Stable error IDs/codes for mandatory user-visible failures | CLOSED — `AREA-XXXXXX` diagnostic code on every remediated failure, logged as `Error-ID=` with traceback |
| `HPC-W01-TODO-020` | No mandatory action may fail while leaving the UI in a success-looking state | CLOSED — every repaired failure shows exactly one coded error dialog; success paths show no error |

## Mandatory source sections read

- `opencode/sources/WAVE_V2_FINAL_01.md` → Workstream B — Build implementation ownership map (§218–226): `Surface -> wx view -> action/controller -> service -> provider/backend -> persistence`; semantically distinct paths kept separate.
- `opencode/sources/V2_TODOS.md` → Error handling / no silent failure governance (§179–183): `ERROR-GOV-001/002` + companions.
- `opencode/sources/V2_FINAL_SPECIFICATION.md:1154`: bare `except Exception: pass` on a critical user-facing path is forbidden unless justified and logged.
- Owned rows: `opencode/REQUIREMENT_REGISTRY.md:66` (TRACE-001), `:1418–1421` (ERROR-GOV TODOs); `opencode/TODO_OWNERSHIP_MAP.md:86–89`; index rows `opencode/REQUIREMENT_WAVE_INDEX.md:28,1380–1383`.
- Reference implementation (live code, not authority): Qt `ui/main_window.py:460–475` + `ui/dialogs/plugin_manager_dialog.py:189–212` — the `PLUGIN-REQUEST` False-return contract mirrored into wx.
- Prior-wave background only (different numbering scheme, not authority): `docs/wave-reports/v2/WAVE_V2_FINAL_02_REPORT.md` (old planning-wave-02 provider contracts) and `artifacts/v2-final/W01/SUPPORT_MATRIX.md` (W01 inventory input). Neither was used as a substitute for the pending Wave or owned rows.

## Discovery pass (before first edit)

- Pinned `develop 0f8902a0` == `origin/develop` tip (read-only `ls-remote`; no fetch needed); working tree held only pre-existing unrelated changes (see W01 report) — all preserved, none reverted.
- `rg "except Exception" src` → large set; triaged to mandatory wx user-visible workflows: 6 silent branches in `_dispatch` (`APP-SETTINGS`, `APP-UPDATE-CHECK`, `APP-SEND-LOGS`, `APP-ABOUT`, `PLUGIN-BROWSE/MANAGE/UPDATES`, `PLUGIN-REQUEST`) plus an ignored `webbrowser.open() == False` return in `PLUGIN-REQUEST` (silent even without an exception).
- Existing diagnosability: `core/debug_support.py` (`new_error_id`, `log_exception_with_id`) + Qt-only `core/ui_errors.py`; no wx counterpart existed. i18n already carried `common.error_code` / `error_code_hint` / `plugins.open_failed` / `plugins.request_plugin_failed`.
- Narrow pre-edit baseline `EV-W02-BASE-001`: `pytest -q tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py tests/test_wx_shell.py` → **24 passed, 0 failed** (exit 0).

## WAVE_FINDINGS

| Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status |
|---|---|---|---|---|---|---|---|---|
| `DEF-W02-001` | P1 | `_dispatch` ×6 branches (`wx_shell.py:2760–2816` pre-fix) | pre-fix source (6× `except Exception: pass`); revert-run 9 failures | bare except-swallow on user-visible dispatch | click fails with zero feedback; UI looks successful | typed report via `wx_errors` helper + visible coded dialog + structured log | YES (FIX-W02-A) | CLOSED |
| `DEF-W02-002` | P1 | `PLUGIN-REQUEST` (`webbrowser.open` return ignored) | pre-fix source; Qt reference shows required contract | return-value neglect: `False` raises nothing, old code showed nothing | no browser opens, no error; UI looks successful | check return; report coded error on `False`/exception (Qt parity) | YES (FIX-W02-B, independent: return-neglect vs exception-swallow) | CLOSED |
| `DEF-W02-001b` | P1 | chrome `_on_plugins` / `_on_send_logs` / `_on_settings` (post-green review find) | pre-fix source (dead-but-bindable duplicate silent handlers) | duplicate implementation path beside the governed chokepoint | same silent failure via any future/alternate binding | route through `_dispatch` like `_on_help` | part of FIX-W02-A (same defect family/chokepoint) | CLOSED |
| `DEF-W02-003` | P1 | Settings Apply staging/persistence (`wx_settings_view.py`, concurrent-tree) | concurrent working-tree change (not this session) | staging `except: pass` + unconditional `OK` dialog | applied-settings success shown on failure | owned by concurrent session (FIX-W02-C); preserved verbatim, not claimed here | NO (not this session's change) | OBSERVED/ROUTED |

## Fixes

### FIX-W02-A — DEF-W02-001 (+001b): silent dispatch failures become visible, coded errors

- Before (`EV-W02-SENS-001` + source): 6 `_dispatch` branches ended in `except Exception: pass`; reverting the fix makes 9/29 tests fail for the right reason (no dialog shown).
- Root cause: the wx dispatch layer treated every downstream failure (dialog construction, view open, browser launch) as ignorable; the Qt surface already proved the truthful pattern (visible warning + log).
- Change (smallest coherent): new `src/hpc_gui/core/wx_errors.py` (`report_wx_action_error`: structured log with `Error-ID=AREA-XXXXXX` via `log_exception_with_id`, then a `wx.MessageBox` carrying user message + `Diagnostic code: AREA-XXXXXX` + hint; dialog is best-effort so logging never goes silent, incl. `wx`-absent environments); 6 `_dispatch` branches now call it with per-action areas (`SETTINGS`, `UPDATE`, `LOGS`, `ABOUT`, `PLUGIN`) and message keys; the 3 duplicate chrome handlers route through `_dispatch` (same pattern as `_on_help`); pre-existing `TypeError` fallback for `show_plugins` preserved.
- i18n (additive only): `settings.open_failed`, `updates.open_failed`, `logs.send_open_failed`, `about.open_failed` in `en.json` + `tr.json` (parity preserved; parity suites green).
- After: 37/37 `tests/test_wx_dispatch_error_gov.py` pass; GUI probe `EV-W02-GUI-001` PASS (real `EVT_MENU` → coded dialog `SETTINGS-E361C0`); sensitivity `EV-W02-SENS-001/002` prove detectors fail pre-fix; W01 detectors still green (no `wx.MessageBox` literal added to the `APP-ABOUT` block — helper indirection preserves FIX-W01-002's regression surface).
- Regression tests: NEG-W02-001…005 (one per branch), happy-path guards (about/plugin fallback/request-ok), `test_error_codes__unique_per_failure`, `test_error_helper__wx_unavailable__still_logs_with_code`, routing lock `test_dispatch__no_silent_pass_on_mandatory_branches` + chrome routing tests, REQ contract tests (16 owners), editor-save separation test.
- Sensitivity: `EV-W02-SENS-001` (temp HEAD revert: 9 failed/20 passed, right reason; tree restored byte-identical, sha256 `769FC0ED…4C07EC` both sides); `EV-W02-SENS-002` (static A2 proof: pre-fix handlers unrouted+silent).
- Residual risk: negligible — synchronous paths, no state retained; modal capture in tests is a documented legitimate boundary (real event routing + real helper + real log).

### FIX-W02-B — DEF-W02-002: PLUGIN-REQUEST honors browser-open failure

- Before: `webbrowser.open()` return ignored; `False` (no browser) produced nothing at all — not even an exception to swallow. Qt `_open_plugin_requests`/`open_plugin_requests` prove the required contract (warn on `not opened`).
- Root cause (independent of FIX-W02-A): return-value neglect, a different failure mode from exception swallowing — FIX-W02-A alone would still leave the `False` case silent.
- Change: capture `opened` + `request_error`; single coded error (`plugins.request_plugin_failed`, area `PLUGIN`) when `not opened`, covering both `False` and exception sub-paths.
- Regression tests: `test_plugin_request__browser_false__visible_error`, `..._browser_exception__visible_error`, `..._browser_ok__no_error`. Sensitivity: both failure tests fail on pre-fix code (`EV-W02-SENS-001`).
- Residual risk: none known; URL allow-listing stays Qt-side (out of wx scope, unchanged).

## Ownership map (HPC-W01-TRACE-001 deliverable)

`Surface -> wx view -> action/controller -> service -> provider/backend -> persistence`. Verified at `HEAD 0f8902a0` + this Wave's diff; contract tests pin the dispatch column.

| ID | Surface / Action | wx view | Action/controller | Service / backend | Provider/persistence | Evidence |
|---|---|---|---|---|---|---|
| `OWN-MENU-SETTINGS` | Menu > Settings | `wx_settings_view.show_settings` | `_dispatch("APP-SETTINGS")` | settings model/service | local config store | NEG-W02-001 + GUI probe pattern |
| `OWN-MENU-UPDATE` | Menu > Check for Updates | `wx_updater_view.WxUpdateDialog` | `_dispatch("APP-UPDATE-CHECK")` | updater service | release feed/packaging (W04/W10) | NEG-W02-002 |
| `OWN-MENU-HELP` | Help > Help Center | `wx_help.show_help` | `_dispatch("APP-HELP")` | help catalog | bundled docs | W01 EV-W01-EXE-003/004 |
| `OWN-MENU-SENDLOGS` | Help > Send Logs | `wx_send_logs_view.show_send_logs` | `_dispatch("APP-SEND-LOGS")` | diagnostics bundler | local log files | NEG-W02-003 |
| `OWN-MENU-ABOUT` | Help > About | `wx_about.show_about` (real `wx.Dialog`) | `_dispatch("APP-ABOUT")` | app metadata | `__version__` | NEG-W02-004 + GUI-W02-001 |
| `OWN-MENU-PLUGINS` | Plugins > Browse/Manage/Updates | `wx_plugins_view.show_plugins` (+`initial_tab`) | `_dispatch("PLUGIN-*")` | plugin loader/registry | plugin repo `f0abb7e7` (W08 packaged proof) | NEG-W02-005 + fallback guard |
| `OWN-MENU-REQUEST` | Plugins > Request Plugin | `webbrowser.open(PLUGIN_REQUEST_URL)` | `_dispatch("PLUGIN-REQUEST")` | OS browser | constant URL (Qt allow-list) | DEF-W02-002 ×3 tests |
| `OWN-CONNECT` | Connection tab | `wx_connection.show_connection` | `_dispatch("APP-CONNECT")` | SSH/session lifecycle | profiles store | untouched; contract test |
| `OWN-TERMINAL` | Terminal tab | `wx_terminal.show_terminal` | `_dispatch("NAV-TERMINAL")` | SSH shell session | live connection (W03) | contract test |
| `OWN-JOBS` | Jobs & Outputs tab | `wx_jobs.show_jobs` | `_dispatch("NAV-JOBS")` | Slurm backend | live cluster (W03) | contract test |
| `OWN-DIRS` | Directories tab | `wx_directories_view.show_directories` | `_dispatch("NAV-DIRECTORIES")` | files service | SFTP (W03) | contract test |
| `OWN-FILES` | Files tab (local+remote+transfers) | `wx_local_files` + `wx_remote_files_view` | `_dispatch("NAV-FILES")` | transfer controllers | local FS / SFTP (W03 remote) | behavior/lifecycle suites |
| `OWN-EDIT-LOCAL` | Editor save (local document) | `wx_editor_view.save_document` | editor manager | **`Path.write_text` (local FS)** | local filesystem | separation test |
| `OWN-EDIT-REMOTE` | Editor save (remote document) | `wx_shell._editor_action_factory.save_remote` | editor manager | **session `files.write_text` (SFTP)** | live connection (W03) | separation test (NOT collapsed) |
| `OWN-LOGS` | Logs tab | `wx_logs_view.show_logs` | `_dispatch("NAV-LOGS")` | log service | local log files | contract test |
| `OWN-LANG` | Language menu | `i18n.set_language` | direct bind | i18n bundles | persisted `language.json` | W01 DEC + i18n suites |

Remote-execution rows keep `REQUIRES_EXTERNAL_VALIDATION` with owner W03; packaged rows with W04/W08/W10. Nothing removed from the W01 ledger.

## Second-defect search protocol (dimensions for the dispatch surface)

1. negative paths — CHECKED, defects found (DEF-W02-001/002), 8 negative tests added.
2. lifecycle — N/A with justification: `_dispatch` is synchronous, retains no callbacks; probe proves controlled shutdown (exit 0).
3. stale state — N/A: no retained callbacks/async results in the repaired paths.
4. identity — CHECKED: per-action area codes (`SETTINGS/UPDATE/LOGS/ABOUT/PLUGIN`); parent owner passed through; no profile context in these branches.
5. concurrency/race — N/A with justification: synchronous modal error, no shared mutable state.
6. boundary values — CHECKED: `webbrowser.open` True/False/exception triple + `TypeError` fallback preserved and tested.
7. capability absence — CHECKED: `wx`-unavailable helper test (log + code survive, dialog best-effort).
8. persistence — N/A: error dialogs persist nothing.
9. packaging — N/A with justification: no new dependency (`wx` stays optional/lazy); i18n JSON already packaged.
10. error visibility — CHECKED: the Wave's core; every repaired failure shows exactly one coded dialog.
11. context menus/secondary entry — CHECKED: single `_dispatch` chokepoint serves menu + shortcut bindings; duplicate chrome handlers routed (DEF-W02-001b).
12. adjacent integration boundary — CHECKED: callee call-sites unchanged (`parent=` kwarg as before); `TypeError` fallback semantics preserved + tested.

No second independent defect in this Wave's scope beyond FIX-W02-A/B; the two-fix floor is met without exception (no `TWO-FIX-EXCEPTION` needed).

## Tests and evidence

| Evidence | Exact command | Exit | Result |
|---|---|---:|---|
| `EV-W02-BASE-001` narrow baseline (pre-edit) | `python -m pytest -q tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py tests/test_wx_shell.py` | 0 | 24 passed, 0 failed |
| `EV-W02-AFTER-001` dedicated regression suite | `python -m pytest -q tests/test_wx_dispatch_error_gov.py` | 0 | 37 passed (33 authored here + 4 concurrent-tree FIX-W02-C/GUI preserved) |
| `EV-W02-SENS-001` revert sensitivity | temp `git show HEAD:wx_shell` swap → same dedicated suite → restore (sha256 `769FC0ED…4C07EC` both sides) | script 0 | 9 failed / 20 passed pre-fix, right reason; 29/29 post-restore |
| `EV-W02-SENS-002` routing sensitivity | `python w02_sens_a2.py` (Temp, outside repo) | 0 | pre-fix handlers unrouted+silent confirmed |
| `EV-W02-GUI-001` real wx event/runtime probe | `python w02_gui_probe.py` (Temp; real shell frame, real `EVT_MENU` via `ProcessEvent`, fault-injected `show_settings`, captured modal) | 0 | `W02_GUI_PROBE=PASS`, `MSGBOX_CALLS=1`, code `SETTINGS-E361C0`; controlled shutdown |
| `EV-W02-GUI-002` in-repo GUI event test | `test_about_menu_event__failure__visible_coded_error` (concurrent-tree, preserved) | 0 | real menu event → exactly one `ABOUT-XXXXXX` dialog |
| `EV-W02-IMPACT-001` i18n/menu/about/help/plugin | 11 suites (unicode baseline, wx_i18n, wave8 i18n, menu_redesign, about, wx_help, palette ×2, help refs/search/catalog, plugin_manager_ui) | 0 | 129 passed |
| `EV-W02-IMPACT-002` shell/editor/terminal | `test_wx_shell`, `test_wx_shell_p0`, `test_wx_editor_cross_view_actions`, `test_wx_term002` | 0 | 35 passed |
| `EV-W02-IMPACT-003` file transfer paths | `test_wx_file_actions_behavior`, `test_wx_file_actions_lifecycle` | 0 | 29 passed |
| `EV-W02-IMPACT-004` combined re-run | gov + w01-truth + w01-sensitivity + wx_shell | 0 | 61 passed |

Environment: `Python 3.12.4`, `wxPython 4.3.1 msw (phoenix) wxWidgets 3.3.3`, Windows. One transient anomaly: a single full-file run exited `-1073740940` after printing `34 passed` (wx interpreter-shutdown heap noise; W01 recorded similar WebView2 teardown noise); the suite re-runs green with exit 0 and no test failed. No test weakening, no new skips/xfails, mocks limited to legitimate boundaries (modal capture, failing callee, `webbrowser.open`, `CallAfter` inline in sibling tests) with real routing/helper/log exercised.

## Post-green review (`POST_GREEN_REVIEW`)

- Duplicate path: FOUND and fixed (`_on_plugins/_on_send_logs/_on_settings` → `_dispatch`; sensitivity-proven). No other mandatory-branch duplicates: remaining `except: pass` occurrences are best-effort housekeeping (tooltips, `Enable/Destroy` guards, teardown/close guards, label refresh) or already-logging paths — explicitly justified, not user-outcome paths.
- Alternate entry: same chokepoint (menu + `Ctrl+,` keymap bind the same `_dispatch` ids); covered by construction.
- Silent fallback: `show_plugins` `TypeError` fallback preserved; fallback failure still reaches the outer reporter (verified by structure + guard test).
- Stale/identity/cleanup/packaging: N/A per dimension notes; no new resources; no secrets in diff/scripts/reports.

## Diff review (recaptured 2026-09-19 UTC, repair cycle 1 for AUDIT-W02-001)

- Identity: main `develop` HEAD `0f8902a023bac76071527232c2287af96478ed2b` (= `0f8902a0`); plugin `../hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin; no plugin change). `waves/pending/` holds W01–W61 (61 files, exactly one `W02.md`); `waves/bak/` never read. No commit made by this session.
- `git status --short` (full, verbatim):
  - Tracked modified (14): `M CONTRIBUTING.md`, `M README.md`, `M artifacts/v2-final/W01/W01_COMPLETION_REPORT.md`, `M artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md`, `M docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md`, `M src/hpc_gui/i18n/en.json`, `M src/hpc_gui/i18n/tr.json`, `M src/hpc_gui/plugins/loader.py`, `M src/hpc_gui/plugins/validator.py`, `M src/hpc_gui/services/connection_controller.py`, `M src/hpc_gui/wx_connection.py`, `M src/hpc_gui/wx_settings_view.py`, `M src/hpc_gui/wx_shell.py`, `M tests/test_wave10_release_gate.py`.
  - Untracked: `?? artifacts/v2-final/W02/`, `?? artifacts/v2-final/W04/`, `?? docs/wave-reports/v2/opencode/`, `?? hpc-client-gui.ffs_gui`, `?? src/hpc_gui/core/wx_errors.py`, `?? sync.ffs_db`, `?? tests/test_w03_settings_provider_inventory.py`, `?? tests/test_w04_support_freeze.py`, `?? tests/test_w08_schema_isolation.py`, `?? tests/test_w09_main_plugin_compat.py`, `?? tests/test_w11_ssh_lifecycle.py`, `?? tests/test_wx_dispatch_error_gov.py`.
- `git diff --stat` (14 files, 277 insertions, 83 deletions): per-file `CONTRIBUTING.md 11/4`, `README.md 2/1`, `W01_COMPLETION_REPORT.md 4/2`, `WAVE_01_SESSION_REPORT.md 4/2`, `WAVE_V2_FINAL_01_REPORT.md 6/0`, `en.json 7/1`, `tr.json 7/1`, `plugins/loader.py 7/1`, `plugins/validator.py 33/23`, `connection_controller.py 24/1`, `wx_connection.py 71/1`, `wx_settings_view.py 19/10`, `wx_shell.py 64/32`, `test_wave10_release_gate.py 18/4`. Full `git diff --numstat` matches; `git diff --check` clean (only pre-existing CRLF-conversion notices on `artifacts/v2-final/W01/*` + i18n). Nothing was reset, reverted, or cleaned; all unrelated changes preserved.
- W02-owned product/test changes (this session; remainder explicitly NOT claimed — see attribution below):
  - `?? src/hpc_gui/core/wx_errors.py` (new helper, W02-owned).
  - `?? tests/test_wx_dispatch_error_gov.py` (shared file: 33 tests authored here + 4 concurrent-tree FIX-W02-C/GUI tests preserved; passes as a whole 37/37 in the earlier full-file run, 56/56 in the 2026-09-19 focused slice below).
  - `src/hpc_gui/wx_shell.py` W02 hunks only: 1 import + 6 `_dispatch` branches + 3 chrome routings + PLUGIN-REQUEST return handling (FIX-W02-A/B). The file additionally carries a later W04 hunk (FIX-W04-A, attributed below) — not W02.
  - `src/hpc_gui/i18n/en.json` + `tr.json` W02 keys only: `settings.open_failed`, `updates.open_failed`, `logs.send_open_failed`, `about.open_failed`, `plugins.action_failed` (W02-authored; `plugins.action_failed` is now additionally exercised by W04 FIX-W04-A — shared key, W02 authorship retained, W04 usage noted not absorbed).
  - `?? docs/wave-reports/v2/opencode/` (these canonical W02 reports).
- Explicitly NOT W02 — preserved verbatim, owned elsewhere (not absorbed, not reverted):
  - `M src/hpc_gui/wx_settings_view.py` + `settings.apply_failed` keys in both locales + FIX-W02-C/GUI-W02-001 tests in the shared gov suite: concurrent-tree Settings Apply error governance (DEF-W02-003/FIX-W02-C), observed/routed.
  - `src/hpc_gui/wx_shell.py` W04 hunk: stale plugin-menu visible coded error (`plugins.action_failed`) + `frame._wx_dispatch_plugin_action` hook (W04 FIX-W04-A / DEF-W04-001) — different defect (log-only plugin-action path), not W02's dispatch-swallow family.
  - `M src/hpc_gui/plugins/loader.py` + `M src/hpc_gui/plugins/validator.py`: plugin schema fail-closed work (W08 track).
  - `M src/hpc_gui/services/connection_controller.py` (`close_session`) + `M src/hpc_gui/wx_connection.py` (disconnect_cb/reconnect teardown/status): session-lifecycle work (other-Wave track).
  - `M CONTRIBUTING.md` + `M README.md`: Python 3.14 setup/docs edits (unrelated).
  - `M artifacts/v2-final/W01/*` (×2) + `M docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md`: W05 SUPERSEDED banners pointing at the canonical W01 report (history preserved, no competing decision).
  - `M tests/test_wave10_release_gate.py`: W10 gate refinement (latin-1/cp125 usage regex).
  - Untracked cross-Wave artifacts/tests: `artifacts/v2-final/W02/`, `artifacts/v2-final/W04/`, `tests/test_w03_settings_provider_inventory.py`, `tests/test_w04_support_freeze.py`, `tests/test_w08_schema_isolation.py`, `tests/test_w09_main_plugin_compat.py`, `tests/test_w11_ssh_lifecycle.py` — not W02 evidence, left untouched. `hpc-client-gui.ffs_gui` + `sync.ffs_db`: local sync sidecars, untouched.
- Full product diff inspected file-by-file (W02 hunks + every unrelated hunk above); no generated/binary noise; no weakened tests; no secrets in diff/scripts/reports.
- Repair-cycle re-verification (2026-09-19, implementation state `0f8902a0` + tree above, no product edit): `python -m pytest -q tests/test_wx_dispatch_error_gov.py tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py` → exit 0, **56 passed** (`EV-W02-REPAIR-001`); `python -m pytest -q tests/test_wx_dispatch_error_gov.py -k 'GUI or about_menu_event'` → exit 0, **1 passed**, real wx menu-event proof intact (`EV-W02-REPAIR-002`). Owned IDs re-read: `REQUIREMENT_REGISTRY.md:66` (TRACE-001) + `:1418–1421` (4 TODOs), `TODO_OWNERSHIP_MAP.md:86–89` — statuses VERIFIED/CLOSED unchanged.

## Concurrent-tree accounting (preserved, not claimed)

During this session a concurrent worker edited the same tree: `M src/hpc_gui/wx_settings_view.py` (Settings Apply error governance, DEF-W02-003/FIX-W02-C), `settings.apply_failed` keys in both locales, and appended FIX-W02-C + `GUI-W02-001` tests to `tests/test_wx_dispatch_error_gov.py` plus a `wx_app` fixture. All preserved byte-for-byte; nothing reverted, reset, or absorbed into this session's claims. The shared test file passes as a whole (37/37). `GUI-W02-001` exercises this session's `APP-ABOUT` failure path and is cited as evidence with provenance noted. DEF-W02-003 remains owned by the concurrent session not this report. Repair cycle 1 (2026-09-19) additionally records later-tree changes observed since the original accounting — W04 FIX-W04-A hunks in `wx_shell.py`, W08 loader/validator, session-lifecycle controller/connection, W05 superseded banners, W10 gate refinement, Python 3.14 docs, and untracked W02/W04 artifacts + W03/W04/W08/W09/W11 tests + FFSync sidecars — all preserved untouched and attributed in §Diff review, none absorbed into W02 ownership.

## Findings and ownership routing

- In-scope P0/P1 opened: `DEF-W02-001`, `DEF-W02-001b`, `DEF-W02-002` — all CLOSED with proof chains above.
- Cross-wave: none absorbed. Remote/package validation stays with W03/W04/W08/W10 per the ownership map. Qt-side swallows (`ui/main_window.py:457,474`) belong to the legacy/Qt truth owner (W05 track) — noted, not touched.
- New defects introduced: 0.

## Resume state

Completed and verified: all 5 owned IDs (TRACE-001 + 4 TODOs); FIX-W02-A/B with regression + sensitivity + GUI proof; ownership map; 61-test combined re-run green; reports current. Repair cycle 1 (2026-09-19): AUDIT-W02-001 closed by recapturing exact tree/diff attribution above (no product edit); focused slice re-run 56 passed + 1 real wx menu-event proof green (EV-W02-REPAIR-001/002).
In progress: none. Open P0/P1: 0 (owned). Open P2/P3: 0 (owned).
Pending tests/evidence: none for this Wave (heavy `test_wx_file003_final_stress` not re-run: untouched paths, behavior/lifecycle equivalents green).
Last exact commands: see evidence table (`EV-W02-IMPACT-004`, `EV-W02-GUI-001`).
Next actions: none in this Wave — stop. `W03` may be planned only after its dependency/prerequisite revalidation.
Evidence/artifact identities: implementation state `0f8902a0`+diff; probe scripts `w02_gui_probe.py`, `w02_sens_a2.py` (Temp, outside repo); no package artifact (N/A for W02).

## Final summary

```text
FIX-A: visible coded errors for 6 silent _dispatch branches + 3 chrome handlers routed to _dispatch
DEF: DEF-W02-001 (+001b)
Root cause: bare except-swallow (and duplicate ungoverned handlers) on user-visible dispatch
Before EV: EV-W02-SENS-001 (9 fail pre-fix, right reason) + pre-fix source
After EV: EV-W02-AFTER-001 (37/37), EV-W02-GUI-001 (PASS, SETTINGS-E361C0), EV-W02-IMPACT-004 (61)
Regression test: tests/test_wx_dispatch_error_gov.py (NEG-W02-001..005, locks, REQ contract ×16, separation, routing ×3)
Sensitivity proof: EV-W02-SENS-001 (byte-identical restore) + EV-W02-SENS-002

FIX-B: PLUGIN-REQUEST honors webbrowser.open()==False (Qt parity)
DEF: DEF-W02-002
Root cause: return-value neglect — False raises nothing, old code showed nothing
Before EV: pre-fix source (return ignored) + Qt reference contract
After EV: False/exception → one PLUGIN-XXXXXX dialog; True → silence; covered in EV-W02-AFTER-001
Regression test: browser False/exception/ok triple
Sensitivity proof: EV-W02-SENS-001 (both failure tests fail pre-fix)

Additional fixes: none (floor met with two independent fixes; no exception needed)
Post-green review: duplicate chrome paths found + routed with sensitivity proof; residuals justified
New/modified tests: tests/test_wx_dispatch_error_gov.py (33 authored here + 4 concurrent preserved); no existing test modified
Skipped/xfail changes: none
Package evidence: N/A (no new dependency; i18n already packaged)
External evidence: N/A (remote rows keep W03 REQUIRES_EXTERNAL_VALIDATION)
Open P0/P1: 0 (owned)
Open P2/P3: 0 (owned)
Two-fix gate: PASS
Wave decision: PASS
```
