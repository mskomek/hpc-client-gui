# Windows Installer Acceptance

Date: 2026-10-23

## Result

Status: **PARTIAL**. The current-source per-user install/uninstall passed on Windows11. The current-source per-machine package was installed in the isolated Windows11 guest and its GUI and plugin install/update/rollback/disable/enable/uninstall/reinstall paths passed. Application upgrade/downgrade, UAC consent, repair, and production signing remain unverified.

## Per-user acceptance

The current-source per-user acceptance installer was built from application commit `1cec0471e3daf50a16ba4161282aff2260ba9dd9`. Artifact SHA-256: `358f9a471d815ec100ee83454195dd36ab103bcca2bbbd0dab774ea6802cbdcb`. Authenticode status: `NotSigned`.

The canonical Windows11 interactive runner verified the active `test\\home` Explorer session, staged and hash-checked this artifact, then ran silent per-user installation. Apps & Features registration, install directory, GUI/CLI files, and Start Menu shortcut were present. Silent uninstall returned exit code 0; the registration and install directory were removed and a separate profile sentinel remained. Runner ID: `2f91db1322024f81ade008977f733540`.

## Current per-machine acceptance

Artifact SHA-256: `2ee9af42007d89818076738c1a9e7e0a01e58f61944ea1cf1b244b1f397e41d8`; size 31,842,431 bytes; Authenticode `NotSigned`. It installs the test-identity product `HPC Client GUI Machine Acceptance` with product code `{C78C4C38-6D59-4429-8F66-6DFD3CB33D7A}`. The packaged GUI SHA-256 is `b79c0e58af4735d425e89bafa7cb48c40a5e194d223d283fbcddbdbd158d79df`; the CLI SHA-256 is `911d1a22da2b497ab44fbcf8b2f9b4fe2d8ba37a088d53cb363fa45d02ed1b10`.

The canonical Windows11 runner installed it into `C:\\Program Files\\HPC Client GUI Machine Acceptance` using a high-integrity PowerShell Direct process. The executable hash matched the staged artifact payload. The expected HKLM uninstall registration, uninstaller, and Start Menu shortcut were present; the isolated profile had no pre-existing data. This verifies the elevated install operation, but no interactive UAC consent prompt was observed.

The installed GUI was launched in Explorer session 2 under `test\\home`; the main window and Plugin Manager were visible. The terminal WebView startup still reports `E_ABORT` in the separate F04 packaged-smoke path. The core window and Plugin Manager remained usable for the following real UI acceptance. Evidence and screenshots are under `.tmp/f05-machine-installer-runner/`.

An explicit local-only test catalog was enabled in the isolated acceptance profile with `HPC_GUI_TEST_MODE=1` and `HPC_GUI_PLUGIN_TEST_CATALOG`. The GUI displayed the `TEST CATALOG` warning. The production registry URL/policy were not changed and the test catalog made no network requests. The following Plugin Manager actions passed against the current plugin package and locally staged update payloads:

| Operation | Observed result |
|---|---|
| Install Journal Studio 0.1.0 | Success modal; active and installed manifest hash matched `200edc60bf710918b86526875254f69c9179c2f6f5733ce0ae26864d5c1f9f0a` |
| Discover 0.1.1 local update | Updates row reported active 0.1.0 and update available |
| Update to 0.1.1 | Success modal; active manifest matched `83f6a31575e4acd677e52772057907117aef31ccec72e373dbb094ad490b893d`; test marker was present |
| Roll back to 0.1.0 | GUI confirmation accepted; `active.json` returned to 0.1.0 |
| Update to 0.1.1 again | Success modal and active manifest verified |
| Disable / enable | `disabled.json` contained then removed the plugin ID |
| Uninstall plugin | `active.json` emptied and installed package directory was removed |
| Reinstall plugin | 0.1.1 installed and active manifest verified |

The real UI automation helper SHA-256 was `47d07dee9fb444db0eef008f0780e3ee6d8f8b82ffd395b5d210b9f3ab8db64a`. Its runner, state, catalog, and image evidence is retained in `.tmp/f05-machine-installer-runner/`. Screenshots include `test-catalog-manager.png` and `lean-update.png`.

## Remaining installer lifecycle

An older acceptance artifact covered per-machine install/uninstall and preserved the separate per-user registration. Older tests also covered same-version reinstall and uninstall. An older 1.5.10 “upgrade” changed installer metadata while carrying the same 1.5.9 application payload; it is not valid application-upgrade evidence.

The current per-machine VM test did **not** verify an application upgrade/downgrade with a genuinely different application payload, repair, interactive UAC consent, close-running-app behavior, a clean reinstall after application removal, or profile-data behavior after application uninstall. The test app and isolated test profile are not a production installation. Those lifecycle steps remain `NOT_RUN`.

| Artifact | SHA-256 | Authenticode |
|---|---|---|
| Current per-user 1.5.9 acceptance EXE | `358f9a471d815ec100ee83454195dd36ab103bcca2bbbd0dab774ea6802cbdcb` | NotSigned |
| Current per-machine 1.5.9 acceptance EXE | `2ee9af42007d89818076738c1a9e7e0a01e58f61944ea1cf1b244b1f397e41d8` | NotSigned |

The unsigned packages are test artifacts only. A valid code-signing certificate and owner-controlled signing process are required for production signing acceptance. No production release was published.

## 2026-10-26 R5 machine payload follow-up

A current-source per-machine acceptance package with isolated product identity was installed and removed on Kole Windows11-New. It used the exact R5 GUI and CLI payload hashes, passed HKLM/Start Menu/uninstaller checks, and preserved the pre-existing user-scope Machine Acceptance installation and the test profile marker. Evidence: `.tmp/F05-current-machine-20261026/evidence/r5-isolated/`.

The actual R5 product installer (`30919CE5C36C6D7398580E9DFDE0E280BB855D287C4F851A4284A70C34F65220`) was not run because Windows11-New already has that product identity installed in HKCU and several test GUI processes were open. The first isolated run found UAC consent policy values 0/0, so it did not display a prompt. A second isolated attempt observed `consent.exe` in Session 1 but exited with task result 1 before elevation; no test product was installed. UAC consent is **NOT_VERIFIED**. The original policy values (1/0/0) were restored and the task was removed. Evidence status SHA-256: `7B8429CCF85AD1E323421DB4C8D78CA0401795208B55B187662C8F3E93A18A91`; see the R5 evidence directory. Production signing remains **BLOCKED_EXTERNAL**; no release was published.
