# UPDATE-07 report — cross-platform acceptance and rollout

Status: PARTIAL ROLLOUT PREPARATION; production rollout is not complete.

## Acceptance matrix

| Capability | Mock/local evidence | Packaged smoke | Real N→N+1 | Result |
| --- | --- | --- | --- | --- |
| Windows updater regression | Existing updater tests pass | Not run here | Not run here | PASS for local regression |
| Source/manual | Installation detection and manual routing | Not applicable | Not applicable | PASS |
| DEB / Ubuntu | PackageKit probe and secure staging tests | Not available | Not available | BLOCKED |
| AppImage | Staging/replacement and recovery tests | Not available | Not available | BLOCKED |
| Flatpak delegation | App ID/origin handoff test | Not available | Not available | BLOCKED |
| macOS Intel | Existing packaging tests only | No macOS runtime | Not available | BLOCKED |
| macOS Apple Silicon | Existing packaging tests only | No macOS runtime | Not available | BLOCKED |

## Checks performed

- Updater/verification/DEB/AppImage focused tests: `17 passed, 2 skipped`.
- macOS release/packaging regression tests: `38 passed`.
- Ruff and `git diff --check`: passed.
- No real package installation, feed publication, release upload, signing, or external update was performed.

The two skipped tests require symlink creation unavailable on this Windows host. Mock tests are not treated as proof of Linux/macOS package behavior.

## Rollout checklist

1. Owner supplies and reviews production update signing keys, key rotation/recovery policy, immutable metadata hosting, and release feed URLs.
2. Run disposable Ubuntu DEB N→N+1 with PackageKit authorization, cancellation, active-work deferral, normal-user relaunch, and version reconciliation.
3. Run disposable Linux AppImage replacement/recovery and Flatpak scope/remote tests.
4. Run packaged macOS Intel and Apple Silicon Sparkle feasibility tests; UPDATE-04 is currently blocked, so UPDATE-05 cannot be approved.
5. Keep Mac assisted/manual while its gate is blocked. Do not publish a claim that all platforms update automatically.
6. After all applicable gates pass, obtain owner approval, then publish immutable artifacts and metadata/feed last.

No production feed or release was modified by this work. Remote Slurm jobs and saved profiles/credentials are not touched by the update helpers.
