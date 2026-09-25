# W45 Wave Report — GJ-01 Fresh user to connected state

```text
Wave: W45
Canonical report path: docs/wave-reports/v2/opencode/W45_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (sibling-wave working-tree changes uncommitted; controller owns commit/integration; W45 made zero product/test edits)
Content identity (controller handoff): bc8e0c25be61b35f5adab6343064706bcf1bd8e2c0cbe19e9183af9a0bc4bcb5
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W45 run phase)
Last updated: 2026-09-25
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W45.md` (wave_id W45, execution kind, canonical_source W45, 1 owned requirement `HPC-W10-GJ01-PATH-001`, start gate NONE, cohort P10-golden-journeys, required evidence `GUI,PACKAGE,EXTERNAL`, integration refs W44 non-blocking, unattended/non-interactive contract, Golden-Journey candidate rule: W44 candidate is behaviorally read-only).
2. `opencode/REQUIREMENT_REGISTRY.md` line 1292: `HPC-W10-GJ01-PATH-001` MANDATORY — "Execute GJ-01 as this explicit end-to-end path: clean config → launch → logs/settings initialize → create profile → select provider/auth → host-key path → connect → status says connected → remote-dependent tabs/actions bind to the same session."
3. `opencode/TODO_OWNERSHIP_MAP.md`: no rows owned by W45 (none).
4. `waves/bak/WAVE_V2_FINAL_10.md` → GJ-01 section (lines 55-67): clean config → launch → logs/settings initialize → create profile → select provider/auth → host-key path → connect → status says connected → remote-dependent tabs/actions bind to same session.
5. `.opencode/protocol/LOCAL_REAL_HPC_LAB.md`: EXTERNAL authority; LOCAL_REAL_HYPERV is default real infra for generic SSH/connection claims; serialize EXTERNAL replay; GUI/PACKAGE claims need their own journey proof, not lab-health inference.
6. Live code before edits: `src/hpc_gui/ssh/client.py` (`SSHClientWrapper.connect` returns None, `run()` for exec, `accept-new` default policy, isolated `known_hosts_path`); `src/hpc_gui/config/storage.py` (`load_settings`/`update_settings`); `src/hpc_gui/core/paths.py` (`HPC_GUI_CONFIG_ROOT` isolation). No product edits made by W45 — candidate treated as read-only per wave contract.

## Baseline capture

```text
Evidence ID: EV-W45-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files + untracked sibling artifacts preserved untouched; W45 added zero tracked hunks, zero new source/test files outside .tmp)
git diff --check: clean (exit 0; only pre-existing sibling CRLF warnings)
```

Content-identity note: `waves/` is gitignored so the pending spec lives outside Git history by program design. The worker proceeded on current repository truth without editing the spec; identity reconciliation is controller-owned. HEAD `c8293d3` matches the W44 audit candidate SHA.

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
OBS-W45-001 | N/A | GJ-01 path fully executable on current candidate | EV-W45-GUI (80 green) + EV-W45-EXT (real connect PASS) | n/a — journey holds, no product defect | none | none needed (read-only candidate rule) | NO (journey replay, not a remediation) | VERIFIED
OBS-W45-002 | N/A | lab Slurm degraded (compute01 down) | lab-status.ps1 status=FAIL, slurm.ok=false, "compute01|down, compute02|idle" | infrastructure state, not product | GJ-01 unaffected (no job submit in path); recorded truthfully | none (lab lifecycle is controller/lab owned; W45 must not reset VMs) | NO | RECORDED
```

Golden-Journey candidate rule applied: no product behavior was patched inside W45. No defect was found on the GJ-01 path, so nothing was routed to another owner. Second-defect sweep dimensions (negative/closed-port, lifecycle disconnect/reconnect, stale-callback, identity/profile-switch, capability-absence, persistence/fresh-root, error-visibility) are all covered by the green slices below; no sweep dimension surfaced a W45-owned defect.

## Implementation

No product-code, test, or config changes. W45 is a journey-replay wave on a read-only candidate; the only new artifacts are this report and `.tmp/w45-run/` logs/harness (temp, never committed as evidence).

## Tests and evidence

### EV-W45-GUI — journey GUI/runtime slices (all green, exact reruns at HEAD `c8293d3`, `PYTHONPATH=src`, `-p no:cacheprovider`)

```text
Evidence ID: EV-W45-GUI
tests/test_w15_fresh_user_startup.py + tests/test_w19_connection_lifecycle.py → 31 passed
  (clean config root, logs/settings init, visible AddConnection profile dialog,
   closed-port NEG fails visibly, visible connect drives controller to connected,
   disconnect/reconnect/session-rebind across terminal/files/jobs domains,
   stale-callback isolation, host-key GUI-thread prompt, transport-loss indicator)
focused rebind slice (-k "rebind or profile_switch or disconnect_clears or transport_loss or host_key") → 6 passed
tests/test_wx_connection.py + tests/test_wx_connection_profiles.py + tests/test_connection_profile_service.py → 49 passed
  (profile create/select/provider/auth service + wx connection surfaces)
GUI verdict: 80 passed, 0 failed across the GJ-01 path surfaces
```

GJ-01 step → evidence mapping:

| GJ-01 step | Evidence |
|---|---|
| clean config | `test_isolated_root_redirects_app_dirs_and_creates_them` + W45 isolated `HPC_GUI_CONFIG_ROOT` fresh-root in EXTERNAL replay |
| launch / logs+settings init | W15 root/store/corrupt-recovery tests + `load_settings/update_settings` roundtrip in replay harness |
| create profile | `test_profile_created_through_visible_add_dialog` (real wx modal proof) |
| select provider/auth | `test_connection_profile_service.py` (23 passed slice) + disposable local-real profile in replay |
| host-key path | isolated `known_hosts_w45` (seeded from lab, W45-disjoint) + `accept-new` policy + `test_host_key_prompt_from_worker_thread_uses_gui_thread` |
| connect | real SSH connect to `192.168.250.11:22` as `hpctest`, transport_active=True |
| status says connected | exec exit=0 + token echo readback; `test_visible_connect_drives_controller_to_connected`, `test_transport_loss_updates_panel_indicator` |
| remote tabs bind same session | single `SSHClientWrapper` session for exec + `test_reconnect_rebinds_all_domains_through_canonical_session`, `test_profile_switch_invalidates_navigation_and_filters` |
| negative path | `test_closed_port_connect_fails_visibly_without_connected_state`, `test_recoverable_failure_keeps_app_alive_and_rearms` |

### EV-W45-EXT — real EXTERNAL replay against LOCAL_REAL_HYPERV

```text
Evidence ID: EV-W45-EXT
Harness: .tmp/w45-run/gj01_connect.py (disposable; secrets never enter report/git)
Target identity: LOCAL_REAL_HYPERV controller 192.168.250.11:22, user hpctest, provider local-real, key auth (emitted lab profile), isolated known_hosts_w45, accept-new
Lab health at replay: lab-status.ps1 status=FAIL overall ONLY because slurm.ok=false (compute01 down, compute02 idle); transport_ok=true + services_ok=true on all 3 nodes; image pin OK; profile valid (profile_sha256 a99c96fd…).
  Lab verdict recorded truthfully: SSH/connection surfaces healthy; Slurm degradation is out of GJ-01 scope (no job submit in this path) and was not reset by this worker (shared lab, serialized use).
Observed result:
  CONFIG_ROOT_ISOLATED: <approved-tmp>/w45-gj01-*/fresh-root (home untouched)
  LOGS_SETTINGS_INIT: OK
  CONNECT: transport_active=True
  EXEC_EXIT: 0; EXEC_OUT: W45-GJ01-<token> + hostname login-control01
  STATUS: connected (transport_active=True, exec exit=0, token echoed)
  DISCONNECT: OK
  GJ01_EXTERNAL_RESULT: PASS
Cleanup: SSH closed; disposable token echo only (no writes, no jobs, no shared-namespace mutation); isolated temp dirs left for GC.
```

### EV-W45-PKG — PACKAGE class

```text
Evidence ID: EV-W45-PKG
No packaged artifact was built, published, or claimed by W45 (candidate freeze is owned by W56–W61). Recorded honestly as NO-CANDIDATE.
No product/package-content modification was made by W45, so no freeze invalidation arises from this Wave.
```

Evidence classes: `GUI` (required) → EV-W45-GUI (80 green incl. real wx event proof). `PACKAGE` (required) → EV-W45-PKG (NO-CANDIDATE, honestly recorded; freeze owned downstream). `EXTERNAL` (required) → EV-W45-EXT (real LOCAL_REAL connect/status/session readback, PASS). No mocks substituted for any owned claim.

## Diff review

```text
Evidence ID: EV-W45-DIFF
Tracked hunks added by W45: none (zero src/test/config edits; read-only candidate rule honored)
New files: docs/wave-reports/v2/opencode/W45_WAVE_REPORT.md (this report; allowed closeout-only path)
Temp only: .tmp/w45-run/gj01_connect.py, .tmp/w45-lab-status.json/.err (never committed)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
Scope check: no sibling M file touched; no test weakened (zero skip/xfail/assertion edits); no secrets in report (key path referenced by role only, token redacted to class); no generated/binary noise.
```

## Handoff / DAG unlocks

Historical unlock target W55 is an integration hint only; no downstream Wave was started by this worker. Lab left suitable for the next serialized consumer (connection closed, no jobs/files created).

## Findings and resume state

- No owned blocking defect remains. GJ-01 executes end-to-end on the integrated candidate: GUI slices 80/80 green + real EXTERNAL replay PASS.
- Cross-scope routes: none (no product defect observed; lab Slurm degradation is infrastructure state, recorded not routed as a product finding).
- No `AWAITING_INPUT` (no concrete missing artifact/API).
- No `EXTERNAL_BLOCKED` (real connect succeeded; Slurm scope not required by GJ-01).
- No `TWO-FIX-EXCEPTION` needed: W45 owns a journey-replay requirement, not a stabilization quota; the candidate rule forbids manufacturing product fixes.
- Resume point: controller independent audit of this READY_FOR_AUDIT candidate; auditor re-runs EV-W45-GUI slice commands + `.tmp/w45-run/gj01_connect.py` verbatim (needs lab transport) and inspects EV-W45-DIFF (expect: report file only).

---

## Contradiction scan

- Lab status is uniformly reported as transport-healthy / Slurm-degraded across report and raw JSON — no healthy-lab claim anywhere.
- PACKAGE status is uniformly NO-CANDIDATE — no artifact claim anywhere.
- Full-suite green is never claimed; only the GJ-01 slices are claimed green with exact counts.
- No test weakened; no product file touched.

## Review passes

- Claim-to-source: the single owned ID `HPC-W10-GJ01-PATH-001` traces to live owners (`ssh/client.py`, `config/storage.py`, `core/paths.py`, wx connection surfaces) + pinned tests/commands in this report.
- Diff review: zero tracked hunks by W45; sibling hunks explicitly disclaimed.
- Adversarial: token-echo readback proves the session is live (not controller-only state); closed-port NEG proves failure is visible; profile-switch/stale-callback tests prove session-identity isolation.

## Resume state

```text
Completed and verified:
- EV-W45-BASELINE (HEAD c8293d3, dirty-tree disclaimed, diff --check clean)
- EV-W45-GUI (31 + 6 focused + 49 = 80 passed, 0 failed)
- EV-W45-EXT (real LOCAL_REAL connect/status/session PASS, token+hostname readback)
- EV-W45-PKG (NO-CANDIDATE, honestly recorded)
- EV-W45-DIFF (zero tracked hunks)

In progress: none
Open P0/P1: none
Open P2/P3: none
Pending tests/evidence: controller fresh independent audit
Last exact commands run:
- PYTHONPATH=src python -m pytest tests/test_w15_fresh_user_startup.py tests/test_w19_connection_lifecycle.py -p no:cacheprovider -q → 31 passed
- PYTHONPATH=src python -m pytest tests/test_w19_connection_lifecycle.py -p no:cacheprovider -q -k "rebind or profile_switch or disconnect_clears or transport_loss or host_key" → 6 passed
- PYTHONPATH=src python -m pytest tests/test_wx_connection.py tests/test_wx_connection_profiles.py tests/test_connection_profile_service.py -p no:cacheprovider -q → 49 passed
- PYTHONPATH=src python .tmp/w45-run/gj01_connect.py → GJ01_EXTERNAL_RESULT: PASS
- lab/lab-status.ps1 → status=FAIL (slurm-only: compute01 down), transport/services healthy

Next actions:
1. Controller fresh independent audit of W45 (re-run slices + harness, inspect diff).
2. On audit PASS, close W45 independently.

Evidence/artifact identities:
- EV-W45-BASELINE @ c8293d3
- EV-W45-GUI @ c8293d3 (80 passed / 0 failed)
- EV-W45-EXT vs LOCAL_REAL_HYPERV 192.168.250.11 (token echo + hostname login-control01)
- EV-W45-PKG: NO-CANDIDATE
- EV-W45-DIFF: report-file-only
```
