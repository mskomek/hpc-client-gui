# Job Outputs

> Türkçe: [[Job-Outputs-TR]]

A Slurm job writes standard output and standard error to files on the cluster.
The **Outputs** area follows those files while the job runs.

## The two output panels

**Output 1: Standard Output** and **Output 2: Error Output** are the two
panels. The active Slurm script is shown above them, or *(none)* when nothing
is being followed.

From a file in the listing you can choose:

- **Follow in Output 1** or **Follow in Output 2**
- **Follow in Output 1/2 in new tab**
- **Follow in Output 1/2 in new window**, or **Follow file in new window**
- **Assign to \<target\> Output 1 / Output 2** to send a file to an existing
  follow window or tab

Follow tabs and windows are numbered, and a combined window's title names both
the output and the error file it is following, so several concurrent jobs stay
distinguishable.

## Live following

Output is tailed as it is written.

| Control | Effect |
|---|---|
| **Auto-scroll** | Keep the view pinned to the newest line |
| **Pause live follow** | Stop updating without closing the view |
| **Resume live follow** | Continue |
| **Search output** with **Next** | Find text in what has been read so far |
| **Close window** / **Close tracking screen** | Stop following |

When tracking stops, the view says so explicitly rather than appearing to be a
live view that has gone quiet — the difference matters when you are waiting on
a job.

Live following can pause automatically while the window is minimized, and a
periodic warning about long-running tracking can be enabled or disabled. See
[[Settings Reference|Settings-Reference]].

## What opens after submission

Configurable in Settings:

| Choice | Result |
|---|---|
| Do not open a follower | The job is registered and refreshed; the current view is unchanged |
| Jobs & Outputs — Outputs tab | Output continues in the existing Output 1 and Output 2 panels |
| New follow tab | One new lower tab with output and error together |
| One combined follow window | One independent window with both |
| Separate output and error windows | Two independent windows |

New follow windows can be opened minimized.

## Finding output files

The **Files** and **Scratch** panels browse to where your job wrote its output.
Because the templates name output files `logs/%x_%j.out` and `.err` — job name
and job ID — concurrent runs do not overwrite each other and each job's files
are identifiable. See [[Job Script Templates|Job-Script-Templates]].

The refresh interval for the jobs and outputs views is configurable.

## Downloading results

Any output file can be downloaded through the file manager, or on the command
line:

```bash
hpc-client-gui --profile mycluster files download \
  /scratch/$USER/logs/run_123456.out ./run.out --verify
```

## See also

[[Slurm Jobs|Slurm-Jobs]] ·
[[Remote File Manager|Remote-File-Manager]] ·
[[File Transfers|File-Transfers]]
