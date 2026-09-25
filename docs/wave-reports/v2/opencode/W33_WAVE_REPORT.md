# W33 -- Plugin enable/disable lifecycle and isolation - Wave Report

```text
Wave: W33
Canonical report: docs/wave-reports/v2/opencode/W33_WAVE_REPORT.md
Repository: hpc-client-gui / develop
Branch: develop
Baseline SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Tested implementation: working tree at 3e9635ba + W33-owned additions
  (src/hpc_gui/plugins/lifecycle.py [new],
   src/hpc_gui/i18n/en.json + tr.json [owned key additions],
   src/hpc_gui/ui/dialogs/plugin_manager_dialog.py [owned note],
   src/hpc_gui/wx_plugins_view.py [owned note],
   tests/test_w33_lifecycle_isolation.py [new, 22 tests])
  Plus pre-existing uncommitted hunks (preserved, not owned by W33):
   src/hpc_gui/plugins/loader.py + installer.py + models.py + validator.py [W32-owned],
   src/hpc_gui/plugins/discovery.py [untracked, W32-owned],
   src/hpc_gui/i18n/en.json + tr.json [other hunks sibling-owned],
   src/hpc_gui/services/slurm_models.py [sibling-owned],
   src/hpc_gui/services/files_ssh.py + output_follower.py [sibling-owned],
   src/hpc_gui/wx_editor_view.py + wx_jobs.py + wx_shell.py [sibling-owned],
   src/hpc_gui/wx_plugins_view.py [W26-owned hunk preserved],
   src/hpc_gui/services/job_identity.py + job_list_filter_sort.py +
   job_submit_cancel.py + jobs_refresh_state.py [untracked, sibling-owned],
   tests/test_w26/test_w27/test_w28/test_w29/test_w30/test_w31_*/test_w32_* [untracked, sibling-owned]
Current HEAD: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Content handoff: controller content_identity
  8e529756ea0befb1fa515882e5c6fbe7d22c3bf8d2c59f14c112f8e401cea295
  (phase=run handoff for W33)
Observed waves/pending/W33.md SHA-256 (BOM-stripped, LF-normalized bytes):
  102bba7a6f96da11844c57073818ffe405d1b25c4ae9eb760aa151345e1ef15d
  (frontmatter wave_id=W33/wave_kind=execution/canonical_source=W33/
   12 owned IDs/aggregate_close_owner=false/evidence_policy=wave-local/
   audit_policy=fresh-independent verified consistent)
Execution start gate: NONE (per Wave independence contract)
No rebase/reset performed. Pre-existing working-tree progress preserved;
W33 touches only its owned lifecycle files plus its own test/report.
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24 (run phase)
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: READY_FOR_AUDIT (independent audit pending, controller-owned)
```

## Scope

W33 owns 12 IDs per `waves/pending/W33.md` frontmatter:
`HPC-W08-LIFE-001..012`. No TODO-detail IDs.
Mandatory authority read before edits: all `opencode/REQUIREMENT_REGISTRY.md`
W33 rows (12 source-derived: 5 Workstream C enable/disable semantics,
1 Workstream D isolation, 6 Workstream E duplicate/conflict handling),
`opencode/TODO_OWNERSHIP_MAP.md` W33 rows (none -- empty result is the
correct reading, not an omission), and
`opencode/sources/WAVE_V2_FINAL_08.md` sections **Workstream C --
Enable/disable semantics**, **Workstream D -- Isolation**, and
**Workstream E -- Duplicate/conflict handling**. Live code inspected
before acting (`plugins/loader.py`, `plugins/state.py`, `plugins/models.py`,
`plugins/storage.py`, `plugins/discovery.py`, `plugins/compatibility.py`,
`plugins/validator.py`, `plugins/ui_contributions.py`, `wx_plugins.py`,
`wx_plugins_view.py`, `ui/dialogs/plugin_manager_dialog.py`,
`ui/main_window.py` plugin-refresh path, `i18n/en.json` plugin keys).
Unattended, non-interactive; no user questions asked. No cross-Wave
worktree/report/temp edits. Pre-existing dirty hunks preserved verbatim.

Controller audit-receipt context (informational, non-gating): W32 audit PASS
at `3e9635ba` recorded by the controller. Per the independence contract it
does not gate W33 start or acceptance. W32 is an integration reference only.

## Discovery

Pre-change narrow baseline (green before W33 additions):
`test_w32_discovery_manifest.py + test_wx_plugins.py` 22 passed.
No W33 product edits yet.

| Finding ID | Severity | Surface | Evidence | Root cause |
|---|---|---|---|---|
| OBS-W33-001 | P2 | entry prerequisites | W33 has no execution start gate; W32 is an integration reference only | per independence contract, non-blocking; every owned requirement proceeds on the current base with disposable roots |
| DEF-W33-002 | P1 (owned, fixed) | lifecycle contract gaps | loader/state/discovery enforced pieces but no single live owner stated the enable/disable effect matrix, the seven-phase isolation guarantee, or the deterministic conflict rules; Qt/wx surfaces offered bare toggles with no behavior note | closed by the W33 edits below; verified by the new 22-test cohort |
| OBS-W33-003 | P2 | wx/Qt process coexistence | wx-then-Qt in one Windows pytest process raises an access violation (reproduced: Qt dialog probe crashes after a wx.App exists) | platform toolkit limitation, not a product defect; Qt GUI proof runs subprocess-isolated (offscreen) per the repo's established pattern |

Second-defect search (dimensions checked): negative (malformed JSON,
identity mismatch, tampered payload, incompatible app, duplicate profile
ids, unsafe entrypoints, ghost active pointers, invalid dep versions),
unavailable-capability/backend (no network or registry access used; all
fixtures local), permission/network failure (loader collects PluginProblem
instead of raising; sibling still loads), cancellation/retry (synchronous
loader/state paths; wx toggle worker is daemon-threaded with closed-guard;
Qt dialog nulls workers on reject), stale callback/result (view handlers
guard `state["closed"]`; rebuild always reloads before use), persistence/
identity/cleanup (disposable tmp roots only; disabled/active JSON under the
same root; no real user config touched), packaging (no package claim made;
N/A justified below), docs/schema comparison (planning source sections
preserved verbatim in trace).

## Requirement trace (requirement -> live owner -> test -> evidence)

- `HPC-W08-LIFE-001` (immediately) -> `plugins/lifecycle.py::ENABLE_DISABLE_EFFECTS`
  (persisted-state row: disabled.json/active.json rewritten synchronously;
  listing row: next `load_installed_plugins()` observes it) +
  `plugins/state.py::set_plugin_disabled` ->
  `test_life_effect_matrix_covers_all_scopes`,
  `test_life001_disable_takes_effect_on_next_load_without_restart`
  (toggle -> flag on disk -> next load skips -> re-enable restores) -> EV-W33-NEW.
- `HPC-W08-LIFE-002` (after tab/view rebuild) -> `lifecycle.py` (rebuild row:
  rebuilds call `load_installed_plugins()` first) + `ui/main_window.py::
  _refresh_plugin_contributions_cache` (live rebuild path) ->
  `test_life002_view_rebuild_reloads_without_disabled_plugin`
  (menu-contribution rebuild yields empty set after disable) -> EV-W33-NEW.
- `HPC-W08-LIFE-003` (after reconnect) -> `lifecycle.py` (reconnect row:
  profile resolution uses the fresh load; saved profiles embed snapshots) ->
  `test_life003_reconnect_resolves_fresh_saved_snapshots_kept`
  (reconnect-time load excludes disabled plugin; saved copy keeps profile_id) -> EV-W33-NEW.
- `HPC-W08-LIFE-004` (after app restart) -> `lifecycle.py` (restart row:
  sufficient but never required; same persisted flags) ->
  `test_life004_restart_reads_same_persisted_flags`
  (re-read of disabled.json/active.json + load from disk) -> EV-W33-NEW.
- `HPC-W08-LIFE-005` (UI states the real behavior) ->
  `i18n/en.json+tr.json::plugins.lifecycle_effect_note` +
  `ui/dialogs/plugin_manager_dialog.py::_populate_installed` (note QLabel,
  objectName `pluginLifecycleNote`) + `wx_plugins_view.py::_build_plugins`
  (note StaticText + language-refresh + controls handle) ->
  `test_life005_effect_note_keys_exist_in_both_languages`,
  `test_life005_wx_view_states_effect_and_toggle_works` (wx FULL: panel builds,
  note readback asserts restart/next-load wording, model toggle persists),
  `test_life005_qt_installed_tab_states_effect` (offscreen subprocess: dialog
  rebuild, note widget text asserted) -> EV-W33-NEW.
- `HPC-W08-LIFE-006` (isolation) -> `lifecycle.py::LIFECYCLE_PHASES` (seven
  phases with containing gates) + `loader.py` (collect-not-raise, sorted
  iteration, no imports, TOFU integrity, whole-plugin rejection) ->
  `test_life006_seven_phases_enumerated`,
  `test_life006_broken_sibling_never_blocks_healthy` (parametrized:
  discovery/manifest-parse/registration/initialization),
  `test_life006_integrity_and_compat_failures_are_contained`
  (tampered + incompatible siblings diagnosed, healthy loads),
  `test_life006_import_never_executes_and_shutdown_is_trivial`
  (no importlib/exec/eval/subprocess in loader source) -> EV-W33-NEW.
- `HPC-W08-LIFE-007` (duplicate plugin ID) -> `lifecycle.py::
  resolve_duplicate_plugin_id` (sorted-first wins; single active source makes
  cross-source duplicates impossible) ->
  `test_life007_duplicate_plugin_id_sorted_first_wins` -> EV-W33-NEW.
- `HPC-W08-LIFE-008` (duplicate provider ID) -> `loader.py` (sorted active
  iteration, first claimant wins, later rejected whole) + `lifecycle.py::
  resolve_duplicate_provider_id` ->
  `test_life008_duplicate_provider_id_sorted_winner_and_diagnostic`
  (real two-plugin load: aaa wins, zzz diagnosed, plus resolver unit proof) -> EV-W33-NEW.
- `HPC-W08-LIFE-009` (two versions of same plugin) -> `state.py::
  activate_version` (validates before moving the pointer; restores on failure)
  + `lifecycle.py::resolve_plugin_versions` (pointer wins, else highest) ->
  `test_life009_two_versions_active_pointer_wins` (real 1.0.0/2.0.0 install:
  pointer honoured, validated switch to 2.0.0, inert version kept on disk),
  `test_life009_no_pointer_highest_version_wins_deterministically` -> EV-W33-NEW.
- `HPC-W08-LIFE-010` (bundled vs user override) -> `discovery.py`
  (bundled inactive, never scanned; user-installed sole active source) +
  `lifecycle.py::resolve_bundled_vs_user_override` ->
  `test_life010_bundled_never_shadows_user_installed` -> EV-W33-NEW.
- `HPC-W08-LIFE-011` (invalid dependency version) -> `validator.py`
  (semver-checked, precise diagnostic) + `lifecycle.py::
  resolve_optional_dependency_versions` (advisory-only; declaring plugin still
  loads) ->
  `test_life011_invalid_dependency_version_is_advisory`
  (validator rejects, resolver diagnoses, missing-dep install still loads) -> EV-W33-NEW.
- `HPC-W08-LIFE-012` (deterministic + visible) -> `lifecycle.py::
  summarize_problems_for_diagnostics` (sorted `(id, version, reason)` lines;
  installed tab renders loader problems) + `describe_for_report` ->
  `test_life012_resolution_is_deterministic_and_visible`
  (two failures summarize identically twice, sorted, 12-ID report) -> EV-W33-NEW.

## Tests and Evidence Required

- Narrow baseline before edits: `test_w32_discovery_manifest + test_wx_plugins`
  22 passed (recorded above).
- New/changed behavioral tests: `tests/test_w33_lifecycle_isolation.py` 22 passed
  (EV-W33-NEW). Command: `python -m pytest tests/test_w33_lifecycle_isolation.py -q`.
- Focused regression: `test_w32_discovery_manifest + test_wx_plugins +
  test_plugin_manager_ui + test_plugin_core + test_plugin_contract +
  test_plugin_installer` 151 passed, 20 skipped (EV-W33-REG1);
  `test_plugin_security + test_plugin_template_integration + test_plugin_v2`
  34 passed (EV-W33-REG2). No failures.
- New/changed tests have meaningful assertions (real files through the loader,
  disable->reload->readback round trips, validated version switch, sorted
  winner by id, subprocess Qt widget text) and legitimate mock boundaries
  (tmp roots only; no network; `monkeypatch.chdir` not needed -- no CWD input
  exists; Qt probe subprocess-isolated for the documented toolkit reason).
- GUI claims (required class GUI): wx FULL runtime proof
  (`test_life005_wx_view_states_effect_and_toggle_works`: real `wx.App`,
  panel build, note-label readback, model toggle through the view's path) plus
  Qt offscreen-subprocess widget proof
  (`test_life005_qt_installed_tab_states_effect`) plus maintained suites
  `tests/test_wx_plugins.py` (3 passed) and `tests/test_plugin_manager_ui.py`
  (in EV-W33-REG1). No static-only substitution.
- Package claims: N/A with justification -- W33 makes no packaged-artifact
  acceptance claim; no wheel SHA asserted.
- External claims: N/A with justification -- no external HPC/registry/network
  used; all fixtures are local disposable roots. No EXTERNAL_BLOCKED needed;
  nothing invented.
- Evidence classes not required by an owned requirement are N/A only with the
  concrete justifications above.

## Diff Review

`git status --short`, `git diff --stat`, `git diff --check`, and full diff
inspected. Owned diff: `plugins/lifecycle.py` [new, ~380 lines: effect matrix,
seven phases, five conflict resolvers, diagnostics summary, report helper],
`tests/test_w33_lifecycle_isolation.py` [new, 22 tests],
`i18n/en.json + tr.json` [one `lifecycle_effect_note` key each; sibling hunks
preserved], `ui/dialogs/plugin_manager_dialog.py` (+8: installed-tab note),
`wx_plugins_view.py` (+29: note widget + language refresh + controls handle;
W26-owned listing hunk preserved verbatim). `git diff --check` clean.
No secrets, no generated/binary noise, no unrelated refactors, no duplicated
business logic in wx views (lifecycle logic lives in `plugins/lifecycle.py`;
views render one i18n sentence), no weakened tests. Untracked sibling
artifacts/reports/tests preserved untouched. Candidate identity for audit:
working tree at `3e9635ba` plus the owned additions listed in the header block.

## Report / Evidence Requirements

This file is the canonical report
(`docs/wave-reports/v2/opencode/W33_WAVE_REPORT.md`). No session-suffixed
copies created. Branch/SHA/working-tree identities, requirement IDs, commands,
counts, evidence identities (EV-W33-NEW, EV-W33-REG1, EV-W33-REG2), findings
(OBS-W33-001, DEF-W33-002 closed, OBS-W33-003 documented), and resume state
are recorded here. Fresh-context audit is controller-owned and pending; no
audit verdict is synthesized in this run phase.

## Stop Conditions

No destructive-Git need, no unresolved authority conflict, no missing mandatory
package/external prerequisite, no cross-Wave ownership escape. Pre-existing
dirty/sibling hunks were preserved; W33 stops after its canonical report is
current with focused tests green. The worker does not start downstream Waves;
W34/W35 integration is a non-blocking hint.

## Definition of Done (run-phase claim)

Every owned non-superseded mandatory requirement is implemented or already
valid with a live owner, required evidence is current and truthful (22 new +
185 focused regression passes, wx FULL + Qt offscreen GUI proofs,
precedence/duplicate/isolation proofs), no owned blocking defect remains
(OBS-W33-003 is a documented toolkit constraint with an isolated proof path,
not a product defect), the diff is reviewed, and this canonical report is
current. Fresh independent audit PASS remains controller-owned and is
explicitly not claimed here.

## Handoff / DAG unlocks

W33 is ready for fresh independent audit. Historical unlock targets are
integration hints only; no other Wave waits on W33 solely because of DAG
metadata. Suggested audit focus: effect-matrix truthfulness against
`state.py`/`loader.py` (disable path, no live-object mutation claim),
seven-phase isolation (tamper/compat/duplicate containment), two-version
pointer discipline, advisory-only optional deps, deterministic diagnostics,
and both UI notes rendering the translated sentence.
