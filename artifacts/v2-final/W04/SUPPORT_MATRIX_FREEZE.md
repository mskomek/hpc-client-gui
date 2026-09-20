# W04 — Frozen Support Classification and Evidence Matrix

**Wave:** `W04` (executable authority: `waves/pending/W04.md`; `waves/bak/` never read)
**Pinned main HEAD:** `0f8902a023bac76071527232c2287af96478ed2b` (`develop`)
**Carried plugin pin (read-only, not re-pinned here):** `..\hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb`
**Supersedes (as current truth, history preserved):** `artifacts/v2-final/W01/SUPPORT_MATRIX.md` (pinned at `afd4fb1d…`; counts there marked non-authoritative by its own §8)
**Owned requirements:** `HPC-W01-TRUTH-047…072`, `076…083` + TODOs `HPC-W01-TODO-W01-DISPOSITION-001`, `HPC-W01-TODO-W01-SUPPORT-EVIDENCE-001`, `HPC-W01-TODO-W01-GUI-PROOF-001`
**Contract tests:** `tests/test_w04_support_freeze.py` (`EV-W04-AFTER-001`)
**GUI proof:** `EV-W04-GUI-001` (real wx launch/event/runtime probe, Temp script outside repo)

## Disposition vocabulary (TRUTH-047…054, frozen)

| State | Meaning at this freeze |
|---|---|
| `SUPPORTED` | Evidence-backed at the cited evidence IDs. Never assigned merely because a source handler exists. |
| `EXPERIMENTAL` | Implemented but required runtime/package evidence or stability proof is incomplete; every such row carries an open gap. |
| `REQUIRES_EXTERNAL_VALIDATION` | Implementation exists but real SSH/SFTP/Slurm (or equivalent external) proof is still required. Used exactly for backend-dependent rows, never as a synonym for `EXPERIMENTAL`. |
| `HIDDEN` | Implemented but intentionally not exposed. Count at this freeze: **0** (no baseline-visible feature is hidden-with-implementation at HEAD; removals are `NOT-IN-V2`). |
| `UNSUPPORTED` | Visible-but-not-working surface the product does not stand behind. Count at this freeze: **0** (no such surface found; gaps are `EXPERIMENTAL` with owners, not silent `UNSUPPORTED`). |
| `DEPRECATED` | Persisted/read for migration only; not user-facing. |
| `NOT-IN-V2` | Baseline-visible candidate explicitly excluded from the V2 wx surface with a decision ID. |

## Frozen matrix (TRUTH-055/056/077 + TODO SUPPORT-EVIDENCE-001/DISPOSITION-001)

Disposition is separated from evidence class: `Required evidence class` vs `Current evidence class` are distinct columns, and every row carries a `Verification owner Wave` and an `Open gap` (TODO `W01-SUPPORT-EVIDENCE-001`). Baseline-removed rows retain their ID and final disposition (TRUTH-056, TODO `W01-DISPOSITION-001`).

| ID | Surface | Action | UI owner | Service/provider | Config | Implementation owner | Verification owner Wave | Required evidence class | Current evidence class | Support disposition | Open gap | Evidence IDs | Decision ID |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `MENU-SETTINGS` | Menu > Settings | `APP-SETTINGS` | `wx_shell` menu | `wx_settings_view.show_settings` | global + profile config | W01 | W37 | GUI | GUI (open path only) | EXPERIMENTAL | `DEF-W03-001`: shell Apply persists nothing → W37 | `EV-W01-EXE-003`, `EV-W02-AFTER-001` | — |
| `MENU-UPDATE` | Menu > Check for Updates | `APP-UPDATE-CHECK` | `wx_shell` menu | `wx_updater_view.WxUpdateDialog` (checking state) | release feed | W01 | W10 | GUI | GUI (dialog-open only) | EXPERIMENTAL | real feed + packaged proof → W10 | `EV-W02-AFTER-001` | — |
| `MENU-EXIT` | Menu > Exit | `frame.Close()` | `wx_shell` menu | wx native | — | W01 | — (native) | GUI | GUI | SUPPORTED | none | `EV-W01-EXE-003` | — |
| `PLUGIN-BROWSE` | Plugins > Browse & Install | `PLUGIN-BROWSE` | `wx_shell` menu | `wx_plugins_view.show_plugins(discover)` | plugin registry | W01 | W35 | GUI | GUI (listing rows=2) | EXPERIMENTAL | distinct-state truthfulness + install backend → W35 (`PLUGIN-GUI-001/002`); package → W08/W10 | `EV-W03-GUI-001`, `EV-W02-AFTER-001` | — |
| `PLUGIN-MANAGE` | Plugins > Manage Installed | `PLUGIN-MANAGE` | `wx_shell` menu | `wx_plugins_view.show_plugins(installed)` | plugin registry | W01 | W35 | GUI | GUI (listing) | EXPERIMENTAL | distinct views (`PLUGIN-GUI-002`) → W35 | `EV-W03-GUI-001` | — |
| `PLUGIN-UPDATES` | Plugins > Check for Plugin Updates | `PLUGIN-UPDATES` | `wx_shell` menu | `wx_plugins_view.show_plugins(updates)` | plugin registry | W01 | W35 | GUI | GUI (listing) | EXPERIMENTAL | real update resolution → W35 | `EV-W03-GUI-001` | — |
| `PLUGIN-ROOTS` | Plugins > dynamic plugin roots | per-plugin dispatch | `wx_shell._wx_rebuild_plugins_menu` | `services/plugin_menu_actions` (capability-gated) | plugin manifest capabilities | W01 | W35/W08 | GUI | GUI (gating + FIX-W04-A visible errors) | EXPERIMENTAL | lifecycle/install semantics → W35; packaged discovery → W08 | `EV-W04-AFTER-001`, `EV-W04-GUI-001` | — |
| `PLUGIN-REQUEST` | Plugins > Request Plugin | `PLUGIN-REQUEST` | `wx_shell` menu | `webbrowser.open(PLUGIN_REQUEST_URL)` | constant URL | W01/W02 | — | GUI | GUI | SUPPORTED | none (`False`/exception → coded `PLUGIN-XXXXXX` error) | `EV-W02-AFTER-001` | — |
| `HELP-CENTER` | Help > Help Center | `APP-HELP` (+`APP-COMMAND-PALETTE` alias) | `wx_shell` menu | `wx_help.show_help` (searchable; `WxHelpModel.palette_search` backend) | bundled docs | W01 | W10/W11 | GUI | GUI (launch) + source/event trace | EXPERIMENTAL | outcome/bundle proof replay → W10/W11 | `EV-W01-EXE-003` | `DEC-W01-PALETTE` (palette discovery surface) |
| `HELP-SEND-LOGS` | Help > Send Logs | `APP-SEND-LOGS` | `wx_shell` menu | `wx_send_logs_view.show_send_logs` | local logs | W01 | W10/W11 | GUI | source/event trace + failure governance | EXPERIMENTAL | bundle proof replay → W10/W11 | `EV-W02-AFTER-001` | — |
| `HELP-ABOUT` | Help > About | `APP-ABOUT` | `wx_shell` menu | `wx_about.show_about` (real `wx.Dialog`; FIX-W01-002) | `__version__` | W01 | W10 | GUI | GUI (real dialog runtime) | SUPPORTED | packaged replay → W10 | `EV-W01-EXE-004`, `EV-W04-AFTER-001`, `EV-W04-GUI-001` | `DEC-W01-ABOUT` |
| `SHELL-LANGUAGE` | Language > English/Turkish | `set_language` | `wx_shell` language menu | i18n bundles | `language.json` | W01 | W09/W10 | GUI | source/event trace | EXPERIMENTAL | runtime relabel/persistence replay → W09/W10 | `EV-W01-EXE-003` | — |
| `VERSION-INFO` | Version menu (disabled item) | — (informational) | `wx_shell` version menu | `__version__` label | — | W01 | — | GUI | GUI | SUPPORTED | none (intentional disable, not a dead end) | `EV-W01-EXE-003` | — |
| `SHELL-MAIN` | Menus, notebook (7 tabs), status bar | shell frame | `wx_shell.create_shell_frame` | panel builders | layout prefs | W01 | W10/W11 | GUI | GUI (launch + navigation inventory) | SUPPORTED | full journey replay later | `EV-W01-EXE-003`, `EV-W04-GUI-001` | `DEC-W01-SHELL` |
| `APP-CONNECT` | Connection tab | `APP-CONNECT` | notebook p0 | `wx_connection.show_connection` | profiles store | W01 | — | GUI | GUI | SUPPORTED | none for the tab surface (opens locally); live-connect proof belongs to each connection attempt, not this row | `EV-W01-EXE-003` | — |
| `NAV-TERMINAL` | Terminal tab | `NAV-TERMINAL` | notebook p1 | `wx_terminal` (SSH shell; disconnected → warning + `ID_CANCEL`) | live session | W01 | W03 (inventory done)/W05/W10 | GUI + external | source/event trace + disconnected-gate proof | REQUIRES_EXTERNAL_VALIDATION | real SSH/PTY + GUI journey proof | `EV-W04-AFTER-001` (gate), `EV-W01-R5-007` (ref) | `DEC-W01-TERMINAL` |
| `NAV-JOBS` | Jobs & Outputs tab | `NAV-JOBS` | notebook p2 | `wx_jobs` (Slurm backend) | live session | W01 | W03/W07/W10 | GUI + external | source/event trace | REQUIRES_EXTERNAL_VALIDATION | real Slurm job lifecycle proof | `EV-W01-R5-008` (ref) | `DEC-W01-JOBS` |
| `NAV-DIRECTORIES` | Directories tab | `NAV-DIRECTORIES` | notebook p3 | `wx_directories_view` (SFTP) | live session | W01 | W03/W06/W10 | GUI + external | source/event trace | REQUIRES_EXTERNAL_VALIDATION | real SSH/SFTP lifecycle proof | `EV-W01-R5-009` (ref) | `DEC-W01-DIRECTORIES` |
| `NAV-FILES` | Files/transfers tab | `NAV-FILES` | notebook p4 | local + remote panels, transfer controllers | live session (remote leg) | W01 | W03/W06/W10 | GUI + external | GUI (local) + source trace | REQUIRES_EXTERNAL_VALIDATION | remote transfer proof | `EV-W01-R5-010` (ref) | `DEC-W01-FILES` |
| `NAV-EDITOR` | Script Editor tab | `NAV-EDITOR` | notebook p5 | `wx_editor_view` + editor manager | local FS / session (remote leg) | W01 | W06/W07/W10 | GUI | GUI (local lifecycle) + source/event trace | EXPERIMENTAL | integrated remote/plugin paths | `EV-W01-R5-011` (ref) | `DEC-W01-EDITOR` |
| `NAV-LOGS` | Logs tab | `NAV-LOGS` | notebook p6 | `wx_logs_view` + log service | local logs | W01 | W09/W10 | GUI | source/event trace | EXPERIMENTAL | lifecycle/redaction replay | `EV-W01-R5-012` (ref) | `DEC-W01-LOGS` |
| `FILES-TRANSFER-TYPE` | Transfer type choice | `_on_transfer_choice` → session state | Files header | session state | transfer prefs | W01 | W06/W10 | GUI | GUI (event) | SUPPORTED | remote-leg proof → W06/W10 | `test_wx_65a_stress`, `test_wx_files_sync_compare` | — |
| `FILES-EFFECTIVE` | Effective-mode label | display only | Files header | session state | — | W01 | — | GUI | GUI | SUPPORTED | none | `test_wx_65a_stress` | — |
| `FILES-SYNC` | Synchronized browsing checkbox | `_on_sync_toggle` | Files header | session state | — | W01 | — | GUI | GUI | SUPPORTED | none | `test_wx_files_sync_compare` | — |
| `FILES-COMPARE` | Compare directories button | `_on_compare` | Files header | compare service | — | W01 | W06 | GUI | GUI | SUPPORTED | remote compare → W06 | `test_wx_files_sync_compare` | — |
| `FILES-UPLOAD` | Upload selected button | `_header_upload` → local `run_action("upload")` (single path) | Files header | transfer controllers | live session (remote leg) | W01 | W06/W10 | GUI | GUI (single-path pin) | SUPPORTED | remote transfer proof → W06/W10 | `EV-W04-AFTER-001` (single path) | — |
| `FILES-DOWNLOAD` | Download selected button | `_header_download` → remote `run_action("download")` | Files header | transfer controllers | live session | W01 | W06/W10 | GUI | GUI | SUPPORTED | remote transfer proof → W06/W10 | `EV-W01-EXE-003` | — |
| `CTX-LOCAL` | Local listing context (15 actions) | `dirs.*` / `editor.open` / `files.open_with` | `wx_local_files` | local FS ops | — | W01 | — | GUI | GUI | SUPPORTED | none (delete guarded by `YES_NO` + `ICON_WARNING` confirm) | `EV-W04-AFTER-001` | — |
| `CTX-REMOTE` | Remote listing context (20 actions) | `dirs.*` | `wx_remote_files_view` | SFTP ops | live session | W01 | W06/W10 | GUI + external | GUI (construction/gating) + source/event trace | REQUIRES_EXTERNAL_VALIDATION | real SFTP proof; `chmod`/`sbatch`/`new_file`/`favorite` filtered when capability absent | `EV-W04-AFTER-001` (gating) | — |
| `CTX-PROFILES` | Profile list context (Connect/Edit/Duplicate/Delete) | `login.*` / `connection.*` | `wx_connection` | profile store | profiles store | W01 | W03 (store inventory done) | GUI | GUI + source/event trace | SUPPORTED | live-connect proof per use | `EV-W03-AFTER-001` | — |
| `CTX-TRAY` | Tray > Close | `wx.ID_EXIT` | `wx_shell` tray | wx native | — | W01 | — | GUI | GUI | SUPPORTED | none | `EV-W01-EXE-003` | — |
| `CTX-TABCLOSE` | Notebook tab context > Close | `common.close` | local/remote views | tab model | — | W01 | — | GUI | GUI | SUPPORTED | none | W01 inventory | — |
| `SET-DLG` | Settings dialog (4 value controls) | `APP-SETTINGS` open | `wx_settings_view` | `WxSettingsModel` | `config.json` + side stores | W01/W03 | W37 | GUI | GUI (4 controls enumerated, staged snapshot) | EXPERIMENTAL | `DEF-W03-001` persistence reunion → W37 | `EV-W03-GUI-001` | `DEC-W01-SETTINGS` |
| `SET-HIDDEN` | Hidden-capability settings (jobs interval, sbatch mode, lssrv toggles, shortcut prefs, keepalive/x11 in connection dialog, transfer/CLI prefs) | programmatic + connection dialog | connection dialog / owning service | consuming services (jobs/transfer/CLI/shortcut/connection) | config stores | W03 | — | source contract | source contract (W03 pins, live consumers of record) | SUPPORTED | none (intentional; consumers pinned) | `EV-W03-AFTER-001` | — |
| `SET-LEGACY` | Migration-only keys (global `transfer_parallelism`, `focus_jobs_outputs_after_submission_enabled`) | migration read | — (no UI) | `migrate_legacy_transfer_parallelism`, `get_sbatch_follow_mode` | legacy config | W01/W03 | W09 | source contract | source contract | DEPRECATED | migration closeout → W09 | `EV-W03-AFTER-001` | `DEC-W01-LEGACY-SETTINGS` |
| `SET-OBSOLETE` | Ignored Qt keys (`terminal_graphics_auto_compatibility`, `qt_webengine_gpu`) | `LEGACY_IGNORED_KEYS` | — (no UI) | `config/storage` | — | W03 | W09 | source contract | source contract | DEPRECATED | none (explicitly ignored, never consumed; removal with migration closeout) | `EV-W03-AFTER-001` | — |
| `PROVIDER-LABEL` | Connection provider label | display | `wx_connection` | provider contract | profile provider id | W02/W03 | W03 (done)/W08 | GUI | GUI + contract tests | SUPPORTED | packaged discovery → W08 | `EV-W03-IMPACT-001` | — |
| `PROVIDER-SELECTOR` | Profile editor provider/template selector | select | `wx_connection_dialog` | plugin templates | profile store | W02/W03 | W08 | GUI | GUI + contract tests | SUPPORTED | packaged proof → W08 | `EV-W03-IMPACT-001` | — |
| `PROVIDER-TEMPLATES-POPUP` | System templates popup (builtin/plugin/user) | popup | `wx_connection_dialog` | builtin/plugin/user templates | template stores | W02/W03 | W02/W03/W08 | GUI + package | source trace + plugin SHA | REQUIRES_EXTERNAL_VALIDATION | live/provider/package validation → W02/W03/W08 | `EV-W01-R5-014` (ref) | `DEC-W01-PROVIDER` |
| `PROVIDER-VALIDATION` | Provider-required field validation | validate | `wx_connection_dialog` | provider schema | profile draft | W02/W03 | — | GUI | GUI + contract tests | SUPPORTED | none | `EV-W03-IMPACT-001` | — |
| `PROVIDER-SELFTEST` | Cluster self-test button | self-test | `wx_connection_dialog` | capability probes | live session | W01 | W03 | GUI + external | source/event trace | REQUIRES_EXTERNAL_VALIDATION | real backend proof | `EV-W01-R5-007` (ref) | — |
| `PROVIDER-QUOTA` | Quota controls (per provider) | gate display | `wx_connection_dialog` | `quota_monitor.quota_gate` (six-state contract) | provider declaration | W02/W03 | W02 (declaration done)/W03 (live probe) | source contract + GUI | source contract + unit test | SUPPORTED | live probe with declaring provider | `EV-W02-AFTER-001`, `EV-W03-AFTER-001` | — |
| `PLUGIN-SEARCH` | Plugin Manager search box | filter (current: no-op `on_search`) | `wx_plugins_view` | — (unimplemented) | registry cache | W03 (inventory) | W35 | GUI | GUI (surface enumerated, behavior pinned) | EXPERIMENTAL | `DEF-W03-002`: real filter → W35 (`PLUGIN-SEARCH-001`) | `EV-W03-GUI-001` | — |
| `PLUGIN-REFRESH` | Plugin Manager refresh | refresh (current: simulated, always `cached`) | `wx_plugins_view` | registry source | registry | W03 (inventory) | W35 | GUI | GUI | EXPERIMENTAL | `DEF-W03-002`: real source resolution → W35 (`PLUGIN-REFRESH-001`, `PLUGIN-OFFLINE-001`) | `EV-W03-GUI-001` | — |
| `PLUGIN-INSTALL-BTN` | Plugin Manager install button | install | `wx_plugins_view` | installer backend | network/registry | W01 | W35/W08 | GUI + external | source/event trace | REQUIRES_EXTERNAL_VALIDATION | installer backend (`PLUGIN-INSTALL-001`) + packaged proof | `EV-W01-R5-013` (ref) | `DEC-W01-PLUGIN-MANAGER` |
| `PLUGIN-TOGGLE` | Plugin disable/enable toggle | toggle | `wx_plugins_view` | plugin registry | `active.json` | W03 (inventory) | W35 | GUI | GUI (surface) | EXPERIMENTAL | backend wiring proof → W35 (`PLUGIN-GUI-001`) | `EV-W03-GUI-001` | — |
| `PLUGIN-REMOVE` | Plugin remove button | remove | `wx_plugins_view` | registry | plugin root | W03 (inventory) | W35 | GUI | GUI (surface) | EXPERIMENTAL | backend proof → W35 | `EV-W03-GUI-001` | — |
| `PLUGIN-SOURCE-LABEL` | Status label (network/cache/offline) | display | `wx_plugins_view` | registry source | — | W03 (inventory) | W35 | GUI | GUI | EXPERIMENTAL | deterministic source proof → W35 (`PLUGIN-OFFLINE-001`) | `EV-W03-GUI-001` | — |
| `ANSYS-LINT` | ANSYS lint UI (pick/lint/table/copy) | `PLUGIN-ANSYS-LINTER` / `APP-ANSYS` | `wx_ansys_view` | linter engines (lazy, trust-gated) | local files | W03 (inventory) | — | GUI | GUI + source contract | SUPPORTED | none (local; trust gate pinned) | `EV-W03-AFTER-001` | — |
| `ANSYS-DOC-URL` | Open documentation URL | `webbrowser.open` | `wx_ansys_view` | OS browser | constant URL | W01 | — | GUI | GUI | SUPPORTED | none (external link) | W01 inventory | — |
| `ADAPTER-SCONTROL` | `slurm.scontrol.job` adapter | query | services | live Slurm | live session | W02 | W02 (reachability done)/W03 (execution) | external (real backend) | source contract + integration test | REQUIRES_EXTERNAL_VALIDATION | real execution proof | `EV-W02-AFTER-001` | — |
| `ADAPTER-SACCT` | `slurm.sacct.job` adapter | query | services | live Slurm | live session | W02 | W02 (reachability done)/W03 (execution) | external (real backend) | source contract + integration test | REQUIRES_EXTERNAL_VALIDATION | real execution proof | `EV-W02-AFTER-001` | — |
| `ADAPTER-LSSRV` | `truba.lssrv` adapter | query | services | live TRUBA | live session | W02 | W02 (reachability done)/W03 (execution) | external (real backend) | source contract + integration test | REQUIRES_EXTERNAL_VALIDATION | real execution proof | `EV-W02-AFTER-001` | — |
| `CAPS-DECLARED` | Plugin capabilities (`cluster-profile`, `lint-rules`, `job-template`, `application-tools`, `linter-tool`) | declare | plugin manifest | schema/registry | manifests | W02 | W02 (declaration done)/W08 (packaged discovery) | source contract | schema/registry tests | SUPPORTED | packaged discovery → W08 | `EV-W02-AFTER-001` | — |
| `APP-QUICKTOUR` | Quick Tour (baseline-visible ghost, removed) | — (no dispatch; `help_items["tour"] is None`) | — | — (no wx implementation) | — | W01 | W10/W11 | specification-compatible disposition + GUI inventory | source/runtime inventory | NOT-IN-V2 | public-surface replay remains later | `EV-W01-EXE-005`, `EV-W04-AFTER-001` | `DEC-W01-QUICKTOUR` |
| `APP-PALETTE-STANDALONE` | Command Palette standalone UI (never shipped) | — (`APP-COMMAND-PALETTE` aliases to Help Center) | Help Center (discovery surface) | `WxHelpModel.palette_search` | shortcut prefs | W01 | W38 (shortcut wiring) | specification-compatible disposition | source/event trace | NOT-IN-V2 | `Ctrl+Shift+P` documented but unwired as wx accelerator → shortcuts owner | `EV-W01-EXE-007` | `DEC-W01-PALETTE` |

## Exact freeze totals

| Disposition | Count |
|---|---:|
| SUPPORTED | 24 |
| EXPERIMENTAL | 17 |
| REQUIRES_EXTERNAL_VALIDATION | 11 |
| DEPRECATED | 2 |
| NOT-IN-V2 | 2 |
| HIDDEN | 0 (justified: no hidden-with-implementation surface at HEAD) |
| UNSUPPORTED | 0 (justified: no visible-but-disowned surface at HEAD) |
| **Total rows** | **56** |

## Negative/edge-case verdicts (TRUTH-065…072, frozen truth with test pins)

| Case | Verdict at HEAD | Pin |
|---|---|---|
| disabled action enabled at wrong lifecycle | plugin actions lacking capability render disabled **and unbound**; remote op buttons disable without an operation callback | `EV-W04-AFTER-001` (capability-gate GUI test) |
| action available while disconnected | terminal-without-session warns (`login.status_disconnected`) + `ID_CANCEL`, never a dead terminal | `EV-W04-AFTER-001` (disconnected gate) |
| stale menu/context state after reconnect | Plugins menu rebuilds on every `EVT_MENU_OPEN`; stale plugin click now raises a visible coded `PLUGIN-XXXXXX` error (FIX-W04-A) instead of a silent no-op | `EV-W04-AFTER-001`, `EV-W04-GUI-001` |
| provider capability shown when provider lacks it | lacking capability → `can_execute_action == (False, reason)` → menu item disabled + unbound; remote `chmod`/`sbatch`/`new_file`/`favorite` filtered from context when unsupported | `EV-W04-AFTER-001` |
| duplicated command with divergent handlers | header Upload/Download call the same panel `run_action` paths as the browser toolbars (one truthful transfer path, W01 TODO-021) | `EV-W04-AFTER-001` (single-path pin) |
| destructive/non-destructive label semantics | local + remote Delete both require `YES_NO` + `ICON_WARNING` confirmation; labels match the confirmed-destructive action | `EV-W04-AFTER-001` (confirm-style pin) |
| dead localization keys masking missing UI | `menu.quick_tour` / `menu.command_palette` resolve but bind to **no** wx visible item (`help_items["tour"] is None`); retained for the legacy Qt surface only, ledgered as `NOT-IN-V2`, never presented as supported UI | `EV-W04-AFTER-001` (no-wx-binding pin) |
| log-only error paths leaving success-looking UI | `_dispatch` branches governed (W02); `_wx_dispatch_plugin_action` stale-click + exception paths now report visible coded errors (FIX-W04-A, `DEF-W04-001` CLOSED) | `EV-W04-AFTER-001`, `EV-W04-SENS-001` |

## Test-matrix coverage (TRUTH-057…064)

| Layer | Required proof | W04 proof |
|---|---|---|
| Static discovery | no untracked visible surfaces in sampled menus/tabs/context menus | menu/dispatch ledger test: every `_dispatch("…")` literal in `wx_shell.py` resolves to a freeze row; 5 top-level menus + 7-tab order pinned by GUI probe |
| Event binding | each Supported/Experimental action has reachable handler | real `EVT_MENU` → view-function routing tests (Settings/About/Help/Send-Logs/Update/Plugins) |
| Service path | handler reaches meaningful implementation | routing tests assert the canonical owner (e.g. `show_about`, `show_help`, `show_plugins`) is invoked with the shell parent |
| Settings | visible option changes an owned value or is classified honestly | `WxSettingsModel` round-trip pins + `SET-DLG` honestly `EXPERIMENTAL` with `DEF-W03-001` gap (no behavior change here; W37 owns the reunion) |
| Plugin/provider | capability exposure matches declared contract | `can_execute_action` allow/capability pins + capability-gate GUI test + quota absent-vs-failed distinction carried from W03 |
| Runtime | representative actions produce visible state/result/error | `EV-W04-GUI-001`: launch (7 pages, 5 menus, `Ready`), About real dialog, stale plugin action → coded error, controlled shutdown |
| Packaging | not required for every row yet; package-dependent gaps marked for W04+ | N/A with justification: W04 claims **no** package artifact; every package-dependent row carries `→ W08/W10` in `Open gap`; no `SHA-256` is cited because no artifact is bound |

## Findings

| Finding ID | Severity | Surface | Evidence | Root cause | Fix | Status |
|---|---|---|---|---|---|---|
| `DEF-W04-001` | P1 | `_wx_dispatch_plugin_action` (dynamic plugin menu dispatch, `wx_shell.py`) | pre-fix source: `plugin is None → return` + `except → log-warning only` | stale-click/exception paths invisible; UI left success-looking | FIX-W04-A: both paths report visible coded `PLUGIN-XXXXXX` errors via `report_wx_action_error` (+ `plugins.action_failed` keys en/tr) | CLOSED (regression + sensitivity + GUI proof) |

No other in-scope defect: the freeze vocabulary, matrix, ledger, and negative cases above are otherwise already truthful at HEAD (W01–W03 evidence carried, not re-proven). `DEF-W03-001` (W37) and `DEF-W03-002` (W35) remain routed, untouched, and cited as open gaps — not absorbed.
