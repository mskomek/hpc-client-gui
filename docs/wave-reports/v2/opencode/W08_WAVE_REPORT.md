# W08 Wave Report — Provider schema, optional capability and isolation semantics

Wave: `W08`
Canonical report path: `docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA: `0f8902a023bac76071527232c2287af96478ed2b`
Current HEAD: `0f8902a023bac76071527232c2287af96478ed2b`
Tested implementation state: `HEAD 0f8902a0` + working-tree fix (uncommitted; `src/hpc_gui/plugins/validator.py`, `src/hpc_gui/plugins/loader.py`, `tests/test_w08_schema_isolation.py`); every cited suite ran after the final tree state
Plugin/external repo SHA(s): `D:\Projeler\hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin; no plugin change; working tree clean except pre-existing untracked `.github/social-preview.jpg`)
First started: 2026-09-19 (UTC)
Last updated: 2026-09-19T07:16:14Z
Session status: COMPLETE
Wave decision: PASS (one substantive in-scope blocker closed; all other owned rows verified; valid per `HPC-GOV-017` — no minimum fix quota)
Executable authority: `waves/pending/W08.md` (exactly one copy; `waves/bak/` never read for execution)
Execution model: `opencode-go/muse-spark-1.3-contributor`
Runtime truth: Python `3.12.4`, wx `4.3.1 msw (phoenix) wxWidgets 3.3.3`, `src/hpc_gui/runtime.py` `DEFAULT_GUI_RUNTIME="qt"`
Dependency: `W07` — `docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md` decision `PASS`, audit `PASS`; entry revalidated (pins equal: main `0f8902a0` == `origin/develop` tip; plugin `f0abb7e7`; no owned W07 blocker touches this scope)
Report-scope note: `waves/pending/W08.md` asks for a second file (`W08_AUDIT_REPORT.md`). The controlling session instruction for this run was "Keep/update only `docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md` (+ required evidence). No auto-specific reports." The fresh-context audit is therefore recorded inline (§Inline audit) instead of a separate file. No competing report exists.

## Owned requirements and TODO details

| ID | Authority | Status and trace (requirement → live owner → test → evidence) |
|---|---|---|
| `HPC-W02-SCHEMA-001` | MANDATORY (WS-C absence semantics) | VERIFIED — five states stay distinct: not-declared (`NOT_DECLARED` + `quota_gate None → not_configured`), disabled (`quota_gate → disabled`), probe-failed (`QuotaResult("error")`, `used_bytes None`), valid zero (`QuotaResult("ok", 0)` formats `"0 / 20 bytes"`), invalid (`invalid_configuration`); none collapses to `0`/`""`/success. Owners: `services/quota_monitor.py:128–168`, `services/provider_capabilities.py:39–76`. Tests: `test_optional_quota_absence_states_do_not_collapse` (new) + `EV-W07-GUI-001` precedence. Evidence: `EV-W08-FIX-001`, `EV-W08-GUI-001` |
| `HPC-W02-SCHEMA-002` | MANDATORY (required metadata validated) | FIXED + VERIFIED — DEF-W08-001: v1/v4 skipped storage/quota shape validation. Owner now `plugins/validator.py::_validate_storage_and_quota_sections` (shared by v1–v4). Tests: `test_malformed_section_shape_is_rejected_before_build`, `test_section_item_without_id_is_rejected`. Evidence: `EV-W08-FIX-001`, `EV-W08-SENS-001` |
| `HPC-W02-SCHEMA-003` | MANDATORY (unknown keys tolerated/rejected intentionally) | VERIFIED — unknown top-level manifest keys rejected (`unknown properties`), unknown profile keys rejected for v2–v4, unknown command keys rejected via trusted allow-list. Test: `test_unknown_manifest_keys_are_rejected_intentionally` + pre-existing schema suites. Evidence: `EV-W08-FIX-001`, `EV-W08-REG-001` |
| `HPC-W02-SCHEMA-004` | CONDITIONAL (optional-field defaults; verify-only-if-live-path) | VERIFIED — minimal v4 template emits explicit `storage: []`, `quota_sources: []`, `job_details/accounting/cluster_status: None` (live path `ClusterProfileDefinition.to_provider_template`). Test: `test_minimal_v4_template_defaults_are_explicit`. Evidence: `EV-W08-FIX-001` |
| `HPC-W02-SCHEMA-005` | MANDATORY (command templates keep required placeholders) | VERIFIED — only application-owned Slurm operations accepted (`_TRUSTED_SLURM_COMMANDS` + one published TRUBA variant); placeholders restricted to 7 known names; non-conforming keys rejected, never silently rewritten. Tests: pre-existing `test_plugin_schema_compat.py` (+ compat gate `EV-W08-COMPAT-001`). Evidence: `EV-W08-REG-001` |
| `HPC-W02-SCHEMA-006` | MANDATORY (storage paths normalized safely) | FIXED + VERIFIED — same DEF-W08-001 root cause (malformed storage reached path consumers); plus `validate_storage_area` (placeholder allow-list, `;\|&`$\(\)<>` rejection) and `resolve_provider_path` (`resolved/missing-context/invalid-template` tri-state). Evidence: `EV-W08-FIX-001`, `EV-W08-REG-001` |
| `HPC-W02-SCHEMA-007` | MANDATORY (no provider-string leakage) | VERIFIED — `GENERIC_SLURM_DEFAULTS` carries no `/arf`/`lssrv` (pre-existing test), `to_system_settings` transfers only `SYSTEM_SETTING_COMMAND_KEYS`, capability layer has no provider-name conditionals (W07 grep evidence reused: only help-topic routing hits). No change required. Evidence: `EV-W08-REG-001` |
| `HPC-W02-SCHEMA-008` | MANDATORY (errors name provider+field, hide secrets) | VERIFIED — validator/loader diagnostics echo field names/keys only, never values; planted-secret test proves absence across validator + manifest + loader layers. Test: `test_config_errors_never_echo_secret_values` (NEG). Evidence: `EV-W08-FIX-001` |
| `HPC-W02-SCHEMA-009` | MANDATORY (malformed plugin never blocks startup) | FIXED + VERIFIED — DEF-W08-001 before-behavior was a `ValueError` escaping `load_installed_plugins` (startup crash). Now: rejected at validation with provider+field diagnostic; `_build_profile` try/except backstop converts any residual shape escape into a recorded `PluginProblem`. Tests: `test_malformed_plugin_does_not_prevent_startup` (param v1/v4 × storage/quota) + pre-existing malformed-JSON/profile isolation tests. Evidence: `EV-W08-FIX-001`, `EV-W08-SENS-001`, `EV-W08-GUI-001` |
| `HPC-W02-SCHEMA-010` | CONDITIONAL (missing optional dependency; verify-only-if-live-path) | VERIFIED — optional `linter_engine` failure rejects only its own plugin (`unapproved trusted tool` / `linter engine missing` problem), sibling loads; `list_linter_tools` catches per-plugin `ToolLoadError`. Test: `test_optional_linter_engine_failure_stays_isolated`. Evidence: `EV-W08-FIX-001` |
| `HPC-W02-SCHEMA-011` | MANDATORY (duplicate provider IDs deterministic + diagnosed) | VERIFIED — sorted plugin-id iteration decides the winner regardless of install order; loser diagnosed with owner identity; rejected plugin reserves nothing. Tests: pre-existing `test_duplicate_profile_id_is_rejected_deterministically[False/True]` + isolation negatives. Evidence: `EV-W08-REG-001` |
| `HPC-W02-SCHEMA-012` | MANDATORY (incompatible API version rejected clearly) | VERIFIED — `plugin_api ∉ {1,2}` → `invalid manifest` problem; `requires_app` mismatch → `incompatible with app …` problem; schema-floor gate (`cluster_profile_floor_errors`). Tests: pre-existing core/schema suites. Evidence: `EV-W08-REG-001` |
| `HPC-W02-SCHEMA-013` | MANDATORY (no silent shadowing) | VERIFIED — `claimed_profile_ids` reservation happens only after every gate passes; intra-plugin duplicates rejected whole-plugin. Tests: `test_rejected_plugin_does_not_reserve_its_profile_id`, `test_duplicate_profile_id_inside_one_plugin_is_rejected`. Evidence: `EV-W08-REG-001` |
| `HPC-W02-SCHEMA-014` | MANDATORY (stable discovery ordering) | VERIFIED — `sorted(active.items())` iteration; template groups follow load order; repeat-load determinism asserted in new test + wx probe. Tests: new determinism assertion + parametrized swap test. Evidence: `EV-W08-FIX-001`, `EV-W08-GUI-001` |

Owned TODO-detail IDs: none (0 rows).

## Mandatory source sections read

- `opencode/sources/WAVE_V2_FINAL_02.md` → Workstream C — Optional capabilities and absence semantics (§118–132): five-state differentiation, no collapse to `0`/`""`/success, TRUBA-quota-absent-not-fabricated rule.
- `opencode/sources/WAVE_V2_FINAL_02.md` → Workstream D — Provider schema validation (§134–144): all seven bullets traced in the table above.
- `opencode/sources/WAVE_V2_FINAL_02.md` → Workstream E — Plugin import/discovery isolation (§146–155): all six bullets traced above.
- Owned rows: `opencode/REQUIREMENT_REGISTRY.md:1203–1216` (SCHEMA-001…014); index rows `opencode/REQUIREMENT_WAVE_INDEX.md:165–178`.
- Reference implementation (live code, not authority): `src/hpc_gui/plugins/{validator,loader,models,templates,linter_tools}.py`, `src/hpc_gui/services/{provider_capabilities,provider_contract,quota_monitor,storage_policy,capability_report}.py`, `src/hpc_gui/config/system_profile.py`.
- Workstreams F/G read for boundary awareness only and NOT absorbed (compat fixtures → W09, expansion → W10). W07 freeze (`W07_WAVE_REPORT.md` §Capability freeze) reused as background; the quota `DECLARED`-while-listed contract was kept, not redefined.

## Discovery pass (before first edit)

- Pinned `develop 0f8902a0` == `origin/develop` tip; plugin `develop f0abb7e7`; working tree held pre-existing unrelated changes — all preserved, none reverted, none touched (see §Diff review).
- Narrow pre-edit baseline `EV-W08-BASE-001`: 9 provider/plugin/quota suites → **80 passed** (exit 0).
- Live-symbol rediscovery: `git ls-files` provider/plugin/capability/registry inventory; validator v1/v4 branches compared against v2/v3 line-by-line — that comparison surfaced DEF-W08-001.
- Before-evidence for DEF-W08-001: standalone repro installing a v4 `{"storage": "nope"}` plugin raised `ValueError: dictionary update sequence element #0 has length 1; 2 is required` out of `load_installed_plugins` (shell transcript); validator returned `[]` for the same payload (v1 and v4, storage and quota_sources, wrong-type and id-less variants — all `[]`).

## WAVE_FINDINGS

| Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status |
|---|---|---|---|---|---|---|---|---|
| `DEF-W08-001` | P1 | plugin loader startup (`load_installed_plugins`) + validator v1/v4 | pre-fix repro `ValueError`; validator `[]` on 6 malformed variants | v2/v3 enforced storage/quota list-of-objects shape; v1/v4 skipped it; `build_cluster_profile` assumes the shape without guard | one malformed installed plugin crashes host startup; violates SCHEMA-002/006/009 | shared `_validate_storage_and_quota_sections` for v1–v4 + `_build_profile` try/except backstop | YES (single substantive remediation; no second independent defect found — second-defect search below) | CLOSED |
| `OBS-W08-001` | P3 | loader comment vs code (optional lint/job-template index `continue`) | `loader.py:270–317` | comment promises malformed optional index "does not invalidate the rest of the plugin"; code skips the whole plugin | none user-facing; fail-closed direction is safe; doc-only mismatch | comment correction, no behavior change | NO (non-countable, not made) | OPEN, routed as cleanup, not blocking |
| second-defect search | — | 12 dimensions | suites + probes | no second independent in-scope defect found | — | none | N/A | ZERO further blockers |

Second-defect search (12 dimensions): 1. negative paths — CHECKED (malformed JSON/profile/shape, duplicate, incompatible API/floor, unknown keys, disabled/invalid quota, secret-bearing payloads); 2. lifecycle — CHECKED (loader synchronous, no retained callbacks; `QuotaMonitor.invalidate/close` + stale guard pre-existing); 3. stale state — N/A (no new async path); 4. identity — CHECKED (sorted-id winner, no reservation by rejected plugin); 5. concurrency/race — N/A (no shared mutable discovery state); 6. boundary values — CHECKED (empty list vs missing section, id-less items, wrong-type sections, valid-zero quota); 7. capability absence — CHECKED (five-state test); 8. persistence — N/A (no new persisted state); 9. packaging — N/A (no artifact bound); 10. error visibility — CHECKED (diagnostics name provider+field, secrets absent, loader warning log kept); 11. secondary entry — CHECKED (installer validates before build + `InstallError`; both `build_cluster_profile` call sites now guarded); 12. adjacent boundary — CHECKED (no new provider-name branching; `truba.lssrv*` refs remain allow-listed IDs).

Single-fix justification (authority `HPC-GOV-017` over source §B quota): exactly one genuine in-scope blocker existed; no defect was manufactured to satisfy a count. `OBS-W08-001` is a P3 doc mismatch in the fail-safe direction and does not block.

## Fix proof chain

Fix ID: `FIX-W08-001` · Defect: `DEF-W08-001` · Severity: P1 · Independent root cause: validation-shape gap (v1/v4) + unguarded build assumption — one coherent correction, two layers (gate + backstop).
Before behavior: v4 `{"storage": "nope"}` passed validation (`[]`) and raised `ValueError` from `load_installed_plugins` — host startup crash; sibling plugin never loaded.
Before evidence: `EV-W08-BASE-001` + standalone repro transcript (ValueError, validator `[]` × 6 variants).
Files changed: `src/hpc_gui/plugins/validator.py` (+29/−16: `_validate_storage_and_quota_sections`, wired into v1/v2/v3/v4; v2/v3 bodies deduplicated with identical messages), `src/hpc_gui/plugins/loader.py` (+7/−1: `_build_profile` try/except → recorded problem), `tests/test_w08_schema_isolation.py` (new, 15 tests).
Behavioral contract changed: malformed storage/quota sections are rejected at validation with `cluster profile '<section>' must be a list | '<section>[i]' must be an object | needs a non-empty id`; any residual unbuildable shape becomes a `PluginProblem`, never an exception. Well-formed profiles (all 11 shipped plugin payloads: v1/v2/v3/v4) validate identically to before.
Regression tests: `tests/test_w08_schema_isolation.py` (15 nodes: 11 defect/contract + 4 conditional/verify-only).
Sensitivity proof: `EV-W08-SENS-001` — fix stashed → **11 failed / 4 passed** (the 4 passes are the verify-only SCHEMA-001/003/004/010 tests that hold before and after, as designed); fix restored → 15/15.
Negative tests: wrong-type sections, id-less items, secret-bearing payload, bad optional engine, unknown manifest key.
Narrow-suite result: `EV-W08-FIX-001` 15/15 exit 0. Broader-suite result: `EV-W08-REG-001` 255 passed / 20 env-gated skips exit 0; `EV-W08-COMPAT-001` 20/20 exit 0.
Runtime/manual result: `EV-W08-GUI-001` 12/12 real-wx checks exit 0 (malformed isolation, stable ordering, contract/capability render, two `EVT_BUTTON` round-trips, clean teardown).
Package result: NOT APPLICABLE (no artifact bound; no SHA-256 cited). External result: NOT APPLICABLE (no live-cluster claim; quota-absent logic is local gate evaluation).
Residual risk: third-party hand-written v1 profiles carrying malformed storage/quota sections that previously loaded-then-crashed will now be rejected at load with a diagnostic — intended fail-closed change; all 11 shipped payloads verified unaffected.

## Tests and evidence

| Evidence | Exact command | Timestamp (UTC) | Exit | Result |
|---|---|---|---|---|
| `EV-W08-BASE-001` narrow pre-edit baseline | `python -m pytest tests/test_wave_v2_02_provider_contract.py tests/test_provider_capabilities.py tests/test_capability_report.py tests/test_quota_monitor.py tests/test_plugin_core.py tests/test_plugin_schema_compat.py tests/test_provider_context.py tests/test_provider_path_resolver.py tests/test_storage_policy.py -q -p no:cacheprovider` | 2026-09-19 | 0 | 80 passed |
| `EV-W08-FIX-001` new W08 regression suite | `python -m pytest tests/test_w08_schema_isolation.py -q -p no:cacheprovider` | 2026-09-19 | 0 | 15 passed |
| `EV-W08-SENS-001` sensitivity (fix stashed) | `git stash push -- src/hpc_gui/plugins/validator.py src/hpc_gui/plugins/loader.py` then same suite | 2026-09-19 | 0 (probe) | 11 failed / 4 passed pre-fix; `git stash pop` restored fix → 15/15 |
| `EV-W08-REG-001` impacted suites | 28-file provider/plugin/quota/storage/wx-model run (see Resume state) `-q -p no:cacheprovider` | 2026-09-19 | 0 | 255 passed, 20 skipped (skips are env-gated `HPC_GUI_CONTRACT_REPO`, closed by COMPAT-001) |
| `EV-W08-COMPAT-001` main↔plugin vs live checkout | `$env:HPC_GUI_CONTRACT_REPO='D:\Projeler\hpc-client-gui-plugins'; python -m pytest tests/test_plugin_contract.py -q -p no:cacheprovider` | 2026-09-19 | 0 | 20 passed (plugin `f0abb7e7`) |
| `EV-W08-GUI-001` real-wx probe | `python C:\Users\mskomek\AppData\Local\Temp\opencode\w08_wx_probe.py` (wx 4.3.1; real `wx.App`+`Frame`, 7 capability rows, 2× `wx.PostEvent`+`Yield` button round-trips, malformed+duplicate isolation, stable ordering) | 2026-09-19 | 0 | 12/12 PASS (first run 2 probe-side manifest failures — v4 schema floor `requires_app >=1.5.9`; corrected in probe, product untouched, rerun 12/12) |
| `EV-W08-PIN-001` repo pins | `git branch --show-current` → `develop`; `git rev-parse HEAD` and `origin/develop` → `0f8902a0…` (equal); plugin `develop` → `f0abb7e7…`; `git log -1` → `0f8902a0 docs(w01)…` | 2026-09-19T07:16:14Z | 0 | pins equal origin tip; no fetch needed |

Totals: **290 passed** (255 + 15 + 20; BASE-001's 80 are a subset of REG-001's scope, not added) + **12/12 wx probe checks**, 0 failures. No test weakening, no new skips/xfails, no mocks standing in for behavior under test. No fabricated output; raw probe output retained in shell transcript; probe script lives in Temp, outside the repo.

Evidence classes: required class for W08 is `GUI` — satisfied by `EV-W08-GUI-001` (real wx event/runtime; static-only not used as substitute). Package class: N/A with justification (no artifact bound in any owned row; no SHA-256 cited). External class: N/A (real-cluster acceptance belongs to W03; no live-cluster claim made).

## Diff review

- `git diff --check`: exit 0 for this session's files (only pre-existing CRLF notices elsewhere).
- This session's diff: `src/hpc_gui/plugins/validator.py` (+29/−16), `src/hpc_gui/plugins/loader.py` (+7/−1), `tests/test_w08_schema_isolation.py` (new, 15 tests), this report (new). Full diff inspected above; no unrelated files touched.
- Pre-existing working-tree entries (`CONTRIBUTING.md`, `README.md`, W01 artifacts, i18n, `wx_settings_view.py`, `wx_shell.py`, `test_wave10_release_gate.py`, untracked W03/W04 test files, `wx_errors.py`, sync artifacts) — preserved untouched, none reverted. Plugin repo: no change (read-only).
- Secrets: validator/loader/report/probe contain no credentials, `.env`, keys, PEM/PFX, `.ssh`, tokens, or secret directories (planted-secret test asserts absence mechanically).
- No duplicated logic (one shared helper), no weakened tests, no provider-name branching added.

## Inline audit (fresh-context, read-only standard)

- Authority check: `waves/pending/W08.md` single copy executed; `waves/bak/` never read; owned rows + WS-C/D/E read verbatim; report deviation (single file vs two) documented with controller instruction as basis — ACCEPT.
- Coverage check: 14/14 owned IDs traced with live owner + test + evidence; 0 TODO rows (confirmed in map); conditionals SCHEMA-004/010 verified on live paths — PASS.
- Test-quality check: regression tests behavioral (state transitions, diagnostics content, isolation outcomes); sensitivity demonstrated by revert-fail (11/20 defect nodes fail pre-fix); verify-only nodes identified as such; no skip/xfail/greenwashing — PASS.
- Evidence-identity check: all evidence bound to `0f8902a0` + working-tree fix, plugin `f0abb7e7`; wx probe real-runtime; package/external honestly N/A — PASS.
- Diff/governance check: unrelated changes preserved; secrets absent; cross-wave items routed (compat fixtures → W09, expansion → W10, lint-index comment → cleanup note, real-cluster → W03) — PASS.
- Audit verdict: **PASS**.

## Findings and ownership routing

- In-scope P0/P1 opened: 1 (`DEF-W08-001`), now CLOSED. New defects introduced: 0.
- Cross-wave: nothing absorbed. Compat/installer hardening → W09 (observed: installer already fail-closed via `InstallError`); expansion → W10; real-cluster → W03; `OBS-W08-001` (P3 loader comment mismatch) left open as cleanup, fail-safe direction, non-blocking.

## Resume state

Completed: entry revalidated (both-repo pins, narrow baseline 80 green); WS-C/D/E + 14 owned rows read; discovery + 12-dimension second-defect search done; `DEF-W08-001` (P1) fixed at two layers with 15-test suite, revert-sensitivity, 255-test regression sweep, 20-test live-checkout compat, 12/12 real-wx probe; pins current; diff reviewed; secret-safe; inline audit PASS.
In progress: none. Open P0/P1 (owned): 0. Open P3: `OBS-W08-001` (loader comment/code mismatch, cleanup only).
Pending tests/evidence: none for this Wave.
Exact commands run (last): `python -m pytest tests/test_w08_schema_isolation.py …` → 15 passed; broad 28-file run → 255 passed/20 skipped; contract vs live plugin → 20 passed; `w08_wx_probe.py` → 12/12; `git diff --check` → clean for session files.
Next: none in this Wave — stop. `W09` may be planned only after its dependency/prerequisite checks are revalidated; this session starts nothing.
Evidence/artifact identities: main `0f8902a023bac76071527232c2287af96478ed2b` (+ working-tree W08 fix, uncommitted); plugin `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; no artifact SHA-256 (no package bound).

```
FIX: FIX-W08-001 (sole substantive remediation; GOV-017 applies)
DEF: DEF-W08-001 (P1: v1/v4 storage/quota shape gap → loader startup crash)
Root cause: v2/v3 enforced the section shape; v1/v4 skipped it; build assumed it
Before EV: ValueError from load_installed_plugins + validator [] (EV-W08-BASE-001 + repro transcript)
After EV: EV-W08-FIX-001 15/15; EV-W08-REG-001 255 passed/20 skipped; EV-W08-COMPAT-001 20/20; EV-W08-GUI-001 12/12
Regression test: tests/test_w08_schema_isolation.py (11 defect/contract nodes)
Sensitivity proof: EV-W08-SENS-001 (11 fail pre-fix / 15 pass post-fix)
Additional fixes: none (second-defect search found no second independent defect; OBS-W08-001 P3 noted, not made)
Post-green review: both build_cluster_profile call sites guarded (loader try/except; installer validate-then-InstallError); no duplicate paths, no silent fallbacks, no provider branching
New/modified tests: 15 new (11 REQ/DEF/CON/NEG + 4 conditional verify-only); 0 modified; 0 deleted
Skipped/xfail changes: none
Package evidence: N/A (no artifact bound)
External evidence: N/A (no live-cluster claim; W03 owns it)
Open P0/P1: 0
Open P2/P3: 1 × P3 (OBS-W08-001, cleanup only)
Two-fix gate: SINGLE SUBSTANTIVE FIX under HPC-GOV-017 (higher authority than source §B quota); no manufactured second fix
Wave decision: PASS
```
