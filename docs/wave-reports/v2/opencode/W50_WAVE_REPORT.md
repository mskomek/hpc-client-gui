# W50 Wave Report — GJ-06 Settings/logs/diagnostics/restart

```text
Wave: W50
Canonical report path: docs/wave-reports/v2/opencode/W50_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (sibling-wave working-tree changes uncommitted; controller owns commit/integration; W50 made zero product/test edits)
Content identity (controller handoff): bc8e0c25be61b35f5adab6343064706bcf1bd8e2c0cbe19e9183af9a0bc4bcb5
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W50 run phase)
Last updated: 2026-09-25
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W50.md` (wave_id W50, execution kind, canonical_source W50, 1 owned requirement `HPC-W10-GJ06-PATH-001`, start gate NONE, cohort P10-golden-journeys, required evidence `GUI,PACKAGE`, integration refs W44 non-blocking, unattended/non-interactive contract, Golden-Journey candidate rule: W44 candidate is behaviorally read-only).
2. `opencode/REQUIREMENT_REGISTRY.md` line 1297: `HPC-W10-GJ06-PATH-001` MANDATORY — "Execute GJ-06 as this explicit end-to-end path: change representative settings → verify runtime effect → open logs/diagnostics → close → restart → verify expected persistence."
3. `opencode/TODO_OWNERSHIP_MAP.md`: no rows owned by W50 (verified: Select-String for W50 returns no TODO-detail rows; only the registry row above).
4. `waves/bak/WAVE_V2_FINAL_10.md` → GJ-06 section (lines 120-129): change representative settings → verify runtime effect → open logs/diagnostics → close → restart → verify expected persistence.
5. Live code before edits: `src/hpc_gui/wx_settings.py` (`build_model_from_storage` real-storage reads, `persist_model_snapshot` atomic writes with attributed errors, `load_persisted_snapshot` reopen proof, `SETTINGS_INVENTORY`); `src/hpc_gui/wx_settings_view.py` (callback attach + snapshot persist); `src/hpc_gui/config/storage.py` (atomic save, typed getters/setters); `src/hpc_gui/wx_logs.py` (`WxLogsModel.refresh` bounded redacted tail, `logs_dir()` lazy active-dir, `resolve_active_logs_dir()`); `src/hpc_gui/wx_logs_view.py` (Open Logs Folder + `_alive` lifetime guards); `src/hpc_gui/core/diagnostics.py` (truthful `wxPython (...)` runtime summary, `create_diagnostic_bundle`); `src/hpc_gui/core/paths.py` (`HPC_GUI_CONFIG_ROOT` isolation). No product edits made by W50 — candidate treated as read-only per wave contract.

## Baseline capture

```text
Evidence ID: EV-W50-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files + untracked sibling artifacts preserved untouched; W50 added zero tracked hunks, zero new source/test files outside .tmp)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
git log -1: c8293d3c (HEAD -> develop) Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
```

Content-identity note: `waves/` is gitignored so the pending spec lives outside Git history by program design. The worker proceeded on current repository truth without editing the spec; identity reconciliation is controller-owned. HEAD `c8293d3` matches the W44 audit candidate SHA and the W45–W49 baselines, and the handoff content identity `bc8e0c25…` matches the W45–W49 handoffs.

Sibling-hunk disclaimer: the working tree contains pre-existing sibling modifications including `src/hpc_gui/wx_settings.py`, `src/hpc_gui/wx_settings_view.py`, `src/hpc_gui/wx_logs.py`, `src/hpc_gui/wx_logs_view.py`, `src/hpc_gui/core/diagnostics.py`, `src/hpc_gui/config/storage.py` and `src/hpc_gui/wx_shell.py`. These hunks pre-date the W50 run phase and were not authored, reviewed, or claimed by W50. After controller integration or conflict resolution affecting the settings/logs/diagnostics surfaces, the affected W50 slices and the journey harness must be re-run before audit acceptance.

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
OBS-W50-001 | N/A | GJ-06 path fully executable on current candidate | EV-W50-GUI (132 passed, 0 failed) + EV-W50-JOURNEY (15/15 product-path checks PASS) | n/a — journey holds, no product defect | none | none needed (read-only candidate rule) | NO (journey replay, not a remediation) | VERIFIED
```

Golden-Journey candidate rule applied: no product behavior was patched inside W50. No defect was found on the GJ-06 path, so nothing was routed to another owner. Second-defect sweep dimensions (settings change truthfulness, runtime-effect getters, logs open/readback, active-dir laziness, diagnostics bundle completeness, runtime-summary truthfulness, close lifetime safety, cross-process restart persistence, reopen-from-disk proof, secret redaction in logs/bundle) are all covered by the green slices below; no sweep dimension surfaced a W50-owned defect.

## Implementation

No product-code, test, or config changes. W50 is a journey-replay wave on a read-only candidate; the only new artifacts are this report and the `.tmp/w50-run/` harness (temp, never committed as evidence).

## Tests and evidence

### EV-W50-GUI — journey GUI/runtime slices (all green, exact reruns at HEAD `c8293d3`, `PYTHONPATH=src`, `-p no:cacheprovider`, process-isolated per wx-lifetime note)

```text
Evidence ID: EV-W50-GUI
tests/test_w37_settings_persistence.py → 31 passed
  (settings inventory/schema, corruption matrix, persist/reopen round-trips, profile isolation, live/restart sets, parity, migration, arch boundary, 2 real-wx FULL tests: checkbox event → Apply → config.json → OK-only-on-persisted + write-failure → visible error with zero OK)
tests/test_wx_settings.py + tests/test_config_storage_atomic.py + tests/test_w03_settings_provider_inventory.py → 22 passed
  (dialog model, atomic save/backup/coercion, provider settings truthfulness)
tests/test_w39_logs_diagnostics.py → 14 passed
  (first-run init, real-wx open/readback/refresh, logs-dir resolution + Open-Folder event, no-unconfirmed-clear, truthful runtime summary, copy/export redaction, offline bundle, export-failure visibility, close-during-refresh lifetime, raw-log completeness, migration-secret redaction)
tests/test_wx_logs.py + tests/test_diagnostics.py + tests/test_log_redaction.py + tests/test_wave37_diagnostics.py + tests/test_wave7_editor_terminal_logs.py → 21 passed
  (logs model/view pins, diagnostics bundle, redaction service, output-buffer/diagnostics, editor/terminal logs surface)
tests/test_w43_restart_package_policy.py + tests/test_w40_localization_window_settings.py + tests/test_wx_lifecycle.py → 44 passed
  (restart/package policy, window-setting persistence incl. localization, app lifecycle close/restart behavior)
GUI verdict: 132 passed, 0 failed (31 + 22 + 14 + 21 + 44 = 132)
```

Isolation note: the five slice commands above each run in their own process. Sibling wave W49 recorded that a single combined process of wx-bearing suites can end in a native access violation while each file is green alone; W50 therefore claims only the process-isolated slice results above. No suite file was edited, skipped, or weakened to obtain green.

GJ-06 step → evidence mapping:

| GJ-06 step | Evidence |
|---|---|
| change representative settings | `CHANGE_SETTINGS_PERSISTED` harness check via product `persist_model_snapshot` + `test_w37` PERSIST-002/Apply tests + real-wx Apply-event test |
| verify runtime effect | `RUNTIME_*_EFFECT` harness checks via the same storage getters the runtime consumes + `test_w37` RUNTIME-001 live-toggle test |
| open logs/diagnostics | `LOGS_OPEN_READBACK`/`LOGS_DIR_ACTIVE` harness checks via `WxLogsModel` + `DIAG_*` harness checks via `create_diagnostic_bundle`/`_runtime_summary` + `test_w39` DIAG-001..010 tests (real-wx panel open/readback/refresh) |
| close | `CLOSE_MODEL_DROPPED` harness check + `test_w39` lifecycle test (close → late refresh callback safe) + `test_wx_lifecycle` close behavior |
| restart | `RESTART_PROCESS_OK` — a genuinely fresh OS process re-reads the disposable config root (true relaunch semantics, not in-process re-read) |
| verify expected persistence | `PERSIST_*_AFTER_RESTART` + `REOPEN_SNAPSHOT_MATCHES` harness checks + `test_w37` PERSIST-003 reopen-from-storage test + `test_w40` window-setting persistence + `test_w43` restart policy |

### EV-W50-JOURNEY — disposable end-to-end journey replay on product paths

```text
Evidence ID: EV-W50-JOURNEY
Harness: .tmp/w50-run/gj06_journey.py (disposable; W50-disjoint tmp root w50-gj06-*, no network, no real user config)
Product paths exercised: wx_settings.build_model_from_storage / persist_model_snapshot / load_persisted_snapshot + config.storage getters/setters (change + runtime effect) + WxLogsModel (open/readback/active-dir) + diagnostics._runtime_summary + create_diagnostic_bundle (diagnostics) + fresh-subprocess storage read (restart + persistence proof)
Observed result:
  CHANGE_SETTINGS_PERSISTED: OK
  RUNTIME_CACHE_EFFECT: OK (cache=False), RUNTIME_CHECKSUM_EFFECT: OK, RUNTIME_INTERVAL_EFFECT: OK (interval=42)
  LOGS_OPEN_READBACK: OK, LOGS_DIR_ACTIVE: OK
  DIAG_RUNTIME_TRUTHFUL: OK (ui_framework='wxPython (4.3.1 msw (phoenix) wxWidgets 3.3.3)')
  DIAG_BUNDLE_CREATED: OK, DIAG_BUNDLE_MANIFEST: OK (runtime.json plugins.json manifest.json)
  CLOSE_MODEL_DROPPED: OK
  RESTART_PROCESS_OK: OK (rc=0)
  PERSIST_CACHE_AFTER_RESTART: OK, PERSIST_CHECKSUM_AFTER_RESTART: OK, PERSIST_INTERVAL_AFTER_RESTART: OK
  REOPEN_SNAPSHOT_MATCHES: OK
  GJ06_JOURNEY_RESULT: PASS (15/15)
Cleanup: all fixture state lives only under the disposable tmp root (config root, logs, bundle); nothing written to the user environment, repo, or shared namespace.
```

### EV-W50-PKG — PACKAGE class

```text
Evidence ID: EV-W50-PKG
No packaged artifact was built, published, or claimed by W50 (candidate freeze is owned by W56–W61). Recorded honestly as NO-CANDIDATE.
No product/package-content modification was made by W50, so no freeze invalidation arises from this Wave.
Settings/logs/diagnostics behavior on the journey path is pinned by the GUI slices above; no artifact SHA-256 is claimed because no candidate artifact exists at this Wave.
```

Evidence classes: `GUI` (required) → EV-W50-GUI (132 passed, real wx event proof in the w37/w39 slices) + EV-W50-JOURNEY (15/15 product-path checks PASS incl. cross-process restart). `PACKAGE` (required) → EV-W50-PKG (NO-CANDIDATE, honestly recorded; freeze owned downstream). No mocks substituted for any owned claim (harness uses real storage/model/bundle paths under a disposable root).

## Diff review

```text
Evidence ID: EV-W50-DIFF
Tracked hunks added by W50: none (zero src/test/config edits; read-only candidate rule honored)
New files: docs/wave-reports/v2/opencode/W50_WAVE_REPORT.md (this report; allowed closeout-only path)
Temp only: .tmp/w50-run/gj06_journey.py (never committed)
git diff --check: exit 0 (only pre-existing sibling CRLF warnings)
Scope check: no sibling M file touched; no test weakened (zero skip/xfail/assertion edits); no secrets in report or harness (no tokens, keys, or hosts); no generated/binary noise.
```

## Handoff / DAG unlocks

Historical unlock target W55 is an integration hint only; no downstream Wave was started by this worker. No shared lab, device, or namespace was used (fully local disposable replay); nothing to clean beyond OS temp GC.

## Findings and resume state

- No owned blocking defect remains. GJ-06 executes end-to-end on the integrated candidate: GUI slices 132 passed / 0 failed with real wx event proof + disposable journey replay 15/15 PASS incl. fresh-process restart persistence.
- Cross-scope routes: none (no product defect observed on the GJ-06 path).
- No `AWAITING_INPUT` (no concrete missing artifact/API).
- No `EXTERNAL_BLOCKED` (no external prerequisite; W50 requires GUI+PACKAGE only).
- No `TWO-FIX-EXCEPTION` needed: W50 owns a journey-replay requirement, not a stabilization quota; the candidate rule forbids manufacturing product fixes.
- Resume point: controller fresh independent audit of this READY_FOR_AUDIT candidate; auditor re-runs the five EV-W50-GUI slice commands process-isolated + `PYTHONPATH=src python .tmp/w50-run/gj06_journey.py` verbatim and inspects EV-W50-DIFF (expect: report file only). If integration rebased sibling hunks in `wx_settings*.py`/`wx_logs*.py`/`core/diagnostics.py`/`config/storage.py`, re-run affected slices + harness first.

---

## Contradiction scan

- PACKAGE status is uniformly NO-CANDIDATE — no artifact claim anywhere.
- Full-suite green is never claimed; only the GJ-06 slices are claimed green with exact counts (132 passed / 0 failed).
- Restart persistence is uniformly proven by a fresh OS subprocess reading the disposable config root — no in-process-only re-read claim anywhere.
- Diagnostics truthfulness is uniformly the live `wxPython (...)` runtime string — no Qt-era claim anywhere.
- No test weakened; no product file touched.

## Review passes

- Claim-to-source: the owned ID (`HPC-W10-GJ06-PATH-001`) traces to live owners (`wx_settings.py` model/persist/reopen, `config/storage.py` atomic getters/setters, `wx_logs.py` model, `core/diagnostics.py` bundle/summary, `core/paths.py` isolation) + pinned tests/commands in this report.
- Diff review: zero tracked hunks by W50; sibling hunks explicitly disclaimed with re-run condition.
- Adversarial: runtime-effect checks read through the same getters the runtime consumes (not the dialog model); restart proof crosses a process boundary (not same-memory); reopen proof deletes the in-memory model first; bundle manifest membership is asserted from zip bytes (not the build call's return); redaction paths are pinned by the w39/log_redaction slices rather than re-asserted loosely.

## Resume state

```text
Completed and verified:
- EV-W50-BASELINE (HEAD c8293d3, dirty-tree disclaimed, diff --check clean)
- EV-W50-GUI (31 + 22 + 14 + 21 + 44 = 132 passed, 0 failed; process-isolated slices)
- EV-W50-JOURNEY (15/15 product-path checks PASS, disposable root, fresh-process restart proof)
- EV-W50-PKG (NO-CANDIDATE, honestly recorded)
- EV-W50-DIFF (zero tracked hunks)

In progress: none
Open P0/P1: none
Open P2/P3: none
Pending tests/evidence: controller fresh independent audit
Last exact commands run:
- PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_w37_settings_persistence.py -p no:cacheprovider -q → 31 passed
- PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_wx_settings.py tests/test_config_storage_atomic.py tests/test_w03_settings_provider_inventory.py -p no:cacheprovider -q → 22 passed
- PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_w39_logs_diagnostics.py -p no:cacheprovider -q → 14 passed
- PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_wx_logs.py tests/test_diagnostics.py tests/test_log_redaction.py tests/test_wave37_diagnostics.py tests/test_wave7_editor_terminal_logs.py -p no:cacheprovider -q → 21 passed
- PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_w43_restart_package_policy.py tests/test_w40_localization_window_settings.py tests/test_wx_lifecycle.py -p no:cacheprovider -q → 44 passed
- PYTHONPATH=src .venv/Scripts/python.exe .tmp/w50-run/gj06_journey.py → GJ06_JOURNEY_RESULT: PASS (15/15)
- git diff --check → exit 0 (sibling CRLF warnings only)

Next actions:
1. Controller fresh independent audit of W50 (re-run slices process-isolated + harness, inspect diff).
2. On audit PASS, close W50 independently.

Evidence/artifact identities:
- EV-W50-BASELINE @ c8293d3
- EV-W50-GUI @ c8293d3 (132 passed / 0 failed)
- EV-W50-JOURNEY disposable root w50-gj06-* (15/15, fresh-process restart proof)
- EV-W50-PKG: NO-CANDIDATE
- EV-W50-DIFF: report-file-only
```
