# V2 Manual GUI Parity Test

Record one copy per build:

| Field | Value |
|---|---|
| Tester | |
| Build/version | |
| Date/time | |
| OS/display | |
| Qt baseline / wx candidate | |

Run the same cases against the current Qt build and the wx candidate. Mark
`PASS`, `FAIL`, or `N/A`; attach only redacted screenshots/log references.

| ID | Steps | Expected result |
|---|---|---|
| GUI-FILE-014/018 | Middle-click a folder, then a directory tab | Folder opens in a new tab; tab middle-click has no inferred close action. |
| GUI-FILE-015 | Select two entries, right-click selected and unselected entries | Existing multi-selection is retained for selected target; unselected target becomes the explicit target. |
| GUI-FILE-016 | Drag remote entries between panes; drag a local path to a remote folder | Move/upload is asynchronous, targets the drop folder, and preserves errors/conflict gates. |
| GUI-FILE-017 | Repeat the remote drag with Ctrl | Copy is asynchronous and preserves the same safety gates. |
| GUI-XFER-010/011 | Double-click local then remote files in FTP view | Upload/download is queued to the active destination. |
| GUI-XFER-012/013/014 | Open menus for queued, failed, and completed transfers | Actions match state; failure reason remains visible and completed items are not offered an implied retry. |
| GUI-CONN-010 | Single-click, then double-click a saved profile | Single click selects only; double-click connects that profile. |
| GUI-CONN-002 | Connect with MFA and an invalid host key | MFA prompts remain private; host-key policy is explicit and unsafe keys are not silently accepted. |
| GUI-TERM-020 | Focus terminal and press Ctrl+C, Ctrl+Z, and copy shortcut with a selection | Control codes reach the shell; copy does not interrupt selected terminal text. |
| GUI-JOBS-002 | Open a live output window and let output update while resizing | Output remains readable, follows configured mode, and the UI stays responsive. |
| GUI-PLUGIN-002 | Open the allowlisted ANSYS tool and run lint | Tool disclosure, lint result, and failure state are visible; arbitrary plugin executables are not run. |
| GUI-SET-001 | Edit a shortcut, save settings, restart, and restore defaults | Shortcut persists, applies in its platform context, and reset is reversible. |
| GUI-HELP-001 | Open Help, search, navigate results with keyboard, open a documented link | Search/result focus and activation work without a pointer; only allowed external URLs open. |

Platform variants:

- Windows/Linux: Ctrl-based file and terminal gestures; test Explorer/file-manager
  DnD and the platform clipboard.
- macOS: Cmd file/edit gestures and XQuartz/system OpenSSH X11; do not expect
  a mechanical Ctrl-to-Cmd rewrite in terminal interrupt semantics.
- Wayland/X11 and 100/150/200% DPI: repeat focus, dialogs, DnD, clipboard,
  tray, and live-output cases where the desktop differs.

Safety and evidence:

- Use a disposable profile and non-sensitive test files; never record passwords,
  MFA responses, private keys, tokens, or unsanitized remote paths.
- This plan complements automated tests and makes no automated claim for manual
  interactions. Differences must be recorded in `V2_PARITY_STATUS.md` with an
  explicit `INTENTIONALLY_CHANGED` justification.
