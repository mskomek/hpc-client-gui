# WAVE 01 result — macOS bundle inventory

## Status

**Partial / blocked for file-level inventory.** The Windows orchestrator
cannot build or mount a macOS app/DMG. The CI packaging job currently fails
before its candidate artifact upload when the DMG budget check rejects the
package, so the generated bundle report is not retained by Actions.

## Confirmed measurements

| Source | Architecture | Size | Result |
| --- | ---: | ---: | --- |
| GitHub Release `v1.5.0` | arm64 DMG | 1,430,471,955 bytes / 1,364.05 MiB | published previously |
| GitHub Release `v1.5.0` | x86_64 DMG | 1,572,185,991 bytes / 1,499.14 MiB | published previously |
| Release run `33058369604` | arm64 DMG | 1,361,855,504 bytes / 1,298.77 MiB | rejected by 600 MiB budget |

The current run’s x86_64 job also failed in the same packaging step. The full
run result was:

- Linux: success
- Windows: success
- macOS arm64: failure
- macOS x86_64: failure
- signing/notarization: skipped because `macos_mode=unsigned`
- final release gate: failure
- publication: skipped

## Current packaging dependency boundary

The macOS spec explicitly includes:

- `PySide6.QtWebChannel`
- `PySide6.QtWebEngineCore`
- `PySide6.QtWebEngineWidgets`
- `QtWebEngineProcess` supplied by the PyInstaller Qt hooks
- ICU and software-renderer fallbacks
- terminal assets (`index.html`, `bridge.js`, `xterm.js`, `xterm.css`)

The spec excludes only `qtwebengine_devtools_resources`. The terminal widget
imports `QWebChannel`, `QWebEnginePage`, and `QWebEngineView`; the packaged
smoke test requires `QtWebEngineProcess`. Therefore WebEngine cannot be
removed merely to hit the budget without changing a supported user path.

## Missing evidence

The following cannot be truthfully filled from the current run:

- top 30 files by byte count;
- top 20 grouped frameworks/directories;
- exact QtWebEngine/Chromium/ICU/Python contribution;
- duplicate architecture slices;
- a file-by-file safe-removal table.

The existing release workflow creates `bundle-size-report-macos-<arch>.txt`
before the DMG budget check, but the upload step is skipped when the build
step exits non-zero. A future diagnostic run must upload that report with an
`if: always()` diagnostic step while keeping the final release gate blocking.

## Initial conclusion

The package is not oversized because of signing: the current failed run is
explicitly unsigned. The measured size is already rejected before release.
The likely dominant payload is the QtWebEngine/Chromium runtime, but that is
an inference until the retained bundle report identifies exact paths and
sizes. No pruning candidate is approved by this wave yet.

## Next safe action

Add failure-path-only bundle-report retention, rerun both macOS packaging jobs,
then use the exact report to define WAVE 02 exclusions. Do not raise the
600 MiB budget and do not remove WebEngine runtime files before that evidence.
