# UPDATE-03 report — Ubuntu/Debian DEB updates

Status: BLOCKED for real package installation acceptance; safe unprivileged handoff primitives are implemented and tested.

## Changes

- Added a bounded `pkcon get-actions` capability probe that distinguishes missing PackageKit, command/reporting failure, and unsupported `install-local` support.
- Added private, non-predictable DEB staging under the per-user update directory. Staging rejects symlinks, uses a regular `.deb` file, copies bytes, flushes, and fsyncs the result.
- Added an argument-list-only `pkcon install-local <path>` handoff builder. Administrator authorization remains entirely with the operating system; no password, polkit rule, sudo configuration, or package-manager lock is touched.
- No real transaction was started and no package was installed.

## Verification

- `python -m pytest -q tests/test_deb_installer.py tests/test_update_verification.py tests/test_app_updater.py` — 14 passed, 1 skipped.
- Ruff on changed installer/verification/updater files — passed.
- `git diff --check` — passed.

The skipped test requires creating a symlink; this Windows host does not grant that privilege. It is a test-environment limitation, not a production fallback.

## Acceptance blocker

The required disposable Ubuntu desktop/VM with PackageKit backend and authentication agent is unavailable in this environment. Therefore N-to-N+1 DEB installation, authorization cancellation, transaction progress/failure, normal-user relaunch, post-install package verification, and safe shutdown during replacement remain unverified. This wave must not be reported as production-verified.

Next prerequisite: provide the disposable Ubuntu acceptance environment, then continue with UPDATE-04 only after this BLOCKED result is reviewed and the DEB handoff is integrated into the UI coordinator.
