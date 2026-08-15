# Logs and Diagnostics

> Türkçe: [[Logs-and-Diagnostics-TR]]

## Where the log lives

```text
~/.truba_slurm_gui/app.log
```

On Windows that is `C:\Users\<you>\.truba_slurm_gui\app.log`. The directory
name is legacy and is retained for compatibility with existing installations —
it does not mean the application is tied to any particular cluster.

The log rotates: older content moves to `app.log.1`, `app.log.2`, and so on.
The on-disk log is deliberately **not** redacted, because it is your local
debugging record. Redaction happens at the points where a log leaves the
machine — see [[Data and Privacy|Data-and-Privacy]].

Alongside it you may find `crash.log` (the crash reporter's record) and
`vcxsrv_stdout.log` / `vcxsrv_stderr.log` (X11 helper output on Windows).

## When something goes wrong

The interface is designed to stay responsive and write the failure to the log
rather than freeze or pop up an unhelpful dialog. If a remote operation fails,
the log is the first place to look, and attaching it makes a bug report far
faster to act on.

## Diagnostic commands

Three `doctor` subcommands cover local checks, connectivity, and a real
round-trip:

```bash
hpc-client-gui doctor environment
hpc-client-gui --profile mycluster doctor connection
hpc-client-gui --profile mycluster doctor smoke
```

| Command | What it does |
|---|---|
| `doctor environment` | Checks the local environment the application depends on |
| `doctor connection` | Opens a session and initializes the file transport |
| `doctor smoke` | Round-trips a smoke-test file over the file transport |

`doctor smoke` accepts two options:

- `--keep` preserves the remote smoke directory instead of deleting it, which
  helps when you need to inspect what was written.
- `--artifact PATH` writes the smoke result as JSON to a local path, which is
  what you want in scripted checks.

Each command reports through the standard exit-code contract, so a script can
gate on connectivity before doing real work:

```bash
hpc-client-gui --profile mycluster doctor connection || exit $?
```

See [[CLI Exit Codes|CLI-Exit-Codes]].

## Increasing detail

`--verbose` adds diagnostics to any command's output; `--quiet` suppresses
non-error output. Neither changes the exit code or the log file.

## Exporting a bundle

The send-logs dialog collects a redacted diagnostic bundle you can attach to an
issue. See [[Crash Reports and Send Logs|Crash-Reports-and-Send-Logs]].

## See also

[[Troubleshooting|Troubleshooting]] ·
[[Data and Privacy|Data-and-Privacy]] ·
[[Security Model|Security-Model]]
