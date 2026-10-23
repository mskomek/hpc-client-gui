# ANSYS Journal Studio — Continuation Acceptance

Date: 2026-10-23

## Revision

Application branch: codex/ansys-journal-studio-host-integration
Application code commit: 1cec0471e3daf50a16ba4161282aff2260ba9dd9
Plugin branch: codex/ansys-journal-studio-plugin
Plugin code commit: 744d1bb556660576eb2597fe0b593ef2acc7e83b

The final documentation commit is the application branch HEAD included in the handoff manifest. The authorized feature branches are pushed after report commit; exact refs and hashes are recorded in the handoff manifest.

## Acceptance matrix

| Area | Status | Evidence / limit |
|---|---|---|
| Tailscale remote workstation | PARTIAL | Remote Tailscale service online and SSH works; the remote workstation is not the Hyper-V host |
| Windows11 VM | PARTIAL | Current per-user installer installed and uninstalled; no full GUI/plugin lifecycle |
| Ubuntu-Test VM | HISTORICAL | Prior four-test evidence used an older service hash; not current-source proof |
| login-control01 | PASS, lab path | Current-source live SFTP 19/19; not Tailscale-routed |
| compute01 / compute02 | PARTIAL | Scheduler relationship observed; guest SSH via remote Tailscale not proven |
| Windows installer | PARTIAL | Current per-user install/uninstall passed; unsigned; current per-machine not VM-tested |
| Windows install/update | PARTIAL | Current install/uninstall passed; complete upgrade/downgrade/repair lifecycle not tested on current package |
| Linux deb lifecycle | HISTORICAL | Earlier Ubuntu-Test lifecycle passed on a different service hash |
| Plugin install/update/rollback | HISTORICAL / NOT_RUN current | Prior catalog/lifecycle evidence is not current guest acceptance |
| GUI drag-drop | NOT_RUN | OS-level file and card drag/drop not verified |
| Cross-session persistence | NOT_RUN | No current-source fresh-process layout comparison |
| Live SFTP | PASS | 19/19 actual SFTP checks on current service source; local lab route |
| Live Slurm read-only | PASS | Slurm 23.11.4; queue empty before/after |
| Slurm draft | PASS, partial GUI | One-node draft accepted; current GUI Jobs handoff not fully exercised |
| Slurm test-only | PASS | sbatch --test-only exit 0; no job submitted |
| Fluent startup | HISTORICAL PASS; current attempt inconclusive | Historical 2026-10-22 startup/TUI pass; current RustDesk attempt found no Fluent process |
| Fluent case solve | NOT_RUN | No case/mesh or explicit solve approval |
| Security | PARTIAL | Automated suites and live-path safeguards pass; hostile archive matrix incomplete |
| Regression | PARTIAL | Focused suites pass; broad pytest had a wx native access violation |
| 500-line exceptions | PARTIAL | 42 remain; 12 conflicted checkout files unchanged |

## Test summary

PASS: app-focused suite 1,017; plugin suite 192; SSH focused 24; large-journal focused 6; package/version focused 20; live SFTP 19/19; Slurm test-only; current Windows11 per-user install/uninstall; Ruff, registry, i18n, package content, and architecture checks.

FAIL: broad pytest process ended with a wx native access violation; current RustDesk Fluent process check did not find a Fluent process.

SKIP: 22 skipped in the app-focused run. Suite counts are independent and are not aggregated.

BLOCKED: Tailscale-to-HPC VM routing, complete current GUI acceptance, current per-machine installer lifecycle, signed production package, and full adversarial security matrix.

NOT_RUN: Fluent case solve and real Slurm job submission.

## Final verdict

BLOCKED_EXTERNAL for overall continuation acceptance. The implemented Journal Studio source, live SFTP path, Slurm test-only draft, and current-source per-user installer path have substantial passing evidence, but the acceptance target requires proof over the requested remote route and the remaining GUI/installer/security workflows. No feature is marked GO based on historical, mock-only, or unrelated-path evidence.

Fluent case solve is outside the minimum author/edit/lint/job-draft scope unless the owner expands it; its absence alone does not prevent acceptance of that narrower product scope. The overall verdict remains blocked for the independent reasons above.

## External prerequisites

1. Tailnet/Hyper-V owner chooses and authorizes a safe guest access path (guest tailnet membership or narrowly scoped subnet routing).
2. Rerun live SFTP/Slurm acceptance through that verified route and exercise the GUI Jobs handoff.
3. Run current-source OS-level GUI drag/drop and cross-session persistence acceptance.
4. Test current per-machine installer and full update/rollback/plugin lifecycle on the Windows11 guest.
5. Obtain signing certificate/process before production package acceptance.
6. Complete the isolated hostile-archive and interrupted-update security matrix.
7. Integrate the 12 conflicted line-limit files safely before refactoring them.
