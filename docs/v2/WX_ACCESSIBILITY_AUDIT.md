# wx Accessibility Audit

The wx models retain the shared command palette, help search, native platform
keymap, and terminal semantics. The Help screen gives its search and results
controls accessible names and places focus in the search field when opened.
macOS settings use the native Command bindings; terminal interrupt semantics
remain distinct from file-copy shortcuts.

Keyboard smoke checklist:

- Open Help and Settings from the menu/shortcut, confirm initial focus, then
  traverse controls with Tab/Shift+Tab and activate with Enter/Space.
- Reach connection, files, transfers, jobs, editor, plugins, diagnostics,
  dialogs, and shutdown without a pointer; verify every context has a menu or
  shortcut alternative for pointer-only actions.
- Confirm status is conveyed by text/state, not color alone, and that terminal
  screen-reader output is usable for bounded output.

Known limit: terminal emulation and native wx accessibility behavior still
require manual checks on each supported desktop and no formal certification is
claimed.
