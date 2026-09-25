# Wave W52 Audit Report
## Controller-persisted fresh independent audit — 2026-09-24T23:05:56.187897+00:00

- Wave: `W52`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0088-W52-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0088-W52-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md [offset=30]
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Skill "ac-wave-core" 
→ Read .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md 
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
→ Read .agents/protocol/AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending 
✱ Glob "waves/**/W52*" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W52.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git status --short | Select-Object -First 50; Write-Host "---SHA---"; git rev-parse HEAD; Write-Host "---LOG---"; git log --oneline -5; Write-Host "---W52REPORT_EXISTS---"; Test-Path docs/wave-reports/v2/opencode/W52_WAVE_REPORT.md; Test-Path docs/wave-reports/v2/opencode/W52_AUDIT_REPORT.md; Test-Path artifacts/wave_W52/WAVE_W52_EVIDENCE_MANIFEST.json; Test-Path artifacts/opencode/wave_W52/WAVE_W52_EVIDENCE_MANIFEST.json
/usr/bin/bash: line 1: Select-Object: command not found
/usr/bin/bash: line 1: Write-Host: command not found
c8293d3ca309526ed250c794c3b294f7c54ef369
/usr/bin/bash: line 1: Write-Host: command not found
c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
/usr/bin/bash: line 1: Write-Host: command not found
/usr/bin/bash: line 1: Test-Path: command not found
/usr/bin/bash: line 1: Test-Path: command not found
/usr/bin/bash: line 1: Test-Path: command not found
/usr/bin/bash: line 1: Test-Path: command not found
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git status --short | head -n 50; echo "---SHA---"; git rev-parse HEAD; echo "---LOG---"; git log --oneline -5; echo "---FILES---"; ls -la docs/wave-reports/v2/opencode/W52* 2>&1; ls -la artifacts/wave_W52/ 2>&1; ls -la artifacts/opencode/wave_W52/ 2>&1
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
---SHA---
c8293d3ca309526ed250c794c3b294f7c54ef369
---LOG---
c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
---FILES---
-rw-r--r-- 1 mskomek 197121 20674 Sep 25 02:03 docs/wave-reports/v2/opencode/W52_WAVE_REPORT.md
ls: cannot access 'artifacts/wave_W52/': No such file or directory
ls: cannot access 'artifacts/opencode/wave_W52/': No such file or directory
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W52_WAVE_REPORT.md 
$ ls docs/wave-reports/v2/opencode/ | head -n 100; echo "---"; git diff --stat HEAD | head -n 60; echo "---CHECK---"; git diff --check | head -n 30
W01_AUDIT_REPORT.md
W01_WAVE_REPORT.md
W02_AUDIT_REPORT.md
W02_WAVE_REPORT.md
W03_AUDIT_REPORT.md
W03_WAVE_REPORT.md
W04_AUDIT_REPORT.md
W04_WAVE_REPORT.md
W05_AUDIT_REPORT.md
W05_WAVE_REPORT.md
W06_AUDIT_REPORT.md
W06_WAVE_REPORT.md
W07_AUDIT_REPORT.md
W07_WAVE_REPORT.md
W08_AUDIT_REPORT.md
W08_WAVE_REPORT.md
W09_AUDIT_REPORT.md
W09_WAVE_REPORT.md
W10_AUDIT_REPORT.md
W10_WAVE_REPORT.md
W11_AUDIT_REPORT.md
W11_WAVE_REPORT.md
W12_AUDIT_REPORT.md
W12_WAVE_REPORT.md
W13_AUDIT_REPORT.md
W13_WAVE_REPORT.md
W14_AUDIT_REPORT.md
W14_WAVE_REPORT.md
W15_AUDIT_REPORT.md
W15_WAVE_REPORT.md
W16_AUDIT_REPORT.md
W16_WAVE_REPORT.md
W17_AUDIT_REPORT.md
W17_WAVE_REPORT.md
W18_AUDIT_REPORT.md
W18_WAVE_REPORT.md
W19_AUDIT_REPORT.md
W19_WAVE_REPORT.md
W20_AUDIT_REPORT.md
W20_WAVE_REPORT.md
W21_AUDIT_REPORT.md
W21_WAVE_REPORT.md
W22_AUDIT_REPORT.md
W22_WAVE_REPORT.md
W23_WAVE_REPORT.md
W24_AUDIT_REPORT.md
W24_WAVE_REPORT.md
W25_WAVE_REPORT.md
W26_WAVE_REPORT.md
W27_WAVE_REPORT.md
W28_WAVE_REPORT.md
W29_WAVE_REPORT.md
W30_WAVE_REPORT.md
W31_WAVE_REPORT.md
W32_WAVE_REPORT.md
W33_WAVE_REPORT.md
W34_WAVE_REPORT.md
W35_AUDIT_REPORT.md
W35_WAVE_REPORT.md
W36_WAVE_REPORT.md
W37_AUDIT_REPORT.md
W37_WAVE_REPORT.md
W38_AUDIT_REPORT.md
W38_WAVE_REPORT.md
W39_AUDIT_REPORT.md
W39_WAVE_REPORT.md
W40_AUDIT_REPORT.md
W40_WAVE_REPORT.md
W41_WAVE_REPORT.md
W42_WAVE_REPORT.md
W43_WAVE_REPORT.md
W44_WAVE_REPORT.md
W45_WAVE_REPORT.md
W46_WAVE_REPORT.md
W47_WAVE_REPORT.md
W48_WAVE_REPORT.md
W49_WAVE_REPORT.md
W50_WAVE_REPORT.md
W51_WAVE_REPORT.md
W52_WAVE_REPORT.md
---
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
 README.md                                       |   5 +-
 build/windows/hpc-client-gui.spec               |   6 +
 src/hpc_gui/config/storage.py                   | 104 ++++++
 src/hpc_gui/core/diagnostics.py                 |  21 +-
 src/hpc_gui/core/i18n.py                        |  74 +++-
 src/hpc_gui/core/ui_errors.py                   |   8 +-
 src/hpc_gui/core/wx_errors.py                   |   6 +
 src/hpc_gui/docs/HELP_en.md                     |   3 +-
 src/hpc_gui/docs/HELP_tr.md                     |   4 +-
 src/hpc_gui/docs/PLUGINS_en.md                  |  65 +++-
 src/hpc_gui/docs/PLUGINS_tr.md                  |  62 +++-
 src/hpc_gui/i18n/en.json                        |  15 +-
 src/hpc_gui/i18n/tr.json                        |  15 +-
 src/hpc_gui/plugins/installer.py                |   7 +
 src/hpc_gui/plugins/loader.py                   |   7 +
 src/hpc_gui/plugins/models.py                   |   5 +
 src/hpc_gui/plugins/validator.py                |  99 +++++-
 src/hpc_gui/services/command_history_store.py   |   6 +-
 src/hpc_gui/services/files_ssh.py               |  20 +-
 src/hpc_gui/services/geometry_policy.py         |  64 ++++
 src/hpc_gui/services/output_follower.py         |   5 +
 src/hpc_gui/services/shortcut_preferences.py    |  36 +-
 src/hpc_gui/services/slurm_models.py            |  81 +++++
 src/hpc_gui/ui/dialogs/plugin_manager_dialog.py |  17 +-
 src/hpc_gui/ui/models/remote_entry_helpers.py   |  79 +----
 src/hpc_gui/wx_editor_view.py                   | 306 ++++++++++++++++-
 src/hpc_gui/wx_jobs.py                          | 315 +++++++++++++++--
 src/hpc_gui/wx_local_files.py                   |   2 +-
 src/hpc_gui/wx_logs.py                          |  22 +-
 src/hpc_gui/wx_logs_view.py                     |  62 +++-
 src/hpc_gui/wx_plugins.py                       | 284 +++++++++++++++-
 src/hpc_gui/wx_plugins_view.py                  | 433 +++++++++++++++++++++---
 src/hpc_gui/wx_remote_files_view.py             |   2 +-
 src/hpc_gui/wx_settings.py                      | 338 +++++++++++++++++-
 src/hpc_gui/wx_settings_view.py                 |  32 +-
 src/hpc_gui/wx_shell.py                         | 409 ++++++++++++++++------
 src/hpc_gui/wx_updater_view.py                  |  57 ++++
 tests/test_remote_entry_helpers.py              |   8 +-
 38 files changed, 2736 insertions(+), 348 deletions(-)
---CHECK---
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
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls .tmp/w52-run/ 2>&1; echo "---REG---"; grep -n "HPC-W10-GJ2-00\|HPC-W10-GJ08-PATH-001\|PROFILE-ISOLATION-GJ-001" opencode/REQUIREMENT_REGISTRY.md | head -n 20; echo "---TODO---"; grep -n "PROFILE-ISOLATION-GJ" opencode/TODO_OWNERSHIP_MAP.md V2_TODOS.md opencode/sources/V2_TODOS.md 2>&1 | head -n 20
gj08_external.py
gj08_journey.py
---REG---
1029:| `HPC-W10-GJ2-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 135 | Workstream A0 — Integrated functional GUI Golden Journeys / GJ-07 — Offline/degraded mode | `W51` | — | local files/editor still function; |
1030:| `HPC-W10-GJ2-002` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 136 | Workstream A0 — Integrated functional GUI Golden Journeys / GJ-07 — Offline/degraded mode | `W51` | — | settings/logs/diagnostics remain reachable; |
1031:| `HPC-W10-GJ2-003` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 137 | Workstream A0 — Integrated functional GUI Golden Journeys / GJ-07 — Offline/degraded mode | `W51` | — | plugin manager truthfully reports offline/cache when applicable; |
1032:| `HPC-W10-GJ2-004` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 138 | Workstream A0 — Integrated functional GUI Golden Journeys / GJ-07 — Offline/degraded mode | `W51` | — | remote actions disable or fail visibly; |
1033:| `HPC-W10-GJ2-005` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 139 | Workstream A0 — Integrated functional GUI Golden Journeys / GJ-07 — Offline/degraded mode | `W51` | — | no repeated modal/error storm. |
1034:| `HPC-W10-GJ2-006` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 145 | Workstream A0 — Integrated functional GUI Golden Journeys / GJ-08 — Profile A → Profile B isolation | `W52` | — | terminal output/session; |
1035:| `HPC-W10-GJ2-007` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 146 | Workstream A0 — Integrated functional GUI Golden Journeys / GJ-08 — Profile A → Profile B isolation | `W52` | — | remote directory/file location; |
1036:| `HPC-W10-GJ2-008` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 147 | Workstream A0 — Integrated functional GUI Golden Journeys / GJ-08 — Profile A → Profile B isolation | `W52` | — | remote editor tab; |
1037:| `HPC-W10-GJ2-009` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 148 | Workstream A0 — Integrated functional GUI Golden Journeys / GJ-08 — Profile A → Profile B isolation | `W52` | — | jobs refresh/details/output. |
1299:| `HPC-W10-GJ08-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 141 | GJ-08 | `W52` | — | Execute GJ-08 as this explicit end-to-end path: with representative Profile A terminal/files/editor/jobs state active, switch/connect to Profile B and prove no A callback/result/action is applied to B. |
1533:| `HPC-W10-TODO-PROFILE-ISOLATION-GJ-001` | `PROFILE-ISOLATION-GJ-001` | `W52` | `PROFILE-ISOLATION-GJ-001` — GJ-08 proves Profile A state/callbacks cannot leak into Profile B. |
---TODO---
opencode/TODO_OWNERSHIP_MAP.md:201:| `HPC-W10-TODO-PROFILE-ISOLATION-GJ-001` | `W52` | `W10` | `PROFILE-ISOLATION-GJ-001` | ACTIVE | `PROFILE-ISOLATION-GJ-001` — GJ-08 proves Profile A state/callbacks cannot leak into Profile B. |
grep: V2_TODOS.md: No such file or directory
opencode/sources/V2_TODOS.md:380:- [ ] `PROFILE-ISOLATION-GJ-001` — GJ-08 proves Profile A state/callbacks cannot leak into Profile B.
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python .tmp/w52-run/gj08_journey.py 2>&1 | tail -n 30
CONN_GEN_MONOTONIC: OK � genA=1 genB=2
CONN_SESSION_DISTINCT: OK
CONN_STALE_A_NOT_CURRENT: OK � A generation must not equal B current
TERMINAL_STALE_A_DROPPED: OK � text=''
TERMINAL_B_LIVE_RENDERED: OK
TERMINAL_POST_CLOSE_DROPPED: OK
TERMINAL_WX_GUARD_PRESENT: OK � wx_terminal generation guard + swap mint
NAV_STORE_DISTINCT: OK
REMOTE_STALE_A_LISTING_DROPPED: OK � genA=1 genB=2
REMOTE_B_LISTING_APPLIED: OK � {'profile': 'w52-profile-beta', 'path': '/arf/scratch/w52-B'}
REMOTE_WX_GUARD_PRESENT: OK � wx_remote_files_view generation+request guard
EDITOR_KEYS_DISTINCT: OK � A=(False, 'local-real', 'w52-profile-alpha', 'gen-1', '/arf/scratch/w52-A/notes.txt') B=(False, 'local-real', 'w52-profile-beta', 'gen-2', '/arf/scratch/w52-A/notes.txt')
EDITOR_TABS_ISOLATED: OK � idxA=0 idxB=1 docs=2
EDITOR_B_TAB_PINNED: OK
EDITOR_A_TAB_UNTOUCHED: OK
JOBS_STALE_A_REFRESH_DROPPED: OK � seqA=1 seqB=2
JOBS_B_REFRESH_APPLIED: OK � [{'id': 'B-JOB-7'}]
JOBS_STALE_A_FAILURE_DROPPED: OK
JOBS_TRACKING_BOUND_TO_B: OK � session switch reconnects and clears A selection/output
JOBS_OUTPUT_REASSIGN_RESETS: OK � text='' job=B-JOB-7
GJ08_PATH_ISOLATION: OK � A state active then B connected; no A applied to B
GJ08_JOURNEY_RESULT: PASS (21/21)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_w19_connection_lifecycle.py tests/test_profile_identity.py tests/test_connection_profile_service.py -p no:cacheprovider -q 2>&1 | tail -n 10
...................................                                      [100%]
35 passed in 11.89s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_editor_controller.py tests/test_editor_flow.py tests/test_output_follower.py -p no:cacheprovider -q 2>&1 | tail -n 5; PYTHONPATH=src python -m pytest tests/test_wx_terminal.py tests/test_wx_terminal_behavioral.py -p no:cacheprovider -q 2>&1 | tail -n 5
......................                                                   [100%]
22 passed in 0.87s
.....................                                                    [100%]
21 passed in 18.06s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_wx_remote_files.py tests/test_remote_entry_helpers.py tests/test_wx_remote_editor_flow.py tests/test_local_edit_flow.py -p no:cacheprovider -q 2>&1 | tail -n 5; PYTHONPATH=src python -m pytest tests/test_wx_editor.py tests/test_wx_jobs.py tests/test_job_tracking_controller.py -p no:cacheprovider -q 2>&1 | tail -n 5; PYTHONPATH=src python -m pytest tests/test_w31_race_lifecycle.py tests/test_w33_lifecycle_isolation.py -p no:cacheprovider -q 2>&1 | tail -n 5
...............................                                          [100%]
31 passed in 5.96s
.....................                                                    [100%]
21 passed in 4.03s
....................................                                     [100%]
36 passed in 6.43s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git status --short docs/wave-reports/v2/opencode/W52_WAVE_REPORT.md; echo "---DIFFCHECK---"; git diff --check 2>&1 | head -n 5; echo "exit=$?"; echo "---HARNESS_HEAD---"; head -n 40 .tmp/w52-run/gj08_external.py
?? docs/wave-reports/v2/opencode/W52_WAVE_REPORT.md
---DIFFCHECK---
warning: in the working copy of 'src/hpc_gui/config/storage.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/diagnostics.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/i18n.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/wx_errors.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
exit=0
---HARNESS_HEAD---
"""W52 GJ-08 EXTERNAL replay: Profile A active -> switch/connect Profile B -> no A applied to B."""
import json, os, sys, tempfile, uuid
from pathlib import Path
sys.path.insert(0, "src")
tmp = Path(tempfile.mkdtemp(prefix="w52-gj08-"))
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
print("PROFILES: disposable-W52-A/B host=192.168.250.11 user=hpctest provider=local-real auth=key host_key_policy=accept-new")
kh = tmp / "known_hosts_w52"
lab_kh = Path(r"C:\Users\mskomek\AppData\Local\hpc-client-gui-lab\known_hosts")
if lab_kh.exists():
    kh.write_bytes(lab_kh.read_bytes())
print("HOST_KEY_PATH: isolated=" + str(kh) + " seeded=" + str(kh.exists()))
from hpc_gui.ssh.client import SSHConnInfo, SSHClientWrapper

def mk_wrapper():
    return SSHClientWrapper(SSHConnInfo(host="192.168.250.11", port=22, username="hpctest",
                           key_path=str(key_path), host_key_policy="accept-new",
                           known_hosts_path=str(kh), timeout=25))

# Profile A active: representative terminal/files/editor/jobs state
token_a = "W52-GJ08-A-" + uuid.uuid4().hex[:8]
wa = mk_wrapper()
wa.connect()
ta = wa.client.get_transport() if wa.client else None
assert ta is not None and ta.is_active(), "A connect transport not active"
print("PROFILE_A_CONNECTED: transport_active=True")
code_a, out_a, err_a = wa.run("echo " + token_a + "; hostname", timeout_s=25)
assert code_a == 0 and token_a in out_a, (code_a, err_a[:200])
print("PROFILE_A_TERMINAL: OK token readback")
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ timeout 90 python .tmp/w52-run/gj08_external.py 2>&1 | tail -n 25; echo "EXIT=$?"
CONFIG_ROOT_ISOLATED: D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\w52-gj08-2ocr8fb2\fresh-root
PROFILES: disposable-W52-A/B host=192.168.250.11 user=hpctest provider=local-real auth=key host_key_policy=accept-new
HOST_KEY_PATH: isolated=D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\w52-gj08-2ocr8fb2\known_hosts_w52 seeded=True
PROFILE_A_CONNECTED: transport_active=True
PROFILE_A_TERMINAL: OK token readback
PROFILE_A_FILES: exit=0 out=/home/hpctest|slurm-10.out|slurm-14.out|slurm-16.out|slurm-18.out|slurm-2.out
PROFILE_A_JOBS: JOBID PARTITION     NAME     USER ST       TIME  NODES NODELIST(REASON)|W52-A-JOBS-EXIT:0
PROFILE_B_CONNECTED: transport_active=True distinct_transport=True
PROFILE_B_TERMINAL_ISOLATED: OK (B token present, A token absent)
PROFILE_B_FILES: OK exit=0
PROFILE_B_JOBS: JOBID PARTITION     NAME     USER ST       TIME  NODES NODELIST(REASON)|W52-B-JOBS-EXIT:0
STALE_A_GATED: closed-A exec raised RuntimeError
PROFILE_B_STILL_ALIVE: OK (B unaffected by A close)
DISCONNECT_BOTH: OK
GJ08_EXTERNAL_RESULT: PASS
EXIT=0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
AC_WAVE_BRIDGE_STDOUT_BEGIN
Auditing wave W52 — loading the canonical criteria.
Spec is clear. Now I'm gathering the independent evidence for W52.
Core checks are green — now verifying the remaining audit dimensions.
W52 fresh independent audit — PASS.

Authority: `waves/pending/W52.md` (execution, 5 source IDs + 1 TODO, start gate NONE, evidence GUI/PACKAGE/EXTERNAL), registry rows 1034–1037/1299/1533, TODO map line 201, GJ-08 source semantics, live code read-only.

Candidate: HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369`, handoff content identity `bc8e0c25…` (matches W45–W51 baselines). W52 authored zero product/test edits (read-only candidate rule honored); only untracked `W52_WAVE_REPORT.md` (allowed closeout-only path) plus `.tmp/w52-run/` harnesses. `git diff --check` exit 0. Sibling dirty tree preserved untouched with correct re-run disclaimer.

Independent reruns at current HEAD (auditor-executed, not report-quoted):
- `.tmp/w52-run/gj08_journey.py` → `GJ08_JOURNEY_RESULT: PASS (21/21)` — all CONN/TERMINAL/REMOTE/EDITOR/JOBS/PATH checks OK via real product paths under disposable roots.
- GUI slices process-isolated, `PYTHONPATH=src -p no:cacheprovider`: editor trio 22 passed; w19+profile+connection-profile 35 passed (20+12+3); terminal 21 passed (2+19); remote group 31 passed (4+12+7+8); editor/jobs group 21 passed (14+5+2); race/lifecycle 36 passed (14+22). Total 166 passed, 0 failed — matches EV-W52-GUI claim exactly.
- `.tmp/w52-run/gj08_external.py` (90s bound) → `GJ08_EXTERNAL_RESULT: PASS` against LOCAL_REAL_HYPERV 192.168.250.11 hpctest: A connected/terminal/files/squeue OK, B connected distinct transport, B terminal isolated (B token present, A absent), stale-A exec raised RuntimeError (visible gating), B unaffected by A close, both disconnected, disposable tokens only.

Requirement coverage verified: 006 terminal, 007 remote location, 008 editor tab, 009 jobs, PATH-001 end-to-end, TODO-PROFILE-ISOLATION-GJ-001 — all IMPLEMENT with journey+slice+external evidence, no mocks substituted for owned claims. PACKAGE NO-CANDIDATE honestly recorded (freeze owned W56–W61), no artifact SHA claimed, no freeze invalidation. `test_file_manager_profile` CWD failures honestly excluded, not claimed green. No weakened tests, no secrets, no cross-scope fixes, no user prompts.

No owned blocking defect. No repair performed (audit read-only).

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
