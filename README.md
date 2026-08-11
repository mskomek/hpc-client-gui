# HPC Client GUI

A **client-side GUI application** for **SSH + Slurm + optional X11 workflows** on TRUBA and other Slurm-based HPC systems.


> It is designed for TRUBA and similar Slurm/SSH-based HPC infrastructures.

---

## Features

* SSH session management (client-side)
* Slurm job monitoring / basic job operations (via `squeue`, `sacct`, etc.)
* Remote file manager (copy / move / paste, drag & drop, resume, progress / cancel, undo-move)
* i18n: Turkish / English
* Centralized logging: `~/.truba_slurm_gui/app.log` (rotating)
* X11 runs **in the background**: `plink.exe -X` + `VcXsrv` (no dedicated X11 UI tab)

---

## Installation & Running

### Option A — Standalone (EXE) ✅ Recommended

In this mode, **Python is NOT required**.

1. Download the latest package from **GitHub Releases** (Windows).
2. (Optional: if you will use X11) Install **VcXsrv**.
3. Obtain **PuTTY / plink**:
   - Place `plink.exe` next to the application **or**
   - Specify the `plink.exe` path via application settings (if available).
4. Run the EXE.

**External dependencies (NOT bundled in the EXE):**
- `plink.exe` (PuTTY)
- `VcXsrv` (required only for X11)
- Institutional firewall / antivirus policies (permissions may be required in some environments)

---

### Option B — From Source (Developer Mode)

#### Requirements

- Windows 10 / 11
- Python 3.10+ (recommended)
- (Optional) VcXsrv + plink.exe

#### Setup

```powershell
# In the project root directory
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
# or:
pip install -e .
```

#### Run

```powershell
python -m truba_gui
```

---

## Command-line Interface

`python -m truba_gui` exposes a command-line interface (`hpc-client-gui` is its internal program name shown in help output). Top-level commands:

- `gui` - launch the desktop GUI
- `version` - print version and build information
- `profile` - manage saved connection profiles (`list`, `show`, `create`, `update`, `delete`, `test`)
- `doctor` - run local diagnostics (`environment`, `connection`, `smoke`)
- `files` - remote SFTP file operations (`ls`, `stat`, `checksum`, `mkdir`, `upload`, `download`, `cp`, `mv`, `rm`)
- `jobs` - scheduler job operations (`list`, `status`, `accounting`, `lssrv`, `submit`, `cancel`)

Shared global options exist (format, quiet, verbose, timeout, profile selection, host/port/user/key overrides, a stdin-based sensitive-value input flag, and strict host-key checking); `python -m truba_gui --help` is authoritative.

- Full guides (drafted later in this wave):
  - Turkish: `src/truba_gui/docs/CLI_GUIDE_tr.md`
  - English: `src/truba_gui/docs/CLI_GUIDE_en.md`

---

## Documentation

- From within the application: click the **Help (❓)** icon in the top-left corner.
- As files:
  - Turkish: `src/truba_gui/docs/HELP_tr.md`
  - English: `src/truba_gui/docs/HELP_en.md`

---

## Security Notes

- Passwords / tokens are **never written to history** and **never shown in the UI**.
- Secrets are **never logged** (commands may be logged, but credentials are not).
- X11 processes are cleaned up on application exit; orphan processes are handled defensively.

---

## Support the Project

HPC Client GUI is independently developed and maintained. If you find HPC Client GUI useful in your research, engineering, or HPC workflow, you can support its continued development through [GitHub Sponsors](https://github.com/sponsors/mskomek).

Sponsorship helps support ongoing maintenance, bug fixes, documentation,
compatibility work, and future features.

### GitHub Sponsors

[Sponsor HPC Client GUI on GitHub](https://github.com/sponsors/mskomek)

### Bitcoin (BTC)

Bitcoin remains available as an alternative donation method:

```text
bc1qvnrw2rn89rltx8ttj0hfyyte8lasgcsr7f3lxz
```

<img width="263" height="261" alt="Bitcoin donation QR code" src="https://github.com/user-attachments/assets/a1cf3da4-ce28-42b8-afc7-010548bdb6ee" />

Donations are **completely optional** and do not unlock features, privileges,
priority support, or support guarantees.

**A donation does not grant commercial-use rights or constitute a commercial license.**

Commercial use still requires a separate commercial license. For additional
information and other ways to support the project, see [SUPPORT.md](SUPPORT.md).

---

## Licensing

Starting with v1.2.0, this project is licensed under the **PolyForm Noncommercial License 1.0.0** (see `LICENSE`).

- Free personal, academic, educational, public-research, and other permitted non-commercial use stays easy under the PolyForm Noncommercial 1.0.0 terms.
- **Commercial use requires a separate license.** Commercial embedding, incorporation, OEM/bundling, redistribution as a commercial product, and proprietary commercial derivatives are not covered by the PolyForm Noncommercial License. See [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md) for details and contact information.

**Historical boundary:** releases before v1.2.0 were distributed under the MIT License. That MIT grant is **not revoked** for copies of those earlier releases that were already distributed; they remain MIT-licensed.

This is an independent, community project. It is **not an official TRUBA tool** and is not affiliated with TÜBİTAK, ANSYS, or any other organization. It is **client-side only**; it does **NOT** modify the TRUBA infrastructure.

- Issues / PRs: via GitHub
