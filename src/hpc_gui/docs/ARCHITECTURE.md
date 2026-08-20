# ARCHITECTURE.md

## Overview

This repository is a **PySide6 desktop application** for SSH/SFTP + Slurm HPC
workflows on Windows and Linux. TRUBA is a supported/example environment, not
the only deployment target.

High-level product behavior:
- start the GUI
- establish or reuse a remote session
- browse or edit remote content
- prepare or submit Slurm scripts
- observe queue/accounting state
- inspect diagnostics and logs
- optionally launch X11-backed programs through platform-specific helpers
- render the interactive SSH PTY with local xterm.js assets in Qt WebEngine

The GUI and CLI are separate entry points. The GUI owns presentation and
background workers; the CLI remains independent from Qt WebEngine startup.

## Main Code Areas

### `src/hpc_gui/ui/`
Responsibilities:
- windows, dialogs, widgets
- user interaction
- progress and status display

Should not own:
- reusable Slurm parsing logic
- deep SSH logic
- hidden business rules that belong in services

### `src/hpc_gui/services/`
Responsibilities:
- Slurm service abstractions
- remote file operations
- process registry / process launching
- X11 helper orchestration
- integration with PuTTY/VcXsrv and related tools

### `src/hpc_gui/ssh/`
Responsibilities:
- SSH client behavior
- connection-level wrappers or helpers
- interactive PTY creation, byte decoding, complete writes, and resize

### Terminal boundary

`services/terminal_bridge.py` exposes the existing Paramiko interactive shell
to `ui/widgets/terminal_widget.py`. The local xterm.js page owns VT rendering,
selection, keyboard semantics, and bounded scrollback. Python does not parse
ANSI/VT sequences on the embedded-terminal path.

### `src/hpc_gui/config/`
Responsibilities:
- local configuration models
- storage of user preferences
- safe persistence helpers

### `src/hpc_gui/core/`
Responsibilities:
- logging setup
- i18n support
- diagnostics helpers
- paths/resources/debug helpers

### `templates/`
Responsibilities:
- starter Slurm script templates for CPU / GPU / MPI flows

### `scripts/`
Responsibilities:
- repo validation
- smoke tests
- packaging and release helpers

## Architectural Priorities

1. UI responsiveness
2. explicit and inspectable remote operations
3. reusable service/domain logic
4. observable failures
5. i18n consistency
6. Windows and Linux packaging practicality

Packaging definitions under `build/` produce candidate artifacts; generated
release output belongs under ignored `dist/` paths and is not source content.

## Design Rules

- If logic can be tested outside a widget, prefer moving it out of the widget.
- Keep user-visible strings in the language layer where practical.
- Keep external command execution easy to reason about.
- Keep test seams available for fake file/Slurm layers, as already seen in `tests/test_editor_flow.py`.
