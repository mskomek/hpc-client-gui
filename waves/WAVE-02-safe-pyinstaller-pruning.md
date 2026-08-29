# WAVE 02 — safe PyInstaller and Qt payload pruning

## Goal

Reduce the macOS bundle using only files proven unnecessary for the supported
GUI, terminal, updater, plugin manager, and CLI paths.

## Preconditions

- WAVE 01 has produced both architecture reports.
- Every candidate removal has a path, size, reason, and validation test.
- The candidate stays below the 600 MiB compressed DMG budget with margin.

## In scope

- `build/macos/hpc-client-gui.spec`
- macOS-only packaging helper code under `scripts/`
- targeted macOS packaging tests under `tests/`
- release workflow reporting only when needed to preserve evidence

## Candidate order

1. Remove debug symbols, development metadata, test data, caches, and unused
   documentation only when the inventory proves they are shipped.
2. Remove unused Qt modules discovered by the inventory and import graph. Each
   exclusion must be tested by launching the app and opening the relevant GUI
   screens.
3. Remove duplicate resources or duplicate architecture slices only when
   `file`, `lipo`, or an equivalent macOS inspection proves they are not needed
   by the target architecture.
4. Keep only the WebEngine resources required by the local xterm terminal and
   its `QWebChannel` bridge. Keep `QtWebEngineProcess`, ICU data, and software
   rendering fallbacks unless WAVE 01 proves a smaller safe equivalent.
5. Do not remove terminal `index.html`, `bridge.js`, `xterm.js`, `xterm.css`,
   locale data used by the UI, or updater metadata.

## Forbidden shortcuts

- No blanket `PySide6` or `QtWebEngine` exclusion.
- No `HPC_GUI_DISABLE_WEBENGINE=1` in the production package.
- No `--windowed`/smoke-test weakening to hide a missing runtime.
- No budget increase, skip, xfail, `continue-on-error`, or `|| true`.
- No changes to Windows/Linux packaging unless independently justified.
- No commit, push, release, tag mutation, or main-branch write.

## Required implementation pattern

For each exclusion:

1. Add the smallest macOS spec change.
2. Add or update one focused packaging test that asserts the exclusion is
   intentional and documents the runtime dependency boundary.
3. Build on both macOS architectures.
4. Run packaged CLI and GUI smoke tests.
5. Run the terminal interaction test with WebEngine enabled.
6. Regenerate bundle reports and compare before/after sizes.

## Acceptance criteria

- arm64 and x86_64 builds both pass packaging and smoke tests.
- The terminal opens, renders, accepts input, and closes cleanly.
- Plugin manager, updater, help, and CLI entry points remain functional.
- DMG size is below 600 MiB on both architectures with documented margin.
- The diff contains no unrelated application behavior changes.
