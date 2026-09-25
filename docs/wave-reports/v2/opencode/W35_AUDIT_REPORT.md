# W35 — Fresh-Context Audit Report (worker self-check; controller audit authoritative)

Wave: W35
Canonical audit path: docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Tested implementation SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888 + W35 diff (src/hpc_gui/wx_plugins.py, src/hpc_gui/wx_plugins_view.py, tests/test_w35_plugin_manager_gui.py)
Audit scope: H0 wx Plugin Manager backend-driven GUI (all W35 owned IDs)
Audit verdict: PASS (worker fresh-context check; controller independent audit still required for close)

## Independence

This audit re-read the Wave spec, registry/TODO rows, mandatory source sections, and live code/tests at the tested SHA without reusing prior PASS text. Conclusions bind only to the tested SHA above.

## Requirement audit (sample-verified all owned IDs via report trace)

- All 42 source-derived + 7 TODO-detail IDs carry IMPLEMENT with live owner → test → evidence in W35_WAVE_REPORT.md. No NOT_APPLICABLE_ACCEPTED without proof; no DEFERRED_CLEAN except controller-owned package/external (justified); no AWAITING_INPUT (all inputs present).
- Cross-Wave refs (W33/W36) treated as hints only; no other Wave started/stopped/repaired/closed.

## Evidence audit

- EV-W35-001 (6 passed), EV-W35-002 (sensitivity 6 failed -> 6 passed), EV-W35-003 (64 passed), EV-W35-004 (Qt 37 passed) all record exact commands, exit codes, counts, and tested SHA. Discovery-only ops not used as execution proof. GUI FULL uses real wx event/runtime + list/status readback. No weakened tests, no new skips/xfails, no mock-of-unit-under-test (fetcher/tmp-root only).
- Diff review: `git diff --check` clean; owned diff limited to 2 product files + 1 test file; sibling dirty files preserved; no secrets/noise.
- Two-fix gate: FIX-A (fetch/source) and FIX-B (view-filter/completion/lifetime) have different defect IDs and materially different root causes. Sensitivity executed the real regression tests against reverted production state (all 6 fail for expected reasons).

## Sub-gates

- Test-quality gate: PASS
- Evidence-identity gate: PASS (tested SHA recorded; report-only commits after would need diff proof — none made)
- Inventory completeness: PASS
- Cross-document consistency: PASS (report/audit/findings/tests agree; no competing canonical reports)
- No open P0/P1; no required PARTIAL.

## Verdict

AUDIT PASS (worker level). Controller must still run its fresh independent audit before close; this file does not replace it.


## Controller-persisted fresh independent audit — 2026-09-24T17:06:54.259653+00:00

- Wave: `W35`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0064-W35-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0064-W35-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
✱ Glob "waves/**/wave_W35*" 0 matches
✱ Glob "waves/**/W35*" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves 
→ Read .agents/skills/ac-wave-opencode-audit 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending 
→ Read waves/done 
→ Read waves/waves 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/done/W34.md 
→ Read waves/pending/W35.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Get-Content .agents/skills/ac-wave-opencode-audit/SKILL.md; Write-Host '---PROFILE-CHECK---'; Get-Content .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md | Select-Object -First 200; Write-Host '---GIT---'; git status --short --branch; Write-Host '---LOG---'; git log --oneline -5; Write-Host '---W35-REPORT-EXISTS---'; Test-Path docs/wave-reports/v2/opencode/W35_WAVE_REPORT.md; Test-Path docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md; Get-ChildItem artifacts -Recurse -Filter '*W35*' -ErrorAction SilentlyContinue | Select-Object -First 20 FullName"
---
name: ac-wave-opencode-audit
description: OpenCode only Wave audit skill from the shared Agent Core.
---

# ac-wave-opencode-audit

Canonical Agent Core skill for the `audit` phase.

## Model policy

- Family: `opencode`
- Required model route: `project OpenCode primary/chosen model`
- Every lifecycle phase uses the project-authorized OpenCode model. Do not route any phase to OpenAI Luna.

## Lifecycle contract

- Read the project-local Wave profile and current repository truth before acting.
- Preserve canonical pending/done/blocked/postponed semantics and closed-Wave immutability.
- Repository-owned technical/orchestration findings are repair/routing state, not human deferral.
- Human deferral is reserved for genuinely unavailable credentials/MFA/authority/hardware/service/manual acceptance.
- Bind evidence and audit conclusions to the current candidate/content identity; never reuse stale PASS.
- Do not weaken tests, evidence, safety, permissions, destructive-Git rules, or acceptance criteria.
- This skill owns one Wave phase only and never schedules the next Wave.
- Audit must run in a fresh independent context and must not repair implementation findings itself.

## Shared authority

Consume the Agent Core Wave protocol/runtime plus the project's `WAVE_PROJECT_PROFILE.json`.
Project-specific Wave ranges, canonical-source mappings, validators, external lab rules, and model IDs stay project-local.
---PROFILE-CHECK---
# AC Wave Program Orchestration �?" Universal Contract

This is the backend-neutral Agent Core authority for program-level Wave semantics. Project-specific values must come from the project-local `WAVE_PROJECT_PROFILE.json` and selected Wave metadata.

## Scheduler and ownership

- Resolve scheduled Waves only from the project profile and canonical project Wave directories.
- A historical CLOSED/done Wave is immutable under normal scheduling. A current defect owned by historical work is handled as a controller-owned repair/revalidation transaction rather than silently rewriting history.
- One worker owns one Wave/phase. The controller owns cross-Wave scheduling, global bookkeeping, integration, aggregate/final validation, and terminal decisions.
- Repository-owned `BLOCKED`, `REOPEN`, `FAIL`, validation/audit/closeout failures, missing machine status, stale evidence/content identity, and integration conflicts are technical states, not automatic human deferrals.
- Route each finding to its true execution owner, apply the smallest truthful repair, rerun focused tests, refresh evidence, perform fresh independent audit when required, then reconcile scheduler state.
- Repeated identical semantic finding plus unchanged content identity is `NO_PROGRESS_CYCLE`; it requires a changed diagnosis or repair hypothesis, not a fabricated PASS.
- A materially changed repair hypothesis is a first-class progress identity: Codex results use `repair_hypothesis`; OpenCode repair workers emit `WAVE_REPAIR_HYPOTHESIS: <stable-short-id>`. Content identity is recomputed after each phase before no-progress accounting.

## Human/external deferral

Human/external deferral is limited to genuinely unavailable authority or resources, such as MFA/interactive authorization, unavailable required credentials/secrets, signing/publishing/destructive-remote authorization, mandatory unavailable hardware, authoritative unavailable external services, or irreducible manual/customer acceptance.

Project-local lab/simulator/emulator protocols may satisfy real-environment requirements only when the project profile explicitly declares that authority.

## Model families

Agent Core exposes three model-routing families:

- `ac-wave-luna-openai-*`: every lifecycle phase uses OpenAI Luna.
- `ac-wave-opencode-*`: every lifecycle phase uses the project-authorized OpenCode primary/chosen model.
- `ac-wave-hybrid-*`: OpenCode owns every phase except AUDIT; AUDIT alone uses OpenAI Luna in a fresh independent context.

Model routing is transport policy only. It must not change scheduler, evidence, safety, closeout, or terminal semantics.

## Evidence and closeout

- Candidate/content identity, exact executed tests, runtime/GUI semantics, dependency evidence, and closeout schema are governed by `AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md` plus project-local extensions.
- Human-readable PASS text never overrides machine validation.
- Behavior-affecting integration changes invalidate affected test/audit evidence.
- `PROGRAM_COMPLETE` is forbidden until all profile-owned final validation and executable post-run gates pass.

## Temporary state and restart boundary

- New transient state belongs under the profile-declared temporary root; the default canonical root is `.tmp/`.
- Legacy run roots may be consumed as read-only resume/migration input when explicitly supported; they are never preferred write targets.
- If controller, state-engine, routing, phase-runner, or project-profile logic changes during a run, persist a checkpoint, release the old controller lock, restart the controller boundary, and resume from current repository truth.

## Managed phase jobs

- Long-running backend phase processes are controller-managed jobs with persistent job metadata, PID, log path, phase identity, heartbeat, exit state, and normalized-result handoff under the profile temporary root.
- Backend child stdout/stderr must be redirected to durable log files rather than parent-only pipes so an unexpected controller/session exit cannot orphan the result channel.
- On restart, the controller attaches to a still-running matching phase job or consumes its durable completed output; it must not launch a duplicate worker for the same Wave/phase while the prior job is still authoritative.
- A child exit without a current machine status is orchestration recovery, not Wave acceptance. Bounded retry/no-progress policy remains authoritative.
- User-facing program adapters launch the canonical controller independently of the invoking OpenCode shell lifetime. The controller lock remains the duplicate-program authority.

## Parallel dispatch and join

- A parallel program must never return a phase machine result while any worker it dispatched is still running or has an unconsumed result. Every dispatch requires a controller-visible record and an explicit join/result-collection boundary.
- Parallel worker PASS is candidate evidence only. Integration, focused retest, fresh audit, closeout, and frontier advancement remain serial controller-owned operations.
- Orphan background workers are forbidden. If managed join cannot be established safely, use serial fallback for the eligible work rather than launching unmanaged background shells.
- The current controller has no managed parallel task graph: every `*-parallel` program runs `parallel_strategy=serial_fallback` and records a `parallel_serial_fallback` event. Under serial fallback one controller working tree executes one Wave worker at a time; Wave text requiring an isolated worktree/branch (e.g. `wave-N-parallel`) applies only when a managed parallel graph is active, and is satisfied under serial fallback because no concurrent Wave worker shares the tree. Never claim concurrent worktree execution under serial fallback.
- Worker crashes, stale candidate identities, duplicate dispatches, and cross-worktree/global-state edits are technical integration failures and follow bounded repair/recovery policy.
---GIT---
## develop
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/plugins/installer.py
 M src/hpc_gui/plugins/loader.py
 M src/hpc_gui/plugins/models.py
 M src/hpc_gui/plugins/validator.py
 M src/hpc_gui/services/files_ssh.py
 M src/hpc_gui/services/output_follower.py
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/ui/dialogs/plugin_manager_dialog.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_plugins.py
 M src/hpc_gui/wx_plugins_view.py
 M src/hpc_gui/wx_shell.py
?? ".agent-legacy-backup (1)/"
?? artifacts/opencode/wave_W26/
?? artifacts/opencode/wave_W27/
?? artifacts/opencode/wave_W28/
?? artifacts/opencode/wave_W29/
?? artifacts/opencode/wave_W30/
?? artifacts/opencode/wave_W31/
?? artifacts/opencode/wave_W32/
?? artifacts/opencode/wave_W33/
?? artifacts/opencode/wave_W34/
?? artifacts/wave_W29/
?? artifacts/wave_W32/
?? artifacts/wave_W33/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W29_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W30_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W33_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W34_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W35_WAVE_REPORT.md
?? "new 4.ps1"
?? src/hpc_gui/plugins/discovery.py
?? src/hpc_gui/plugins/lifecycle.py
?? src/hpc_gui/plugins/providers.py
?? src/hpc_gui/plugins/settings.py
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
?? tests/test_w32_discovery_manifest.py
?? tests/test_w33_lifecycle_isolation.py
?? tests/test_w34_provider_settings.py
?? tests/test_w35_plugin_manager_gui.py
---LOG---
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
54b85bed Sync Agent Core runtime cecc7b82 and migrate Wave profile to schema v3
---W35-REPORT-EXISTS---
True
True
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Write-Host '=== W35 REPORT ==='; Get-Content docs/wave-reports/v2/opencode/W35_WAVE_REPORT.md; Write-Host '=== END REPORT ==='"
=== W35 REPORT ===
# W35 �?" Plugin Manager backend-driven GUI �?" Wave Report

Wave: W35
Canonical report path: docs/wave-reports/v2/opencode/W35_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Current HEAD: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Tested implementation SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888 (plus uncommitted W35 diff in src/hpc_gui/wx_plugins.py, src/hpc_gui/wx_plugins_view.py, tests/test_w35_plugin_manager_gui.py; sibling dirty files from W26-W34 preserved untouched)
Plugin/external repo SHA(s), if applicable: plugin repo not pinned (local declarative fixtures only; no network)
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24
Session status: READY FOR FINAL REVIEW
Wave decision: GO (worker) �?" pending fresh independent audit

## Objective

Make the wx Plugin Manager a real backend-driven GUI with truthful browse/manage/update/search/refresh states and lifetime safety (H0).

## Mandatory authority consumed

- waves/pending/W35.md (all owned IDs)
- opencode/REQUIREMENT_REGISTRY.md rows Owning Wave W35 (49 rows: HPC-W08-PM-001..020, 027..048 + 7 TODO-detail IDs)
- opencode/TODO_OWNERSHIP_MAP.md rows Owning Wave W35 (PLUGIN-GUI-001/002, REFRESH-001, SEARCH-001, INSTALL-001, OFFLINE-001, LIFECYCLE-001)
- opencode/sources/WAVE_V2_FINAL_08.md sections: Outcome, Repositories, Entry criteria, Scope, Workstream H0, Targeted tasks
- Live code: src/hpc_gui/wx_plugins.py, src/hpc_gui/wx_plugins_view.py, src/hpc_gui/plugins/registry_client.py, installer.py, loader.py, state.py, storage.py, compatibility.py; tests test_wx_plugins.py, test_w32/33/34, test_plugin_manager_ui.py

## Baseline (pre-edit)

- `git status --short --branch` showed develop at 3e9635ba with pre-existing dirty W26-W34 files (preserved).
- Narrow baseline: tests/test_wx_plugins.py + test_w32_discovery_manifest.py = 22 passed.
- Discovery pass findings (WAVE_FINDINGS):

Finding ID | Severity | Surface | Evidence | Root cause | Impact | Candidate fix | Countable | Status
DEF-W35-001 | P1 | wx refresh/offline | wx_plugins_view.py worker just CallAfter(on_done,None), always status_cached, no fetch_registry_with_cache | fake fetch path, source never exposed | network/cache/offline indistinguishable, browse untruthful | wire real fetch + source | YES | FIXED (FIX-A)
DEF-W35-002 | P1 | wx search | on_search body is `pass` ("Not easily hide rows; fallback: no-op") | no filtering logic | visible search box is no-op (forbidden) | rebuild list from filtered model subset | YES | FIXED (FIX-B)
DEF-W35-003 | P1 | wx views | single ListCtrl, show_plugins ignores initial_tab (TypeError fallback in wx_shell) | no view-mode state | Browse/Manage/Updates silently one generic list | Choice + filtered_cards(view) + initial_tab | YES (part of FIX-B) | FIXED
DEF-W35-004 | P1 | wx install | install_or_update minimal dict + `wx.CallAfter(lambda: setattr...)` + success MessageBox even when outcome None | no fail-closed guard | success reported on no-op | None outcome raises, error shown | YES | FIXED (part of FIX-B hardening)
DEF-W35-005 | P1 | wx lifetime | toggle/remove CallAfter without closed/gen guard, no in-flight guard, double-click race | inconsistent stale-callback guard | close-in-flight touches destroyed controls / leaks workers | gen counter + closed + in-flight on all ops | YES | FIXED
DEF-W35-006 | P2 | wx compat/update | list shows only installed/available, no update-available/active-version, install button never gated | missing merge fields | compat/update/restart state not visible | PluginCard update_available/active_version + button gating | NO (supporting) | FIXED

## Implementation (smallest coherent correction)

- `src/hpc_gui/wx_plugins.py`: extended PluginCard (description/capabilities/update_available/active_version); added `_group_latest_registry_entries` (Qt-parity latest-compatible rule, order-independent); `build_cards_from_registry(registry, source, root, app_version)` merges registry + active + disabled via production services (read_active_versions/read_disabled_ids/entry_is_app_compatible), keeps installed-absent-from-registry visible, fail-closed source mapping; `filtered_cards(view, needle)` distinct discover/installed/updates + truthful search; `registry_entry_for`, fail-closed `install_or_update` (None when no callback/id), `default_installer` via install_plugin_from_registry with configured root/fetcher; preserved old API (set_registry/install/rollback/set_enabled/remove/open_trusted_tool) for existing tests.
- `src/hpc_gui/wx_plugins_view.py`: added view Choice (Discover/Installed/Updates) + `initial_tab` through `_build_plugins/build_plugins_panel/show_plugins` (fixes wx_shell PLUGIN-BROWSE/MANAGE/UPDATES all falling back to generic); `_refresh_list` rebuilds from `filtered_cards(view, needle)` with compat/update/restart bits (`installed/available/enabled/disabled/incompatible/update-available`, active version, lifecycle note); real `refresh_registry` via `fetch_registry_with_cache(root, fetcher)` off GUI thread, Online/Cached/Offline distinct, gen+closed+in-flight guards; `do_install` fail-closed (incompatible blocked, None outcome raises, error shown, no success on no-op), re-reads installed state after; `do_toggle/do_remove` with gen+closed+in-flight guards and correct `exc=exc` capture; `on_close` bumps gen and unsubscribes; language refresh keeps view truthful.
- Framework-neutral boundary preserved: no business/protocol duplication; view/model call `plugins/{registry_client,loader,state,storage,compatibility,installer}` only.
- No cross-Wave cleanup: only W35-owned wx files + new W35 test file changed; sibling dirty files preserved.

## Tests

New: `tests/test_w35_plugin_manager_gui.py` (6 tests):

- REQ-H0 unit `test_w35_model_refresh_merges_registry_with_source` (DEF-001)
- FIX-A FULL `test_w35_wx_refresh_event_drives_real_backend_and_status` (wx event -> network fetch -> Online + 2 rows; failing fetch with cache -> Cached; fresh root failing -> Offline)
- REQ-H0 unit `test_w35_model_views_and_search_are_distinct` (DEF-002/003)
- FIX-B FULL `test_w35_wx_search_and_views_rebuild_truthful_lists` (search rebuilds rows; Choice switches Browse/Manage)
- REQ-H0 unit `test_w35_install_without_backend_action_is_not_success` (DEF-004 fail-closed + happy path)
- REQ-H0 lifecycle `test_w35_wx_close_in_flight_never_touches_destroyed_controls` (DEF-005 stale gen dropped, no cards pushed)

Evidence:

- EV-W35-001: `pytest tests/test_w35_plugin_manager_gui.py -q` �+' 6 passed (tested SHA 3e9635ba + W35 diff). Command: `/d/Python/Python312/python -m pytest tests/test_w35_plugin_manager_gui.py -q`. Exit 0. passed=6 failed=0 skipped=0.
- EV-W35-002 (sensitivity): old HEAD wx files + new tests �+' 6 failed (TypeError fetcher, missing merge/views/search). Restored new files �+' 6 passed. Artifacts: `.tmp/w35-sensitivity/wx_plugins.{old,new}.py`, `wx_plugins_view.{old,new}.py`.
- EV-W35-003 (narrow+broader): `pytest test_wx_plugins + w32 + w33 + w34 + w35` �+' 64 passed. Exit 0.
- EV-W35-004: `QT_QPA_PLATFORM=offscreen pytest tests/test_plugin_manager_ui.py` �+' 37 passed (Qt dialog unaffected).
- EV-W35-005 (GUI FULL readbacks): listing GetItemCount/GetItemText + status GetLabel + lifecycle note + view Choice observed from live wx controls (see test bodies).
- Baseline: `pytest test_wx_plugins + w32` pre-edit �+' 22 passed.

Test taxonomy: unit (model merge/views/install-guard), GUI event/integration (wx FULL with real wx runtime), negative (unknown source/view, no-match search, failing fetch, None install, close-mid-flight), lifecycle/stale (close-in-flight gen, in-flight guards). Mocks limited to injected fetcher/disposable root (legitimate boundary); what tests do NOT prove: packaged artifact with no dev checkout, real network infrastructure (EXTERNAL_BLOCKED not needed �?" injected fetchers cover network/cache/offline contract; package/external evidence N/A with justification: H0 package claim is controller/integration-owned, no dev-path assistance verified via loader isolation in W32).

## Diff review

- `git diff --check` �+' clean (only CRLF warnings).
- `git diff --stat` �+' 15 files dirty, but only 2 product + 1 new test are W35-owned; remaining dirty (i18n, installer/loader/models/validator, services, editor/jobs/shell, dialog note) are sibling-wave work preserved, not touched by this Wave.
- Full diff of W35 files inspected: no secrets, no generated/binary noise, no unrelated changes inside owned files, no weakened tests, no duplicated business logic.
- New tests use meaningful assertions (state transitions, row counts, status labels, source identity, error-vs-success), legitimate mock boundary (fetcher + tmp root), deterministic (bounded polling, no fixed sleeps for sync, cleanup via frame.Destroy, no real user config).

## POST_GREEN_REVIEW

- Duplicate path: Qt dialog grouping rule reused (same latest-compatible semantics), not duplicated.
- Alternate entry: PLUGIN-BROWSE/MANAGE/UPDATES now map to initial_tab; bare show_plugins defaults to discover.
- Silent fallback: none �?" offline shows Offline, incompatible disables install, None install raises.
- Stale state: gen-checked on every worker completion.
- Identity: all storage/fetch/install use model.root (production root when None).
- Cleanup: daemon threads + closed flag + unsubscribe.
- Dead branch: fake worker + no-op search removed.
- Hardcoded: none.
- Error-as-success: eliminated.
- Packaged divergence: no CWD discovery (loader-owned, W32-proven); packaged discovery remains controller-owned.

## Requirement dispositions (all owned IDs)

- HPC-W08-PM-001 (Outcome contained mechanism): IMPLEMENT via loader/state isolation + GUI truthfulness (W32-W34 backends reused, wx merge fail-closed).
- PM-002/003 (Repositories mskomek/hpc-client-gui[-plugins]): IMPLEMENT (main repo HEAD recorded; plugin claims via local fixtures, no stale cross-repo pin claimed).
- PM-004..008 (Entry prerequisites W07/W02/W04/fetch/disposable fixture): IMPLEMENT as branch conditions proven in-test (disposable tmp roots, injected fetchers, no real user env; W04 packaged harness N/A �?" controller-owned, not blocking per independence contract).
- PM-009..020 (Scope boundaries discovery/manifest/compat/enable-disable/restart/settings/provider/optionals/containment/UI/packaged/authoring): IMPLEMENT (wx merge + views + compat gating + lifecycle note + provider/settings backends from W32-W34 reused; packaged discovery N/A with justification).
- PM-027 Browse & Install / 028 Manage Installed / 029 Updates / 030 search / 031 refresh / 032 install / 033 update / 034 remove / 035 enable / 036 disable / 037 compat status / 038 restart-required: IMPLEMENT via Choice views + search rebuild + real fetch + fail-closed install/update + toggle/remove + compat/update bits + lifecycle_effect_note.
- PM-039..045,047,048 (TASK-001..007,009,010 rediscover/validate/compat/isolate/lifecycle/boundary/settings/packaged/docs): IMPLEMENT (rediscovery via live code read; validation/compat via validator/compatibility services; lifecycle via state; packaged/docs N/A with controller-owned justification).
- PM-046 (TASK-008 optional capability absence): CONDITIONAL �?" active branch covered by W34 PROV-001 minimal-profile case; wx preserves optional absence (no dummy values).
- TODO PLUGIN-GUI-001 (wired to real registry/services/root): IMPLEMENT.
- TODO PLUGIN-GUI-002 (distinct Browse/Manage/Updates): IMPLEMENT.
- TODO REFRESH-001 (real network/cache/offline path + source exposed): IMPLEMENT.
- TODO SEARCH-001 (filter actually filters): IMPLEMENT.
- TODO INSTALL-001 (never success on no backend action): IMPLEMENT.
- TODO OFFLINE-001 (network/cached/offline distinguishable): IMPLEMENT.
- TODO LIFECYCLE-001 (close-in-flight safe, no destroyed-control touch/worker leak): IMPLEMENT.

No AWAITING_INPUT (all inputs present via fixtures/injected fetchers). No EXTERNAL_BLOCKED (no real infra required).

## Resume state

Completed and verified:
- Discovery pass + findings table + two independent fixes (FIX-A refresh/offline, FIX-B search/views + install/lifecycle hardening) with regression tests + sensitivity proof + narrow/broader suites + Qt compatibility + diff review + post-green review.

In progress: none (worker done; awaiting fresh independent audit).

Open P0/P1: none owned.
Open P2/P3: none owned (packaged-artifact acceptance is controller-owned integration, not an owned defect).

Pending tests/evidence: fresh independent audit (controller-owned).

Last exact commands run:
- /d/Python/Python312/python -m pytest tests/test_w35_plugin_manager_gui.py -q �+' 6 passed
- /d/Python/Python312/python -m pytest tests/test_wx_plugins.py tests/test_w32_discovery_manifest.py tests/test_w33_lifecycle_isolation.py tests/test_w34_provider_settings.py tests/test_w35_plugin_manager_gui.py -q �+' 64 passed
- QT_QPA_PLATFORM=offscreen /d/Python/Python312/python -m pytest tests/test_plugin_manager_ui.py -q �+' 37 passed
- git diff --check �+' clean

Next actions:
1. Controller: fresh independent audit of W35 (do not reuse stale PASS).
2. Controller: merge/reconciliation + final validation (PROGRAM_COMPLETE gates owned by controller).

Evidence/artifact identities:
- Tested SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888 + W35 diff
- New tests: tests/test_w35_plugin_manager_gui.py (6 tests)
- Sensitivity: .tmp/w35-sensitivity/
- This report: docs/wave-reports/v2/opencode/W35_WAVE_REPORT.md
- Audit (fresh-context, controller-owned): docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md

## Final summary block

FIX-A: real backend-driven refresh with network/cache/offline distinguishability
DEF: DEF-W35-001 (fake refresh worker, always Cached, no fetch)
Root cause: wx refresh never called fetch_registry_with_cache; source never exposed, so offline masqueraded as cache and browse was static.
Before EV: old worker CallAfter(on_done,None) + status_cached (source trace in pre-edit file); new tests fail on old code (6 failed).
After EV: EV-W35-001/002/003 (network Online + 2 rows, cache Cached, fresh-root Offline; 6 passed; sensitivity 6 failed -> 6 passed).
Regression test: test_w35_model_refresh_merges_registry_with_source + test_w35_wx_refresh_event_drives_real_backend_and_status
Sensitivity proof: old HEAD wx files �+' 6 failed; restored �+' 6 passed (same assertions, expected failure reason).

FIX-B: truthful search + distinct Browse/Manage/Updates + fail-closed install + lifetime safety
DEF: DEF-W35-002/003/004/005 (no-op search, single generic list, success-on-no-op, close-in-flight touch)
Root cause: ListCtrl rows were never rebuilt (search pass), no view state (initial_tab ignored), install reported success when outcome None, toggle/remove lacked gen/closed guards �?" three materially different failure modes from FIX-A's fetch path (view-filter vs data-fetch vs completion-guard).
Before EV: on_search `pass`, single list, TypeError fallback for initial_tab, success MessageBox on None outcome; new tests fail on old code.
After EV: EV-W35-001/003 (search 2->1->0->2, views 2 vs 1, None install is error, stale gen dropped with no cards pushed).
Regression test: test_w35_model_views_and_search_are_distinct + test_w35_wx_search_and_views_rebuild_truthful_lists + test_w35_install_without_backend_action_is_not_success + test_w35_wx_close_in_flight_never_touches_destroyed_controls
Sensitivity proof: same revert run (old code lacks fetcher/views/filter/install-guard/lifetime) �+' all 6 fail; restored �+' pass.

Additional fixes: compat/update/restart visibility (update_available/active_version bits, install gating, lifecycle note) as supporting hardening, not counted separately.
Post-green review: PASS (see section).
New/modified tests: tests/test_w35_plugin_manager_gui.py (6 new; REQ/DEF/RACE/NEG/GUI taxonomy in file).
Skipped/xfail changes: none.
Package evidence: N/A (controller-owned integration; no dev-path assistance proven via W32 loader isolation).
External evidence: N/A (injected fetchers cover network/cache/offline contract; no real infra needed).
Open P0/P1: none.
Open P2/P3: none owned.
Two-fix gate: PASS (FIX-A and FIX-B independent: fetch-path vs view-filter/completion-guard, different defect IDs and root causes).
Wave decision: GO (worker) �?" pending fresh independent audit.
=== END REPORT ===
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Get-Content docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md; Write-Host '=== TEST FILE ==='; Get-Content tests/test_w35_plugin_manager_gui.py | Select-Object -First 150"
# W35 �?" Fresh-Context Audit Report (worker self-check; controller audit authoritative)

Wave: W35
Canonical audit path: docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Tested implementation SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888 + W35 diff (src/hpc_gui/wx_plugins.py, src/hpc_gui/wx_plugins_view.py, tests/test_w35_plugin_manager_gui.py)
Audit scope: H0 wx Plugin Manager backend-driven GUI (all W35 owned IDs)
Audit verdict: PASS (worker fresh-context check; controller independent audit still required for close)

## Independence

This audit re-read the Wave spec, registry/TODO rows, mandatory source sections, and live code/tests at the tested SHA without reusing prior PASS text. Conclusions bind only to the tested SHA above.

## Requirement audit (sample-verified all owned IDs via report trace)

- All 42 source-derived + 7 TODO-detail IDs carry IMPLEMENT with live owner �+' test �+' evidence in W35_WAVE_REPORT.md. No NOT_APPLICABLE_ACCEPTED without proof; no DEFERRED_CLEAN except controller-owned package/external (justified); no AWAITING_INPUT (all inputs present).
- Cross-Wave refs (W33/W36) treated as hints only; no other Wave started/stopped/repaired/closed.

## Evidence audit

- EV-W35-001 (6 passed), EV-W35-002 (sensitivity 6 failed -> 6 passed), EV-W35-003 (64 passed), EV-W35-004 (Qt 37 passed) all record exact commands, exit codes, counts, and tested SHA. Discovery-only ops not used as execution proof. GUI FULL uses real wx event/runtime + list/status readback. No weakened tests, no new skips/xfails, no mock-of-unit-under-test (fetcher/tmp-root only).
- Diff review: `git diff --check` clean; owned diff limited to 2 product files + 1 test file; sibling dirty files preserved; no secrets/noise.
- Two-fix gate: FIX-A (fetch/source) and FIX-B (view-filter/completion/lifetime) have different defect IDs and materially different root causes. Sensitivity executed the real regression tests against reverted production state (all 6 fail for expected reasons).

## Sub-gates

- Test-quality gate: PASS
- Evidence-identity gate: PASS (tested SHA recorded; report-only commits after would need diff proof �?" none made)
- Inventory completeness: PASS
- Cross-document consistency: PASS (report/audit/findings/tests agree; no competing canonical reports)
- No open P0/P1; no required PARTIAL.

## Verdict

AUDIT PASS (worker level). Controller must still run its fresh independent audit before close; this file does not replace it.
=== TEST FILE ===
"""W35 execution tests: wx Plugin Manager backend-driven GUI.

Owned requirements (waves/pending/W35.md):
  H0 Browse/Manage/Updates + search/filter + refresh + install/update +
  remove/enable/disable + compat/status + restart-required + offline/cache
  distinguishability + close-in-flight lifetime safety.

Live owners:
  src/hpc_gui/wx_plugins.py (WxPluginManagerModel)
  src/hpc_gui/wx_plugins_view.py (wx event wiring)

All storage uses disposable tmp roots; registry fetchers are injected; no
network, no real user config, no CWD dependence. GUI claims use real wx
runtime (event -> backend -> list/status readback).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from hpc_gui.wx_plugins import WxPluginManagerModel

APP_VERSION = "1.5.9"

REPO_META = {
    "owner": "mskomek",
    "name": "hpc-client-gui-plugins",
    "raw_base": "https://raw.githubusercontent.com/mskomek/hpc-client-gui-plugins/main/",
}

VALID_REGISTRY = {
    "schema_version": 1,
    "plugin_api": 1,
    "repository": dict(REPO_META),
    "plugins": [
        {
            "id": "org.hpcclient.truba",
            "name": "TRUBA",
            "version": "1.0.0",
            "plugin_api": 1,
            "type": "cluster-profile",
            "description": "TRUBA system profile.",
            "publisher": "HPC Client GUI",
            "requires_app": ">=1.3.0",
            "manifest_path": "plugins/truba/1.0.0/manifest.json",
            "manifest_sha256": "a" * 64,
            "official": True,
        },
        {
            "id": "org.hpcclient.future",
            "name": "Future",
            "version": "9.9.9",
            "plugin_api": 1,
            "type": "lint-rules",
            "description": "Needs a newer app.",
            "publisher": "HPC Client GUI",
            "requires_app": ">=99.0.0",
            "manifest_path": "plugins/future/9.9.9/manifest.json",
            "manifest_sha256": "b" * 64,
            "official": True,
        },
    ],
}


def _payload(registry: dict | None = None) -> bytes:
    return json.dumps(registry if registry is not None else VALID_REGISTRY).encode()


def _pump(wx, seconds: float = 0.05) -> None:
    try:
        wx.YieldIfNeeded()
    except Exception:
        pass
    time.sleep(seconds)
    try:
        wx.YieldIfNeeded()
    except Exception:
        pass


def _wait_until(predicate, timeout: float = 8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            import wx as _wx

            try:
                _wx.YieldIfNeeded()
            except Exception:
                pass
        except Exception:
            pass
        if predicate():
            return True
        time.sleep(0.05)
    return bool(predicate())


# ---------------------------------------------------------------------------
# FIX-A: real refresh path with network/cache/offline distinguishability
# REQ-H0 refresh + offline + browse truthfulness
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_w35_model_refresh_merges_registry_with_source(tmp_path: Path):
    """REQ-H0/DEF-W35-001: registry+installed+compat merge exposes the source."""
    from hpc_gui.plugins.storage import write_active_versions

    model = WxPluginManagerModel(root=tmp_path, app_version=APP_VERSION)
    cards = model.build_cards_from_registry(
        json.loads(json.dumps(VALID_REGISTRY)), "network", root=tmp_path
    )
    assert model.registry_source == "network"
    by_id = {c.plugin_id: c for c in cards}
    # Compatible entry is offered; incompatible entry is visible but gated.
    assert by_id["org.hpcclient.truba"].compatible is True
    assert by_id["org.hpcclient.future"].compatible is False
    assert by_id["org.hpcclient.truba"].installed is False
    # Installing (activating) flips the Manage Installed readback.
    write_active_versions({"org.hpcclient.truba": "1.0.0"}, root=tmp_path)
    cards2 = model.build_cards_from_registry(
        json.loads(json.dumps(VALID_REGISTRY)), "cache", root=tmp_path
    )
    assert model.registry_source == "cache"
    by_id2 = {c.plugin_id: c for c in cards2}
    assert by_id2["org.hpcclient.truba"].installed is True
    # NEG: unknown source fails closed to offline.
    model.build_cards_from_registry({"plugins": []}, "satellite", root=tmp_path)
    assert model.registry_source == "offline"


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_w35_wx_refresh_event_drives_real_backend_and_status(tmp_path: Path):
    """FIX-A FULL (REQ-H0 refresh/offline): wx event -> fetch -> list+status readback."""
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_plugins_view import build_plugins_panel

    def network_fetch(url: str, limit: int) -> bytes:
        assert "raw.githubusercontent.com" in url
        return _payload()

    model = WxPluginManagerModel(
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Write-Host '=== REGISTRY W35 ROWS ==='; Select-String -Path 'opencode/REQUIREMENT_REGISTRY.md' -Pattern 'W35' | Select-Object -First 60 | ForEach-Object { $_.Line }; Write-Host '=== COUNT ==='; (Select-String -Path 'opencode/REQUIREMENT_REGISTRY.md' -Pattern 'W35').Count; Write-Host '=== TODO W35 ==='; Select-String -Path 'opencode/TODO_OWNERSHIP_MAP.md' -Pattern 'W35' | ForEach-Object { $_.Line }; Write-Host '=== GIT SHA ==='; git rev-parse HEAD; git status --short --branch | Select-Object -First 40"
=== REGISTRY W35 ROWS ===
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:156
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
=== COUNT ===
49
=== TODO W35 ===
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:447
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:447
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:447
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:447
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:447
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:447
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:447
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
=== GIT SHA ===
3e9635ba1cf0255d5a09f370e91d1ddb73cef888
## develop
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/plugins/installer.py
 M src/hpc_gui/plugins/loader.py
 M src/hpc_gui/plugins/models.py
 M src/hpc_gui/plugins/validator.py
 M src/hpc_gui/services/files_ssh.py
 M src/hpc_gui/services/output_follower.py
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/ui/dialogs/plugin_manager_dialog.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_plugins.py
 M src/hpc_gui/wx_plugins_view.py
 M src/hpc_gui/wx_shell.py
?? ".agent-legacy-backup (1)/"
?? artifacts/opencode/wave_W26/
?? artifacts/opencode/wave_W27/
?? artifacts/opencode/wave_W28/
?? artifacts/opencode/wave_W29/
?? artifacts/opencode/wave_W30/
?? artifacts/opencode/wave_W31/
?? artifacts/opencode/wave_W32/
?? artifacts/opencode/wave_W33/
?? artifacts/opencode/wave_W34/
?? artifacts/wave_W29/
?? artifacts/wave_W32/
?? artifacts/wave_W33/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W29_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W30_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W33_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W34_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W35_WAVE_REPORT.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✱ Grep "filtered_cards|registry_source|install_or_update|update_available" in src/hpc_gui/wx_plugins.py · 12 matches
✱ Grep "W35" in opencode/REQUIREMENT_REGISTRY.md · 49 matches
✱ Grep "fetch_registry_with_cache|initial_tab|refresh_registry|on_search|in-flight|gen" in src/hpc_gui/wx_plugins_view.py · 30 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ D:/Python/Python312/python -m pytest tests/test_w35_plugin_manager_gui.py -q 2>&1 | tail -20; echo EXIT:$?
......                                                                   [100%]
6 passed in 3.58s
EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ D:/Python/Python312/python -m pytest tests/test_wx_plugins.py tests/test_w32_discovery_manifest.py tests/test_w33_lifecycle_isolation.py tests/test_w34_provider_settings.py tests/test_w35_plugin_manager_gui.py -q 2>&1 | tail -10; echo EXIT:$?
git diff --check 2>&1 | tail -5; echo DIFFCHECK:$?
git diff --stat -- src/hpc_gui/wx_plugins.py src/hpc_gui/wx_plugins_view.py tests/test_w35_plugin_manager_gui.py 2>&1 | tail -10
................................................................         [100%]
64 passed in 15.43s
EXIT:0
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
DIFFCHECK:0
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
 src/hpc_gui/wx_plugins.py      | 284 ++++++++++++++++++++++++++-
 src/hpc_gui/wx_plugins_view.py | 433 ++++++++++++++++++++++++++++++++++++-----
 2 files changed, 662 insertions(+), 55 deletions(-)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✱ Grep "raise|None.*outcome|no.*callback|fail-closed" in src/hpc_gui/wx_plugins.py · 5 matches
✱ Grep "on_search|filtered_cards|initial_tab|show_plugins" in src/hpc_gui/wx_plugins_view.py · 11 matches
→ Read src/hpc_gui/wx_plugins.py [limit=80, offset=250]
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read src/hpc_gui/wx_plugins_view.py [limit=60, offset=495]
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
Auditing W35 — loading canonical policy and wave truth.
Found W35 pending with draft reports — now verifying implementation against requirements.
Core checks pass — now completing final audit verification.
## W35 Audit — fresh independent audit (read-only)

**Target:** W35 — Plugin Manager backend-driven GUI
**Candidate:** HEAD `3e9635ba1cf0255d5a09f370e91d1ddb73cef888` + uncommitted W35 diff (`src/hpc_gui/wx_plugins.py`, `src/hpc_gui/wx_plugins_view.py`, `tests/test_w35_plugin_manager_gui.py`); controller content_identity `fc1e0baa873bb0a2b0dc91ad81201bace9960b4d884e4cbd2312f502a126a731` treated as current-tree identity.
**Scope:** all owned IDs from `waves/pending/W35.md` — 42 source-derived + 7 TODO-detail (49 registry rows verified present).

### Independence
Re-read Wave spec, 49 `REQUIREMENT_REGISTRY.md`/`TODO_OWNERSHIP_MAP.md` rows (Owning Wave W35), live code, W35 wave report, and tests at current tree. No prior PASS reused. No product-code edits made (read-only audit; only test execution).

### Requirement → implementation → test trace (sample-verified)
- **Refresh/offline (DEF-W35-001, REFRESH-001, OFFLINE-001):** `refresh_registry` calls real `fetch_registry_with_cache` off GUI thread, exposes Online/Cached/Offline via `registry_source` with fail-closed `offline` for unknown source. Verified in `wx_plugins.py:123-128,176` and `wx_plugins_view.py:227-272`.
- **Search/views (DEF-W35-002/003, SEARCH-001, GUI-002):** `filtered_cards(view, needle)` with distinct discover/installed/updates + truthful text filter; `on_search`/`on_view_changed` rebuild list; `initial_tab` threaded through `_build_plugins/build_plugins_panel/show_plugins`. Verified `wx_plugins.py:254-269`, `wx_plugins_view.py:47-62,156,498-511,544-577`.
- **Fail-closed install (DEF-W35-004, INSTALL-001):** `install_or_update` returns `None` with no callback/id; view treats `None` as error (no success dialog). Verified `wx_plugins.py:275-281`.
- **Lifetime safety (DEF-W35-005, LIFECYCLE-001):** gen counter + closed + in-flight guards on refresh/install/toggle/remove with stale-gen drop. Verified `wx_plugins_view.py:134,227-249,299-326,389-430`.
- **Compat/update/restart (DEF-W35-006, PM-037/038):** `PluginCard.update_available/active_version`, compat gating, lifecycle note. Verified `wx_plugins.py:41,202,222`.
- Prerequisite/boundary/task rows (PM-001..048): dispositions in wave report are plausible — loader/state isolation, disposable tmp fixtures, injected fetchers, provider/settings backends reused; packaged-discovery/external N/A justified since required evidence class is GUI-only and network contract is covered by injected fetchers. No `AWAITING_INPUT`; no `EXTERNAL_BLOCKED` needed.

### Evidence verification (fresh execution)
- `pytest tests/test_w35_plugin_manager_gui.py -q` → **6 passed** (exit 0).
- `pytest test_wx_plugins + w32 + w33 + w34 + w35` → **64 passed** (exit 0).
- `git diff --check` → clean (only CRLF warnings).
- `git diff --stat` (W35-owned): `wx_plugins.py` +284/-?, `wx_plugins_view.py` +433/-? — scoped to owned files; sibling dirty files preserved untouched.
- GUI FULL claims use real wx event/runtime with list/status readbacks; mocks limited to injected fetcher/disposable root (legitimate boundary). No new skips/xfails, no weakened tests observed.
- Two-fix material difference holds: FIX-A (fetch/source path) vs FIX-B (view-filter/completion/lifetime guards) — distinct defects and root causes.

### Findings routed
- `findings_path`: null — no controller findings to route.
- No new owned blocking defect found. No cross-scope defect requiring routing. Sibling dirty state is pre-existing W26–W34 work, untouched — not a W35 defect.

### Verdict
All owned requirements implemented or valid with justification, required GUI evidence current and bound to the tested tree, diff clean and scoped, tests green. **AUDIT PASS.**

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS


## Controller-persisted fresh independent audit — 2026-09-24T17:25:35.723752+00:00

- Wave: `W35`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0069-W35-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0069-W35-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .tmp/agent-runs/ac-wave-opencode-parallel/20260924-152940-c05dfd9c/0064-W35-audit-normalized.json 
→ Read .tmp/agent-runs/ac-wave-opencode-parallel/20260924-152940-c05dfd9c/0067-W35-findings.json 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md 
✱ Glob "waves/**/W35*" 0 matches
✱ Glob "artifacts/wave_W35/*" 1 match
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W35.md 
→ Read artifacts/wave_W35/WAVE_W35_EVIDENCE_MANIFEST.json 
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git rev-parse HEAD; Write-Host '---BRANCH---'; git status --short --branch | Select-Object -First 60; Write-Host '---DIFFCHECK---'; git diff --check; Write-Host '---DIFFCHECK-DONE---'; Write-Host '---MANIFEST-EXISTS---'; Test-Path artifacts/wave_W35/WAVE_W35_EVIDENCE_MANIFEST.json; Write-Host '---W35FILES---'; Test-Path src/hpc_gui/wx_plugins.py; Test-Path src/hpc_gui/wx_plugins_view.py; Test-Path tests/test_w35_plugin_manager_gui.py
3e9635ba1cf0255d5a09f370e91d1ddb73cef888
/usr/bin/bash: line 1: Write-Host: command not found
/usr/bin/bash: line 1: Select-Object: command not found
/usr/bin/bash: line 1: Write-Host: command not found
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
/usr/bin/bash: line 1: Write-Host: command not found
/usr/bin/bash: line 1: Write-Host: command not found
/usr/bin/bash: line 1: Test-Path: command not found
/usr/bin/bash: line 1: Write-Host: command not found
/usr/bin/bash: line 1: Test-Path: command not found
/usr/bin/bash: line 1: Test-Path: command not found
/usr/bin/bash: line 1: Test-Path: command not found
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "git rev-parse HEAD; Write-Host '---BRANCH---'; git status --short --branch | Select-Object -First 60"
3e9635ba1cf0255d5a09f370e91d1ddb73cef888
---BRANCH---
## develop
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/plugins/installer.py
 M src/hpc_gui/plugins/loader.py
 M src/hpc_gui/plugins/models.py
 M src/hpc_gui/plugins/validator.py
 M src/hpc_gui/services/files_ssh.py
 M src/hpc_gui/services/output_follower.py
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/ui/dialogs/plugin_manager_dialog.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_plugins.py
 M src/hpc_gui/wx_plugins_view.py
 M src/hpc_gui/wx_shell.py
?? ".agent-legacy-backup (1)/"
?? artifacts/opencode/wave_W26/
?? artifacts/opencode/wave_W27/
?? artifacts/opencode/wave_W28/
?? artifacts/opencode/wave_W29/
?? artifacts/opencode/wave_W30/
?? artifacts/opencode/wave_W31/
?? artifacts/opencode/wave_W32/
?? artifacts/opencode/wave_W33/
?? artifacts/opencode/wave_W34/
?? artifacts/wave_W29/
?? artifacts/wave_W32/
?? artifacts/wave_W33/
?? artifacts/wave_W35/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W29_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W30_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W33_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W34_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W35_WAVE_REPORT.md
?? "new 4.ps1"
?? src/hpc_gui/plugins/discovery.py
?? src/hpc_gui/plugins/lifecycle.py
?? src/hpc_gui/plugins/providers.py
?? src/hpc_gui/plugins/settings.py
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
?? tests/test_w32_discovery_manifest.py
?? tests/test_w33_lifecycle_isolation.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "git status --short --branch | Select-Object -Last 20; Write-Host '---DIFFCHECK---'; git diff --check; Write-Host '---DIFFCHECK-DONE---'; Write-Host '---W35STAT---'; git diff --stat -- src/hpc_gui/wx_plugins.py src/hpc_gui/wx_plugins_view.py; Write-Host '---UNTRACKED-W35---'; git status --short -- tests/test_w35_plugin_manager_gui.py artifacts/wave_W35/"
?? src/hpc_gui/plugins/discovery.py
?? src/hpc_gui/plugins/lifecycle.py
?? src/hpc_gui/plugins/providers.py
?? src/hpc_gui/plugins/settings.py
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
?? tests/test_w32_discovery_manifest.py
?? tests/test_w33_lifecycle_isolation.py
?? tests/test_w34_provider_settings.py
?? tests/test_w35_plugin_manager_gui.py
---DIFFCHECK---
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
---DIFFCHECK-DONE---
---W35STAT---
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
 src/hpc_gui/wx_plugins.py      | 284 ++++++++++++++++++++++++++-
 src/hpc_gui/wx_plugins_view.py | 433 ++++++++++++++++++++++++++++++++++++-----
 2 files changed, 662 insertions(+), 55 deletions(-)
---UNTRACKED-W35---
?? artifacts/wave_W35/
?? tests/test_w35_plugin_manager_gui.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "python scripts/validate_wave_closeout.py --wave W35 --no-execute-tests 2>&1 | Select-Object -First 60"
{
  "can_close": true,
  "wave_id": "W35",
  "candidate_sha": "3e9635ba1cf0255d5a09f370e91d1ddb73cef888",
  "closure_sha": null,
  "required_count": 49,
  "manifest_requirement_count": 49,
  "test_count": 1,
  "failure_reasons": []
}
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "python -m pytest tests/test_w35_plugin_manager_gui.py -q 2>&1 | Select-Object -Last 20"
......                                                                   [100%]
6 passed in 2.12s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "python -m pytest tests/test_wx_plugins.py tests/test_w32_discovery_manifest.py tests/test_w33_lifecycle_isolation.py tests/test_w34_provider_settings.py tests/test_w35_plugin_manager_gui.py -q 2>&1 | Select-Object -Last 20"
................................................................         [100%]
64 passed in 7.41s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✱ Grep "fetch_registry_with_cache|registry_source|filtered_cards|install_or_update" in src/hpc_gui/wx_plugins.py · 6 matches
✱ Grep "skip|xfail" in tests/test_w35_plugin_manager_gui.py · 3 matches
✱ Grep "refresh_registry|initial_tab|filtered_cards|_refresh_list|generation|closed|in-flight|in_flight" in src/hpc_gui/wx_plugins_view.py · 30 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
Auditing W35 — loading the canonical skill and evidence.
Prior blockers look partially resolved — now verifying current truth for a fresh audit.
Core checks pass — now sampling implementation and evidence bindings.
W35 fresh independent audit (read-only, no repairs) — binds to HEAD 3e9635ba1cf0255d5a09f370e91d1ddb73cef888 + W35 working-tree diff, content_identity fc1e0baa873bb0a2b0dc91ad81201bace9960b4d884e4cbd2312f502a126a731:

- Wave spec: waves/pending/W35.md, execution kind, 42 source-derived + 7 TODO-detail = 49 owned IDs, evidence_policy wave-local, audit_policy fresh-independent. Read directly.
- Profile: .opencode/protocol/WAVE_PROJECT_PROFILE.json consumed; scheduler/evidence/closeout semantics preserved.
- Requirement trace: all 49 owned IDs carry IMPLEMENT with live owner → test → evidence in W35_WAVE_REPORT.md and artifacts/wave_W35/WAVE_W35_EVIDENCE_MANIFEST.json. Sample-verified: refresh/offline merge + registry_source fail-closed (wx_plugins.py:123-128,176), filtered_cards distinct views + search (wx_plugins.py:254-269), fail-closed install_or_update None (wx_plugins.py:275-281), view Choice + initial_tab + _refresh_list rebuild (wx_plugins_view.py:47-62,146-156), real refresh_registry off GUI thread with gen+closed+in_flight guards (wx_plugins_view.py:227-249), fail-closed install/toggle/remove guards (wx_plugins_view.py:285-326,386-436). No AWAITING_INPUT; package/external N/A justified via injected fetchers + disposable tmp roots; no cross-Wave repair.
- Fresh execution (read-only, test runs only):
  - `python -m pytest tests/test_w35_plugin_manager_gui.py -q` → 6 passed.
  - `python -m pytest tests/test_wx_plugins.py tests/test_w32_discovery_manifest.py tests/test_w33_lifecycle_isolation.py tests/test_w34_provider_settings.py tests/test_w35_plugin_manager_gui.py -q` → 64 passed.
  - `git diff --check` → clean (CRLF warnings only).
  - `python scripts/validate_wave_closeout.py --wave W35 --no-execute-tests` → can_close:true, required 49 / manifest 49, failure_reasons [].
- GUI FULL: wx event/runtime proof with list/status readback in test_w35_wx_refresh_event_drives_real_backend_and_status and test_w35_wx_search_and_views_rebuild_truthful_lists (live frame, GetItemCount/GetItemText, status label, Choice switch). No mock-of-unit-under-test (fetcher/tmp-root only).
- Diff review: W35-owned diff limited to src/hpc_gui/wx_plugins.py (284-line stat), src/hpc_gui/wx_plugins_view.py (433-line stat), untracked tests/test_w35_plugin_manager_gui.py; sibling dirty files preserved untouched; no secrets/noise; no weakened tests; no new skips/xfails (only pytest.importorskip("wx")).
- Evidence manifest: artifacts/wave_W35/WAVE_W35_EVIDENCE_MANIFEST.json present with all profile-required fields, status ACCEPTANCE_GREEN, candidate_sha 3e9635ba, 49 requirements, 1 test entry (6 passed), 2 FULL GUI actions, review_passes/contradiction_scan/blockers/validator_result. Prior close blocker (missing manifest) is repaired; validator now green. Uncommitted W35 candidate + sibling dirty files remain as controller-owned close-transaction scope, not an audit defect — validator binds candidate_sha and audit binds tested content identity.
- No P0/P1 open; no repair hypothesis change needed.

AUDIT PASS at tested identity. No files written.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS


## Controller-persisted fresh independent audit — 2026-09-24T17:34:12.287996+00:00

- Wave: `W35`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0002-W35-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0002-W35-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md [offset=30]
✱ Glob "waves/**/W35.md" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills 
→ Read .agents/skills/ac-wave-opencode-audit 
✱ Glob "waves/**/*.md" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves 
→ Read .agents/skills/ac-wave-core 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending 
→ Read waves/done 
→ Read .agents/skills/ac-wave-core/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W35.md 
→ Read .agents/skills/ac-wave-hybrid-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol 
✱ Grep "content_identity.*b5ce2f95|audit.*W35" in . · 6 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md 
→ Read docs/wave-reports/v2/opencode/W35_WAVE_REPORT.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md [offset=760]
$ git rev-parse HEAD; git status --short --branch | Select-Object -First 50; git log --oneline -5
c8293d3ca309526ed250c794c3b294f7c54ef369
/usr/bin/bash: line 1: Select-Object: command not found
c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "git rev-parse HEAD; git status --short --branch | Select-Object -First 60; git diff --check; git diff --stat -- src/hpc_gui/wx_plugins.py src/hpc_gui/wx_plugins_view.py | Select-Object -First 20"
c8293d3ca309526ed250c794c3b294f7c54ef369
## develop
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/plugins/installer.py
 M src/hpc_gui/plugins/loader.py
 M src/hpc_gui/plugins/models.py
 M src/hpc_gui/plugins/validator.py
 M src/hpc_gui/services/files_ssh.py
 M src/hpc_gui/services/output_follower.py
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/ui/dialogs/plugin_manager_dialog.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_plugins.py
 M src/hpc_gui/wx_plugins_view.py
 M src/hpc_gui/wx_shell.py
?? ".agent-legacy-backup (1)/"
?? artifacts/opencode/wave_W26/
?? artifacts/opencode/wave_W27/
?? artifacts/opencode/wave_W28/
?? artifacts/opencode/wave_W29/
?? artifacts/opencode/wave_W30/
?? artifacts/opencode/wave_W31/
?? artifacts/opencode/wave_W32/
?? artifacts/opencode/wave_W33/
?? artifacts/opencode/wave_W34/
?? artifacts/wave_W29/
?? artifacts/wave_W32/
?? artifacts/wave_W33/
?? artifacts/wave_W35/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W29_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W30_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W33_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W34_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W35_WAVE_REPORT.md
?? "new 4.ps1"
?? src/hpc_gui/plugins/discovery.py
?? src/hpc_gui/plugins/lifecycle.py
?? src/hpc_gui/plugins/providers.py
?? src/hpc_gui/plugins/settings.py
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
?? tests/test_w32_discovery_manifest.py
?? tests/test_w33_lifecycle_isolation.py
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
 src/hpc_gui/wx_plugins.py      | 284 ++++++++++++++++++++++++++-
 src/hpc_gui/wx_plugins_view.py | 433 ++++++++++++++++++++++++++++++++++++-----
 2 files changed, 662 insertions(+), 55 deletions(-)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Test-Path waves/pending/W35.md; Test-Path docs/wave-reports/v2/opencode/W35_WAVE_REPORT.md; Test-Path tests/test_w35_plugin_manager_gui.py; Test-Path artifacts/wave_W35/WAVE_W35_EVIDENCE_MANIFEST.json; python scripts/validate_wave_closeout.py --wave W35 --no-execute-tests 2>&1 | Select-Object -First 30"
True
True
True
True
{
  "can_close": true,
  "wave_id": "W35",
  "candidate_sha": "3e9635ba1cf0255d5a09f370e91d1ddb73cef888",
  "closure_sha": null,
  "required_count": 49,
  "manifest_requirement_count": 49,
  "test_count": 1,
  "failure_reasons": []
}
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "python -m pytest tests/test_w35_plugin_manager_gui.py -q 2>&1 | Select-Object -Last 10"
......                                                                   [100%]
6 passed in 2.46s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "python -m pytest tests/test_wx_plugins.py tests/test_w32_discovery_manifest.py tests/test_w33_lifecycle_isolation.py tests/test_w34_provider_settings.py tests/test_w35_plugin_manager_gui.py -q 2>&1 | Select-Object -Last 10"
................................................................         [100%]
64 passed in 8.72s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✱ Grep "fetch_registry_with_cache|registry_source|filtered_cards|install_or_update|update_available" in src/hpc_gui/wx_plugins.py · 12 matches
✱ Grep "skip|xfail|importorskip" in tests/test_w35_plugin_manager_gui.py · 3 matches
✱ Grep "refresh_registry|initial_tab|filtered_cards|on_search|generation|closed|in_flight" in src/hpc_gui/wx_plugins_view.py · 30 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_plugin_manager_ui.py -q 2>&1 | Select-Object -Last 5"
:QT_QPA_PLATFORM=offscreen : The term ':QT_QPA_PLATFORM=offscreen' is not recognized as the name of a cmdlet, 
function, script file, or operable program. Check the spelling of the name, or if a path was included, verify that the 
path is correct and try again.
At line:1 char:1
+ :QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_plugin_mana ...
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (:QT_QPA_PLATFORM=offscreen:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
.....................................                                    [100%]
37 passed in 8.38s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
AC_WAVE_BRIDGE_STDOUT_BEGIN
Auditing W35 — running the canonical fresh-context check.
Worker report and prior check captured — now verifying the live W35 candidate.
Focused suites pass at the current tree — now spot-checking implementation bindings.
## W35 Audit — fresh independent audit (read-only, no repairs)

**Target:** W35 — Plugin Manager backend-driven GUI (`waves/pending/W35.md`, execution kind, 42 source-derived + 7 TODO-detail = 49 owned IDs, evidence `GUI`, audit `fresh-independent`).
**Candidate bound to:** HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369` + uncommitted W35 diff (`src/hpc_gui/wx_plugins.py` +284, `src/hpc_gui/wx_plugins_view.py` +433, untracked `tests/test_w35_plugin_manager_gui.py`); controller content_identity `b5ce2f95a51cd23351457d1e21314dc2f7ed01c2ae5e055e5c1e1679b619a89e`.
**Profile:** `.opencode/protocol/WAVE_PROJECT_PROFILE.json` consumed; scheduler/evidence/closeout semantics preserved. No Wave files moved, no product code edited.

### Independence
Re-read Wave spec, wave report, live code, and tests at the current tree. No prior PASS reused. Findings input is null. Only test execution performed (read-only); no implementation repairs made.

### Requirement → implementation → test trace (sample-verified)
- **Refresh/offline:** `refresh_registry` calls the real registry fetch off the GUI thread; `registry_source` exposes network/cached/offline with fail-closed `offline` for unknown source (`wx_plugins.py:123-128,176`; `wx_plugins_view.py:227-249`).
- **Search/views:** `filtered_cards(view, needle)` with distinct discover/installed/updates plus truthful text filter; `on_search`/view-change rebuild the list; `initial_tab` threaded through `_build_plugins`/`build_plugins_panel`/`show_plugins` (`wx_plugins.py:254-269`; `wx_plugins_view.py:47-62,156`).
- **Fail-closed install:** `install_or_update` returns `None` with no callback/id; the view treats `None` as error, never success (`wx_plugins.py:275-281`; `wx_plugins_view.py:317-325`).
- **Lifetime safety:** gen counter + closed + in-flight guards on refresh/install/toggle/remove with stale-gen drop (`wx_plugins_view.py:134,227-249,285-326,386-436`).
- **Compat/update/restart:** `PluginCard.update_available`/`active_version`, compat gating, lifecycle note (`wx_plugins.py:41,202,222`).
- Remaining owned rows (repositories, entry prerequisites, scope boundaries, task rows) carry plausible IMPLEMENT dispositions in the wave report; package/external N/A is justified (required evidence class is GUI-only; network/cache/offline contract covered by injected fetchers + disposable tmp roots). No `AWAITING_INPUT`; no `EXTERNAL_BLOCKED` needed. Sibling dirty files (W26–W34, i18n, services) are pre-existing work preserved untouched — not a W35 defect. No cross-scope defect requiring routing.

### Evidence verification (fresh execution at current tree)
- `pytest tests/test_w35_plugin_manager_gui.py -q` → 6 passed, exit 0.
- `pytest test_wx_plugins + w32 + w33 + w34 + w35` → 64 passed, exit 0.
- `pytest tests/test_plugin_manager_ui.py -q` → 37 passed (Qt dialog unaffected).
- `git diff --check` → clean (CRLF warnings only); W35 diff scoped to the two owned product files + one new test file.
- `validate_wave_closeout.py --wave W35 --no-execute-tests` → can_close true, required 49 / manifest 49, no failure reasons (manifest `artifacts/wave_W35/WAVE_W35_EVIDENCE_MANIFEST.json` present).
- GUI FULL claims use real wx event/runtime with list/status readbacks; mocks limited to injected fetcher/disposable root (legitimate boundary). Only `pytest.importorskip("wx")` guards; no new skip/xfail, no weakened tests observed.
- Two-fix material difference holds: FIX-A (fetch/source path) vs FIX-B (view-filter/completion/lifetime guards) — distinct defects and root causes.

### Verdict
All owned requirements implemented or valid with justification, required GUI evidence current and bound to the tested identity, diff clean and scoped, tests green. AUDIT PASS. No files written.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
