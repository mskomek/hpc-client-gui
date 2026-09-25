# W40 Wave Report — Localization, window state and runtime setting effects

```text
Wave: W40
Canonical report path: docs/wave-reports/v2/opencode/W40_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (working-tree changes uncommitted; controller owns commit/integration)
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W40 run phase)
Last updated: 2026-09-24
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W40.md` (wave_id W40, execution, 20 source rows + 17 TODO rows, start gate NONE, cohort P6-settings-split).
2. `opencode/REQUIREMENT_REGISTRY.md` rows owning Wave W40: `HPC-W09-UISTATE-001`..`020`.
3. `opencode/TODO_OWNERSHIP_MAP.md` rows owning Wave W40: `HPC-W09-TODO-005/006`, `VISUAL-CURRENT-001`, `TODO-015/016/017/018/019/020`, `A11Y-CURRENT-001`, `TODO-022/023`, `I18N-CURRENT-001`, `PUBLIC-SURFACE-CURRENT-001`, `EVIDENCE-FRESHNESS-001`, `MIGRATION-LANGUAGE-001`, `TODO-056`.
4. `opencode/sources/WAVE_V2_FINAL_09.md` → Workstream E1 (lines 151-164), E2 (166-179), E3 (181-191).
5. Live code before edits: `src/hpc_gui/core/i18n.py`, `src/hpc_gui/config/storage.py`, `src/hpc_gui/services/geometry_policy.py`, `src/hpc_gui/wx_shell.py`, `src/hpc_gui/wx_settings.py`, `src/hpc_gui/i18n/{en,tr}.json`, `README.md`, `src/hpc_gui/docs/{HELP,PLUGINS,CLI_GUIDE}_{en,tr}.md`.
6. Live tests before edits: `tests/test_wx_i18n.py`, `tests/test_wx_shell_i18n.py`, `tests/test_wave8_i18n_ui_ergonomics.py`, `tests/test_startup_i18n.py`, `tests/test_geometry_policy.py`, `tests/test_config_storage_atomic.py`, `tests/test_w37_settings_persistence.py`.

## Baseline capture

```text
Evidence ID: EV-W40-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files preserved untouched; W40 adds 4 focused implementation areas + 1 new test file, see diff review)
```

Narrow baseline before W40 edits is not separable from the shared dirty tree (parallel cohort P6 shares one working tree on `develop`). The W40 worker therefore baselined by focused suite, not by a clean tree: `tests/test_w40_localization_window_settings.py` (new) plus the impacted maintained cluster below were executed after edits; pre-existing suites listed in authority-read (6) were re-run as regression (all green, see evidence). No sibling file was reverted or merged by this worker.

Pre-existing dirty files NOT owned by W40 (preserved untouched): `core/diagnostics.py`, `core/ui_errors.py`, `core/wx_errors.py`, `plugins/*`, `services/command_history_store.py`, `services/files_ssh.py`, `services/output_follower.py`, `services/shortcut_preferences.py`, `services/slurm_models.py`, `ui/dialogs/plugin_manager_dialog.py`, `wx_editor_view.py`, `wx_jobs.py`, `wx_logs.py`, `wx_logs_view.py`, `wx_plugins.py`, `wx_plugins_view.py`, `wx_settings_view.py` (W37) except where W40 asserts live-apply declarations read-only. W40 touched only the files in EV-W40-DIFF.

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
DEF-W40-001 | P1 | i18n language contract open | load_language/set_language accepted any string, no SUPPORTED_LANGUAGES, no validation; t() returned [key] for merely-untranslated keys with no fallback | contract never enumerated after wx port | unsupported locale silently loads missing file (crash) or leaks raw [dotted.key] into menus/tabs | enumerate ("en","tr") + ValueError guard + cross-bundle fallback | YES (FIX-A) | FIXED+VERIFIED
DEF-W40-002 | P1 | main-window state not persisted | no get/save_main_window_state, no restore/save hooks in wx_shell create/close | never implemented in wx port | size/position/maximized/selected-tab lost every restart (E2 fully unmet) | storage record + geometry resolve + shell hooks | YES (FIX-B) | FIXED+VERIFIED
DEF-W40-003 | P1 | corrupt/off-screen/Qt-blob geometry unguarded | no resolve/recover/dispose path; Qt blobs could be misapplied | no migration disposition written | crash or invisible off-screen window on corrupt/multi-monitor state | resolve_main_window_state + recover_geometry clamp + dispose_legacy_qt_geometry_blob | YES (FIX-C) | FIXED+VERIFIED
DEF-W40-004 | P2 | public surface stale (Plugins entry) | README + HELP_en/tr described a top-right Plugins button that no longer exists | docs not updated after menubar migration | user follows dead instruction (PUBLIC-SURFACE) | menubar Plugins menu wording en+tr | YES (FIX-D) | FIXED+VERIFIED
OBS-W40-005 | N/A | splitter/column/dialog geometry | wx shell constructs splitters with fixed initial sash + sash gravity; no persistence call anywhere | deliberate product scope (E2 lists only main-window + conditional items) | fresh defaults every launch; conditional UISTATE-011/013/014 satisfied by explicit non-persistence | none (documented) | NO | VERIFIED
OBS-W40-006 | N/A | detached/plugin surfaces (TODO-020) | no W40-owned detached surface in final scope; plugin manager owned by W08/W35 | out of scope | integration hint only | none | NO | CLASSIFIED
```

Second-defect search (12 dimensions): negative paths checked (de/fr rejected without side effects; zero/negative sizes raise; corrupt/non-dict/Qt-keyed records resolve to defaults); lifecycle checked (close persists best-effort, never blocks shutdown; restore never raises); stale state checked (language.json + config.json re-read at call time, never cached; geometry resolved per-launch against live work areas); identity checked (notebook page objects identical across relabel; selection index preserved); concurrency checked (synchronous subscriber fan-out, no threads); boundary values checked (0/negative sizes, off-screen 5000x3000, tab 99 vs 7 pages); capability absence checked (wx missing → diagnostics path unaffected; no OS DPI API assumed); persistence checked (language.json roundtrip + restart-load; main-window save/restart roundtrip); packaging checked (N/A — no artifact built); error visibility checked (ValueError for bad language/size; folder errors N/A here); secondary entry checked (compact language popup shares set_language path with menubar); adjacent boundary checked (en/tr key sets identical; sibling editor/logs keys preserved). Result: no further defects beyond DEF-W40-001..004.

## Implementation

### FIX-A — closed language contract + fallback (DEF-W40-001, UISTATE-001/002/003/004/006)

- `src/hpc_gui/core/i18n.py::SUPPORTED_LANGUAGES = ("en", "tr")` — the exact user-selectable set; the wx shell exposes exactly these as menubar radio items plus the compact popup (current checked).
- `load_language`/`set_language` reject anything else with `ValueError` **before** state change or persistence (negative path tested).
- Effect model documented live: `set_language` notifies `subscribe_language_change` synchronously; `wx_shell.refresh_labels` is subscribed and relabels title/status/menus/tabs/dialogs/errors in place; `language` is absent from `wx_settings.RESTART_REQUIRED_KEYS` (asserted).
- `t()` falls back to the other shipped bundle before `[key]`; `[key]` only when both bundles lack the key (dev-time key error). Shipped `en.json`/`tr.json` key sets are identical (asserted programmatically).

### FIX-B — main-window persistence + restore (DEF-W40-002, UISTATE-009/010/012)

- `src/hpc_gui/config/storage.py::MAIN_WINDOW_STATE_KEY = "main_window"` + `get_main_window_state` (absent/corrupt/foreign → `None`, never raises) + `save_main_window_state` (`ValueError` on non-positive sizes so corruption can never be written) + `clear_main_window_state`.
- `src/hpc_gui/wx_shell.py::_restore_main_window_state` (create path: resolve against live `wx.Display` work areas, apply size/position/selection/maximize, best-effort never-raises) and `_save_main_window_state` (close path: persist geometry/selection/maximized first, best-effort, shutdown never blocks).
- Fresh defaults when no state: `Rect(0,0,1440,900)`, maximized False, selected_tab None. Save/restart roundtrip proven at both GUI and storage layers.

### FIX-C — safe geometry resolution + Qt-blob disposition (DEF-W40-003, UISTATE-009..015)

- `src/hpc_gui/services/geometry_policy.py::resolve_main_window_state` — corrupt/foreign records → fresh defaults; saved rect clamped via `recover_geometry` into a visible work area; `selected_tab` kept only when `0 <= selected < tab_count`.
- `dispose_legacy_qt_geometry_blob` — every Qt `saveGeometry`/`saveState` payload shape (bytes, base64 text, Qt-keyed dict) returns an explicit `ignored:` disposition; there is no Qt-blob ingestion path in the wx shell. A Qt-style record planted in config reads back as `None`.
- Splitter positions (UISTATE-011), column widths/order (UISTATE-013) and dialog geometry (UISTATE-014) are intentionally **not** persisted: the shell uses fixed initial sash + gravity and fresh dialog defaults every launch. The conditional requirements are therefore satisfied by explicit non-persistence (no silent contract).

### FIX-D — public-surface reconciliation (DEF-W40-004, PUBLIC-SURFACE-CURRENT-001)

- `README.md`: Plugins entry now reads menubar **Plugins** menu (**Browse & Install...**, **Manage Installed...**, **Check for Plugin Updates...**).
- `src/hpc_gui/docs/HELP_en.md` / `HELP_tr.md`: same correction, both languages.
- Verified: `README` contains "English and Turkish"; `HELP/PLUGINS/CLI_GUIDE × en/tr` all ship; `LICENSE` ships; shell source contains the `"APP-ABOUT"` acceptance surface (About dialog path asserted live).

### Settings effect ownership (UISTATE-016..020, no orphan controls)

- UISTATE-016 terminal → `terminal_graphics.normalize_settings` consumes the stored mode (asserted).
- UISTATE-017 files/transfers/editor → `get_remote_directory_cache_enabled`, `get_transfer_checksum_verification_enabled`, `coerce_profile_transfer_parallelism` live getters (asserted).
- UISTATE-018 jobs refresh/output → `get_jobs_outputs_refresh_interval_seconds` widget-consumed interval (asserted).
- UISTATE-019 plugin → `plugin_settings_survive_absence` namespaced survival (asserted).
- UISTATE-020 updater/log/language/window → `load_saved_language` + `get_main_window_state` startup-consumed paths (asserted callable + exercised).
- Live-apply declared: `remote_directory_cache`, `transfer_checksum`, `jobs_outputs_refresh_interval`, `transfer_parallelism` are in `LIVE_APPLY_KEYS` and mapped in `GLOBAL/PROFILE_STORAGE_KEYS` (read-only assertion; W37 owns the schema).

### Explicit classifications (no code change)

- `DEC-W40-VISUAL` (VISUAL-CURRENT-001, TODO-015/018): the `8414eee` visual/parity report is historical only. Current visual proof is runtime readback on this candidate: 7 tabs × 2 locales × 2 sizes (`1280×760`, `1440×900`) with zero off-screen/negative-size problems plus the canonical tab-order readback. No screenshots are produced by the headless harness; the assertions above are the retained equivalent evidence (test + report).
- `DEC-W40-NARROW` (TODO-016): no narrower mandatory size exists in the Wave authority; `1280×760` is the smallest exercised size. Narrower-window behavior is not claimed.
- `DEC-W40-DPI` (TODO-017): OS-level 150%/200% scaling proof is **manual acceptance** (controller-owned). It is not drivable unattended (no virtual-display DPI control in the harness) and is not faked here. Code-level mitigation: sizer-based layout, no hardcoded-pixel breakage observed at either size in either locale; high-DPI focus visibility covered at the keyboard-focus level below. No DPI-specific defect was found in code search.
- `DEC-W40-A11Y` (A11Y-CURRENT-001, TODO-022/023, TODO-056): keyboard half proven on this candidate (non-empty names, per-tab selection/focus restoration, menubar + labelled controls, terminal surface is the current WebView/xterm `build_terminal_panel` — old TextCtrl-terminal evidence explicitly not reused). Screen-reader certification and OS high-DPI focus-visibility certification remain manual acceptance; they are recorded, not faked.
- `DEC-W40-DETACHED` (TODO-020): no W40-owned detached surface exists in final scope; plugin surfaces are W08/W35 integration hints only.
- `DEC-W40-MIGRATION-LANGUAGE` (MIGRATION-LANGUAGE-001): language preference lives in `language.json` (`{"lang": ...}`); unknown values fall back to default, corrupt files fall back to default — both asserted. There is no Qt language-blob ingestion path; nothing to migrate beyond this file.
- `EVIDENCE-FRESHNESS-001`: every number below is bound to the candidate in this report header (base `c8293d3c` + working tree, 2026-09-24 runs). Any screenshot/audit from another commit is historical only.

## Tests and evidence

New: `tests/test_w40_localization_window_settings.py` — **25 passed** (real wx runtime where GUI is claimed; wxPython 4.3.1 msw).

| Requirement | Test | Evidence |
|---|---|---|
| UISTATE-001 | test_w40_uistate001_supported_languages_enumerated | `("en","tr")` + bundle files exist |
| UISTATE-002/004 | test_w40_uistate002_set_language_switches_current, _invalid_rejected_without_side_effects, test_w40_uistate004_persists_and_reloads | live switch en↔tr read back; de/fr raise, no write; `{"lang":"en"}` roundtrip + restart-load |
| UISTATE-003 | test_w40_uistate003_language_effect_is_live | subscriber saw `["en","tr"]`; `language ∉ RESTART_REQUIRED_KEYS` |
| UISTATE-005 | test_w40_uistate005_representative_surfaces_relabel | 13 keys relabelled en+tr, no `[` leakage |
| UISTATE-006 | test_w40_uistate006_missing_key_falls_back_not_raw_key, _shipped_bundles_have_no_key_drift | cross-bundle fallback `fallback-visible`; en/tr key sets identical |
| UISTATE-009..014 | test_w40_uistate009_fresh_defaults, _save_restart_roundtrip, test_w40_uistate010_maximized_and_tab, _corrupt_recovers, _offscreen_recovered, test_w40_uistate015_qt_blobs_never_drive | defaults `(1440,900)`; roundtrips; 6 corrupt shapes → positive sizes; off-screen clamped; tab 99 dropped; Qt blobs `ignored:` |
| UISTATE-016..020 | test_w40_uistate_settings_effect_ownership, _settings_live_apply_declared | every domain has a named live consumer; 4 keys in LIVE_APPLY + storage maps |
| MIGRATION-LANGUAGE-001 | test_w40_migration_language_preference | saved en wins; unknown → default; corrupt → default |
| I18N-CURRENT-001 | test_w40_i18n_every_shipped_language_exercised | en+tr set→persist→restart-load→relabel readback |
| PUBLIC-SURFACE-CURRENT-001 | test_w40_public_surface_matches_shipped_runtime | README/docs/LICENSE/About assertions |
| TODO-005 + UISTATE-002/005 GUI FULL | test_w40_gui_language_change_relabels_tabs_without_identity_change | real frame: en→tr relabels `Connection`→`Bağlantı`, same page objects, selection 2 kept |
| TODO-006 GUI FULL | test_w40_gui_menu_actions_have_stable_ids_and_labels | real menubar ≥5 menus, settings/check_updates/exit + help/logs/about + `{en,tr}` checked |
| UISTATE-009..014 GUI FULL | test_w40_gui_window_state_save_restore_roundtrip | real close persists `1280×760`+tab 4; real create restores both |
| TODO-015/018 + UISTATE-007/008 GUI FULL | test_w40_gui_layout_sizes_both_locales_no_clipped_geometry | 7 tabs × 2 locales × 2 sizes, zero problems |
| TODO-019 GUI FULL | test_w40_gui_canonical_tab_order_matches_wave01 | live `["Connection","Terminal","Jobs & Outputs","Directories","Files","Script Editor","Logs"]` |
| A11Y-CURRENT-001 + TODO-023/056 GUI FULL (keyboard half) | test_w40_gui_keyboard_accessibility_names_and_order | names non-empty, per-tab selection restore, controls labelled, WebView terminal surface |

Regression sweep (after edits): `test_w37_settings_persistence + test_w40` → **56 passed**. `test_geometry_policy + test_startup_i18n + test_wx_i18n + test_wx_shell_i18n + test_wave8_i18n_ui_ergonomics + test_config_storage_atomic` → **29 passed**. `git diff --check` → clean (exit 0; only standard LF→CRLF notices).

Evidence classes: `GUI` (required) → FULL via 6 real-wx runtime tests above (real `wx.App`/frames/menus/notebook events/pumped loop/readback). Package → N/A (no artifact built or claimed). External HPC → N/A (no external system touched; language/window/settings surface is connection-independent).

## Diff review

```text
Evidence ID: EV-W40-DIFF
git diff --check: clean
Files changed with W40-owned hunks (4 implementation areas + docs + 1 new test):
  src/hpc_gui/core/i18n.py              (FIX-A: SUPPORTED_LANGUAGES, validation, fallback)
  src/hpc_gui/config/storage.py         (FIX-B: main_window record get/save/clear)
  src/hpc_gui/services/geometry_policy.py (FIX-C: resolve/recover/dispose)
  src/hpc_gui/wx_shell.py               (FIX-B hooks + live relabel subscription; sibling editor-validation hunks preserved untouched)
  src/hpc_gui/i18n/en.json + tr.json    (sibling editor/logs keys preserved; parity asserted, no W40 key added/removed)
  src/hpc_gui/wx_settings.py            (read-only LIVE_APPLY assertion target; schema owned by W37, untouched)
  README.md                             (FIX-D plugins-menu wording)
  src/hpc_gui/docs/HELP_en.md + HELP_tr.md (FIX-D both languages)
  src/hpc_gui/docs/PLUGINS_en.md + PLUGINS_tr.md (sibling hunks preserved untouched)
  tests/test_w40_localization_window_settings.py (new, 25 tests)
```

Secrets scan: no credentials, tokens, keys, or user/host literals added; `language.json`/`config.json` fixtures use isolated tmp roots; i18n diffs are UI strings only. No binary/generated noise. No weakened tests (all assertions are positive behavioral checks; modal popups auto-neutered by `tests/conftest.py`).

## Cross-scope routing

No cross-scope defects fixed opportunistically. Sibling dirty files (W26–W39 surfaces: diagnostics, plugins, jobs, editor, logs, settings schema) were not touched; W40 asserts against them read-only where the Wave requires a consumer proof. One finding is routed, not fixed here: none — no concrete defect in another Wave's owned IDs was found during the second-defect search.

## Handoff

Worker requests independent audit. Resume point: none — work is complete; candidate is the current working tree on `develop` at base `c8293d3c` plus the W40 files listed above (uncommitted; commit/integration is controller-owned).

```text
Candidate identity: working tree on develop @ c8293d3ca309526ed250c794c3b294f7c54ef369 + W40 diff (EV-W40-DIFF)
Focused tests: 25 passed (W40 new) + 56 passed (w37+w40 cluster) + 29 passed (i18n/geometry/config cluster)
GUI runtime: wxPython 4.3.1 msw — 6 real-wx tests (relabel-identity/menus/save-restore/layout-sizes/tab-order/keyboard-a11y)
Manual acceptance remaining (controller-owned, not faked): OS 150%/200% DPI proof (DEC-W40-DPI), screen-reader certification (DEC-W40-A11Y)
```
