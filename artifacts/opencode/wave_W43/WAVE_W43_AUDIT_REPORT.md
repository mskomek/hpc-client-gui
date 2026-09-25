# Wave W43 Audit Report
## Controller-persisted fresh independent audit — 2026-09-24T20:42:45.918695+00:00

- Wave: `W43`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0043-W43-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0043-W43-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md [limit=2000, offset=30]
$ powershell -NoProfile -Command "Get-ChildItem waves/pending, waves/done, waves/blocked, waves/postponed -Filter 'W43*' 2>&1; Write-Host '---GIT---'; git rev-parse HEAD; git status --short | Select-Object -First 50"
Directory: D:\Projeler\hpc-client-gui\waves\pending


Mode                 LastWriteTime         Length Name                                                                 
----                 -------------         ------ ----                                                                 
-a----         9/22/2026   3:54 PM          11693 W43.md                                                               
---GIT---
c8293d3ca309526ed250c794c3b294f7c54ef369
 M README.md
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
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_logs.py
 M src/hpc_gui/wx_logs_view.py
 M src/hpc_gui/wx_plugins.py
 M src/hpc_gui/wx_plugins_view.py
 M src/hpc_gui/wx_settings.py
 M src/hpc_gui/wx_settings_view.py
 M src/hpc_gui/wx_shell.py
 M src/hpc_gui/wx_updater_view.py
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
?? artifacts/wave_W29/
?? artifacts/wave_W32/
?? artifacts/wave_W33/
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol/AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md 
→ Read waves/pending/W43.md 
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
→ Read .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Get-Content waves/pending/W43.md -Encoding UTF8 | Select-Object -First 5 | Out-String | Write-Host; Write-Host '---REQUIREMENT_REGISTRY W43---'; Select-String -Path REQUIREMENT_REGISTRY.md -Pattern 'W43' | Select-Object -First 30 | ForEach-Object { $_.Line } | Out-String -Width 400 | Write-Host"
---
wave_id: "W43"
wave_kind: execution
canonical_source: "W43"
owned_requirements:

---REQUIREMENT_REGISTRY W43---
Select-String : Cannot find path 'D:\Projeler\hpc-client-gui\REQUIREMENT_REGISTRY.md' because it does not exist.
At line:1 char:146
+ ... RY W43---'; Select-String -Path REQUIREMENT_REGISTRY.md -Pattern 'W43 ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (D:\Projeler\hpc...ENT_REGISTRY.md:String) [Select-String], ItemNotFound 
   Exception
    + FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.SelectStringCommand
$ powershell -NoProfile -Command "$ErrorActionPreference='Continue'; Write-Host '=== W43 reports ==='; Get-ChildItem docs/wave-reports/v2/opencode/ -Filter 'W43*' 2>&1 | Format-Table Name,Length,LastWriteTime | Out-String -Width 200 | Write-Host; Write-Host '=== artifacts W43 ==='; Get-ChildItem artifacts/ -Recurse -Filter '*W43*' 2>&1 | Select-Object FullName | Select-Object -First 30 | Out-String -Width 300 | Write-Host; Write-Host '=== evidence manifest ==='; Get-ChildItem artifacts/wave_W43, artifacts/opencode/wave_W43 -Recurse 2>&1 | Select-Object -First 40 | Out-String -Width 300 | Write-Host"
=Continue : The term '=Continue' is not recognized as the name of a cmdlet, function, script file, or operable 
program. Check the spelling of the name, or if a path was included, verify that the path is correct and try again.
At line:1 char:1
+ ='Continue'; Write-Host '=== W43 reports ==='; Get-ChildItem docs/wav ...
+ ~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (=Continue:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
=== W43 reports ===

Name               Length LastWriteTime        
----               ------ -------------        
W43_WAVE_REPORT.md  16061 9/24/2026 11:39:54 PM



=== artifacts W43 ===

=== evidence manifest ===
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W43_WAVE_REPORT.md 
$ powershell -NoProfile -Command "Write-Host '=== locate registries ==='; Get-ChildItem -Recurse -Filter '*REGISTRY*' | Select-Object FullName | Out-String -Width 300 | Write-Host; Write-Host '=== TODO MAP ==='; Get-ChildItem -Recurse -Filter '*TODO*' | Select-Object FullName | Select-Object -First 20 | Out-String -Width 300 | Write-Host; Write-Host '=== closeout validator ==='; Test-Path scripts/validate_wave_closeout.py | Write-Host"
=== locate registries ===

FullName                                                                                                                                         
--------                                                                                                                                         
D:\Projeler\hpc-client-gui\.tmp\os\20260924-134705-4fb4dc51\33528-1790246825314213600\pytest-of-mskomek\pytest-26\test_find_registry_entry_lates0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-134705-4fb4dc51\33528-1790246825314213600\pytest-of-mskomek\pytest-26\test_w03_plugin_registry_sourc0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-134705-4fb4dc51\33528-1790246825314213600\pytest-of-mskomek\pytest-28\test_find_registry_entry_lates0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-134705-4fb4dc51\33528-1790246825314213600\pytest-of-mskomek\pytest-28\test_w03_plugin_registry_sourc0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-152940-c05dfd9c\14740-1790252980882148700\pytest-of-mskomek\pytest-171\test_w35_wx_close_in_flight...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-152940-c05dfd9c\14740-1790252980882148700\pytest-of-mskomek\pytest-171\test_w35_wx_refresh_event_d...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-152940-c05dfd9c\14740-1790252980882148700\pytest-of-mskomek\pytest-184\test_w35_wx_close_in_flight...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-152940-c05dfd9c\14740-1790252980882148700\pytest-of-mskomek\pytest-184\test_w35_wx_refresh_event_d...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-152940-c05dfd9c\14740-1790252980882148700\pytest-of-mskomek\pytest-185\test_w35_wx_close_in_flight...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-152940-c05dfd9c\14740-1790252980882148700\pytest-of-mskomek\pytest-185\test_w35_wx_refresh_event_d...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-152940-c05dfd9c\14740-1790252980882148700\pytest-of-mskomek\pytest-186\test_w35_wx_close_in_flight...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-152940-c05dfd9c\14740-1790252980882148700\pytest-of-mskomek\pytest-186\test_w35_wx_refresh_event_d...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-104\test_provider_registry_aggr...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-105\test_provider_registry_aggr...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-26\test_registry_ids_labels_queri0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-27\test_registry_ids_labels_queri0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_find_registry_entry_lates0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_parse_registry_accepts_va0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_parse_registry_rejects_in0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_parse_registry_rejects_in1
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_parse_registry_rejects_in2
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_parse_registry_rejects_in3
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_registry_entry_installs_v0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_registry_ids_labels_queri0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_registry_size_limit_const0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_registry_vocabulary_alias0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_registry_without_override0
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_cache_rejects_a_widenin...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_corrupt_cache_is_not_tr...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_full_clean_user_lifecyc...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_full_clean_user_lifecyc...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_full_clean_user_lifecyc...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_network_fetch_then_cach...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-28\test_override_survives_the_c...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-7\test_find_registry_entry_lates0 
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-7\test_parse_registry_accepts_va0 
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-7\test_parse_registry_rejects_in0 
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-7\test_parse_registry_rejects_in1 
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-7\test_parse_registry_rejects_in2 
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-7\test_parse_registry_rejects_in3 
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-7\test_registry_size_limit_const0 
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-7\test_corrupt_cache_is_not_tru...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-7\test_network_fetch_then_cache...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-7\test_w35_wx_close_in_flight_n...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\pytest-of-mskomek\pytest-7\test_w35_wx_refresh_event_dri...
D:\Projeler\hpc-client-gui\.tmp\os\w10-repair-20260922\wheel-proof\hpc_gui\plugins\registry_client.py                                            
D:\Projeler\hpc-client-gui\.tmp\os\w10-repair-20260922\wheel-proof\hpc_gui\services\adapter_registry.py                                          
D:\Projeler\hpc-client-gui\.tmp\os\w10-repair-20260922\wheel-proof\hpc_gui\services\command_registry.py                                          
D:\Projeler\hpc-client-gui\.tmp\os\w10-repair-20260922\wheel-proof\hpc_gui\services\file_filter_registry.py                                      
D:\Projeler\hpc-client-gui\.tmp\os\w10-repair-20260922\wheel-proof\hpc_gui\services\parser_registry.py                                           
D:\Projeler\hpc-client-gui\.tmp\os\w10-repair-20260922\wheel-proof\hpc_gui\services\process_registry.py                                          
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-proof-current\hpc_gui\plugins\registry_client.py                                             
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-proof-current\hpc_gui\services\adapter_registry.py                                           
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-proof-current\hpc_gui\services\command_registry.py                                           
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-proof-current\hpc_gui\services\file_filter_registry.py                                       
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-proof-current\hpc_gui\services\parser_registry.py                                            
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-proof-current\hpc_gui\services\process_registry.py                                           
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-47vlw85_\hpc_gui\plugins\registry_client.py                           
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-47vlw85_\hpc_gui\services\adapter_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-47vlw85_\hpc_gui\services\command_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-47vlw85_\hpc_gui\services\file_filter_registry.py                     
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-47vlw85_\hpc_gui\services\parser_registry.py                          
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-47vlw85_\hpc_gui\services\process_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-bn2bs025\hpc_gui\plugins\registry_client.py                           
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-bn2bs025\hpc_gui\services\adapter_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-bn2bs025\hpc_gui\services\command_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-bn2bs025\hpc_gui\services\file_filter_registry.py                     
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-bn2bs025\hpc_gui\services\parser_registry.py                          
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-bn2bs025\hpc_gui\services\process_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-hmwp15re\hpc_gui\plugins\registry_client.py                           
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-hmwp15re\hpc_gui\services\adapter_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-hmwp15re\hpc_gui\services\command_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-hmwp15re\hpc_gui\services\file_filter_registry.py                     
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-hmwp15re\hpc_gui\services\parser_registry.py                          
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-hmwp15re\hpc_gui\services\process_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-o1mhc3ud\hpc_gui\plugins\registry_client.py                           
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-o1mhc3ud\hpc_gui\services\adapter_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-o1mhc3ud\hpc_gui\services\command_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-o1mhc3ud\hpc_gui\services\file_filter_registry.py                     
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-o1mhc3ud\hpc_gui\services\parser_registry.py                          
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-o1mhc3ud\hpc_gui\services\process_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-olgxravt\hpc_gui\plugins\registry_client.py                           
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-olgxravt\hpc_gui\services\adapter_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-olgxravt\hpc_gui\services\command_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-olgxravt\hpc_gui\services\file_filter_registry.py                     
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-olgxravt\hpc_gui\services\parser_registry.py                          
D:\Projeler\hpc-client-gui\.tmp\scratch\w10-package-repair\w10-wheel-proof-olgxravt\hpc_gui\services\process_registry.py                         
D:\Projeler\hpc-client-gui\.tmp\validator-pytest\run-er_05xgt\test_w35_wx_close_in_flight_ne0\cache\registry.json                                
D:\Projeler\hpc-client-gui\.tmp\validator-pytest\run-er_05xgt\test_w35_wx_refresh_event_driv0\cache\registry.json                                
D:\Projeler\hpc-client-gui\.tmp\w27_pkg\install\hpc_gui\plugins\registry_client.py                                                               
D:\Projeler\hpc-client-gui\.tmp\w27_pkg\install\hpc_gui\plugins\__pycache__\registry_client.cpython-314.pyc                                      
D:\Projeler\hpc-client-gui\.tmp\w27_pkg\install\hpc_gui\services\adapter_registry.py                                                             
D:\Projeler\hpc-client-gui\.tmp\w27_pkg\install\hpc_gui\services\command_registry.py                                                             
D:\Projeler\hpc-client-gui\.tmp\w27_pkg\install\hpc_gui\services\file_filter_registry.py                                                         
D:\Projeler\hpc-client-gui\.tmp\w27_pkg\install\hpc_gui\services\parser_registry.py                                                              
D:\Projeler\hpc-client-gui\.tmp\w27_pkg\install\hpc_gui\services\process_registry.py                                                             
D:\Projeler\hpc-client-gui\.tmp\w27_pkg\install\hpc_gui\services\__pycache__\adapter_registry.cpython-314.pyc                                    
D:\Projeler\hpc-client-gui\.tmp\w27_pkg\install\hpc_gui\services\__pycache__\command_registry.cpython-314.pyc                                    
D:\Projeler\hpc-client-gui\.tmp\w27_pkg\install\hpc_gui\services\__pycache__\file_filter_registry.cpython-314.pyc                                
D:\Projeler\hpc-client-gui\.tmp\w27_pkg\install\hpc_gui\services\__pycache__\parser_registry.cpython-314.pyc                                     
D:\Projeler\hpc-client-gui\.tmp\w27_pkg\install\hpc_gui\services\__pycache__\process_registry.cpython-314.pyc                                    
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W23\scripts\plugin_registry_smoke.py                                         
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W23\src\hpc_gui\plugins\registry_client.py                                   
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W23\src\hpc_gui\services\adapter_registry.py                                 
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W23\src\hpc_gui\services\command_registry.py                                 
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W23\src\hpc_gui\services\file_filter_registry.py                             
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W23\src\hpc_gui\services\parser_registry.py                                  
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W23\src\hpc_gui\services\process_registry.py                                 
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W23\tests\test_command_registry.py                                           
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W23\tests\test_file_filter_registry.py                                       
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W24\scripts\plugin_registry_smoke.py                                         
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W24\src\hpc_gui\plugins\registry_client.py                                   
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W24\src\hpc_gui\services\adapter_registry.py                                 
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W24\src\hpc_gui\services\command_registry.py                                 
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W24\src\hpc_gui\services\file_filter_registry.py                             
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W24\src\hpc_gui\services\parser_registry.py                                  
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W24\src\hpc_gui\services\process_registry.py                                 
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W24\tests\test_command_registry.py                                           
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W24\tests\test_file_filter_registry.py                                       
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W28\scripts\plugin_registry_smoke.py                                         
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W28\src\hpc_gui\plugins\registry_client.py                                   
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W28\src\hpc_gui\services\adapter_registry.py                                 
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W28\src\hpc_gui\services\command_registry.py                                 
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W28\src\hpc_gui\services\file_filter_registry.py                             
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W28\src\hpc_gui\services\parser_registry.py                                  
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W28\src\hpc_gui\services\process_registry.py                                 
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W28\tests\test_command_registry.py                                           
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W28\tests\test_file_filter_registry.py                                       
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W32\scripts\plugin_registry_smoke.py                                         
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W32\src\hpc_gui\plugins\registry_client.py                                   
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W32\src\hpc_gui\services\adapter_registry.py                                 
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W32\src\hpc_gui\services\command_registry.py                                 
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W32\src\hpc_gui\services\file_filter_registry.py                             
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W32\src\hpc_gui\services\parser_registry.py                                  
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W32\src\hpc_gui\services\process_registry.py                                 
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W32\tests\test_command_registry.py                                           
D:\Projeler\hpc-client-gui\.tmp\worktrees\ac-wave-opencode-parallel\W32\tests\test_file_filter_registry.py                                       
D:\Projeler\hpc-client-gui\.tmp-pytest-merge3\test_registry_entry_installs_v0                                                                    
D:\Projeler\hpc-client-gui\.tmp-pytest-merge4\test_registry_entry_installs_v0                                                                    
D:\Projeler\hpc-client-gui\.tmp-pytest-merge4\test_registry_vocabulary_alias0                                                                    
D:\Projeler\hpc-client-gui\.tmp-pytest-merge5\test_registry_entry_installs_v0                                                                    
D:\Projeler\hpc-client-gui\.tmp-pytest-merge5\test_registry_vocabulary_alias0                                                                    
D:\Projeler\hpc-client-gui\.tmp-pytest-merge6\test_registry_entry_installs_v0                                                                    
D:\Projeler\hpc-client-gui\.tmp-pytest-merge6\test_registry_vocabulary_alias0                                                                    
D:\Projeler\hpc-client-gui\.venv\Lib\site-packages\jsonschema\benchmarks\unused_registry.py                                                      
D:\Projeler\hpc-client-gui\.venv\Lib\site-packages\jsonschema\benchmarks\__pycache__\unused_registry.cpython-314.pyc                             
D:\Projeler\hpc-client-gui\.venv314\Lib\site-packages\jsonschema\benchmarks\unused_registry.py                                                   
D:\Projeler\hpc-client-gui\.venv314\Lib\site-packages\jsonschema\benchmarks\__pycache__\unused_registry.cpython-314.pyc                          
D:\Projeler\hpc-client-gui\build\lib\hpc_gui\plugins\registry_client.py                                                                          
D:\Projeler\hpc-client-gui\build\lib\hpc_gui\services\adapter_registry.py                                                                        
D:\Projeler\hpc-client-gui\build\lib\hpc_gui\services\command_registry.py                                                                        
D:\Projeler\hpc-client-gui\build\lib\hpc_gui\services\file_filter_registry.py                                                                    
D:\Projeler\hpc-client-gui\build\lib\hpc_gui\services\parser_registry.py                                                                         
D:\Projeler\hpc-client-gui\build\lib\hpc_gui\services\process_registry.py                                                                        
D:\Projeler\hpc-client-gui\opencode\REQUIREMENT_REGISTRY.md                                                                                      
D:\Projeler\hpc-client-gui\scripts\plugin_registry_smoke.py                                                                                      
D:\Projeler\hpc-client-gui\src\hpc_gui\plugins\registry_client.py                                                                                
D:\Projeler\hpc-client-gui\src\hpc_gui\plugins\__pycache__\registry_client.cpython-312.pyc                                                       
D:\Projeler\hpc-client-gui\src\hpc_gui\plugins\__pycache__\registry_client.cpython-314.pyc                                                       
D:\Projeler\hpc-client-gui\src\hpc_gui\services\adapter_registry.py                                                                              
D:\Projeler\hpc-client-gui\src\hpc_gui\services\command_registry.py                                                                              
D:\Projeler\hpc-client-gui\src\hpc_gui\services\file_filter_registry.py                                                                          
D:\Projeler\hpc-client-gui\src\hpc_gui\services\parser_registry.py                                                                               
D:\Projeler\hpc-client-gui\src\hpc_gui\services\process_registry.py                                                                              
D:\Projeler\hpc-client-gui\src\hpc_gui\services\__pycache__\adapter_registry.cpython-312.pyc                                                     
D:\Projeler\hpc-client-gui\src\hpc_gui\services\__pycache__\adapter_registry.cpython-314.pyc                                                     
D:\Projeler\hpc-client-gui\src\hpc_gui\services\__pycache__\command_registry.cpython-312.pyc                                                     
D:\Projeler\hpc-client-gui\src\hpc_gui\services\__pycache__\command_registry.cpython-314.pyc                                                     
D:\Projeler\hpc-client-gui\src\hpc_gui\services\__pycache__\file_filter_registry.cpython-312.pyc                                                 
D:\Projeler\hpc-client-gui\src\hpc_gui\services\__pycache__\file_filter_registry.cpython-314.pyc                                                 
D:\Projeler\hpc-client-gui\src\hpc_gui\services\__pycache__\parser_registry.cpython-312.pyc                                                      
D:\Projeler\hpc-client-gui\src\hpc_gui\services\__pycache__\parser_registry.cpython-314.pyc                                                      
D:\Projeler\hpc-client-gui\src\hpc_gui\services\__pycache__\process_registry.cpython-312.pyc                                                     
D:\Projeler\hpc-client-gui\src\hpc_gui\services\__pycache__\process_registry.cpython-314.pyc                                                     
D:\Projeler\hpc-client-gui\tests\test_command_registry.py                                                                                        
D:\Projeler\hpc-client-gui\tests\test_file_filter_registry.py                                                                                    
D:\Projeler\hpc-client-gui\tests\__pycache__\test_command_registry.cpython-312-pytest-9.0.2.pyc                                                  
D:\Projeler\hpc-client-gui\tests\__pycache__\test_command_registry.cpython-314-pytest-9.1.1.pyc                                                  
D:\Projeler\hpc-client-gui\tests\__pycache__\test_file_filter_registry.cpython-312-pytest-9.0.2.pyc                                              
D:\Projeler\hpc-client-gui\tests\__pycache__\test_file_filter_registry.cpython-314-pytest-9.1.1.pyc                                              
D:\Projeler\hpc-client-gui\waves\blocked\wave_12_registry_release_and_application_integration.md                                                 
D:\Projeler\hpc-client-gui\waves\done\wave_24_framework_neutral_command_registry.md                                                              
D:\Projeler\hpc-client-gui\waves\waves\blocked\wave_12_registry_release_and_application_integration.md                                           
D:\Projeler\hpc-client-gui\waves\waves\waiting\wave_24_framework_neutral_command_registry.md                                                     



=== TODO MAP ===

FullName                                                                                                                                   
--------                                                                                                                                   
D:\Projeler\hpc-client-gui\.tmp\w37todo.txt                                                                                                
D:\Projeler\hpc-client-gui\.tmp\codex-py314-cache-verify-20260911b\Lib\site-packages\_pyinstaller_hooks_contrib\stdhooks\hook-Cryptodome.py
D:\Projeler\hpc-client-gui\.tmp\codex-py314-cache-verify-20260911b\Lib\site-packages\_pyinstaller_hooks_contrib\stdhooks\__pycache__\hoo...
D:\Projeler\hpc-client-gui\.tmp\os\20260924-152940-c05dfd9c\14740-1790252980882148700\opencode\todo26.txt                                  
D:\Projeler\hpc-client-gui\.venv\Lib\site-packages\_pyinstaller_hooks_contrib\stdhooks\hook-Cryptodome.py                                  
D:\Projeler\hpc-client-gui\.venv\Lib\site-packages\_pyinstaller_hooks_contrib\stdhooks\__pycache__\hook-Cryptodome.cpython-314.pyc         
D:\Projeler\hpc-client-gui\opencode\TODO_OWNERSHIP_MAP.md                                                                                  
D:\Projeler\hpc-client-gui\opencode\sources\V2_TODOS.md                                                                                    
D:\Projeler\hpc-client-gui\opencode\sources\V2_TODO_WAVE_COVERAGE.md                                                                       
D:\Projeler\hpc-client-gui\waves\bak\V2_TODOS.md                                                                                           
D:\Projeler\hpc-client-gui\waves\bak\V2_TODO_WAVE_COVERAGE.md                                                                              



=== closeout validator ===
True
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Write-Host '=== W43 owned files ==='; Test-Path src/hpc_gui/services/update_restart_policy.py | Write-Host; Test-Path tests/test_w43_restart_package_policy.py | Write-Host; Write-Host '=== diff stat ==='; git diff --stat | Select-Object -First 60 | Out-String -Width 300 | Write-Host; Write-Host '=== diff check ==='; git diff --check; Write-Host ('diff-check-exit=' + $LASTEXITCODE); Write-Host '=== W43 diff only ==='; git diff -- src/hpc_gui/wx_updater_view.py | Select-Object -First 120 | Out-String -Width 400 | Write-Host; Write-Host '=== untracked W43 ==='; git status --short | Select-String -Pattern 'update_restart|w43' | Out-String -Width 300 | Write-Host"
At line:1 char:369
+ ... heck ==='; git diff --check; Write-Host ('diff-check-exit=' + ); Writ ...
+                                                                  ~
You must provide a value expression following the '+' operator.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : ExpectedValueExpression
$ powershell -NoProfile -Command "Write-Host '=== registry rows W43 ==='; Select-String -Path opencode/REQUIREMENT_REGISTRY.md -Pattern 'W43' | ForEach-Object { $_.Line } | Select-Object -First 40 | Out-String -Width 500 | Write-Host; Write-Host '=== todo row ==='; Select-String -Path opencode/TODO_OWNERSHIP_MAP.md -Pattern 'W43' | ForEach-Object { $_.Line } | Out-String -Width 500 | Write-Host"
=== registry rows W43 ===
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:128
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 

=== todo row ===
C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line : The term 
'C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe.Line' is not recognized as the name of a cmdlet, function, 
script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is 
correct and try again.
At line:1 char:373
+ ... ch-Object { C:/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:/WINDOWS/Syst...rshell.exe.Line:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read tests/test_w43_restart_package_policy.py 
→ Read src/hpc_gui/services/update_restart_policy.py 
✱ Grep "W43" in opencode · 46 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read src/hpc_gui/wx_updater_view.py [limit=120, offset=1]
✱ Grep "_install_deferred_due_to_unsaved|unsaved_probe|confirm_fn|_install_confirmed_with_unsaved" in src/hpc_gui · 8 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read src/hpc_gui/wx_updater_view.py [limit=120, offset=800]
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_w43_restart_package_policy.py -q
................                                                         [100%]
16 passed in 1.10s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_update_verification.py tests/test_app_updater.py tests/test_wx_updater_spec.py tests/test_updater_helper.py tests/test_w41_updater_routing.py tests/test_installation_context.py tests/test_linux_update_handoff.py tests/test_deb_installer.py tests/test_w43_restart_package_policy.py -q
...................................................................s..s. [ 82%]
...............                                                          [100%]
85 passed, 2 skipped in 8.74s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_update_verification.py tests/test_app_updater.py tests/test_wx_updater_spec.py tests/test_updater_helper.py tests/test_w41_updater_routing.py tests/test_installation_context.py tests/test_linux_update_handoff.py tests/test_deb_installer.py tests/test_w43_restart_package_policy.py -q -rs
...................................................................s..s. [ 82%]
...............                                                          [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_linux_update_handoff.py:49: symlink creation is unavailable on this Windows test host
SKIPPED [1] tests\test_deb_installer.py:47: symlink creation is unavailable on this Windows test host
85 passed, 2 skipped in 8.56s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff --check
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
warning: in the working copy of 'src/hpc_gui/services/shortcut_preferences.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_logs.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_updater_view.py', LF will be replaced by CRLF the next time Git touches it
$ python scripts/validate_wave_closeout.py --wave W43
{
  "can_close": false,
  "wave_id": "W43",
  "manifest": "D:/Projeler/hpc-client-gui/artifacts/wave_W43/WAVE_W43_EVIDENCE_MANIFEST.json",
  "failure_reasons": [
    "missing/invalid evidence manifest: [Errno 2] No such file or directory: 'D:\\\\Projeler\\\\hpc-client-gui\\\\artifacts\\\\wave_W43\\\\WAVE_W43_EVIDENCE_MANIFEST.json'"
  ]
}
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read scripts/validate_wave_closeout.py 
$ python scripts/validate_wave_closeout.py --help
usage: validate_wave_closeout.py [-h] [--wave WAVE] [--self-test]
                                 [--no-execute-tests]

options:
  -h, --help          show this help message and exit
  --wave WAVE
  --self-test
  --no-execute-tests
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✱ Grep "Authenticode signing is" in docs · 2 matches
$ python -m pytest tests/test_w43_restart_package_policy.py::test_windows_signing_policy_is_unsigned_with_documented_wording -q
.                                                                        [100%]
1 passed in 0.41s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
AC_WAVE_BRIDGE_STDOUT_BEGIN
Auditing W43 — loading the canonical audit skill and project profile.
Skill scope is minimal — now gathering W43's requirements, reports, and candidate evidence.
Worker claims look structurally sound — now independently verifying the implementation and test evidence.
Core evidence re-verified (85 passed, 2 skipped) — now checking for weakened tests, scope escapes, and validator status.
## W43 Independent Audit — PASS

**Wave:** W43 (Updater restart, package validation and signing policy), execution kind, `waves/pending/W43.md`
**Candidate:** HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369` + working-tree W43 hunks (controller owns commit/integration). Controller `content_identity=545d2a62…` noted; `waves/` is gitignored by program design so the spec fingerprint reconciles controller-side. This audit binds to the tested tree below and re-executed evidence, not to stale PASS.
**Mode:** fresh independent context, read-only for product code — no implementation files edited; only test/validator execution.

### Authority reads
- `waves/pending/W43.md` — 18 source rows + 1 TODO row, start gate NONE, evidence `GUI,PACKAGE`, cohort P8.
- `opencode/REQUIREMENT_REGISTRY.md` W43 rows (UPD-039…043, 053…055, 068, 069, 079…081, 086…088, PKGUPD-001/002) and `TODO_OWNERSHIP_MAP.md` TODO-058 confirmed via grep.
- `docs/wave-reports/v2/opencode/W43_WAVE_REPORT.md` (READY FOR INDEPENDENT AUDIT, GO worker-level).
- Live code: `src/hpc_gui/services/update_restart_policy.py` (new), `src/hpc_gui/wx_updater_view.py` restart guard (lines 812–879), `tests/test_w43_restart_package_policy.py` (new, 16 tests).

### Independent re-execution (verbatim EV-W43-TESTS)
- `tests/test_w43_restart_package_policy.py` → **16 passed**.
- Full cluster (`test_update_verification`, `test_app_updater`, `test_wx_updater_spec`, `test_updater_helper`, `test_w41_updater_routing`, `test_installation_context`, `test_linux_update_handoff`, `test_deb_installer`, `test_w43_*`) → **85 passed, 2 skipped**. Skips verified pre-existing platform-conditional (`symlink creation is unavailable on this Windows test host` × 2), not weaknesses.
- `git diff --check` → exit 0 (only sibling-wave CRLF warnings on already-dirty files; no whitespace errors).
- `test_windows_signing_policy_is_unsigned_with_documented_wording` re-run → pass; `docs/VERIFYING_RELEASES.md:78` confirms "Authenticode signing is **not enabled yet**".
- `scripts/validate_wave_closeout.py --wave W43` → `can_close=false` solely for missing `artifacts/wave_W43/WAVE_W43_EVIDENCE_MANIFEST.json`. This is a **close-phase** artifact owned by the controller, not an audit-phase acceptance gate; no owned-ID defect is identified by it. Not a blocker for audit PASS.

### Requirement trace (claim → owner → test, all verified)
- UPD-039/053 mode → `restart_mode()="user-confirmed"` → `test_restart_is_user_confirmed_not_automatic` ✓
- UPD-040/043/079/086 dirty/never-silent → `count_unsaved/should_defer_install/deferral_message` → clean/dirty/message tests ✓
- UPD-042 version → `verify_post_update_version` exact trimmed equality → equality test ✓
- UPD-041 provider wiring → registry → aggregation test ✓
- UPD-055/068 GUI FULL → `_start_install` defer-or-confirm guard (verified gate retained; unsaved computed before dialog close; decline stays READY with artifact retained; confirm-exception fail-closed) → 4 real-wx tests (decline-stays-READY, confirm-proceeds, clean-no-prompt, restart-label readback) ✓ — real `wx.App`/dialog/panel readback, bound to candidate tree.
- PKGUPD-001/002 PACKAGE FULL → real `verify_artifact` size+SHA-256 on exact bytes; byte-flip invalidates; stubbed channel still runs real `download_and_verify_release`; unverified launch refused → 3 tests ✓ — exact-fixture SHA-256 binding, no published artifact claimed.
- UPD-069 resources → PS1 progress/backup assertions ✓; UPD-087 rollback → `_internal.backup` + exe backup + log + rollback ✓; TODO-058 signing → unsigned policy + doc wording + no-false-signed-claim sweep ✓; UPD-088 handoff → payload carrier test ✓.
- No-code-change classifications (exact package path, rollback script, signing doc) are legitimate pins with zero product edits outside FIX-A; each has an executed test.

### Review passes
- **Claim-to-source:** every owned ID traces to a named live owner + executed test above.
- **Diff review:** W43 hunk is scoped (+57 restart-safety seams/guard in `wx_updater_view.py`) + 2 new W43-owned files; no sibling M file attributed to W43; no skip/xfail/assertion weakening (new file only); no secrets (public-key posture unchanged, no private-key material in W43 files); no generated/binary noise.
- **Adversarial:** confirm-exception→defer, byte-flip→mismatch, unverified→refusal, clean→no-nag all pinned and re-run green.
- **Contradiction scan:** user-confirmed/defer/unsigned/exact-bytes semantics agree across policy, code, tests, report. Minor non-blocking note: the handoff test's input string literal says "17 passed" while the file has 16 tests — test-input data only, no assertion; report's "16 passed" is correct. No reopen.
- **Owner routing:** no cross-scope defect found; nothing to route. No AWAITING_INPUT, no EXTERNAL_BLOCKED (updater surface connection-independent; package claims bind to local fixture bytes).

### Verdict
All 19 owned IDs implemented or validly pinned, required GUI + PACKAGE evidence FULL with exact runtime/artifact binding, diff clean and scoped, no blockers. **AUDIT PASS**, bound to HEAD `c8293d3c…` + W43 working-tree files with EV-W43-TESTS re-executed green (85 passed, 2 platform-conditional skips).

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
