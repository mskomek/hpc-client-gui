# Compatibility and Support Matrix

> Türkçe: [[Compatibility-and-Support-Matrix-TR]]

Current version: **1.5.9** (`pyproject.toml`).

## Platforms and packaging

The platform rows below describe documented build and installation formats;
they do not certify that every listed artifact was produced or validated for
the current frozen release candidate. Candidate-specific support is recorded
in the dated evidence section below.

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

## Frozen release candidate 1.5.9 (evidence scope)

This section bounds the evidence for the frozen 1.5.9 candidate. It does not
certify the full platform release set described above.

| Item | Status for this candidate | Evidence |
|---|---|---|
| Windows 10/11 AMD64, onedir `hpc-client-gui.exe` (freeze SHA-256 `B3019DEA16783C8AB859FA36D2B0FEF2FB70DB075633E54EB0F36587295374FD`) | **B301… is the frozen reference; observed DB29… bytes are not validated against that pin, so release support is not established** | The W61.2 U02 smoke was tied to HEAD `92128c8726435aa0087f090c4a080720f148781f` and exact B301… bytes. At HEAD `bc2e61dcf86dadeda26141e5324088be8285243f`, the observed executable SHA-256 is `DB29B6A8BD2C78FE1D9169F36B595752DEC40F411085AB8E6032384E740BBFBD`, differing from the frozen reference. W61.3 U02 records a 20/20 packaged smoke on DB29…; W61.1 records that the authoritative W10 identity/census remains unresolved. The smoke does not reconcile the B301/DB29 mismatch or establish release acceptance. |
| GUI runtime | wxPython 4.3.1 observed in W61.2's B301… smoke; W61.3's DB29… summary reports 20 checks PASS, but its referenced runtime sidecar is absent, so current-candidate runtime acceptance is not demonstrated | `artifacts/wave_W61.2/W61.2_U02_FROZEN_PACKAGE_GATE.json`; `artifacts/wave_W61.3/W61.3_U02_CORE_SMOKE.json`. `W61.3_U02_CORE_SMOKE.runtime.json` is currently missing. These records do not validate DB29… against the B301… freeze pin. |
| Cluster side | **Not validated for this candidate** | W61.2 U03 did not run a mutating replay against LOCAL_REAL: the exact pinned executable is unavailable and no controller-established serial fallback or exclusive lab lease was present. Health probes and disposable loopback smoke do not establish real-cluster support. |
| macOS (Apple Silicon / Intel) DMG | **Not part of this candidate** | no macOS artifact was built or regressed for this freeze |
| Linux AppImage / `.deb` | **Not part of this candidate** | no Linux artifact was built or regressed for this freeze |
| From source (Python 3.14.x) | Developer use only; not validated as a W61.2 release candidate artifact | Historical W57.4 suite results are not current frozen-candidate platform evidence. |

No macOS or Linux artifact is included in this candidate evidence. These rows
record historical, bounded checks only; DB29… has a separate narrow packaged
smoke summary but has no current runtime sidecar and remains unreconciled with
the B301… freeze pin. The receipts do not imply release acceptance or that every documented platform is supported
by this candidate. Any later byte
change to the executable mints a new SHA-256 and voids its candidate-specific
evidence.
