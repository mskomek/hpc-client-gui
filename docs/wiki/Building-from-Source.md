# Building from Source

> Türkçe: [[Building-from-Source-TR]]

This page covers producing distributable artifacts. To simply *run* from
source, see [[Installation from source|Installation-From-Source]].

## Prerequisites

- A working source checkout with the development install
  (`pip install -e .[test]`).
- Windows for the Windows package.
- Docker for the Linux artifacts, which are built in a container image
  (`hpc-client-gui-linux-build:24.04` by default).

## Build both platforms from Windows

```powershell
.\scripts\build_release.ps1 -Version 1.2.6
```

To reuse only what is already cached and download nothing:

```powershell
.\scripts\build_release.ps1 -Version 1.2.6 -Offline
```

`-Offline` makes missing inputs an error rather than a download. If the Linux
build image, the AppImage tool, the build virtual environment, or the Flatpak
runtime and SDK are not already cached, the script fails instead of fetching
them.

## Where build inputs and outputs live

- Cached build inputs: `.cache/release`.
- Release artifacts: one combined `dist/releases/v<version>` directory.

Existing cached inputs are not redownloaded unless they are missing.

## Windows packaging

`scripts/package_release.ps1` assembles the Windows onedir build into
`hpc-client-gui_windows_onedir.zip` inside the version directory and writes a
matching `.sha256` file next to it.

```powershell
.\scripts\package_release.ps1 -Version 1.2.6
```

## Linux packaging

`scripts/release_linux.py` validates the Linux release inputs and produces the
Linux artifacts:

- `hpc-client-gui-<version>-x86_64.AppImage`
- `hpc-client-gui_<version>_amd64.deb`

It validates before it packages: the AppImage `.desktop` entry must have a
`[Desktop Entry]` section with `Exec=` and `Name=` lines, the `AppRun` launcher
must exist and start with a shebang, and the `.deb` control file must carry its
required fields and the version placeholder. A malformed input fails the build
rather than shipping bad metadata.

## Checksums

Every published artifact gets a matching `.sha256`. Verify before installing:

```bash
sha256sum -c hpc-client-gui-1.2.6-x86_64.AppImage.sha256
```

## See also

[[Release Process|Release-Process]] ·
[[Testing and CI|Testing-and-CI]] ·
[[Architecture|Architecture]]
