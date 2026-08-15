# CLI Overview

> Türkçe: [[CLI-Overview-TR]]

The application ships a command-line interface alongside the desktop GUI. It
exists so that connection profiles, file operations, and Slurm job operations
can be scripted without a GUI session.

## Invoking it

```bash
python -m hpc_gui --help
```

`hpc-client-gui` is the program name shown in help output. The packaged
Windows and Linux builds expose the same interface.

## Discovering commands

```bash
hpc-client-gui commands
hpc-client-gui --format json commands
```

`commands` prints the full command tree, every option, the alias table, and the
exit-code table. It is the authoritative inventory; this wiki mirrors it in
[[CLI Command Reference|CLI-Command-Reference]].

## The external access gate

Remote commands are gated. **"Allow external CLI access to remote commands"**
in Settings is **off by default**. While it is off, commands that reach the
cluster refuse to run and print:

> Remote CLI access is disabled. Enable "Allow external CLI access to remote
> commands" in Settings to use this command.

When the setting is on, any local process running this application's
command-line interface can reach remote commands — files, jobs, edit, shell,
and diagnostics — using saved profiles, without a GUI session. Settings also
lets you choose a default CLI profile used when a command omits `--profile`.
See [[Settings Reference|Settings-Reference]] and
[[Security Model|Security-Model]].

## Global options

These apply to every command and are listed in full in
[[CLI Command Reference|CLI-Command-Reference]]:

| Option | Purpose |
|---|---|
| `--format {text,json}` | Output format for command results |
| `--quiet` | Suppress non-error output |
| `--verbose` | Enable verbose diagnostics |
| `--timeout TIMEOUT` | Default operation timeout in seconds |
| `--profile PROFILE` | Saved connection profile name |
| `--host`, `--port`, `--user`, `--key` | Per-invocation connection overrides |
| `--transport {sftp,ftp}` | File transport, default `sftp` |
| `--password-stdin` | Read the session password from stdin |
| `--password-prompt` | Prompt without echoing (terminal only) |
| `--no-saved-password` | Ignore a profile's stored secret |
| `--strict-host-key` | Reject unknown host keys |

## Output and exit codes

Results are printed as text or as JSON, and every invocation ends with a
documented exit code. Automation should branch on the exit code, not on
message text. See [[CLI Output Contract|CLI-Output-Contract]] and
[[CLI Exit Codes|CLI-Exit-Codes]].

## Next steps

[[CLI Command Reference|CLI-Command-Reference]] ·
[[Scripting Examples|Scripting-Examples]]
