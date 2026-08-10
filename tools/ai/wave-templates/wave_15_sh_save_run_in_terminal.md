# Wave 15 — .sh Save & Run in Terminal

Status: waiting
Owner: Codex
Priority: P1
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

When a `.sh` (shell script) file is opened in the editor tab, provide a
"Save & Run" button that saves the file to the remote path and then
executes it in the terminal (e.g. `bash script.sh`), distinct from the
existing "Save + Submit" which runs `sbatch`.

## Why This Wave Exists

The editor widget already has a "Save + Submit" button that saves and
calls `sbatch` for `.slurm`/`.sbatch` files. Shell scripts (`.sh`) are
not Slurm job scripts — they are meant to be executed interactively in
a terminal. Users currently must save, switch to the terminal tab, and
manually run the script. A single "Save & Run" button removes this
friction.

## Depends On

- Wave 12 is under `waves/done/`
- existing `EditorWidget` toolbar with `btn_save_submit`
- existing `runShellRequested` signal in `FtpWidget` (connected to
  terminal execution in `main_window.py`)
- existing `session["files"].write_text()` for save

## Target Files

- `src/truba_gui/ui/widgets/editor_widget.py`
- narrowly `src/truba_gui/ui/main_window.py` if new signal routing is
  needed
- `src/truba_gui/i18n/tr.json` and `src/truba_gui/i18n/en.json` for
  new button label
- focused editor flow test

## In Scope

- detect file extension in the active editor document tab
- when the active document path ends with `.sh`, show a "Save & Run"
  button (or repurpose `btn_save_submit` contextually)
- when `.sh`: save the file → emit a signal to run `bash <path>` in the
  terminal
- when `.slurm`/`.sbatch`: keep the existing "Save + Submit" behavior
  (unchanged)
- when neither `.sh` nor `.slurm`/`.sbatch`: only "Save" is available
- after save-and-run, the terminal tab should be visible and the command
  output should be user-visible
- save must complete before the run command is sent to the terminal

## Out of Scope

- running the script locally (only remote execution via terminal)
- editing the script while it runs (no live-reload)
- stopping/killing a running script from the editor toolbar
- changing the Slurm submit flow or `_offer_submit_after_save`
- CLI changes
- live remote operations beyond the existing terminal infrastructure

## Packets and Tasks

### DS-15A — .sh Save & Run button and terminal integration (Medium)

- [ ] Add a `btn_save_run` button to the editor toolbar, initially hidden.
- [ ] When the active document tab changes, check the file extension of
  the current document path.
- [ ] If the path ends with `.sh`, show `btn_save_run` and hide
  `btn_save_submit` (or show both with appropriate labels).
- [ ] If the path ends with `.slurm`/`.sbatch`, show `btn_save_submit`
  and hide `btn_save_run`.
- [ ] If the path has neither extension, hide both `btn_save_submit` and
  `btn_save_run`.
- [ ] `btn_save_run` click handler: save the file via the existing save
  path, then emit a signal (e.g. `run_in_terminal(path)`) that is
  connected in `main_window.py` to send `bash <path>` to the terminal.
- [ ] After save completes successfully, switch to the terminal tab so
  the user sees the output.
- [ ] Ensure the save operation runs off the GUI thread if it involves
  remote I/O.
- [ ] Add Turkish and English labels for "Save & Run".
- [ ] Add a focused test verifying the button visibility logic and save-
  then-run signal emission.

## Validation

- [ ] Manual: open a `.sh` file in editor → "Save & Run" button visible → click → file saved, terminal runs `bash script.sh`
- [ ] Manual: open a `.slurm` file → "Save + Submit" visible, "Save & Run" hidden
- [ ] Manual: open a `.txt` file → neither "Save + Submit" nor "Save & Run" visible
- [ ] Manual: switch tabs between `.sh` and `.slurm` → buttons toggle correctly
- [ ] `$env:PYTHONPATH = "src"; python -m unittest tests/test_editor_flow.py`
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-15A.

## Done Criteria

1. `.sh` files show a "Save & Run" button in the editor toolbar.
2. Clicking it saves the file to the remote path and runs `bash <path>`
   in the terminal.
3. `.slurm`/`.sbatch` files retain the existing "Save + Submit" behavior
   without change.
4. Files with neither extension show only "Save".
5. The terminal tab becomes visible after save-and-run completes.
6. Button labels are translated in both Turkish and English.

## Possible Blockers

- the terminal widget may not expose a public method to send a command
  programmatically
- the `runShellRequested` signal already exists on `FtpWidget` but
  `EditorWidget` may need its own signal wired to the same terminal
  handler in `main_window.py`
- save is async (remote write); the run command must not be sent before
  save completes
- the file path used for `bash` must be the remote path, not a local
  one

## Completion Notes

- Completed at:
- Packet verdicts:
- Files changed:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex changes `Status` to `done` and fills Completion Notes.
- Codex moves this file to `waves/done/` only after all gates PASS.
- Stop the prompt; report Wave 16 as next but do not start it.
