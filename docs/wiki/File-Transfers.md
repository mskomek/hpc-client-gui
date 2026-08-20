# File Transfers

> Türkçe: [[File-Transfers-TR]]

Uploads and downloads run through a queue with its own view, so a long transfer
never blocks the rest of the interface.

## Starting a transfer

**Upload selected** and **Download selected** act on the current selection;
drag and drop and the clipboard's paste actions do the same thing. If nothing
is selected, the application says so instead of doing nothing silently.

## Transfer type

**Transfer type** is **Auto**, **Binary**, or **ASCII**, and the panel shows
the effective mode in use. The default is set in Settings — see
[[Settings Reference|Settings-Reference]].

## The transfer view

Four tabs: **Queue**, **Transfers** (active), **Failed**, and **Completed**.

Controls:

| Control | Effect |
|---|---|
| **Process Queue** | Start working through the queue |
| **Stop** | Stop after the current transfer finishes |
| **Cancel** / **Cancel all** | Cancel the current transfer or everything |
| **Stop and remove all** | Stop and clear the queue |
| **Retry failed** / **Retry selected** | Requeue failures |
| **Remove selected** | Drop entries from the queue |
| **Clear queued** / **Clear failed** / **Clear completed** | Tidy each list |
| **Set Priority** | Highest, High, Normal, Low, or Lowest |

Progress shows the running item with transferred and total bytes, current
speed, and estimated remaining time. Stopping after the current transfer and
cancelling are both reported explicitly, so you know which one happened.

## Parallelism

The configured parallel transfer limit is shown in the view. Parallel uploads
and downloads use isolated channels; other file operations remain sequential. A
profile can override the global limit — see
[[Connecting and Profiles|Connecting-and-Profiles]].

## Upload plan confirmation

When enabled, an upload shows its plan first: the **Operation** for each entry
(**Upload**, **Create folder**, **Delete existing**), the **Source**, and the
**Destination**. **Start transfer** proceeds; **Don't ask again** turns the
confirmation off.

This is the last point at which you can see that a transfer would delete
something before it does.

## Conflicts

When the destination file already exists, the conflict dialog shows both files
with their size and modification time, and offers:

| Action | Effect |
|---|---|
| **Overwrite** | Replace unconditionally |
| **Overwrite if source newer** | Replace only when the source is newer |
| **Overwrite if different size** | Replace only when sizes differ |
| **Overwrite if different size or source newer** | Either of the above |
| **Resume** | Continue an interrupted transfer |
| **Rename** | Keep both |
| **Skip** | Leave the destination alone |

The choice can be remembered with **Always use this action**, scoped with
**Apply to current queue only** or **Apply only to downloads**.

## Resuming

**Resume** continues an interrupted transfer instead of starting over, which
matters for large files on unreliable links. Transfer state is journaled
locally, so a resume survives restarting the application.

## Verifying integrity

With **Verify transfers with SHA-256 after completion** enabled, source and
destination checksums are compared before a transfer is marked successful. On
the command line the equivalent is `--verify`:

```bash
hpc-client-gui --profile mycluster files download /scratch/$USER/out.csv ./out.csv --verify
hpc-client-gui --profile mycluster files upload ./inputs /scratch/$USER/inputs --recursive --if-exists resume
```

`--if-exists` takes `overwrite`, `skip`, `rename`, or `resume`. See
[[CLI Guide|CLI-Guide]].

## Measuring throughput

**Run remote transfer speed test** uploads and downloads a temporary file of
the configured size on the remote backend, verifies it, removes it, and reports
upload and download rates. It is a genuine round-trip against your cluster, not
an estimate.

## After the queue finishes

An action can run when the queue empties: none, a notification bubble, a
request for attention, a sound, a command, closing the application (once or
always), or a one-time system reboot, shutdown, or suspend.

The one-time variants apply to the next completion only — useful for an
overnight transfer without permanently changing what happens afterwards.

## See also

[[Remote File Manager|Remote-File-Manager]] · [[Settings Reference|Settings-Reference]] · [[Troubleshooting|Troubleshooting]]
