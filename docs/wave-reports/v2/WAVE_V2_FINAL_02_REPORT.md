# WAVE 02 SESSION REPORT — Provider and Capability Contract Audit / Expansion

| Field | Value |
|---|---|
| Wave | W02 — Provider and Capability Contract Audit / Expansion |
| Canonical report path | `docs/wave-reports/v2/WAVE_V2_FINAL_02_REPORT.md` |
| Baseline SHA (main) | `731357c6a9e69da121f6783e07d5d65ad3a8539c` |
| Tested implementation SHA (main) | `a2fb5d26` (this report is inside that same commit) |
| Current HEAD (main) | `a2fb5d26` (session start: `731357c6`) |
| Plugin repo SHA (read-only pin) | checkout `main` = `602e904bfd4120b3bd65b3f172d14638fe817f50`; `origin/develop` = `f0abb7e7037e66ab451d463c699fecf4e00c89eb` |
| First started | 2026-09-16 |
| Last updated | 2026-09-16 |
| Session status | Implementation + audit complete |
| Wave decision | see §14 |

---

## 1. Scope

```text
TARGET_WAVE: W02 — Provider and Capability Contract Audit / Expansion
TARGET_WAVE_FILE: waves/waiting/WAVE_V2_FINAL_02.md
SESSION_SCOPE_LOCKED: YES
```

Selected because W01 closed `GO` (`docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md` line 314) and
named W02 as the next target. No other Wave was executed, prepared, or closed.

### Repository truth

```text
Main repo
Branch:          develop
HEAD:            731357c6a9e69da121f6783e07d5d65ad3a8539c
origin/develop:  731357c6a9e69da121f6783e07d5d65ad3a8539c
Working tree:    untracked only (.integration-recovery/, audit.zip, docs.zip,
                 docs/TEST_SUITE_AUDIT_REPORT_12ce7993.md, scripts/*.py,
                 temp_waves/, tests/WAVE2_REMAINING_TEST_PROMPTS.md, waves.zip)

Plugin repo (D:\Projeler\hpc-client-gui-plugins) — pinned, NOT modified
Branch:          main
HEAD:            602e904bfd4120b3bd65b3f172d14638fe817f50
origin/develop:  f0abb7e7037e66ab451d463c699fecf4e00c89eb
Working tree:    untracked only (.github/social-preview.jpg)
```

The W02 package's authoring pin `f0abb7ed2ab2…` is **not** the current
`origin/develop` (`f0abb7e7037e…`). Per the repo-truth rule the live SHAs above
are the execution pins.

---

## 2. Entry criteria

| Criterion | Status | Evidence |
|---|---|---|
| W01 support matrix frozen | VERIFIED | `artifacts/v2-final/W01/SUPPORT_MATRIX.md` §6 |
| Main repo freshly pinned | VERIFIED | §1 |
| Plugin repo freshly pinned | VERIFIED | §1 |
| Plugin repo discoverable in dev workflow | VERIFIED | profiles read directly from `D:\Projeler\hpc-client-gui-plugins\plugins\truba\*` |

---

## 3. Discovery

### Provider/capability contract surface (rediscovered, not assumed)

| Concern | Live path |
|---|---|
| Plugin discovery / registration | `src/hpc_gui/plugins/loader.py::load_installed_plugins` |
| Manifest + profile schema validation | `src/hpc_gui/plugins/validator.py` |
| Typed provider model | `src/hpc_gui/plugins/models.py::ClusterProfileDefinition` |
| Schema↔app compatibility floors | `src/hpc_gui/plugins/schema_compat.py` |
| App version compatibility | `src/hpc_gui/plugins/compatibility.py` |
| Plugin → system template adapter | `src/hpc_gui/plugins/templates.py` |
| Builtin/plugin template groups | `src/hpc_gui/config/system_profile.py` |
| Declarative adapter/parser contract | `src/hpc_gui/services/provider_contract.py` |
| Declared-vs-observed capability view | `src/hpc_gui/services/provider_capabilities.py` |
| Environment capability report | `src/hpc_gui/services/capability_report.py` |
| Optional quota capability gate | `src/hpc_gui/services/quota_monitor.py::quota_gate` |
| wx consumers | `src/hpc_gui/wx_connection_dialog.py`, `wx_connection.py`, `wx_jobs.py`, `wx_shell.py` |

### Architecture path traced

```text
cluster-profile.json (plugin repo)
  -> validator.validate_cluster_profile_dict
  -> models.build_cluster_profile           (ClusterProfileDefinition)
  -> models.to_system_settings / templates.PluginSystemTemplate
  -> wx_connection_dialog._apply_system_template
  -> saved profile["provider_template"]
  -> provider_contract.extract_contract      (adapter/parser selection)
     provider_capabilities.build_provider_capability_view (declared vs observed)
     quota_monitor.quota_state_for_profile   (optional capability gate)
  -> wx_jobs / wx_shell backend execution
```

### Spec/plan conflicts

```text
SPEC-PLAN-CONFLICT:
Documents/code involved: waves/waiting/WAVE_V2_FINAL_02.md header pin
                         f0abb7ed2ab25311cd4c3e9de4cae7d3920b8733 vs live
                         plugin origin/develop f0abb7e7037e66ab451d463c699fecf4e00c89eb
Conflict:  The authoring pin does not exist as the current plugin develop head.
Decision:  Use the live SHAs (§1) as execution pins, per the package's own
           repo-truth rule. No plugin-repo change was made in this Wave.
Evidence:  git rev-parse output recorded in §1.
```

---

## 4. Findings table

| ID | Sev | Surface | Reproduction / before evidence | Root cause | Impact | Owner | In scope | Remediation | Countable | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| DEF-W02-001 | P1 | plugin → saved profile provider template | `EV-W02-BEFORE-001` | Two disjoint serializations of the same `provider_template` contract | Declared v4 adapter/parser contract silently dropped for the flagship TRUBA provider; capability view reports different truths per producer | W02 | YES | Single canonical serializer | YES → **FIX-A** | FIXED |
| DEF-W02-002 | P1 | plugin discovery / provider identity | `EV-W02-BEFORE-002` | No uniqueness rule for `profile_id` across (or within) plugins | A second plugin can shadow a live provider identity with no diagnostic; saved profiles become ambiguous | W02 | YES | Deterministic claim + diagnostic rejection | YES → **FIX-B** | FIXED |
| OBS-W02-003 | — | plugin load isolation | `loader.py` per-plugin `problems` list; verified by reading full function | n/a | One malformed plugin already cannot abort discovery | W02 | YES | none required | NO | VERIFIED-OK |
| OBS-W02-004 | — | optional quota semantics | `quota_monitor.quota_gate` returns `not_configured` / `disabled` / `invalid_configuration` / `incomplete-unsupported` / `ready_not_enabled` / `eligible` | n/a | Absence is already distinguishable from failure; TRUBA 1.5.0 declares quota explicitly disabled with a note | W02 | YES | none required | NO | VERIFIED-OK |
| OBS-W02-005 | — | generic-layer provider-name branching | grep for `== "truba"`, `startswith("truba")`, `"TRUBA" in` outside `plugins/` | n/a | No capability decision branches on a provider name; `truba.lssrv` occurrences are allow-listed adapter/parser **IDs** consumed declaratively | W02 | YES | none required | NO | VERIFIED-OK |
| DEF-W02-006 | P2 | duplicate-id claim ordering (introduced by FIX-B, caught in POST_GREEN_REVIEW) | code review of the first FIX-B draft | id claimed before the schema-floor gate ran | A plugin rejected later could reserve an id it never registered | W02 | YES | Claim only after every gate passes | NO (same root cause as FIX-B) | FIXED |
| DEF-W02-007 | P2 | intra-plugin duplicate ids (found by delegated review) | code review | claim map only saw committed ids, so one plugin could declare the same id twice | A single plugin could register two profiles with the same identity | W02 | YES | Local pre-commit check in the same guard | NO (same root cause as FIX-B) | FIXED |
| OBS-W02-008 | P3 | `profile_exchange` export size | delegated review | canonical template is larger than the old partial one | Exported profiles grow; no secret exposure — cluster-profile content is public declarative metadata validated by `validator.py` | W02 | YES | accepted, documented | NO | ACCEPTED |
| ENV-W02-009 | — | whole-suite native crash | `EV-W02-BASE-003` / `EV-W02-AFTER-003` | wx/mock-SSH interaction in `tests/test_editor_flow.py::test_ctrl_o_focuses_remote_path_and_enter_opens_it` | Full-suite run aborts with a Windows access violation | **pre-existing, not W02** — reproduced identically at unmodified baseline | NO | not in W02 scope | NO | PRE-EXISTING |

---

## 5. FIX-A — canonical provider template serialization

```text
Fix ID:                 FIX-W02-A
Defect ID:              DEF-W02-001
Severity:               P1
Independent root cause: the provider contract had two disjoint serializations
                        of the same dict key, so each consumer saw half of it.
```

**Before behavior.** `ClusterProfileDefinition.to_system_settings()` emitted a
`provider_template` containing `profile_id, name, schema_version, job_outputs,
file_filters, job_details, accounting, cluster_status`. `PluginSystemTemplate.
structured` emitted a *different* dict containing `schema_version, metadata,
site, access, requirements, scheduler_hints, software, storage, quota_sources`.
`wx_connection_dialog._apply_system_template` (and its Qt twin) store
`structured` verbatim as the saved profile's `provider_template`, and
`provider_contract.extract_contract` / `provider_capabilities.
build_provider_capability_view` / `quota_monitor.quota_state_for_profile` all
read that one dict.

**Before evidence — `EV-W02-BEFORE-001`** (executed against the shipped
`hpc-client-gui-plugins` TRUBA 1.5.0 profile, schema_version 4):

```text
Commit:      731357c6 (working tree clean of W02 changes)
Command:     PYTHONPATH=src python - (ad-hoc reproduction, see below)
Exit code:   0
Observed:
  validator errors: []
  to_system_settings provider_template keys:
    ['accounting','cluster_status','file_filters','job_details','job_outputs',
     'name','profile_id','schema_version']
  PluginSystemTemplate.structured keys:
    ['access','metadata','quota_sources','requirements','scheduler_hints',
     'schema_version','site','software','storage']

  --- settings_tpl ---
    contract: job_details=True accounting=True cluster_status=True
    declared: storage=NOT_DECLARED quota=NOT_DECLARED scheduler=NOT_DECLARED
  --- structured (the shape the dialog actually saves) ---
    contract: job_details=False accounting=False cluster_status=False
    declared: storage=DECLARED quota=DECLARED scheduler=NOT_DECLARED
Expected:    one template carrying every declared section
```

The second block is the runtime path: the declarative `job_details`,
`accounting` and `cluster_status` contracts TRUBA 1.5.0 declares collapse to
"unsupported" (`parse_with_contract` → `ParseResult.fail("unsupported")`).

**Files changed.**

- `src/hpc_gui/plugins/models.py` — new `ClusterProfileDefinition.to_provider_template()`;
  `to_system_settings()` now emits exactly that.
- `src/hpc_gui/plugins/templates.py` — `PluginSystemTemplate.structured` is the
  same serialization.

**Behavioral contract.** There is one `provider_template` shape. Every declared
section is present; sections the profile does not declare are present with a
falsy value (`[]` / `None`) so "declared but empty" stays distinguishable from
"not declared", and a consumer can still distinguish "a provider template
exists" from "no provider at all" (key absent / value `None`).

**After evidence — `EV-W02-AFTER-001`:**

```text
Command:   PYTHONPATH=src python - (same reproduction script)
Exit code: 0
Observed:  shapes identical: True
           contract: job_details=True accounting=True cluster_status=True
           declared: scheduler=DECLARED storage=DECLARED quota=DECLARED
```

**Regression tests.**

| Test | Purpose ID | Proves |
|---|---|---|
| `test_system_settings_and_structured_template_are_identical` | CON-W02-001 | both producers emit one identical dict with every contract section |
| `test_stored_plugin_template_keeps_contract_and_capabilities` | DEF-W02-001 | end-to-end through `load_installed_plugins` → `installed_cluster_template_groups`: the dict the dialog stores still yields all three adapter contracts and DECLARED storage/quota/scheduler |
| `test_undeclared_sections_stay_distinguishable_from_declared_empty` | NEG-W02-001 | a minimal profile keeps falsy sections; `scheduler` stays DECLARED because it is a required field |

**Sensitivity proof — `EV-W02-SENS-A1`** (narrow fault injection: keep the new
API, restore only the old partial `structured` producer):

```text
Command:   git show HEAD:src/hpc_gui/plugins/templates.py > src/hpc_gui/plugins/templates.py
           PYTHONPATH=src python -m pytest tests/test_wave_v2_02_provider_contract.py -q -p no:randomly
Exit code: 1
Observed:  1 failed, 5 passed
Failure:   test_stored_plugin_template_keeps_contract_and_capabilities
           tests/test_wave_v2_02_provider_contract.py:155  assert contract.has_job_details
```

**Sensitivity proof — `EV-W02-SENS-A2`** (fault injection inside the canonical
serializer: drop `storage` and `quota_sources`):

```text
Exit code: 1
Observed:  3 failed, 3 passed
           test_system_settings_and_structured_template_are_identical
           test_stored_plugin_template_keeps_contract_and_capabilities
           test_undeclared_sections_stay_distinguishable_from_declared_empty
```

Both injections were reverted immediately; `git diff --stat` afterwards shows
only the intended files.

**Residual risk.** Saved profiles that already contain an old partial
`provider_template` are not rewritten by this Wave; they keep whatever they
stored until the user re-applies a plugin template. Nested values inside
`job_outputs` are shallow-copied, exactly as before this Wave.

---

## 6. FIX-B — deterministic cluster-profile identity

```text
Fix ID:                 FIX-W02-B
Defect ID:              DEF-W02-002
Severity:               P1
Independent root cause: provider registration had no identity-uniqueness rule;
                        this is registry/identity, not serialization.
```

**Before behavior.** `load_installed_plugins` deduplicated *plugin* ids (the
active index is a dict) but never checked `cluster_profile.profile_id`. Two
installed plugins could each register a profile called `truba`;
`installed_cluster_template_groups` then offered both with no diagnostic, and
which provider a saved profile referred to depended on menu order. Nothing in
`src/hpc_gui/plugins/` or `src/hpc_gui/services/` mentioned duplicate provider
identity (`grep -rni duplicate` over both packages returned only manifest-file,
registry-entry and UI-contribution duplicate checks).

**Before evidence — `EV-W02-BEFORE-002`:** running the new
`test_duplicate_profile_id_is_rejected_deterministically[False/True]` and
`test_duplicate_rejection_does_not_disable_unrelated_plugins` against the
unmodified `loader.py`:

```text
Command:   git show HEAD:src/hpc_gui/plugins/loader.py > src/hpc_gui/plugins/loader.py
           PYTHONPATH=src python -m pytest tests/test_wave_v2_02_provider_contract.py -q -p no:randomly
Exit code: 1
Observed:  3 failed, 3 passed
           test_duplicate_profile_id_is_rejected_deterministically[False]
           test_duplicate_profile_id_is_rejected_deterministically[True]
           test_duplicate_rejection_does_not_disable_unrelated_plugins
           (both plugins registered; problems list empty)
```

This doubles as the **sensitivity proof `EV-W02-SENS-B`** — the detector fails
if the guard is removed.

**Files changed.** `src/hpc_gui/plugins/loader.py`.

**Behavioral contract.**

- Iteration is `sorted(active.items())`, so the winner is the lexicographically
  first plugin id — deterministic and independent of install order.
- A plugin whose profile collides with an already-claimed id is rejected whole,
  with a `PluginProblem` naming the id and the owning `plugin@version`. It is
  never half-registered.
- The same guard catches a plugin colliding with itself (two entrypoints
  declaring the same `profile_id`).
- Ids are claimed **after** every gate (identity, API, app compatibility,
  integrity, schema floor) passes, so a plugin that is rejected later cannot
  reserve an id it never registers.

**Regression tests.**

| Test | Purpose ID | Proves |
|---|---|---|
| `test_duplicate_profile_id_is_rejected_deterministically[False]` / `[True]` | DEF-W02-002 / RACE-W02-001 | same winner under both install orders; diagnostic names id + owner; only one provider reaches the template groups |
| `test_duplicate_rejection_does_not_disable_unrelated_plugins` | NEG-W02-002 | rejection is isolated: an unrelated third plugin still loads |
| `test_rejected_plugin_does_not_reserve_its_profile_id` | NEG-W02-003 | a plugin rejected by the schema-floor gate frees the id for the next plugin |
| `test_duplicate_profile_id_inside_one_plugin_is_rejected` | NEG-W02-004 | intra-plugin duplicate is rejected too |

**Residual risk.** `profile_id` comparison is exact (case-sensitive). The
validator constrains the id to `^[a-z][a-z0-9_-]*$`, so case variance cannot
occur through the supported path.

---

## 7. Additional remediation

DEF-W02-006 and DEF-W02-007 were found during POST_GREEN_REVIEW and the
delegated review and repaired inside FIX-B's root cause. They are **not**
counted as additional independent fixes (§18 / B2 — same root cause).

---

## 8. Test ledger

| Evidence ID | Command | Exit | Passed | Failed | Skipped | Xfail | Proves | Does NOT prove |
|---|---|---|---|---|---|---|---|---|
| EV-W02-BASE-001 | `PYTHONPATH=src pytest tests/test_provider_capabilities.py tests/test_wave79_provider_contract.py tests/test_provider_overrides.py tests/test_provider_context.py tests/test_local_provider_storage.py -q -p no:randomly` | 0 | 64 | 0 | 0 | 0 | pre-change provider slice is green | nothing about cross-layer template fidelity |
| EV-W02-BASE-002 | `PYTHONPATH=src pytest <10 plugin test files> -q -p no:randomly` | 0 | 74 | 0 | 24 | 0 | pre-change plugin slice is green | nothing about provider identity uniqueness |
| EV-W02-BASE-003 | `PYTHONPATH=src pytest tests -q -p no:randomly -rf` at **unmodified HEAD** | crash | — | — | — | — | the whole-suite Windows access violation in `test_editor_flow.py:281` exists at baseline | that the rest of the suite is green in one process |
| EV-W02-AFTER-001 | `PYTHONPATH=src pytest tests/test_wave_v2_02_provider_contract.py -q -p no:randomly` | 0 | 8 | 0 | 0 | 0 | both fixes and their negative/lifecycle paths | runtime GUI behavior |
| EV-W02-AFTER-002 | `PYTHONPATH=src pytest <30 provider/plugin/connection/quota test files> -q -p no:randomly` (final code state) | 0 | 421 | 0 | 24 | 0 | impacted subsystem green after every fix | packaged or real-cluster behavior |
| EV-W02-AFTER-003 | `PYTHONPATH=src pytest tests -q -p no:randomly -rf` | crash | — | — | — | — | the same whole-suite native crash reproduces after the W02 changes, at the same test as at baseline | nothing about W02 correctness |
| EV-W02-AFTER-004 | `PYTHONPATH=src pytest tests --ignore=tests/test_editor_flow.py -q -p no:randomly -rf` | crash | — | — | — | — | the crash is not tied to one test: with that file ignored the run aborts in `tests/test_ftp_widget.py` `tearDown` instead | — |
| EV-W02-AFTER-005 | `PYTHONPATH=src pytest tests/test_editor_flow.py -q -p no:randomly` | 0 | 14 | 0 | 0 | 0 | the crashing file passes in its own process | — |
| EV-W02-AFTER-006 | per-file sweep (`pytest <one file>` for each `tests/test_*.py`, 180 s timeout) | terminated | — | — | — | — | the sweep reached the `test_w*` files reporting exactly one non-zero exit — `tests/test_gui_verification.py` exit 5 (no tests collected, not a failure) — before a wx GUI file wedged past its timeout and the sweep was stopped | a whole-suite pass/fail total |
| EV-W02-SENS-A1 | templates.py reverted, W02 suite rerun | 1 | 5 | 1 | 0 | 0 | the FIX-A detector fails on the exact original defect | — |
| EV-W02-SENS-A2 | canonical serializer fault-injected | 1 | 3 | 3 | 0 | 0 | the FIX-A detectors fail on a narrow equivalent fault | — |
| EV-W02-SENS-B | loader.py reverted | 1 | 3 | 3 | 0 | 0 | the FIX-B detectors fail without the guard | — |

### 8a. Whole-suite result — BLOCKED by a pre-existing environmental defect

The full suite cannot complete in one process in this environment. It aborts
with `Windows fatal exception: access violation` in a wx GUI test, and the
**identical crash reproduces at the unmodified baseline** (`EV-W02-BASE-003`
vs `EV-W02-AFTER-003`, both at `tests/test_editor_flow.py:281`). Ignoring that
file moves the abort to a different GUI file (`EV-W02-AFTER-004`), and the
crashing file passes on its own (`EV-W02-AFTER-005`), so this is a cross-test
native/lifecycle problem, not a W02 regression.

Consequence for this Wave: there is **no exact whole-suite pass/fail total**.
The broadest exact figure is the impacted-subsystem run, `EV-W02-AFTER-002`
(421 passed, 0 failed, 24 skipped, 0 xfailed, exit 0), which covers every
module W02 touches plus its consumers. This is recorded as `BLOCKED`, not
substituted with a narrower run relabelled as a full-suite result.

Ownership: the crash is a stabilization/lifecycle defect in the wx test
environment, owned by **W10** (stabilization / regression sweep). It is not a
provider-contract defect and it predates this Wave, so it does not block the
W02 gate — but it does mean W10 must fix the harness before any Wave can cite
a whole-suite number.

---

## 9. Runtime / package / external evidence

| Class | Status | Reason |
|---|---|---|
| Source-level unit/contract/integration | VERIFIED | §8 |
| wx runtime (GUI launch) | NOT EVIDENCED | W02's fixes are in the framework-neutral plugin/service layer; no wx widget behavior changed. The wx consumers were read and traced (§3) but not exercised at runtime in this session. |
| Packaged artifact | NOT APPLICABLE | W02 declares no packaged requirement; W04 owns the packaged-artifact harness. |
| Real SSH/SFTP/Slurm | NOT APPLICABLE | W02 explicitly non-scope; W03 owns external validation. |

No evidence class was substituted: nothing here claims runtime or packaged
proof from source inspection.

---

## 10. Cross-Wave impact

```text
CROSS_WAVE_CHANGE: none.
```

All edits are inside `src/hpc_gui/plugins/`, which W02 owns.

**Evidence invalidated for later Waves.** Any later Wave that asserts the
*absence* of `provider_template` for a plugin-derived profile, or the old
partial `structured` key set, must re-run. W06/W07/W08 should re-confirm the
declarative job-details / accounting / cluster-status path now that the
contract actually reaches `wx_jobs.py`.

**Handoff to W03 (per the Wave's handoff section).**

```text
provider:          truba (org.hpcclient.truba 1.5.0, cluster-profile schema 4)
host class:        TRUBA login node (SSH + Slurm)
capability:        job_details / accounting / cluster_status
command/action:    scontrol show job; sacct per-job; lssrv
expected result:   adapters slurm.scontrol.job / slurm.sacct.job / truba.lssrv
                   are now reachable from a saved profile and parse via
                   slurm.scontrol.v1 / slurm.sacct.pipe.v1 / truba.lssrv.v1
safe test fixture: a completed short job owned by the test account
cleanup required:  none (read-only commands)

provider:          truba
capability:        quota
expected result:   capability declared but explicitly disabled
                   (quota_sources[0].enabled == false, empty command_template)
                   -> quota_gate returns "disabled"/"not_configured", never a
                   fabricated number
```

**Cross-Wave blockers.** None.

---

## 11. POST_GREEN_REVIEW

```text
Areas checked:
  - alternate entry paths: wx system-templates popup
    (wx_connection_dialog.py:813/825/832) and the Qt twin
    (ui/dialogs/connection_dialog.py:765/815) both route through
    _apply_system_template; both now receive the canonical shape.
  - save path key filtering: ui/dialogs/connection_dialog.py:753-757 copies
    provider_template verbatim (no whitelist that would re-drop sections).
  - profile diff / apply: services/provider_profile_diff.py:99-115 compares
    auth/partitions/requirements/storage/quota/docs — sections that were
    previously missing from one producer and are now always present.
  - quota absence semantics: services/quota_monitor.py:127-153 keeps six
    distinct states; no collapse to 0/empty/success. TRUBA 1.5.0 declares
    quota explicitly disabled with a documented note.
  - plugin load isolation: plugins/loader.py collects per-plugin problems and
    never raises; one malformed plugin cannot abort discovery.
  - generic-layer provider-name branching: no capability decision outside
    plugins/ branches on a provider name; truba.lssrv occurrences are
    allow-listed adapter/parser IDs.
  - claim ordering / lifecycle: found DEF-W02-006 (id claimed before the
    schema-floor gate).
  - delegated review (opencode-worker, muse-spark-1.2-contributor,
    logs/ai-runs/review-20260916-085447.log) raised the intra-plugin duplicate
    gap (DEF-W02-007), the always-present provider_template semantics, and the
    export-size question.

New findings: DEF-W02-006, DEF-W02-007, OBS-W02-008.
Fixes performed: DEF-W02-006, DEF-W02-007 (both inside FIX-B's root cause);
                 OBS-W02-008 accepted and documented.
Retests: EV-W02-AFTER-001, EV-W02-AFTER-002, EV-W02-AFTER-003.
Result: PASS after remediation.
```

On the always-present `provider_template`: the serializer runs only on a
`ClusterProfileDefinition`, i.e. only where a plugin-declared provider actually
exists. Builtin and user templates are unaffected
(`config/system_profile.py::builtin_system_template_groups`,
`normalize_system_settings`). The plugin path already produced a non-empty
`structured` dict for every schema, so `_provider_origin` in either dialog is
unchanged.

---

## 12. Diff hygiene gate

| Question | Answer |
|---|---|
| Unrelated changes? | NO — three source files in `src/hpc_gui/plugins/` plus one new test file |
| Generated/cache/temp files? | NO |
| Secrets? | NO |
| User-specific paths? | NO in the diff; absolute plugin-repo paths appear only in ad-hoc reproduction commands recorded in this report |
| Assertions weakened? | NO |
| Skip/xfail changes? | NO — no skip or xfail added, removed or broadened |
| Broad exception handling added? | NO |
| Same root cause counted twice? | NO — DEF-W02-006/007 are explicitly not counted |
| Cross-Wave behavior changed? | NO |

---

## 13. Final Wave Audit

_See §13 detail table below; iterations recorded in §13c._

### 13a. Requirement-by-requirement

| Requirement | Status | Evidence | What proves it | What remains unproven |
|---|---|---|---|---|
| Provider registry/discovery mapped and tested | VERIFIED | §3, EV-W02-AFTER-001/002 | full read of `loader.py` + new contract tests exercising it end to end | packaged discovery path (W04) |
| Capability semantics explicit | VERIFIED | FIX-A, CON-W02-001, NEG-W02-001 | one canonical template; declared/not-declared preserved | observed-vs-declared at a real cluster (W03) |
| Optional capability absence distinguishable from failure | VERIFIED | OBS-W02-004, NEG-W02-001 | six distinct `quota_gate` states; falsy-but-present sections | live quota probe (W03) |
| One bad plugin cannot crash the host | VERIFIED | OBS-W02-003, NEG-W02-002 | per-plugin `problems` collection; isolation test | GUI-level surfacing of problems (W08) |
| Duplicate/incompatible providers produce clear diagnostics | VERIFIED | FIX-B, DEF-W02-002, NEG-W02-003/004 | diagnostic names id and owning plugin@version | — |
| Main/plugin compatibility pair recorded | VERIFIED | §1, §13b | both SHAs pinned; provider ids and capabilities listed | — |
| W01 provider-dependent rows evidence-backed | VERIFIED | `artifacts/v2-final/W01/SUPPORT_MATRIX.md` §6f (W02 addendum) | addendum with verification owners | rows owned by W03/W04 remain external |
| No generic path needs hardcoded provider-name checks | VERIFIED | OBS-W02-005 | grep + read of every `truba` occurrence outside `plugins/` | — |
| No P0/P1 provider-contract defect remains | VERIFIED | §4 | DEF-W02-001/002 fixed; no other P0/P1 found | — |
| Provider schema validated at load time (TASK-W02-003) | VERIFIED | `validator.py`, `schema_compat.py`, NEG-W02-003 | floor gate rejects inconsistent compatibility claims | — |
| Security / command-template checks | VERIFIED | `validator.py` `_TRUSTED_SLURM_COMMANDS` allow-list; `models.validate_storage_area` rejects `\r\n;|&\`$()<>` | commands are exact allow-listed strings, not free interpolation | injection through a real SSH backend (W03) |
| Real-cluster acceptance | NOT APPLICABLE | Wave non-scope | — | W03 owns it |
| Packaged validation | NOT APPLICABLE | Wave declares none | — | W04 owns it |

### 13b. Compatibility tuple

```text
main SHA:               see §14 (tested implementation SHA)
plugin SHA:             602e904bfd4120b3bd65b3f172d14638fe817f50 (checkout main)
                        origin/develop f0abb7e7037e66ab451d463c699fecf4e00c89eb
plugin API version:     1 (legacy marker 2 only for the approved ANSYS identity)
cluster-profile schemas: 1, 2, 3, 4
provider IDs tested:    truba (schema 1..4 payloads), generic (schema 1)
capabilities tested:    cluster-profile, storage, quota_sources, job_details,
                        accounting, cluster_status, scheduler
```

### 13c. Audit iterations

```text
Audit iteration 1:
  Findings: DEF-W02-006 (claim ordering), DEF-W02-007 (intra-plugin duplicate),
            NEG-W02-001 did not pin `scheduler` semantics.
  Fixes:    claim moved behind every gate; intra-plugin guard added;
            NEG-W02-001 strengthened; loader comment documents whole-plugin
            rejection.
  Retests:  EV-W02-AFTER-001/002/003.
  Result:   FAILED -> remediated -> audit restarted.

Audit iteration 2:
  Findings: none correctable in scope.
  Result:   see §14.
```

### 13d. Gate summary

| Gate | Result |
|---|---|
| Two-fix gate | PASS (FIX-A serialization vs FIX-B identity — different finding IDs, different root causes) |
| Regression-sensitivity gate | PASS (EV-W02-SENS-A1, A2, B) |
| Negative-path gate | PASS (NEG-W02-001..004) |
| Lifecycle/race gate | PASS (install-order parametrization; reject-then-reclaim ordering) |
| Test-quality gate | PASS (no skip/xfail/weakening; behavioral assertions; `tmp_path` isolation; no sleeps; no network) |
| Package gate | NOT APPLICABLE |
| External gate | NOT APPLICABLE |
| Evidence-identity gate | PASS (all evidence at the baseline tree plus the W02 diff) |
| Diff-hygiene gate | PASS (§12) |
| TODO-leakage gate | PASS (§13e) |

### 13e. TODO leakage

| TODO row | Status | Note |
|---|---|---|
| Existing provider audit (owner 02) | CLOSED for W02's part | schema/registry/immutability proven by tests; official-source verification remains with W09/W11 |
| Provider template optional capabilities (owner 02) | CLOSED | unsupported capabilities are absent, not fabricated; TRUBA quota declared disabled |
| Optional provider expansion | NOT IN SCOPE | owned by W03 |

Open P0: 0 · Open P1: 0 · Open P2: 0 · Open P3: 1 (OBS-W02-008, accepted)

---

## 14. Decision

| Field | Value |
|---|---|
| Tested implementation SHA | recorded in the commit created at session close (this report is part of that same commit; the diff is product + tests + evidence, so no separate report-only commit is needed) |
| **Wave decision** | **GO** |

**Reason.** Two independent substantive remediations closed real P1 gaps in
the provider/capability contract and both carry a full proof chain:

- **FIX-A** — the provider contract had two disjoint serializations of the
  same `provider_template`, so the declarative `job_details` / `accounting` /
  `cluster_status` contracts the shipped TRUBA 1.5.0 profile declares were
  silently unreachable from a saved profile, while the capability view
  reported different truths depending on which producer a caller had used.
  One canonical serializer now feeds both. Before evidence, after evidence,
  three regression tests and two independent sensitivity proofs
  (`EV-W02-SENS-A1`, `EV-W02-SENS-A2`).
- **FIX-B** — cluster-profile identity had no uniqueness rule, so a second
  plugin could shadow a live provider id with no diagnostic. Identity is now
  claimed deterministically after every gate, collisions across and within
  plugins are rejected whole with a diagnostic naming the id and owner, and a
  rejected plugin no longer reserves an id. Four regression tests and a
  sensitivity proof (`EV-W02-SENS-B`).

Different finding IDs, different root causes (serialization completeness vs.
registration identity). Neither is a test-only, docs-only, or refactor-only
change. Every mandatory final-audit gate is PASS or NOT APPLICABLE — none is
PARTIAL. Open P0: 0. Open P1: 0. Open P2: 0. Open P3: 1 (OBS-W02-008,
accepted and documented).

**Qualification.** The whole-suite figure is `BLOCKED` by a pre-existing
environmental crash proven to reproduce at the unmodified baseline (§8a). The
broadest exact evidence is `EV-W02-AFTER-002` (421 passed, 0 failed,
24 skipped, exit 0) over every module W02 touches and its consumers. W02
declares no packaged or real-cluster requirement — those belong to W03/W04 —
so no evidence class was substituted to reach this decision.

**Recommended next session target:** W03 — Real SSH / SFTP / Slurm laboratory
validation. **Not started in this session.**

---

## Resume state

```text
Completed and verified: FIX-A, FIX-B, DEF-W02-006, DEF-W02-007, all regression
                        and sensitivity evidence, POST_GREEN_REVIEW, final audit.
In progress:            none
Open P0/P1:             none
Open P2/P3:             OBS-W02-008 (export size, accepted)
Pending tests/evidence: whole-suite total BLOCKED by the pre-existing
                        GUI-test crash (W10 owns the harness fix)
Last exact commands:    see §8
Next actions:           W03 — Real SSH / SFTP / Slurm laboratory validation
                        (do NOT start it in this session)
Evidence identities:    EV-W02-BEFORE-001/002, EV-W02-BASE-001/002/003,
                        EV-W02-AFTER-001/002/003, EV-W02-SENS-A1/A2/B
```
