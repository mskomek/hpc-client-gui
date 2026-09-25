# Wave W46 Audit Report
## Controller-persisted fresh independent audit — 2026-09-24T21:49:24.479065+00:00

- Wave: `W46`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0058-W46-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0058-W46-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
✱ Glob "waves/**/W46*" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves 
✱ Glob "**/W46*" 1 match
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending 
→ Read waves/done 
→ Read waves/waves 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W46.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W46_WAVE_REPORT.md 
✱ Grep "HPC-W10-GJ02-PATH-001" in . · 4 matches
$ git rev-parse HEAD; git status --short --branch; git log --oneline -5
c8293d3ca309526ed250c794c3b294f7c54ef369
## develop
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
c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Get-Content 'opencode/sources/WAVE_V2_FINAL_10.md' | Select-Object -First 120 | Select-Object -Last 70; Write-Output '---TMP---'; Get-ChildItem .tmp/w46-run/ -ErrorAction Continue | Format-Table Name,Length; Write-Output '---AUDIT-REPORT-EXISTS---'; Test-Path docs/wave-reports/v2/opencode/W46_AUDIT_REPORT.md"
W10 owns integrated replay of `GJ-01` through `GJ-10` from the Index.

At minimum execute these end-to-end journeys on the candidate code and then the packaged candidate:

### GJ-01 �?" Fresh user to connected state

```text
clean config
�+' launch
�+' logs/settings initialize
�+' create profile
�+' select provider/auth
�+' host-key path
�+' connect
�+' status says connected
�+' remote-dependent tabs/actions bind to the same session
```

### GJ-02 �?" Connection + terminal lifecycle

```text
connect
�+' terminal ready
�+' command/output
�+' disconnect
�+' remote controls truthfully disabled/stale
�+' reconnect
�+' terminal operates on new session only
```

### GJ-03 �?" Files/directories/editor round trip

```text
local file
�+' upload to selected storage area
�+' verify remote bytes
�+' open remote in editor
�+' edit/save
�+' verify remote bytes
�+' download
�+' verify local bytes
```

Include overwrite-cancel and one failure path.

### GJ-04 �?" Job + output lifecycle

```text
submit
�+' job ID
�+' list/details
�+' running/final state
�+' stdout/stderr
�+' live refresh/tail where exposed
�+' completion
```

Also execute cancel on a disposable job.

### GJ-05 �?" Plugin Manager/provider journey

```text
open Plugin Manager
�+' browse/search or offline/cache state
�+' manage installed
�+' install/update/remove/enable-disable safe fixture
�+' provider registration/state reflects result
```

### GJ-06 �?" Settings/logs/diagnostics/restart
---TMP---

Name              Length
----              ------
gj02_lifecycle.py   3900


---AUDIT-REPORT-EXISTS---
False
$ powershell -NoProfile -Command "Select-String -Path 'opencode/REQUIREMENT_REGISTRY.md' -Pattern 'HPC-W10-GJ02-PATH-001' -Context 0,5; Write-Output '---TODO---'; Select-String -Path 'opencode/TODO_OWNERSHIP_MAP.md' -Pattern 'W46' | Select-Object -First 20; Write-Output '---LAB---'; Get-Content '.opencode/protocol/LOCAL_REAL_HPC_LAB.md' | Select-Object -First 80"
> opencode\REQUIREMENT_REGISTRY.md:1293:| `HPC-W10-GJ02-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 
69 | GJ-02 | `W46` | - | Execute GJ-02 as this explicit end-to-end path: connect  terminal ready  command/output  
disconnect  remote controls truthfully disabled/stale  reconnect  terminal operates on the new session only. |
  opencode\REQUIREMENT_REGISTRY.md:1294:| `HPC-W10-GJ03-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 
81 | GJ-03 | `W47` | - | Execute GJ-03 as this explicit end-to-end path: local file  upload to selected storage area 
 verify remote bytes  open remote in editor  edit/save  verify remote bytes  download  verify local bytes. |
  opencode\REQUIREMENT_REGISTRY.md:1295:| `HPC-W10-GJ04-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 
96 | GJ-04 | `W48` | - | Execute GJ-04 as this explicit end-to-end path: submit  job ID  list/details  
running/final state  stdout/stderr  live refresh/tail where exposed  completion. |
  opencode\REQUIREMENT_REGISTRY.md:1296:| `HPC-W10-GJ05-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 
110 | GJ-05 | `W49` | - | Execute GJ-05 as this explicit end-to-end path: open Plugin Manager  browse/search or 
offline/cache state  manage installed  install/update/remove/enable-disable safe fixture  provider 
registration/state reflects result. |
  opencode\REQUIREMENT_REGISTRY.md:1297:| `HPC-W10-GJ06-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 
120 | GJ-06 | `W50` | - | Execute GJ-06 as this explicit end-to-end path: change representative settings  verify 
runtime effect  open logs/diagnostics  close  restart  verify expected persistence. |
  opencode\REQUIREMENT_REGISTRY.md:1298:| `HPC-W10-GJ07-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 
131 | GJ-07 | `W51` | - | Execute GJ-07 as this explicit end-to-end path: offline/degraded mode preserves local 
files/editor and settings/logs/diagnostics, reports plugin offline/cache truthfully, gates remote actions visibly, and 
avoids repeated modal/error storms. |
---TODO---
---LAB---
# LOCAL_REAL HPC Lab Protocol


This protocol applies to the HPC W01-W61 program only.


## Purpose


Use the maintainer-owned LOCAL_REAL Hyper-V cluster as the default real
authorized infrastructure for HPC Wave requirements that require generic real
SSH/SFTP/Slurm/filesystem/job/connection evidence and do not explicitly require
a named production/site-specific system.


`LOCAL_REAL_HYPERV` is real external infrastructure for acceptance purposes. It is not:
- a mock server;
- a fake scheduler;
- a substitute identity for TRUBA;
- evidence for a site-specific requirement that explicitly names another system.


## Canonical target


- profile: `C:\Users\mskomek\AppData\Local\hpc-client-gui-lab\hpc-client-profile.json`
- controller/login: `192.168.250.11:22`
- user: `hpctest`
- compute nodes: `compute01`, `compute02`
- infrastructure class: `LOCAL_REAL_HYPERV`
- provider/profile ID: `local-real`
- scheduler: real Slurm
- shared storage: real NFS-backed Home/Scratch/Project
- auth: generated SSH key from the emitted profile
- host-key policy: isolated lab known_hosts with `accept-new`; later key changes fail

## Capability-scoped password target

`LOCAL_REAL_HYPERV` is intentionally key-only (`ssh_pwauth: false`) and is
authoritative only for the capabilities it actually provisions. It must not
be used as password-auth evidence.

For generic password-auth requirements, the maintained secondary target is
`LOCAL_PASSWORD_REAL`: the disposable OpenSSH/Slurm fixture defined by
`docs/testing/LOCAL_HPC_LAB.md` and `devtools/lab/docker-compose.yml`. It is
bound to `127.0.0.1` only, uses a real containerized OpenSSH/Slurm runtime
(not an in-process mock), and uses documented throwaway fixture input supplied
through stdin or an equivalent secure input channel. It is authoritative only
for generic password success/failure and invalid-password rejection. It does
not replace `LOCAL_REAL_HYPERV` for key, host-key, Slurm, SFTP, storage, or
site-specific claims. Its password must never appear in logs, reports,
manifests, or evidence.


## Verified baseline


Current accepted LOCAL_REAL baseline:
- `lab-up.ps1`: PASS
- `lab-status.ps1`: PASS
- image pin: PASS
- generated profile validation: PASS
- `lab-test.ps1`: `LOCAL_REAL_READY`
- behavioral gates: 23/23 PASS
- real PTY evidence: `/dev/pts/0`
- controller and both compute transports/services: PASS
- compute nodes: Slurm `idle`
- real SSH key login: PASS
- host-key pins: PASS
- real SFTP download/upload/hash: PASS
- MUNGE: PASS
- two-node `srun`: PASS
- `sinfo/squeue/scontrol/sbatch/sacct/scancel`: PASS
- shared-home compute execution: PASS
- permission-denied negative path: PASS


Repository context:
- `lab/LAB_AUDIT_REPORT.md`
- `lab/README.md`
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Get-Content .tmp/w46-run/gj02_lifecycle.py"
"""W46 GJ-02 EXTERNAL replay: connect -> terminal ready -> command/output -> disconnect -> stale gating -> reconnect -> new session only."""
import json, os, sys, tempfile, uuid
from pathlib import Path
sys.path.insert(0, "src")
tmp = Path(tempfile.mkdtemp(prefix="w46-gj02-"))
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
print("PROFILE: disposable-W46-copy host=192.168.250.11 user=hpctest provider=local-real auth=key host_key_policy=accept-new")
kh = tmp / "known_hosts_w46"
lab_kh = Path(r"C:\Users\mskomek\AppData\Local\hpc-client-gui-lab\known_hosts")
if lab_kh.exists():
    kh.write_bytes(lab_kh.read_bytes())
print("HOST_KEY_PATH: isolated=" + str(kh) + " seeded=" + str(kh.exists()))
from hpc_gui.ssh.client import SSHConnInfo, SSHClientWrapper

def mk_wrapper():
    return SSHClientWrapper(SSHConnInfo(host="192.168.250.11", port=22, username="hpctest",
                           key_path=str(key_path), host_key_policy="accept-new",
                           known_hosts_path=str(kh), timeout=25))

# 1 connect
token1 = "W46-GJ02-A-" + uuid.uuid4().hex[:8]
w1 = mk_wrapper()
w1.connect()
t1 = w1.client.get_transport() if w1.client else None
active1 = t1 is not None and t1.is_active()
print("CONNECT_1: transport_active=" + str(active1))
assert active1, "first connect transport not active"

# 2 terminal ready + command/output (exec channel on live session)
code, out, err = w1.run("echo " + token1 + "; hostname", timeout_s=25)
print("EXEC_1_EXIT: " + str(code))
print("EXEC_1_OUT: " + out.strip()[:200])
assert code == 0, (code, err[:200])
assert token1 in out, "first session token missing"
assert "login-control01" in out or "login" in out, "hostname readback missing"
print("TERMINAL_READY_1: OK (live session exec readback)")

# 3 disconnect
w1.close()
t1b = w1.client.get_transport() if getattr(w1, "client", None) else None
active_after = (t1b is not None and t1b.is_active()) if t1b is not None else False
print("DISCONNECT_1: closed old_transport_active=" + str(active_after))
assert not active_after, "old transport still active after close"

# 4 stale gating: exec on closed session must fail visibly, not silently succeed
try:
    code_s, out_s, err_s = w1.run("echo STALE-PROBE", timeout_s=10)
    print("STALE_EXEC: unexpectedly returned code=" + str(code_s))
    raise SystemExit("STALE gating FAILED: closed session exec succeeded")
except SystemExit:
    raise
except Exception as ex:
    print("STALE_GATED: closed-session exec raised " + ex.__class__.__name__)

# 5 reconnect -> new session only
token2 = "W46-GJ02-B-" + uuid.uuid4().hex[:8]
w2 = mk_wrapper()
w2.connect()
t2 = w2.client.get_transport() if w2.client else None
active2 = t2 is not None and t2.is_active()
print("RECONNECT_2: transport_active=" + str(active2))
assert active2, "reconnect transport not active"
assert token2 != token1
code2, out2, err2 = w2.run("echo " + token2 + "; hostname", timeout_s=25)
print("EXEC_2_EXIT: " + str(code2))
print("EXEC_2_OUT: " + out2.strip()[:200])
assert code2 == 0, (code2, err2[:200])
assert token2 in out2, "second session token missing"
assert token1 not in out2, "old session output leaked into new session"
print("NEW_SESSION_ONLY: OK (fresh token echoed, old token absent)")
w2.close()
print("DISCONNECT_2: OK")
print("GJ02_EXTERNAL_RESULT: PASS")
$ $env:PYTHONPATH="src"; python -m pytest tests/test_w19_connection_lifecycle.py tests/test_wx_terminal.py tests/test_wx_embedded_terminal.py tests/test_wx_terminal_behavioral.py tests/test_wx_terminal_parity_evidence.py -p no:cacheprovider -q 2>&1 | Select-Object -Last 15
/usr/bin/bash: line 1: :PYTHONPATH=src: command not found
/usr/bin/bash: line 1: Select-Object: command not found
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_w19_connection_lifecycle.py tests/test_wx_terminal.py tests/test_wx_embedded_terminal.py tests/test_wx_terminal_behavioral.py tests/test_wx_terminal_parity_evidence.py -p no:cacheprovider -q 2>&1 | tail -15
..............................................................           [100%]
62 passed in 46.86s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_wx_shell_p0.py tests/test_wx_connection.py -p no:cacheprovider -q 2>&1 | tail -8
PYTHONPATH=src python -m pytest tests/test_w19_connection_lifecycle.py -p no:cacheprovider -q -k "reconnect or disconnect or stale or rebind or profile_switch or transport_loss or detach or fresh_session or supersedes" 2>&1 | tail -8
.....................                                                    [100%]
21 passed in 42.84s
.........                                                                [100%]
9 passed, 11 deselected in 3.33s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff --check 2>&1 | tail -5; echo "---DIFF-STAT---"; git diff --stat 2>&1 | tail -8; echo "---OWNERS---"; ls src/hpc_gui/ssh/client.py src/hpc_gui/ssh/shell_session.py src/hpc_gui/wx_shell.py 2>&1
warning: in the working copy of 'src/hpc_gui/services/shortcut_preferences.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_logs.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_updater_view.py', LF will be replaced by CRLF the next time Git touches it
---DIFF-STAT---
 src/hpc_gui/wx_plugins_view.py                  | 433 +++++++++++++++++++++---
 src/hpc_gui/wx_remote_files_view.py             |   2 +-
 src/hpc_gui/wx_settings.py                      | 338 +++++++++++++++++-
 src/hpc_gui/wx_settings_view.py                 |  32 +-
 src/hpc_gui/wx_shell.py                         | 409 ++++++++++++++++------
 src/hpc_gui/wx_updater_view.py                  |  57 ++++
 tests/test_remote_entry_helpers.py              |   8 +-
 38 files changed, 2736 insertions(+), 348 deletions(-)
---OWNERS---
src/hpc_gui/ssh/client.py
src/hpc_gui/ssh/shell_session.py
src/hpc_gui/wx_shell.py
$ ls "C:/Users/mskomek/AppData/Local/hpc-client-gui-lab/hpc-client-profile.json" 2>&1; timeout 90 python .tmp/w46-run/gj02_lifecycle.py 2>&1 | tail -25
C:/Users/mskomek/AppData/Local/hpc-client-gui-lab/hpc-client-profile.json
CONFIG_ROOT_ISOLATED: D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\w46-gj02-0ii292fo\fresh-root
PROFILE: disposable-W46-copy host=192.168.250.11 user=hpctest provider=local-real auth=key host_key_policy=accept-new
HOST_KEY_PATH: isolated=D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\w46-gj02-0ii292fo\known_hosts_w46 seeded=True
CONNECT_1: transport_active=True
EXEC_1_EXIT: 0
EXEC_1_OUT: W46-GJ02-A-9e1e7001
login-control01
TERMINAL_READY_1: OK (live session exec readback)
DISCONNECT_1: closed old_transport_active=False
STALE_GATED: closed-session exec raised RuntimeError
RECONNECT_2: transport_active=True
EXEC_2_EXIT: 0
EXEC_2_OUT: W46-GJ02-B-302ae739
login-control01
NEW_SESSION_ONLY: OK (fresh token echoed, old token absent)
DISCONNECT_2: OK
GJ02_EXTERNAL_RESULT: PASS
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
AC_WAVE_BRIDGE_STDOUT_BEGIN
Auditing W46 — loading the canonical audit skill and wave scope.
W46's journey report is in hand — now verifying its evidence against repository truth.
GUI slices check out at 83 green — now confirming the terminal lifecycle end-to-end.
## W46 Audit — fresh independent (HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369`)

**Owned requirement:** `HPC-W10-GJ02-PATH-001` (MANDATORY, GJ-02: connect → terminal ready → command/output → disconnect → stale-gated → reconnect → new-session-only). Registry row verified; TODO map has no W46 rows; mandatory source `WAVE_V2_FINAL_10.md` GJ-02 section verified; live owners `src/hpc_gui/ssh/client.py`, `src/hpc_gui/ssh/shell_session.py`, `src/hpc_gui/wx_shell.py` present.

**Candidate bound:** `c8293d3ca309526ed250c794c3b294f7c54ef369` (branch `develop`), matching report baseline. `waves/` gitignored identity reconciliation is controller-owned; no stale PASS reused — all evidence below was freshly rerun by this auditor at current HEAD/dirty-tree truth.

**EV-W46-GUI — RERUN PASS (83/83):**
- `test_w19_connection_lifecycle + test_wx_terminal + test_wx_embedded_terminal + test_wx_terminal_behavioral + test_wx_terminal_parity_evidence` → **62 passed**
- `test_wx_shell_p0 + test_wx_connection` → **21 passed**
- Focused lifecycle `-k "reconnect or disconnect or stale or rebind or profile_switch or transport_loss or detach or fresh_session or supersedes"` → **9 passed** (subset)
- Covers: supersede/cancel-safe connect, stale-callback isolation, matching-callback fail+invalidate, fresh-session mint, disconnect gating/rebind+generation, detach, GUI-thread marshal, host-key prompt, transport-loss indicator, terminal parity.

**EV-W46-EXT — RERUN PASS verbatim** (`.tmp/w46-run/gj02_lifecycle.py`, LOCAL_REAL_HYPERV `192.168.250.11:22` `hpctest` key auth, isolated config root + known_hosts):
- `CONNECT_1: transport_active=True`, `EXEC_1_EXIT: 0` token `W46-GJ02-A-*` + `login-control01`
- `TERMINAL_READY_1: OK`, `DISCONNECT_1: old_transport_active=False`
- `STALE_GATED: RuntimeError` (truthful visible failure)
- `RECONNECT_2: transport_active=True`, `EXEC_2` token `W46-GJ02-B-*` + hostname, old token absent → `NEW_SESSION_ONLY: OK`, `DISCONNECT_2: OK`, `GJ02_EXTERNAL_RESULT: PASS`. Both sessions closed; no writes/jobs.

**EV-W46-PKG — NO-CANDIDATE accepted with justification:** no artifact built/published/claimed; freeze owned downstream (W56–W61); zero product edits by W46 so no invalidation. GJ-02 path requires no packaging; honest N/A per evidence policy.

**EV-W46-DIFF:** `git diff --check` exit 0 (only pre-existing sibling CRLF warnings). 38 tracked M files are pre-existing sibling-wave changes (including `wx_shell.py`), preserved untouched; W46 added zero product/test hunks — only untracked allowed-closeout report `W46_WAVE_REPORT.md` (no `W46_AUDIT_REPORT.md` yet; controller owns persistence). No secrets, no weakened tests, no generated/binary noise.

**Findings:** no W46-owned product defect. OBS-W46-002 (lab Slurm `compute01 down`, transport/services healthy) is infra state out of GJ-02 scope, truthfully recorded, not a product route. No `AWAITING_INPUT`, no `EXTERNAL_BLOCKED`, no cross-scope route. Golden-Journey candidate rule honored (read-only).

**Verdict: PASS** — GJ-02 executes end-to-end on the current candidate; close W46 independently (W55 hint non-blocking).

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
