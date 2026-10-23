# Windows Installer Acceptance

Date: 2026-10-23

## Result

Status: PARTIAL. Current-source per-user install/uninstall passed on Windows11. Formal installer lifecycle and signed production acceptance are incomplete.

The current-source per-user acceptance installer was built from application commit 1cec0471e3daf50a16ba4161282aff2260ba9dd9. Artifact SHA-256: 358f9a471d815ec100ee83454195dd36ab103bcca2bbbd0dab774ea6802cbdcb. Size: 31,837,495 bytes. Authenticode status: NotSigned.

The canonical Windows11 interactive runner verified the active test\home Explorer session, staged and hash-checked this exact artifact, and launched its silent per-user install. The recorded verification found the expected Apps & Features registration, install directory, GUI/CLI files, and Start Menu shortcut. Silent uninstall returned exit code 0; the uninstall registration and install directory were gone afterward. A separate test sentinel under the test profile remained present. Runner ID: 2f91db1322024f81ade008977f733540.

An older acceptance artifact was used for a per-machine install/uninstall and preserved the separate per-user registration. Older tests also covered same-version reinstall and uninstall. An older 1.5.10 “upgrade” changed installer metadata while carrying the same 1.5.9 application payload; it is not valid application-upgrade evidence.

The current per-machine artifact was built and hash-checked but was not installed in the VM. The current-source test did not launch the app GUI or exercise plugin install/update/rollback, application upgrade/downgrade, repair, close-running-app behavior, or clean reinstall lifecycle. The current package used a test identity and did not replace a real installation.

## Artifacts

| Artifact | SHA-256 | Authenticode |
|---|---|---|
| Current per-user 1.5.9 acceptance EXE | 358f9a471d815ec100ee83454195dd36ab103bcca2bbbd0dab774ea6802cbdcb | NotSigned |
| Current per-machine 1.5.9 acceptance EXE | 06b0611414f1c173357c88d0baeb1e6cad39aec04d1ae621c1990c6e00ddc733 | NotSigned |

The unsigned packages are test artifacts only. A real signing certificate and owner-controlled release signing process are required before signed production acceptance. No public release was published.
