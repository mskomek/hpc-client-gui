# W49 Wave Report — GJ-05 Plugin Manager/provider journey

```text
Wave: W49
Canonical report path: docs/wave-reports/v2/opencode/W49_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (sibling-wave working-tree changes uncommitted; controller owns commit/integration; W49 made zero product/test edits)
Content identity (controller handoff): bc8e0c25be61b35f5adab6343064706bcf1bd8e2c0cbe19e9183af9a0bc4bcb5
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W49 run phase)
Last updated: 2026-09-25
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W49.md` (wave_id W49, execution kind, canonical_source W49, 1 owned requirement `HPC-W10-GJ05-PATH-001`, start gate NONE, cohort P10-golden-journeys, required evidence `GUI,PACKAGE`, integration refs W44 non-blocking, unattended/non-interactive contract, Golden-Journey candidate rule: W44 candidate is behaviorally read-only).
2. `opencode/REQUIREMENT_REGISTRY.md` line 1296: `HPC-W10-GJ05-PATH-001` MANDATORY — "Execute GJ-05 as this explicit end-to-end path: open Plugin Manager → browse/search or offline/cache state → manage installed → install/update/remove/enable-disable safe fixture → provider registration/state reflects result."
3. `opencode/TODO_OWNERSHIP_MAP.md`: no rows owned by W49 (verified: grep for W49 returns no TODO-detail rows; only the registry row above).
4. `opencode/sources/WAVE_V2_FINAL_10.md` → GJ-05 section (lines 110-118): open Plugin Manager → browse/search or offline/cache state → manage installed → install/update/remove/enable-disable safe fixture → provider registration/state reflects result.
5. Live code before edits: `src/hpc_gui/wx_plugins.py` (`WxPluginManagerModel`: `build_cards_from_registry` network/cache/offline merge, `filtered_cards` discover/installed/updates views + search, `install_or_update`/`default_installer`/`install_with_default_or_injected`, `set_enabled`, `remove`, `rollback`); `src/hpc_gui/wx_plugins_view.py` (wx event wiring, refresh worker, Online/Cached/Offline status); `src/hpc_gui/plugins/installer.py` (`install_plugin_from_registry` exact-file protocol); `src/hpc_gui/plugins/loader.py` (`load_installed_plugins`, fail-closed containment); `src/hpc_gui/plugins/state.py` (`record_installed_version`, `remove_plugin`, `set_plugin_disabled`); `src/hpc_gui/plugins/providers.py` (`registered_providers` loader→adapter→capability chain, `ui_global_mutation_violations`); `src/hpc_gui/services/provider_capabilities.py` (W02 truthful capability view). No product edits made by W49 — candidate treated as read-only per wave contract.

## Baseline capture

```text
Evidence ID: EV-W49-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files + untracked sibling artifacts preserved untouched; W49 added zero tracked hunks, zero new source/test files outside .tmp)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
git log -1: c8293d3c (HEAD -> develop) Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
```

Content-identity note: `waves/` is gitignored so the pending spec lives outside Git history by program design. The worker proceeded on current repository truth without editing the spec; identity reconciliation is controller-owned. HEAD `c8293d3` matches the W44 audit candidate SHA and the W45–W48 baselines, and the handoff content identity `bc8e0c25…` matches the W45–W48 handoffs.

Sibling-hunk disclaimer: the working tree contains pre-existing sibling modifications including `src/hpc_gui/wx_plugins.py`, `src/hpc_gui/wx_plugins_view.py`, `src/hpc_gui/plugins/installer.py`, `src/hpc_gui/plugins/loader.py`, `src/hpc_gui/plugins/models.py`, `src/hpc_gui/plugins/validator.py`, `src/hpc_gui/ui/dialogs/plugin_manager_dialog.py` and `tests/test_remote_entry_helpers.py`. These hunks pre-date the W49 run phase and were not authored, reviewed, or claimed by W49. After controller integration or conflict resolution affecting the plugin/provider surfaces, the affected W49 slices and the journey harness must be re-run before audit acceptance.

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
OBS-W49-001 | N/A | GJ-05 path fully executable on current candidate | EV-W49-GUI (222 passed, 20 pre-existing conditional skips, 0 failed) + EV-W49-JOURNEY (27/27 product-path checks PASS) | n/a — journey holds, no product defect | none | none needed (read-only candidate rule) | NO (journey replay, not a remediation) | VERIFIED
OBS-W49-002 | N/A | cross-file wx suites crash natively in one process (access violation in test_plugin_manager_ui.py::test_first_show_starts_exactly_one_automatic_refresh when sharing a process with earlier wx suites) | .tmp/w49-run/combined_b.log faulthandler trace; each file green in its own process (37 + 51 + 9) | wx native App/frame lifetime across suites in one process; test-isolation property, not product behavior (W49 made zero product edits) | none for evidence (slices run process-isolated, exactly as each suite's own CI shard would) | none (no product change; no test edited) | NO | RECORDED
```

Golden-Journey candidate rule applied: no product behavior was patched inside W49. No defect was found on the GJ-05 path, so nothing was routed to another owner. Second-defect sweep dimensions (registry/browse truthfulness, search filtering, network/cache/offline distinguishability, installed/updates views, install/update integrity, enable/disable containment, duplicate/conflict handling, provider capability truthfulness, UI-global bypass, Qt-surface separation) are all covered by the green slices below; no sweep dimension surfaced a W49-owned defect.

Harness-correctness note (worker-owned, recorded honestly): the first harness run failed at `PROVIDER_REGISTERED` because the harness read a non-existent `cluster_profiles` attribute off `PluginLoadResult` instead of the canonical `registered_providers()` chain (which walks `result.plugins[].cluster_profiles`). The harness was corrected to the product's own `providers.registered_providers()` path and re-run clean (27/27 below); only the corrected run is claimed as EV-W49-JOURNEY.

## Implementation

No product-code, test, or config changes. W49 is a journey-replay wave on a read-only candidate; the only new artifacts are this report and the `.tmp/w49-run/` harness (temp, never committed as evidence).

## Tests and evidence

### EV-W49-GUI — journey GUI/runtime slices (all green, exact reruns at HEAD `c8293d3`, `PYTHONPATH=src`, `-p no:cacheprovider`, process-isolated per wx-lifetime note)

```text
Evidence ID: EV-W49-GUI
tests/test_w32_discovery_manifest.py + tests/test_w33_lifecycle_isolation.py + tests/test_w34_provider_settings.py → 55 passed
  (discovery/manifest/compat, enable-disable lifecycle + isolation + conflicts, provider registration + settings ownership)
tests/test_w35_plugin_manager_gui.py + tests/test_wx_plugins.py → 9 passed
  (model refresh network/cache/offline merge, REAL wx button-event refresh with Online/Cached/Offline status readback, views/search distinctness, install/update/remove/enable-disable/compat/restart/offline GUI pins)
tests/test_plugin_installer.py → 51 passed
  (exact-file installer protocol, integrity, fail-closed paths)
tests/test_plugin_manager_ui.py → 37 passed
  (Qt Plugin Manager UI surface incl. single-automatic-refresh behavior)
tests/test_plugin_core.py → 41 passed
  (plugin core contract)
tests/test_plugin_contract.py → 0 passed, 20 skipped (ALL skips pre-existing and conditional: require HPC_GUI_CONTRACT_REPO pointing at an official plugins checkout; unavailable infrastructure, not weakened by W49)
tests/test_w44_arch_qt_wx_package.py + tests/test_plugin_e2e.py + tests/test_plugin_security.py → 29 passed
  (Qt/wx/package arch pins, end-to-end plugin flows, security containment)
GUI verdict: 222 passed, 20 skipped (conditional-external only), 0 failed
  (55 + 9 + 51 + 37 + 41 + 29 = 222 passed)
```

Isolation note: the seven slice commands above each run in their own process. A single combined process of the wx-bearing files ends in a native access violation inside `test_plugin_manager_ui.py::test_first_show_starts_exactly_one_automatic_refresh` (faulthandler log at `.tmp/w49-run/combined_b.log`); each constituent file is green alone. This is recorded, not repaired: W49 owns a journey replay on a read-only candidate, and no suite file was edited, skipped, or weakened to obtain green.

GJ-05 step → evidence mapping:

| GJ-05 step | Evidence |
|---|---|
| open Plugin Manager | `OPEN` harness check (`WxPluginManagerModel` constructs) + `test_w35_wx_refresh_event_drives_real_backend_and_status` (real panel build + button events) |
| browse/search | `BROWSE_*` + `SEARCH_HIT`/`SEARCH_MISS_EMPTY` harness checks + `test_w35_model_views_and_search_are_distinct` + discovery slices (`test_w32`) |
| offline/cache state | `CACHE_SOURCE` + `OFFLINE_FAIL_CLOSED` harness checks + wx refresh test NEG paths (network-down→Cached, fresh-root→Offline with status-label readback) |
| manage installed | `MANAGE_INSTALLED_VIEW`/`MANAGE_INSTALLED_FILTER` harness checks + installed/updates view tests |
| install/update/remove/enable-disable safe fixture | `INSTALL_*`/`UPDATE_*`/`DISABLE_*`/`ENABLE_*`/`REMOVE_*` harness checks + `test_w33` lifecycle/isolation + `test_plugin_installer` (51) + `test_wx_plugins` lifecycle actions |
| provider registration/state reflects result | `PROVIDER_REGISTERED`/`PROVIDER_AFTER_UPDATE`/`PROVIDER_WITHDRAWN_WHEN_DISABLED`/`PROVIDER_RESTORED_WHEN_ENABLED`/`PROVIDER_WITHDRAWN_AFTER_REMOVE`/`PROVIDER_NO_UI_GLOBAL_BYPASS` harness checks via canonical `registered_providers()` + `test_w34` provider/settings slices |

### EV-W49-JOURNEY — disposable end-to-end journey replay on product paths

```text
Evidence ID: EV-W49-JOURNEY
Harness: .tmp/w49-run/gj05_journey.py (disposable; W49-disjoint tmp root, safe fixture plugin org.hpcclient.w49probe v1.0.0→v1.0.1, profile w49probe; no network, no real user config)
Product paths exercised: WxPluginManagerModel (open/browse/search/views/source/install/enable/remove) + plugins.state (record/remove/disable) + plugins.storage (active versions) + plugins.loader (containment) + plugins.providers.registered_providers (loader→adapter→capability chain, the exact registration readback under acceptance)
Observed result:
  OPEN: OK
  BROWSE_SOURCE_NETWORK: OK, BROWSE_CARD_VISIBLE: OK, BROWSE_COMPATIBLE: OK, BROWSE_NOT_INSTALLED_YET: OK
  SEARCH_HIT: OK, SEARCH_MISS_EMPTY: OK
  CACHE_SOURCE: OK, OFFLINE_FAIL_CLOSED: OK
  INSTALL_ACTIVE: OK, MANAGE_INSTALLED_VIEW: OK, MANAGE_INSTALLED_FILTER: OK
  PROVIDER_REGISTERED: OK, PROVIDER_FROM_FIXTURE: OK, PROVIDER_NO_PROBLEMS: OK, PROVIDER_NO_UI_GLOBAL_BYPASS: OK
  UPDATE_OFFERED: OK, UPDATE_ACTIVE: OK, PROVIDER_AFTER_UPDATE: OK
  DISABLE_READBACK: OK, PROVIDER_WITHDRAWN_WHEN_DISABLED: OK
  ENABLE_READBACK: OK, PROVIDER_RESTORED_WHEN_ENABLED: OK
  REMOVE_RESULT: OK, REMOVE_ACTIVE_GONE: OK, REMOVE_MANAGE_READBACK: OK, PROVIDER_WITHDRAWN_AFTER_REMOVE: OK
  GJ05_JOURNEY_RESULT: PASS (27/27)
Cleanup: fixture lives only under the disposable tmp root (no repo, plugin-dir, or shared-namespace mutation); nothing to uninstall from the user environment.
```

### EV-W49-PKG — PACKAGE class

```text
Evidence ID: EV-W49-PKG
No packaged artifact was built, published, or claimed by W49 (candidate freeze is owned by W56–W61). Recorded honestly as NO-CANDIDATE.
No product/package-content modification was made by W49, so no freeze invalidation arises from this Wave.
Plugin payload integrity on the journey path is additionally pinned by the installer slices (exact-file protocol, manifest hash trust anchors) and the W44 arch/package pins (29-slice group), but no artifact SHA-256 is claimed because no candidate artifact exists at this Wave.
```

Evidence classes: `GUI` (required) → EV-W49-GUI (222 passed + 20 conditional-external skips + real wx event proof) + EV-W49-JOURNEY (27/27 product-path checks PASS). `PACKAGE` (required) → EV-W49-PKG (NO-CANDIDATE, honestly recorded; freeze owned downstream). No mocks substituted for any owned claim.

## Diff review

```text
Evidence ID: EV-W49-DIFF
Tracked hunks added by W49: none (zero src/test/config edits; read-only candidate rule honored)
New files: docs/wave-reports/v2/opencode/W49_WAVE_REPORT.md (this report; allowed closeout-only path)
Temp only: .tmp/w49-run/gj05_journey.py + .tmp/w49-run/combined_a.log + .tmp/w49-run/combined_b.log (never committed)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
Scope check: no sibling M file touched; no test weakened (zero skip/xfail/assertion edits; the 20 contract skips are pre-existing env gates); no secrets in report or harness (no tokens, keys, or hosts; hashes truncated to class); no generated/binary noise.
```

## Handoff / DAG unlocks

Historical unlock target W55 is an integration hint only; no downstream Wave was started by this worker. No shared lab, device, or namespace was used (fully local disposable replay); nothing to clean beyond OS temp GC.

## Findings and resume state

- No owned blocking defect remains. GJ-05 executes end-to-end on the integrated candidate: GUI slices 222 passed / 0 failed (+ 20 pre-existing conditional skips) with real wx event proof + disposable journey replay 27/27 PASS.
- Cross-scope routes: none (no product defect observed; the single-process wx crash is a suite-isolation property, recorded not routed as a product finding).
- No `AWAITING_INPUT` (no concrete missing artifact/API).
- No `EXTERNAL_BLOCKED` (no external prerequisite; W49 requires GUI+PACKAGE only).
- No `TWO-FIX-EXCEPTION` needed: W49 owns a journey-replay requirement, not a stabilization quota; the candidate rule forbids manufacturing product fixes.
- Resume point: controller fresh independent audit of this READY_FOR_AUDIT candidate; auditor re-runs the seven EV-W49-GUI slice commands process-isolated + `PYTHONPATH=src python .tmp/w49-run/gj05_journey.py` verbatim and inspects EV-W49-DIFF (expect: report file only). If integration rebased sibling hunks in `wx_plugins*.py`/`plugins/*`/provider surfaces, re-run affected slices + harness first.

---

## Contradiction scan

- PACKAGE status is uniformly NO-CANDIDATE — no artifact claim anywhere.
- Full-suite green is never claimed; only the GJ-05 slices are claimed green with exact counts (222 passed / 20 conditional skips / 0 failed).
- The single-process wx crash is uniformly disclosed as an isolation property with per-file green commands — no combined-green claim anywhere.
- The first (superseded) harness run is uniformly disclosed as a harness attribute bug, never claimed as evidence; only the corrected 27/27 run is claimed.
- Provider registration is uniformly the canonical `registered_providers()` chain readback — no direct-payload or controller-only registration claim anywhere.
- Disable/remove are uniformly verified by loader-level withdrawal (provider absent), not just card flags.
- No test weakened; no product file touched.

## Review passes

- Claim-to-source: the owned ID (`HPC-W10-GJ05-PATH-001`) traces to live owners (`wx_plugins.py` model, `wx_plugins_view.py` wiring, `plugins/installer.py`, `plugins/loader.py`, `plugins/state.py`, `plugins/providers.py`, `services/provider_capabilities.py`) + pinned tests/commands in this report.
- Diff review: zero tracked hunks by W49; sibling hunks explicitly disclaimed with re-run condition.
- Adversarial: search-miss emptiness proves filtering is real (not show-all); offline fail-closed on unknown source proves source labels are enforced; update_offered→active flip proves the update path mutates registration rather than card text; disabled/removed withdrawal at the loader level proves containment is backend truth (not UI flags); `PROVIDER_NO_UI_GLOBAL_BYPASS` proves no out-of-band injection; installer + arch pins prove payload integrity without claiming an artifact.

## Resume state

```text
Completed and verified:
- EV-W49-BASELINE (HEAD c8293d3, dirty-tree disclaimed, diff --check clean)
- EV-W49-GUI (55 + 9 + 51 + 37 + 41 + 29 = 222 passed, 20 conditional-external skipped, 0 failed; process-isolated slices)
- EV-W49-JOURNEY (27/27 product-path checks PASS, disposable fixture, canonical provider chain)
- EV-W49-PKG (NO-CANDIDATE, honestly recorded)
- EV-W49-DIFF (zero tracked hunks)

In progress: none
Open P0/P1: none
Open P2/P3: none
Pending tests/evidence: controller fresh independent audit
Last exact commands run:
- PYTHONPATH=src python -m pytest tests/test_w32_discovery_manifest.py tests/test_w33_lifecycle_isolation.py tests/test_w34_provider_settings.py -p no:cacheprovider -q → 55 passed
- PYTHONPATH=src python -m pytest tests/test_w35_plugin_manager_gui.py tests/test_wx_plugins.py -p no:cacheprovider -q → 9 passed
- PYTHONPATH=src python -m pytest tests/test_plugin_installer.py -p no:cacheprovider -q → 51 passed
- PYTHONPATH=src python -m pytest tests/test_plugin_manager_ui.py -p no:cacheprovider -q → 37 passed
- PYTHONPATH=src python -m pytest tests/test_plugin_core.py -p no:cacheprovider -q → 41 passed
- PYTHONPATH=src python -m pytest tests/test_plugin_contract.py -p no:cacheprovider -q → 20 skipped (HPC_GUI_CONTRACT_REPO gate)
- PYTHONPATH=src python -m pytest tests/test_w44_arch_qt_wx_package.py tests/test_plugin_e2e.py tests/test_plugin_security.py -p no:cacheprovider -q → 29 passed
- PYTHONPATH=src python .tmp/w49-run/gj05_journey.py → GJ05_JOURNEY_RESULT: PASS (27/27)
- git diff --check → exit 0 (sibling CRLF warnings only)

Next actions:
1. Controller fresh independent audit of W49 (re-run slices process-isolated + harness, inspect diff).
2. On audit PASS, close W49 independently.

Evidence/artifact identities:
- EV-W49-BASELINE @ c8293d3
- EV-W49-GUI @ c8293d3 (222 passed / 20 conditional skipped / 0 failed)
- EV-W49-JOURNEY disposable root w49-gj05-* (27/27, fixture org.hpcclient.w49probe 1.0.0→1.0.1, profile w49probe)
- EV-W49-PKG: NO-CANDIDATE
- EV-W49-DIFF: report-file-only
```
