# CLI Command Reference

> Türkçe: [[CLI-Command-Reference-TR]]

This page mirrors the output of `hpc-client-gui commands`, which is
authoritative. Run it against your installed version if the two ever disagree.

## Global options

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

## Local commands

| Command | Arguments | Purpose |
|---|---|---|
| `gui` | — | Launch the desktop GUI |
| `version` | — | Print version and build information |
| `commands` | — | Print the full command tree, aliases, and exit codes |

## `profile` — saved connection profiles

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

## `doctor` — diagnostics

| Command | Options | Purpose |
|---|---|---|
| `doctor environment` | — | Check the local environment |
| `doctor connection` | — | Connect and initialize the file transport |
| `doctor smoke` | `[--keep]` `[--artifact ARTIFACT]` | Round-trip a smoke-test file; `--keep` preserves the remote smoke directory, `--artifact` writes the JSON result to a local path |

See [[Logs and Diagnostics|Logs-and-Diagnostics]].

## `files` — remote file operations

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

## Editing and running

| Command | Arguments and options | Purpose |
|---|---|---|
| `edit` | `remote_path` `[--editor EDITOR]` `[--verify]` | Download, open in a local editor, and upload back. `--editor` defaults to `TRUBA_EDITOR`, then `EDITOR` |
| `sh` | `-- COMMAND [ARG ...]` | Run a single remote command; prefix the command with `--` |
| `run` | `remote_script [ARG ...]` | Run a remote script with arguments |
| `terminal` | `[--cols COLS]` `[--rows ROWS]` | Open an interactive remote terminal |
| `interactive` | — | Open an interactive prompt for this CLI |

## `jobs` — scheduler operations

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

## Aliases

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

## See also

[[CLI Exit Codes|CLI-Exit-Codes]] ·
[[CLI Output Contract|CLI-Output-Contract]] ·
[[Scripting Examples|Scripting-Examples]]
