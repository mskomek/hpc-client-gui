# Installation on macOS

HPC Client GUI macOS packages are distributed outside the Mac App Store as
signed and notarized DMG files when the release gate is complete. macOS 13 or
newer is required.

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
