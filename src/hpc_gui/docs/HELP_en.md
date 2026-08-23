# HPC Client GUI — Help

> **Unofficial client-side GUI** to simplify **SSH / Slurm / X11 workflows** across **Slurm-based HPC systems**.
>
> This is an independent, provider-neutral community project.

---

## For first-time users

The mental model is simple:

- **SSH**: connect to the HPC remotely.
- **Slurm**: submits and runs your jobs on allocated resources.
- **X11**: only needed for **graphical** apps (MATLAB, ParaView, etc.).

### Your first job in 5 minutes

1. **Connect**
2. Copy input/script/data to **Scratch / project directory**
3. Create a simple `job.sh`
4. Submit:
   - `sbatch job.sh`
5. Check status:
   - `squeue -u $USER`

### When do I need X11?

- ✅ MATLAB, ParaView, other GUI applications
- ❌ Not needed for terminal workloads (Python scripts, batch CFD, training jobs)

### If something doesn’t work

- The GUI should not freeze; errors are written to the **log file**.
- Log path:
  - `~/.truba_slurm_gui/app.log`
- When asking for help, sharing this log makes troubleshooting much faster.

---

## Embedded SSH terminal

The terminal on the Connection tab opens the remote shell inside the app. It
resizes with the window; **Find**, **Clear**, **A−**, and **A+** control the
local terminal view. All terminal assets are bundled, with no CDN or runtime
download.

When a connection fails, the dialog explains the likely cause and what to
check. A diagnostic code such as `SSH-XXXXXX` links the dialog to its log entry.

---

## File manager features

### Default local folder (per profile)

Under **Advanced → File browser** each connection profile can define a
**Default local folder**. When this profile connects, the local file pane
opens that folder. Leave it blank to keep the normal behavior (the last
locally visited folder). Scratch and Home remain the separate *remote*
defaults for the profile.

### Synchronized browsing

The checkable **Synchronized browsing** button in the Files tab mirrors
*directory navigation only* between the local pane and the active remote
pane. It never uploads, downloads, creates, renames, or deletes anything.

- Enabling it the first time asks whether the **currently visible local and
  remote folders** should become the synchronized root pair.
- Navigation inside the pair is mapped by relative path only; navigation
  outside either root simply does not mirror.
- A missing local counterpart folder is reported non-modally and is never
  created automatically.
- The button's menu offers **Reset synchronized roots to current folders**
  and **Disable synchronized browsing**. The root pair is stored per profile.

### Compare directories

The checkable **Compare directories** button adds a **Comparison** column to
the local and active remote file tables. It compares the *current immediate
directory only*, reusing metadata the panels already downloaded:

- exact name matching (case-sensitive on the remote side);
- statuses: Same, Local only, Remote only, Type differs, Size differs,
  Local newer, Remote newer;
- modification times use a small tolerance (2 seconds);
- no recursion into subfolders and no content/SHA comparison;
- enabling or recomputing causes **zero extra remote listing/stat traffic**;
  results refresh from existing snapshots after normal loads or transfers.

### Maximum simultaneous transfers

Per connection profile under **Advanced → Transfers**. This controls how many
file transfers run at the same time within the session — it does not open
extra login sessions. If the server/backend cannot support isolated parallel
transfer channels, the limit safely falls back to 1. Values of 2–4 may
improve throughput on fast links; be considerate on shared HPC login nodes.

### SSH advanced settings

- **Host key verification**: *Trust new hosts, reject changed keys*
  (`accept-new`; unknown hosts prompt for trust-once/trust-and-save) or
  *Require previously trusted host* (`strict`). Changed keys are always a
  hard failure; there is deliberately no "accept everything" mode.
- **SSH keepalive interval**: seconds between keepalive probes; `0`
  disables keepalive. It helps detect dead connections but is not a
  transfer-speed knob.
- **SSH timeout override**: `0` uses the application defaults; a positive
  value overrides the SSH connect/channel timeout.

### Connect through jump host (bastion)

Advanced → SSH offers a one-hop jump host: the app connects to the jump host
first and reaches the target cluster through an SSH `direct-tcpip` channel.

- Exactly one hop; multi-hop chains are not supported in this version.
- The jump host authenticates with an **SSH key or agent**; there is no jump
  password field, and your target password/credentials are never reused for
  the jump host.
- Both the jump host key and the target host key are verified independently;
  fingerprint prompts label which host they refer to.
- Terminal, file browsing, and Slurm features all run over the target
  connection exactly as with direct connections.

---

## What does it do?

- Manage SSH connections (client-side)
- Monitor Slurm jobs (queue, status, outputs)
- Manage remote files (copy/move/rename/delete, upload/download, resume, queue)
- Run X11 apps via **PuTTY plink** + **VcXsrv** in the background (no dedicated X11 tab)

---

## Help libraries in app

Use the Help dialog's library selector for:

- **Core Help**: app usage and common workflows
- **Provider Playbooks**: optional site-specific operational notes
- **Generic Slurm/HPC**: portable guidance for other clusters

---

## Install & run

### Standalone (EXE)

If you download the **standalone EXE**, you do **not** need Python or `requirements.txt`.

External prerequisites (Windows):

- **PuTTY / plink.exe** (X11 uses `plink.exe -X`, not Paramiko)
- **VcXsrv** (only if you need X11 / GUI apps)

Steps:

1. Start **VcXsrv** (only if you will run GUI apps)
2. Launch the EXE
3. Create/select a connection profile and connect

---

## Site-specific notes

## Script Editor keyboard shortcuts

Shortcuts apply to the active document tab:

| Shortcut | Action |
|---|---|
| `Ctrl+S` | Save the active file |
| `Ctrl+Shift+S` | Save and submit the active Slurm file |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+X` | Cut |
| `Ctrl+C` | Copy |
| `Ctrl+V` | Paste |
| `Ctrl+A` | Select all text |
| `Ctrl+F` | Find text in the active file |
| `F3` | Find the next match |
| `Ctrl+O` | Focus the remote path field; press Enter to open the file |
| `Ctrl+W` | Close the active document tab |
| `Ctrl+Tab` | Switch to the next document tab |
| `Ctrl+Shift+Tab` | Switch to the previous document tab |
| `Page Up` / `Page Down` | Move one screen up/down |
| `End` | Move to the end of the file |

- Prefer **Scratch** for large data and long runs.
- Scratch may be periodically cleaned by the HPC administrators; keep important outputs in Home or project storage.

---

## Other Slurm-based HPC systems

This app is provider-neutral. It should work if:

- SSH access is available
- Slurm commands exist (`sbatch`, `squeue`, `sacct`, ...)
- X11 forwarding is allowed (only if you need GUI apps)

If your site prints banners/warnings that affect command output, parsing may degrade, but the app should fail **softly** and log the details.

---

## Security

- Passwords/tokens are never written to command history or UI.
- The app uses a rotating log file:
  - `~/.truba_slurm_gui/app.log`
- "Allow external CLI access to remote commands" (Settings): off by default.
  When enabled, any local process running this application's command-line
  interface can reach remote commands (files/jobs/edit/shell/diagnostics) using saved
  profiles, without a GUI session. Settings also lets you pick a default CLI
  profile used when a command omits `--profile`.

---

## Limitations

- Windows-first UX
- Slurm output parsing may vary by site customization
- X11 performance depends heavily on network quality

---

## Support matrix

| Scenario | Status | Notes |
|---|---|---|
| Paramiko + key auth | Supported | Main SSH/session path |
| Paramiko + password auth | Supported | Password can be encrypted in profile |
| X11 + plink + VcXsrv | Recommended | Most reliable on Windows |
| X11 + OpenSSH + key | Supported | Uses system/bundled ssh with `-Y/-X` |
| X11 + OpenSSH + password | Limited | Hidden TTY prompts can block; plink preferred |
| Host key policy = `accept-new` | Supported | Unknown keys prompt for trust-and-save, trust-once, or cancel; saved keys go to `~/.truba_slurm_gui/known_hosts` |
| Host key policy = `strict` | Supported | Unknown keys are rejected; changed keys are always rejected |

---

## Support

- Please attach the log file when opening an issue:
  - `~/.truba_slurm_gui/app.log`

---

## SLURM Quick Commands

### Submit a job

- `sbatch job.sh`
- `sbatch --time=01:00:00 --mem=8G --cpus-per-task=4 job.sh`

### List jobs

- `squeue -u $USER`
- `squeue -j <JOBID>`

### Cancel jobs

- `scancel <JOBID>`
- `scancel -u $USER`  *(careful: cancels all your jobs)*

### Partitions / resources

- `sinfo`
- `sinfo -o "%P %a %l %D %t"`

### Accounting / history

- `sacct -u $USER --format=JobID,JobName,State,Elapsed,MaxRSS,AllocTRES`
- `sacct -j <JOBID> --format=JobID,State,ExitCode,Elapsed,MaxRSS`

### Inspect a job

- `scontrol show job <JOBID>`

### Interactive allocation (debug / GUI prep)

- `salloc -N 1 -n 1 -c 4 --mem=8G -t 01:00:00`
- `srun --pty bash`

---

## Linux support

Linux x86_64 releases are published on GitHub Releases as AppImage, Debian
`.deb`, and Flatpak packages. Each package has a sibling SHA-256 file.

### Requirements

- A supported Linux distribution (currently Ubuntu LTS, Fedora, or openSUSE),
  x86_64.
- Python 3.10+.
- Qt platform libraries PySide6 needs (e.g. `libegl1` on Ubuntu/Debian).

### Run from source

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[test]
python -m hpc_gui
```

The CLI is available the same way: `python -m hpc_gui --help`.

### X11 note

On Linux, X11 forwarding uses the **system OpenSSH client** (`ssh -X/-Y`). It
does not use the Windows plink/VcXsrv path. Make sure `ssh` is installed before
using X11 applications.
