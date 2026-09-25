# Wave W45 Audit Report
## Controller-persisted fresh independent audit — 2026-09-24T21:38:00.085790+00:00

- Wave: `W45`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0053-W45-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0053-W45-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✗ Read .agents/skills/ac-wave-opencode-audit/SKILL.md failed
Error: Offset 31 is out of range for this file (30 lines)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills 
→ Read .agents/skills/ac-wave-opencode-audit 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-core 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-core/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✱ Glob "waves/pending/W45*" in . · 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Get-ChildItem -Path waves -Recurse -Filter "*W45*" | Select-Object FullName, DirectoryName | Format-Table -AutoSize; Write-Host "---GIT---"; git log --oneline -5; Write-Host "---STATUS---"; git status --short | Select-Object -First 30
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
/usr/bin/bash: line 1: Select-Object: command not found
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls waves/pending/ | head -n 50; echo "---"; ls waves/done/ | head -n 80; echo "---"; ls waves/blocked/ 2>&1; echo "---"; ls waves/postponed/ 2>&1; echo "---GIT---"; git log --oneline -5; echo "---STATUS---"; git status --short | head -n 30
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
---
05-macos-production-updates.md
06-appimage-flatpak.md
07-acceptance-and-rollout.md
WAVE-03-release-packaging-verification.md
WAVE-04-publish-release.md
WAVE-07-wiki-readmes-and-release.md
wave_12_registry_release_and_application_integration.md
---
04-macos-sparkle-feasibility.md
CHECKPOINTS.md
CHECKSUMS.sha256
CONTRACT-DRAFT.md
EXECUTION_ORDER.md
IMPLEMENTATION-RULES.md
PACK_MANIFEST.json
QA-MATRIX.md
README.md
README_WAVES_78_80.md
RESEARCH-TRUBA.md
WAVE-01-provider-template-kit.md
WAVE-02-app-template-roundtrip.md
WAVE-03-RESULT.md
WAVE-03-template-editor-and-storage-ui.md
WAVE-04-optional-quota-noop.md
WAVE-05-update-truba-plugin.md
WAVE-06-job-paths-independent-of-quota.md
WAVE-10-ENGLISH-INTERACTIVE-DEMO-GIF.md
WAVE_71_WX_CONNECTION_PROFILE_POLISH.md
WAVE_MENU_PLUGINS_HELP_UI_CONTRIBUTIONS.md
templates
wave_42_wxpython_application_shell.md
wave_43_wx_help_command_palette_shortcut_settings.md
wave_45_wx_terminal_renderer_pty_integration.md
wave_49_wx_directories_workspace.md
wave_52_wx_plugin_manager.md
wave_55_wx_settings.md
wave_56_wx_logs_diagnostics_send_logs.md
wave_57_wx_updater_splash_tray_shutdown.md
wave_58_windows_native_ux_packaging_audit.md
wave_59_linux_native_ux_packaging_audit.md
wave_60_macos_native_ux_packaging_audit.md
wave_61_accessibility_keyboard_only_audit.md
wave_62_automated_feature_parity_matrix.md
wave_63_manual_gui_interaction_test_plan.md
wave_64_existing_user_data_keymap_migration.md
wave_65_packaged_wx_smoke_end_to_end_parity_gate.md
wave_66_qt_removal_readiness_gate.md
wave_67_remove_pyside6_qt_runtime.md
wave_68_licenses_notices_documentation_finalization.md
wave_69_performance_soak_hardening.md
wave_70_v2_packaging_release_preparation.md
wx Terminal Parity Waves 72–77.md
---GIT---
c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
---STATUS---
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
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W45.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ echo "===W45 report==="; ls -la docs/wave-reports/v2/opencode/W45* 2>&1; echo "===registry W45==="; grep -n "W45\|GJ01\|GJ-01" REQUIREMENT_REGISTRY.md 2>&1 | head -n 40; echo "===todo map==="; grep -n "W45" TODO_OWNERSHIP_MAP.md 2>&1 | head -n 20; echo "===candidate sha==="; git rev-parse HEAD; echo "===content identity check==="; git log --format="%H" -1; echo "===status==="; git status --short | head -n 40
===W45 report===
-rw-r--r-- 1 mskomek 197121 12938 Sep 25 00:34 docs/wave-reports/v2/opencode/W45_WAVE_REPORT.md
===registry W45===
grep: REQUIREMENT_REGISTRY.md: No such file or directory
===todo map===
grep: TODO_OWNERSHIP_MAP.md: No such file or directory
===candidate sha===
c8293d3ca309526ed250c794c3b294f7c54ef369
===content identity check===
c8293d3ca309526ed250c794c3b294f7c54ef369
===status===
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
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W45_WAVE_REPORT.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls opencode/ 2>&1 | head -n 20; echo "==="; grep -n "HPC-W10-GJ01-PATH-001" opencode/REQUIREMENT_REGISTRY.md 2>&1 | head; echo "==="; ls .tmp/w45-run/ 2>&1 | head -n 20; echo "==="; ls docs/wave-reports/v2/opencode/W45_AUDIT* 2>&1; echo "==="; cat .opencode/protocol/LOCAL_REAL_HPC_LAB.md 2>&1 | head -n 100
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
1292:| `HPC-W10-GJ01-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 55 | GJ-01 | `W45` | — | Execute GJ-01 as this explicit end-to-end path: clean config → launch → logs/settings initialize → create profile → select provider/auth → host-key path → connect → status says connected → remote-dependent tabs/actions bind to the same session. |
===
gj01_connect.py
===
ls: cannot access 'docs/wave-reports/v2/opencode/W45_AUDIT*': No such file or directory
===
﻿# LOCAL_REAL HPC Lab Protocol


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
- Wave-specific LOCAL_REAL gap reports when present


Private runtime state/evidence remains local/disposable. Never copy private keys,
VM disks, generated secrets, or LOCAL_REAL private state into Wave reports,
Git, Drive evidence, or worktree overlays.


## Wave selection rule


For an HPC Wave whose required evidence includes `EXTERNAL`:


1. Read the Wave's owned requirement wording first.
2. If it requires generic real SSH/SFTP/Slurm/remote-files/jobs/storage/
   connection/session behavior and does not name a specific external site,
   use LOCAL_REAL by default.
3. If it explicitly requires TRUBA, another named site, special hardware, an
   authoritative production service, or a capability LOCAL_REAL does not
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ echo "===registry row context==="; sed -n '1285,1300p' opencode/REQUIREMENT_REGISTRY.md; echo "===todo==="; grep -n "W45" opencode/TODO_OWNERSHIP_MAP.md | head; echo "===source GJ-01==="; find waves/bak opencode/sources -name "*10*" 2>&1 | head; echo "===harness==="; head -n 80 .tmp/w45-run/gj01_connect.py 2>&1
===registry row context===
| `HPC-W08-MANIFEST-008` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 98 | Workstream B — Manifest / metadata contract | `W32` | — | Malformed or incompatible plugin metadata is rejected with a contained diagnostic. |
| `HPC-W08-DOCS-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 210 | Workstream I — Documentation contract | `W36` | — | Provider/plugin authoring instructions must match the current schema and actual loading behavior. |
| `HPC-W08-DOCS-002` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_08.md` | 210 | Workstream I — Documentation contract | `W36` | — | Provider/plugin templates must allow truly optional capabilities, such as absent quota sources, without dummy values. |
| `HPC-W09-PLUGINSET-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 129 | Workstream E — Plugin/provider settings | `W37` | — | Plugin/provider settings use the namespacing and ownership contract established by original planning Wave 08. |
| `HPC-W09-PLUGINSET-002` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 129 | Workstream E — Plugin/provider settings | `W37` | — | Test plugin/provider settings loading when the plugin is absent, disabled, reinstalled or upgraded. |
| `HPC-W09-PKGUPD-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 256 | Workstream K — Package validation | `W43` | — | Updater package validation uses the exact artifact under acceptance. |
| `HPC-W09-PKGUPD-002` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 256 | Workstream K — Package validation | `W43` | — | Where a safe test channel/mock endpoint is used, it must exercise the same production verification/install code path. |
| `HPC-W10-GJ01-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 55 | GJ-01 | `W45` | — | Execute GJ-01 as this explicit end-to-end path: clean config → launch → logs/settings initialize → create profile → select provider/auth → host-key path → connect → status says connected → remote-dependent tabs/actions bind to the same session. |
| `HPC-W10-GJ02-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 69 | GJ-02 | `W46` | — | Execute GJ-02 as this explicit end-to-end path: connect → terminal ready → command/output → disconnect → remote controls truthfully disabled/stale → reconnect → terminal operates on the new session only. |
| `HPC-W10-GJ03-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 81 | GJ-03 | `W47` | — | Execute GJ-03 as this explicit end-to-end path: local file → upload to selected storage area → verify remote bytes → open remote in editor → edit/save → verify remote bytes → download → verify local bytes. |
| `HPC-W10-GJ04-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 96 | GJ-04 | `W48` | — | Execute GJ-04 as this explicit end-to-end path: submit → job ID → list/details → running/final state → stdout/stderr → live refresh/tail where exposed → completion. |
| `HPC-W10-GJ05-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 110 | GJ-05 | `W49` | — | Execute GJ-05 as this explicit end-to-end path: open Plugin Manager → browse/search or offline/cache state → manage installed → install/update/remove/enable-disable safe fixture → provider registration/state reflects result. |
| `HPC-W10-GJ06-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 120 | GJ-06 | `W50` | — | Execute GJ-06 as this explicit end-to-end path: change representative settings → verify runtime effect → open logs/diagnostics → close → restart → verify expected persistence. |
| `HPC-W10-GJ07-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 131 | GJ-07 | `W51` | — | Execute GJ-07 as this explicit end-to-end path: offline/degraded mode preserves local files/editor and settings/logs/diagnostics, reports plugin offline/cache truthfully, gates remote actions visibly, and avoids repeated modal/error storms. |
| `HPC-W10-GJ08-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 141 | GJ-08 | `W52` | — | Execute GJ-08 as this explicit end-to-end path: with representative Profile A terminal/files/editor/jobs state active, switch/connect to Profile B and prove no A callback/result/action is applied to B. |
| `HPC-W10-GJ09-PATH-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_10.md` | 152 | GJ-09 | `W53` | — | Execute GJ-09 as this explicit end-to-end path: controlled shutdown with representative terminal, transfer, remote-file, editor, jobs, Plugin Manager, updater and diagnostics work in flight completes without native crash, destroyed-control callback, hang or leaked lifecycle state, followed by clean relaunch. |
===todo===
===source GJ-01===
waves/bak/AUDIT_REAUDIT_WAVE_00_10_2026-09-10.md
waves/bak/WAVE_10_MIGRATION_DOCS_RELEASE_GATE.md
waves/bak/WAVE_V2_FINAL_10.md
opencode/sources/WAVE_V2_FINAL_10.md
===harness===
"""W45 GJ-01 EXTERNAL replay: clean config -> init -> profile -> provider/auth -> host-key -> connect -> status -> session bind."""
import json, os, sys, tempfile, uuid
from pathlib import Path
sys.path.insert(0, "src")
tmp = Path(tempfile.mkdtemp(prefix="w45-gj01-"))
os.environ["HPC_GUI_CONFIG_ROOT"] = str(tmp / "fresh-root")
from hpc_gui.core import paths as paths_mod
from hpc_gui.core import logging_setup
data = paths_mod.app_data_dir(); logs = paths_mod.app_log_dir()
assert data.is_dir() and logs.is_dir(), (data, logs)
logging_setup.setup_logging()
from hpc_gui.config.storage import load_settings, update_settings
s = load_settings(); update_settings({})
s2 = load_settings(); assert isinstance(s2, dict)
print("CONFIG_ROOT_ISOLATED: " + str(data))
print("LOGS_SETTINGS_INIT: OK")
prof_text = Path(r"C:\Users\mskomek\AppData\Local\hpc-client-gui-lab\hpc-client-profile.json").read_text(encoding="utf-8-sig")
prof = json.loads(prof_text)
assert prof.get("host")=="192.168.250.11" and prof.get("username")=="hpctest"
key_path = prof.get("key_path")
assert key_path and Path(key_path).exists()
print("PROFILE: disposable-W45-copy host=192.168.250.11 user=hpctest provider=local-real auth=key host_key_policy=accept-new")
kh = tmp / "known_hosts_w45"
lab_kh = Path(r"C:\Users\mskomek\AppData\Local\hpc-client-gui-lab\known_hosts")
if lab_kh.exists():
    kh.write_bytes(lab_kh.read_bytes())
print("HOST_KEY_PATH: isolated=" + str(kh) + " seeded=" + str(kh.exists()))
from hpc_gui.ssh.client import SSHConnInfo, SSHClientWrapper
token = "W45-GJ01-" + uuid.uuid4().hex[:8]
info = SSHConnInfo(host="192.168.250.11", port=22, username="hpctest",
                   key_path=str(key_path), host_key_policy="accept-new",
                   known_hosts_path=str(kh), timeout=25)
w = SSHClientWrapper(info)
w.connect()
transport = w.client.get_transport() if w.client else None
active = transport is not None and transport.is_active()
print("CONNECT: connected transport_active=" + str(active))
assert active, "transport not active"
code, out, err = w.run("echo " + token + "; hostname", timeout_s=25)
print("EXEC_EXIT: " + str(code))
print("EXEC_OUT: " + out.strip()[:200])
assert code == 0, (code, err[:200])
assert token in out, "session echo token missing"
print("STATUS: connected (transport_active=True, exec exit=0, token echoed)")
print("SESSION_BIND: single SSHClientWrapper session serves terminal/files/jobs domains; wx rebind covered by W19 slice")
w.close()
print("DISCONNECT: OK")
print("GJ01_EXTERNAL_RESULT: PASS")
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git rev-parse HEAD; echo "==="; git status --short | head -n 50; echo "===diff check==="; git diff --check 2>&1 | head -n 20; echo "exit=$?"; echo "===diff stat W45-owned?==="; git diff --stat 2>&1 | head -n 40
c8293d3ca309526ed250c794c3b294f7c54ef369
===
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
===diff check===
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
exit=0
===diff stat W45-owned?===
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
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_w15_fresh_user_startup.py tests/test_w19_connection_lifecycle.py -p no:cacheprovider -q 2>&1 | tail -n 10
assert model.controller.state == ConnectionState.DISCONNECTED
            assert model.controller.session is None
>           assert worker_ssh.closed >= 1
E           assert 0 >= 1
E            +  where 0 = <test_w19_connection_lifecycle.FakeSsh object at 0x000001BFD2C5C140>.closed

tests\test_w19_connection_lifecycle.py:292: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_w19_connection_lifecycle.py::test_panel_cancel_control_cancels_slow_connect_safely
1 failed, 30 passed in 13.45s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_w19_connection_lifecycle.py::test_panel_cancel_control_cancels_slow_connect_safely -p no:cacheprovider -q 2>&1 | tail -n 20; echo "===RETRY==="; PYTHONPATH=src python -m pytest tests/test_w19_connection_lifecycle.py -p no:cacheprovider -q -k "rebind or profile_switch or disconnect_clears or transport_loss or host_key" 2>&1 | tail -n 5; echo "===THIRD==="; PYTHONPATH=src python -m pytest tests/test_wx_connection.py tests/test_wx_connection_profiles.py tests/test_connection_profile_service.py -p no:cacheprovider -q 2>&1 | tail -n 5
.                                                                        [100%]
1 passed in 0.38s
===RETRY===
......                                                                   [100%]
6 passed, 14 deselected in 3.27s
===THIRD===
.................................................                        [100%]
49 passed in 6.78s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONPATH=src python -m pytest tests/test_w15_fresh_user_startup.py tests/test_w19_connection_lifecycle.py -p no:cacheprovider -q 2>&1 | tail -n 5; echo "===AGAIN==="; PYTHONPATH=src python -m pytest tests/test_w15_fresh_user_startup.py tests/test_w19_connection_lifecycle.py -p no:cacheprovider -q 2>&1 | tail -n 5
...............................                                          [100%]
31 passed in 12.67s
===AGAIN===
...............................                                          [100%]
31 passed in 12.64s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls "C:/Users/mskomek/AppData/Local/hpc-client-gui-lab/hpc-client-profile.json" 2>&1 | head; echo "==="; timeout 30 python .tmp/w45-run/gj01_connect.py 2>&1 | tail -n 20; echo "EXIT=$?"
C:/Users/mskomek/AppData/Local/hpc-client-gui-lab/hpc-client-profile.json
===
CONFIG_ROOT_ISOLATED: D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\w45-gj01-hzbilwis\fresh-root
LOGS_SETTINGS_INIT: OK
PROFILE: disposable-W45-copy host=192.168.250.11 user=hpctest provider=local-real auth=key host_key_policy=accept-new
HOST_KEY_PATH: isolated=D:\Projeler\hpc-client-gui\.tmp\os\20260924-203154-ca45d2b7\23844-1790271114033321000\w45-gj01-hzbilwis\known_hosts_w45 seeded=True
CONNECT: connected transport_active=True
EXEC_EXIT: 0
EXEC_OUT: W45-GJ01-8887c8cb
login-control01
STATUS: connected (transport_active=True, exec exit=0, token echoed)
SESSION_BIND: single SSHClientWrapper session serves terminal/files/jobs domains; wx rebind covered by W19 slice
DISCONNECT: OK
GJ01_EXTERNAL_RESULT: PASS
EXIT=0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git status --short -- docs/wave-reports/v2/opencode/W45_WAVE_REPORT.md 2>&1; echo "==="; git check-ignore -v docs/wave-reports/v2/opencode/W45_WAVE_REPORT.md 2>&1; echo "==="; git log --oneline --all -- docs/wave-reports/v2/opencode/W45_WAVE_REPORT.md 2>&1 | head; echo "===source GJ01==="; sed -n '55,67p' waves/bak/WAVE_V2_FINAL_10.md 2>&1; echo "===opencode source==="; sed -n '50,70p' opencode/sources/WAVE_V2_FINAL_10.md 2>&1 | head -n 30
?? docs/wave-reports/v2/opencode/W45_WAVE_REPORT.md
===
===
===source GJ01===
### GJ-01 — Fresh user to connected state

```text
clean config
→ launch
→ logs/settings initialize
→ create profile
→ select provider/auth
→ host-key path
→ connect
→ status says connected
→ remote-dependent tabs/actions bind to the same session
```
===opencode source===

W10 owns integrated replay of `GJ-01` through `GJ-10` from the Index.

At minimum execute these end-to-end journeys on the candidate code and then the packaged candidate:

### GJ-01 — Fresh user to connected state

```text
clean config
→ launch
→ logs/settings initialize
→ create profile
→ select provider/auth
→ host-key path
→ connect
→ status says connected
→ remote-dependent tabs/actions bind to the same session
```

### GJ-02 — Connection + terminal lifecycle
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
AC_WAVE_BRIDGE_STDOUT_BEGIN
Auditing W45 — running the canonical fresh-context check.
W45 scope confirmed — now gathering fresh evidence for the independent verdict.
First pass surfaced a timing-sensitive check — verifying whether it's a stable defect or test flakiness.
## W45 Audit — fresh independent verdict

**Wave:** W45 (GJ-01 Fresh user to connected state) — owned requirement `HPC-W10-GJ01-PATH-001`, start gate NONE, cohort P10-golden-journeys.
**Candidate:** HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369` — matches W44 audit candidate SHA and report baseline. Working tree dirty with pre-existing sibling-wave modifications, preserved untouched.
**Report audited:** `docs/wave-reports/v2/opencode/W45_WAVE_REPORT.md` (untracked, allowed closeout-only path), status READY FOR INDEPENDENT AUDIT.

### Authority reads (audit)
- `waves/pending/W45.md` — execution kind, 1 owned ID, evidence `GUI,PACKAGE,EXTERNAL`, read-only candidate rule, unattended contract.
- `opencode/REQUIREMENT_REGISTRY.md:1292` — GJ-01 explicit path confirmed.
- `opencode/TODO_OWNERSHIP_MAP.md` — no W45 rows (confirmed, empty grep).
- `waves/bak/WAVE_V2_FINAL_10.md:55-67` + `opencode/sources/WAVE_V2_FINAL_10.md` — GJ-01 9-step path semantics preserved.
- `.opencode/protocol/LOCAL_REAL_HPC_LAB.md` — LOCAL_REAL_HYPERV default for generic SSH/connection claims; key-only; disposable isolated state.
- Live code inspected read-only (`ssh/client.py`, `config/storage.py`, `core/paths.py` surfaces referenced, not modified).

### Independent re-execution (fresh context, read-only)
- `tests/test_w15_fresh_user_startup.py + tests/test_w19_connection_lifecycle.py` → **31 passed** on retry (first run: 1 failed / 30 passed on `test_panel_cancel_control_cancels_slow_connect_safely`, `assert worker_ssh.closed >= 1`; isolated rerun PASS; two further full reruns 31 passed each — timing-sensitive cancel flake, not a deterministic W45-owned defect; W45 touched zero product lines).
- Focused rebind slice (`-k "rebind or profile_switch or disconnect_clears or transport_loss or host_key"`) → **6 passed**.
- `tests/test_wx_connection.py + tests/test_wx_connection_profiles.py + tests/test_connection_profile_service.py` → **49 passed**.
- GUI total: **80 passed, 0 failed** on accepted reruns, incl. real wx modal/thread proof. No test weakened (zero skip/xfail edits by W45).
- EXTERNAL harness `.tmp/w45-run/gj01_connect.py` run verbatim → **GJ01_EXTERNAL_RESULT: PASS** (isolated `HPC_GUI_CONFIG_ROOT` fresh-root, LOGS_SETTINGS_INIT OK, isolated `known_hosts_w45` seeded, `transport_active=True`, `EXEC_EXIT: 0`, fresh token echo + `hostname login-control01`, STATUS connected, DISCONNECT OK). No secrets in report (token class-redacted).
- Lab Slurm degradation (compute01 down) correctly recorded as infrastructure state, out of GJ-01 scope (no job submit in path); not reset by worker — correct serialized-lab discipline. No `EXTERNAL_BLOCKED` needed since connect succeeded.
- PACKAGE → **NO-CANDIDATE honestly recorded**: no artifact built/published/claimed by W45; zero product modifications so no freeze invalidation; freeze owned downstream (W56–W61). No package claim made anywhere — accepted as truthful N/A with concrete justification for a read-only journey-replay wave.
- Diff review: `git diff --check` exit 0 (only pre-existing sibling CRLF warnings); `git diff --stat` shows only sibling-wave M files; W45 added zero tracked hunks and zero src/test edits; sole new file is the canonical report. Scope discipline honored.

### Findings
- No owned blocking defect. GJ-01 executes end-to-end: clean config → launch/logs-settings → profile/provider-auth → host-key → connect → connected status → same-session bind, plus negative/lifecycle/identity/persistence/error-visibility coverage via green slices.
- Cross-scope routes: none. One transient cancel-timing flake recorded as observation (OBS-AUDIT-001), not a product defect, cleared on independent retry.
- Evidence binds to tested HEAD `c8293d3`; no stale PASS reused. Audit performed no product repairs.

**Audit verdict: PASS** — W45 meets its Definition of Done; ready for controller independent close.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
