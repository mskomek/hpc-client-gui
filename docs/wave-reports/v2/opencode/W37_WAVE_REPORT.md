# W37 — Settings schema, persistence and plugin/provider settings — Wave Report

Wave: W37
Canonical report path: docs/wave-reports/v2/opencode/W37_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369
Tested implementation SHA: c8293d3ca309526ed250c794c3b294f7c54ef369 (plus uncommitted W37 diff in src/hpc_gui/wx_settings.py, src/hpc_gui/wx_settings_view.py, src/hpc_gui/wx_shell.py, tests/test_w37_settings_persistence.py; sibling dirty files from W26-W36 preserved untouched)
Plugin/external repo SHA(s), if applicable: no plugin repo checkout; plugin/provider settings proven with local declarative fixtures only (no network — same basis as W32-W36)
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24
Session status: READY FOR FINAL REVIEW
Wave decision: GO (worker) — pending fresh independent audit

## Objective

Close settings inventory, validation, atomic load/save, scope, persistence and plugin/provider setting ownership (Workstreams A/B/E + entry/scope/test/acceptance rows + 24 TODO-detail rows).

## Mandatory authority consumed

- waves/pending/W37.md (all owned IDs: 35 source-derived + 24 TODO-detail)
- opencode/REQUIREMENT_REGISTRY.md rows Owning Wave W37 (59 rows: HPC-W09-SET-001..015, HPC-W09-UPD-003/007..009/011/012/014/015/044/045/048/056/057/059/060/070/071/074, HPC-W09-PLUGINSET-001/002, plus the 24 W11/W09 TODO rows)
- opencode/TODO_OWNERSHIP_MAP.md rows Owning Wave W37 (24 rows, all ACTIVE)
- opencode/sources/WAVE_V2_FINAL_09.md sections: Workstream A (Settings inventory), Workstream B (Load/save atomicity), Entry criteria, Scope, Targeted tasks, Test matrix, Acceptance criteria, Workstream E (Plugin/provider settings)
- Live code: src/hpc_gui/wx_settings.py, src/hpc_gui/wx_settings_view.py, src/hpc_gui/wx_shell.py (APP-SETTINGS), src/hpc_gui/config/storage.py, src/hpc_gui/plugins/settings.py, src/hpc_gui/services/shortcut_preferences.py, src/hpc_gui/cli/session.py, src/hpc_gui/ssh/client.py

## Baseline (pre-edit)

- `git status --short --branch` showed develop at c8293d3c with pre-existing dirty W26-W36 files (preserved; sibling diffs in README/docs/plugins/services/wx_editor/wx_jobs/wx_plugins/wx_shell are other waves' work, not re-owned).
- Narrow baseline: tests/test_wx_settings.py + test_config_storage_atomic.py + test_w03_settings_provider_inventory.py = 22 passed, exit 0.
- Discovery pass findings (WAVE_FINDINGS):

Finding ID | Severity | Surface | Evidence | Root cause | Impact | Candidate fix | Countable | Status
DEF-W37-001 | P1 | wx shell settings entry | `wx_shell._dispatch APP-SETTINGS` calls `show_settings(parent)` with no model and no persistence callback (src/hpc_gui/wx_shell.py:3682 pre-edit) | settings dialog opens on an empty default model whose Apply persists nothing except the checksum bridge | SETTINGS-PERSIST-001 unmet: Apply-without-persistence possible; dialog state fabricated, not storage-loaded | inject `build_model_from_storage(apply=persist_model_snapshot)` | YES | FIXED (FIX-A)
DEF-W37-002 | P1 | settings view persistence | `_build_settings` drops a caller-supplied `apply` when a prebuilt model is passed (`model or WxSettingsModel(...)` ignores kwarg); worker persists only the checksum bridge, other keys stay in-memory | same root helper predates real persistence wiring | SETTINGS-PERSIST-001/002 unmet for all non-checksum keys | attach callback when absent; persist full snapshot when no callback | YES | FIXED (FIX-A)
DEF-W37-003 | P2 (routed, not fixed) | editor save ownership text | `test_editor_save__local_and_remote_paths_have_distinct_owners` fails: `Path(snapshot.path).write_text` absent from dirty `src/hpc_gui/wx_editor_view.py` | sibling W26 editor-identity refactor changed the local-save line | W37 untouched surface; owned by the editor wave | none on W37 acceptance | ROUTED to controller/true owner; no opportunistic edit | NO | ROUTED
DEF-W37-004 | P3 (documented, not a defect) | hours-scale soak | SOAK-LONG-001 requires an hours-scale packaged soak (terminal, reconnect, transfers, jobs, editor, settings, plugins, open/close cycles with growth evidence) | unattended single-phase execution cannot run hours-scale packaged soak | recorded EXTERNAL_BLOCKED with resume point; all safe local/package/GUI checks complete | controller-scheduled soak run | NO | EXTERNAL_BLOCKED

## Implementation (smallest coherent correction)

- FIX-A (product, PERSIST-001/002/003, PROFILE-001, RUNTIME/RESTART, PARITY, SILENT-ERROR):
  - `src/hpc_gui/wx_settings.py`: added `SETTINGS_INVENTORY` (8 key-level rows: Key|Owner|Type|Default|Persisted|Sensitive|Migrated-from|Consumer|UI-control|Scope|Live), `INVENTORY_FLAGS` (SET-002..006 evaluated, none open), `GLOBAL_STORAGE_KEYS`/`PROFILE_STORAGE_KEYS` maps (`x11_enabled` aliases profile record `x11_forwarding` — the same bit Qt dialog/CLI/SSH consume), `LIVE_APPLY_KEYS` (all 8 dialog keys live) + `RESTART_REQUIRED_KEYS` (deliberately empty, declared not implicit), `QT_PARITY_MAP` (every known Qt-era key PORT-TO-WX/DEPRECATED/NOT-IN-V2), `build_model_from_storage()` (real storage reads through the same getters the runtime consumes), `persist_model_snapshot()` (globals via atomic storage writes, profile keys to the active profile record only; raises attributed errors, never false-success), `load_persisted_snapshot()` (reopen proof), `plugin_settings_survive_absence()` (ARCH-BOUNDARY bridge to `plugins.settings`, no duplicated logic).
  - `src/hpc_gui/wx_shell.py` (`_dispatch APP-SETTINGS` only): builds the model from real storage with a real persistence callback; failure path unchanged (visible coded error).
  - `src/hpc_gui/wx_settings_view.py`: attaches a supplied callback to a prebuilt model instead of dropping it; worker persists the full snapshot when no callback exists, keeps the legacy checksum bridge on the callback path; OK dialog only after writes succeed, failures route to `report_wx_action_error` with a stable code.
- No cross-Wave cleanup: sibling dirty files untouched; the W30 hunks already present in wx_shell.py left byte-identical; no Qt/PySide removal; no skips/xfails added.

## Tests

New: `tests/test_w37_settings_persistence.py` (31 tests):

- UPD-056/070 + UPD-044 (SET-001): defaults live + inventory schema frozen + model key sets frozen.
- SET-007..015 + UPD-045/057 (corruption matrix): missing/empty/malformed/partial-corrupt/unknown/wrong-type/read-only/write-failure + backup-preserved recovery + no-temp residue.
- PERSIST-001: shell dispatch source wires real builder+callback; builder reads live storage; view attaches supplied callbacks.
- PERSIST-002: Apply persists (readback True); failed write raises `persist rejected`, no false success.
- PERSIST-003: model deleted after Apply; reopen snapshot loads True/False from storage.
- PROFILE-001 + TODO-050: A/B isolation (B untouched); missing-active-profile attributed; x11 mapping shared with Qt/CLI/SSH consumers.
- RUNTIME-001/RESTART-001: live set declared + measurable toggle; restart set deliberately empty.
- PARITY-001 + SILENT-ERROR-001: Qt map classifies all known keys; legacy keys never serialize; unknown model keys raise KeyError.
- TODO-033 verify matrix (default/alternate/persist/scope), TODO-034 CLI/GUI shared-record agreement.
- UPD-060/074 + PLUGINSET-001/002 + UPD-048: absent-plugin defaults, namespaced keys, core-key fail-closed, reinstall/upgrade merge, secret export drop.
- MIGRATION-SETTINGS-001 (legacy global→profile idempotent), MIGRATION-QUOTA-001 (legacy bool source-only), MIGRATION-TERMINAL-001 (terminal history deliberately out of V2 migration scope — asserted absence by decision).
- ARCH-BOUNDARY-001: bridge delegates to `plugins.settings`.
- GUI FULL (2 tests, real wx runtime): checkbox event → Apply click → config.json True → OK dialog only on persisted path → reopen readback; negative: write failure → visible error, zero OK dialogs.

Evidence:

- EV-W37-001: `pytest tests/test_w37_settings_persistence.py -q` → 31 passed, exit 0 (tested SHA c8293d3c + W37 diff). passed=31 failed=0 skipped=0.
- EV-W37-002 (GUI FULL): `test_w37_wx_apply_event_persists_to_storage` (event→storage→reopen) and `test_w37_wx_failed_persist_shows_error_never_false_ok` (error visible, no OK) — both green in EV-W37-001; wx 4.3.1 runtime, MessageBox patched only to avoid modal blocking (success/error routing still asserted).
- EV-W37-003 (regression): test_wx_settings + test_config_storage_atomic + test_w03_settings_provider_inventory + test_w34_provider_settings + test_w35_plugin_manager_gui + test_w36_packaged_docs + test_connection_advanced_settings + test_live_tracking_settings + test_profile_storage_areas + test_profile_transfer_settings = 87 passed; test_wx_shell.py = 5 passed; test_wx_dispatch_error_gov.py = 36 passed (1 sibling-owned editor assertion deselected, see DEF-W37-003); early CLI/config/connection batch = 233 passed.
- EV-W37-004 (negative controls): full-suite run hits a pre-existing access-violation crash in `tests/test_editor_flow.py` (mock SSH server thread + wx editor, unrelated surface) and DEF-W37-003 fails identically as a source-text assertion on a sibling-dirty file — both independent of the W37 diff.
- Baseline: pre-edit narrow suites (22 passed) recorded before edits.

Test taxonomy: contract (inventory/schema/parity/migration/boundary), integration (corruption matrix, persistence round-trips, profile isolation), GUI (wx event→storage→readback + negative). Mocks limited to disposable config roots, tmp plugin roots, injected MessageBox/error-report spies and one save_config failure injection (legitimate boundaries); what tests do NOT prove: hours-scale packaged soak (EXTERNAL_BLOCKED, DEF-W37-004) and real-network registry fetch (no owned requirement needs live infra).

## Diff review

- `git diff --check` on owned files → clean.
- W37-owned diff: src/hpc_gui/wx_settings.py (+336/-2: inventory + bridge, existing model untouched), src/hpc_gui/wx_settings_view.py (+callback attach + snapshot persist), src/hpc_gui/wx_shell.py (APP-SETTINGS hunk only), tests/test_w37_settings_persistence.py (new, 31 tests).
- Full diff of owned hunks inspected: no secrets, no generated/binary noise, no unrelated changes, no weakened tests, no duplicated framework logic in wx views.
- Sibling dirty files (wx_editor_view, wx_jobs, wx_plugins*, services, docs, i18n) preserved byte-identical; DEF-W37-003 routed, not opportunistically fixed.

## POST_GREEN_REVIEW

- Duplicate path: profile/global persistence reuses `config.storage` public APIs; plugin cases reuse `plugins.settings`; no logic duplicated into tests or views.
- Alternate entry: Qt connection dialog and CLI session read the same profile record keys the wx dialog persists (TODO-034 test pins both).
- Silent fallback: none — persist failures raise attributed errors; worker never shows OK after failure (negative GUI test pins zero-OK).
- Stale state: every persistence test uses an isolated tmp config; reopen proof deletes the dialog model first.
- Identity: tests bind to candidate SHA c8293d3c + owned diff; storage identity is the tmp config path per test.
- Cleanup: all fixtures under tmp_path; no .tmp plan artifacts written by this phase (report files are the required canonical outputs).
- Dead branch: none added; legacy checksum bridge retained as the callback-path second write (idempotent same-value).
- Hardcoded: none (profile resolution via `get_last_profile_name`; no fixture profile names leak into product code).
- Error-as-success: persist errors propagate as exceptions → visible coded dialog; tests assert the OK counter stays 0.
- Packaged divergence: N/A (no owned requirement needs a fresh wheel; W36 wheel staleness noted but not W37-owned).

## Requirement dispositions (all owned IDs)

- HPC-W09-SET-001 (key-level map): IMPLEMENT (`SETTINGS_INVENTORY`, 8 rows + inventory test).
- HPC-W09-SET-002..006 (dead keys / duplicates / coercion / UI-default / collisions): IMPLEMENT (`INVENTORY_FLAGS`, all five evaluated none-open + frozen key-set test).
- HPC-W09-SET-007..014 (missing/empty/malformed/partial/unknown/wrong-type/read-only/write-failure): IMPLEMENT (8 matrix tests over `config.storage` atomic save + backup + coercion).
- HPC-W09-SET-015 (no silent discard): IMPLEMENT (corrupt input leaves `.bak` with recoverable bytes; backup-preservation asserted).
- HPC-W09-UPD-003 (W05–W08 consumers known): IMPLEMENT (inventory consumers name live getters; jobs/files/plugin/updater consumers pinned by existing suites reused in EV-W37-003).
- HPC-W09-UPD-007/008/009/011/012/014/015 (scope boundaries): IMPLEMENT (defaults/schema/load-save/unknown/profile/plugin/import-corruption each covered; sensitive boundary via plugin secret-drop + W03 plaintext-password pin).
- HPC-W09-UPD-044 (TASK-W09-001 key map): IMPLEMENT (inventory + test).
- HPC-W09-UPD-045 (TASK-W09-002 corruption tests): IMPLEMENT (matrix tests).
- HPC-W09-UPD-048 (TASK-W09-005 plugin compat): IMPLEMENT (absent/disabled/reinstall/upgrade cases).
- HPC-W09-UPD-056/057/059/060 (test matrix): IMPLEMENT (defaults / corrupt / unknown-key / absent-plugin tests).
- HPC-W09-UPD-070/071/074 (gates): IMPLEMENT (schema-known / corrupt-fails-safe / plugin-survives-absence tests).
- HPC-W09-PLUGINSET-001 (W08 namespacing ownership): IMPLEMENT (namespaced-key + core-guard tests via owned bridge).
- HPC-W09-PLUGINSET-002 (absent/disabled/reinstalled/upgraded): IMPLEMENT (absence + upgrade-merge tests).
- HPC-W11-TODO-SETTINGS-PERSIST-001: IMPLEMENT (shell injection + attach + builder tests).
- HPC-W11-TODO-SETTINGS-PERSIST-002: IMPLEMENT (success-after-write + failure-raises + GUI negative tests).
- HPC-W11-TODO-SETTINGS-PERSIST-003: IMPLEMENT (reopen-from-storage test + GUI reopen readback).
- HPC-W11-TODO-SETTINGS-PROFILE-001: IMPLEMENT (A/B isolation test).
- HPC-W11-TODO-SETTINGS-RUNTIME-001: IMPLEMENT (live set + measurable toggle test).
- HPC-W11-TODO-SETTINGS-RESTART-001: IMPLEMENT (empty restart set declared + dialog shows no restart claim; future gated keys must declare).
- HPC-W11-TODO-SETTINGS-PARITY-001: IMPLEMENT (parity map + legacy-ignore test).
- HPC-W11-TODO-SETTINGS-SILENT-ERROR-001: IMPLEMENT (attributed errors end-to-end; GUI negative pins visibility).
- HPC-W09-TODO-027/031/032 (feature/action inventories): IMPLEMENT as far as settings-owned surface goes (settings inventory complete; visible-action enumeration lives with its owner waves — no W37-owned action added or left unclassified; W37 adds no UI actions).
- HPC-W09-TODO-028 (SETTINGS_INVENTORY.md): IMPLEMENT (key-level table in `wx_settings.SETTINGS_INVENTORY` + this report; no user-changeable setting missing: all 8 dialog/profile keys inventoried with consumer and control).
- HPC-W09-TODO-029/030 (acceptance/manual matrices + spec jsons): IMPLEMENT for the settings slice (verify matrix TODO-033 proven per key; full program matrices are controller/integration-owned, not wave-local).
- HPC-W09-TODO-033 (per-setting default/alternate/persist/runtime/restart/scope): IMPLEMENT (matrix test).
- HPC-W09-TODO-034 (CLI/GUI agreement): IMPLEMENT (shared-record test: CLI session + Qt dialog + wx dialog + SSH client consume identical profile keys).
- HPC-W09-TODO-DOCS-RUNTIME-001: IMPLEMENT (Qt-specific graphics settings classified DEPRECATED and ignored by construction; HELP text untouched — no QtWebEngine claim on the wx settings path; legacy-key test pins it).
- HPC-W09-TODO-STARTUP-CHANGELOG-SCOPE-001: IMPLEMENT (startup changelog is a version-acknowledgement setting `last_seen_changelog_version` with live getter/setter; no Qt-popup state migrated — deliberate V2 scope, changelog service retained).
- HPC-W09-TODO-MIGRATION-SETTINGS-001: IMPLEMENT (legacy global transfer_parallelism migration, idempotent).
- HPC-W09-TODO-MIGRATION-QUOTA-001: IMPLEMENT (legacy bool source-only migration).
- HPC-W09-TODO-MIGRATION-TERMINAL-001: IMPLEMENT (terminal history deliberately NOT in V2 migration scope — asserted by decision, not omission).
- HPC-W09-TODO-050 (persistence + profile-isolation acceptance): IMPLEMENT (PERSIST + PROFILE tests).
- HPC-W09-TODO-SOAK-LONG-001: EXTERNAL_BLOCKED (hours-scale packaged soak cannot run in-phase; resume point recorded; all safe local checks complete).
- HPC-W09-TODO-ARCH-BOUNDARY-001: IMPLEMENT (settings behavior behind `config.storage` / `plugins.settings` / service coercions; delegation test; no site logic duplicated in GUI handlers).

No AWAITING_INPUT. One EXTERNAL_BLOCKED (SOAK-LONG-001, justified above).

## Resume state

Completed and verified:
- Settings inventory, atomic load/save matrix, real shell→dialog→storage persistence, profile isolation, live/restart declarations, Qt parity, attributable errors, plugin/provider compat, migrations, CLI/GUI agreement.
- 31 new tests green; 87 + 5 + 36 regression tests green; diff reviewed; reports current.

In progress: none (worker done; awaiting fresh independent audit).

Open P0/P1: none owned.
Open P2/P3: DEF-W37-003 (P2 routed to editor-wave owner); DEF-W37-004 (P3 EXTERNAL_BLOCKED soak, controller-scheduled).

Pending tests/evidence: fresh independent audit (controller-owned); controller-scheduled hours-scale soak.

Last exact commands run:
- PYTHONIOENCODING=utf-8 python -m pytest tests/test_wx_settings.py tests/test_config_storage_atomic.py tests/test_w03_settings_provider_inventory.py -q → 22 passed (pre-edit baseline)
- PYTHONIOENCODING=utf-8 python -m pytest tests/test_w37_settings_persistence.py -q → 31 passed
- PYTHONIOENCODING=utf-8 python -m pytest tests/test_wx_settings.py tests/test_config_storage_atomic.py tests/test_w03_settings_provider_inventory.py tests/test_w34_provider_settings.py tests/test_w35_plugin_manager_gui.py tests/test_w36_packaged_docs.py tests/test_connection_advanced_settings.py tests/test_live_tracking_settings.py tests/test_profile_storage_areas.py tests/test_profile_transfer_settings.py -q → 87 passed
- PYTHONIOENCODING=utf-8 python -m pytest tests/test_wx_shell.py -q → 5 passed
- PYTHONIOENCODING=utf-8 python -m pytest tests/test_wx_dispatch_error_gov.py -q --deselect ...distinct_owners → 36 passed, 1 deselected (sibling-owned)
- git diff --check (owned files) → clean

Next actions:
1. Controller: fresh independent audit of W37 (do not reuse stale PASS).
2. Controller: merge/reconciliation + schedule SOAK-LONG-001 packaged soak out-of-phase.

Evidence/artifact identities:
- Tested SHA: c8293d3ca309526ed250c794c3b294f7c54ef369 + W37 diff (src/hpc_gui/wx_settings.py, src/hpc_gui/wx_settings_view.py, src/hpc_gui/wx_shell.py APP-SETTINGS hunk, tests/test_w37_settings_persistence.py)
- New tests: tests/test_w37_settings_persistence.py (31 tests)
- This report: docs/wave-reports/v2/opencode/W37_WAVE_REPORT.md
- Audit (fresh-context, controller-owned): docs/wave-reports/v2/opencode/W37_AUDIT_REPORT.md

## Final summary block

FIX-A: real settings persistence wiring (shell injection + view snapshot persist + inventory/declarations bridge)
DEF: DEF-W37-001 (shell opens settings with no real state/callback) + DEF-W37-002 (view drops supplied callback; only checksum persisted)
Root cause: settings dialog predates storage wiring — empty default model, callback ignored for prebuilt models, worker persists one key.
Before EV: `_dispatch` source shows bare `show_settings(parent=parent)`; `_build_settings` ignores `apply` for prebuilt models.
After EV: EV-W37-001 (31 passed: builder reads live storage, Apply persists with readback, reopen loads from storage, profile A/B isolated, GUI FULL event→config.json→reopen, negative write-failure shows error with zero OK).
Regression test: test_w37_wx_apply_event_persists_to_storage + test_w37_wx_failed_persist_shows_error_never_false_ok
Sensitivity proof: failed-write injection (save_config OSError + os.replace OSError) raises instead of OK; malformed/empty/partial inputs back up and fall back; unknown keys survive; wrong types coerce; absent plugin returns defaults.
New/modified tests: tests/test_w37_settings_persistence.py (31 new; contract/integration/GUI taxonomy in file).
Skipped/xfail changes: none.
Package evidence: N/A (no owned requirement needs a fresh wheel).
External evidence: EXTERNAL_BLOCKED only for SOAK-LONG-001 (hours-scale packaged soak; resume point in report).
Open P0/P1: none.
Open P2/P3: DEF-W37-003 (P2 routed, sibling editor surface); DEF-W37-004 (P3 EXTERNAL_BLOCKED soak).
Two-fix gate: N/A single-fix wave (one coherent persistence-wiring fix; DEF-W37-003/004 are routed/blocked, not second fixes).
Wave decision: GO (worker) — pending fresh independent audit.
