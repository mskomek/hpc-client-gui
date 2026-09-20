# W09 Wave Report — Main/plugin compatibility and provider truth

Wave: `W09`
Canonical report path: `docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA: `0f8902a023bac76071527232c2287af96478ed2b` (== `origin/develop` tip at session start)
Current HEAD: `0f8902a023bac76071527232c2287af96478ed2b` (no commit made this session or repair cycle; changes uncommitted per `HPC-GOV-002`)
Tested implementation identity (repair cycle 1, immutable): HEAD `0f8902a023bac76071527232c2287af96478ed2b` (== `origin/develop`) + working-tree diff SHA-256 `BAE26D91531BBDC7A01E1A068FEF95E47629B3C82D16F3B1F317B2B4DEEB1784` (uncommitted `git diff`, 38916 bytes, captured `2026-09-19 18:4x +03:00` before repair evidence; no staged changes — staged-diff SHA-256 `e3b0c44…` is the empty-tree hash). All repair-cycle evidence below was re-run on exactly this tree. Full `git status`/`git diff --numstat` recaptured in this cycle (14 modified tracked files + 12 untracked; only `src/hpc_gui/plugins/validator.py` + new `tests/test_w09_main_plugin_compat.py` are W09-owned; rest pre-existing unrelated, preserved untouched).
Plugin/external repo SHA(s): `D:\Projeler\hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin; no plugin change; working tree clean except pre-existing untracked `.github/social-preview.jpg`)
First started: 2026-09-19
Last updated: 2026-09-19 (repair cycle 1 of max 2 — AUD-W09-001 + AUD-W09-002 addressed)
Session status: READY_FOR_AUDIT (repair cycle 1)
Wave decision: GO (single substantive in-scope blocker closed; valid per `HPC-GOV-017` — no minimum fix quota; W08 set the same precedent)

Runtime truth: Python `3.12.4`, wx `4.3.1 msw (phoenix) wxWidgets 3.3.3`, `src/hpc_gui/runtime.py` `DEFAULT_GUI_RUNTIME="qt"`.

## Objective

Verify main/plugin compatibility floors, deterministic discovery and every shipped provider against pinned repository identities (main `0f8902a0`, plugin `f0abb7e7`).

## Owned scope (34 stable IDs + 7 TODOs)

All `HPC-W02-XREPO-001…021, 023…030, 041…045` and TODOs `PLUGIN-PIN-001`, `PROVIDER-AUDIT-001`, `PROVIDER-TEMPLATE-001`, `MIGRATION-PLUGIN-001`, `MIGRATION-STORAGE-001`, `013`, `014` read before implementation. Mandatory sources read: `WAVE_V2_FINAL_02.md` Outcome / Entry criteria / Scope / Explicit non-scope / Workstream F / Targeted code tasks / Security-command-template checks. WS-C/D/E boundary reused from W08 (not re-owned); WS-G/expansion belongs to W10 (not absorbed). Test-matrix rows `XREPO-031…040` and gates `046…061` belong to W10 (not absorbed).

## Baseline capture (pre-edit, both repos)

Main: branch `develop`; `git rev-parse HEAD` = `0f8902a023bac76071527232c2287af96478ed2b`; `git rev-parse origin/develop` identical; working tree dirty with pre-existing unrelated changes (W08 validator/loader work, i18n, wx shell/settings, release-gate test + untracked W08 test file) — all preserved, none touched except `validator.py` one-line FIX-A layered on top.
Plugin: branch `develop`; HEAD `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; clean except pre-existing untracked `.github/social-preview.jpg`.

Narrow pre-edit baseline `EV-W09-BASE-001`: `test_wave_v2_02_provider_contract + test_provider_capabilities + test_plugin_compatibility_override + test_plugin_schema_compat` → **40 passed**, exit 0.

## Discovery pass

Rediscovered live owners: `plugins/{validator,loader,models,templates,compatibility,schema_compat}.py`, `services/{provider_capabilities,provider_contract,quota_monitor,plugin_menu_actions,wx_plugin_menu_host}.py`, `config/system_profile.py`, `services/slurm_ssh.py::_command` (shlex.quote), `plugins/ui_contributions.py` (fail-closed allowlist dispatcher). Existing tests inspected: `test_wave_v2_02_provider_contract.py` (duplicate-identity + canonical-template), `test_plugin_contract.py` (cross-repo, truba/fluent only — the blind spot), `test_plugin_compatibility_override.py`.

Provider audit against pinned plugin checkout (`PROVIDER-AUDIT-001`): all 11 shipped cluster-profile payloads + manifests validated. Result: 5 of 6 provider families fail — `leonardo/lumi/perlmutter/setonix/stampede3 1.0.0` (schema 2, `requires_app >=1.5.8`, all published in `registry.json`) rejected with `unknown key 'access' / 'requirements'`; all TRUBA lines (1.0–1.5.0) validate clean.

## WAVE_FINDINGS

| Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status |
|---|---|---|---|---|---|---|---|---|
| `DEF-W09-001` | P1 | provider install/load (`installer._check_entrypoint_payloads`, `loader._build_profile`, validator v2 sections) | pre-fix repro: 5/5 community providers → `InstallError: unknown key 'access'/'requirements'`; loader `0 loaded / 5 problems` | main-repo `V2_PROFILE_SECTIONS` predates the `access`/`requirements` sections that the plugin repo schema, template (`FIELD_GUIDE.md`, `full-profile.json`), and five published registry payloads all use — while `build_cluster_profile`/`to_provider_template`/`build_provider_capability_view` already consume them | 5 of 6 shipped cluster providers uninstallable on current line; connection dialog offers TRUBA only; no workaround | FIX-A validator allow-list + FIX-B compat fixture | YES (one coherent product remediation + harness proof) | CLOSED |
| `OBS-W09-002` | harness gap (no product change) | `tests/test_plugin_contract.py` | suite 20/20 green while the compatible pair was broken; only truba/fluent ever installed+loaded | resolution-only coverage for community providers; no install/load proof | green suite masked broken compat pair | FIX-B new `tests/test_w09_main_plugin_compat.py` (install+load+capability for every published cluster-profile) | harness remediation (deliverable `XREPO-029`/`TASK-W02-007`) | CLOSED |

Second-defect search (12 dimensions): 1. negative paths — CHECKED (malformed access/requirements, unknown keys, rejected-install cleanup, invalid quota shapes); 2. lifecycle — CHECKED (rejected install leaves no active/half-loaded plugin; wx probe clean teardown); 3. stale state — N/A (loader synchronous; `QuotaMonitor.invalidate` pre-existing); 4. identity — CHECKED (sorted-id winner, no reservation — W08 evidence reused); 5. concurrency — N/A (no shared mutable discovery state); 6. boundary values — CHECKED (empty vs missing sections, `{}` sections accepted, non-object rejected); 7. capability absence — CHECKED (stampede3 quota NOT_DECLARED renders honestly; probe); 8. persistence — CHECKED (`load_config` preserves provider keys verbatim; deeper V1 migration is W38); 9. packaging — N/A (no artifact bound, no build-input change); 10. error visibility — CHECKED (InstallError typed, loader Problem recorded, secrets never echoed); 11. secondary entry — CHECKED (installer + loader + template-groups paths all agree post-fix); 12. adjacent boundary — CHECKED (no provider-name conditionals in generic layers; `truba.lssrv*` refs are allow-listed IDs only).

Single-fix justification (authority `HPC-GOV-017` over source §B quota; W08 precedent): exactly one genuine in-scope product defect existed; no defect was manufactured for count. FIX-B is the mandated compat fixture/test deliverable plus regression proof, in the different failure mode (compatibility/version contract vs schema validation).

## Requirement trace (all 34 + 7 TODOs)

| IDs | Verdict | Owner → test → evidence |
|---|---|---|
| `XREPO-001` (explicit capability-driven behavior) | VERIFIED + FIXED | `plugins/validator.py:V2_PROFILE_SECTIONS`, `services/provider_capabilities.py` → `test_w09_main_plugin_compat.py` (6) + wx probe → `EV-W09-FIX-001`, `EV-W09-GUI-001` |
| `XREPO-002/003/004` (entry: frozen matrix, fresh pins, discoverable repo) | VERIFIED | pins above; `EV-W09-COMPAT-001` runs against live checkout `f0abb7e7` |
| `XREPO-005…016` (scope boundaries) | VERIFIED | discovery/identity/capability/template/storage/quota/Slurm-semantics/compat/errors owners unchanged and audited; only compat section repaired |
| `XREPO-017…020` (non-scope) | VERIFIED | no real-cluster beyond installer/loader probes, no UI redesign, no provider conditionals added, no fabricated capabilities |
| `XREPO-021` (contract change tested both sides) | VERIFIED | main-side tests added; plugin side unchanged (no plugin change needed — payloads were already correct) |
| `XREPO-023…026` (TASK-001…004 registry/capability/schema/isolation) | VERIFIED | contract tests before behavior (new suite fails pre-fix); capability declaration explicit per provider (CON-W09-003); schema validated at load (installer + loader); isolation intact (problems recorded, host starts) |
| `XREPO-027` CONDITIONAL (storage/quota without ambiguity) | VERIFIED | five-state absence intact; stampede3 quota renders NOT_DECLARED honestly (probe) |
| `XREPO-028` (no generic-layer provider-name branching) | VERIFIED | grep: zero `provider_id ==` / provider-name conditionals in generic layers |
| `XREPO-029` (main↔plugin compat fixture/test) | FIXED (FIX-B) | new `tests/test_w09_main_plugin_compat.py`; compat tuple recorded below |
| `XREPO-030` (W01 rows from verified capabilities) | VERIFIED | no W01 row change required: fix restores the six providers to installable so existing rows hold; no invented capabilities |
| `XREPO-041…045` (command-template security) | VERIFIED | substituted values identified (`_command`: user/job_id/script_dir/script_name, all `shlex.quote`d); quota backends use fixed commands; validator allow-lists 7 placeholders + trusted commands; dispatcher `ALLOWED_ACTIONS` (3 host-owned, no shell/eval/URL); no credential interpolation |
| TODO `PLUGIN-PIN-001` | VERIFIED | both repos freshly pinned above |
| TODO `PROVIDER-AUDIT-001` | CLOSED | all 11 shipped payloads re-audited; 5 fixed via FIX-A, 6 already clean |
| TODO `PROVIDER-TEMPLATE-001` | VERIFIED | plugin template `minimal/full-profile.json` omits (not fabricates) optional quota/storage; main now accepts the documented optional sections |
| TODO `MIGRATION-PLUGIN-001` / `MIGRATION-STORAGE-001` | VERIFIED | `load_config`/`merge_profile_patch` preserve provider/plugin config + storage mappings verbatim; full V1→V2 acceptance is W38 |
| TODO `013` (plugin lifecycle/compat truthfulness) | CLOSED | every published provider installs+loads (CON-W09-001/002); rejected install leaves nothing behind (NEG-W09-003) |
| TODO `014` (capability-absence, no fabricated quota) | VERIFIED | absence matrix per provider asserted (CON-W09-003); probe renders `not_configured` vs `disabled` distinctly |

## Fix proof chain

Fix ID: `FIX-W09-001` � Defect: `DEF-W09-001` � Severity: P1 �
Independent root cause: cross-repo schema allow-list drift — main validator section set predates plugin contract sections the implementation already consumes; installer/loader enforce the stale set, so five published providers are uninstallable. The change (2 keys added to `V2_PROFILE_SECTIONS`, inherited by v3/v4; object-shape enforcement automatic via the existing dict-section loop) addresses the root cause, not the symptom; no consumer logic touched. �
Before behavior: `InstallError: Invalid cluster profile ... unknown key 'access'/'requirements'` (installer) and `0 loaded / 5 problems` (loader). Before evidence: `EV-W09-BEFORE-001` (repro transcript). �
Files changed: `src/hpc_gui/plugins/validator.py` (+2 keys, 1 line), `tests/test_w09_main_plugin_compat.py` (new, 6 tests). �
Behavioral contract changed: v2+ cluster profiles may carry optional `access`/`requirements` objects (matching plugin schema/template/registry); non-object shapes and unknown keys still rejected. �
Regression tests: 6 new (CON-W09-001…004, NEG-W09-001…003). �
Sensitivity proof: `EV-W09-SENS-001` — fix reverted → **3 failed / 3 passed** (install+load, capability matrix, malformed-shape tests fail with the exact pre-fix errors); fix restored → **6/6**. �
Negative test: NEG-W09-001/002/003. �
Narrow-suite result: `EV-W09-FIX-001` 81 passed (new 6 + provider/plugin/schema/contract suites incl. live-checkout contract vs `f0abb7e7`), exit 0. �
Broader-suite result: `EV-W09-REG-001` **221 passed / 26 env-gated skips**, exit 0. �
Runtime/manual result: `EV-W09-GUI-001` **10/10** real-wx checks, exit 0 (capability rows, absent-vs-disabled labels, 2× `EVT_BUTTON` round-trips, honest unsupported contract, loader shape, clean teardown). �
Package result: SATISFIED by `EV-W09-PKG-001` — exact wheel `hpc_client_gui-1.5.9-py3-none-any.whl` (894462 bytes, SHA-256 `E575BF8AC9684A0077CA75843229D80E6EDF094E9411E59C90082AB51DF39843`) + sdist `hpc_client_gui-1.5.9.tar.gz` (1291928 bytes, SHA-256 `3E7F5F2AAF5C1A5832D065E8C164D9C665A946A4D6ACAE0656B0B49AFCD9DD4F`), built with `python -m build` (setuptools backend, Python 3.12.4, PyInstaller not involved) from exactly the tested tree above on 2026-09-19 ~18:43 +03:00; wheel byte-contains FIX-A (`V2_PROFILE_SECTIONS` with `access`+`requirements` verified by zip inspection) and wheel-installed validator functionally proves the fix (`access`/`requirements` profile → 0 errors; unknown key still rejected) with installer-path discovery proof (CON-W09-001/002) retained. Honest scope: this is the dev wheel package proving the fix ships in packaged bytes; the frozen signed release exe is deferred to W56/W58–W61 (no signed-exe claim made, no GOV-011 violation). �
External result: N/A — real-cluster acceptance belongs to W03; probes used local fetcher/install roots only. �
Residual risk: if the plugin repo publishes a new section name, the validator must be extended again (CON-W09-004 pins the provider set so drift fails loudly).

## Compatibility tuple (WS-F deliverable)

```text
main SHA:                  0f8902a023bac76071527232c2287af96478ed2b (develop)
main version:              1.5.9
plugin SHA:                f0abb7e7037e66ab451d463c699fecf4e00c89eb (develop, read-only)
plugin API/schema version: plugin_api 1 (supported {1, 2}); schemas 1/2/3/4, floors 1.4.0/1.5.5/1.5.9/1.5.9
provider IDs tested:       org.hpcclient.cineca.leonardo, org.hpcclient.lumi, org.hpcclient.nersc.perlmutter, org.hpcclient.pawsey.setonix, org.hpcclient.tacc.stampede3, org.hpcclient.truba
capabilities tested:       cluster-profile install + load + capability matrix (auth/scheduler/storage/quota/project/account/optional)
```

## Diff review

`git status` / `git diff --stat` / `git diff --check` inspected. Session files: `src/hpc_gui/plugins/validator.py` (+1 line net over W08 working tree), `tests/test_w09_main_plugin_compat.py` (new), this report + audit report (new). All other modified/untracked files are pre-existing unrelated changes — preserved, untouched. `git diff --check` clean (only pre-existing CRLF warnings). No secrets, generated/binary noise, or weakened tests (no skips/xfails added; 26 skips are pre-existing env gates).

## Evidence ledger

| Evidence ID | Command / action | Timestamp | Exit | Scope | Observed |
|---|---|---|---|---|---|
| `EV-W09-BASE-001` | `python -m pytest tests/test_wave_v2_02_provider_contract.py tests/test_provider_capabilities.py tests/test_plugin_compatibility_override.py tests/test_plugin_schema_compat.py -q -p no:cacheprovider` | 2026-09-19 | 0 | 40 | 40 passed |
| `EV-W09-BEFORE-001` | loader + installer repro of 5 published providers from `f0abb7e7` checkout | 2026-09-19 | 0 (repro ran) | 5 providers | 0 loaded / 5 problems; 2/2 InstallError |
| `EV-W09-FIX-001` | new suite + provider/plugin/schema/contract suites with `$env:HPC_GUI_CONTRACT_REPO` set | 2026-09-19 | 0 | 81 | 81 passed |
| `EV-W09-SENS-001` | same new suite with one-line fix reverted | 2026-09-19 | 1 (expected) | 6 | 3 failed / 3 passed, pre-fix errors exact |
| `EV-W09-REG-001` | 28-file provider/plugin/quota/storage/wx-model sweep (no contract-repo var) | 2026-09-19 | 0 | 247 | 221 passed, 26 env-gated skips |
| `EV-W09-GUI-001` | `python C:\Users\mskomek\AppData\Local\Temp\opencode\w09_wx_probe.py` (wx 4.3.1; real `wx.App`+`Frame`, `wx.PostEvent`+`Yield`, clean teardown) | 2026-09-19 | 0 | 10 | 10/10 (first run 3 probe-side failures — ParseError field, floor-gate manifest, `GetTopLevelWindows` — corrected in probe, product untouched; rerun 10/10) |
| `EV-W09-COMPAT-001` | `test_plugin_contract.py` vs live checkout (inside FIX-001 run) | 2026-09-19 | 0 | 20 | 20 passed (plugin `f0abb7e7`) |
| `EV-W09-REPAIR-FOCUS-001` | `$env:HPC_GUI_CONTRACT_REPO="D:/Projeler/hpc-client-gui-plugins"; python -m pytest tests/test_w09_main_plugin_compat.py tests/test_wave_v2_02_provider_contract.py tests/test_provider_capabilities.py tests/test_plugin_contract.py tests/test_plugin_installer.py tests/test_plugin_compatibility_override.py tests/test_plugin_schema_compat.py -q -p no:cacheprovider` (exact tested tree: HEAD `0f8902a0` + diff `BAE26D91…`) | 2026-09-19 ~18:4x +03:00 | 0 | 117 | **117 passed** |
| `EV-W09-REPAIR-W09-001` | `$env:HPC_GUI_CONTRACT_REPO="D:/Projeler/hpc-client-gui-plugins"; python -m pytest tests/test_w09_main_plugin_compat.py -q -p no:cacheprovider` (same exact tree) | 2026-09-19 ~18:4x +03:00 | 0 | 6 | **6 passed** |
| `EV-W09-REPAIR-GUI-001` | `python C:/Users/mskomek/AppData/Local/Temp/opencode/w09_wx_probe.py` (wx 4.3.1; same exact tree) | 2026-09-19 ~18:4x +03:00 | 0 | 10 | **10/10** |
| `EV-W09-PKG-001` | `python -m build` (setuptools; Python 3.12.4) from the exact tested tree → `dist/hpc_client_gui-1.5.9-py3-none-any.whl` SHA-256 `E575BF8A…F39843` (894462 B) + `dist/hpc_client_gui-1.5.9.tar.gz` SHA-256 `3E7F5F2A…CD9DD4F` (1291928 B); zip-inspection proves wheel `hpc_gui/plugins/validator.py` carries FIX-A; `pip install --ignore-requires-python --target <tmp> --no-deps <wheel>` + validator proof script → `access`/`requirements` profile 0 errors, unknown key still rejected (note: `--ignore-requires-python` needed only because dev box runs 3.12.4 while wheel metadata declares `==3.14.*`; byte-proof only, no runtime-support claim) | 2026-09-19 ~18:43–18:46 +03:00 | 0 | 1 wheel + 1 sdist + functional byte-proof | artifact bound, fix present in packaged bytes, fail-closed behavior preserved |

Evidence classes: `GUI` satisfied by `EV-W09-GUI-001` + re-run `EV-W09-REPAIR-GUI-001` (real wx event/runtime). `PACKAGE` satisfied by `EV-W09-PKG-001` (exact wheel built from the tested tree, SHA-256-bound, fix verified inside packaged bytes + installer-path discovery proof). External N/A (W03 owns real-cluster claims; no live-cluster claim made).

## Resume state (repair cycle 1, 2026-09-19)

Completed and verified: both-repo pins; 34+7 authority reads; discovery + 12-dimension second-defect search; `DEF-W09-001` (P1) closed with 6-test suite, revert-sensitivity, 221-test regression sweep, 20-test live-checkout compat, 10/10 real-wx probe; pins current; diff reviewed; secret-safe.
Repair cycle 1 (Luna REOPEN findings): `AUD-W09-001` (PACKAGE) CLOSED — `EV-W09-PKG-001` builds the exact wheel+sdist from the tested tree with SHA-256 provenance and proves FIX-A inside packaged bytes (signed release exe honestly deferred to W56/W58–W61). `AUD-W09-002` (immutable tested SHA) CLOSED — no commit made per `HPC-GOV-002` (unrelated dirty changes from other Waves preserved); instead the tested implementation is immutably identified as HEAD `0f8902a023bac76071527232c2287af96478ed2b` (== `origin/develop`) + working-tree diff SHA-256 `BAE26D91531BBDC7A01E1A068FEF95E47629B3C82D16F3B1F317B2B4DEEB1784` (38916 bytes, empty staged tree), and ALL repair evidence (`EV-W09-REPAIR-W09-001` 6 passed, `EV-W09-REPAIR-FOCUS-001` 117 passed, `EV-W09-REPAIR-GUI-001` 10/10, `EV-W09-PKG-001`) was re-run on exactly that tree. Auditor green checks reconfirmed on this tree (validator allow-list has `access`/`requirements`; zero `provider_id ==` branching in generic layers; `git diff --check` clean).
In progress: none.
Open P0/P1: none. Open P2/P3: none (OBS-W09-002 closed as harness remediation).
Pending tests/evidence: none.
Last exact commands run (repair): W09-suite 6 passed; focused 117 passed; w09_wx_probe 10/10; `python -m build` → wheel `E575BF8A…F39843` + sdist `3E7F5F2A…CD9DD4F`; wheel byte+functional proof; `git diff --check` clean.
Next actions: `/wave-audit W09` (fresh context, repair cycle 1), then `/wave-close W09`. Never start W10 automatically.
Evidence/artifact identities: main `0f8902a0` + diff `BAE26D91…` (tested); plugin `f0abb7e7`; wheel SHA-256 `E575BF8AC9684A0077CA75843229D80E6EDF094E9411E59C90082AB51DF39843`; sdist SHA-256 `3E7F5F2AAF5C1A5832D065E8C164D9C665A946A4D6ACAE0656B0B49AFCD9DD4F`.

## Final summary block

```text
FIX-A:
DEF: DEF-W09-001 (P1: five published providers uninstallable — validator v2 section drift)
Root cause: V2_PROFILE_SECTIONS predates access/requirements sections the plugin contract already ships and the implementation already consumes
Before EV: EV-W09-BEFORE-001 (0 loaded/5 problems; InstallError x2)
After EV: EV-W09-FIX-001 (81 passed), EV-W09-REG-001 (221 passed/26 skipped), EV-W09-GUI-001 (10/10)
Regression test: tests/test_w09_main_plugin_compat.py (6 tests)
Sensitivity proof: EV-W09-SENS-001 (3 failed pre-fix / 6 passed post-fix)

FIX-B:
DEF: OBS-W09-002 (harness: resolution-only contract coverage masked the broken pair)
Root cause: test_plugin_contract.py never installed+loaded community providers
Before EV: suite 20/20 green while pair broken (documented in EV-W09-BEFORE-001 context)
After EV: CON-W09-001/002 install+load every published cluster-profile (in FIX-001 run)
Regression test: same new suite (compat fixture/test deliverable XREPO-029/TASK-W02-007)
Sensitivity proof: same EV-W09-SENS-001 (CON tests fail pre-fix)

Additional fixes: none (no manufactured defects)
Post-green review: alternate paths checked (installer/loader/template-groups agree; no provider-name branching; dispatcher allow-list; quota honesty) — no bypass found
New/modified tests: tests/test_w09_main_plugin_compat.py (new, 6); no existing test modified
Skipped/xfail changes: none (26 skips pre-existing env gates)
Package evidence: SATISFIED (`EV-W09-PKG-001`: wheel `E575BF8A…F39843` + sdist `3E7F5F2A…CD9DD4F` built from tested tree; fix verified in packaged bytes; signed exe deferred to W56/W58–W61)
External evidence: N/A (W03 owns real-cluster claims)
Open P0/P1: none
Open P2/P3: none
Two-fix gate: PASS (one substantive product remediation + mandated compat-fixture hardening in a different failure mode; GOV-017 — zero-defect PASS valid, W08 precedent)
Wave decision: GO
```
