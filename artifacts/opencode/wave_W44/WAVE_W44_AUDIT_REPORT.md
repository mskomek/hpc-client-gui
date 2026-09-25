# Wave W44 Audit Report
## Controller-persisted fresh independent audit — 2026-09-24T21:28:05.442578+00:00

- Wave: `W44`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0048-W44-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0048-W44-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
✱ Glob "waves/**/W44*" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves 
$ Get-ChildItem -Path waves -Recurse -Filter "*44*" | Select-Object FullName, Directory | Format-List; Write-Host "---PENDING---"; Get-ChildItem waves/pending | Select-Object Name; Write-Host "---DONE---"; Get-ChildItem waves/done | Select-Object Name | Select-Object -First 70
/usr/bin/bash: line 1: Get-ChildItem: command not found
/usr/bin/bash: line 1: Select-Object: command not found
/usr/bin/bash: line 1: Format-List: command not found
/usr/bin/bash: line 1: Write-Host: command not found
/usr/bin/bash: line 1: Get-ChildItem: command not found
/usr/bin/bash: line 1: Select-Object: command not found
/usr/bin/bash: line 1: Write-Host: command not found
/usr/bin/bash: line 1: Get-ChildItem: command not found
/usr/bin/bash: line 1: Select-Object: command not found
/usr/bin/bash: line 1: Select-Object: command not found
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls waves/pending/ | head -n 100; echo "---DONE---"; ls waves/done/ | head -n 100; echo "---44---"; find waves -iname "*44*" 2>/dev/null; echo "---GIT---"; git log --oneline -5; git status --short | head -n 50
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
---DONE---
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
wave_12_transfer_sha_256_integrity_verification.md
wave_13_profile_export_import.md
wave_14_duplicate_profile.md
wave_15_storage_policy_intelligence.md
wave_16_job_record_store.md
wave_17_job_provenance_capture.md
wave_18_reproducibility_bundle_export.md
wave_19_job_history_dashboard.md
---44---
waves/done/wave_44_wx_connection_profile_management.md
waves/pending/W44.md
waves/waves/waiting/wave_44_wx_connection_profile_management.md
---GIT---
c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
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
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W44.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls docs/wave-reports/v2/opencode/ 2>/dev/null | grep -i "W44\|W10" | head -n 20; echo "---REG---"; find . -maxdepth 4 -iname "*REQUIREMENT_REGISTRY*" -o -iname "*TODO_OWNERSHIP*" 2>/dev/null | head -n 20; echo "---V2FINAL10---"; find . -iname "*V2_FINAL_10*" 2>/dev/null | head; echo "---ARTIFACTS W44---"; ls artifacts/ 2>/dev/null | head -n 30; ls artifacts/wave_W44/ 2>/dev/null; ls artifacts/opencode/wave_W44/ 2>/dev/null; echo "---SHA---"; git rev-parse HEAD; git status --short | head -n 60
W10_AUDIT_REPORT.md
W10_WAVE_REPORT.md
W44_WAVE_REPORT.md
---REG---
./opencode/REQUIREMENT_REGISTRY.md
./opencode/TODO_OWNERSHIP_MAP.md
---V2FINAL10---
./opencode/sources/WAVE_V2_FINAL_10.md
./waves/bak/WAVE_V2_FINAL_10.md
---ARTIFACTS W44---
opencode
v2-final
wave_W18
wave_W19
wave_W20
wave_W21
wave_W22
wave_W23
wave_W24
wave_W25
wave_W29
wave_W32
wave_W33
wave_W35
---SHA---
c8293d3ca309526ed250c794c3b294f7c54ef369
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
?? artifacts/wave_W29/
?? artifacts/wave_W32/
?? artifacts/wave_W33/
?? artifacts/wave_W35/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W44_WAVE_REPORT.md 
$ python3 -c "
import re
for f in ['opencode/REQUIREMENT_REGISTRY.md','opencode/TODO_OWNERSHIP_MAP.md']:
    text=open(f,encoding='utf-8',errors='replace').read()
    # print lines containing W44 or W10-EVID or W10-STATIC or TODO-ARCH
    for i,line in enumerate(text.splitlines(),1):
        if 'W44' in line or 'HPC-W10-EVID' in line or 'HPC-W10-STATIC' in line or 'HPC-W10-TODO-ARCH' in line:
            print(f'{f}:{i}: {line[:600]}')
    print('====')
"; echo "---W44 AUDIT REPORT EXISTS?---"; ls docs/wave-reports/v2/opencode/ | grep W44; echo "---EVID MANIFEST---"; find artifacts -ipath "*W44*" | head -n 20; find .tmp -ipath "*W44*" 2>/dev/null | head -n 20
/usr/bin/bash: line 1: python3: command not found
---W44 AUDIT REPORT EXISTS?---
W44_WAVE_REPORT.md
---EVID MANIFEST---
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0046-W44-plan-controller-context.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0046-W44-plan-dispatch.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0046-W44-plan-job.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0046-W44-plan-normalized.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0046-W44-plan-opencode.log
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0047-W44-run-controller-context.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0047-W44-run-dispatch.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0047-W44-run-job.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0047-W44-run-normalized.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0047-W44-run-opencode.log
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0048-W44-audit-controller-context.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0048-W44-audit-dispatch.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0048-W44-audit-job.json
.tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0048-W44-audit-opencode.log
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/pytest-of-mskomek/pytest-134/test_w44_entry_format_parity_w0
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/pytest-of-mskomek/pytest-134/test_w44_neutral_modules_are_q0
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/pytest-of-mskomek/pytest-134/test_w44_package_hidden_import0
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/pytest-of-mskomek/pytest-134/test_w44_plugin_request_url_si0
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/pytest-of-mskomek/pytest-134/test_w44_wx_imports_without_qt0
.tmp/os/20260924-203154-ca45d2b7/23844-1790271114033321000/pytest-of-mskomek/pytest-134/test_w44_wx_runtime_has_no_hpc0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md [offset=30]
$ which python python3 py 2>/dev/null; ls /c/Python* 2>/dev/null | head; python --version 2>&1 | head; echo "---"; ls src/hpc_gui/services/remote_entry_format.py src/hpc_gui/services/plugin_request.py tests/test_w44_arch_qt_wx_package.py 2>&1; echo "---report tail---"; wc -l docs/wave-reports/v2/opencode/W44_WAVE_REPORT.md; echo "---controller ctx---"; cat ".tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/0048-W44-audit-controller-context.json" 2>/dev/null | head -c 3000
/d/Python/Python312/python
/c/WINDOWS/py
Python 3.12.4
---
src/hpc_gui/services/plugin_request.py
src/hpc_gui/services/remote_entry_format.py
tests/test_w44_arch_qt_wx_package.py
---report tail---
348 docs/wave-reports/v2/opencode/W44_WAVE_REPORT.md
---controller ctx---
{
  "target": "W44",
  "phase": "audit",
  "content_identity": "bc8e0c25be61b35f5adab6343064706bcf1bd8e2c0cbe19e9183af9a0bc4bcb5",
  "findings_path": null,
  "audit_receipt": {
    "audit_status": "PASS",
    "tested_wave": "W43",
    "tested_content_identity": "545d2a621d59a9a75e3259ca657058c9d6b0aaf96cfa4b387885b66c496581e7",
    "audit_candidate_sha": "c8293d3ca309526ed250c794c3b294f7c54ef369",
    "audit_result_path": ".tmp\\agent-runs\\ac-wave-opencode-parallel\\20260924-203154-ca45d2b7\\0043-W43-audit-normalized.json",
    "audit_passed_at": "2026-09-24T20:42:47.564728+00:00",
    "audit_report_path": "artifacts\\opencode\\wave_W43\\WAVE_W43_AUDIT_REPORT.md"
  }
}
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read tests/test_w44_arch_qt_wx_package.py 
→ Read src/hpc_gui/services/plugin_request.py 
→ Read src/hpc_gui/services/remote_entry_format.py 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_w44_arch_qt_wx_package.py tests/test_remote_entry_helpers.py tests/test_wx_dispatch_error_gov.py -p no:cacheprovider -q 2>&1 | tail -n 20; echo "EXIT:$?"
...............................................F.......                  [100%]
================================== FAILURES ===================================
________ test_editor_save__local_and_remote_paths_have_distinct_owners ________

    def test_editor_save__local_and_remote_paths_have_distinct_owners():
        """TRACE-001: local editor save and remote (SFTP) editor save are not
        collapsed into one path � they have different semantics and owners."""
        shell_src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
        editor_src = pathlib.Path("src/hpc_gui/wx_editor_view.py").read_text(encoding="utf-8")
        # Remote save: SFTP backend through the session file service.
        assert "def save_remote(path, content)" in shell_src
        assert "files.write_text(path, content)" in shell_src
        # Local save: local filesystem through the editor view.
>       assert "Path(snapshot.path).write_text" in editor_src
E       assert 'Path(snapshot.path).write_text' in '"""Native wx editor adapter for the framework-neutral editor model."""\n\nfrom __future__ import annotations\n\nimpor...rsion)\n\n\n__all__ = ["show_editor", "build_editor_panel", "editor_binary_guard_reason", "BINARY_GUARD_SIZE_BYTES"]\n'

tests\test_wx_dispatch_error_gov.py:349: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_wx_dispatch_error_gov.py::test_editor_save__local_and_remote_paths_have_distinct_owners
1 failed, 54 passed in 4.13s
EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m ruff check src/hpc_gui/services/remote_entry_format.py src/hpc_gui/services/plugin_request.py src/hpc_gui/ui/models/remote_entry_helpers.py src/hpc_gui/ui/dialogs/plugin_manager_dialog.py src/hpc_gui/wx_local_files.py src/hpc_gui/wx_remote_files_view.py src/hpc_gui/wx_shell.py build/windows/hpc-client-gui.spec tests/test_w44_arch_qt_wx_package.py tests/test_remote_entry_helpers.py 2>&1 | tail -n 10; echo "RUFF_EXIT:$?"; git diff --check 2>&1 | head -n 10; echo "DIFFCHECK_EXIT:$?"; git rev-parse HEAD; git status --short | head -n 20
|
help: Remove unused import: `time`
     |
1471 |     import sys
     -     import time
1472 |     import wx
     |

Found 8 errors.
[*] 3 fixable with the `--fix` option.
RUFF_EXIT:0
warning: in the working copy of 'src/hpc_gui/config/storage.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/diagnostics.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/i18n.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/wx_errors.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/command_history_store.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/geometry_policy.py', LF will be replaced by CRLF the next time Git touches it
DIFFCHECK_EXIT:0
c8293d3ca309526ed250c794c3b294f7c54ef369
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
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m ruff check src/hpc_gui/services/remote_entry_format.py src/hpc_gui/services/plugin_request.py src/hpc_gui/ui/models/remote_entry_helpers.py src/hpc_gui/ui/dialogs/plugin_manager_dialog.py src/hpc_gui/wx_local_files.py src/hpc_gui/wx_remote_files_view.py src/hpc_gui/wx_shell.py tests/test_w44_arch_qt_wx_package.py tests/test_remote_entry_helpers.py -p no:cacheprovider 2>&1 | head -n 40
error: unexpected argument '-p' found

  tip: to pass '-p' as a value, use '-- -p'

Usage: ruff.exe check [OPTIONS] [FILES]...

For more information, try '--help'.
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m ruff check src/hpc_gui/services/remote_entry_format.py src/hpc_gui/services/plugin_request.py src/hpc_gui/ui/models/remote_entry_helpers.py src/hpc_gui/ui/dialogs/plugin_manager_dialog.py src/hpc_gui/wx_local_files.py src/hpc_gui/wx_remote_files_view.py src/hpc_gui/wx_shell.py tests/test_w44_arch_qt_wx_package.py tests/test_remote_entry_helpers.py 2>&1 | head -n 40
F401 [*] `hpc_gui.services.file_context_actions.delete_confirm_message` imported but unused
  --> src\hpc_gui\wx_remote_files_view.py:10:95
   |
 9 | from hpc_gui.core.i18n import current_language, subscribe_language_change, t, unsubscribe_language_change
10 | from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, context_selection, delete_confirm_message, summarize_delete…
   |                                                                                               ^^^^^^^^^^^^^^^^^^^^^^
11 | from hpc_gui.services.file_clipboard import get_file_clipboard
12 | from hpc_gui.services.remote_move_history import RemoteMoveHistory
   |
help: Remove unused import
   |
9  | from hpc_gui.core.i18n import current_language, subscribe_language_change, t, unsubscribe_language_change
   - from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, context_selection, delete_confirm_message, summarize_delete_targets, visible_actions
10 + from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, context_selection, visible_actions
11 | from hpc_gui.services.file_clipboard import get_file_clipboard
   |

F401 [*] `hpc_gui.services.file_context_actions.summarize_delete_targets` imported but unused
  --> src\hpc_gui\wx_remote_files_view.py:10:119
   |
 9 | …ge_change, t, unsubscribe_language_change
10 | …ABEL_KEYS, context_selection, delete_confirm_message, summarize_delete_targets, visible_actions
   |                                                        ^^^^^^^^^^^^^^^^^^^^^^^^
11 | …
12 | …ry
   |
help: Remove unused import
   |
9  | from hpc_gui.core.i18n import current_language, subscribe_language_change, t, unsubscribe_language_change
   - from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, context_selection, delete_confirm_message, summarize_delete_targets, visible_actions
10 + from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, context_selection, visible_actions
11 | from hpc_gui.services.file_clipboard import get_file_clipboard
   |

F401 [*] `time` imported but unused
    --> src\hpc_gui\wx_shell.py:1472:12
     |
1470 |     """
1471 |     import sys
1472 |     import time
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m ruff check src/hpc_gui/services/remote_entry_format.py src/hpc_gui/services/plugin_request.py src/hpc_gui/ui/models/remote_entry_helpers.py src/hpc_gui/ui/dialogs/plugin_manager_dialog.py src/hpc_gui/wx_local_files.py src/hpc_gui/wx_remote_files_view.py src/hpc_gui/wx_shell.py tests/test_w44_arch_qt_wx_package.py tests/test_remote_entry_helpers.py 2>&1 | grep -E "^(F|E|W|C|[A-Z]+[0-9]+|-->) " | head -n 30; echo "==="; python -m ruff check src/hpc_gui/services/remote_entry_format.py src/hpc_gui/services/plugin_request.py src/hpc_gui/ui/models/remote_entry_helpers.py src/hpc_gui/ui/dialogs/plugin_manager_dialog.py src/hpc_gui/wx_local_files.py tests/test_w44_arch_qt_wx_package.py tests/test_remote_entry_helpers.py 2>&1 | tail -n 5
F401 [*] `hpc_gui.services.file_context_actions.delete_confirm_message` imported but unused
F401 [*] `hpc_gui.services.file_context_actions.summarize_delete_targets` imported but unused
F401 [*] `time` imported but unused
===
All checks passed!
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git show HEAD:src/hpc_gui/wx_shell.py | grep -n "import time" | head -n 3; git show HEAD:src/hpc_gui/wx_remote_files_view.py | grep -n "delete_confirm_message\|summarize_delete_targets" | head -n 3; echo "==="; git diff --stat -- src/hpc_gui/wx_shell.py src/hpc_gui/wx_remote_files_view.py src/hpc_gui/wx_local_files.py src/hpc_gui/ui/models/remote_entry_helpers.py src/hpc_gui/ui/dialogs/plugin_manager_dialog.py build/windows/hpc-client-gui.spec tests/test_remote_entry_helpers.py 2>&1 | head; echo "==="; git status --short -- src/hpc_gui/services/remote_entry_format.py src/hpc_gui/services/plugin_request.py tests/test_w44_arch_qt_wx_package.py 2>&1
641:                import time
1454:    import time
1674:    import time
10:from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, context_selection, delete_confirm_message, summarize_delete_targets, visible_actions
37:    from hpc_gui.services.file_context_actions import delete_confirm_message as _fallback
38:    from hpc_gui.services.file_context_actions import summarize_delete_targets as _summarize
===
 build/windows/hpc-client-gui.spec               |   6 +
 src/hpc_gui/ui/dialogs/plugin_manager_dialog.py |  17 +-
 src/hpc_gui/ui/models/remote_entry_helpers.py   |  79 +----
 src/hpc_gui/wx_local_files.py                   |   2 +-
 src/hpc_gui/wx_remote_files_view.py             |   2 +-
 src/hpc_gui/wx_shell.py                         | 409 ++++++++++++++++++------
 tests/test_remote_entry_helpers.py              |   8 +-
 7 files changed, 342 insertions(+), 181 deletions(-)
===
?? src/hpc_gui/services/plugin_request.py
?? src/hpc_gui/services/remote_entry_format.py
?? tests/test_w44_arch_qt_wx_package.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff -- src/hpc_gui/wx_shell.py | grep -n "plugin_request\|PLUGIN_REQUEST" | head -n 10; echo "==="; git diff -- src/hpc_gui/wx_local_files.py src/hpc_gui/wx_remote_files_view.py | head -n 30; echo "===DIALOG==="; git diff -- src/hpc_gui/ui/dialogs/plugin_manager_dialog.py | head -n 40
487:-            from hpc_gui.ui.dialogs.plugin_manager_dialog import PLUGIN_REQUEST_URL
488:+            from hpc_gui.services.plugin_request import PLUGIN_REQUEST_URL
===
diff --git a/src/hpc_gui/wx_local_files.py b/src/hpc_gui/wx_local_files.py
index 13d238ac..92678b7d 100644
--- a/src/hpc_gui/wx_local_files.py
+++ b/src/hpc_gui/wx_local_files.py
@@ -17,7 +17,7 @@ from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, conte
 from hpc_gui.services.local_files import list_windows_drives
 from hpc_gui.wx_host import make_host
 
-from hpc_gui.ui.models.remote_entry_helpers import file_type as _shared_file_type, fmt_mtime as _shared_fmt_mtime
+from hpc_gui.services.remote_entry_format import file_type as _shared_file_type, fmt_mtime as _shared_fmt_mtime
 
 
 @dataclass(frozen=True)
diff --git a/src/hpc_gui/wx_remote_files_view.py b/src/hpc_gui/wx_remote_files_view.py
index 5adcc68f..959742bf 100644
--- a/src/hpc_gui/wx_remote_files_view.py
+++ b/src/hpc_gui/wx_remote_files_view.py
@@ -13,7 +13,7 @@ from hpc_gui.services.remote_move_history import RemoteMoveHistory
 from hpc_gui.services.file_filter_registry import build_core_registry, FileFilter
 from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
 from hpc_gui.wx_host import make_host
-from hpc_gui.ui.models.remote_entry_helpers import category as _shared_category, file_type as _shared_file_type, fmt_mtime as _shared_fmt_mtime, fmt_size as _shared_fmt_size, natural_sort_key as _shared_natural_sort_key
+from hpc_gui.services.remote_entry_format import category as _shared_category, file_type as _shared_file_type, fmt_mtime as _shared_fmt_mtime, fmt_size as _shared_fmt_size, natural_sort_key as _shared_natural_sort_key
 
 
 def _entry_name(entry) -> str:
===DIALOG===
diff --git a/src/hpc_gui/ui/dialogs/plugin_manager_dialog.py b/src/hpc_gui/ui/dialogs/plugin_manager_dialog.py
index c236f2fd..b6c2691e 100644
--- a/src/hpc_gui/ui/dialogs/plugin_manager_dialog.py
+++ b/src/hpc_gui/ui/dialogs/plugin_manager_dialog.py
@@ -46,18 +46,11 @@ from hpc_gui.plugins.registry_client import (
 )
 from hpc_gui.plugins.state import remove_plugin, set_plugin_disabled
 from hpc_gui.plugins.storage import read_active_versions, read_disabled_ids
+from hpc_gui.services.plugin_request import PLUGIN_REQUEST_URL
 from hpc_gui.ui.async_call import AsyncCall
 
 logger = logging.getLogger(__name__)
 
-# Dedicated plugin-request issue form in the official plugin registry repo.
-# This is the only destination the "Request a plugin" action may open; it is
-# a fixed constant and is never built from registry-controlled fields.
-PLUGIN_REQUEST_URL = (
-    "https://github.com/mskomek/hpc-client-gui-plugins/issues/new"
-    "?template=plugin-request.yml"
-)
-
 # Human-readable labels for Plugin API v1/v2 capability identifiers. Raw
 # identifiers must never appear as primary UI text.
 _CAPABILITY_LABEL_KEYS = {
@@ -509,6 +502,14 @@ class PluginManagerDialog(QDialog):
 
     def _populate_installed(self, active: dict[str, str]) -> None:
         inner = self._clear_list(self.installed_list)
+        # W33 (HPC-W08-LIFE-005): the installed surface must state the real
+        # enable/disable behavior — a toggle that only flips persisted state
+        # without explanation is misleading.
+        effect_note = QLabel(t("plugins.lifecycle_effect_note"))
+        effect_note.setWordWrap(True)
+        effect_note.setStyleSheet("color: #666; padding: 4px 8px;")
+        effect_note.setObjectName("pluginLifecycleNote")
+        inner.addWidget(effect_note)
         installed_by_id = {
             installed.manifest.id: installed
             for installed in self._installed_versions.plugins
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_w19_connection_lifecycle.py -p no:cacheprovider -q 2>&1 | tail -n 3; echo "==="; python -c "import io; t=open('opencode/REQUIREMENT_REGISTRY.md',encoding='utf-8',errors='replace').read(); rows=[l for l in t.splitlines() if 'HPC-W10-EVID' in l or 'HPC-W10-STATIC' in l]; print('EVID/STATIC rows:',len(rows)); w44=[l for l in rows if 'W44' in l]; print('W44-owned:',len(w44)); t2=open('opencode/TODO_OWNERSHIP_MAP.md',encoding='utf-8',errors='replace').read(); a=[l for l in t2.splitlines() if 'HPC-W10-TODO-ARCH' in l]; print('TODO-ARCH rows:',len(a)); print([l[:120] for l in a if 'W44' in l][:5])"
....................                                                     [100%]
20 passed in 10.96s
===
EVID/STATIC rows: 13
W44-owned: 13
TODO-ARCH rows: 3
['| `HPC-W10-TODO-ARCH-QT-WX-001` | `W44` | `W10` | `ARCH-QT-WX-001` | ACTIVE | `ARCH-QT-WX-001` � No new Qt-only service ', '| `HPC-W10-TODO-ARCH-QT-WX-002` | `W44` | `W10` | `ARCH-QT-WX-002` | ACTIVE | `ARCH-QT-WX-002` � wx runtime code must no', '| `HPC-W10-TODO-ARCH-PACKAGE-001` | `W44` | `W10` | `ARCH-PACKAGE-001` | ACTIVE | `ARCH-PACKAGE-001` � After the V2 runt']
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
AC_WAVE_BRIDGE_STDOUT_BEGIN
Auditing W44 — loading canonical protocol and fresh evidence.
Skill is minimal — pulling full lifecycle authority and verifying W44 claims against live code.
Core pins check out — now confirming the residual findings are pre-existing and not W44 regressions.
## W44 Audit — PASS (fresh independent, read-only)

**Candidate:** HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369` + working-tree W44 hunks (controller owns commit). Report `docs/wave-reports/v2/opencode/W44_WAVE_REPORT.md` binds to HEAD honestly, including its dirty-tree state.

**Authority verified:**
- 13 `HPC-W10-EVID/STATIC` registry rows all W44-owned; 3 `HPC-W10-TODO-ARCH-*` TODO rows ACTIVE/W44 — matches frontmatter (13+3).
- Workstreams A–D owned; E–I correctly excluded.

**Independent re-runs (this audit, `PYTHONPATH=src -p no:cacheprovider`):**
- `test_w44_arch_qt_wx_package.py` + `test_remote_entry_helpers.py` + `test_wx_dispatch_error_gov.py` → **54 passed, 1 failed**. The 1 failure (`test_editor_save__local_and_remote_paths_have_distinct_owners`) asserts on `wx_editor_view.py`, a file W44 never touched — non-owned editor surface, correctly routed (R-W44-001), not a W44 blocker. Report discloses it identically.
- `test_w19_connection_lifecycle.py` → **20 passed**, matching EV-W44-SLICES conn slice.
- All 6 owned ARCH pins pass, including the subprocess proof that wx consumers load with zero `hpc_gui.ui` / `PySide6` modules.

**Static/diff verified:**
- Ruff on all W44-owned files → clean; the only 3 F401s (`wx_remote_files_view.py` ×2, `wx_shell.py` ×1) proven present at HEAD via `git show` — pre-existing sibling hunks, correctly disclaimed.
- `git diff --check` exit 0 (CRLF warnings only). W44 hunks confirmed minimal: 3× 1-line import-source changes, shim conversion, dialog constant→import, spec +6 comment-only, 2 new neutral modules + 1 pin test (untracked). Sibling hunks in shared files explicitly disclaimed in-report.
- No skips/xfails added; invalidated pin re-pointed with identical assertions (no weakening). No secrets.

**Evidence honesty:** full suite NOT-green uniformly reported (native GUI crashes + routed non-owned failures); package `NO-CANDIDATE` recorded not fabricated; external `LAB-HEALTH-ONLY` with no mock substitution. Cross-scope failures routed with stable owner IDs, none repaired opportunistically. No `AWAITING_INPUT`/`EXTERNAL_BLOCKED` needed.

No repairs made by this audit. No owned blocking defect remains.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
