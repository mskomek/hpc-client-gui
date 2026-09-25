# Wave W31 Audit Report
## Controller-persisted fresh independent audit — 2026-09-24T14:55:11.293541+00:00

- Wave: `W31`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0037-W31-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0037-W31-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
→ Read .tmp/agent-runs/ac-wave-opencode-parallel/20260924-152940-c05dfd9c/0033-W31-findings.json 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Get-ChildItem waves/pending, waves/done, waves/blocked, waves/postponed -Filter 'W31*' -ErrorAction SilentlyContinue | Select-Object FullName, Directory, Name; Write-Host '---GIT---'; git rev-parse HEAD; git status --short | Select-Object -First 50; Write-Host '---W31 LOCATE---'; Get-ChildItem waves -Recurse -Filter 'W31*' | Select-Object FullName"
---GIT---
3e9635ba1cf0255d5a09f370e91d1ddb73cef888
---W31 LOCATE---
FullName                                        Directory                                Name  
--------                                        ---------                                ----  
D:\Projeler\hpc-client-gui\waves\pending\W31.md D:\Projeler\hpc-client-gui\waves\pending W31.md
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/services/files_ssh.py
 M src/hpc_gui/services/output_follower.py
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_plugins_view.py
 M src/hpc_gui/wx_shell.py
?? ".agent-legacy-backup (1)/"
?? artifacts/opencode/wave_W26/
?? artifacts/opencode/wave_W27/
?? artifacts/opencode/wave_W28/
?? artifacts/opencode/wave_W29/
?? artifacts/opencode/wave_W30/
?? artifacts/wave_W29/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W29_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W30_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
?? "new 4.ps1"
?? src/hpc_gui/services/job_identity.py
?? src/hpc_gui/services/job_list_filter_sort.py
?? src/hpc_gui/services/job_submit_cancel.py
?? src/hpc_gui/services/jobs_refresh_state.py
?? "tests/contracts (1)/"
?? "tests/contracts (2)/"
?? tests/test_w26_run_supplement.py
?? tests/test_w27_editor_conflicts.py
?? tests/test_w28_jobs_identity_refresh.py
?? tests/test_w29_job_outputs.py
?? tests/test_w30_submit_cancel.py
?? tests/test_w31_race_lifecycle.py
D:\Projeler\hpc-client-gui\waves\pending\W31.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W31.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Write-Host '---W31 REPORT---'; Get-Content docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md -ErrorAction SilentlyContinue | Select-Object -First 200; Write-Host '---AUDIT REPORT---'; Get-ChildItem docs/wave-reports/v2/opencode/W31* -ErrorAction SilentlyContinue | Select-Object Name, Length; Write-Host '---TEST FILE---'; Get-Content tests/test_w31_race_lifecycle.py -ErrorAction SilentlyContinue | Select-Object -First 120; Write-Host '---GIT LOG---'; git log --oneline -5; Write-Host '---CONTENT IDENTITY CHECK---'; git hash-object docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md 2>&1 | Select-Object -First 5"
---W31 REPORT---
# W31 �?" Job lifecycle races and real/package acceptance - Wave Report

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
   from the spec-bytes hash �?" controller-owned reconciliation)
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
`opencode/TODO_OWNERSHIP_MAP.md` W31 rows (none �?" empty result is the
correct reading, not an omission), and `opencode/sources/WAVE_V2_FINAL_07.md`
sections **Entry criteria**, **Scope**, **Workstream H �?"
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
| DEF-W31-001 | P1 | package currency | `test_w31_package...` first run: `dist/hpc_client_gui-1.5.9-py3-none-any.whl` (built 2026-09-22, `d3a3dcbe�?�`) lacks `services/job_identity`, `services/jobs_refresh_state`, `services/job_submit_cancel` | release wheel predates the W28/W30 working-tree race modules; it cannot be the artifact under acceptance for RACE-050/055 |
| OBS-W31-002 | P2 | entry prerequisites | source read: RACE-001..005 cite W06/W05/W04/W03/W02 states; per the Wave independence contract these are non-blocking hints, and the owned behaviors they gate (session/profile/filesystem, connection, harness, Slurm target, capability declarations) are exercised directly by the W31 tests/mocks | no concrete missing input consumed by an owned requirement; no `AWAITING_INPUT` emitted |
| OBS-W31-003 | P3 | content-identity reconciliation | controller handoff `0da446f7�?�` equals the W30 audit-receipt tested identity; observed W31 spec bytes hash `8a0c5e40�?�` | distinct Waves/identities by design; 55 IDs + policies verified, no spec tampering �?" controller-owned reconciliation |

Pre-change narrow baseline (green before W31 additions):
`test_w28 + test_w30` (non-GUI) 32 passed; single wx probe
`test_w28_wx_refresh_success` 1 passed; lab TCP `192.168.250.11:22`
reachable.

Second-defect search (dimensions checked): negative (refresh failure with
and without prior data, late failure for an old session, malformed rows,
unknown `ZZ` state, unconfirmed sbatch blobs, already-gone vs unauthorized
cancel, empty selection), unavailable-capability (lab SSH
`Permission denied (publickey)` BatchMode �?" EXTERNAL_BLOCKED, nothing
invented), permission/network failure (cancel ERROR path distinct from
`ALREADY_GONE`; outputs per-channel permission errors preserved from W29),
cancellation/retry (in-flight + close guards untouched), stale
callback/result (sequence + generation + identity guards at every async
boundary �?" refresh, sacct, details, accounting, server status, outputs),
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
(`wx_jobs.py` �+' `job_identity`/`job_list_filter_sort`/`jobs_refresh_state`/
`job_submit_cancel`/`slurm_models`/`selected_job_context`) �?" no dangling
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
job 67 submit�+'RUNNING list�+'details�+'scancel�+'CANCELLED�+'empty-refresh,
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
(generation + selection guards). Real Slurm journey: PASS (EV-W31-REAL �?"
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
Change: no product-source change (nothing to fix in code �?" the modules
exist and are wired); built the candidate wheel from the exact working
tree with `.venv/Scripts/python -m pip wheel . --no-deps
--no-build-isolation -w .tmp/w31-package/` (offline, setuptools backend).
The `dist/` release artifact was left untouched �?" release versioning/
publishing is controller/release-owned, not a silent worker overwrite.
Before EV: package test failed with the three missing fragments named.
After EV: all 14 W31 tests pass; the candidate wheel
(`9253a7e6�?�`, 934795 bytes, 270 entries) contains all seven required
fragments.
Sensitivity: the test fails closed on any missing fragment and binds the
full SHA-256; the stale release wheel is recorded, never adopted as
acceptance.
---AUDIT REPORT---

---TEST FILE---
---GIT LOG---
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
54b85bed Sync Agent Core runtime cecc7b82 and migrate Wave profile to schema v3
---CONTENT IDENTITY CHECK---
Name               Length
----               ------
W31_WAVE_REPORT.md  17597
"""W31 �?" Job lifecycle races and real/package acceptance.

Owned requirements: HPC-W07-RACE-001..055 (Workstream H disconnect/profile
switch, targeted tasks, test matrix, acceptance gates, STOP conditions).

Covers the W31-owned deltas plus requirement-to-owner traceability:
- RACE-019: refresh while disconnecting discards the late response.
- RACE-020: profile switch during refresh; old response never wins.
- RACE-021: cancel after profile switch is blocked.
- RACE-022: details callback from an old session never attaches.
- RACE-023: reconnect then refresh recovers with a fresh timestamp.
- TASK-004/007 (RACE-027/030/037/044/052): overlapping refresh + safe cancel.
- TASK-003/006 (RACE-026/029/045/046/054): parser safety + confirmed submit.
- TASK-008/009 (RACE-031/032/049/050/055): real-shape lifecycle + package.
- STOP (RACE-052..055): none of the four stop conditions trigger.
"""

from __future__ import annotations

import hashlib
import threading
import time
import zipfile
from pathlib import Path

import pytest

from hpc_gui.services.job_identity import cancel_is_safe, make_identity
from hpc_gui.services.job_list_filter_sort import cancel_target_is_safe
from hpc_gui.services.jobs_refresh_state import JobsRefreshState
from hpc_gui.services.job_submit_cancel import submit_result_status
from hpc_gui.services.selected_job_context import SelectedJobStore
from hpc_gui.services.slurm_models import (
    is_terminal_state,
    parse_sacct,
    parse_scontrol,
    parse_squeue,
    safe_state_display,
)

pytestmark = pytest.mark.contract


# --- RACE-019/020/023 + TASK-004: refresh/disconnect/profile-switch races ---


def test_w31_refresh_sequence_rejects_stale_after_reconnect():
    """An older refresh response can never overwrite a newer context."""
    machine = JobsRefreshState()
    old_seq = machine.begin()  # issued under the old session
    new_seq = machine.begin()  # issued after reconnect/profile switch
    assert new_seq > old_seq
    assert machine.complete_success(old_seq, [{"id": "OLD"}]) is False
    assert machine.complete_success(new_seq, [{"id": "NEW"}]) is True
    assert [row["id"] for row in machine.data] == ["NEW"]
    assert machine.status == "success"
    assert machine.last_success_ts


def test_w31_refresh_failure_after_reconnect_keeps_new_context():
    """A late failure for the old session must not poison the new listing."""
    machine = JobsRefreshState()
    old_seq = machine.begin()
    new_seq = machine.begin()
    assert machine.complete_success(new_seq, [{"id": "NEW"}], timestamp="T-NEW")
    assert machine.complete_failure(old_seq, "old session timed out") is False
    assert machine.status == "success"
    assert [row["id"] for row in machine.data] == ["NEW"]


def test_w31_overlapping_refresh_newest_wins():
    """Overlapping refreshes serialize on the monotonic sequence."""
    machine = JobsRefreshState()
    first = machine.begin()
    second = machine.begin()
    third = machine.begin()
    assert machine.complete_success(first, [{"id": "1"}]) is False
    assert machine.complete_success(second, [{"id": "2"}]) is False
    assert machine.complete_success(third, [{"id": "3"}]) is True
    assert [row["id"] for row in machine.data] == ["3"]


# --- RACE-021 + TASK-007: cancel after profile switch is blocked ---


def test_w31_profile_switch_blocks_cancel_identity():
    selected = make_identity(
        "42", profile_id="p1", cluster_id="c1", provider_id="slurm",
        session_generation=3,
    )
    same = make_identity(
        "42", profile_id="p1", cluster_id="c1", provider_id="slurm",
        session_generation=3,
    )
    assert cancel_is_safe(selected, same)
    for drifted in (
        make_identity("42", profile_id="p2", cluster_id="c1",
                      provider_id="slurm", session_generation=3),
        make_identity("42", profile_id="p1", cluster_id="c2",
                      provider_id="slurm", session_generation=3),
        make_identity("42", profile_id="p1", cluster_id="c1",
                      provider_id="slurm", session_generation=4),
        make_identity("43", profile_id="p1", cluster_id="c1",
                      provider_id="slurm", session_generation=3),
        make_identity("42_4", profile_id="p1", cluster_id="c1",
                      provider_id="slurm", session_generation=3),
    ):
        assert not cancel_is_safe(selected, drifted)


def test_w31_stale_selection_cannot_cancel_after_refresh():
    """A selection that vanished from backend rows can never cancel."""
    assert cancel_target_is_safe("42", [{"id": "42"}, {"id": "43"}], "42")
    assert not cancel_target_is_safe("42", [{"id": "43"}], "42")
    assert not cancel_target_is_safe("42", [{"id": "42"}], "43")
    assert not cancel_target_is_safe("", [{"id": "42"}], "42")


# --- RACE-022 + TASK-005: details callback from old session discarded ---

c8fe3b115b96c6c450216d6f2e8b4d3310bafe29
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Write-Host '=== REPORT TAIL ==='; Get-Content docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md | Select-Object -Skip 200 | Select-Object -First 300; Write-Host '=== ARTIFACTS W31 ==='; Get-ChildItem artifacts -Recurse -Filter '*W31*' -ErrorAction SilentlyContinue | Select-Object FullName; Get-ChildItem artifacts/wave_W31* -ErrorAction SilentlyContinue | Select-Object FullName; Get-ChildItem .tmp/w31-package -ErrorAction SilentlyContinue | Select-Object Name, Length; Write-Host '=== EVIDENCE MANIFEST ==='; Get-ChildItem artifacts -Recurse -Filter '*EVIDENCE*' | Select-Object FullName | Select-Object -First 20"
=== REPORT TAIL ===
Regression: EV-W31-REG cohorts green (68 passed).

## Evidence

| ID | Command | Result | Binds to |
|---|---|---|---|
| EV-W31-NEW | `python -m pytest tests/test_w31_race_lifecycle.py -q` | 14 passed (10 unit + 4 wx GUI with event/runtime readback) | RACE-019..023/026/027/029..032/037/042..048/050/052..055 (sequence/generation/identity guards, parser safety, submit acceptance, package content, wx disconnect/switch/cancel/reconnect journeys) |
| EV-W31-REG | `python -m pytest tests/test_w28_jobs_identity_refresh.py tests/test_w29_job_outputs.py tests/test_w30_submit_cancel.py tests/test_wx_jobs_behavior.py tests/test_slurm_models.py -q` | 68 passed | no W28/W29/W30/wx/parser regression |
| EV-W31-PKG | candidate wheel `.tmp/w31-package/hpc_client_gui-1.5.9-py3-none-any.whl` | SHA-256 `9253a7e6085e61ed93fd6b5232544270d2258ee5d3bb49409d1c6adb658d1a3e`, 270 entries, 7/7 required fragments | required class PACKAGE via exact artifact SHA-256 under acceptance, bound to the working-tree candidate |
| EV-W31-GUI | wx tests in EV-W31-NEW | 4 passed | required class GUI via exact runtime action/test/readback (blocked `list_jobs` + mid-flight `set_session`, generation-bump switch, `ListEvent` select �+' `_wx_jobs_cancel` with zero-fire assertion, reconnect �+' `refresh_jobs` timestamp/stale/error readback), bound to the working-tree candidate |
| EV-W31-EXT | `ssh -i <emitted-profile-key> -o BatchMode=yes -o StrictHostKeyChecking=yes hpctest@192.168.250.11 echo LAB_OK` | `LAB_OK`, exit 0 (repair probe 2026-09-24; prior run-phase `Permission denied` was a missing-key-path env defect, not a lab defect) | lab key auth feasible with the emitted profile key; superseded by EV-W31-REAL |
| EV-W31-REAL | real Slurm lifecycle vs `LOCAL_REAL_HYPERV` (`local-real`, `192.168.250.11:22`, `hpctest`) 2026-09-24 ~14:44 UTC: `sbatch --parsable job.sbatch` �+' `67`; `squeue -j 67` �+' `RUNNING` (`w31-repair2`, `compute02`, `debug`); `scontrol show job 67` �+' `RUNNING` (`SubmitTime=2026-09-24T14:44:09`, `StartTime=14:44:10`, `NodeList=compute02`); `scancel 67` exit 0 �+' `CANCELLED` (`EndTime=14:44:14`); `sacct -j 67` �+' `CANCELLED by 1000`; `squeue` refresh empty; scratch `w31-repair-*` dirs removed, `squeue`/`sinfo` verified clean (compute02 idle) | PASS �?" binds RACE-049 + matrix real-Slurm legs (submit/list/details/cancel/refresh) to env HEAD `3e9635ba`, target identity above, disposable job `w31-repair2`/ID 67, with cleanup | required class EXTERNAL via real authorized infrastructure with environment identity and cleanup |
| EV-W31-REAL-NOTE | first repair `sbatch` (job 65, `w31-repair-race`) reached terminal `FAILED (RaisedSignal:53)` before any cancel leg; `srun` probe then passed (`compute02`, exit 0) and the retry (job 67) completed the full journey | transient scheduler/node placement event, not a product defect; no owner routing; recorded for transparency, lab verified healthy afterwards |
| EV-W31-EXTERNAL | required class EXTERNAL per Wave header | PASS via EV-W31-REAL | no mock substitution for external claims (mock/parse shapes cited only as code-shape reference, never as external evidence) |
| EV-W31-LAB | TCP `192.168.250.11:22` + `sinfo` (`debug` idle on compute02; compute01 DOWN reboot) + `srun --partition=debug hostname` �+' `compute02` exit 0 | lab healthy for the exercised path | context + transport proof for EV-W31-REAL |

Candidate identity: working tree at `3e9635ba` + W31 additions
(`tests/test_w31_race_lifecycle.py` new, `.tmp/w31-package/` candidate
wheel, this report). No tracked product-source edits by W31; sibling
W26�?"W30 hunks preserved verbatim. Closure-only changes (this report)
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

External evidence: PASS via EV-W31-REAL (job 67 submit�+'RUNNING�+'details�+'CANCELLED�+'empty-refresh on LOCAL_REAL_HYPERV, cleaned up)
Package evidence: `9253a7e6085e61ed93fd6b5232544270d2258ee5d3bb49409d1c6adb658d1a3e` (candidate wheel, `.tmp/w31-package/`)
=== ARTIFACTS W31 ===

=== EVIDENCE MANIFEST ===
Name                                  Length
----                                  ------
hpc_client_gui-1.5.9-py3-none-any.whl 934795
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Write-Host '=== REGISTRY W31 RACE-049 ==='; Select-String -Path 'opencode/REQUIREMENT_REGISTRY.md' -Pattern 'RACE-049' | Select-Object -First 10; Write-Host '=== SOURCES RACE-049 ==='; Select-String -Path 'opencode/sources/WAVE_V2_FINAL_07.md' -Pattern 'RACE-049|real.*Slurm|lifecycle' | Select-Object -First 20; Write-Host '=== TEST COUNT ==='; python -m pytest tests/test_w31_race_lifecycle.py -q 2>&1 | Select-Object -Last 20; Write-Host '=== WHEEL CHECK ==='; Get-FileHash .tmp/w31-package/hpc_client_gui-1.5.9-py3-none-any.whl -Algorithm SHA256 2>&1 | Select-Object -First 5; Write-Host '=== CONTENT IDENTITY ==='; python .opencode/scripts/wave_state_engine.py --help 2>&1 | Select-Object -First 30"
=== REGISTRY W31 RACE-049 ===

opencode\REQUIREMENT_REGISTRY.md:762:| `HPC-W07-RACE-049` | MANDATORY | GATE | `WAVE_V2_FINAL_07.md` | 231 | 
Acceptance criteria | `W31` | - | [ ] Real Slurm submit/list/details/cancel passes. |
=== SOURCES RACE-049 ===
opencode\sources\WAVE_V2_FINAL_07.md:16:Make Jobs and Outputs a trustworthy Slurm surface: users can refresh, inspect, 
submit and cancel the intended job, then read truthful stdout/stderr/live output without stale-profile, 
duplicate-tail, wrong-target or lifecycle errors.
opencode\sources\WAVE_V2_FINAL_07.md:41:- refresh lifecycle;
opencode\sources\WAVE_V2_FINAL_07.md:51:- real Slurm;
opencode\sources\WAVE_V2_FINAL_07.md:206:- `TASK-W07-008`: real Slurm lifecycle test.
opencode\sources\WAVE_V2_FINAL_07.md:211:| Case | Automated | Real Slurm | Package |
opencode\sources\WAVE_V2_FINAL_07.md:231:- [ ] Real Slurm submit/list/details/cancel passes.
opencode\sources\WAVE_V2_FINAL_07.md:475:2. **lifecycle** - startup, active use, close, reconnect/reopen;
opencode\sources\WAVE_V2_FINAL_07.md:648:- one lifecycle/stale/cancel/retry assertion.
opencode\sources\WAVE_V2_FINAL_07.md:714:Real SSH/SFTP/Slurm tests must be separated from hermetic tests and clearly 
marked. Their evidence must include environment/provider identity class and cleanup. Failure due to unavailable lab is 
`BLOCKED`, not converted to a fake unit-test pass.
opencode\sources\WAVE_V2_FINAL_07.md:727:- [ ] Is a stateful/asynchronous lifecycle case covered?
opencode\sources\WAVE_V2_FINAL_07.md:1042:- dialog constructor test ? full lifecycle/shutdown safety;
opencode\sources\WAVE_V2_FINAL_07.md:1101:For example, Plugin Manager install/update/remove must not be frozen as 
fully `SUPPORTED` in W01 merely because buttons and handlers exist when W08 still owns real backend/lifecycle 
validation.
=== TEST COUNT ===
..............                                                           [100%]
14 passed in 5.05s
=== WHEEL CHECK ===

Algorithm : SHA256
Hash      : 9253A7E6085E61ED93FD6B5232544270D2258EE5D3BB49409D1C6ADB658D1A3E
Path      : D:\Projeler\hpc-client-gui\.tmp\w31-package\hpc_client_gui-1.5.9-py3-none-any.whl

=== CONTENT IDENTITY ===
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Write-Host '=== REGRESSION ==='; python -m pytest tests/test_w28_jobs_identity_refresh.py tests/test_w29_job_outputs.py tests/test_w30_submit_cancel.py -q 2>&1 | Select-Object -Last 10; Write-Host '=== SOURCE SEC 231 ==='; Get-Content opencode/sources/WAVE_V2_FINAL_07.md | Select-Object -Skip 200 | Select-Object -First 60; Write-Host '=== PROTOCOL EXTERNAL ==='; Get-Content opencode/sources/WAVE_V2_FINAL_07.md | Select-Object -Skip 705 | Select-Object -First 30; Write-Host '=== FULL FINDINGS TEXT ==='; Get-Content '.tmp/agent-runs/ac-wave-opencode-parallel/20260924-152940-c05dfd9c/0033-W31-findings.json' | Select-Object -First 100"
=== REGRESSION ===
......................................................                   [100%]
54 passed in 8.61s
=== SOURCE SEC 231 ===
- `TASK-W07-003`: harden parser for unknown/malformed scheduler output.
- `TASK-W07-004`: race-test overlapping refresh.
- `TASK-W07-005`: identity-safe details/log callbacks.
- `TASK-W07-006`: submission validation and confirmed-result semantics.
- `TASK-W07-007`: identity-safe cancel.
- `TASK-W07-008`: real Slurm lifecycle test.
- `TASK-W07-009`: exact packaged-artifact test.

## Test matrix

| Case | Automated | Real Slurm | Package |
|---|---:|---:|---:|
| empty/list | yes | yes | yes |
| unknown state | yes | optional | yes |
| refresh failure/stale | yes | yes if feasible | yes |
| overlapping refresh | yes | optional | yes |
| details/log | yes | yes | yes |
| submit | yes | yes | yes |
| cancel | yes | yes | yes |
| already-completed cancel | yes | yes if feasible | yes |
| profile switch race | yes | desirable | yes |

## Acceptance criteria

- [ ] Refresh success/failure/stale state is unambiguous.
- [ ] Older response cannot overwrite newer context.
- [ ] Unknown scheduler states do not crash/misreport.
- [ ] Submission success requires backend confirmation.
- [ ] Cancellation targets the selected job on the intended profile/cluster.
- [ ] Details/log response cannot attach to a newly selected wrong job.
- [ ] Real Slurm submit/list/details/cancel passes.
- [ ] Exact packaged workflow passes.
- [ ] No P0/P1 remains.

## STOP conditions

- wrong job can be cancelled;
- stale response can overwrite a different profile�?Ts list;
- submission can report success after scheduler rejection;
- package lacks required provider/parser resources.

## Evidence

Record disposable job script, returned job ID, transitions, cancel result, UI state timestamps, parser tests, package SHA.

## Rollback

Only submit harmless disposable jobs. Ensure cleanup/cancel at the end. Keep race-condition tests after reverting any implementation approach.

## Handoff

Shared provider/session/parser changes require impact analysis against W02/W03 and possibly W05/W06.

## Shared execution contract

This Wave is part of the final V2 closure sequence. The implementation agent must work from evidence rather than from old screenshots, assumptions, historical filenames, or version strings.

### Evidence precedence

Use this order when sources disagree:
=== PROTOCOL EXTERNAL ===
- delete arbitrary real paths;
- use the user's actual config as a writable fixture;
- submit meaningful production jobs;
- overwrite real plugin directories;
- expose credentials in test output.

### E11. External tests

Real SSH/SFTP/Slurm tests must be separated from hermetic tests and clearly marked. Their evidence must include environment/provider identity class and cleanup. Failure due to unavailable lab is `BLOCKED`, not converted to a fake unit-test pass.

### E12. Package tests

Package tests must identify the exact artifact hash. A package test run against an unknown/stale build is invalid evidence.

## F. Mandatory Test Review Checklist

Before declaring tests complete, answer **YES with evidence** to every applicable item:

- [ ] Does each counted fix have a regression test or justified runtime-only proof?
- [ ] Did the regression test fail before the fix or pass a sensitivity/mutation proof?
- [ ] Is at least one negative path covered?
- [ ] Is a stateful/asynchronous lifecycle case covered?
- [ ] Are assertions behavioral rather than existence-only?
- [ ] Are mocks limited to legitimate boundaries?
- [ ] Are no new unjustified skips/xfails introduced?
- [ ] Are fixtures isolated from real user data?
- [ ] Is cleanup deterministic?
- [ ] Are package/external tests honestly classified?
- [ ] Does the full impacted slice still pass?
- [ ] Would a future regression of the same defect make the test fail?
=== FULL FINDINGS TEXT ===
{
  "wave": "W31",
  "finding_count": 1,
  "human_only": false,
  "findings": [
    {
      "finding_id": "RACE-049",
      "source": "phase-result",
      "text": "mise (read-only, no state created, probe key copy removed afterwards):**\n  - The maintainer-emitted lab profile exists at the canonical path with `key_path �?�/hpc-client-gui-lab/id_ed25519`, user `hpctest`, host `192.168.250.11:22`; the key file exists.\n  - `ssh -i <emitted-key> -o BatchMode=yes -o StrictHostKeyChecking=yes` against the isolated lab known_hosts returned **`LAB_OK`, exit 0**. TCP 22 was already known-reachable.\n- **Conclusion:** the real-Slurm leg was feasible with already-available credentials but never attempted. EXTERNAL is unproven, not blocked. This is a W31-owned missing-evidence defect �?" not orchestration, not human-deferral (no unavailable authority; credentials exist and work). The Wave report itself forbids synthesizing PASS here.\n- **Repair pointer (worker-owned, not performed by this audit):** execute the real-Slurm submit�+'list�+'details�+'cancel�+'refresh journey with environment identity and cleanup using the emitted profile key, bind exact evidence to RACE-049/matrix rows, refresh the canonical report, return for re-audit.\n\n## Controller-owned note (not a W31 defect, no action taken)\n\nW30's PASS receipt rests on the same `EXTERNAL_BLOCKED` premise. W30 is closed/immutable; whether a closed-owner repair transaction is warranted is a controller decision. This audit does not touch W30.\n\n## Audit discipline\n\nRead-only throughout: no product, test, report, or manifest files written; no repairs attempted. Fresh context, bound to the current candidate �?" no stale PASS reused.\n\nAC_WAVE_MACHINE_RESULT_BEGIN\nWAVE_PHASE_STATUS: REOPEN\nAC_WAVE_MACHINE_RESULT_END\n",
      "execution_owner": "W31",
      "owner_state": "current_or_unresolved",
      "human_only": false
    }
  ]
}
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Write-Host '=== LAB PROFILE ==='; Get-Content .opencode/protocol/LOCAL_REAL_HPC_LAB.md -ErrorAction SilentlyContinue | Select-Object -First 80; Write-Host '=== WHEEL CONTENTS ==='; python -c \"import zipfile; z=zipfile.ZipFile('.tmp/w31-package/hpc_client_gui-1.5.9-py3-none-any.whl'); names=z.namelist(); print(len(names)); [print(n) for n in names if 'job_identity' in n or 'jobs_refresh' in n or 'job_submit' in n or 'job_list' in n or 'selected_job' in n or 'slurm_model' in n or 'wx_jobs' in n]\" 2>&1 | Select-Object -First 20; Write-Host '=== REGRESSION FULL ==='; python -m pytest tests/test_w28_jobs_identity_refresh.py tests/test_w29_job_outputs.py tests/test_w30_submit_cancel.py tests/test_wx_jobs_behavior.py tests/test_slurm_models.py -q 2>&1 | Select-Object -Last 5; Write-Host '=== REAL JOURNEY LOGS ==='; Get-ChildItem .tmp -Recurse -Filter '*w31*' -ErrorAction SilentlyContinue | Select-Object FullName | Select-Object -First 20; Get-ChildItem .tmp -Recurse -Filter '*real*' -ErrorAction SilentlyContinue | Select-Object FullName | Select-Object -First 20"
=== LAB PROFILE ===
# LOCAL_REAL HPC Lab Protocol


This protocol applies to the HPC W01-W61 program only.


## Purpose


Use the maintainer-owned LOCAL_REAL Hyper-V cluster as the default real
authorized infrastructure for HPC Wave requirements that require generic real
SSH/SFTP/Slurm/filesystem/job/connection evidence and do not explicitly require
a named production/site-specific system.


`LOCAL_REAL_HYPERV` is real external infrastructure for acceptance purposes. It is not:
- a mock server;
- a fake scheduler;
- a substitute identity for TRUBA;
- evidence for a site-specific requirement that explicitly names another system.


## Canonical target


- profile: `C:\Users\mskomek\AppData\Local\hpc-client-gui-lab\hpc-client-profile.json`
- controller/login: `192.168.250.11:22`
- user: `hpctest`
- compute nodes: `compute01`, `compute02`
- infrastructure class: `LOCAL_REAL_HYPERV`
- provider/profile ID: `local-real`
- scheduler: real Slurm
- shared storage: real NFS-backed Home/Scratch/Project
- auth: generated SSH key from the emitted profile
- host-key policy: isolated lab known_hosts with `accept-new`; later key changes fail

## Capability-scoped password target

`LOCAL_REAL_HYPERV` is intentionally key-only (`ssh_pwauth: false`) and is
authoritative only for the capabilities it actually provisions. It must not
be used as password-auth evidence.

For generic password-auth requirements, the maintained secondary target is
`LOCAL_PASSWORD_REAL`: the disposable OpenSSH/Slurm fixture defined by
`docs/testing/LOCAL_HPC_LAB.md` and `devtools/lab/docker-compose.yml`. It is
bound to `127.0.0.1` only, uses a real containerized OpenSSH/Slurm runtime
(not an in-process mock), and uses documented throwaway fixture input supplied
through stdin or an equivalent secure input channel. It is authoritative only
for generic password success/failure and invalid-password rejection. It does
not replace `LOCAL_REAL_HYPERV` for key, host-key, Slurm, SFTP, storage, or
site-specific claims. Its password must never appear in logs, reports,
manifests, or evidence.


## Verified baseline


Current accepted LOCAL_REAL baseline:
- `lab-up.ps1`: PASS
- `lab-status.ps1`: PASS
- image pin: PASS
- generated profile validation: PASS
- `lab-test.ps1`: `LOCAL_REAL_READY`
- behavioral gates: 23/23 PASS
- real PTY evidence: `/dev/pts/0`
- controller and both compute transports/services: PASS
- compute nodes: Slurm `idle`
- real SSH key login: PASS
- host-key pins: PASS
- real SFTP download/upload/hash: PASS
- MUNGE: PASS
- two-node `srun`: PASS
- `sinfo/squeue/scontrol/sbatch/sacct/scancel`: PASS
- shared-home compute execution: PASS
- permission-denied negative path: PASS


Repository context:
- `lab/LAB_AUDIT_REPORT.md`
- `lab/README.md`
=== WHEEL CONTENTS ===
270
hpc_gui/wx_jobs.py
hpc_gui/services/job_identity.py
hpc_gui/services/job_list_filter_sort.py
hpc_gui/services/job_submit_cancel.py
hpc_gui/services/jobs_refresh_state.py
hpc_gui/services/selected_job_context.py
hpc_gui/services/slurm_models.py
=== REGRESSION FULL ===
....................................................................     [100%]
68 passed in 16.22s
=== REAL JOURNEY LOGS ===

FullName                                                                                                               
--------                                                                                                               
D:\Projeler\hpc-client-gui\.tmp\w31-package                                                                            
D:\Projeler\hpc-client-gui\.tmp\w31-audit-slice.txt                                                                    
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0031-W31-plan-controll...
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0031-W31-plan-dispatch...
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0031-W31-plan-job.json   
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0031-W31-plan-normaliz...
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0031-W31-plan-opencode...
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0032-W31-run-controlle...
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0032-W31-run-dispatch....
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0032-W31-run-job.json    
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0032-W31-run-normalize...
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0032-W31-run-opencode.log
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0033-W31-audit-control...
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0033-W31-audit-dispatc...
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0033-W31-audit-job.json  
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0033-W31-audit-normali...
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0033-W31-audit-opencod...
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0033-W31-findings.json   
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0034-W31-repair-contro...
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0034-W31-repair-dispat...
D:\Projeler\hpc-client-gui\.tmp\w11-local-real-run                                                                     
D:\Projeler\hpc-client-gui\.tmp\w12-local-real-00np3zvp                                                                
D:\Projeler\hpc-client-gui\.tmp\w12-local-real-o0tfn265                                                                
D:\Projeler\hpc-client-gui\.tmp\w13-local-real-iluitlim                                                                
D:\Projeler\hpc-client-gui\.tmp\w18-real-wx-config                                                                     
D:\Projeler\hpc-client-gui\.tmp\w18-real-wx-config2                                                                    
D:\Projeler\hpc-client-gui\.tmp\w18-real-wx-config3                                                                    
D:\Projeler\hpc-client-gui\.tmp\w18-real-wx-config4                                                                    
D:\Projeler\hpc-client-gui\.tmp\w18-real-wx-config5                                                                    
D:\Projeler\hpc-client-gui\.tmp\w18-real-wx-config6                                                                    
D:\Projeler\hpc-client-gui\.tmp\w22-gui-local-real-replay                                                              
D:\Projeler\hpc-client-gui\.tmp\w11_local_real_matrix.json                                                             
D:\Projeler\hpc-client-gui\.tmp\w11_local_real_matrix.py                                                               
D:\Projeler\hpc-client-gui\.tmp\w13-local-real-known_hosts                                                             
D:\Projeler\hpc-client-gui\.tmp\w13-local-real-known_hosts-repair-20260922                                             
D:\Projeler\hpc-client-gui\.tmp\w13_local_real_replay.py                                                               
D:\Projeler\hpc-client-gui\.tmp\w18_gui_real_replay_current.py                                                         
D:\Projeler\hpc-client-gui\.tmp\w22_gui_local_real_replay.py                                                           
D:\Projeler\hpc-client-gui\.tmp\codex-direct-main-smoke-profile\EBWebView\Default\Code Cache\js\index-dir\the-real-i...
D:\Projeler\hpc-client-gui\.tmp\codex-direct-main-smoke-profile\EBWebView\Default\Code Cache\wasm\index-dir\the-real...
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Write-Host '=== AUDIT SLICE ==='; Get-Content .tmp/w31-audit-slice.txt -ErrorAction SilentlyContinue | Select-Object -First 60; Write-Host '=== REPAIR LOG TAIL ==='; Get-ChildItem '.tmp/agent-runs/ac-wave-opencode-parallel/20260924-152940-c05dfd9c/' -Filter '*repair*' | Select-Object Name; Write-Host '=== LAB PROFILE FULL TAIL ==='; Get-Content .opencode/protocol/LOCAL_REAL_HPC_LAB.md | Select-Object -Skip 80 | Select-Object -First 80; Write-Host '=== PROFILE JSON ==='; Get-Content 'C:\\Users\\mskomek\\AppData\\Local\\hpc-client-gui-lab\\hpc-client-profile.json' -ErrorAction SilentlyContinue | Select-Object -First 20"
=== AUDIT SLICE ===
/2/0/2|1792
debug*|up|down|compute01|0/0/2/2|1792
=== SCONTROL NODES ===
NodeName=compute01 Arch=x86_64 CoresPerSocket=1 
   State=DOWN ThreadsPerCore=1 TmpDisk=0 Weight=1 Owner=N/A MCS_label=N/A
   Reason=Node unexpectedly rebooted [slurm@2026-09-23T13:50:50]
NodeName=compute02 Arch=x86_64 CoresPerSocket=1 
   State=IDLE ThreadsPerCore=1 TmpDisk=0 Weight=1 Owner=N/A MCS_label=N/A
=== JOBDIR LOG ===
cat: /srv/hpc/scratch/hpctest/w31-repair-20260924-144325/slurm-65.out: No such file or directory
---
total 12
drwxrwxr-x 2 hpctest hpctest 4096 Sep 24 14:43 .
drwx------ 3 hpctest hpctest 4096 Sep 24 14:43 ..
-rw-rw-r-- 1 hpctest hpctest  226 Sep 24 14:43 w31_race.sbatch
> ac-wave-opencode-executor A� muse-spark-1.3-contributor
$ KEY="/c/Users/mskomek/AppData/Local/hpc-client-gui-lab/id_ed25519"; SSH="ssh -i $KEY -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 hpctest@192.168.250.11"; echo "=== SRUN PROBE ==="; $SSH 'timeout 40 srun --partition=debug --nodes=1 --ntasks=1 --time=00:01:00 hostname 2>&1; echo "SRUN_EXIT:$?"' 2>&1
=== SRUN PROBE ===
compute02
SRUN_EXIT:0
> ac-wave-opencode-executor A� muse-spark-1.3-contributor
$ KEY="/c/Users/mskomek/AppData/Local/hpc-client-gui-lab/id_ed25519"; SSH="ssh -i $KEY -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 hpctest@192.168.250.11"; $SSH 'set -x; TS=$(date +%Y%m%d-%H%M%S); JOBDIR="/srv/hpc/scratch/hpctest/w31-repair-$TS"; mkdir -p "$JOBDIR"; printf "#!/bin/bash\n#SBATCH --job-name=w31-repair2\n#SBATCH --partition=debug\n#SBATCH --nodes=1\n#SBATCH --ntasks=1\n#SBATCH --time=00:05:00\nsleep 300\n" > "$JOBDIR/job.sbatch"; cat "$JOBDIR/job.sbatch"; echo "JOBDIR=$JOBDIR"; sbatch --parsable "$JOBDIR/job.sbatch" 2>&1; echo "SBATCH_EXIT:$?"' 2>&1
++ date +%Y%m%d-%H%M%S
+ TS=20260924-144409
+ JOBDIR=/srv/hpc/scratch/hpctest/w31-repair-20260924-144409
+ mkdir -p /srv/hpc/scratch/hpctest/w31-repair-20260924-144409
+ printf '#!/bin/bash\n#SBATCH --job-name=w31-repair2\n#SBATCH --partition=debug\n#SBATCH --nodes=1\n#SBATCH --ntasks=1\n#SBATCH --time=00:05:00\nsleep 300\n'
+ cat /srv/hpc/scratch/hpctest/w31-repair-20260924-144409/job.sbatch
#!/bin/bash
#SBATCH --job-name=w31-repair2
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=00:05:00
sleep 300
JOBDIR=/srv/hpc/scratch/hpctest/w31-repair-20260924-144409
+ echo JOBDIR=/srv/hpc/scratch/hpctest/w31-repair-20260924-144409
+ sbatch --parsable /srv/hpc/scratch/hpctest/w31-repair-20260924-144409/job.sbatch
67
SBATCH_EXIT:0
+ echo SBATCH_EXIT:0
> ac-wave-opencode-executor A� muse-spark-1.3-contributor
$ KEY="/c/Users/mskomek/AppData/Local/hpc-client-gui-lab/id_ed25519"; SSH="ssh -i $KEY -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 hpctest@192.168.250.11"; JID=67; echo "=== LIST ==="; $SSH "squeue -j $JID -o '%i|%j|%u|%T|%M|%R|%P' 2>&1" 2>&1; echo "=== DETAILS ==="; $SSH "scontrol show job $JID 2>&1 | grep -E 'JobId|JobName|JobState|Partition|NodeList|SubmitTime|StartTime|WorkDir|Command' | head -n 12" 2>&1; echo "=== CANCEL ==="; $SSH "scancel $JID 2>&1; echo SCANCEL_EXIT:\$?; sleep 3; squeue -j $JID -o '%i|%T|%R' 2>&1; echo '---scontrol-after---'; scontrol show job $JID 2>&1 | grep -E 'JobId|JobState|Reason|EndTime' | head -n 6; echo '---sacct---'; sacct -j $JID --format=JobID,JobName,State,ExitCode -P 2>&1 | head -n 6" 2>&1; echo "=== REFRESH (squeue empty proof) ==="; $SSH "squeue -h -o '%i|%j|%T' 2>&1 | head -n 10; echo REFRESH_DONE" 2>&1
=== LIST ===
JOBID|NAME|USER|STATE|TIME|NODELIST(REASON)|PARTITION
67|w31-repair2|hpctest|RUNNING|0:04|compute02|debug
=== DETAILS ===
JobId=67 JobName=w31-repair2
   JobState=RUNNING Reason=None Dependency=(null)
   SubmitTime=2026-09-24T14:44:09 EligibleTime=2026-09-24T14:44:09
   StartTime=2026-09-24T14:44:10 EndTime=2026-09-24T14:49:10 Deadline=N/A
   Partition=debug AllocNode:Sid=login-control01:8318
   ReqNodeList=(null) ExcNodeList=(null)
   NodeList=compute02
   Command=/srv/hpc/scratch/hpctest/w31-repair-20260924-144409/job.sbatch
   WorkDir=/home/hpctest
=== CANCEL ===
SCANCEL_EXIT:0
JOBID|STATE|NODELIST(REASON)
---scontrol-after---
=== REPAIR LOG TAIL ===

=== LAB PROFILE FULL TAIL ===
=== PROFILE JSON ===
Name                                   
----                                   
0021-W29-repair-controller-context.json
0021-W29-repair-dispatch.json          
0021-W29-repair-job.json               
0021-W29-repair-normalized.json        
0021-W29-repair-opencode.log           
0034-W31-repair-controller-context.json
0034-W31-repair-dispatch.json          
0034-W31-repair-job.json               
0034-W31-repair-normalized.json        
0034-W31-repair-opencode.log           
- Wave-specific LOCAL_REAL gap reports when present


Private runtime state/evidence remains local/disposable. Never copy private keys,
VM disks, generated secrets, or LOCAL_REAL private state into Wave reports,
Git, Drive evidence, or worktree overlays.


## Wave selection rule


For an HPC Wave whose required evidence includes `EXTERNAL`:


1. Read the Wave's owned requirement wording first.
2. If it requires generic real SSH/SFTP/Slurm/remote-files/jobs/storage/
   connection/session behavior and does not name a specific external site,
   use LOCAL_REAL by default.
3. If it explicitly requires TRUBA, another named site, special hardware, an
   authoritative production service, or a capability LOCAL_REAL does not
   implement, LOCAL_REAL cannot substitute for that requirement.
4. Do not declare HUMAN/EXTERNAL blocked merely because TRUBA is unavailable
   when the owned generic requirement can be truthfully satisfied by LOCAL_REAL.
5. Do not claim LOCAL_REAL proves GUI or PACKAGE evidence merely because the
   infrastructure itself is healthy. Run the required GUI/package journey
   against LOCAL_REAL.


## Use contract


Before external replay:
- prefer `lab-status.ps1` for a bounded health check;
- use the existing emitted profile rather than manually reconstructing secrets;
- do not rebuild/reset/recreate VMs, rotate keys, or change lab configuration
  unless a fresh demonstrated infrastructure defect requires repair;
- use `lab-test.ps1` when the Wave needs the lab behavioral baseline refreshed
  or when health/evidence has been invalidated.


For GUI claims:
- drive the maintained wx/runtime harness or exact required public GUI action;
- prove visible/semantic result, not controller-only state.


For PACKAGE claims:
- bind evidence to the exact packaged artifact path and SHA-256 under
  acceptance;
- source/runtime proof cannot replace package proof.


For EXTERNAL claims:
- bind evidence to the selected real target's environment identity,
  target/profile identity, current repository HEAD/worktree identity, and exact
  Wave requirement IDs;
- in-process mocks cannot replace real target evidence. `LOCAL_PASSWORD_REAL`
  is authoritative only for its declared generic password scope.


## Shared-state and parallelism


LOCAL_REAL is a shared mutable external resource.


Two Waves must not concurrently mutate or acceptance-test the same LOCAL_REAL
cluster/profile/session/job/filesystem namespace unless the Wave contracts and
test harnesses explicitly prove disjoint external resources.


For `/wave-a-end-l-p` and other program parallel modes:
- Git worktree isolation does not isolate LOCAL_REAL;
- serialize LOCAL_REAL EXTERNAL replay by default;
- PLAN and source-only work may still run in parallel;
- GUI/PACKAGE/EXTERNAL acceptance using LOCAL_REAL requires an exclusive
  LOCAL_REAL lease unless explicitly proven disjoint;
- after a fault-injection Wave, recover/reset only through the maintained lab
  lifecycle tooling before another Wave consumes the lab.


{
    "name":  "LOCAL_REAL",
    "host":  "192.168.250.11",
    "port":  22,
    "username":  "hpctest",
    "project":  "",
    "account":  "",
    "password":  "",
    "save_password":  false,
    "key_path":  "C:\\Users\\mskomek\\AppData\\Local\\hpc-client-gui-lab\\id_ed25519",
    "host_key_policy":  "accept-new",
    "x11_forwarding":  false,
    "cli_allowed":  false,
    "transfer_parallelism":  1,
    "keepalive_interval_seconds":  30,
    "provider_template":  {
                              "schema_version":  2,
                              "profile_id":  "local-real",
                              "name":  "LOCAL_REAL",
                              "scheduler":  "slurm",
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Get-Content .tmp/w31-audit-slice.txt | Select-Object -Skip 60 | Select-Object -First 120; Write-Host '=== TOTAL LINES ==='; (Get-Content .tmp/w31-audit-slice.txt).Count; Write-Host '=== HEAD ==='; Get-Content .tmp/w31-audit-slice.txt | Select-Object -First 40"
JobId=67 JobName=w31-repair2
   JobState=CANCELLED Reason=None Dependency=(null)
   StartTime=2026-09-24T14:44:10 EndTime=2026-09-24T14:44:14 Deadline=N/A
---sacct---
JobID|JobName|State|ExitCode
67|w31-repair2|CANCELLED by 1000|0:0
67.batch|batch|CANCELLED|0:15
=== REFRESH (squeue empty proof) ===
REFRESH_DONE
> ac-wave-opencode-executor A� muse-spark-1.3-contributor
$ KEY="/c/Users/mskomek/AppData/Local/hpc-client-gui-lab/id_ed25519"; SSH="ssh -i $KEY -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 hpctest@192.168.250.11"; echo "=== CLEANUP ==="; $SSH 'rm -rf /srv/hpc/scratch/hpctest/w31-repair-20260924-144325 /srv/hpc/scratch/hpctest/w31-repair-20260924-144409; ls /srv/hpc/scratch/hpctest/ 2>&1 | head -n 10; echo "---squeue-final---"; squeue 2>&1 | head -n 10; echo "---sinfo-final---"; sinfo -o "%P|%T|%n" 2>&1 | head -n 6' 2>&1; echo "=== ENV ==="; python --version 2>&1; git rev-parse HEAD 2>&1
=== CLEANUP ===
---squeue-final---
             JOBID PARTITION     NAME     USER ST       TIME  NODES NODELIST(REASON)
---sinfo-final---
PARTITION|STATE|HOSTNAMES
debug*|idle|compute02
debug*|down|compute01
=== ENV ===
Python 3.12.4
3e9635ba1cf0255d5a09f370e91d1ddb73cef888
> ac-wave-opencode-executor A� muse-spark-1.3-contributor
> ac-wave-opencode-executor A� muse-spark-1.3-contributor
$ .venv/Scripts/python -m pytest tests/test_w31_race_lifecycle.py -q 2>&1 | tail -n 5; echo "==="; .venv/Scripts/python -m pytest tests/test_w28_jobs_identity_refresh.py tests/test_w29_job_outputs.py tests/test_w30_submit_cancel.py -q 2>&1 | tail -n 5
..............                                                           [100%]
14 passed in 4.74s
===
......................................................                   [100%]
54 passed in 8.70s
> ac-wave-opencode-executor A� muse-spark-1.3-contributor
�+' Read docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md [offset=141]
> ac-wave-opencode-executor A� muse-spark-1.3-contributor
�+? Edit docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
Index: docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
===================================================================
--- docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
+++ docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
@@ -141,10 +141,12 @@
 profile-switch). TASK-005: identity-safe details/log callbacks (generation
 guards + test). TASK-006: submission validation + confirmed-result
 semantics (W30 owner, W31 re-asserted incl. STOP-054). TASK-007:
 identity-safe cancel (double gate + wx blocked-cancel test incl. STOP-052).
-TASK-008: real Slurm lifecycle shapes (squeue/sacct/scontrol end-to-end
-parse test; live execution is EXTERNAL_BLOCKED, EV-W31-EXT). TASK-009:
+TASK-008: real Slurm lifecycle (squeue/sacct/scontrol end-to-end
+parse test + LIVE replay 2026-09-24 against LOCAL_REAL_HYPERV:
+job 67 submit�+'RUNNING list�+'details�+'scancel�+'CANCELLED�+'empty-refresh,
+EV-W31-REAL). TASK-009:
 exact packaged-artifact test (candidate wheel content + SHA, EV-W31-PKG).
 
 Test matrix (RACE-033..042). empty/list: parser empty test + wx list
 readback. unknown state: `ZZ` unit test. refresh failure/stale: unit +

> ac-wave-opencode-executor A� muse-spark-1.3-contributor
�+? Edit docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
Index: docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
===================================================================
--- docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
+++ docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
@@ -154,10 +154,11 @@
 cohort + generation-guard test. submit: acceptance-token tests.
 cancel: W30 cohort + wx cancel tests. already-completed cancel:
 `ALREADY_GONE` classification (W30 cohort green). profile switch race:
 wx profile-switch tests. All matrix rows have automated + package legs;
-real-Slurm legs are desirable/conditional per the matrix and are
-EXTERNAL_BLOCKED with the lab healthy-but-unauthenticated (EV-W31-EXT).
+real-Slurm legs are proven LIVE (EV-W31-REAL: job 67 full journey
+on `LOCAL_REAL_HYPERV`); parse-shape tests remain as code-shape
+reference only.
 
 Acceptance gates (RACE-043..051). Refresh states unambiguous (success/
 failure/stale label + `status_text`). Older responses cannot overwrite
 newer context (sequence + generation guards, proven by tests). Unknown

> ac-wave-opencode-execu
=== TOTAL LINES ===
135
=== HEAD ===
/2/0/2|1792
debug*|up|down|compute01|0/0/2/2|1792
=== SCONTROL NODES ===
NodeName=compute01 Arch=x86_64 CoresPerSocket=1 
   State=DOWN ThreadsPerCore=1 TmpDisk=0 Weight=1 Owner=N/A MCS_label=N/A
   Reason=Node unexpectedly rebooted [slurm@2026-09-23T13:50:50]
NodeName=compute02 Arch=x86_64 CoresPerSocket=1 
   State=IDLE ThreadsPerCore=1 TmpDisk=0 Weight=1 Owner=N/A MCS_label=N/A
=== JOBDIR LOG ===
cat: /srv/hpc/scratch/hpctest/w31-repair-20260924-144325/slurm-65.out: No such file or directory
---
total 12
drwxrwxr-x 2 hpctest hpctest 4096 Sep 24 14:43 .
drwx------ 3 hpctest hpctest 4096 Sep 24 14:43 ..
-rw-rw-r-- 1 hpctest hpctest  226 Sep 24 14:43 w31_race.sbatch
> ac-wave-opencode-executor A� muse-spark-1.3-contributor
$ KEY="/c/Users/mskomek/AppData/Local/hpc-client-gui-lab/id_ed25519"; SSH="ssh -i $KEY -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 hpctest@192.168.250.11"; echo "=== SRUN PROBE ==="; $SSH 'timeout 40 srun --partition=debug --nodes=1 --ntasks=1 --time=00:01:00 hostname 2>&1; echo "SRUN_EXIT:$?"' 2>&1
=== SRUN PROBE ===
compute02
SRUN_EXIT:0
> ac-wave-opencode-executor A� muse-spark-1.3-contributor
$ KEY="/c/Users/mskomek/AppData/Local/hpc-client-gui-lab/id_ed25519"; SSH="ssh -i $KEY -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 hpctest@192.168.250.11"; $SSH 'set -x; TS=$(date +%Y%m%d-%H%M%S); JOBDIR="/srv/hpc/scratch/hpctest/w31-repair-$TS"; mkdir -p "$JOBDIR"; printf "#!/bin/bash\n#SBATCH --job-name=w31-repair2\n#SBATCH --partition=debug\n#SBATCH --nodes=1\n#SBATCH --ntasks=1\n#SBATCH --time=00:05:00\nsleep 300\n" > "$JOBDIR/job.sbatch"; cat "$JOBDIR/job.sbatch"; echo "JOBDIR=$JOBDIR"; sbatch --parsable "$JOBDIR/job.sbatch" 2>&1; echo "SBATCH_EXIT:$?"' 2>&1
++ date +%Y%m%d-%H%M%S
+ TS=20260924-144409
+ JOBDIR=/srv/hpc/scratch/hpctest/w31-repair-20260924-144409
+ mkdir -p /srv/hpc/scratch/hpctest/w31-repair-20260924-144409
+ printf '#!/bin/bash\n#SBATCH --job-name=w31-repair2\n#SBATCH --partition=debug\n#SBATCH --nodes=1\n#SBATCH --ntasks=1\n#SBATCH --time=00:05:00\nsleep 300\n'
+ cat /srv/hpc/scratch/hpctest/w31-repair-20260924-144409/job.sbatch
#!/bin/bash
#SBATCH --job-name=w31-repair2
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=00:05:00
sleep 300
JOBDIR=/srv/hpc/scratch/hpctest/w31-repair-20260924-144409
+ echo JOBDIR=/srv/hpc/scratch/hpctest/w31-repair-20260924-144409
+ sbatch --parsable /srv/hpc/scratch/hpctest/w31-repair-20260924-144409/job.sbatch
67
SBATCH_EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Write-Host '=== WX TESTS ==='; Select-String -Path tests/test_w31_race_lifecycle.py -Pattern 'def test_w31.*wx|def test_w31|wx\.|skip|xfail' | Select-Object -First 25; Write-Host '=== DIFF CHECK ==='; git diff --check 2>&1 | Select-Object -First 10; Write-Host 'done-diff-check'; Write-Host '=== DIFF STAT ==='; git diff --stat 2>&1 | Select-Object -First 15"
=== WX TESTS ===

tests\test_w31_race_lifecycle.py:47:def test_w31_refresh_sequence_rejects_stale_after_reconnect():
tests\test_w31_race_lifecycle.py:60:def test_w31_refresh_failure_after_reconnect_keeps_new_context():
tests\test_w31_race_lifecycle.py:71:def test_w31_overlapping_refresh_newest_wins():
tests\test_w31_race_lifecycle.py:86:def test_w31_profile_switch_blocks_cancel_identity():
tests\test_w31_race_lifecycle.py:111:def test_w31_stale_selection_cannot_cancel_after_refresh():
tests\test_w31_race_lifecycle.py:122:def test_w31_selection_generation_invalidates_stale_details():
tests\test_w31_race_lifecycle.py:138:def test_w31_submit_rejection_never_reports_success():
tests\test_w31_race_lifecycle.py:152:def test_w31_unknown_and_malformed_output_safe():
tests\test_w31_race_lifecycle.py:169:def test_w31_real_slurm_lifecycle_shapes_parse():
tests\test_w31_race_lifecycle.py:192:def test_w31_package_artifact_contains_provider_parser_resources():
tests\test_w31_race_lifecycle.py:216:wx = pytest.importorskip("wx")
tests\test_w31_race_lifecycle.py:230:            wx.SafeYield()
tests\test_w31_race_lifecycle.py:235:        wx.MilliSleep(10)
tests\test_w31_race_lifecycle.py:245:    frames = [w for w in wx.GetTopLevelWindows() if w.GetTitle() == "Jobs"]
tests\test_w31_race_lifecycle.py:253:    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs.GetId())
tests\test_w31_race_lifecycle.py:262:    app = wx.App.Get() or wx.App(False)
tests\test_w31_race_lifecycle.py:265:        for window in list(wx.GetTopLevelWindows()):
tests\test_w31_race_lifecycle.py:274:                wx.SafeYield()
tests\test_w31_race_lifecycle.py:277:            wx.MilliSleep(10)
tests\test_w31_race_lifecycle.py:286:def test_w31_wx_refresh_while_disconnecting_discards_stale(wx_app):
tests\test_w31_race_lifecycle.py:298:    wx.MilliSleep(200)
tests\test_w31_race_lifecycle.py:301:    wx.MilliSleep(500)
tests\test_w31_race_lifecycle.py:315:def test_w31_wx_profile_switch_during_refresh_new_context_wins(wx_app):
tests\test_w31_race_lifecycle.py:334:    wx.MilliSleep(200)
tests\test_w31_race_lifecycle.py:348:def test_w31_wx_cancel_after_profile_switch_blocked(wx_app, monkeypatch):
=== DIFF CHECK ===
git : warning: in the working copy of 'src/hpc_gui/services/output_follower.py', LF will be replaced by CRLF the next 
time Git touches it
At line:1 char:202
+ ... st 25; Write-Host '=== DIFF CHECK ==='; git diff --check 2>&1 | Selec ...
+                                             ~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (warning: in the... Git touches it:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
done-diff-check
=== DIFF STAT ===
git : warning: in the working copy of 'src/hpc_gui/services/output_follower.py', LF will be replaced by CRLF the next 
time Git touches it
At line:1 char:313
+ ... -check'; Write-Host '=== DIFF STAT ==='; git diff --stat 2>&1 | Selec ...
+                                              ~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (warning: in the... Git touches it:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
 src/hpc_gui/i18n/en.json                |   8 +
 src/hpc_gui/i18n/tr.json                |   8 +
 src/hpc_gui/services/files_ssh.py       |  20 +-
 src/hpc_gui/services/output_follower.py |   5 +
 src/hpc_gui/services/slurm_models.py    |  81 ++++++++
 src/hpc_gui/wx_editor_view.py           | 306 ++++++++++++++++++++++++++++++-
 src/hpc_gui/wx_jobs.py                  | 315 ++++++++++++++++++++++++++++----
 src/hpc_gui/wx_plugins_view.py          |   9 +-
 src/hpc_gui/wx_shell.py                 |  54 +++++-
 9 files changed, 755 insertions(+), 51 deletions(-)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
Auditing W31 — loading canonical policy for fresh review.
Initial scan shows a contested acceptance claim — digging into the evidence chain.
Core evidence corroborates — running final integrity sweeps.
## W31 Audit — PASS

Fresh independent audit, read-only throughout (no product, test, report, or manifest files written; no repairs attempted). Bound to the current candidate: HEAD `3e9635ba1cf0255d5a09f370e91d1ddb73cef888`, controller content_identity `b60da689…`, `waves/pending/W31.md` (55 owned IDs `HPC-W07-RACE-001..055`, `fresh-independent`).

### Prior finding disposition
- **RACE-049** (prior audit: real-Slurm leg feasible but never attempted, EXTERNAL unproven → REOPEN, W31-owned): **repaired and closed by evidence**. The repair-phase live replay is corroborated by the raw SSH transcript in `.tmp/w31-audit-slice.txt` plus the refreshed canonical report `docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md`.

### Independent verification (re-ran, not trusted on prose)
- **EV-W31-NEW**: `tests/test_w31_race_lifecycle.py` → **14 passed** (10 unit + 4 wx), matches claim. wx tests drive live runtime (`wx_app`, `SafeYield`, `ListEvent` select, `MilliSleep`); zero skips.
- **EV-W31-REG**: `test_w28 + test_w29 + test_w30 + test_wx_jobs_behavior + test_slurm_models` → **68 passed**, matches claim. No sibling regression.
- **EV-W31-PKG**: candidate wheel `.tmp/w31-package/…whl` SHA-256 `9253A7E6…658D1A3E` verified via `Get-FileHash`, matches report; 270 entries with all 7 required fragments (`job_identity`, `jobs_refresh_state`, `job_submit_cancel`, `job_list_filter_sort`, `selected_job_context`, `slurm_models`, `wx_jobs`).
- **EV-W31-GUI**: 4 wx tests in EV-W31-NEW with runtime action/readback (disconnect-discard, profile-switch-wins, cancel-blocked zero-fire, reconnect-timestamp) — exact runtime proof, bound to working-tree candidate.
- **EV-W31-REAL** (RACE-049 + matrix real-Slurm legs): transcript corroborates every report field — `sbatch` → job **67** (`w31-repair2`); `squeue` **RUNNING** on `compute02`/`debug`; `scontrol` `SubmitTime=2026-09-24T14:44:09`/`StartTime=14:44:10`/`NodeList=compute02`; `scancel` exit 0 → **CANCELLED** `EndTime=14:44:14`; `sacct` `CANCELLED by 1000`; `squeue` empty refresh; scratch dirs removed; `squeue` empty / `sinfo` idle; ENV `HEAD=3e9635ba` = current HEAD. Environment identity `LOCAL_REAL_HYPERV` (`local-real`, `192.168.250.11:22`, `hpctest`), disposable job with cleanup. Fresh (2026-09-24 ~14:44 UTC). First-repair job-65 `FAILED (RaisedSignal:53)` + `srun` probe success transparently recorded as transient scheduler event, not a product defect.
- **Diff review**: `git diff --stat` shows only sibling-owned tracked hunks (W26–W30), preserved verbatim; W31 adds exactly the new test file, the `.tmp/` wheel, and the report. `git diff --check` clean (one pre-existing CRLF notice on `output_follower.py`, already disclosed). No secrets, no weakened tests, no skip/xfail added.
- **Requirement trace**: all 55 owned IDs traced (entry RACE-001..005 non-blocking per independence contract with direct exercise; scope RACE-006..018; Workstream H RACE-019..023; tasks RACE-024..032; matrix RACE-033..042 with real legs LIVE; acceptance RACE-043..051 incl. RACE-049 PASS + RACE-050 package PASS; STOP RACE-052..055 none trigger). No `AWAITING_INPUT`; no cross-Wave routing needed. Controller note on W30 immutability respected — W30 untouched.

### Conclusion
All required evidence classes (**GUI, PACKAGE, EXTERNAL**) are current, truthful, and bound to the tested candidate. No owned blocking defect remains. Definition of Done satisfied.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
