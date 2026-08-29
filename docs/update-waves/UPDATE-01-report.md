# UPDATE-01 report — shared foundation and installation detection

Status: PASS for the shared, unprivileged foundation; real packaged Linux/macOS acceptance remains pending for later waves.

Inspected commit: `HEAD` at implementation start (`codex/update-01-shared-foundation`).

## Changes

- Added `InstallationContext` and evidence-based installation detection.
- Linux detection checks Flatpak identity, the actual AppImage runtime path, and `dpkg-query` package ownership/metadata. A Linux path or `/usr/lib` location alone is not treated as a DEB installation.
- macOS bundle detection reads `Contents/Info.plist` and records bundle identity/version when available.
- Windows frozen execution retains the existing Windows updater capability.
- Source and unknown installations remain manual-only with an actionable reason.
- Updater release routing now consumes the detected capability instead of guessing from the operating system.

No privileged installation, package-manager mutation, download, publication, or external service was performed.

## Verification

- `python -m pytest -q tests/test_app_updater.py` — 9 passed.
- `python -m ruff check src/hpc_gui/services/installation_context.py src/hpc_gui/services/app_updater.py tests/test_app_updater.py` — passed.
- `git diff --check` — passed.

The tests mock/construct installation evidence and do not prove a real DEB/AppImage/Flatpak/macOS packaged upgrade. This Windows development environment cannot provide that evidence.

## Risks and follow-up

- Linux DEB ownership is intentionally manual-only until UPDATE-03 supplies a verified installer path.
- AppImage replacement, Flatpak delegation, Sparkle, signatures, and production feeds are not implemented in this wave.
- Rosetta architecture selection and mounted/translocated macOS edge cases need the UPDATE-04 acceptance work.

Next prerequisite: review and accept UPDATE-01, then implement UPDATE-02 verification/publication contract.
