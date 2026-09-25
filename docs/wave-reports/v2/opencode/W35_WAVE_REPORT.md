# W35 — Plugin Manager backend-driven GUI — Wave Report

Wave: W35
Canonical report path: docs/wave-reports/v2/opencode/W35_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Current HEAD: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Tested implementation SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888 (plus uncommitted W35 diff in src/hpc_gui/wx_plugins.py, src/hpc_gui/wx_plugins_view.py, tests/test_w35_plugin_manager_gui.py; sibling dirty files from W26-W34 preserved untouched)
Plugin/external repo SHA(s), if applicable: plugin repo not pinned (local declarative fixtures only; no network)
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24
Session status: READY FOR FINAL REVIEW
Wave decision: GO (worker) — pending fresh independent audit

## Objective

Make the wx Plugin Manager a real backend-driven GUI with truthful browse/manage/update/search/refresh states and lifetime safety (H0).

## Mandatory authority consumed

- waves/pending/W35.md (all owned IDs)
- opencode/REQUIREMENT_REGISTRY.md rows Owning Wave W35 (49 rows: HPC-W08-PM-001..020, 027..048 + 7 TODO-detail IDs)
- opencode/TODO_OWNERSHIP_MAP.md rows Owning Wave W35 (PLUGIN-GUI-001/002, REFRESH-001, SEARCH-001, INSTALL-001, OFFLINE-001, LIFECYCLE-001)
- opencode/sources/WAVE_V2_FINAL_08.md sections: Outcome, Repositories, Entry criteria, Scope, Workstream H0, Targeted tasks
- Live code: src/hpc_gui/wx_plugins.py, src/hpc_gui/wx_plugins_view.py, src/hpc_gui/plugins/registry_client.py, installer.py, loader.py, state.py, storage.py, compatibility.py; tests test_wx_plugins.py, test_w32/33/34, test_plugin_manager_ui.py

## Baseline (pre-edit)

- `git status --short --branch` showed develop at 3e9635ba with pre-existing dirty W26-W34 files (preserved).
- Narrow baseline: tests/test_wx_plugins.py + test_w32_discovery_manifest.py = 22 passed.
- Discovery pass findings (WAVE_FINDINGS):

Finding ID | Severity | Surface | Evidence | Root cause | Impact | Candidate fix | Countable | Status
DEF-W35-001 | P1 | wx refresh/offline | wx_plugins_view.py worker just CallAfter(on_done,None), always status_cached, no fetch_registry_with_cache | fake fetch path, source never exposed | network/cache/offline indistinguishable, browse untruthful | wire real fetch + source | YES | FIXED (FIX-A)
DEF-W35-002 | P1 | wx search | on_search body is `pass` ("Not easily hide rows; fallback: no-op") | no filtering logic | visible search box is no-op (forbidden) | rebuild list from filtered model subset | YES | FIXED (FIX-B)
DEF-W35-003 | P1 | wx views | single ListCtrl, show_plugins ignores initial_tab (TypeError fallback in wx_shell) | no view-mode state | Browse/Manage/Updates silently one generic list | Choice + filtered_cards(view) + initial_tab | YES (part of FIX-B) | FIXED
DEF-W35-004 | P1 | wx install | install_or_update minimal dict + `wx.CallAfter(lambda: setattr...)` + success MessageBox even when outcome None | no fail-closed guard | success reported on no-op | None outcome raises, error shown | YES | FIXED (part of FIX-B hardening)
DEF-W35-005 | P1 | wx lifetime | toggle/remove CallAfter without closed/gen guard, no in-flight guard, double-click race | inconsistent stale-callback guard | close-in-flight touches destroyed controls / leaks workers | gen counter + closed + in-flight on all ops | YES | FIXED
DEF-W35-006 | P2 | wx compat/update | list shows only installed/available, no update-available/active-version, install button never gated | missing merge fields | compat/update/restart state not visible | PluginCard update_available/active_version + button gating | NO (supporting) | FIXED

## Implementation (smallest coherent correction)

- `src/hpc_gui/wx_plugins.py`: extended PluginCard (description/capabilities/update_available/active_version); added `_group_latest_registry_entries` (Qt-parity latest-compatible rule, order-independent); `build_cards_from_registry(registry, source, root, app_version)` merges registry + active + disabled via production services (read_active_versions/read_disabled_ids/entry_is_app_compatible), keeps installed-absent-from-registry visible, fail-closed source mapping; `filtered_cards(view, needle)` distinct discover/installed/updates + truthful search; `registry_entry_for`, fail-closed `install_or_update` (None when no callback/id), `default_installer` via install_plugin_from_registry with configured root/fetcher; preserved old API (set_registry/install/rollback/set_enabled/remove/open_trusted_tool) for existing tests.
- `src/hpc_gui/wx_plugins_view.py`: added view Choice (Discover/Installed/Updates) + `initial_tab` through `_build_plugins/build_plugins_panel/show_plugins` (fixes wx_shell PLUGIN-BROWSE/MANAGE/UPDATES all falling back to generic); `_refresh_list` rebuilds from `filtered_cards(view, needle)` with compat/update/restart bits (`installed/available/enabled/disabled/incompatible/update-available`, active version, lifecycle note); real `refresh_registry` via `fetch_registry_with_cache(root, fetcher)` off GUI thread, Online/Cached/Offline distinct, gen+closed+in-flight guards; `do_install` fail-closed (incompatible blocked, None outcome raises, error shown, no success on no-op), re-reads installed state after; `do_toggle/do_remove` with gen+closed+in-flight guards and correct `exc=exc` capture; `on_close` bumps gen and unsubscribes; language refresh keeps view truthful.
- Framework-neutral boundary preserved: no business/protocol duplication; view/model call `plugins/{registry_client,loader,state,storage,compatibility,installer}` only.
- No cross-Wave cleanup: only W35-owned wx files + new W35 test file changed; sibling dirty files preserved.

## Tests

New: `tests/test_w35_plugin_manager_gui.py` (6 tests):

- REQ-H0 unit `test_w35_model_refresh_merges_registry_with_source` (DEF-001)
- FIX-A FULL `test_w35_wx_refresh_event_drives_real_backend_and_status` (wx event -> network fetch -> Online + 2 rows; failing fetch with cache -> Cached; fresh root failing -> Offline)
- REQ-H0 unit `test_w35_model_views_and_search_are_distinct` (DEF-002/003)
- FIX-B FULL `test_w35_wx_search_and_views_rebuild_truthful_lists` (search rebuilds rows; Choice switches Browse/Manage)
- REQ-H0 unit `test_w35_install_without_backend_action_is_not_success` (DEF-004 fail-closed + happy path)
- REQ-H0 lifecycle `test_w35_wx_close_in_flight_never_touches_destroyed_controls` (DEF-005 stale gen dropped, no cards pushed)

Evidence:

- EV-W35-001: `pytest tests/test_w35_plugin_manager_gui.py -q` → 6 passed (tested SHA 3e9635ba + W35 diff). Command: `/d/Python/Python312/python -m pytest tests/test_w35_plugin_manager_gui.py -q`. Exit 0. passed=6 failed=0 skipped=0.
- EV-W35-002 (sensitivity): old HEAD wx files + new tests → 6 failed (TypeError fetcher, missing merge/views/search). Restored new files → 6 passed. Artifacts: `.tmp/w35-sensitivity/wx_plugins.{old,new}.py`, `wx_plugins_view.{old,new}.py`.
- EV-W35-003 (narrow+broader): `pytest test_wx_plugins + w32 + w33 + w34 + w35` → 64 passed. Exit 0.
- EV-W35-004: `QT_QPA_PLATFORM=offscreen pytest tests/test_plugin_manager_ui.py` → 37 passed (Qt dialog unaffected).
- EV-W35-005 (GUI FULL readbacks): listing GetItemCount/GetItemText + status GetLabel + lifecycle note + view Choice observed from live wx controls (see test bodies).
- Baseline: `pytest test_wx_plugins + w32` pre-edit → 22 passed.

Test taxonomy: unit (model merge/views/install-guard), GUI event/integration (wx FULL with real wx runtime), negative (unknown source/view, no-match search, failing fetch, None install, close-mid-flight), lifecycle/stale (close-in-flight gen, in-flight guards). Mocks limited to injected fetcher/disposable root (legitimate boundary); what tests do NOT prove: packaged artifact with no dev checkout, real network infrastructure (EXTERNAL_BLOCKED not needed — injected fetchers cover network/cache/offline contract; package/external evidence N/A with justification: H0 package claim is controller/integration-owned, no dev-path assistance verified via loader isolation in W32).

## Diff review

- `git diff --check` → clean (only CRLF warnings).
- `git diff --stat` → 15 files dirty, but only 2 product + 1 new test are W35-owned; remaining dirty (i18n, installer/loader/models/validator, services, editor/jobs/shell, dialog note) are sibling-wave work preserved, not touched by this Wave.
- Full diff of W35 files inspected: no secrets, no generated/binary noise, no unrelated changes inside owned files, no weakened tests, no duplicated business logic.
- New tests use meaningful assertions (state transitions, row counts, status labels, source identity, error-vs-success), legitimate mock boundary (fetcher + tmp root), deterministic (bounded polling, no fixed sleeps for sync, cleanup via frame.Destroy, no real user config).

## POST_GREEN_REVIEW

- Duplicate path: Qt dialog grouping rule reused (same latest-compatible semantics), not duplicated.
- Alternate entry: PLUGIN-BROWSE/MANAGE/UPDATES now map to initial_tab; bare show_plugins defaults to discover.
- Silent fallback: none — offline shows Offline, incompatible disables install, None install raises.
- Stale state: gen-checked on every worker completion.
- Identity: all storage/fetch/install use model.root (production root when None).
- Cleanup: daemon threads + closed flag + unsubscribe.
- Dead branch: fake worker + no-op search removed.
- Hardcoded: none.
- Error-as-success: eliminated.
- Packaged divergence: no CWD discovery (loader-owned, W32-proven); packaged discovery remains controller-owned.

## Requirement dispositions (all owned IDs)

- HPC-W08-PM-001 (Outcome contained mechanism): IMPLEMENT via loader/state isolation + GUI truthfulness (W32-W34 backends reused, wx merge fail-closed).
- PM-002/003 (Repositories mskomek/hpc-client-gui[-plugins]): IMPLEMENT (main repo HEAD recorded; plugin claims via local fixtures, no stale cross-repo pin claimed).
- PM-004..008 (Entry prerequisites W07/W02/W04/fetch/disposable fixture): IMPLEMENT as branch conditions proven in-test (disposable tmp roots, injected fetchers, no real user env; W04 packaged harness N/A — controller-owned, not blocking per independence contract).
- PM-009..020 (Scope boundaries discovery/manifest/compat/enable-disable/restart/settings/provider/optionals/containment/UI/packaged/authoring): IMPLEMENT (wx merge + views + compat gating + lifecycle note + provider/settings backends from W32-W34 reused; packaged discovery N/A with justification).
- PM-027 Browse & Install / 028 Manage Installed / 029 Updates / 030 search / 031 refresh / 032 install / 033 update / 034 remove / 035 enable / 036 disable / 037 compat status / 038 restart-required: IMPLEMENT via Choice views + search rebuild + real fetch + fail-closed install/update + toggle/remove + compat/update bits + lifecycle_effect_note.
- PM-039..045,047,048 (TASK-001..007,009,010 rediscover/validate/compat/isolate/lifecycle/boundary/settings/packaged/docs): IMPLEMENT (rediscovery via live code read; validation/compat via validator/compatibility services; lifecycle via state; packaged/docs N/A with controller-owned justification).
- PM-046 (TASK-008 optional capability absence): CONDITIONAL — active branch covered by W34 PROV-001 minimal-profile case; wx preserves optional absence (no dummy values).
- TODO PLUGIN-GUI-001 (wired to real registry/services/root): IMPLEMENT.
- TODO PLUGIN-GUI-002 (distinct Browse/Manage/Updates): IMPLEMENT.
- TODO REFRESH-001 (real network/cache/offline path + source exposed): IMPLEMENT.
- TODO SEARCH-001 (filter actually filters): IMPLEMENT.
- TODO INSTALL-001 (never success on no backend action): IMPLEMENT.
- TODO OFFLINE-001 (network/cached/offline distinguishable): IMPLEMENT.
- TODO LIFECYCLE-001 (close-in-flight safe, no destroyed-control touch/worker leak): IMPLEMENT.

No AWAITING_INPUT (all inputs present via fixtures/injected fetchers). No EXTERNAL_BLOCKED (no real infra required).

## Resume state

Completed and verified:
- Discovery pass + findings table + two independent fixes (FIX-A refresh/offline, FIX-B search/views + install/lifecycle hardening) with regression tests + sensitivity proof + narrow/broader suites + Qt compatibility + diff review + post-green review.

In progress: none (worker done; awaiting fresh independent audit).

Open P0/P1: none owned.
Open P2/P3: none owned (packaged-artifact acceptance is controller-owned integration, not an owned defect).

Pending tests/evidence: fresh independent audit (controller-owned).

Last exact commands run:
- /d/Python/Python312/python -m pytest tests/test_w35_plugin_manager_gui.py -q → 6 passed
- /d/Python/Python312/python -m pytest tests/test_wx_plugins.py tests/test_w32_discovery_manifest.py tests/test_w33_lifecycle_isolation.py tests/test_w34_provider_settings.py tests/test_w35_plugin_manager_gui.py -q → 64 passed
- QT_QPA_PLATFORM=offscreen /d/Python/Python312/python -m pytest tests/test_plugin_manager_ui.py -q → 37 passed
- git diff --check → clean

Next actions:
1. Controller: fresh independent audit of W35 (do not reuse stale PASS).
2. Controller: merge/reconciliation + final validation (PROGRAM_COMPLETE gates owned by controller).

Evidence/artifact identities:
- Tested SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888 + W35 diff
- New tests: tests/test_w35_plugin_manager_gui.py (6 tests)
- Sensitivity: .tmp/w35-sensitivity/
- This report: docs/wave-reports/v2/opencode/W35_WAVE_REPORT.md
- Audit (fresh-context, controller-owned): docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md

## Final summary block

FIX-A: real backend-driven refresh with network/cache/offline distinguishability
DEF: DEF-W35-001 (fake refresh worker, always Cached, no fetch)
Root cause: wx refresh never called fetch_registry_with_cache; source never exposed, so offline masqueraded as cache and browse was static.
Before EV: old worker CallAfter(on_done,None) + status_cached (source trace in pre-edit file); new tests fail on old code (6 failed).
After EV: EV-W35-001/002/003 (network Online + 2 rows, cache Cached, fresh-root Offline; 6 passed; sensitivity 6 failed -> 6 passed).
Regression test: test_w35_model_refresh_merges_registry_with_source + test_w35_wx_refresh_event_drives_real_backend_and_status
Sensitivity proof: old HEAD wx files → 6 failed; restored → 6 passed (same assertions, expected failure reason).

FIX-B: truthful search + distinct Browse/Manage/Updates + fail-closed install + lifetime safety
DEF: DEF-W35-002/003/004/005 (no-op search, single generic list, success-on-no-op, close-in-flight touch)
Root cause: ListCtrl rows were never rebuilt (search pass), no view state (initial_tab ignored), install reported success when outcome None, toggle/remove lacked gen/closed guards — three materially different failure modes from FIX-A's fetch path (view-filter vs data-fetch vs completion-guard).
Before EV: on_search `pass`, single list, TypeError fallback for initial_tab, success MessageBox on None outcome; new tests fail on old code.
After EV: EV-W35-001/003 (search 2->1->0->2, views 2 vs 1, None install is error, stale gen dropped with no cards pushed).
Regression test: test_w35_model_views_and_search_are_distinct + test_w35_wx_search_and_views_rebuild_truthful_lists + test_w35_install_without_backend_action_is_not_success + test_w35_wx_close_in_flight_never_touches_destroyed_controls
Sensitivity proof: same revert run (old code lacks fetcher/views/filter/install-guard/lifetime) → all 6 fail; restored → pass.

Additional fixes: compat/update/restart visibility (update_available/active_version bits, install gating, lifecycle note) as supporting hardening, not counted separately.
Post-green review: PASS (see section).
New/modified tests: tests/test_w35_plugin_manager_gui.py (6 new; REQ/DEF/RACE/NEG/GUI taxonomy in file).
Skipped/xfail changes: none.
Package evidence: N/A (controller-owned integration; no dev-path assistance proven via W32 loader isolation).
External evidence: N/A (injected fetchers cover network/cache/offline contract; no real infra needed).
Open P0/P1: none.
Open P2/P3: none owned.
Two-fix gate: PASS (FIX-A and FIX-B independent: fetch-path vs view-filter/completion-guard, different defect IDs and root causes).
Wave decision: GO (worker) — pending fresh independent audit.
