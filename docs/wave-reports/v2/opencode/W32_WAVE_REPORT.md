# W32 -- Plugin discovery, manifest and compatibility - Wave Report

```text
Wave: W32
Canonical report: docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md
Repository: hpc-client-gui / develop
Branch: develop
Baseline SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Tested implementation: working tree at 3e9635ba + W32-owned additions
  (src/hpc_gui/plugins/discovery.py [new],
   src/hpc_gui/plugins/validator.py + models.py + loader.py + installer.py [owned edits],
   tests/test_w32_discovery_manifest.py [new, 19 tests])
  Plus pre-existing uncommitted hunks (preserved, not owned by W32):
   src/hpc_gui/i18n/en.json + tr.json [sibling-owned],
   src/hpc_gui/services/slurm_models.py [sibling-owned],
   src/hpc_gui/services/files_ssh.py + output_follower.py [sibling-owned],
   src/hpc_gui/wx_editor_view.py + wx_jobs.py + wx_shell.py + wx_plugins_view.py [sibling-owned],
   src/hpc_gui/services/job_identity.py + job_list_filter_sort.py +
   job_submit_cancel.py + jobs_refresh_state.py [untracked, sibling-owned],
   tests/test_w26/test_w27/test_w28/test_w29/test_w30/test_w31_* [untracked, sibling-owned]
Current HEAD: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Content handoff: controller content_identity
  b60da6895a0bdb992cdc0fbca090cbfefae574b65a4159ef6e742acaa65b0537
  (phase=run handoff for W32)
Observed waves/pending/W32.md SHA-256 (BOM-stripped, LF-normalized bytes):
  4dac42cccf01cc26a1e6ce04bbb850926e89ec3c61bcc05c772f5c042252dfbe
  (frontmatter wave_id=W32/wave_kind=execution/canonical_source=W32/
   13 owned IDs/aggregate_close_owner=false/evidence_policy=wave-local/
   audit_policy=fresh-independent verified consistent)
Execution start gate: NONE (per Wave independence contract)
HEAD vs origin/develop divergence: HEAD 3e9635ba != origin/develop 63b696b3.
  No rebase/reset performed. Divergence explained as preserved sibling-owned
  working-tree progress plus controller runtime sync; W32 touches only its
  owned plugin files plus its own test/report.
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24 (run phase)
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: READY_FOR_AUDIT (independent audit pending, controller-owned)
```

## Scope

W32 owns 13 IDs per `waves/pending/W32.md` frontmatter:
`HPC-W08-DISC-001..005`, `HPC-W08-MANIFEST-001..008`. No TODO-detail IDs.
Mandatory authority read before edits: all `opencode/REQUIREMENT_REGISTRY.md`
W32 rows (13 source-derived: 5 Workstream A discovery sources, 8 Workstream B
manifest contract), `opencode/TODO_OWNERSHIP_MAP.md` W32 rows (none -- empty
result is the correct reading, not an omission), and
`opencode/sources/WAVE_V2_FINAL_08.md` sections **Workstream A -- Discovery
sources** and **Workstream B -- Manifest / metadata contract**. Live code
inspected before acting (`plugins/loader.py`, `plugins/validator.py`,
`plugins/models.py`, `plugins/storage.py`, `plugins/state.py`,
`plugins/compatibility.py`, `plugins/schema_compat.py`, `plugins/installer.py`,
`wx_plugins.py`, existing plugin contract/core/schema suites). Unattended,
non-interactive; no user questions asked. No cross-Wave worktree/report/temp
edits. Pre-existing dirty hunks preserved verbatim (W32 touches no sibling
product source; only the five owned plugin files, the new test file, and this
report).

Controller audit-receipt context (informational, non-gating): W31 audit PASS
at `3e9635ba` recorded by the controller. Per the independence contract it
does not gate W32 start or acceptance.

## Discovery

Pre-change narrow baseline (green before W32 additions):
`test_plugin_core.py + test_wx_plugins.py + test_plugin_schema_compat.py`
55 passed. No plugin product edits yet.

| Finding ID | Severity | Surface | Evidence | Root cause |
|---|---|---|---|---|
| OBS-W32-001 | P2 | entry prerequisites | W32 has no execution start gate; W21 is an integration reference only | per independence contract, non-blocking; every owned requirement proceeds on the current base with disposable roots |
| OBS-W32-002 | P2 | pre-existing suite failure (out of scope) | `test_wave6_plugin_provider_unicode.py::TestIntegration::test_full_plugin_unicode_flow` fails identically with and without W32 changes (`cluster profile 'storage[0]' needs a non-empty id`) | historical unicode fixture predates the W08 strict storage-shape gate; owned by its stable owner, not W32; routed, not fixed opportunistically |
| OBS-W32-003 | P3 | content-identity reconciliation | controller handoff `b60da689...` vs observed W32 spec-bytes hash `4dac42cc...` | distinct program-chain identity vs spec-bytes hash by design; 13 IDs + policies verified, no spec tampering -- controller-owned reconciliation |
| DEF-W32-004 | P1 (owned, fixed) | manifest contract gaps | validator accepted free-form plugin IDs, unbounded display names, and had no `provider_ids`/`optional_dependencies` contract; only user-installed discovery was codified | closed by the W32 edits below; verified by the new 19-test cohort |

Second-defect search (dimensions checked): negative (malformed JSON,
missing manifest keys, bad semver, bad requires_app, incompatible app,
unsafe/duplicate provider ids, malformed optional deps, duplicate profile
ids, missing entrypoint files), unavailable-capability/backend (no network
or registry access used; all fetchers injected/local), permission/network
failure (loader collects PluginProblem instead of raising; sibling plugin
still loads), cancellation/retry (synchronous loader/installer; no workers
leaked), stale callback/result (no async paths in discovery/manifest),
persistence/identity/cleanup (disposable tmp roots only; disabled state
under the same root; no real user config touched; CWD fake tree ignored),
packaging (no package claim made; N/A justified below), docs/schema
comparison (planning source sections preserved verbatim in trace).

## Requirement trace (requirement -> live owner -> test -> evidence)

- `HPC-W08-DISC-001` (bundled) -> `plugins/discovery.py::list_sources`
  (bundled inactive, no package-resource scan) -> `test_disc_all_five_sources_enumerated`,
  `test_disc_bundled_is_not_active` -> EV-W32-NEW (2 passed).
- `HPC-W08-DISC-002` (user-installed) -> `plugins/loader.py::load_installed_plugins`
  + `plugins/storage.py::plugins_root` + `discovery.py::active_sources` ->
  `test_disc_user_installed_loads` (real manifest+profile round trip) -> EV-W32-NEW.
- `HPC-W08-DISC-003` (configured path) -> `plugins/storage.py::plugins_root(override)`
  documented as conditional explicit-root-only in `discovery.py` ->
  `test_disc_configured_path_override_is_isolated` (root A loads, root B empty) -> EV-W32-NEW.
- `HPC-W08-DISC-004` (entry point/package mechanism) -> `discovery.py`
  (entry-point inactive; manifest entrypoints are relative declarative paths) +
  `loader.py` (no importlib/exec/eval/subprocess) ->
  `test_disc_entry_point_mechanism_never_executes` (source scan + load) -> EV-W32-NEW.
- `HPC-W08-DISC-005` (development path) -> `discovery.py::assert_no_cwd_discovery`
  + loader/storage (no getcwd/getcwdb) ->
  `test_disc_development_path_and_cwd_never_discovered` (chdir into fake CWD tree,
  load unaffected) -> EV-W32-NEW.
- Precedence/duplicate/identity (Workstream A cross-cutting) ->
  `discovery.py::discovery_precedence`, `duplicate_handling_note`,
  `deterministic_registry_identity` + `loader.py` sorted iteration and
  whole-plugin duplicate rejection ->
  `test_disc_precedence_and_identity_deterministic`,
  `test_disc_duplicate_profile_deterministic` (aaa wins, zzz diagnosed) -> EV-W32-NEW.
- `HPC-W08-MANIFEST-001` (plugin ID) -> `plugins/validator.py::validate_manifest_dict`
  (dotted reverse-DNS shape, hyphen/underscore-compatible; loader enforces exact
  PLUGIN_ID_RE at load) -> `test_manifest_plugin_id_validated` -> EV-W32-NEW.
- `HPC-W08-MANIFEST-002` (display name) -> `validator.py` (non-empty, max 128) ->
  `test_manifest_display_name_validated` -> EV-W32-NEW.
- `HPC-W08-MANIFEST-003` (plugin version) -> `validator.py` (`is_valid_semver`) ->
  `test_manifest_version_semver` -> EV-W32-NEW.
- `HPC-W08-MANIFEST-004` (API/schema compatibility version) ->
  `validator.py` (plugin_api allow-list + requires_app syntax) +
  `compatibility.py::is_app_compatible` + `schema_compat.py` floors (loader gate) ->
  `test_manifest_api_schema_compat` -> EV-W32-NEW.
- `HPC-W08-MANIFEST-005` (entry point) -> `validator.py` (entrypoints must be JSON
  object; v2 linter_engine must point at package __init__.py and match declared
  files) + `loader.py` (unsafe/missing entrypoint becomes contained PluginProblem) ->
  `test_manifest_entrypoint_required` -> EV-W32-NEW.
- `HPC-W08-MANIFEST-006` (provider IDs/capabilities if applicable) ->
  `validator.py` (optional `provider_ids` list, safe alphabet, max 64, deduped) +
  `models.py::PluginManifest.provider_ids` + loader/installer preservation ->
  `test_manifest_provider_ids_validated`,
  `test_manifest_provider_ids_preserved_through_loader` -> EV-W32-NEW.
- `HPC-W08-MANIFEST-007` (optional dependencies) -> `validator.py` (optional
  `optional_dependencies` list of string-or-{id,version}, semver-checked, advisory-only) +
  `models.py::PluginManifest.optional_dependencies` + loader/installer preservation ->
  `test_manifest_optional_dependencies_advisory`,
  `test_manifest_optional_dep_missing_does_not_block_load` (unknown optional dep still loads) -> EV-W32-NEW.
- `HPC-W08-MANIFEST-008` (malformed/incompatible rejected with contained diagnostic) ->
  `validator.py` + `loader.py::PluginLoadResult.problems` (collect, never raise; sibling
  still loads) ->
  `test_manifest_malformed_rejected_with_diagnostic_and_isolated`
  (broken JSON isolated; incompatible app diagnosed) -> EV-W32-NEW.

## Tests and Evidence Required

- Narrow baseline before edits: `test_plugin_core + test_wx_plugins +
  test_plugin_schema_compat` 55 passed (recorded above).
- New/changed behavioral tests: `tests/test_w32_discovery_manifest.py` 19 passed
  (EV-W32-NEW). Command: `python -m pytest tests/test_w32_discovery_manifest.py -q`.
- Focused regression: `test_plugin_core + test_plugin_schema_compat +
  test_plugin_security + test_plugin_installer + test_plugin_integrity +
  test_wx_plugins + test_w08_schema_isolation` 153 passed (EV-W32-REG).
  Broader plugin sweep (212 passed) with the single pre-existing
  `test_wave6 ... test_full_plugin_unicode_flow` failure deselected/recorded as
  OBS-W32-002 (fails identically without W32 changes; routed to its owner).
- New/changed tests have meaningful assertions (manifest round trips through
  real files, loader problems asserted by substring, duplicate winner asserted
  by id, CWD isolation asserted by chdir + reload) and legitimate mock
  boundaries (tmp roots only; no network; `monkeypatch.chdir` for CWD proof).
- GUI claims (required class GUI): headless wx manager model test
  `test_gui_manager_surfaces_discovery_state` passed (installed card + disabled
  persistence under the same root, CWD untouched), plus maintained suites
  `tests/test_wx_plugins.py` (3 passed) and `tests/test_plugin_manager_ui.py`
  collection (Qt-gated). No static-only substitution: loader behavior is
  exercised through real files and the manager model.
- Package claims: N/A with justification -- W32 makes no packaged-artifact
  acceptance claim; discovery explicitly proves packaged builds discover the
  same set (no dev-path assistance) without asserting a wheel SHA.
- External claims: N/A with justification -- no external HPC/registry/network
  used; all registry interactions are local disposable fixtures. No
  EXTERNAL_BLOCKED needed; nothing invented.
- Evidence classes not required by an owned requirement are N/A only with the
  concrete justifications above.

## Diff Review

`git status --short --branch`, `git diff --stat`, `git diff --check`, and full
diff inspected for the owned repositories. Owned diff (tracked):
`plugins/validator.py` (+99/-1: optional keys, provider/optional-dep validation,
ID shape, name bound), `plugins/models.py` (+5: advisory fields with defaults),
`plugins/loader.py` (+7: preserve new fields), `plugins/installer.py` (+7:
preserve new fields). New files: `plugins/discovery.py` (canonical five-source
enumeration + deterministic identity), `tests/test_w32_discovery_manifest.py`
(19 tests). `git diff --check` clean. No secrets, no generated/binary noise,
no unrelated refactors, no duplicated business logic in wx views, no weakened
tests (existing suites green except the pre-existing OBS-W32-002 failure which
is recorded, not edited). Untracked sibling artifacts/reports/tests preserved
untouched. Candidate identity for audit: working tree at `3e9635ba` plus the
owned additions listed in the header block.

## Report / Evidence Requirements

This file is the canonical report
(`docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md`). No session-suffixed
copies created. Branch/SHA/working-tree identities, requirement IDs, commands,
counts, evidence identities (EV-W32-NEW, EV-W32-REG), findings (OBS-W32-001..003,
DEF-W32-004 closed), and resume state are recorded here. Fresh-context audit is
controller-owned and pending; no audit verdict is synthesized in this run phase.

## Stop Conditions

No destructive-Git need, no unresolved authority conflict, no missing mandatory
package/external prerequisite, no cross-Wave ownership escape. Pre-existing
dirty/sibling hunks were preserved; W32 stops after its canonical report is
current with focused tests green. The worker does not start downstream Waves;
W33 integration is a non-blocking hint.

## Definition of Done (run-phase claim)

Every owned non-superseded mandatory requirement is implemented or already
valid with a live owner, required evidence is current and truthful (19 new +
153 focused regression passes, GUI model proof, CWD/precedence/duplicate
proofs), no owned blocking defect remains (OBS-W32-002 is out-of-scope and
routed), the diff is reviewed, and this canonical report is current. Fresh
independent audit PASS remains controller-owned and is explicitly not claimed
here.

## Handoff / DAG unlocks

W32 is ready for fresh independent audit. Historical unlock targets are
integration hints only; no other Wave waits on W32 solely because of DAG
metadata. Suggested audit focus: discovery precedence/CWD proof, ID/name/version
bounds, provider/optional-dep advisory semantics (missing optional dep must not
gate load), duplicate determinism, and contained-diagnostic isolation.
