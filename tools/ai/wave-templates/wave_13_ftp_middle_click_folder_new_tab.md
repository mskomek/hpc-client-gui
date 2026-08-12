# Wave 13 — FTP Middle-Click Folder in New Tab

Status: waiting
Owner: Codex
Priority: P1
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Add middle-mouse-button support to the local directory panel so that
middle-clicking a folder entry opens that folder in a new editor tab,
matching the existing "Open in new tab" context-menu action.

## Why This Wave Exists

The local directory panel already has an "Open in new tab" right-click
context-menu action (`_on_context_menu` in `local_dir_panel.py`). Users
expect middle-click (common in file managers and browsers) to trigger the
same behavior without reaching for the context menu.

## Depends On

- Wave 12 is under `waves/done/`
- existing `FtpWidget` and `LocalDirPanel` architecture
- existing "Open in new tab" context-menu action path

## Target Files

- `src/truba_gui/ui/widgets/local_dir_panel.py`
- narrowly `src/truba_gui/ui/widgets/ftp_widget.py` if signal plumbing is needed

## In Scope

- detect middle-click on a `_LocalTree` item that is a directory
- reuse the existing "Open in new tab" handler path (or the same backend
  call it makes)
- keep the existing right-click context-menu behavior intact
- middle-click on a file or on empty space does nothing (no-op)

## Out of Scope

- remote panel middle-click behavior
- middle-click on files (only folders)
- changing the existing context-menu action or its signature
- CLI changes
- live remote operations

## Packets and Tasks

### DS-13A — Middle-click folder opens in new tab (Small)

- [ ] In `_LocalTree`, override `mouseReleaseEvent` (or install an
  event filter) to detect middle-button release.
- [ ] On middle-click, identify the item under the cursor via
  `itemAt(event.pos())`.
- [ ] If the item is a directory, invoke the same handler that the
  "Open in new tab" context-menu action calls.
- [ ] Ensure the existing right-click context menu still works
  correctly after the change.
- [ ] Verify that middle-click on a file, on empty area, or on the
  header does nothing.
- [ ] Add a focused regression test covering middle-click on a folder,
  middle-click on a file (no-op), and middle-click on empty space
  (no-op).

## Validation

- [ ] Manual: open FTP panel → navigate local dir → middle-click a folder → new tab opens with that folder
- [ ] Manual: middle-click a file → nothing happens
- [ ] Manual: middle-click empty area → nothing happens
- [ ] Manual: right-click context menu still works
- [ ] `$env:PYTHONPATH = "src"; python -m pytest tests/test_ftp_widget.py -q`
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-13A.

## Done Criteria

1. Middle-click on a local folder row opens the folder in a new editor tab.
2. Middle-click on a file or empty space is a silent no-op.
3. Existing right-click context-menu and all other mouse interactions are
   unchanged.
4. Regression test covers the three middle-click cases.

## Possible Blockers

- Qt mouse event propagation conflicts with existing drag-and-drop or
  selection logic in `_LocalTree`
- the "Open in new tab" handler is private to `LocalDirPanel` and is not
  directly callable from `_LocalTree` without refactoring
- middle-click on some systems is mapped to a different button constant

## Completion Notes

- Completed at:
- Packet verdicts:
- Files changed:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex changes `Status` to `done` and fills Completion Notes.
- Codex moves this file to `waves/done/` only after all gates PASS.
- Stop the prompt; report Wave 14 as next but do not start it.
