# W64 Wave Report (U01–U04 complete — evidence closeout, PROV-004 parked)

**Wave:** W64 — EU/AU provider pack (U01: HPC-W64-PROV-001, HPC-W64-PROV-002; U02: HPC-W64-PROV-003, HPC-W64-PROV-004; U03: HPC-W64-PROV-005; U04: HPC-W64-PROV-006 closeout).
**Date:** 2026-10-14. **Candidate:** `4268668f4b1af6cac2affd8679e3ffc62fbb6f0d`.
**Plugins repo HEAD:** `f0abb7e7037e66ab451d463c699fecf4e00c89eb`.

## Scope

Verify-only, evidence-only unit. No product source modified. `validator.py`
is >500 LOC; this unit performs READ_ONLY exercise only, no split required.

## Content identity

S02 sha256 re-hash matches for all four S02 files:

- `src/hpc_gui/plugins/providers.py` `b0934eb2…` (actual LOC 212; S02 says 248 — count drift only)
- `src/hpc_gui/plugins/validator.py` `f9a813dd…` (actual LOC 646; S02 says 698 — count drift only)
- `src/hpc_gui/services/lumi_quota.py` `f17091ac…` (actual LOC 18; S02 says 27 — count drift only)
- `src/hpc_gui/services/cineca_quota.py` `136cfbe6…` (actual LOC 42; S02 says 51 — count drift only)

Hashes authoritative; evidence re-bound to current hashes above.

## PROV-001 LUMI — PASS (verify-only)

- Profile `D:/Projeler/hpc-client-gui-plugins/plugins/lumi/1.0.0/cluster-profile.json`
  (`schema_version` 2, `scheduler` slurm, project/work paths parameterized:
  `/users/{user}`, `/scratch/{project}`, `/project/{project}`, `/flash/{project}`).
- `validate_cluster_profile_dict` returns `[]`.
- `parse_lumi_quota` fixture `project 12.5 GiB 100.0 GiB 1500 100000`
  → ok, used 13421772800 B, limit 107374182400 B, files 1500/100000, storage `project`.
- `build_lumi_quota_command` returns `lumi-quota -v`.
- Provenance: LUMI docs URLs + verification date 2026-10-14 in
  `artifacts/refactored-v2/w64/lumi-leonardo-provenance.json`; allocation
  values remain user-supplied placeholders.
- Readback: `artifacts/wave_W64/requirements/HPC-W64-PROV-001.json`.

## PROV-002 Leonardo — PASS (verify-only)

- Profile `D:/Projeler/hpc-client-gui-plugins/plugins/leonardo/1.0.0/cluster-profile.json`
  (`schema_version` 2, `scheduler` slurm; Booster/DCGP partitions listed;
  storage home/work/fast/scratch/public/dres via remote-environment resolvers).
- `validate_cluster_profile_dict` returns `[]`.
- `build_cineca_cinquota_command` returns constant `cinQuota`;
  `parse_cineca_cinquota` work-row fixture → ok, storage `work`.
- Prerequisites (Smallstep/2FA) documented, never auto-executed.
- Provenance: CINECA docs URLs + verification date 2026-10-14 in
  `artifacts/refactored-v2/w64/lumi-leonardo-provenance.json`.
- Readback: `artifacts/wave_W64/requirements/HPC-W64-PROV-002.json`.

## Focused proof

Command: `python -m pytest tests/test_lumi_quota.py
tests/test_plugin_profile_v2.py tests/test_plugin_profile_v3.py
tests/test_plugin_schema_compat.py tests/test_plugin_security.py
tests/test_w34_provider_settings.py -q --durations=25 -p no:cacheprovider`

Result: **55 passed in 2.78s, exit 0** (55 collected). No defect reproduced;
no product write surface requested.

## Remaining

U01 complete. U02 complete (PROV-003 PASS, PROV-004 parked OWNER_DECISION_REQUIRED).
U03 complete (PROV-005 PASS). U04 complete (PROV-006 PASS; manifest
closeout-schema-clean, closure gated only on the PROV-004 owner decision).

## U02 Setonix verification and JUWELS absence triage (2026-10-14)

Verify-only, evidence-only unit. No product source modified.

### Content identity

S02 sha256 re-hash matches for all three U02 S02 files:

- `src/hpc_gui/plugins/providers.py` `b0934eb2…` (actual LOC 212; S02 says 248 — count drift only)
- `src/hpc_gui/plugins/validator.py` `f9a813dd…` (actual LOC 646; S02 says 698 — count drift only)
- `src/hpc_gui/services/pawsey_quota.py` `a11c2320…` (actual LOC 35; S02 says 44 — count drift only)

### PROV-003 Setonix — PASS (verify-only)

- Profile `D:/Projeler/hpc-client-gui-plugins/plugins/setonix/1.0.0/cluster-profile.json`
  (`schema_version` 2, `scheduler` slurm; partitions work/gpu/highmem/copy/debug/long;
  storage home/scratch/software; paths `/home/{user}`, `/scratch/{project}`).
- `validate_cluster_profile_dict` returns `[]`;
  `_validate_storage_and_quota_sections` returns `[]`.
- `parse_pawsey_account_balance` test fixture
  (`/software 124.66 GiB 161.37 GiB 63.0 (project) 43308 43.3 (user)`)
  → ok, storage `software`; `build_pawsey_account_balance_command` returns
  `pawseyAccountBalance -s`.
- Provenance: Pawsey docs URLs + verification date 2026-10-14 in
  `artifacts/refactored-v2/w64/setonix-juwels-provenance.json`; allocation
  values remain user-supplied placeholders.
- Readback: `artifacts/wave_W64/requirements/HPC-W64-PROV-003.json`.

### PROV-004 JUWELS — BLOCKED, parked OWNER_DECISION_REQUIRED

- Bounded search: `Get-ChildItem D:/Projeler/hpc-client-gui-plugins/plugins/`
  → ansys-lint, delta, fluent, frontera, leonardo, lumi, perlmutter, setonix,
  stampede3, truba; `Test-Path .../juwels/` → False. Setonix present as control.
- No JUWELS naming/partitions/hosts/auth fabricated; disposable validator fixture
  only (never a registry entry). CREATE surface
  `D:/Projeler/hpc-client-gui-plugins/plugins/juwels/` is outside W64 S05
  evidence-only authority → owner decision requested; creation work stopped.
- Readback: `artifacts/wave_W64/requirements/HPC-W64-PROV-004.json`.

### Focused proof

Plan validator nodes (12/12, exit 0):

`python -m pytest tests/test_w34_provider_settings.py::test_prov001_provider_registers_through_registry
[...advisory, optional-features, roundtrip...]
tests/test_w36_packaged_docs.py::test_matrix_disabled_plugin_registers_nothing
tests/test_w36_packaged_docs.py::test_matrix_provider_omits_quota_no_fake_quota
tests/test_pawsey_quota.py::test_pawsey_account_balance_parser_reads_software_usage_and_files
tests/test_plugin_profile_v2.py::[...] tests/test_plugin_profile_v3.py::[...]`

Result: **12 passed, exit 0**. Broad file run: 41 passed + 1 failed
(`test_docs_surface_plugin_entry_points_match_wx`, PLUGIN-BROWSE assert) —
outside the U02 validator set with the product tree untouched; reported as a
separate owner finding, not fixed per scope firewall.

## U03 Four-provider security schema and lifecycle matrix (2026-10-14)

Verify-only, evidence-only unit. No product source modified (all four S02
files git-clean). `validator.py` over 500 LOC — READ_ONLY exercise only.

### Content identity

S02 sha256 re-hash matches for all four U03 S02 files:

- `src/hpc_gui/plugins/validator.py` `f9a813dd…` (actual LOC 646; S02 says 698 — count drift only)
- `src/hpc_gui/plugins/integrity.py` `41f0a935…` (actual LOC 225; S02 says 256 — count drift only)
- `src/hpc_gui/plugins/installer.py` `4da7c37c…` (actual LOC 407; S02 says 451 — count drift only)
- `src/hpc_gui/wx_plugins.py` `fb333ce2…` (actual LOC 283; S02 says 322 — count drift only)

### PROV-005 — PASS (verify-only)

- Schema: `validate_registry_dict` refuses non-dict, bad `schema_version`,
  unsafe `manifest_path` (`../evil.json`, `/abs/evil.json`) and duplicate
  `(id, version)` pairs — all fail-closed.
- Hash: `verify_installed_version` on empty disposable root fail-closed
  (`missing manifest.json`); installer SHA mismatch raises `InstallError`;
  incomplete entry raises `InstallError: Registry entry is incomplete.`
- Discover/enable/disable/remove: `WxPluginManagerModel` on a disposable root
  runs headless (construct, `set_enabled` False, `remove` unknown → `[]`);
  no Windows11 runner needed — no native windows are created. Temp dirs removed.
- Providers: lumi/leonardo/setonix exercised via real sibling profiles;
  JUWELS shape only via disposable fixture (absent in sibling repo, nothing
  fabricated). No secrets or executables in provider data.
- Readbacks: `artifacts/wave_W64/requirements/HPC-W64-PROV-005.json`,
  `artifacts/refactored-v2/w64/security-lifecycle-matrix.json`.

### Focused proof

`python -m pytest tests/test_fluent_plugin_integration.py::test_latest_fluent_template_renders_after_install
tests/test_fluent_plugin_integration.py::test_registry_entry_installs_via_exact_file_protocol
tests/test_plugin_compatibility_override.py::test_absent_override_is_not_an_error_for_any_entry
tests/test_plugin_compatibility_override.py::test_override_cannot_widen_what_the_manifest_permits
tests/test_plugin_compatibility_override.py::test_unsupported_schema_stays_fail_closed_under_an_override
tests/test_plugin_compatibility_override.py::test_registry_without_override_resolves_exactly_as_before`

Result: **6 passed, exit 0**. Canonical validators: authoring PASS (79),
orchestration PASS, source-architecture changed-scope PASS.
`validate-managed-runtime.py` FAILS inside Agent Core harness internals
(`_wave_node_ship_gates` ModuleNotFoundError in core-snapshot scratch) — a
shared harness defect outside W64 scope, left untouched per S05/Agent Core
read-only rule and recorded as an external dependency, not a PROV-005 defect.

## U04 Provenance normalization and evidence closeout (2026-10-14)

Verify-only, evidence-only unit. No product source modified (both S02 files
git-clean).

### Content identity

- `scripts/generate_release_manifest.py` `00903d70…` (actual LOC 191; S02 says 228 — count drift only)
- `src/hpc_gui/plugins/registry_client.py` `f825f3b5…` (actual LOC 198; S02 says 236 — count drift only)

### PROV-006 — PASS (verify-only)

- `_plugin_commit()` returns sibling `.git` HEAD
  `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (UNKNOWN fallback `unknown`
  never triggered); plugin repository identity recorded.
- `parse_registry`: valid payload returns keys
  `[plugin_api, plugins, repository, schema_version]`; non-UTF-8, invalid
  JSON and schema-violating payloads all raise `RegistryError` fail-closed.
- Consolidated `artifacts/refactored-v2/w64/provider-evidence-normalized.json`
  from the U01–U03 matrices: exact source URL + verification date per field,
  allocation unknowns as placeholders, JUWELS as placeholder/BLOCKED
  (never fabricated).
- Readback: `artifacts/wave_W64/requirements/HPC-W64-PROV-006.json`.

### Focused proof

Plan nodes (8 items, exit 0): `test_registry_without_override_resolves_exactly_as_before`,
`test_widening_override_is_rejected_by_application_registry_validation`,
`test_parse_registry_accepts_valid_payload`,
`test_parse_registry_rejects_invalid_payloads[mutation0-3]`,
`test_real_ansys_installer_round_trip` — the last runs only with
`HPC_GUI_CONTRACT_REPO` pointing at the sibling checkout (first run 7 passed
+ 1 conditional skip; rerun with the recorded HEAD checkout 1 passed).
Authoring validator PASS (79).

`scripts/validate_wave_closeout.py --wave W64`: `can_close=false` on genuine
grounds only — `mandatory requirement blocked: HPC-W64-PROV-004` plus
`unresolved blockers: 1`. Manifest is schema-clean (6/6 owned requirements,
valid dispositions, green test rows). Closure awaits the PROV-004 owner
decision; no further evidence work is pending in this Wave.

## Repair 2026-10-14 - PROV-004 JUWELS rebind to sibling 8cce854 (repair 20261014-121312-6ab80522:4:W64:repair)

Evidence-only repair for finding W64-F001-PROV-004-JUWELS-REBIND
(semantic W64/AUTO/aae8afb8e725d606, hypothesis
PROV-004-juwels-present-at-sibling-8cce854-rebind-verify-only).
No product source modified; S02 files re-measured with zero drift vs the
W64 S02 snapshot; sibling repo untouched (read-only).

### Changed condition

- Sibling repo HEAD is now 8cce85446a8db72ea6b89b56bcb3df8916cbb0a8
  (feat: add Frontera Delta and JUWELS providers), previously f0abb7e7.
- plugins/juwels/1.0.0/ is committed at that HEAD
  (cluster-profile.json, manifest.json, README.md, sources.md;
  working tree clean for plugins/juwels/).
- The stale OWNER_DECISION_REQUIRED blocker for absent-juwels at f0abb7e7
  is therefore cleared without any owner CREATE grant.

### JUWELS 1.0.0 verification (truthful, no fabrication)

- validate_cluster_profile_dict(JUWELS 1.0.0 cluster-profile.json) returns []
  (exit 0); schema_version 2, profile_id juwels, scheduler slurm.
- Data-only: storage resolvers all remote-environment (HOME/PROJECT/SCRATCH);
  project/account are parameterized user-supplied requirement labels.
- No secrets or executables: no private-key material and no stored
  credential/username/project values (the access note explicitly states none
  are stored); manifest capabilities are [cluster-profile] only.
- Hosts juwels-cluster/juwels-booster.fz-juelich.de:22,
  auth ssh-key + keyboard-interactive, partitions snapshot
  batch, mem192, devel, gpus, booster, develbooster, large, largebooster
  (committed JSC-guide snapshot; large partitions are timeslot-restricted;
  re-check the live JSC guide before submission).
- File hashes (SHA-256): cluster-profile.json
  544c33fd34c4cb012e228b72b1e701ac6e6d087ef6a2833857c5b7ec2b7a4a40,
  manifest.json 31ce0abcd4160f6b9c78b56853698aba81080ee39feA632AB03F61E5106033DB,
  README.md AAF40F31303067EB8F386ABD321F6E883A625091583177B0C8113028636B76BF,
  sources.md E7686CB159BDDC3240408988A5F0A1EDEC9B562CD12B2EFA75D00728980A809D.

### Rebound evidence

- artifacts/wave_W64/requirements/HPC-W64-PROV-004.json: requirement_status
  PASS, plugins_head 8cce854, validator [], focused rerun recorded.
- artifacts/refactored-v2/w64/setonix-juwels-provenance.json: juwels presence
  proof with hashes and verified fields; disposition ACCEPTANCE_GREEN.
- artifacts/refactored-v2/w64/provider-evidence-normalized.json: juwels entry
  ACCEPTANCE_GREEN with requirement HPC-W64-PROV-004; repository head 8cce854.
- artifacts/wave_W64/WAVE_W64_EVIDENCE_MANIFEST.json: PROV-004 disposition PASS
  (implementation owner W64-U02), plugins_head 8cce854, blockers [], repair
  focused-retest row appended.
- HPC-W64-PROV-001/002/003/005/006 PASS rows preserved byte-identical.

### Focused proof

- Focused pytest (test_v1_profile_still_validates,
  test_v1_v2_v3_profiles_remain_valid,
  test_only_application_owned_slurm_commands_are_accepted): 3 passed, exit 0.
- scripts/validate_wave_closeout.py --wave W64 --no-execute-tests re-run at
  close of this repair; required outcome can_close=true with zero unresolved
  blockers (see repair receipt).

Repair written at 2026-10-14T09:27:18Z (UTC).
