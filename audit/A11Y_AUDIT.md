# Wave 61 — Accessibility & Keyboard-Only Audit (954783e)

**Date:** 2026-09-06
**SHA:** 954783e (develop)
**OS:** Windows 11 Pro 10.0.26200

## Tab Order / Focus

- `wx.Notebook` with 7 tabs (Connection, Jobs & Outputs, Directories, Files, Script Editor, Terminal, Logs) — verified via `test_wx_a11y_focus_order_and_labels` (SetSelection 0..6)
- Chrome row: Update, Plugins, Send Logs, Settings, Help, Language — all have `GetLabel() != ""` and tooltips
- Menu bar: Help + Language, keyboard accessible via Alt, labels verified
- No modal focus traps: dialogs (ANSYS, Settings) use `wx.Dialog` with default focus and ESC handling

## Accessible Names / Descriptions

- All primary controls have `GetLabel()` or `GetPageText()` non-empty, serving as accessible names in wxMSW
- Files header: Transfer type Choice + Effective label, Sync CheckBox, Compare Button, Upload/Download
- Editor: Remote label + path TextCtrl + Open/Template/Lint/Save buttons
- Jobs: notebook tabs Files/Outputs have labels, job list columns Job ID/State
- Logs: bounded viewer with Copy/Refresh

## Color Alone

- No state communicated by color alone: file comparison uses text categories (same/local_only/remote_only/type_mismatch) plus status TextCtrl; job states use text + icons; dirty marker uses `*` in tab label

## Keyboard Alternatives for Mouse Gestures

- Middle-click folder new tab → keyboard alternative: `Ctrl+T` (new tab) via local file browser, documented in Help
- Drag & Drop → `Ctrl+C/X/V` cross-pane, `Ctrl+V` paste into folder, also via context menu
- All context menus have keyboard access via Shift+F10 / Menu key

## Help / Shortcut Settings

- Help dialog keyboard accessible (F1), Command Palette `Ctrl+Shift+P`
- Shortcut settings via Settings dialog, keyboard navigable

## Terminal Limits (Documented)

- Terminal uses `wx.TextCtrl` with custom `EVT_CHAR` handling for PTY; screen readers will see a single multiline text control with Find/Clear/Font controls. Full screen-reader semantics for ANSI colors are limited; documented as intentional deviation. Core workflows (input, Find, Clear, Font) are keyboard operable.

## Test Evidence

- `tests/test_wx_a11y.py::test_wx_a11y_focus_order_and_labels` — PASS
- `tests/test_wx_a11y.py::test_wx_a11y_terminal_limits_documented` — PASS

## Verdict
**Wave 61: VERIFIED_COMPLETE** with documented terminal limits. No formal certification claimed.
