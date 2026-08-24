# Compatibility and Support Matrix

> Türkçe: [[Compatibility-and-Support-Matrix-TR]]

Current version: **1.2.6** (`pyproject.toml`).

## Platforms and packaging

| Platform | Format | Notes |
|---|---|---|
| Windows 10 / 11 | Portable ZIP containing `hpc-client-gui.exe` | Python not required |
| macOS 13+ Apple Silicon | `hpc-client-gui_macos_arm64.dmg` | Signed/notarized release DMG |
| macOS 13+ Intel | `hpc-client-gui_macos_x86_64.dmg` | Signed/notarized release DMG |
| Linux x86_64 | AppImage | Runs without installation |
| Linux x86_64 (Debian-based) | `.deb` | Installs system-wide |
| Any supported platform | From source | Python 3.10+, `pip install -e .` |

Flatpak is optional and not part of the standard release set, because its
runtime and SDK are substantially larger. There is no ARM64 build.

Linux from-source use is documented for Ubuntu LTS, Fedora, and openSUSE on
x86_64. Qt platform libraries are required (`libegl1` on Ubuntu/Debian, the
distribution equivalent elsewhere).

## Runtime requirements

| Requirement | Portable / packaged | From source |
|---|---|---|
| Python 3.10+ | Not required | Required |
| Qt runtime | Bundled | Provided by PySide6 |
| Qt platform libraries | Bundled or system | System (`libegl1` class) |
| `plink.exe` (PuTTY) | Optional, X11 only, Windows | Optional, X11 only |
| VcXsrv | Optional, X11 only, Windows | Optional, X11 only |
| System OpenSSH client | Not used for X11 on Windows | Required for X11 on Linux |
| XQuartz | Not required | Required only for macOS X11 |

## Cluster-side requirements

The application is provider-neutral. It works where SSH access is available,
Slurm commands exist (`sbatch`, `squeue`, `sacct`, …), and — only if you need
remote graphical applications — X11 forwarding is permitted.

If your site prints login banners or warnings that alter command output, Slurm
output parsing may degrade. The application is written to fail softly and log
the details rather than to guess.

## Connection and X11 support

| Scenario | Status | Notes |
|---|---|---|
| Key-based authentication | Supported | Main session path |
| Password authentication | Supported | Can be stored protected in a profile |
| X11 via plink + VcXsrv (Windows) | Recommended | Most reliable on Windows |
| X11 via OpenSSH with a key | Supported | Uses `ssh -X/-Y` |
| X11 via OpenSSH with a password | Limited | Hidden TTY prompts can block; plink preferred |
| macOS X11 with a password | Limited | SSH key or agent required; password-only X11 is not started |
| Host key policy `accept-new` | Supported | Unknown keys prompt to trust-and-save, trust once, or cancel |
| Host key policy `strict` | Supported | Unknown keys rejected; changed keys always rejected |

Saved host keys are written to `~/.truba_slurm_gui/known_hosts`.

## Known limitations

- The user experience is Windows-first.
- Slurm output parsing varies with site customization.
- X11 responsiveness depends heavily on network quality.

See also [[Installation on Windows|Installation-Windows]],
[[Installation on Linux|Installation-Linux]], and
[[Installation on macOS|Installation-macOS]], and
[[X11 Forwarding|X11-Forwarding]].
