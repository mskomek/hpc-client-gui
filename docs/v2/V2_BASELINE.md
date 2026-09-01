# V2 Baseline — Wave 00

This document freezes the current `develop` state as the reference for later
waves. Published provider and plugin version directories are immutable.

## Source revisions

Captured 2026-09-01 (Europe/Istanbul):

| Repository | develop | origin/main | origin/develop | working tree |
|---|---|---|---|---|
| `hpc-client-gui` | `21a5fac03e09d72363834328f1edd8a57da4368c` | `063d83b523be377d4ef02dc8a61e2fdd15876ecc` | `938e68b81431bb57a725c5e6ac935c0d87e25c38` | dirty: pre-existing untracked `.tmp/` |
| `hpc-client-gui-plugins` | `4e79325873a3eda232071339b367722ccacbb8f8` | `a320cde6affe9072523a49352b2d688e050168b3` | `4e79325873a3eda232071339b367722ccacbb8f8` | dirty: pre-existing untracked `.github/social-preview.jpg` |

The application version is `1.5.8`. The consumer contract pin is official
registry release `hpc-client-gui-plugins v1.0.0`, commit
`c893861fdba3573a756588cedfb2521ae81bd226`.

## Release surface

Supported packaged targets are Windows 10/11 x86_64 portable ZIP, macOS 13+
Apple Silicon and Intel DMGs, and Linux x86_64 AppImage or Debian `.deb`.
Flatpak is optional; there is no ARM64 Linux build. Source use requires Python
3.14.x. The user experience is Windows-first; Slurm parsing varies with site
customization, and X11 responsiveness depends on network quality.

Current registry entries:

- Cluster profiles: TRUBA `1.3.0` (also immutable `1.0.0`–`1.2.0`), LUMI
  `1.0.0`, NERSC Perlmutter `1.0.0`, Pawsey Setonix `1.0.0`, and TACC
  Stampede3 `1.0.0`, plus CINECA Leonardo `1.0.0`.
- ANSYS Fluent tools `0.2.0` (and immutable `0.1.0`).
- ANSYS Script & Journal Linter `0.1.0` (Plugin API v2 marker).

The linter documents Fluent packs `24.2`, `25.1`, `25.2` (2025 R2 default),
and `26.1`; supported dialects include Fluent, MAPDL, Workbench, CCL, ICEM,
System Coupling, DesignModeler, Mechanical, SpaceClaim, AEDT, and Motion.
The application remains provider-neutral and retains the Generic Slurm path.

## Test evidence

Commands run from each repository root:

| Repository | Command | Result |
|---|---|---|
| `hpc-client-gui` | `python -m pytest -q` | **1243 passed, 20 skipped, 29 subtests passed** in 123.01s |
| `hpc-client-gui-plugins` | `python -m pytest -q` | **153 passed** in 3.12s |

Application test coverage map:

| Area | Existing evidence |
|---|---|
| SSH / SFTP | `test_slurm_ssh.py`, `test_ssh_*`, `test_sftp_*`, `test_mock_cluster_roundtrip.py` |
| Profiles / providers / quota | `test_profile_*`, `test_provider_*`, `test_*quota*`, `test_plugin_*` |
| Jobs / transfers | `test_job_*`, `test_transfer_*`, `test_ftp_widget.py`, `test_download_*`, `test_upload_*` |
| Editor / ANSYS | `test_editor_*`, `test_fluent_plugin_integration.py`, `test_linter_tools_v2.py`, `test_job_context.py` |
| Plugin Manager / security | `test_plugin_manager_ui.py`, `test_plugin_installer.py`, `test_plugin_integrity.py`, `test_plugin_security.py` |
| Updater / diagnostics | `test_app_updater.py`, `test_update_verification.py`, `test_updater_helper.py`, `test_diagnostics.py`, `test_wave37_diagnostics.py` |

Plugin test coverage includes registry/schema validation, provider profiles,
TRUBA, ANSYS lint engine and fixtures, compatibility, documentation, and
template payloads.

## Behavior classification

| Current behavior or inconsistency | Classification |
|---|---|
| Generic Slurm, TRUBA, provider, quota, SSH/SFTP, jobs, transfer, editor, ANSYS Trusted Tool, Plugin Manager, updater, and diagnostics behavior | PRESERVE |
| Published plugin/provider version directories and their hashes | PRESERVE / IMMUTABLE |
| Password, MFA, private-key, secret-blob, and unsanitized environment data are not logged/exported | PRESERVE |
| X11 password-only limitations, site-specific Slurm parsing, and Windows-first UX | PRESERVE |
| `docs/wiki/Compatibility-and-Support-Matrix.md` still says current version `1.2.6` while the application is `1.5.8` | UNKNOWN; reconcile in documentation maintenance before relying on that marker |
| No intentional product behavior changes in Wave 00 | INTENTIONALLY_CHANGE: none |
| No behavior removed in Wave 00 | REMOVE: none |

## Handoff

Wave 00 adds no feature work and no plugin-format redesign. Later waves should
cite this file, preserve the recorded revisions and immutable published
versions, and update the baseline only through an explicitly authorized new
baseline wave.
