# W52 Wave Report — GJ-08 Profile A → Profile B isolation

```text
Wave: W52
Canonical report path: docs/wave-reports/v2/opencode/W52_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (sibling-wave working-tree changes uncommitted; controller owns commit/integration; W52 made zero product/test edits)
Content identity (controller handoff): bc8e0c25be61b35f5adab6343064706bcf1bd8e2c0cbe19e9183af9a0bc4bcb5
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W52 run phase)
Last updated: 2026-09-25
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W52.md` (wave_id W52, execution kind, canonical_source W52, 5 source rows + 1 TODO row, start gate NONE, cohort P10-golden-journeys, required evidence `GUI,PACKAGE,EXTERNAL`, integration refs W44 non-blocking, unattended/non-interactive contract, Golden-Journey candidate rule: W44 candidate is behaviorally read-only).
2. `opencode/REQUIREMENT_REGISTRY.md` lines 1034–1037: `HPC-W10-GJ2-006` (terminal output/session) / `007` (remote directory/file location) / `008` (remote editor tab) / `009` (jobs refresh/details/output); line 1299: `HPC-W10-GJ08-PATH-001` (explicit GJ-08 end-to-end path: A state active, switch/connect to B, prove no A callback/result/action applied to B); line 1533: `HPC-W10-TODO-PROFILE-ISOLATION-GJ-001` (`PROFILE-ISOLATION-GJ-001` — GJ-08 proves Profile A state/callbacks cannot leak into Profile B).
3. `opencode/TODO_OWNERSHIP_MAP.md` line 201: `HPC-W10-TODO-PROFILE-ISOLATION-GJ-001` owned by W52, ACTIVE.
4. `opencode/sources/WAVE_V2_FINAL_10.md` → GJ-08 section (lines 141–149): with A active create representative A state (terminal, remote directory/file location, remote editor tab, jobs refresh/details/output); switch/connect to B and prove no A callback/result/action applied to B; ambiguous ownership is release-blocking.
5. `opencode/sources/V2_TODOS.md` line 380: `PROFILE-ISOLATION-GJ-001` unchecked TODO detail (first-class owned work for this Wave).
6. `.opencode/protocol/LOCAL_REAL_HPC_LAB.md`: EXTERNAL authority; LOCAL_REAL_HYPERV is default real infra for generic SSH/connection claims; serialize EXTERNAL replay; GUI/PACKAGE claims need their own journey proof, not lab-health inference.
7. Live code before edits (read-only): `src/hpc_gui/services/connection_controller.py` (`ConnectionController.finish` mints `session_generation`; `close_session` best-effort teardown of superseded transports), `src/hpc_gui/wx_terminal.py` (generation-gated `render_output`, `set_ssh` swap mints fresh generation, close mints generation + unsubscribes), `src/hpc_gui/wx_remote_files_view.py` (`view_generation` + `listing_request_id` guards), `src/hpc_gui/services/remote_navigation_store.py` (`navigation_store_for_profile` per-profile stores), `src/hpc_gui/services/editor_controller.py` (`DocumentModel.canonical_key` pins provider/profile/session_key; W26 identity), `src/hpc_gui/services/jobs_refresh_state.py` (monotonic sequence; older responses never overwrite newer), `src/hpc_gui/services/job_tracking_controller.py` (`set_session` reconnects + clears A selection/output), `src/hpc_gui/services/output_follower.py` (`assign` on changed job/path/origin/generation resets text/offset), `src/hpc_gui/wx_jobs.py` (monitor/provider/outputs/selected generations + session-generation owner check). No product edits made by W52 — candidate treated as read-only per wave contract.

## Baseline capture

```text
Evidence ID: EV-W52-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files + untracked sibling artifacts preserved untouched; W52 added zero tracked hunks, zero new source/test files outside .tmp)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
git log -1: c8293d3c (HEAD -> develop) Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
```

Content-identity note: `waves/` is gitignored so the pending spec lives outside Git history by program design. The worker proceeded on current repository truth without editing the spec; identity reconciliation is controller-owned. HEAD `c8293d3` matches the W44 audit candidate SHA and the W45–W51 baselines, and the handoff content identity `bc8e0c25…` matches the W45–W51 handoffs.

Sibling-hunk disclaimer: the working tree contains pre-existing sibling modifications (including `src/hpc_gui/wx_jobs.py`, `src/hpc_gui/wx_remote_files_view.py`, `src/hpc_gui/wx_editor_view.py`, `src/hpc_gui/services/output_follower.py`, `src/hpc_gui/ui/models/remote_entry_helpers.py`, `src/hpc_gui/ui/dialogs/plugin_manager_dialog.py` and related settings/plugins/logs/i18n/docs). These hunks pre-date the W52 run phase and were not authored, reviewed, or claimed by W52. After controller integration or conflict resolution affecting the terminal/files/editor/jobs/profile surfaces, the affected W52 slices and both journey harnesses must be re-run before audit acceptance.

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
OBS-W52-001 | N/A | GJ-08 path fully executable on current candidate | EV-W52-GUI (166 passed, 0 failed) + EV-W52-JOURNEY (21/21 product-path checks PASS) + EV-W52-EXT (real LOCAL_REAL dual-session PASS) | n/a — journey holds, no product defect | none | none needed (read-only candidate rule) | NO (journey replay, not a remediation) | VERIFIED
OBS-W52-002 | N/A | file-manager profile slice has 2 CWD-environmental failures | tests/test_file_manager_profile.py FtpWidgetLocalStartTests x2: 'C:\\Users\\mskomek' != 'D:\\Projeler\\hpc-client-gui' (asserts os.getcwd() == home) | test assumes checkout CWD equals user home; this checkout lives on D: | none on GJ-08 path (profile file-manager defaults still covered by the 8 passing tests in the same file + connection-profile/profile-identity slices) | none by W52 (not a W52-owned defect; zero W52 edits) | NO | RECORDED (excluded from green claim)
```

Golden-Journey candidate rule applied: no product behavior was patched inside W52. No defect was found on the GJ-08 path, so nothing was routed to another owner. Second-defect sweep dimensions (terminal stale-output gating + post-close gating, remote listing generation/request gating + per-profile navigation stores + provider filters, editor canonical-key tab isolation + save pinning, jobs refresh sequence gating + failure-stale handling + tracking reconnect reset + output-follower generation reset, connection generation monotonicity) are all covered by the green slices below; no sweep dimension surfaced a W52-owned defect.

## Implementation

No product-code, test, or config changes. W52 is a journey-replay wave on a read-only candidate; the only new artifacts are this report and the `.tmp/w52-run/` harnesses (temp, never committed as evidence).

## Tests and evidence

### EV-W52-GUI — journey GUI/runtime slices (all green, exact reruns at HEAD `c8293d3`, `PYTHONPATH=src`, `-p no:cacheprovider`, process-isolated per wx-lifetime note)

```text
Evidence ID: EV-W52-GUI
tests/test_editor_controller.py + tests/test_editor_flow.py + tests/test_output_follower.py → 22 passed
  (document identity/open/update/save, editor flow, output follower poll/assign/close)
tests/test_w19_connection_lifecycle.py → 20 passed
  (connection lifecycle incl. test_profile_switch_invalidates_navigation_and_filters + test_reconnect_rebinds_all_domains_through_canonical_session)
tests/test_connection_profile_service.py → 12 passed
  (profile persistence/secure-secret lifecycle)
tests/test_profile_identity.py → 3 passed
  (profile identity)
tests/test_wx_remote_files.py → 4 passed
  (wx remote files view behavior)
tests/test_wx_editor.py → 14 passed
  (wx editor view behavior incl. tabs/cross-view actions)
tests/test_wx_jobs.py → 5 passed
  (wx jobs model behavior)
tests/test_job_tracking_controller.py → 2 passed
  (tracking reconnect/selection/output reset + poll gating)
tests/test_wx_terminal.py → 2 passed
  (wx terminal model behavior)
tests/test_wx_terminal_behavioral.py → 19 passed
  (terminal behavioral incl. lifecycle/render/resize guards)
tests/test_remote_entry_helpers.py → 12 passed
  (remote entry presentation helpers)
tests/test_w31_race_lifecycle.py → 14 passed
  (race/lifecycle guards)
tests/test_w33_lifecycle_isolation.py → 22 passed
  (lifecycle isolation incl. duplicate/conflict handling)
tests/test_wx_remote_editor_flow.py → 7 passed
  (remote editor open/save flow)
tests/test_local_edit_flow.py → 8 passed
  (local edit flow)
GUI verdict: 166 passed, 0 failed
  (22 + 20 + 12 + 3 + 4 + 14 + 5 + 2 + 2 + 19 + 12 + 14 + 22 + 7 + 8 = 166 passed)
```

Isolation note: each slice command above runs in its own process. A single combined process of wx-bearing suites can end in a native access violation while each file is green alone (W50/W51 recorded the same; W52 reproduced it when combining `test_w19_connection_lifecycle` with the editor/output suites); W52 therefore claims only the process-isolated slice results above. No suite file was edited, skipped, or weakened to obtain green. The 2 `test_file_manager_profile` CWD failures are environmental (see OBS-W52-002) and are excluded from the green claim — no file-manager green is claimed beyond the 8 passing tests in that file, and GJ-08 file-location isolation is proven by the wx-remote/navigation slices + journey + external replay instead.

GJ-08 step → evidence mapping:

| GJ-08 step | Evidence |
|---|---|
| terminal output/session | `TERMINAL_STALE_A_DROPPED`/`TERMINAL_B_LIVE_RENDERED`/`TERMINAL_POST_CLOSE_DROPPED`/`TERMINAL_WX_GUARD_PRESENT` harness checks via product `TerminalModel` + `wx_terminal` generation guard + terminal slices (21 passed) |
| remote directory/file location | `NAV_STORE_DISTINCT`/`REMOTE_STALE_A_LISTING_DROPPED`/`REMOTE_B_LISTING_APPLIED`/`REMOTE_WX_GUARD_PRESENT` harness checks via product `navigation_store_for_profile` + `wx_remote_files_view` generation/request guard + remote/entry/profile slices (31 passed) |
| remote editor tab | `EDITOR_KEYS_DISTINCT`/`EDITOR_TABS_ISOLATED`/`EDITOR_B_TAB_PINNED`/`EDITOR_A_TAB_UNTOUCHED` harness checks via product `DocumentModel.canonical_key` + `EditorController` + editor slices (51 passed) |
| jobs refresh/details/output | `JOBS_STALE_A_REFRESH_DROPPED`/`JOBS_B_REFRESH_APPLIED`/`JOBS_STALE_A_FAILURE_DROPPED`/`JOBS_TRACKING_BOUND_TO_B`/`JOBS_OUTPUT_REASSIGN_RESETS` harness checks via product `JobsRefreshState` + `JobTrackingController` + `OutputFollower` + jobs/output/race/lifecycle slices (63 passed) |
| switch/connect to B, no A applied | `CONN_GEN_MONOTONIC`/`CONN_SESSION_DISTINCT`/`CONN_STALE_A_NOT_CURRENT`/`GJ08_PATH_ISOLATION` + `test_profile_switch_invalidates_navigation_and_filters` + `test_reconnect_rebinds_all_domains_through_canonical_session` + EXTERNAL dual-session replay |

### EV-W52-JOURNEY — disposable end-to-end journey replay on product paths

```text
Evidence ID: EV-W52-JOURNEY
Harness: .tmp/w52-run/gj08_journey.py (disposable; W52-disjoint tmp root w52-gj08-*, no network, no real user config)
Product paths exercised: services.connection_controller ConnectionController (generation monotonicity) + wx_terminal TerminalModel + wx_terminal/wx_remote_files_view source guards + services.remote_navigation_store navigation_store_for_profile + services.editor_controller DocumentModel/EditorController + services.jobs_refresh_state JobsRefreshState + services.job_tracking_controller JobTrackingController + services.output_follower OutputFollower/OutputFollowerState
Observed result:
  CONN_GEN_MONOTONIC: OK (genA=1 genB=2)
  CONN_SESSION_DISTINCT: OK
  CONN_STALE_A_NOT_CURRENT: OK
  TERMINAL_STALE_A_DROPPED: OK
  TERMINAL_B_LIVE_RENDERED: OK
  TERMINAL_POST_CLOSE_DROPPED: OK
  TERMINAL_WX_GUARD_PRESENT: OK
  NAV_STORE_DISTINCT: OK
  REMOTE_STALE_A_LISTING_DROPPED: OK
  REMOTE_B_LISTING_APPLIED: OK
  REMOTE_WX_GUARD_PRESENT: OK
  EDITOR_KEYS_DISTINCT: OK
  EDITOR_TABS_ISOLATED: OK
  EDITOR_B_TAB_PINNED: OK
  EDITOR_A_TAB_UNTOUCHED: OK
  JOBS_STALE_A_REFRESH_DROPPED: OK
  JOBS_B_REFRESH_APPLIED: OK
  JOBS_STALE_A_FAILURE_DROPPED: OK
  JOBS_TRACKING_BOUND_TO_B: OK
  JOBS_OUTPUT_REASSIGN_RESETS: OK
  GJ08_PATH_ISOLATION: OK
  GJ08_JOURNEY_RESULT: PASS (21/21)
Cleanup: all fixture state lives only under the disposable tmp root (config root only); nothing written to the user environment, repo, or shared namespace.
```

### EV-W52-EXT — real EXTERNAL replay against LOCAL_REAL_HYPERV

```text
Evidence ID: EV-W52-EXT
Harness: .tmp/w52-run/gj08_external.py (disposable; secrets never enter report/git)
Target identity: LOCAL_REAL_HYPERV controller 192.168.250.11:22, user hpctest, provider local-real, key auth (emitted lab profile), isolated known_hosts_w52, accept-new
Lab health at replay: Slurm responsive (squeue --me exit 0, empty queue on both sessions); transport healthy on both sessions. No lab reset performed by this worker (shared lab, serialized use).
Observed result:
  CONFIG_ROOT_ISOLATED: <approved-tmp>/w52-gj08-*/fresh-root (home untouched)
  PROFILE_A_CONNECTED: transport_active=True
  PROFILE_A_TERMINAL: OK token readback (echo W52-GJ08-A-* + hostname)
  PROFILE_A_FILES: OK exit=0 (pwd + ls ~ readback, e.g. /home/hpctest + slurm-*.out)
  PROFILE_A_JOBS: OK (squeue --me header + W52-A-JOBS-EXIT:0)
  PROFILE_B_CONNECTED: transport_active=True distinct_transport=True
  PROFILE_B_TERMINAL_ISOLATED: OK (B token present, A token absent)
  PROFILE_B_FILES: OK exit=0
  PROFILE_B_JOBS: OK (squeue --me header + W52-B-JOBS-EXIT:0)
  STALE_A_GATED: closed-A exec raised RuntimeError (visible failure, not silent success)
  PROFILE_B_STILL_ALIVE: OK (B unaffected by A close; B token alive, A token absent)
  GJ08_EXTERNAL_RESULT: PASS
Cleanup: both SSH sessions closed; disposable echo tokens only (no writes, no jobs, no shared-namespace mutation); isolated temp dirs left for GC.
```

### EV-W52-PKG — PACKAGE class

```text
Evidence ID: EV-W52-PKG
No packaged artifact was built, published, or claimed by W52 (candidate freeze is owned by W56–W61). Recorded honestly as NO-CANDIDATE.
No product/package-content modification was made by W52, so no freeze invalidation arises from this Wave.
Profile-isolation behavior on the journey path is pinned by the GUI slices above; no artifact SHA-256 is claimed because no candidate artifact exists at this Wave.
```

Evidence classes: `GUI` (required) → EV-W52-GUI (166 passed, real wx event proof in the w19/wx-terminal/wx-remote/wx-editor/wx-jobs/w31/w33 slices) + EV-W52-JOURNEY (21/21 product-path checks PASS). `PACKAGE` (required) → EV-W52-PKG (NO-CANDIDATE, honestly recorded; freeze owned downstream). `EXTERNAL` (required) → EV-W52-EXT (real LOCAL_REAL dual-session A→B isolation readback, PASS). No mocks substituted for any owned claim (harnesses use real connection/terminal/navigation/editor/jobs/output paths under disposable roots + real lab transports; isolated SFTP/exec only, no shared mutation).

## Diff review

```text
Evidence ID: EV-W52-DIFF
Tracked hunks added by W52: none (zero src/test/config edits; read-only candidate rule honored)
New files: docs/wave-reports/v2/opencode/W52_WAVE_REPORT.md (this report; allowed closeout-only path)
Temp only: .tmp/w52-run/gj08_journey.py + .tmp/w52-run/gj08_external.py (never committed)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
Scope check: no sibling M file touched; no test weakened (zero skip/xfail/assertion edits); no secrets in report or harnesses (disposable W52-GJ08-* tokens only, key path referenced never printed); no generated/binary noise.
```

## Requirement disposition

| Requirement | Disposition | Evidence |
|---|---|---|
| `HPC-W10-GJ2-006` (terminal output/session) | IMPLEMENT (journey holds; no remediation needed) | EV-W52-JOURNEY terminal checks + terminal slices (21) + EV-W52-EXT A/B terminal isolation |
| `HPC-W10-GJ2-007` (remote directory/file location) | IMPLEMENT (journey holds; no remediation needed) | EV-W52-JOURNEY remote checks + remote/entry/profile slices + EV-W52-EXT A/B files readback |
| `HPC-W10-GJ2-008` (remote editor tab) | IMPLEMENT (journey holds; no remediation needed) | EV-W52-JOURNEY editor checks + editor slices (51) + EV-W52-EXT path separation |
| `HPC-W10-GJ2-009` (jobs refresh/details/output) | IMPLEMENT (journey holds; no remediation needed) | EV-W52-JOURNEY jobs checks + jobs/output/race/lifecycle slices (63) + EV-W52-EXT A/B squeue |
| `HPC-W10-GJ08-PATH-001` (explicit GJ-08 path) | IMPLEMENT (journey holds; no remediation needed) | EV-W52-JOURNEY `GJ08_PATH_ISOLATION` 21/21 + EV-W52-EXT `GJ08_EXTERNAL_RESULT: PASS` |
| `HPC-W10-TODO-PROFILE-ISOLATION-GJ-001` | IMPLEMENT (journey holds; no remediation needed) | Same as PATH-001 (TODO detail proven by identical checks) |

## Stop / resume

- No `BLOCKED` (no destructive-Git need, no unresolved authority conflict, no missing mandatory prerequisite — lab transport healthy, all owned checks executable headless + real).
- No `EXTERNAL_BLOCKED` (real dual-session connect/exec/list/squeue succeeded; Slurm responsive for the read-only probes in this path).
- No `AWAITING_INPUT` (unattended contract honored; zero user questions asked).
- Cross-scope routes: none (no product defect observed; file-manager CWD failures are environmental test assumptions, recorded not routed as a product finding).
- Resume point: controller independent audit of this READY_FOR_AUDIT candidate; auditor re-runs EV-W52-GUI slice commands + `.tmp/w52-run/gj08_journey.py` verbatim (headless) and `.tmp/w52-run/gj08_external.py` verbatim (needs lab transport) and inspects EV-W52-DIFF (expect: report file only).

## Auditor checklist (verbatim)

```text
PYTHONPATH=src python .tmp/w52-run/gj08_journey.py → GJ08_JOURNEY_RESULT: PASS (21/21)
PYTHONPATH=src python -m pytest tests/test_editor_controller.py tests/test_editor_flow.py tests/test_output_follower.py -p no:cacheprovider -q → 22 passed
PYTHONPATH=src python -m pytest tests/test_w19_connection_lifecycle.py -p no:cacheprovider -q → 20 passed
PYTHONPATH=src python -m pytest tests/test_connection_profile_service.py -p no:cacheprovider -q → 12 passed
PYTHONPATH=src python -m pytest tests/test_profile_identity.py -p no:cacheprovider -q → 3 passed
PYTHONPATH=src python -m pytest tests/test_wx_remote_files.py -p no:cacheprovider -q → 4 passed
PYTHONPATH=src python -m pytest tests/test_wx_editor.py -p no:cacheprovider -q → 14 passed
PYTHONPATH=src python -m pytest tests/test_wx_jobs.py -p no:cacheprovider -q → 5 passed
PYTHONPATH=src python -m pytest tests/test_job_tracking_controller.py -p no:cacheprovider -q → 2 passed
PYTHONPATH=src python -m pytest tests/test_wx_terminal.py -p no:cacheprovider -q → 2 passed
PYTHONPATH=src python -m pytest tests/test_wx_terminal_behavioral.py -p no:cacheprovider -q → 19 passed
PYTHONPATH=src python -m pytest tests/test_remote_entry_helpers.py -p no:cacheprovider -q → 12 passed
PYTHONPATH=src python -m pytest tests/test_w31_race_lifecycle.py -p no:cacheprovider -q → 14 passed
PYTHONPATH=src python -m pytest tests/test_w33_lifecycle_isolation.py -p no:cacheprovider -q → 22 passed
PYTHONPATH=src python -m pytest tests/test_wx_remote_editor_flow.py -p no:cacheprovider -q → 7 passed
PYTHONPATH=src python -m pytest tests/test_local_edit_flow.py -p no:cacheprovider -q → 8 passed
python .tmp/w52-run/gj08_external.py → GJ08_EXTERNAL_RESULT: PASS
git diff --check → exit 0 (only pre-existing sibling CRLF warnings)
git status --porcelain=v1 → only pre-existing sibling M/?? plus docs/wave-reports/v2/opencode/W52_WAVE_REPORT.md
```

## Closeout statement

- Every owned non-superseded mandatory requirement and TODO detail is already valid on the integrated candidate; required evidence is current and truthful; no owned blocking defect remains; the diff is reviewed; this canonical report is current.
- Fresh-context audit is controller-owned and has not yet run for W52; this worker claims `READY_FOR_AUDIT`, never `PASS`.
- Evidence binds to HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369` plus the pre-existing sibling dirty tree (controller-owned integration identity); any integration-base change affecting the terminal/files/editor/jobs/profile surfaces invalidates this evidence until re-run.
