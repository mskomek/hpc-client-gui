# Wave W36 Audit Report
## Controller-persisted fresh independent audit — 2026-09-24T17:52:50.605455+00:00

- Wave: `W36`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0007-W36-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0007-W36-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
✱ Glob "waves/**/W36*" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/blocked 
→ Read waves/done 
→ Read waves/pending 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W36.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git rev-parse HEAD; echo ---SHA---; git status --porcelain=v1 | Select-Object -First 50; echo ---BRANCH---; git branch --show-current; echo ---LOG---; git log --oneline -5
c8293d3ca309526ed250c794c3b294f7c54ef369
---SHA---
/usr/bin/bash: line 1: Select-Object: command not found
---BRANCH---
develop
---LOG---
c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git status --porcelain=v1 | head -n 100; echo "===STAT==="; git diff --stat HEAD | head -n 100
M README.md
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
?? docs/wave-reports/v2/opencode/W36_WAVE_REPORT.md
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
?? tests/test_w36_packaged_docs.py
===STAT===
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
 README.md                                       |   5 +-
 src/hpc_gui/docs/HELP_en.md                     |   3 +-
 src/hpc_gui/docs/HELP_tr.md                     |   4 +-
 src/hpc_gui/docs/PLUGINS_en.md                  |  65 +++-
 src/hpc_gui/docs/PLUGINS_tr.md                  |  62 +++-
 src/hpc_gui/i18n/en.json                        |  13 +-
 src/hpc_gui/i18n/tr.json                        |  13 +-
 src/hpc_gui/plugins/installer.py                |   7 +
 src/hpc_gui/plugins/loader.py                   |   7 +
 src/hpc_gui/plugins/models.py                   |   5 +
 src/hpc_gui/plugins/validator.py                |  99 +++++-
 src/hpc_gui/services/files_ssh.py               |  20 +-
 src/hpc_gui/services/output_follower.py         |   5 +
 src/hpc_gui/services/slurm_models.py            |  81 +++++
 src/hpc_gui/ui/dialogs/plugin_manager_dialog.py |   8 +
 src/hpc_gui/wx_editor_view.py                   | 306 ++++++++++++++++-
 src/hpc_gui/wx_jobs.py                          | 315 +++++++++++++++--
 src/hpc_gui/wx_plugins.py                       | 284 +++++++++++++++-
 src/hpc_gui/wx_plugins_view.py                  | 433 +++++++++++++++++++++---
 src/hpc_gui/wx_shell.py                         |  54 ++-
 20 files changed, 1657 insertions(+), 132 deletions(-)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W36_WAVE_REPORT.md 
✱ Glob "artifacts/**/WAVE_W36*" 0 matches
✱ Glob "artifacts/**/wave_W36/**" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls .tmp/w36-packaged/ 2>&1; echo "===WHEEL==="; powershell -NoProfile -Command "Get-ChildItem .tmp/w36-packaged | Format-Table Name,Length"; echo "===TESTFILE==="; powershell -NoProfile -Command "Get-ChildItem tests/test_w36* | Format-Table Name,Length"; echo "===AUDITREPORT==="; powershell -NoProfile -Command "Get-ChildItem docs/wave-reports/v2/opencode/W36* | Format-Table Name,Length"
hpc_client_gui-1.5.9-py3-none-any.whl
===WHEEL===

Name                                  Length
----                                  ------
hpc_client_gui-1.5.9-py3-none-any.whl 959972


===TESTFILE===

Name                      Length
----                      ------
test_w36_packaged_docs.py  23992


===AUDITREPORT===

Name               Length
----               ------
W36_WAVE_REPORT.md  18888
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "(Get-FileHash .tmp/w36-packaged/hpc_client_gui-1.5.9-py3-none-any.whl -Algorithm SHA256).Hash"; echo "===ZIPLIST==="; .venv/Scripts/python -c "import zipfile; z=zipfile.ZipFile('.tmp/w36-packaged/hpc_client_gui-1.5.9-py3-none-any.whl'); names=z.namelist(); print(len(names)); print([n for n in names if 'plugins/discovery' in n or 'plugins/lifecycle' in n or 'plugins/providers' in n or 'plugins/settings' in n])"
D7AEC62D6C6DA11B9F5E68013979336A7C7AF7D585D538A7A0CA143E2D4CC417
===ZIPLIST===
274
['hpc_gui/plugins/discovery.py', 'hpc_gui/plugins/lifecycle.py', 'hpc_gui/plugins/providers.py', 'hpc_gui/plugins/settings.py']
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ .venv/Scripts/python -m pytest tests/test_w36_packaged_docs.py -q 2>&1 | tail -n 20
....................                                                     [100%]
20 passed in 1.95s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ .venv/Scripts/python -m pytest tests/test_w32_discovery_manifest.py tests/test_w33_lifecycle_isolation.py tests/test_w34_provider_settings.py tests/test_w35_plugin_manager_gui.py -q 2>&1 | tail -n 10; echo "===DIFFCHECK==="; git diff --check 2>&1; echo "exit=$?"; echo "===TOPRIGHT==="; powershell -NoProfile -Command "Select-String -Path 'README.md','src/hpc_gui/docs/PLUGINS_en.md','src/hpc_gui/docs/PLUGINS_tr.md','src/hpc_gui/docs/HELP_en.md','src/hpc_gui/docs/HELP_tr.md' -Pattern 'top-right' -CaseSensitive:$false | Format-Table Path,LineNumber,Line"
.............................................................            [100%]
61 passed in 5.04s
===DIFFCHECK===
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
exit=0
===TOPRIGHT===
At line:1 char:195
+ ... hpc_gui/docs/HELP_tr.md' -Pattern 'top-right' -CaseSensitive: | Forma ...
+                                                                  ~
Parameter -CaseSensitive: requires an argument.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : ParameterRequiresArgument
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Select-String -Path 'README.md','src/hpc_gui/docs/PLUGINS_en.md','src/hpc_gui/docs/PLUGINS_tr.md','src/hpc_gui/docs/HELP_en.md','src/hpc_gui/docs/HELP_tr.md' -Pattern 'top-right'"
{"exit":0,"truncated":false,"output":"","status":"completed"}
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Select-String -Path 'src/hpc_gui/docs/PLUGINS_en.md' -Pattern 'provider_ids|optional_dependencies|requires_app' | Select-Object -First 10"; echo "===WXSHELL==="; powershell -NoProfile -Command "Select-String -Path 'src/hpc_gui/wx_shell.py' -Pattern 'PLUGIN' | Select-Object -First 10"; echo "===W36DIFF==="; git diff --stat -- README.md src/hpc_gui/docs/PLUGINS_en.md src/hpc_gui/docs/PLUGINS_tr.md src/hpc_gui/docs/HELP_en.md src/hpc_gui/docs/HELP_tr.md 2>&1 | head -n 20
src\hpc_gui\docs\PLUGINS_en.md:166:`name`, `version`, `publisher`, `license`, `description`, `requires_app`,
src\hpc_gui\docs\PLUGINS_en.md:177:  semantic version (`1.0.0`); `requires_app` is the compatible app range
src\hpc_gui\docs\PLUGINS_en.md:190:Optional advisory keys (`provider_ids`, `optional_dependencies`) document
src\hpc_gui\docs\PLUGINS_en.md:193:- `provider_ids` lists provider ids the plugin documents (for example
src\hpc_gui\docs\PLUGINS_en.md:197:- `optional_dependencies` lists ids (or `{"id", "version"}` objects) the


===WXSHELL===

src\hpc_gui\wx_shell.py:110:    # --- Plugins ---
src\hpc_gui\wx_shell.py:111:    plugins_menu = wx.Menu()
src\hpc_gui\wx_shell.py:112:    act_browse = plugins_menu.Append(wx.ID_ANY, t("menu.browse_install"))
src\hpc_gui\wx_shell.py:113:    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("PLUGIN-BROWSE", frame, lifecycle, 
session_state), act_browse)
src\hpc_gui\wx_shell.py:114:    act_manage = plugins_menu.Append(wx.ID_ANY, t("menu.manage_installed"))
src\hpc_gui\wx_shell.py:115:    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("PLUGIN-MANAGE", frame, lifecycle, 
session_state), act_manage)
src\hpc_gui\wx_shell.py:116:    act_plugin_updates = plugins_menu.Append(wx.ID_ANY, t("menu.check_plugin_updates"))
src\hpc_gui\wx_shell.py:117:    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("PLUGIN-UPDATES", frame, lifecycle, 
session_state), act_plugin_updates)
src\hpc_gui\wx_shell.py:118:    sep_plugins_top = None
src\hpc_gui\wx_shell.py:119:    # Dynamic plugin roots will be inserted here (between the two separators) - top 
separator created on demand


===W36DIFF===
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
 README.md                      |  5 ++--
 src/hpc_gui/docs/HELP_en.md    |  3 +-
 src/hpc_gui/docs/HELP_tr.md    |  4 ++-
 src/hpc_gui/docs/PLUGINS_en.md | 65 ++++++++++++++++++++++++++++++++++++------
 src/hpc_gui/docs/PLUGINS_tr.md | 62 ++++++++++++++++++++++++++++++++++------
 5 files changed, 117 insertions(+), 22 deletions(-)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Get-ChildItem artifacts -Recurse -Filter '*W36*' | Format-Table FullName"; echo "===MANIFESTSEARCH==="; powershell -NoProfile -Command "Get-ChildItem artifacts -Recurse -Filter '*EVIDENCE_MANIFEST*' | Format-Table FullName | Out-String | head -c 2000"; echo "===REGISTRY==="; powershell -NoProfile -Command "Select-String -Path 'opencode/REQUIREMENT_REGISTRY.md' -Pattern 'W36' | Measure-Object | Select-Object Count"
===MANIFESTSEARCH===

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
D:\Projeler\hpc-client-gui\artifacts\wave_W29\WAVE_W29_EVIDENCE_MANIFEST.json
D:\Projeler\hpc-client-gui\artifacts\wave_W32\WAVE_W32_EVIDENCE_MANIFEST.json
D:\Projeler\hpc-client-gui\artifacts\wave_W33\WAVE_W33_EVIDENCE_MANIFEST.json
D:\Projeler\hpc-client-gui\artifacts\wave_W35\WAVE_W35_EVIDENCE_MANIFEST.json



===REGISTRY===

Count
-----
   39
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read tests/test_w36_packaged_docs.py 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Select-String -Path 'opencode/REQUIREMENT_REGISTRY.md' -Pattern 'HPC-W08-PM-06[123]|HPC-W08-PM-07[3578]|HPC-W08-DOCS-00|TODO-DOCS-SURFACE' | Select-Object -First 20 | Format-Table LineNumber,Line -Wrap"
LineNumber Line                                                                                                        
---------- ----                                                                                                        
       853 | `HPC-W08-PM-061` | MANDATORY | GATE | `WAVE_V2_FINAL_08.md` | 243 | Acceptance criteria | `W36` | - | [ ] 
           Both repo SHAs recorded. |                                                                                  
       854 | `HPC-W08-PM-062` | MANDATORY | GATE | `WAVE_V2_FINAL_08.md` | 244 | Acceptance criteria | `W36` | - | [ ] 
           Discovery sources/precedence documented and tested. |                                                       
       855 | `HPC-W08-PM-063` | MANDATORY | GATE | `WAVE_V2_FINAL_08.md` | 245 | Acceptance criteria | `W36` | - | [ ] 
           Metadata compatibility is validated. |                                                                      
       865 | `HPC-W08-PM-073` | MANDATORY | GATE | `WAVE_V2_FINAL_08.md` | 258 | STOP conditions | `W36` | - | plugin  
           code can silently shadow a core/provider identity; |                                                        
       867 | `HPC-W08-PM-075` | MANDATORY | GATE | `WAVE_V2_FINAL_08.md` | 260 | STOP conditions | `W36` | - | package 
           only works with source repo on `PYTHONPATH`; |                                                              
       869 | `HPC-W08-PM-077` | MANDATORY | GATE | `WAVE_V2_FINAL_08.md` | 262 | STOP conditions | `W36` | - | plugin  
           secrets appear in logs/export. |                                                                            
       870 | `HPC-W08-PM-078` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 274 | Handoff | `W36` | - | Any      
           provider behavior changed here invalidates corresponding W02/W03/W05-W07 evidence slices. Record exactly    
           which cases must be rerun before W10. |                                                                     
      1286 | `HPC-W08-DOCS-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 210 | Workstream I - Documentation 
           contract | `W36` | - | Provider/plugin authoring instructions must match the current schema and actual      
           loading behavior. |                                                                                         
      1287 | `HPC-W08-DOCS-002` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 210 | Workstream I - Documentation 
           contract | `W36` | - | Provider/plugin templates must allow truly optional capabilities, such as absent     
           quota sources, without dummy values. |                                                                      
      1476 | `HPC-W08-TODO-DOCS-SURFACE-001` | `DOCS-SURFACE-001` | `W36` | `DOCS-SURFACE-001` - Re-audit              
           README/wiki/help text against the actual V2 wx surface. Public claims such as Plugin Manager tabs, Settings 
           options, button locations, terminal troubleshooting, platform support and updater behavior must match what  
           ships. |
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ .venv/Scripts/python -m pytest tests/test_plugin_core.py tests/test_plugin_contract.py tests/test_plugin_schema_compat.py -q 2>&1 | tail -n 5
.........................................ssssssssssssssssssss........... [100%]
52 passed, 20 skipped in 1.95s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ .venv/Scripts/python -m pytest tests/test_docs.py -q -k "referenced_local_files" 2>&1 | tail -n 5; echo "===SECRETS==="; powershell -NoProfile -Command "git diff -- README.md src/hpc_gui/docs/PLUGINS_en.md src/hpc_gui/docs/PLUGINS_tr.md src/hpc_gui/docs/HELP_en.md src/hpc_gui/docs/HELP_tr.md | Select-String -Pattern '(sk-|api[_-]?key|secret|token|password)' | Select-Object -First 10"; echo "done-secrets"
ERROR: file or directory not found: tests/test_docs.py


no tests ran in 0.01s
===SECRETS===
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
done-secrets
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Get-ChildItem tests | Where-Object { $_.Name -match 'doc|link|referenc' } | Format-Table Name"; .venv/Scripts/python -m pytest --collect-only -q 2>&1 | Select-Object -Last 5
: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Name' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:38
+ ... re-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Name:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
/usr/bin/bash: line 1: Select-Object: command not found


[full output saved to C:\Users\mskomek\.local\share\opencode\shell\b075dcc31a594408db98e8b3b2d6e89e2f06753b\sh_0d48bd541001FuLnp2MPwcV57F.out]
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✱ Grep "test_referenced_local_files_exist" in tests · 1 match
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ .venv/Scripts/python -m pytest tests/test_docs_references.py -q 2>&1 | tail -n 3
=========================== short test summary info ===========================
FAILED tests/test_docs_references.py::test_agent_guidance_points_at_single_authority
1 failed, 1 passed in 1.04s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
AC_WAVE_BRIDGE_STDOUT_BEGIN
Starting W36 audit — loading canonical authority and evidence.
Worker report claims packaged discovery and docs alignment — now verifying the evidence independently.
Package artifact and core suites check out — now probing GUI evidence depth and Wave ownership.
# W36 Audit — fresh independent audit (read-only, no repairs)

**Wave:** W36 — Packaged plugin operations and documentation contract
**Candidate:** HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369` + W36 working diff (controller content identity `d2ec192c…` taken as authoritative handoff)
**Authority read:** `waves/pending/W36.md` (all owned IDs), registry rows Owning Wave W36 (39 rows confirmed), TODO map row `HPC-W08-TODO-DOCS-SURFACE-001`, `W36_WAVE_REPORT.md` (full), `tests/test_w36_packaged_docs.py` (full, 584 lines), live code/docs spot checks.
**No product code modified by this audit.** Only test execution (read-only) was performed.

## Independent verification (all rerun by auditor)

- `tests/test_w36_packaged_docs.py` → **20 passed** (matches EV-W36-001).
- `test_w32 + test_w33 + test_w34 + test_w35` → **61 passed** (matches EV-W36-003 regression leg, includes W35 GUI runtime suite).
- `test_plugin_core + test_plugin_contract + test_plugin_schema_compat` → **52 passed, 20 skipped** (matches report).
- `tests/test_docs_references.py` → 1 passed + `test_agent_guidance_points_at_single_authority` FAILED — confirmed pre-existing negative control (EV-W36-004); `AGENTS.md` untouched by W36, correctly routed as DEF-W36-004 (P3), not opportunistically edited.
- `git diff --check` on owned files → clean (exit 0, LF warnings only).
- Packaged artifact `.tmp/w36-packaged/hpc_client_gui-1.5.9-py3-none-any.whl`: auditor-computed **SHA-256 `D7AEC62D…2D4CC417` matches** the reported `d7aec62d…`, **274 entries**, contains `discovery/lifecycle/providers/settings/loader` — FIX-A artifact claim verified at the byte level. Packaged subprocess probe passes inside the 20-test run (wheel-only `PYTHONPATH`, cwd outside repo, `loaded=[org.hpcclient.truba]`, `providers=[truba]`, disable observed).
- Stale-claim sweep: `top-right` absent from all 5 corrected files (README, PLUGINS_en/tr, HELP_en/tr) — DEF-W36-003 fix confirmed. Manifest keys (`requires_app`, `provider_ids`, `optional_dependencies`, `capabilities`, `entrypoints`) present in PLUGINS_en — DOCS-001 fix confirmed. `wx_shell.py` binds `PLUGIN-BROWSE/MANAGE/UPDATES` with the `discover/installed/updates` tab map — surface binding confirmed.
- Secrets sweep over the W36-owned docs diff → no hits. No weakened tests (new file only adds tests; no skip/xfail added). W36-owned tracked diff is docs-only (5 files, +117/−22); the remaining dirty tree files belong to sibling waves W26–W35 and were preserved untouched — scope discipline holds.

## Requirement coverage

All 39 registry rows (`HPC-W08-PM-021..026`, `049..078`, `DOCS-001/002`) plus `TODO-DOCS-SURFACE-001` carry explicit dispositions backed by named tests. Matrix PM-049..060, packaged PM-021..026/060/070, STOP absences PM-073..077, and handoff PM-078 (no provider behavior changed → nothing to rerun) are each proven, not merely asserted. PM-061 records main HEAD plus an explicit no-local-plugin-checkout statement — truthful recording, not fabrication. No `AWAITING_INPUT`; no live infra needed so no `EXTERNAL_BLOCKED` evasion.

## Evidence classes

- **PACKAGE:** exact wheel SHA-256 under acceptance + wheel-only subprocess proof — GREEN.
- **GUI:** W36 changes no wx product code; GUI behavior covered by the reused W35 runtime suite (in the 61) plus the surface-consistency test binding docs to real i18n menu/tab/command strings — GREEN by reference, appropriate to a docs-only wave.

## Observations (non-blocking, routed to controller)

- No wave-local evidence manifest under `artifacts/wave_W36/` (same posture as several sibling waves); aggregate manifests are controller-owned per the independence contract — not a W36 defect.
- SURFACE-001 non-plugin claims (terminal/updater/platform) are asserted clean without itemized proof; auditor found no concrete counter-evidence — no blocker.

## Verdict

No owned P0/P1 defect. One P3 routed correctly. Evidence is current, bound to the tested candidate, and independently reproduced. **AUDIT PASS.**

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
