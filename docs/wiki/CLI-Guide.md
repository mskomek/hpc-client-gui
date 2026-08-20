# CLI Guide

> Türkçe: [[CLI-Guide-TR]]

The complete command-line surface: what it is for, every command, the
output contract, and the exit codes.

## Overview

The application ships a command-line interface alongside the desktop GUI. It
exists so that connection profiles, file operations, and Slurm job operations
can be scripted without a GUI session.

### Invoking it

```bash
python -m hpc_gui --help
```

`hpc-client-gui` is the program name shown in help output. The packaged
Windows and Linux builds expose the same interface.

### Discovering commands

```bash
hpc-client-gui commands
hpc-client-gui --format json commands
```

`commands` prints the full command tree, every option, the alias table, and the
exit-code table. It is the authoritative inventory; this wiki mirrors it in
[[CLI Guide|CLI-Guide]].

### The external access gate

Remote commands are gated. **"Allow external CLI access to remote commands"**
in Settings is **off by default**. While it is off, commands that reach the
cluster refuse to run and print:


When the setting is on, any local process running this application's
command-line interface can reach remote commands — files, jobs, edit, shell,
and diagnostics — using saved profiles, without a GUI session. Settings also
lets you choose a default CLI profile used when a command omits `--profile`.
See [[Settings Reference|Settings-Reference]] and
[[Security Model|Security-Model]].

Global options apply to every command; the full table is under
[Command reference](#command-reference).

### Output and exit codes

Results are printed as text or as JSON, and every invocation ends with a
documented exit code. Automation should branch on the exit code, not on
message text. See [[CLI Guide|CLI-Guide]] and
[[CLI Guide|CLI-Guide]].

## Command reference

This page mirrors the output of `hpc-client-gui commands`, which is
authoritative. Run it against your installed version if the two ever disagree.

### Global options

| Option | Meaning |
|---|---|
| `--format {text,json}` | Output format for command results |
| `--quiet` | Suppress non-error output |
| `--verbose` | Enable verbose diagnostics |
| `--timeout TIMEOUT` | Default operation timeout in seconds |
| `--profile PROFILE` | Saved connection profile name |
| `--host HOST` | Host override |
| `--port PORT` | Port override |
| `--transport {sftp,ftp}` | File transport (default `sftp`) |
| `--user USERNAME` | Username override |
| `--key KEY_PATH` | Private-key path override |
| `--password-stdin` | Read the session password from stdin |
| `--password-prompt` | Prompt for the password without echoing (terminal only) |
| `--no-saved-password` | Do not use a profile's stored protected secret; require `--password-stdin` instead |
| `--strict-host-key` | Reject unknown host keys |

### Local commands

| Command | Arguments | Purpose |
|---|---|---|
| `gui` | — | Launch the desktop GUI |
| `version` | — | Print version and build information |
| `commands` | — | Print the full command tree, aliases, and exit codes |

### `profile` — saved connection profiles

| Command | Arguments and options |
|---|---|
| `profile list` | — |
| `profile show` | `name` |
| `profile create` | `name` `[--host]` `[--port]` `[--user]` `[--key]` `[--host-key-policy]` |
| `profile update` | `name` `[--host]` `[--port]` `[--user]` `[--key]` `[--host-key-policy]` |
| `profile delete` | `name` `--yes` |
| `profile test` | `name` |

`profile create` and `profile update` accept non-sensitive fields only.
`profile delete` refuses to run without `--yes`.

### `doctor` — diagnostics

| Command | Options | Purpose |
|---|---|---|
| `doctor environment` | — | Check the local environment |
| `doctor connection` | — | Connect and initialize the file transport |
| `doctor smoke` | `[--keep]` `[--artifact ARTIFACT]` | Round-trip a smoke-test file; `--keep` preserves the remote smoke directory, `--artifact` writes the JSON result to a local path |

See [[Logs and Diagnostics|Logs-and-Diagnostics]].

### `files` — remote file operations

| Command | Arguments and options |
|---|---|
| `files ls` | `[path]` |
| `files stat` | `path` |
| `files checksum` | `path` |
| `files mkdir` | `path` |
| `files upload` | `local_path` `remote_path` `[--recursive]` `[--mode {binary,ascii,auto}]` `[--verify]` `[--if-exists {overwrite,skip,rename,resume}]` |
| `files download` | `remote_path` `local_path` `[--recursive]` `[--mode {binary,ascii,auto}]` `[--verify]` `[--if-exists {overwrite,skip,rename,resume}]` |
| `files cp` | `source` `destination` `[--recursive]` |
| `files mv` | `source` `destination` |
| `files rm` | `path` `[--recursive]` `--yes` |

`--verify` checks the SHA-256 of the transferred file. `files rm` is
destructive and refuses to run without `--yes` (exit code `2`).

### Editing and running

| Command | Arguments and options | Purpose |
|---|---|---|
| `edit` | `remote_path` `[--editor EDITOR]` `[--verify]` | Download, open in a local editor, and upload back. `--editor` defaults to `TRUBA_EDITOR`, then `EDITOR` |
| `sh` | `-- COMMAND [ARG ...]` | Run a single remote command; prefix the command with `--` |
| `run` | `remote_script [ARG ...]` | Run a remote script with arguments |
| `terminal` | `[--cols COLS]` `[--rows ROWS]` | Open an interactive remote terminal |
| `interactive` | — | Open an interactive prompt for this CLI |

### `jobs` — scheduler operations

| Command | Arguments and options |
|---|---|
| `jobs list` | — |
| `jobs status` | `job_id` |
| `jobs accounting` | — |
| `jobs lssrv` | — |
| `jobs submit` | `script` `--yes` |
| `jobs cancel` | `job_id` `--yes` |

`jobs submit` and `jobs cancel` change cluster state and refuse to run without
`--yes`.

### Aliases

| Alias | Expands to |
|---|---|
| `ls` | `files ls` |
| `stat` | `files stat` |
| `checksum` | `files checksum` |
| `mkdir` | `files mkdir` |
| `put` | `files upload` |
| `get` | `files download` |
| `cp` | `files cp` |
| `mv` | `files mv` |
| `rm` | `files rm` |
| `squeue` | `jobs list` |
| `scontrol` | `jobs status` |
| `sacct` | `jobs accounting` |
| `sbatch` | `jobs submit` |
| `scancel` | `jobs cancel` |
| `lssrv` | `jobs lssrv` |

The aliases are named after the familiar Slurm and shell commands, but they run
through this application's own dispatch — they are not passthroughs.

## Output contract

Every command honours `--format {text,json}`. The contract below is enforced by
`src/hpc_gui/cli/errors.py` and documented canonically in
`docs/cli/exit_codes.md`.

### Success output

- **Text mode** (default): human-readable results on `stdout`.
- **JSON mode**: a single parseable object on `stdout`.

```bash
hpc-client-gui --format json commands
```

`--quiet` suppresses non-error output; `--verbose` adds diagnostics. Neither
changes the exit code.

### Error output

Failures are routed through `emit_error`:

- **Text mode** — an actionable human message on `stderr`, with the underlying
  detail preserved.
- **JSON mode** — a single object on `stdout`:

```json
{
  "error": {
    "message": "...",
    "exit_code": 1
  }
}
```

### The no-duplication rule

The same message text is never emitted twice. In text mode it appears only on
`stderr`; in JSON mode it appears only inside the `message` field. A parser
consuming JSON on `stdout` will not also find the message on `stderr`, and a
shell script capturing `stderr` in text mode will not find a stray copy on
`stdout`.

### Consuming the output

```bash
if output=$(hpc-client-gui --format json files ls /home/$USER); then
  printf '%s\n' "$output" | jq '.'
else
  status=$?
  printf '%s\n' "$output" | jq -r '.error.message'
  exit "$status"
fi
```

`exit_code` inside the error object matches the process exit status, so either
source is usable — but the process exit status is the simpler one to branch on.

## Exit codes

The command-line interface has a stable numeric exit-code contract. The
constants live in `src/hpc_gui/cli/errors.py` (`ExitCode`) and the canonical
table is `docs/cli/exit_codes.md` in the repository. This page cites that
table; it does not fork it.

| Exit code | Name | Meaning |
|---|---|---|
| `0` | `SUCCESS` | The command completed successfully. |
| `1` | `OPERATION_FAILED` | Generic operation failure — for example a failed file operation, or `profile show` for a name that does not exist. |
| `2` | `USAGE` | Usage error or refused confirmation: an unsupported subcommand or argument, or a destructive command such as `files rm` issued without `--yes`. Argument-parsing errors also exit `2`. |
| `3` | `CONNECTION` | Connection failure while opening a session. Requesting a missing profile for a connection maps here. |
| `124` | `TIMEOUT` | The operation timed out. |

### Notes for automation

- Branch on the exit code, never on message text. Messages are localized and
  may be reworded; codes are contractual.
- `2` means *you asked for something the interface would not do* — usually a
  missing `--yes` on a destructive command. Retrying without fixing the
  invocation will fail identically.
- `3` distinguishes "could not reach or authenticate to the cluster" from "the
  operation ran and failed" (`1`). Retry logic belongs on `3`, not on `1`.
- `124` follows the conventional timeout code. `--timeout` sets the connection
  knobs and the default per-operation timeout.

## See also

[[Scripting Examples|Scripting-Examples]] · [[Settings Reference|Settings-Reference]] · [[Security Model|Security-Model]]
