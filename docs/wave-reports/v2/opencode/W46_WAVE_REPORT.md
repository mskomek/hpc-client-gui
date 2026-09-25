# W46 Wave Report — GJ-02 Connection and terminal lifecycle

```text
Wave: W46
Canonical report path: docs/wave-reports/v2/opencode/W46_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (sibling-wave working-tree changes uncommitted; controller owns commit/integration; W46 made zero product/test edits)
Content identity (controller handoff): bc8e0c25be61b35f5adab6343064706bcf1bd8e2c0cbe19e9183af9a0bc4bcb5
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W46 run phase)
Last updated: 2026-09-25
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W46.md` (wave_id W46, execution kind, canonical_source W46, 1 owned requirement `HPC-W10-GJ02-PATH-001`, start gate NONE, cohort P10-golden-journeys, required evidence `GUI,PACKAGE,EXTERNAL`, integration refs W44 non-blocking, unattended/non-interactive contract, Golden-Journey candidate rule: W44 candidate is behaviorally read-only).
2. `opencode/REQUIREMENT_REGISTRY.md`: `HPC-W10-GJ02-PATH-001` MANDATORY — "Execute GJ-02 as this explicit end-to-end path: connect → terminal ready → command/output → disconnect → remote controls truthfully disabled/stale → reconnect → terminal operates on the new session only."
3. `opencode/TODO_OWNERSHIP_MAP.md`: no rows owned by W46 (verified: `NO_W46_ROWS`).
4. `opencode/sources/WAVE_V2_FINAL_10.md` → GJ-02 section (lines 69-79): connect → terminal ready → command/output → disconnect → remote controls truthfully disabled/stale → reconnect → terminal operates on new session only.
5. `.opencode/protocol/LOCAL_REAL_HPC_LAB.md`: EXTERNAL authority; LOCAL_REAL_HYPERV is default real infra for generic SSH/connection claims; serialize EXTERNAL replay; GUI/PACKAGE claims need their own journey proof, not lab-health inference.
6. Live code before edits: `src/hpc_gui/ssh/client.py` (`SSHClientWrapper.connect`, `run()` for exec, `close()` best-effort teardown, `accept-new` default policy, isolated `known_hosts_path`); `src/hpc_gui/ssh/shell_session.py` (`InteractiveShellSession` PTY lifecycle owned by wx terminal panel); wx terminal/shell surfaces (`src/hpc_gui/wx_shell.py` disconnect-rebind + generation bump, terminal panel ssh swap). No product edits made by W46 — candidate treated as read-only per wave contract.

## Baseline capture

```text
Evidence ID: EV-W46-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files + untracked sibling artifacts preserved untouched; W46 added zero tracked hunks, zero new source/test files outside .tmp)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
git log -1: c8293d3c (HEAD -> develop) Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
```

Content-identity note: `waves/` is gitignored so the pending spec lives outside Git history by program design. The worker proceeded on current repository truth without editing the spec; identity reconciliation is controller-owned. HEAD `c8293d3` matches the W44 audit candidate SHA and the W45 baseline.

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
OBS-W46-001 | N/A | GJ-02 path fully executable on current candidate | EV-W46-GUI (83 green) + EV-W46-EXT (connect/exec/disconnect/stale/reconnect PASS) | n/a — journey holds, no product defect | none | none needed (read-only candidate rule) | NO (journey replay, not a remediation) | VERIFIED
OBS-W46-002 | N/A | lab Slurm degraded (compute01 down) | lab-status.ps1 status=FAIL, slurm.ok=false, "compute01|down, compute02|idle"; transport_ok=true + services_ok=true on all 3 nodes | infrastructure state, not product | GJ-02 unaffected (no job submit in path); recorded truthfully | none (lab lifecycle is controller/lab owned; W46 must not reset VMs) | NO | RECORDED
```

Golden-Journey candidate rule applied: no product behavior was patched inside W46. No defect was found on the GJ-02 path, so nothing was routed to another owner. Second-defect sweep dimensions (negative/closed-port via W45 slice reference, disconnect gating, stale-callback isolation, fresh-session identity, profile-switch invalidation, transport-loss indicator, terminal detach, host-key GUI-thread) are all covered by the green slices below; no sweep dimension surfaced a W46-owned defect.

## Implementation

No product-code, test, or config changes. W46 is a journey-replay wave on a read-only candidate; the only new artifacts are this report and `.tmp/w46-run/` harness (temp, never committed as evidence).

## Tests and evidence

### EV-W46-GUI — journey GUI/runtime slices (all green, exact reruns at HEAD `c8293d3`, `PYTHONPATH=src`, `-p no:cacheprovider`)

```text
Evidence ID: EV-W46-GUI
tests/test_w19_connection_lifecycle.py + tests/test_wx_terminal.py + tests/test_wx_embedded_terminal.py + tests/test_wx_terminal_behavioral.py + tests/test_wx_terminal_parity_evidence.py → 62 passed
  (connect supersede/cancel-safe, stale-transport-callback isolation, matching-callback fail+invalidate,
   no-live-session drop, fresh-session mint, best-effort close, panel disconnect clears session + gates remote,
   shell disconnect rebinds terminal + bumps generation, terminal detaches stale subscriber,
   GUI-thread marshal, host-key GUI-thread prompt, transport-loss indicator,
   terminal ready/render/font/clear/find/resize/PT up to parity evidence)
focused lifecycle slice (-k "reconnect or disconnect or stale or rebind or profile_switch or transport_loss or detach or fresh_session or supersedes") → 9 passed
tests/test_wx_shell_p0.py + tests/test_wx_connection.py → 21 passed
  (wx shell lifecycle P0 + visible connection surfaces)
GUI verdict: 83 passed, 0 failed across the GJ-02 path surfaces (62 + 21; focused 9 is a subset, not double-counted)
```

GJ-02 step → evidence mapping:

| GJ-02 step | Evidence |
|---|---|
| connect | `test_repeated_connect_supersedes_without_conflict`, `test_model_cancel_while_connecting_returns_to_safe_state`, real SSH connect to `192.168.250.11:22` as `hpctest`, transport_active=True |
| terminal ready | wx terminal/embedded/behavioral/parity slices (panel build, render, font/find/clear, resize→pty, lifecycle) + live-session exec readback in EXTERNAL replay |
| command/output | `EXEC_1_EXIT: 0`, token `W46-GJ02-A-*` + hostname `login-control01` echoed on live session |
| disconnect | `test_panel_disconnect_clears_session_and_gates_remote`, `test_shell_disconnect_rebinds_terminal_and_bumps_generation`, real `DISCONNECT_1: closed old_transport_active=False` |
| remote controls truthfully disabled/stale | `test_stale_transport_callback_cannot_fail_new_session`, `test_terminal_detaches_stale_output_subscriber`, `test_transport_callback_without_live_session_is_dropped`, real `STALE_GATED: closed-session exec raised RuntimeError` |
| reconnect | `test_reconnect_mints_fresh_session_identity`, `test_reconnect_rebinds_all_domains_through_canonical_session`, real `RECONNECT_2: transport_active=True` |
| terminal operates on new session only | `test_stale_transport_callback_cannot_fail_new_session` + `test_profile_switch_invalidates_navigation_and_filters` + real `NEW_SESSION_ONLY: OK (fresh token echoed, old token absent)` |
| negative path | closed-port NEG covered by GJ-01 slice reference (same connection stack); `test_recoverable_failure_keeps_app_alive_and_rearms`, `test_matching_transport_callback_fails_and_invalidates` |

### EV-W46-EXT — real EXTERNAL replay against LOCAL_REAL_HYPERV

```text
Evidence ID: EV-W46-EXT
Harness: .tmp/w46-run/gj02_lifecycle.py (disposable; secrets never enter report/git)
Target identity: LOCAL_REAL_HYPERV controller 192.168.250.11:22, user hpctest, provider local-real, key auth (emitted lab profile), isolated known_hosts_w46, accept-new
Lab health at replay: lab-status.ps1 status=FAIL overall ONLY because slurm.ok=false (compute01 down, compute02 idle); transport_ok=true + services_ok=true on all 3 nodes.
  Lab verdict recorded truthfully: SSH/connection surfaces healthy; Slurm degradation is out of GJ-02 scope (no job submit in this path) and was not reset by this worker (shared lab, serialized use).
Observed result:
  CONFIG_ROOT_ISOLATED: <approved-tmp>/w46-gj02-*/fresh-root (home untouched)
  CONNECT_1: transport_active=True
  EXEC_1_EXIT: 0; EXEC_1_OUT: W46-GJ02-A-* + hostname login-control01
  TERMINAL_READY_1: OK
  DISCONNECT_1: closed old_transport_active=False
  STALE_GATED: closed-session exec raised RuntimeError (truthful visible failure, no silent success)
  RECONNECT_2: transport_active=True
  EXEC_2_EXIT: 0; EXEC_2_OUT: W46-GJ02-B-* + hostname login-control01 (old token absent)
  NEW_SESSION_ONLY: OK
  DISCONNECT_2: OK
  GJ02_EXTERNAL_RESULT: PASS
Cleanup: both sessions closed; disposable token echo only (no writes, no jobs, no shared-namespace mutation); isolated temp dirs left for GC.
```

### EV-W46-PKG — PACKAGE class

```text
Evidence ID: EV-W46-PKG
No packaged artifact was built, published, or claimed by W46 (candidate freeze is owned by W56–W61). Recorded honestly as NO-CANDIDATE.
No product/package-content modification was made by W46, so no freeze invalidation arises from this Wave.
```

Evidence classes: `GUI` (required) → EV-W46-GUI (83 green incl. real wx event proof). `PACKAGE` (required) → EV-W46-PKG (NO-CANDIDATE, honestly recorded; freeze owned downstream). `EXTERNAL` (required) → EV-W46-EXT (real LOCAL_REAL connect/exec/disconnect/stale/reconnect readback, PASS). No mocks substituted for any owned claim.

## Diff review

```text
Evidence ID: EV-W46-DIFF
Tracked hunks added by W46: none (zero src/test/config edits; read-only candidate rule honored)
New files: docs/wave-reports/v2/opencode/W46_WAVE_REPORT.md (this report; allowed closeout-only path)
Temp only: .tmp/w46-run/gj02_lifecycle.py (never committed)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
Scope check: no sibling M file touched; no test weakened (zero skip/xfail/assertion edits); no secrets in report (key path referenced by role only, tokens redacted to class); no generated/binary noise.
```

## Handoff / DAG unlocks

Historical unlock target W55 is an integration hint only; no downstream Wave was started by this worker. Lab left suitable for the next serialized consumer (both sessions closed, no jobs/files created).

## Findings and resume state

- No owned blocking defect remains. GJ-02 executes end-to-end on the integrated candidate: GUI slices 83/83 green + real EXTERNAL replay PASS.
- Cross-scope routes: none (no product defect observed; lab Slurm degradation is infrastructure state, recorded not routed as a product finding).
- No `AWAITING_INPUT` (no concrete missing artifact/API).
- No `EXTERNAL_BLOCKED` (real connect/exec/reconnect succeeded; Slurm scope not required by GJ-02).
- No `TWO-FIX-EXCEPTION` needed: W46 owns a journey-replay requirement, not a stabilization quota; the candidate rule forbids manufacturing product fixes.
- Resume point: controller independent audit of this READY_FOR_AUDIT candidate; auditor re-runs EV-W46-GUI slice commands + `.tmp/w46-run/gj02_lifecycle.py` verbatim (needs lab transport) and inspects EV-W46-DIFF (expect: report file only).

---

## Contradiction scan

- Lab status is uniformly reported as transport-healthy / Slurm-degraded across report and raw output — no healthy-lab claim anywhere.
- PACKAGE status is uniformly NO-CANDIDATE — no artifact claim anywhere.
- Full-suite green is never claimed; only the GJ-02 slices are claimed green with exact counts.
- Stale gating is uniformly a visible failure (RuntimeError) — no silent-success claim anywhere.
- No test weakened; no product file touched.

## Review passes

- Claim-to-source: the single owned ID `HPC-W10-GJ02-PATH-001` traces to live owners (`ssh/client.py`, `ssh/shell_session.py`, wx terminal/shell surfaces) + pinned tests/commands in this report.
- Diff review: zero tracked hunks by W46; sibling hunks explicitly disclaimed.
- Adversarial: dual-token readback proves the reconnected terminal is a new session (not resurrected old state); closed-session exec raising proves stale gating is truthful; stale-callback/detach/profile-switch tests prove session-identity isolation.

## Resume state

```text
Completed and verified:
- EV-W46-BASELINE (HEAD c8293d3, dirty-tree disclaimed, diff --check clean)
- EV-W46-GUI (62 + 21 = 83 passed, 0 failed; focused lifecycle 9/9 subset)
- EV-W46-EXT (real LOCAL_REAL connect/exec/disconnect/stale/reconnect PASS, dual-token + hostname readback)
- EV-W46-PKG (NO-CANDIDATE, honestly recorded)
- EV-W46-DIFF (zero tracked hunks)

In progress: none
Open P0/P1: none
Open P2/P3: none
Pending tests/evidence: controller fresh independent audit
Last exact commands run:
- PYTHONPATH=src python -m pytest tests/test_w19_connection_lifecycle.py tests/test_wx_terminal.py tests/test_wx_embedded_terminal.py tests/test_wx_terminal_behavioral.py tests/test_wx_terminal_parity_evidence.py -p no:cacheprovider -q → 62 passed
- PYTHONPATH=src python -m pytest tests/test_w19_connection_lifecycle.py -p no:cacheprovider -q -k "reconnect or disconnect or stale or rebind or profile_switch or transport_loss or detach or fresh_session or supersedes" → 9 passed
- PYTHONPATH=src python -m pytest tests/test_wx_shell_p0.py tests/test_wx_connection.py -p no:cacheprovider -q → 21 passed
- PYTHONPATH=src python .tmp/w46-run/gj02_lifecycle.py → GJ02_EXTERNAL_RESULT: PASS
- powershell -NoProfile -ExecutionPolicy Bypass -File lab/lab-status.ps1 → status=FAIL (slurm-only: compute01 down), transport/services healthy

Next actions:
1. Controller fresh independent audit of W46 (re-run slices + harness, inspect diff).
2. On audit PASS, close W46 independently.

Evidence/artifact identities:
- EV-W46-BASELINE @ c8293d3
- EV-W46-GUI @ c8293d3 (83 passed / 0 failed)
- EV-W46-EXT vs LOCAL_REAL_HYPERV 192.168.250.11 (dual-token echo + hostname login-control01, stale RuntimeError, old-token-absent)
- EV-W46-PKG: NO-CANDIDATE
- EV-W46-DIFF: report-file-only
```
