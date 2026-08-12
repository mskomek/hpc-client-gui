# Wave 14 — Batch Submit (sbatch) and Batch Shell (bash) from Multi-Select

Status: waiting
Owner: Codex
Priority: P1
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Let users select multiple script files in the local or remote directory
panel, right-click, and execute them in batch:

- `.slurm` / `.sbatch` files → submit all via `sbatch` in alphabetical
  order
- `.sh` files → send all to the terminal via `bash <path>` in
  alphabetical order

A single right-click menu adapts its label and action to the selected
file type.

## Why This Wave Exists

The current submit flow handles one Slurm script at a time. Shell scripts
(`.sh`) are not Slurm jobs — they are meant to be run interactively in a
terminal, yet users must manually switch to the terminal and type each
command. Multi-select batch execution for both types removes repetitive
manual steps and guarantees deterministic ordering.

## Depends On

- Wave 12 is under `waves/done/`
- existing `SlurmBackend.sbatch(path)` service method
- existing `submitRequested` and `runShellRequested` signal plumbing in
  `FtpWidget` and panel classes
- existing terminal widget infrastructure in `main_window.py`

## Target Files

- `src/truba_gui/ui/widgets/remote_dir_panel.py`
- `src/truba_gui/ui/widgets/local_dir_panel.py`
- `src/truba_gui/services/slurm_ssh.py` (or `slurm_base.py` for batch
  method)
- narrowly `src/truba_gui/ui/widgets/ftp_widget.py` for signal routing
- `src/truba_gui/i18n/tr.json` and `src/truba_gui/i18n/en.json` for new
  menu labels
- focused GUI test

## In Scope

### .slurm / .sbatch batch (sbatch)

- detect multi-selection (Ctrl+Click / Shift+Click) of `.slurm` /
  `.sbatch` files
- add "Submit all with sbatch" to the right-click context menu
- sort selected paths alphabetically before submission
- submit each file sequentially via the existing `sbatch` backend method
- run submissions off the GUI thread
- show progress feedback during batch submission
- report a summary: success/failure per file, extracted job IDs

### .sh batch (bash in terminal)

- detect multi-selection of `.sh` files
- add "Run all in terminal" to the right-click context menu
- sort selected paths alphabetically
- send each path sequentially to the terminal as `bash <path>`
- switch to the terminal tab so output is visible
- report which scripts were queued

### Shared

- mixed `.slurm` + `.sh` selection: show both actions or warn that the
  selection mixes types; at minimum, do not silently submit `.sh` files
  to sbatch or send `.slurm` files to bash
- menu label adapts to selected type(s)

## Out of Scope

- parallel/concurrent batch execution (sequential only)
- cancelling a batch mid-flight
- CLI changes
- changing the existing single-file submit or single-file shell-run flow
- executing `.sh` scripts locally (only remote via terminal)

## Packets and Tasks

### DS-14A — Batch sbatch context menu and submission (Medium)

- [ ] In the directory panel context-menu handler, detect when the
  selection contains at least two `.slurm`/`.sbatch` files.
- [ ] Add a "Submit all with sbatch" context-menu action that is only
  visible when the multi-select criteria are met.
- [ ] Sort the selected paths alphabetically (case-insensitive).
- [ ] Submit each path sequentially via `session["slurm"].sbatch(path)`.
- [ ] Run submissions off the GUI thread (use `async_call` or equivalent
  existing async pattern from the codebase).
- [ ] Show per-file progress and a final summary (success count, failure
  count, extracted job IDs).
- [ ] Handle backend errors gracefully: a failed submission does not
  block the remaining files.

### DS-14B — Batch .sh run in terminal (Medium)

- [ ] In the directory panel context-menu handler, detect when the
  selection contains at least two `.sh` files.
- [ ] Add a "Run all in terminal" context-menu action that is only
  visible when the multi-select criteria are met.
- [ ] Sort the selected paths alphabetically (case-insensitive).
- [ ] For each path, emit a signal (reuse or extend
  `runShellRequested`) so `main_window.py` sends `bash <path>` to the
  terminal.
- [ ] After all commands are queued, switch to the terminal tab.
- [ ] Show a brief summary of how many scripts were sent to the terminal.

### DS-14C — Mixed-selection guard and shared test (Small)

- [ ] When the selection mixes `.slurm`/`.sbatch` and `.sh` (and
  possibly other extensions), show only the appropriate batch action
  for each homogeneous subset, OR show a single grouped menu that
  separates the two actions.
- [ ] Add a focused test that verifies sorting, sequential calls,
  and summary output with a mock Slurm backend for DS-14A.
- [ ] Add a focused test that verifies signal emission order and
  terminal-command format for DS-14B.
- [ ] Add Turkish and English labels for "Submit all with sbatch" and
  "Run all in terminal".

## Validation

- [ ] Manual: select 3 `.slurm` → right-click → "Submit all with sbatch" → all submitted alphabetically
- [ ] Manual: select 3 `.sh` → right-click → "Run all in terminal" → all queued in terminal alphabetically
- [ ] Manual: select mix of `.slurm` and `.txt` → only `.slurm` action shown
- [ ] Manual: select mix of `.sh` and `.txt` → only `.sh` action shown
- [ ] Manual: select mix of `.slurm` and `.sh` → both actions available or clearly separated
- [ ] Manual: one `.slurm` fails → remaining `.slurm` files still submitted
- [ ] Manual: progress feedback visible during batch sbatch
- [ ] Manual: summary dialog/panel shows success/failure counts
- [ ] `$env:PYTHONPATH = "src"; python -m unittest tests/test_slurm_ssh.py`
- [ ] `$env:PYTHONPATH = "src"; python -m pytest tests/test_ftp_widget.py -q`
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-14A, DS-14B, and DS-14C.

## Done Criteria

1. Multi-selected `.slurm` files can be submitted in one action
   alphabetically via `sbatch`.
2. Multi-selected `.sh` files can be queued in the terminal in one action
   alphabetically via `bash`.
3. Mixed `.slurm`/`.sh` selections are handled safely (no wrong-type
   execution).
4. All batch operations run sequentially off the GUI thread.
5. Failures in sbatch batch are reported per-file and do not stop the
   remaining files.
6. A summary of results is shown when each batch completes.
7. Menu labels are translated in both Turkish and English.

## Possible Blockers

- the existing `async_call` pattern may not support a queue of sequential
  operations
- the context-menu handler lives deep in the panel class and may need
  access to the session for both sbatch and terminal
- the `runShellRequested` signal currently lives on `FtpWidget`; the
  panel may need a new signal path to trigger terminal commands for
  batch `.sh` execution
- the Slurm backend `sbatch` method returns a raw string; extracting
  job IDs reliably for the summary may need a shared parser

## Completion Notes

- Completed at:
- Packet verdicts:
- Files changed:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex changes `Status` to `done` and fills Completion Notes.
- Codex moves this file to `waves/done/` only after all gates PASS.
- Stop the prompt; report Wave 15 as next but do not start it.
