# W48 Wave Report — GJ-04 Job and output lifecycle

```text
Wave: W48
Canonical report path: docs/wave-reports/v2/opencode/W48_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (sibling-wave working-tree changes uncommitted; controller owns commit/integration; W48 made zero product/test edits)
Content identity (controller handoff): bc8e0c25be61b35f5adab6343064706bcf1bd8e2c0cbe19e9183af9a0bc4bcb5
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W48 run phase)
Last updated: 2026-09-25
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W48.md` (wave_id W48, execution kind, canonical_source W48, 2 owned requirements `HPC-W10-GJ04-PATH-001` + `HPC-W10-GJ04-PATH-002`, start gate NONE, cohort P10-golden-journeys, required evidence `GUI,PACKAGE,EXTERNAL`, integration refs W44 non-blocking, unattended/non-interactive contract, Golden-Journey candidate rule: W44 candidate is behaviorally read-only).
2. `opencode/REQUIREMENT_REGISTRY.md` lines 1295/1303: `HPC-W10-GJ04-PATH-001` MANDATORY — "Execute GJ-04 as this explicit end-to-end path: submit → job ID → list/details → running/final state → stdout/stderr → live refresh/tail where exposed → completion." `HPC-W10-GJ04-PATH-002` MANDATORY — "GJ-04 additionally executes cancellation on a disposable job."
3. `opencode/TODO_OWNERSHIP_MAP.md`: no rows owned by W48 (verified: `NO_W48_ROWS`, grep for W48 returns empty).
4. `opencode/sources/WAVE_V2_FINAL_10.md` → GJ-04 section (lines 96-108): submit → job ID → list/details → running/final state → stdout/stderr → live refresh/tail where exposed → completion; also execute cancel on a disposable job.
5. `.opencode/protocol/LOCAL_REAL_HPC_LAB.md`: EXTERNAL authority; LOCAL_REAL_HYPERV is default real infra for generic Slurm/job claims; serialize EXTERNAL replay; GUI/PACKAGE claims need their own journey proof, not lab-health inference.
6. Live code before edits: `src/hpc_gui/services/job_submit_cancel.py` (`validate_submit_request`, `extract_sbatch_job_id`/`submit_result_status` requiring the canonical `Submitted batch job <id>` token, `build_cancel_confirmation`, `classify_cancel_outcome`/`reflect_cancel_result`); `src/hpc_gui/services/slurm_models.py` (`parse_squeue`/`parse_sacct`/`parse_scontrol`, `format_job_details`, `safe_state_display`, `is_terminal_state`); `src/hpc_gui/services/job_tracking_controller.py` (`JobTrackingController` select/output-metadata); `src/hpc_gui/services/jobs_refresh_state.py` (`JobsRefreshState` monotonic refresh lifecycle); `src/hpc_gui/services/output_follower.py` (`OutputFollower` bounded follow + `retain_last_lines`); wx jobs surfaces (`src/hpc_gui/wx_jobs.py`). No product edits made by W48 — candidate treated as read-only per wave contract.

## Baseline capture

```text
Evidence ID: EV-W48-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files + untracked sibling artifacts preserved untouched; W48 added zero tracked hunks, zero new source/test files outside .tmp)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
git log -1: c8293d3c (HEAD -> develop) Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
```

Content-identity note: `waves/` is gitignored so the pending spec lives outside Git history by program design. The worker proceeded on current repository truth without editing the spec; identity reconciliation is controller-owned. HEAD `c8293d3` matches the W44 audit candidate SHA and the W45/W46/W47 baselines, and the handoff content identity `bc8e0c25…` matches the W45/W46 handoff.

Sibling-hunk disclaimer: the working tree contains pre-existing sibling modifications including `src/hpc_gui/services/slurm_models.py`, `src/hpc_gui/services/output_follower.py`, `src/hpc_gui/wx_jobs.py`, `src/hpc_gui/services/files_ssh.py`, `src/hpc_gui/wx_shell.py` and `tests/test_remote_entry_helpers.py`. These hunks pre-date the W48 run phase and were not authored, reviewed, or claimed by W48. After controller integration or conflict resolution affecting the jobs/output surfaces, the affected W48 slices and the external replay must be re-run before audit acceptance.

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
OBS-W48-001 | N/A | GJ-04 path fully executable on current candidate | EV-W48-GUI (267 green) + EV-W48-EXT (submit/list/details/state/stdout/stderr/tail/completion PASS + cancel PASS) | n/a — journey holds, no product defect | none | none needed (read-only candidate rule) | NO (journey replay, not a remediation) | VERIFIED
OBS-W48-002 | N/A | lab Slurm partially degraded (compute01 down, compute02 idle) | lab-status.ps1 status=FAIL, slurm.ok=false, "compute01|down / compute02|idle"; transport_ok=true + services_ok=true on all 3 nodes; sinfo shows partition debug* up with compute02 idle | infrastructure state, not product | GJ-04 fully executable (both disposable jobs scheduled and ran on compute02); recorded truthfully | none (lab lifecycle is controller/lab owned; W48 must not reset VMs) | NO | RECORDED
```

Golden-Journey candidate rule applied: no product behavior was patched inside W48. No defect was found on the GJ-04 path, so nothing was routed to another owner. Second-defect sweep dimensions (submit validation gating, acceptance-token parsing, already-gone vs unauthorized cancel classification, stale/overlapped refresh suppression, follower offset/rotation handling, permission-denied surfacing, tracking selection/identity, record/provenance/history stores, failure classification, wx jobs behavior/files-outputs) are all covered by the green slices below; no sweep dimension surfaced a W48-owned defect.

Harness-correctness note (worker-owned, recorded honestly): the first replay run used an `squeue -o '%i|%j|%u|%T|%M|%R'` column order that does not match the product `parse_squeue` contract (`job_id|partition|name|user|state|elapsed`), so the polled state labels were elapsed times, not states (jobs 68 COMPLETED + 69 CANCELLED still verified end-to-end). The harness was corrected to `'%i|%P|%j|%u|%T|%M|%R'` and re-run clean (jobs 70/71 below); only the second run is claimed as EV-W48-EXT.

## Implementation

No product-code, test, or config changes. W48 is a journey-replay wave on a read-only candidate; the only new artifacts are this report and `.tmp/w48-run/` harness (temp, never committed as evidence).

## Tests and evidence

### EV-W48-GUI — journey GUI/runtime slices (all green, exact reruns at HEAD `c8293d3`, `PYTHONPATH=src`, `-p no:cacheprovider`)

```text
Evidence ID: EV-W48-GUI
tests/test_job_tracking_controller.py + tests/test_w28_jobs_identity_refresh.py + tests/test_w29_job_outputs.py + tests/test_job_failure_classifier.py → 51 passed
  (tracking select/output-metadata, identity refresh lifecycle, output channel resolution, failure classification)
tests/test_wx_jobs.py + tests/test_wx_jobs_behavior.py + tests/test_wx_jobs_final_fix.py → 29 passed
  (wx jobs surfaces with real event proof, behavior pins, final-fix regression)
tests/test_job_record_store.py + tests/test_job_history_dashboard.py + tests/test_job_provenance.py + tests/test_job_templates.py + tests/test_wave5_slurm_jobs_unicode.py → 44 passed
  (record store, history dashboard, provenance, submit templates, unicode job names)
tests/test_wave78_jobs_details.py + tests/test_corrective_jobs_details.py + tests/test_selected_job_context.py + tests/test_job_context.py → 74 passed
  (details/raw fallback, corrective details, selected-job context)
tests/test_wx_jobs_files_outputs.py → 16 passed
  (wx jobs files/outputs integration)
tests/test_w30_submit_cancel.py + tests/test_w31_race_lifecycle.py + tests/test_output_follower.py + tests/test_slurm_ssh.py + tests/test_w13_slurm_state.py → 53 passed
  (submit/cancel control paths, race lifecycle, output follower, Slurm over SSH, Slurm state)
Combined rerun of all 22 files above → 267 passed, 0 failed
GUI verdict: 267 passed, 0 failed across the GJ-04 path surfaces (51 + 29 + 44 + 74 + 16 + 53)
```

GJ-04 step → evidence mapping:

| GJ-04 step | Evidence |
|---|---|
| submit | `validate_submit_request` gate in replay + `extract_sbatch_job_id`/`submit_result_status` acceptance-token parse; `test_w30_submit_cancel` control paths |
| job ID | real `sbatch` acceptance `Submitted batch job 70` parsed by the product parser; `SlurmJob.job_id` pins |
| list/details | real `squeue` rows via product `parse_squeue` + real `scontrol show job` via product `parse_scontrol`/`format_job_details` (asserted to name the job ID) |
| running/final state | polled `PENDING -> RUNNING -> GONE` via product `safe_state_display`; terminal confirmed by product `is_terminal_state` + `sacct COMPLETED` |
| stdout/stderr | `cat` readbacks equal to submit tokens; `test_w29_job_outputs` + `test_output_follower` slices |
| live refresh/tail where exposed | product `JobsRefreshState` begin/complete_success per poll (`success`, applied_seq=4) + product `OutputFollower.poll` chunks (2 chunks, token present in retained text) |
| completion | `sacct 70\|COMPLETED\|0:0` + `DONE-<token>` trailer in stdout |
| cancel on disposable job | real `scancel 71` → product `classify_cancel_outcome=CANCELLED` + `reflect_cancel_result` (should_refresh, non-error) + `squeue` empty + `sacct 71\|CANCELLED by 1000` |

### EV-W48-EXT — real EXTERNAL replay against LOCAL_REAL_HYPERV

```text
Evidence ID: EV-W48-EXT
Harness: .tmp/w48-run/gj04_jobs.py (disposable; secrets never enter report/git)
Target identity: LOCAL_REAL_HYPERV controller 192.168.250.11:22, user hpctest, provider local-real, key auth (emitted lab profile), isolated known_hosts_w48 (seeded copy of lab known_hosts, W48-disjoint), accept-new
Product paths exercised: SSHClientWrapper.connect/run + validate_submit_request + extract_sbatch_job_id/submit_result_status + parse_squeue/parse_scontrol/format_job_details/safe_state_display/is_terminal_state + JobsRefreshState + JobTrackingController.select_job/set_output_metadata + OutputFollower.poll/retain_last_lines + build_cancel_confirmation/classify_cancel_outcome/reflect_cancel_result (the exact code under acceptance, not a parallel reimplementation)
Lab health at replay: lab-status.ps1 status=FAIL overall ONLY because slurm.ok=false (compute01 down, compute02 idle); transport_ok=true + services_ok=true on all 3 nodes; partition debug* up.
  Lab verdict recorded truthfully: Slurm was schedulable on compute02 (both jobs accepted and ran); the down node is infrastructure state out of W48 scope and was not reset by this worker (shared lab, serialized use).
Observed result (authoritative second run):
  KNOWN_HOSTS_SEEDED: OK (W48-disjoint copy)
  SUBMIT_VALIDATE: OK (product validate_submit_request, zero blocking errors)
  CONNECT: transport_active=True
  REMOTE_MKDIR: OK (disposable /home/hpctest/.w48-gj04-<pid>/)
  SCRIPTS_STAGED: OK (job_a.slurm + job_b.slurm)
  SUBMIT_A: OK job_id=70
  TRACK_SELECT: OK selected=70
  STATES_SEEN: PENDING -> RUNNING -> GONE
  REFRESH_STATUS: success, applied_seq=4
  LIVE_TAIL: OK chunks=2 retained_lines=2
  TAIL_TOKEN: OK (submit token visible in live tail)
  SACCT_A: 70|COMPLETED|0:0
  COMPLETION_A: OK COMPLETED
  STDOUT_VERIFY: OK (2 lines, token + DONE trailer present)
  STDERR_VERIFY: OK (stderr token present)
  SUBMIT_B: OK job_id=71
  CANCEL_CONFIRM: OK (wording names job id)
  SCANCEL_OUT: SCANCEL_EXIT=0
  CANCEL_CLASSIFY: OK CANCELLED (product classify_cancel_outcome)
  CANCEL_VERIFY: OK squeue empty; sacct=71|CANCELLED by 1000
  CANCEL_REFLECT: OK CANCELLED should_refresh=True
  GJ04_EXTERNAL_RESULT: PASS
Cleanup: scancel attempted for both jobs, remote disposable dir removed (rm -rf, CLEANED); session closed (DISCONNECT: OK); no shared-namespace mutation; isolated temp dirs left for GC.
```

### EV-W48-PKG — PACKAGE class

```text
Evidence ID: EV-W48-PKG
No packaged artifact was built, published, or claimed by W48 (candidate freeze is owned by W56–W61). Recorded honestly as NO-CANDIDATE.
No product/package-content modification was made by W48, so no freeze invalidation arises from this Wave.
```

Evidence classes: `GUI` (required) → EV-W48-GUI (267 green incl. real wx event proof). `PACKAGE` (required) → EV-W48-PKG (NO-CANDIDATE, honestly recorded; freeze owned downstream). `EXTERNAL` (required) → EV-W48-EXT (real LOCAL_REAL submit→COMPLETED with sha-class token readbacks + live tail + cancel→CANCELLED, PASS). No mocks substituted for any owned claim.

## Diff review

```text
Evidence ID: EV-W48-DIFF
Tracked hunks added by W48: none (zero src/test/config edits; read-only candidate rule honored)
New files: docs/wave-reports/v2/opencode/W48_WAVE_REPORT.md (this report; allowed closeout-only path)
Temp only: .tmp/w48-run/gj04_jobs.py + .tmp/w48-run/probe_slurm.py (never committed)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
Scope check: no sibling M file touched; no test weakened (zero skip/xfail/assertion edits); no secrets in report (key path referenced by role only, tokens redacted to class, job IDs are disposable scheduler IDs); no generated/binary noise.
```

## Handoff / DAG unlocks

Historical unlock target W55 is an integration hint only; no downstream Wave was started by this worker. Lab left suitable for the next serialized consumer (both disposable jobs ended — 70 COMPLETED, 71 CANCELLED — disposable remote dir removed, session closed, no jobs/files created).

## Findings and resume state

- No owned blocking defect remains. GJ-04 executes end-to-end on the integrated candidate: GUI slices 267/267 green + real EXTERNAL replay PASS.
- Cross-scope routes: none (no product defect observed; lab compute01-down is infrastructure state, recorded not routed as a product finding).
- No `AWAITING_INPUT` (no concrete missing artifact/API).
- No `EXTERNAL_BLOCKED` (real submit/run/complete/cancel all succeeded on compute02).
- No `TWO-FIX-EXCEPTION` needed: W48 owns a journey-replay requirement, not a stabilization quota; the candidate rule forbids manufacturing product fixes.
- Resume point: controller fresh independent audit of this READY_FOR_AUDIT candidate; auditor re-runs EV-W48-GUI slice commands + `.tmp/w48-run/gj04_jobs.py` verbatim (needs lab transport; allocates fresh disposable job IDs) and inspects EV-W48-DIFF (expect: report file only). If integration rebased sibling hunks in `slurm_models.py`/`output_follower.py`/`wx_jobs.py`/submit-cancel surfaces, re-run affected slices + replay first.

---

## Contradiction scan

- Lab status is uniformly reported as transport-healthy / Slurm partially-degraded-but-schedulable across report and raw output — no healthy-lab claim anywhere.
- PACKAGE status is uniformly NO-CANDIDATE — no artifact claim anywhere.
- Full-suite green is never claimed; only the GJ-04 slices are claimed green with exact counts.
- Cancel is uniformly a real `scancel` with `CANCELLED by <uid>` + empty squeue — no silent-cancel claim anywhere.
- Completion is uniformly `sacct COMPLETED` plus token + DONE-trailer file readbacks — no controller-only completion claim anywhere.
- The first (superseded) replay run is uniformly disclosed as a harness column-order artifact, never claimed as evidence; only the corrected second run is claimed.
- No test weakened; no product file touched.

## Review passes

- Claim-to-source: both owned IDs (`HPC-W10-GJ04-PATH-001`, `HPC-W10-GJ04-PATH-002`) trace to live owners (`services/job_submit_cancel.py`, `services/slurm_models.py`, `services/job_tracking_controller.py`, `services/jobs_refresh_state.py`, `services/output_follower.py`, wx jobs surfaces) + pinned tests/commands in this report.
- Diff review: zero tracked hunks by W48; sibling hunks explicitly disclaimed with re-run condition.
- Adversarial: token + DONE-trailer readbacks prove the job really ran to completion (not controller-only state); `CANCELLED by <uid>` + empty squeue proves the cancel really landed; live-tail chunks prove refresh/tail observed the running job (not post-hoc file reads); already-gone/unauthorized classification and overlapped-refresh suppression are pinned by the w30/w31 slices.

## Resume state

```text
Completed and verified:
- EV-W48-BASELINE (HEAD c8293d3, dirty-tree disclaimed, diff --check clean)
- EV-W48-GUI (51 + 29 + 44 + 74 + 16 + 53 = 267 passed, 0 failed; combined rerun 267/267)
- EV-W48-EXT (real LOCAL_REAL submit→PENDING→RUNNING→COMPLETED PASS job 70 + cancel→CANCELLED PASS job 71, token/DONE readbacks, live tail chunks, cancel reflection)
- EV-W48-PKG (NO-CANDIDATE, honestly recorded)
- EV-W48-DIFF (zero tracked hunks)

In progress: none
Open P0/P1: none
Open P2/P3: none
Pending tests/evidence: controller fresh independent audit
Last exact commands run:
- PYTHONPATH=src python -m pytest tests/test_job_tracking_controller.py tests/test_w28_jobs_identity_refresh.py tests/test_w29_job_outputs.py tests/test_job_failure_classifier.py -p no:cacheprovider -q → 51 passed
- PYTHONPATH=src python -m pytest tests/test_wx_jobs.py tests/test_wx_jobs_behavior.py tests/test_wx_jobs_final_fix.py -p no:cacheprovider -q → 29 passed
- PYTHONPATH=src python -m pytest tests/test_job_record_store.py tests/test_job_history_dashboard.py tests/test_job_provenance.py tests/test_wave5_slurm_jobs_unicode.py -p no:cacheprovider -q → 44 passed
- PYTHONPATH=src python -m pytest tests/test_wave78_jobs_details.py tests/test_corrective_jobs_details.py tests/test_selected_job_context.py tests/test_job_context.py -p no:cacheprovider -q → 74 passed
- PYTHONPATH=src python -m pytest tests/test_wx_jobs_files_outputs.py -p no:cacheprovider -q → 16 passed
- PYTHONPATH=src python -m pytest tests/test_w30_submit_cancel.py tests/test_w31_race_lifecycle.py tests/test_output_follower.py tests/test_slurm_ssh.py tests/test_w13_slurm_state.py -p no:cacheprovider -q → 53 passed
- PYTHONPATH=src python -m pytest <all 22 files above> -p no:cacheprovider -q → 267 passed
- PYTHONPATH=src python .tmp/w48-run/gj04_jobs.py → GJ04_EXTERNAL_RESULT: PASS (job 70 COMPLETED, job 71 CANCELLED)
- powershell -NoProfile -ExecutionPolicy Bypass -File lab/lab-status.ps1 → status=FAIL (slurm-only: compute01 down, compute02 idle), transport/services healthy

Next actions:
1. Controller fresh independent audit of W48 (re-run slices + harness, inspect diff).
2. On audit PASS, close W48 independently.

Evidence/artifact identities:
- EV-W48-BASELINE @ c8293d3
- EV-W48-GUI @ c8293d3 (267 passed / 0 failed)
- EV-W48-EXT vs LOCAL_REAL_HYPERV 192.168.250.11 (job 70 COMPLETED + DONE trailer, job 71 CANCELLED by 1000, live-tail token, cancel reflection)
- EV-W48-PKG: NO-CANDIDATE
- EV-W48-DIFF: report-file-only
```
