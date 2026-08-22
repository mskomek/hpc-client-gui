# Verifying Releases

Every release publishes its artifacts together with SHA-256 checksum files and a
`MANIFEST.json` that inventories each file (size + SHA-256). Build provenance is
published as signed GitHub artifact attestations. This page explains how to
check a download before running it.

## 1. Verify the SHA-256 checksum

Each downloadable archive has a sibling `<file>.sha256` containing
`<digest>  <filename>`.

Windows (PowerShell):

```powershell
Get-FileHash .\hpc-client-gui_windows_onedir.zip -Algorithm SHA256
# compare against the digest in hpc-client-gui_windows_onedir.zip.sha256
```

Linux:

```bash
sha256sum -c hpc-client-gui-1.2.7-x86_64.AppImage.sha256
```

`MANIFEST.json` lists the expected size and digest for every asset, so a single
download of the manifest is enough to check the whole release offline.

## 2. Verify build provenance (GitHub artifact attestations)

The release workflow signs SLSA build provenance for the final ZIP, AppImage,
`.deb`, and Flatpak artifacts using GitHub's official
[`actions/attest-build-provenance`](https://github.com/actions/attest-build-provenance)
action. Verify with the GitHub CLI against this repository:

```bash
gh attestation verify hpc-client-gui_windows_onedir.zip -R mskomek/hpc-client-gui
```

See [Using artifact attestations to establish provenance for builds](https://docs.github.com/en/actions/security-guides/using-artifact-attestations-to-establish-provenance-for-builds)
for background on how the signatures work.

## 3. Windows code signature

Authenticode signing is **not enabled yet**. Windows may show an
SmartScreen/"unknown publisher" prompt; the checks above are the supported
verification path today. This document will be updated if/when a real code
signing certificate is configured.
