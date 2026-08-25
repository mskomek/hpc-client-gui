# Installation on macOS

HPC Client GUI macOS packages are distributed outside the Mac App Store as
DMG files. macOS 13 or newer is required.

## Signed or unsigned?

Every release publishes a `RELEASE_SECURITY.json` asset that states exactly
what happened to the DMGs:

- `macos_mode: "signed-notarized"` — both DMGs were Developer ID signed,
  notarized, stapled, checksum verified, and passed a Gatekeeper assessment.
- `macos_mode: "unsigned"` — Apple signing credentials were not used. The
  app is **not** Developer ID signed or notarized; Gatekeeper may block the
  first launch (see below). SHA-256 checksums and GitHub build provenance
  attest integrity and origin but are **not** substitutes for Apple code
  signing.

If the metadata asset is missing, treat the build as unsigned.

## Choose the correct DMG

- Apple Silicon (M1/M2/M3/M4): `hpc-client-gui_macos_arm64.dmg`
- Intel: `hpc-client-gui_macos_x86_64.dmg`

Do not use the other architecture's package. Each DMG has a sibling `.sha256`
file and the release includes a `MANIFEST.json` inventory.

## Install

1. Download the matching DMG from [GitHub Releases](https://github.com/mskomek/hpc-client-gui/releases/latest).
2. Verify the SHA-256 file if desired.
3. Open the DMG.
4. Drag **HPC Client GUI.app** to **Applications**.
5. Launch it from Finder.

### If Gatekeeper blocks the first launch

1. Try opening the app normally first.
2. If macOS reports that the app cannot be verified, control-click
   (right-click) the app in Finder and choose **Open**, then confirm, or use
   **System Settings → Privacy & Security → Open Anyway**.
3. Do not disable Gatekeeper globally and do not make quarantine-stripping
   (`xattr`) commands part of your normal installation routine.
4. Verify the DMG SHA-256 and, where available, the GitHub build attestation
   as described in [Verifying Releases](https://github.com/mskomek/hpc-client-gui/blob/main/docs/VERIFYING_RELEASES.md).

The application may ask for Keychain access when you save a connection password.
Only an opaque Keychain reference is stored in the application configuration;
the plaintext password is not written to logs, diagnostics, or configuration.

## X11 and XQuartz

XQuartz is optional. Install it only when you need remote graphical X11
applications. The app expects XQuartz, `/opt/X11/bin/xauth`, and a valid
`DISPLAY`; it does not download or stop XQuartz. macOS X11 requires an SSH key
or agent, not password-only authentication.

## Updates and removal

Updates are manual: download the newer architecture-matching DMG, drag the new
app over the old one, and launch it from Applications. Remove the app by
moving it to the Trash. User data remains under `~/Library/Application Support/HPC Client GUI`.

This is an unofficial client-side tool, not an official TRUBA application.
