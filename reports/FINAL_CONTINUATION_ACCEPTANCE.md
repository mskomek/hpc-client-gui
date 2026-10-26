# ANSYS Journal Studio — Final Continuation Acceptance

Date: 2026-10-26

## Current acceptance — 2026-10-26 (F08-R5 layered source)

**Verdict: PARTIAL.** The latest full regression F08-R5 adds the updater source/test extractions and SSH jump-host profile test split to the R6c base. Its layered source identities are base ZIP `82744F9CBB16266E88613E883F7D9E24D59A37D4478BBFD36AC0EDD58FA0B9E5`, updater test overlay `DA7626C340DED767EFE5C877B08E2D443AC23433D17E51870E18F505853CDEC1`, updater source overlay `D448B53E37A262559C4987F22A3034DE9D7ACECBFC1D89AEEC2AEA1AA3A21E9E`, and SSH test split overlay `20C7E0F4F112F9F1D2320EE8E07B3D0F6AC81076A9C0A144EDA5BEA9C0A797BD`, based on app commit `3eb3dc637359b9c1c143d4e418d34b2411c17ac5`. Results below remain separate suites.

| Gate | Status | Current result / remaining limit |
|---|---|---|
| wxPython native crash | **PASS** | W19 duplicate teardown root cause fixed. R5 full suite had no native marker; R6c broad wx 3/3 each passed 725, 1 skipped. |
| Full app regression | **PASS** | Windows11-New, Python 3.14.7: R5 4,415 passed, 50 skipped, 29 subtests, 1 warning; exit 0. |
| Tailscale to HPC | **PASS via Kole SSH jump** | Direct tailnet peer to Kole then strict-key SSH ProxyJump to guest; direct guest 100.x membership/subnet routing not claimed. |
| Live SFTP | **PASS** | 19/19 on the verified Kole jump route; cleanup PASS. |
| Slurm | **PASS, test-only** | Slurm 23.11.4 `sbatch --test-only`; GUI draft handoff passed; no submission, `srun`, `salloc`, or solver job. |
| Windows GUI | **PARTIAL** | The exact R6c portable executable passed Studio open, 10,020-line source-mode usability, tabs, undo/redo, dirty-journal plugin lifecycle, and normal-mode test-catalog isolation on Windows11-New. Remaining GUI boundaries are listed in F04. |
| Windows per-user installer | **HISTORICAL PASS** | Earlier install/uninstall passed; no R6c installer test was run. This continuation used the portable executable per the latest instruction. |
| Windows per-machine installer | **HISTORICAL PASS / R6c NOT_RUN** | Earlier fix4 machine-payload install/upgrade/rollback/uninstall passed in its isolated identity. No R6c installer or UAC operation was run in this continuation; portable GUI validation was used instead. Production signing remains blocked. |
| App/plugin GUI lifecycle | **PARTIAL** | R6c portable GUI passed plugin install, enable, disable, uninstall and reinstall with a dirty journal open; no newer version existed in the isolated catalog, so update and rollback remain unverified in this run. |
| Ubuntu current-source | **PARTIAL / GUI BLOCKED_ENV** | `.deb` lifecycle/package smoke passed on the 398-file app payload. Live probe found the console at the login screen; existing GUI PID 210326 was preserved. Current-source Jobs-editor handoff needs an active interactive session. |
| Security matrix | **PARTIAL** | Focused security suite, dirty-journal plugin lifecycle, and normal-mode test-catalog isolation pass. Disk exhaustion, interrupted lifecycle, junction and resource-exhaustion cases remain. |
| 500-line architecture | **PARTIAL** | Gate passes across 893 first-party files; 29 exceptions remain (17 independent; 12 protected-checkout overlaps). |
| Fluent | **PARTIAL** | Historical Fluent 2025 R2 startup PASS; case/mesh solve NOT_RUN by scope. |
| Production signing | **BLOCKED_EXTERNAL** | No valid code-signing certificate / approved signing process. |

R5 regression details and its layered source hashes are in `reports/F01_WX_NATIVE_CRASH_FIX.md`, `reports/F08_ARCHITECTURE_DEBT.md`, and `reports/F10_FULL_REGRESSION.md`. Exact logs and JSON are under `.tmp/F08-jobs-scroll-20261026/evidence/kole-win11-new/`; overlay ZIPs and manifests are under `.tmp/F08-jobs-scroll-20261026/evidence/local/`. Portable GUI evidence is in `.tmp/F04-gui-matrix-20261025/evidence/r6c-ui-20261026/`; no installer or UAC action was part of this continuation.

Application branch remains `codex/ansys-journal-studio-host-integration`; remote HEAD `3eb3dc637359b9c1c143d4e418d34b2411c17ac5`. Plugin branch remains `codex/ansys-journal-studio-plugin`; remote HEAD `744d1bb556660576eb2597fe0b593ef2acc7e83b`. No commit or push was made. The protected `D:\Projeler\hpc-client-gui` checkout was not modified.

### Remaining work

1. If exact R6c installer acceptance is still required, schedule it separately with an operator-visible UAC session; this portable continuation did not attempt elevation.
2. Complete remaining Windows GUI boundary cases (including plugin update with a newer catalog version), Ubuntu Jobs-editor handoff, and adversarial VM security cases.
3. Reduce the 17 independent line-limit exceptions; do not edit the 12 protected-checkout conflicts.
4. Obtain approved signing for a production release. No production release or Fluent solver job was started.

## Historical snapshot — 2026-10-25

Application branch: codex/ansys-journal-studio-host-integration
Application base commit: 3eb3dc637359b9c1c143d4e418d34b2411c17ac5
Latest tested source-code manifest SHA-256: b0d9e1d53088e71a244e60e2f6dc713633dcadc633eb145d87750225b69714db
Latest transport snapshot SHA-256: 21e8c1a1c72dd8a2a4c81e33bf9db35a95b0b1f3c864f3ac3b3f48f98cf3b44a
Plugin branch / commit: codex/ansys-journal-studio-plugin / 744d1bb556660576eb2597fe0b593ef2acc7e83b

Remote feature branch heads were checked with git ls-remote on 2026-10-24: application 3eb3dc637359b9c1c143d4e418d34b2411c17ac5; plugin 744d1bb556660576eb2597fe0b593ef2acc7e83b. No continuation changes were pushed.

The application worktree has uncommitted user/task changes. No commit or push was made; repository instructions require approval before committing or pushing. The separate D:\Projeler\hpc-client-gui checkout was not modified.

## Acceptance matrix

| Area | Status | Current evidence and limit |
|---|---|---|
| wxPython native crash | **PASS** | Three clean Windows11-New broad wx runs on latest source manifest, each 725 passed, 1 skipped, 3,736 deselected; no access violation or `UnregisterClass` failure. |
| Full application pytest | **PASS** | Windows11-New, Python 3.14.7: 4,412 passed, 50 skipped, 29 subtests passed, 1 warning; exit 0. Log SHA-256 `A02712049B3075B55CABF0D7FE7775D6D9FCBD6EE46C1445550956B486704C64`. |
| Tailscale to HPC guests | PASS via SSH jump | PC → direct Tailscale peer Kole → authenticated SSH direct-tcpip to guest. login-control01, compute01, and compute02 probes passed with strict host-key checking. Subnet route propagation and guest 100.x membership are not claimed. |
| Tailscale live SFTP | PASS, prior source manifest | 19/19 real SFTP tests through the Kole jump path; cleanup PASS. Evidence and source hash are in the local F03 report. |
| Kole Slurm test-only | **PASS, no submission** | Slurm 23.11.4; `sbatch --test-only` passed through `kole-login`; no real job or solver was started. Current layout build Jobs-editor draft handoff passed, submit controls untouched. |
| Windows current-source GUI | PARTIAL | Latest layout build validated lint, Jobs-editor handoff, and panel/tab persistence across process restart. Explorer drag/drop matrix and remaining boundary cases are NOT_RUN. |
| Windows per-user installer | HISTORICAL PASS | Earlier install/uninstall pass is not tied to corrected archive 3cc972c0. Current-source installer was not built. |
| Windows per-machine installer | **BLOCKED_USER_CANCELLED_UAC** | The isolated RunAs attempt was cancelled; no elevated install artifact exists. Production signing remains unavailable. |
| Windows app/plugin lifecycle | PARTIAL | Earlier packaged plugin lifecycle passed on a previous source/package. Corrected-source Windows smoke passed, but corrected-source full plugin install/update/rollback/disable/uninstall lifecycle is NOT_RUN. |
| Ubuntu current-source package | PARTIAL | `.deb` lifecycle and packaged smoke passed on recorded prior source manifest `9c401e4a…`; current layout-build interactive Studio workflow remains open. |
| Security matrix | PARTIAL | Focused current-source security selection and plugin tests passed; VM interruption, disk exhaustion, junction, hostile resource-exhaustion, and dirty-journal lifecycle cases remain incomplete. |
| 500-line architecture | PARTIAL | Gate PASS; 37 allowlisted exceptions remain (25 independent; 12 overlap the separate checkout). |
| Fluent startup | PASS | Fluent 2025 R2 no-GUI TUI startup on Kole, version 25.2.0, exit 0; no case/mesh loaded. |
| Fluent solve | NOT_RUN | Outside minimum editor/lint/draft scope; no case/mesh or solve approval. |
| Production signing | BLOCKED_EXTERNAL | No valid code-signing certificate and approved signing process available. |

## Suite results (kept separate)

- Latest-source wx broad suite: 3 runs; each **725 passed, 1 skipped, 3,736 deselected**.
- Latest-source full app regression: **4,412 passed, 50 skipped, 29 subtests**, exit 0.
- Kole Tailscale-jump SFTP: **19/19 PASS** on its recorded source snapshot, cleanup PASS.
- Current layout-build Slurm draft handoff and `sbatch --test-only`: **PASS**, no real submission.
- Package smoke and security counts are from their individual source manifests as recorded in the F05–F07 evidence files; counts are not combined.

Counts above describe separate suites and are not combined.

## Final verdict

**PARTIAL.** The wx native crash repeat gate and the full Windows application regression pass on the latest source manifest. Kole Slurm test-only and the GUI draft handoff also pass. Explorer drag/drop, complete current-source installer/Ubuntu Studio workflows, adversarial VM security cases, and 37 architecture exceptions remain open. Per-machine installer verification was blocked by cancelled UAC; production signing is unavailable. No production package was signed or published.

## Evidence

- Acceptance evidence files are local task deliverables under `reports/`: `F02_TAILSCALE_HYPERV_RECOVERY.md`, `F03_TAILSCALE_LIVE_SFTP.md`, `F03_TAILSCALE_SLURM_TESTONLY.md`, `F04_WINDOWS_GUI_ACCEPTANCE.md`, `F05_WINDOWS_INSTALLER_LIFECYCLE.md`, `F06_UBUNTU_CURRENT_SOURCE_ACCEPTANCE.md`, `F07_SECURITY_MATRIX.md`, `F08_ARCHITECTURE_DEBT.md`, `F09_FLUENT_SCOPE.md`, and `F10_FULL_REGRESSION.md`. They are ignored by the repository's `/reports/` rule, so they are not available in a clean clone unless included in the handoff package.
- Corrected source package smoke and SFTP/security logs are under .tmp; report entries record artifact and evidence SHA-256 values.

## Remaining prerequisites and work

1. Complete Explorer file/card drag/drop and remaining Windows GUI boundary checks on the current frozen build.
2. Retry the per-machine installer only when the VM's interactive UAC consent can be completed; do not count the cancelled attempt as a pass.
3. Build and test the latest-source Ubuntu package's interactive Journal Studio/plugin/editor workflow.
4. Run remaining isolated VM security lifecycle cases, including interruption, disk exhaustion, junction escapes, and dirty-journal preservation.
5. Reduce the 25 independent line-limit exceptions; leave the 12 cross-checkout files untouched until safely integrated.
6. Obtain an approved code-signing certificate/process before any production-signed release.

## 2026-10-25 continuation — current-source status

Application branch `codex/ansys-journal-studio-host-integration`, base HEAD `3eb3dc637359b9c1c143d4e418d34b2411c17ac5`; tested dirty source archive SHA-256 `9c401e4adc9e20cfead95693bbb9a480a92f019d42b9ab5c4efb7315df16c21a`. Plugin branch/commit remains `codex/ansys-journal-studio-plugin` / `744d1bb556660576eb2597fe0b593ef2acc7e83b`.

| Acceptance area | Updated status |
|---|---|
| wx native crash | No recurrence in one full current-source Windows VM run. Three prior broad wx repeats passed on archive `3cc972…`; exact `9c401…` repeat gate remains at one complete run. |
| Full current-source pytest | **PASS** on Kole `Windows11-New`: 4,408 passed, 50 skipped, 29 subtests passed, 1 warning; Python 3.14.7; exit 0; 971.80s. Log SHA-256 `5DF20969A7EB49E0B696B59D6453C5A162D0BA5A64C0E0F5D135DAA8ED4C7CC6`. |
| Tailscale HPC route | **PASS via verified SSH jump** from PC to Kole over Tailscale and strict ProxyJump to `login-control01`; no guest Tailscale identity/subnet route claimed. |
| Current-source SFTP | **PASS 19/19**, cleanup PASS, result SHA-256 `EB112E43C0666919065BC614D6E1E76963B8EBC582EFAC9B5ED769638259F77F`. |
| Current-source Slurm test-only | **PASS_TEST_ONLY_NO_SUBMISSION** on Slurm 23.11.4; queue empty before/after; estimated Job 13 was not submitted; cleanup PASS; result SHA-256 `9C92E7BA976F660B6D27B8BBF171230498731255135A85F3528399B40B33D0EA`. |
| Windows11 current GUI | **PARTIAL**; current-source full pytest passes; packaged GUI smoke and plugin surfaces are from archive `3cc972…`; Explorer drop matrix and new-process panel persistence remain open. |
| Windows installer lifecycle | **PARTIAL**; current-source full installer lifecycle not complete. UAC rollback awaits interactive approval; production signing remains externally blocked. |
| Ubuntu current-source | **PARTIAL**; `.deb` built (SHA-256 `0e191423a30ee79d2da512530de7737f70e60c7aaa7cd70d02626ba1c49bf4a1`) and extracted packaged wx smoke passed 21/21. Install lifecycle and current-source Journal Studio plugin/editor workflow remain open. Existing installed app/process was left intact. |
| Security | **PARTIAL**; current-source Ubuntu selection 83/83 PASS; plugin repository 192/192 PASS and registry valid at commit `744d1bb…`; VM fault-injection cases remain open. |
| 500-line architecture | Gate **PASS**: 874 files scanned, 37 exceptions (25 independent; 12 cross-checkout). The latter remain untouched. |
| Fluent | Historical Fluent 25.2.0 startup PASS; solver/case/mesh **NOT_RUN** by scope. |

Separate suite totals above are not added together. The initial Windows R1 attempt is excluded because the staging/ACL harness failed; corrected R2 completed cleanly. No `sbatch` submission, `srun`, `salloc`, Fluent solver, production signing, release, commit or push occurred. The protected `D:\Projeler\hpc-client-gui` checkout remained untouched.

**Final verdict: PARTIAL.** The 2026-10-25 current-source Windows full regression, live SFTP suite, Kole Slurm `--test-only`, and Ubuntu packaged wx smoke are now evidenced. Remaining acceptance work includes exact-source repeated wx broad runs, real Windows Explorer drag/drop and cross-process persistence, complete current-source installer and Ubuntu package lifecycles, current-source GUI Jobs-editor handoff, VM adversarial security cases, and 37 architecture exceptions.

## 2026-10-25 latest Kole VM continuation

The latest exact-source acceptance is tied to application base commit `3eb3dc637359b9c1c143d4e418d34b2411c17ac5` and source archive SHA-256 `9c401e4adc9e20cfead95693bbb9a480a92f019d42b9ab5c4efb7315df16c21a`.

| Area | Latest status |
|---|---|
| wx native crash | **PASS**: 3/3 current-source broad wx runs on Windows11-New, each 725 passed, 1 skipped, 3,732 deselected; no crash. |
| Full application pytest | **PASS**: 4,408 passed, 50 skipped, 29 subtests passed, 1 warning; exact-source full log SHA-256 `5DF20969A7EB49E0B696B59D6453C5A162D0BA5A64C0E0F5D135DAA8ED4C7CC6`. |
| Tailscale/Kole HPC path | **PASS via strict-key SSH jump**; direct Kole peer and guest jump verified. No subnet route or direct guest Tailscale identity is claimed. |
| Live SFTP | **PASS 19/19**, cleanup pass. |
| Slurm | **PASS test-only** on 23.11.4; queue empty before/after; no real job submitted. GUI Jobs draft handoff remains open. |
| Windows per-user installer | **PASS** current-source install, Start Menu/application launch smoke 21/21, uninstall, and profile marker preservation. |
| Windows per-machine installer | **PENDING_USER_UAC**: exact current-source installer is launched through `RunAs` from the VM's interactive session; the task remains running without install artifacts. User must complete the Windows UAC consent in the VM session, after which verification can continue. |
| Ubuntu current-source `.deb` | **PASS** isolated install/remove/purge, 21/21 packaged runtime checks, and distinct payload upgrade/downgrade with profile preservation. Current-source interactive Journal Studio/plugin editor actions remain open. |
| Security matrix | **PARTIAL**: 83 current-source Ubuntu security checks and 192 plugin tests pass; adversarial VM interruption/resource exhaustion cases remain. |
| 500-line architecture | **PARTIAL**: gate passes; 37 exceptions remain (25 independent, 12 protected-checkout overlaps). |
| Fluent | Historical startup pass; solver/case/mesh **NOT_RUN** under the stated scope. |
| Production signing | **BLOCKED_EXTERNAL**: unsigned acceptance artifacts were used; approved signing certificate/process is unavailable. |

Evidence details and hashes are in `reports/F05_WINDOWS_INSTALLER_LIFECYCLE.md`, `reports/F06_UBUNTU_CURRENT_SOURCE_ACCEPTANCE.md`, and `reports/F10_FULL_REGRESSION.md`. Separate test counts remain separate. No real Slurm job, `srun`, `salloc`, Fluent solver, production release, commit, or push occurred. The protected user checkout `D:\Projeler\hpc-client-gui` remains untouched.

**Latest verdict: PARTIAL.** Per-machine installer acceptance awaits the interactive UAC action. Current-source Windows manual editor/drag-drop/persistence and Ubuntu Journal Studio editor workflows, full adversarial security coverage, and architecture debt remain open.

### Per-machine UAC result correction — 2026-10-25 09:30:47 +03:00

The exact-source installer RunAs attempt returned The operation was canceled by the user; result JSON SHA-256 43d4c7a7ac3413dc9ac1328edff92e79c0b1a1c438aff3139adc7af498e88b14. The interactive task ended, and guest verification found no per-machine install artifacts. Replace the earlier pending-running state above with **BLOCKED_USER_CANCELLED_UAC**. Do not claim per-machine install or elevation acceptance.

## Latest Kole VM update — 2026-10-25

The R3 full application regression now passes on Windows11-New under interactive user `home`, Python 3.14.7, base commit `3eb3dc637359b9c1c143d4e418d34b2411c17ac5`, source-code manifest SHA-256 `b0d9e1d53088e71a244e60e2f6dc713633dcadc633eb145d87750225b69714db`. Result: **4,412 passed, 50 skipped, 29 subtests passed, 1 warning**, exit 0 in 951.04 seconds. Log SHA-256: `A02712049B3075B55CABF0D7FE7775D6D9FCBD6EE46C1445550956B486704C64`. The run contained no native access violation or wx class-unregister failure. R2’s three staging errors were corrected and all three failed target tests passed in the follow-up run.

| Gate | Latest status |
|---|---|
| wx native crash | **PASS, 3/3 exact-source broad repeats**; each 725 passed, 1 skipped, 3,736 deselected. The independent full suite also passed without access violation or `UnregisterClass` failure. |
| Tailscale / Kole route | Verified PC → Kole Tailscale peer → strict SSH jump to Kole guest. Guest access is through Kole's Hyper-V host; direct guest Tailscale or subnet route is not claimed. |
| Live SFTP | 19/19 PASS from the current-source Kole jump test; cleanup passed. |
| Slurm draft and test-only | GUI draft handoff and Slurm 23.11.4 `sbatch --test-only` passed in the current layout build; no real submission or solver. |
| Windows GUI | Current layout build verified validation and Jobs editor handoff; panel ratios and selected tab survived a close and new-process reopen. Explorer drag/drop matrix remains open. |
| Windows per-user installer | Earlier current-source package lifecycle passed; confirm exact layout-build artifact binding in F05 before release acceptance. |
| Windows per-machine installer | **BLOCKED_USER_CANCELLED_UAC**; no elevated install was verified. |
| Ubuntu current-source package and GUI | Earlier `.deb` package lifecycle/smoke passed on its recorded source manifest; current layout-build interactive editor workflow remains open. |
| Security | PARTIAL; focused security and plugin suites pass, full adversarial VM lifecycle matrix remains open. |
| 500-line architecture | Gate passes with 37 allowlisted exceptions (25 independent; 12 protected-checkout overlaps). |
| Fluent | Historical startup only; solver/case/mesh remains NOT_RUN. |
| Signing / production release | BLOCKED_EXTERNAL; no approved production signing process. |

The overall verdict remains **PARTIAL**. The wx native-crash and full application regression gates now pass on the tested source manifest, while the current-source Explorer drop matrix, per-machine installer, Ubuntu interactive workflow, and adversarial security matrix remain incomplete; 37 architecture exceptions remain. No commit, push, real Slurm job, solver, or production release occurred. The protected `D:\Projeler\hpc-client-gui` checkout was not changed.

## 2026-10-25 UAC visibility retry update

On Kole `Windows11-New`, the operator-facing consent prompt is now reproducibly visible. The test VM had been configured to auto-elevate administrators without prompting (`ConsentPromptBehaviorAdmin=0`, `PromptOnSecureDesktop=0`); these two test-VM settings were changed to consent prompt `5` and secure desktop `1`. `EnableLUA` remains `1`. The exact per-machine acceptance installer hash `0a605eebfb423a21f14eb2da9740dea1936a1577c65bfd00514e220531e55794` was launched from `home`, Session 1. UAC screenshot SHA-256 is `67029d9c1cd568f012e516073edd68c17894b38a1b2e4a7b1c5a1a9c647a286e`.

The installer remains at `PROMPT_PENDING`; there is no elevated process, install log, or HKLM registration. User consent is still required before the per-machine installation can proceed. This artifact is tied to source archive `9c401e4a…`; the newer `642e080d…` layout-fix snapshot has not yet been repackaged as an installer. The overall verdict remains **PARTIAL**.

## 2026-10-25 fix4 acceptance update

This update supersedes the pending-UAC status above for the fix4 installer only. Application base commit remains `3eb3dc637359b9c1c143d4e418d34b2411c17ac5`, branch `codex/ansys-journal-studio-host-integration`; plugin branch/commit remain `codex/ansys-journal-studio-plugin` / `744d1bb556660576eb2597fe0b593ef2acc7e83b`. Current layout-fix source ZIP SHA-256 is `642e080dae9254ecfcac658da83f9a658e3029b1acee3c3a29fa5be3e90579c7` (1,364 files; manifest SHA-256 `e8914da550dc8792502d1ca8b79f0a074503c9c5b39b783365eeac45f81a25d3`). This is a working-source snapshot; no new commit or push was made.

| Gate | Latest fix4 disposition |
|---|---|
| Windows11-New Journal Studio GUI | **PASS for tested subset**: 6 focused tests; real packaged command drag/reorder, Undo/Redo, Save, and Explorer drop of one `.jou`. Other F04 boundary variants remain NOT_RUN. |
| Windows per-machine installer | UAC was accepted and the current fix4 installer wizard is open at its license screen. **PENDING_OPERATOR_LICENSE_ACCEPTANCE**: no HKLM registration, install directory, or machine Start Menu entry exists yet. This fix4 installer SHA-256 is `C2402DDDA1E34CBE3F1307CF0E917B747183E6CD36116C824DB6D580ECFCABF9`. |
| Full application regression | Prior 4,412-pass result is tied to manifest `b0d9e1d5…`; it is not a full-regression result for the newer `642e080d…` snapshot. |
| Tailscale, SFTP/Slurm, Ubuntu, security, architecture, Fluent, signing | See prior rows and wave reports. No new result is attributed to fix4 by this update. |

The guest wizard screenshot is `.tmp/f05-fix4-installer-build-20261025/installer-license-guest.png` (SHA-256 `6E20711B46C1BF269B26F9DFD899829CDBA3FD7FECC0BA716CF6BA5BA5DF5C59`); the guest UIA snapshot is `.tmp/f05-fix4-installer-build-20261025/installer-focus.json` (SHA-256 `E92BE409EAD2FE7ECF5B80367D0B400CE943622780838BF6793311929B3FC8D9`). The operator has been asked to accept the displayed PolyForm license and finish the default installation pages. The latest verdict remains **PARTIAL**; do not mark per-machine install or lifecycle PASS until guest registration, payload, launch, and cleanup checks complete.

## 2026-10-25 fix4 installer completion and live Plugin Manager lifecycle

This update supersedes the fix4 pending-license status above. Application source snapshot ZIP SHA-256: `642e080dae9254ecfcac658da83f9a658e3029b1acee3c3a29fa5be3e90579c7`; source manifest SHA-256: `e8914da550dc8792502d1ca8b79f0a074503c9c5b39b783365eeac45f81a25d3`; base commit `3eb3dc637359b9c1c143d4e418d34b2411c17ac5`. Plugin branch checkout HEAD `744d1bb556660576eb2597fe0b593ef2acc7e83b`.

On Kole `WINDOWS11-NEW`, the operator accepted the unknown-publisher UAC prompt and completed the PolyForm license and default install pages as `WINDOWS11-NEW\home`, Session 1. Exact fix4 machine installer SHA-256: `C2402DDDA1E34CBE3F1307CF0E917B747183E6CD36116C824DB6D580ECFCABF9`. Setup log reports installation succeeded (SHA-256 `B26185041967A235D8D22892B42D39CB47BD64227F13619B28887E9812C9986C`). HKLM registration reports version 1.5.9; Program Files install, uninstaller, and machine Start Menu shortcut exist. Installed GUI SHA-256 `72004AC1049DA0A5EEFCAE08F1D01F2CAC445B70F75E5EAA6E847D68FEB6C69C` and CLI SHA-256 `DD90BBD1C6524BA4B16513FB4F0EFB00467FA0C7CD226BCE3BF93875895B0E12` match the exact frozen package. Start Menu link resolves to the installed GUI; that GUI launched and opened Plugin Manager in the active session.

The real Plugin Manager workflow used a fresh, isolated config root and a local test catalog whose UI title showed `TEST CATALOG`; production registry settings were untouched. UI actions passed for Journal Studio 0.1.0 install, 0.1.1 update, rollback to 0.1.0, disable/enable, update, remove, reinstall, and final cleanup. `active.json`, `installed.json`, `disabled.json`, and package directories were read after state changes; final test-profile plugin indexes were empty. Details, action results, installer log, and screenshots are in `.tmp/f05-fix4-installer-build-20261025/guest-evidence/` and `reports/F05_WINDOWS_INSTALLER_LIFECYCLE.md`.

| Gate | Latest fix4 disposition |
|---|---|
| wx native crash / full pytest | Prior results remain bound to their own source manifest; full regression on manifest `e8914da5…` is **NOT_RUN**. |
| Windows11-New GUI | **PASS for tested subset**: 6 focused tests plus real command drag/reorder, Undo/Redo, Save, one Explorer `.jou` drop, and Plugin Manager workflows. Other drag/drop variants, large-journal UI, and session-to-session persistence matrix remain open. |
| Windows per-machine install | **PASS** for exact fix4 package, UAC/EULA, HKLM registration, file hashes, Start Menu shortcut, and installed app launch. |
| Windows app/plugin lifecycle | Plugin Manager operations **PASS** in an isolated local test profile. Different app-payload upgrade/downgrade, machine installer uninstall/reinstall, per-user/per-machine collision, and cross-install profile preservation are **NOT_RUN**. |
| Tailscale HPC, live SFTP, Slurm test-only | Prior results only; route remains via strict SSH jump to Kole, not direct guest Tailscale identity/subnet route. No real Slurm submission. |
| Ubuntu-Test current source | Prior package results only; current-source interactive Journal Studio workflow remains open. |
| Security / architecture | **PARTIAL**; adversarial VM matrix remains incomplete; 37 allowlisted architecture exceptions remain. |
| Fluent | Historical startup only; solver/case/mesh **NOT_RUN**. |
| Production signing | **BLOCKED_EXTERNAL**; unsigned acceptance artifacts only. |

Overall verdict remains **PARTIAL**. The fix4 per-machine install and plugin lifecycle passed, but this does not close app-payload downgrade/upgrade or installer uninstall and data-preservation cases. No commit, push, production signing, release, real Slurm job, `srun`, `salloc`, or Fluent solve occurred. The protected `D:\Projeler\hpc-client-gui` checkout remains untouched.

## 2026-10-25 latest exact-source VM acceptance addendum

Application branch `codex/ansys-journal-studio-host-integration`, base commit `3eb3dc637359b9c1c143d4e418d34b2411c17ac5`; current working-source ZIP SHA-256 `642e080dae9254ecfcac658da83f9a658e3029b1acee3c3a29fa5be3e90579c7`, manifest SHA-256 `e8914da550dc8792502d1ca8b79f0a074503c9c5b39b783365eeac45f81a25d3`. Plugin remains `codex/ansys-journal-studio-plugin` at `744d1bb556660576eb2597fe0b593ef2acc7e83b`.

| Gate | Latest status |
|---|---|
| wx native crash | **PASS**: three exact-source broad wx processes on Kole `Windows11-New`, each 725 passed, 1 skipped; no native crash or class-unregister failure. |
| Full application pytest — Kole | **PASS**: Windows11-New, Python 3.14.7; 4,414 passed, 50 skipped, 29 subtests; exit 0. |
| Full application pytest — local Windows11 | **HARNESS_PATH_LIMIT**: 4,411 passed, 50 skipped, 29 subtests, 3 failed (exit 1). The three plugin-catalog tests failed with Windows path-length errors in the canonical runner's deep temporary checkout. Those exact tests passed 3/3 from a short guest path; keep this separate from the Kole pass. |
| Windows per-machine installer | **PASS for fix4 install/launch and plugin lifecycle** after operator accepted UAC/license. App payload upgrade/downgrade, installer uninstall/reinstall and cross-install profile preservation remain NOT_RUN. |
| Tailscale HPC / live SFTP / Slurm test-only | **PASS via strict Kole SSH jump**, SFTP 19/19, Slurm 23.11.4 `sbatch --test-only`; no real job. Direct guest Tailscale/subnet route is not claimed. |
| Windows GUI | **PARTIAL**: panel persistence across a fresh process, Jobs editor draft handoff, command drag/reorder/undo/redo, and one Explorer `.jou` drop passed. Remaining OS drop and boundary cases are NOT_RUN. |
| Ubuntu current-source | Package lifecycle/smoke passed on recorded source; interactive Studio/plugin/editor GUI acceptance remains open. |
| Security / architecture | **PARTIAL**: adversarial VM lifecycle cases remain; architecture gate passes with 37 exceptions (25 independent, 12 protected-checkout overlaps). |
| Fluent / signing | Historical Fluent startup only; solve NOT_RUN by scope. Production signing BLOCKED_EXTERNAL. |

The local Windows full-suite attempt and short-path follow-up are detailed in `reports/F10_FULL_REGRESSION.md`; wx repeat evidence is in F01. Test counts remain separate by run. Overall verdict: **PARTIAL**, not GO. Remaining work includes the untested GUI/install/security/Ubuntu boundaries and the 37 architecture exceptions. No commit, push, production signing, release, Slurm submission, or Fluent solve occurred. The protected `D:\Projeler\hpc-client-gui` checkout remains untouched.

## 2026-10-25 exact fix4 Ubuntu-Test package update

This supersedes the earlier Ubuntu current-source row for package smoke and lifecycle only. On Kole Ubuntu-Test, source ZIP 642e080dae9254ecfcac658da83f9a658e3029b1acee3c3a29fa5be3e90579c7 produced .deb SHA-256 32410f78b02731e034f106e3e5d48cac18096dbc72065c9183aa7a9c58072e53 and packaged executable SHA-256 fe59d2ce381cd7f7492e6eac39e7eeee44cec184d2d6a38f4a4342e15ccf17a3. Packaged GUI smoke passed 21/21 (JSON SHA-256 690549077dd14a8bd42da43cd94e02ac561ad1561be7f2648b1a520d7a612e27). Exact-source alternate-root dpkg install/verify, distinct-payload upgrade from 1.5.8, rollback, remove/purge, profile-marker preservation, audit, and cleanup passed with exit 0. The live system package stayed at 1.5.9 and GUI PID 210326 remained running. Fix4 interactive Studio/plugin/editor acceptance remains open, so F06 is still PARTIAL. Evidence: .tmp/F06-fix4-ubuntu-evidence-20261025/ and reports/F06_UBUNTU_CURRENT_SOURCE_ACCEPTANCE.md.

## 2026-10-25 exact fix4 Windows security selection

On Kole Windows11-New, the exact fix4 source security selection completed on source ZIP SHA-256 642e080dae9254ecfcac658da83f9a658e3029b1acee3c3a29fa5be3e90579c7: 68 passed, 1 skipped, exit 0. The skip was POSIX permission semantics on Windows. The selection covered plugin manifest/catalog traversal and URL policy, payload tampering and truncation, digest checks, capability validation, rollback and write-failure state preservation. It does not close the OS fault-injection and open-journal cases in F07. Evidence: .tmp/F07-fix4-security-evidence-20261025/.

## 2026-10-25 fix4 Linux security selection

The exact fix4 source completed five app/plugin security and lifecycle modules on Kole Ubuntu-Test: 83 passed, 0 skipped, exit 0, Python 3.14.9. POSIX permission cases ran on Linux. The live 1.5.9 package and GUI PID 210326 remained unchanged. OS fault-injection and dirty-journal UI scenarios remain open. Evidence: .tmp/F07-fix4-linux-security-evidence-20261025/; pytest log SHA-256 9A271F2A916B0B6EE6CECB2426F0B3206EF074578BE55D9BC94F6F3FE3AB86AA.

## 2026-10-25 per-user installer prepared; per-machine UAC pending

Built the exact-fix4 per-user acceptance installer from the frozen Windows payload: SHA-256 AC67EDDD161B724E7579A00644437FD06AA152384904220FE540B0D2CACCD92B. The Windows11-New staged copy matched. It has not been installed yet. The fix4 per-machine acceptance install remains present, and the isolated uninstall task is waiting for operator approval at a real UAC prompt. Profile marker/hash were prepared before the request. The previous per-machine install/launch and Plugin Manager lifecycle pass remains valid for its tested scope; uninstall/reinstall and per-user/per-machine coexistence are still pending.


## 2026-10-25 latest continuation status — W33 overlay and installer uninstall

Application branch codex/ansys-journal-studio-host-integration remains at base commit 3eb3dc637359b9c1c143d4e418d34b2411c17ac5 with uncommitted isolated-worktree changes. Plugin branch codex/ansys-journal-studio-plugin remains at 744d1bb556660576eb2597fe0b593ef2acc7e83b. The Windows full regression used overlay ZIP SHA-256 77B48E0BF126A6F98E9FA7389DF0038ED3CE43F6FC381D66B408530779184EA8 and overlay manifest SHA-256 D5863F65EC35F2126490E9389AF7213D3707CAC96A745FE76E9112B1720E2780.

| Gate | Latest verified result |
|---|---|
| wx native crash | No native crash or wx class-unregister failure in the W33-overlay full suite; 4,414 passed, 50 skipped, exit 0. The three broad wx repeats remain bound to the earlier source archive identified in F01. |
| Full application regression | **PASS on Kole Windows11-New**: 4,414 passed, 50 skipped, 29 subtests passed, 1 warning, exit 0; Python 3.14.7, interactive Session 1. Evidence and hashes are in F10. |
| Tailscale HPC path | PC-to-Kole-host Tailscale peer plus strict SSH ProxyJump to Kole guests is usable. Direct guest Tailscale identity or subnet route is not configured or claimed. |
| Live SFTP / Slurm draft | Prior verified path result remains SFTP 19/19 and Slurm 23.11.4 sbatch --test-only; no real submission. |
| Windows GUI | **PARTIAL**: selected real GUI actions passed; full requested drag/drop and boundary matrix remains open. |
| Windows installers | Fix4 per-machine install, launch, Plugin Manager lifecycle, and operator-approved uninstall passed. Uninstall exit 0; no Program Files directory, HKLM registration, or machine shortcut remained; isolated profile marker hash was preserved. Per-user/per-machine coexistence and different application-payload upgrade/downgrade remain NOT_RUN. Production signing remains BLOCKED_EXTERNAL. |
| Ubuntu-Test | Exact fix4 .deb package smoke and isolated dpkg upgrade/rollback/purge passed. Interactive Journal Studio/editor acceptance remains open; live system package and GUI were left running. |
| Security | Exact-source Windows and Linux focused selections passed; adversarial OS fault injection, disk-full/file-lock, resource exhaustion, and dirty-journal UI cases remain NOT_RUN. |
| Architecture debt | **36 allowlisted exceptions** remain: 24 independent candidates and 12 protected-checkout overlaps. No unallowlisted line-limit violation; protected overlaps were not touched. |
| Fluent | Journal authoring/lint/draft scope preserved. Solver/case/mesh solve is NOT_RUN. |
| Release | No production signing, publication, or production install. |

Final verdict remains **PARTIAL**. Remaining acceptance work includes the untested GUI/install/security/Ubuntu interaction boundaries, direct Tailscale guest route if required, and 36 architecture exceptions. Evidence for the latest full regression is under .tmp/F10-w33-full-r2-evidence-20261025/; per-machine uninstall evidence is recorded in F05. No commit or push was made, consistent with the project-local workflow rules. The protected D:/Projeler/hpc-client-gui checkout remains untouched.



## 2026-10-25 fix4 per-user installer completion

The exact fix4 per-user installer was installed on Kole Windows11-New, launched in the active interactive session using an isolated config root, closed through the normal window-close path, and uninstalled. Install and uninstall both exited 0. The test verified one HKCU registration and one Start Menu target during install, matching GUI/CLI payload hashes, zero machine registration, absent install path/registration/shortcut after uninstall, and preservation of the isolated config root and profile marker. Evidence and hashes are in reports/F05_WINDOWS_INSTALLER_LIFECYCLE.md and .tmp/F05-peruser-fix4-20261025/.

F05 per-user install/launch/uninstall is now PASS. Per-user/per-machine coexistence and distinct-payload application upgrade/downgrade remain NOT_RUN, so the installer lifecycle wave and final overall verdict remain PARTIAL.


## 2026-10-25 exact fix4 per-user payload upgrade/rollback completion

This supersedes the previous final-report statements that per-user/per-machine coexistence and distinct-payload upgrade/downgrade were all untested. On Kole Windows11-New, the exact fix4 per-user installer SHA-256 `AC67EDDD161B724E7579A00644437FD06AA152384904220FE540B0D2CACCD92B` upgraded an installed 1.5.8 package with a different GUI/CLI payload to 1.5.9, exit 0. The old installer SHA-256 `99FE1155DB83878191CE4CE53DA8F0783DA0D617E2B5294958A4EF34ABCEA2B2` then performed an in-place 1.5.9→1.5.8 downgrade with exit 0; registry and both executable hashes changed back to the recorded 1.5.8 payload. The profile marker stayed identical. The package was restored to 1.5.9 and uninstalled; final guest checks found no test install directory, per-user/per-machine registration, or Start Menu shortcut. Evidence logs/results and `SHA256SUMS.txt` are under `.tmp/F05-v158-different-payload-20261025/evidence/`.

F05 now has a PASS for per-user install/launch/uninstall and distinct-payload upgrade/downgrade. Simultaneous per-user/per-machine coexistence remains NOT_RUN; production signing remains BLOCKED_EXTERNAL. The overall project verdict remains PARTIAL while GUI/Ubuntu/security gates, architecture exceptions, and externally dependent release gates remain open. No commit or push was made.

## 2026-10-25 fix4 simultaneous install coexistence and cleanup

On Kole Windows11-New, the exact fix4 per-user (`AC67EDDD161B724E7579A00644437FD06AA152384904220FE540B0D2CACCD92B`) and per-machine (`C2402DDDA1E34CBE3F1307CF0E917B747183E6CD36116C824DB6D580ECFCABF9`) acceptance installers coexisted at 1.5.9 with separate AppIds, HKCU/HKLM registrations, install paths, and Start Menu shortcuts. Both copies' GUI/CLI payload hashes matched fix4. Removing per-user left the machine copy intact; then machine uninstall completed successfully. Final guest verification found no test registrations, directories, or shortcuts; the isolated marker hash was unchanged. Task-owned UAC launch tasks completed and were removed. Evidence: `.tmp/F05-coexistence-20261025/evidence/`.

F05 now passes per-user install/launch/uninstall, per-user distinct-payload upgrade/downgrade, and simultaneous per-user/per-machine coexistence plus cleanup. Machine-scope distinct-payload upgrade/rollback remains untested, and production code signing remains BLOCKED_EXTERNAL. Overall verdict remains PARTIAL.

## 2026-10-25 latest F05 per-machine payload lifecycle update

The per-machine different-payload case is now exercised on Kole Windows11-New: 1.5.8 machine install → exact fix4 1.5.9 upgrade → 1.5.8 rollback → uninstall. The two installer hashes were verified on the guest; the fail-fast script asserts exact version, install location, and GUI/CLI payload hashes at each install/upgrade/rollback state. Four chronological setup/uninstall logs all contain success records; their local hashes match the guest. Final live checks show no test registrations, install path, or shortcut, and the isolated profile marker remains unchanged. The own scheduled task is gone. Evidence is in `.tmp/F05-machine-payload-20261025/evidence/` and its `SHA256SUMS.txt`.

The detailed lifecycle result JSON was not written; the separate postcheck writer created a malformed 104,769,374-byte file by serializing a provider object. That malformed task-owned temporary file was removed after the sanitized guest summary was verified. A sanitized 2.5 KB guest summary was generated and copied. In addition, a duplicate one-shot trigger caused the same guarded sequence to run twice sequentially; both reached successful logs, and the task was removed. Report the machine-scope installer sequence as exercised with this harness evidence gap; do not claim a fully captured per-step result artifact. This update supersedes earlier statements that machine-scope payload upgrade/rollback were NOT_RUN.

Overall verdict remains **PARTIAL**, not GO. Other open gates remain the current-source real Windows GUI boundary matrix, Ubuntu interactive GUI/editor acceptance, adversarial OS/lifecycle security cases, a verified end-to-end Tailscale path to an HPC guest, unresolved architecture exceptions, and production signing approval. See the wave reports for exact scope and evidence. No commit or push was made.

## 2026-10-25 corrected per-machine lifecycle rerun — PASS

This supersedes the prior F05 harness evidence-gap status. The corrected single-run PowerShell 5.1 harness wrote and hash-verified the full per-step result: on Windows11-New, per-machine 1.5.8 install → exact fix4 1.5.9 upgrade → 1.5.8 payload rollback → uninstall all completed with exit code 0. At each install/upgrade/rollback step, the HKLM version and exact GUI/CLI SHA-256 values were recorded and matched the corresponding old/current payload. Final live verification found no acceptance registrations, install path, or shortcut; the profile marker was unchanged. The task was removed after completion and did not run twice.

The previous missing result was traced to Windows PowerShell 5.1 failing to serialize an empty generic list with `@($steps)`; the harness now serializes `$steps.ToArray()`. Result JSON SHA-256 `9C00C4DFF1D8B24331E7F3F0B8AD7C32A7241E88E8235810D155A2E45888FBA7`; seven-file evidence manifest verified under `.tmp/F05-machine-payload-20261025/evidence/verified-rerun/`. The earlier malformed 104 MB file and first duplicate-trigger execution are historical harness faults; the malformed file was removed, and the corrected run completed once.

F05 machine-scope different-payload lifecycle is **PASS**. Overall verdict remains **PARTIAL** because the remaining Windows/Linux GUI, security, Tailscale route, architecture-debt, and production-signing gates remain open. No commit or push was made.

## 2026-10-26 live localization continuation

Application branch `codex/ansys-journal-studio-host-integration` remains based on `3eb3dc637359b9c1c143d4e418d34b2411c17ac5`, with an uncommitted working tree. The current frozen GUI executable is SHA-256 `770F7A73EB8E7BF28385BE0084084640DC2846B7BD9FC6DC425C20FA418CB959`; package ZIP SHA-256 `87B15F858AB96AFE251CCDD72082CE019FD6189A4D3373A63264D6732CC391C9`. A 1,013-file source manifest is `.tmp/F04-gui-matrix-20261025/evidence/current-source-manifest-20261026.json`, SHA-256 `9201B519A5D5665AB570361190D0386762C286D3CE349D46FD34105E8EB9E7A5`.

On Kole Windows11, current-build GUI PID 8080 in `WINDOWS11\home` session 2 passed the live existing-page English → Turkish → English refresh and Turkish New Journal context/target dialogs; see `reports/F04_WINDOWS_GUI_ACCEPTANCE.md` and `.tmp/F04-gui-matrix-20261025/evidence/`. The focused local Windows11 guest GUI module passed 7/7, including the new language-refresh regression test. Journal save UI displayed “Saved,” but the expected isolated file and its SHA-256 could not be verified; file persistence is not credited.

This is a scoped F04 improvement, not full acceptance. The existing latest results in the wave reports remain scoped to their recorded source snapshots; the new language fix has not yet passed a full application regression. Remaining acceptance includes the broader Windows GUI matrix, current-source Linux interactive GUI, adversarial security gaps, direct Tailscale route to an HPC guest, architecture exceptions, and production signing. Overall verdict remains **PARTIAL**. No commit or push was made.

## 2026-10-26 current-build Windows GUI acceptance correction

This supersedes the previous current-build save statement: the asynchronous New Journal save completed after the earlier premature check. `english-fresh.jou` was recovered from the isolated Kole Windows11 profile, 107 bytes, SHA-256 `4435ADAB4F77B0FD4D8E0A708420521E9CD79E70D27C4BDDA9C1E35A2A2AC04E`; its local evidence copy matches. The document contains only the safe Fluent 2025 R2 starter comments.

The current frozen executable (`770F7A73EB8E7BF28385BE0084084640DC2846B7BD9FC6DC425C20FA418CB959`) also passed real Explorer drops for one `.jou`, two `.jou` files together, ignoring `.txt`, Escape cancellation, dirty-document preservation, and dropping onto the Connection tab outside Studio. The dirty test comment was undone, returning the document to Saved. Kole `WINDOWS11`, session 2, PID 8080 remained responsive; screenshot hashes and adjacent JSON are in `reports/F04_WINDOWS_GUI_ACCEPTANCE.md` and `.tmp/F04-gui-matrix-20261025/evidence/`.

The focused GUI module remains 7/7 PASS. The complete current-source regression is a separate gate and must not inherit the previous fix4/W33 full-suite result. F04 and overall verdict remain **PARTIAL** while current-source full regression and the other listed waves are unresolved.

## 2026-10-26 R6c current-source and architecture update

Application branch `codex/ansys-journal-studio-host-integration`, base HEAD `3eb3dc637359b9c1c143d4e418d34b2411c17ac5`; plugin remote branch remains `codex/ansys-journal-studio-plugin` at `744d1bb556660576eb2597fe0b593ef2acc7e83b`. The corrected R6c app archive SHA-256 is `82744F9CBB16266E88613E883F7D9E24D59A37D4478BBFD36AC0EDD58FA0B9E5`, manifest `54F4280E4068045F0CE20A55C850AE76B4E07EB0C96479EAE53345DBAD71832E`.

| Gate | Latest verified result |
|---|---|
| wx native crash | **PASS** on R6c: no access violation, `Windows fatal exception`, or `UnregisterClass failed`; 3/3 serial broad wx runs passed. |
| Full application regression | **PASS** on R6c / Windows11-New: 4,415 passed, 50 skipped, 29 subtests, 1 warning; exit 0. |
| Jobs outputs test split | **PASS**: 16 focused wx tests passed; 328-line jobs/files module, 278-line follow module, 40-line shared harness. |
| Architecture gate | **PASS**, 883 first-party files; 34 allowlist entries remain (22 independent, 12 protected-checkout overlaps). |
| Tailscale HPC route | Strict SSH ProxyJump through the Tailscale-connected Kole host is the verified access path. Direct guest Tailscale identity/subnet route remains unverified. |
| Live SFTP / Slurm draft | Prior acceptance remains SFTP 19/19 and Slurm 23.11.4 `sbatch --test-only`; no real submission. |
| Windows GUI | **PARTIAL**: selected real GUI actions passed; full boundary matrix remains open. |
| Windows installers | Prior fix4 per-user/per-machine lifecycle evidence remains scoped to those packages. Current exact R6c installer/UAC acceptance is not established. Production signing remains blocked on a valid certificate and approved signing operation. |
| Ubuntu-Test | Current-source package lifecycle smoke passed; interactive Studio/editor GUI handoff remains unverified. |
| Security | Automated current-source Windows/Linux selections passed; OS fault injection, resource exhaustion and dirty-journal UI cases remain open. |
| Fluent | Journal creation/edit/lint/Slurm draft scope is covered. Solver/case/mesh solve remains NOT_RUN. |

R6c evidence (result JSON, complete logs, wheel, source ZIP/manifest and `SHA256SUMS.txt`) is under `.tmp/F08-jobs-outputs-20261026/evidence/r6c/`. The earlier R6 diagnostic run is not combined with R6c; it exposed a stale allowlist entry and two lost wx markers, both corrected before R6c.

Final verdict remains **PARTIAL**, not GO. Remaining work is the full real GUI and current exact installer acceptance, remaining Ubuntu/security cases, reducing the remaining 34 architecture exceptions without touching the protected checkout, and production signing. The user checkout `D:\Projeler\hpc-client-gui` remains untouched. No commit or push was performed under the project-local workflow rule; no production release, real Slurm submission or Fluent solver job was performed.

## 2026-10-26 R6c portable GUI continuation — Kole Windows11-New

At the user's direction, this acceptance used the current frozen onedir portable package directly from an isolated temporary directory. No installer or UAC prompt was run. The guest was Windows11-New, `WINDOWS11-NEW\home`, interactive session 1. App PID 20108 ran from `C:\Users\home\AppData\Local\Temp\AJSF04\r6c-ui-20261026\package\hpc-client-gui.exe` from 2026-10-26 02:37:12Z through graceful main-window close at 03:00:05Z. `CloseMainWindow()` returned true and the process exited; an exit code was not captured.

The executable SHA-256 is `770F7A73EB8E7BF28385BE0084084640DC2846B7BD9FC6DC425C20FA418CB959`, package ZIP SHA-256 `87B15F858AB96AFE251CCDD72082CE019FD6189A4D3373A63264D6732CC391C9`, and GUI build manifest SHA-256 `9201B519A5D5665AB570361190D0386762C286D3CE349D46FD34105E8EB9E7A5`. A comparison of the 473 app/build source paths between the R6c source and the frozen build found 0 differences. Isolated test catalog SHA-256 is `C995898D3524060EDBAA359C24932C8D68760349CA8FD6F97432E7C9C5D1BD52`.

Observed PASS cases: Studio opened from Plugin Manager; a 10,020-line journal remained usable in source mode while the app clearly reported Visual Flow/highlighting pause at the threshold; two journal tabs opened and switched; Undo/Redo restored the expected Saved/Modified states; plugin install, enable, disable, uninstall, and reinstall completed while an edited journal stayed open; Studio remained responsive; journal fixture hashes were unchanged and the final document state was Saved. This is selected GUI acceptance, not the whole F04 matrix. No newer plugin version was present, so plugin update was NOT_RUN. Corrupt Scheme, SFTP disconnect, disk-full, invalid encoding, theme/DPI, and this-run OS drag/drop variants were not exercised.

Evidence package: `.tmp/F04-gui-matrix-20261025/evidence/r6c-ui-20261026/`. The package contains 106 files listed in `SHA256SUMS.txt`; all 106 hashes matched, with no missing/extra entries. The 32 JSON records parsed; 31 screenshot hash references resolved with no mismatch. The test-owned completed scheduled task was removed. F04 and F07 addenda record their scoped outcomes. Overall verdict remains **PARTIAL**. No commit or push was made.
## 2026-10-26 normal-mode test-catalog isolation

R6c portable Windows11-New GUI check: test catalog path was set, `HPC_GUI_TEST_MODE` was unset, and a fresh isolated config root was used. The Plugin Manager displayed the online production entries `ANSYS Fluent Tools` and `TRUBA`; the test-only ANSYS Journal Studio 0.1.0 entry in registry SHA-256 `72355DC01DB5F226AEE46DE7FA454B659EC767620759A42C340FC16A311B4D77` was absent. **PASS for this scope only.** Screenshot SHA-256 `10A47F396374D1AA4CC56E52C06829DA610659462E3A9B534A95E822F6145813`; evidence JSON and registry snapshot are in `.tmp/F04-gui-matrix-20261025/evidence/`. The probe's app process exited via graceful window-close (exit code not captured); both owned scheduled tasks were removed. No plugin install or profile mutation occurred. Overall verdict remains **PARTIAL**.
