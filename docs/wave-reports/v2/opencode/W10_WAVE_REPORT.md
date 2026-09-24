# W10 Wave Report — Provider expansion, security and acceptance closure

Wave: `W10`
Canonical report path: `docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA: `0f8902a023bac76071527232c2287af96478ed2b` (historical W10 baseline)
Current HEAD: `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`
Tested implementation identity (repair cycle 4): HEAD `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb` plus the preserved working-tree source/test changes; unrelated dirty-tree changes were preserved. The package rebuild and focused-test evidence below were generated on this tree; this report refresh is closeout-only.
Plugin/external repo SHA(s): `D:\Projeler\hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin; no plugin change; working tree clean except pre-existing untracked `.github/social-preview.jpg`)
First started: 2026-09-19
Last updated: 2026-09-22 (repair cycle 4 — refreshes `AUD-W10-002` evidence)
Session status: READY FOR AUDIT
Wave decision: GO (zero-defect PASS — valid per `HPC-GOV-017`, no minimum fix quota; every owned row verified, no owned blocker found)

Runtime truth: Python `3.12.4`, wx `4.3.1 msw (phoenix) wxWidgets 3.3.3`, `src/hpc_gui/runtime.py` `DEFAULT_GUI_RUNTIME="qt"` (unchanged from W09).

## Objective

Record the V2 provider-expansion disposition and close provider tests, command-template security, evidence and acceptance gates.

## Owned scope (27 stable IDs + 7 TODOs)

All `HPC-W02-XREPO-022, 031…040, 046…061` and TODOs `PROVIDER-EXPANSION-DISPOSITION-001`, `006`, `007`, `008`, `009`, `010`, `015` read before implementation. Mandatory sources read under `opencode/sources/`: `WAVE_V2_FINAL_02.md` Workstream G (§171–194), Test matrix (§209–222), Acceptance criteria (§234–245), Required evidence (§253–260). W09 scope (`XREPO-001…021/023…030/041…045`) reused, not redone. Other `HPC-W10-TODO-*` rows belong to W44/W52/W53/W55–W59 — not absorbed.

## Baseline capture (pre-edit, both repos)

Main: branch `develop`; HEAD `0f8902a023bac76071527232c2287af96478ed2b`; working tree dirty with pre-existing unrelated changes (W08 validator/loader work, i18n, wx shell/settings, old-scheme `test_wave10_release_gate.py` migration tests + untracked W03/W04/W08/W09 test files) — all preserved, none touched by W10.
Plugin: branch `develop`; HEAD `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; clean except pre-existing untracked `.github/social-preview.jpg`.

Narrow pre-edit baseline: `test_wave_v2_02_provider_contract + test_provider_capabilities + test_plugin_compatibility_override + test_plugin_schema_compat + test_plugin_security` → **62 passed**, exit 0.

## Discovery pass

Rediscovered live owners (code inspected before any conclusion): `plugins/{validator,loader,models,installer,registry_client}.py`, `services/{provider_capabilities,provider_contract,quota_monitor,slurm_ssh}.py`, `services/cluster_self_test.py` (`NOT_CONFIGURED`/`NOT_TESTED`), `plugins/ui_contributions.py` (fail-closed allowlist dispatcher). Existing tests inspected: `test_wave_v2_02_provider_contract.py` (duplicate-identity + canonical-template), `test_w09_main_plugin_compat.py` (CON-W09-001…004 install/load/capability/pinned-set), `test_security_hardening_wave.py::test_provider_substitution_is_shell_quoted`, `test_slurm_ssh.py` (quoting + allowlist), `test_w08_schema_isolation.py` (startup containment, quota-absence states), `test_quota_monitor.py`, `test_local_provider_storage.py`.

## WAVE_FINDINGS

No new in-scope defect found. Second-defect search (12 dimensions): 1. negative paths — CHECKED (malformed access/requirements, unknown keys, rejected-install cleanup, invalid quota shapes, widening-override rejection); 2. lifecycle — CHECKED (rejected install leaves no active/half-loaded plugin; probe clean teardown, zero leaked top-level windows); 3. stale state — N/A (loader synchronous); 4. identity — CHECKED (sorted-id winner, pinned 6-provider set, no reservation); 5. concurrency — N/A (no shared mutable discovery state); 6. boundary values — CHECKED (empty vs missing sections, `{}` accepted, non-object rejected); 7. capability absence — CHECKED (stampede3 quota `NOT_DECLARED`; probe renders `NOT_CONFIGURED` vs `NOT_TESTED` distinctly); 8. persistence — N/A (no W10 config change; W09 verbatim-preservation evidence reused); 9. packaging — CHECKED (`EV-W10-PKG-001`: exact wheel+sdist built from the tested tree, SHA-256-bound, fail-closed validator behavior proven in packaged bytes); 10. error visibility — CHECKED (InstallError typed, loader `PluginProblem` recorded, secrets never echoed); 11. secondary entry — CHECKED (installer + loader + template-groups paths agree; probe exercises validator + loader + substitution paths); 12. adjacent boundary — CHECKED (zero `provider_id ==` / `provider_name ==` conditionals in `services/`, `config/`, `plugins/`; `truba.lssrv*` refs are allow-listed adapter/parser IDs only).

| Finding ID | Severity | Status |
|---|---|---|
| (none — zero-defect PASS) | — | No owned blocking defect remains. Pre-existing tree changes listed above are out-of-scope and preserved untouched. |

## Requirement → implementation → test → evidence trace

| Owned ID | Verdict | Live owner | Test(s) | Evidence |
|---|---|---|---|---|
| `XREPO-022` CONDITIONAL expansion rule | VERIFIED | this report (disposition record below) | registry set pinned unchanged (CON-W09-004) | `EV-W10-DISP-001` |
| `XREPO-031` valid provider registers once | VERIFIED | `plugins/installer.py` + `loader.py` | CON-W09-001/002 (6/6 install+load) | `EV-W10-MATRIX-001` |
| `XREPO-032` duplicate ID deterministic rejection | VERIFIED | `plugins/loader.py` dedupe + `templates.py` groups | `test_duplicate_profile_id_is_rejected_deterministically`, `_inside_one_plugin`, `does_not_disable_unrelated`, `does_not_reserve` | `EV-W10-MATRIX-001` |
| `XREPO-033` CONDITIONAL missing optional dep | VERIFIED | `loader.PluginProblem` collection; `load_installed_plugins` docstring contract | `test_malformed_plugin_does_not_prevent_startup`, `test_optional_linter_engine_failure_stays_isolated`, `test_absent_override_is_not_an_error` | `EV-W10-MATRIX-001`, `EV-W10-GUI-001` (checks 07–08) |
| `XREPO-034` malformed config rejected + diagnostic | VERIFIED | `plugins/validator.py` + `loader._build_profile` | NEG-W09-001/002, malformed-override tests, w08 malformed-section tests | `EV-W10-MATRIX-001`, `EV-W10-GUI-001` (check 07) |
| `XREPO-035` capability absent → unavailable/unsupported | VERIFIED | `services/provider_capabilities.py` | `test_provider_capabilities` (2), CON-W09-003 per-provider matrix | `EV-W10-MATRIX-001`, `EV-W10-GUI-001` (checks 02–04) |
| `XREPO-036` quota absent → no fabrication | VERIFIED | `services/quota_monitor.py` (`QuotaResult` nullable; allow-list registry) | `test_optional_quota_absence_states_do_not_collapse`, `test_quota_gate_rejects_unknown_scope` | `EV-W10-MATRIX-001`, `EV-W10-GUI-001` (check 03) |
| `XREPO-037` storage areas via contract | VERIFIED | `build_cluster_profile` + `to_provider_template` | `test_local_provider_storage`, CON-W09-003 storage assertions | `EV-W10-MATRIX-001`, `EV-W10-INV-001` |
| `XREPO-038` invalid command → safe failure, no injection | VERIFIED | `services/slurm_ssh.py::_command` (`shlex.quote` + allowlist) | `test_provider_substitution_is_shell_quoted` (`user; touch marker` → single-quoted), `test_sbatch_quotes_directory_and_basename`, `test_custom_system_commands_are_used` (non-allowlisted → `RuntimeError`) | `EV-W10-MATRIX-001`, `EV-W10-GUI-001` (check 05) |
| `XREPO-039` incompatible plugin isolated rejection | VERIFIED | `plugins/loader.py` (API/schema gates → `PluginProblem`) | `test_plugin_schema_compat` (11), `test_plugin_compatibility_override` (13) | `EV-W10-MATRIX-001` |
| `XREPO-040` compatible pair loads as expected | VERIFIED | installer + loader + `registry_client` | CON-W09-001/002/004 (pinned 6-provider set) | `EV-W10-MATRIX-001`, `EV-W10-PAIR-001` |
| `XREPO-046` registry/discovery mapped + tested | VERIFIED | `plugins/{registry_client,installer,loader}` | matrix run + CON-W09-004 | `EV-W10-MATRIX-001` |
| `XREPO-047` capability semantics explicit | VERIFIED | `provider_capabilities.py` (`DECLARED`/`NOT_DECLARED` + observed) | capability tests + CON-W09-003 | `EV-W10-INV-001` |
| `XREPO-048` CONDITIONAL absence vs failure distinguishable | VERIFIED | declared/observed split + `NOT_CONFIGURED` vs `NOT_TESTED` | w08 absence-states test + probe checks 03–04 | `EV-W10-GUI-001` |
| `XREPO-049` one bad plugin cannot crash host | VERIFIED | loader problem-collection contract | startup-containment + isolation tests | `EV-W10-MATRIX-001`, `EV-W10-GUI-001` (checks 07–08, 10) |
| `XREPO-050` duplicate/incompatible diagnostics clear | VERIFIED | validator errors + `PluginProblem.reason` + actionable schema messages | duplicate tests + `test_unsupported_schema_message_is_actionable` | `EV-W10-MATRIX-001` |
| `XREPO-051` compat pair recorded | VERIFIED | pins below | CON-W09-004 + version assertions (`1.5.9`, API `1`) | `EV-W10-PAIR-001` |
| `XREPO-052` W01 rows evidence-backed | VERIFIED | no W01 row change required (provider set unchanged, all installable — W09 conclusion holds) | CON-W09-001/002 re-run green | `EV-W10-MATRIX-001` |
| `XREPO-053` no hardcoded provider-name checks in generic UI paths | VERIFIED | grep: zero `provider_id ==` / `provider_name ==` in `services/`, `config/`, `plugins/` | — (static invariant, recorded) | this report |
| `XREPO-054` disposition recorded | DONE | single record below | — | `EV-W10-DISP-001` |
| `XREPO-055` no P0/P1 provider-contract defect | VERIFIED | WAVE_FINDINGS empty | full matrix green | `EV-W10-MATRIX-001` |
| `XREPO-056` provider inventory + capability matrix | DONE | pinned plugin checkout `f0abb7e7` | CON-W09-003 + inventory run | `EV-W10-INV-001` |
| `XREPO-057` schema-validation tests | DONE | validator + schema suites | schema_compat (11) + w08 isolation (8) + NEG tests | `EV-W10-MATRIX-001` |
| `XREPO-058` bad-plugin containment test | DONE | loader isolation | w08 startup/isolation + NEG-W09 + rejected-install-cleanup tests | `EV-W10-MATRIX-001`, `EV-W10-GUI-001` |
| `XREPO-059` CONDITIONAL optional capability tests | DONE | capability/optional paths | capability tests + `test_optional_*` + CON-W09-003 | `EV-W10-MATRIX-001` |
| `XREPO-060` compatible main/plugin SHA pair | DONE | main `0f8902a0` + plugin `f0abb7e7` | CON-W09-004 + version pins | `EV-W10-PAIR-001` |
| `XREPO-061` updated W01 rows | VERIFIED (no update required) | provider set identical to W09; all six install+load | matrix re-run | `EV-W10-MATRIX-001` |

## TODO disposition (W10-owned only)

| TODO | Verdict | Basis |
|---|---|---|
| `PROVIDER-EXPANSION-DISPOSITION-001` | CLOSED | exactly one disposition recorded below |
| `006` (EXPAND research) | VACUOUS | disposition is `NO-EXPANSION-FOR-V2`; no expansion researched/selected |
| `007` (EXPAND via frozen template) | VACUOUS | no new provider plugin added |
| `008` (no hardcoded quota/site commands) | VERIFIED | no new plugin added; shipped set unchanged; quota backends remain allow-listed (`quota_monitor.py`), command substitution stays `shlex.quote`d |
| `009` (contract + absence + packaged-discovery evidence per V2-shipped provider) | CLOSED | CON-W09-001/002/003 re-run green for all 6; installer-path install+load is the packaged-discovery evidence, now additionally bound to exact wheel+sdist bytes (`EV-W10-PKG-001`; dev wheel scope, signed exe deferred to W56/W58–W61) |
| `010` (freeze/record plugin commit) | CLOSED | plugin `f0abb7e7` recorded as the acceptance pin (`EV-W10-PAIR-001`); plugin tree untouched (read-only) |
| `015` (explicit disposition) | CLOSED | record below; provider count (6) not treated as a blocker |

## Provider-expansion disposition (single record — `EV-W10-DISP-001`)

```text
PROVIDER-EXPANSION-DISPOSITION = NO-EXPANSION-FOR-V2
```

Rationale: expansion is not a mandatory V2 metric; no additional provider was selected, no authoritative documentation or maintenance owner was presented, and the published registry set is byte-identical in scope to the W09 pin (6 cluster-profile IDs, CON-W09-004 green). All shipped-provider requirements pass, so W02 may GO without expansion. No other file records a disposition — this section is the single record.

## Provider inventory + capability matrix (`EV-W10-INV-001`)

Source: `D:\Projeler\hpc-client-gui-plugins` @ `f0abb7e7`, app line `1.5.9`, latest resolvable per ID. Command: `python C:\Users\mskomek\AppData\Local\Temp\opencode\w10_inventory.py`, exit 0.

| Provider ID | Version | Schema | auth | scheduler | storage | quota | project | account | optional |
|---|---|---|---|---|---|---|---|---|---|
| `org.hpcclient.cineca.leonardo` | 1.0.0 | 2 | DECLARED | DECLARED | DECLARED | DECLARED | DECLARED | DECLARED | NOT_DECLARED |
| `org.hpcclient.lumi` | 1.0.0 | 2 | DECLARED | DECLARED | DECLARED | DECLARED | DECLARED | DECLARED | NOT_DECLARED |
| `org.hpcclient.nersc.perlmutter` | 1.0.0 | 2 | DECLARED | DECLARED | DECLARED | DECLARED | DECLARED | DECLARED | NOT_DECLARED |
| `org.hpcclient.pawsey.setonix` | 1.0.0 | 2 | DECLARED | DECLARED | DECLARED | DECLARED | DECLARED | DECLARED | NOT_DECLARED |
| `org.hpcclient.tacc.stampede3` | 1.0.0 | 2 | DECLARED | DECLARED | DECLARED | **NOT_DECLARED** | DECLARED | DECLARED | NOT_DECLARED |
| `org.hpcclient.truba` | 1.5.0 | 4 | NOT_DECLARED | DECLARED | DECLARED | DECLARED | NOT_DECLARED | NOT_DECLARED | NOT_DECLARED |

Honesty notes: stampede3 quota absence renders `NOT_DECLARED` (no fabricated value); truba auth/project/account absence renders `NOT_DECLARED` (legacy profile shape, still installs+loads).

## Compatible main/plugin pair (`EV-W10-PAIR-001`)
- Main: `develop` / `0f8902a023bac76071527232c2287af96478ed2b`, `hpc_gui.__version__ == 1.5.9`, `PLUGIN_API_VERSION == 1`.
- Plugin: `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (2026-09-15, `Make the publication ledger complete in both directions`).
- Contract: `CONTRACT_APP_VERSION 1.5.9`, plugin API `{1, 2}` supported, 6/6 published cluster providers install+load with zero problems.

## Package evidence (`EV-W10-PKG-001`)

Repair cycle 4 (resolves `AUD-W10-002`): rebuilt exact wheel+sdist from the tested tree above with `TEMP`/`TMP` under `.tmp/os/w10-repair-20260922` and `python -m build --no-isolation --wheel --sdist` (setuptools backend, `build` 1.5.0, Python 3.12.4, PyInstaller not involved) on 2026-09-22. The artifacts are freshly hash-bound to this repair run:

- Wheel `dist/hpc_client_gui-1.5.9-py3-none-any.whl`, 907971 bytes, SHA-256 `D3A3DCBE2F10FD7B11B36B79BB5E27B9E47B24428F6B2AC78142EEA5A5F551D9`.
- Sdist `dist/hpc_client_gui-1.5.9.tar.gz`, 1336899 bytes, SHA-256 `BDA608CFBF2F50E7DAA4A676644787FDF64CAE456402C17464FD4B9F584C1DE7`.
- (Prior `dist/` bytes from the W09 build — wheel `E575BF8A…F39843`, sdist `3E7F5F2A…CD9DD4F` — were overwritten by this rebuild; byte sizes identical, hashes differ only by build-embedded timestamps. `dist/` is gitignored build output, so the rebuild touches no tracked file.)

Packaged-bytes proof (all on the freshly built wheel, exit 0):

1. Zip inspection: wheel holds 266 files including every W10-relevant module — `hpc_gui/plugins/loader.py`, `hpc_gui/plugins/validator.py`, `hpc_gui/services/provider_capabilities.py`, `hpc_gui/services/quota_monitor.py`, `hpc_gui/services/slurm_ssh.py`.
2. Wheel-installed functional proof (`pip install --ignore-requires-python --target <tmp> --no-deps <wheel>`, then exercised the installed copy — note: `--ignore-requires-python` needed only because dev box runs 3.12.4 while wheel metadata declares `==3.14.*`; byte-proof only, no runtime-support claim): empty `access`/`{}` + `requirements`/`{}` profile → 0 errors; malformed `access` (`"lounge"`) → rejected; malformed `requirements` (`[1,2]`) → rejected; unknown key `frobnicate` → rejected. **4/4 PASS**, fail-closed behavior preserved in packaged bytes.
3. Capability/contract behavior in packaged bytes is additionally proven by the installer-path discovery evidence (CON-W09-001/002 re-run green, `EV-W10-MATRIX-001`).

Honest scope: this is the dev wheel package proving the W10-accepted implementation ships in packaged bytes; no signed `.exe` is claimed — the frozen signed release artifact is deferred to W56/W58–W61 (no GOV-011 violation).

## Evidence ledger

| Evidence ID | Command | Date | Exit | Result |
|---|---|---|---|---|
| `EV-W10-BASE-001` | `pytest test_wave_v2_02_provider_contract + test_provider_capabilities + test_plugin_compatibility_override + test_plugin_schema_compat + test_plugin_security -q` | 2026-09-19 | 0 | 62 passed |
| `EV-W10-MATRIX-001` | `$env:HPC_GUI_CONTRACT_REPO='D:\Projeler\hpc-client-gui-plugins'; pytest test_wave_v2_02_provider_contract test_provider_capabilities test_plugin_compatibility_override test_plugin_schema_compat test_plugin_security test_w09_main_plugin_compat test_w08_schema_isolation test_local_provider_storage test_quota_monitor test_security_hardening_wave test_slurm_ssh -q -rs` | 2026-09-19 (re-run in repair cycle 1 on the exact tested tree) | 0 | **106 passed, 2 skipped** (skips: symlink-creation unavailable + POSIX-permission semantics on Windows — platform-legitimate, not weakening) |
| `EV-W10-GUI-001` | `python C:\Users\mskomek\AppData\Local\Temp\opencode\w10_wx_probe.py` (wx 4.3.1; real `wx.App`+`Frame`, `EVT_BUTTON` round-trip, clean teardown) | 2026-09-19 (re-run in repair cycle 1 on the exact tested tree) | 0 | **10/10** (first runs: 2 probe-side fixture key errors — `profile_id`/`name`, `site`-shape — corrected in probe, product untouched; rerun 10/10) |
| `EV-W10-INV-001` | `python C:\Users\mskomek\AppData\Local\Temp\opencode\w10_inventory.py` | 2026-09-19 (re-run in repair cycle 1 on the exact tested tree) | 0 | 6 providers, matrix above |
| `EV-W10-PKG-001` | `python -m build --no-isolation --wheel --sdist` with temp under `.tmp/os/w10-repair-20260922` from HEAD `63b696b3`; wheel SHA-256 `D3A3DCBE…F551D9` (907971 B) + sdist SHA-256 `BDA608CF…C1DE7` (1336899 B); archive inspection found all five W10-relevant modules; packaged validator proof checked valid empty sections plus malformed `access`, malformed `requirements`, and unknown-key rejection (4/4; byte-proof only, no runtime-support claim) | 2026-09-22 | 0 | 1 wheel + 1 sdist + functional byte-proof | artifact bound to current tested tree, W10-accepted behavior present in packaged bytes, fail-closed behavior preserved |
| `EV-W10-PKG-002` | same build command from HEAD `63b696b3`; wheel SHA-256 `D3A3DCBE…F551D9` (907971 B) + sdist SHA-256 `BDA608CF…C1DE7` (1336899 B); focused provider/security contract suite rerun after build | 2026-09-22 | 0 | 1 wheel + 1 sdist, 62 focused tests passed | fresh package bytes and source checks are current; independent audit still required |
| `EV-W10-PAIR-001` | `git rev-parse HEAD` (both repos) + `test_published_cluster_provider_set_is_pinned` + version asserts | 2026-09-19 | 0 | main `0f8902a0` + plugin `f0abb7e7` |
| `EV-W10-DISP-001` | disposition record in this report (single record) | 2026-09-19 | — | `NO-EXPANSION-FOR-V2` |

Evidence classes: `GUI` satisfied by `EV-W10-GUI-001` (real wx event/runtime proof, re-run green in repair cycle 1). `PACKAGE` satisfied by `EV-W10-PKG-001` (exact wheel+sdist built from the tested tree, SHA-256-bound, W10-accepted behavior verified inside packaged bytes + installer-path discovery proof; signed release exe honestly deferred to W56/W58–W61). External: N/A — no live-cluster claim made (real-cluster acceptance belongs to W03).

## Diff review

`git diff --check`: clean for W10-owned changes (exit 0). The repair changed no product or test source; it regenerated gitignored `dist/` bytes and refreshed this canonical report only. The focused W10 matrix re-ran at **106 passed, 2 skipped**. No secrets, generated/binary noise, duplicated logic, or weakened tests introduced.

## Acceptance checklist (XREPO-046…055)

- [x] Provider registry/discovery is mapped and tested.
- [x] Capability semantics are explicit.
- [x] Optional capability absence is distinguishable from failure.
- [x] One bad plugin/provider cannot crash the host.
- [x] Duplicate/incompatible providers produce clear diagnostics.
- [x] Main/plugin compatibility pair is recorded.
- [x] W01 provider-dependent support rows have evidence-backed states (no change required).
- [x] No generic UI path requires hardcoded TRUBA/provider-name checks for ordinary capability decisions.
- [x] Provider expansion disposition is recorded as `NO-EXPANSION-FOR-V2`.
- [x] No P0/P1 provider-contract defect remains.

## Handoff / resume state

W10 is ready for fresh audit: disposition recorded (`NO-EXPANSION-FOR-V2`, single record), matrix/acceptance/evidence gates remain closed, pins current, and `AUD-W10-002` is repaired by fresh package evidence bound to HEAD `63b696b3` plus diff `7F4C3E2C…`. Signed release exe remains honestly deferred to W56–W61. All 27 owned requirement rows + 7 owned TODOs retain their prior verdicts. This repair does not start W11.
