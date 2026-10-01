# Compatibility and Support Matrix

> Türkçe: [[Compatibility-and-Support-Matrix-TR]]

Current version: **1.5.9** (`pyproject.toml`).

## Platforms and packaging

| Platform | Format | Notes |
|---|---|---|
| Windows 10 / 11 | Portable ZIP containing `hpc-client-gui.exe` | Python not required |
| macOS 13+ Apple Silicon | `hpc-client-gui_macos_arm64.dmg` | Signed/notarized release DMG |
| macOS 13+ Intel | `hpc-client-gui_macos_x86_64.dmg` | Signed/notarized release DMG |
| Linux x86_64 | AppImage | Runs without installation |
| Linux x86_64 (Debian-based) | `.deb` | Installs system-wide |
| Any supported platform | From source | Python 3.14.x, `pip install -e .` |

Flatpak is optional and not part of the standard release set, because its
runtime and SDK are substantially larger. There is no ARM64 build.

Linux from-source use is documented for Ubuntu LTS, Fedora, and openSUSE on
x86_64. Qt platform libraries (`libegl1` class) are no longer required: the V2
production runtime is wxPython (wxWidgets); Qt/PySide6 is legacy-only
(unadvertised `legacy-qt` extra) and is not shipped in the V2 production
package. Building wxPython from source on Linux needs the GTK/WebKit build
dependencies documented in `docs/v2/WX_DEPENDENCY_CLOSURE.md`.

## Runtime requirements

| Requirement | Portable / packaged | From source |
|---|---|---|
| Python 3.14.x | Not required | Required |
| wxWidgets runtime (wxPython 4.3.1) | Bundled | `wxPython>=4.3.1` required |
| Qt/PySide6 | Not shipped (legacy-only `legacy-qt` extra) | Optional, legacy-only, not required |
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

## Frozen release candidate 1.5.9 (W57.4 final support statement)

This section is authoritative for the frozen candidate handed to W11; the
platform table above describes the release *set* the project can produce.

| Item | Status for this candidate | Evidence |
|---|---|---|
| Windows 10/11 AMD64, portable `hpc-client-gui.exe` (SHA-256 `B3019DEA16783C8AB859FA36D2B0FEF2FB70DB075633E54EB0F36587295374FD`) | **Supported** | packaged smoke 20/20 on the exact artifact; W57.1 packaged functional replay 110/110; LOCAL_REAL Hyper-V cluster `lab-test` LOCAL_REAL_READY (0 failed) |
| GUI runtime | **wxPython 4.3.1 (wx V2)**; Qt/PySide6 not shipped | bundle has zero Qt files (freeze declaration) |
| Cluster side | SSH/SFTP + Slurm (`sbatch`/`squeue`/`sacct`/`scancel`) | LOCAL_REAL lab: SSH, SFTP round trip, sbatch, cancel, shared home |
| macOS (Apple Silicon / Intel) DMG | **Not part of this candidate** | no macOS artifact was built or regressed for this freeze |
| Linux AppImage / `.deb` | **Not part of this candidate** | no Linux artifact was built or regressed for this freeze |
| From source (Python 3.14.x) | Developer use only, not a release artifact | full automated suite in W57.4 report |

Any later byte change to the artifact mints a new SHA-256 and voids this statement.
