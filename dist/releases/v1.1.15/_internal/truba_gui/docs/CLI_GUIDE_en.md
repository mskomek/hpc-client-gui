# HPC Client GUI — Command-Line Guide (CLI)

> This guide documents the HPC Client GUI command-line interface (CLI) end to end: connection profiles, diagnostics, remote file operations, scheduler operations, and launching the desktop GUI.

## Introduction

The command-line interface lets you use HPC Client GUI without the graphical interface. On TRUBA or similar **Slurm-based HPC** systems you can manage saved connection profiles, diagnose the local environment and the connection, perform remote file-transfer operations, and submit or cancel jobs on the scheduler. You can also launch the desktop GUI from this interface.

From a source checkout:

```bash
python -m truba_gui <command> [options]
```

The packaged executable also exposes the same interface as `hpc-client-gui <command> [options]`.

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
| `--strict-host-key` | Reject unknown remote host keys (the opposite of the default accept-new policy). |

---

## Command groups

### `gui`

Launch the desktop GUI. No arguments.

```bash
python -m truba_gui gui
```

### `version`

Print version and build information. No arguments.

```bash
python -m truba_gui version
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
python -m truba_gui profile create myprofile --host hpc.example --port 22 --user myuser

# Update the profile
python -m truba_gui profile update myprofile --host hpc.example --host-key-policy strict

# Delete the profile (confirmation required)
python -m truba_gui profile delete myprofile --yes
```

### `doctor`

Run local diagnostics. Subcommands: `environment`, `connection`, `smoke`.

- `hpc-client-gui doctor environment` — Inspect the local runtime environment.
- `hpc-client-gui doctor connection` — Connect and initialize the remote file transport.
- `hpc-client-gui doctor smoke [--keep] [--artifact ARTIFACT]` — Round-trip a smoke-test file over the remote file transport; `--keep` preserves the remote smoke directory instead of deleting it; `--artifact ARTIFACT` writes the smoke result JSON to the given local path.

```bash
python -m truba_gui doctor environment
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
python -m truba_gui files download /remote/path/run.sh /local/path/run.sh --if-exists skip

# Upload a local file and verify
python -m truba_gui files upload /local/path/run.sh /remote/path/run.sh --verify

# Remove a remote directory (confirmation required)
python -m truba_gui files rm /remote/path/old_dir --recursive --yes
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
python -m truba_gui jobs submit /remote/path/run.sh --yes

# Cancel a job (confirmation required)
python -m truba_gui jobs cancel 12345 --yes
```

---

## Exit codes

| Exit code | Name | Meaning |
|---|---|---|
| `0` | `SUCCESS` | The command completed successfully. |
| `1` | `OPERATION_FAILED` | Generic operation failure (for example an unknown profile name for `profile show`). |
| `2` | `USAGE` | Usage error or confirmation refusal (unsupported subcommand/argument, or a mutating command issued without `--yes`). argparse's own parsing errors also exit with `2`. |
| `3` | `CONNECTION` | Connection failure while opening a session (for example a missing profile explicitly requested via `--profile`). |
| `124` | `TIMEOUT` | A remote operation timed out; the `--timeout` global option sets the default per-operation timeout. |

---

## Text/JSON output contract

When a command fails, output is produced according to the selected format:

- **Text mode:** an actionable error message is written to **stderr**.
- **JSON mode:** a single parseable object is written to **stdout** in the form `{"error": {"message": "...", "exit_code": N}}`.

The same message text is never duplicated between the two formats: the message appears only on stderr in text mode and only inside the `message` field in JSON mode.

---

## Closing note

This guide and its Turkish counterpart (`CLI_GUIDE_tr.md`, already written) cover identical commands and topics. If this document and the live output ever disagree, `hpc-client-gui --help` (or `python -m truba_gui --help` in a source checkout) is always the final authority.
