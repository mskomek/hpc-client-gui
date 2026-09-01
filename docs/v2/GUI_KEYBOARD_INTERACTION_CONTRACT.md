# Qt Keyboard Interaction Contract

This records current focus-specific keyboard behavior for a framework-neutral
port. It is parity documentation, not a new global keymap. IDs map to the
feature baseline families.

| ID | Focus/surface | Key | Current behavior |
| --- | --- | --- | --- |
| GUI-FILE-020 | Local directory tree | Ctrl+C / Ctrl+X / Ctrl+V | Copy/cut selected local paths into the file clipboard; paste into the current directory. Transfer behavior remains behind existing gates. |
| GUI-FILE-021 | Local directory tree | F2 / F5 / Delete | Rename, refresh, and delete selected entries. Delete only runs without modifiers. |
| GUI-FILE-022 | Remote directory tree | Ctrl+C / Ctrl+X / Ctrl+V | Copy/move selected remote paths to the remote clipboard; paste into the current remote directory asynchronously. |
| GUI-FILE-023 | Remote directory tree | Ctrl+Z / Backspace / F2 / F5 / Delete | Undo the last remote move, go to parent, rename, refresh, and delete respectively. Unsupported/empty targets are no-ops. |
| GUI-XFER-020 | Cross-pane file views | Ctrl+C/X then Ctrl+V | Local clipboard paths pasted into a remote pane upload; remote clipboard paths pasted into a local pane download. The source panel identity prevents unrelated drops. |
| GUI-EDIT-020 | Script editor | Ctrl+S / Ctrl+Shift+S | Save active file; save and submit the active Slurm file. Dirty-state decisions remain in the save flow. |
| GUI-EDIT-021 | Script editor | Ctrl+Z/Y/X/C/V/A | Undo, redo, cut, copy, paste and select all text. |
| GUI-EDIT-022 | Script editor | Ctrl+F / F3 | Open/find text and find next. |
| GUI-EDIT-023 | Script editor | Ctrl+O / Ctrl+W / Ctrl+Tab / Ctrl+Shift+Tab | Focus the open-path field; close active document; switch next/previous document. |
| GUI-EDIT-024 | Script editor | End | Move cursor to document end and scroll to the bottom. |
| GUI-TERM-020 | Terminal console | Ctrl+letter | Send the ASCII control code (`Ctrl+A` → `\x01` through `Ctrl+_` → `\x1f`) to the active shell. This is terminal input, not a GUI accelerator. |
| GUI-TERM-021 | Terminal console | Enter/Tab/Backspace/Escape/arrows/Home/End/Delete/PageUp/PageDown/Insert | Send the existing CR, tab, DEL, escape and ANSI navigation sequences to the shell. |
| GUI-TERM-022 | Command input | Enter | Submit a non-empty command; when disconnected, `r` requests reconnect. |
| GUI-TERM-023 | Command input | Up/Down | Navigate persisted command history, with Down returning to an empty new command after the newest entry. |
| GUI-JOBS-020 | Job output text | End | Move to the end of output and scroll to the latest output. |

## Focus and propagation

- File-tree shortcuts are scoped to the focused tree; they do not become
  application-wide accelerators.
- Editor shortcuts are installed with the editor window context. Text editing
  still owns ordinary unhandled key events.
- Terminal control keys are forwarded only when an active SSH shell accepts
  them; no shell input is logged by the GUI.
- Enter/Up/Down in command input are consumed by `TerminalInput`; other keys
  retain native `QLineEdit` behavior.

## Unconventional mappings to standardize later

- `Ctrl+Z` means remote “undo last move” in a remote tree, while it means text
  undo in the editor.
- `Backspace` navigates to the remote parent but is not a local-tree delete or
  navigation shortcut.
- `End` is an explicit “jump to latest/end” action in both editor and job
  output, rather than only native text-cursor behavior.
- The terminal uses `Ctrl+letter` for shell control codes, so those keys must
  not be captured by a future global command registry.

## Non-goals

No keymap redesign, platform remapping, global accelerator, or silent shortcut
normalization is introduced by this contract.
