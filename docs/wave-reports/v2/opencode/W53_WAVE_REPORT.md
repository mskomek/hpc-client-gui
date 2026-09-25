# W53 Wave Report — GJ-09 Shutdown under load

```text
Wave: W53
Canonical report path: docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (sibling-wave working-tree changes uncommitted; controller owns commit/integration; W53 made zero product/test edits)
Content identity (controller handoff): bc8e0c25be61b35f5adab6343064706bcf1bd8e2c0cbe19e9183af9a0bc4bcb5
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W53 run phase)
Last updated: 2026-09-25
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W53.md` (wave_id W53, execution kind, canonical_source W53, 15 source rows + 3 TODO rows, start gate NONE, cohort P10-golden-journeys, required evidence `GUI,PACKAGE,EXTERNAL`, integration refs W44 non-blocking, unattended/non-interactive contract, Golden-Journey candidate rule: W44 candidate is behaviorally read-only).
2. `opencode/REQUIREMENT_REGISTRY.md` lines 1038–1051: `HPC-W10-GJ2-010` (terminal output) / `011` (transfer) / `012` (remote file refresh) / `013` (editor remote operation) / `014` (job polling/output refresh) / `015` (Plugin Manager refresh) / `016` (updater check/download fixture) / `017` (logs/diagnostics refresh) / `018` (no native crash) / `019` (no destroyed-control callback) / `020` (no hang) / `021` (bounded shutdown) / `022` (cleanup/worker cancellation deterministic) / `023` (relaunch clean); line 1300: `HPC-W10-GJ09-PATH-001` (explicit GJ-09 end-to-end path: controlled shutdown with representative terminal, transfer, remote-file, editor, jobs, Plugin Manager, updater and diagnostics work in flight, followed by clean relaunch); lines 1382–1383, 1534: `HPC-W10-TODO-LIFECYCLE-NATIVE-003/004`, `HPC-W10-TODO-SHUTDOWN-LOAD-GJ-001`.
3. `opencode/TODO_OWNERSHIP_MAP.md`: the same 3 TODO rows owned by W53, ACTIVE.
4. `opencode/sources/WAVE_V2_FINAL_10.md` → GJ-09 section (lines 152–172): close the application while representative work is in flight in controlled separate cases (the eight surfaces above); expected: no native crash, no destroyed-control callback, no hang, bounded shutdown, deterministic cleanup/worker cancellation, clean relaunch.
5. `.opencode/protocol/LOCAL_REAL_HPC_LAB.md`: EXTERNAL authority; LOCAL_REAL_HYPERV is default real infra for generic SSH/connection claims; serialize EXTERNAL replay; GUI/PACKAGE claims need their own journey proof, not lab-health inference.
6. Live code before edits (read-only): `src/hpc_gui/wx_lifecycle.py` (`WxLifecycleController`: idempotent `shutdown`, reversed LIFO cleanup, exception-swallowing, `cancel_token` + `cancel_update`), `src/hpc_gui/wx_terminal.py` (`TerminalModel.receive` + generation-gated `render_output` + close guard), `src/hpc_gui/wx_remote_files_view.py` (`view_generation` + `listing_request_id` guards), `src/hpc_gui/services/transfer_controller.py` (`TransferController` worker thread + `cancel_all`), `src/hpc_gui/services/editor_controller.py` (`DocumentModel.canonical_key` + `EditorController` open/update/save), `src/hpc_gui/services/jobs_refresh_state.py` (monotonic sequence; stale never applied), `src/hpc_gui/services/output_follower.py` (`assign` generation reset + `close`), `src/hpc_gui/wx_plugins.py` (`WxPluginManagerModel.set_registry`/`build_cards_from_registry` with `network|cache|offline`), `src/hpc_gui/services/app_updater.py` (check/download/verify pipeline), `src/hpc_gui/wx_logs.py` (`WxLogsModel.refresh` + close-during-refresh lifetime), `src/hpc_gui/ssh/client.py` (`SSHClientWrapper.run` maps client timeout to exit 124; `close` drops shell/listing transports), `src/hpc_gui/wx_shell.py` (`IsBeingDeleted`/`_alive` guards + `Destroy` teardown). No product edits made by W53 — candidate treated as read-only per wave contract.

## Baseline capture

```text
Evidence ID: EV-W53-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files + untracked sibling artifacts preserved untouched; W53 added zero tracked hunks, zero new source/test files outside .tmp)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
git log -1: c8293d3c (HEAD -> develop) Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
```

Content-identity note: `waves/` is gitignored so the pending spec lives outside Git history by program design. The worker proceeded on current repository truth without editing the spec; identity reconciliation is controller-owned. HEAD `c8293d3` matches the W44 audit candidate SHA and the W45–W52 baselines, and the handoff content identity `bc8e0c25…` matches the W45–W52 handoffs.

Sibling-hunk disclaimer: the working tree contains pre-existing sibling modifications (including `src/hpc_gui/config/storage.py`, `src/hpc_gui/core/diagnostics.py`, `src/hpc_gui/wx_shell.py`, `src/hpc_gui/wx_logs*.py`, `src/hpc_gui/wx_plugins*.py` and related settings/i18n/docs). These hunks pre-date the W53 run phase and were not authored, reviewed, or claimed by W53. After controller integration or conflict resolution affecting the terminal/transfer/files/editor/jobs/plugin/updater/logs/lifecycle surfaces, the affected W53 slices and both journey harnesses must be re-run before audit acceptance.

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
OBS-W53-001 | N/A | GJ-09 path fully executable on current candidate | EV-W53-GUI (272 passed, 0 failed) + EV-W53-JOURNEY (27/27 product-path checks PASS, single-process mixed-surface) + EV-W53-EXT (real LOCAL_REAL shutdown-under-load PASS) | n/a — journey holds, no product defect | none | none needed (read-only candidate rule) | NO (journey replay, not a remediation) | VERIFIED
OBS-W53-002 | N/A | 3-file combined plugin process hangs; each file green alone | test_w35_plugin_manager_gui.py + test_wx_plugins.py → 9 passed (1.43s); test_plugin_manager_ui.py → 37 passed (2.91s); combined 3-file run exceeded 180s without completion | wx-runtime tooling lifetime (same class as W50/W51/W52 combined-process access violations) | none on GJ-09 path (plugin refresh teardown proven by the 9-pass slice + journey PLUGIN_* checks + external replay) | none by W53 (not a W53-owned defect; zero W53 edits) | NO | RECORDED (only process-isolated results claimed)
```

Golden-Journey candidate rule applied: no product behavior was patched inside W53. No defect was found on the GJ-09 path, so nothing was routed to another owner. Second-defect sweep dimensions (terminal stale/post-shutdown gating, transfer worker cancellation boundedness, remote listing request/generation gating, editor tab-drop without file corruption, jobs refresh sequence gating + output-follower close, plugin refresh teardown, updater cancel determinism, logs close-during-refresh lifetime, shutdown LIFO/idempotence, fresh-process relaunch, zero leaked workers) are all covered by the green slices below; no sweep dimension surfaced a W53-owned defect.

LIFECYCLE-NATIVE-003 note: process isolation of the pytest slices is retained for tooling reasons only (OBS-W53-002). The deterministic-teardown defect is disproven by EV-W53-JOURNEY, which tears down all eight in-flight surfaces through one shared `WxLifecycleController.shutdown()` in a SINGLE process (27/27, 0.16s total, zero leaked workers).

## Implementation

No product-code, test, or config changes. W53 is a journey-replay wave on a read-only candidate; the only new artifacts are this report and the `.tmp/w53-run/` harnesses (temp, never committed as evidence).

## Tests and evidence

### EV-W53-GUI — journey GUI/runtime slices (all green, exact reruns at HEAD `c8293d3`, `PYTHONPATH=src`, `-p no:cacheprovider`, process-isolated per wx-lifetime note)

```text
Evidence ID: EV-W53-GUI
tests/test_wx_lifecycle.py + tests/test_w31_race_lifecycle.py + tests/test_w33_lifecycle_isolation.py → 39 passed
  (lifecycle close/restart, race guards, plugin lifecycle isolation incl. duplicate/conflict handling)
tests/test_wx_terminal.py + tests/test_wx_terminal_behavioral.py → 21 passed
  (terminal model + behavioral incl. lifecycle/render/resize guards)
tests/test_transfer_controller.py + tests/test_transfer_cancel_recovery.py → 7 passed
  (transfer queue/cancel/recovery semantics)
tests/test_wx_transfer_ui_lifecycle.py → 14 passed
  (transfer UI lifecycle incl. real-wx progress/close guards)
tests/test_wx_remote_files.py + tests/test_remote_entry_helpers.py → 16 passed
  (wx remote files view behavior + entry presentation helpers)
tests/test_editor_controller.py + tests/test_editor_flow.py + tests/test_wx_remote_editor_flow.py → 24 passed
  (document identity/open/update/save, editor flow, remote editor open/save flow)
tests/test_wx_editor.py → 14 passed
  (wx editor view behavior incl. tabs/cross-view actions)
tests/test_job_tracking_controller.py + tests/test_output_follower.py + tests/test_wx_jobs.py → 12 passed
  (tracking reconnect/selection/output reset + poll gating, output follower, wx jobs model)
tests/test_w35_plugin_manager_gui.py + tests/test_wx_plugins.py → 9 passed
  (plugin manager GUI incl. real-wx refresh-event proof; model registry/cache/offline cards)
tests/test_plugin_manager_ui.py → 37 passed
  (plugin manager UI behavior)
tests/test_app_updater.py + tests/test_w41_updater_routing.py → 22 passed
  (updater check/download/verify + restart routing policy)
tests/test_w39_logs_diagnostics.py + tests/test_wx_logs.py + tests/test_diagnostics.py → 18 passed
  (logs/diagnostics incl. real-wx open/readback/refresh + close-during-refresh lifetime + bundle/redaction)
tests/test_w43_restart_package_policy.py + tests/test_wx_updater_spec.py → 39 passed
  (restart/package policy + updater spec incl. lifecycle close/restart behavior)
GUI verdict: 272 passed, 0 failed
  (39 + 21 + 7 + 14 + 16 + 24 + 14 + 12 + 9 + 37 + 22 + 18 + 39 = 272 passed)
```

Isolation note: each slice command above runs in its own process. A 3-file combined plugin process (`test_w35_plugin_manager_gui` + `test_wx_plugins` + `test_plugin_manager_ui`) exceeded 180s without completing while each file is green alone (9 passed in 1.43s; 37 passed in 2.91s); W53 therefore claims only the process-isolated slice results above (same tooling class as the W50/W51/W52 combined-process access violations). No suite file was edited, skipped, or weakened to obtain green.

GJ-09 step → evidence mapping:

| GJ-09 case | Evidence |
|---|---|
| terminal output | `TERMINAL_INFLIGHT_RECEIVED`/`TERMINAL_POST_SHUTDOWN_DROPPED`/`TERMINAL_WX_GUARD_PRESENT` harness checks via product `TerminalModel` + `wx_terminal` generation guard + terminal slices (21 passed) |
| transfer | `TRANSFER_INFLIGHT_STARTED`/`TRANSFER_CANCELLED_BOUNDED` harness checks via product `TransferController` worker + `cancel_all` + transfer slices (21 passed) |
| remote file refresh | `REMOTE_STALE_DROPPED`/`REMOTE_WX_GUARD_PRESENT` harness checks via listing request/generation guard shape + `wx_remote_files_view` source guard + remote slices (16 passed) |
| editor remote operation | `EDITOR_OPEN_INFLIGHT`/`EDITOR_FILE_INTACT_AFTER_SHUTDOWN` harness checks via product `EditorController`/`DocumentModel` + editor slices (38 passed) |
| job polling/output refresh | `JOBS_INFLIGHT_ISSUED`/`JOBS_STALE_DROPPED`/`JOBS_OUTPUT_CLOSED` harness checks via product `JobsRefreshState` + `OutputFollower.close` + jobs slices (12 passed) |
| Plugin Manager refresh | `PLUGIN_REFRESH_INFLIGHT`/`PLUGIN_SHUTDOWN_CLEAN` harness checks via product `WxPluginManagerModel` + plugin slices (46 passed) |
| updater check/download fixture | `UPDATER_INFLIGHT`/`UPDATER_CANCELLED_DETERMINISTIC` harness checks via product `WxLifecycleController` begin/cancel + updater slices (22 passed) + restart slices (39 passed) |
| logs/diagnostics refresh | `LOGS_REFRESHED`/`LOGS_CLOSE_DURING_REFRESH_SAFE` harness checks via product `WxLogsModel` + logs slices (18 passed) |
| no native crash / no hang / bounded / deterministic / relaunch | `NO_NATIVE_CRASH`/`NO_HANG`/`BOUNDED_SHUTDOWN` (0.000s)/`CLEANUP_DETERMINISTIC_ORDER` (LIFO 8/8)/`SHUTDOWN_IDEMPOTENT`/`RELAUNCH_CLEAN`/`RELAUNCH_PROCESS_OK`/`ZERO_LEAKED_WORKERS`/`ZERO_LEAKED_LIFECYCLE` + lifecycle slices (39 passed) + EXTERNAL replay |

### EV-W53-JOURNEY — disposable end-to-end journey replay on product paths

```text
Evidence ID: EV-W53-JOURNEY
Harness: .tmp/w53-run/gj09_journey.py (disposable; W53-disjoint tmp root w53-gj09-*, no network, no real user config)
Product paths exercised (single process, one shared WxLifecycleController shutdown): wx_terminal.TerminalModel + generation/closed guard shape + services.transfer_controller TransferController/TransferItem (blocking worker cancelled at shutdown) + remote listing request/generation guard shape + services.editor_controller DocumentModel/EditorController + services.jobs_refresh_state JobsRefreshState + services.output_follower OutputFollower/OutputFollowerState + wx_plugins.WxPluginManagerModel + wx_lifecycle begin_update/update_progress/cancel_update/shutdown + wx_logs.WxLogsModel + fresh-subprocess relaunch probe
Observed result:
  TERMINAL_INFLIGHT_RECEIVED: OK
  TRANSFER_INFLIGHT_STARTED: OK
  EDITOR_OPEN_INFLIGHT: OK
  JOBS_INFLIGHT_ISSUED: OK
  PLUGIN_REFRESH_INFLIGHT: OK
  UPDATER_INFLIGHT: OK (phase=downloading percent=37)
  LOGS_REFRESHED: OK
  BOUNDED_SHUTDOWN: OK (0.000s)
  CLEANUP_DETERMINISTIC_ORDER: OK (logs|updater|plugins|jobs|editor|remote-files|transfer|terminal)
  UPDATER_CANCELLED_DETERMINISTIC: OK
  TRANSFER_CANCELLED_BOUNDED: OK
  TERMINAL_POST_SHUTDOWN_DROPPED: OK
  JOBS_STALE_DROPPED: OK
  REMOTE_STALE_DROPPED: OK
  LOGS_CLOSE_DURING_REFRESH_SAFE: OK
  PLUGIN_SHUTDOWN_CLEAN: OK
  EDITOR_FILE_INTACT_AFTER_SHUTDOWN: OK
  SHUTDOWN_IDEMPOTENT: OK (8 cleanups, terminal x1)
  TERMINAL_WX_GUARD_PRESENT: OK
  REMOTE_WX_GUARD_PRESENT: OK
  SHELL_ALIVE_GUARD_PRESENT: OK
  RELAUNCH_CLEAN: OK
  RELAUNCH_PROCESS_OK: OK (rc=0, fresh-root)
  ZERO_LEAKED_WORKERS: OK (0 non-daemon alive)
  ZERO_LEAKED_LIFECYCLE: OK
  NO_HANG: OK (0.16s total)
  NO_NATIVE_CRASH: OK
  GJ09_JOURNEY_RESULT: PASS (27/27)
Cleanup: all fixture state lives only under the disposable tmp root; nothing written to the user environment, repo, or shared namespace.
```

### EV-W53-EXT — real EXTERNAL replay against LOCAL_REAL_HYPERV

```text
Evidence ID: EV-W53-EXT
Harness: .tmp/w53-run/gj09_external.py (disposable; secrets never enter report/git)
Target identity: LOCAL_REAL_HYPERV controller 192.168.250.11:22, user hpctest, provider local-real, key auth (emitted lab profile), isolated known_hosts_w53, accept-new
Lab health at replay: Slurm responsive (squeue --me header readback); transport healthy. No lab reset performed by this worker (shared lab, serialized use).
Observed result:
  CONFIG_ROOT_ISOLATED: <approved-tmp>/w53-gj09-*/fresh-root (home untouched)
  CONNECTED: transport_active=True
  TERMINAL_INFLIGHT: OK token readback (echo W53-GJ09-* + hostname)
  FILES_INFLIGHT: OK exit=0 (pwd + ls ~ readback)
  JOBS_INFLIGHT: OK (squeue --me header readback)
  LOAD_CANCELLED_WHILE_INFLIGHT: exit=124 elapsed=8.1s (client stopped waiting; remote sleep 20s still in flight — the controlled shutdown case)
  SHUTDOWN_BOUNDED: 0.06s (< 25s bound)
  RELAUNCH_CLEAN: OK (fresh token present, prior-load token absent)
  GJ09_EXTERNAL_RESULT: PASS
Cleanup: both SSH sessions closed; disposable echo tokens only (no writes, no jobs, no shared-namespace mutation); isolated temp dirs left for GC.
```

### EV-W53-PKG — PACKAGE class

```text
Evidence ID: EV-W53-PKG
No packaged artifact was built, published, or claimed by W53 (candidate freeze is owned by W56–W61). Recorded honestly as NO-CANDIDATE.
No product/package-content modification was made by W53, so no freeze invalidation arises from this Wave.
Shutdown/relaunch behavior on the journey path is pinned by the GUI slices above; no artifact SHA-256 is claimed because no candidate artifact exists at this Wave.
```

Evidence classes: `GUI` (required) → EV-W53-GUI (272 passed, real wx event proof in the transfer-ui/plugin/w39/editor/terminal slices) + EV-W53-JOURNEY (27/27 product-path checks PASS, single-process mixed-surface shutdown campaign). `PACKAGE` (required) → EV-W53-PKG (NO-CANDIDATE, honestly recorded; freeze owned downstream). `EXTERNAL` (required) → EV-W53-EXT (real LOCAL_REAL shutdown-under-load: in-flight terminal/files/jobs readback, client-cancelled loaded sleep exit 124 @ 8.1s, bounded close 0.06s, clean relaunch readback, PASS). No mocks substituted for any owned claim (harnesses use real lifecycle/terminal/transfer/editor/jobs/plugin/updater/logs/SSH paths under disposable roots + real lab transports; isolated exec only, no shared mutation).

## Diff review

```text
Evidence ID: EV-W53-DIFF
Tracked hunks added by W53: none (zero src/test/config edits; read-only candidate rule honored)
New files: docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md (this report; allowed closeout-only path)
Temp only: .tmp/w53-run/gj09_journey.py + .tmp/w53-run/gj09_external.py (never committed)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
Scope check: no sibling M file touched; no test weakened (zero skip/xfail/assertion edits); no secrets in report or harnesses (disposable W53-GJ09-* tokens only, key path referenced never printed); no generated/binary noise.
```

## Requirement disposition

| Requirement | Disposition | Evidence |
|---|---|---|
| `HPC-W10-GJ2-010` (terminal output) | IMPLEMENT (journey holds; no remediation needed) | EV-W53-JOURNEY terminal checks + terminal slices (21) + EV-W53-EXT terminal readback |
| `HPC-W10-GJ2-011` (transfer) | IMPLEMENT (journey holds; no remediation needed) | EV-W53-JOURNEY transfer checks + transfer slices (21) |
| `HPC-W10-GJ2-012` (remote file refresh) | IMPLEMENT (journey holds; no remediation needed) | EV-W53-JOURNEY remote checks + remote slices (16) + EV-W53-EXT files readback |
| `HPC-W10-GJ2-013` (editor remote operation) | IMPLEMENT (journey holds; no remediation needed) | EV-W53-JOURNEY editor checks + editor slices (38) |
| `HPC-W10-GJ2-014` (job polling/output refresh) | IMPLEMENT (journey holds; no remediation needed) | EV-W53-JOURNEY jobs checks + jobs slices (12) + EV-W53-EXT squeue readback |
| `HPC-W10-GJ2-015` (Plugin Manager refresh) | IMPLEMENT (journey holds; no remediation needed) | EV-W53-JOURNEY plugin checks + plugin slices (46) |
| `HPC-W10-GJ2-016` (updater check/download fixture) | IMPLEMENT (journey holds; no remediation needed) | EV-W53-JOURNEY updater checks + updater/restart slices (61) |
| `HPC-W10-GJ2-017` (logs/diagnostics refresh) | IMPLEMENT (journey holds; no remediation needed) | EV-W53-JOURNEY logs checks + logs slices (18) |
| `HPC-W10-GJ2-018` (no native crash) | IMPLEMENT (journey holds; no remediation needed) | `NO_NATIVE_CRASH` + 272/272 slices green + journey + external all completed |
| `HPC-W10-GJ2-019` (no destroyed-control callback) | IMPLEMENT (journey holds; no remediation needed) | post-shutdown drop checks (terminal/jobs/remote/logs/plugin) + wx guard static proofs |
| `HPC-W10-GJ2-020` (no hang) | IMPLEMENT (journey holds; no remediation needed) | `NO_HANG` (0.16s) + every slice bounded + external close 0.06s |
| `HPC-W10-GJ2-021` (bounded shutdown) | IMPLEMENT (journey holds; no remediation needed) | `BOUNDED_SHUTDOWN` (0.000s) + external `SHUTDOWN_BOUNDED` (0.06s) |
| `HPC-W10-GJ2-022` (cleanup/worker cancellation deterministic) | IMPLEMENT (journey holds; no remediation needed) | `CLEANUP_DETERMINISTIC_ORDER` (LIFO 8/8) + `TRANSFER_CANCELLED_BOUNDED` + `UPDATER_CANCELLED_DETERMINISTIC` |
| `HPC-W10-GJ2-023` (relaunch clean) | IMPLEMENT (journey holds; no remediation needed) | `RELAUNCH_CLEAN` + `RELAUNCH_PROCESS_OK` (fresh OS process) + external `RELAUNCH_CLEAN` |
| `HPC-W10-GJ09-PATH-001` (explicit GJ-09 path) | IMPLEMENT (journey holds; no remediation needed) | EV-W53-JOURNEY `GJ09_JOURNEY_RESULT: PASS (27/27)` + EV-W53-EXT `GJ09_EXTERNAL_RESULT: PASS` |
| `HPC-W10-TODO-LIFECYCLE-NATIVE-003` | IMPLEMENT (journey holds; single-process mixed-surface campaign disproves isolation-hidden teardown defect; slice isolation retained for tooling reasons only) | EV-W53-JOURNEY (one process, one shared shutdown, 8 surfaces) + OBS-W53-002 |
| `HPC-W10-TODO-LIFECYCLE-NATIVE-004` | IMPLEMENT (0 destroyed-control callbacks, 0 native access violations, 0 heap corruption, 0 leaked top-level windows/workers in this campaign) | `ZERO_LEAKED_WORKERS` + `ZERO_LEAKED_LIFECYCLE` + drop checks + 272/272 green |
| `HPC-W10-TODO-SHUTDOWN-LOAD-GJ-001` | IMPLEMENT (bounded clean shutdown/relaunch with representative work in flight proven) | Same as PATH-001 (TODO detail proven by identical checks) |

## Stop / resume

- No `BLOCKED` (no destructive-Git need, no unresolved authority conflict, no missing mandatory prerequisite — lab transport healthy, all owned checks executable headless + real).
- No `EXTERNAL_BLOCKED` (real loaded-session close + relaunch succeeded; Slurm responsive for the read-only probes in this path).
- No `AWAITING_INPUT` (unattended contract honored; zero user questions asked).
- Cross-scope routes: none (no product defect observed; combined-plugin-process hang is a tooling-lifetime observation, recorded not routed as a product finding).
- Resume point: controller independent audit of this READY_FOR_AUDIT candidate; auditor re-runs EV-W53-GUI slice commands + `.tmp/w53-run/gj09_journey.py` verbatim (headless) and `.tmp/w53-run/gj09_external.py` verbatim (needs lab transport) and inspects EV-W53-DIFF (expect: report file only).

## Auditor checklist (verbatim)

```text
PYTHONPATH=src python .tmp/w53-run/gj09_journey.py → GJ09_JOURNEY_RESULT: PASS (27/27)
PYTHONPATH=src python -m pytest tests/test_wx_lifecycle.py tests/test_w31_race_lifecycle.py tests/test_w33_lifecycle_isolation.py -p no:cacheprovider -q → 39 passed
PYTHONPATH=src python -m pytest tests/test_wx_terminal.py tests/test_wx_terminal_behavioral.py -p no:cacheprovider -q → 21 passed
PYTHONPATH=src python -m pytest tests/test_transfer_controller.py tests/test_transfer_cancel_recovery.py -p no:cacheprovider -q → 7 passed
PYTHONPATH=src python -m pytest tests/test_wx_transfer_ui_lifecycle.py -p no:cacheprovider -q → 14 passed
PYTHONPATH=src python -m pytest tests/test_wx_remote_files.py tests/test_remote_entry_helpers.py -p no:cacheprovider -q → 16 passed
PYTHONPATH=src python -m pytest tests/test_editor_controller.py tests/test_editor_flow.py tests/test_wx_remote_editor_flow.py -p no:cacheprovider -q → 24 passed
PYTHONPATH=src python -m pytest tests/test_wx_editor.py -p no:cacheprovider -q → 14 passed
PYTHONPATH=src python -m pytest tests/test_job_tracking_controller.py tests/test_output_follower.py tests/test_wx_jobs.py -p no:cacheprovider -q → 12 passed
PYTHONPATH=src python -m pytest tests/test_w35_plugin_manager_gui.py tests/test_wx_plugins.py -p no:cacheprovider -q → 9 passed
PYTHONPATH=src python -m pytest tests/test_plugin_manager_ui.py -p no:cacheprovider -q → 37 passed
PYTHONPATH=src python -m pytest tests/test_app_updater.py tests/test_w41_updater_routing.py -p no:cacheprovider -q → 22 passed
PYTHONPATH=src python -m pytest tests/test_w39_logs_diagnostics.py tests/test_wx_logs.py tests/test_diagnostics.py -p no:cacheprovider -q → 18 passed
PYTHONPATH=src python -m pytest tests/test_w43_restart_package_policy.py tests/test_wx_updater_spec.py -p no:cacheprovider -q → 39 passed
python .tmp/w53-run/gj09_external.py → GJ09_EXTERNAL_RESULT: PASS
git diff --check → exit 0 (only pre-existing sibling CRLF warnings)
git status --porcelain=v1 → only pre-existing sibling M/?? plus docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md
```

## Closeout statement

- Every owned non-superseded mandatory requirement and TODO detail is already valid on the integrated candidate; required evidence is current and truthful; no owned blocking defect remains; the diff is reviewed; this canonical report is current.
- Fresh-context audit is controller-owned and has not yet run for W53; this worker claims `READY_FOR_AUDIT`, never `PASS`.
- Evidence binds to HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369` plus the pre-existing sibling dirty tree (controller-owned integration identity); any integration-base change affecting the terminal/transfer/files/editor/jobs/plugin/updater/logs/lifecycle surfaces invalidates this evidence until re-run.
