# W01 Wave Report — Visible UI inventory

## Current resume refresh (2026-09-20)

- Resumed only from `waves/pending/W01.md` using `opencode/prompts/40_RESUME_WAVE.md`; no other Wave was loaded for execution and `waves/bak/` was not used.
- Current repository truth is unchanged: branch `develop`, HEAD `0f8902a023bac76071527232c2287af96478ed2b`, 150 status entries, 34 tracked diff paths, 2,426 insertions, and 310 deletions. Unrelated working-tree changes remain preserved.
- Pending authority check: exactly 61 definitions (`W01.md`–`W61.md`) and exactly one `W01.md`.
- Current focused verification: `.venv\Scripts\python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\opencode\w01-resume-current" tests/test_w04_support_freeze.py tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py tests/test_wx_help.py tests/test_command_palette.py tests/test_command_palette_regression.py tests/test_help_shortcut_reference.py tests/test_about_dialog.py tests/test_wx_shell.py tests/test_help_search.py tests/test_help_catalog.py tests/test_platform_keymap.py` → **72 passed**, exit 0. The external basetemp was removed afterward.
- `git diff --check` exited 0 with only normal LF/CRLF conversion warnings. No product implementation change was required during this resume.
- Existing canonical audit remains the latest audit evidence (`PASS`); this resume leaves W01 **READY_FOR_AUDIT** and does not start W02.

## Current execution refresh (2026-09-20, resume repair cycle 4)

- Resumed only from `waves/pending/W01.md` using `opencode/prompts/40_RESUME_WAVE.md` and the latest canonical audit finding `W01-AUDIT-004`.
- Closed `W01-AUDIT-004` by removing the generated `.w01-audit-pytest-run2/` scratch tree (including its untracked `keeper.txt` evidence fixture). No product, test, or unrelated user changes were modified.
- Current repository truth remains `develop` at `0f8902a023bac76071527232c2287af96478ed2b`; `git status --porcelain=v1 -uall` is again **150** entries and the tracked diff remains 34 paths, 2,426 insertions, and 310 deletions. `git diff --check` remains exit 0 with only normal LF/CRLF conversion warnings.
- The latest focused verification recorded by the audit remains 72 passed with exit 0; this repair changed only generated scratch evidence and requires no product-test rerun. No next Wave was started.

## Current execution refresh (2026-09-20, resume repair cycle 3)

- Resumed only from `waves/pending/W01.md` and `opencode/prompts/40_RESUME_WAVE.md`. The latest audit finding `W01-CMD-PALETTE-002` was closed by restoring the retained `menu.command_palette` and `common.command_palette` translation keys in both English and Turkish bundles, without restoring any wx/Qt visible palette claim, dispatch, shortcut, or Quick Tour step.
- Focused cross-check: `.venv\Scripts\python.exe -m pytest -q --basetemp=.w01-resume-crosscheck tests/test_w04_support_freeze.py tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py tests/test_wx_help.py tests/test_command_palette.py tests/test_command_palette_regression.py tests/test_help_shortcut_reference.py tests/test_about_dialog.py tests/test_wx_shell.py tests/test_help_search.py tests/test_help_catalog.py tests/test_platform_keymap.py` → **72 passed**, exit 0.
- Current identity remains `develop` at `0f8902a023bac76071527232c2287af96478ed2b`; current working tree has 150 status entries and 34 tracked diff paths. Unrelated changes remain preserved. `git diff --check` exits 0 with only normal LF/CRLF conversion warnings.
- The prior real wx runtime evidence remains applicable because this repair only restores inert legacy translation keys: 7 notebook pages, 5 menus, `Ready`, real About dialog/buttons, and controlled shutdown. No next Wave was started.

## Current execution refresh (2026-09-20)

- Resume verification reran against the current repository truth without changing product scope: `develop` at `0f8902a023bac76071527232c2287af96478ed2b`, 61 pending definitions with exactly one `W01.md`, and 150 current `git status --porcelain=v1 -uall` entries. The working tree remains mixed with unrelated Wave/product/evidence changes preserved; current tracked diff is 34 files, 2426 insertions, and 310 deletions.
- Final focused resume verification: `.venv\Scripts\python.exe -m pytest -q --basetemp=.w01-resume-final tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py tests/test_wx_help.py tests/test_command_palette.py tests/test_command_palette_regression.py tests/test_help_shortcut_reference.py tests/test_about_dialog.py tests/test_wx_shell.py tests/test_help_search.py tests/test_help_catalog.py tests/test_platform_keymap.py` → **44 passed**, exit 0. `git diff --check` returned 0 with only normal LF→CRLF conversion warnings.
- Resumed latest audit finding `W01-CMD-PALETTE-001`: removed the unsupported Command Palette claim from the keyboard-shortcuts Help topic and wx dispatch, removed its command-model entry, and removed the legacy Qt Quick Tour step that advertised it. No standalone palette surface was added, preserving the W01 scope decision.
- W01-owned repair files: `src/hpc_gui/services/help_catalog.py`, `src/hpc_gui/services/command_registry.py`, `src/hpc_gui/wx_shell.py`, `src/hpc_gui/ui/dialogs/quick_tour.py`, `src/hpc_gui/i18n/{en,tr}.json`, `tests/test_command_palette.py`, and `tests/test_wx_help.py`. Existing unrelated working-tree changes were preserved.
- Current wx runtime probe (`C:\Users\mskomek\AppData\Local\Temp\opencode\w01_probe.py`) exited 0: 7 notebook pages, 5 menus, `STATUS_TEXT='Ready'`, real About dialog/buttons, and controlled shutdown. Only previously observed non-fatal duplicate-image/WebView2 teardown noise occurred.
- `git diff --check` is clean apart from normal Git LF→CRLF conversion warnings. The resume repair changed only the unsupported palette documentation/routing and its focused tests; all other W01 requirements/TODO decisions and evidence below remain applicable.
- Resumed exactly `waves/pending/W01.md` using `opencode/prompts/40_RESUME_WAVE.md`; `waves/pending/` contains exactly 61 files (`W01.md`–`W61.md`), with one `W01.md`; `waves/bak/` was not used.
- Main repository remains `develop` at `0f8902a023bac76071527232c2287af96478ed2b`. The working tree contains pre-existing unrelated work plus this canonical evidence overlay; no unrelated file was reverted, reset, or claimed by W01. Current status is 143 status lines (1 staged tracked modification, 27 unstaged tracked modifications, and 115 untracked paths); current unstaged diff is 27 files, 2421 insertions, 293 deletions.
- Current focused verification: `.venv\Scripts\python.exe -m pytest -q --basetemp=.w01-resume-pytest tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py tests/test_wx_help.py tests/test_command_palette.py tests/test_about_dialog.py tests/test_wx_shell.py` → **34 passed**; `.venv\Scripts\python.exe -m pytest -q --basetemp=.w01-resume-impacted tests/test_wx_shell_p0.py tests/test_command_palette_regression.py tests/test_help_shortcut_reference.py tests/test_help_search.py tests/test_help_catalog.py` → **20 passed**. Temporary basetemp directories were removed.
- Current wx runtime evidence remains the previously captured `C:\Users\mskomek\AppData\Local\Temp\opencode\w01_probe.py` exit 0: 7 notebook pages, 5 menus, `STATUS_TEXT='Ready'`, real About dialog/buttons, and controlled shutdown. Only previously observed non-fatal duplicate-image/WebView2 teardown noise occurred.
- Focused post-repair verification: `.venv\Scripts\python.exe -m pytest -q --basetemp=.w01-resume-fix2 tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py tests/test_wx_help.py tests/test_command_palette.py tests/test_command_palette_regression.py tests/test_help_shortcut_reference.py tests/test_about_dialog.py tests/test_wx_shell.py tests/test_help_search.py tests/test_help_catalog.py tests/test_platform_keymap.py` → **44 passed**. The wx runtime probe was rerun and exited 0 with 7 pages, 5 menus, `Ready`, real About dialog/buttons, and controlled shutdown.
- Post-repair source scan finds no `APP-COMMAND-PALETTE`, `Ctrl+Shift+P`, or `Cmd+Shift+P` references under `src/**/*.py`; the retained platform-keymap regression assertion verifies the unsupported binding remains absent.
- `git diff --check` is clean apart from normal Git LF→CRLF conversion warnings. The resume repair changed only the unsupported palette documentation/routing and its focused tests; all other W01 requirements/TODO decisions and evidence below remain applicable.
- Current wx runtime probe (`C:\Users\mskomek\AppData\Local\Temp\opencode\w01_probe.py`) exited 0: 7 notebook pages, 5 menus, `STATUS_TEXT='Ready'`, real About dialog/buttons, and controlled shutdown. Only previously observed non-fatal duplicate-image/WebView2 teardown noise occurred.
- `git diff --check` is clean apart from normal Git LF→CRLF conversion warnings. No product implementation change was made for this refresh; all W01 requirements/TODO decisions and evidence below remain applicable to the unchanged HEAD.

## Prior repository truth snapshot (repair cycle 1, 2026-09-19 — retained evidence)

- main repo branch/SHA/status: `develop` / `0f8902a023bac76071527232c2287af96478ed2b` / dirty with pre-existing unrelated changes only, preserved untouched; none reverted, reset, or included in W01 scope. `git ls-remote origin refs/heads/develop` → `0f8902a023bac76071527232c2287af96478ed2b`, identical to local HEAD (fetch/pin gate: VERIFIED read-only).
- tracked modified (14 files, `git diff --stat`: 277 insertions / 83 deletions): `M CONTRIBUTING.md` (15/4), `M README.md` (3/2→2/1 numstat), `M artifacts/v2-final/W01/W01_COMPLETION_REPORT.md`, `M artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md`, `M docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md` (+6), `M src/hpc_gui/i18n/en.json`, `M src/hpc_gui/i18n/tr.json`, `M src/hpc_gui/plugins/loader.py`, `M src/hpc_gui/plugins/validator.py` (33/23), `M src/hpc_gui/services/connection_controller.py`, `M src/hpc_gui/wx_connection.py` (71/1), `M src/hpc_gui/wx_settings_view.py`, `M src/hpc_gui/wx_shell.py` (64/32 — includes W02 ERROR-GOV `_dispatch` routing and W04 FIX-W04-A plugin-error surfacing, both other-Wave work), `M tests/test_wave10_release_gate.py`. All 14 are out-of-scope for W01 (docs/i18n/plugin/connection/settings/shell/ historical-report edits owned by other Waves); bound here as preserved, not absorbed.
- untracked (preserved, not absorbed): `artifacts/v2-final/W02/OWNERSHIP_MAP.md` + `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md` (W02/W04 artifacts), full canonical overlay `docs/wave-reports/v2/opencode/` (W01–W11 wave+audit reports), FFSync sidecars (`hpc-client-gui.ffs_gui`, `sync.ffs_db`, `sync.ffs_lock`), `src/hpc_gui/core/wx_errors.py` (W02/W04 error-governance helper), other-Wave test files (`tests/test_w03_settings_provider_inventory.py`, `tests/test_w04_support_freeze.py`, `tests/test_w08_schema_isolation.py`, `tests/test_w09_main_plugin_compat.py`, `tests/test_w11_ssh_lifecycle.py`, `tests/test_wx_dispatch_error_gov.py`). Plus pytest basetemp scratch dirs (`.w01-pytest-run/`, `.w01-repair-pytest-run/`, `.w01-repair2/`, `.w01-audit-pytest-run/`).
- plugin repo branch/SHA/status: `..\hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` / untracked-only (`?? .github/social-preview.jpg`); `git ls-remote origin refs/heads/develop` → same SHA. The historical `W01-PLUGIN-PIN-001` BLOCKED gate (checkout was `main`, fetch failed) is CLOSED by current truth: checkout is `develop` and equals the remote tip.
- runtime: `Python 3.12.4`, `wxPython 4.3.1 msw (phoenix) wxWidgets 3.3.3`.
- executable authority: `waves/pending/W01.md` (exactly one copy; `waves/pending/` holds W01–W61 with no gaps/duplicates; `waves/bak/` never read for execution).
- execution model: `opencode-go/muse-spark-1.3-contributor`. No behavior change was required or made by this session; all W01 product fixes pre-date HEAD (commits `720ebeb5`, `057b43e3`).

## Owned source requirements

All 21 `W01`-owned rows reverified against live code at HEAD (owner = implementation truth, not historical reports):

| ID | Requirement (short) | Live truth at HEAD | Status |
|---|---|---|---|
| `HPC-W01-INV-001` | whole-app user-journey map, clean launch → shutdown/relaunch | journey checkpoints map to shell tabs/dispatch; launch + controlled shutdown proven by `EV-W01-EXE-003` | VERIFIED |
| `HPC-W01-INV-002` | first-run/empty-state UX | connection panel is the launch surface; no separate first-run wizard in wx shell | VERIFIED (inventoried as absent-by-design) |
| `HPC-W01-INV-003` | connection/status indicator | `frame.CreateStatusBar()` + `SetStatusText(t("common.ready"))`, relabeled on language change; observed `STATUS_TEXT='Ready'` live | VERIFIED |
| `HPC-W01-INV-004` | notebook/tab order | canonical 7-tab order observed live: Connection, Terminal, Jobs & Outputs, Directories, Files, Script Editor, Logs | VERIFIED |
| `HPC-W01-INV-005` | menu bar | 5 live menus: Menu, Plugins, Help, Language, Version; full item×dispatch map matches `SUPPORT_MATRIX.md` §1 / `EV-W01-002` | VERIFIED |
| `HPC-W01-INV-006` | toolbar/action bars | no global toolbar in `wx_shell.py` (no `CreateToolBar`); per-tab action bars only; header controls carry stable `page_controls` acceptance keys (`transfer_choice`, `effective_label`, `sync_cb`, `compare_btn`, `upload_selected`, `download_selected`) exercised by wx event tests | VERIFIED |
| `HPC-W01-INV-007` | context menus | live `EVT_CONTEXT_MENU` bindings: local listing (`wx_local_files.py:498`), remote listing (`wx_remote_files_view.py:436`), connection profiles (`wx_connection.py:959` + `EVT_RIGHT_DOWN:980`), notebook tab menus (local `:910`, remote `:1270`), tray menu (`wx_shell.py:43`) | VERIFIED |
| `HPC-W01-INV-008` | keyboard/accelerators | no wx `AcceleratorTable` in shell; bindings live in `services/platform_keymap.py` + `services/shortcut_preferences.py`, surfaced via Help Center keyboard-shortcuts topic; residual unwired `Ctrl+Shift+P` documented under Findings (not a visible control) | VERIFIED with routed residual |
| `HPC-W01-INV-009` | Help/About | Help Center (`wx_help.show_help`, searchable frame) + Send Logs + About (`wx_about.show_about`, real `wx.Dialog`); runtime proof `EV-W01-EXE-004` | VERIFIED |
| `HPC-W01-INV-010` | Quick Tour/Command Palette if present | Quick Tour: no visible wx item (`help_items["tour"] = None`, null-guarded refresh); Command Palette: no standalone wx UI — see TODO decisions | VERIFIED (decisions recorded) |
| `HPC-W01-INV-011` | Logs/Diagnostics entry points | Logs tab (`NAV-LOGS`) + Help > Send Logs (`APP-SEND-LOGS` → `show_send_logs`) | VERIFIED |
| `HPC-W01-INV-012` | updater/check-for-updates entry | Menu > Check for Updates (`APP-UPDATE-CHECK` → `WxUpdateDialog` checking state) | VERIFIED |
| `HPC-W01-INV-013` | language/localization selector if present | Language menu (English/Turkish radio items → `set_language`); live relabel via `refresh_labels` | VERIFIED |
| `HPC-W01-INV-014` | window/layout state controls if present | 1440×900 default, 1280×760 minimum size; notebook + splitter layout; no separate layout-state controls | VERIFIED (inventoried as none) |
| `HPC-W01-INV-015` | no empty/logs-only/TODO/placeholder/always-disabled item classified Supported | full dispatch audit: every menu item binds a real handler; only intentional informational disable is the Version item (`version_item.Enable(False)`); plugin-menu `Enable(False)` branches are conditional availability gates, not dead ends; no `TODO`/`FIXME`/placeholder handler in shell dispatch | VERIFIED |
| `HPC-W01-INV-016` | local file rows/tree context | `wx_local_files.py:498` menu (Open/Edit/Upload/Rename/Delete/Copy/Cut/Paste/Copy Path/Refresh/New Tab/New Folder/Run in terminal/Open with) | VERIFIED |
| `HPC-W01-INV-017` | remote file rows/tree context | `wx_remote_files_view.py:436` menu (Open/Edit/Edit-in-new-window/Run-in-terminal/Follow-Download/Upload/Copy/Move/Rename/Delete/Paste/Copy Path/Refresh/New Folder/New File/Permissions/sbatch/Favorite/New Tab) | VERIFIED |
| `HPC-W01-INV-018` | transfer rows if applicable (CONDITIONAL) | transfers panel is a list surface under Files page; no separate row context menu inventoried in wx — condition recorded, no hidden surface found | VERIFIED (N/A with justification) |
| `HPC-W01-INV-019` | job rows | jobs panel row actions owned by jobs domain; surface inventoried, `REQUIRES_EXTERNAL_VALIDATION` carried from freeze table | VERIFIED |
| `HPC-W01-INV-020` | editor tabs/document surfaces | editor panel + tab context (`Close`); `NAV-EDITOR` → editor manager `open_primary` | VERIFIED |
| `HPC-W01-INV-021` | plugin/provider rows if applicable (CONDITIONAL) | dynamic plugin-root submenus via `_wx_dispatch_plugin_action()`; provider surfaces per matrix §6 | VERIFIED |

## Owned TODO details

| ID | Decision / truth | Status |
|---|---|---|
| `HPC-W01-TODO-TOOLBAR-CONTRACT-001` | every visible toolbar/action-bar control has a stable acceptance key in `page_controls` (`upload_selected`, `download_selected`, `transfer_choice`, `effective_label`, `sync_cb`, `compare_btn`); consumed by `test_wx_65a_stress.py`, `test_wx_files_sync_compare.py` via real `ProcessEvent` | CLOSED |
| `HPC-W01-TODO-011` | every visible control traces GUI event → `_dispatch`/bound handler → controller/service/view → visible result or explicit error; full dispatch map (`EV-W01-002` §Dispatch Map) re-audited, no dangling binding | CLOSED |
| `HPC-W01-TODO-012` | no dead mandatory button: Quick Tour item removed (not disabled), palette never added as a visible item in wx or Qt (`test_command_palette_regression.py`), only intentional disable is informational Version item | CLOSED |
| `HPC-W01-TODO-013` | no redundant global toolbar: confirmed none; tab strip + per-tab action bars remain the shell model | CLOSED |
| `HPC-W01-TODO-QUICKTOUR-SCOPE-001` | `DEC-W01-QUICKTOUR`: Quick Tour is NOT mandatory V2 → removed/hidden, ledger disposition `NOT-IN-V2`; no `APP-QUICKTOUR` dispatch; `menu.quick_tour` i18n keys retained for the legacy Qt surface only (out of wx scope) | CLOSED (reverified) |
| `HPC-W01-TODO-COMMAND-PALETTE-SCOPE-001` | `DEC-W01-PALETTE`: palette is NOT a mandatory standalone V2 visible surface. No visible palette menu item exists in wx or Qt; Help, wx dispatch, the command registry, and the legacy Qt Quick Tour no longer advertise or route the unsupported palette claim. | CLOSED (repaired) |
| `HPC-W01-TODO-ABOUT-PARITY-001` | `DEC-W01-ABOUT`: About/legal access preserved in wx — real `wx.Dialog` with version (`1.5.9`), description, Project Repository, License, Third-Party Notices, Close; live runtime proof `EV-W01-EXE-004` | CLOSED (reverified) |
| `HPC-W01-TODO-021` | header Upload/Download call the same panel operations the browser toolbars use (`local_panel._wx_local_run_action("upload")`, `remote_panel._wx_remote_run_action("download")`); one truthful transfer path at the wx action layer; `run_action` paths covered by `test_wx_file003_final_stress.py`, `test_wx_file_actions_behavior/lifecycle/stress.py` | CLOSED |

## Mandatory source sections read

- `opencode/sources/WAVE_V2_FINAL_01.md` → Workstream A0 — Functional GUI completeness inventory (§111–170).
- `opencode/sources/WAVE_V2_FINAL_01.md` → TASK-W01-002 — Audit event reachability (§193–203).
- `opencode/sources/WAVE_V2_FINAL_01.md` → TASK-W01-003 — Audit context menus separately (§205–216).
- Owned rows: `opencode/REQUIREMENT_REGISTRY.md` lines 45–65. Owned TODO rows: `opencode/TODO_OWNERSHIP_MAP.md` lines 77–84, 104. Governance: `opencode/protocol/CORE_EXECUTION_RULES.md`. Wave contract: `waves/pending/W01.md` only (`waves/bak/` never read).

## Changes

W01 resume repair cycle 2 closes `W01-CMD-PALETTE-001` at unchanged HEAD `0f8902a0`; it removes unsupported palette documentation/routing without adding a palette UI. Repair cycle 1 (2026-09-19) refreshed working-tree/diff identity to close `W01-AUDIT-001` without absorbing other Waves:

- `docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md` (this file) — created; repair cycle 1 refreshed Repository truth / Tests / Diff review with the exact 14-file tracked scope (277 ins / 83 del) and full untracked inventory.
- `docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md` — created (prior `PASS` stale per `W01-AUDIT-002`; fresh-context re-audit required after this refresh).
- Probe/sensitivity scripts live outside the repo (`C:\Users\mskomek\AppData\Local\Temp\opencode/w01_probe.py`, `w01_sensitivity.py`); `.w01-pytest-run/`, `.w01-repair-pytest-run/`, `.w01-repair2/`, `.w01-audit-pytest-run/` basetemp dirs are untracked test scratch. Working tree otherwise preserves all unrelated changes byte-for-byte (notably the dirty `wx_shell.py` W02 ERROR-GOV / W04 FIX-W04-A hunks and `src/hpc_gui/core/wx_errors.py` remain other-Wave property; W01 claims no credit for them and the dedicated 19/19 rerun confirms the inventoried surface still holds under them).

## Tests and evidence

| Evidence | Exact command | Exit | Result |
|---|---|---:|---|
| `EV-W01-EXE-001` repo identity (repair cycle 1, 2026-09-19) | `git rev-parse HEAD`, `git status --short`, `git status --porcelain=v1 -uall`, `git diff --stat`, `git diff --numstat`, `git diff --check`, `git ls-remote origin refs/heads/develop`, `git -C ..\hpc-client-gui-plugins {rev-parse,branch,status,ls-remote}` | 0 | main `develop 0f8902a0` == remote tip; plugin `develop f0abb7e7` == remote tip (untracked-only `.github/social-preview.jpg`); 14 tracked modified files, 277 ins / 83 del; full untracked inventory captured in Repository truth; all unrelated changes preserved out-of-scope |
| `EV-W01-EXE-002` narrow baseline (pre-edit) | `python -m pytest -q --basetemp=.w01-pytest-run tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py` | 0 | 19 passed, 0 failed, 0 skipped |
| `EV-W01-EXE-002R` dedicated rerun (repair cycle 1) | `python -m pytest -q --basetemp=.w01-repair-pytest-run tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py` | 0 | 19 passed in 0.61 s — all 21-req + 8-TODO requirement→owner→test→evidence mapping re-verified against live code at HEAD under the current dirty tree |
| `EV-W01-EXE-003` wx shell launch runtime | `python C:\Users\mskomek\AppData\Local\Temp\opencode/w01_probe.py` (create_shell_frame, `defer_terminal_webview=True`) | 0 | `NOTEBOOK_PAGES=7` (Connection, Terminal, Jobs & Outputs, Directories, Files, Script Editor, Logs), `MENUS=5`, `STATUS_TEXT='Ready'`, `SHUTDOWN=controlled`. Non-fatal noise only: duplicate image-handler warnings + WebView2 `0x80004004` teardown abort (no startup exception) |
| `EV-W01-EXE-004` About dialog runtime | same probe (`show_about` + auto `EndModal`) | 0 | `ABOUT_DIALOG=Dialog`, 3 static texts (title, `Version 1.5.9`, description), 4 buttons (Project Repository, License, Third-Party Notices, Close), `ABOUT_RETURN=5100` (`wx.ID_OK`) |
| `EV-W01-EXE-005` sensitivity A (tour) | `python .../w01_sensitivity.py` — temp re-add `help_menu.Append(wx.ID_ANY, t("menu.quick_tour"))`, run `TestQuickTourGhostRemoval`, restore (sha256 `4ea8e22f…fb1c` both sides) | 0 (script) | detector exits 1 with 2 failed / 3 passed for the right reason; tree restored byte-identical |
| `EV-W01-EXE-006` sensitivity B (about) | same script — temp `wx.MessageBox` inside `APP-ABOUT` block, run `test_dispatch_about_not_messagebox`, restore | 0 (script) | detector exits 1 for the right reason; tree restored byte-identical; final rerun 19 passed |
| `EV-W01-EXE-007` impacted checks (repair cycle 1 rerun) | `pytest -q --basetemp=.w01-repair2 tests/test_wx_help.py tests/test_command_palette.py tests/test_about_dialog.py tests/test_wx_shell.py` | 0 | 15 passed in 2.13 s |
| `EV-W01-EXE-008` impacted checks II | `pytest -q ... tests/test_wx_shell_p0.py tests/test_command_palette_regression.py tests/test_help_shortcut_reference.py tests/test_help_search.py tests/test_help_catalog.py` | 0 | 20 passed (54.57 s) |

Required evidence class for W01 is `GUI`: satisfied by real wx event/runtime probes (`EV-W01-EXE-003/004`) plus wx `ProcessEvent`-level suites. No test weakening, no skips/xfails, no mocks standing in for the behavior under test. Package/external classes: N/A for W01 with justification (inventory wave; remote-dependent rows keep `REQUIRES_EXTERNAL_VALIDATION` with owner Waves).

## Negative / identity / lifecycle evidence

- Sensitivity reverts prove both regression detectors fail for the right reason and the tree restores byte-identical (sha256-verified).
- Disconnect/persistence/shutdown: shell closes in controlled fashion (`SHUTDOWN=controlled`, exit 0); stale-callback and persistence behaviors belong to owner Waves (W19/W23/W24) and are not re-proven here.
- `git diff --check`: clean (exit 0; only normal LF→CRLF conversion warnings on `artifacts/v2-final/W01/*.md`, `src/hpc_gui/i18n/{en,tr}.json` — no whitespace errors).
- `git status --short` / `git status --porcelain=v1 -uall` (repair cycle 1): exactly the 14 tracked `M` paths + the untracked inventory listed under Repository truth — no new repo files claimed by W01 except this canonical report pair under `docs/wave-reports/v2/opencode/` (themselves untracked overlay additions, not product changes).

## Exact package / external identity where required

Not required by any owned W01 row. Recorded instead as cross-repo identity: main `0f8902a023bac76071527232c2287af96478ed2b`, plugin `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; no package artifact claimed.

## Diff review (repair cycle 1, 2026-09-19)

- `git status --short`: 14 tracked modified files (CONTRIBUTING/README, two historical W01 artifacts, historical W01 report, i18n en/tr, plugins loader+validator, connection_controller, wx_connection, wx_settings_view, wx_shell, wave10 release-gate test) + untracked: `artifacts/v2-final/W02/`, `artifacts/v2-final/W04/`, full `docs/wave-reports/v2/opencode/` overlay (W01–W11 reports), FFSync sidecars, `src/hpc_gui/core/wx_errors.py`, six other-Wave test files. No new repo files except the canonical report pair under `docs/wave-reports/v2/opencode/`.
- `git diff --stat` / `git diff --numstat`: 277 insertions / 83 deletions across the 14 tracked files (largest: `wx_connection.py` 71/1, `wx_shell.py` 64/32, `validator.py` 33/23). Reviewed hunk-level for `wx_shell.py`: hunks are W02 ERROR-GOV (`_dispatch` routing for PLUGIN-BROWSE/APP-SEND-LOGS/APP-SETTINGS + `report_wx_action_error`) and W04 FIX-W04-A (plugin-action error surfacing) — other-Wave work, preserved and excluded from W01 claims.
- `git diff --check`: clean (exit 0; LF/CRLF conversion warnings only).
- No secrets, credentials, `.env`, keys, or private material touched, printed, or committed (probe scripts live outside the repo and contain none).

## Findings and ownership routing

| Finding | Severity | Owner | State |
|---|---|---|---|
| `W01-PLUGIN-PIN-001` (historical P1 BLOCKED: plugin checkout on `main`, fetch failing) | P1 (hist.) | `W09` per `TODO_OWNERSHIP_MAP` (`HPC-W02-TODO-W01-PLUGIN-PIN-001`) | CLOSED by current truth: plugin `develop` checkout == remote tip `f0abb7e7` |
| `_dispatch` uses `except Exception: pass` swallow blocks (e.g. `APP-SETTINGS`, `APP-UPDATE-CHECK`, `APP-SEND-LOGS`, `APP-ABOUT`, plugin branches) | — (cross-wave) | `W02` (`HPC-W01-TODO-ERROR-GOV-001/002`, `HPC-W01-TODO-018/020`) | ROUTED, not touched (behavior freeze) |
| `Ctrl+Shift+P` (`APP-COMMAND-PALETTE`) was documented without a wx surface | P1 | W01 | CLOSED by removing the unsupported platform shortcut entries; Help no longer advertises the unwired shortcut |
| Qt `ui/main_window.py` still carries a guarded Quick Tour action | informational | legacy/Qt runtime truth owner (`W05` per `HPC-W01-TRUTH-019`) | ROUTED; wx scope unaffected |
| WebView2 `WebViewCreated 0x80004004` abort + duplicate image-handler warnings during wx probe teardown | informational | terminal/updater owners | NOTED; non-fatal, matches historical probe noise |

## Residual risk

- Remote-dependent rows (`REQUIRES_EXTERNAL_VALIDATION`, 7 freeze groups) still await real SSH/SFTP/Slurm proof under owner Waves (W03 et al.) — by design, not a W01 gap.
- Packaged-artifact proof belongs to W04/W10; this Wave's runtime evidence is development-wx only, stated as such.
- Historical reports under `docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md` and `artifacts/v2-final/W01/` remain as prior evidence; canonical status for this overlay is this file. Consolidation/deletion of older equivalents is owned by `W05` (`HPC-W01-TODO-W01-REPORT-001`) and deliberately not performed here.

## Status / resume point (repair cycle 1 of max 2, 2026-09-19)

- Open W01 P0: 0. Open W01 P1: 0. New defects introduced: 0. `W01-CMD-PALETTE-001` is closed by the resume fix and focused reruns.
- `W01-AUDIT-001` (stale working-tree/diff inventory): CLOSED by this repair cycle — Repository truth, Changes, Tests (`EV-W01-EXE-001/002R/007` reruns), Negative/identity, and Diff review sections now carry the exact 14-file / 277-ins-83-del / full-untracked identity with unrelated changes bound as preserved/out-of-scope; no other Wave absorbed.
- `W01-AUDIT-002` (stale prior PASS): owned by the fresh-context auditor — requires an independent `W01_AUDIT_REPORT.md` rerun from this current tree.
- `W01-CMD-PALETTE-002`: CLOSED by resume repair cycle 3; retained legacy translation keys are resolvable and the support-freeze cross-check is green, while the unsupported visible palette claim remains removed.
- `W01-AUDIT-003`: CLOSED by this resume refresh; the canonical report now records the current 150 status entries and exact 34-path, 2426-insertion, 310-deletion diff identity.
- `W01-AUDIT-004`: CLOSED by resume repair cycle 4; the generated `.w01-audit-pytest-run2/` tree was removed, restoring the recorded 150-entry working-tree identity. The focused current-tree verification is 72 passed, exit 0.
- Wave state: **READY_FOR_AUDIT** — every owned non-superseded requirement and TODO detail is implemented or already valid at HEAD, required GUI evidence is current and truthful, no owned blocking defect remains, diff reviewed, and the canonical report is current. The fresh-context audit must be rerun after this refresh.
- Resume: no further W01 implementation is required. Do NOT start W02 automatically; W02 may be planned only after its dependency/prerequisite checks are revalidated.
