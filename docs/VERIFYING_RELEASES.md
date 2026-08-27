# Verifying Releases

Every release publishes its artifacts together with SHA-256 checksum files and a
`MANIFEST.json` that inventories each file (size + SHA-256). Build provenance is
published as signed GitHub artifact attestations. This page explains how to
check a download before running it.

## 1. Check the release security metadata

Every release ships `RELEASE_SECURITY.json`. It states the macOS mode
(`signed-notarized` or `unsigned`), the source commit, whether Developer ID
verification, notarization, stapling, and the Gatekeeper assessment passed,
and which architectures were produced.

- `macos_mode: "unsigned"` means the DMGs are **not** Apple Developer ID
  signed or notarized. Gatekeeper may block the first launch; SHA-256 and
  GitHub provenance verify integrity and origin but are **not** substitutes
  for Apple code signing.
- If the file is missing, treat the build as unsigned/unknown — do not assume
  it was signed.
- An ad-hoc (`codesign -`) signature on a DMG is not a Developer ID signature;
  only trust the claims in `RELEASE_SECURITY.json` after the release's
  verification job succeeded.

## 2. Verify the SHA-256 checksum

Each downloadable archive has a sibling `<file>.sha256` containing
`<digest>  <filename>`.

Windows (PowerShell):

```powershell
Get-FileHash .\hpc-client-gui_windows_onedir.zip -Algorithm SHA256
# compare against the digest in hpc-client-gui_windows_onedir.zip.sha256
```

macOS / Linux:

```bash
shasum -a 256 -c hpc-client-gui_macos_arm64.dmg.sha256   # macOS
sha256sum -c hpc-client-gui-<version>-x86_64.AppImage.sha256   # Linux
```

`MANIFEST.json` lists the expected size and digest for every asset (including
the DMGs and `RELEASE_SECURITY.json`), so a single download of the manifest is
enough to check the whole release offline.

## 3. Verify build provenance (GitHub artifact attestations)

The release workflow signs SLSA build provenance for the final ZIP, AppImage,
`.deb`, Flatpak, and DMG artifacts plus `MANIFEST.json` and
`RELEASE_SECURITY.json` using GitHub's official
[`actions/attest-build-provenance`](https://github.com/actions/attest-build-provenance)
action. Verify with the GitHub CLI against this repository:

```bash
gh attestation verify hpc-client-gui_windows_onedir.zip -R mskomek/hpc-client-gui
gh attestation verify hpc-client-gui_macos_arm64.dmg -R mskomek/hpc-client-gui
```

See [Using artifact attestations to establish provenance for builds](https://docs.github.com/en/actions/security-guides/using-artifact-attestations-to-establish-provenance-for-builds)
for background on how the signatures work. Attestations prove where and how a
binary was built; they do not replace Apple code signing.

## 4. macOS Gatekeeper (first launch)

If the release is unsigned:

1. Try opening the app normally.
2. If Gatekeeper blocks it, control-click/right-click the app in Finder and
   choose **Open**, or use **System Settings → Privacy & Security → Open
   Anyway**.
3. Do not disable Gatekeeper globally and do not use quarantine-stripping
   commands as a normal installation path.

## 5. Windows code signature

Authenticode signing is **not enabled yet**. Windows may show an
SmartScreen/"unknown publisher" prompt; the checks above are the supported
verification path today. This document will be updated if/when a real code
signing certificate is configured.
