# W54 Wave Report — GJ-10 Migration/updater/restart continuity

```text
Wave: W54
Canonical report path: docs/wave-reports/v2/opencode/W54_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (sibling-wave working-tree changes uncommitted; controller owns commit/integration; W54 made zero product/test edits)
Content identity (controller handoff): bc8e0c25be61b35f5adab6343064706bcf1bd8e2c0cbe19e9183af9a0bc4bcb5
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W54 run phase)
Last updated: 2026-09-25
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W54.md` (wave_id W54, execution kind, canonical_source W54, 1 owned requirement `HPC-W10-GJ10-PATH-001`, zero TODO rows, start gate NONE, cohort P10-golden-journeys, required evidence `GUI,PACKAGE`, integration refs W44 non-blocking, unattended/non-interactive contract, Golden-Journey candidate rule: W44 candidate is behaviorally read-only).
2. `opencode/REQUIREMENT_REGISTRY.md` line 1301: `HPC-W10-GJ10-PATH-001` MANDATORY — "Execute GJ-10 as this explicit end-to-end path: supported older configuration fixture → launch → migrate → core GUI usable → settings/profile/provider state correct → updater check/verification path → safe restart/defer around unsaved state → relaunch."
3. `opencode/TODO_OWNERSHIP_MAP.md`: no rows owned by W54 (verified: grep for W54 returns no matches).
4. `opencode/sources/WAVE_V2_FINAL_10.md` → GJ-10 section (lines 174–186): using a supported older configuration fixture: launch → migrate → core GUI usable → settings/profile/provider state correct → updater check/verification path → safe restart/defer around unsaved state → relaunch.
5. Live code before edits (read-only): `src/hpc_gui/config/storage.py` (`migrate_legacy_transfer_parallelism` pure migration + `load_profiles` first-read id-stamping/migration + `_backup_before_migration` rollback copy + atomic `save_config`), `src/hpc_gui/core/paths.py` (`HPC_GUI_CONFIG_ROOT` isolated per-run root), `src/hpc_gui/wx_settings.py` (`build_model_from_storage` / `persist_model_snapshot` / `load_persisted_snapshot`), `src/hpc_gui/services/update_verification.py` (`verify_artifact` exact size + SHA-256 on the exact path), `src/hpc_gui/services/app_updater.py` (`download_and_verify_release` / `launch_update_installer` production path), `src/hpc_gui/services/update_restart_policy.py` (user-confirmed restart, dirty-defer, exact post-update version equality, unsigned Windows policy). No product edits made by W54 — candidate treated as read-only per wave contract.

## Baseline capture

```text
Evidence ID: EV-W54-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files + untracked sibling artifacts preserved untouched; W54 added zero tracked hunks, zero new source/test files outside .tmp)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
git log -1: c8293d3c (HEAD -> develop) Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
```

Content-identity note: `waves/` is gitignored so the pending spec lives outside Git history by program design. The worker proceeded on current repository truth without editing the spec; identity reconciliation is controller-owned. HEAD `c8293d3` matches the W44 audit candidate SHA and the W45–W53 baselines, and the handoff content identity `bc8e0c25…` matches the W45–W53 handoffs.

Sibling-hunk disclaimer: the working tree contains pre-existing sibling modifications (including `src/hpc_gui/config/storage.py`, `src/hpc_gui/wx_settings.py`, `src/hpc_gui/wx_updater_view.py`, `src/hpc_gui/services/update_restart_policy.py` and related settings/plugins/logs/i18n/docs). These hunks pre-date the W54 run phase and were not authored, reviewed, or claimed by W54. After controller integration or conflict resolution affecting the migration/settings/updater/restart surfaces, the affected W54 slices and the journey harness must be re-run before audit acceptance.

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
OBS-W54-001 | N/A | GJ-10 path fully executable on current candidate | EV-W54-GUI (197 passed, 0 failed) + EV-W54-JOURNEY (23/23 product-path checks PASS) | n/a — journey holds, no product defect | none | none needed (read-only candidate rule) | NO (journey replay, not a remediation) | VERIFIED
```

Golden-Journey candidate rule applied: no product behavior was patched inside W54. No defect was found on the GJ-10 path, so nothing was routed to another owner. Second-defect sweep dimensions (legacy global→per-profile migration + idempotence + profile-win preservation, first-read id-stamping, settings getter truthfulness, provider preservation, core settings-model usability, snapshot reopen, updater exact-verifier accept/reject, tamper rejection, post-update version equality, unsigned-policy truthfulness, user-confirmed restart, dirty-defer vs clean-proceed, provider-aggregated unsaved count, fresh-process relaunch persistence) are all covered by the green slices below; no sweep dimension surfaced a W54-owned defect.

## Implementation

No product-code, test, or config changes. W54 is a journey-replay wave on a read-only candidate; the only new artifacts are this report and the `.tmp/w54-run/` harness (temp, never committed as evidence).

## Tests and evidence

### EV-W54-GUI — journey GUI/runtime slices (all green, exact reruns at HEAD `c8293d3`, `PYTHONPATH=src`, `-p no:cacheprovider`, process-isolated per wx-lifetime note)

```text
Evidence ID: EV-W54-GUI
tests/test_w37_settings_persistence.py → 31 passed
  (settings inventory/schema, corruption matrix, persist/reopen round-trips, profile isolation, live/restart sets, parity, migration, arch boundary, 2 real-wx FULL tests)
tests/test_w38_migration_secrets.py → 12 passed
  (migration + secret handling)
tests/test_config_storage_atomic.py → 2 passed
  (atomic save/backup/coercion)
tests/test_connection_profile_service.py → 12 passed
  (profile persistence/secure-secret lifecycle)
tests/test_profile_identity.py → 3 passed
  (profile identity)
tests/test_app_updater.py → 18 passed
  (updater check/download/verify pipeline)
tests/test_w41_updater_routing.py → 4 passed
  (updater restart routing policy)
tests/test_w43_restart_package_policy.py → 16 passed
  (restart/package policy incl. dirty-defer, version equality, signing policy)
tests/test_wx_updater_spec.py → 23 passed
  (updater spec incl. lifecycle close/restart behavior)
tests/test_wx_lifecycle.py → 3 passed
  (app lifecycle close/restart behavior)
tests/test_editor_controller.py → 3 passed
  (document identity/open/update/save)
tests/test_wx_settings.py → 3 passed
  (dialog model behavior)
tests/test_w03_settings_provider_inventory.py → 17 passed
  (provider settings truthfulness incl. migration assertions)
tests/test_editor_flow.py → 14 passed
  (editor flow incl. local edit lifecycle)
tests/test_w31_race_lifecycle.py → 14 passed
  (race/lifecycle guards)
tests/test_w33_lifecycle_isolation.py → 22 passed
  (lifecycle isolation incl. duplicate/conflict handling)
GUI verdict: 197 passed, 0 failed
  (31 + 12 + 2 + 12 + 3 + 18 + 4 + 16 + 23 + 3 + 3 + 3 + 17 + 14 + 14 + 22 = 197 passed)
```

Isolation note: each slice command above runs in its own process. Sibling waves W49–W53 recorded that a single combined process of wx-bearing suites can end in a native access violation/hang while each file is green alone; W54 therefore claims only the process-isolated slice results above. No suite file was edited, skipped, or weakened to obtain green.

GJ-10 step → evidence mapping:

| GJ-10 step | Evidence |
|---|---|
| supported older configuration fixture | `OLDER_FIXTURE_WRITTEN` harness check (legacy global 4 + profile lacking per-profile value + profile with valid 7 + legacy profile without id) + migration slices (w37/w03/w38) |
| launch | `LAUNCH_LOAD_OK` harness check via product `load_config` on the persisted older config + lifecycle slices |
| migrate | `MIGRATE_CHANGED`/`MIGRATE_LEGACY_COPIED`/`MIGRATE_PROFILE_WIN`/`MIGRATE_IDEMPOTENT` harness checks via product `migrate_legacy_transfer_parallelism` (same function `load_profiles` calls) + `PROFILE_IDS_STAMPED`/`PROFILE_MIGRATED_ON_LAUNCH` via product `load_profiles` |
| core GUI usable | `CORE_GUI_MODEL_USABLE` harness check via product `build_model_from_storage` (WxSettingsModel) + wx-settings/editor/lifecycle slices |
| settings/profile/provider state correct | `SETTINGS_STATE_CORRECT` (snapshot reloads) / `SETTINGS_GETTER_CORRECT` (getter=4) / `PROVIDER_STATE_CORRECT` (local-real preserved) + settings/profile/provider slices (w37/w03/connection-profile/profile-identity) |
| updater check/verification path | `UPDATER_VERIFY_OK` harness check via exact production `verify_artifact` (size + SHA-256) + `UPDATER_TAMPER_REJECTED` (tamper visible) + `POST_UPDATE_VERSION_EXACT` + `SIGNING_POLICY_TRUTHFUL` + updater slices (app_updater/w41/w43/updater-spec) |
| safe restart/defer around unsaved state | `RESTART_USER_CONFIRMED`/`DEFER_DIRTY`/`DEFER_CLEAN`/`DEFERRAL_MESSAGE_SAFE`/`UNSAFE_COUNT_PROVIDER`/`UNSAFE_COUNT_CLEAN` harness checks via product `update_restart_policy` + restart slices (w43/lifecycle/w31/w33) |
| relaunch | `RELAUNCH_CLEAN` fresh-subprocess probe with the same isolated root (A=4 B=7, A id set) + persistence slices (w37) |

### EV-W54-JOURNEY — disposable end-to-end journey replay on product paths

```text
Evidence ID: EV-W54-JOURNEY
Harness: .tmp/w54-run/gj10_journey.py (disposable; W54-disjoint tmp root w54-gj10-*, HPC_GUI_CONFIG_ROOT isolated, no network, no real user config)
Product paths exercised: config.storage migrate_legacy_transfer_parallelism/save_config/load_config/load_profiles/get_transfer_parallelism + core.paths HPC_GUI_CONFIG_ROOT isolation + wx_settings build_model_from_storage/load_persisted_snapshot + services.update_verification verify_artifact (exact production verifier) + services.update_restart_policy restart_mode/should_defer_install/deferral_message/verify_post_update_version/windows_signing_policy/register_unsaved_provider/get_unsaved_count + fresh-subprocess relaunch probe
Observed result:
  OLDER_FIXTURE_WRITTEN: OK
  MIGRATE_CHANGED: OK
  MIGRATE_LEGACY_COPIED: OK
  MIGRATE_PROFILE_WIN: OK
  MIGRATE_IDEMPOTENT: OK
  LAUNCH_LOAD_OK: OK
  PROFILE_IDS_STAMPED: OK
  PROFILE_MIGRATED_ON_LAUNCH: OK
  CORE_GUI_MODEL_USABLE: OK
  SETTINGS_STATE_CORRECT: OK
  SETTINGS_GETTER_CORRECT: OK
  PROVIDER_STATE_CORRECT: OK
  UPDATER_VERIFY_OK: OK
  UPDATER_TAMPER_REJECTED: OK
  POST_UPDATE_VERSION_EXACT: OK
  SIGNING_POLICY_TRUTHFUL: OK
  RESTART_USER_CONFIRMED: OK
  DEFER_DIRTY: OK
  DEFER_CLEAN: OK
  DEFERRAL_MESSAGE_SAFE: OK
  UNSAFE_COUNT_PROVIDER: OK
  UNSAFE_COUNT_CLEAN: OK
  RELAUNCH_CLEAN: OK
  GJ10_JOURNEY_RESULT: PASS (23/23)
Cleanup: all fixture state lives only under the disposable tmp root (config root only); nothing written to the user environment, repo, or shared namespace.
```

### EV-W54-PKG — PACKAGE class

```text
Evidence ID: EV-W54-PKG
No packaged artifact was built, published, or claimed by W54 (candidate freeze is owned by W56–W61). Recorded honestly as NO-CANDIDATE.
No product/package-content modification was made by W54, so no freeze invalidation arises from this Wave.
Migration/updater/restart behavior on the journey path is pinned by the GUI slices above; no artifact SHA-256 is claimed because no candidate artifact exists at this Wave.
```

Evidence classes: `GUI` (required) → EV-W54-GUI (197 passed, real-wx proof in the w37/w43/updater-spec/lifecycle slices) + EV-W54-JOURNEY (23/23 product-path checks PASS). `PACKAGE` (required) → EV-W54-PKG (NO-CANDIDATE, honestly recorded; freeze owned downstream). `EXTERNAL` is not required by W54's wave spec; no real-cluster claim is made (updater verification uses the exact production verifier on fixture bytes with no network; no EXTERNAL substitution). No mocks substituted for any owned claim.

## Diff review

```text
Evidence ID: EV-W54-DIFF
Tracked hunks added by W54: none (zero src/test/config edits; read-only candidate rule honored)
New files: docs/wave-reports/v2/opencode/W54_WAVE_REPORT.md (this report; allowed closeout-only path)
Temp only: .tmp/w54-run/gj10_journey.py (never committed)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
Scope check: no sibling M file touched; no test weakened (zero skip/xfail/assertion edits); no secrets in report or harness (disposable W54-* tokens only; fixture bytes contain no credentials); no generated/binary noise.
```

## Requirement disposition

| Requirement | Disposition | Evidence |
|---|---|---|
| `HPC-W10-GJ10-PATH-001` (explicit GJ-10 path) | IMPLEMENT (journey holds; no remediation needed) | EV-W54-JOURNEY `GJ10_JOURNEY_RESULT: PASS (23/23)` + EV-W54-GUI (197 passed) + EV-W54-PKG (NO-CANDIDATE) |

## Stop / resume

- No `BLOCKED` (no destructive-Git need, no unresolved authority conflict, no missing mandatory prerequisite — all owned checks executable headless + fixture-local).
- No cross-scope defect observed; nothing routed to another owner.
- Resume point for audit: rerun any affected slice + `.tmp/w54-run/gj10_journey.py` verbatim at the audit HEAD if controller integration touches the migration/settings/updater/restart surfaces.

## Resume state

```text
Completed and verified:
- Authority reads (W54 spec, registry line 1301, TODO map, GJ-10 source, live code) + baseline capture at c8293d3
- Discovery pass (OBS-W54-001 only; read-only candidate rule; nothing routed)
- EV-W54-GUI: 197 passed, 0 failed (process-isolated slices)
- EV-W54-JOURNEY: 23/23 product-path checks PASS (disposable isolated root)
- EV-W54-PKG: NO-CANDIDATE honestly recorded
- EV-W54-DIFF: zero tracked hunks, diff --check exit 0
- Canonical report written at docs/wave-reports/v2/opencode/W54_WAVE_REPORT.md

In progress: none (worker complete; awaiting independent audit)
Open P0/P1: none
Open P2/P3: none
Pending tests/evidence: none (fresh-context audit to re-verify at audit HEAD)
Last exact commands run:
- python -m pytest tests/test_w37_settings_persistence.py -p no:cacheprovider -q → 31 passed
- python -m pytest tests/test_w38_migration_secrets.py -p no:cacheprovider -q → 12 passed
- python -m pytest tests/test_config_storage_atomic.py tests/test_connection_profile_service.py tests/test_profile_identity.py -p no:cacheprovider -q → 17 passed
- python -m pytest tests/test_app_updater.py tests/test_w41_updater_routing.py -p no:cacheprovider -q → 22 passed
- python -m pytest tests/test_w43_restart_package_policy.py tests/test_wx_updater_spec.py -p no:cacheprovider -q → 39 passed
- python -m pytest tests/test_wx_lifecycle.py tests/test_editor_controller.py -p no:cacheprovider -q → 6 passed
- python -m pytest tests/test_wx_settings.py tests/test_w03_settings_provider_inventory.py -p no:cacheprovider -q → 20 passed
- python -m pytest tests/test_editor_flow.py tests/test_w31_race_lifecycle.py tests/test_w33_lifecycle_isolation.py -p no:cacheprovider -q → 50 passed
- python .tmp/w54-run/gj10_journey.py → GJ10_JOURNEY_RESULT: PASS (23/23)

Next actions:
1. Controller fresh-context independent audit of W54 (re-run slices + journey at audit HEAD).
2. On audit PASS, close W54 independently (integration hints only).

Evidence/artifact identities:
- Tested implementation SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
- Handoff content identity: bc8e0c25be61b35f5adab6343064706bcf1bd8e2c0cbe19e9183af9a0bc4bcb5
- Report: docs/wave-reports/v2/opencode/W54_WAVE_REPORT.md
- Harness: .tmp/w54-run/gj10_journey.py (temp only)
- Package artifact: none (NO-CANDIDATE; freeze owned W56–W61)
```
