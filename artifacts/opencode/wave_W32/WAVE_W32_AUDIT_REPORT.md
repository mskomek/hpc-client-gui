# Wave W32 Audit Report
## Controller-persisted fresh independent audit — 2026-09-24T15:16:25.955216+00:00

- Wave: `W32`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0042-W32-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0042-W32-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✱ Glob "waves/**/W32.md" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Get-ChildItem -Path waves -Filter "*32*" -Recurse | Select-Object FullName, DirectoryName | Format-List; Write-Host "---DIRS---"; Get-ChildItem -Path waves | Format-Table Name; Write-Host "---GIT LOG W32---"; git log --oneline -5; Write-Host "---STATUS---"; git status --short | Select-Object -First 30
/usr/bin/bash: line 1: Get-ChildItem: command not found
/usr/bin/bash: line 1: Select-Object: command not found
/usr/bin/bash: line 1: Format-List: command not found
/usr/bin/bash: line 1: Write-Host: command not found
/usr/bin/bash: line 1: Get-ChildItem: command not found
/usr/bin/bash: line 1: Format-Table: command not found
/usr/bin/bash: line 1: Write-Host: command not found
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
54b85bed Sync Agent Core runtime cecc7b82 and migrate Wave profile to schema v3
/usr/bin/bash: line 1: Write-Host: command not found
/usr/bin/bash: line 1: Select-Object: command not found
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls waves/ 2>&1 | head -50; echo "---"; ls waves/pending/ 2>&1 | head -80; echo "---"; ls waves/done/ 2>&1 | head -80
00-START-HERE.md
bak
blocked
done
pending
postponed
waves
---
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
---
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
wave_06_trusted_tool_disclosure.md
wave_07_ansys_diagnostic_explanation_ux.md
wave_07_lumi_provider.md
wave_08_pawsey_setonix_provider.md
wave_08_slurm_directive_editing_model.md
wave_09_slurm_job_arrays.md
wave_09_tacc_stampede3_provider_and_mfa.md
wave_10_cineca_leonardo_provider_and_certificate_auth.md
wave_10_slurm_job_dependencies.md
wave_11_job_failure_explanation.md
wave_11_provider_validation_and_docs_hardening.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W32.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ echo "=== git identity ==="; git rev-parse HEAD; git status --short | head -50; echo "=== content identity check ==="; git log --oneline -3; echo "=== reports ==="; ls -la docs/wave-reports/v2/opencode/ 2>&1 | head -60; echo "=== artifacts ==="; ls -la artifacts/opencode/wave_W32/ 2>&1 | head -60; ls -la artifacts/wave_W32/ 2>&1 | head -60
=== git identity ===
3e9635ba1cf0255d5a09f370e91d1ddb73cef888
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/plugins/installer.py
 M src/hpc_gui/plugins/loader.py
 M src/hpc_gui/plugins/models.py
 M src/hpc_gui/plugins/validator.py
 M src/hpc_gui/services/files_ssh.py
 M src/hpc_gui/services/output_follower.py
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_plugins_view.py
 M src/hpc_gui/wx_shell.py
?? ".agent-legacy-backup (1)/"
?? artifacts/opencode/wave_W26/
?? artifacts/opencode/wave_W27/
?? artifacts/opencode/wave_W28/
?? artifacts/opencode/wave_W29/
?? artifacts/opencode/wave_W30/
?? artifacts/opencode/wave_W31/
?? artifacts/wave_W29/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W29_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W30_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md
?? "new 4.ps1"
?? src/hpc_gui/plugins/discovery.py
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
=== content identity check ===
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
=== reports ===
total 1188
drwxr-xr-x 1 mskomek 197121      0 Sep 24 18:13 .
drwxr-xr-x 1 mskomek 197121      0 Sep 17 14:55 ..
-rw-r--r-- 1 mskomek 197121   3234 Sep 21 22:44 W01_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  32218 Sep 21 22:44 W01_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3449 Sep 21 22:48 W02_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  29941 Sep 21 22:53 W02_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2873 Sep 21 22:55 W03_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  29088 Sep 21 22:55 W03_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2763 Sep 21 22:59 W04_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  25620 Sep 21 22:58 W04_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2479 Sep 21 23:40 W05_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  25994 Sep 21 23:40 W05_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   4746 Sep 22 06:39 W06_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  27695 Sep 21 23:55 W06_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   5066 Sep 22 07:48 W07_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  35939 Sep 22 07:48 W07_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2881 Sep 22 07:58 W08_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  23038 Sep 22 07:58 W08_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3901 Sep 21 17:11 W09_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  21254 Sep 22 08:27 W09_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3843 Sep 21 17:14 W10_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  21296 Sep 22 11:15 W10_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   4467 Sep 22 12:07 W11_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  22271 Sep 22 12:10 W11_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2365 Sep 22 12:46 W12_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  25872 Sep 22 12:49 W12_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3746 Sep 22 13:07 W13_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  40239 Sep 22 13:08 W13_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3986 Sep 21 17:31 W14_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  24145 Sep 22 13:25 W14_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   5438 Sep 22 13:55 W15_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  24155 Sep 22 13:55 W15_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   5187 Sep 22 14:59 W16_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  25482 Sep 22 14:59 W16_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   4392 Sep 22 15:13 W17_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  24822 Sep 22 15:27 W17_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  27464 Sep 22 22:10 W18_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  49040 Sep 22 22:10 W18_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3721 Sep 22 22:35 W19_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  21978 Sep 22 22:35 W19_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   4425 Sep 22 22:54 W20_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  20567 Sep 22 22:54 W20_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3542 Sep 22 23:15 W21_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  27266 Sep 22 23:21 W21_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  65358 Sep 24 10:19 W22_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  42340 Sep 24 10:06 W22_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   8434 Sep 24 11:19 W23_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121 122117 Sep 24 12:10 W24_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  14775 Sep 24 12:07 W24_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  18892 Sep 24 12:59 W25_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  14732 Sep 24 15:41 W26_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  21521 Sep 24 16:09 W27_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  21169 Sep 24 16:28 W28_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  19590 Sep 24 16:49 W29_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  16662 Sep 24 17:22 W30_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  17597 Sep 24 17:45 W31_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  14440 Sep 24 18:13 W32_WAVE_REPORT.md
=== artifacts ===
ls: cannot access 'artifacts/opencode/wave_W32/': No such file or directory
ls: cannot access 'artifacts/wave_W32/': No such file or directory
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md 
$ echo "=== diff stat ==="; git diff --stat HEAD | head -60; echo "=== untracked W32 ==="; git status --short | grep -i -E "w32|plugin|discovery|manifest"; echo "=== W32 test file exists ==="; ls -la tests/test_w32* 2>&1; echo "=== plugin dir ==="; ls -la src/hpc_gui/plugins/ 2>&1
=== diff stat ===
 src/hpc_gui/i18n/en.json                |   8 +
 src/hpc_gui/i18n/tr.json                |   8 +
 src/hpc_gui/plugins/installer.py        |   7 +
 src/hpc_gui/plugins/loader.py           |   7 +
 src/hpc_gui/plugins/models.py           |   5 +
 src/hpc_gui/plugins/validator.py        |  99 +++++++++-
 src/hpc_gui/services/files_ssh.py       |  20 +-
 src/hpc_gui/services/output_follower.py |   5 +
 src/hpc_gui/services/slurm_models.py    |  81 ++++++++
 src/hpc_gui/wx_editor_view.py           | 306 ++++++++++++++++++++++++++++++-
 src/hpc_gui/wx_jobs.py                  | 315 ++++++++++++++++++++++++++++----
 src/hpc_gui/wx_plugins_view.py          |   9 +-
 src/hpc_gui/wx_shell.py                 |  54 +++++-
 13 files changed, 872 insertions(+), 52 deletions(-)
=== untracked W32 ===
 M src/hpc_gui/plugins/installer.py
 M src/hpc_gui/plugins/loader.py
 M src/hpc_gui/plugins/models.py
 M src/hpc_gui/plugins/validator.py
 M src/hpc_gui/wx_plugins_view.py
?? docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md
?? src/hpc_gui/plugins/discovery.py
?? tests/test_w32_discovery_manifest.py
=== W32 test file exists ===
-rw-r--r-- 1 mskomek 197121 17074 Sep 24 18:11 tests/test_w32_discovery_manifest.py
=== plugin dir ===
total 273
drwxr-xr-x 1 mskomek 197121     0 Sep 24 18:12 .
drwxr-xr-x 1 mskomek 197121     0 Sep 24 18:12 ..
-rw-r--r-- 1 mskomek 197121   280 Aug 25 14:49 __init__.py
drwxr-xr-x 1 mskomek 197121     0 Sep 24 18:12 __pycache__
-rw-r--r-- 1 mskomek 197121 12577 Sep 16 16:29 compatibility.py
-rw-r--r-- 1 mskomek 197121  8440 Sep 24 18:06 discovery.py
-rw-r--r-- 1 mskomek 197121  4150 Aug 25 14:49 downloader.py
-rw-r--r-- 1 mskomek 197121 18704 Sep 24 18:12 installer.py
-rw-r--r-- 1 mskomek 197121 10174 Aug 30 14:43 integrity.py
-rw-r--r-- 1 mskomek 197121 11169 Sep  6 17:18 job_templates.py
-rw-r--r-- 1 mskomek 197121  9578 Sep  1 18:07 linter_tools.py
-rw-r--r-- 1 mskomek 197121 17280 Sep 24 18:12 loader.py
-rw-r--r-- 1 mskomek 197121 11236 Sep 24 18:12 models.py
-rw-r--r-- 1 mskomek 197121  8833 Sep 16 16:29 registry_client.py
-rw-r--r-- 1 mskomek 197121  4501 Sep 14 14:32 schema_compat.py
-rw-r--r-- 1 mskomek 197121  7430 Aug 30 14:31 state.py
-rw-r--r-- 1 mskomek 197121  4738 Aug 30 14:31 storage.py
-rw-r--r-- 1 mskomek 197121  1879 Sep 16 16:29 templates.py
-rw-r--r-- 1 mskomek 197121  1427 Aug 31 23:37 trusted_tools.py
-rw-r--r-- 1 mskomek 197121 29969 Sep  6 17:20 ui_contributions.py
-rw-r--r-- 1 mskomek 197121 34227 Sep 24 18:12 validator.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls opencode/ 2>&1 | head -30; echo "==="; ls docs/wave-reports/v2/opencode/W32* 2>&1; echo "==="; find . -maxdepth 3 -name "REQUIREMENT_REGISTRY.md" 2>&1 | head; find . -maxdepth 3 -name "WAVE_V2_FINAL_08.md" 2>&1 | head
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
===
docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md
===
./opencode/REQUIREMENT_REGISTRY.md
./opencode/sources/WAVE_V2_FINAL_08.md
./waves/bak/WAVE_V2_FINAL_08.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "
import re
text=open('opencode/REQUIREMENT_REGISTRY.md',encoding='utf-8').read()
# Find W32 rows
for i,line in enumerate(text.splitlines(),1):
    if 'W32' in line or 'HPC-W08-DISC' in line or 'HPC-W08-MANIFEST' in line:
        print(f'{i}: {line[:400]}')
"
769: | `HPC-W08-DISC-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 74 | Workstream A � Discovery sources | `W32` | � | bundled; |
770: | `HPC-W08-DISC-002` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 75 | Workstream A � Discovery sources | `W32` | � | user-installed; |
771: | `HPC-W08-DISC-003` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 76 | Workstream A � Discovery sources | `W32` | � | configured path; |
772: | `HPC-W08-DISC-004` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 77 | Workstream A � Discovery sources | `W32` | � | entry point/package mechanism; |
773: | `HPC-W08-DISC-005` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 78 | Workstream A � Discovery sources | `W32` | � | development path. |
1278: | `HPC-W08-MANIFEST-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 89 | Workstream B � Manifest / metadata contract | `W32` | � | Plugin manifest/metadata validation includes plugin ID. |
1279: | `HPC-W08-MANIFEST-002` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 90 | Workstream B � Manifest / metadata contract | `W32` | � | Plugin manifest/metadata validation includes display name. |
1280: | `HPC-W08-MANIFEST-003` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 91 | Workstream B � Manifest / metadata contract | `W32` | � | Plugin manifest/metadata validation includes plugin version. |
1281: | `HPC-W08-MANIFEST-004` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 92 | Workstream B � Manifest / metadata contract | `W32` | � | Plugin manifest/metadata validation includes API/schema compatibility version. |
1282: | `HPC-W08-MANIFEST-005` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 77 | Workstream B � Manifest / metadata contract | `W32` | � | Plugin manifest/metadata validation includes entry point. |
1283: | `HPC-W08-MANIFEST-006` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 94 | Workstream B � Manifest / metadata contract | `W32` | � | Plugin manifest/metadata validation includes provider IDs/capabilities if applicable. |
1284: | `HPC-W08-MANIFEST-007` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 64 | Workstream B � Manifest / metadata contract | `W32` | � | Plugin manifest/metadata validation includes optional dependencies. |
1285: | `HPC-W08-MANIFEST-008` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 98 | Workstream B � Manifest / metadata contract | `W32` | � | Malformed or incompatible plugin metadata is rejected with a contained diagnostic. |
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "
text=open('opencode/TODO_OWNERSHIP_MAP.md',encoding='utf-8').read()
found=False
for i,line in enumerate(text.splitlines(),1):
    if 'W32' in line:
        print(f'{i}: {line[:400]}'); found=True
if not found: print('NO W32 ROWS (expected none)')
"; echo "=== source sections ==="; grep -n "Workstream" opencode/sources/WAVE_V2_FINAL_08.md | head -20
NO W32 ROWS (expected none)
=== source sections ===
70:## Workstream A — Discovery sources
84:## Workstream B — Manifest / metadata contract
100:## Workstream C — Enable/disable semantics
111:## Workstream D — Isolation
125:## Workstream E — Duplicate/conflict handling
137:## Workstream F — Provider registration
149:## Workstream G — Settings ownership
162:## Workstream H — Packaged discovery
174:## Workstream H0 — wx Plugin Manager as a real functional GUI
208:## Workstream I — Documentation contract
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read opencode/sources/WAVE_V2_FINAL_08.md [limit=160, offset=60]
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read tests/test_w32_discovery_manifest.py 
→ Read src/hpc_gui/plugins/discovery.py 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_w32_discovery_manifest.py -q 2>&1 | tail -15
...................                                                      [100%]
19 passed in 0.54s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_plugin_core.py tests/test_plugin_schema_compat.py tests/test_plugin_security.py tests/test_plugin_installer.py tests/test_plugin_integrity.py tests/test_wx_plugins.py tests/test_w08_schema_isolation.py -q 2>&1 | tail -8; echo "=== diff check ==="; git diff --check 2>&1 | head -20; echo "=== validator diff ==="; git diff -- src/hpc_gui/plugins/validator.py src/hpc_gui/plugins/models.py src/hpc_gui/plugins/loader.py src/hpc_gui/plugins/installer.py --stat
........................................................................ [ 47%]
........................................................................ [ 94%]
.........                                                                [100%]
153 passed in 4.02s
=== diff check ===
=== validator diff ===
diff --git a/src/hpc_gui/plugins/installer.py b/src/hpc_gui/plugins/installer.py
index fff97f98..fbeb0e4f 100644
--- a/src/hpc_gui/plugins/installer.py
+++ b/src/hpc_gui/plugins/installer.py
@@ -124,6 +124,8 @@ def _build_manifest(raw: dict[str, Any]) -> PluginManifest:
         )
         for entry in raw["files"]
     )
+    provider_ids = raw.get("provider_ids") or []
+    optional_dependencies = raw.get("optional_dependencies") or []
     return PluginManifest(
         schema_version=raw["schema_version"],
         plugin_api=raw["plugin_api"],
@@ -137,6 +139,11 @@ def _build_manifest(raw: dict[str, Any]) -> PluginManifest:
         capabilities=tuple(raw["capabilities"]),
         entrypoints=dict(raw.get("entrypoints") or {}),
         files=files,
+        provider_ids=tuple(provider_ids) if isinstance(provider_ids, list) else (),
+        optional_dependencies=tuple(
+            dict(entry) if isinstance(entry, dict) else entry
+            for entry in optional_dependencies
+        ) if isinstance(optional_dependencies, list) else (),
     )
 
 
diff --git a/src/hpc_gui/plugins/loader.py b/src/hpc_gui/plugins/loader.py
index 46c02d68..2a89b282 100644
--- a/src/hpc_gui/plugins/loader.py
+++ b/src/hpc_gui/plugins/loader.py
@@ -89,6 +89,8 @@ def _build_manifest(raw: Any) -> tuple[PluginManifest | None, str | None]:
     ui_contributions = raw.get("ui_contributions")
     if not isinstance(ui_contributions, dict) and ui_contributions is not None:
         ui_contributions = None
+    provider_ids = raw.get("provider_ids") or []
+    optional_dependencies = raw.get("optional_dependencies") or []
     manifest = PluginManifest(
         schema_version=raw["schema_version"],
         plugin_api=raw["plugin_api"],
@@ -103,6 +105,11 @@ def _build_manifest(raw: Any) -> tuple[PluginManifest | None, str | None]:
         entrypoints=dict(raw.get("entrypoints") or {}),
         files=files,
         ui_contributions=dict(ui_contributions) if isinstance(ui_contributions, dict) else None,
+        provider_ids=tuple(provider_ids) if isinstance(provider_ids, list) else (),
+        optional_dependencies=tuple(
+            dict(entry) if isinstance(entry, dict) else entry
+            for entry in optional_dependencies
+        ) if isinstance(optional_dependencies, list) else (),
     )
     return manifest, None
 
diff --git a/src/hpc_gui/plugins/models.py b/src/hpc_gui/plugins/models.py
index 4f722146..8e0c981e 100644
--- a/src/hpc_gui/plugins/models.py
+++ b/src/hpc_gui/plugins/models.py
@@ -77,6 +77,11 @@ class PluginManifest:
     entrypoints: Mapping[str, Any]
     files: tuple[PluginFile, ...]
     ui_contributions: Mapping[str, Any] | None = None
+    # W32 Workstream B: optional provider/capability and dependency metadata.
+    # Both are advisory: they never grant loading, execution, or capability
+    # beyond what capabilities/entrypoints already allow.
+    provider_ids: tuple[str, ...] = ()
+    optional_dependencies: tuple[Any, ...] = ()
 
 
 @dataclass(frozen=True)
diff --git a/src/hpc_gui/plugins/validator.py b/src/hpc_gui/plugins/validator.py
index 4641b689..f3beb07c 100644
--- a/src/hpc_gui/plugins/validator.py
+++ b/src/hpc_gui/plugins/validator.py
@@ -44,7 +44,12 @@ MANIFEST_REQUIRED_KEYS = (
     "files",
 )
 
-MANIFEST_OPTIONAL_KEYS = frozenset({"ui_contributions"})
+MANIFEST_OPTIONAL_KEYS = frozenset({"ui_contributions", "provider_ids", "optional_dependencies"})
+
+# W32 Workstream B: provider-id shape. Provider ids name concrete provider
+# capabilities (e.g. cluster profile ids); they use the same safe alphabet
+# as cluster profile ids.
+PROVIDER_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
 
 CLUSTER_PROFILE_REQUIRED_KEYS = ("schema_version", "profile_id", "name", "scheduler")
 V2_PROFILE_SECTIONS = frozenset(
@@ -170,6 +175,22 @@ def validate_manifest_dict(manifest: Any) -> list[str]:
     for key in ("id", "name", "publisher", "license", "description"):
         if not _is_nonempty_str(manifest[key]):
             errors.append(f"manifest key '{key}' must be a non-empty string")
+    # W32 MANIFEST-001: plugin ID uses a dotted reverse-DNS shape so two
+    # plugins cannot silently shadow each other with free-form names.
+    # The validator accepts hyphens/underscores in segments (compatible
+    # with historical manifests such as `test.unicode-provider`); the
+    # loader still enforces the exact `PLUGIN_ID_RE` at load time, so any
+    # residual mismatch is contained as a load diagnostic, never startup.
+    _PLUGIN_ID_VALIDATOR_RE = re.compile(r"^[a-z][a-z0-9_-]*(?:\.[a-z0-9_-]+)+$")
+
+    if _is_nonempty_str(manifest["id"]) and not _PLUGIN_ID_VALIDATOR_RE.fullmatch(str(manifest["id"])):
+        errors.append(
+            "manifest key 'id' must match ^[a-z][a-z0-9_-]*(?:\\.[a-z0-9_-]+)+$ "
+            f"(got {manifest['id']!r})"
+        )
+    # W32 MANIFEST-002: display name is a bounded human label (not an id).
+    if _is_nonempty_str(manifest["name"]) and len(str(manifest["name"])) > 128:
+        errors.append("manifest key 'name' must be at most 128 characters")
     if not _is_nonempty_str(manifest["requires_app"]):
         errors.append("manifest key 'requires_app' must be a non-empty string")
     else:
@@ -241,6 +262,82 @@ def validate_manifest_dict(manifest: Any) -> list[str]:
         ui_errors = validate_ui_contributions_dict(manifest["ui_contributions"])
         errors.extend(f"ui_contributions: {e}" for e in ui_errors)
 
+    # W32 MANIFEST-006: optional provider IDs / capabilities declaration.
+    # Advisory only: never grants loading or execution by itself.
+    if "provider_ids" in manifest:
+        provider_ids = manifest["provider_ids"]
+        if not isinstance(provider_ids, list):
+            errors.append("manifest provider_ids must be a list")
+        else:
+            seen_providers: set[str] = set()
+            for entry in provider_ids:
+                if not isinstance(entry, str) or not entry.strip():
+                    errors.append("each manifest provider_ids entry must be a non-empty string")
+                    continue
+                if len(entry) > 64 or not PROVIDER_ID_RE.fullmatch(entry):
+                    errors.append(
+                        f"invalid provider id {entry!r}: must match ^[a-z][a-z0-9_-]*$ "
+                        "and be at most 64 characters"
+                    )
+                    continue
+                if entry in seen_providers:
+                    errors.append(f"duplicate provider id {entry!r}")
+                    continue
+                seen_providers.add(entry)
+
+    # W32 MANIFEST-007: optional dependencies. Advisory only: a missing
+    # optional dependency must never block host startup or sibling plugins;
+    # the loader treats the declaring plugin normally (the dependency is
+    # documentation for the registry/operator, not a load gate).
+    if "optional_dependencies" in manifest:
+        optional_deps = manifest["optional_dependencies"]
+        if not isinstance(optional_deps, list):
+            errors.append("manifest optional_dependencies must be a list")
+        else:
+            seen_deps: set[str] = set()
+            for entry in optional_deps:
+                dep_id: Any = entry
+                dep_version: Any = None
+                if isinstance(entry, dict):
+                    dep_id = entry.get("id")
+                    dep_version = entry.get("version", None)
+                    unknown_dep_keys = set(entry) - {"id", "version"}
+                    if unknown_dep_keys:
+                        errors.append(
+                            f"manifest optional_dependencies entry has unknown keys "
+                            f"{sorted(unknown_dep_keys)}"
+                        )
+                        continue
+                elif not isinstance(entry, str):
+                    errors.append(
+                        "each manifest optional_dependencies entry must be a string "
+                        "or an object with an 'id'"
+                    )
+                    continue
+                if not isinstance(dep_id, str) or not dep_id.strip():
+                    errors.append(
+                        "each manifest optional_dependencies entry needs a non-empty 'id'"
+                    )
+                    continue
+                if len(dep_id) > 128:
+                    errors.append(
+                        f"optional dependency id {dep_id!r} must be at most 128 characters"
+                    )
+                    continue
+                if any(ch in dep_id for ch in ("\n", "\r", "\x00", "/", "\\", "..")):
+                    errors.append(f"optional dependency id {dep_id!r} is unsafe")
+                    continue
+                if dep_version is not None and not is_valid_semver(dep_version):
+                    errors.append(
+                        f"optional dependency {dep_id!r} version {dep_version!r} "
+                        "is not a valid semantic version"
+                    )
+                    continue
+                if dep_id in seen_deps:
+                    errors.append(f"duplicate optional dependency {dep_id!r}")
+                    continue
+                seen_deps.add(dep_id)
+
     files = manifest["files"]
     if not isinstance(files, list) or not files:
         errors.append("manifest files must be a non-empty list")
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_wave6_plugin_provider_unicode.py::TestIntegration::test_full_plugin_unicode_flow -q 2>&1 | tail -20
"squeue_command": 'squeue -h -u {user} -o "%i|%P|%j|%u|%T|%M|%D|%C|%R"',
                "sbatch_command": "cd -- {script_dir_q} && sbatch -- {script_name_q}",
                "scancel_command": "scancel {job_id_q}",
                "sacct_command": 'sacct -n -P -u {user} --format=JobIDRaw,JobName,State,Elapsed,MaxRSS,AllocTRES,ExitCode',
                "scontrol_command": "scontrol show job {job_id_q}",
                "status_command": "lssrv",
            },
        }
    
        # 5. Validate profile
        errors = validate_cluster_profile_dict(profile_dict)
>       assert len(errors) == 0, f"Profile validation errors: {errors}"
E       AssertionError: Profile validation errors: ["cluster profile 'storage[0]' needs a non-empty id"]
E       assert 1 == 0
E        +  where 1 = len(["cluster profile 'storage[0]' needs a non-empty id"])

tests\test_wave6_plugin_provider_unicode.py:377: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_wave6_plugin_provider_unicode.py::TestIntegration::test_full_plugin_unicode_flow
1 failed in 0.64s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "
import subprocess
# Check if this failure involves W32-owned files: does the test touch validator/discovery/loader manifest paths?
text=open('tests/test_wave6_plugin_provider_unicode.py',encoding='utf-8').read()
print('uses validator:', 'validator' in text)
print('uses discovery:', 'discovery' in text)
print('uses storage shape:', 'storage' in text[:2000])
"; echo "==="; python -m pytest tests/test_plugin_core.py tests/test_plugin_schema_compat.py -q --collect-only 2>&1 | tail -3; echo "=== check validator history: does HEAD version accept the unicode manifest? ==="; git show HEAD:src/hpc_gui/plugins/validator.py | grep -n "storage\[0\]\|needs a non-empty id" | head -5
uses validator: True
uses discovery: False
uses storage shape: True
===
tests/test_plugin_schema_compat.py::test_plugin_infrastructure_baseline_is_release_fact

52 tests collected in 0.58s
=== check validator history: does HEAD version accept the unicode manifest? ===
138:                errors.append(f"cluster profile '{section_key}[{index}]' needs a non-empty id")
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/ -k "plugin" -q --deselect tests/test_wave6_plugin_provider_unicode.py::TestIntegration::test_full_plugin_unicode_flow 2>&1 | tail -6
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
=========================== short test summary info ===========================
ERROR tests/contracts (1)/test_wave_closeout_hardening.py
ERROR tests/contracts (2)/test_wave_closeout_hardening.py
!!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!
2872 deselected, 2 errors in 3.00s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/ -k "plugin" -q --deselect tests/test_wave6_plugin_provider_unicode.py::TestIntegration::test_full_plugin_unicode_flow --ignore="tests/contracts (1)" --ignore="tests/contracts (2)" 2>&1 | tail -6
.........................................ssssssssssssssssssss........... [ 22%]
........................................................................ [ 44%]
........................................................................ [ 66%]
.......................................ssss...s..............ssssss..... [ 88%]
....................................                                     [100%]
293 passed, 31 skipped, 2872 deselected in 14.17s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "
import re,pathlib
files=['src/hpc_gui/plugins/discovery.py','src/hpc_gui/plugins/validator.py','src/hpc_gui/plugins/models.py','src/hpc_gui/plugins/loader.py','src/hpc_gui/plugins/installer.py','tests/test_w32_discovery_manifest.py']
import subprocess
for f in files:
    t=open(f,encoding='utf-8').read()
    hits=re.findall(r'(?i)(api_key|secret|password|BEGIN [A-Z ]*PRIVATE KEY|token\s*=\s*[\"\\'][A-Za-z0-9]{16})',t)
    print(f, 'secret-hits:', hits if hits else 'none')
print('diff-check done earlier: clean')
print('untracked owned:', 'discovery.py + test file only')
"
src/hpc_gui/plugins/discovery.py secret-hits: none
src/hpc_gui/plugins/validator.py secret-hits: none
src/hpc_gui/plugins/models.py secret-hits: none
src/hpc_gui/plugins/loader.py secret-hits: none
src/hpc_gui/plugins/installer.py secret-hits: none
tests/test_w32_discovery_manifest.py secret-hits: none
diff-check done earlier: clean
untracked owned: discovery.py + test file only
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
Auditing W32 — pulling the canonical skill and wave truth.
Run report shows ready for audit — now digging into requirements and test evidence.
Core tests check out — now verifying the one known failure is truly out of scope.
Fresh independent audit of W32 complete (read-only for product code; no repairs made).

**Scope verified:** 13 owned IDs (`HPC-W08-DISC-001..005`, `HPC-W08-MANIFEST-001..008`) from `waves/pending/W32.md` frontmatter; `TODO_OWNERSHIP_MAP.md` has no W32 rows (correct empty reading); mandatory source sections Workstream A + B of `WAVE_V2_FINAL_08.md` preserved.

**Requirement → owner → test → evidence (all green):**
- DISC-001..005 → `plugins/discovery.py` (5-source enumeration, 1 active) + loader/storage → 8 discovery tests incl. CWD-isolation (`monkeypatch.chdir` + reload), precedence/identity determinism, duplicate-winner `aaa` — passed.
- MANIFEST-001 (ID shape) → `validator.py` reverse-DNS RE + loader `PLUGIN_ID_RE` gate → passed; historical `test.unicode-provider` shape still accepted.
- MANIFEST-002 (name ≤128) → passed. 003 (semver) → passed. 004 (plugin_api allow-list + requires_app + `is_app_compatible`) → passed. 005 (entrypoints object + v2 `__init__.py` rule + contained loader problem) → passed. 006 (provider_ids safe-alphabet/max64/dedupe, preserved through loader/installer) → passed. 007 (optional_dependencies advisory; missing dep does not block load) → passed. 008 (broken JSON + incompatible app isolated, sibling loads, problems non-empty) → passed.

**Test evidence (exact, re-run by auditor):**
- `tests/test_w32_discovery_manifest.py`: **19 passed**.
- Focused regression (`plugin_core + schema_compat + security + installer + integrity + wx_plugins + w08_schema_isolation`): **153 passed**.
- Broader plugin sweep (`-k plugin`, deselecting 1 known failure, ignoring 2 stray sibling `contracts (N)` dirs): **293 passed, 31 skipped** (Qt-gated).
- `git diff --check`: clean. No secrets in owned files. No weakened tests.

**GUI class (required):** headless `WxPluginManagerModel` test (installed card + disabled persistence under same root, CWD untouched) passed within the 19; maintained `test_wx_plugins.py` green. Real-file/loader/model proof, not static-only.

**Negative/lifecycle:** malformed JSON, bad semver/requires_app, unsafe/duplicate provider ids, malformed optional deps, duplicate profile ids, CWD fake tree, sibling-isolation all exercised. No network/registry use → Package N/A and External N/A justifications accepted.

**Findings disposition:**
- OBS (pre-existing, routed, non-blocking): `test_wave6 ... test_full_plugin_unicode_flow` fails on `validate_cluster_profile_dict` storage-shape gate that exists verbatim at HEAD `3e9635ba` — untouched by the W32 validator diff. Correctly routed to stable owner.
- Stray `tests/contracts (1)/(2)` collection errors are sibling-owned untracked dirs, not W32.

**Candidate identity:** HEAD `3e9635ba1cf0255d5a09f370e91d1ddb73cef888` + owned working-tree additions (5 plugin files + new `discovery.py` + new test + canonical report). Content-identity note in report is controller-owned reconciliation, not a defect.

No owned blocking defect remains. Audit verdict: **PASS**.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS


## Controller-persisted fresh independent audit — 2026-09-24T15:22:51.553845+00:00

- Wave: `W32`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0045-W32-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0045-W32-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md [limit=2000, offset=30]
→ Read .tmp/agent-runs/ac-wave-opencode-parallel/20260924-152940-c05dfd9c/0043-W32-findings.json 
→ Read .tmp/agent-runs/ac-wave-opencode-parallel/20260924-152940-c05dfd9c/0042-W32-audit-normalized.json 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Skill "ac-wave-core" 
→ Read waves/pending/W32.md 
→ Read artifacts/opencode/wave_W32/WAVE_W32_AUDIT_REPORT.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol/AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md 
→ Read .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md 
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git rev-parse HEAD; echo "---STATUS---"; git status --short | head -n 100; echo "---W32LOC---"; ls waves/pending/W32.md waves/done/W32.md 2>&1; echo "---ARTIFACTS---"; ls artifacts/wave_W32/ 2>&1; ls artifacts/opencode/wave_W32/ 2>&1; echo "---REPORTS---"; ls docs/wave-reports/v2/opencode/W32* 2>&1
3e9635ba1cf0255d5a09f370e91d1ddb73cef888
---STATUS---
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/plugins/installer.py
 M src/hpc_gui/plugins/loader.py
 M src/hpc_gui/plugins/models.py
 M src/hpc_gui/plugins/validator.py
 M src/hpc_gui/services/files_ssh.py
 M src/hpc_gui/services/output_follower.py
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
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
?? artifacts/wave_W29/
?? artifacts/wave_W32/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W29_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W30_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md
?? "new 4.ps1"
?? src/hpc_gui/plugins/discovery.py
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
---W32LOC---
ls: cannot access 'waves/done/W32.md': No such file or directory
waves/pending/W32.md
---ARTIFACTS---
WAVE_W32_EVIDENCE_MANIFEST.json
WAVE_W32_AUDIT_REPORT.md
---REPORTS---
docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ echo "=== wave_W32 ==="; ls -la artifacts/wave_W32/; echo "=== opencode wave_W32 ==="; ls -la artifacts/opencode/wave_W32/; echo "=== manifest head ==="; head -c 4000 artifacts/wave_W32/WAVE_W32_EVIDENCE_MANIFEST.json 2>&1 | head -n 200
python -c "import json; d=json.load(open('artifacts/wave_W32/WAVE_W32_EVIDENCE_MANIFEST.json')); print(list(d.keys())); print('status',d.get('status')); print('candidate',d.get('candidate_sha')); print('reqs',len(d.get('requirements',[]))); print('tests',len(d.get('tests',[])))"
=== wave_W32 ===
total 20
drwxr-xr-x 1 mskomek 197121     0 Sep 24 18:19 .
drwxr-xr-x 1 mskomek 197121     0 Sep 24 18:19 ..
-rw-r--r-- 1 mskomek 197121 13477 Sep 24 18:19 WAVE_W32_EVIDENCE_MANIFEST.json
=== opencode wave_W32 ===
total 44
drwxr-xr-x 1 mskomek 197121     0 Sep 24 18:16 .
drwxr-xr-x 1 mskomek 197121     0 Sep 24 18:16 ..
-rw-r--r-- 1 mskomek 197121 37621 Sep 24 18:16 WAVE_W32_AUDIT_REPORT.md
=== manifest head ===
{
 "spec_profile_id": "HPC",
 "protocol_revision": 2,
 "wave_id": "W32",
 "wave_spec_revision": "sha256:4dac42cccf01cc26a1e6ce04bbb850926e89ec3c61bcc05c772f5c042252dfbe",
 "status": "ACCEPTANCE_GREEN",
 "candidate_sha": "3e9635ba1cf0255d5a09f370e91d1ddb73cef888",
 "closure_sha": null,
 "dependency_validation": {
  "dependencies": []
 },
 "requirements": [
  {
   "requirement_id": "HPC-W08-DISC-001",
   "mandatory": true,
   "disposition": "PASS",
   "implementation_owners": [
    "src/hpc_gui/plugins/discovery.py"
   ],
   "test_nodes": [
    "tests/test_w32_discovery_manifest.py::test_disc_all_five_sources_enumerated",
    "tests/test_w32_discovery_manifest.py::test_disc_bundled_is_not_active",
    "tests/test_w32_discovery_manifest.py::test_disc_precedence_and_identity_deterministic",
    "tests/test_w32_discovery_manifest.py::test_disc_duplicate_profile_deterministic"
   ],
   "expected_semantics": "five-source enumeration; bundled source present but never active; deterministic precedence and registry identity",
   "evidence_refs": [
    "docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md",
    "artifacts/opencode/wave_W32/WAVE_W32_AUDIT_REPORT.md",
    ".tmp/w32-repair/w32-focused.txt",
    "tests/test_w32_discovery_manifest.py"
   ],
   "candidate_sha": "3e9635ba1cf0255d5a09f370e91d1ddb73cef888"
  },
  {
   "requirement_id": "HPC-W08-DISC-002",
   "mandatory": true,
   "disposition": "PASS",
   "implementation_owners": [
    "src/hpc_gui/plugins/loader.py",
    "src/hpc_gui/plugins/storage.py",
    "src/hpc_gui/plugins/discovery.py"
   ],
   "test_nodes": [
    "tests/test_w32_discovery_manifest.py::test_disc_user_installed_loads",
    "tests/test_w32_discovery_manifest.py::test_gui_manager_surfaces_discovery_state"
   ],
   "expected_semantics": "user-installed plugins load from explicit root with manifest+profile round trip; manager model surfaces installed state",
   "evidence_refs": [
    "docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md",
    "artifacts/opencode/wave_W32/WAVE_W32_AUDIT_REPORT.md",
    ".tmp/w32-repair/w32-focused.txt",
    "tests/test_w32_discovery_manifest.py"
   ],
   "candidate_sha": "3e9635ba1cf0255d5a09f370e91d1ddb73cef888"
  },
  {
   "requirement_id": "HPC-W08-DISC-003",
   "mandatory": true,
   "disposition": "PASS",
   "implementation_owners": [
    "src/hpc_gui/plugins/storage.py",
    "src/hpc_gui/plugins/discovery.py"
   ],
   "test_nodes": [
    "tests/test_w32_discovery_manifest.py::test_disc_configured_path_override_is_isolated"
   ],
   "expected_semantics": "configured path override is isolated per explicit root; other roots unaffected",
   "evidence_refs": [
    "docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md",
    "artifacts/opencode/wave_W32/WAVE_W32_AUDIT_REPORT.md",
    ".tmp/w32-repair/w32-focused.txt",
    "tests/test_w32_discovery_manifest.py"
   ],
   "candidate_sha": "3e9635ba1cf0255d5a09f370e91d1ddb73cef888"
  },
  {
   "requirement_id": "HPC-W08-DISC-004",
   "mandatory": true,
   "disposition": "PASS",
   "implementation_owners": [
    "src/hpc_gui/plugins/discovery.py",
    "src/hpc_gui/plugins/loader.py"
   ],
   "test_nodes": [
    "tests/test_w32_discovery_manifest.py::test_disc_entry_point_mechanism_never_executes"
   ],
   "expected_semantics": "entry-point/package mechanism never executes code; manifest entrypoints are relative declarative paths; loader has no importlib/exec/eval/subprocess",
   "evidence_refs": [
    "docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md",
    "artifacts/opencode/wave_W32/WAVE_W32_AUDIT_REPORT.md",
    ".tmp/w32-repair/w32-focused.txt",
    "tests/test_w32_discovery_manifest.py"
   ],
   "candidate_sha": "3e9635ba1cf0255d5a09f370e91d1ddb73cef888"
  },
  {
   "requirement_id": "HPC-W08-DISC-005",
   "mandatory": true,
   "disposition": "PASS",
   "implementation_owners": [
    "src/hpc_gui/plugins/discovery.py",
    "src/hpc_gui/plugin['spec_profile_id', 'protocol_revision', 'wave_id', 'wave_spec_revision', 'status', 'candidate_sha', 'closure_sha', 'dependency_validation', 'requirements', 'tests', 'gui_actions', 'resources', 'artifacts', 'review_passes', 'contradiction_scan', 'blockers', 'deferred_items', 'validator_result']
status ACCEPTANCE_GREEN
candidate 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
reqs 13
tests 1
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python scripts/validate_wave_closeout.py --wave W32 2>&1 | head -n 100; echo "EXIT:$?"
{
  "can_close": true,
  "wave_id": "W32",
  "candidate_sha": "3e9635ba1cf0255d5a09f370e91d1ddb73cef888",
  "closure_sha": null,
  "required_count": 13,
  "manifest_requirement_count": 13,
  "test_count": 1,
  "failure_reasons": []
}
EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_w32_discovery_manifest.py -q 2>&1 | tail -n 5; echo "---FOCUSED---"; python -m pytest tests/test_plugin_core.py tests/test_plugin_schema_compat.py tests/test_plugin_security.py tests/test_plugin_installer.py tests/test_plugin_integrity.py tests/test_wx_plugins.py tests/test_w08_schema_isolation.py -q 2>&1 | tail -n 5; echo "---DIFFCHECK---"; git diff --check; echo "DIFFCHECK_EXIT:$?"
...................                                                      [100%]
19 passed in 0.71s
---FOCUSED---
........................................................................ [ 47%]
........................................................................ [ 94%]
.........                                                                [100%]
153 passed in 5.19s
---DIFFCHECK---
DIFFCHECK_EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "import json; d=json.load(open('artifacts/wave_W32/WAVE_W32_EVIDENCE_MANIFEST.json')); print('validator_result:', d.get('validator_result')); print('blockers:', d.get('blockers')); print('gui_actions:', len(d.get('gui_actions',[]))); print('artifacts:', d.get('artifacts')); print('review_passes:', d.get('review_passes')); print('contradiction:', d.get('contradiction_scan'))"; echo "---MANIFEST_TESTS---"; python -c "import json; d=json.load(open('artifacts/wave_W32/WAVE_W32_EVIDENCE_MANIFEST.json')); [print(t.get('node'), t.get('outcome'), t.get('candidate_sha','')[:8]) for t in d.get('tests',[])]"
validator_result: {'state': 'ACCEPTANCE_GREEN', 'reason': '19 focused green at candidate plus fresh independent audit PASS plus diff check clean'}
blockers: []
gui_actions: 1
artifacts: [{'path': 'docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md', 'identity': 'canonical W32 wave report at candidate 3e9635ba'}, {'path': 'artifacts/opencode/wave_W32/WAVE_W32_AUDIT_REPORT.md', 'identity': 'fresh independent W32 audit PASS at candidate 3e9635ba'}, {'path': 'tests/test_w32_discovery_manifest.py', 'identity': 'W32 tests, 19 tests at candidate'}, {'path': '.tmp/w32-repair/w32-focused.txt', 'identity': 'focused 19 passed evidence at candidate'}]
review_passes: {'diff_check': 'PASS', 'claim_source_review': 'PASS', 'independent_audit': 'PASS'}
contradiction: {'unresolved': []}
---MANIFEST_TESTS---
tests/test_w32_discovery_manifest.py None 3e9635ba
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/ -k "plugin" -q --ignore="tests/contracts (1)" --ignore="tests/contracts (2)" --deselect tests/test_wave6_plugin_provider_unicode.py::TestIntegration::test_full_plugin_unicode_flow 2>&1 | tail -n 4
echo "---NEGATIVE-CHECK---"
grep -c "broken\|malformed\|incompatible\|unsafe\|duplicate" tests/test_w32_discovery_manifest.py 2>&1 || python -c "import pathlib; t=open('tests/test_w32_discovery_manifest.py').read().lower(); print(sum(t.count(k) for k in ['broken','malformed','incompatible','unsafe','duplicate']))"
........................................................................ [ 66%]
.......................................ssss...s..............ssssss..... [ 88%]
....................................                                     [100%]
293 passed, 31 skipped, 2872 deselected in 21.98s
---NEGATIVE-CHECK---
15
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "
import json
d=json.load(open('artifacts/wave_W32/WAVE_W32_EVIDENCE_MANIFEST.json'))
required=['spec_profile_id','protocol_revision','wave_id','wave_spec_revision','status','candidate_sha','closure_sha','dependency_validation','requirements','tests','gui_actions','resources','artifacts','review_passes','contradiction_scan','blockers','deferred_items','validator_result']
missing=[k for k in required if k not in d]
print('missing:', missing if missing else 'none')
print('status:', d['status'])
print('req ids:', [r['requirement_id'] for r in d['requirements']])
print('all PASS:', all(r.get('disposition')=='PASS' for r in d['requirements']))
print('resources:', d.get('resources'))
print('deferred:', d.get('deferred_items'))
print('gui0:', d.get('gui_actions')[0] if d.get('gui_actions') else None)
"
missing: none
status: ACCEPTANCE_GREEN
req ids: ['HPC-W08-DISC-001', 'HPC-W08-DISC-002', 'HPC-W08-DISC-003', 'HPC-W08-DISC-004', 'HPC-W08-DISC-005', 'HPC-W08-MANIFEST-001', 'HPC-W08-MANIFEST-002', 'HPC-W08-MANIFEST-003', 'HPC-W08-MANIFEST-004', 'HPC-W08-MANIFEST-005', 'HPC-W08-MANIFEST-006', 'HPC-W08-MANIFEST-007', 'HPC-W08-MANIFEST-008']
all PASS: True
resources: []
deferred: []
gui0: {'status': 'FULL', 'source_binding': 'src/hpc_gui/wx_plugins_view.py WxPluginManagerModel set_registry/cards plus set_enabled persistence via plugins/storage read_disabled_ids under the same root', 'runtime_test_node': 'tests/test_w32_discovery_manifest.py::test_gui_manager_surfaces_discovery_state', 'observed_readback': 'headless WxPluginManagerModel: registry_source cache, card plugin_id org.hpcclient.truba installed True, disabled id persisted via read_disabled_ids under same tmp root, CWD untouched', 'candidate_sha': '3e9635ba1cf0255d5a09f370e91d1ddb73cef888'}
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
Auditing W32 — executing the canonical skill read-only.
Prior audit and close signals conflict — verifying current repository truth independently.
Core evidence re-verified green — final completeness check before verdict.
Fresh independent audit of W32 complete (read-only for product code; no repairs made).

Scope: 13 owned IDs `HPC-W08-DISC-001..005`, `HPC-W08-MANIFEST-001..008` from `waves/pending/W32.md` frontmatter; `TODO_OWNERSHIP_MAP.md` has no W32 rows; mandatory Workstream A + B of `WAVE_V2_FINAL_08.md` preserved. Wave location `waves/pending/W32.md`, not yet in `waves/done`.

Requirement to owner to test (all green):
- DISC-001..005 to `plugins/discovery.py` 5-source enumeration plus loader/storage, covered by `tests/test_w32_discovery_manifest.py` discovery tests including CWD-isolation, precedence/identity determinism.
- MANIFEST-001 ID shape to `validator.py` reverse-DNS RE plus loader gate; 002 name bound 128; 003 semver; 004 plugin_api allow-list plus requires_app; 005 entrypoints object plus contained loader problem; 006 provider_ids safe-alphabet/max64/dedupe preserved through loader/installer; 007 optional_dependencies advisory; 008 broken JSON plus incompatible app isolated with sibling loads.

Test evidence re-run by this auditor at HEAD `3e9635ba1cf0255d5a09f370e91d1ddb73cef888`:
- `tests/test_w32_discovery_manifest.py`: 19 passed.
- Focused regression plugin_core, schema_compat, security, installer, integrity, wx_plugins, w08_schema_isolation: 153 passed.
- Broader plugin sweep ignoring 2 stray sibling contracts dirs and deselecting 1 known failure: 293 passed, 31 skipped.
- `git diff --check`: clean. No secrets in owned files. No weakened tests.

GUI class required: headless `WxPluginManagerModel` runtime test with installed card plus disabled persistence under same root passed within the 19; manifest gui_actions FULL binding with source, runtime node, observed readback, candidate SHA present.

Evidence manifest: `artifacts/wave_W32/WAVE_W32_EVIDENCE_MANIFEST.json` now exists with all profile required fields, status ACCEPTANCE_GREEN, candidate_sha matching HEAD, 13 requirements all PASS bound to candidate, GUI FULL, contradiction_scan without unresolved, no blockers. Closeout validator `scripts/validate_wave_closeout.py --wave W32`: can_close true, no failure reasons. Prior missing-manifest blocker from findings input is therefore resolved and stale, not a current defect.

Findings disposition: pre-existing `test_wave6_plugin_provider_unicode` unicode-flow failure is on `validate_cluster_profile_dict` storage-shape gate present verbatim at HEAD, untouched by W32 validator diff, correctly routed to stable owner and non-blocking for W32. Stray `tests/contracts (1)/(2)` collection errors are sibling-owned untracked dirs.

Candidate identity: HEAD matches audit candidate SHA; owned working-tree additions are W32-scoped product plus test plus report plus manifests. Content-identity reconciliation remains controller-owned. No owned blocking defect remains. Verdict PASS.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
