# W03 Wave Report — Settings and provider surface inventory

Wave: `W03`
Canonical report path: `docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA: `0f8902a023bac76071527232c2287af96478ed2b`
Current HEAD: `0f8902a023bac76071527232c2287af96478ed2b`
Tested implementation state: `HEAD 0f8902a0` on `develop` PLUS the full working tree below (14 tracked modifications + 12 untracked paths, all preserved; every cited suite re-ran 2026-09-19 against this exact dirty tree — see EV-W03-REPAIR-001/002/003)
Plugin/external repo SHA(s): `..\hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (clean except one untracked sidecar `.github/social-preview.jpg`); re-pinned 2026-09-19, no plugin change in scope
First started: 2026-09-18
Last updated: 2026-09-19 (UTC) — repair cycle 1: rebound all evidence to the current dirty tree per Luna audit AUD-W03-001 REOPEN
Session status: COMPLETE
Wave decision: PASS
Executable authority: `waves/pending/W03.md` (exactly one copy; `waves/pending/` holds W01–W61, 61 files, no gaps/duplicates; `waves/bak/` never read for execution)
Execution model: `opencode-go/muse-spark-1.3-contributor`
Dependency: `W02` — `docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md` decision `PASS`, audit `PASS`; entry revalidated (same pins, no owned W02 blocker touches this scope)

## Owned requirements and TODO details

20 source-derived requirements, 0 TODO details. All VERIFIED (inventory frozen + pinned by contract tests + GUI proof) except two routed observations below, which belong to other Waves by TODO ownership and are not absorbed here.

| ID | Kind | Status |
|---|---|---|
| `HPC-W01-TRUTH-027` | settings keys and defaults | VERIFIED — §Settings inventory; `test_w03_settings_keys_and_defaults_are_frozen` |
| `HPC-W01-TRUTH-028` | UI controls for settings | VERIFIED — 4 bound wx controls enumerated + GUI-proven; §Settings inventory |
| `HPC-W01-TRUTH-029` | persistence location | VERIFIED — `<app_data_dir>/config.json` + side stores; `test_w03_settings_persist_to_config_json`, `test_w03_config_path_is_app_data_config_json` |
| `HPC-W01-TRUTH-030` | migration/versioning owner | VERIFIED — `migrate_legacy_transfer_parallelism`, sbatch legacy-bool source, profile-id stamping; 2 migration pins |
| `HPC-W01-TRUTH-031` | sensitive values | VERIFIED — persisted `password` always empty, secrets via keychain/DPAPI/master refs; `test_w03_saved_profile_never_persists_plaintext_password` |
| `HPC-W01-TRUTH-032` | settings consumed only by obsolete code | VERIFIED — legacy Qt keys classified `LEGACY_IGNORED_KEYS`; `test_w03_obsolete_qt_keys_are_explicitly_ignored` |
| `HPC-W01-TRUTH-033` | runtime options with no UI | VERIFIED — hidden-capability list with live consumers; `test_w03_hidden_settings_still_have_live_consumers` |
| `HPC-W01-TRUTH-034` | UI options with no effective consumer | VERIFIED — no ghost control in wx Settings dialog (GUI-proven); 1 items routed to owners (DEF-W03-001/002) |
| `HPC-W01-TRUTH-035` | orphan-setting class | VERIFIED — 2 classified (legacy global `transfer_parallelism`, legacy `focus_jobs_outputs_after_submission_enabled`), both handled as migration-only |
| `HPC-W01-TRUTH-036` | ghost-control class | VERIFIED — 0 in wx Settings dialog; 1 routed candidate in Plugins view (DEF-W03-002, owner W35) |
| `HPC-W01-TRUTH-037` | hidden-capability class | VERIFIED — 4 classified with consumers of record (jobs interval, sbatch mode, lssrv toggle, shortcut prefs) + keepalive/x11 live in connection dialog |
| `HPC-W01-TRUTH-038` | provider discovery mechanism | VERIFIED — local declarative loader, `active.json` index; empty-root/discovery pins |
| `HPC-W01-TRUTH-039` | declared identity/version | VERIFIED — manifest id/version enforcement; mismatch-rejection pin |
| `HPC-W01-TRUTH-040` | capabilities | VERIFIED — `build_provider_capability_view` DECLARED/NOT_DECLARED pin |
| `HPC-W01-TRUTH-041` | optional capability semantics (CONDITIONAL) | VERIFIED — absent quota (`NOT_DECLARED`) distinct from failed probe (`observed FAILED`) |
| `HPC-W01-TRUTH-042` | unavailable capability behavior | VERIFIED — unknown adapter → `None`, missing parser → `fail("unsupported")`, malformed contract → empty |
| `HPC-W01-TRUTH-043` | UI exposure | VERIFIED — Plugin Manager cards + remote provider filters + self-test declared/observed; listing pin + GUI probe rows=2 |
| `HPC-W01-TRUTH-044` | fallback behavior | VERIFIED — registry source degrades unknown → `offline`; entries without id never become cards |
| `HPC-W01-TRUTH-045` | dependency/import safety | VERIFIED — malformed plugin isolated, valid still registers; linter engines lazy/trust-gated |
| `HPC-W01-TRUTH-046` | tests that prove registration | VERIFIED — new pins + pre-existing `test_plugin_core` / `test_plugin_contract` / `test_provider_capabilities` / `test_wave_v2_02_provider_contract` / `test_wave79_provider_contract` all green |

## Mandatory source sections read

- `opencode/sources/WAVE_V2_FINAL_01.md:228–245` → Workstream C — Audit settings and stored state (enumerate 8 items; flag orphan/ghost/hidden).
- `opencode/sources/WAVE_V2_FINAL_01.md:247–261` → Workstream D — Audit provider/plugin surface (9 items per provider + quota/probe distinction).
- Owned rows: `opencode/REQUIREMENT_REGISTRY.md:93–112` (TRUTH-027…046); index rows `opencode/REQUIREMENT_WAVE_INDEX.md:55–74`; `opencode/TODO_OWNERSHIP_MAP.md` confirms 0 TODO rows owned by W03.
- Live code inspected before any edit (source wording = requirement, code = implementation truth): `config/storage.py`, `config/models.py`, `core/paths.py`, `wx_settings.py`, `wx_settings_view.py`, `wx_shell.py` (`_dispatch APP-SETTINGS`), `wx_plugins.py`, `wx_plugins_view.py`, `plugins/loader.py`, `plugins/storage.py`, `services/provider_capabilities.py`, `services/provider_contract.py`, `services/connection_profile_service.py` (`save_profile`), `services/remote_navigation_store.py`, `wx_connection_dialog.py` (keepalive/ssh-timeout/x11 controls).

## Discovery pass (before first edit)

- Pinned `develop 0f8902a0`; working tree held pre-existing/concurrent changes (W02 error-governance, i18n additions, FFSync sidecars) — all preserved byte-for-byte, none reverted; this session made zero product edits.
- Narrow pre-edit baseline `EV-W03-BASE-001`: `pytest -q tests/test_wx_settings.py tests/test_wx_plugins.py tests/test_provider_capabilities.py tests/test_plugin_core.py` → **49 passed, 0 failed** (exit 0).
- `wxPython 4.3.1 msw (phoenix) wxWidgets 3.3.3` present, so real GUI evidence was obtainable.

## Settings inventory (frozen truth)

Persistence root: `<app_data_dir>/config.json` (`~/.truba_slurm_gui`, macOS `~/Library/Application Support/HPC Client GUI` with one-way legacy migration). Side stores: `language.json`, `private/<profile_id>.json` (Fernet-encrypted navigation), `plugins/` registry, keychain/DPAPI/master secret refs, `config.json.ui` prefs, `config.json.bak*` migration/corruption backups.

| Key (storage) | Default | wx Settings control | Consumer of record | Drift class |
|---|---|---|---|---|
| `remote_directory_cache_enabled` | `true` | `remote_cache` checkbox (via model key `remote_directory_cache`) | remote listing cache | — (see key-name note) |
| `transfer_checksum_verification_enabled` | `false` | `checksum` checkbox (via `transfer_checksum`) | transfer verify | — (see key-name note) |
| profile `transfer_parallelism` | `1` (1–10) | `parallelism` spin | transfer queue | — |
| profile `ssh_timeout` | `None` (transport default) | `timeout` spin (int 0–300) | SSH client/connect | — |
| `jobs_outputs_refresh_interval_seconds` | `15` | none | jobs polling timer | hidden-capability (intentional) |
| `sbatch_follow_mode` | `outputs_tab` | none | post-sbatch follow | hidden-capability (intentional) |
| `lssrv_auto_refresh_enabled` | `false` | none | jobs polling | hidden-capability (intentional) |
| `squeue/sacct_auto_refresh_enabled` | `true` | none | jobs polling | hidden-capability (intentional) |
| `live_tracking_warning_interval_seconds` | `60` | none | live follow | hidden-capability (intentional) |
| `transfer_completion_action`, `upload_preflight_confirmation_enabled`, `ftp_transfer_type`, `file_associations`, `ftp_*` state, CLI prefs, changelog version, minimize/follow prefs | see test pin | none | transfer/CLI/changelog/window services | hidden-capability (intentional) |
| profile `keepalive_interval_seconds` | `30` | none in Settings; `sp_keepalive` in connection dialog | SSH keepalive | exposed elsewhere |
| profile `x11_enabled` (model) / `x11_forwarding` (dialog) | `false` | none in Settings; `cb_x11` in connection dialog | X11 runner | exposed elsewhere + key-name note |
| `shortcut_preferences` | `{}` | none (displayed via help/shortcut surfaces) | shortcut display | hidden-capability (intentional) |
| legacy global `transfer_parallelism` | migration source only | none | `migrate_legacy_transfer_parallelism` (once per profile) | orphan-setting (handled) |
| legacy `focus_jobs_outputs_after_submission_enabled` | migration source only | none | `get_sbatch_follow_mode` fallback | orphan-setting (handled) |
| `terminal_graphics_auto_compatibility`, `qt_webengine_gpu` | ignored | none | `LEGACY_IGNORED_KEYS` | obsolete (explicit) |

Key-name note (inventory honesty, no behavior change here): `WxSettingsModel` uses short keys (`remote_directory_cache`, `transfer_checksum`, `jobs_outputs_refresh_interval`) while `config/storage.py` persists suffixed keys (`*_enabled`, `*_seconds`); the shell currently opens Settings with no persistence callback at all (DEF-W03-001, owner W37), so these names never meet in the wx path today. W37 owns the reunion; this inventory records both vocabularies so the reunion is exact.

Ghost-control verdict: the wx Settings dialog exposes exactly 4 value controls (`remote_cache`, `checksum`, `parallelism`, `timeout`), each bound to a model key with a live service consumer — GUI-proven by `EV-W03-GUI-001`. Zero ghost controls in the Settings dialog.

## Provider/plugin surface inventory (frozen truth)

| Item | Truth |
|---|---|
| Discovery | local declarative loader (`plugins/loader.py::load_installed_plugins`) over `plugins/<active.json>` index; no network at load; empty root → empty result, no error |
| Identity/version | manifest `id` must equal index id, `version` must equal index version; `plugin_api` must be supported; `requires_app` must satisfy app version; violations → `PluginProblem`, plugin skipped |
| Capabilities | `provider_capabilities.build_provider_capability_view`: auth/scheduler/storage/quota/project/account/optional → `DECLARED`/`NOT_DECLARED` + observed status + detail |
| Optional semantics | absent quota = `NOT_DECLARED` with observed `NOT_TESTED`; failed probe = observed `FAILED`; the two never collapse (pinned) |
| Unavailable behavior | unknown adapter → `None` + warning log; missing/unknown parser → `ParseResult.fail("unsupported")`; malformed sections → empty contract, no raise |
| UI exposure | Plugin Manager cards (`WxPluginManagerModel` → `ListCtrl` rows, GUI-proven 2/2); registry source label ∈ `{network, cache, offline}`; remote-files provider/plugin filters; cluster self-test declared-vs-observed view |
| Fallback | unknown registry source → `offline`; entries without `id` never become cards; `show_plugins` `TypeError` fallback preserved (W02) |
| Import safety | one malformed plugin → recorded problem, rest load, startup never blocked; duplicate profile ids deterministic (sorted iteration, first wins, loser diagnosed); linter engines lazy + trust-gated (`trusted_tool_error`) |
| Registration proof | new pins (valid registers; malformed/duplicate/mismatch isolated) + existing `test_plugin_core`, `test_plugin_contract`, `test_provider_capabilities`, `test_wave_v2_02_provider_contract`, `test_wave79_provider_contract` — all green |

## WAVE_FINDINGS

| Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status |
|---|---|---|---|---|---|---|---|---|
| `DEF-W03-001` | P1 (routed) | wx Settings Apply from shell (`wx_shell._dispatch APP-SETTINGS` → `show_settings(parent=parent)`) | live source `wx_shell.py:2756–2760`: no model/settings/apply passed; `WxSettingsModel(settings=None, apply=None)` → `apply_callback None` → Apply shows OK while persisting nothing | missing persistence wiring (owned TODO `HPC-W11-TODO-SETTINGS-PERSIST-001`, Wave W37) | user believes settings saved; nothing persisted | W37: inject real state + real persistence callback (do not fix here — cross-wave rule) | NO (true owner W37) | OBSERVED/ROUTED |
| `DEF-W03-002` | P2 (routed) | Plugins view search + refresh (`wx_plugins_view.py:80–106, 200–206`) | live source: `on_search` body is `pass`; refresh worker simulates fetch, always labels `cached` | unimplemented GUI behavior (owned TODOs `PLUGIN-SEARCH-001`, `PLUGIN-REFRESH-001`, Wave W35) | search box implies filtering that never happens; source label implies freshness unproven | W35: real filter + real source resolution (do not fix here) | NO (true owner W35) | OBSERVED/ROUTED |

No in-scope P0/P1 remains open: both findings are cross-wave by TODO ownership and are routed, not absorbed. Zero-defect PASS for owned scope is valid per `HPC-GOV-017`.

## Fixes

None. This Wave is an inventory freeze; the tree was already truthful for every owned requirement, and the two real defects found belong to W37/W35 by explicit TODO ownership. Smallest coherent correction = no product edit. The session's only repo addition is the inventory pin suite below.

## Tests and evidence

| Evidence | Exact command | Exit | Result |
|---|---|---:|---|
| `EV-W03-BASE-001` narrow baseline (pre-edit) | `python -m pytest -q tests/test_wx_settings.py tests/test_wx_plugins.py tests/test_provider_capabilities.py tests/test_plugin_core.py` | 0 | 49 passed, 0 failed |
| `EV-W03-AFTER-001` new inventory pin suite | `python -m pytest -q tests/test_w03_settings_provider_inventory.py` | 0 | 17 passed (11 settings + 6 provider incl. path-construction pin) |
| `EV-W03-SENS-001` drift sensitivity | temp `default: 15 → 16` in `get_jobs_outputs_refresh_interval_seconds` → defaults test fails `16 == 15` (right reason) → restored byte-identical (sha256 `a502f859…7e5b` both sides, `git diff` clean for the file) | script 0 | sensitivity proven |
| `EV-W03-GUI-001` real wx event/runtime probe | `python C:\Users\mskomek\AppData\Local\Temp\opencode\w03_gui_probe.py` (Temp, outside repo; real `wx.App`, real panel builds, real `EVT_BUTTON` via `ProcessEvent`, real worker-thread apply) | 0 | `W03_GUI_PROBE=PASS`: 7 controls enumerated, staged snapshot `{remote_cache False, checksum True, parallelism 4, timeout 25}`, plugin listing rows=2, 1 success MessageBox, controlled shutdown |
| `EV-W03-IMPACT-001` settings/provider/plugin lanes | 17-file run (inventory + wx_settings + wx_plugins + provider ×6 + plugin ×2 + tracking/migration/lssrv/connection/profile + v2-02 + wave79 contracts) | 0 | 180 passed, 20 skipped (all skips pre-existing markers, none added here) |
| `EV-W03-IMPACT-002` dispatch/shell/truth lanes | `python -m pytest -q tests/test_wx_dispatch_error_gov.py tests/test_wx_shell.py tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py` | 0 | 61 passed |
| `EV-W03-REPAIR-001` re-run inventory pins on current dirty tree (2026-09-19) | `python -m pytest -q tests/test_w03_settings_provider_inventory.py` | 0 | 17 passed in 0.72s — binds all 20 owned-ID pins to `0f8902a0` + dirty tree |
| `EV-W03-REPAIR-002` re-run narrow baseline on current dirty tree (2026-09-19) | `python -m pytest -q tests/test_wx_settings.py tests/test_wx_plugins.py tests/test_provider_capabilities.py tests/test_plugin_core.py` | 0 | 49 passed in 1.94s — no regression from later-Wave edits |
| `EV-W03-REPAIR-003` re-run real wx GUI probe on current dirty tree (2026-09-19) | `python C:\Users\mskomek\AppData\Local\Temp\opencode\w03_gui_probe.py` (Temp, outside repo) | 0 | `W03_GUI_PROBE=PASS`: `W03_SETTINGS_CONTROLS=apply,checksum,close,parallelism,remote_cache,timeout,title`, `W03_SETTINGS_APPLY=PASS`, `W03_PLUGINS_LISTING=PASS rows=2 source=cache`, `W03_MSGBOX_CALLS=1` |

Environment: `Python 3.12.4`, `wxPython 4.3.1 msw (phoenix) wxWidgets 3.3.3`, Windows. Mocks limited to legitimate boundaries: isolated `_config_path` (real JSON round-trip through the real storage layer), tmp plugin roots through the real loader + integrity path, modal `MessageBox` capture in the GUI probe with real event routing and real apply callback. No test weakening, no new skips/xfails, no fabricated output.

## Second-defect search protocol (dimensions for the inventory surface)

1. negative paths — CHECKED: malformed JSON/manifest, identity mismatch, incompatible API/app, missing entrypoint, duplicate ids, unknown adapter/parser, unknown registry source, id-less cards, invalid model keys (`KeyError`), corrupt config → backup + fresh.
2. lifecycle — CHECKED: probe destroys frame, pumps pending events, exits 0; loader retains no handles; settings worker is daemon + callback-only.
3. stale state — N/A with justification: inventory reads live code at pinned HEAD; no retained callbacks in inventoried paths.
4. identity — CHECKED: manifest/index identity enforcement; profile stable ids; per-profile navigation isolation + delete cleanup; secret-ref rotation cleanup.
5. concurrency/race — N/A with justification: atomic config writes (`mkstemp` + `os.replace`); loader single-threaded at startup; probe worker joins via event.
6. boundary values — CHECKED: coercion clamps (parallelism 1–10, ssh 0–600, intervals, ftp types, completion actions, splitter sizes) pinned by existing suites.
7. capability absence — CHECKED: quota-absent vs probe-failed distinction pinned; optional capabilities surfaced, not fabricated.
8. persistence — CHECKED: the Wave's core; one real gap found and routed (DEF-W03-001, W37).
9. packaging — N/A with justification: no new dependency (wx optional/lazy, JSON stdlib); no artifact claim.
10. error visibility — CHECKED: unavailable behaviors return explicit fail/None + diagnostics; no silent collapse found in owned scope.
11. context menus/secondary entry — CHECKED: single `_dispatch` chokepoint serves menu + shortcuts (W02 map reused, not duplicated).
12. adjacent integration boundary — CHECKED: callee call-sites untouched (zero product edits); key-name vocabularies on both sides recorded for W37.

No second in-scope defect beyond the two routed observations; nothing absorbed from other Waves.

## Diff review (recaptured 2026-09-19 on the current tree — repair cycle 1)

Prior revision of this section described an older tree (`HEAD + one untracked test file`). The Luna fresh-context audit (AUD-W03-001 REOPEN) correctly observed the current tree is further dirty with later/concurrent Wave work. This section now records the full verbatim current-tree truth. Nothing below is absorbed into W03 scope; every non-W03 entry is explicitly attributed and preserved byte-for-byte.

- `git status` (verbatim, 2026-09-19):

```text
On branch develop
Changes not staged for commit:
	modified:   CONTRIBUTING.md
	modified:   README.md
	modified:   artifacts/v2-final/W01/W01_COMPLETION_REPORT.md
	modified:   artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md
	modified:   docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md
	modified:   src/hpc_gui/i18n/en.json
	modified:   src/hpc_gui/i18n/tr.json
	modified:   src/hpc_gui/plugins/loader.py
	modified:   src/hpc_gui/plugins/validator.py
	modified:   src/hpc_gui/services/connection_controller.py
	modified:   src/hpc_gui/wx_connection.py
	modified:   src/hpc_gui/wx_settings_view.py
	modified:   src/hpc_gui/wx_shell.py
	modified:   tests/test_wave10_release_gate.py

Untracked files:
	artifacts/v2-final/W02/
	artifacts/v2-final/W04/
	docs/wave-reports/v2/opencode/
	hpc-client-gui.ffs_gui
	src/hpc_gui/core/wx_errors.py
	sync.ffs_db
	tests/test_w03_settings_provider_inventory.py
	tests/test_w04_support_freeze.py
	tests/test_w08_schema_isolation.py
	tests/test_w09_main_plugin_compat.py
	tests/test_w11_ssh_lifecycle.py
	tests/test_wx_dispatch_error_gov.py
```

- `git diff --stat` (verbatim):

```text
 CONTRIBUTING.md                                  | 15 +++-
 README.md                                        |  3 +-
 artifacts/v2-final/W01/W01_COMPLETION_REPORT.md  |  6 +-
 artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md |  6 +-
 docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md  |  6 ++
 src/hpc_gui/i18n/en.json                         |  8 +-
 src/hpc_gui/i18n/tr.json                         |  8 +-
 src/hpc_gui/plugins/loader.py                    |  8 +-
 src/hpc_gui/plugins/validator.py                 | 56 ++++++++------
 src/hpc_gui/services/connection_controller.py    | 25 +++++-
 src/hpc_gui/wx_connection.py                     | 72 +++++++++++++++++-
 src/hpc_gui/wx_settings_view.py                  | 29 ++++---
 src/hpc_gui/wx_shell.py                          | 96 ++++++++++++++++--------
 tests/test_wave10_release_gate.py                | 22 +++++-
 14 files changed, 277 insertions(+), 83 deletions(-)
```

- `git diff --numstat` (verbatim): `11/4 CONTRIBUTING.md`, `2/1 README.md`, `4/2 + 4/2` W01 artifacts, `6/0` planning report, `7/1 + 7/1` i18n, `7/1 loader.py`, `33/23 validator.py`, `24/1 connection_controller.py`, `71/1 wx_connection.py`, `19/10 wx_settings_view.py`, `64/32 wx_shell.py`, `18/4 test_wave10_release_gate.py`.
- `git diff --check`: clean (only pre-existing CRLF warnings on W01 artifacts + i18n; zero whitespace errors).
- Plugin repo: `develop / f0abb7e7037e66ab451d463c699fecf4e00c89eb`, status shows only untracked sidecar `.github/social-preview.jpg`.

Attribution (preserve, do not absorb — none reverted, none edited by this repair session):
- W03-owned addition: `tests/test_w03_settings_provider_inventory.py` (untracked, this Wave's inventory pin suite).
- W02 error-governance: `src/hpc_gui/core/wx_errors.py`, `tests/test_wx_dispatch_error_gov.py`, plus the `report_wx_action_error` hunks in `wx_settings_view.py` / `wx_shell.py` (staging-error collection, visible coded failures, `_dispatch` routing for PLUGIN-BROWSE/APP-SEND-LOGS/APP-SETTINGS).
- W04 support surface: `frame._wx_dispatch_plugin_action` hook + `FIX-W04-A` comments in `wx_shell.py`, `artifacts/v2-final/W04/`, `tests/test_w04_support_freeze.py`.
- W08 schema hardening: `plugins/loader.py` fail-closed `_build_profile` try/except + `plugins/validator.py` `_validate_storage_and_quota_sections` (v1/v4) and `access`/`requirements` v2 sections, `tests/test_w08_schema_isolation.py`.
- Other later/concurrent Waves: `tests/test_w09_main_plugin_compat.py` (W09), `tests/test_wave10_release_gate.py` (W10), `tests/test_w11_ssh_lifecycle.py` + `connection_controller.py` + `wx_connection.py` (W11), W01 artifacts + planning report + CONTRIBUTING/README/i18n churn (W01/i18n lanes), `artifacts/v2-final/W02/` (W02 sidecar), FFSync sidecars (`hpc-client-gui.ffs_gui`, `sync.ffs_db`).
- Effect on W03 truth re-verified 2026-09-19: the W02/W04/W08 hunks in W03-adjacent files strengthen fail-closed/error-visible behavior in the same direction as the frozen inventory (malformed still isolated, failures still visible); `EV-W03-REPAIR-001/002/003` prove zero regression (17 + 49 passed, GUI PASS). DEF-W03-001 re-confirmed live (`wx_shell.py:2776` still `show_settings(parent=parent)`, no persistence wiring — still W37). DEF-W03-002 re-confirmed live (`wx_plugins_view.py:201–204` `on_search` still no-op `pass` — still W35).
- No secrets in diff/scripts/reports; probe script lives in Temp, outside the repo.

## Findings and ownership routing

- In-scope P0/P1 opened: 0 owned. `DEF-W03-001` → W37 (`HPC-W11-TODO-SETTINGS-PERSIST-001` family + key-name reunion). `DEF-W03-002` → W35 (`PLUGIN-SEARCH-001`, `PLUGIN-REFRESH-001`).
- Cross-wave: nothing absorbed. Remote/package validation stays with W03-external/W04/W08/W10 per W02 ownership map (unchanged).
- New defects introduced: 0.

## Resume state

Completed and verified: all 20 owned IDs inventoried with requirement → implementation owner → test → evidence traces (registry rows `opencode/REQUIREMENT_REGISTRY.md:93–112` re-read 2026-09-19, all 20 confirm Owning Wave `W03`); 17-test pin suite + sensitivity + GUI proof, all rebound to the current dirty tree (EV-W03-REPAIR-001/002/003); 241-test combined re-runs green (180+61); routed defects re-confirmed live on the current tree (DEF-W03-001 line 2776, DEF-W03-002 lines 201–204); reports current.
In progress: none. Open P0/P1: 0 (owned). Open P2/P3: 0 (owned).
Pending tests/evidence: none for this Wave.
Last exact commands: see evidence table (`EV-W03-REPAIR-001`, `EV-W03-REPAIR-002`, `EV-W03-REPAIR-003`; earlier `EV-W03-IMPACT-001`, `EV-W03-IMPACT-002`, `EV-W03-GUI-001`).
Next actions: none in this Wave — stop. `W04` may be planned only after its dependency/prerequisite checks are revalidated.
Evidence/artifact identities: implementation state `develop 0f8902a0` + 14 tracked modifications + 12 untracked paths (verbatim above; non-W03 entries attributed, preserved, not absorbed); probe `w03_gui_probe.py` (Temp, outside repo); no package artifact (N/A for W03).

## Final summary

```text
Inventory freeze: settings keys/defaults/controls/persistence/migration/secrets/drift classes + provider discovery/identity/capabilities/optional/unavailable/UI/fallback/safety/registration
DEF: DEF-W03-001 (P1, settings Apply persists nothing from shell — routed W37), DEF-W03-002 (P2, plugin search/refresh unimplemented — routed W35)
Root cause: owned scope is already truthful; both real gaps belong to other Waves by TODO ownership
Before EV: EV-W03-BASE-001 (49 green pre-edit)
After EV: EV-W03-AFTER-001 (17/17), EV-W03-GUI-001 (PASS, exit 0), EV-W03-IMPACT-001 (180+20 pre-existing skips), EV-W03-IMPACT-002 (61); repair-cycle-1 rebind EV-W03-REPAIR-001 (17/17 on dirty tree), EV-W03-REPAIR-002 (49/49 on dirty tree), EV-W03-REPAIR-003 (GUI PASS on dirty tree)
Regression test: tests/test_w03_settings_provider_inventory.py (new; no existing test modified)
Sensitivity proof: EV-W03-SENS-001 (byte-identical restore, sha256 a502f859…7e5b)
Additional fixes: none (zero-defect PASS per HPC-GOV-017; no quota to fill)
Post-green review: 12-dimension second-defect search, no further in-scope defect; residuals routed with owner IDs
New/modified tests: 1 new file, 17 tests; no existing test modified
Skipped/xfail changes: none
Package evidence: N/A (no new dependency; no artifact claim)
External evidence: N/A (remote rows keep REQUIRES_EXTERNAL_VALIDATION downstream; no live-cluster claim here)
Open P0/P1: 0 (owned)
Open P2/P3: 0 (owned)
Wave decision: PASS
```
