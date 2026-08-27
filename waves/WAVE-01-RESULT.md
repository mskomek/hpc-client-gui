# WAVE 01 result — macOS bundle inventory

## Status

**Complete.** Diagnostic release run `33060763991` retained both application
bundle inventories although the blocking DMG budget checks failed. No release
was published and no signing/notarization was performed.

## Confirmed measurements

| Source | Architecture | Size | Result |
| --- | ---: | ---: | --- |
| GitHub Release `v1.5.0` | arm64 DMG | 1,430,471,955 bytes / 1,364.05 MiB | published previously |
| GitHub Release `v1.5.0` | x86_64 DMG | 1,572,185,991 bytes / 1,499.14 MiB | published previously |
| Release run `33058369604` | arm64 DMG | 1,361,855,504 bytes / 1,298.77 MiB | rejected by 600 MiB budget |
| Diagnostic run `33060763991` | arm64 app bundle | 527,378,343 bytes / 502.86 MiB | retained before DMG check |
| Diagnostic run `33060763991` | x86_64 app bundle | 542,096,424 bytes / 516.92 MiB | retained before DMG check |

Current diagnostic job results:

- Linux: running at collection time;
- Windows: failed at the release-commit workflow guard;
- macOS arm64: failed at the 600 MiB DMG budget check;
- macOS x86_64: failed at the 600 MiB DMG budget check;
- signing/notarization: skipped because `macos_mode=unsigned`;
- publication: skipped because `publish=false`.

## Dominant bundle contents

| Group/file | arm64 | x86_64 |
| --- | ---: | ---: |
| `Frameworks/PySide6` | 466,280,477 bytes | 485,804,717 bytes |
| `Resources/PySide6` | 20,499,232 bytes | 20,499,232 bytes |
| `QtWebEngineCore` | 228,494,352 bytes | 247,131,536 bytes |
| WebEngine `icudtl.dat` | 10,467,680 bytes | 10,467,680 bytes |
| Python framework | 7,191,577 bytes | 7,191,577 bytes |
| cryptography | 11,810,528 bytes | 5,894,336 bytes |

Other bundled Qt modules include QtQuick, QtPdf, QtQml, QtShaderTools,
QtQuick3D, QtCharts, QtLocation, and related styles/plugins. Their presence
is not by itself evidence that they are safe to remove.

## Packaging dependency boundary

The macOS spec explicitly includes `PySide6.QtWebChannel`,
`PySide6.QtWebEngineCore`, `PySide6.QtWebEngineWidgets`, the hook-provided
`QtWebEngineProcess`, ICU/software-renderer fallbacks, and terminal assets
(`index.html`, `bridge.js`, `xterm.js`, `xterm.css`). It excludes only
`qtwebengine_devtools_resources`.

The terminal widget imports `QWebChannel`, `QWebEnginePage`, and
`QWebEngineView`; the packaged smoke test requires `QtWebEngineProcess`.
WebEngine therefore cannot be removed merely to hit the budget without
changing a supported user path.

## Conclusion and next wave

The package is oversized primarily because of the QtWebEngine/PySide6
runtime. The failed build was explicitly unsigned, so signing is not the
cause. The x86_64 application bundle is about 14.72 MiB larger than arm64,
but both are dominated by the same WebEngine payload.

WAVE 02 must map actual imports and packaged smoke-test requirements before
proposing exclusions or build changes. Do not raise the 600 MiB budget or
delete Qt runtime files based only on this size report.

## Evidence

- Artifacts: `hpc-client-gui-macos-arm64-diagnostics-1.5.1` and
  `hpc-client-gui-macos-x86_64-diagnostics-1.5.1`
- Run: `33060763991`
- Reports: `bundle-size-report-macos-arm64.txt` and
  `bundle-size-report-macos-x86_64.txt`
