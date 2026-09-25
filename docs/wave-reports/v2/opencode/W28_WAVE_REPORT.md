# W28 — Jobs identity, listing, parser and refresh state - Wave Report

```text
Wave: W28
Canonical report: docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
Repository: hpc-client-gui / develop
Branch: develop
Baseline SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Tested implementation: working tree at 3e9635ba + W28-owned hunks
  (src/hpc_gui/services/job_identity.py [new],
   src/hpc_gui/services/jobs_refresh_state.py [new],
   src/hpc_gui/services/job_list_filter_sort.py [new],
   src/hpc_gui/services/slurm_models.py [safe-state + result-guard helpers],
   src/hpc_gui/wx_jobs.py [semantic filter/sort, refresh machine, cancel guard,
    visible stale readback, column-click sort],
   tests/test_w28_jobs_identity_refresh.py [new, 23 tests])
  Plus pre-existing uncommitted hunks (preserved, not owned by W28):
   src/hpc_gui/i18n/en.json + tr.json [W27-owned, 8 lines each],
   src/hpc_gui/wx_editor_view.py [W26/W27-owned, 306 lines],
   src/hpc_gui/wx_plugins_view.py [W26-owned],
   tests/test_w26_run_supplement.py + tests/test_w27_editor_conflicts.py [untracked, sibling-owned]
Current HEAD: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Content handoff: controller content_identity
  cc1ce303e235c9759977913e3c94109c1582f6e7e874e43013fc34c50377cab9
  (W27 audit receipt; W28 spec identity observed separately below)
Observed waves/pending/W28.md SHA-256 (BOM-stripped, LF-normalized bytes):
  e13509636180721517a1a1523fdabdcfcf4e6650639612a1b1ccdae8b3ebad7b
  (frontmatter wave_id/wave_kind/canonical_source/21 owned IDs/
   aggregate_close_owner=false/evidence_policy=wave-local/
   audit_policy=fresh-independent verified consistent)
Execution start gate: NONE (per Wave independence contract)
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: READY_FOR_AUDIT (independent audit pending, controller-owned)
```

## Scope

W28 owns 21 IDs per `waves/pending/W28.md` frontmatter:
`HPC-W07-JOB-001..017` (17) + `HPC-W07-REFRESH-001..004` (4). No TODO-detail
IDs. Mandatory authority read before edits: all
`opencode/REQUIREMENT_REGISTRY.md` W28 rows (21, extracted to
`.tmp/w28-reg.txt`), `opencode/TODO_OWNERSHIP_MAP.md` W28 rows (none — empty
result is the correct reading, not an omission), and
`opencode/sources/WAVE_V2_FINAL_07.md` sections **Workstream A — Data model
and identity**, **Workstream C — Slurm parsing**, **Workstream D —
Filtering/sorting**, **Workstream B — Refresh state machine** (lines 54-103).
Live code inspected before editing (`services/slurm_models.py`,
`services/slurm_ssh.py`, `services/selected_job_context.py`,
`services/job_tracking_controller.py`, `wx_jobs.py` table/filter/refresh/
cancel paths, `services/slurm_mock.py`, existing `test_slurm_models.py` +
`test_wx_jobs_behavior.py` contracts). Unattended, non-interactive; no user
questions asked. No cross-Wave worktree/report/temp edits. Pre-existing dirty
hunks preserved verbatim (`git status` before/after compared; W28 diff touches
only the 6 paths listed above). HEAD (`3e9635ba`) is ahead of
`origin/develop` (`63b696b3`); the divergence is local program work already on
`develop` (W19-W25 + Agent Core sync commits), not a rebase target — worked
from the recorded HEAD as the Wave execution baseline per the repo-truth rule
and resolved nothing silently.

## Discovery

| Finding ID | Severity | Surface | Evidence | Root cause |
|---|---|---|---|---|
| DEF-W28-001 | P1 | jobs refresh lifecycle | source read: `_build_jobs` `state` has only `in_flight` bool; `refresh_jobs.done` on error does `pass` (retains rows silently with no stale flag, no timestamp, no visible status); no monotonic per-refresh sequence for the listing path (only session `generation()`) | Workstream B state machine not implemented on the listing path |
| DEF-W28-002 | P1 | stale/overlapping refresh | source read: `refresh_jobs` serializes via `in_flight+refresh_pending` but `done` applies any arriving payload for the current session generation with no issued-vs-applied sequence check | older overlapping response can overwrite newer context (REFRESH-004) |
| DEF-W28-003 | P1 | cancel wrong-target | source read: `cancel_job` uses `model.tracking.selected_job_id` with no check that the ID still exists in current `raw_items` or equals `state["selected_job"]`; selection-clear only when the filtered view is empty | stale selection after reorder/filter/refresh can cancel a different row (STOP condition) |
| DEF-W28-004 | P2 | filtering/sorting semantics | source read: `_apply_filter` is correctly non-mutating but there is zero `sort` handling in `wx_jobs.py` (only `sorted()` is on monitor IDs); no semantic sort helper exists | JOB-014 (semantic sort) has no owner |
| DEF-W28-005 | P2 | parser failure-vs-empty | source read: `slurm_ssh.SlurmCommandResult` preserves `code`, but `parse_squeue/parse_sacct` take only text; a non-zero-exit error blob fed as text relies solely on `_looks_like_job_id` to avoid phantom rows | JOB-013 has no explicit exit-guard owner |
| DEF-W28-006 | P2 | identity tuple | source read: selection keys are bare `selected_job` strings + session/provider generations; no framework-neutral `(job_id, profile, cluster, provider, session, array/task)` tuple with an explicit same-target/cancel gate | JOB-001..004 have no unit-owned identity module |
| OBS-W28-007 | P3 | content-identity reconciliation | controller handoff `cc1ce303…` is the W27 audit receipt identity; observed W28 spec bytes hash `e1350963…` | distinct Waves/identities by design; no spec tampering (21 IDs + policies verified) — controller-owned reconciliation |

Pre-change narrow baseline: `test_slurm_models.py` `5 passed` (parser groundwork
green before edits).

Second-defect search (dimensions checked): negative (empty list, unknown
state, malformed row, non-zero exit, failure-without-prior-data),
unavailable-capability (keyless lab SSH `Permission denied (publickey)`,
BatchMode — EXTERNAL_BLOCKED, nothing invented), permission/network failure
(refresh-failure path retains + marks stale), cancellation/retry (stale cancel
blocked both at row-list and identity-tuple layers), stale callback/result
(older-seq discard + selection-drop when identity vanishes + sacct/details
generation guards untouched), persistence/identity/cleanup (frame teardown in
tests; no real user config touched), packaging (N/A — see evidence table).

## Requirement trace (requirement -> live owner -> test -> evidence)

Workstream A — identity (JOB-001..004). Owner: NEW
`services/job_identity.py` (`JobIdentity`, `split_job_id`/`base_job_id`,
`make_identity`, `same_target`, `cancel_is_safe`,
`selection_survives_refresh`) + wx wiring (identity-tuple cancel gate in
`cancel_job`, selection-drop on refresh when
`selection_still_exists` is false):
- JOB-001 (identity tuple, no mixing): IMPLEMENT.
  `test_w28_job_identity_tuple_scopes_profile_cluster_provider`.
- JOB-002 (different profile/cluster/provider): IMPLEMENT. Same test
  (profile/cluster/provider drifts each block `same_target` + `cancel_is_safe`).
- JOB-003 (old vs new session): IMPLEMENT.
  `test_w28_job_identity_scopes_old_vs_new_session` (generation 7 vs 8).
- JOB-004 (array/task identifiers): IMPLEMENT.
  `test_w28_job_identity_preserves_array_task_identifiers` (`123` vs `123_4`
  vs `123.batch`; suffixes preserved, never normalized away).

Workstream C — parsing (JOB-005..013). Owner:
`services/slurm_models.py` (existing `parse_squeue`/`parse_sacct` preserved;
NEW `safe_state_display`, `is_terminal_state`, `parse_squeue_result`,
`parse_sacct_result` exit guards):
- JOB-005 (empty job list): IMPLEMENT. `test_w28_parser_empty_job_list`.
- JOB-006 (one job): IMPLEMENT. `test_w28_parser_one_and_many_jobs` (single).
- JOB-007 (many jobs): IMPLEMENT. Same test (3-row ordering).
- JOB-008 (long names): IMPLEMENT. `test_w28_parser_long_names_preserved`
  (200-char name round-trips).
- JOB-009 (unknown/new state): IMPLEMENT.
  `test_w28_parser_unknown_new_state_displays_safely` (`ZZ` passes through,
  never mapped to success/terminal).
- JOB-010 (array job representation): IMPLEMENT.
  `test_w28_parser_array_job_representation` (`123_4`, `123.batch`, sacct
  `123_4`).
- JOB-011 (cancelled/completed state): IMPLEMENT.
  `test_w28_parser_cancelled_completed_state` (`CA`/`CD` + terminal set).
- JOB-012 (malformed row/partial output): IMPLEMENT.
  `test_w28_parser_malformed_row_partial_output_skipped` (garbage + scheduler
  error text yield zero phantom rows).
- JOB-013 (non-zero scheduler exit): IMPLEMENT.
  `test_w28_parser_non_zero_scheduler_exit_is_not_empty_data`
  (`SlurmCommandResult(code=1)` -> `[]`; `code=0` empty -> `[]`; `code=0` rows
  parse normally).

Workstream D — filtering/sorting (JOB-014..017). Owner: NEW
`services/job_list_filter_sort.py` (`sort_key_for`/`sort_jobs`,
`filter_jobs`/`matches_filter`, `selection_still_exists`,
`cancel_target_is_safe`) + wx wiring (`_apply_filter` via helpers,
`_on_column_click` semantic sort, cancel guard, refresh selection-drop):
- JOB-014 (semantic sort): IMPLEMENT.
  `test_w28_sort_uses_semantic_values_not_display_strings` (numeric job-ID
  `2<9<10`, elapsed seconds, state rank RUNNING<PENDING).
- JOB-015 (filter refresh does not mutate backend): IMPLEMENT.
  `test_w28_filter_refresh_does_not_mutate_backend_data` (snapshot equality).
- JOB-016 (selection survives only when identity exists): IMPLEMENT.
  `test_w28_selection_survives_only_when_identity_exists` + wx
  `test_w28_wx_selection_cleared_when_identity_disappears` (row `1` removed ->
  selection cleared, cancel disabled).
- JOB-017 (stale selection cannot cancel different row): IMPLEMENT.
  `test_w28_stale_selection_cannot_cancel_different_row_after_reorder` +
  wx `cancel_job` double gate (row-list check + identity-tuple check).

Workstream B — refresh state machine (REFRESH-001..004). Owner: NEW
`services/jobs_refresh_state.py` (`JobsRefreshState`: `begin`,
`is_current`/`should_apply`, `complete_success(timestamp)`,
`complete_failure(error, clear_on_failure=False)`, `status_text`,
`snapshot`) + wx wiring (monotonic `jobs_refresh_seq`, mirrored
`jobs_refresh_status/timestamp/error/stale`, visible `jobs_refresh_label`,
older-seq discard, retain-on-failure, selection-drop):
- REFRESH-001 (idle->refreshing->success(timestamp)/failure(error)): IMPLEMENT.
  `test_w28_refresh_idle_to_success_with_timestamp` + wx
  `test_w28_wx_refresh_success_sets_timestamp_and_clears_stale`.
- REFRESH-002 (transient failure must not silently clear prior data): IMPLEMENT.
  `test_w28_refresh_failure_keeps_prior_data_marked_stale` + wx
  `test_w28_wx_refresh_failure_retains_rows_and_marks_stale` (row count stays 1).
- REFRESH-003 (retained data visibly marked stale): IMPLEMENT. Same tests
  (`status_text` contains `stale`; wx label contains `stale`/`fail`; `stale`
  flag true; error surfaced, never implied fresh).
- REFRESH-004 (older response cannot overwrite newer): IMPLEMENT.
  `test_w28_refresh_older_response_cannot_overwrite_newer` (old-seq success
  and late failure both discarded) + wx `req_seq != jobs_refresh_seq` discard
  in `done`.

## Fixes (proof chains)

FIX-A (DEF-W28-006; JOB-001..004):
Root cause: no framework-neutral identity tuple; bare job-ID strings plus
ambient generations.
Change: `services/job_identity.py` (frozen `JobIdentity` with
job_id/profile/cluster/provider/session_generation, array-preserving split,
`same_target` conjunction, `cancel_is_safe` + `selection_survives_refresh`
gates); wx `cancel_job` verifies both the row-list gate and the tuple gate.
Before EV: no owner module existed (source-read finding).
After EV: 4 identity tests pass (EV-W28-NEW below).
Regression: full W28 file 23 passed; wx behavior/files/final/stress cohorts
green (EV-W28-REG).

FIX-B (DEF-W28-001/002; REFRESH-001..004):
Root cause: boolean `in_flight` with silent error `pass` and no issued/applied
sequence on the listing path.
Change: `services/jobs_refresh_state.py` machine + wx `jobs_refresh_seq` /
`jobs_refresh_applied_seq` / status/timestamp/error/stale mirror + visible
`jobs_refresh_label` + older-seq discard + retain-and-mark-stale failure path
+ selection-drop when the identity vanishes.
Before EV: error path retained rows silently (no stale flag/status/timestamp).
After EV: 4 machine tests + 3 wx refresh/selection tests pass.
Sensitivity: failure-without-prior-data (`stale is False`) vs
failure-with-data (`stale is True`) both asserted; older-seq success/failure
both discarded.
Residual: `clear_on_failure=True` escape hatch exists for an explicit UX that
wants to drop the list; the wx path never passes it (retains by default).

FIX-C (DEF-W28-005; JOB-005..013):
Root cause: text-only parsers with no exit-status owner.
Change: additive `safe_state_display` / `is_terminal_state` /
`parse_squeue_result` / `parse_sacct_result` (existing `parse_squeue` /
`parse_sacct` / `parse_scontrol` byte-identical behavior; new guards return
`[]` on `ok is False`).
Before EV: error-text-as-input relied on the job-ID heuristic alone.
After EV: 9 parser tests pass including the `code=1 -> []` guard.
Residual: heuristic retained for plain-string legacy callers (mock/backends).

FIX-D (DEF-W28-003/004; JOB-014..017):
Root cause: no semantic sort owner; cancel used the tracking ID unchecked.
Change: `services/job_list_filter_sort.py` (semantic keys: numeric job-ID,
elapsed-seconds, state-rank; non-mutating filter; survival + cancel guards) +
wx `_apply_filter` rewrite (snapshot -> filter -> optional semantic sort ->
render), `_on_column_click` toggling sort, `cancel_job` double gate,
post-success selection-drop.
Before EV: `grep sort` in `wx_jobs.py` hit only monitor-ID sorting; cancel had
no membership check.
After EV: 4 filter/sort tests + wx selection/cancel wiring tests pass.
Residual: sort is user-invoked (column click); default order remains scheduler
order until the user sorts (documented, matches prior UX).

Two-fix gate: PASS (FIX-A identity vs FIX-B ordering vs FIX-C parsing vs
FIX-D filter/sort/cancel are independent root causes; counted once each).

## Tests and evidence required

Environment: Windows, repo `develop`, HEAD `3e9635ba`, Python 3.12
(`python -m pytest` harness), wxPython `4.3.1 msw (phoenix) wxWidgets 3.3.3`
for GUI tests (`@pytest.mark.gui @pytest.mark.wx`).

| Evidence ID | Command / action | Exit | Scope / result |
|---|---|---|---|
| EV-W28-BASE | `pytest tests/test_slurm_models.py -q` (pre-change narrow baseline) | 0 | 5 passed |
| EV-W28-NEW | `pytest tests/test_w28_jobs_identity_refresh.py -q` | 0 | 23 passed (4 identity + 9 parser + 4 filter/sort + 4 refresh-machine + 3 wx integration; 1 pre-existing wx quirk-free run) |
| EV-W28-REG | `pytest test_slurm_models test_wx_jobs test_wx_jobs_behavior test_wx_jobs_files_outputs test_wx_jobs_final_fix test_wx_jobs_stress test_selected_job_context test_job_tracking_controller -q` | 0 | 83 passed in ~87 s, no regression |
| EV-W28-STATIC | `git diff --check` | 0 | clean |
| EV-W28-EXT | `ssh -o BatchMode=yes -o ConnectTimeout=10 hpctest@192.168.250.11 echo LAB_OK` (20 s bound) | denied | EXTERNAL_BLOCKED (`Permission denied (publickey)`; host reachable, no key auth in env; no credentials requested or invented; all safe local/package/GUI checks completed) |
| EV-W28-GUI | wx runtime in EV-W28-NEW (3 tests) | 0 | real `show_jobs` frames: success timestamp + cleared stale; failure retains 1 row + stale flag + visible label; vanished identity clears selection (exact runtime action/test/readback, not controller-only) |
| EV-W28-EXTERNAL | required class EXTERNAL per Wave header | — | EXTERNAL_BLOCKED (above); no mock substitution for external claims (mock backend cited only as code-shape reference, never as external evidence) |
| EV-W28-PACKAGE | package class | — | N/A with justification: no owned ID requires a packaged artifact (identity/parser/refresh/filter behaviors proven at service + wx runtime); no artifact SHA claimed |

New/changed tests: `tests/test_w28_jobs_identity_refresh.py` (new, 23 tests:
REQ identity x4, REQ parser x9, REQ filter/sort x4, REQ refresh-machine x4,
wx integration x3). Taxonomy: 20 x contract/unit, 3 x GUI event/integration.
Mocks: none (real `SlurmCommandResult` values, real wx frames, real
`JobsRefreshState`; `list_jobs` lambdas are the documented service-adapter
seam, not scheduler mocks). No skips/xfails added or weakened; no existing
test modified. Cleanup: `wx_app` fixture destroys top-level windows; unit
tests are pure. GUI claims carry exact runtime readback (item counts, state
mirror keys, label text, selected_job).

## Diff review

`git diff --check`: clean. W28-owned diff only:
`src/hpc_gui/services/slurm_models.py` (+81 additive helpers),
`src/hpc_gui/wx_jobs.py` (+~183/-~24: imports, refresh-label widget, state
keys, filter/sort rewrite, refresh machine, cancel double gate, column-click
bind, controls exposure), plus untracked additions
`src/hpc_gui/services/job_identity.py` / `jobs_refresh_state.py` /
`job_list_filter_sort.py` and `tests/test_w28_jobs_identity_refresh.py`.
Preserved untouched: `i18n/en.json + tr.json`, `wx_editor_view.py`,
`wx_plugins_view.py` (pre-existing sibling hunks, byte-identical via
`git status` before/after). No generated/binary/cache/secret/user-specific
data in the W28 diff. No weakened tests. All new temp state under `.tmp/`
(`w28-reg.txt`, `w28-src.txt`).

## Post-green review (POST_GREEN_REVIEW)

Duplicate paths: Qt `jobs_widget.py` (56-line shim) untouched — wx-only Wave;
Qt parity out of scope, routed nowhere. Alternate entry: `render_items` still
the single table entry; `_on_column_click` bound once with `event.Skip`.
Silent fallbacks: none added — refresh failures now write the visible label +
error mirror (previously silent `pass`). Stale state: sacct/details/outputs
generation guards untouched and green (83-pass cohort). Identity:
`SelectedJobStore` generation semantics untouched; new tuple gate is additive.
Cleanup: no new processes/files outside fixtures + `.tmp/`. Dead branches:
none introduced (`_matches_filter` retained for compatibility though the wx
path now routes through `filter_jobs`). Hardcoded provider: none (profile/
cluster/provider IDs thread through kwargs, default empty). Success-claiming
errors: none (failure paths set `failure` status + error text, never success).
Packaged divergence: none claimed.

## Handoff / resume

Completed and verified: FIX-A, FIX-B, FIX-C, FIX-D with exact executed tests;
23 new tests green; 83-test impacted cohort green; static check clean; GUI
runtime readback (FULL-equivalent for owned GUI semantics: action -> state
mirror + visible label + table readback bound to the tested tree); external
lab blocked on key auth; canonical report current.
In progress: none (run work complete).
Open P0/P1: none in owned scope.
Open P2/P3: none newly found (OBS-W28-007 is a process observation, not a
product defect).
Pending tests/evidence: independent fresh-context audit (controller-owned);
auditor reruns EV-W28-NEW + EV-W28-REG, adjudicates EXTERNAL_BLOCKED residual
and package N/A justification, and verifies candidate/working-tree identity.
Last exact commands: `test_w28_jobs_identity_refresh` 23 passed;
impacted cohort 83 passed; `git diff --check` clean.
Next actions (controller): schedule fresh independent audit of W28; auditor
re-verifies content identity (`e1350963…` over BOM-stripped LF bytes),
reruns the evidence commands, and returns PASS/REOPEN.
Evidence identities: HEAD `3e9635ba1cf0255d5a09f370e91d1ddb73cef888`; spec
`e13509636180721517a1a1523fdabdcfcf4e6650639612a1b1ccdae8b3ebad7b`; report
this file; new tests `tests/test_w28_jobs_identity_refresh.py`.

```text
FIX-A: JobIdentity tuple (profile/cluster/provider/session/array) + same-target/cancel gates
DEF: DEF-W28-006
Root cause: bare job-ID strings with no framework-neutral identity owner
Before EV: no tuple module (source-read finding)
After EV: 4 identity tests pass
Regression test: test_w28_job_identity_* (4)
Sensitivity proof: each drift axis (profile/cluster/provider/session/array) blocks same_target + cancel

FIX-B: JobsRefreshState machine (idle->refreshing->success/failure) + monotonic anti-overwrite + stale marking
DEF: DEF-W28-001/002
Root cause: bool in_flight + silent error pass + no listing sequence
Before EV: failures silent, no timestamp/stale/sequence
After EV: 4 machine + 3 wx refresh/selection tests pass
Regression test: test_w28_refresh_* + test_w28_wx_refresh_*
Sensitivity proof: stale True with data / False without; old-seq success+failure discarded

Additional fixes: FIX-C parser exit/safe-state guards; FIX-D semantic filter/sort + cancel double gate
Post-green review: POST_GREEN_REVIEW (above, no new defect)
New/modified tests: tests/test_w28_jobs_identity_refresh.py (new, 23 tests)
Skipped/xfail changes: none
Package evidence: N/A (no owned packaging requirement; justification above)
External evidence: EXTERNAL_BLOCKED (lab key auth unavailable; host reachable)
Open P0/P1: none (owned scope)
Open P2/P3: none (OBS-W28-007 is process observation)
Two-fix gate: PASS
Wave decision: READY_FOR_AUDIT
```
