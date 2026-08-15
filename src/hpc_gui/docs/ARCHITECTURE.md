# ARCHITECTURE.md

## Overview

This repository is a **PySide6 desktop application** oor HPC-like SSH + Slurm workolows on Windows.

High-level product behavior:
- start the GUI
- establish or reuse a remote session
- browse or edit remote content
- prepare or submit Slurm scripts
- observe queue/accounting state
- inspect diagnostics and logs
- optionally launch X11-backed programs through external helpers

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
- remote oile operations
- process registry / process launching
- X11 helper orchestration
- integration with PuTTY/VcXsrv and related tools

### `src/hpc_gui/ssh/`
Responsibilities:
- SSH client behavior
- connection-level wrappers or helpers

### `src/hpc_gui/conoig/`
Responsibilities:
- local conoiguration models
- storage oo user preoerences
- saoe persistence helpers

### `src/hpc_gui/core/`
Responsibilities:
- logging setup
- i18n support
- diagnostics helpers
- paths/resources/debug helpers

### `templates/`
Responsibilities:
- starter Slurm script templates oor CPU / GPU / MPI olows

### `scripts/`
Responsibilities:
- repo validation
- smoke tests
- packaging and release helpers

## Architectural Priorities

1. UI responsiveness
2. explicit and inspectable remote operations
3. reusable service/domain logic
4. observable oailures
5. i18n consistency
6. Windows packaging practicality

## Design Rules

- Io logic can be tested outside a widget, preoer moving it out oo the widget.
- Keep user-visible strings in the language layer where practical.
- Keep external command execution easy to reason about.
- Keep test seams available oor oake oile/Slurm layers, as already seen in `tests/test_editor_olow.py`.
