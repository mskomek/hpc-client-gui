# Changelog

## v1.2.0

### Licensing Change

Starting with v1.2.0 the project moves from the MIT License to the PolyForm
Noncommercial License 1.0.0, with a separate commercial license path available
(see `COMMERCIAL_LICENSE.md`). Prior releases remain MIT-licensed; the MIT
grant for those releases is not revoked.

### Stability
- Transfers: fixed a native crash that could happen on app shutdown while a
  download/upload planning thread was still active — the thread is now kept
  alive until it actually finishes instead of being torn down mid-run, and
  its completion callbacks now guard against a panel that was already closed.
- Transfers: SFTP transfer channels now use a bounded socket timeout, so a
  silently dropped connection surfaces as a failed transfer instead of
  freezing the queue at 100% forever.

### Crash Reporting
- Added a crash dialog that appears automatically after an unexpected error
  (and again on the next startup if the app closed unexpectedly), plus a
  permanent "Send Logs" toolbar button for reviewing and sharing logs anytime.

### Privacy
- Logs and diagnostics exports now redact the local Windows username and any
  saved connection profile's username/hostname before they can be copied,
  exported, or shown in a crash summary.
- Diagnostics export no longer includes `config.json` (which holds saved
  connection profiles and encrypted password data); it was never needed for
  log-based debugging.

## Unreleased

## v1.1.21
- Release pipeline: restore the Windows offline CI environment, require workflow changes to be committed before the version/changelog release commit, and keep generated packages out of Git.

## v1.1.20
- CLI: the packaged console executable now opens the `truba>` interactive prompt when run without a command, instead of attempting to load the desktop GUI.
- Release: bumped the application and CLI version to 1.1.20.

## v1.1.19
- Release: bumped the application, GUI package, CLI, and release metadata to
  1.1.19.
- CLI: shipped the separate console executable with aliases, explicit
  SFTP/FTP selection, remote edit, quoted shell/script execution, terminal,
  and interactive prompt support.
- Release validation: completed the full local test suite and virtual
  SSH/SFTP/FTP packaged release smoke gate; no live cluster or publication was
  performed.

## v1.1.18
- CLI: added the separate console surface for root aliases, explicit FTP
  selection, remote edit, quoted remote shell/script execution, terminal, and
  interactive prompt; release packaging now carries the console executable.
- Docs: the shipped Help library (`HELP_tr.md`/`HELP_en.md`) no longer tells
  people who downloaded the packaged EXE to install Python/pip and run from
  source; that path is now covered only in the developer README.
- Docs: the CLI guide (`CLI_GUIDE_tr.md`/`CLI_GUIDE_en.md`) now leads every
  example with the packaged `hpc-client-gui` command instead of
  `python -m truba_gui`; the source-checkout form is now a one-line footnote.

## v1.1.17
- Connections: each saved connection now has its own "Allow this connection
  to be used from the CLI" checkbox (off by default for both new and
  existing connections). The CLI refuses `--profile NAME` for a profile
  with the checkbox unchecked, even when the global external CLI access
  toggle is enabled.
- Connections: editing a saved connection that has a stored password
  (Windows-credential-protected or master-password-encrypted) now always
  requires re-entering/validating that password before the edit dialog
  opens, regardless of the connection's password-prompt policy.

## v1.1.16
- CLI: the CLI now resolves an already-saved, DPAPI-protected profile
  password automatically when `--profile NAME` is given, instead of
  requiring `--password-stdin` on every invocation; a new
  `--no-saved-password` flag opts back into the previous stdin-only
  behavior. Falls back unchanged whenever DPAPI is unavailable, no saved
  secret exists, or key-based auth is configured. The resolved value is
  never printed, logged, or included in any output.
- CLI: `files ls/stat/checksum/download/cp/mv/rm` now report "not found" and
  "permission denied" failures with the same message shape and the affected
  remote path attached, instead of raw SFTP/shell error text. An existing,
  empty remote directory still returns a successful empty listing.
- CLI: added a new, off-by-default Settings toggle ("Allow external CLI
  access to remote commands") that gates every remote-session CLI command
  (`files *`, `jobs *`, `profile test`, `doctor connection/smoke`); denied
  commands fail with one clear message before any connection attempt.
  `profile list/show`, `doctor environment`, `version`, `gui`, and the new
  `commands` subcommand stay available regardless.
- CLI: added a saved default-profile setting so `--profile` can be omitted
  on repeated invocations; an explicit `--profile` always overrides it.
- CLI: added a new `commands` subcommand that prints the full command
  inventory (every command path, flag, and help text) plus the exit-code
  table, in text or `--format json`, for scripting and automation.
- CLI: an unknown or incomplete command now prints that command's full help
  text (not just the one-line usage string) before exiting; the root
  `--help` output now includes real, working example invocations.
- Settings: added a checkbox and a saved-profile picker for the two new CLI
  settings above, in the Connection and X11 group.
- Release packaging: packaged releases now include a `help/` folder next to
  the executable with the Turkish and English GUI help and CLI guides; an
  automated release-smoke check fails packaging if any of the four files is
  missing or if a CLI command path is undocumented in either CLI guide.
- Documentation: both CLI guides document the saved-secret resolution order,
  the external-access toggle and its security implications, the
  default-profile fallback, and the `commands` output shape.

## v1.1.15
- CLI: added a full command-line interface (`hpc-client-gui` / `python -m
  truba_gui`) covering connection profiles (`profile list/show/create/
  update/delete/test`), diagnostics (`doctor environment/connection/smoke`),
  remote file operations (`files ls/stat/checksum/mkdir/upload/download/cp/
  mv/rm`), and Slurm job operations (`jobs list/status/accounting/lssrv/
  submit/cancel`), with `--format text|json` output and a documented text/
  JSON error contract. See `CLI_GUIDE_tr.md` and `CLI_GUIDE_en.md`.
- Documentation: added Turkish and English CLI guides and a maintenance/
  GUI-CLI parity policy (`MAINTENANCE_POLICY.md`) describing when a new GUI
  action needs a CLI counterpart and which release gates must stay connected.
- Reliability: increased the default SSH connect/banner timeout (15s/30s to
  45s/45s) so slower VPN or busy login-node connections no longer time out
  prematurely; the timeout remains configurable.
- Tests: fixed a hang in the FTP conflict-resolution test suite (a
  `patch.object` on `RemoteDirPanel._session_conflict_action` was silently
  reverting session state between test steps, causing a later step to fall
  through to a real, unmocked confirmation dialog and block indefinitely).
- Tests: added a local, fully offline SSH/SFTP integration harness
  (`tests/support/mock_ssh_server.py`) that drives the real CLI over an
  actual paramiko wire connection against a disposable local server, proving
  the file-transfer and job-command code paths round-trip correctly without
  any real cluster or credential involved.
- Release quality: added a local, offline gate that runs a Turkish-filename
  transfer round trip and places the `sftp-smoke/1` JSON artifact under the
  version folder; any gate failure stops the release.
- Verification: the CLI's connection, file-transfer, and read-only job
  commands were independently verified end to end against a real TRUBA
  cluster account (authentication, SFTP, checksum, upload/download/copy/
  move/delete round trip, `jobs list/lssrv/accounting`).

## v1.1.14
- Transfers: when uploading or downloading a selected folder into an existing
  folder of the same name, merge the folders and ask only about conflicting
  nested files; preserve the complete subfolder hierarchy in both directions.
- Transfers: an overwrite now deletes each conflicting target immediately
  before its own upload or download, rather than deleting all conflicts first.
- Local files: fixed a Delete-key crash caused by debug telemetry converting a
  Qt keyboard-modifier flag incorrectly.

## v1.1.13
- Branding: renamed the application, CLI, Windows executable, release assets,
  and GitHub update source to HPC Client GUI / `hpc-client-gui`.
- Compatibility: retained the existing `truba_gui` Python module and
  `.truba_slurm_gui` user-data directory so saved profiles, history, and
  settings continue to work.
- Updates: included a one-time legacy-named migration package so v1.1.12
  installations can update to the renamed executable.

## v1.1.12
- Startup: added a branded splash screen and ensured the application icon is used
  consistently for the window and taskbar.
- CLI: added commands for diagnostics, connection profiles, and file operations,
  while preserving normal GUI startup when no command is supplied.
- FTP: added configurable transfer mode, encoding, timeout, passive-mode, and
  keep-alive settings; transfer errors now provide clearer guidance for
  ASCII-mode files that are not valid UTF-8 text.
- Transfers: added queue and connection controls in the Directories view, along
  with safer cancellation, cleanup, and status reporting for SSH and FTP work.
- Jobs & outputs: added detachable output views, adjustable refresh/follow
  behavior, and improved scroll handling for live output.
- Release quality: expanded FTP stress coverage and added build/startup smoke
  checks before release artifacts are packaged.

## v1.1.11
- Transfers: kept large multi-folder uploads and downloads responsive by moving
  recursive planning, remote probing, and delete preparation out of the GUI
  thread; transfer queues now publish bounded updates instead of creating an
  unbounded number of widgets at once.
- Transfers: added an upload preflight review with an opt-out setting, safer
  per-file conflict handling, session-accurate resume speed/ETA, and reliable
  visibility and cancellation for overlapping transfer queues.
- Jobs & outputs: made follow-path fields editable across output slots, tabs,
  and separate windows; submitting a job can now keep the current view, use the
  Outputs tab, or open split/combined follow views according to Settings.
- Directories: improved local/remote transfer integration, added an SH filter,
  and kept long shell-script output in a screen-bounded, scrollable dialog.
- Updates: show changelog entries from newest to oldest after an update.

## v1.1.10
- Updates: show the full changelog from newest to oldest on the first launch after an update and remember the last shown app version.
- File operations: ask separately for each nested file conflict during folder upload and download unless an apply-to-all or queue-wide choice is active.
- Local files: fixed Delete-key removal for non-empty folders by deleting local directories recursively after confirmation.

## v1.1.8
- FTP transfers: fixed configured parallel transfers so multiple uploads or downloads can run at the same time instead of staying sequential.
- FTP transfers: added an embedded progress bar with percentage in the Transfers table and hid internal local setup steps from the visible queue.
- FTP transfers: verified local FTP upload, parallel download, and visible partial-file resume behavior with a temporary FTP server.
- Directories: added Ctrl+C, Ctrl+X, and Ctrl+V support for local and remote file panels, including local-to-remote upload paste and remote-to-local download paste.
- Directories: made the remote path field editable so pressing Enter navigates to the typed path, and Backspace in the remote file list moves to the parent directory.

## v1.1.7
- Directories: added data-aware sorting for Name, Size, Type, and Modified columns while keeping parent and folder rows in the expected positions.
- Live output: kept Output 1 and Output 2 pinned to the newest content during live follow while preserving manual scrolling when follow is paused.
- Live output: reduced SSH and fallback output loading to the latest 200 lines per file.

## v1.1.6
- Connection profiles: grouped TRUBA directories and Slurm commands as editable per-profile system defaults.
- Authentication: allowed profiles without a username or password and added an option to reuse saved Windows-protected credentials without prompting until the profile is edited.
- Activity control: paused `squeue`, `tail`, `lssrv`, accounting, and log refresh operations while their tabs are not visible.
- Responsiveness: moved remote polling and command execution off the GUI thread, prevented overlapping requests, and reduced duplicate SSH/log rendering work.
- Connection console: added right-click paste from the system clipboard into the live SSH shell.
- Directories: added a context-menu action to copy the full remote path including the file name.
- Directories: added New Folder and New File buttons plus a right-click New submenu for creating remote items in the current or selected directory.
- Jobs files: added a refresh button to the Files subtab and F5 refresh support for file panels in Jobs and Directories.

## v1.1.5
- Connection profiles: grouped TRUBA directories and Slurm commands as editable per-profile system defaults.
- Authentication: allowed profiles without a username or password and added an option to reuse saved Windows-protected credentials without prompting until the profile is edited.
- Activity control: paused `squeue`, `tail`, `lssrv`, accounting, and log refresh operations while their tabs are not visible.
- Responsiveness: moved remote polling and command execution off the GUI thread, prevented overlapping requests, and reduced duplicate SSH/log rendering work.

## v1.1.4
- Interface: added the current version to the top bar and switched Jobs, Accounting, `lssrv`, and terminal output areas to dark monospace rendering.
- Updates: added automatic startup checks, a visible download/install progress dialog, and stable versionless release asset names.
- Localization: completed the Turkish and English UI text audit and translated previously hardcoded interface messages.
- Live output: improved Output 1 and Output 2 following with one-second refresh, missing-file retries, automatic bottom scrolling, and a 500-line limit.
- Output controls: added per-panel search plus pause and resume controls without losing the active followed files.
- Job monitoring: added Windows notifications for completed and failed Slurm jobs.

## v1.1.3
- Jobs files: added translated context-menu actions to follow any selected file in Output 1 or Output 2, with independent active sources for both panels.
- Jobs outputs: keep retrying Slurm output and error files while they are waiting to be created.
- Live output: refresh followed files every second, automatically scroll to the newest content, and load at most the latest 500 lines.

## v1.1.2
- Updates: added an in-app GitHub Releases update check, SHA256-verified ZIP download, automatic Windows restart/install flow, install logging, and rollback protection.
- Releases: GitHub Actions now publishes the versioned onedir ZIP and SHA256 as GitHub Release assets.

## v1.1.1
- Jobs outputs: resolved Slurm `%x`, `%j`, and `%A` placeholders so parsed output and error files are followed with `tail`.
- Jobs files: fixed the Output-1 and Output-2 context-menu actions to switch to Outputs, load immediately, and continue live polling.
- Saved profiles: cached the encryption master password only in memory for the application session, cleared it on shutdown, and re-prompted when a profile uses a different master password.

## v1.1.0
- Connection: removed Start Tour from the normal flow and added a dedicated Add Connection dialog plus a Settings dialog for app-level options.
- Saved profiles: added direct connection on double-click and a Connect action to the context menu.
- Connection console: improved login output, prompt rendering, PTY resize handling, and interactive shell routing.
- Terminal rendering: added ANSI/VT emulation so redraw, cursor movement, box drawing, and dialog-style screens render more correctly.
- Navigation: fixed saved session context editing, prevented unwanted auto-switching back to the Connection tab, and improved directory double-click plus parent-folder navigation.
- Jobs: split the Jobs area into clearer Job Details, Files, and Outputs sub-tabs.
- Jobs refresh: added a configurable refresh interval with a 15-second default and an optional persisted setting to refresh `lssrv` on the same timer.
- TRUBA status: added refreshable `lssrv` output with terminal-style rendering in Job Details.
- Slurm submission: added a translated Directories context-menu action for remote `.slurm` and `.sbatch` files.
- Slurm submission: changed SSH-backed `sbatch` execution to run from the remote script's parent directory.
- Localization: fixed Turkish i18n encoding issues so translated strings render correctly.
- X11 and logs: improved X server startup checks, download flow, logging, and shutdown safety.

## 2026-01-31
- Fix: Prevent starting a second VcXsrv instance when the display port is already listening.
- X11: When X11 forwarding is enabled, GUI commands launched from the `SSH$` prompt now use the system `ssh/plink` path instead of Paramiko so apps open as separate Windows X11 windows.
- X11: Remote commands are wrapped in `bash -lc 'unset LD_LIBRARY_PATH; ...'` to avoid environment-related symbol conflicts such as `libXrender/_XGetRequest`.
- Standalone support: Added `services/xserver_manager.py` to automatically start portable VcXsrv from `~/.truba_slurm_gui/third_party/vcxsrv/XWin.exe` when no X server is available.
- Standalone X11: Removed the assumption that VcXsrv only exposes `XWin.exe`; the app now discovers `vcxsrv.exe/XWin.exe` entry points, including `third_party/vcxsrv/vcxsrv.exe` and `third_party/vcxsrv/runtime/vcxsrv.exe`, and starts them with the correct working directory.
- Logs: Added persistent log writing to `~/.truba_slurm_gui/app.log` and added a Logs tab.
- Logs: Added a Copy button to the Logs tab.
- Security: When saving a profile with "Remember password" enabled, the plain-text password is no longer written to the config; it is encrypted with PBKDF2+Fernet using a user-entered master password and stored as `password_enc` + `password_salt`.
- Security: If the password field is empty during connection and the profile has `password_enc`, the app now prompts for the master password and decrypts it for the connection.
- X11: Added a download plus silent install flow for VcXsrv from GitHub Releases when no X server is present, with user consent.
- X11: `xserver_manager` now offers a download prompt when `XWin.exe` is missing and auto-starts when it is available.
- X11: `x11_widget` and `login_widget` now call local X server checks with download support before X11 commands.
- Fix: Defined the missing `_log` callback in `X11Widget` for logging during X server download and startup.
- Fix: Replaced `QTextCursor.End` usage in the Logs tab for PySide6 compatibility.
- Fix: Made `LoginWidget.append_console` safe against `QTextEdit already deleted` errors triggered by `QProcess` signals during shutdown.
- Fix: Prevented crashes when `X11Widget` closes while a process finishes by guarding `QLabel` validity.
- Fix: Reduced false-positive X server detection by verifying that the X server process exists when port 6000 is open.

## v1.0.3

- Windows EXE hotfix: fixed `ModuleNotFoundError: No module named 'PySide6'` at startup by rebuilding with PySide6/shiboken6 available in the build environment.
- Rebuilt release artifacts and refreshed packaged `CHANGELOG.txt`.

## v1.0.2

- Added ARF-side quick action to create/edit Slurm scripts from templates in Directories.
- Added template selection flow (core/CPU/GPU/MPI) and file naming prompt before opening in Script Editor.
- Added `Save + Submit` action in Script Editor.
- On save of `.slurm/.sbatch`, app now asks whether to submit with `sbatch`.
- Added pre-save script checks (shebang, `#SBATCH`, placeholder/time/output hints).
- Added lint action in Script Editor for quick static checks.
- Improved `sbatch` error diagnostics with actionable hints for account/QOS/time/CPU/GPU issues.
- After successful submit, parsed Job ID now auto-focuses Jobs & Outputs.
- Added template override search via `TRUBA_TEMPLATE_DIR` and `~/.truba_slurm_gui/templates`.
- Updated the Generic Slurm help library with detailed tutorial content (TR/EN).

## v1.0.1

- X11 flow refactored into a dedicated `X11Runner`.
- Added Slurm accounting and job detail actions (`sacct`, `scontrol show job`).
- Added host key policy option (`accept-new` / `strict`) for SSH profiles.
- Added diagnostics bundle export from Logs tab.
- Added transfer operation journal (`transfer_journal.jsonl`).
- Added CI checks (compile, i18n key drift, smoke test).
- Added Windows release automation workflow.

## v1.0.0

- Initial public release.
