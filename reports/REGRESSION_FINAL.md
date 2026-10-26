# Regression Final

Date: 2026-10-23

Application branch: codex/ansys-journal-studio-host-integration
Application source commit: 1cec0471e3daf50a16ba4161282aff2260ba9dd9
Plugin branch: codex/ansys-journal-studio-plugin
Plugin commit: 744d1bb556660576eb2597fe0b593ef2acc7e83b

## Results

| Check | Result |
|---|---|
| Application focused pytest run | 1,017 passed, 22 skipped |
| Current SSH jump-host boundary | 24 passed |
| Current large-journal boundary | 6 passed |
| Version and packaged-content boundary | 20 passed |
| Plugin repository pytest | 192 passed |
| Plugin registry validation | PASS |
| Ruff on app and plugin | PASS |
| i18n consistency | PASS |
| 500-line architecture check | PASS; 42 allowlisted over-limit entries remain |
| Windows package content | PASS, 8/8 checks |
| Live SFTP | PASS, 19/19 on current source, using existing lab path |
| Slurm test-only | PASS; no job submission |
| Current Windows11 per-user installer install/uninstall | PASS |

Test counts are independent suites and must not be added together as a unique-test total. The broad app pytest run separately terminated with Windows wx native access violation -1073740771 at tests/test_editor_flow.py:281. That test passed in isolation. The 1,017/22 focused run is retained as its own result; the changed SSH and large-journal boundaries were tested on the final source separately.

The PyInstaller package-content report identifies application source commit 1cec0471e3daf50a16ba4161282aff2260ba9dd9 and passed all eight content checks. Packaged GUI EXE SHA-256: 33469798a48ee53ce0e3ce0939cb0715c479271561ab3a8e43b3276049149a24. The embedded plugin hash is unknown because plugins are separately installed.

This is not a complete cross-platform or release regression: current-source GUI drag/drop and persistence, the full hostile security matrix, current per-machine installer lifecycle, plugin lifecycle in the guest, and Tailscale-routed VM tests remain outstanding.

Detailed snapshots: evidence/ in the handoff ZIP. Raw credential-bearing material was not collected.

## 2026-10-25 latest complete Windows regression snapshot

The latest full Windows11-New application regression completed on source manifest SHA-256 `b0d9e1d53088e71a244e60e2f6dc713633dcadc633eb145d87750225b69714db`, application base commit `3eb3dc637359b9c1c143d4e418d34b2411c17ac5`, Python 3.14.7, interactive `home` session. Result: **4,412 passed, 50 skipped, 29 subtests passed, 1 warning**, exit 0 in 951.04 seconds. Log SHA-256: `A02712049B3075B55CABF0D7FE7775D6D9FCBD6EE46C1445550956B486704C64`. No native access violation or wx `UnregisterClass` failure occurred. This replaces the earlier broad-run crash status for that manifest; the exact newer fix4 archive `642e080d…` still requires its own full regression.

The three broad wx repeats on that same source each completed **725 passed, 1 skipped**, with no crash. The current-source fix4 GUI drag/drop evidence is recorded in `reports/F04_WINDOWS_GUI_ACCEPTANCE.md`; it is a focused 6-test run and is not a full-regression result.

## 2026-10-25 fix4 exact-source VM regression addendum

Exact fix4 source ZIP `642e080dae9254ecfcac658da83f9a658e3029b1acee3c3a29fa5be3e90579c7` (manifest `e8914da550dc8792502d1ca8b79f0a074503c9c5b39b783365eeac45f81a25d3`) completed a full regression on Kole `Windows11-New`: **4,414 passed, 50 skipped, 29 subtests passed**, exit 0. Three broad wx repeats each passed **725 tests, 1 skipped**. The per-machine fix4 installation and isolated Plugin Manager lifecycle also completed after the operator accepted UAC and the license pages; see F05.

The same source full suite ran on the local Hyper-V `Windows11` VM. It completed **4,411 passed, 50 skipped, 29 subtests passed, 3 failed**, exit 1. The three failures were plugin catalog tests whose temporary fixture paths exceeded Windows' path limit beneath the canonical runner's deep `CodexGuestRuns` staging directory. The exact three test node IDs passed together (3/3) when rerun from `C:\Users\home\x\<run-id>`. Preserve the local full-suite result as a harness path limitation; do not combine it with the independent Kole counts or call it a full-suite PASS. No native wx crash occurred in the completed local process.

Overall acceptance remains **PARTIAL**: GUI boundary variants, full app payload installer upgrade/rollback/uninstall and cross-install data checks, Ubuntu interactive Journal Studio workflow, adversarial VM security cases, and 37 architecture exceptions remain open. Production signing remains externally blocked. No commit or push was made.

## 2026-10-26 R5 current-source continuation

R5 source ZIP SHA-256 `A27B1970D19123A181523AB969AAAB3AF795FC419A8B481110E86B43D529B19C`; manifest SHA-256 `65E83A5E713E129F4BDFA2623476B07C740AD280AB4B3880E85174CEB3D414F3`; app base commit `3eb3dc637359b9c1c143d4e418d34b2411c17ac5`. Kole Windows11-New, Python 3.14.7: full app pytest **4,415 passed, 50 skipped, 29 subtests, 1 warning**, exit 0. Three clean broad wx processes each passed **725 passed, 1 skipped, 3,739 deselected**, exit 0. W19 teardown focused tests passed **13/13**; SSH credential focus passed **21/21**. No native access violation or wx class-unregister marker appeared.

Ruff, compileall, i18n, official registry smoke, wheel build, and the architecture gate passed. The line-limit gate has 35 allowlisted files (23 independent; 12 protected-checkout overlaps). Current-source SFTP and Slurm test-only remain separate successful suites. Current per-machine payload install/uninstall passed in an isolated test identity; exact R5 product installer and real UAC consent are still open. See F01, F05, and F10 for details and artifact hashes. Historical suite counts remain separate and are not added together.

Overall verdict: **PARTIAL**. GUI boundary cases, current exact product installer/UAC, remaining Ubuntu GUI handoff and VM security cases, 23 independent architecture exceptions, and production signing remain open. No commit, push, production release, Slurm submission, or solver job was performed.

## 2026-10-26 R6c corrected current-source regression

The final R6c app ZIP is `82744F9CBB16266E88613E883F7D9E24D59A37D4478BBFD36AC0EDD58FA0B9E5`, manifest `54F4280E4068045F0CE20A55C850AE76B4E07EB0C96479EAE53345DBAD71832E`, based on app HEAD `3eb3dc637359b9c1c143d4e418d34b2411c17ac5`. On Kole Windows11-New (`WINDOWS11-NEW\home`, Session 1, Python 3.14.7), the 16-test Jobs split focus passed, full pytest passed **4,415 passed, 50 skipped, 29 subtests**, and three serial broad wx runs each passed **725 passed, 1 skipped, 3,739 deselected**. All exits were 0; no native crash marker appeared. See `reports/F01_WX_NATIVE_CRASH_FIX.md`, `reports/F08_ARCHITECTURE_DEBT.md`, and `reports/F10_FULL_REGRESSION.md` for per-run hashes and evidence.

The line-limit gate passes with 34 allowlisted exceptions (22 independent plus 12 protected-checkout overlaps). The wx lifecycle/full test gates are closed for this exact snapshot. Overall verdict remains **PARTIAL**: the requested full Windows GUI boundary matrix, exact current-product installer/UAC acceptance, remaining Ubuntu GUI workflow, adversarial VM security cases, remaining architecture exceptions, and production signing remain open. The exact R6 initial run was not accepted because of stale allowlist metadata and two dropped test markers; R6c fixes both. No commit or push was made, and the protected checkout remains untouched.

## 2026-10-26 F08-R5 current-source overlay regression

R5 layered R6c base ZIP `82744F9CBB16266E88613E883F7D9E24D59A37D4478BBFD36AC0EDD58FA0B9E5` with updater test overlay `DA7626C340DED767EFE5C877B08E2D443AC23433D17E51870E18F505853CDEC1`, updater source extraction overlay `D448B53E37A262559C4987F22A3034DE9D7ACECBFC1D89AEEC2AEA1AA3A21E9E`, and SSH jump-host profile split overlay `20C7E0F4F112F9F1D2320EE8E07B3D0F6AC81076A9C0A144EDA5BEA9C0A797BD`. On Kole Windows11-New, Python 3.14.7, normal interactive `home` Session 1, wheel build and full pytest passed: **4,415 passed, 50 skipped, 29 subtests, 1 warning**, exit 0. There were no native crash markers and pytest stderr was empty. Wheel SHA-256 `76C11ABF892183DD162AB9344473E10FD165766F6FA7F738937C337A54671FCA`; stdout SHA-256 `5505FB0BD4389390C7CF117E8AC2E0725A9C4953F1759E0471FBBC096F448921`; result JSON SHA-256 `96F955693E747CC74382990A7F41ACDB24518D016D88E1EB218974F80307C6B8`.

The updater extraction focus passed 21/21. SSH jump-host module baseline and post-split focused run each passed 24/24. The current line-limit gate passes at 893 first-party files with 29 exceptions (17 independent and 12 protected-checkout overlaps). These independent results are not added into the full regression count. Updated wave reports and exact logs are preserved under `reports/` and `.tmp/F08-jobs-scroll-20261026/evidence/`. Overall verdict remains **PARTIAL** because real GUI boundary rows, Ubuntu desktop Jobs handoff, adversarial VM security cases, remaining architecture exceptions, and production signing approval are open.
