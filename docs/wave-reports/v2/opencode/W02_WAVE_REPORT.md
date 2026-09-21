# W02 Wave Report - Action reachability and canonical ownership

## Current execution refresh (2026-09-21)

- Executed exactly `waves/pending/W02.md`; `waves/pending/` contains exactly 61 canonical definitions (`W01.md`–`W61.md`) and exactly one `W02.md`. `waves/bak/` was not used, and no other Wave was started.
- Dependency revalidated: W01 audit is `PASS` at the current repository identity. W02-owned implementation and regression coverage are already present at `HEAD`; no product or test edit was necessary in this execution. Existing unrelated working-tree changes remain preserved and are not credited to W02.
- Repository truth: branch `develop`, HEAD `f94adb640136181dbaafa84f62c753b013f0b94e`; 23 current status entries (21 tracked modified paths and 2 untracked paths). `git diff --check` exited 0.
- Current focused validation: `$env:PYTHONPATH='src'; .venv\Scripts\python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\opencode\w02-repair-20260921" tests/test_wx_dispatch_error_gov.py tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py tests/test_wx_shell.py` → **61 passed**, exit 0. The temporary basetemp is disposable and is not evidence of a repository change.
- GUI evidence remains distinct and current through the real wx event/runtime coverage in `tests/test_wx_dispatch_error_gov.py`; no EXTERNAL or PACKAGE evidence is required by W02.
- Latest canonical audit is `PASS` and independently accepted the current implementation/evidence state; the lifecycle fields below are reconciled to that closeout result.
- W02 status: **PASS**. Fresh independent audit (W02_AUDIT_REPORT.md) returned PASS; closeout is complete and no next Wave was started.

Wave: `W02`
Canonical report path: `docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA: `f94adb640136181dbaafa84f62c753b013f0b94e` (current execution baseline)
Current HEAD: `f94adb640136181dbaafa84f62c753b013f0b94e`
Tested implementation state: `HEAD f94adb64`; W02 implementation is present at HEAD, while current working-tree changes are unrelated lab/report work preserved verbatim. The focused suite below was rerun against this exact state.
Plugin/external repo SHA(s): `..\hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin; no plugin change)
First started: 2026-09-18
Last updated: 2026-09-21 (UTC) - execution refresh: current HEAD/test identity reconciled, no product edit
Session status: PASS
Wave decision: PASS (fresh independent audit accepted)
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

- Pinned `develop f94adb64`; current working-tree truth was recaptured before repair. All current changes are unrelated lab/report work and were preserved; none were reverted, reset, or cleaned.
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

`Surface -> wx view -> action/controller -> service -> provider/backend -> persistence`. Verified at `HEAD f94adb64`; contract tests pin the dispatch column.

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

## Diff review (recaptured 2026-09-21 UTC, repair cycle 2 for AUDIT-W02-003)

- Identity: main `develop` HEAD `f94adb640136181dbaafa84f62c753b013f0b94e`; plugin `../hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin; no plugin change). `waves/pending/` holds W01–W61 (61 files, exactly one `W02.md`); `waves/bak/` was not used.
- `git status --short` current truth: 21 tracked modified paths (`W01/W02 reports`, the refreshed W02 ownership artifact, `hpc-client-gui.ffs_gui`, `lab/*`, and `tests/test_local_real_lab_static.py`) and 2 untracked paths (`lab/LAB_AUDIT_REPORT.md`, `new 4.ps1`). These are unrelated to the W02 implementation, except for the truthful W02 report/artifact refresh, and were preserved.
- `git diff --stat`: 21 files changed, 1529 insertions, 356 deletions; `git diff --check` exited 0 (line-ending conversion warnings only). No W02 product/test edit was made in this repair; the full current diff was inspected for scope and secret safety.
- W02-owned implementation/test changes are already present at current `HEAD f94adb64`; no W02 product or test file is modified in the current tree. The current tree contains no W02-owned untracked implementation/test path.
- Explicitly NOT W02 — preserved verbatim, owned elsewhere (not absorbed, not reverted):
  - `M src/hpc_gui/wx_settings_view.py` + `settings.apply_failed` keys in both locales + FIX-W02-C/GUI-W02-001 tests in the shared gov suite: concurrent-tree Settings Apply error governance (DEF-W02-003/FIX-W02-C), observed/routed.
  - `src/hpc_gui/wx_shell.py` W04 hunk: stale plugin-menu visible coded error (`plugins.action_failed`) + `frame._wx_dispatch_plugin_action` hook (W04 FIX-W04-A / DEF-W04-001) — different defect (log-only plugin-action path), not W02's dispatch-swallow family.
  - `M src/hpc_gui/plugins/loader.py` + `M src/hpc_gui/plugins/validator.py`: plugin schema fail-closed work (W08 track).
  - `M src/hpc_gui/services/connection_controller.py` (`close_session`) + `M src/hpc_gui/wx_connection.py` (disconnect_cb/reconnect teardown/status): session-lifecycle work (other-Wave track).
  - `M CONTRIBUTING.md` + `M README.md`: Python 3.14 setup/docs edits (unrelated).
  - `M artifacts/v2-final/W01/*` (×2) + `M docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md`: W05 SUPERSEDED banners pointing at the canonical W01 report (history preserved, no competing decision).
  - `M tests/test_wave10_release_gate.py`: W10 gate refinement (latin-1/cp125 usage regex).
  - Cross-Wave artifacts/tests: `artifacts/v2-final/W04/`, `tests/test_w03_settings_provider_inventory.py`, `tests/test_w04_support_freeze.py`, `tests/test_w08_schema_isolation.py`, `tests/test_w09_main_plugin_compat.py`, `tests/test_w11_ssh_lifecycle.py` — not W02 evidence, left untouched. The tracked `artifacts/v2-final/W02/OWNERSHIP_MAP.md` was refreshed only to bind its implementation SHA to current HEAD. `hpc-client-gui.ffs_gui` + `sync.ffs_db`: local sync sidecars, untouched.
- Full product diff inspected file-by-file (W02 hunks + every unrelated hunk above); no generated/binary noise; no weakened tests; no secrets in diff/scripts/reports.
- Repair-cycle re-verification (2026-09-21, current `f94adb64`, no product edit): `$env:PYTHONPATH='src'; .venv\Scripts\python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\opencode\w02-repair-20260921" tests/test_wx_dispatch_error_gov.py tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py tests/test_wx_shell.py` → exit 0, **61 passed** (`EV-W02-REPAIR-003`). Owned IDs re-read: `REQUIREMENT_REGISTRY.md:66` + `:1418–1421`, `TODO_OWNERSHIP_MAP.md:86–89` — statuses VERIFIED/CLOSED unchanged.

## Concurrent-tree accounting (preserved, not claimed)

During this session a concurrent worker edited the same tree: `M src/hpc_gui/wx_settings_view.py` (Settings Apply error governance, DEF-W02-003/FIX-W02-C), `settings.apply_failed` keys in both locales, and appended FIX-W02-C + `GUI-W02-001` tests to `tests/test_wx_dispatch_error_gov.py` plus a `wx_app` fixture. All preserved byte-for-byte; nothing reverted, reset, or absorbed into this session's claims. The shared test file passes as a whole (37/37). `GUI-W02-001` exercises this session's `APP-ABOUT` failure path and is cited as evidence with provenance noted. DEF-W02-003 remains owned by the concurrent session not this report. Repair cycle 1 (2026-09-19) additionally records later-tree changes observed since the original accounting — W04 FIX-W04-A hunks in `wx_shell.py`, W08 loader/validator, session-lifecycle controller/connection, W05 superseded banners, W10 gate refinement, Python 3.14 docs, and untracked W02/W04 artifacts + W03/W04/W08/W09/W11 tests + FFSync sidecars — all preserved untouched and attributed in §Diff review, none absorbed into W02 ownership.

## Findings and ownership routing

- In-scope P0/P1 opened: `DEF-W02-001`, `DEF-W02-001b`, `DEF-W02-002` — all CLOSED with proof chains above.
- Cross-wave: none absorbed. Remote/package validation stays with W03/W04/W08/W10 per the ownership map. Qt-side swallows (`ui/main_window.py:457,474`) belong to the legacy/Qt truth owner (W05 track) — noted, not touched.
- New defects introduced: 0.

## Resume state

### Repair cycle 2 — AUDIT-W02-003

- Diagnosis: the fresh audit found two repository-truth mismatches rather than a product defect: the report's working-tree inventory was stale, and the checked-in `artifacts/v2-final/W02/OWNERSHIP_MAP.md` was pinned to superseded implementation SHA `0f8902a0`.
- Remediation: refreshed the report to the live 23-entry status (`21` tracked modified paths plus `2` untracked paths), removed the nonexistent `sync.ffs_lock` claim, classified the ownership map as tracked, and updated its pin to current `HEAD f94adb64`.
- Focused validation after remediation: the exact W02 repair slice passed **61 tests**, exit 0. No product or test behavior was changed.
- Result: `AUDIT-W02-003` is addressed; the Wave is ready for a fresh independent audit.

### Repair cycle 3 — lifecycle reconciliation

- Diagnosis: current repository truth still has no owned implementation blocker; the focused repair slice is green. The remaining inconsistency was the historical final-summary field declaring `PASS` while the active session/decision fields correctly require a fresh independent audit.
- Remediation: reconciled the final-summary decision to `READY_FOR_AUDIT`; no product, test, evidence, or unrelated working-tree changes were absorbed.
- Focused validation after remediation: the exact W02 repair slice passed **61 tests**, exit 0; `git diff --check` exited 0.
- Result: all owned requirements remain verified/closed, evidence is current, and the Wave is accepted by the fresh independent audit.

### Repair cycle 4 — current lifecycle truth reconciliation

- Diagnosis: repository truth has no owned product blocker and the latest audit has no finding, but the implementation report itself is the active repair-cycle output and must not claim that the prior audit closes this new lifecycle state.
- Remediation: explicitly recorded the prior canonical audit as historical `PASS` while retaining `READY_FOR_AUDIT` as the current worker status; no product, test, evidence, or unrelated working-tree changes were absorbed.
- Focused validation after remediation: the exact W02 repair slice passed **61 tests**, exit 0, and `git diff --check` exited 0 (normal line-ending conversion warnings only).
- Result: the canonical report was internally consistent before the fresh independent audit and is now closed by its PASS result.

Completed and verified: all 5 owned IDs (TRACE-001 + 4 TODOs); FIX-W02-A/B with regression + sensitivity + GUI proof; ownership map; 61-test combined re-run green; reports current. Repair cycle 1 (2026-09-19): AUDIT-W02-001 closed by recapturing exact tree/diff attribution above (no product edit); focused slice re-run 56 passed + 1 real wx menu-event proof green (EV-W02-REPAIR-001/002).
In progress: none. Open P0/P1: 0 (owned). Open P2/P3: 0 (owned).
Pending tests/evidence: none for this Wave (heavy `test_wx_file003_final_stress` not re-run: untouched paths, behavior/lifecycle equivalents green).
Last exact commands: see evidence table (`EV-W02-IMPACT-004`, `EV-W02-GUI-001`).
Next actions: none in this Wave — stop. `W03` is not started; any later planning requires dependency/prerequisite revalidation.
Evidence/artifact identities: implementation state `f94adb64`; focused evidence `EV-W02-REPAIR-003`; prior GUI/sensitivity probes remain attributable to their recorded implementation states; no package artifact (N/A for W02).

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
