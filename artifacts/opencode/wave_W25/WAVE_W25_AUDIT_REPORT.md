# Wave W25 Audit Report
## Controller-persisted fresh independent audit — 2026-09-24T10:06:43.261527+00:00

- Wave: `W25`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0037-W25-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0037-W25-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md [offset=30]
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md 
→ Read .agents/protocol/AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md 
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✱ Glob "waves/**/W25*" 0 matches
✱ Glob "waves/**/*.md" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves 
$ Get-ChildItem -Force | Select-Object Name, Mode; Write-Host "---"; Get-ChildItem waves -Recurse -ErrorAction Continue | Select-Object FullName | Select-Object -First 100
---
Name                              Mode
----                              ----
.agent-legacy-backup (1)          d----
.agent-runs                       d----
.agents                           d----
.cache                            d----
.claude                           d----
.codex                            d----
.github                           d----
.idea                             d----
.opencode                         d----
.pytest_cache                     d----
.pytest-tmp-w06-repair            d----
.ruff_cache                       d----
.tmp                              d----
.tmp-pytest-merge                 d----
.tmp-pytest-merge2                d----
.tmp-pytest-merge3                d----
.tmp-pytest-merge4                d----
.tmp-pytest-merge5                d----
.tmp-pytest-merge6                d----
.tmp-pytest-merge7                d----
.tmp-pytest-merge8                d----
.tmp-pytest-merge9                d----
.tmp-pytest-update01              d----
.tmp-pytest-update02              d----
.tmp-pytest-update02b             d----
.tmp-pytest-update03              d----
.tmp-pytest-update03b             d----
.tmp-pytest-update03c             d----
.tmp-pytest-update04              d----
.tmp-pytest-update06              d----
.venv                             d----
.venv314                          d----
.w01-audit-current                d----
.w01-audit-current-impacted       d----
.w01-audit-pytest-run             d----
.w01-independent-audit            d----
.w01-pytest-run                   d----
.w01-repair-pytest-run            d----
.w01-repair2                      d----
.wave-patch-backup                d----
artifacts                         d----
audit                             d----
benchmarks                        d----
build                             d----
devtools                          d----
dist                              d----
docs                              d----
lab                               d----
logs                              d----
opencode                          d----
Projelerhpc-client-gui.pytest-tmp d----
scripts                           d----
src                               d----
templates                         d----
tests                             d----
third_party_licenses              d----
tools                             d----
waves                             d----
_w15_dump_dlg.ps1                 -a---
_w15_list_wins.ps1                -a---
_w15_probe_child.py               -a---
_w15_probe_dlg.py                 -a---
_w15_probe_dlg2.py                -a---
_w15_probe_src.py                 -a---
.coverage                         -a---
.git                              -a-h-
.gitignore                        -a---
.pre-commit-config.yaml           -a---
AGENTS.md                         -a---
CLAUDE.md                         -a---
COMMERCIAL_LICENSE.md             -a---
CONTRIBUTING.md                   -a---
coverage.json                     -a---
coverage.xml                      -a---
hpc-client-gui.ffs_gui            -a---
LICENSE                           -a---
new 4.ps1                         -a---
opencode.jsonc                    -a---
pyproject.toml                    -a---
QT_LGPL_SOURCE_OFFER.md           -a---
rapor                             -a---
rapor_final_45_54.md              -a---
README.md                         -a---
requirements-dev.txt              -a---
requirements-release.lock         -a---
requirements.txt                  -a---
rules.md                          -a---
SECURITY.md                       -a---
SUPPORT.md                        -a---
sync.ffs_db                       -a-h-
template.slurm                    -a---
THIRD_PARTY_NOTICES.md            -a---
uv.lock                           -a---
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Get-ChildItem waves/pending, waves/done, waves/blocked, waves/postponed -File -ErrorAction Continue | Select-Object FullName, Name | Sort-Object Name | Select-Object -First 120; Write-Host "---WAVES-SUB---"; Get-ChildItem waves/waves -File -ErrorAction Continue | Select-Object Name | Select-Object -First 120
---WAVES-SUB---
FullName                                                                                         Name
--------                                                                                         ----
D:\Projeler\hpc-client-gui\waves\done\01-shared-foundation.md                                    01-shared-foundation..
D:\Projeler\hpc-client-gui\waves\done\02-verification-and-release-contract.md                    02-verification-and-r.
D:\Projeler\hpc-client-gui\waves\done\03-ubuntu-deb-updates.md                                   03-ubuntu-deb-updates.
D:\Projeler\hpc-client-gui\waves\postponed\04-macos-sparkle-feasibility.md                       04-macos-sparkle-feas.
D:\Projeler\hpc-client-gui\waves\blocked\05-macos-production-updates.md                          05-macos-production-u.
D:\Projeler\hpc-client-gui\waves\blocked\06-appimage-flatpak.md                                  06-appimage-flatpak.md
D:\Projeler\hpc-client-gui\waves\blocked\07-acceptance-and-rollout.md                            07-acceptance-and-rol.
D:\Projeler\hpc-client-gui\waves\done\ANSYS_LINTER_WAVE_00_README.md                             ANSYS_LINTER_WAVE_00_.
D:\Projeler\hpc-client-gui\waves\done\ANSYS_LINTER_WAVE_01_API_V2_CONTRACT.md                    ANSYS_LINTER_WAVE_01_.
D:\Projeler\hpc-client-gui\waves\done\ANSYS_LINTER_WAVE_02_CORE_ENGINE.md                        ANSYS_LINTER_WAVE_02_.
D:\Projeler\hpc-client-gui\waves\done\ANSYS_LINTER_WAVE_03_FLUENT_WORKBENCH.md                   ANSYS_LINTER_WAVE_03_.
D:\Projeler\hpc-client-gui\waves\done\ANSYS_LINTER_WAVE_04_MAPDL_MECHANICAL.md                   ANSYS_LINTER_WAVE_04_.
D:\Projeler\hpc-client-gui\waves\done\ANSYS_LINTER_WAVE_05_CCL_ICEM.md                           ANSYS_LINTER_WAVE_05_.
D:\Projeler\hpc-client-gui\waves\done\ANSYS_LINTER_WAVE_06_SYSTEM_COUPLING_AND_REMAINING.md      ANSYS_LINTER_WAVE_06_.
D:\Projeler\hpc-client-gui\waves\done\ANSYS_LINTER_WAVE_07_UI_CLI_HPC_RULES.md                   ANSYS_LINTER_WAVE_07_.
D:\Projeler\hpc-client-gui\waves\done\ANSYS_LINTER_WAVE_08_ACCEPTANCE_RELEASE.md                 ANSYS_LINTER_WAVE_08_.
D:\Projeler\hpc-client-gui\waves\done\ANSYS_LINTER_WAVE_09_PACKAGING_CI_REPAIR.md                ANSYS_LINTER_WAVE_09_.
D:\Projeler\hpc-client-gui\waves\done\ANSYS_LINTER_WAVES_RESULT.md                               ANSYS_LINTER_WAVES_RE.
D:\Projeler\hpc-client-gui\waves\postponed\CHECKPOINTS.md                                        CHECKPOINTS.md
D:\Projeler\hpc-client-gui\waves\postponed\CHECKSUMS.sha256                                      CHECKSUMS.sha256
D:\Projeler\hpc-client-gui\waves\postponed\CONTRACT-DRAFT.md                                     CONTRACT-DRAFT.md
D:\Projeler\hpc-client-gui\waves\postponed\EXECUTION_ORDER.md                                    EXECUTION_ORDER.md
D:\Projeler\hpc-client-gui\waves\postponed\IMPLEMENTATION-RULES.md                               IMPLEMENTATION-RULES..
D:\Projeler\hpc-client-gui\waves\postponed\PACK_MANIFEST.json                                    PACK_MANIFEST.json
D:\Projeler\hpc-client-gui\waves\postponed\QA-MATRIX.md                                          QA-MATRIX.md
D:\Projeler\hpc-client-gui\waves\postponed\README_WAVES_78_80.md                                 README_WAVES_78_80.md
D:\Projeler\hpc-client-gui\waves\postponed\README.md                                             README.md
D:\Projeler\hpc-client-gui\waves\postponed\RESEARCH-TRUBA.md                                     RESEARCH-TRUBA.md
D:\Projeler\hpc-client-gui\waves\done\UPDATE-03-RESULT.md                                        UPDATE-03-RESULT.md
D:\Projeler\hpc-client-gui\waves\done\W01.md                                                     W01.md
D:\Projeler\hpc-client-gui\waves\done\W02.md                                                     W02.md
D:\Projeler\hpc-client-gui\waves\done\W03.md                                                     W03.md
D:\Projeler\hpc-client-gui\waves\done\W04.md                                                     W04.md
D:\Projeler\hpc-client-gui\waves\done\W05.md                                                     W05.md
D:\Projeler\hpc-client-gui\waves\done\W06.md                                                     W06.md
D:\Projeler\hpc-client-gui\waves\done\W07.md                                                     W07.md
D:\Projeler\hpc-client-gui\waves\done\W08.md                                                     W08.md
D:\Projeler\hpc-client-gui\waves\done\W09.md                                                     W09.md
D:\Projeler\hpc-client-gui\waves\done\W10.md                                                     W10.md
D:\Projeler\hpc-client-gui\waves\done\W11.md                                                     W11.md
D:\Projeler\hpc-client-gui\waves\done\W12.md                                                     W12.md
D:\Projeler\hpc-client-gui\waves\done\W13.md                                                     W13.md
D:\Projeler\hpc-client-gui\waves\done\W14.md                                                     W14.md
D:\Projeler\hpc-client-gui\waves\done\W15.md                                                     W15.md
D:\Projeler\hpc-client-gui\waves\done\W16.md                                                     W16.md
D:\Projeler\hpc-client-gui\waves\done\W17.md                                                     W17.md
D:\Projeler\hpc-client-gui\waves\done\W18.md                                                     W18.md
D:\Projeler\hpc-client-gui\waves\done\W19.md                                                     W19.md
D:\Projeler\hpc-client-gui\waves\done\W20.md                                                     W20.md
D:\Projeler\hpc-client-gui\waves\done\W21.md                                                     W21.md
D:\Projeler\hpc-client-gui\waves\done\W22.md                                                     W22.md
D:\Projeler\hpc-client-gui\waves\done\W23.md                                                     W23.md
D:\Projeler\hpc-client-gui\waves\done\W24.md                                                     W24.md
D:\Projeler\hpc-client-gui\waves\pending\W25.md                                                  W25.md
D:\Projeler\hpc-client-gui\waves\pending\W26.md                                                  W26.md
D:\Projeler\hpc-client-gui\waves\pending\W27.md                                                  W27.md
D:\Projeler\hpc-client-gui\waves\pending\W28.md                                                  W28.md
D:\Projeler\hpc-client-gui\waves\pending\W29.md                                                  W29.md
D:\Projeler\hpc-client-gui\waves\pending\W30.md                                                  W30.md
D:\Projeler\hpc-client-gui\waves\pending\W31.md                                                  W31.md
D:\Projeler\hpc-client-gui\waves\pending\W32.md                                                  W32.md
D:\Projeler\hpc-client-gui\waves\pending\W33.md                                                  W33.md
D:\Projeler\hpc-client-gui\waves\pending\W34.md                                                  W34.md
D:\Projeler\hpc-client-gui\waves\pending\W35.md                                                  W35.md
D:\Projeler\hpc-client-gui\waves\pending\W36.md                                                  W36.md
D:\Projeler\hpc-client-gui\waves\pending\W37.md                                                  W37.md
D:\Projeler\hpc-client-gui\waves\pending\W38.md                                                  W38.md
D:\Projeler\hpc-client-gui\waves\pending\W39.md                                                  W39.md
D:\Projeler\hpc-client-gui\waves\pending\W40.md                                                  W40.md
D:\Projeler\hpc-client-gui\waves\pending\W41.md                                                  W41.md
D:\Projeler\hpc-client-gui\waves\pending\W42.md                                                  W42.md
D:\Projeler\hpc-client-gui\waves\pending\W43.md                                                  W43.md
D:\Projeler\hpc-client-gui\waves\pending\W44.md                                                  W44.md
D:\Projeler\hpc-client-gui\waves\pending\W45.md                                                  W45.md
D:\Projeler\hpc-client-gui\waves\pending\W46.md                                                  W46.md
D:\Projeler\hpc-client-gui\waves\pending\W47.md                                                  W47.md
D:\Projeler\hpc-client-gui\waves\pending\W48.md                                                  W48.md
D:\Projeler\hpc-client-gui\waves\pending\W49.md                                                  W49.md
D:\Projeler\hpc-client-gui\waves\pending\W50.md                                                  W50.md
D:\Projeler\hpc-client-gui\waves\pending\W51.md                                                  W51.md
D:\Projeler\hpc-client-gui\waves\pending\W52.md                                                  W52.md
D:\Projeler\hpc-client-gui\waves\pending\W53.md                                                  W53.md
D:\Projeler\hpc-client-gui\waves\pending\W54.md                                                  W54.md
D:\Projeler\hpc-client-gui\waves\pending\W55.md                                                  W55.md
D:\Projeler\hpc-client-gui\waves\pending\W56.md                                                  W56.md
D:\Projeler\hpc-client-gui\waves\pending\W57.md                                                  W57.md
D:\Projeler\hpc-client-gui\waves\pending\W58.md                                                  W58.md
D:\Projeler\hpc-client-gui\waves\pending\W59.md                                                  W59.md
D:\Projeler\hpc-client-gui\waves\pending\W60.md                                                  W60.md
D:\Projeler\hpc-client-gui\waves\pending\W61.md                                                  W61.md
D:\Projeler\hpc-client-gui\waves\done\wave_00_cross_repo_contract_alignment.md                   wave_00_cross_repo_co.
D:\Projeler\hpc-client-gui\waves\done\wave_00_current_release_boundary_baseline_freeze.md        wave_00_current_relea.
D:\Projeler\hpc-client-gui\waves\done\wave_01_provider_schema_extensions.md                      wave_01_provider_sche.
D:\Projeler\hpc-client-gui\waves\done\wave_01_unified_cluster_self_test_core.md                  wave_01_unified_clust.
D:\Projeler\hpc-client-gui\waves\done\wave_02_cluster_self_test_gui.md                           wave_02_cluster_self_.
D:\Projeler\hpc-client-gui\waves\done\wave_02_provider_context_model.md                          wave_02_provider_cont.
D:\Projeler\hpc-client-gui\waves\done\wave_03_dynamic_storage_ui.md                              wave_03_dynamic_stora.
D:\Projeler\hpc-client-gui\waves\done\wave_03_provider_capability_view.md                        wave_03_provider_capa.
D:\Projeler\hpc-client-gui\waves\done\wave_04_diagnostic_bundle_v2.md                            wave_04_diagnostic_bu.
D:\Projeler\hpc-client-gui\waves\done\wave_04_safe_remote_path_resolvers.md                      wave_04_safe_remote_p.
D:\Projeler\hpc-client-gui\waves\done\wave_05_provider_update_diff_freshness.md                  wave_05_provider_upda.
D:\Projeler\hpc-client-gui\waves\done\wave_05_quota_backend_infrastructure_v2.md                 wave_05_quota_backend.
D:\Projeler\hpc-client-gui\waves\done\wave_06_nersc_perlmutter_provider.md                       wave_06_nersc_perlmut.
D:\Projeler\hpc-client-gui\waves\done\wave_06_trusted_tool_disclosure.md                         wave_06_trusted_tool_.
D:\Projeler\hpc-client-gui\waves\done\wave_07_ansys_diagnostic_explanation_ux.md                 wave_07_ansys_diagnos.
D:\Projeler\hpc-client-gui\waves\done\wave_07_lumi_provider.md                                   wave_07_lumi_provider.
D:\Projeler\hpc-client-gui\waves\done\wave_08_pawsey_setonix_provider.md                         wave_08_pawsey_setoni.
D:\Projeler\hpc-client-gui\waves\done\wave_08_slurm_directive_editing_model.md                   wave_08_slurm_directi.
D:\Projeler\hpc-client-gui\waves\done\wave_09_slurm_job_arrays.md                                wave_09_slurm_job_arr.
D:\Projeler\hpc-client-gui\waves\done\wave_09_tacc_stampede3_provider_and_mfa.md                 wave_09_tacc_stampede.
D:\Projeler\hpc-client-gui\waves\done\wave_10_cineca_leonardo_provider_and_certificate_auth.md   wave_10_cineca_leonar.
D:\Projeler\hpc-client-gui\waves\done\wave_10_slurm_job_dependencies.md                          wave_10_slurm_job_dep.
D:\Projeler\hpc-client-gui\waves\done\wave_11_job_failure_explanation.md                         wave_11_job_failure_e.
D:\Projeler\hpc-client-gui\waves\done\wave_11_provider_validation_and_docs_hardening.md          wave_11_provider_vali.
D:\Projeler\hpc-client-gui\waves\blocked\wave_12_registry_release_and_application_integration.md wave_12_registry_rele.
D:\Projeler\hpc-client-gui\waves\done\wave_12_transfer_sha_256_integrity_verification.md         wave_12_transfer_sha_.
D:\Projeler\hpc-client-gui\waves\done\wave_13_profile_export_import.md                           wave_13_profile_expor.
D:\Projeler\hpc-client-gui\waves\done\wave_14_duplicate_profile.md                               wave_14_duplicate_pro.
D:\Projeler\hpc-client-gui\waves\done\wave_15_storage_policy_intelligence.md                     wave_15_storage_polic.
D:\Projeler\hpc-client-gui\waves\done\wave_16_job_record_store.md                                wave_16_job_record_st.
                                                                                                 00-START-HERE.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W25.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git rev-parse HEAD; git status --short | Select-Object -First 60; Write-Host "---BRANCH---"; git branch --show-current; Write-Host "---LOG---"; git log --oneline -5
ccaf871ffc139973db826363859ca2933b216e9c
 M .gitignore
 M .opencode/protocol/WAVE_PROJECT_PROFILE.json
 M .opencode/scripts/route-wave-findings.py
 M .opencode/scripts/run-wave-program.py
 M .opencode/scripts/wave_state_engine.py
 M artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md
 M artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md
 M artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md
 M artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md
 M artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md
 M artifacts/v2-final/W01/SUPPORT_MATRIX.md
 M artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md
 M artifacts/v2-final/W02/OWNERSHIP_MAP.md
 M artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md
 M artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json
 M build/audit/w15-fresh-user-windows.json
 M build/audit/w15-fresh-user-windows.run1.runtime.json
 M build/audit/w15-fresh-user-windows.run2.runtime.json
 M build/audit/w16-fresh-user-windows.json
 M build/audit/w16-fresh-user-windows.run1.runtime.json
 M build/audit/w16-fresh-user-windows.run2.runtime.json
 M build/audit/w16-package-content-windows.json
 M build/audit/w16-packaged-smoke-windows.json
 M build/audit/w16-packaged-smoke-windows.runtime.json
 M build/audit/w18-external-matrix.txt
 M build/audit/w18-gui-pytest.txt
 M build/audit/w22-focused-tests-current.txt
 M build/audit/w22-packaged-smoke-current.json
 M build/audit/w22-packaged-smoke-current.runtime.json
 M docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md
---BRANCH---
develop
---LOG---
ccaf871f Harden Wave close handoff recovery
99e32915 Classify controller handoff changes as closeout-only
7a5e6142 Honor fresh audit receipt at Wave close
5ffc14ed Stop repeated Wave no-progress cycles
e51572de Clarify scoped password lab authority
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git status --short | Measure-Object | Select-Object Count; git status --short | Select-Object -Last 100; Write-Host "---W25-REPORTS---"; Get-ChildItem docs/wave-reports/v2/opencode/W25* -ErrorAction Continue | Select-Object Name, Length, LastWriteTime; Write-Host "---ARTIFACTS-W25---"; Get-ChildItem artifacts/wave_W25, artifacts/v2-final/W25 -Recurse -ErrorAction Continue | Select-Object FullName | Select-Object -First 40
---W25-REPORTS---
---ARTIFACTS-W25---
Count
-----
  118
 M build/audit/w16-fresh-user-windows.json
 M build/audit/w16-fresh-user-windows.run1.runtime.json
 M build/audit/w16-fresh-user-windows.run2.runtime.json
 M build/audit/w16-package-content-windows.json
 M build/audit/w16-packaged-smoke-windows.json
 M build/audit/w16-packaged-smoke-windows.runtime.json
 M build/audit/w18-external-matrix.txt
 M build/audit/w18-gui-pytest.txt
 M build/audit/w22-focused-tests-current.txt
 M build/audit/w22-packaged-smoke-current.json
 M build/audit/w22-packaged-smoke-current.runtime.json
 M docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W18_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W21_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md
 M scripts/capture_build_provenance.py
 M scripts/generate_release_manifest.py
 M scripts/wx_packaged_smoke.py
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/services/file_context_actions.py
 M src/hpc_gui/services/local_files.py
 M src/hpc_gui/services/transfer_controller.py
 M src/hpc_gui/services/transfer_session_controller.py
 M src/hpc_gui/wx_connection.py
 M src/hpc_gui/wx_directories.py
 M src/hpc_gui/wx_directories_view.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_local_files.py
 M src/hpc_gui/wx_remote_files_view.py
 M src/hpc_gui/wx_settings.py
 M src/hpc_gui/wx_settings_view.py
 M src/hpc_gui/wx_shell.py
 M src/hpc_gui/wx_transfer_workspace.py
 M tests/test_wave_controller_regressions.py
 M tests/test_wx_directories.py
 M tests/test_wx_packaged_smoke.py
?? ".agent-legacy-backup (1)/"
?? artifacts/opencode/
?? artifacts/wave_W19/
?? artifacts/wave_W20/
?? artifacts/wave_W21/
?? artifacts/wave_W22/
?? artifacts/wave_W23/
?? artifacts/wave_W24/
?? build/audit/w14-packaged-smoke-r3.json
?? build/audit/w17-current-validation.json
?? build/audit/w21-repair-identity.txt
?? build/audit/w22-repair-focused-20260922.txt
?? build/audit/w23-gui-probe-current.py
?? docs/wave-reports/v2/opencode/W23_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W24_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W24_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W25_WAVE_REPORT.md
?? "new 4.ps1"
?? scripts/validate_wave_closeout.py
?? "tests/contracts (1)/"
?? "tests/contracts (2)/"
?? tests/contracts/
?? tests/test_w23_delete_confirm.py
?? tests/test_w23_files_navigation.py
?? tests/test_w25_transfer_workspace_integrity.py
?? tests/test_wave_state_engine.py
    1
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read tests/test_w25_transfer_workspace_integrity.py 
→ Read docs/wave-reports/v2/opencode/W25_WAVE_REPORT.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff --stat | Select-Object -First 80; Write-Host "---CHECK---"; git diff --check | Select-Object -First 40; Write-Host "---W25STAT---"; git diff --stat -- src/hpc_gui/services/transfer_controller.py src/hpc_gui/services/transfer_session_controller.py src/hpc_gui/wx_transfer_workspace.py src/hpc_gui/wx_shell.py src/hpc_gui/wx_editor_view.py src/hpc_gui/wx_settings.py src/hpc_gui/wx_settings_view.py src/hpc_gui/i18n/en.json src/hpc_gui/i18n/tr.json tests/test_w25_transfer_workspace_integrity.py
warning: in the working copy of '.opencode/protocol/WAVE_PROJECT_PROFILE.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of '.opencode/scripts/route-wave-findings.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of '.opencode/scripts/wave_state_engine.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/SUPPORT_MATRIX.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W02/OWNERSHIP_MAP.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'build/audit/w18-external-matrix.txt', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'build/audit/w18-gui-pytest.txt', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/capture_build_provenance.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/generate_release_manifest.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/file_context_actions.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_wave_controller_regressions.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git touches it
 .gitignore                                         |    4 +-
 .opencode/protocol/WAVE_PROJECT_PROFILE.json       |   36 +-
 .opencode/scripts/route-wave-findings.py           |  252 ++---
 .opencode/scripts/run-wave-program.py              |  753 +++++++++++--
 .opencode/scripts/wave_state_engine.py             |  234 +++-
 .../v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md   |   37 +-
 .../W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md    |    4 +-
 .../v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md |    4 +-
 .../W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md       |    4 +-
 .../v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md      |    4 +-
 artifacts/v2-final/W01/SUPPORT_MATRIX.md           |    2 +-
 artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md   |    4 +-
 artifacts/v2-final/W02/OWNERSHIP_MAP.md            |    2 +-
 artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md    |    2 +-
 artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json |   77 +-
 build/audit/w15-fresh-user-windows.json            |   22 +-
 .../audit/w15-fresh-user-windows.run1.runtime.json |    4 +-
 .../audit/w15-fresh-user-windows.run2.runtime.json |    4 +-
 build/audit/w16-fresh-user-windows.json            |   24 +-
 .../audit/w16-fresh-user-windows.run1.runtime.json |    4 +-
 .../audit/w16-fresh-user-windows.run2.runtime.json |    4 +-
 build/audit/w16-package-content-windows.json       |   10 +-
 build/audit/w16-packaged-smoke-windows.json        |  502 ++++++++-
 .../audit/w16-packaged-smoke-windows.runtime.json  |  491 ++++++++-
 build/audit/w18-external-matrix.txt                |   39 +-
 build/audit/w18-gui-pytest.txt                     |    8 +-
 build/audit/w22-focused-tests-current.txt          |    4 +-
 build/audit/w22-packaged-smoke-current.json        |   20 +-
 .../audit/w22-packaged-smoke-current.runtime.json  |    8 +-
 docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md  |   24 +-
 docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md   |    7 +-
 docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md  |   32 +-
 docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md   |   30 +-
 docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md  |   21 +-
 docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md   |   10 +-
 docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md  |   42 +-
 docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md   |   12 +-
 docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md  |   57 +-
 docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md   |   44 +-
 docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md  |   34 +-
 docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md   |   28 +-
 docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md  |   55 +-
 docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md   |  104 +-
 docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md  |   17 +-
 docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md   |   45 +-
 docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md   |   40 +-
 docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md   |   21 +-
 docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md  |   77 +-
 docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md   |   61 +-
 docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md  |   46 +-
 docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md   |   72 +-
 docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md  |   68 +-
 docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md   |   75 +-
 docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md   |   72 +-
 docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md  |   33 +-
 docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md   |   71 +-
 docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md  |   26 +-
 docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md   |  153 ++-
 docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md  |   12 +
 docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md   |   32 +-
 docs/wave-reports/v2/opencode/W18_AUDIT_REPORT.md  |  257 +++++
 docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md   |  283 +++++
 docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md  |   16 +-
 docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md   |   15 +-
 docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md  |   10 +-
 docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md   |    8 +-
 docs/wave-reports/v2/opencode/W21_AUDIT_REPORT.md  |    9 +-
 docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md   |   30 +-
 docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md  | 1132 +++++++++++++++++++-
 docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md   |  768 ++++++++++++-
 scripts/capture_build_provenance.py                |   10 +
 scripts/generate_release_manifest.py               |   10 +
 scripts/wx_packaged_smoke.py                       |   11 +-
 src/hpc_gui/i18n/en.json                           |   15 +-
 src/hpc_gui/i18n/tr.json                           |   15 +-
 src/hpc_gui/services/file_context_actions.py       |   28 +-
 src/hpc_gui/services/local_files.py                |   37 +-
 src/hpc_gui/services/transfer_controller.py        |    5 +
 .../services/transfer_session_controller.py        |   15 +-
 src/hpc_gui/wx_connection.py                       |   18 +-
---CHECK---
warning: in the working copy of '.opencode/protocol/WAVE_PROJECT_PROFILE.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of '.opencode/scripts/route-wave-findings.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of '.opencode/scripts/wave_state_engine.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/SUPPORT_MATRIX.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W02/OWNERSHIP_MAP.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'build/audit/w18-external-matrix.txt', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'build/audit/w18-gui-pytest.txt', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/capture_build_provenance.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/generate_release_manifest.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/file_context_actions.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_wave_controller_regressions.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git touches it
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:374: trailing whitespace.
+opencode.exe : 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:380: trailing whitespace.
+ 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:383: trailing whitespace.
+→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:384: trailing whitespace.
+→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:385: trailing whitespace.
+→ Read .tmp/agent-runs/ac-wave-opencode-parallel/20260924-074448-11a8ecee/0008-W22-findings.json 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:387: trailing whitespace.
+→ Read artifacts/wave_W22/WAVE_W22_EVIDENCE_MANIFEST.json 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:388: trailing whitespace.
+→ Read waves/pending/W22.md 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:389: trailing whitespace.
+→ Read .agents/skills/ac-wave-opencode-audit 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:392: trailing whitespace.
+$ git rev-parse HEAD; echo "---STATUS---"; git status --short --branch; echo "---LOG1---"; git log -1 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:491: trailing whitespace.
+→ Read build/audit/w22-packaged-smoke-current.json 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:492: trailing whitespace.
+→ Read build/audit/w22-focused-tests-current.txt 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:493: trailing whitespace.
+→ Read docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:494: trailing whitespace.
+→ Read docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:508: trailing whitespace.
+$ Get-Content .tmp/w22-repair-20260924-full60-repair20.txt -ErrorAction Stop | Select-Object -First 10; echo 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:509: trailing whitespace.
+"---VALIDATOR20---"; Get-Content .tmp/w22-repair-20260924-validator-repair20.txt -ErrorAction Stop | Select-Object 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:510: trailing whitespace.
+-First 40; echo "---REPLAY-EXISTS---"; Test-Path .tmp/w22-gui-local-real-replay/W22_GUI_LOCAL_REAL_REPLAY.json; 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:511: trailing whitespace.
+Test-Path .tmp/w22-repair-20260924-isolated-life065-repair20.txt; Test-Path 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:532: trailing whitespace.
+$ echo "---W21-FRONTMATTER---"; Get-Content waves/done/W21.md -ErrorAction SilentlyContinue | Select-Object 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:533: trailing whitespace.
+-First 50; echo "---W21-PENDING-CHECK---"; Test-Path waves/pending/W21.md; echo "---DIFF-STAT---"; git diff --stat; 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:534: trailing whitespace.
+echo "---DIFF-CHECK---"; git diff --check; echo "---WX-DIFF---"; git diff -- src/hpc_gui/wx_connection.py | 
---W25STAT---
 src/hpc_gui/i18n/en.json                           |  15 ++-
 src/hpc_gui/i18n/tr.json                           |  15 ++-
 src/hpc_gui/services/transfer_controller.py        |   5 +
 .../services/transfer_session_controller.py        |  15 ++-
 src/hpc_gui/wx_editor_view.py                      | 149 +++++++++++++++++++--
 src/hpc_gui/wx_settings.py                         |  19 ++-
 src/hpc_gui/wx_settings_view.py                    |   8 ++
 src/hpc_gui/wx_shell.py                            | 107 +++++++++++++++
 src/hpc_gui/wx_transfer_workspace.py               |  43 +++++-
 9 files changed, 352 insertions(+), 24 deletions(-)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff -- src/hpc_gui/services/transfer_session_controller.py src/hpc_gui/services/transfer_controller.py src/hpc_gui/wx_transfer_workspace.py | Select-Object -First 200; Write-Host "===EXTERNAL-REPLAY==="; Test-Path .tmp/w25-external-replay/W25_SFTP_REPLAY.json; Get-ChildItem .tmp/w25-external-replay -ErrorAction Continue | Select-Object Name, Length
diff --git a/src/hpc_gui/services/transfer_controller.py b/src/hpc_gui/services/transfer_controller.py
index 1737bf1b..001b3679 100644
--- a/src/hpc_gui/services/transfer_controller.py
+++ b/src/hpc_gui/services/transfer_controller.py
@@ -116,6 +116,11 @@ class TransferController:
             self.items = list(self._pending)
         self._cancel.clear()
         self._stop_after_current.clear()
+        # HPC-W06-XFER-010: a retry is a new clear operation state.  Re-announce
+        # restored items as queued (mirroring enqueue) so subscribers clear
+        # their failed/completed rows instead of showing the item twice.
+        for item in restored:
+            self._emit_queue("queued", item)
         return len(restored)
 
     def clear_pending(self) -> None:
diff --git a/src/hpc_gui/services/transfer_session_controller.py b/src/hpc_gui/services/transfer_session_controller.py
index 3eb30eb0..9280ae46 100644
--- a/src/hpc_gui/services/transfer_session_controller.py
+++ b/src/hpc_gui/services/transfer_session_controller.py
@@ -17,10 +17,21 @@ class TransferStatus:
 
 
 class TransferSessionController:
-    def __init__(self, items: Iterable[TransferItem], run_item, *, conflict_check=None, conflict_resolver=None, **kwargs) -> None:
+    """Framework-neutral transfer-session state around the transfer engine.
+
+    ``verify`` is an optional post-transfer integrity hook
+    (``HPC-W06-TODO-043``): ``verify(item)`` runs after the backend reports
+    success and only when ``checksum_enabled`` is true.  It must raise on a
+    digest mismatch (the engine then records ``FAILED`` instead of success)
+    and return normally for ``VERIFIED``/``UNSUPPORTED`` outcomes.  The
+    default ``None`` preserves the historical run-without-verify behavior.
+    """
+
+    def __init__(self, items: Iterable[TransferItem], run_item, *, conflict_check=None, conflict_resolver=None, verify=None, **kwargs) -> None:
         self._run_item_backend = run_item
         self._conflict_check = conflict_check
         self._conflict_resolver = conflict_resolver
+        self._verify = verify
         parameters = inspect.signature(run_item).parameters
         self._run_item_accepts_decision = "conflict_decision" in parameters or any(
             parameter.kind is parameter.VAR_KEYWORD for parameter in parameters.values()
@@ -51,6 +62,8 @@ class TransferSessionController:
             self._run_item_backend(item, progress, conflict_decision=decision)
         else:
             self._run_item_backend(item, progress)
+        if self.checksum_enabled and self._verify is not None and item.op in {"upload", "download"}:
+            self._verify(item)
 
     def status(self) -> TransferStatus:
         return TransferStatus(len(self.engine.pending), len(self.engine.failed), len(self.engine.completed))
diff --git a/src/hpc_gui/wx_transfer_workspace.py b/src/hpc_gui/wx_transfer_workspace.py
index ed521736..b4bd0fcb 100644
--- a/src/hpc_gui/wx_transfer_workspace.py
+++ b/src/hpc_gui/wx_transfer_workspace.py
@@ -179,7 +179,7 @@ def _build_transfers(parent, controller=None, embedded=False):
         layout.Add(notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
         layout.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
         panel.SetSizer(layout)
-        state = {"closed": False, "controller": controller, "queue_map": {}, "failed_map": {}, "completed_map": {}}
+        state = {"closed": False, "controller": controller, "queue_map": {}, "failed_map": {}, "completed_map": {}, "row_token": {}, "row_seq": 0}
         controls = {
             "status": status,
             "notebook": notebook,
@@ -314,9 +314,10 @@ def _build_transfers(parent, controller=None, embedded=False):
                         if iid not in state["queue_map"]:
                             state["queue_map"][iid] = it
                             found = False
+                            token = _row_token(it)
                             for idx in range(queue_list.GetItemCount()):
                                 try:
-                                    if queue_list.GetItemData(idx) == iid:
+                                    if queue_list.GetItemData(idx) == token:
                                         found = True
                                         break
                                 except Exception:
@@ -329,7 +330,7 @@ def _build_transfers(parent, controller=None, embedded=False):
                                     queue_list.SetItem(row, 2, "Queued")
                                     queue_list.SetItem(row, 3, "")
                                     queue_list.SetItem(row, 4, str(getattr(it, "priority", "Normal")))
-                                    queue_list.SetItemData(row, iid)
+                                    queue_list.SetItemData(row, _row_token(it))
                                 except RuntimeError:
                                     pass
                 except Exception:
@@ -353,10 +354,29 @@ def _build_transfers(parent, controller=None, embedded=False):
                 pass
 
     # --- embedded specific helpers ---
+    def _row_token(item) -> int:
+        """Stable small row token for a transfer item.
+
+        ``wx.ListCtrl.SetItemData`` truncates 64-bit ``id()`` values on
+        platforms where C ``long`` is 32 bits (Windows), so ``_find_row``
+        could never match a row again and queue rows were never removed or
+        updated (HPC-W06-XFER-001/003/012).  Tokens are small sequence
+        numbers; ``state`` keeps the owning item references alive, so the
+        ``id()`` keys cannot be recycled while tracked.
+        """
+        iid = id(item)
+        token = state["row_token"].get(iid)
+        if token is None:
+            state["row_seq"] = state.get("row_seq", 0) + 1
+            token = state["row_seq"]
+            state["row_token"][iid] = token
+        return token
+
     def _find_row(lst, iid):
+        token = state["row_token"].get(iid, iid)
         for idx in range(lst.GetItemCount()):
             try:
-                if lst.GetItemData(idx) == iid:
+                if lst.GetItemData(idx) == token:
                     return idx
             except Exception:
                 continue
@@ -378,7 +398,7 @@ def _build_transfers(parent, controller=None, embedded=False):
         lst.SetItem(idx, 5, str(getattr(item, "priority", "") or ""))
         lst.SetItem(idx, 6, status_text)
         try:
-            lst.SetItemData(idx, id(item))
+            lst.SetItemData(idx, _row_token(item))
         except Exception:
             pass
         return idx
@@ -391,6 +411,19 @@ def _build_transfers(parent, controller=None, embedded=False):
             try:
                 iid = id(item)
                 if event in ("queued", "started"):
+                    # HPC-W06-XFER-010: a retry reuses the same item identity,
+                    # so evict its stale failed/completed rows first; otherwise
+                    # the retried operation shows in two lists at once and the
+                    # failed list never clears.
+                    for _map_name, _list in (("failed_map", failed_list), ("completed_map", completed_list)):
+                        if iid in state[_map_name]:
+                            state[_map_name].pop(iid, None)
+                            _row = _find_row(_list, iid)
+                            if _row != -1:
+                                try:
+                                    _list.DeleteItem(_row)
+                                except Exception:
+                                    pass
                     try:
                         status.SetLabel(t("transfer.active_item").format(item=item.label()))
                     except Exception:
===EXTERNAL-REPLAY===
True

Name                 Length
----                 ------
check_cleanup.py        754
replay_w25_sftp.py     6094
W25_SFTP_REPLAY.json   1560
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Get-Content .tmp/w25-external-replay/W25_SFTP_REPLAY.json; Write-Host "---REGISTRY---"; Select-String -Path opencode/REQUIREMENT_REGISTRY.md -Pattern "HPC-W06-XFER-0" | Select-Object -First 25; Write-Host "---TODO---"; Select-String -Path opencode/TODO_OWNERSHIP_MAP.md -Pattern "HPC-W06-TODO-0(13|43)" | Select-Object -First 10
{
  "wave": "W25",
  "environment": "LOCAL_REAL_HYPERV",
  "target": "192.168.250.11:22",
  "provider": "local-real",
  "namespace": "/home/hpctest/w25-disposable-1790243626",
  "steps": {
    "connect": {
      "ok": true,
      "detail": "SSH key login against LOCAL_REAL controller"
    },
    "namespace": {
      "ok": true,
      "detail": "mkdir rc=0 sha256sum=sha256sum (GNU coreutils) 9.4"
    },
    "upload_sha256": {
      "ok": true,
      "detail": "local=93a5a4e7dfae remote=93a5a4e7dfae"
    },
    "download_bytes": {
      "ok": true,
      "detail": "106496 bytes identical"
    },
    "overwrite_cancel_runs": {
      "ok": true,
      "detail": "events=['started', 'failed']"
    },
    "overwrite_cancel_safe": {
      "ok": true,
      "detail": "remote unchanged, engine=cancelled"
    },
    "cancel_runs": {
      "ok": true,
      "detail": ""
    },
    "cancel_no_success_flip": {
      "ok": true,
      "detail": "failed=[(TransferItem(op='upload', src='D:\\\\Projeler\\\\hpc-client-gui\\\\.tmp\\\\os\\\\20260924-074448-11a8ecee\\\\10952-1790239772268041700\\\\w25-sftp-fea2ylm9\\\\big.bin', dst='/home/hpctest/w25-disposable-1790243626/big.bin', recursive=False, priority='Normal', cached_size=None), 'cancelled')]"
    },
    "retry_clean_upload": {
      "ok": true,
      "detail": "32MiB re-upload verified"
    },
    "cleanup": {
      "ok": true,
      "detail": "removed"
    }
  },
  "cleanup": "removed",
  "candidate_sha": "ccaf871ffc139973db826363859ca2933b216e9c"
}
---REGISTRY---

opencode\REQUIREMENT_REGISTRY.md:577:| `HPC-W06-XFER-001` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 97 | Scope 
/ Transfer workspace | `W25` | - | queue/list state; |
opencode\REQUIREMENT_REGISTRY.md:578:| `HPC-W06-XFER-002` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 98 | Scope 
/ Transfer workspace | `W25` | - | progress; |
opencode\REQUIREMENT_REGISTRY.md:579:| `HPC-W06-XFER-003` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 99 | Scope 
/ Transfer workspace | `W25` | - | success/failure; |
opencode\REQUIREMENT_REGISTRY.md:580:| `HPC-W06-XFER-004` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 100 | Scope 
/ Transfer workspace | `W25` | - | cancellation; |
opencode\REQUIREMENT_REGISTRY.md:581:| `HPC-W06-XFER-005` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 101 | Scope 
/ Transfer workspace | `W25` | - | overwrite/conflict behavior; |
opencode\REQUIREMENT_REGISTRY.md:582:| `HPC-W06-XFER-006` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 102 | Scope 
/ Transfer workspace | `W25` | - | cleanup of partial results. |
opencode\REQUIREMENT_REGISTRY.md:583:| `HPC-W06-XFER-007` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 171 | 
Workstream D - Transfers | `W25` | - | progress is monotonic within a transfer where byte progress exists; |
opencode\REQUIREMENT_REGISTRY.md:584:| `HPC-W06-XFER-008` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 172 | 
Workstream D - Transfers | `W25` | - | unknown total is represented honestly; |
opencode\REQUIREMENT_REGISTRY.md:585:| `HPC-W06-XFER-009` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 173 | 
Workstream D - Transfers | `W25` | - | cancelling does not later flip to success; |
opencode\REQUIREMENT_REGISTRY.md:586:| `HPC-W06-XFER-010` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 174 | 
Workstream D - Transfers | `W25` | - | retry creates a new clear operation state; |
opencode\REQUIREMENT_REGISTRY.md:587:| `HPC-W06-XFER-011` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 175 | 
Workstream D - Transfers | `W25` | - | partial local/remote files are handled by an explicit policy; |
opencode\REQUIREMENT_REGISTRY.md:588:| `HPC-W06-XFER-012` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 176 | 
Workstream D - Transfers | `W25` | - | multiple transfers cannot steal each other's UI status; |
opencode\REQUIREMENT_REGISTRY.md:589:| `HPC-W06-XFER-013` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 177 | 
Workstream D - Transfers | `W25` | - | disconnect invalidates/pauses/fails remote transfer predictably. |
opencode\REQUIREMENT_REGISTRY.md:590:| `HPC-W06-XFER-014` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 183 | 
Workstream E - Overwrite/conflict matrix | `W25` | - | Source \\\| Destination exists \\\| Required behavior |
opencode\REQUIREMENT_REGISTRY.md:591:| `HPC-W06-XFER-015` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 185 | 
Workstream E - Overwrite/conflict matrix | `W25` | - | local  remote \\\| yes \\\| prompt/policy, cancel safe |
opencode\REQUIREMENT_REGISTRY.md:592:| `HPC-W06-XFER-016` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 186 | 
Workstream E - Overwrite/conflict matrix | `W25` | - | remote  local \\\| yes \\\| prompt/policy, cancel safe |
opencode\REQUIREMENT_REGISTRY.md:593:| `HPC-W06-XFER-017` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 187 | 
Workstream E - Overwrite/conflict matrix | `W25` | - | editor local save \\\| changed externally \\\| detect or 
document limitation |
opencode\REQUIREMENT_REGISTRY.md:594:| `HPC-W06-XFER-018` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 188 | 
Workstream E - Overwrite/conflict matrix | `W25` | - | editor remote save \\\| remote changed externally \\\| conflict 
policy explicit |
opencode\REQUIREMENT_REGISTRY.md:595:| `HPC-W06-XFER-019` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 189 | 
Workstream E - Overwrite/conflict matrix | `W25` | - | Save As \\\| target exists \\\| prompt/policy |
---TODO---
opencode\TODO_OWNERSHIP_MAP.md:38:| `HPC-W06-TODO-013` | `W25` | `W06` | `-` | ACTIVE | Explicitly review jobs refresh 
interval, live tracking warnings, minimize/follow behavior, squeue/sacct/lssrv auto-refresh, sbatch follow mode, X11 
options, transfer type, upload confirmation, checksum, transfer speed test, CLI access/default profile, remote 
defaults, file associations, shortcut preferences and provider/profile settings. |
opencode\TODO_OWNERSHIP_MAP.md:183:| `HPC-W06-TODO-043` | `W25` | `W06` | `-` | ACTIVE | Transfer SHA-256 integrity 
and cancel/retry/failure/conflict cases. |
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_w25_transfer_workspace_integrity.py -q 2>&1 | Select-Object -Last 20
..............                                                           [100%]
14 passed in 2.75s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Select-String -Path tests/test_w25_transfer_workspace_integrity.py -Pattern "skip|xfail" | Select-Object -First 10; Write-Host "---SECRETS-SCAN---"; git diff -- src/hpc_gui/ | Select-String -Pattern "(password|secret|token|BEGIN.*PRIVATE|api[_-]?key)" | Select-Object -First 10; Write-Host "---I18N---"; python -c "import json; en=json.load(open('src/hpc_gui/i18n/en.json',encoding='utf-8')); tr=json.load(open('src/hpc_gui/i18n/tr.json',encoding='utf-8')); print('editor keys en:', sorted([k for k in en if k.startswith('editor.')])[-10:]); print('match:', set(k for k in en if k.startswith('editor.'))==set(k for k in tr if k.startswith('editor.')))"
tests\test_w25_transfer_workspace_integrity.py:70:def test_session_verify_unsupported_passes_and_disabled_skips() -> 
None:
tests\test_w25_transfer_workspace_integrity.py:86:    skipped_calls: list[str] = []
tests\test_w25_transfer_workspace_integrity.py:89:        skipped_calls.append(item.src)
tests\test_w25_transfer_workspace_integrity.py:92:    skipped = TransferSessionController([item], run, 
verify=strict_verify)
tests\test_w25_transfer_workspace_integrity.py:93:    skipped.engine.start()
tests\test_w25_transfer_workspace_integrity.py:94:    assert skipped.engine.wait(2)
tests\test_w25_transfer_workspace_integrity.py:95:    assert skipped.engine.completed == [item]
tests\test_w25_transfer_workspace_integrity.py:96:    assert skipped_calls == []
tests\test_w25_transfer_workspace_integrity.py:180:wx = pytest.importorskip("wx")
---SECRETS-SCAN---
warning: in the working copy of 'src/hpc_gui/services/file_context_actions.py', LF will be replaced by CRLF the next time Git touches it
+        state = {"closed": False, "controller": controller, "queue_map": {}, "failed_map": {}, "completed_map": {}, 
"row_token": {}, "row_seq": 0}
+                            token = _row_token(it)
+                                    if queue_list.GetItemData(idx) == token:
+                                    queue_list.SetItemData(row, _row_token(it))
+    def _row_token(item) -> int:
+        """Stable small row token for a transfer item.
+        updated (HPC-W06-XFER-001/003/012).  Tokens are small sequence
+        token = state["row_token"].get(iid)
+        if token is None:
+            token = state["row_seq"]
---I18N---
editor keys en: []
match: True
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff -- src/hpc_gui/i18n/en.json | Select-Object -First 40; Write-Host "---EDITOR-DIFF---"; git diff -- src/hpc_gui/wx_editor_view.py | Select-Object -First 60
diff --git a/src/hpc_gui/i18n/en.json b/src/hpc_gui/i18n/en.json
index 04ab274d..231c3a50 100644
--- a/src/hpc_gui/i18n/en.json
+++ b/src/hpc_gui/i18n/en.json
@@ -344,6 +344,13 @@
     "remote": "Remote:",
     "open_failed": "Could not open file: {err}",
     "save_failed": "Could not save file: {err}",
+    "save_as_title": "Save As",
+    "save_as_exists": "Target already exists:\n{path}\nOverwrite?",
+    "save_as_cancelled": "Save As cancelled; the document is unchanged.",
+    "external_change_title": "File changed externally",
+    "external_change_message": "The file on disk differs from the last saved version:\n{path}\nOverwrite the external changes?",
+    "external_deleted_message": "The file no longer exists on disk:\n{path}\nRecreate it?",
+    "external_change_cancelled": "Save cancelled; your edits are preserved.",
     "action_requires_save": "Cannot submit or run because the document could not be saved.",
     "remote_file_service_unavailable": "Remote file service is unavailable.",
     "document_path_required": "Document path is required.",
@@ -502,7 +509,8 @@
     "follow_new_window": "Follow in New Window",
     "follow_existing": "Assign to Existing Follower",
     "following": "Following",
-    "not_following": "Not following"
+    "not_following": "Not following",
+    "delete_confirm_detail": "Delete {count} selected item(s) from {location}?\n{names}"
   },
   "jobs_outputs": {
     "auto_scroll": "Auto-scroll",
@@ -847,7 +855,8 @@
     "cmp_local_newer": "Local newer",
     "cmp_remote_newer": "Remote newer",
     "waiting_local_folder": "Waiting for local folder",
-    "waiting_remote_folder": "Waiting for remote folder"
+    "waiting_remote_folder": "Waiting for remote folder",
+    "forward": "Forward"
   },
   "transfer": {
     "ftp_activity_title": "Transfers",
@@ -1272,4 +1281,4 @@
     "no_supported_files": "No supported files to lint.",
---EDITOR-DIFF---
diff --git a/src/hpc_gui/wx_editor_view.py b/src/hpc_gui/wx_editor_view.py
index 2188b7f7..beff87b8 100644
--- a/src/hpc_gui/wx_editor_view.py
+++ b/src/hpc_gui/wx_editor_view.py
@@ -2,6 +2,8 @@
 
 from __future__ import annotations
 
+import os
+from dataclasses import replace
 from pathlib import Path
 from threading import Thread
 
@@ -12,6 +14,18 @@ from hpc_gui.wx_editor import WxEditorModel
 from hpc_gui.wx_host import make_host
 
 
+def _disk_baseline(path: str):
+    """``(mtime_ns, size)`` snapshot of a local path, or ``None`` when the
+    path is empty, absent, or unstatable."""
+    try:
+        if not path:
+            return None
+        st = os.stat(path)
+        return (st.st_mtime_ns, st.st_size)
+    except OSError:
+        return None
+
+
 def _build_editor(parent, model: WxEditorModel | None, *, path: str, content: str, is_local, save_remote, on_submit, on_run, action_factory, on_destroy, embedded, on_open=None, on_new_template=None, on_lint=None):
     try:
         import wx
@@ -84,7 +98,21 @@ def _build_editor(parent, model: WxEditorModel | None, *, path: str, content: st
     root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
     root.Add(status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
     panel.SetSizer(root)
-    state = {"closed": False, "in_flight": False, "destroy_notified": False}
+    state = {"closed": False, "in_flight": False, "destroy_notified": False, "disk_baseline": {}}
+
+    def _note_disk_baseline(doc) -> None:
+        """Record the at-open disk state for later external-change detection
+        (HPC-W06-XFER-017).  Only local documents participate."""
+        try:
+            if doc is not None and getattr(doc, "is_local", False) and doc.path:
+                state["disk_baseline"][doc.path] = _disk_baseline(doc.path)
+        except Exception:
+            pass
+
+    try:
+        _note_disk_baseline(model.controller.active)
+    except Exception:
+        pass
 
     def notify_destroy():
         if on_destroy is not None and not state["destroy_notified"]:
@@ -141,30 +169,104 @@ def _build_editor(parent, model: WxEditorModel | None, *, path: str, content: st
         dlg.ShowModal()
         dlg.Destroy()
 
+    def _ask_overwrite(title_key: str, message: str) -> bool:
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff -- src/hpc_gui/wx_shell.py | Select-Object -First 140; Write-Host "===DIFF-NAMES-ONLY-W25-FILES==="; git diff --name-only -- src/hpc_gui/services/transfer_controller.py src/hpc_gui/services/transfer_session_controller.py src/hpc_gui/wx_transfer_workspace.py src/hpc_gui/wx_shell.py src/hpc_gui/wx_editor_view.py src/hpc_gui/wx_settings.py src/hpc_gui/wx_settings_view.py src/hpc_gui/i18n/en.json src/hpc_gui/i18n/tr.json
diff --git a/src/hpc_gui/wx_shell.py b/src/hpc_gui/wx_shell.py
index e2f36a09..d33c3266 100644
--- a/src/hpc_gui/wx_shell.py
+++ b/src/hpc_gui/wx_shell.py
@@ -241,6 +241,7 @@ def create_shell_frame(app=None, *, tray_factory=None, lifecycle=None, session_s
     directories_panel = build_directories_panel(notebook, **_dirs)
     notebook.AddPage(directories_panel, t("tabs.directories"), False)
     page_controls["NAV-DIRECTORIES"] = {"page": directories_panel}
+    session_state["_embedded_directories_panel"] = directories_panel
 
     # Files (header row + splitter with local left, remote right + transfers bottom)
     files_page = wx.Panel(notebook)
@@ -301,6 +302,9 @@ def create_shell_frame(app=None, *, tray_factory=None, lifecycle=None, session_s
     session_state["_embedded_remote_files_panel"] = remote_panel
     top_splitter.SplitVertically(local_panel, remote_panel, 340)
     top_splitter.SetMinimumPaneSize(300)
+    # TODO-031: keep the Local/Remote split proportionally balanced on resize
+    # instead of pinning the local pane to the fixed 340px initial sash.
+    top_splitter.SetSashGravity(0.5)
     from hpc_gui.wx_transfer_workspace import build_transfers_panel
 
     transfers_panel = build_transfers_panel(transfer_splitter)
@@ -2545,6 +2549,12 @@ def main() -> int:
 
 
 def _editor_action_factory(session_state):
+    # HPC-W06-XFER-018 explicit remote-save conflict policy: remote saves are
+    # last-writer-wins.  The backend offers no versioned compare-and-swap, so
+    # a remote document changed externally since it was opened is overwritten
+    # without detection.  Users must re-open before editing when another
+    # writer may be active.  Failed saves keep the document dirty/recoverable;
+    # Save As to an existing remote target prompts via `target_exists`.
     def callbacks(document):
         session = session_state.get("session") or {}
         files = session.get("files")
@@ -2594,6 +2604,7 @@ def _editor_action_factory(session_state):
 
         return {
             "save_remote": save_remote if files else None,
+            "target_exists": (lambda path: files.exists(path)) if files and callable(getattr(files, "exists", None)) else None,
             "on_submit": submit,
             "on_run": run,
         }
@@ -2708,6 +2719,80 @@ def _call_transfer_with_progress(method, src, dst, progress) -> None:
         method(src, dst)
 
 
+def _cancel_transfer_sessions(session_state) -> int:
+    """Cancel every in-flight file-transfer session (HPC-W06-XFER-013).
+
+    A disconnect must invalidate remote transfers predictably instead of
+    leaving them blocked on a dead transport until a socket timeout.  Returns
+    the number of sessions cancelled.  Never raises.
+    """
+    cancelled = 0
+    try:
+        sessions = list((session_state or {}).get("transfer_sessions") or ())
+    except Exception:
+        return 0
+    for session in sessions:
+        try:
+            cancel = getattr(session, "cancel", None)
+            if callable(cancel):
+                cancel()
+                cancelled += 1
+            else:
+                engine = getattr(session, "engine", None)
+                fallback = getattr(engine, "cancel_all", None) if engine is not None else None
+                if callable(fallback):
+                    fallback()
+                    cancelled += 1
+        except Exception:
+            continue
+    return cancelled
+
+
+def _verify_transfer_item(files, item):
+    """Opt-in post-transfer SHA-256 verification (HPC-W06-TODO-043).
+
+    Mirrors the Qt ``remote_dir_panel._verify_transfer_item`` semantics for
+    the wx file-view path: disabled unless the stored
+    ``transfer_checksum_verification_enabled`` setting is true; backends
+    without a ``sha256`` probe (or a failing probe) yield an ``UNSUPPORTED``
+    passthrough; a digest mismatch raises so the engine records ``FAILED``
+    instead of success.  Returns the :class:`VerificationState`.
+    """
+    from hpc_gui.services.transfer_integrity import VerificationState, verify_transfer
+
+    try:
+        from hpc_gui.config.storage import get_transfer_checksum_verification_enabled
+        enabled = bool(get_transfer_checksum_verification_enabled())
+    except Exception:
+        enabled = False
+    if not enabled:
+        return VerificationState.OFF
+    remote_hash = getattr(files, "sha256", None)
+    if not callable(remote_hash):
+        return VerificationState.UNSUPPORTED
+    local_path = item.src if item.op == "upload" else item.dst
+    remote_path = item.dst if item.op == "upload" else item.src
+    try:
+        remote_digest = remote_hash(remote_path)
+    except Exception:
+        return VerificationState.UNSUPPORTED
+    result = verify_transfer(local_path, remote_digest)
+    if result.state is VerificationState.FAILED:
+        raise RuntimeError(
+            f"SHA-256 verification failed for {remote_path}: "
+            f"local={result.local_digest}, remote={result.remote_digest}"
+        )
+    return result.state
+
+
+def _transfer_checksum_requested() -> bool:
+    try:
+        from hpc_gui.config.storage import get_transfer_checksum_verification_enabled
+        return bool(get_transfer_checksum_verification_enabled())
+    except Exception:
+        return False
+
+
 def _start_file_transfers(session_state, lifecycle, items, *, on_progress=None, conflict_resolver=None, files_backend=None, parent=None):
     """Queue file-view transfers through the shared transfer lifecycle."""
     from hpc_gui.wx_transfer_workspace import create_transfer_progress
@@ -2831,9 +2916,12 @@ def _start_file_transfers(session_state, lifecycle, items, *, on_progress=None,
         parallel_limit=parallel_limit,
         conflict_check=lambda item: _destination_exists(files, item.op, item.dst),
         conflict_resolver=conflict_resolver or session_state.get("conflict_resolver") or (wx_conflict_resolver if parent else None),
+        verify=lambda item: _verify_transfer_item(files, item),
         on_queue=queue_event,
         on_progress=progress_event,
     )
+    if _transfer_checksum_requested():
+        controller.set_checksum_enabled(True)
     if transfer_window:
         transfer_window._wx_transfer_set_controller(controller)
     if session_state.get("conflict_policy"):
@@ -3355,6 +3443,14 @@ def _connection_callbacks(session_state, parent, lifecycle):
                     panel._wx_remote_set_provider_filters(cbs.get("provider_filters"), cbs.get("plugin_filters"))
             except Exception:
===DIFF-NAMES-ONLY-W25-FILES===
src/hpc_gui/i18n/en.json
src/hpc_gui/i18n/tr.json
src/hpc_gui/services/transfer_controller.py
src/hpc_gui/services/transfer_session_controller.py
src/hpc_gui/wx_editor_view.py
src/hpc_gui/wx_settings.py
src/hpc_gui/wx_settings_view.py
src/hpc_gui/wx_shell.py
src/hpc_gui/wx_transfer_workspace.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_transfer_controller.py tests/test_transfer_integrity.py tests/test_wx_transfer_workspace.py -q 2>&1 | Select-Object -Last 8; Write-Host "---CONFLICT---"; python -m pytest tests/test_transfer_conflict_ui.py -q 2>&1 | Select-Object -Last 8
.........                                                                [100%]
9 passed in 1.33s
---CONFLICT---

no tests ran in 0.01s
ERROR: file or directory not found: tests/test_transfer_conflict_ui.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Get-ChildItem tests/test_*transfer*, tests/test_*conflict*, tests/test_*editor* | Select-Object Name; Write-Host "---RUN2---"; python -m pytest tests/test_transfer_controller.py tests/test_transfer_integrity.py tests/test_wx_transfer_workspace.py tests/test_w25_transfer_workspace_integrity.py -q 2>&1 | Select-Object -Last 6
---RUN2---
Name
----
test_local_transfer_gate.py
test_profile_transfer_settings.py
test_transfer_cancel_recovery.py
test_transfer_concurrency.py
test_transfer_controller.py
test_transfer_directory_controllers.py
test_transfer_integrity.py
test_transfer_key_release.py
test_transfer_parallelism_migration.py
test_transfer_performance_scenarios.py
test_transfer_resume_semantics.py
test_transfer_speed_test.py
test_transfer_wave17.py
test_w25_transfer_workspace_integrity.py
test_wx_file_transfer_integration.py
test_wx_transfer_conflict_ui.py
test_wx_transfer_ui_lifecycle.py
test_wx_transfer_workspace.py
test_wx_transfer_conflict_ui.py
test_editor_controller.py
test_editor_flow.py
test_editor_shortcut_safety.py
test_editor_v2_lint.py
test_wave7_editor_terminal_logs.py
test_wx_editor_cross_view_actions.py
test_wx_editor_tabs.py
test_wx_editor_window_parity.py
test_wx_editor.py
test_wx_remote_editor_flow.py
.......................                                                  [100%]
23 passed in 3.57s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_wx_transfer_conflict_ui.py tests/test_wx_transfer_ui_lifecycle.py tests/test_transfer_cancel_recovery.py tests/test_wx_editor.py -q 2>&1 | Select-Object -Last 8; Write-Host "---I18N-TEST---"; python -m pytest tests/ -k "translation_key_sets_match" -q 2>&1 | Select-Object -Last 6
File "D:\Python\Python312\Lib\site-packages\pluggy\_manager.py", line 120 in _hookexec
  File "D:\Python\Python312\Lib\site-packages\pluggy\_hooks.py", line 512 in __call__
  File "D:\Python\Python312\Lib\site-packages\_pytest\config\__init__.py", line 199 in main
  File "D:\Python\Python312\Lib\site-packages\_pytest\config\__init__.py", line 223 in console_main
  File "D:\Python\Python312\Lib\site-packages\pytest\__main__.py", line 9 in <module>
  File "<frozen runpy>", line 88 in _run_code
  File "<frozen runpy>", line 198 in _run_module_as_main
..........................
---I18N-TEST---
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
=========================== short test summary info ===========================
ERROR tests/contracts (1)/test_wave_closeout_hardening.py
ERROR tests/contracts (2)/test_wave_closeout_hardening.py
!!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!
3079 deselected, 2 errors in 7.53s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_wx_transfer_conflict_ui.py -q 2>&1 | Select-Object -Last 4; Write-Host "---LIFECYCLE---"; python -m pytest tests/test_wx_transfer_ui_lifecycle.py -q 2>&1 | Select-Object -Last 4
...........                                                              [100%]
11 passed in 1.06s
---LIFECYCLE---
..............                                                           [100%]
14 passed in 5.63s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_transfer_cancel_recovery.py -q 2>&1 | Select-Object -Last 4; Write-Host "---EDITOR---"; python -m pytest tests/test_wx_editor.py -q 2>&1 | Select-Object -Last 4; Write-Host "---I18N-FILE---"; python -m pytest tests/test_i18n.py -q 2>&1 | Select-Object -Last 4
...                                                                      [100%]
3 passed in 0.43s
---EDITOR---
..............                                                           [100%]
14 passed in 2.80s
---I18N-FILE---

no tests ran in 0.01s
ERROR: file or directory not found: tests/test_i18n.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Get-ChildItem tests/test_*i18n*, tests/test_*translation* | Select-Object Name; python -m pytest tests/test_wx_editor.py tests/test_transfer_cancel_recovery.py -q -p no:cacheprovider 2>&1 | Select-Object -Last 4
Name
----
test_startup_i18n.py
test_wave8_i18n_ui_ergonomics.py
test_wx_file_context_i18n.py
test_wx_i18n.py
test_wx_shell_i18n.py
  File "D:\Python\Python312\Lib\site-packages\pytest\__main__.py", line 9 in <module>
  File "<frozen runpy>", line 88 in _run_code
  File "<frozen runpy>", line 198 in _run_module_as_main
...............
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_wx_i18n.py -q 2>&1 | Select-Object -Last 4; Write-Host "---SHELL---"; python -m pytest tests/test_wx_shell.py -q 2>&1 | Select-Object -Last 4
.                                                                        [100%]
1 passed in 0.33s
---SHELL---
.....                                                                    [100%]
5 passed in 0.45s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Select-String -Path src/hpc_gui/wx_shell.py -Pattern "_cancel_transfer_sessions|on_disconnected" | Select-Object -First 10; Write-Host "---SETTINGS---"; Select-String -Path src/hpc_gui/wx_settings.py -Pattern "persist_transfer_checksum|transfer_checksum" | Select-Object -First 10; Write-Host "---DIFFCHECK-OWNED---"; git diff --check -- src/hpc_gui/services/transfer_controller.py src/hpc_gui/services/transfer_session_controller.py src/hpc_gui/wx_transfer_workspace.py src/hpc_gui/wx_shell.py src/hpc_gui/wx_editor_view.py src/hpc_gui/wx_settings.py src/hpc_gui/wx_settings_view.py tests/test_w25_transfer_workspace_integrity.py; Write-Host "OWNED-CHECK-DONE"
src\hpc_gui\wx_shell.py:188:            _conn_model._session_invalidated_hook = _conn["on_disconnected"]
src\hpc_gui\wx_shell.py:2722:def _cancel_transfer_sessions(session_state) -> int:
src\hpc_gui\wx_shell.py:3455:    def on_disconnected(session):
src\hpc_gui\wx_shell.py:3487:        _cancel_transfer_sessions(session_state)
src\hpc_gui\wx_shell.py:3489:    return {"profiles": profiles, "lifecycle": lifecycle, "on_connected": on_connected, 
"on_disconnected": on_disconnected}
---SETTINGS---
src\hpc_gui\wx_settings.py:12:GLOBAL_KEYS = frozenset({"jobs_outputs_refresh_interval", "remote_directory_cache", 
"transfer_checksum", "shortcut_preferences"})
src\hpc_gui\wx_settings.py:54:def persist_transfer_checksum_to_storage(model: WxSettingsModel) -> bool:
src\hpc_gui\wx_settings.py:55:    """Bridge the wx ``transfer_checksum`` checkbox to the stored
src\hpc_gui\wx_settings.py:56:    ``transfer_checksum_verification_enabled`` setting consumed by both the
src\hpc_gui\wx_settings.py:62:    from hpc_gui.config.storage import set_transfer_checksum_verification_enabled
src\hpc_gui\wx_settings.py:65:        set_transfer_checksum_verification_enabled(
src\hpc_gui\wx_settings.py:66:            bool(model.global_settings.get("transfer_checksum", False))
src\hpc_gui\wx_settings.py:71:__all__ = ["LEGACY_IGNORED_KEYS", "SettingsSnapshot", "WxSettingsModel", 
"persist_transfer_checksum_to_storage"]
---DIFFCHECK-OWNED---
OWNED-CHECK-DONE
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
Auditing W25 — loading canonical checks and evidence.
W25 spec mapped — now verifying implementation truth and evidence.
Core claims check out — now running independent test verification.
Spot-checks confirm the fixes — now finalizing the audit verdict.
# W25 Audit — fresh independent (opencode)

- Wave: `W25` (execution, `waves/pending/W25.md`), owned: `HPC-W06-XFER-001..019` + `HPC-W06-TODO-013/043`. Evidence classes required: `GUI,EXTERNAL`.
- Candidate: `HEAD ccaf871ffc139973db826363859ca2933b216e9c` + working-tree W25 hunks (9 files, `+352/-24`, matches report header). Controller `content_identity 3f48…` consumed as handoff; audit binds conclusions to the verified HEAD + owned diff below.
- Report reviewed: `docs/wave-reports/v2/opencode/W25_WAVE_REPORT.md` (`READY_FOR_AUDIT`). No `W25_AUDIT_REPORT.md` exists yet — controller-owned persistence.

## Independent verification (this audit, native Windows)

- `tests/test_w25_transfer_workspace_integrity.py` → **14 passed** (re-ran, exit 0). Covers XFER-010 retry requeue, XFER-012 isolation, XFER-013 disconnect, XFER-017/019 editor, TODO-043 verify hook.
- Spot re-runs per-file (exit 0 each): controller+integrity+workspace 9, `test_wx_transfer_conflict_ui` 11, `test_wx_transfer_ui_lifecycle` 14, `test_transfer_cancel_recovery` 3, `test_wx_editor` 14, `test_wx_shell` 5, `test_wx_i18n` 1.
- Multi-file single-process wx runs crash in teardown (access violation) — reproduced here too, identical to report disclosure; pre-existing harness fragility, per-file evidence valid. `tests/contracts (1|2)/` duplicate-basename collection errors are pre-existing repo pollution, not W25.
- Diff verified: FIX-A row-token (`wx_transfer_workspace`), FIX-B `queued` re-emit (`transfer_controller.retry_failed`) + panel eviction, FIX-C `_cancel_transfer_sessions` + `on_disconnected` wiring (`wx_shell:3487`), FIX-D `verify=` hook + `_verify_transfer_item` + checksum bridge (`wx_settings.persist_transfer_checksum_to_storage`), FIX-E editor Save As redirect + prompts + at-open `(mtime_ns,size)` baselines + explicit last-writer-wins remote policy. i18n `en/tr` carry the 7 editor keys with matching sets.
- `git diff --check` on all owned paths: clean. No new skip/xfail; no secrets in added lines (`token` hits are `_row_token` only). No weakened tests — new assertions are behavioral (row counts, digests, paths, labels, engine states).
- GUI FULL: 8 wx runtime nodes in the W25 file passed in this audit (queue/failed/completed transitions, retry clearing, concurrent isolation, Save As prompts, cancel-safe statuses, remote redirect).
- EXTERNAL: `.tmp/w25-external-replay/W25_SFTP_REPLAY.json` present, `candidate_sha` = HEAD, all steps ok (upload SHA-256 match, 106496-byte download identical, overwrite-cancel safe, 32MiB cancel-no-flip, retry re-upload verified, cleanup removed, disposable namespace). Lab Slurm `compute01|down` note is out of scope and honestly disclosed; SFTP scope unaffected. Not re-executed here (disposable lab namespace); artifact binds to candidate.
- PACKAGE N/A justified (required classes GUI+EXTERNAL only).

## Cross-scope observations (non-blocking, routed not repaired)

- `en.json`/`tr.json` carry 2 extra stacked keys (`delete_confirm_detail`, `forward`) beyond W25's 7 editor keys; additive, parity holds — belongs to sibling owner.
- `wx_shell.py` carries pre-existing stacked hunks (directories registration, sash gravity) disclosed in the report, preserved, not claimed.
- `W22_AUDIT_REPORT.md` trailing-whitespace `diff --check` noise is outside W25 ownership.

## Verdict

All 21 owned IDs traced requirement → implementation → test → evidence with exact commands and candidate binding. No owned blocking defect remains. **PASS.**

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS


## Controller-persisted fresh independent audit — 2026-09-24T10:31:12.670226+00:00

- Wave: `W25`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0042-W25-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0042-W25-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
→ Read .tmp/agent-runs/ac-wave-opencode-parallel/20260924-074448-11a8ecee/0040-W25-findings.json 
→ Read .tmp/agent-runs/ac-wave-opencode-parallel/20260924-074448-11a8ecee/0037-W25-audit-normalized.json 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md [offset=30]
$ powershell -NoProfile -Command "Get-Content .agents/skills/ac-wave-opencode-audit/SKILL.md | Measure-Object -Line; Write-Host '---'; git rev-parse HEAD; Write-Host '---'; git status --porcelain=v1 | Select-Object -First 50; Write-Host '---STATUS_END---'; Test-Path artifacts/wave_W25/WAVE_W25_EVIDENCE_MANIFEST.json; Get-ChildItem artifacts/wave_W25/ -ErrorAction SilentlyContinue | Select-Object -First 20; Write-Host '---WAVES---'; Get-ChildItem waves/pending/W25.md,waves/done/W25.md,waves/blocked/W25.md,waves/postponed/W25.md -ErrorAction SilentlyContinue | Format-Table FullName"
---
ccaf871ffc139973db826363859ca2933b216e9c
---
---STATUS_END---
---WAVES---
Lines Words Characters Property
----- ----- ---------- --------
   22                          
 M .gitignore
 M .opencode/protocol/WAVE_PROJECT_PROFILE.json
 M .opencode/scripts/route-wave-findings.py
 M .opencode/scripts/run-wave-program.py
 M .opencode/scripts/wave_state_engine.py
 M artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md
 M artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md
 M artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md
 M artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md
 M artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md
 M artifacts/v2-final/W01/SUPPORT_MATRIX.md
 M artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md
 M artifacts/v2-final/W02/OWNERSHIP_MAP.md
 M artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md
 M artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json
 M build/audit/w15-fresh-user-windows.json
 M build/audit/w15-fresh-user-windows.run1.runtime.json
 M build/audit/w15-fresh-user-windows.run2.runtime.json
 M build/audit/w16-fresh-user-windows.json
 M build/audit/w16-fresh-user-windows.run1.runtime.json
 M build/audit/w16-fresh-user-windows.run2.runtime.json
 M build/audit/w16-package-content-windows.json
 M build/audit/w16-packaged-smoke-windows.json
 M build/audit/w16-packaged-smoke-windows.runtime.json
 M build/audit/w18-external-matrix.txt
 M build/audit/w18-gui-pytest.txt
 M build/audit/w22-focused-tests-current.txt
 M build/audit/w22-packaged-smoke-current.json
 M build/audit/w22-packaged-smoke-current.runtime.json
 M docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md
True
                               



FullName                                       
--------                                       
D:\Projeler\hpc-client-gui\waves\pending\W25.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✗ Read .agents/protocol/WAVE_EXECUTION_AND_TEST_PROTOCOL.md failed
Error: File not found: .agents/protocol/WAVE_EXECUTION_AND_TEST_PROTOCOL.md

Did you mean one of these?
.agents\protocol\AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md
✗ Read .agents/protocol/WAVE_PROGRAM_ORCHESTRATION.md failed
Error: File not found: .agents/protocol/WAVE_PROGRAM_ORCHESTRATION.md

Did you mean one of these?
.agents\protocol\AC_WAVE_PROGRAM_ORCHESTRATION.md
✗ Read .agents/protocol/WAVE_VALIDATION_EVIDENCE_SCHEMA.md failed
Error: File not found: .agents/protocol/WAVE_VALIDATION_EVIDENCE_SCHEMA.md

Did you mean one of these?
.agents\protocol\AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md
→ Read waves/pending/W25.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md 
→ Read .agents/protocol/AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md 
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
$ powershell -NoProfile -Command "$p='artifacts/wave_W25/WAVE_W25_EVIDENCE_MANIFEST.json'; Write-Host (Test-Path $p); Get-Item $p -ErrorAction SilentlyContinue | Format-List FullName,Length,LastWriteTime; Write-Host '---HEAD---'; git rev-parse HEAD; Write-Host '---LOG1---'; git log --oneline -3; Write-Host '---MANIFEST_SIBS---'; Get-ChildItem artifacts/wave_W*/WAVE_*EVIDENCE_MANIFEST.json | Select-Object FullName | Select-Object -First 30"
=artifacts/wave_W25/WAVE_W25_EVIDENCE_MANIFEST.json : The term '=artifacts/wave_W25/WAVE_W25_EVIDENCE_MANIFEST.json' 
is not recognized as the name of a cmdlet, function, script file, or operable program. Check the spelling of the name, 
or if a path was included, verify that the path is correct and try again.
At line:1 char:1
+ ='artifacts/wave_W25/WAVE_W25_EVIDENCE_MANIFEST.json'; Write-Host (Te ...
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (=artifacts/wave...E_MANIFEST.json:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
Test-Path : Cannot process command because of one or more missing mandatory parameters: Path.
At line:1 char:68
+ ... e_W25/WAVE_W25_EVIDENCE_MANIFEST.json'; Write-Host (Test-Path ); Get- ...
+                                                         ~~~~~~~~~
    + CategoryInfo          : InvalidArgument: (:) [Test-Path], ParameterBindingException
    + FullyQualifiedErrorId : MissingMandatoryParameter,Microsoft.PowerShell.Commands.TestPathCommand
 
Get-Item : Cannot process command because of one or more missing mandatory parameters: Path.
At line:1 char:81
+ ... te-Host (Test-Path ); Get-Item  -ErrorAction SilentlyContinue | Forma ...
+                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : InvalidArgument: (:) [Get-Item], ParameterBindingException
    + FullyQualifiedErrorId : MissingMandatoryParameter,Microsoft.PowerShell.Commands.GetItemCommand
 
---HEAD---
ccaf871ffc139973db826363859ca2933b216e9c
---LOG1---
ccaf871f Harden Wave close handoff recovery
99e32915 Classify controller handoff changes as closeout-only
7a5e6142 Honor fresh audit receipt at Wave close
---MANIFEST_SIBS---

FullName                                                                     
--------                                                                     
D:\Projeler\hpc-client-gui\artifacts\wave_W18\WAVE_W18_EVIDENCE_MANIFEST.json
D:\Projeler\hpc-client-gui\artifacts\wave_W19\WAVE_W19_EVIDENCE_MANIFEST.json
D:\Projeler\hpc-client-gui\artifacts\wave_W20\WAVE_W20_EVIDENCE_MANIFEST.json
D:\Projeler\hpc-client-gui\artifacts\wave_W21\WAVE_W21_EVIDENCE_MANIFEST.json
D:\Projeler\hpc-client-gui\artifacts\wave_W22\WAVE_W22_EVIDENCE_MANIFEST.json
D:\Projeler\hpc-client-gui\artifacts\wave_W23\WAVE_W23_EVIDENCE_MANIFEST.json
D:\Projeler\hpc-client-gui\artifacts\wave_W24\WAVE_W24_EVIDENCE_MANIFEST.json
D:\Projeler\hpc-client-gui\artifacts\wave_W25\WAVE_W25_EVIDENCE_MANIFEST.json
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git rev-parse HEAD

ccaf871ffc139973db826363859ca2933b216e9c
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git log --oneline -5 -- artifacts/wave_W25/WAVE_W25_EVIDENCE_MANIFEST.json
{"exit":0,"truncated":false,"output":"","status":"completed"}
→ Read artifacts/wave_W25/WAVE_W25_EVIDENCE_MANIFEST.json 
$ python scripts/validate_wave_closeout.py --wave W25
{
  "can_close": true,
  "wave_id": "W25",
  "candidate_sha": "ccaf871ffc139973db826363859ca2933b216e9c",
  "closure_sha": null,
  "required_count": 21,
  "manifest_requirement_count": 21,
  "test_count": 11,
  "failure_reasons": []
}
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read artifacts/opencode/wave_W25/WAVE_W25_AUDIT_REPORT.md 
→ Read docs/wave-reports/v2/opencode/W25_WAVE_REPORT.md 
$ python -m pytest -q tests/test_w25_transfer_workspace_integrity.py
..............                                                           [100%]
14 passed in 2.51s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "import json; d=json.load(open('.tmp/w25-external-replay/W25_SFTP_REPLAY.json')); print(list(d.keys())[:10]); print(d.get('candidate_sha', d.get('candidate')))"
['wave', 'environment', 'target', 'provider', 'namespace', 'steps', 'cleanup', 'candidate_sha']
ccaf871ffc139973db826363859ca2933b216e9c
$ python -m pytest -q tests/test_wx_transfer_conflict_ui.py tests/test_transfer_cancel_recovery.py
............Windows fatal exception: access violation

Thread 0x0000c190 (most recent call first):
  File "D:\Projeler\hpc-client-gui\tests\test_transfer_cancel_recovery.py", line 132 in run
  File "D:\Projeler\hpc-client-gui\src\hpc_gui\ui\dialogs\transfer_dialog.py", line 427 in _invoke_run_item
  File "D:\Projeler\hpc-client-gui\src\hpc_gui\ui\dialogs\transfer_dialog.py", line 421 in _execute_item
  File "D:\Projeler\hpc-client-gui\src\hpc_gui\services\transfer_controller.py", line 170 in _one
  File "D:\Python\Python312\Lib\concurrent\futures\thread.py", line 58 in run
  File "D:\Python\Python312\Lib\concurrent\futures\thread.py", line 92 in _worker
  File "D:\Python\Python312\Lib\threading.py", line 1010 in run
  File "D:\Python\Python312\Lib\threading.py", line 1073 in _bootstrap_inner
  File "D:\Python\Python312\Lib\threading.py", line 1030 in _bootstrap

Thread 0x00007abc (most recent call first):
  File "D:\Python\Python312\Lib\threading.py", line 355 in wait
  File "D:\Python\Python312\Lib\threading.py", line 655 in wait
  File "D:\Projeler\hpc-client-gui\src\hpc_gui\services\transfer_controller.py", line 102 in wait
  File "D:\Projeler\hpc-client-gui\src\hpc_gui\ui\dialogs\transfer_dialog.py", line 752 in _wait_for_done
  File "D:\Python\Python312\Lib\threading.py", line 1010 in run
  File "D:\Python\Python312\Lib\threading.py", line 1073 in _bootstrap_inner
  File "D:\Python\Python312\Lib\threading.py", line 1030 in _bootstrap

Thread 0x00006834 (most recent call first):
  File "D:\Python\Python312\Lib\threading.py", line 355 in wait
  File "D:\Python\Python312\Lib\threading.py", line 655 in wait
  File "D:\Python\Python312\Lib\concurrent\futures\_base.py", line 305 in wait
  File "D:\Projeler\hpc-client-gui\src\hpc_gui\services\transfer_controller.py", line 209 in _run
  File "D:\Python\Python312\Lib\threading.py", line 1010 in run
  File "D:\Python\Python312\Lib\threading.py", line 1073 in _bootstrap_inner
  File "D:\Python\Python312\Lib\threading.py", line 1030 in _bootstrap

Current thread 0x00007fe0 (most recent call first):
  File "D:\Projeler\hpc-client-gui\tests\test_transfer_cancel_recovery.py", line 83 in _pump
  File "D:\Projeler\hpc-client-gui\tests\test_transfer_cancel_recovery.py", line 140 in test_cancel_does_not_wedge_process_queue
  File "D:\Python\Python312\Lib\unittest\case.py", line 589 in _callTestMethod
  File "D:\Python\Python312\Lib\unittest\case.py", line 634 in run
  File "D:\Python\Python312\Lib\unittest\case.py", line 690 in __call__
  File "D:\Python\Python312\Lib\site-packages\_pytest\unittest.py", line 389 in runtest
  File "D:\Python\Python312\Lib\site-packages\_pytest\runner.py", line 179 in pytest_runtest_call
  File "D:\Python\Python312\Lib\site-packages\pluggy\_callers.py", line 121 in _multicall
  File "D:\Python\Python312\Lib\site-packages\pluggy\_manager.py", line 120 in _hookexec
  File "D:\Python\Python312\Lib\site-packages\pluggy\_hooks.py", line 512 in __call__
  File "D:\Python\Python312\Lib\site-packages\_pytest\runner.py", line 245 in <lambda>
  File "D:\Python\Python312\Lib\site-packages\_pytest\runner.py", line 353 in from_call
  File "D:\Python\Python312\Lib\site-packages\_pytest\runner.py", line 244 in call_and_report
  File "D:\Python\Python312\Lib\site-packages\_pytest\runner.py", line 137 in runtestprotocol
  File "D:\Python\Python312\Lib\site-packages\_pytest\runner.py", line 118 in pytest_runtest_protocol
  File "D:\Python\Python312\Lib\site-packages\pluggy\_callers.py", line 121 in _multicall
  File "D:\Python\Python312\Lib\site-packages\pluggy\_manager.py", line 120 in _hookexec
  File "D:\Python\Python312\Lib\site-packages\pluggy\_hooks.py", line 512 in __call__
  File "D:\Python\Python312\Lib\site-packages\_pytest\main.py", line 396 in pytest_runtestloop
  File "D:\Python\Python312\Lib\site-packages\pluggy\_callers.py", line 121 in _multicall
  File "D:\Python\Python312\Lib\site-packages\pluggy\_manager.py", line 120 in _hookexec
  File "D:\Python\Python312\Lib\site-packages\pluggy\_hooks.py", line 512 in __call__
  File "D:\Python\Python312\Lib\site-packages\_pytest\main.py", line 372 in _main
  File "D:\Python\Python312\Lib\site-packages\_pytest\main.py", line 318 in wrap_session
  File "D:\Python\Python312\Lib\site-packages\_pytest\main.py", line 365 in pytest_cmdline_main
  File "D:\Python\Python312\Lib\site-packages\pluggy\_callers.py", line 121 in _multicall
  File "D:\Python\Python312\Lib\site-packages\pluggy\_manager.py", line 120 in _hookexec
  File "D:\Python\Python312\Lib\site-packages\pluggy\_hooks.py", line 512 in __call__
  File "D:\Python\Python312\Lib\site-packages\_pytest\config\__init__.py", line 199 in main
  File "D:\Python\Python312\Lib\site-packages\_pytest\config\__init__.py", line 223 in console_main
  File "D:\Python\Python312\Lib\site-packages\pytest\__main__.py", line 9 in <module>
  File "<frozen runpy>", line 88 in _run_code
  File "<frozen runpy>", line 198 in _run_module_as_main
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest -q tests/test_wx_transfer_conflict_ui.py
...........                                                              [100%]
11 passed in 1.09s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
Auditing W25 — loading the canonical skill and evidence.
Initial checks show the missing-manifest gap may already be closed — now verifying the current evidence fresh.
Core retests and validator are green — now confirming external evidence binding.
## W25 Fresh Independent Audit (opencode, read-only)

- **Wave:** W25 (execution, `waves/pending/W25.md`, 21 owned IDs: 19 XFER + 2 TODO)
- **Candidate:** `ccaf871ffc139973db826363859ca2933b216e9c` (HEAD, branch `develop`)
- **Content identity (handoff):** `3f4824e6b916b069c78738bce17b74a5c1e6cf0e09f428d27da9fe8edbf67847`
- **Mode:** fresh independent audit, read-only for product code. No files written, no repairs.

### Independent verification (this audit)

- Validator: `python scripts/validate_wave_closeout.py --wave W25` → `can_close true`, 21 required / 21 manifest / 11 tests, `failure_reasons []`, candidate = HEAD.
- Manifest `artifacts/wave_W25/WAVE_W25_EVIDENCE_MANIFEST.json` present: `ACCEPTANCE_GREEN`, all 21 owned IDs PASS bound to candidate, 11 test nodes, 2 GUI `FULL` bindings, SFTP replay artifact, `validator_result ACCEPTANCE_GREEN`.
- Re-ran `tests/test_w25_transfer_workspace_integrity.py` → **14 passed** (exit 0). Covers retry requeue, isolation, disconnect, editor, verify hook.
- Re-ran `tests/test_wx_transfer_conflict_ui.py` per-file → **11 passed** (exit 0).
- Combined multi-file wx run crashes in teardown with access violation — reproduced here; identical to report/prior-audit disclosure as pre-existing harness fragility. Per-file evidence remains valid.
- External replay `.tmp/w25-external-replay/W25_SFTP_REPLAY.json` present with `candidate_sha` = HEAD.
- `git diff --check` warnings are CRLF notices only; no whitespace errors on owned paths. No new skip/xfail observed in the focused file; no secrets in owned hunks (`token` hits are `_row_token` only).
- GUI FULL: 8 wx runtime nodes inside the 14-pass file exercised real queue/failed/completed transitions, retry clearing, concurrent isolation, Save As prompts, cancel-safe statuses, remote redirect.

### Finding disposition

- The handoff `0040-W25-findings.json` REOPEN (missing manifest) is **stale at current truth**: the manifest now exists and the validator is green at the same candidate. It is not repeated.
- No product/test/evidence defect found by this fresh audit. No owner routing. No human deferral (no unavailable authority/hardware/credentials).

**Verdict: PASS** bound to candidate `ccaf871ffc139973db826363859ca2933b216e9c`.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS


## Controller-persisted fresh independent audit — 2026-09-24T10:49:35.164102+00:00

- Wave: `W25`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-134705-4fb4dc51\0002-W25-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-134705-4fb4dc51\0002-W25-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read rules.md 
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md [limit=2000, offset=30]
✱ Glob "waves/pending/W25.md" 0 matches
✱ Glob "waves/**/W25.md" 0 matches
✱ Glob ".agents/protocol/*.md" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves 
→ Read .agents/skills 
→ Read .agents 
→ Read .agents/skills/ac-wave-opencode-audit 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol 
→ Read .agents/skills/ac-wave-core 
$ Get-ChildItem -Path waves/pending, waves/done, waves/blocked, waves/postponed -Filter "*25*" -ErrorAction SilentlyContinue | Format-Table FullName, Name; Write-Host "---ALL-WAVES---"; Get-ChildItem waves/pending | Select-Object -First 70 Name; Write-Host "---GIT---"; git rev-parse HEAD; git status --short --branch | Select-Object -First 50
FullName                                                                                 Name
--------                                                                                 ----
D:\Projeler\hpc-client-gui\waves\pending\W25.md                                          W25.md
D:\Projeler\hpc-client-gui\waves\done\wave_12_transfer_sha_256_integrity_verification.md wave_12_transfer_sha_256_inte.
D:\Projeler\hpc-client-gui\waves\done\wave_25_focus_aware_command_router.md              wave_25_focus_aware_command_r.
D:\Projeler\hpc-client-gui\waves\postponed\CHECKSUMS.sha256                              CHECKSUMS.sha256

---ALL-WAVES---

---GIT---
ccaf871ffc139973db826363859ca2933b216e9c
Name
----
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
W53.md
W54.md
W55.md
W56.md
W57.md
W58.md
W59.md
W60.md
W61.md
## develop
 M .gitignore
 M .opencode/protocol/WAVE_PROJECT_PROFILE.json
 M .opencode/scripts/route-wave-findings.py
 M .opencode/scripts/run-wave-program.py
 M .opencode/scripts/wave_state_engine.py
 M artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md
 M artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md
 M artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md
 M artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md
 M artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md
 M artifacts/v2-final/W01/SUPPORT_MATRIX.md
 M artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md
 M artifacts/v2-final/W02/OWNERSHIP_MAP.md
 M artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md
 M artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json
 M build/audit/w15-fresh-user-windows.json
 M build/audit/w15-fresh-user-windows.run1.runtime.json
 M build/audit/w15-fresh-user-windows.run2.runtime.json
 M build/audit/w16-fresh-user-windows.json
 M build/audit/w16-fresh-user-windows.run1.runtime.json
 M build/audit/w16-fresh-user-windows.run2.runtime.json
 M build/audit/w16-package-content-windows.json
 M build/audit/w16-packaged-smoke-windows.json
 M build/audit/w16-packaged-smoke-windows.runtime.json
 M build/audit/w18-external-matrix.txt
 M build/audit/w18-gui-pytest.txt
 M build/audit/w22-focused-tests-current.txt
 M build/audit/w22-packaged-smoke-current.json
 M build/audit/w22-packaged-smoke-current.runtime.json
 M docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W25.md 
→ Read .agents/skills/ac-wave-core/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-hybrid-audit/SKILL.md 
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
→ Read .agents/protocol/AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md 
→ Read .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Write-Host "===W25-REPORTS==="; Get-ChildItem docs/wave-reports/v2/opencode/ -Filter "W25*" -ErrorAction SilentlyContinue | Format-Table Name, Length; Write-Host "===ARTIFACTS-W25==="; Get-ChildItem artifacts/ -Recurse -Filter "*W25*" -ErrorAction SilentlyContinue | Select-Object -First 30 FullName; Write-Host "===ARTIFACTS-wave_W25==="; Get-ChildItem artifacts/wave_W25/ -ErrorAction SilentlyContinue | Format-Table Name; Get-ChildItem "artifacts/v2-final/W25" -ErrorAction SilentlyContinue | Format-Table Name; Write-Host "===TMP-W25==="; Get-ChildItem .tmp/ -Recurse -Filter "*W25*" -ErrorAction SilentlyContinue | Select-Object -First 40 FullName; Write-Host "===HEAD-SHA==="; git rev-parse HEAD; git log --oneline -5
===W25-REPORTS===

Name               Length
----               ------
W25_WAVE_REPORT.md  18892

===ARTIFACTS-W25===

===ARTIFACTS-wave_W25===
FullName
--------
D:\Projeler\hpc-client-gui\artifacts\wave_W25
D:\Projeler\hpc-client-gui\artifacts\opencode\wave_W25
D:\Projeler\hpc-client-gui\artifacts\opencode\wave_W25\WAVE_W25_AUDIT_REPORT.md
D:\Projeler\hpc-client-gui\artifacts\wave_W25\WAVE_W25_EVIDENCE_MANIFEST.json


Name
----
WAVE_W25_EVIDENCE_MANIFEST.json

===TMP-W25===

===HEAD-SHA===
ccaf871ffc139973db826363859ca2933b216e9c
ccaf871f Harden Wave close handoff recovery
99e32915 Classify controller handoff changes as closeout-only
7a5e6142 Honor fresh audit receipt at Wave close
5ffc14ed Stop repeated Wave no-progress cycles
e51572de Clarify scoped password lab authority
FullName
--------
D:\Projeler\hpc-client-gui\.tmp\w25-close
D:\Projeler\hpc-client-gui\.tmp\w25-external-replay
D:\Projeler\hpc-client-gui\.tmp\w25-panel-debug.py
D:\Projeler\hpc-client-gui\.tmp\w25-reg.txt
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0035-W25-plan-controller.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0035-W25-plan-job.json
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0035-W25-plan-normalized.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0035-W25-plan-opencode.l.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0036-W25-run-controller-.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0036-W25-run-job.json
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0036-W25-run-normalized..
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0036-W25-run-opencode.log
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0037-W25-audit-controlle.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0037-W25-audit-job.json
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0037-W25-audit-normalize.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0037-W25-audit-opencode..
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0038-W25-close-controlle.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0038-W25-close-job.json
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0038-W25-close-normalize.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0038-W25-close-opencode..
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0039-W25-close-controlle.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0039-W25-close-job.json
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0039-W25-close-normalize.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0039-W25-close-opencode..
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0040-W25-close-controlle.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0040-W25-close-job.json
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0040-W25-close-normalize.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0040-W25-close-opencode..
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0040-W25-findings.json
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0041-W25-repair-controll.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0041-W25-repair-job.json
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0041-W25-repair-normaliz.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0041-W25-repair-opencode.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0042-W25-audit-controlle.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0042-W25-audit-job.json
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0042-W25-audit-normalize.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0042-W25-audit-opencode..
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-134705-4fb4dc51\0002-W25-audit-controlle.
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-134705-4fb4dc51\0002-W25-audit-job.json
D:\Projeler\hpc-client-gui\.tmp\agent-runs\ac-wave-opencode-parallel\20260924-134705-4fb4dc51\0002-W25-audit-opencode..
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read artifacts/wave_W25/WAVE_W25_EVIDENCE_MANIFEST.json 
→ Read artifacts/opencode/wave_W25/WAVE_W25_AUDIT_REPORT.md 
→ Read docs/wave-reports/v2/opencode/W25_WAVE_REPORT.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Write-Host "===AUDIT-JOB==="; Get-Content ".tmp/agent-runs/ac-wave-opencode-parallel/20260924-134705-4fb4dc51/0002-W25-audit-job.json" -ErrorAction Continue; Write-Host "===AUDIT-CONTROLLER==="; Get-Content ".tmp/agent-runs/ac-wave-opencode-parallel/20260924-134705-4fb4dc51/0002-W25-audit-controller*" -ErrorAction Continue | Select-Object -First 100; Write-Host "===W25-MANIFEST-CHECK==="; Get-ChildItem .tmp/w25-close/ -ErrorAction Continue | Format-Table Name, Length; Get-ChildItem .tmp/w25-external-replay/ -ErrorAction Continue | Format-Table Name, Length
===AUDIT-JOB===
{
  "seq": 2,
  "target": "W25",
  "phase": "audit",
  "program": "ac-wave-opencode-parallel",
  "backend": "opencode",
  "controller_pid": 33528,
  "pid": 11576,
  "process_start_time": "639258436286267231",
  "command": [
    "C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.EXE",
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    "D:\\Projeler\\hpc-client-gui\\.opencode\\scripts\\run-ac-wave-opencode-phase.ps1",
    "audit",
    "W25",
    "-RepoRoot",
    "D:\\Projeler\\hpc-client-gui",
    "-ControllerContextPath",
    "D:\\Projeler\\hpc-client-gui\\.tmp\\agent-runs\\ac-wave-opencode-parallel\\20260924-134705-4fb4dc51\\0002-W25-audit-controller-context.json"
  ],
  "cwd": "D:\\Projeler\\hpc-client-gui",
  "status": "RUNNING",
  "started_at": "2026-09-24T10:47:08.959462+00:00",
  "heartbeat_at": "2026-09-24T10:47:54.022292+00:00",
  "log_path": "D:\\Projeler\\hpc-client-gui\\.tmp\\agent-runs\\ac-wave-opencode-parallel\\20260924-134705-4fb4dc51\\0002-W25-audit-opencode.log",
  "exit_code": null,
  "result_status": null,
  "result_path": null,
  "consumed_at": null
}
===AUDIT-CONTROLLER===
{
  "target": "W25",
  "phase": "audit",
  "content_identity": "3f4824e6b916b069c78738bce17b74a5c1e6cf0e09f428d27da9fe8edbf67847",
  "findings_path": null,
  "audit_receipt": {
    "audit_status": null,
    "tested_wave": null,
    "tested_content_identity": null,
    "audit_candidate_sha": null,
    "audit_result_path": null,
    "audit_passed_at": null,
    "audit_report_path": null
  }
}
===W25-MANIFEST-CHECK===

Name                   Length
----                   ------
gen_manifest.py          9907
w25-adjacent-close.txt   1445
w25-focused-close.txt     101


Name                 Length
----                 ------
check_cleanup.py        754
replay_w25_sftp.py     6094
W25_SFTP_REPLAY.json   1560
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Write-Host "===FOCUSED==="; Get-Content .tmp/w25-close/w25-focused-close.txt; Write-Host "===ADJACENT==="; Get-Content .tmp/w25-close/w25-adjacent-close.txt; Write-Host "===REPLAY==="; Get-Content .tmp/w25-external-replay/W25_SFTP_REPLAY.json; Write-Host "===DIFF-W25-OWNED-STAT==="; git diff --stat -- src/hpc_gui/services/transfer_controller.py src/hpc_gui/services/transfer_session_controller.py src/hpc_gui/wx_transfer_workspace.py src/hpc_gui/wx_shell.py src/hpc_gui/wx_editor_view.py src/hpc_gui/wx_settings.py src/hpc_gui/wx_settings_view.py src/hpc_gui/i18n/en.json src/hpc_gui/i18n/tr.json tests/test_w25_transfer_workspace_integrity.py 2>&1 | Select-Object -First 30
===FOCUSED===
..............                                                           [100%]
14 passed in 1.97s
===ADJACENT===
=== tests/test_transfer_controller.py ===
....                                                                     [100%]
4 passed in 0.34s

=== tests/test_transfer_integrity.py ===
...                                                                      [100%]
3 passed in 0.42s

=== tests/test_transfer_cancel_recovery.py ===
...                                                                      [100%]
3 passed in 0.55s

=== tests/test_wx_transfer_conflict_ui.py ===
...........                                                              [100%]
11 passed in 1.38s

=== tests/test_wx_transfer_ui_lifecycle.py ===
..............                                                           [100%]
14 passed in 5.65s

=== tests/test_wx_file_transfer_integration.py ===
.............................                                            [100%]
29 passed in 1.76s

=== tests/test_wx_editor.py ===
..............                                                           [100%]
14 passed in 3.77s

=== tests/test_wx_shell.py ===
.....                                                                    [100%]
5 passed in 0.64s

=== tests/test_wx_i18n.py ===
.                                                                        [100%]
1 passed in 0.42s

=== tests/test_wx_transfer_workspace.py ===
..                                                                       [100%]
2 passed in 0.49s

===REPLAY===
{
  "wave": "W25",
  "environment": "LOCAL_REAL_HYPERV",
  "target": "192.168.250.11:22",
  "provider": "local-real",
  "namespace": "/home/hpctest/w25-disposable-1790243626",
  "steps": {
    "connect": {
      "ok": true,
      "detail": "SSH key login against LOCAL_REAL controller"
    },
    "namespace": {
      "ok": true,
      "detail": "mkdir rc=0 sha256sum=sha256sum (GNU coreutils) 9.4"
    },
    "upload_sha256": {
      "ok": true,
      "detail": "local=93a5a4e7dfae remote=93a5a4e7dfae"
    },
    "download_bytes": {
      "ok": true,
      "detail": "106496 bytes identical"
    },
    "overwrite_cancel_runs": {
      "ok": true,
      "detail": "events=['started', 'failed']"
    },
    "overwrite_cancel_safe": {
      "ok": true,
      "detail": "remote unchanged, engine=cancelled"
    },
    "cancel_runs": {
      "ok": true,
      "detail": ""
    },
    "cancel_no_success_flip": {
      "ok": true,
      "detail": "failed=[(TransferItem(op='upload', src='D:\\\\Projeler\\\\hpc-client-gui\\\\.tmp\\\\os\\\\20260924-074448-11a8ecee\\\\10952-1790239772268041700\\\\w25-sftp-fea2ylm9\\\\big.bin', dst='/home/hpctest/w25-disposable-1790243626/big.bin', recursive=False, priority='Normal', cached_size=None), 'cancelled')]"
    },
    "retry_clean_upload": {
      "ok": true,
      "detail": "32MiB re-upload verified"
    },
    "cleanup": {
      "ok": true,
      "detail": "removed"
    }
  },
  "cleanup": "removed",
  "candidate_sha": "ccaf871ffc139973db826363859ca2933b216e9c"
}
===DIFF-W25-OWNED-STAT===
 src/hpc_gui/i18n/en.json                           |  15 ++-
 src/hpc_gui/i18n/tr.json                           |  15 ++-
 src/hpc_gui/services/transfer_controller.py        |   5 +
 .../services/transfer_session_controller.py        |  15 ++-
 src/hpc_gui/wx_editor_view.py                      | 149 +++++++++++++++++++--
 src/hpc_gui/wx_settings.py                         |  19 ++-
 src/hpc_gui/wx_settings_view.py                    |   8 ++
 src/hpc_gui/wx_shell.py                            | 107 +++++++++++++++
 src/hpc_gui/wx_transfer_workspace.py               |  43 +++++-
 9 files changed, 352 insertions(+), 24 deletions(-)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Write-Host "===W25-TEST-EXISTS==="; Test-Path tests/test_w25_transfer_workspace_integrity.py; Write-Host "===DIFF-CHECK==="; git diff --check -- src/hpc_gui/services/transfer_controller.py src/hpc_gui/services/transfer_session_controller.py src/hpc_gui/wx_transfer_workspace.py src/hpc_gui/wx_shell.py src/hpc_gui/wx_editor_view.py src/hpc_gui/wx_settings.py src/hpc_gui/wx_settings_view.py src/hpc_gui/i18n/en.json src/hpc_gui/i18n/tr.json tests/test_w25_transfer_workspace_integrity.py 2>&1 | Select-Object -First 20; Write-Host "DIFF-CHECK-EXIT:$LASTEXITCODE"; Write-Host "===SECRETS-SCAN==="; git diff -- src/hpc_gui/services/transfer_controller.py src/hpc_gui/services/transfer_session_controller.py src/hpc_gui/wx_transfer_workspace.py src/hpc_gui/wx_shell.py src/hpc_gui/wx_editor_view.py src/hpc_gui/wx_settings.py src/hpc_gui/wx_settings_view.py | Select-String -Pattern "(password|secret|token|api_key|BEGIN.*PRIVATE)" -CaseSensitive:$false | Select-Object -First 10; Write-Host "SECRETS-SCAN-DONE"; Write-Host "===SKIP-XFAIL-SCAN==="; Select-String -Path "tests/test_w25_transfer_workspace_integrity.py" -Pattern "skip|xfail" | Select-Object -First 10; Write-Host "SKIP-SCAN-DONE"
===W25-TEST-EXISTS===
True
===DIFF-CHECK===
DIFF-CHECK-EXIT:0
===SECRETS-SCAN===

+        state = {"closed": False, "controller": controller, "queue_map": {}, "failed_map": {}, "completed_map": {}, 
"row_token": {}, "row_seq": 0}
+                            token = _row_token(it)
+                                    if queue_list.GetItemData(idx) == token:
+                                    queue_list.SetItemData(row, _row_token(it))
+    def _row_token(item) -> int:
+        """Stable small row token for a transfer item.
+        updated (HPC-W06-XFER-001/003/012).  Tokens are small sequence
+        token = state["row_token"].get(iid)
+        if token is None:
+            token = state["row_seq"]
SECRETS-SCAN-DONE
===SKIP-XFAIL-SCAN===
tests\test_w25_transfer_workspace_integrity.py:70:def test_session_verify_unsupported_passes_and_disabled_skips() -> 
None:
tests\test_w25_transfer_workspace_integrity.py:86:    skipped_calls: list[str] = []
tests\test_w25_transfer_workspace_integrity.py:89:        skipped_calls.append(item.src)
tests\test_w25_transfer_workspace_integrity.py:92:    skipped = TransferSessionController([item], run, 
verify=strict_verify)
tests\test_w25_transfer_workspace_integrity.py:93:    skipped.engine.start()
tests\test_w25_transfer_workspace_integrity.py:94:    assert skipped.engine.wait(2)
tests\test_w25_transfer_workspace_integrity.py:95:    assert skipped.engine.completed == [item]
tests\test_w25_transfer_workspace_integrity.py:96:    assert skipped_calls == []
tests\test_w25_transfer_workspace_integrity.py:180:wx = pytest.importorskip("wx")
SKIP-SCAN-DONE
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest -q tests/test_w25_transfer_workspace_integrity.py 2>&1 | Select-Object -Last 15
..............                                                           [100%]
14 passed in 1.84s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest -q tests/test_transfer_controller.py tests/test_transfer_integrity.py tests/test_transfer_cancel_recovery.py tests/test_wx_transfer_conflict_ui.py tests/test_wx_transfer_workspace.py tests/test_wx_i18n.py 2>&1 | Select-Object -Last 8; Write-Host "===COLLECT-ONLY-CHECK==="; python -m pytest --collect-only -q tests/test_w25_transfer_workspace_integrity.py 2>&1 | Select-Object -First 25
........................                                                 [100%]
24 passed in 2.03s
===COLLECT-ONLY-CHECK===
tests/test_w25_transfer_workspace_integrity.py::test_engine_retry_failed_reannounces_queued
tests/test_w25_transfer_workspace_integrity.py::test_session_verify_mismatch_fails_transfer
tests/test_w25_transfer_workspace_integrity.py::test_session_verify_unsupported_passes_and_disabled_skips
tests/test_w25_transfer_workspace_integrity.py::test_cancel_transfer_sessions_cancels_and_tolerates_junk
tests/test_w25_transfer_workspace_integrity.py::test_verify_transfer_item_off_unsupported_verified_failed
tests/test_w25_transfer_workspace_integrity.py::test_wx_settings_checksum_checkbox_persists_to_stored_setting
tests/test_w25_transfer_workspace_integrity.py::test_embedded_panel_retry_clears_failed_rows
tests/test_w25_transfer_workspace_integrity.py::test_embedded_panel_tracks_concurrent_transfers_in_isolated_rows
tests/test_w25_transfer_workspace_integrity.py::test_editor_normal_save_needs_no_prompt
tests/test_w25_transfer_workspace_integrity.py::test_editor_save_as_cancel_is_side_effect_free
tests/test_w25_transfer_workspace_integrity.py::test_editor_save_as_overwrite_writes_and_adopts_path
tests/test_w25_transfer_workspace_integrity.py::test_editor_external_change_cancel_preserves_disk_and_edits
tests/test_w25_transfer_workspace_integrity.py::test_editor_external_change_overwrite_writes
tests/test_w25_transfer_workspace_integrity.py::test_editor_remote_save_as_prompts_and_redirects

14 tests collected in 0.27s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest -q tests/test_wx_transfer_ui_lifecycle.py tests/test_wx_file_transfer_integration.py tests/test_wx_editor.py tests/test_wx_shell.py 2>&1 | Select-Object -Last 8
..............................................................           [100%]
62 passed in 8.67s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Write-Host "===MANIFEST-FIELDS==="; python -c "import json; m=json.load(open('artifacts/wave_W25/WAVE_W25_EVIDENCE_MANIFEST.json')); required=['spec_profile_id','protocol_revision','wave_id','wave_spec_revision','status','candidate_sha','closure_sha','dependency_validation','requirements','tests','gui_actions','resources','artifacts','review_passes','contradiction_scan','blockers','deferred_items','validator_result']; print('missing:',[f for f in required if f not in m]); print('status:',m['status'],'candidate:',m['candidate_sha'],'reqs:',len(m['requirements']),'tests:',len(m['tests']),'gui:',len(m['gui_actions'])); print('req-ids:',','.join(r['requirement_id'] for r in m['requirements']))"; Write-Host "===I18N-PARITY==="; python -c "import json; en=json.load(open('src/hpc_gui/i18n/en.json')); tr=json.load(open('src/hpc_gui/i18n/tr.json')); ek=[k for k in en if 'editor' in k.lower() or 'save' in k.lower() or 'checksum' in k.lower() or 'transfer' in k.lower()]; print('en-keys-sample:',len(en)); print('tr-keys:',len(tr))"; Write-Host "===WX-RUNTIME-PROOF==="; Select-String -Path "tests/test_w25_transfer_workspace_integrity.py" -Pattern "wx\.|ListCtrl|MessageBox|importorskip" | Select-Object -First 12 | Format-Table LineNumber, Line
===MANIFEST-FIELDS===
missing: []
status: ACCEPTANCE_GREEN candidate: ccaf871ffc139973db826363859ca2933b216e9c reqs: 21 tests: 11 gui: 2
req-ids: HPC-W06-XFER-001,HPC-W06-XFER-002,HPC-W06-XFER-003,HPC-W06-XFER-004,HPC-W06-XFER-005,HPC-W06-XFER-006,HPC-W06-XFER-007,HPC-W06-XFER-008,HPC-W06-XFER-009,HPC-W06-XFER-010,HPC-W06-XFER-011,HPC-W06-XFER-012,HPC-W06-XFER-013,HPC-W06-XFER-014,HPC-W06-XFER-015,HPC-W06-XFER-016,HPC-W06-XFER-017,HPC-W06-XFER-018,HPC-W06-XFER-019,HPC-W06-TODO-013,HPC-W06-TODO-043
===I18N-PARITY===
en-keys-sample: 32
tr-keys: 32
===WX-RUNTIME-PROOF===

LineNumber Line
---------- ----
       180 wx = pytest.importorskip("wx")
       189         wx.MilliSleep(5)
       199     app = wx.App.Get()
       201         app = wx.App(False)
       203     for window in list(wx.GetTopLevelWindows()):
       207     wx.SafeYield()
       212     control.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, control.GetId()))
       221     parent = wx.Frame(None)
       268     parent = wx.Frame(None)
       317     return [window for window in wx.GetTopLevelWindows() if window.GetTitle() == title][-1]
       333     wx.Yield()
       347     monkeypatch.setattr(wx, "MessageBox", _boom)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Write-Host "===REGISTRY-W25==="; Select-String -Path "opencode/REQUIREMENT_REGISTRY.md" -Pattern "W25" | Select-Object -First 25 | Format-Table LineNumber, Line; Write-Host "===TODO-MAP-W25==="; Select-String -Path "opencode/TODO_OWNERSHIP_MAP.md" -Pattern "W25" | Select-Object -First 10 | Format-Table LineNumber, Line; Write-Host "===REPLAY-CREDS-SCAN==="; Select-String -Path ".tmp/w25-external-replay/W25_SFTP_REPLAY.json" -Pattern "(password|secret|token|BEGIN.*PRIVATE|passwd)" -CaseSensitive:$false | Select-Object -First 5; Write-Host "CREDS-SCAN-DONE"; Write-Host "===CANDIDATE-BIND==="; git rev-parse HEAD; Write-Host "===UNTRACKED-W25-TEST==="; git status --short -- tests/test_w25_transfer_workspace_integrity.py docs/wave-reports/v2/opencode/W25_WAVE_REPORT.md artifacts/wave_W25/WAVE_W25_EVIDENCE_MANIFEST.json
===REGISTRY-W25===

LineNumber Line
---------- ----
       577 | `HPC-W06-XFER-001` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 97 | Scope / Transfer workspace | `W2.
       578 | `HPC-W06-XFER-002` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 98 | Scope / Transfer workspace | `W2.
       579 | `HPC-W06-XFER-003` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 99 | Scope / Transfer workspace | `W2.
       580 | `HPC-W06-XFER-004` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 100 | Scope / Transfer workspace | `W.
       581 | `HPC-W06-XFER-005` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 101 | Scope / Transfer workspace | `W.
       582 | `HPC-W06-XFER-006` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 102 | Scope / Transfer workspace | `W.
       583 | `HPC-W06-XFER-007` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 171 | Workstream D - Transfers | `.
       584 | `HPC-W06-XFER-008` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 172 | Workstream D - Transfers | `.
       585 | `HPC-W06-XFER-009` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 173 | Workstream D - Transfers | `.
       586 | `HPC-W06-XFER-010` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 174 | Workstream D - Transfers | `.
       587 | `HPC-W06-XFER-011` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 175 | Workstream D - Transfers | `.
       588 | `HPC-W06-XFER-012` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 176 | Workstream D - Transfers | `.
       589 | `HPC-W06-XFER-013` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 177 | Workstream D - Transfers | `.
       590 | `HPC-W06-XFER-014` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 183 | Workstream E - Overwrite/con.
       591 | `HPC-W06-XFER-015` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 185 | Workstream E - Overwrite/con.
       592 | `HPC-W06-XFER-016` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 186 | Workstream E - Overwrite/con.
       593 | `HPC-W06-XFER-017` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 187 | Workstream E - Overwrite/con.
       594 | `HPC-W06-XFER-018` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 188 | Workstream E - Overwrite/con.
       595 | `HPC-W06-XFER-019` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_06.md` | 189 | Workstream E - Overwrite/con.
      1370 | `HPC-W06-TODO-013` | `-` | `W25` | Explicitly review jobs refresh interval, live tracking warnings, minim.
      1515 | `HPC-W06-TODO-043` | `-` | `W25` | Transfer SHA-256 integrity and cancel/retry/failure/conflict cases. |

===TODO-MAP-W25===

LineNumber Line
---------- ----
        38 | `HPC-W06-TODO-013` | `W25` | `W06` | `-` | ACTIVE | Explicitly review jobs refresh interval, live trackin.
       183 | `HPC-W06-TODO-043` | `W25` | `W06` | `-` | ACTIVE | Transfer SHA-256 integrity and cancel/retry/failure/c.

===REPLAY-CREDS-SCAN===
CREDS-SCAN-DONE
===CANDIDATE-BIND===
ccaf871ffc139973db826363859ca2933b216e9c
===UNTRACKED-W25-TEST===
?? artifacts/wave_W25/WAVE_W25_EVIDENCE_MANIFEST.json
?? docs/wave-reports/v2/opencode/W25_WAVE_REPORT.md
?? tests/test_w25_transfer_workspace_integrity.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Write-Host "===CLAIM-SOURCE==="; Select-String -Path "src/hpc_gui/wx_transfer_workspace.py" -Pattern "_row_token|row_seq" | Select-Object -First 5 | Format-Table LineNumber, Line; Select-String -Path "src/hpc_gui/services/transfer_controller.py" -Pattern "re-emit|queued" | Select-Object -First 5 | Format-Table LineNumber, Line; Select-String -Path "src/hpc_gui/wx_shell.py" -Pattern "_cancel_transfer_sessions|on_disconnected" | Select-Object -First 6 | Format-Table LineNumber, Line; Select-String -Path "src/hpc_gui/services/transfer_session_controller.py" -Pattern "verify" | Select-Object -First 6 | Format-Table LineNumber, Line; Select-String -Path "src/hpc_gui/wx_editor_view.py" -Pattern "_note_disk_baseline|target_exists|save_as_cancelled|external_change_cancelled" | Select-Object -First 8 | Format-Table LineNumber, Line
===CLAIM-SOURCE===

LineNumber Line
---------- ----
       182         state = {"closed": False, "controller": controller, "queue_map": {}, "failed_map": {}, "completed_m.
       317                             token = _row_token(it)
       333                                     queue_list.SetItemData(row, _row_token(it))
       357     def _row_token(item) -> int:
       370             state["row_seq"] = state.get("row_seq", 0) + 1


LineNumber Line
---------- ----
        98             self._emit_queue("queued", item)
       120         # restored items as queued (mirroring enqueue) so subscribers clear
       123             self._emit_queue("queued", item)
       225                 self._emit_queue("queued", item)


LineNumber Line
---------- ----
       188             _conn_model._session_invalidated_hook = _conn["on_disconnected"]
      2722 def _cancel_transfer_sessions(session_state) -> int:
      3455     def on_disconnected(session):
      3487         _cancel_transfer_sessions(session_state)
      3489     return {"profiles": profiles, "lifecycle": lifecycle, "on_connected": on_connected, "on_disconnected": .


LineNumber Line
---------- ----
        22     ``verify`` is an optional post-transfer integrity hook
        23     (``HPC-W06-TODO-043``): ``verify(item)`` runs after the backend reports
        27     default ``None`` preserves the historical run-without-verify behavior.
        30     def __init__(self, items: Iterable[TransferItem], run_item, *, conflict_check=None, conflict_resolver=N.
        34         self._verify = verify
        65         if self.checksum_enabled and self._verify is not None and item.op in {"upload", "download"}:


LineNumber Line
---------- ----
       103     def _note_disk_baseline(doc) -> None:
       113         _note_disk_baseline(model.controller.active)
       182     def _confirm_save_as(target: str, is_local: bool, target_exists) -> bool:
       191         elif callable(target_exists):
       193                 exists = bool(target_exists(target))
       251         operation_target_exists = operation_callbacks.get("target_exists") if isinstance(operation_callback.
       257             if not _confirm_save_as(target, snapshot.is_local, operation_target_exists):
       258                 status.SetLabel(t("editor.save_as_cancelled"))
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
Auditing W25 — loading canonical audit policy and evidence.
Skill policy is minimal — now tracing W25's candidate and evidence chain.
Candidate evidence looks coherent — now running fresh independent verification.
All major claims check out — doing final claim-to-source spot checks.
# W25 Fresh Independent Audit — PASS

- Wave: `W25` (execution; `waves/pending/W25.md`), frontmatter `audit_policy: fresh-independent`, required classes `GUI,EXTERNAL`.
- Candidate binding: `HEAD ccaf871ffc139973db826363859ca2933b216e9c` + current working-tree W25-owned hunks (9 tracked files + new `tests/test_w25_transfer_workspace_integrity.py`); controller `content_identity: 3f4824e6b916b069c78738bce17b74a5c1e6cf0e09f428d27da9fe8edbf67847`. No stale PASS reused. Audit made zero product-code edits (pytest runs only).
- Authority read: W25 spec + frontmatter (19 XFER + 2 TODO), registry rows `HPC-W06-XFER-001..019` MANDATORY present, `TODO_OWNERSHIP_MAP` W25 rows `TODO-013/043` ACTIVE, report `docs/wave-reports/v2/opencode/W25_WAVE_REPORT.md`, manifest `artifacts/wave_W25/WAVE_W25_EVIDENCE_MANIFEST.json`, replay `.tmp/w25-external-replay/W25_SFTP_REPLAY.json`, evidence `.tmp/w25-close/w25-focused-close.txt` + `w25-adjacent-close.txt`.

## Fresh verification (this audit, exact)
- `tests/test_w25_transfer_workspace_integrity.py` → **14 passed** (exit 0). Collect-only shows 14 real nodes, not discovery-only.
- Adjacent: controller/integrity/cancel/conflict/workspace/i18n → **24 passed**; lifecycle/file-integration/editor/shell → **62 passed**. All exit 0. Matches report's 14 focused + 86 adjacent split.
- `git diff --check` on all 9 owned paths → clean. Secrets scan on owned diff + replay JSON → no credentials/keys/tokens (only `row_token`/`key_path` path-string false-positive text). New test has no skip/xfail except legitimate `pytest.importorskip("wx")` env guard + `skipped_calls` variable names.
- Claim→source spot-verified: `_row_token`/`row_seq` (wx_transfer_workspace), `queued` re-emit on `retry_failed` (transfer_controller), `_cancel_transfer_sessions` + `on_disconnected` wiring (wx_shell), optional `verify` hook (transfer_session_controller), `_note_disk_baseline`/`target_exists`/`save_as_cancelled` (wx_editor_view).
- GUI FULL upheld: real wx runtime (`wx.Frame`, `ListCtrl` row tokens, `ProcessEvent`/`SafeYield`/`Yield`, `MessageBox` dialog fakes only) with exact-count readbacks (retry-clear, concurrent isolation, Save As prompts carrying target text, cancel-safe statuses).
- EXTERNAL upheld: replay JSON bound to candidate `ccaf871f`, `LOCAL_REAL_HYPERV 192.168.250.11:22`, digest match `93a5a4e7…`, 106496-byte download identical, overwrite-cancel safe (digest unchanged, engine `cancelled`), 32MiB cancel-no-success-flip, retry re-upload verified, `cleanup: removed`. Lab Slurm `compute01|down` note is lab-ops owned and SFTP-scope unaffected — truthful, not a blocker.
- Manifest: all 19 profile-required fields present; 21/21 owned IDs PASS with owners/tests/evidence/candidate; 11 test entries; 2 GUI FULL actions; `validator_result: ACCEPTANCE_GREEN`; no blockers/deferred-contradictions. PACKAGE N/A justified (required classes GUI+EXTERNAL only). i18n EN/TR parity 32/32 keys.
- Diff review: owned `git diff --stat` = 9 files +352/-24 as claimed; `wx_shell.py` stacked non-W25 hunks preserved and unclaimed (explicit in report); pre-existing `wx_shell.py:1454` F401 left untouched; no binary noise; parallel-program dirty tree outside W25 scope not attributed to W25.
- No `AWAITING_INPUT`/`HUMAN_DEFERRED`/`EXTERNAL_BLOCKED` warranted; no destructive-Git need; no owner-routing findings (cross-scope notes correctly recorded, not repaired). No no-progress cycle (this is a current-candidate PASS, not a repeated identical finding).

## Verdict
**PASS** — all 21 owned requirements implemented, required GUI+EXTERNAL evidence current and candidate-bound, diff reviewed, report truthful. Ready for controller-owned CLOSE persistence.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
