# Installation on Linux

> Türkçe: [[Installation-Linux-TR]]

Linux releases target **x86_64** and are published as an AppImage and a `.deb`
package. Flatpak is optional and not part of the standard release set. There is
no ARM64 build.

## Artifact names

For version 1.5.9 the release tooling produces:

- `hpc-client-gui-1.5.9-x86_64.AppImage`
- `hpc-client-gui_1.5.9_amd64.deb`

Each artifact is published with a matching `.sha256` file.

## Verify the download

```bash
sha256sum -c hpc-client-gui-1.5.9-x86_64.AppImage.sha256
```

Do not install an artifact whose checksum does not verify.

## AppImage

```bash
chmod +x hpc-client-gui-1.5.9-x86_64.AppImage
./hpc-client-gui-1.5.9-x86_64.AppImage
```

The AppImage runs without installation.

## Debian package

```bash
sudo apt install ./hpc-client-gui_1.5.9_amd64.deb
```

## wxWidgets system libraries

The application is a wxPython (wxWidgets) desktop program. Qt (PySide6)
platform libraries are not required: Qt is legacy-only and is not shipped in
the V2 production package. A startup failure is not expected to mention the Qt
`xcb` platform plugin; if the application fails at startup, see
[[Troubleshooting|Troubleshooting]].

## X11 forwarding on Linux

X11 forwarding on Linux uses the **system OpenSSH client** (`ssh -X/-Y`). It
does not use the Windows plink/VcXsrv path, and no helper is downloaded.
Confirm the client is installed and that `DISPLAY` is set in your session
before launching remote graphical applications. Details:
[[X11 Forwarding|X11-Forwarding]].

## Application data

Configuration, the rotating log, and saved host keys live in
`~/.truba_slurm_gui`. The directory name is legacy and is retained for
compatibility with existing installations.

## Next steps

[[Quick Start|Quick-Start]] · [[Installation from source|Installation-From-Source]] · [[Upgrading and uninstalling|Upgrading-and-Uninstalling]]
