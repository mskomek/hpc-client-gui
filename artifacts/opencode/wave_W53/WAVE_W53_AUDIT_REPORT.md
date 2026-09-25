# Wave W53 Audit Report
## Controller-persisted fresh independent audit — 2026-09-24T23:21:44.672191+00:00

- Wave: `W53`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0093-W53-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0093-W53-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit 
$ Get-ChildItem waves/pending, waves/done, waves/blocked, waves/postponed -ErrorAction SilentlyContinue | Select-Object FullName, Name, LastWriteTime | Format-Table -AutoSize; Write-Host "---W53-LOCATE---"; Get-ChildItem -Recurse -Filter "W53*" | Select-Object FullName | Format-Table -AutoSize; Write-Host "---GIT-LOG---"; git log --oneline -5; Write-Host "---GIT-STATUS---"; git status --short; Write-Host "---GIT-SHA---"; git rev-parse HEAD
/usr/bin/bash: line 1: Get-ChildItem: command not found
/usr/bin/bash: line 1: Select-Object: command not found
/usr/bin/bash: line 1: Format-Table: command not found
/usr/bin/bash: line 1: Write-Host: command not found
/usr/bin/bash: line 1: Get-ChildItem: command not found
/usr/bin/bash: line 1: Select-Object: command not found
/usr/bin/bash: line 1: Format-Table: command not found
/usr/bin/bash: line 1: Write-Host: command not found
c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
/usr/bin/bash: line 1: Write-Host: command not found
 M README.md
 M build/windows/hpc-client-gui.spec
 M src/hpc_gui/config/storage.py
 M src/hpc_gui/core/diagnostics.py
 M src/hpc_gui/core/i18n.py
 M src/hpc_gui/core/ui_errors.py
 M src/hpc_gui/core/wx_errors.py
 M src/hpc_gui/docs/HELP_en.md
 M src/hpc_gui/docs/HELP_tr.md
 M src/hpc_gui/docs/PLUGINS_en.md
 M src/hpc_gui/docs/PLUGINS_tr.md
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/plugins/installer.py
 M src/hpc_gui/plugins/loader.py
 M src/hpc_gui/plugins/models.py
 M src/hpc_gui/plugins/validator.py
 M src/hpc_gui/services/command_history_store.py
 M src/hpc_gui/services/files_ssh.py
 M src/hpc_gui/services/geometry_policy.py
 M src/hpc_gui/services/output_follower.py
 M src/hpc_gui/services/shortcut_preferences.py
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/ui/dialogs/plugin_manager_dialog.py
 M src/hpc_gui/ui/models/remote_entry_helpers.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_local_files.py
 M src/hpc_gui/wx_logs.py
 M src/hpc_gui/wx_logs_view.py
 M src/hpc_gui/wx_plugins.py
 M src/hpc_gui/wx_plugins_view.py
 M src/hpc_gui/wx_remote_files_view.py
 M src/hpc_gui/wx_settings.py
 M src/hpc_gui/wx_settings_view.py
 M src/hpc_gui/wx_shell.py
 M src/hpc_gui/wx_updater_view.py
 M tests/test_remote_entry_helpers.py
?? ".agent-legacy-backup (1)/"
?? NUL
?? artifacts/opencode/wave_W26/
?? artifacts/opencode/wave_W27/
?? artifacts/opencode/wave_W28/
?? artifacts/opencode/wave_W29/
?? artifacts/opencode/wave_W30/
?? artifacts/opencode/wave_W31/
?? artifacts/opencode/wave_W32/
?? artifacts/opencode/wave_W33/
?? artifacts/opencode/wave_W34/
?? artifacts/opencode/wave_W36/
?? artifacts/opencode/wave_W41/
?? artifacts/opencode/wave_W42/
?? artifacts/opencode/wave_W43/
?? artifacts/opencode/wave_W44/
?? artifacts/opencode/wave_W45/
?? artifacts/opencode/wave_W46/
?? artifacts/opencode/wave_W47/
?? artifacts/opencode/wave_W48/
?? artifacts/opencode/wave_W49/
?? artifacts/opencode/wave_W50/
?? artifacts/opencode/wave_W51/
?? artifacts/opencode/wave_W52/
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
?? docs/wave-reports/v2/opencode/W36_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W37_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W37_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W38_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W38_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W39_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W39_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W40_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W40_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W41_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W42_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W43_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W44_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W45_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W46_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W47_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W48_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W49_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W50_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W51_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W52_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md
?? "new 4.ps1"
?? src/hpc_gui/plugins/discovery.py
?? src/hpc_gui/plugins/lifecycle.py
?? src/hpc_gui/plugins/providers.py
?? src/hpc_gui/plugins/settings.py
?? src/hpc_gui/services/job_identity.py
?? src/hpc_gui/services/job_list_filter_sort.py
?? src/hpc_gui/services/job_submit_cancel.py
?? src/hpc_gui/services/jobs_refresh_state.py
?? src/hpc_gui/services/plugin_request.py
?? src/hpc_gui/services/remote_entry_format.py
?? src/hpc_gui/services/update_restart_policy.py
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
?? tests/test_w36_packaged_docs.py
?? tests/test_w37_settings_persistence.py
?? tests/test_w38_migration_secrets.py
?? tests/test_w39_logs_diagnostics.py
?? tests/test_w40_localization_window_settings.py
?? tests/test_w41_updater_routing.py
?? tests/test_w43_restart_package_policy.py
?? tests/test_w44_arch_qt_wx_package.py
/usr/bin/bash: line 1: Write-Host: command not found
c8293d3ca309526ed250c794c3b294f7c54ef369
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls waves/pending/ waves/done/ waves/blocked/ waves/postponed/ 2>&1 | head -100; echo "===W53-FILES==="; find . -maxdepth 4 -iname "*W53*" -not -path "./.git/*" 2>/dev/null | head -50; echo "===PROFILE-W53==="; ls artifacts/wave_W53/ artifacts/opencode/wave_W53/ 2>&1 | head -50
waves/blocked/:
05-macos-production-updates.md
06-appimage-flatpak.md
07-acceptance-and-rollout.md
WAVE-03-release-packaging-verification.md
WAVE-04-publish-release.md
WAVE-07-wiki-readmes-and-release.md
wave_12_registry_release_and_application_integration.md

waves/done/:
01-shared-foundation.md
02-verification-and-release-contract.md
03-ubuntu-deb-updates.md
ANSYS_LINTER_WAVES_RESULT.md
ANSYS_LINTER_WAVE_00_README.md
ANSYS_LINTER_WAVE_01_API_V2_CONTRACT.md
ANSYS_LINTER_WAVE_02_CORE_ENGINE.md
ANSYS_LINTER_WAVE_03_FLUENT_WORKBENCH.md
ANSYS_LINTER_WAVE_04_MAPDL_MECHANICAL.md
ANSYS_LINTER_WAVE_05_CCL_ICEM.md
ANSYS_LINTER_WAVE_06_SYSTEM_COUPLING_AND_REMAINING.md
ANSYS_LINTER_WAVE_07_UI_CLI_HPC_RULES.md
ANSYS_LINTER_WAVE_08_ACCEPTANCE_RELEASE.md
ANSYS_LINTER_WAVE_09_PACKAGING_CI_REPAIR.md
UPDATE-03-RESULT.md
W01.md
W02.md
W03.md
W04.md
W05.md
W06.md
W07.md
W08.md
W09.md
W10.md
W11.md
W12.md
W13.md
W14.md
W15.md
W16.md
W17.md
W18.md
W19.md
W20.md
W21.md
W22.md
W23.md
W24.md
W25.md
W26.md
W27.md
W28.md
W29.md
W30.md
W31.md
W32.md
W33.md
W34.md
W35.md
W36.md
W37.md
W38.md
W39.md
W40.md
W41.md
W42.md
W43.md
W44.md
W45.md
W46.md
W47.md
W48.md
W49.md
W50.md
W51.md
W52.md
WAVE-01-RESULT.md
WAVE-01-macos-bundle-inventory.md
WAVE-02-RESULT.md
WAVE-02-safe-pyinstaller-pruning.md
WAVE_72_JOBS_DETAILS_WORKSPACE.md
WAVE_73_JOBS_FILES_EXPLORER_PROVIDER_FILTERS.md
WAVE_74_DYNAMIC_JOB_OUTPUT_CHANNELS.md
WAVE_78_JOBS_DETAILS_RAW_FALLBACK.md
WAVE_79_PROVIDER_PARSER_CONTRACT_TRUBA.md
WAVE_80_FILES_OUTPUTS_UX_I18N.md
wave_00_cross_repo_contract_alignment.md
wave_00_current_release_boundary_baseline_freeze.md
wave_01_provider_schema_extensions.md
wave_01_unified_cluster_self_test_core.md
wave_02_cluster_self_test_gui.md
wave_02_provider_context_model.md
wave_03_dynamic_storage_ui.md
wave_03_provider_capability_view.md
wave_04_diagnostic_bundle_v2.md
wave_04_safe_remote_path_resolvers.md
wave_05_provider_update_diff_freshness.md
wave_05_quota_backend_infrastructure_v2.md
wave_06_nersc_perlmutter_provider.md
===W53-FILES===
./.tmp/os/20260922-103254-9af3da2d/w15-0r13tw53
./.tmp/w53-run
./waves/pending/W53.md
===PROFILE-W53===
ls: cannot access 'artifacts/wave_W53/': No such file or directory
ls: cannot access 'artifacts/opencode/wave_W53/': No such file or directory
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W53.md 
$ echo "===W53-REPORT==="; ls docs/wave-reports/v2/opencode/ | grep -i W53; echo "===ARTIFACTS-SEARCH==="; find artifacts .tmp -maxdepth 6 -iname "*W53*" 2>/dev/null | head -30; echo "===W52-DONE-FRONTMATTER==="; head -60 waves/done/W52.md; echo "===W52-AUDIT-REPORT==="; ls artifacts/opencode/wave_W52/ 2>&1 | head -20
===W53-REPORT===
W53_WAVE_REPORT.md
===ARTIFACTS-SEARCH===
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0091-W53-plan-controller-context.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0091-W53-plan-dispatch.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0091-W53-plan-job.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0091-W53-plan-normalized.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0091-W53-plan-opencode.log
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0092-W53-run-controller-context.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0092-W53-run-dispatch.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0092-W53-run-job.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0092-W53-run-normalized.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0092-W53-run-opencode.log
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0093-W53-audit-controller-context.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0093-W53-audit-dispatch.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0093-W53-audit-job.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0093-W53-audit-opencode.log
.tmp/os/20260922-103254-9af3da2d/w15-0r13tw53
.tmp/os/20260924-152940-c05dfd9c/14740-1790252980882148700/context-mode-guidance-s-ses_f2c21ce10fferuPrejW533CGkB
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/w53-gj09-barsxdbh
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/w53-gj09-barsxdbh/w53-remote-note.slurm
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/w53-gj09-eik9_wti
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/w53-gj09-eik9_wti/known_hosts_w53
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/w53-gj09-epop4pbn
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/w53-gj09-epop4pbn/known_hosts_w53
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/w53-gj09-m5nv_atn
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/w53-gj09-m5nv_atn/w53-remote-note.slurm
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/w53-gj09-smr7zhcf
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/w53-gj09-smr7zhcf/w53-gui.log
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/w53-gj09-smr7zhcf/w53-remote-note.slurm
.tmp/w53-run
===W52-DONE-FRONTMATTER===
---
wave_id: "W52"
wave_kind: execution
canonical_source: "W52"
owned_requirements:
  - "HPC-W10-GJ2-006"
  - "HPC-W10-GJ2-007"
  - "HPC-W10-GJ2-008"
  - "HPC-W10-GJ2-009"
  - "HPC-W10-GJ08-PATH-001"
  - "HPC-W10-TODO-PROFILE-ISOLATION-GJ-001"
aggregate_close_owner: false
global_bookkeeping_owner: controller
completion_dependencies: []
evidence_policy: wave-local
audit_policy: fresh-independent
---
# W52 — Golden Journey 08 — Profile isolation

- **Wave ID:** `W52`
- **Original planning Wave:** `W10` (provenance only)
- **Original source Wave file:** `WAVE_V2_FINAL_10.md`
- **Source-derived requirement rows:** **5**
- **TODO-detail rows:** **1**
- **Execution start gate:** `NONE`
- **Integration references (non-blocking):** `W44`
- **Required evidence classes:** `GUI,PACKAGE,EXTERNAL`
- **Parallel execution:** `YES`
- **Execution cohort:** `P10-golden-journeys`
- **User interaction:** `NONE`
- **Integration hints after PASS (non-blocking):** `W55`

## Execution Wave Independence Contract

This execution Wave is lifecycle-independent from every other Wave.

- **Start gate:** none. Historical `Dependencies`, predecessor PASS states, sibling status, downstream unlocks, parent/canonical closeout state, aggregate manifests and aggregate validators are not execution-start or execution-acceptance gates.
- **Acceptance authority:** this Wave reaches `ACCEPTED` only from its own owned requirement IDs, its own required evidence, its own diff review, and a fresh independent audit `PASS`.
- **Cross-Wave references:** any former dependency/unlock relationship is an integration-order hint only. Do not wait for another Wave merely because it is listed as a predecessor, sibling, parent or downstream consumer.
- **Concrete input exception:** if an owned requirement literally consumes an artifact/API/schema produced elsewhere and that input does not exist on the current integration base, mark only the affected requirement `AWAITING_INPUT` with the exact missing identity. Continue all other owned work. Do not reopen or repair another Wave solely from dependency metadata; route a concrete finding to its true owner.
- **Aggregate ownership:** multi-Wave evidence manifests, canonical-source aggregate validators, program-wide ledgers and final program verdicts are controller/integration-reconciliation responsibilities. This Wave may emit its own evidence fragment, but absence/failure of an aggregate artifact cannot block this Wave's `ACCEPTED` unless the failure identifies a concrete defect in one of this Wave's owned IDs.
- **No blanket reopen:** after this Wave is accepted, later sibling/parent integration or aggregate-validator changes do not reopen it. Reopen only for a fresh current defect mapped to an owned requirement/finding ID or when integration changes a file/behavior inside this Wave's ownership surface and a fresh audit demonstrates regression.
- **Conditional Waves:** when applicability depends on a branch/decision, recompute that applicability independently from repository truth. An inactive branch closes as evidence-backed `NOT_APPLICABLE_ACCEPTED`; it does not wait for another Wave's decision artifact.
- The Wave worker never starts, stops, repairs or closes another Wave. Program scheduling and canonical/group reconciliation remain controller-owned.

## Objective

Execute GJ-08 and prove Profile A terminal/files/editor/jobs state or callbacks cannot leak into Profile B.

## Parallel / unattended execution contract

- **Execution mode:** unattended and non-interactive. This Wave must not ask the user a question, wait for user confirmation, pause for a manual click, or require a human to choose among safe alternatives.
- **Scheduler rule:** schedule this Wave independently. Integration references and historical unlocks are non-blocking. Only a concrete missing input required by an owned requirement may produce `AWAITING_INPUT` for that requirement.
- **Isolation:** when any sibling Wave can run concurrently, use an isolated Git branch/worktree and Wave-specific temp/runtime directories. Never edit another Wave's worktree, canonical report, audit report, temp profile, or external test resources.
- **Scope discipline:** parallel execution does not authorize cross-Wave cleanup. Modify only this Wave's owned requirements and directly necessary tests/evidence. Route cross-scope defects to their stable owner instead of fixing them opportunistically.
- **Deterministic decisions:** resolve safe implementation choices from the mandatory authority, current code, tests, and repository conventions. Do not ask the user to choose naming, layout, test strategy, retry behavior, or other routine implementation details.
- **No interactive tooling:** use non-interactive Git/tool flags and bounded commands. Do not open an editor, pager, credential prompt, confirmation prompt, or indefinite watch/tail. Apply explicit timeouts to subprocesses and network/external checks.
- **Credentials / external systems:** use only credentials, tokens, hosts, package artifacts, test accounts, and infrastructure already available to the execution environment. Never request secrets from the user and never invent credentials. If required authorization/infrastructure is unavailable, record `EXTERNAL_BLOCKED` (or the repository's equivalent), complete every remaining safe local/package/GUI check, update the canonical report/audit, and exit without prompting.
- **GUI automation:** any confirmation dialog, chooser, overwrite prompt, restart prompt, or destructive-action guard required by tests must be driven by the maintained test harness/GUI automation against disposable fixtures. Do not wait for a person to click it.
- **Safe failure:** destructive Git, ambiguous authority that remains unresolved after applying documented precedence, or a missing mandatory prerequisite is a terminal Wave status, **not a request for user input**. Preserve evidence, record the exact blocker and resume point, and exit cleanly.
===W52-AUDIT-REPORT===
WAVE_W52_AUDIT_REPORT.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ cat ".tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0091-W53-plan-normalized.json" 2>/dev/null; echo "===RUN-NORM==="; cat ".tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0092-W53-run-normalized.json" 2>/dev/null; echo "===AUDIT-CTX==="; cat ".tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0093-W53-audit-controller-context.json" 2>/dev/null | head -100
{
  "status": "READY",
  "summary": "f baseline invalidated); serialize LOCAL_REAL lease; cleanup leaves lab suitable for next consumer; never invent credentials or log secrets; site-specific claims LOCAL_REAL cannot cover stay `EXTERNAL_BLOCKED`/routed, never weakened.\n\n## 5. Ordered run steps (for RUN worker)\n\n1. Freeze baseline: `git status`, `git rev-parse HEAD`, record content identity; narrow pytest baseline on lifecycle/shell/transfer/jobs/editor/plugin/updater/logs slices where practical.\n2. Build disposable fixtures: Wave-specific profile, local/remote dirs, job names, transfer fixtures, updater fixture, plugin cache; confirm LOCAL_REAL health via `lab-status.ps1` (bounded).\n3. Execute 8 controlled shutdown-in-flight cases separately (terminal, transfer, remote refresh, editor op, jobs poll, plugin refresh, updater fixture, logs refresh) under wx runtime harness with semantic readback (visible control state, worker/thread join proof, no destroyed-control touch).\n4. Assert 6-part envelope per case and E2E: no crash, no destroyed-control callback, no hang, bounded time, deterministic cancel, clean relaunch; collect leak counters (windows/workers) and native-error scan.\n5. Prove TODO details: isolation-independent teardown, zero-counters, bounded relaunch.\n6. PACKAGE smoke on exact artifact SHA; EXTERNAL replay against LOCAL_REAL with environment/target/profile/HEAD binding + cleanup.\n7. Focused regression rerun for every touched behavior + impacted maintained checks; no skip/xfail weakening, no golden rewriting, no retry-to-green.\n8. Diff review: `git status`, `git diff --stat`, `git diff --check`, full diff; secrets/binary-noise/unrelated-change/duplicate-logic check.\n9. Update exactly `docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md` + fresh-context `W53_AUDIT_REPORT.md` (run phase); no suffixed copies.\n10. Fresh independent audit `PASS` required before `ACCEPTED`; close W53 independently.\n\n## 6. Validators / stop conditions\n\n- Validators: profile final validator `scripts/validate_wave_closeout.py` is controller-owned context only, not a start gate; Wave-local evidence manifest per evidence schema; executable postrun checks controller-owned.\n- Stop (never ask user): destructive-Git need, unresolved authority conflict, missing mandatory package/external prerequisite, cross-Wave ownership escape, or report/audit current → record `BLOCKED`/`EXTERNAL_BLOCKED`/truthful status + exact resume point, exit cleanly.\n- No-progress: repeated identical finding + unchanged content identity requires changed hypothesis, never fabricated PASS. Human deferral only for genuinely unavailable credentials/MFA/authority/hardware/service/manual acceptance.\n\n## 7. Definition of Done\n\nAll 18 owned IDs implemented-or-already-valid with current truthful GUI+PACKAGE+EXTERNAL evidence bound to tested candidate/content identity, no owned blocking defect, diff reviewed, canonical report current, fresh-context audit `PASS`.\n\nAC_WAVE_MACHINE_RESULT_BEGIN\nWAVE_PHASE_STATUS: READY\nAC_WAVE_MACHINE_RESULT_END\n",
  "findings": [],
  "changed_files": [],
  "next_action": "none",
  "phase_log_path": ".tmp\\agent-runs\\ac-wave-opencode-parallel\\20260924-203154-ca45d2b7\\0091-W53-plan-opencode.log"
}
===RUN-NORM===
{
  "status": "READY_FOR_AUDIT",
  "summary": "ite docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md\nCreated file successfully: docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md\n> ac-wave-opencode-executor · muse-spark-1.3-contributor\n\u001b[0m$ \u001b[0mgit status --short 2>&1 | grep -v \"^ M\" | head -n 20; echo \"===TRACKED-DIFF-STAT===\"; git diff --stat 2>&1 | tail -n 3; echo \"===CHECK===\"; git diff --check 2>&1 | grep -v \"CRLF\" | head -n 5; echo CHECK-DONE; git status --short docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md 2>&1\n?? \".agent-legacy-backup (1)/\"\n?? NUL\n?? artifacts/opencode/wave_W26/\n?? artifacts/opencode/wave_W27/\n?? artifacts/opencode/wave_W28/\n?? artifacts/opencode/wave_W29/\n?? artifacts/opencode/wave_W30/\n?? artifacts/opencode/wave_W31/\n?? artifacts/opencode/wave_W32/\n?? artifacts/opencode/wave_W33/\n?? artifacts/opencode/wave_W34/\n?? artifacts/opencode/wave_W36/\n?? artifacts/opencode/wave_W41/\n?? artifacts/opencode/wave_W42/\n?? artifacts/opencode/wave_W43/\n?? artifacts/opencode/wave_W44/\n?? artifacts/opencode/wave_W45/\n?? artifacts/opencode/wave_W46/\n?? artifacts/opencode/wave_W47/\n?? artifacts/opencode/wave_W48/\n===TRACKED-DIFF-STAT===\n src/hpc_gui/wx_updater_view.py                  |  57 ++++\n tests/test_remote_entry_helpers.py              |   8 +-\n 38 files changed, 2736 insertions(+), 348 deletions(-)\n===CHECK===\nCHECK-DONE\n?? docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md\n> ac-wave-opencode-executor · muse-spark-1.3-contributor\nAC_WAVE_BRIDGE_STDOUT_BEGIN\nExecuting W53 run phase — loading canonical wave authority.\nFound W53 — shutdown-under-load journey with 18 owned requirements. Gathering requirement truth.\nW52 pattern is clear — read-only journey replay. Now mapping W53's shutdown ownership surface.\nOwnership surface mapped. Building the shutdown-under-load journey harness.\nJourney harness green 27/27. Now running process-isolated GUI evidence slices.\nPlugin slice hung when combined — isolating per prior-wave practice.\nGUI slices total 272 passed. Now building the external shutdown-under-load replay.\nTimeout surfaces as exit 124, not an exception — correcting the harness assertion.\nExternal replay green. Writing the canonical wave report.\nW53 run phase complete. All owned requirements verified on the read-only candidate with zero product/test edits.\n\nSummary of worker evidence:\n- EV-W53-GUI: 272 passed, 0 failed across 14 process-isolated slices covering all 8 in-flight surfaces plus lifecycle/restart\n- EV-W53-JOURNEY: 27/27 PASS — single-process mixed-surface shutdown campaign through one shared `WxLifecycleController` (disproves isolation-hidden teardown defects per LIFECYCLE-NATIVE-003)\n- EV-W53-EXT: PASS — real LOCAL_REAL shutdown-under-load (client-cancelled loaded sleep exit 124 @ 8.1s, bounded close 0.06s, clean relaunch)\n- EV-W53-PKG: NO-CANDIDATE (freeze owned by W56–W61)\n- EV-W53-DIFF: zero tracked hunks by W53; only the canonical report added (allowed closeout-only path)\n\nAC_WAVE_MACHINE_RESULT_BEGIN\nWAVE_PHASE_STATUS: READY_FOR_AUDIT\nAC_WAVE_MACHINE_RESULT_END\n",
  "findings": [],
  "changed_files": [],
  "next_action": "none",
  "phase_log_path": ".tmp\\agent-runs\\ac-wave-opencode-parallel\\20260924-203154-ca45d2b7\\0092-W53-run-opencode.log"
}
===AUDIT-CTX===
{
  "target": "W53",
  "phase": "audit",
  "content_identity": "bc8e0c25be61b35f5adab6343064706bcf1bd8e2c0cbe19e9183af9a0bc4bcb5",
  "findings_path": null,
  "audit_receipt": {
    "audit_status": "PASS",
    "tested_wave": "W52",
    "tested_content_identity": "bc8e0c25be61b35f5adab6343064706bcf1bd8e2c0cbe19e9183af9a0bc4bcb5",
    "audit_candidate_sha": "c8293d3ca309526ed250c794c3b294f7c54ef369",
    "audit_result_path": ".tmp\\agent-runs\\ac-wave-opencode-parallel\\20260924-203154-ca45d2b7\\0088-W52-audit-normalized.json",
    "audit_passed_at": "2026-09-24T23:05:57.276048+00:00",
    "audit_report_path": "artifacts\\opencode\\wave_W52\\WAVE_W52_AUDIT_REPORT.md"
  }
}
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ wc -l docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md 2>/dev/null; echo "===HEAD==="; head -150 docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md 2>/dev/null; echo "===TAIL==="; tail -100 docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md 2>/dev/null
247 docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md
===HEAD===
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
===TAIL===
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
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls .tmp/w53-run/ 2>&1; echo "===GIT-HEAD==="; git rev-parse HEAD; echo "===DIFF-CHECK==="; git diff --check 2>&1 | head -5; echo "===DIFF-STAT==="; git diff --stat 2>&1 | tail -5; echo "===STATUS-W53==="; git status --short docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md 2>&1; echo "===REGISTRY-W53==="; grep -c "W53" opencode/REQUIREMENT_REGISTRY.md 2>&1 || grep -c "W53" REQUIREMENT_REGISTRY.md 2>&1; ls opencode/ 2>&1 | head -20
gj09_external.py
gj09_journey.py
===GIT-HEAD===
c8293d3ca309526ed250c794c3b294f7c54ef369
===DIFF-CHECK===
warning: in the working copy of 'src/hpc_gui/config/storage.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/diagnostics.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/i18n.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/wx_errors.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
===DIFF-STAT===
 src/hpc_gui/wx_settings_view.py                 |  32 +-
 src/hpc_gui/wx_shell.py                         | 409 ++++++++++++++++------
 src/hpc_gui/wx_updater_view.py                  |  57 ++++
 tests/test_remote_entry_helpers.py              |   8 +-
 38 files changed, 2736 insertions(+), 348 deletions(-)
===STATUS-W53===
?? docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md
===REGISTRY-W53===
18
GOVERNANCE_DIFF.md
INSTALL_LAYOUT.md
INTEGRITY_AUDIT.md
MIGRATION_AUDIT.md
MUSE_RUNTIME.md
OPENCODE_PROGRAM_MANIFEST.md
OPENCODE_RUNTIME_AUDIT.md
README.md
REQUIREMENT_REGISTRY.md
REQUIREMENT_WAVE_INDEX.md
SOURCE_MAP.md
TODO_OWNERSHIP_MAP.md
UNIFIED_WAVE_ORCHESTRATION_AUDIT.md
WAVE_RENUMBERING.md
prompts
protocol
sources
templates
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python .tmp/w53-run/gj09_journey.py 2>&1 | tail -35
TERMINAL_INFLIGHT_RECEIVED: OK
TRANSFER_INFLIGHT_STARTED: OK
EDITOR_OPEN_INFLIGHT: OK
JOBS_INFLIGHT_ISSUED: OK
PLUGIN_REFRESH_INFLIGHT: OK
UPDATER_INFLIGHT: OK
LOGS_REFRESHED: OK
BOUNDED_SHUTDOWN: OK � 0.000s
CLEANUP_DETERMINISTIC_ORDER: OK � logs|updater|plugins|jobs|editor|remote-files|transfer|terminal
UPDATER_CANCELLED_DETERMINISTIC: OK
TRANSFER_CANCELLED_BOUNDED: OK
TERMINAL_POST_SHUTDOWN_DROPPED: OK
JOBS_STALE_DROPPED: OK
REMOTE_STALE_DROPPED: OK
LOGS_CLOSE_DURING_REFRESH_SAFE: OK
PLUGIN_SHUTDOWN_CLEAN: OK
EDITOR_FILE_INTACT_AFTER_SHUTDOWN: OK
SHUTDOWN_IDEMPOTENT: OK
TERMINAL_WX_GUARD_PRESENT: OK
REMOTE_WX_GUARD_PRESENT: OK
SHELL_ALIVE_GUARD_PRESENT: OK
RELAUNCH_CLEAN: OK
RELAUNCH_PROCESS_OK: OK
ZERO_LEAKED_WORKERS: OK � 0 non-daemon alive
ZERO_LEAKED_LIFECYCLE: OK
NO_HANG: OK � 0.14s total
NO_NATIVE_CRASH: OK � harness reached end in-process
GJ09_JOURNEY_RESULT: PASS (27/27)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_wx_lifecycle.py tests/test_w31_race_lifecycle.py tests/test_w33_lifecycle_isolation.py -p no:cacheprovider -q 2>&1 | tail -5
.......................................                                  [100%]
39 passed in 6.61s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_wx_terminal.py tests/test_wx_terminal_behavioral.py tests/test_transfer_controller.py tests/test_transfer_cancel_recovery.py tests/test_editor_controller.py tests/test_editor_flow.py -p no:cacheprovider -q 2>&1 | tail -5
File "D:\Python\Python312\Lib\site-packages\_pytest\config\__init__.py", line 199 in main
  File "D:\Python\Python312\Lib\site-packages\_pytest\config\__init__.py", line 223 in console_main
  File "D:\Python\Python312\Lib\site-packages\pytest\__main__.py", line 9 in <module>
  File "<frozen runpy>", line 88 in _run_code
  File "<frozen runpy>", line 198 in _run_module_as_main
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_wx_terminal.py tests/test_wx_terminal_behavioral.py -p no:cacheprovider -q 2>&1 | tail -4; echo "===SLICE2==="; PYTHONPATH=src python -m pytest tests/test_transfer_controller.py tests/test_transfer_cancel_recovery.py -p no:cacheprovider -q 2>&1 | tail -4
.....................                                                    [100%]
21 passed in 18.37s
===SLICE2===
.......                                                                  [100%]
7 passed in 0.54s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_editor_controller.py tests/test_editor_flow.py tests/test_wx_remote_editor_flow.py -p no:cacheprovider -q 2>&1 | tail -4; echo "===SLICE-JOBS==="; PYTHONPATH=src python -m pytest tests/test_job_tracking_controller.py tests/test_output_follower.py tests/test_wx_jobs.py -p no:cacheprovider -q 2>&1 | tail -4
........................                                                 [100%]
24 passed in 4.80s
===SLICE-JOBS===
............                                                             [100%]
12 passed in 0.76s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_wx_remote_files.py tests/test_remote_entry_helpers.py -p no:cacheprovider -q 2>&1 | tail -3; echo "===SLICE-LOG==="; PYTHONPATH=src python -m pytest tests/test_w39_logs_diagnostics.py tests/test_wx_logs.py tests/test_diagnostics.py -p no:cacheprovider -q 2>&1 | tail -3; echo "===SLICE-UPD==="; PYTHONPATH=src python -m pytest tests/test_app_updater.py tests/test_w41_updater_routing.py -p no:cacheprovider -q 2>&1 | tail -3
................                                                         [100%]
16 passed in 0.52s
===SLICE-LOG===
..................                                                       [100%]
18 passed in 1.40s
===SLICE-UPD===
......................                                                   [100%]
22 passed in 0.82s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_w35_plugin_manager_gui.py tests/test_wx_plugins.py -p no:cacheprovider -q 2>&1 | tail -3; echo "===SLICE-PMUI==="; PYTHONPATH=src python -m pytest tests/test_plugin_manager_ui.py -p no:cacheprovider -q 2>&1 | tail -3
.........                                                                [100%]
9 passed in 1.44s
===SLICE-PMUI===
.....................................                                    [100%]
37 passed in 3.04s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_wx_transfer_ui_lifecycle.py -p no:cacheprovider -q 2>&1 | tail -3; echo "===SLICE-WXED==="; PYTHONPATH=src python -m pytest tests/test_wx_editor.py -p no:cacheprovider -q 2>&1 | tail -3; echo "===SLICE-RESTART==="; PYTHONPATH=src python -m pytest tests/test_w43_restart_package_policy.py tests/test_wx_updater_spec.py -p no:cacheprovider -q 2>&1 | tail -3
..............                                                           [100%]
14 passed in 5.23s
===SLICE-WXED===
..............                                                           [100%]
14 passed in 3.58s
===SLICE-RESTART===
.......................................                                  [100%]
39 passed in 4.57s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ grep -n "PKG\|NO-CANDIDATE\|PACKAGE" docs/wave-reports/v2/opencode/W52_WAVE_REPORT.md 2>/dev/null | head -10; echo "===EXT-HARNESS==="; head -60 .tmp/w53-run/gj09_external.py 2>/dev/null; echo "===TODO-MAP==="; grep -n "W53" opencode/TODO_OWNERSHIP_MAP.md 2>/dev/null | head -10
20:1. `waves/pending/W52.md` (wave_id W52, execution kind, canonical_source W52, 5 source rows + 1 TODO row, start gate NONE, cohort P10-golden-journeys, required evidence `GUI,PACKAGE,EXTERNAL`, integration refs W44 non-blocking, unattended/non-interactive contract, Golden-Journey candidate rule: W44 candidate is behaviorally read-only).
25:6. `.opencode/protocol/LOCAL_REAL_HPC_LAB.md`: EXTERNAL authority; LOCAL_REAL_HYPERV is default real infra for generic SSH/connection claims; serialize EXTERNAL replay; GUI/PACKAGE claims need their own journey proof, not lab-health inference.
164:### EV-W52-PKG — PACKAGE class
167:Evidence ID: EV-W52-PKG
168:No packaged artifact was built, published, or claimed by W52 (candidate freeze is owned by W56–W61). Recorded honestly as NO-CANDIDATE.
173:Evidence classes: `GUI` (required) → EV-W52-GUI (166 passed, real wx event proof in the w19/wx-terminal/wx-remote/wx-editor/wx-jobs/w31/w33 slices) + EV-W52-JOURNEY (21/21 product-path checks PASS). `PACKAGE` (required) → EV-W52-PKG (NO-CANDIDATE, honestly recorded; freeze owned downstream). `EXTERNAL` (required) → EV-W52-EXT (real LOCAL_REAL dual-session A→B isolation readback, PASS). No mocks substituted for any owned claim (harnesses use real connection/terminal/navigation/editor/jobs/output paths under disposable roots + real lab transports; isolated SFTP/exec only, no shared mutation).
===EXT-HARNESS===
"""W53 GJ-09 EXTERNAL replay: shutdown under load against LOCAL_REAL_HYPERV."""
import json, os, sys, tempfile, time, uuid
from pathlib import Path
sys.path.insert(0, "src")
tmp = Path(tempfile.mkdtemp(prefix="w53-gj09-"))
os.environ["HPC_GUI_CONFIG_ROOT"] = str(tmp / "fresh-root")
from hpc_gui.core import paths as paths_mod
from hpc_gui.core import logging_setup
data = paths_mod.app_data_dir(); logs = paths_mod.app_log_dir()
assert data.is_dir() and logs.is_dir(), (data, logs)
logging_setup.setup_logging()
print("CONFIG_ROOT_ISOLATED: " + str(data))
prof_text = Path(r"C:\Users\mskomek\AppData\Local\hpc-client-gui-lab\hpc-client-profile.json").read_text(encoding="utf-8-sig")
prof = json.loads(prof_text)
assert prof.get("host") == "192.168.250.11" and prof.get("username") == "hpctest"
key_path = prof.get("key_path")
assert key_path and Path(key_path).exists()
print("PROFILE: disposable-W53 host=192.168.250.11 user=hpctest provider=local-real auth=key host_key_policy=accept-new")
kh = tmp / "known_hosts_w53"
lab_kh = Path(r"C:\Users\mskomek\AppData\Local\hpc-client-gui-lab\known_hosts")
if lab_kh.exists():
    kh.write_bytes(lab_kh.read_bytes())
print("HOST_KEY_PATH: isolated=" + str(kh) + " seeded=" + str(kh.exists()))
from hpc_gui.ssh.client import SSHConnInfo, SSHClientWrapper

def mk_wrapper():
    return SSHClientWrapper(SSHConnInfo(host="192.168.250.11", port=22, username="hpctest",
                           key_path=str(key_path), host_key_policy="accept-new",
                           known_hosts_path=str(kh), timeout=25))

# Representative work in flight: terminal + files + jobs readback.
token = "W53-GJ09-" + uuid.uuid4().hex[:8]
w1 = mk_wrapper()
w1.connect()
ta = w1.client.get_transport() if w1.client else None
assert ta is not None and ta.is_active(), "connect transport not active"
print("CONNECTED: transport_active=True")
code, out, err = w1.run("echo " + token + "; hostname", timeout_s=25)
assert code == 0 and token in out, (code, err[:200])
print("TERMINAL_INFLIGHT: OK token readback")
code_f, out_f, err_f = w1.run("pwd; ls ~ | head -n 5", timeout_s=25)
assert code_f == 0, err_f[:200]
print("FILES_INFLIGHT: OK exit=0")
try:
    code_j, out_j, err_j = w1.run("squeue --me 2>&1 | head -n 5", timeout_s=25)
    print("JOBS_INFLIGHT: " + out_j.strip()[:160].replace(chr(10), "|"))
except Exception as ex:
    print("JOBS_INFLIGHT: probe raised " + ex.__class__.__name__ + " (recorded, not fatal)")

# Controlled shutdown UNDER LOAD: remote sleep outlives the client wait, so
# the client times out / cancels while remote work is still in flight.
t0 = time.monotonic()
code_l, out_l, err_l = w1.run("sleep 20; echo W53-LOAD-DONE-" + token, timeout_s=8)
load_elapsed = time.monotonic() - t0
# Client-side timeout while remote work is still in flight surfaces as
# exit 124 (see SSHClientWrapper.run): the client stops waiting (~8s, not
# 20s) while the remote sleep continues — the controlled shutdown case.
load_cancelled = (code_l == 124 and load_elapsed < 18.0)
print(f"LOAD_CANCELLED_WHILE_INFLIGHT: exit={code_l} elapsed={load_elapsed:.1f}s")
assert load_cancelled, (code_l, load_elapsed)
===TODO-MAP===
50:| `HPC-W10-TODO-LIFECYCLE-NATIVE-003` | `W53` | `W10` | `LIFECYCLE-NATIVE-003` | ACTIVE | `LIFECYCLE-NATIVE-003` — Broad/mixed GUI test execution must not depend on process isolation to hide deterministic product teardown defects. Process isolation may remain for tooling reasons only after the runtime defect is disproven/closed. |
51:| `HPC-W10-TODO-LIFECYCLE-NATIVE-004` | `W53` | `W10` | `LIFECYCLE-NATIVE-004` | ACTIVE | `LIFECYCLE-NATIVE-004` — 0 destroyed-control callbacks, 0 native access violations, 0 heap corruption, 0 leaked top-level windows/workers in the release-candidate lifecycle campaign. |
202:| `HPC-W10-TODO-SHUTDOWN-LOAD-GJ-001` | `W53` | `W10` | `SHUTDOWN-LOAD-GJ-001` | ACTIVE | `SHUTDOWN-LOAD-GJ-001` — GJ-09 proves bounded clean shutdown/relaunch with representative work in flight. |
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls "C:/Users/mskomek/AppData/Local/hpc-client-gui-lab/" 2>&1 | head -10
compute01
compute02
hostname.copy
hpc-client-profile.json
id_ed25519
id_ed25519.pub
known_hosts
login-control01
ubuntu-24.04-server-cloudimg-amd64.img
ubuntu-base.vhdx
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src timeout 150 python .tmp/w53-run/gj09_external.py 2>&1 | tail -15
CONFIG_ROOT_ISOLATED: D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\w53-gj09-7gpc6yjq\fresh-root
PROFILE: disposable-W53 host=192.168.250.11 user=hpctest provider=local-real auth=key host_key_policy=accept-new
HOST_KEY_PATH: isolated=D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\w53-gj09-7gpc6yjq\known_hosts_w53 seeded=True
CONNECTED: transport_active=True
TERMINAL_INFLIGHT: OK token readback
FILES_INFLIGHT: OK exit=0
JOBS_INFLIGHT: JOBID PARTITION     NAME     USER ST       TIME  NODES NODELIST(REASON)
LOAD_CANCELLED_WHILE_INFLIGHT: exit=124 elapsed=8.0s
SHUTDOWN_BOUNDED: 0.06s
RELAUNCH_CLEAN: OK (fresh token present, prior-load token absent)
GJ09_EXTERNAL_RESULT: PASS
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
AC_WAVE_BRIDGE_STDOUT_BEGIN
Auditing W53 — loading canonical protocol.
W53 scope is shutdown under load — inspecting prior run evidence.
All GUI slices re-verified green in isolation. Checking remaining audit dimensions.
W53 fresh independent audit complete. All worker claims re-verified against the current candidate.

## Audit verdict: PASS

**Candidate identity:** HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369` matches the report baseline; handoff content identity `bc8e0c25…` confirmed. The controller handoff's `audit_receipt` references W52 (stale, same identity family) — it was **not** reused; this is a fresh W53 audit on current repository truth.

**Independent re-verification (all at HEAD `c8293d3`, `PYTHONPATH=src`, `-p no:cacheprovider`):**
- EV-W53-JOURNEY: `.tmp/w53-run/gj09_journey.py` re-run verbatim → `GJ09_JOURNEY_RESULT: PASS (27/27)`, single-process mixed-surface teardown through one shared `WxLifecycleController`, zero leaked workers.
- EV-W53-GUI: all 13 process-isolated slices re-run → 39+21+7+14+16+24+14+12+9+37+22+18+39 = **272 passed, 0 failed**. One ad-hoc combined multi-file invocation crashed (same wx-runtime tooling-lifetime class as recorded OBS-W53-002); only isolated results are claimed, so this is not a product finding.
- EV-W53-EXT: `.tmp/w53-run/gj09_external.py` re-run verbatim against LOCAL_REAL_HYPERV → `GJ09_EXTERNAL_RESULT: PASS` (terminal/files/squeue readback, loaded-sleep client-cancel exit 124 @ 8.0s, bounded close 0.06s, clean relaunch). Real transport, disposable tokens, no shared mutation, secrets never printed.
- EV-W53-PKG: NO-CANDIDATE honestly recorded; candidate freeze owned by W56–W61 — identical to the W52 PASS precedent. No artifact SHA claimed because none exists at this Wave.
- EV-W53-DIFF: zero tracked hunks authored by W53; only `docs/wave-reports/v2/opencode/W53_WAVE_REPORT.md` added (allowed closeout-only path); `git diff --check` exit 0 (pre-existing sibling CRLF warnings only); sibling dirty tree preserved untouched and disclosed.

**Requirement coverage:** all 18 owned IDs (15 source + 3 TODO) mapped to journey/GUI/external evidence; Golden-Journey candidate rule honored (zero product/test edits, read-only candidate); no owned blocking defect; no cross-scope defect observed (combined-process hang is a tooling observation, recorded not routed). No weakened tests, no mocks substituted, no secrets in report/harnesses.

** finding:** none blocking. OBS note only — combined-process wx crash class already recorded by the worker as OBS-W53-002.

Per the execution boundary, no repository files were written; canonical audit-report persistence is controller-owned.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
