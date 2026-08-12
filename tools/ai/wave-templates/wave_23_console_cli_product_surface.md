# Wave 23 — First-Class Console CLI Product Surface

Status: waiting
Owner: Codex
Priority: P1
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Ship a separate Windows console application beside the GUI release. Users,
scripts, scheduled jobs, and external tools must be able to operate the same
saved profiles and shared services without launching Qt or losing stdin/stdout.

Every release contains:

- `hpc-client-gui.exe`: unchanged windowed desktop application.
- `hpc-client-cli.exe`: console-subsystem application with stdout, stderr,
  exit codes, stdin, optional masked password prompt, and no Qt startup.

The console executable retains the canonical argparse tree and adds familiar
file, terminal, FTP/SFTP, and Slurm shortcuts. Shortcuts normalize into existing
handlers; they never create a second connection, transfer, scheduler, parsing,
or error implementation.

## Why This Wave Exists

- The current GUI executable is built with `console=False`; CMD execution has
  unreliable output and `sys.stdin` can be `None`.
- The repository already has CLI handlers, saved profiles, SSH/SFTP and FTP
  backends, Slurm services, editor read/write paths, an SSH terminal, command
  inventory, bilingual guides, and localhost virtual-server tests.
- Release verification must exercise a packaged console executable rather than
  only source imports or the windowed executable.

## Dependencies

- Wave 12: saved-profile CLI access and command inventory.
- Wave 15: GUI `.sh` Save & Run remains GUI-owned.
- Wave 19: offline integration and CI gates.
- Wave 20: version and release consistency.
- Wave 21: shared Slurm behavior.
- Wave 22: correct FTP/SFTP product terminology.

Queue order still applies. This future-wave manifest does not authorize
skipping an active lower-numbered wave.

## Fixed Product Decisions

1. Keep GUI and CLI as separate executables. Do not make GUI startup open a
   console window.
2. Use a thin console entry point around existing `run_cli()` and never import
   Qt for CLI-only execution.
3. Preserve canonical commands. Short forms are aliases, not replacements.
4. Keep argparse as the single registry used by help, JSON inventory, aliases,
   docs, consistency checks, and release gates.
5. SFTP remains the default file transport. Plain FTP is explicit and reuses
   `FTPFilesBackend`.
6. Never accept plaintext passwords as command-line arguments. Automation uses
   stdin or an approved protected profile value; humans may explicitly request
   a masked console prompt.
7. Aliases retain confirmations, validation, quoting, timeout, cancellation,
   error, and exit-code contracts.
8. Shell and Slurm commands require SSH and reject FTP-only sessions.
9. Tests use localhost disposable servers and fake credentials only. No real
   TRUBA, deployment, publication, or credential access occurs in this wave.

## Required Command Surface

Canonical commands remain:

```text
profile list|show|create|update|delete|test
doctor environment|connection|smoke
files ls|stat|checksum|mkdir|upload|download|cp|mv|rm
jobs list|status|accounting|lssrv|submit|cancel
commands
version
```

Console shortcuts:

```text
put LOCAL REMOTE [--verify] [--if-exists POLICY]
get REMOTE LOCAL [--verify] [--if-exists POLICY]
ls [REMOTE]
stat REMOTE
checksum REMOTE
mkdir REMOTE
cp SOURCE DESTINATION [--recursive]
mv SOURCE DESTINATION
rm REMOTE [--recursive] --yes

squeue
scontrol JOB_ID
sacct
lssrv
sbatch SCRIPT --yes
scancel JOB_ID --yes

edit REMOTE [--editor PROGRAM] [--verify]
sh -- COMMAND [ARG ...]
run REMOTE_SCRIPT [ARG ...]
terminal
interactive
```

Exact mappings:

| Shortcut | Canonical behavior |
|---|---|
| `put` / `get` | `files upload` / `files download` |
| root file aliases | matching `files` subcommand |
| `squeue` | `jobs list` |
| `scontrol` | `jobs status` |
| `sacct` | `jobs accounting` |
| root `lssrv` | `jobs lssrv` |
| `sbatch` | `jobs submit` |
| `scancel` | `jobs cancel` |

## Transport Contract

- `--transport sftp` is the default and uses the existing SSH session and
  `SSHFilesBackend`.
- `--transport ftp` uses `FTPFilesBackend` with explicit host, port, username,
  timeout, and the approved secret-resolution path.
- Explicit transport and port flags are sufficient for this wave; do not add a
  persistence migration solely for FTP.
- File commands and aliases use the selected file backend.
- Scheduler, `sh`, `run`, and `terminal` require SSH and refuse FTP transport.
- Text/JSON output identifies transport without printing credentials.
- Turkish names and binary content round-trip byte-for-byte on both transports.

## Remote Edit Contract

`edit REMOTE` reuses the selected backend:

1. Download to a unique local temporary file.
2. Record initial size and SHA-256.
3. Launch the requested editor or existing configured file association.
4. Wait for the editor process.
5. Upload only if content changed and apply existing conflict policy.
6. Verify upload when requested.
7. Remove the temporary file on success and failure.

Do not add an embedded console editor, plugin framework, watcher, or permanent
cache. Automation can use `get` and `put`.

## Shell and Console Contract

- `sh -- COMMAND ...` runs one explicit remote command and preserves stdout,
  stderr, remote exit status, timeout, and cancellation.
- `run REMOTE_SCRIPT ...` quotes the path and arguments and invokes remote
  `bash`; it never runs the script locally.
- `terminal` attaches the existing interactive SSH shell until exit/EOF and
  forwards terminal resize where supported.
- `interactive` is a small stdlib line prompt such as `truba[arf]>`; entered
  commands are parsed by the same argparse registry.
- History may reuse the existing history service. Do not add curses,
  prompt-toolkit, a TUI framework, daemon, or plugin system.
- JSON/non-interactive mode never emits prompts or terminal decoration.

## Packets

### DS-23A — Separate console executable and entry point (Medium)

- Add the thinnest console entry point around `run_cli()`.
- Add a dedicated PyInstaller console spec/config with `console=True` and no Qt
  import for CLI-only commands.
- Keep GUI packaging/startup unchanged.
- Verify help, version, inventory, text/JSON, stderr, exit codes, stdin, and
  `--password-stdin` in CMD and PowerShell.
- Add explicit masked `--password-prompt` via `getpass` only when requested and
  attached to a terminal.
- Missing stdin or a non-interactive prompt request returns an actionable CLI
  error, never a traceback.

Allowed: console entry module, console spec/config, packaging script, focused
CLI/release tests. Forbidden: GUI startup changes, new CLI framework, plaintext
password arguments, or duplicate parsers.

### DS-23B — Root aliases and normalization (Medium)

- Add every listed file and Slurm alias to the existing parser.
- Normalize aliases into canonical namespaces before execution.
- Preserve canonical output and exit contracts.
- Inventory JSON includes aliases with `alias_for`.
- Test every alias/canonical pair for equivalent service calls, confirmations,
  text/JSON results, and errors.

Allowed: parser/normalization modules and focused CLI tests. Forbidden: service
rewrites, new scheduler behavior, or relaxed confirmations.

### DS-23C — SFTP/FTP transfer parity (Medium)

- Select an existing backend through `--transport`.
- Cover upload/download, list/stat, mkdir, copy/move/remove, overwrite/skip/
  rename/resume, binary data, Turkish paths, and useful failures.
- Unsupported transport capabilities return stable actionable errors.
- Preserve protected profile/stdin/prompt rules and secret redaction.

Allowed: thin backend selection, existing file services, focused tests, and the
localhost FTP/SFTP harness. Forbidden: second FTP backend, network discovery,
schema migration, or live servers.

### DS-23D — Remote edit lifecycle (Medium)

- Implement the Remote Edit Contract using stdlib temporary/process helpers,
  existing file associations, and existing file services.
- Preserve remote content on editor failure, cancellation, or no change.
- Detect remote conflicts before upload; never silently overwrite a remotely
  changed file.
- Test success, unchanged file, editor failure, conflict, upload failure,
  verification mismatch, and temporary cleanup.

Allowed: one small edit helper, existing config/file services, focused tests.
Forbidden: embedded editor, permanent cache, watcher, or GUI editor changes.

### DS-23E — Shell, script run, terminal, and interactive prompt (Medium)

- Implement `sh`, `run`, `terminal`, and `interactive` through existing SSH,
  terminal, history, parser, and output services.
- Quote script paths and arguments and reject NUL/control characters.
- Preserve stdout, stderr, remote status, timeout, cancellation, and disconnect
  diagnostics.
- Test localhost PTY resize, Ctrl+C/EOF, spaces in paths, nonzero exit, timeout,
  and disconnect.

Allowed: thin CLI orchestration, existing SSH/terminal/history services,
virtual-server support, focused tests. Forbidden: local shell execution,
unquoted command construction, or a new terminal engine.

### DS-23F — Packaging, docs, and mandatory virtual-server gate (Medium)

- Package both executables in the canonical version directory and onedir ZIP.
- Verify both executable versions and final archive hashes against the release
  version source.
- Run the packaged console executable through virtual profile login, SFTP/FTP
  transfer, remote edit, `sh`, remote script execution, interactive terminal,
  Slurm aliases, cleanup, and negative cases.
- Local test credentials remain `test`/`test`; release ports are ephemeral.
- Update Turkish/English CLI guides, help, changelog, and inventory together.
- Block release for any missing executable/guide/inventory entry, failed
  operation/cleanup, hash mismatch, or version mismatch.

Allowed: packaging/release scripts, existing virtual harness, paired docs,
changelog, release tests. Forbidden: publication, deployment, live TRUBA, real
credentials, or loose release assets.

### DS-23G — Future command parity and extension gate (Small)

- Compare argparse inventory, alias metadata, both guides, virtual-server
  coverage, and release smoke expectations.
- Every future GUI remote action is classified as shared CLI command,
  documented GUI-only action with rationale, or unsupported.
- Every future CLI command declares transport, mutability, confirmation,
  text/JSON output, timeout/cancellation, docs, and offline coverage.
- Missing declarations fail CI/release.
- Keep metadata beside the parser or in one small registry. Do not introduce
  plugins, dynamic loading, duplicated implementations, or code generation.

## Explicitly Deferred

- Live TRUBA verification remains separately authorized.
- SSH agent redesign, hardware tokens, Kerberos, MFA automation, and remote
  credential provisioning require separate security work.
- Tunnels, X11 aliases, rsync, SCP, WebDAV, object storage, containers, remote
  package installation, and cluster provisioning are not added here.
- Rich full-screen TUI, completion daemon, scripting language, plugins, and
  remote API/server modes wait for measured demand.
- Persisted per-profile FTP transport fields wait until explicit flags prove
  insufficient.

Deferred ideas become later wave files only with repository evidence and user
value; they are not silently appended while Wave 23 executes.

## Validation

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_cli.py -q
python -m unittest tests/test_mock_cluster_roundtrip.py
python -m unittest tests/test_editor_flow.py
python scripts/check_i18n.py
powershell -NoProfile -File scripts/test_release_smoke_cli_gate.ps1
powershell -NoProfile -File scripts/release_smoke.ps1 -ExePath <GUI_EXE> -CliExePath <CLI_EXE>
git diff --check
git status --short
```

Also observe:

- CMD stdin, masked prompt, stdout/stderr, and `%ERRORLEVEL%`.
- PowerShell text/JSON, redirection, and pipeline stdin.
- Packaged CLI canonical/alias parity with no Qt startup.
- Virtual SFTP login, transfers, edit, checksum, shell, script, terminal,
  Slurm, and cleanup.
- Virtual FTP transfers, metadata, Turkish/binary data, conflicts, and cleanup.
- Packaged GUI startup remains unchanged.

## Done Criteria

1. Every release contains working GUI and CLI executables without changing the
   other's subsystem/startup behavior.
2. CMD and PowerShell preserve console I/O, errors, exit codes, stdin, and an
   explicit masked prompt without leaking secrets.
3. Canonical commands remain compatible; aliases use identical handlers,
   validation, confirmations, and result contracts.
4. SFTP and opt-in FTP cover transfers, metadata, conflicts, Turkish paths,
   binary content, and cleanup.
5. Remote edit safely downloads, edits, detects changes/conflicts, uploads,
   verifies, and cleans temporary data.
6. One-shot shell, remote script, interactive terminal, and interactive prompt
   reuse existing SSH/terminal services and preserve diagnostics.
7. Slurm aliases cover queue, status, accounting, server state, submit, and
   cancel without weakening safety.
8. The packaged CLI passes the localhost virtual TRUBA/FTP release gate.
9. Bilingual guides/help, inventory, aliases, tests, hashes, and versions are
   synchronized and release-blocking.
10. Future commands fail consistency checks unless safety, transport, output,
    documentation, and offline test obligations are complete.

## Possible Blockers

- Packaging may assume exactly one executable; update that assumption without
  weakening canonical release-folder rules.
- `console=True` may pull Qt through imports; split only the entry import
  boundary, not CLI business logic.
- Reuse the existing credential store; never invent another one.
- FTP cannot run shell/checksum tools; report capability limits and verify
  transfer bytes locally.
- Interactive tests must use deterministic local prompts/events and bounded
  timeouts rather than strict timing.

## Completion Notes

- Completed at:
- Packet verdicts:
- Files changed:
- Tests and exit codes:
- Release artifacts:
- Remaining uncertainty:

## On Completion

- Codex fills Completion Notes and archives this wave only through the queue
  manager after every packet and exit gate have PASS evidence.
- Stop after Wave 23 archival; do not start a later wave in the same prompt.
