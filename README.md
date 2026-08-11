# HPC Client GUI

**A Windows desktop client for TRUBA and other Slurm-based HPC systems.**

HPC Client GUI brings common HPC tasks into a single desktop application, including
**SSH connections, remote file management, Slurm job workflows, job output monitoring,
and optional X11 applications**.

It is designed to reduce the need to switch between SSH terminals, file-transfer tools,
and separate Slurm commands during everyday HPC work.

[**Download Latest Release**](https://github.com/mskomek/hpc-client-gui/releases/latest)
&nbsp;•&nbsp;
[**Documentation**](#documentation)
&nbsp;•&nbsp;
[**Sponsor**](https://github.com/sponsors/mskomek)

> **Independent project:** HPC Client GUI is not an official TRUBA or TÜBİTAK
> application. It is a client-side tool designed for TRUBA and compatible
> SSH/Slurm-based HPC environments.

---

## Features

### Remote access and files

- SSH connection and session management
- Remote file browsing and management
- SFTP upload and download
- Transfer progress, cancellation, resume, and conflict handling
- Copy, move, rename, delete, drag & drop, and remote file editing

### Slurm workflows

- Submit Slurm jobs
- Monitor active jobs using structured queue information
- Inspect job details and accounting data
- Cancel jobs
- Follow standard output and error files
- Create and edit Slurm scripts from templates

### Desktop workflow

- Turkish and English interface
- Saved connection profiles
- Windows notifications for completed and failed jobs
- Centralized application logging
- Optional X11 workflows using VcXsrv and `plink.exe`

### CLI and diagnostics

- Command-line access for profiles, remote files, jobs, and diagnostics
- Script-friendly text and JSON output
- Connection and transfer diagnostics
- SSH host-key verification
- Protected local credential storage on supported Windows systems

---

## Installation and Running

### Option A — Portable Windows Package (Recommended)

Python is **not required** when using the packaged Windows release.

1. Download the latest Windows package from
   [GitHub Releases](https://github.com/mskomek/hpc-client-gui/releases/latest).
2. Extract the downloaded ZIP archive.
3. Run `hpc-client-gui.exe`.

For normal **SSH, SFTP, Slurm, remote file, and CLI workflows**, PuTTY is not required.

### Optional X11 support

If you want to launch remote graphical applications through X11, you may additionally need:

- `VcXsrv`
- `plink.exe` from PuTTY

These components are used only for optional X11 workflows and are not required for the
core SSH/SFTP/Slurm functionality.

Institutional firewall, VPN, antivirus, or endpoint-security policies may affect network
connections or external helper applications.

---

### Option B — From Source (Developer Mode)

#### Requirements

- Windows 10 or Windows 11
- Python 3.10+
- Optional for X11: VcXsrv + `plink.exe`

#### Setup

```powershell
# In the project root directory
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

# Or install the project in editable mode:
pip install -e .
```

#### Run the GUI

```powershell
python -m truba_gui
```

---

## Command-Line Interface

The project also provides CLI access to connection profiles, diagnostics, remote files,
and Slurm jobs.

Top-level commands include:

- `gui` — launch the desktop GUI
- `version` — print version and build information
- `profile` — manage saved connection profiles
- `doctor` — run diagnostics
- `files` — perform remote SFTP file operations
- `jobs` — perform Slurm scheduler operations

Examples of available subcommands include:

```text
profile: list, show, create, update, delete, test
doctor:  environment, connection, smoke
files:   ls, stat, checksum, mkdir, upload, download, cp, mv, rm
jobs:    list, status, accounting, lssrv, submit, cancel
```

Shared options include output formatting, quiet/verbose modes, timeouts, profile
selection, SSH host/user/key overrides, sensitive-value input handling, and strict
host-key checking.

Use the built-in help as the authoritative command reference:

```powershell
python -m truba_gui --help
```

Packaged releases may also include the standalone CLI executable:

```text
hpc-client-cli.exe
```

### CLI guides

- [Turkish CLI Guide](src/truba_gui/docs/CLI_GUIDE_tr.md)
- [English CLI Guide](src/truba_gui/docs/CLI_GUIDE_en.md)

---

## Documentation

Documentation is available both inside the application and in the repository.

- In the application: use the **Help** button in the top-left area.
- [Turkish Help](src/truba_gui/docs/HELP_tr.md)
- [English Help](src/truba_gui/docs/HELP_en.md)

---

## Security Notes

- Sensitive values such as passwords and tokens are not written to command history.
- Credentials are excluded from normal application logs.
- Saved credentials can use protected local storage on supported Windows systems.
- SSH host-key verification is supported.
- X11 helper processes are cleaned up on application exit where possible.
- Diagnostic and logging features are designed to avoid exposing sensitive values.

If you discover a security issue, avoid posting credentials, private keys, tokens,
cluster secrets, or other sensitive information in a public GitHub issue.

---

## Support the Project

HPC Client GUI is independently developed and maintained.

If you find HPC Client GUI useful in your research, engineering, or HPC workflow,
you can support its continued development through
[GitHub Sponsors](https://github.com/sponsors/mskomek).

Sponsorship can help support ongoing maintenance, bug fixes, testing, documentation,
compatibility work, release maintenance, and future improvements.

### GitHub Sponsors

[**Sponsor HPC Client GUI on GitHub**](https://github.com/sponsors/mskomek)

Monthly and one-time sponsorship options are available.

### Bitcoin (BTC)

Bitcoin is also available as an alternative voluntary donation method.

```text
bc1qvnrw2rn89rltx8ttj0hfyyte8lasgcsr7f3lxz
```

<img width="263" height="261" alt="Bitcoin donation QR code" src="https://github.com/user-attachments/assets/a1cf3da4-ce28-42b8-afc7-010548bdb6ee" />

Please verify the address shown in this repository before sending funds.

Sponsorships and donations are **completely optional** and do not unlock exclusive
features, privileges, priority support, or guaranteed support.

**A sponsorship or donation does not grant commercial-use rights and does not
constitute a commercial license.**

For additional information and other ways to support the project, see
[SUPPORT.md](SUPPORT.md).

---

## Licensing

Starting with **v1.2.0**, HPC Client GUI is licensed under the
**PolyForm Noncommercial License 1.0.0**. See [LICENSE](LICENSE).

Under the current licensing model:

- personal, academic, educational, public-research, and other permitted
  non-commercial uses remain available under the PolyForm Noncommercial terms;
- **commercial use requires a separate commercial license**;
- commercial embedding, incorporation, OEM/bundling, commercial redistribution,
  and proprietary commercial derivatives are not covered by the non-commercial license.

For commercial licensing details, see
[COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md).

### Historical license boundary

Releases before **v1.2.0** were distributed under the MIT License.

That earlier MIT license grant is **not revoked** for copies of those releases that
were already distributed. Those earlier releases remain subject to the license under
which they were originally released.

---

## Project Status and Disclaimer

HPC Client GUI is an independent community project.

It is:

- **not an official TRUBA tool**;
- **not affiliated with TÜBİTAK, ANSYS, or any other organization** unless explicitly stated;
- a **client-side application**;
- not designed to modify TRUBA or another HPC provider's server infrastructure.

Issues and pull requests can be submitted through GitHub.
