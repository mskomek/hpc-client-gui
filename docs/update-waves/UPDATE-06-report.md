# UPDATE-06 report — AppImage and Flatpak routing

Status: BLOCKED for real Linux N-to-N+1 acceptance; local handoff primitives are implemented and tested.

## Changes

- Added AppImage runtime-path validation that rejects missing and symlinked `APPIMAGE` values.
- Added same-filesystem AppImage staging with a random temporary name, byte flush/fsync, and preserved executable permissions.
- Added atomic replacement with a retained `.previous` recovery copy; no candidate is executed before verification and no automatic rollback loop is introduced.
- Added Flatpak app ID/origin probing and an explicit external `flatpak update --app <id>` handoff command. The application does not add remotes, keys, or deployments.

## Verification

- `python -m pytest -q tests/test_linux_update_handoff.py tests/test_deb_installer.py tests/test_update_verification.py tests/test_app_updater.py` — 17 passed, 2 skipped.
- Ruff on changed Linux updater/verification files — passed.
- `git diff --check` — passed.

Skipped checks require symlink creation, unavailable on this Windows host.

## Acceptance blocker

No disposable Linux desktop with AppImage runtime, Flatpak installation scopes/remotes, and N-to-N+1 update fixtures is available. Real destination permissions, disk-full/rename failures, coordinator survival after shutdown/unmount, launch acknowledgement/recovery, Flatpak remote-backed update, and external handoff reconciliation remain unverified. This wave is not production-verified.

UPDATE-05 remains blocked by UPDATE-04’s missing macOS runtime and signing inputs. UPDATE-07 must therefore report a partial rollout with explicit BLOCKED entries.
