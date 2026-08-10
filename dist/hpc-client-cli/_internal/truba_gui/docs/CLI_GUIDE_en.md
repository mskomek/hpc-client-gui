# HPC Client GUI — Command-Line Guide (CLI)

> This guide documents the HPC Client GUI command-line interface (CLI) end to end: connection profiles, diagnostics, remote file operations, scheduler operations, and launching the desktop GUI.

## Introduction

The command-line interface lets you use HPC Client GUI without the graphical interface. On TRUBA or similar **Slurm-based HPC** systems you can manage saved connection profiles, diagnose the local environment and the connection, perform remote file-transfer operations, and submit or cancel jobs on the scheduler. You can also launch the desktop GUI from this interface.

```bash
hpc-client-gui <command> [options]
```

(From a source checkout, run the same commands as `python -m truba_gui <command> [options]` instead.)

> Note: this CLI's remote calls depend on real network connectivity and real cluster state. This guide cannot guarantee live-cluster behavior; if you encounter unexpected results, refer to the relevant exit code and error message.

---

## Global options

The following options apply to all command groups and are usually written before the subcommand:

| Option | Description |
|---|---|
| `--format {text,json}` | Output format for command results. |
| `--quiet` | Suppress non-error output. |
| `--verbose` | Enable verbose diagnostics. |
| `--timeout TIMEOUT` | Default operation timeout in seconds. |
| `--profile PROFILE` | Saved connection profile name. |
| `--host HOST` | remote host override for the connection. |
| `--port PORT` | remote port override for the connection. |
| `--user USERNAME` | remote username override for the connection. |
| `--key KEY_PATH` | private-key path override for the connection. |
| `--password-stdin` | Read the remote password value from stdin rather than accepting it as a bare command-line argument. |
| `--no-saved-password` | Do not use a profile's saved DPAPI-protected secret; require `--password-stdin` instead. |
| `--strict-host-key` | Reject unknown remote host keys; changed keys are always rejected. |

The default `accept-new` CLI policy saves the first observed key in `~/.truba_slurm_gui/known_hosts` and verifies it on later connections. The GUI asks whether to trust and save, trust once, or cancel. If a saved key changes, both interfaces cancel the connection; verify the new fingerprint before removing that host's line from this file.

### Saved-secret resolution order (`--profile`)

When `--profile NAME` is used and `--password-stdin` is not given, the CLI resolves the connection secret in this order:

1. If `--no-saved-password` is set, or the profile uses key-based auth (`--key`/a saved key path), no saved secret is used — the connection proceeds with no password unless `--password-stdin` is also given.
2. Otherwise, if the profile has a saved DPAPI-protected secret (the same one the GUI's "remember password" flow writes) and the OS credential store is available (Windows only), that secret is decrypted in-memory and used.
3. Otherwise, the connection proceeds with no password unless `--password-stdin` is given.

The decrypted secret is never printed, logged, or included in `--verbose` output or JSON results.

### External CLI access, the default profile, and the command inventory

Two settings in the GUI's **Settings → Connection and X11** dialog control how this CLI reaches saved profiles:

- **Allow external CLI access to remote commands** (the `cli_external_access_enabled` setting, off by default). While it is off, every remote-session command — `files *`, `jobs *`, `edit`, `sh`, `run`, `terminal`, `profile test`, `doctor connection`, `doctor smoke` — fails with one message naming the toggle and exits with code `1` (`OPERATION_FAILED`), before any connection attempt. `profile list`, `profile show`, `doctor environment`, `version`, `gui`, and `commands` are always available.
- **Default CLI profile** (the `cli_default_profile` setting). When `--profile` is omitted, the CLI uses the saved default profile; an explicit `--profile` always overrides it. A configured default that no longer exists among saved profiles still produces the existing `Profile not found: NAME` error.

Independently of the two settings above, each saved connection also carries its own **"Allow this connection to be used from the CLI"** checkbox (the profile's `cli_allowed` field, off by default, in the connection's add/edit dialog). A profile used with `--profile NAME` that has this checkbox unchecked fails with `Profile 'NAME' is not allowed for CLI use.` before any connection attempt, even when external CLI access is enabled globally. Existing saved connections default to disallowed until edited and re-saved with the checkbox on.

> **Security note:** enabling external CLI access grants **any local process** that can run this application's executable the same remote command surface as the GUI's saved profiles. This is a broad, host-level trust decision, not a per-tool permission — the toggle is off by default for this reason. The per-connection checkbox narrows that surface to only the profiles you explicitly opt in.

The `commands` subcommand prints the command inventory for scripting and automation: all command paths, options, and the exit-code table. Append `--help` to a command for its detailed help. It honors `--format text|json` and is always available. Global flags must precede the subcommand:

```bash
# Text mode
hpc-client-gui commands

# JSON mode
hpc-client-gui --format json commands
```

Verify help with the packaged EXE on Windows:

```cmd
set "EXE=D:\Projeler\truba-client-gui_windows_onedir\hpc-client-gui.exe"
"%EXE%" --help
"%EXE%" --format json commands
"%EXE%" files upload --help
"%EXE%" jobs submit --help
"%EXE%" --format json version
```

These commands run without opening the GUI. From a source checkout, use the equivalent `python -m truba_gui ...` form. The `version` result identifies the EXE being run; an older packaged EXE may report a different version from the source tree.

---

## Command groups

### `gui`

Launch the desktop GUI. No arguments.

```bash
hpc-client-gui gui
```

### `version`

Print version and build information. No arguments.

```bash
hpc-client-gui version
```

### `profile`

Manage saved connection profiles. Subcommands: `list`, `show`, `create`, `update`, `delete`, `test`.

- `hpc-client-gui profile list` — List profile names without secrets.
- `hpc-client-gui profile show NAME` — Show a profile without secrets.
- `hpc-client-gui profile create NAME [--host HOST] [--port PORT] [--user USERNAME] [--key KEY_PATH] [--host-key-policy {accept-new,strict}]` — Create a profile with non-sensitive fields only.
- `hpc-client-gui profile update NAME [--host HOST] [--port PORT] [--user USERNAME] [--key KEY_PATH] [--host-key-policy {accept-new,strict}]` — Update non-sensitive fields of a profile (has the same flag structure as `create`).
- `hpc-client-gui profile delete NAME [--yes]` — Delete a profile; refuses without `--yes`.
- `hpc-client-gui profile test NAME` — Verify a saved profile's connection.

**Mutating commands:** `profile delete` is refused without any action being taken if the `--yes` flag is not given. `profile create` and `profile update` operate on non-sensitive fields; secret fields (such as passwords) are not set by these commands.

```bash
# Create a profile (non-sensitive fields)
hpc-client-gui profile create myprofile --host hpc.example --port 22 --user myuser

# Update the profile
hpc-client-gui profile update myprofile --host hpc.example --host-key-policy strict

# Delete the profile (confirmation required)
hpc-client-gui profile delete myprofile --yes
```

### `doctor`

Run local diagnostics. Subcommands: `environment`, `connection`, `smoke`.

- `hpc-client-gui doctor environment` — Inspect the local runtime environment.
- `hpc-client-gui doctor connection` — Connect and initialize the remote file transport.
- `hpc-client-gui doctor smoke [--keep] [--artifact ARTIFACT]` — Round-trip a smoke-test file over the remote file transport; `--keep` preserves the remote smoke directory instead of deleting it; `--artifact ARTIFACT` writes the smoke result JSON to the given local path.

```bash
hpc-client-gui doctor environment
```

### `files`

Remote file operations. All subcommands operate on remote paths over the remote file transport; the CLI layer itself never composes remote command text. Subcommands: `ls`, `stat`, `checksum`, `mkdir`, `upload`, `download`, `cp`, `mv`, `rm`.

- `hpc-client-gui files ls [REMOTE_PATH]` — List a remote directory; when the path is omitted, `.` (the current remote directory) is used.
- `hpc-client-gui files stat REMOTE_PATH` — Show remote file metadata.
- `hpc-client-gui files checksum REMOTE_PATH` — Show a remote file's SHA-256.
- `hpc-client-gui files mkdir REMOTE_PATH` — Create a remote directory.
- `hpc-client-gui files upload LOCAL_PATH REMOTE_PATH [--recursive] [--mode {binary,ascii,auto}] [--verify] [--if-exists {overwrite,skip,rename,resume}]` — Upload a local file or directory; `--verify` checks SHA-256 after upload; `--if-exists` controls the conflict policy when the remote destination already exists.
- `hpc-client-gui files download REMOTE_PATH LOCAL_PATH [--recursive] [--mode {binary,ascii,auto}] [--verify] [--if-exists {overwrite,skip,rename,resume}]` — Download a remote file or directory; has the same flag structure as `upload`.
- `hpc-client-gui files cp REMOTE_SRC REMOTE_DST [--recursive]` — Copy a remote file or directory.
- `hpc-client-gui files mv REMOTE_SRC REMOTE_DST` — Move or rename a remote path.
- `hpc-client-gui files rm REMOTE_PATH [--recursive] [--yes]` — Remove a remote path; refuses without `--yes`.

**Mutating commands:** `files rm` is refused without any remote action being taken if the `--yes` flag is not given. For `files upload` and `files download`, the `--if-exists` policy applies when the destination already exists; `--verify` checks integrity after the transfer.

```bash
# Download a remote file (skip if the destination already exists)
hpc-client-gui files download /remote/path/run.sh /local/path/run.sh --if-exists skip

# Upload a local file and verify
hpc-client-gui files upload /local/path/run.sh /remote/path/run.sh --verify

# Remove a remote directory (confirmation required)
hpc-client-gui files rm /remote/path/old_dir --recursive --yes
```

### `jobs`

Scheduler operations. Runs through the existing scheduler service; the CLI layer itself never composes scheduler command text. Subcommands: `list`, `status`, `accounting`, `lssrv`, `submit`, `cancel`.

- `hpc-client-gui jobs list` — List the user's queued and running jobs.
- `hpc-client-gui jobs status JOB_ID` — Show the state of a single job.
- `hpc-client-gui jobs accounting` — Show accounting data for the user's jobs.
- `hpc-client-gui jobs lssrv` — Show login-node cluster state.
- `hpc-client-gui jobs submit SCRIPT [--yes]` — Submit a batch script to the scheduler; refuses without `--yes`; the script path is a remote path.
- `hpc-client-gui jobs cancel JOB_ID [--yes]` — Cancel a queued or running job; refuses without `--yes`. Rejects a job ID containing unsafe characters before ever attempting a connection; accepts plain numeric IDs and array-task/step forms such as `12345_3` or `12345.0`.

**Mutating commands:** `jobs submit` and `jobs cancel` are refused without any remote action being taken if the `--yes` flag is not given.

```bash
# Submit a batch script (confirmation required)
hpc-client-gui jobs submit /remote/path/run.sh --yes

# Cancel a job (confirmation required)
hpc-client-gui jobs cancel 12345 --yes
```

### Shortcuts, FTP, and remote shell

Root shortcuts map to the canonical handlers: `put`/`get` map to file upload/download; `ls`, `stat`, `checksum`, `mkdir`, `cp`, `mv`, and `rm` map to matching file commands; `squeue`, `scontrol`, `sacct`, `lssrv`, `sbatch`, and `scancel` map to the matching jobs commands. `hpc-client-gui --format json commands` lists the same mappings in its `aliases` field.

File commands use SFTP by default. Use `--transport ftp` explicitly for file-only FTP operations; scheduler and shell commands require SFTP/SSH. FTP metadata and SHA-256 are computed through the file backend and never invoke a remote shell.

Remote edit and shell commands:

- `hpc-client-gui edit REMOTE [--editor PROGRAM] [--verify]` — Download, edit, conflict-check, and upload a remote file; unchanged or failed edits are not uploaded.
- `hpc-client-gui sh -- COMMAND [ARG ...]` — Run one explicitly quoted remote command and preserve its stdout, stderr, and exit status.
- `hpc-client-gui run REMOTE_SCRIPT [ARG ...]` — Invoke the remote script with `bash`; the script never runs locally.
- `hpc-client-gui terminal` — Attach to the existing SSH terminal; requires an interactive console.
- `hpc-client-gui interactive` — Use a small text prompt that parses entered commands with the same CLI registry; `exit` and `quit` leave it.

The remote shell commands reject NUL/control characters. `--password-stdin` is intended for automation, while `--password-prompt` is masked and requires a real terminal.

---

## Exit codes

| Exit code | Name | Meaning |
|---|---|---|
| `0` | `SUCCESS` | The command completed successfully. |
| `1` | `OPERATION_FAILED` | Generic operation failure (for example an unknown profile name for `profile show`). |
| `2` | `USAGE` | Usage error or confirmation refusal (unsupported subcommand/argument, or a mutating command issued without `--yes`). argparse's own parsing errors also exit with `2`. |
| `3` | `CONNECTION` | Connection failure while opening a session (for example a missing profile explicitly requested via `--profile`). |
| `124` | `TIMEOUT` | A remote operation timed out; the `--timeout` global option sets the default per-operation timeout. |

### `files` error messages

Remote `files` operations report "not found" and "permission denied" with the affected remote path attached, so the failure shows exactly which path was involved:

| Situation | Result | Exit code |
|---|---|---|
| Remote path does not exist | `Not found: <path>` | `1` (`OPERATION_FAILED`) |
| Access to the remote path is denied | `Permission denied: <path>` | `1` (`OPERATION_FAILED`) |
| `files ls` on an existing, empty directory | Successful empty listing (`[]` in JSON mode) | `0` (`SUCCESS`) |

`<path>` is the remote path the failure refers to, for example `Not found: /remote/path/run.sh` or `Permission denied: /remote/path/run.sh`.

---

## Text/JSON output contract

When a command fails, output is produced according to the selected format:

- **Text mode:** an actionable error message is written to **stderr**.
- **JSON mode:** a single parseable object is written to **stdout** in the form `{"error": {"message": "...", "exit_code": N}}`.

The same message text is never duplicated between the two formats: the message appears only on stderr in text mode and only inside the `message` field in JSON mode.

---

## Closing note

This guide and its Turkish counterpart (`CLI_GUIDE_tr.md`, already written) cover identical commands and topics. If this document and the live output ever disagree, `hpc-client-gui --help` (or `python -m truba_gui --help` in a source checkout) is always the final authority.
