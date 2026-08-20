# Cluster Requirements

> Türkçe: [[Cluster-Requirements-TR]]

**Will this work on my HPC system?** Usually yes. This page is the checklist.

## What the cluster must provide

| Requirement | Why |
|---|---|
| SSH access with your own account | Every session, command, and transfer runs over it |
| An SFTP subsystem | The default file transport (`--transport ftp` is the alternative) |
| Slurm | `squeue`, `sbatch`, `scancel` for the job features |
| `sacct` | Accounting and finished-job history — recommended, not required |
| X11 forwarding permitted | Only if you need remote graphical applications |

If Slurm is missing, the connection, file manager, transfers, terminal, and
editor still work; only the job features are unavailable.

## What the cluster does **not** need

- **No server component.** Nothing of this project runs on the cluster.
- **No daemon or background service.**
- **No root access.**
- **No installation on the cluster** — not even in your home directory.
- **No administrator involvement.** If you can already reach the cluster with
  an SSH client, you can use this application.

It is an ordinary SSH and SFTP client that happens to know how to drive Slurm.
Your site's policies — authentication requirements, allocation limits, whether
X11 is allowed — stay in force and are not something the application can relax.

## Checking your cluster

Run these on the cluster after logging in normally:

```bash
sinfo                 # Slurm is present and you can see partitions
squeue -u $USER       # your queue is readable
sacct -u $USER        # accounting is available (optional)
```

Or let the application check for you once a profile exists:

```bash
hpc-client-gui --profile mycluster doctor connection
hpc-client-gui --profile mycluster doctor smoke
```

`doctor smoke` round-trips a real file over the transport, which is the
strongest single check that the setup works. See
[[Logs and Diagnostics|Logs-and-Diagnostics]].

## Site-specific tooling

Sites that wrap or rename the Slurm commands are configured, not patched: each
connection profile carries its own list-jobs, submit, cancel, accounting, and
job-details commands, plus custom status commands. See
[[Connecting and Profiles|Connecting-and-Profiles]].

Login banners or warnings mixed into command output can degrade Slurm output
parsing. The application fails softly and logs the details rather than
guessing — see [[Troubleshooting|Troubleshooting]].

## See also

[[Compatibility and Support Matrix|Compatibility-and-Support-Matrix]] ·
[[Quick Start|Quick-Start]] ·
[[X11 Forwarding|X11-Forwarding]]
