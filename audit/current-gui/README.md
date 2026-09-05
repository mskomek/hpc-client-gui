# Current GUI Visual Audit — Qt vs wx (2026-09-05, 3a72940)

This directory is the **authoritative current visual record** of the Qt production GUI and the wx migration candidate, captured from the same commit `3a72940` (`bd40fe6` + provenance) on the same Windows 100% scaling environment.

- **Product source commit:** `3a7294079b992d3ddcabc349bbeadf6988312b64` (`develop`, `3a72940`)
- **Capture commit:** same (audit tooling only, no product source change)
- **Platform:** Windows 11 Pro 10.0.26200, 1920x1080, 96 DPI (100%), light theme
- **Python:** 3.12.4, **PySide6** 6.11.2, **wxPython** 4.3.1 msw (phoenix) wxWidgets 3.3.3, **App** 1.5.8, **Language** `en` (primary), `tr` supplementary

## Runtime commands (real)

```powershell
# Qt (default, MainWindow)
python -m hpc_gui

# wx (migration, integrated shell)
python -m hpc_gui --wx
# or directly
python -c "from hpc_gui.wx_shell import main; main()"
```

Both launches use the **real production UI** with **disposable mock/offline data** (see `Mock Data` below). No real cluster credentials.

## Window geometry

- **Primary comparison:** `1366x768` (both runtimes, same dimensions)
- **Supplementary:** `1100x720`, `960x640` (adaptive layout, captured for `01-main-default`)
- Qt and wx were captured at the **same** size per comparison pair. `win.resize(w,h)` was used before each capture; actual grabbed image dimensions may include window chrome and DPI scaling (recorded per file in `MANIFEST.json`).

## Mock/offline fixture

Deterministic fixture `Test Cluster` / `researcher@hpc.example.org` with:

- Profile: `Test Cluster` (host `hpc.example.org`, port 22, user `researcher`)
- Fake home under `%TEMP%\hpc-current-gui-{qt,wx}\researcher` (no real HOME)
- Local workspace: `projects/analysis` with `run.slurm`, `analyze.py`, `data/input.csv` (disposable)
- Remote: `MockFilesBackend` / `MockRemoteFilesBackend` with `/home/researcher`, `/scratch/researcher`, `run.slurm` etc.
- Jobs: `SQUEUE_TEXT` 2 jobs (`100001 R`, `100002 PD`) via `parse_squeue`
- Logs: `FAKE_LOG` 8 lines (no secrets)
- Editor: `JOB_SCRIPT` (`#SBATCH` ...)

Same logical fixture used for Qt and wx where both support it. If a runtime cannot reach a state (e.g., Qt has no wx-only Terminal tab), the manifest marks `QT_EQUIVALENT_NOT_AVAILABLE` or `MISSING` rather than fabricating.

## Directory

```
audit/current-gui/
├── README.md               # this file
├── MANIFEST.md             # human-readable per-screenshot explanation
├── MANIFEST.json           # machine-readable inventory (schema gui-visual-audit/2)
├── HASHES.sha256           # sha256sum of every PNG
├── CONTROL_INVENTORY.md    # control-by-control Qt vs wx
├── TAB_INVENTORY.md        # tab order, embedded vs detached
├── MENU_INVENTORY.md       # menu + context menu inventory
├── ACTION_INVENTORY.md     # button/action inventory
├── DIFFERENCES_PREVIEW.md  # factual differences, no judgment
├── qt/                     # Qt screenshots (25 files, 1366x768 primary)
└── wx/                     # wx screenshots (29 files, 1366x768 primary)
```

Historical evidence remains untouched:

- `audit/screenshots/` (legacy wiki)
- `audit/gui-screenshots/` (previous parity, 1100x720)

## Naming

Strict numeric prefixes, Qt/wx same filename for equivalent states:

```
01-main-default.png
02-connection-default.png
10-jobs-default.png
...
```

`wx-only-...` or `qt-only-...` where no equivalent. No file is reused under multiple names without `intentional_alias` documentation (see `MANIFEST.json` and `HASHES.sha256`).

## How to compare

Open `qt/` and `wx/` side-by-side:

```powershell
explorer audit\current-gui\qt
explorer audit\current-gui\wx
```

`MANIFEST.md` explains each shot (runtime, surface, mock data, paired file). `CONTROL_INVENTORY.md` lists every visible control per surface.

## Known limitations (this capture)

- Qt `AnsysLintResultsDialog` import failed (`cannot import name 'AnsysLintResultsDialog'`), so Qt ansys screenshots are `MISSING` (marked in manifest).
- Qt jobs sub-tabs (Files/Outputs) and connection profile selection were captured without deep state change, so `01-main`/`02-connection`/`03-connection-profile-selected` are byte-identical (duplicate hash `41b79349...`) — intentional alias, same rendered state (Qt starts on Connection). Future capture should select a profile via UI to make them distinct.
- Qt logs `80`/`81` identical (no log population difference), `150-menu`/`160-chrome`/`170-language` identical to `80` due to capturing main window chrome only — documented as alias.
- Updater/tray/balloon, transfer conflict/progress, and many file context menus (8 required) are `MISSING` in this run (no fake backend path for those states without real transfer). Manifest marks `MISSING`.
- Dimensions: Qt `win.grab()` captures widget at 2054x768 (devicePixelRatio handling) vs requested 1366x768 — recorded verbatim; wx `ImageGrab.grab(window=handle)` includes title bar, dimensions differ slightly. Both are comparable but not pixel-identical; documented.

No UI was modified to improve appearance before capture. Screenshots are **before-further-polish baseline** for `3a72940`.

## Reproducibility

To recapture:

```powershell
python scripts/capture_current_gui_qt.py --size 1366x768 --lang en
python scripts/capture_current_gui_wx.py --size 1366x768 --lang en
python scripts/generate_current_gui_manifest.py
```

All screenshots use disposable mock data; no `.tmp/` content is used.
