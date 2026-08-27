# WAVE 02 result — safe PyInstaller pruning

## Status

**Started — evidence review complete; Qt exclusions not yet approved.**

WAVE 01 reports show that the application bundle is approximately 502.86 MiB
(arm64) and 516.92 MiB (x86_64), while the failed DMGs were approximately
1.3–1.5 GiB. The first high-confidence size defect was staging: both macOS
DMG paths followed PyInstaller framework symlinks during `copytree`,
duplicating Qt framework payloads. That is fixed by PR #18 with
`symlinks=True` in the unsigned and signed staging paths.

## Current dependency boundary

The supported terminal uses `QWebChannel`, `QWebEnginePage`, and
`QWebEngineView`. The packaged smoke test requires `QtWebEngineProcess`.
Therefore these remain required:

- QtWebEngineCore and QtWebEngineWidgets;
- QtWebChannel;
- QtWebEngineProcess;
- ICU data and software-renderer fallbacks;
- terminal assets: `index.html`, `bridge.js`, `xterm.js`, `xterm.css`.

## Inventory-based candidates

The reports identify QtQuick, QtPdf, QtQml, QtShaderTools, QtQuick3D,
QtCharts, QtLocation, and related style/plugin files. Their size makes them
worth investigating, but the inventory alone does not prove that they are
unused: QtWebEngine and PySide hooks can load transitive modules.

No exclusion is approved until all of the following are true:

1. repository imports and PyInstaller analysis show no supported use;
2. the exclusion is limited to macOS and has a focused packaging test;
3. arm64 and x86_64 builds pass;
4. packaged CLI, GUI, terminal, plugin manager, updater, and help smoke tests
   pass;
5. the regenerated reports show the measured saving and both DMGs remain
   below the 600 MiB budget.

## Next action

Run PR #18 on both macOS architectures after review. If the symlink fix puts
both DMGs below budget, stop pruning and keep the smaller, lower-risk diff.
If either remains over budget, perform a module-level import audit and test
one exclusion at a time. Do not raise the budget or remove WebEngine runtime
files.
