# Installation from Source

> Türkçe: [[Installation-From-Source-TR]]

Running from source works on Windows and Linux and gives you the same
application and the same command-line interface as the packaged builds.

## Requirements

- Python 3.10 or newer (`requires-python = ">=3.10"`).
- On Linux, the Qt platform libraries PySide6 needs (`libegl1` on
  Ubuntu/Debian, the distribution equivalent on Fedora and openSUSE).
- Optional, X11 only: `plink.exe` and VcXsrv on Windows; the system OpenSSH
  client on Linux.

## Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[test]
python -m hpc_gui
```

## Linux

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[test]
python -m hpc_gui
```

## Install variants

- `pip install -e .` installs the application only.
- `pip install -e .[test]` additionally installs the test dependencies, which
  you need to run the offline suite. See [[Testing and CI|Testing-and-CI]].

## Command-line interface

The same entry point serves the command line:

```bash
python -m hpc_gui --help
```

`hpc-client-gui` is the program name shown in help output. See
[[CLI Overview|CLI-Overview]].

## Running the desktop application headlessly

For automated checks, Qt's offscreen platform avoids opening a window:

```bash
QT_QPA_PLATFORM=offscreen python -m hpc_gui --help
```

## Next steps

[[Building from Source|Building-from-Source]] ·
[[Architecture|Architecture]] ·
[[Contributing|Contributing]]
