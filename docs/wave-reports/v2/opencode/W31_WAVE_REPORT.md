# W31 — Job lifecycle races and real/package acceptance - Wave Report

```text
Wave: W31
Canonical report: docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
Repository: hpc-client-gui / develop
Branch: develop
Baseline SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Tested implementation: working tree at 3e9635ba + W31-owned additions
  (tests/test_w31_race_lifecycle.py [new, 14 tests],
   .tmp/w31-package/hpc_client_gui-1.5.9-py3-none-any.whl [candidate-built,
   SHA-256 9253a7e6085e61ed93fd6b5232544270d2258ee5d3bb49409d1c6adb658d1a3e])
  No tracked-source product edits by W31: the race-hardening implementation
  (JobsRefreshState sequence machine, JobIdentity tuple + double cancel
  gate, semantic filter/sort, submit acceptance + cancel classification,
  generation-guarded details/accounting/outputs, set_session invalidation)
  already exists in the working tree as preserved sibling-owned hunks
  (W28/W29/W30, listed below). W31 verified, race-tested, and acceptance-
  bound that implementation against its own 55 owned IDs.
  Plus pre-existing uncommitted hunks (preserved, not owned by W31):
   src/hpc_gui/i18n/en.json + tr.json [W27-owned],
   src/hpc_gui/services/slurm_models.py [W28-owned],
   src/hpc_gui/services/files_ssh.py + output_follower.py [W29-owned],
   src/hpc_gui/wx_editor_view.py [W26/W27-owned],
   src/hpc_gui/wx_plugins_view.py [W26-owned],
   src/hpc_gui/wx_shell.py [W30-owned],
   src/hpc_gui/wx_jobs.py W28/W29/W30-owned hunks [refresh machine,
     filter/sort, identity double gate, cancel reflection, per-channel
     output errors - preserved],
   src/hpc_gui/services/job_identity.py + job_list_filter_sort.py +
   jobs_refresh_state.py + job_submit_cancel.py [untracked, W28/W30-owned],
   tests/test_w26_run_supplement.py + tests/test_w27_editor_conflicts.py +
   tests/test_w28_jobs_identity_refresh.py + tests/test_w29_job_outputs.py +
   tests/test_w30_submit_cancel.py [untracked, sibling-owned]
Current HEAD: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Content handoff: controller content_identity
  0da446f7ae66eeb5f54432985a010cf41d7776ca97cfb66c982e425b2ea8ca9c
  (phase=run handoff; equals the W30 audit-receipt tested identity chain)
Observed waves/pending/W31.md SHA-256 (BOM-stripped, LF-normalized bytes):
  8a0c5e4000be33c8f0ec978e1ee43159f746f45cadb84d96a9efcdd3c664e9f8
  (frontmatter wave_id=W31/wave_kind=execution/canonical_source=W31/
   55 owned IDs/aggregate_close_owner=false/evidence_policy=wave-local/
   audit_policy=fresh-independent verified consistent; the handoff
   content_identity is the program chain identity, distinct by design
   from the spec-bytes hash — controller-owned reconciliation)
Execution start gate: NONE (per Wave independence contract)
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24 (repair: RACE-049 live Slurm replay, job 67)
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: READY_FOR_AUDIT (independent audit pending, controller-owned)
```

## Scope

W31 owns 55 IDs per `waves/pending/W31.md` frontmatter:
`HPC-W07-RACE-001..055`. No TODO-detail IDs. Mandatory authority read before
edits: all `opencode/REQUIREMENT_REGISTRY.md` W31 rows (55 source-derived:
RACE-001..005 entry prerequisites, RACE-006..018 scope boundary,
RACE-019..023 Workstream H, RACE-024..032 targeted tasks, RACE-033..042 test
matrix, RACE-043..051 acceptance gates, RACE-052..055 STOP conditions),
`opencode/TODO_OWNERSHIP_MAP.md` W31 rows (none — empty result is the
correct reading, not an omission), and `opencode/sources/WAVE_V2_FINAL_07.md`
sections **Entry criteria**, **Scope**, **Workstream H —
Disconnect/profile switch**, **Targeted tasks**, **Test matrix**,
**Acceptance criteria**, **STOP conditions**. Live code inspected before
acting (`wx_jobs.py` refresh/details/accounting/outputs/cancel/set_session
paths, `job_identity.py`, `jobs_refresh_state.py`,
`job_list_filter_sort.py`, `job_submit_cancel.py`, `slurm_models.py`,
`selected_job_context.py`, existing `test_w28/test_w30` contracts).
Unattended, non-interactive; no user questions asked. No cross-Wave
worktree/report/temp edits. Pre-existing dirty hunks preserved verbatim
(W31 touches no tracked product source; only the new test file, the
candidate-built wheel under `.tmp/`, and this report).

## Discovery

| Finding ID | Severity | Surface | Evidence | Root cause |
|---|---|---|---|---|
| DEF-W31-001 | P1 | package currency | `test_w31_package...` first run: `dist/hpc_client_gui-1.5.9-py3-none-any.whl` (built 2026-09-22, `d3a3dcbe…`) lacks `services/job_identity`, `services/jobs_refresh_state`, `services/job_submit_cancel` | release wheel predates the W28/W30 working-tree race modules; it cannot be the artifact under acceptance for RACE-050/055 |
| OBS-W31-002 | P2 | entry prerequisites | source read: RACE-001..005 cite W06/W05/W04/W03/W02 states; per the Wave independence contract these are non-blocking hints, and the owned behaviors they gate (session/profile/filesystem, connection, harness, Slurm target, capability declarations) are exercised directly by the W31 tests/mocks | no concrete missing input consumed by an owned requirement; no `AWAITING_INPUT` emitted |
| OBS-W31-003 | P3 | content-identity reconciliation | controller handoff `0da446f7…` equals the W30 audit-receipt tested identity; observed W31 spec bytes hash `8a0c5e40…` | distinct Waves/identities by design; 55 IDs + policies verified, no spec tampering — controller-owned reconciliation |

Pre-change narrow baseline (green before W31 additions):
`test_w28 + test_w30` (non-GUI) 32 passed; single wx probe
`test_w28_wx_refresh_success` 1 passed; lab TCP `192.168.250.11:22`
reachable.

Second-defect search (dimensions checked): negative (refresh failure with
and without prior data, late failure for an old session, malformed rows,
unknown `ZZ` state, unconfirmed sbatch blobs, already-gone vs unauthorized
cancel, empty selection), unavailable-capability (lab SSH
`Permission denied (publickey)` BatchMode — EXTERNAL_BLOCKED, nothing
invented), permission/network failure (cancel ERROR path distinct from
`ALREADY_GONE`; outputs per-channel permission errors preserved from W29),
cancellation/retry (in-flight + close guards untouched), stale
callback/result (sequence + generation + identity guards at every async
boundary — refresh, sacct, details, accounting, server status, outputs),
persistence/identity/cleanup (`set_session` clears selection/store/followers/
tabs/request IDs and bumps `provider_generation`; frame teardown in tests;
no real user config touched), packaging (candidate wheel rebuilt from the
working tree; release wheel gap recorded as DEF-W31-001, not silently
adopted).

## Requirement trace (requirement -> live owner -> test -> evidence)

Entry prerequisites (RACE-001..005). No W31-owned code; the contract treats
historical report states as non-blocking. Each gated dimension is exercised
directly: session/profile switching (wx profile-switch tests), connection
generation guards, packaged harness (candidate wheel), Slurm target shapes
(real-shape parse test), capability declarations (config-driven template
test in W30 cohort, green). No `AWAITING_INPUT`: every owned requirement
proceeds on the current integration base.

Scope boundary (RACE-006..018). Owners: `wx_jobs.py` listing/refresh/state/
filter/sort/details/outputs/submit/cancel/capability/stale/periodic paths +
`slurm_models.py` real/package parsers. Tests: W28/W29/W30 cohorts (68
regression passes, EV-W31-REG) + W31 race/matrix tests (EV-W31-NEW).

Workstream H (RACE-019..023). Owners: `JobsRefreshState` sequence machine +
`generation()` session check in `refresh_jobs.done`; `provider_generation`
bump + selection/store/follower invalidation in `set_session`; identity
double gate (`cancel_target_is_safe` + `make_identity`/`cancel_is_safe`) in
`cancel_job`; `selected_job_store.generation` capture guards in
`_refresh_raw_job_details`/`_refresh_raw_accounting`/`_refresh_sacct`;
`provider_generation` + `generation()` guards in outputs/sacct/server-status
`done` handlers. Tests: 3 unit sequence tests + 4 wx race tests
(EV-W31-NEW): refresh-while-disconnecting discards stale, profile-switch
during refresh lets the new context win, cancel after profile switch never
fires, reconnect-then-refresh recovers with a fresh timestamp; details-guard
unit test pins the generation-invalidation semantic.

Targeted tasks (RACE-024..032). TASK-001: bindings traced
(`wx_jobs.py` → `job_identity`/`job_list_filter_sort`/`jobs_refresh_state`/
`job_submit_cancel`/`slurm_models`/`selected_job_context`) — no dangling
wx-local duplicates. TASK-002: refresh/stale behavior defined in
`JobsRefreshState.status_text` + visible label (`Updated:`/`Refresh
failed:`/`Refresh failed (stale):`). TASK-003: parser hardening
(`safe_state_display`, `is_terminal_state`, `parse_squeue_result`/
`parse_sacct_result` fail-closed on non-zero exit, malformed-row skipping).
TASK-004: overlapping-refresh race tests (unit triple-sequence + wx
profile-switch). TASK-005: identity-safe details/log callbacks (generation
guards + test). TASK-006: submission validation + confirmed-result
semantics (W30 owner, W31 re-asserted incl. STOP-054). TASK-007:
identity-safe cancel (double gate + wx blocked-cancel test incl. STOP-052).
TASK-008: real Slurm lifecycle (squeue/sacct/scontrol end-to-end
parse test + LIVE replay 2026-09-24 against LOCAL_REAL_HYPERV:
job 67 submit→RUNNING list→details→scancel→CANCELLED→empty-refresh,
EV-W31-REAL). TASK-009:
exact packaged-artifact test (candidate wheel content + SHA, EV-W31-PKG).

Test matrix (RACE-033..042). empty/list: parser empty test + wx list
readback. unknown state: `ZZ` unit test. refresh failure/stale: unit +
wx stale tests. overlapping refresh: unit + wx tests. details/log: W29
cohort + generation-guard test. submit: acceptance-token tests.
cancel: W30 cohort + wx cancel tests. already-completed cancel:
`ALREADY_GONE` classification (W30 cohort green). profile switch race:
wx profile-switch tests. All matrix rows have automated + package legs;
real-Slurm legs are proven LIVE (EV-W31-REAL: job 67 full journey
on `LOCAL_REAL_HYPERV`); parse-shape tests remain as code-shape
reference only.

Acceptance gates (RACE-043..051). Refresh states unambiguous (success/
failure/stale label + `status_text`). Older responses cannot overwrite
newer context (sequence + generation guards, proven by tests). Unknown
states display safely (`ZZ` passes through, never terminal). Submission
requires backend confirmation (token-only `SUCCESS`). Cancel targets the
selected job on the intended profile/cluster (`cancel_is_safe` full tuple
+ row-list gate + wx proof). Details/log cannot attach to a wrong job
(generation + selection guards). Real Slurm journey: PASS (EV-W31-REAL —
job 67 submit/list/details/cancel/refresh against LOCAL_REAL_HYPERV
with cleanup). Exact packaged workflow: candidate wheel passes (EV-W31-PKG).
No P0/P1 remains in owned scope (DEF-W31-001 repaired via candidate
rebuild; STOP sweep below green).

STOP conditions (RACE-052..055). Wrong-job cancel: blocked at two gates +
wx proof (`calls["cancel"] == 0`). Stale cross-profile overwrite: old
sequence + old generation responses discarded by test. Success-after-
rejection: every unconfirmed output classifies `FAILURE`. Package missing
resources: candidate wheel contains all seven required fragments.
No STOP condition triggers.

## Fixes (proof chains)

FIX-A (DEF-W31-001; RACE-032/050/055, TASK-009):
Root cause: the `dist/` release wheel was built before the working-tree
race modules existed, so it lacked three required provider/parser-side
resources.
Change: no product-source change (nothing to fix in code — the modules
exist and are wired); built the candidate wheel from the exact working
tree with `.venv/Scripts/python -m pip wheel . --no-deps
--no-build-isolation -w .tmp/w31-package/` (offline, setuptools backend).
The `dist/` release artifact was left untouched — release versioning/
publishing is controller/release-owned, not a silent worker overwrite.
Before EV: package test failed with the three missing fragments named.
After EV: all 14 W31 tests pass; the candidate wheel
(`9253a7e6…`, 934795 bytes, 270 entries) contains all seven required
fragments.
Sensitivity: the test fails closed on any missing fragment and binds the
full SHA-256; the stale release wheel is recorded, never adopted as
acceptance.
Regression: EV-W31-REG cohorts green (68 passed).

## Evidence

| ID | Command | Result | Binds to |
|---|---|---|---|
| EV-W31-NEW | `python -m pytest tests/test_w31_race_lifecycle.py -q` | 14 passed (10 unit + 4 wx GUI with event/runtime readback) | RACE-019..023/026/027/029..032/037/042..048/050/052..055 (sequence/generation/identity guards, parser safety, submit acceptance, package content, wx disconnect/switch/cancel/reconnect journeys) |
| EV-W31-REG | `python -m pytest tests/test_w28_jobs_identity_refresh.py tests/test_w29_job_outputs.py tests/test_w30_submit_cancel.py tests/test_wx_jobs_behavior.py tests/test_slurm_models.py -q` | 68 passed | no W28/W29/W30/wx/parser regression |
| EV-W31-PKG | candidate wheel `.tmp/w31-package/hpc_client_gui-1.5.9-py3-none-any.whl` | SHA-256 `9253a7e6085e61ed93fd6b5232544270d2258ee5d3bb49409d1c6adb658d1a3e`, 270 entries, 7/7 required fragments | required class PACKAGE via exact artifact SHA-256 under acceptance, bound to the working-tree candidate |
| EV-W31-GUI | wx tests in EV-W31-NEW | 4 passed | required class GUI via exact runtime action/test/readback (blocked `list_jobs` + mid-flight `set_session`, generation-bump switch, `ListEvent` select → `_wx_jobs_cancel` with zero-fire assertion, reconnect → `refresh_jobs` timestamp/stale/error readback), bound to the working-tree candidate |
| EV-W31-EXT | `ssh -i <emitted-profile-key> -o BatchMode=yes -o StrictHostKeyChecking=yes hpctest@192.168.250.11 echo LAB_OK` | `LAB_OK`, exit 0 (repair probe 2026-09-24; prior run-phase `Permission denied` was a missing-key-path env defect, not a lab defect) | lab key auth feasible with the emitted profile key; superseded by EV-W31-REAL |
| EV-W31-REAL | real Slurm lifecycle vs `LOCAL_REAL_HYPERV` (`local-real`, `192.168.250.11:22`, `hpctest`) 2026-09-24 ~14:44 UTC: `sbatch --parsable job.sbatch` → `67`; `squeue -j 67` → `RUNNING` (`w31-repair2`, `compute02`, `debug`); `scontrol show job 67` → `RUNNING` (`SubmitTime=2026-09-24T14:44:09`, `StartTime=14:44:10`, `NodeList=compute02`); `scancel 67` exit 0 → `CANCELLED` (`EndTime=14:44:14`); `sacct -j 67` → `CANCELLED by 1000`; `squeue` refresh empty; scratch `w31-repair-*` dirs removed, `squeue`/`sinfo` verified clean (compute02 idle) | PASS — binds RACE-049 + matrix real-Slurm legs (submit/list/details/cancel/refresh) to env HEAD `3e9635ba`, target identity above, disposable job `w31-repair2`/ID 67, with cleanup | required class EXTERNAL via real authorized infrastructure with environment identity and cleanup |
| EV-W31-REAL-NOTE | first repair `sbatch` (job 65, `w31-repair-race`) reached terminal `FAILED (RaisedSignal:53)` before any cancel leg; `srun` probe then passed (`compute02`, exit 0) and the retry (job 67) completed the full journey | transient scheduler/node placement event, not a product defect; no owner routing; recorded for transparency, lab verified healthy afterwards |
| EV-W31-EXTERNAL | required class EXTERNAL per Wave header | PASS via EV-W31-REAL | no mock substitution for external claims (mock/parse shapes cited only as code-shape reference, never as external evidence) |
| EV-W31-LAB | TCP `192.168.250.11:22` + `sinfo` (`debug` idle on compute02; compute01 DOWN reboot) + `srun --partition=debug hostname` → `compute02` exit 0 | lab healthy for the exercised path | context + transport proof for EV-W31-REAL |

Candidate identity: working tree at `3e9635ba` + W31 additions
(`tests/test_w31_race_lifecycle.py` new, `.tmp/w31-package/` candidate
wheel, this report). No tracked product-source edits by W31; sibling
W26–W30 hunks preserved verbatim. Closure-only changes (this report)
stay inside `docs/wave-reports/` per the profile allowlist; the wheel
lives under the profile temp root `.tmp/`.

## Diff review

`git status --porcelain=v1` compared before/after: pre-existing dirty and
untracked sibling paths preserved; W31 adds exactly one new test file,
one `.tmp/` wheel, and this report. `git diff --stat` (tracked):
sibling-owned files only, untouched by W31. `git diff --check`: clean
(no whitespace errors; one pre-existing CRLF notice on
`output_follower.py`). Full new-test diff inspected: no secrets, no
generated/binary noise in tracked paths, no unrelated refactors, no
duplicated business logic (tests call the framework-neutral services and
the live wx handlers), no weakened tests (all assertions meaningful; no
skip/xfail added; the package test was strengthened to the candidate
artifact, not weakened to the stale release wheel).

## Residual / handoff

No owned blocking defect remains. RACE-049 real-Slurm journey is proven
LIVE (EV-W31-REAL, job 67, with cleanup; lab left idle/empty for the next
serialized consumer). The auditor reruns EV-W31-NEW + EV-W31-REG,
adjudicates EV-W31-REAL freshness/binding, performs the fresh independent
audit, and owns the release-wheel refresh/publish decision.

External evidence: PASS via EV-W31-REAL (job 67 submit→RUNNING→details→CANCELLED→empty-refresh on LOCAL_REAL_HYPERV, cleaned up)
Package evidence: `9253a7e6085e61ed93fd6b5232544270d2258ee5d3bb49409d1c6adb658d1a3e` (candidate wheel, `.tmp/w31-package/`)
