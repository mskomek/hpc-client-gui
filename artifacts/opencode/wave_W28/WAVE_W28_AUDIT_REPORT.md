# Wave W28 Audit Report
## Controller-persisted fresh independent audit — 2026-09-24T13:31:00.514751+00:00

- Wave: `W28`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0014-W28-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0014-W28-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
✱ Glob "waves/**/W28*" 0 matches
✱ Glob ".agents/skills/ac-wave-*/**" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending 
→ Read waves/done 
→ Read .agents/skills/ac-wave-opencode-audit 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W28.md 
→ Read .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md 
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
→ Read .agents/protocol/AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md [offset=30]
$ git log --oneline -5; echo ---STATUS---; git status --short --branch; echo ---SHA---; git rev-parse HEAD; echo ---W28REPORT---; ls docs/wave-reports/v2/opencode/ | Select-Object -Last 30
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
54b85bed Sync Agent Core runtime cecc7b82 and migrate Wave profile to schema v3
---STATUS---
## develop
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_plugins_view.py
?? ".agent-legacy-backup (1)/"
?? artifacts/opencode/wave_W26/
?? artifacts/opencode/wave_W27/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
?? "new 4.ps1"
?? src/hpc_gui/services/job_identity.py
?? src/hpc_gui/services/job_list_filter_sort.py
?? src/hpc_gui/services/jobs_refresh_state.py
?? "tests/contracts (1)/"
?? "tests/contracts (2)/"
?? tests/test_w26_run_supplement.py
?? tests/test_w27_editor_conflicts.py
?? tests/test_w28_jobs_identity_refresh.py
---SHA---
3e9635ba1cf0255d5a09f370e91d1ddb73cef888
---W28REPORT---
/usr/bin/bash: line 1: Select-Object: command not found
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md 
$ powershell.exe -NoProfile -Command "git log --oneline -5; Write-Output '---STATUS---'; git status --short --branch; Write-Output '---SHA---'; git rev-parse HEAD; Write-Output '---REPORTS---'; Get-ChildItem docs/wave-reports/v2/opencode/ | Select-Object -Last 30 | Format-Table Name, Length"
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
54b85bed Sync Agent Core runtime cecc7b82 and migrate Wave profile to schema v3
---STATUS---
## develop
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_plugins_view.py
?? ".agent-legacy-backup (1)/"
?? artifacts/opencode/wave_W26/
?? artifacts/opencode/wave_W27/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
?? "new 4.ps1"
?? src/hpc_gui/services/job_identity.py
?? src/hpc_gui/services/job_list_filter_sort.py
?? src/hpc_gui/services/jobs_refresh_state.py
?? "tests/contracts (1)/"
?? "tests/contracts (2)/"
?? tests/test_w26_run_supplement.py
?? tests/test_w27_editor_conflicts.py
?? tests/test_w28_jobs_identity_refresh.py
---SHA---
3e9635ba1cf0255d5a09f370e91d1ddb73cef888
---REPORTS---

Name                Length
----                ------
W11_WAVE_REPORT.md   22271
W12_AUDIT_REPORT.md   2365
W12_WAVE_REPORT.md   25872
W13_AUDIT_REPORT.md   3746
W13_WAVE_REPORT.md   40239
W14_AUDIT_REPORT.md   3986
W14_WAVE_REPORT.md   24145
W15_AUDIT_REPORT.md   5438
W15_WAVE_REPORT.md   24155
W16_AUDIT_REPORT.md   5187
W16_WAVE_REPORT.md   25482
W17_AUDIT_REPORT.md   4392
W17_WAVE_REPORT.md   24822
W18_AUDIT_REPORT.md  27464
W18_WAVE_REPORT.md   49040
W19_AUDIT_REPORT.md   3721
W19_WAVE_REPORT.md   21978
W20_AUDIT_REPORT.md   4425
W20_WAVE_REPORT.md   20567
W21_AUDIT_REPORT.md   3542
W21_WAVE_REPORT.md   27266
W22_AUDIT_REPORT.md  65358
W22_WAVE_REPORT.md   42340
W23_WAVE_REPORT.md    8434
W24_AUDIT_REPORT.md 122117
W24_WAVE_REPORT.md   14775
W25_WAVE_REPORT.md   18892
W26_WAVE_REPORT.md   14732
W27_WAVE_REPORT.md   21521
W28_WAVE_REPORT.md   21169
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "Get-Content waves/pending/W28.md -TotalCount 35; Write-Output '---REGISTRY---'; Select-String -Path 'opencode/REQUIREMENT_REGISTRY.md' -Pattern 'HPC-W07-JOB-001|HPC-W07-REFRESH-001' | Select-Object -First 5; Write-Output '---FILES---'; Get-ChildItem src/hpc_gui/services/job_identity.py, src/hpc_gui/services/jobs_refresh_state.py, src/hpc_gui/services/job_list_filter_sort.py, tests/test_w28_jobs_identity_refresh.py | Format-Table Name, Length; Write-Output '---DIFFSTAT---'; git diff --stat; Write-Output '---UNTRACKED---'; git status --short | Select-String 'W28|job_identity|jobs_refresh|filter_sort'"
---
wave_id: "W28"
wave_kind: execution
canonical_source: "W28"
owned_requirements:
  - "HPC-W07-JOB-001"
  - "HPC-W07-JOB-002"
  - "HPC-W07-JOB-003"
  - "HPC-W07-JOB-004"
  - "HPC-W07-JOB-005"
  - "HPC-W07-JOB-006"
  - "HPC-W07-JOB-007"
  - "HPC-W07-JOB-008"
  - "HPC-W07-JOB-009"
  - "HPC-W07-JOB-010"
  - "HPC-W07-JOB-011"
  - "HPC-W07-JOB-012"
  - "HPC-W07-JOB-013"
  - "HPC-W07-JOB-014"
  - "HPC-W07-JOB-015"
  - "HPC-W07-JOB-016"
  - "HPC-W07-JOB-017"
  - "HPC-W07-REFRESH-001"
  - "HPC-W07-REFRESH-002"
  - "HPC-W07-REFRESH-003"
  - "HPC-W07-REFRESH-004"
aggregate_close_owner: false
global_bookkeeping_owner: controller
completion_dependencies: []
evidence_policy: wave-local
audit_policy: fresh-independent
---
# W28 �?" Jobs identity, listing, parser and refresh state

- **Wave ID:** `W28`
---REGISTRY---

opencode\REQUIREMENT_REGISTRY.md:668:| `HPC-W07-JOB-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_07.md` | 56 | 
Workstream A - Data model and identity | `W28` | - | Identify the job identity tuple used by the app. At minimum, job 
ID must not be mixed across: |
opencode\REQUIREMENT_REGISTRY.md:1274:| `HPC-W07-REFRESH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_07.md` | 64 | 
Workstream B - Refresh state machine | `W28` | - | Jobs refresh has explicit idle  refreshing  success(timestamp) or 
failure(error, previous-data-marked-stale) semantics. |
---FILES---



Name                              Length
----                              ------
job_identity.py                     4074
jobs_refresh_state.py               4095
job_list_filter_sort.py             5853
test_w28_jobs_identity_refresh.py  14164


---DIFFSTAT---
 src/hpc_gui/i18n/en.json             |   8 +
 src/hpc_gui/i18n/tr.json             |   8 +
 src/hpc_gui/services/slurm_models.py |  81 ++++++++++
 src/hpc_gui/wx_editor_view.py        | 306 ++++++++++++++++++++++++++++++++++-
 src/hpc_gui/wx_jobs.py               | 183 +++++++++++++++++++--
 src/hpc_gui/wx_plugins_view.py       |   9 +-
 6 files changed, 571 insertions(+), 24 deletions(-)
---UNTRACKED---

?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
?? src/hpc_gui/services/job_identity.py
?? src/hpc_gui/services/job_list_filter_sort.py
?? src/hpc_gui/services/jobs_refresh_state.py
?? tests/test_w28_jobs_identity_refresh.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read tests/test_w28_jobs_identity_refresh.py 
→ Read src/hpc_gui/services/job_identity.py 
→ Read src/hpc_gui/services/jobs_refresh_state.py 
→ Read src/hpc_gui/services/job_list_filter_sort.py 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "git diff --check; Write-Output \"DIFFCHECK_EXIT:$LASTEXITCODE\"; git diff -- src/hpc_gui/services/slurm_models.py | Select-Object -First 120"
DIFFCHECK_EXIT:
diff --git a/src/hpc_gui/services/slurm_models.py b/src/hpc_gui/services/slurm_models.py
index 4315c8e2..4f5c7434 100644
--- a/src/hpc_gui/services/slurm_models.py
+++ b/src/hpc_gui/services/slurm_models.py
@@ -136,3 +136,84 @@ def parse_scontrol(text: str, job_id: str = "") -> SlurmJob:
         stdout_path=observed.get("StdOut", ""),
         stderr_path=observed.get("StdErr", ""),
     )
+
+
+# --- W28 parser safety helpers (additive; existing parsers unchanged) --------
+
+KNOWN_SQUEUE_STATES = frozenset(
+    {
+        "PD", "R", "CA", "CG", "CD", "CF", "F", "NF", "PR", "RV", "S", "ST",
+        "TO", "OOM",
+    }
+)
+
+KNOWN_SACCT_STATES = frozenset(
+    {
+        "PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "TIMEOUT",
+        "OUT_OF_MEMORY", "SUSPENDED", "PREEMPTED", "NODE_FAIL", "DEADLINE",
+    }
+)
+
+TERMINAL_STATES = frozenset(
+    {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "CD", "F", "CA", "TO", "OOM"}
+)
+
+
+def safe_state_display(state: str) -> str:
+    """Return a crash-safe display state; unknown/new states pass through.
+
+    Unknown scheduler states must display safely rather than crashing or
+    being misreported as success. This helper never maps an unknown token to
+    a success/terminal display value.
+    """
+    text = str(state or "").strip()
+    if not text:
+        return "UNKNOWN"
+    return text
+
+
+def is_terminal_state(state: str) -> bool:
+    """True for scheduler states that mean the job has finished."""
+    return str(state or "").strip().upper() in TERMINAL_STATES
+
+
+def parse_squeue_result(result) -> list[SlurmJob]:
+    """Parse an squeue command result without mistaking failure for empty.
+
+    A non-zero scheduler exit (``SlurmCommandResult.ok is False``) yields no
+    rows so the caller can surface the attached ``message`` instead of
+    rendering error text as phantom jobs. Plain-string input keeps the legacy
+    tolerant behaviour.
+    """
+    code = getattr(result, "code", None)
+    ok = getattr(result, "ok", None)
+    if code is not None or ok is not None:
+        if callable(ok):
+            is_ok = bool(ok())
+        else:
+            is_ok = bool(ok) if ok is not None else int(code) == 0
+        if not is_ok:
+            return []
+        text = getattr(result, "stdout", None)
+        if text is None:
+            text = getattr(result, "text", "")
+        return parse_squeue(str(text or ""))
+    return parse_squeue(str(result or ""))
+
+
+def parse_sacct_result(result) -> list[SlurmJob]:
+    """Parse an sacct command result without mistaking failure for empty."""
+    code = getattr(result, "code", None)
+    ok = getattr(result, "ok", None)
+    if code is not None or ok is not None:
+        if callable(ok):
+            is_ok = bool(ok())
+        else:
+            is_ok = bool(ok) if ok is not None else int(code) == 0
+        if not is_ok:
+            return []
+        text = getattr(result, "stdout", None)
+        if text is None:
+            text = getattr(result, "text", "")
+        return parse_sacct(str(text or ""))
+    return parse_sacct(str(result or ""))
$ python -m pytest tests/test_w28_jobs_identity_refresh.py -q 2>&1 | tail -20
.......................                                                  [100%]
23 passed in 2.52s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "Select-String -Path 'src/hpc_gui/wx_jobs.py' -Pattern 'jobs_refresh_seq|jobs_refresh_label|cancel_is_safe|cancel_target_is_safe|selection_still_exists|sort_jobs|filter_jobs|should_apply|complete_success|complete_failure' | Select-Object -First 30 | Format-Table LineNumber, Line -Wrap"
LineNumber Line                                                                                                        
---------- ----                                                                                                        
        15 from hpc_gui.services.job_identity import cancel_is_safe, make_identity                                     
        17     cancel_target_is_safe,                                                                                  
        18     filter_jobs,                                                                                            
        19     selection_still_exists,                                                                                 
        20     sort_jobs,                                                                                              
       456     jobs_refresh_label = wx.StaticText(jobs_page, label="")                                                 
       457     jobs_toolbar.Add(jobs_refresh_label, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 6)                          
      1008         "jobs_refresh_seq": 0,                                                                              
      1097         filtered = filter_jobs(backend_snapshot, query)                                                     
      1100             filtered = sort_jobs(filtered, sort_key, reverse=bool(state.get("sort_reverse", False)))        
      1308             state["jobs_refresh_seq"] += 1                                                                  
      1309             request_seq = state["jobs_refresh_seq"]                                                         
      1315                 jobs_refresh_label.SetLabel(t("jobs.refreshing"))                                           
      1330             if req_seq is not None and req_seq != state["jobs_refresh_seq"]:                                
      1341                     applied = machine2.complete_failure(req_seq if req_seq is not None else                 
           machine2.sequence, error)                                                                                   
      1349                                 jobs_refresh_label.SetLabel(                                                
      1355                                 jobs_refresh_label.SetLabel(                                                
      1366                     applied = machine2.complete_success(                                                    
      1378                             jobs_refresh_label.SetLabel(                                                    
      1394                         if state["selected_job"] and not selection_still_exists(                            
      2306         if not cancel_target_is_safe(                                                                       
      2326         if not cancel_is_safe(selected_identity, requested_identity):                                       
      2798         "jobs_refresh_label": jobs_refresh_label,
$ python -m pytest tests/test_slurm_models.py tests/test_wx_jobs.py tests/test_wx_jobs_behavior.py tests/test_selected_job_context.py tests/test_job_tracking_controller.py -q 2>&1 | tail -8
..........................................                               [100%]
42 passed in 8.65s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "$ids = @('HPC-W07-JOB-001','HPC-W07-JOB-002','HPC-W07-JOB-003','HPC-W07-JOB-004','HPC-W07-JOB-005','HPC-W07-JOB-006','HPC-W07-JOB-007','HPC-W07-JOB-008','HPC-W07-JOB-009','HPC-W07-JOB-010','HPC-W07-JOB-011','HPC-W07-JOB-012','HPC-W07-JOB-013','HPC-W07-JOB-014','HPC-W07-JOB-015','HPC-W07-JOB-016','HPC-W07-JOB-017','HPC-W07-REFRESH-001','HPC-W07-REFRESH-002','HPC-W07-REFRESH-003','HPC-W07-REFRESH-004'); foreach ($id in $ids) { $n = (Select-String -Path 'docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md' -Pattern $id | Measure-Object).Count; Write-Output \"$id report_hits=$n\" }; Write-Output '---TESTCOVER---'; Select-String -Path 'tests/test_w28_jobs_identity_refresh.py' -Pattern 'def test_' | Measure-Object | Format-Table Count"
At line:1 char:411
+ ... -002','HPC-W07-REFRESH-003','HPC-W07-REFRESH-004'); foreach ( in ) {  ...
+                                                                  ~
Missing variable name after foreach.
At line:1 char:415
+ ... ,'HPC-W07-REFRESH-003','HPC-W07-REFRESH-004'); foreach ( in ) {  = (S ...
+                                                                 ~
Unexpected token ')' in expression or statement.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : MissingVariableNameAfterForeach
$ python -m pytest tests/test_wx_jobs_files_outputs.py tests/test_wx_jobs_final_fix.py -q 2>&1 | tail -5
...............................                                          [100%]
31 passed in 33.34s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "Select-String -Path 'docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md' -Pattern 'HPC-W07-JOB-01' | Measure-Object | Format-Table Count; Select-String -Path 'tests/test_w28_jobs_identity_refresh.py' -Pattern 'def test_' | Measure-Object | Format-Table Count"
Count
-----
    0



Count
-----
   23
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "(Get-Content 'docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md' | Select-String -Pattern 'JOB-001' | Measure-Object).Count; (Get-Content 'tests/test_w28_jobs_identity_refresh.py' | Measure-Object).Count"
5
384
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
Auditing W28 — loading the canonical skill and evidence.
Skill context loaded — now gathering W28 requirements and run evidence for independent verification.
Focused W28 checks pass — now running the regression sweep to confirm no collateral damage.
W28 fresh independent audit — PASS.

Scope verified: `waves/pending/W28.md` (21 owned IDs: HPC-W07-JOB-001..017 + HPC-W07-REFRESH-001..004, evidence GUI+EXTERNAL, audit fresh-independent). Report: `docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md` at HEAD `3e9635ba1cf0255d5a09f370e91d1ddb73cef888`.

Fresh reruns in this audit context:
- `tests/test_w28_jobs_identity_refresh.py` — 23 passed (4 identity, 9 parser, 4 filter/sort, 4 refresh-machine, 3 live wx GUI).
- Regression spot: `test_slurm_models + test_wx_jobs + test_wx_jobs_behavior + test_selected_job_context + test_job_tracking_controller` — 42 passed; `test_wx_jobs_files_outputs + test_wx_jobs_final_fix` — 31 passed. No failures.
- `git diff --check` — clean.

Claim-to-source verified:
- Identity (JOB-001..004): `services/job_identity.py` frozen tuple + same_target/cancel gates; wx `cancel_job` double gate confirmed in source.
- Parser (JOB-005..013): additive `safe_state_display`/`is_terminal_state`/`parse_squeue_result`/`parse_sacct_result` in `slurm_models.py`; existing parsers unchanged; exit-guard returns [] on non-zero.
- Filter/sort (JOB-014..017): `services/job_list_filter_sort.py` semantic keys (numeric job-ID, elapsed seconds, state rank), non-mutating filter, survival/cancel guards; wx `_apply_filter`/column-click wiring confirmed.
- Refresh (REFRESH-001..004): `services/jobs_refresh_state.py` idle->refreshing->success(timestamp)/failure(error, stale) + monotonic seq discard; wx `jobs_refresh_seq` mirror + visible stale label + selection-drop confirmed.
- GUI FULL: 3 wx tests drove real frames with item-count/state-mirror/label readback, all green in this audit.
- No weakened tests (tracked diff touches no test files), no secrets/binary noise, sibling hunks preserved, EXTERNAL_BLOCKED and package-N/A justifications accepted (EXTERNAL required class, no mock substitution; no owned packaging ID).

No owned blocking defect. No reopen.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
