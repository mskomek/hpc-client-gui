# W34 -- Provider registration and plugin settings integration - Wave Report

```text
Wave: W34
Canonical report: docs/wave-reports/v2/opencode/W34_WAVE_REPORT.md
Repository: hpc-client-gui / develop
Branch: develop
Baseline SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Tested implementation: working tree at 3e9635ba + W34-owned additions
  (src/hpc_gui/plugins/providers.py [new],
   src/hpc_gui/plugins/settings.py [new],
   tests/test_w34_provider_settings.py [new, 14 tests])
  Plus pre-existing uncommitted hunks (preserved, not owned by W34):
   src/hpc_gui/plugins/loader.py + installer.py + models.py + validator.py [W32-owned],
   src/hpc_gui/plugins/discovery.py [untracked, W32-owned],
   src/hpc_gui/plugins/lifecycle.py [untracked, W33-owned],
   src/hpc_gui/i18n/en.json + tr.json [sibling-owned],
   src/hpc_gui/services/slurm_models.py [sibling-owned],
   src/hpc_gui/services/files_ssh.py + output_follower.py [sibling-owned],
   src/hpc_gui/wx_editor_view.py + wx_jobs.py + wx_shell.py + wx_plugins_view.py [sibling-owned],
   src/hpc_gui/ui/dialogs/plugin_manager_dialog.py [W33-owned hunk preserved],
   src/hpc_gui/services/job_identity.py + job_list_filter_sort.py +
   job_submit_cancel.py + jobs_refresh_state.py [untracked, sibling-owned],
   tests/test_w26/test_w27/test_w28/test_w29/test_w30/test_w31_*/test_w32_*/test_w33_* [untracked, sibling-owned]
Current HEAD: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Content handoff: controller content_identity
  398279e0dc210c11d7e8cb415d86541d3dac987cf947e421c41f2a2dc4383f7c
  (phase=run handoff for W34)
Observed waves/pending/W34.md SHA-256 (BOM-stripped, LF-normalized bytes):
  388e0dfb4f81f528220a0c7086f2d96e9ccdd3e57a769b93e63aa5cf2c2106d7
  (frontmatter wave_id=W34/wave_kind=execution/canonical_source=W34/
   7 owned IDs/aggregate_close_owner=false/evidence_policy=wave-local/
   audit_policy=fresh-independent verified consistent)
Execution start gate: NONE (per Wave independence contract)
Content-identity note: controller handoff 398279e0... vs observed W34
  spec-bytes hash 388e0dfb... are distinct program-chain identity vs
  spec-bytes hash by design (same pattern as W32/W33 reports); 7 owned
  IDs + policies verified, no spec tampering -- controller-owned
  reconciliation, non-blocking per the independence contract.
No rebase/reset performed. Pre-existing working-tree progress preserved;
W34 touches only its owned new plugin files plus its own test/report.
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24 (run phase)
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: READY_FOR_AUDIT (independent audit pending, controller-owned)
```

## Scope

W34 owns 7 IDs per `waves/pending/W34.md` frontmatter:
`HPC-W08-PROV-001` (CONDITIONAL, Workstream F provider registration),
`HPC-W08-PROV-002..007` (MANDATORY, Workstream G settings ownership).
No TODO-detail IDs.
Mandatory authority read before edits: all `opencode/REQUIREMENT_REGISTRY.md`
W34 rows (7 source-derived: 1 Workstream F provider-registration boundary,
6 Workstream G settings-ownership rules),
`opencode/TODO_OWNERSHIP_MAP.md` W34 rows (none -- empty result is the
correct reading, not an omission), and
`opencode/sources/WAVE_V2_FINAL_08.md` sections **Workstream F --
Provider registration** and **Workstream G -- Settings ownership**.
Live code inspected before acting (`plugins/loader.py`,
`plugins/models.py`, `plugins/validator.py`, `plugins/storage.py`,
`plugins/state.py`, `plugins/discovery.py`, `plugins/lifecycle.py`,
`plugins/templates.py`, `services/provider_capabilities.py`,
`config/system_profile.py`, `config/storage.py`, `core/log_redaction.py`,
`core/secret_store.py`, `wx_plugins.py`, `wx_plugins_view.py`).
Unattended, non-interactive; no user questions asked. No cross-Wave
worktree/report/temp edits. Pre-existing dirty hunks preserved verbatim.

Controller audit-receipt context (informational, non-gating): W33 audit PASS
at `3e9635ba` recorded by the controller. Per the independence contract it
does not gate W34 start or acceptance. W33 is an integration reference only.

## Discovery

Pre-change narrow baseline (green before W34 additions):
`test_plugin_core.py + test_provider_capabilities.py` 43 passed.
No W34 product edits yet.

| Finding ID | Severity | Surface | Evidence | Root cause |
|---|---|---|---|---|
| OBS-W34-001 | P2 | entry prerequisites | W34 has no execution start gate; W33 is an integration reference only | per independence contract, non-blocking; every owned requirement proceeds on the current base with disposable roots |
| DEF-W34-002 | P1 (owned, fixed) | provider-registration boundary gap | loader/templates/capability-view implemented the pieces but no single live owner stated the `plugin -> provider registration -> capability declaration -> generic service -> wx UI` chain, proved W02 truthfulness for omitted optionals, or scanned the declarative boundary for UI-global bypasses | closed by `plugins/providers.py`; verified by the new PROV-001 cohort (6 tests incl. wx FULL) |
| DEF-W34-003 | P1 (owned, fixed) | settings-ownership gap | no plugin settings module existed: nothing enforced namespacing, restart persistence, core-key protection, type/default validation, absence tolerance, or secret hygiene | closed by `plugins/settings.py`; verified by the new PROV-002..007 cohort (7 tests + wx FULL integration) |
| OBS-W34-004 | P2 | conditional applicability | PROV-001 is CONDITIONAL; fires only when a provider plugin is installed | recomputed from repository truth per the independence contract: empty root -> inactive branch (evidence-backed, no provider installed); installed cluster-profile plugin -> active branch implemented and tested |

Second-defect search (dimensions checked): negative (malformed JSON,
identity mismatch, tampered payload, incompatible app, duplicate profile
ids, unsafe entrypoints, ghost active pointers, invalid dep versions,
wrong setting types, unknown setting keys, core-key smuggling, out-of-range
values, corrupt settings JSON), unavailable-capability/backend (no network
or registry access used; all fixtures local), permission/network failure
(loader collects PluginProblem instead of raising; settings load falls back
to defaults with a warning), cancellation/retry (synchronous loader/state/
settings paths; no workers leaked), stale callback/result (wx save handler
reads live control values at event time; rebuild always reloads before use),
persistence/identity/cleanup (disposable tmp roots only; settings under
`<root>/settings/<id>.json` atomic tmp+replace; disabled/active JSON under
the same root; no real user config touched), packaging (no package claim
made; N/A justified below), docs/schema comparison (planning source sections
preserved verbatim in trace).

## Requirement trace (requirement -> live owner -> test -> evidence)

- `HPC-W08-PROV-001` (CONDITIONAL, active branch: a cluster-profile plugin
  is installed in every provider test) ->
  `plugins/providers.py::registered_providers` (loader typed profiles ->
  templates adapter -> W02 `build_provider_capability_view`; UI consumes
  only this output) + `describe_registration_chain` + `provider_ids_advisory_errors`
  + `ui_global_mutation_violations` (AST scan of `plugins/*.py`) ->
  `test_prov001_chain_enumerated`,
  `test_prov001_provider_registers_through_registry` (1 provider, provenance
  kind=plugin/requirement=PROV-001, scheduler DECLARED),
  `test_prov001_optional_features_omitted_are_not_declared` (minimal profile:
  scheduler DECLARED, storage/quota/optional NOT_DECLARED -- nothing fabricated),
  `test_prov001_no_ui_global_mutation` (AST scan clean),
  `test_prov001_advisory_provider_ids_grant_nothing` (provider_ids without a
  profile/capability registers zero providers),
  `test_prov001_conditional_branch_active_when_provider_present`
  (empty root inactive / installed root active) +
  `test_prov_gui_wx_provider_list_and_settings_roundtrip` (wx FULL) -> EV-W34-NEW.
- `HPC-W08-PROV-002` (be namespaced) ->
  `plugins/settings.py::namespaced_key/parse_namespaced_key/export_namespaced_safe_settings/merge_into_shared`
  (short keys persist locally; shared/export views carry only
  `plugins.<id>.<key>`) -> `test_prov002_settings_are_namespaced` (+ wx FULL
  label readback shows the namespaced key) -> EV-W34-NEW.
- `HPC-W08-PROV-003` (survive expected restart) ->
  `settings.py::save_plugin_settings/load_plugin_settings` (atomic
  tmp+replace JSON under `<root>/settings/<id>.json`; restart = fresh read) ->
  `test_prov003_settings_survive_restart` -> EV-W34-NEW.
- `HPC-W08-PROV-004` (not overwrite core keys) ->
  `settings.py::core_protected_keys/validate_setting_key/merge_into_shared`
  (core set = GENERIC_SLURM_DEFAULTS + system keys; write rejected, merge
  only adds namespaced keys, collision fails closed) ->
  `test_prov004_core_keys_are_rejected` -> EV-W34-NEW.
- `HPC-W08-PROV-005` (validate types/defaults) ->
  `settings.py::validate_plugin_settings/spec_defaults` (exact-type match,
  bool/int strictness, unknown-key rejection, per-key validator callables,
  fail-closed: nothing written on any error) ->
  `test_prov005_types_defaults_validated` -> EV-W34-NEW.
- `HPC-W08-PROV-006` (tolerate plugin absence) ->
  `settings.py::load_plugin_settings/load_all_plugin_settings` (missing file,
  corrupt JSON, invalid values, disabled/removed plugin all yield declared
  defaults with a warning, never a crash; namespaced keys simply remain) ->
  `test_prov006_absence_tolerated`,
  `test_prov007_remove_disable_keeps_settings_crash_free` -> EV-W34-NEW.
- `HPC-W08-PROV-007` (avoid leaking secrets in export/logs) ->
  `settings.py::is_secret_key/export_safe_settings/export_namespaced_safe_settings/redact_settings_for_log`
  (declared `secret: True` or name-matched keys dropped from exports --
  never redacted-in-place -- and rendered as `<redacted>` in logs) ->
  `test_prov007_secrets_never_exported_or_logged` (+ wx FULL path carries no
  secret) -> EV-W34-NEW.

## Tests and evidence

- Narrow baseline before edits: `test_plugin_core.py +
  test_provider_capabilities.py` 43 passed (EV-W34-BASE).
- New cohort: `tests/test_w34_provider_settings.py` 14 passed
  (6 PROV-001 incl. conditional-branch + advisory + AST scan, 7 settings
  ownership, 1 wx FULL integration) (EV-W34-NEW).
- Focused regression after edits: new cohort + `test_plugin_core.py` +
  `test_provider_capabilities.py` + `test_w32_discovery_manifest.py` +
  `test_w33_lifecycle_isolation.py` + `test_plugin_contract.py` +
  `test_plugin_installer.py` = 149 passed, 20 skipped (skips are
  pre-existing platform/toolkit gates, unchanged by W34);
  `test_wx_plugins.py` 3 passed (EV-W34-REG).
- GUI FULL (required `GUI` class): `test_prov_gui_wx_provider_list_and_settings_roundtrip`
  runs real wx runtime in-process: installs a provider plugin, populates a
  live `wx.ListCtrl` from `registered_providers()`, posts a genuine
  `wx.EVT_BUTTON` event through the view handler which saves via
  `settings.py` and updates a live `wx.StaticText`; asserts observed
  control readback (`truba` / DECLARED / `providers=1` / namespaced key /
  `WxName`) bound to candidate identity below. Qt-side note: no Qt surface
  change was made by W34, so no Qt probe is owed; wx FULL plus headless
  model coverage satisfies the owned GUI claims.
- Package class: N/A with justification -- W34 makes no distributable
  artifact claim and pins no external package; all fixtures are local
  disposable roots (no SHA-256 artifact owed).
- External class: N/A with justification -- no external HPC/cluster/registry
  call is made; provider capability views are built from local declarative
  payloads (no `EXTERNAL_BLOCKED` needed; nothing mocked in place of a
  required external probe).

## Diff review

- `git status`: W34 adds only `src/hpc_gui/plugins/providers.py` [new],
  `src/hpc_gui/plugins/settings.py` [new],
  `tests/test_w34_provider_settings.py` [new], and this report. All other
  modified/untracked entries are pre-existing sibling-owned progress,
  preserved untouched.
- `git diff --check`: clean (no whitespace errors).
- `git diff --stat` (tracked): W34 touches no tracked file; the 14-file
  tracked diff is entirely pre-existing sibling-owned work.
- Full new-file review: no secrets, no generated/binary noise, no unrelated
  changes, no duplicated framework-neutral logic (capability vocabulary
  delegates to the W02 owner; system-settings keys delegate to
  `config/system_profile.py`), no weakened tests (strict type checks,
  bool/int separation, fail-closed writes, adversary-tolerant loads).
- `ruff check` on the three new/owned files: clean.

## Candidate / closure identity

- Candidate: working tree at HEAD `3e9635ba1cf0255d5a09f370e91d1ddb73cef888`
  + W34-owned untracked additions (`plugins/providers.py`,
  `plugins/settings.py`, `tests/test_w34_provider_settings.py`) + this
  report. Closure-only changes stay inside the profile allowlist
  (`docs/wave-reports/`, `.tmp/`); behavior-affecting product/test changes
  are exactly the W34-owned files above, covered by EV-W34-NEW/REG.
- No behavior-affecting change was made after the green run; evidence binds
  to this candidate. Any post-green edit would invalidate EV-W34-NEW/REG
  and require retest/re-audit per the evidence contract.

## Findings and resume state

No owned blocking defect remains. All 7 owned requirements are implemented
(PROV-001 on its active branch with empty-root inactivity evidence) or
valid, required evidence is current and truthful, the diff is reviewed, and
this canonical report is current. Resume point for the controller: run
fresh independent audit (`W34_AUDIT_REPORT.md`, controller-owned) against
the candidate above, then close W34 independently on audit PASS. No
downstream Wave is started by this worker; scheduling remains
controller-owned.
