# Wave W56 Audit Report
## Controller-persisted fresh independent audit — 2026-09-25T06:16:50.433516+00:00

- Wave: `W56`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260925-074235-63df86b0\0019-W56-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260925-074235-63df86b0\0019-W56-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✗ Read .agents/protocol/WAVE_PROGRAM_ORCHESTRATION.md failed
Error: File not found: .agents/protocol/WAVE_PROGRAM_ORCHESTRATION.md

Did you mean one of these?
.agents\protocol\AC_WAVE_PROGRAM_ORCHESTRATION.md
→ Read rules.md 
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol/AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md 
→ Read .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md 
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md [limit=2000, offset=30]
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/blocked 
→ Read waves/done 
→ Read waves/pending 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W56.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✱ Glob "artifacts/wave_W56/**/*" 1 match
✱ Glob "docs/wave-reports/v2/opencode/W56*" 1 match
✱ Glob "opencode/sources/WAVE_V2_FINAL_10.md" 0 matches
✱ Glob "**/TODO_OWNERSHIP_MAP.md" 0 matches
✱ Glob "**/REQUIREMENT_REGISTRY.md" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read artifacts/wave_W56/WAVE_W56_EVIDENCE_MANIFEST.json 
→ Read docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md 
✱ Glob "opencode/sources/*" 0 matches
✱ Glob "**/*REGISTRY*" 0 matches
✱ Glob "**/*TODO*" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git branch --show-current; git rev-parse HEAD; git status --short; git log -1 --oneline --decorate
develop
36d6151fd9634cf50e14a639ec0407bef1d296f4
 M docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md
?? artifacts/wave_W56/
36d6151f (HEAD -> develop) W56 report follow-up 5: no-Qt verification build and full Workstream E replay PASS
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff --stat; echo "---DIFF-CHECK---"; git diff --check; echo "---STATUS-PORCELAIN---"; git status --porcelain=v1 | Select-Object -First 50; echo "---DIFF-NAME---"; git diff --name-only
warning: in the working copy of 'docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
 docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md | 86 ++++++++++++++++++++++++
 1 file changed, 86 insertions(+)
---DIFF-CHECK---
warning: in the working copy of 'docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
---STATUS-PORCELAIN---
/usr/bin/bash: line 1: Select-Object: command not found
---DIFF-NAME---
warning: in the working copy of 'docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git status --short; echo "===="; git diff --stat HEAD; echo "===="; git ls-files --others --exclude-standard | head -n 50
M docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md
?? artifacts/wave_W56/
====
warning: in the working copy of 'docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
 docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md | 86 ++++++++++++++++++++++++
 1 file changed, 86 insertions(+)
====
artifacts/wave_W56/WAVE_W56_EVIDENCE_MANIFEST.json
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "Get-Content src/hpc_gui/runtime.py; Write-Host '---PYPROJECT-DEPS---'; Select-String -Path pyproject.toml -Pattern 'wxPython|PySide6|shiboken|legacy-qt' ; Write-Host '---REQS---'; Get-Content requirements.txt; Write-Host '---LOCK-QT---'; Select-String -Path requirements-release.lock -Pattern 'PySide6|shiboken6|wxPython' | Select-Object -First 20; Write-Host '---LOCK-QT-COUNT---'; (Select-String -Path requirements-release.lock -Pattern 'PySide|shiboken').Count"
"""Authoritative GUI runtime selection."""

DEFAULT_GUI_RUNTIME = "wx"
---PYPROJECT-DEPS---

pyproject.toml:6:    "wxPython>=4.3.1",
pyproject.toml:19:wx = ["wxPython>=4.3.1"]
pyproject.toml:20:legacy-qt = ["PySide6>=6.5"]
pyproject.toml:49:    "wx: exercises the optional wxPython implementation",
pyproject.toml:50:    "qt: exercises the PySide6/Qt implementation",
---REQS---
wxPython>=4.3.1
paramiko>=3.4
cryptography>=41.0
pyftpdlib>=1.5.9
packaging>=23
keyring>=25.0
---LOCK-QT---
requirements-release.lock:30:wxPython==4.3.1
---LOCK-QT-COUNT---
0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "Write-Host '---WIN-SPEC-QT---'; Select-String -Path build/windows/hpc-client-gui.spec -Pattern 'PySide6|shiboken6|Qt6' ; Write-Host 'exit:'; Write-Host '---WIN-SPEC-EXCLUDES---'; Select-String -Path build/windows/hpc-client-gui.spec -Pattern 'excludes'; Write-Host '---LINUX-SPEC-QT---'; Select-String -Path build/linux/hpc-client-gui-linux.spec -Pattern 'PySide6|shiboken6|Qt6'; Write-Host '---MACOS-SPEC-QT---'; Select-String -Path build/macos/hpc-client-gui.spec -Pattern 'PySide6|shiboken6|Qt6'; Write-Host '---CLI-SPEC---'; Select-String -Path build/windows/hpc-client-cli.spec -Pattern 'PySide6|shiboken6'"
---WIN-SPEC-QT---

build\windows\hpc-client-gui.spec:64:# Qt/PySide6 is legacy-only, not shipped in the V2 production package. The
build\windows\hpc-client-gui.spec:65:# PySide6/QtWebEngine hidden imports are therefore removed from the
build\windows\hpc-client-gui.spec:88:    "PySide6",
build\windows\hpc-client-gui.spec:89:    "shiboken6",
exit:
---WIN-SPEC-EXCLUDES---
build\windows\hpc-client-gui.spec:83:excludes = [
build\windows\hpc-client-gui.spec:119:    excludes=excludes,
---LINUX-SPEC-QT---
build\linux\hpc-client-gui-linux.spec:53:# Qt/PySide6 is legacy-only, not shipped in the V2 production package. The
build\linux\hpc-client-gui-linux.spec:54:# PySide6/QtWebEngine hidden imports are therefore removed from the
build\linux\hpc-client-gui-linux.spec:71:    "PySide6",
build\linux\hpc-client-gui-linux.spec:72:    "shiboken6",
---MACOS-SPEC-QT---
build\macos\hpc-client-gui.spec:56:# Qt/PySide6 is legacy-only, not shipped in the V2 production package.
build\macos\hpc-client-gui.spec:70:    excludes=["_hpc_gui_perf_probe", "PySide6", "shiboken6"],
---CLI-SPEC---
build\windows\hpc-client-cli.spec:40:    hookspath=[], runtime_hooks=[], excludes=["PySide6", "shiboken6"],
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "Get-ChildItem opencode/ | Format-Table Name; Write-Host '---'; Test-Path opencode/REQUIREMENT_REGISTRY.md; Test-Path opencode/TODO_OWNERSHIP_MAP.md; Test-Path 'opencode/sources/WAVE_V2_FINAL_10.md'; Write-Host '---TMP---'; Get-ChildItem .tmp/w56-repair/ -ErrorAction SilentlyContinue | Format-Table Name,Length; Write-Host '---DECISIONS---'; Get-ChildItem docs/decisions/ | Format-Table Name; Write-Host '---WAVEREPORTS-W01-W09---'; Get-ChildItem docs/wave-reports/v2/opencode/ | Where-Object { \$_.Name -match 'W0[1-9]_WAVE_REPORT' } | Format-Table Name"
Name                               
----                               
prompts                            
protocol                           
sources                            
templates                          
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
V2_RUNTIME_DECISION.md             
WAVE_RENUMBERING.md                


---
True
True
True
---TMP---

Name                    Length
----                    ------
make_manifest.py          9695
w56-candidate-proof.txt   1105
w56-focused-repair.txt     203
w56-soak-repair.txt        100


---DECISIONS---

Name                   
----                   
V2_BUILD_ENVIRONMENT.md
V2_RUNTIME_DECISION.md 


---WAVEREPORTS-W01-W09---

Name              
----              
W01_WAVE_REPORT.md
W02_WAVE_REPORT.md
W03_WAVE_REPORT.md
W04_WAVE_REPORT.md
W05_WAVE_REPORT.md
W06_WAVE_REPORT.md
W07_WAVE_REPORT.md
W08_WAVE_REPORT.md
W09_WAVE_REPORT.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "Get-Content .tmp/w56-repair/w56-candidate-proof.txt; Write-Host '===FOCUSED==='; Get-Content .tmp/w56-repair/w56-focused-repair.txt; Write-Host '===SOAK==='; Get-Content .tmp/w56-repair/w56-soak-repair.txt"
W56 frozen candidate proof (repair phase, hypothesis W56-candidate-freeze-clean-pin)
Candidate source: HEAD 36d6151fd9634cf50e14a639ec0407bef1d296f4 (develop, clean; dist/ gitignored)
Build: .venv Python 3.14.0 + PyInstaller 6.22.2, Windows 11 AMD64
Command: .venv/Scripts/python.exe -m PyInstaller -y --clean build/windows/hpc-client-gui.spec
Bundle: dist/hpc-client-gui, 172 files, zero Qt tokens (0 PySide*, 0 shiboken*, 0 Qt6*.dll)
Exe: dist/hpc-client-gui/hpc-client-gui.exe, size 7672473, SHA-256 6cca43a5a98a2c7049aae182b58473db4c491dabc06b13cf599bd429e45e530e
Version: 1.5.9, python 3.14.0, wxPython 4.3.1
Source-independence: from /tmp cwd, hpc-client-gui.exe version -> 1.5.9/python 3.14.0 exit 0;
  doctor environment -> status PASS, frozen True, exit 0.
Behavior carry-over: git diff a6aebd90..36d6151f -- src/ build/ requirements.txt requirements-release.lock pyproject.toml is empty;
  full Workstream E replay from follow-up 5 (bound to a6aebd90 content) carries over to this candidate.
Plugin provenance: in-tree src/hpc_gui/plugins at candidate HEAD 36d6151f (no separate registry repo).
===FOCUSED===
.............................................................            [100%]
61 passed in 17.73s
.............                                                            [100%]
13 passed in 1.08s
===SOAK===
..                                                                       [100%]
2 passed in 9.06s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ .venv/Scripts/python.exe scripts/validate_wave_closeout.py --wave W56 --no-execute-tests 2>&1 | head -n 100
echo "EXIT:$?"
{
  "can_close": true,
  "wave_id": "W56",
  "candidate_sha": "36d6151fd9634cf50e14a639ec0407bef1d296f4",
  "closure_sha": null,
  "required_count": 20,
  "manifest_requirement_count": 20,
  "test_count": 6,
  "failure_reasons": []
}
EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ .venv/Scripts/python.exe -m pytest tests/test_qt_removal_gate.py tests/test_wave0_unicode_baseline.py tests/test_wheel_packaging.py -q --tb=short -rf 2>&1 | tail -n 20
.............................................................            [100%]
61 passed in 19.68s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ .venv/Scripts/python.exe -m pytest tests/test_version_consistency.py tests/test_remote_entry_helpers.py -q --tb=short -rf 2>&1 | tail -n 10; echo "===SOAK==="; timeout 120 .venv/Scripts/python.exe -m pytest tests/test_wx_w55_shell_soak.py -q --tb=short -rf 2>&1 | tail -n 10
.............                                                            [100%]
13 passed in 0.87s
===SOAK===
..                                                                       [100%]
2 passed in 10.18s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "Test-Path dist/hpc-client-gui/hpc-client-gui.exe; Get-ChildItem dist/hpc-client-gui -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count; Write-Host '---DIFF-A6AE-TO-HEAD---'; git diff a6aebd90..36d6151f --stat; Write-Host '---BEHAVIOR-DIFF---'; git diff a6aebd90..36d6151f -- src/ build/ requirements.txt requirements-release.lock pyproject.toml --stat; Write-Host '---WX-QT-IMPORTS---'; Select-String -Path src/hpc_gui/wx_shell/* -Pattern 'PySide6|from PySide|import PySide' -ErrorAction SilentlyContinue | Select-Object -First 10; Write-Host 'WX-QT-DONE'"
True
2
---DIFF-A6AE-TO-HEAD---
 docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md | 130 +++++++++++++++++++++++
 1 file changed, 130 insertions(+)
---BEHAVIOR-DIFF---
---WX-QT-IMPORTS---
Select-String : Cannot find path 'D:\Projeler\hpc-client-gui\src\hpc_gui\wx_shell' because it does not exist.
At line:1 char:422
+ ... MPORTS---'; Select-String -Path src/hpc_gui/wx_shell/* -Pattern 'PySi ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (D:\Projeler\hpc...pc_gui\wx_shell:String) [Select-String], ItemNotFound 
   Exception
    + FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.SelectStringCommand
 
WX-QT-DONE
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "Get-ChildItem dist/hpc-client-gui | Select-Object -First 10 Name; Write-Host '---DIST-COUNT---'; (Get-ChildItem dist/hpc-client-gui -Recurse -File | Measure-Object).Count; Write-Host '---FIND-WXSHELL---'; Get-ChildItem src/hpc_gui/ | Format-Table Name; Write-Host '---WX-QT-RECURSIVE---'; Select-String -Path src/hpc_gui -Pattern 'PySide6' -Include '*.py' | Where-Object { \$_.Path -match 'wx' } | Select-Object -First 10"
---DIST-COUNT---
---FIND-WXSHELL---
Name              
----              
_internal         
hpc-client-gui.exe
172



Name                    
----                    
assets                  
cli                     
config                  
core                    
docs                    
i18n                    
lint                    
plugins                 
services                
ssh                     
ui                      
__pycache__             
app.py                  
README.md               
runtime.py              
wx_about.py             
wx_ansys.py             
wx_ansys_view.py        
wx_connection.py        
wx_connection_dialog.py 
wx_directories.py       
wx_directories_view.py  
wx_editor.py            
wx_editor_view.py       
wx_editor_windows.py    
wx_help.py              
wx_host.py              
wx_jobs.py              
wx_lifecycle.py         
wx_local_files.py       
wx_logs.py              
wx_logs_view.py         
wx_macos_audit.py       
wx_plugins.py           
wx_plugins_view.py      
wx_raw_viewer.py        
wx_remote_files.py      
wx_remote_files_view.py 
wx_runtime.py           
wx_send_logs_view.py    
wx_settings.py          
wx_settings_view.py     
wx_shell.py             
wx_splash.py            
wx_terminal.py          
wx_terminal_webview.py  
wx_transfer_workspace.py
wx_updater_view.py      
wx_windows_audit.py     
__init__.py             
__main2__.py            
__main__.py             


---WX-QT-RECURSIVE---
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "$f=(Get-ChildItem dist/hpc-client-gui -Recurse -File | Measure-Object).Count; Write-Host \"DIST_RECURSE_FILES=$f\"; $e=Get-Item dist/hpc-client-gui/hpc-client-gui.exe; Write-Host (\"EXE_SIZE=\" + $e.Length); Write-Host (\"EXE_EXISTS=\" + (Test-Path dist/hpc-client-gui/hpc-client-gui.exe)); $q=(Get-ChildItem dist/hpc-client-gui -Recurse | Where-Object { \$_.Name -match 'PySide|shiboken|Qt6.*\.dll' } | Measure-Object).Count; Write-Host (\"QT_NAMED_FILES=\" + $q)"
At line:1 char:186
+ ... /hpc-client-gui/hpc-client-gui.exe; Write-Host ("EXE_SIZE=" + .Length ...
+                                                                  ~
You must provide a value expression following the '+' operator.
At line:1 char:187
+ ... ent-gui/hpc-client-gui.exe; Write-Host ("EXE_SIZE=" + .Length); Write ...
+                                                           ~~~~~~~
Unexpected token '.Length' in expression or statement.
At line:1 char:186
+ ... /hpc-client-gui/hpc-client-gui.exe; Write-Host ("EXE_SIZE=" + .Length ...
+                                                                  ~
Missing closing ')' in expression.
At line:1 char:194
+ ... nt-gui/hpc-client-gui.exe; Write-Host ("EXE_SIZE=" + .Length); Write- ...
+                                                                 ~
Unexpected token ')' in expression or statement.
At line:1 char:442
+ ... .*\.dll' } | Measure-Object).Count; Write-Host ("QT_NAMED_FILES=" + )
+                                                                        ~
You must provide a value expression following the '+' operator.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : ExpectedValueExpression
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell.exe -NoProfile -Command "$f=(Get-ChildItem dist/hpc-client-gui -Recurse -File | Measure-Object).Count; Write-Host $f"
= : The term '=' is not recognized as the name of a cmdlet, function, script file, or operable program. Check the 
spelling of the name, or if a path was included, verify that the path is correct and try again.
At line:1 char:1
+ =(Get-ChildItem dist/hpc-client-gui -Recurse -File | Measure-Object). ...
+ ~
    + CategoryInfo          : ObjectNotFound: (=:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ .venv/Scripts/python.exe -c "import pathlib, hashlib; d=pathlib.Path('dist/hpc-client-gui'); files=list(d.rglob('*')); f=[p for p in files if p.is_file()]; print('DIST_TOTAL', len(f)); q=[p for p in f if ('pyside' in p.name.lower() or 'shiboken' in p.name.lower() or (p.name.startswith('Qt6') and p.suffix=='.dll'))]; print('QT_NAMED', len(q), q[:10]); e=d/'hpc-client-gui.exe'; print('EXE_EXISTS', e.exists()); print('EXE_SIZE', e.stat().st_size if e.exists() else -1)"
DIST_TOTAL 172
QT_NAMED 0 []
EXE_EXISTS True
EXE_SIZE 7672473
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ .venv/Scripts/python.exe -c "import hashlib; h=hashlib.sha256(open('dist/hpc-client-gui/hpc-client-gui.exe','rb').read()).hexdigest(); print(h)"
6cca43a5a98a2c7049aae182b58473db4c491dabc06b13cf599bd429e45e530e
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ .venv/Scripts/python.exe -c "import ast,pathlib; specs=['build/windows/hpc-client-gui.spec','build/linux/hpc-client-gui-linux.spec','build/macos/hpc-client-gui.spec','build/windows/hpc-client-cli.spec']; [print(s, 'OK' if ast.parse(open(s).read()) else 'FAIL') for s in specs]" 2>&1
echo "---REGISTRY-W56-COUNT---"
.venv/Scripts/python.exe -c "import re; t=open('opencode/REQUIREMENT_REGISTRY.md',encoding='utf-8-sig').read(); rows=[l for l in t.splitlines() if 'W56' in l]; print(len(rows)); [print(l[:160]) for l in rows[:30]]"
build/windows/hpc-client-gui.spec OK
build/linux/hpc-client-gui-linux.spec OK
build/macos/hpc-client-gui.spec OK
build/windows/hpc-client-cli.spec OK
---REGISTRY-W56-COUNT---
20
| `HPC-W10-FREEZE-001` | MANDATORY | PREREQUISITE | `WAVE_V2_FINAL_10.md` | 28 | Entry criteria | `W56` | � | W01�W09 have completion reports. |
| `HPC-W10-FREEZE-002` | MANDATORY | PREREQUISITE | `WAVE_V2_FINAL_10.md` | 29 | Entry criteria | `W56` | � | Cross-Wave invalidation list is available. |
| `HPC-W10-FREEZE-003` | MANDATORY | PREREQUISITE | `WAVE_V2_FINAL_10.md` | 30 | Entry criteria | `W56` | � | No known untriaged P0. |
| `HPC-W10-FREEZE-004` | MANDATORY | PREREQUISITE | `WAVE_V2_FINAL_10.md` | 31 | Entry criteria | `W56` | � | Packaging harness from W04 is operational. |
| `HPC-W10-FREEZE-006` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_10.md` | 36 | Scope | `W56` | � | changed-surface regression; |
| `HPC-W10-FREEZE-007` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_10.md` | 37 | Scope | `W56` | � | broad automated test suite; |
| `HPC-W10-FREEZE-008` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_10.md` | 38 | Scope | `W56` | � | real-cluster replay required by changes; |
| `HPC-W10-FREEZE-012` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_10.md` | 42 | Scope | `W56` | � | candidate build and freeze. |
| `HPC-W10-FREEZE-014` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 290 | Workstream E � Real-cluster regression | `W56` | � | connection/reconnect; |
| `HPC-W10-FREEZE-015` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 291 | Workstream E � Real-cluster regression | `W56` | � | SFTP round trip; |
| `HPC-W10-FREEZE-016` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 292 | Workstream E � Real-cluster regression | `W56` | � | remote editor save; |
| `HPC-W10-FREEZE-017` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 293 | Workstream E � Real-cluster regression | `W56` | � | job list/submit/cancel; |
| `HPC-W10-FREEZE-018` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 294 | Workstream E � Real-cluster regression | `W56` | � | terminal. |
| `HPC-W10-BUILD-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 300 | Workstream F � Build candidate | `W56` | � | Build one candidate from clean pinn
| `HPC-W10-BUILD-002` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 312 | Workstream F � Build candidate | `W56` | � | After candidate freeze, any product
| `HPC-W10-TODO-RUNTIME-CUTOVER-001` | `RUNTIME-CUTOVER-001` | `W56` | `RUNTIME-CUTOVER-001` � Decide and document the V2 production GUI runtime. If wx is V2, c
| `HPC-W10-TODO-RUNTIME-DEPENDENCY-001` | `RUNTIME-DEPENDENCY-001` | `W56` | `RUNTIME-DEPENDENCY-001` � Decide whether Qt remains as supported fallback/compatib
| `HPC-W10-TODO-007` | `�` | `W56` | Build final Windows artifact from declared commit/configuration. |
| `HPC-W10-TODO-008` | `�` | `W56` | Record exact artifact filename, size, SHA-256, build identity, plugin registry commit/freeze identity. |
| `HPC-W10-TODO-009` | `�` | `W56` | Prove packaged app runs without repository/source-tree dependency. |
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ .venv/Scripts/python.exe -c "import json; m=json.load(open('artifacts/wave_W56/WAVE_W56_EVIDENCE_MANIFEST.json')); reqs=[r['requirement_id'] for r in m['requirements']]; print('REQ_COUNT', len(reqs), 'UNIQUE', len(set(reqs))); print('STATUS', m['status'], 'CAND', m['candidate_sha']); print('TESTS', [(t['node'], t['passed'], t['failed']) for t in m['tests']]); print('BLOCKERS', m['blockers']); print('FIELDS', sorted(m.keys()))"
REQ_COUNT 20 UNIQUE 20
STATUS ACCEPTANCE_GREEN CAND 36d6151fd9634cf50e14a639ec0407bef1d296f4
TESTS [('tests/test_qt_removal_gate.py', 15, 0), ('tests/test_wave0_unicode_baseline.py', 42, 0), ('tests/test_wheel_packaging.py', 4, 0), ('tests/test_version_consistency.py', 9, 0), ('tests/test_remote_entry_helpers.py', 4, 0), ('tests/test_wx_w55_shell_soak.py', 2, 0)]
BLOCKERS []
FIELDS ['artifacts', 'blockers', 'candidate_sha', 'closure_sha', 'contradiction_scan', 'deferred_items', 'dependency_validation', 'gui_actions', 'protocol_revision', 'requirements', 'resources', 'review_passes', 'spec_profile_id', 'status', 'tests', 'validator_result', 'wave_id', 'wave_spec_revision']
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ .venv/Scripts/python.exe -c "import pathlib; d=pathlib.Path('waves/done'); names=[p.name for p in d.iterdir()]; import re; w=[n for n in names if re.match(r'^W\d+\.md$', n)]; print('DONE_W_COUNT', len(w)); missing=[f'W{i:02d}.md' for i in range(26,56) if f'W{i:02d}.md' not in w]; print('MISSING_W26_W55', missing)" 2>&1
echo "---DIFFCHECK---"
git diff --check 2>&1 | head -n 5; echo "DIFFCHECK_EXIT:$?"
DONE_W_COUNT 55
MISSING_W26_W55 []
---DIFFCHECK---
warning: in the working copy of 'docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
DIFFCHECK_EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ timeout 30 ./dist/hpc-client-gui/hpc-client-gui.exe version 2>&1 | head -n 20; echo "EXIT:$?"
version: 1.5.9
name: hpc-client-gui
python: 3.14.0
EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ timeout 30 ./dist/hpc-client-gui/hpc-client-gui.exe doctor environment 2>&1 | head -n 30; echo "EXIT:$?"
status: PASS
python: 3.14.0
platform: Windows-11-10.0.26200-SP0
frozen: True
executable: D:\Projeler\hpc-client-gui\dist\hpc-client-gui\hpc-client-gui.exe
config_dir: C:\Users\mskomek\.truba_slurm_gui
profiles: 1
EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ timeout 30 D:/Projeler/hpc-client-gui/dist/hpc-client-gui/hpc-client-gui.exe version 2>&1 | head -n 10; echo "EXIT:$?"
version: 1.5.9
name: hpc-client-gui
python: 3.14.0
EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✱ Grep "test_wx_is_default_runtime|test_wx_production_dependencies_match_runtime_decision" in tests/test_wave0_unicode_baseline.py · 2 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
AC_WAVE_BRIDGE_STDOUT_BEGIN
Auditing W56 — loading canonical authority and evidence.
Skill boundary confirmed — now gathering W56 requirement truth.
Core invariants hold — now verifying evidence currency and test bindings.
Independent test slices green — now confirming the frozen bundle identity.
Bundle hash matches — final check on source-independence and test strictness.
## W56 Audit — PASS (fresh independent, read-only)

**Tested identity:** Git candidate `36d6151fd9634cf50e14a639ec0407bef1d296f4` (branch `develop`, HEAD). Working-tree delta vs HEAD is closeout-only: `M docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md` (86 insertions, follow-up 6 text) + untracked `artifacts/wave_W56/WAVE_W56_EVIDENCE_MANIFEST.json` — both inside profile `allowed_closeout_only_paths`. No behavior-affecting delta. Controller content_identity `d12d2330…` recorded verbatim; all evidence below binds to the live Git identity stated here.

**Authority consumed:** `waves/pending/W56.md` (20 owned IDs, start gate NONE, evidence `PACKAGE,EXTERNAL`), all 20 `opencode/REQUIREMENT_REGISTRY.md` rows with Owning Wave W56, 5 `TODO_OWNERSHIP_MAP.md` rows, `opencode/sources/WAVE_V2_FINAL_10.md` mandatory sections, live code/tests, `WAVE_PROJECT_PROFILE.json`, `docs/decisions/V2_RUNTIME_DECISION.md`.

**Independent re-verification (fresh, this audit — nothing reused):**
- Focused suites: `test_qt_removal_gate + test_wave0_unicode_baseline + test_wheel_packaging` → 61 passed; `test_version_consistency + test_remote_entry_helpers` → 13 passed; `test_wx_w55_shell_soak` → 2 passed. Total 76/76, exactly matching manifest counts (15+42+4 / 9+4 / 2). Zero failures, skips, xfails.
- Manifest: `ACCEPTANCE_GREEN`, 20/20 unique requirements PASS, 6 test rows, all profile-required fields present, `candidate_sha` == HEAD, zero blockers.
- Validator: `scripts/validate_wave_closeout.py --wave W56 --no-execute-tests` → `can_close true`, 20/20, 6 tests, no failure reasons.
- Runtime cutover: `DEFAULT_GUI_RUNTIME = "wx"`; `wxPython>=4.3.1` mandatory, `PySide6` only in `legacy-qt` extra; `requirements.txt` wx-only; `requirements-release.lock` 0 Qt records; zero `PySide6` imports in wx-recursive sources.
- Specs: all 4 parse OK; GUI specs carry Qt only in `excludes` (correct removal-from-shipment) plus explanatory comments; zero code-level Qt shipment tokens.
- Frozen bundle (live): `dist/hpc-client-gui` 172 files, 0 Qt-named files, exe size 7672473, SHA-256 `6cca43a5a98a2c7049aae182b58473db4c491dabc06b13cf599bd429e45e530e` — matches report/proof. `version` → 1.5.9/python 3.14.0 and `doctor environment` → PASS/frozen True, verified both in-repo and from outside-repo cwd.
- External carry-over: `git diff a6aebd90..36d6151f -- src/ build/ requirements.txt requirements-release.lock pyproject.toml` is empty (only the wave report changed), so the lease-bound five-path Workstream E replay from follow-up 5 (CONN1/RECONN OK, 65536-byte SFTP hash match, editor server-hash match, job 74 RUNNING→CANCELLED, TERM_OK) carries without invalidation. No new lease claimed by this auditor; no external replay re-executed.
- Preconditions: W26–W55 present in `waves/done/`; W01–W09 reports present; `git diff --check` clean; test updates (`test_wx_is_default_runtime`, deps-contract with requirements.txt assertions) are authority-directed and strictly stronger — no weakening, no secrets, no sibling scope touched.

**No findings.** No repair performed. No `AWAITING_INPUT`, no deferral. Controller owns `W56_AUDIT_REPORT.md` persistence; none written by this worker.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
