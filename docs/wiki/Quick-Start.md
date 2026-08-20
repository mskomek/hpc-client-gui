# Quick Start

> Türkçe: [[Quick-Start-TR]]

This page gets you from a fresh download to a running Slurm job. It follows the
canonical "first job in 5 minutes" flow in `src/hpc_gui/docs/HELP_en.md`.

## 1. Install

- **Windows:** download the portable ZIP from the
  [releases page](https://github.com/mskomek/hpc-client-gui/releases), choose
  **Extract All**, then run `hpc-client-gui.exe`. Python is not required.
  See [[Installation on Windows|Installation-Windows]].
- **Linux:** download the AppImage or `.deb` for x86_64, verify the matching
  `.sha256`, then run it. See [[Installation on Linux|Installation-Linux]].
- **From source:** Python 3.10+, a virtual environment, and
  `pip install -e .[test]`. See
  [[Installation from source|Installation-From-Source]].

## 2. Connect

1. Create a connection profile with your cluster hostname and username.
2. Choose key-based or password authentication.
3. Connect. On first connection an unknown host key prompts you to trust and
   save it, trust it once, or cancel.

Details: [[Connecting and Profiles|Connecting-and-Profiles]] and
[[Security Model|Security-Model]].

## 3. Copy your inputs to the cluster

Use the remote file manager to upload your script and data. Prefer the scratch
or project directory for large data and long runs; scratch is periodically
cleaned by cluster administrators, so keep results you care about in home or
project storage.

Details: [[Remote File Manager|Remote-File-Manager]] and
[[File Transfers|File-Transfers]].

## 4. Write a job script

Create a simple `job.sh` — or start from a bundled template. Example:

```bash
#!/bin/bash
#SBATCH --job-name=first
#SBATCH --time=00:10:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G

echo "hello from $(hostname)"
```

Templates: [[Job Script Templates|Job-Script-Templates]]. Editing:
[[Script Editor|Script-Editor]].

## 5. Submit and watch

Submit the script, then follow the job in the jobs view. The equivalent Slurm
commands are:

```bash
sbatch job.sh
squeue -u $USER
```

Details: [[Slurm Jobs|Slurm-Jobs]] and [[Job Outputs|Job-Outputs]].

## 6. If something does not work

The interface should stay responsive and write errors to the rotating log at
`~/.truba_slurm_gui/app.log`. Attach that log when you ask for help.

See [[Troubleshooting|Troubleshooting]] and
[[Logs and Diagnostics|Logs-and-Diagnostics]].

## Do I need X11?

Only for remote **graphical** applications such as MATLAB or ParaView. Terminal
workloads — Python scripts, batch solvers, training jobs — do not need it. See
[[X11 Forwarding|X11-Forwarding]].
