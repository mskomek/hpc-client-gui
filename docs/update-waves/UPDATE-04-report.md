# UPDATE-04 report — macOS Sparkle feasibility

Status: BLOCKED / no-go for a production Sparkle integration in this environment.

## Inspection

The current macOS path publishes architecture-specific DMGs, checksum files, `RELEASE_SECURITY.json`, and a validated PyInstaller bundle. The application updater still routes non-Windows installations to manual handoff. No Sparkle framework, native bridge, Sparkle feed, or packaged Sparkle helper is present.

The existing assisted path discloses macOS security metadata and opens the selected release URL only after user interaction; opening a DMG is not treated as a successful installation.

## Verification

- `python -m pytest -q tests/test_macos_release.py tests/test_macos_release_workflow.py tests/test_macos_packaging_spec.py tests/test_macos_docs.py tests/test_app_updater.py` — 38 passed.
- Ruff on the current updater/verification changes — passed.
- `git diff --check` — passed.

No macOS application was launched, no Sparkle binary was downloaded, no feed was contacted, and no signing/notarization action was performed.

## Blockers

- No macOS Intel or Apple Silicon runtime is available for a real packaged proof.
- No owner-approved Sparkle version, feed URL, update signing key, or native bridge implementation has been validated.
- Developer ID/notarization credentials are unavailable and must not be invented or logged.

Therefore the required real packaged check UI, delegate lifecycle, install-later behavior, architecture feeds, nested signing inventory, and N-to-N+1 update cannot be claimed. The current manual DMG path remains unchanged and safe.

Next prerequisite: provide isolated macOS arm64/x86_64 build/runtime access and owner-approved Sparkle signing/feed inputs before considering UPDATE-04 GO. UPDATE-05 must not start as a production implementation from this BLOCKED result.
