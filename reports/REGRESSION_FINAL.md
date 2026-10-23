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
