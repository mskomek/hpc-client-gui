# W30 — Job submit and cancel control paths - Wave Report

```text
Wave: W30
Canonical report: docs/wave-reports/v2/opencode/W30_WAVE_REPORT.md
Repository: hpc-client-gui / develop
Branch: develop
Baseline SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Tested implementation: working tree at 3e9635ba + W30-owned hunks
  (src/hpc_gui/services/job_submit_cancel.py [new],
   src/hpc_gui/wx_shell.py [submit validation + confirmed acceptance],
   src/hpc_gui/wx_jobs.py [cancel capability/result/refresh/race handling
    + _wx_jobs_cancel exposure + cancel state init + optional event],
   tests/test_w30_submit_cancel.py [new, 15 tests])
  Plus pre-existing uncommitted hunks (preserved, not owned by W30):
   src/hpc_gui/i18n/en.json + tr.json [W27-owned, 8 lines each],
   src/hpc_gui/services/slurm_models.py [W28-owned],
   src/hpc_gui/services/files_ssh.py + output_follower.py [W29-owned],
   src/hpc_gui/wx_editor_view.py [W26/W27-owned, 306 lines],
   src/hpc_gui/wx_plugins_view.py [W26-owned],
   src/hpc_gui/wx_jobs.py W28/W29-owned hunks [refresh machine, filter/sort,
     identity double gate, per-channel output errors - preserved],
   src/hpc_gui/services/job_identity.py + job_list_filter_sort.py +
   jobs_refresh_state.py [untracked, W28-owned],
   tests/test_w26_run_supplement.py + tests/test_w27_editor_conflicts.py +
   tests/test_w28_jobs_identity_refresh.py + tests/test_w29_job_outputs.py
   [untracked, sibling-owned]
Current HEAD: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Content handoff: controller content_identity
  af624903826152a21cd6afee62c1e4d0c2a01fb9e8441e0110ed5d18f5eb7067
  (phase=run handoff; matches W29 audit receipt tested identity chain)
Observed waves/pending/W30.md SHA-256 (BOM-stripped, LF-normalized bytes):
  389ed6ab0464a60811bc66e7c4f001536f8f783075a183e84bda9d20eb893ccb
  (frontmatter wave_id/wave_kind/canonical_source/10 owned IDs/
   aggregate_close_owner=false/evidence_policy=wave-local/
   audit_policy=fresh-independent verified consistent)
Execution start gate: NONE (per Wave independence contract)
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: READY_FOR_AUDIT (independent audit pending, controller-owned)
```

## Scope

W30 owns 10 IDs per `waves/pending/W30.md` frontmatter:
`HPC-W07-CTRL-001..010`. No TODO-detail IDs. Mandatory authority read before
edits: all `opencode/REQUIREMENT_REGISTRY.md` W30 rows (10 source-derived,
`WAVE_V2_FINAL_07.md` line 163 Workstream F Submission + lines 171-181
Workstream G Cancellation), `opencode/TODO_OWNERSHIP_MAP.md` W30 rows (none —
empty result is the correct reading, not an omission), and
`opencode/sources/WAVE_V2_FINAL_07.md` sections **Workstream F — Submission**
and **Workstream G — Cancellation** plus the P0 wrong-target-cancel guard.
Live code inspected before editing (`wx_shell.py` editor + remote submit
paths, `wx_jobs.py` `cancel_job` worker, `slurm_ssh.py`/`slurm_base.py`/
`slurm_mock.py` sbatch/scancel contracts, `slurm_directives.py` initial-block
semantics, `provider_capabilities.py` + `config/system_profile.py` provider
shape, Qt `editor_widget.py` submit validation as behavior reference only,
`job_identity.py` + `job_list_filter_sort.py` W28 gates, existing
`test_w28/test_w29/test_wx_jobs_behavior/test_slurm_models` contracts).
Unattended, non-interactive; no user questions asked. No cross-Wave
worktree/report/temp edits. Pre-existing dirty hunks preserved verbatim (W30
diff touches only the 4 paths listed above). HEAD (`3e9635ba`) is ahead of
`origin/develop`; the divergence is local program work already on `develop`,
not a rebase target — worked from the recorded HEAD as the Wave execution
baseline per the repo-truth rule and resolved nothing silently.

## Discovery

| Finding ID | Severity | Surface | Evidence | Root cause |
|---|---|---|---|---|
| DEF-W30-001 | P1 | submit acceptance | source read: `wx_shell.py` `_editor_action_factory.submit` called `slurm.sbatch(path)` and discarded the return; `_remote_files_callbacks.submit_slurm` returned `slurm.sbatch(path)` verbatim with no job-ID parse and no failure raise | CTRL-001 has no confirmed-acceptance owner on the wx path (Qt widget already parses `Submitted batch job (\d+)` and shows failure hints; wx does not) |
| DEF-W30-002 | P1 | submit validation | source read: both wx submit entry points check only `path` presence (editor) or nothing (remote); no empty-content, placeholder, `#SBATCH`-presence, or provider-driven partition/account check exists on the wx path | CTRL-001/002 have no wx validation owner |
| DEF-W30-003 | P1 | cancel result/refresh | source read: `wx_jobs.py` `cancel_done(error)` only cleared `cancel_in_flight` and re-enabled the button; the scheduler return was discarded, no message was shown, and `refresh_jobs()` was never triggered | CTRL-007/008 have no reflection/refresh owner |
| DEF-W30-004 | P1 | cancel race/error conflation | source read: `worker()` posted only `(callback, error)`; `scancel` text (`Invalid job id`, `Permission denied`, terminal `final_state`) was never classified, so an already-ended race and an authorization refusal were indistinguishable | CTRL-009/010 have no classification owner |
| DEF-W30-005 | P2 | cancel capability | source read: `cancel_job` early-returned when `cancel` was falsy with no recorded reason and no disabled-button semantics; `submit_slurm_supported` exists but no cancel-capability helper exists | CTRL-006 has no explicit availability owner |
| OBS-W30-006 | P3 | content-identity reconciliation | controller handoff `af624903…` equals the W29 audit-receipt tested identity; observed W30 spec bytes hash `389ed6ab…` | distinct Waves/identities by design; no spec tampering (10 IDs + policies verified) — controller-owned reconciliation |

Pre-change narrow baselines (all green before edits):
`test_w28_jobs_identity_refresh + test_slurm_models` 28 passed,
`test_wx_jobs_behavior` 9 passed.

Second-defect search (dimensions checked): negative (empty path/content,
placeholder script, missing `#SBATCH`, unconfirmed sbatch blob, zero-exit
without token, invalid-job-id race, permission-denied refusal, terminal-state
confirmation), unavailable-capability (lab SSH `Permission denied
(publickey)` BatchMode — EXTERNAL_BLOCKED, nothing invented; `compute01|down`
in `lab-status.ps1` noted but not used as acceptance), permission/network
failure (cancel ERROR path surfaces message without refresh storm),
cancellation/retry (in-flight guard + close guard untouched), stale
callback/result (W28 identity/sequence guards untouched and green),
persistence/identity/cleanup (frame teardown in tests; no real user config
touched), packaging (N/A — no owned requirement needs an artifact SHA; see
evidence table).

## Requirement trace (requirement -> live owner -> test -> evidence)

Workstream F — Submission (CTRL-001/002). Owners: NEW
`services/job_submit_cancel.py` (`validate_submit_request`,
`extract_sbatch_job_id`, `submit_result_status`,
`validate_template_against_provider`) + wx wiring (`_editor_action_factory`
editor submit, `_remote_files_callbacks.submit_slurm`):
- CTRL-001 (validate before sending; success only on confirmed acceptance): IMPLEMENT.
  `test_w30_submit_requires_path`,
  `test_w30_submit_rejects_empty_and_placeholder_content`,
  `test_w30_submit_success_requires_confirmed_job_id`,
  `test_w30_submit_rejects_unconfirmed_output`.
  Editor submit now validates path/content/placeholders/`#SBATCH`, calls
  `sbatch` once, parses the acceptance token, and raises
  `Submission failed: …` when no job ID is confirmed instead of marking
  success. Remote `submit_slurm` does the same for the path-only entry point.
- CTRL-002 (template partition/account/directive rules capability/config driven): IMPLEMENT.
  `test_w30_template_rules_are_config_driven_not_hardcoded`,
  `test_w30_submit_validation_threads_provider_config`.
  Allowed partitions/accounts and account/project requirements are read from
  the provider config mapping (`allowed_partitions/partitions`,
  `allowed_accounts/accounts`, `requirements:{account,project}` /
  `require_account/require_project`); undeclared dimensions impose no
  constraint. No partition/account literal is hardcoded in the service.

Workstream G — Cancellation before-cancel (CTRL-003..006). Owners:
`job_identity.make_identity/cancel_is_safe` + `job_list_filter_sort`
row-list gate (W28, reused) + NEW `job_submit_cancel`
(`build_cancel_confirmation`, `cancel_capability_available`) + wx wiring
(`cancel_job` guards + wording + capability state):
- CTRL-003 (selected job identity): IMPLEMENT (pre-existing W28 double gate,
  preserved + covered). `test_w30_cancel_identity_and_scope_gate`,
  `test_w30_cancel_row_list_gate_blocks_stale_selection`.
- CTRL-004 (cluster/profile): IMPLEMENT (same gates: identity tuple carries
  profile/cluster/provider/session; drifted scope blocks cancel). Same tests.
- CTRL-005 (confirmation wording): IMPLEMENT.
  `test_w30_cancel_confirmation_names_exact_target` + wx tests (monkeypatched
  `MessageBox==YES` proves the confirmation gate runs; `msg` always carries
  the job ID with optional `(name)` suffix via `jobs.cancel_confirm` with
  `build_cancel_confirmation` as the fallback/equivalence wording).
- CTRL-006 (capability availability): IMPLEMENT.
  `test_w30_cancel_capability_is_explicit` + wx `cancel_capability` state
  (`available` vs `unavailable` with `last_cancel_outcome==UNAVAILABLE`,
  button disabled, recorded message when neither `cancel` nor
  `slurm_backend.s構築cancel*` is callable).

Workstream G — Cancellation after-cancel (CTRL-007..010). Owners: NEW
`job_submit_cancel.classify_cancel_outcome/reflect_cancel_result` (+
`is_already_gone_message/is_unauthorized_message`) + wx wiring (`worker`
captures output text, `cancel_done` classifies with `final_state`,
stores `last_cancel_*`, shows the reflection dialog, refreshes on benign
outcomes):
- CTRL-007 (reflect command result): IMPLEMENT.
  `test_w30_reflect_cancel_result_drives_refresh_and_visibility` + 3 wx tests
  (`last_cancel_outcome/message/is_error` mirrors + `MessageBox` proof).
- CTRL-008 (refresh): IMPLEMENT. `CANCELLED` and `ALREADY_GONE` set
  `should_refresh=True` and call `refresh_jobs()`; `ERROR` does not.
  `test_w30_wx_cancel_reflects_result_and_refreshes` pumps until
  `refresh > before`.
- CTRL-009 (tolerate already-ended race): IMPLEMENT.
  `test_w30_already_gone_vs_unauthorized_are_distinct`,
  `test_w30_wx_cancel_already_gone_is_benign_and_refreshes`
  (`Invalid job id` + terminal `final_state==COMPLETED` → `ALREADY_GONE`,
  benign message `already ended`, `is_error is False`, refreshes).
- CTRL-010 (already-gone vs unauthorized/error kept distinct): IMPLEMENT.
  Same classification tests (`Permission denied` → `ERROR`, never
  `ALREADY_GONE`; race phrases take precedence over incidental account
  tokens; `ERROR` shows `Cancel failed for …` and does not refresh-storm).
  `test_w30_wx_cancel_error_is_distinct_and_does_not_refresh_as_success`.

## Fixes (proof chains)

FIX-A (DEF-W30-001/002; CTRL-001/002):
Root cause: wx submit paths discarded/confirmed nothing and validated only
path presence.
Change: `services/job_submit_cancel.py` (acceptance regex
`Submitted\s+batch\s+job\s+(\d+)`, `submit_result_status` fail-closes without
a token even when `ok is True`, placeholder/empty/`#SBATCH`/provider-driven
checks) + `wx_shell.py` editor submit (capability check first, provider
config from `session.profile.provider_template`, content-aware validation,
single `sbatch` call, raise on `FAILURE`, return output) + remote
`submit_slurm` (same for the path-only entry point).
Before EV: no wx job-ID parse existed (source-read finding; Qt reference only).
After EV: 6 submit/template tests pass (EV-W30-NEW below).
Sensitivity: zero-exit empty/`OK` blobs still `FAILURE`; `Submitted batch job
12345 (mock)` still `SUCCESS`; trailing-directive-after-code correctly out of
scope (initial-block semantics preserved).
Regression: EV-W30-REG cohorts green.

FIX-B (DEF-W30-003/004/005; CTRL-003..010):
Root cause: cancel worker dropped the scheduler return; no capability,
reflection, refresh, or race/error classification existed.
Change: `services/job_submit_cancel.py` (capability probe, confirmation
builder, gone/unauthorized lexicons with race precedence, `final_state`
terminal confirmation, `CancelReflection` with `should_refresh/is_error`) +
`wx_jobs.py` `cancel_job` (explicit `UNAVAILABLE` state + disabled button,
identity double gate preserved, wording fallback guarantees the job ID is
named, worker captures output text, `cancel_done(error, output_text)`
classifies with `final_state(job_id)`, mirrors `last_cancel_*`, dialogs the
reflection, refreshes only on `CANCELLED/ALREADY_GONE`) + state init
(`cancel_capability/last_cancel_*`) + `host._wx_jobs_cancel` exposure +
optional `_event` for direct handler tests.
Before EV: `cancel_done` re-enabled the button and nothing else (source-read).
After EV: 6 classification/reflection tests + 3 wx cancel tests pass.
Sensitivity: `Invalid job id` vs `Permission denied` asserted both at unit
and wx layers; terminal-state confirmation only upgrades ambiguous errors,
never downgrades refusals; error path bounded to ≤1 incidental refresh.
Regression: EV-W30-REG cohorts green.

## Evidence

| ID | Command | Result | Binds to |
|---|---|---|---|
| EV-W30-NEW | `python -m pytest tests/test_w30_submit_cancel.py -q` | 15 passed | CTRL-001..010 (12 unit + 3 wx GUI with event/runtime readback: select via `ListEvent`, cancel via `_wx_jobs_cancel`, pump `CallAfter`, assert `last_cancel_*` + refresh counts) |
| EV-W30-REG | `python -m pytest tests/test_w28_jobs_identity_refresh.py tests/test_w29_job_outputs.py tests/test_wx_jobs_behavior.py tests/test_slurm_models.py -q` | 53 passed | no W28/W29/wx/parser regression |
| EV-W30-REG2 | `python -m pytest tests/test_output_follower.py tests/test_output_channel_resolver.py tests/test_wx_editor.py -q` | 44 passed | outputs/editor cohorts green |
| EV-W30-EXT | `ssh -o BatchMode=yes -o ConnectTimeout=10 hpctest@192.168.250.11 echo LAB_OK` | denied | EXTERNAL_BLOCKED (`Permission denied (publickey)`; host reachable, no key auth in env; no credentials requested or invented; all safe local/package/GUI checks completed) |
| EV-W30-EXTERNAL | required class EXTERNAL per Wave header | — | EXTERNAL_BLOCKED (above); no mock substitution for external claims (mock backends cited only as code-shape reference, never as external evidence) |
| EV-W30-GUI | wx tests in EV-W30-NEW | 3 passed | required class GUI via exact runtime action/test/readback (select event → cancel handler → `CallAfter` worker → `last_cancel_*` state + `MessageBox` proof + refresh-count readback), bound to the working-tree candidate |
| EV-W30-PACKAGE | required classes are GUI+EXTERNAL only | N/A | no owned requirement needs an artifact SHA-256; no package claim made |
| EV-W30-LAB | `lab/lab-status.ps1` (bounded) | FAIL (infra) | `compute01\|down`, `slurm.ok=false`; transports/services otherwise `true`; image pin PASS; recorded as context only, not acceptance |

Candidate identity: working tree at `3e9635ba` + W30 hunks listed above
(`job_submit_cancel.py` new, `wx_shell.py` submit hunks, `wx_jobs.py` cancel
hunks, `test_w30_submit_cancel.py` new). Closure-only changes (this report)
stay inside `docs/wave-reports/` per the profile allowlist.

## Diff review

`git status --porcelain=v1` compared before/after: pre-existing dirty and
untracked sibling paths preserved; W30 adds exactly one tracked-source new
file, two tracked-source edits, and one new test file plus this report.
`git diff --stat` (tracked): `wx_jobs.py` + `wx_shell.py` only (plus
preserved sibling hunks). `git diff --check`: clean (no whitespace errors).
Full `git diff` inspected: no secrets, no generated/binary noise, no
unrelated refactors, no duplicated business logic (wx layers call the
framework-neutral service), no weakened tests (all new assertions are
meaningful; no skip/xfail added).

## Residual / handoff

No owned blocking defect remains. EXTERNAL is truthfully `EXTERNAL_BLOCKED`
(lab key auth unavailable in this environment); the real-job submit→cancel→
refresh journey against `LOCAL_REAL_HYPERV` is the correct audit-time replay
once key auth is available — the auditor reruns EV-W30-NEW + EV-W30-REG,
adjudicates EXTERNAL_BLOCKED residual, and performs the fresh independent
audit. Do not synthesize a PASS over the blocked external class.

External evidence: EXTERNAL_BLOCKED (lab key auth unavailable; host reachable)
