# W07 Wave Report — Provider contract rediscovery and capability model

Wave: `W07`
Canonical report path: `docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA: `0f8902a023bac76071527232c2287af96478ed2b`
Current HEAD: `0f8902a023bac76071527232c2287af96478ed2b`
Tested implementation state: `HEAD 0f8902a0` + pre-existing working-tree entries only (no commit made by this session; every cited suite ran after the final tree state; this session made zero product/test edits)
Plugin/external repo SHA(s): `D:\Projeler\hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin; no plugin change; working tree clean except untracked `.github/social-preview.jpg`)
First started: 2026-09-19 (UTC)
Last updated: 2026-09-19 (UTC)
Session status: COMPLETE
Wave decision: PASS (zero-defect; valid per `HPC-GOV-017`)
Executable authority: `waves/pending/W07.md` (exactly one copy; `waves/pending/` holds W01–W61, 61 files, no gaps/duplicates; `waves/bak/` never read for execution)
Execution model: `opencode-go/muse-spark-1.3-contributor`
Runtime truth: Python `3.12.4`, wx `4.3.1 msw (phoenix) wxWidgets 3.3.3`, `src/hpc_gui/runtime.py` `DEFAULT_GUI_RUNTIME="qt"`
Dependency: `W06` — `docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md` decision `PASS`, audit `PASS`; entry revalidated (pins equal: main `0f8902a0` == `origin/develop` tip via read-only `ls-remote`; plugin `f0abb7e7`; no owned W06 blocker touches this scope)

## Owned requirements and TODO details

| ID | Kind | Status |
|---|---|---|
| `HPC-W02-CAP-001` | MANDATORY REQUIREMENT (Workstream B — smallest truthful capability vocabulary) | VERIFIED — frozen vocabulary below (§Capability freeze); 7 provider-presentation capabilities + 5 plugin-manifest capabilities + 10 environment-report keys + 3 v4 adapter/parser contracts |
| `HPC-W02-CAP-002` | MANDATORY REQUIREMENT (per-capability declaration) | VERIFIED — declaration column per capability (§Capability freeze); `DECLARED`/`NOT_DECLARED` via `build_provider_capability_view` |
| `HPC-W02-CAP-003` | MANDATORY REQUIREMENT (probe/availability rule) | VERIFIED — probe column per capability; `observed_from_self_test`, `CapabilityReport.from_probes` tri-state, `quota_gate` 6-state gate |
| `HPC-W02-CAP-004` | MANDATORY REQUIREMENT (required fields) | VERIFIED — fields column per capability; manifest/profile required-key sets enforced by `validate_manifest_dict` / `validate_cluster_profile_dict` |
| `HPC-W02-CAP-005` | MANDATORY REQUIREMENT (error type/contract) | VERIFIED — error column per capability; `PluginProblem` collection, `ParseResult.fail("unsupported", …)`, `QuotaResult("error"/"stale"/"unsupported")`, validator problem strings |
| `HPC-W02-CAP-006` | MANDATORY REQUIREMENT (fallback) | VERIFIED — fallback column per capability; loader skips bad plugin and keeps host running; duplicate rejection is deterministic; quota absence yields `not_configured`/`disabled`, never a fabricated value |
| `HPC-W02-CAP-007` | MANDATORY REQUIREMENT (UI implication) | VERIFIED — UI column per capability; wx connection dialog disables quota controls when undeclared (`_load_quota_widgets`); jobs cluster-status panel hides with honest `cluster_unsupported`/`no_cluster_connection` labels; probe `EV-W07-GUI-001` proves real-wx rendering |
| `HPC-W02-DISCOVERY-001` | MANDATORY REQUIREMENT (search both repos before changing the contract) | VERIFIED — mandated `git grep` executed in both repos (§Discovery pass); zero contract changes made, so no change was unsearched |
| `HPC-W02-DISCOVERY-002` | MANDATORY REQUIREMENT (provider protocol/base type inventory) | VERIFIED — inventory §1: `ClusterProfileDefinition` + `PluginManifest`/`InstalledPlugin` + `ProviderContract` + `ProviderCapabilityView` |
| `HPC-W02-DISCOVERY-003` | MANDATORY REQUIREMENT (registry/discovery path inventory) | VERIFIED — inventory §2: `registry.json` → `registry_client` → `installer` (SHA-256 exact-file protocol) → `storage`/`state` → `loader.load_installed_plugins` → `templates.installed_cluster_template_groups` |
| `HPC-W02-DISCOVERY-004` | MANDATORY REQUIREMENT (plugin metadata-format inventory) | VERIFIED — inventory §3: manifest schema v1 + cluster-profile schemas 1–4 + registry schema v1 + 7 JSON schemas under `schema/` |
| `HPC-W02-DISCOVERY-005` | MANDATORY REQUIREMENT (provider configuration-schema inventory) | VERIFIED — inventory §4: profile sections, trusted Slurm command allow-list, placeholder allow-list, storage/quota section shapes, v4 adapter/parser allow-lists |
| `HPC-W02-DISCOVERY-006` | MANDATORY REQUIREMENT (capability representation inventory) | VERIFIED — inventory §5: 4 representation layers frozen (§Capability freeze) |
| `HPC-W02-DISCOVERY-007` | MANDATORY REQUIREMENT (adapters/services consuming the contracts) | VERIFIED — inventory §6: consumer table (jobs, shell, self-test, diagnostics, connection dialogs, quota monitor, capability report) |
| `HPC-W02-DISCOVERY-008` | MANDATORY REQUIREMENT (tests asserting main/plugin/provider compatibility) | VERIFIED — inventory §7 + `EV-W07-COMPAT-001`: `test_plugin_contract.py` green against the live plugin checkout (20/20) |
| `HPC-W02-DISCOVERY-009` | MANDATORY REQUIREMENT (document coexisting provider systems' boundary; no forced merge) | VERIFIED — boundary table: declarative plugin profiles vs legacy local `provider_template` snapshots vs v4 adapter/parser contracts; single canonical serializer (`to_provider_template`) unifies them without a merge |

Owned TODO-detail IDs: none (0 rows).

## Mandatory source sections read

- `opencode/sources/WAVE_V2_FINAL_02.md` → Workstream A — Rediscover current contracts (§70–88): mandated `rg` pattern, 7 inventories (protocol, registry path, metadata format, config schema, capability representation, consuming adapters/services, compat tests), multi-system boundary rule.
- `opencode/sources/WAVE_V2_FINAL_02.md` → Workstream B — Capability taxonomy (§90–116): smallest truthful vocabulary, per-capability declaration/probe/fields/error/fallback/UI.
- Owned rows: `opencode/REQUIREMENT_REGISTRY.md:1196–1202` (CAP-001…007), `:1208–1216` (DISCOVERY-001…009); index rows `opencode/REQUIREMENT_WAVE_INDEX.md:158–164,1170–1178`.
- Reference implementation (live code, not authority): `src/hpc_gui/services/provider_capabilities.py`, `src/hpc_gui/services/provider_contract.py`, `src/hpc_gui/services/quota_monitor.py`, `src/hpc_gui/plugins/{models,loader,validator}.py`, `src/hpc_gui/services/capability_report.py`.
- Prior-wave background only (different numbering, not authority): `docs/wave-reports/v2/WAVE_V2_FINAL_02_REPORT.md` (old planning-wave-02 provider report) and `docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md` (execution W02 error-governance). Neither substitutes for the pending Wave or owned rows.
- Workstreams C–G were read for boundary awareness only and were NOT absorbed: schema/absense semantics → W08; cross-repo repair/compat fixtures → W09; expansion disposition → W10.

## Discovery pass (before first edit)

- Pinned `develop 0f8902a0` == `origin/develop` tip (read-only `git ls-remote origin develop` → `0f8902a023bac76071527232c2287af96478ed2b`); plugin `develop f0abb7e7`; working tree held only pre-existing unrelated changes — all preserved, none reverted, none touched.
- Mandated search executed as `git grep -n -i -E 'provider|capability|plugin|registry|discover|storage|quota|slurm|ssh|sftp' -- src tests` (main) and `git -C <plugins> grep … -- .` (plugin). Full output spooled to Temp (`w07_rg.txt`); representative hits triaged into the 7 inventories below. Binary-asset noise (`xterm.js`) excluded by scoping follow-up greps to `*.py` service/plugin/config layers.
- Narrow pre-edit baseline `EV-W07-BASE-001`: `pytest tests/test_wave_v2_02_provider_contract.py tests/test_provider_capabilities.py tests/test_capability_report.py tests/test_quota_monitor.py` → **20 passed** (exit 0).

### 1. Provider protocol / base types (`HPC-W02-DISCOVERY-002`)

| Type | Owner file | Role |
|---|---|---|
| `ClusterProfileDefinition` | `src/hpc_gui/plugins/models.py:82–166` | Declarative provider: identity (`profile_id/name/scheduler`), `paths/commands`, `storage`, `quota_sources`, v4 `job_details/accounting/cluster_status`; `to_provider_template()` is the single canonical serializer; `visible_storage_areas()` filters enabled rows |
| `PluginManifest` / `PluginFile` / `InstalledPlugin` | `src/hpc_gui/plugins/models.py:57–79,230–239` | Plugin envelope: semver id, `plugin_api`, `capabilities`, `entrypoints`, per-file SHA-256/size/role |
| `ProviderContract` | `src/hpc_gui/services/provider_contract.py:26–48` | Resolved adapter/parser triple; `has_*` flags; `extract_contract` is total (malformed → empty contract, never raises) |
| `ProviderCapability` / `ProviderCapabilityView` | `src/hpc_gui/services/provider_capabilities.py:16–30` | Declared-vs-observed presentation rows; `as_dict()` JSON-serializable |
| `QuotaResult` / `QuotaBackend` / `QuotaBackendRegistry` | `src/hpc_gui/services/quota_monitor.py:15–48` | Optional-quota value type + allow-listed backend adapters (production registry holds only reviewed backends) |
| `CapabilityReport` | `src/hpc_gui/services/capability_report.py:33–73` | Environment tri-state report (`available/unavailable/unknown`) over `CAPABILITY_KEYS` |

### 2. Registry / discovery path (`HPC-W02-DISCOVERY-003`)

`registry.json` (schema v1, `plugin_api` 1, 15 entries — §Live plugin-repo facts) → `plugins/registry_client.py` (`parse_registry`, `find_registry_entry`, official raw-base fetch) → `plugins/installer.py` (exact-file protocol: manifest download + SHA-256 verify + identity/API/compat/capability checks) → `plugins/storage.py` + `plugins/state.py` (packages layout, active versions, disabled ids, trusted manifest hashes) → `plugins/loader.py::load_installed_plugins` (collects `PluginProblem`s, never raises; sorted-id deterministic duplicate handling; TOFU integrity migration) → `plugins/templates.py::installed_cluster_template_groups` (dialog-facing template groups) → `config/system_profile.py` (`PluginSystemTemplate.structured` == `to_provider_template()` canonical shape; `resolve_provider_path` allow-listed placeholders `{user,user_first,project,account}`).

### 3. Plugin metadata format (`HPC-W02-DISCOVERY-004`)

Manifest `schema_version: 1`, required keys `MANIFEST_REQUIRED_KEYS` (12), optional `ui_contributions`; `plugin_api ∈ {1,2}` (`2` only with approved trusted-tool identity); capabilities from `KNOWN_CAPABILITIES` (5); entrypoints `cluster_profiles/lint_index/job_templates/linter_engine`; files carry lowercase-hex SHA-256 + size + `KNOWN_FILE_ROLES`; executable suffixes forbidden except approved `linter-engine` `.py`. Cluster profiles `schema_version ∈ {1,2,3,4}` (`SUPPORTED_CLUSTER_PROFILE_SCHEMAS`); v2 adds metadata/paths/commands/site/hints/software/storage/quota_sources; v3 adds job_outputs/file_filters; v4 adds job_details/accounting/cluster_status. Registry entries carry 11 required keys incl. `manifest_sha256`. Plugin repo ships 7 JSON schemas under `schema/` (manifest, registry, cluster-profile, lint-index, lint-rule, template-index, template).

### 4. Provider configuration schema (`HPC-W02-DISCOVERY-005`)

- Identity: `profile_id ^[a-z][a-z0-9_-]*$` (≤64), `name` (≤80), `scheduler ∈ {slurm}`.
- Commands: ONLY application-owned Slurm operations (`_TRUSTED_SLURM_COMMANDS` + one published TRUBA `sacct` variant); unknown keys rejected; placeholders restricted to `{user,job_id,job_id_q,script_dir,script_dir_q,script_name,script_name_q}`.
- Storage areas: `id/label` required, `kind ∈ {home,scratch,project,custom,node-local}`, `access_context ∈ {login-node,shared,compute-node,unknown}`, path forbids `;\|&`$()<>\r\n`, placeholders `{user,user_first,project,account}` only, `retention_days ≥ 0`, doc URL must be `https://`.
- Quota sources: list of `{id,enabled,backend_id,command_template,scope,…}`; scope `∈ {user,group,project,unknown}`; backend must be registry-allow-listed; multiline templates rejected.
- v4 contracts: `adapter ∈ {slurm.scontrol.job, slurm.sacct.job, truba.lssrv}`, `parser ∈ {slurm.scontrol.v1, slurm.sacct.pipe.v1, truba.lssrv.v1, generic.delimited_table.v1}`; executable fields (`source/import_path/eval/exec/callback/shell`) rejected.

### 5. Capability representation (`HPC-W02-DISCOVERY-006`)

Four layers, frozen in §Capability freeze (no merge; each layer keeps its job): (a) plugin-manifest capabilities (5, install-time), (b) provider-presentation capabilities (7, declared-vs-observed), (c) environment capability report keys (10, probe tri-state), (d) v4 adapter/parser contracts (3 sections, allow-listed IDs).

### 6. Consuming adapters / services (`HPC-W02-DISCOVERY-007`)

| Consumer | Contract used | Truthfulness behavior |
|---|---|---|
| `wx_jobs.py` (cluster status, job details, accounting) | `extract_contract` + `parse_with_contract` + `has_status_capability` gate | Panel hides with `cluster_unsupported`/`no_cluster_connection`; parse failures label `parse_error_cluster`; empty output labels `no_cluster_status` |
| `wx_shell.py` (status/accounting actions) | `extract_contract(_resolve_provider_config())` | Unknown adapter → warning + `None`, no crash |
| `wx_connection_dialog.py` + Qt `connection_dialog.py` (storage/quota editors) | `storage`, `quota_sources`, `quota_state_for_profile`/`quota_gate` | Quota controls disabled when source undeclared; backend choices from production registry + `(unsupported)` marker |
| `services/cluster_self_test.py` | `quota_sources`, storage/scheduler probes | Quota explicitly `NOT_TESTED` ("quota probe is not run by self-test"); missing source → `NOT_CONFIGURED` |
| `services/provider_capabilities.py::observed_from_self_test` | self-test sections | Maps `ssh→auth`, `squeue→scheduler`, `storage/quota` into the 7-vocabulary |
| `services/quota_monitor.py::QuotaMonitor` | `quota_gate` + backend registry | No remote work unless `eligible`; stale-generation guard returns `QuotaResult("stale")`; `invalidate`/`close` lifecycle |
| `services/capability_report.py` | probe booleans | `None → unknown`, never hidden; extra keys ignored |
| `core/diagnostics.py` | `build_provider_capability_view` | Diagnostics embed declared-vs-observed view |

### 7. Compatibility tests (`HPC-W02-DISCOVERY-008`)

`tests/test_plugin_contract.py` (cross-repo, env-gated on `HPC_GUI_CONTRACT_REPO`; 20/20 green against live checkout — `EV-W07-COMPAT-001`), `tests/test_plugin_core.py`, `tests/test_plugin_schema_compat.py`, `tests/test_plugin_installer.py`, `tests/test_plugin_security.py`, `tests/test_plugin_e2e.py`, `tests/test_wave_v2_02_provider_contract.py` (canonical-serializer + duplicate-identity regressions), `tests/test_wave79_provider_contract.py`, `tests/test_w03_settings_provider_inventory.py` (17 inventory tests incl. capability/contract semantics), quota/capability/report unit suites.

### Boundary: coexisting provider systems (`HPC-W02-DISCOVERY-009`)

| System | Shape | Boundary rule |
|---|---|---|
| Declarative plugin profiles (schemas 1–4) | `ClusterProfileDefinition` in plugin packages | Sole authoring source; validated at load; duplicates deterministically rejected |
| Installed template groups (dialog-facing) | `installed_cluster_template_groups` | Read-only projection of loaded plugins; never hand-edited |
| Saved-connection snapshots | `provider_template` dict inside connection profiles | Copy frozen at apply-time via the ONE canonical serializer; keeps working offline / after plugin removal |
| Legacy local templates | `provider_template: {}` default in `config/models.py` | Treated as "no provider"; capability view reports all `NOT_DECLARED`/`NOT_CONFIGURED` |
| v4 adapter/parser contracts | `job_details/accounting/cluster_status` sections | Optional overlays resolved through allow-listed registries; absent → `ParseResult.fail("unsupported", …)` |

No premature merge performed: `to_provider_template()` guarantees every producer emits the identical dict (regression `test_system_settings_and_structured_template_are_identical`), so distinct lifecycle stages agree without collapsing into one store.

### Live plugin-repo facts (both-repo pin `f0abb7e7`)

- `registry.json`: `schema_version 1`, `plugin_api 1`, **15 entries** (truba 1.0.0–1.5.6 versions + leonardo/lumi/perlmutter/setonix/stampede3/fluent ×3/ansyslint), 8 plugin dirs.
- Shipped TRUBA `1.5.0` (`requires_app >=1.5.9`, `plugin_api 1`, capabilities `["cluster-profile"]`): `schema_version 4`; 5 storage rows (2 with real paths: `/arf/home/{user}`, `/arf/scratch/{user}`); 1 quota source (`truba-quota`, `enabled:false`, empty `backend_id`/`command_template`, note states no verified quota command — lssrv is status, not quota); contracts `slurm.scontrol.job/slurm.scontrol.v1`, `slurm.sacct.job/slurm.sacct.pipe.v1`, `truba.lssrv/truba.lssrv.v1`.
- Repo ships 7 JSON schemas; `scripts/validate_registry.py` + `validate.yml` CI gate (registry gate + application contract gate via `tests/test_plugin_contract.py`).

## Capability freeze (HPC-W02-CAP-001…007 deliverable)

Smallest truthful vocabulary: callers may rely on a capability ONLY under its documented prerequisites. Three representation layers are frozen (each keeps its existing job; nothing added, nothing merged):

**Layer A — plugin-manifest capabilities** (`models.KNOWN_CAPABILITIES`, install-time, 5): `cluster-profile`, `lint-rules`, `job-template`, `application-tools`, `linter-tool` (API 2 only + approved trusted-tool identity).

**Layer B — provider-presentation capabilities** (`provider_capabilities._CAPABILITIES`, declared-vs-observed, 7):

| Capability | Declaration | Probe / availability | Required fields | Error contract | Fallback | UI implication |
|---|---|---|---|---|---|---|
| `auth` | `access.auth_methods` non-empty → `DECLARED` | self-test `ssh` section → observed (`observed_from_self_test`) | `access` mapping | undeclared → `NOT_DECLARED`/`NOT_TESTED`, never assumed | connection dialog still collects credentials generically | provider status card shows declared/observed pair |
| `scheduler` | `scheduler` string or `commands` mapping → `DECLARED` | self-test `squeue` item → observed | `scheduler` (+ trusted `commands`) | minimal profile keeps `DECLARED` (required field — contract, proven by `NEG-W02-001`) | jobs actions gate on connection + `has_status_capability` | unsupported → `cluster_unsupported`, panel hidden, refresh disabled |
| `storage` | `storage` list non-empty → `DECLARED` | `visible_storage_areas()` (enabled + path or resolver) | storage-area schema (§4) | malformed rows skipped by validator; empty list → `NOT_DECLARED` | path cards show only visible rows (TRUBA: 2 of 5) | storage list shows `label: path` or `storage_areas_empty` |
| `quota` | `quota_sources` non-empty → `DECLARED` | `quota_gate` 6-state: `eligible/ready_not_enabled/not_configured/disabled/incomplete_unsupported/invalid_configuration` | quota-source schema (§4) | invalid → `invalid_configuration`; failing probe stays `FAILED` observed, never `0`/success | **no fabricated value, no retry loop** (TRUBA 1.5.0: declared-but-unconfigured → `not_configured`) | quota controls disabled when undeclared; status line states the gate state |
| `project` / `account` | key present in `requirements` → `DECLARED` | missing value + declared → observed `NOT_CONFIGURED` | `requirements` mapping | — | prompts collect them generically | requirement fields shown per declaration |
| `optional` | `optional_capabilities` non-empty → `DECLARED` | per-capability probes | provider-defined | unknown optional → unavailable result, not success | generic callers receive supported "unavailable/unsupported" | hidden unless declared |

**Layer C — environment capability report** (`capability_report.CAPABILITY_KEYS`, probe tri-state, 10): `ssh_connected`, `sftp_available`, `slurm_squeue_available`, `slurm_sbatch_available`, `slurm_scancel_available`, `slurm_sacct_available`, `slurm_scontrol_available`, `home_path_known`, `scratch_path_known`, `x11_possible`; `True→available / False→unavailable / None→unknown`; unknown/unavailable are reported (`unknown()`, `unavailable()`, `summary()`), never hidden; extra keys ignored.

**Layer D — v4 adapter/parser contracts** (3 sections): `job_details`, `accounting`, `cluster_status`; declaration = section present with allow-listed `adapter`+`parser`; probe = registry lookup (`get_adapter`/`parse`); error = `ParseResult.fail("unsupported", …)` / unknown-adapter warning + `None`; fallback = honest unavailable labels in jobs UI; UI implication = capability-gated panels (§6).

Generic-layer provider-name branching: **none for capability decisions**. `git grep -i -E '"truba" *\)|== *"truba"|TRUBA.*if |if .*TRUBA' -- src/hpc_gui/wx_*.py src/hpc_gui/services/*.py` → only 2 hits, both help-topic routing (`help_catalog.py:93`, `wx_help.py:44`), not capability logic. All `truba.lssrv*` references are allow-listed adapter/parser **IDs** consumed declaratively (`validator.py`, `adapter_registry.py`, `parsers.py`, `provider_contract.py` docstring) plus one capability-gated fallback parse (`wx_jobs.py:359–362`, reached only after the `has_status_capability` gate at `:1678–1684`; empty/invalid output still yields honest `no_cluster_status`/`parse_error_cluster`). Observed, no change required; consumption hardening stays with W09.

## WAVE_FINDINGS

| Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status |
|---|---|---|---|---|---|---|---|---|
| — | — | full discovery + freeze scope re-audited | suites + probe below; pre-fix history already closed by `test_wave_v2_02_provider_contract.py` (DEF-W02-001/002 at baseline `731357c6`) | no live in-scope defect found | none | none required | N/A | ZERO-DEFECT PASS |

Second-defect search (12 dimensions): 1. negative paths — CHECKED (`PluginProblem` collection, duplicate/incompatible/malformed isolation tests, `quota_gate` 6 states, `extract_contract` totality); 2. lifecycle — CHECKED (loader synchronous, no retained callbacks; `QuotaMonitor.invalidate/close` + stale-generation guard); 3. stale state — N/A (freeze wave; `QuotaResult("stale")` already guards the one async path); 4. identity — CHECKED (sorted-id deterministic winner, both install orders parametrized; rejected plugin reserves nothing); 5. concurrency — N/A (no shared mutable contract state); 6. boundary values — CHECKED (declared-but-empty vs undeclared distinguished, `NEG-W02-001`; empty command → `not_configured` before `disabled`); 7. capability absence — CHECKED (probe negatives for minimal template); 8. persistence — N/A (no new persisted state; snapshots reuse tested serializer); 9. packaging — N/A (no artifact bound; no SHA-256 cited); 10. error visibility — CHECKED (validator problem strings name provider+field; loader logs skipped plugins; no silent `pass` in loader/discovery path); 11. context menus/secondary entry — CHECKED (Qt + wx connection dialogs share the same `provider_template` shape; help-topic `TRUBA/GENERIC` routing is docs navigation, not capability logic); 12. adjacent boundary — CHECKED (`wx_jobs` lssrv fallback is capability-gated; consumption repair belongs to W09 — observed, not absorbed).

Cross-wave routing: schema/absense-semantics behaviors → W08; cross-repo repair/compat fixtures/consumption hardening → W09; expansion disposition → W10; real-cluster validation → W03 (EXTERNAL, no live-cluster claim made); packaging → W08/W10. Nothing absorbed.

## Tests and evidence

| Evidence | Exact command | Timestamp (UTC) | Exit | Result |
|---|---|---|---|---|
| `EV-W07-BASE-001` narrow pre-edit baseline | `python -m pytest tests/test_wave_v2_02_provider_contract.py tests/test_provider_capabilities.py tests/test_capability_report.py tests/test_quota_monitor.py -q -p no:cacheprovider` | 2026-09-19 | 0 | 20 passed in 1.89s |
| `EV-W07-REG-001` plugin core/schema suites | `python -m pytest tests/test_plugin_contract.py tests/test_plugin_core.py tests/test_plugin_schema_compat.py -q -p no:cacheprovider` | 2026-09-19 | 0 | 52 passed, 20 skipped (skips are env-gated: `HPC_GUI_CONTRACT_REPO` unset — closed by `EV-W07-COMPAT-001`) |
| `EV-W07-REG-002` contract/context/storage/wx-model suites | `python -m pytest tests/test_wave79_provider_contract.py tests/test_provider_context.py tests/test_provider_overrides.py tests/test_provider_path_resolver.py tests/test_provider_profile_diff.py tests/test_local_provider_storage.py tests/test_wx_plugins.py -q -p no:cacheprovider` | 2026-09-19 | 0 | 69 passed |
| `EV-W07-REG-003` installer/security/e2e/inventory suites | `python -m pytest tests/test_plugin_installer.py tests/test_plugin_security.py tests/test_plugin_e2e.py tests/test_w03_settings_provider_inventory.py -q -p no:cacheprovider` | 2026-09-19 | 0 | 91 passed |
| `EV-W07-COMPAT-001` main↔plugin contract vs live checkout | `$env:HPC_GUI_CONTRACT_REPO='D:\Projeler\hpc-client-gui-plugins'; python -m pytest tests/test_plugin_contract.py -q -p no:cacheprovider` | 2026-09-19 | 0 | 20 passed (the 20 env-gated skips, now executed against plugin `f0abb7e7`) |
| `EV-W07-GUI-001` real-wx capability probe | `python C:\Users\mskomek\AppData\Local\Temp\opencode\w07_wx_probe.py` (wx 4.3.1; real `wx.App`+`Frame`, 7 capability `StaticText` rows, real `wx.EVT_BUTTON` round-trip via `wx.PostEvent`+`Yield`, live TRUBA 1.5.0 file + minimal-template negative path) | 2026-09-19 | 0 | 17/17 PASS (first run 14/16: two probe-side expectations wrong — gate precedence `not_configured` over `disabled` for empty command template; corrected in probe, product untouched, rerun 17/17) |
| `EV-W07-PIN-001` repo pins | `git branch --show-current` → `develop`; `git rev-parse HEAD` → `0f8902a0…`; `git ls-remote origin develop` → same SHA; plugin `git rev-parse HEAD` → `f0abb7e7…` | 2026-09-19T06:52:38Z | 0 | pins equal origin tip; no fetch needed |

Totals: **252 passed** (20+52+69+91+20; the COMPAT-001 20 are the executed form of REG-001's 20 env-gated skips — no double counting of distinct nodes: 232 distinct nodes + 20 contract nodes = 252 test executions, 0 failures) + **17/17 wx probe checks**. No test weakening, no new skips/xfails, no mocks standing in for behavior under test (registry fetcher injection in pre-existing suites is the legitimate network boundary; probe uses the live plugin file + real wx runtime). No fabricated output; raw probe output retained in shell transcript.

Evidence classes: required class for W07 is `GUI` — satisfied by `EV-W07-GUI-001` (real wx event/runtime). Package class: N/A with justification (no artifact bound; no SHA-256 cited; package-dependent rows defer to W08/W10). External class: N/A (real-cluster behavior beyond diagnostic probes belongs to W03; no live-cluster claim; TRUBA quota correctly reports `not_configured` instead of fabricating).

## Diff review

- `git status --short` (2026-09-19T06:52:38Z): this session adds exactly two files (this report + `W07_AUDIT_REPORT.md`). All other entries are pre-existing/concurrent — preserved untouched, none reverted. This session made zero product/test edits.
- `git diff --stat`: no tracked-file change by this session. `git diff --check`: exit 0 (CRLF notices only, pre-existing).
- Plugin repo: no change (read-only; untracked `.github/social-preview.jpg` pre-existing).
- Secret safety: no credentials, `.env`, keys, PEM/PFX, `.ssh`, tokens, or secret directories in diff, probe script, or reports. Probe script lives in Temp, outside the repo.

## Findings and ownership routing

- In-scope P0/P1 opened: 0. New defects introduced: 0. Zero-defect PASS is valid per `HPC-GOV-017`.
- Cross-wave: nothing absorbed. Schema/absence-semantics → W08; cross-repo repair/consumption → W09; expansion → W10; real-cluster → W03; packaging → W08/W10: cited, untouched.

## Resume state

Completed: all 16 MANDATORY IDs (7 CAP + 9 DISCOVERY) traced requirement → live owner → test → evidence; mandated two-repo search + 7 inventories + boundary doc done; capability vocabulary frozen (Layers A–D with per-capability declaration/probe/fields/error/fallback/UI); failure/lifecycle coverage checked across 12 dimensions; GUI + compat + regression evidence current; pins current; diff reviewed; secret-safe; audit report written.
In progress: none. Open P0/P1 (owned): 0. Pending tests/evidence: none for this Wave.
Next: none in this Wave — stop. `W08` may be planned only after its dependency/prerequisite checks are revalidated; this session starts nothing.
