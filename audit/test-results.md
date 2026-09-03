# GUI audit test results

Run date: 2026-09-03  
Branch: `develop`  
Commit: `f94912f Add GUI feature guides and mock screenshots`

## Screenshot capture

| Command | Result | Output |
|---|---|---|
| `python scripts/capture_wiki_screenshots.py` | PASS | `6/6 screenshots captured` |
| `python scripts/capture_wx_gui_guide.py` | PASS | 8 wx screenshots saved |

Qt reference images are also archived in [`screenshots/qt/`](screenshots/qt/).
New wx images are archived in [`screenshots/wx/`](screenshots/wx/).

## Mock HPC / SFTP / Slurm validation

Command:

```text
python -m pytest -q tests/test_mock_cluster_roundtrip.py
```

Result:

```text
2 passed in 14.79s
```

This exercises the repository's local mock SSH server and provider-neutral
Slurm/SFTP roundtrip without an external endpoint.

## wx Files and mock validation

Command:

```text
python -m pytest -q tests/test_wx_local_files.py tests/test_mock_cluster_roundtrip.py
```

Result:

```text
8 passed in 14.62s
```

## Quality checks

| Command | Result |
|---|---|
| `python scripts/check_wiki.py` | `wiki check: OK` |
| `python -m ruff check scripts/capture_wx_gui_guide.py src/hpc_gui/wx_local_files.py` | `All checks passed!` |
| `python -m py_compile scripts/capture_wx_gui_guide.py src/hpc_gui/wx_local_files.py` | PASS |
| `git diff --check` | PASS |

## Scope notes

The visible wx surfaces captured are Connection, Local Files, Remote Files,
Editor, Jobs, detached output, Help/Shortcuts, and Terminal. Settings,
Plugins, ANSYS, updater, diagnostics, and transfer workspace remain model-only
or Qt-only where the repository has no wx window adapter; they are documented
as such and are not represented by fabricated wx screenshots.
