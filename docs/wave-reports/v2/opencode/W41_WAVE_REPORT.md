# W41 Wave Report — Updater state machine, routing and download UX

```text
Wave: W41
Canonical report path: docs/wave-reports/v2/opencode/W41_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (working-tree changes uncommitted; controller owns commit/integration)
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W41 run phase)
Last updated: 2026-09-24
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W41.md` (wave_id W41, execution kind, canonical_source W41, 24 source rows + 2 TODO rows, start gate NONE, cohort P6-settings-split, required evidence `GUI,PACKAGE`).
2. `opencode/REQUIREMENT_REGISTRY.md` rows owning Wave W41: `HPC-W09-UPD-001`, `002`, `005`, `016`..`028`, `049`, `050`, `062`..`065`, `075`, `076`.
3. `opencode/TODO_OWNERSHIP_MAP.md` rows owning Wave W41: `HPC-W09-TODO-UPDATER-ROUTE-001`, `HPC-W09-TODO-UPDATER-ROUTE-002`.
4. `opencode/sources/WAVE_V2_FINAL_09.md` → Entry criteria (lines 43-48), Scope (52-66), Workstream F — Updater state machine (state list), Workstream G — Update download UX (total/downloaded/percent/unknown-total/cancel/resume), Targeted tasks TASK-W09-006/007, Test matrix rows 282-285, Acceptance gates 298-299.
5. Live code before edits: `src/hpc_gui/wx_shell.py` (`_on_update` closure ~1191, `_dispatch` `APP-UPDATE-CHECK` ~3783), `src/hpc_gui/wx_updater_view.py` (`WxUpdateDialog` state machine), `src/hpc_gui/services/app_updater.py` (`get_latest_release`, `_download`, `download_and_verify_release`, `launch_update_installer`).
6. Live tests before edits: `tests/test_app_updater.py`, `tests/test_update_verification.py`, `tests/test_updater_helper.py`, `tests/test_wx_updater_spec.py`, `tests/test_wx_dispatch_error_gov.py`, `tests/test_w04_support_freeze.py`.

## Baseline capture

```text
Evidence ID: EV-W41-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files preserved untouched; W41 adds 1 focused routing fix + 1 new test file, see diff review)
```

Content-identity note: the controller handoff cites `content_identity=d1e8be9a...`. The working-tree `waves/pending/W41.md` SHA-256 (BOM-stripped, LF-normalized) computes to `6a873fe508433fe59f48ee74b5d8521dd3e5cfb6fdac7da0946ee3cec8f6261f`, and `/waves/` is gitignored (`.gitignore:104`), so the pending spec lives outside Git history by program design. The worker proceeded on current repository truth; identity reconciliation is controller-owned. No spec text was edited by this worker.

Narrow baseline before W41 edits is not separable from the shared dirty tree (parallel cohort shares one working tree on `develop`). The W41 worker therefore baselined by focused suite: updater clusters below were green before edits (`test_app_updater` 31 passed with verification/helper, `test_wx_updater_spec` 23 passed) and re-run after edits as regression. No sibling file was reverted or merged by this worker.

Pre-existing dirty files NOT owned by W41 (preserved untouched): all `M` entries from sibling waves (settings/i18n/plugins/jobs/editor/logs/services — see `git status`; W26 editor identity in progress per program log). W41 touched only the hunks in EV-W41-DIFF.

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
DEF-W41-001 | P1 | visible Check-for-Updates menu opens CHECKING with no worker | _dispatch APP-UPDATE-CHECK branch only constructed WxUpdateDialog + _build_for_state(CHECKING) + Show(); no get_latest_release call, no thread, no transition | dispatch written as dialog-only stub ("just show updater view" comment) | user clicks Check for Updates and waits forever on a spinner; UP_TO_DATE/AVAILABLE/FAILED never reached (ROUTE-001 violated) | route dispatch through authoritative controller that always starts the real worker | YES (FIX-A) | FIXED+VERIFIED
DEF-W41-002 | P1 | duplicate updater routes: dead _on_update worker vs live workerless dispatch | _on_update closure (wx_shell ~1191) held the full correct worker but was never bound to any menu/button (no Bind references it); the bound menu path (_dispatch) had no worker | two routes diverged; correct logic orphaned | startup/manual/menu paths do not share one controller/state machine (ROUTE-002 violated); future fix in one route silently misses the other | extract run_wx_update_check; both paths delegate; delete duplicate worker copy | YES (FIX-A) | FIXED+VERIFIED
OBS-W41-003 | N/A | startup splash update check injects demo fake on timeout/error | wx_shell startup path writes fake UpdateRelease 1.9.0 on timeout or benign error | demo scaffolding in startup flow | startup badge may claim an update that was never verified; manual/menu W41 scope unaffected (startup ownership is splash/W43 packaged acceptance, not ROUTE-001/002 menu paths) | none here | NO | ROUTED (integration hint for splash/packaged owner; not fixed opportunistically)
OBS-W41-004 | N/A | pre-existing editor-owner dispatch test red | test_editor_save__local_and_remote_paths_have_distinct_owners fails identically with W41 hunks stashed (verified) | editor-wave surface | none for W41 | none here | NO | ROUTED (true owner: editor wave)
```

Second-defect search (targeted at W41 surface): negative paths checked (release-check exception → FAILED with message+details, never stuck; parent destroyed mid-check → dialog destroyed, no callback into dead window); stale state checked (release/size/whats-new re-read at transition time; `_total==0` normalized to None so 0-byte size never renders `0 B` as truthful); concurrency checked (worker is daemon thread; cancel flag polled per 1 MiB chunk; `.part` file removed on cancel/failure); boundary values checked (unknown Content-Length → progress `(0,"",n,0)` with no fake percentage; `Calculating...` + Pulse indeterminate in dialog); capability absence checked (unsupported platform raises; unpackaged app refuses installer; unverified artifact refuses install); resume claim checked (`grep resume` across updater view+service → zero hits: no resume is claimed, satisfying "resume only if truly supported" by non-claim); manual-install fallback preserved verbatim (strategy/security gate → MessageBox + browser, dialog destroyed, no silent state). Result: no further W41-owned defects beyond DEF-W41-001/002.

## Implementation

### FIX-A — single authoritative update-check controller (DEF-W41-001/002, ROUTE-001/002, UPD-016/022/049)

- `src/hpc_gui/wx_shell.py::run_wx_update_check(parent)` (new, module-level): opens `WxUpdateDialog(parent, None)` in `CHECKING`, shows it, and **always** starts the real worker thread (`get_latest_release(timeout=10)` → `is_newer_version` → `UP_TO_DATE` | manual-install fallback (MessageBox + browser, dialog destroyed) | `UPDATE_AVAILABLE` with `release`/`_total`/`_whats_new` rebound at transition time | `FAILED` with `_error_message`/`_error_details`). Parent-liveness is probed before every transition (`FindWindowById`); a dead parent destroys the dialog instead of touching dead controls. This is the only `get_latest_release` call site in `wx_shell.py` menu/shell paths.
- `_dispatch("APP-UPDATE-CHECK")` now calls `run_wx_update_check(parent)` (failure → visible coded `UPDATE-XXXXXX` error, unchanged ERROR-GOV contract). The branch keeps an explicit `WxUpdateDialog` canonical-owner reference so the W02 trace contract still resolves statically.
- `_on_update` closure now delegates to `run_wx_update_check(f)` (duplicate ~70-line worker copy deleted). Dead-code eliminated: exactly one worker implementation remains (ROUTE-002).
- Preserved verbatim from the orphaned correct worker: timeout (10 s), macOS signed-bundle gate, `AUTOMATIC_INSTALL_STRATEGIES` membership test, security-message keys, webbrowser fallback, whats-new re-parse. No behavior change except the menu path now actually runs.

### No-code-change classifications (requirement → live owner → evidence)

- UPD-001: entry prerequisite — `W08_AUDIT_REPORT.md`/`W08_WAVE_REPORT.md` exist and plugin/provider ownership is W08-frozen; referenced, not re-proven here.
- UPD-002: entry prerequisite — W04 packaged harness reports exist (`W04_*_REPORT.md`); referenced.
- UPD-005: safe test channel — every updater test uses synthetic fixtures (`https://example.invalid`, fake `UpdateRelease`, tmp-dir archives, stubbed `_request`); production verification path (`download_and_verify_release` → `verify_artifact` against `signed_artifact`) is exercised without network or real-update risk.
- UPD-017/023/024/025 (progress bytes/total/percent): `app_updater._download` reports `progress_cb(value, status, downloaded, total)` from real counters (`downloaded/total` fraction; `test_download_percentage_is_actual_package_percentage` pins `(50,"",1,2)→(100,"",2,2)`); dialog renders `"{bytes} / {bytes}"` + determinate gauge + `"{pct}%"`.
- UPD-026/064 (unknown total honesty): zero `Content-Length` → `progress (0,"",n,0)`, no fake percentage (pinned); dialog shows `Calculating...` + `Pulse()` indeterminate gauge (pinned by `test_update_unknown_total_uses_indeterminate_progress`).
- UPD-027/065 (cancel/interrupt): Cancel button → `_cancel_download` → `cancelled()` polled per chunk → `RuntimeError("Update download cancelled.")` → `DOWNLOAD_CANCELLED`; `.part` file always removed (pinned); close-in-flight and late-callback-after-close are safe (pinned).
- UPD-028 (resume): no resume offered or claimed anywhere in view/service (grep-verified zero hits) — correct by non-claim.
- UPD-018/075 (verification boundary + truthful states): `VERIFYING` state is indeterminate-pulse with integrity text; `_start_install` refuses without `_zip_path + _artifact_verified` (`install_without_verified_artifact_stays_failed`); verified archives are reused, corrupt ones deleted + re-downloaded. Signature/hash install-blocking gates themselves are W42-owned (UPD-029..033); W41 asserts the handoff, not the crypto.
- UPD-019/020/021 (install/restart/failure/packaged boundaries): `READY_TO_INSTALL` requires explicit Install confirmation (`ready_requires_install_confirmation`); install opens the 620×360 splash then `launch_update_installer`, which refuses unpackaged apps, unknown strategies, and unverified artifacts (all pinned); restart semantics + packaged resource acceptance are W43-owned (UPD-039..043/054/069). Failure UX: `FAILED` shows message + Show/Hide Details + Retry/Close (pinned).
- UPD-022/075 (states distinguishable): 11 distinct `STATE_*` constants with per-state titles/builders; availability dialog keeps fixed 520×390 with fixed-height changelog (no state conflation by layout growth).
- UPD-049 (TASK-W09-006): this report section is the state-machine audit record (routes inventoried, dead/duplicated paths found, unified, transition matrix re-proven by tests).
- UPD-050 (TASK-W09-007): byte/percentage math verified against real counters (see UPD-017 evidence); `_format_bytes` B/KB/MB/GB pinned by size-display tests.
- UPD-062/063 (unavailable/available matrix): new W41 routing tests pin both transitions through the real dispatch path.
- UPD-076 (known size displays bytes/total/percentage): `test_update_available_shows_versions_and_download_size` (184 MB visible) + `test_update_download_progress_shows_real_bytes_and_percentage`.

## Tests and evidence

New: `tests/test_w41_updater_routing.py` — **4 passed** (deterministic inline `wx.CallAfter` + inline thread; recording dialog drives the real state constants through the real `_dispatch` → `run_wx_update_check` path; real dialog construction/layout stays covered by `test_wx_updater_spec`).

| Requirement | Test | Evidence |
|---|---|---|
| ROUTE-001/UPD-062 | test_menu_update_check_reaches_up_to_date_via_real_worker | CHECKING → UP_TO_DATE through real dispatch + stubbed service (was stuck forever before FIX-A) |
| ROUTE-001/UPD-063 | test_menu_update_check_newer_release_reaches_available | CHECKING → UPDATE_AVAILABLE, `release` rebound |
| ROUTE-001/UPD-020 | test_menu_update_check_failure_reaches_failed | service raise → FAILED with `network down` message retained |
| ROUTE-002 | test_single_authoritative_controller | dispatch + `_on_update` both delegate; no second `get_latest_release` copy; signature has `parent` |
| UPD-017/025/076 | test_download_reports_transferred_and_total_bytes, test_download_percentage_is_actual_package_percentage (existing) | `(100,"",2,2)`; `(50,"",1,2)→(100,"",2,2)` real-counter math |
| UPD-026/064 | test_unknown_content_length_reports_bytes_without_fake_percentage, test_update_unknown_total_uses_indeterminate_progress (existing) | `(0,"",1,0)→(100,"",2,0)`; indeterminate Pulse |
| UPD-027/065 | test_cancelled_update_download_removes_partial_file, test_update_cancel_reaches_downloader, test_update_cancel_prevents_install, test_update_close_in_flight_safe, test_update_late_callback_after_close_safe (existing) | `.part` removed; cancel reaches downloader; no install after cancel; no dead-control callbacks |
| UPD-023/024/076 GUI | test_update_available_shows_versions_and_download_size, test_update_download_progress_shows_real_bytes_and_percentage (existing, real wx) | `1.9.0` + `184 MB` visible; real bytes/percent readback |
| UPD-018/019 GUI | test_update_verification_state_visible, test_update_ready_requires_install_confirmation, test_install_without_verified_artifact_stays_failed, test_update_install_opens_installation_splash (existing, real wx) | verifying visible; install gated on confirmation + verified artifact |
| UPD-021 | test_unpackaged_app_never_launches_installer, test_unknown_update_platform_is_rejected, test_release_assets_are_platform_specific, test_updater_selects_arch_specific_dmg_per_platform (existing) | packaged-behavior boundary |
| ERROR-GOV (unchanged) | test_update_check_failure__dispatch__visible_error_with_code, test_dispatch__reaches_canonical_owner[APP-UPDATE-CHECK-*] (existing) | coded UPDATE error; canonical trace intact after refactor |

Regression sweep (after edits): `test_w41_updater_routing + test_app_updater + test_update_verification + test_updater_helper + test_wx_updater_spec + test_wx_dispatch_error_gov + test_w04_support_freeze` → **122 passed, 1 failed** where the single failure (`test_editor_save__local_and_remote_paths_have_distinct_owners`) is pre-existing and unrelated — it fails identically with W41 hunks stashed (OBS-W41-004, routed to editor owner). `git diff --check` on W41 files → clean.

Evidence classes: `GUI` (required) → FULL via 23 real-wx `test_wx_updater_spec` runtime tests (real `wx.App`/dialogs/events/gauges/readback) + 4 dispatch-path routing tests through the real controller. `PACKAGE` (required) → N/A with concrete justification: no artifact was built or claimed in W41 scope; updater tests run against synthetic fixtures by UPD-005 design, and packaged updater-resource acceptance is W43-owned (UPD-069). External HPC → N/A (updater surface is connection-independent; no external system touched — real-network interruption is simulated via the `cancelled()` callback boundary, not mocked away).

## Diff review

```text
Evidence ID: EV-W41-DIFF
git diff --check (W41 files): clean
Files changed with W41-owned hunks:
  src/hpc_gui/wx_shell.py               (FIX-A: +run_wx_update_check controller; _dispatch delegates w/ canonical-owner ref; _on_update delegates, duplicate worker deleted)
  tests/test_w41_updater_routing.py     (new, 4 tests)
```

Secrets scan: no credentials, tokens, keys, hosts, or user literals added; fixtures use `example.com`/`example.invalid` + tmp dirs. No binary/generated noise. No weakened tests (all new assertions are positive behavioral checks; `wx.CallAfter`/thread inlining is declared in the file's mock-boundary header; real dialog construction remains under `test_wx_updater_spec`).

`git diff --stat` for the whole tree shows sibling-wave hunks (W19–W26+ surfaces) that are explicitly NOT W41's and were preserved untouched; the W41-owned delta is exactly the two files above (verified via `git diff -- src/hpc_gui/wx_shell.py` hunk inspection: only `run_wx_update_check`, `_on_update`, `APP-UPDATE-CHECK` hunks).

## Cross-scope routing

No cross-scope defects fixed opportunistically (per parallel-execution scope discipline). Two findings routed, not fixed here: OBS-W41-003 (startup-splash demo fake → splash/packaged owner, W43 integration hint) and OBS-W41-004 (editor dispatch-owner test → editor wave owner). The `_dispatch` ERROR-GOV contract and W02 trace contract were preserved, not weakened, for the touched branch.

## Handoff

Worker requests independent audit. Resume point: none — work is complete; candidate is the current working tree on `develop` at base `c8293d3c` plus the W41 files listed above (uncommitted; commit/integration is controller-owned). The fresh-context audit report (`W41_AUDIT_REPORT.md`) is controller/audit-phase owned and is intentionally not written here — a worker self-audit cannot satisfy `audit_policy: fresh-independent`.

```text
Candidate identity: working tree on develop @ c8293d3ca309526ed250c794c3b294f7c54ef369 + W41 diff (EV-W41-DIFF)
Focused tests: 4 passed (W41 new) + 118 passed (updater + dispatch + freeze regression clusters)
GUI runtime: wxPython (msw) — 23 real-wx updater-spec tests + 4 dispatch-path routing tests
Manual acceptance remaining (controller-owned, not faked): none for W41 scope (no MFA/hardware/credential/manual gate in owned rows)
```
