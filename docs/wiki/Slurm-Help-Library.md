# Slurm Help Library

> Türkçe: [[Slurm-Help-Library-TR]]

The application ships a built-in Slurm reference, reachable from the Help
dialog's library selector:

- **Core Help** — application usage and common workflows.
- **Provider Playbooks** — optional site-specific operational notes.
- **Generic Slurm/HPC** — portable guidance that applies to any Slurm cluster.

The generic library is `src/hpc_gui/docs/HELP_LIBRARY_GENERIC_en.md` (and
`_tr.md`) in the repository, and it is canonical. This page is a map of what is
in it, not a copy.

## What the generic library covers

| Section | Topic |
|---|---|
| 1 | Identifying your environment before you start |
| 2 | Core Slurm commands for the daily workflow |
| 3 | A first successful job, minimal example |
| 4 | Job script anatomy and requesting resources correctly |
| 5 | Templates for CPU, MPI, and GPU jobs |
| 6 | Interactive mode for debugging and quick tests |
| 7 | Job arrays and dependencies for pipeline workflows |
| 8 | A debugging workflow |
| 9 | Data layout and I/O performance |
| 10 | Software environments: modules, conda, containers |
| 11 | Security and operational best practices |
| 12 | Frequent errors and quick fixes |
| 13 | A pre-production checklist |

## The commands you will use most

```bash
sbatch job.sh                      # submit
squeue -u $USER                    # what is queued or running
scontrol show job <JOBID>          # details for one job
sacct -j <JOBID> --format=JobID,JobName,State,Elapsed,MaxRSS,ExitCode
scancel <JOBID>                    # cancel
sinfo                              # partitions and their state
```

The same operations are available through the application — see
[[Slurm Jobs|Slurm-Jobs]] — and through the command line, where
[[CLI Guide|CLI-Guide]] documents `jobs list`,
`jobs status`, `jobs accounting`, `jobs submit`, and `jobs cancel`.

## Before your first job on a new cluster

Every site differs in partition names, account and QOS limits, storage layout,
and module stack. Check them before you write a job script:

```bash
sinfo
module avail
```

Confirm which partitions your account may use; what the time, CPU, memory, and
GPU limits are; and which storage areas exist along with their quota and purge
policies. Slurm output parsing in the application varies with site
customization for exactly this reason.

## See also

[[Job Script Templates|Job-Script-Templates]] · [[Slurm Jobs|Slurm-Jobs]] · [[Quick Start|Quick-Start]]
