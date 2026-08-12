# Wave 16 — Transfer UI Freeze and Queue Performance

Status: waiting
Owner: Codex
Priority: P0
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Prevent large transfer plans and high-frequency progress events from making the
Qt GUI unresponsive, while preserving the complete backend transfer plan and
existing transfer behavior.

## Evaluation

The supplied backlog is directionally correct, but it mixes confirmed hot paths
with speculative file splitting.

Verified current state:

- `src/truba_gui/ui/widgets/remote_dir_panel.py` is 140.6 KB / 3661 lines and
  carries too many responsibilities, but splitting it is a structural refactor,
  not the first fix for transfer freezes.
- `TransferPreflightDialog` currently creates one `QTreeWidgetItem` per plan
  item. Its summary is present, but the visible plan is not bounded.
- `TransferDialog` already bounds each list at 500 items and coalesces structural
  refreshes with a 50 ms `QTimer`; it still emits `transferProgressChanged` for
  every transfer callback.
- `TransferActivityPanel` currently caps visible rows at 500, rebuilds lists
  with `clear()`, finds progress rows by scanning the queue, and calls local
  `stat()` while rendering rows.
- `TransferItem` currently has no cached size field.
- Existing controller/signal wiring is sufficient for the first performance
  wave; extracting a new controller before measuring the fixes would expand the
  diff without proving value.

## Depends On

- Waves 01–12 are under `waves/done/`.
- Existing transfer tests and fake backends remain the only execution surface;
  no live cluster or production transfer is allowed.

## Target Files

- `src/truba_gui/ui/dialogs/transfer_dialog.py`
- `src/truba_gui/ui/widgets/ftp_widget.py`
- `src/truba_gui/ui/widgets/remote_dir_panel.py` only where transfer-item size
  is already known during plan construction
- `tests/test_ftp_widget.py` and narrowly related transfer tests
- `src/truba_gui/i18n/tr.json` and `src/truba_gui/i18n/en.json` only if a new
  visible summary string cannot reuse an existing key

## Out of Scope

- Splitting `remote_dir_panel.py`, `transfer_dialog.py`, `ftp_widget.py`,
  `jobs_outputs_widget.py`, or `login_widget.py` into new modules.
- New transfer abstractions, a new dependency, a new persistence format, or a
  new queue implementation.
- Changing concurrency, retry, conflict, resume, checksum, or cancellation
  semantics.
- Live cluster actions, credentials, deployment, packaging, or publication.

## Packets and Tasks

### DS-16A — Bound preflight rendering (Small)

- [ ] Keep the full `TransferItem` list for execution and confirmation logic.
- [ ] Render at most 200 plan rows in `TransferPreflightDialog`.
- [ ] Add one localized summary row such as `Remaining: N` when rows are
  hidden; do not create Qt widgets for hidden items.
- [ ] Preserve the existing file/folder/step totals and start/cancel behavior.
- [ ] Add a focused test with more than 200 items proving the backend list is
  unchanged and the visible widget count is bounded.

Allowed files: `transfer_dialog.py`, one focused transfer test, and both i18n
files only if required by the chosen text.

### DS-16B — Throttle progress publication (Small)

- [ ] Keep transfer callbacks flowing to the worker/backend without delay.
- [ ] Publish `transferProgressChanged` and progress text at no more than one
  update per 100–200 ms per item, always publishing the final update.
- [ ] Preserve the latest byte count and completion statistics.
- [ ] Add a deterministic test using a monotonic-clock seam or equivalent
  injected timing to prove burst callbacks are coalesced and completion is not
  lost.

Allowed files: `transfer_dialog.py` and its focused test. Do not throttle the
backend callback itself.

### DS-16C — O(1) row updates and cached item size (Medium)

- [ ] Add an optional cached size to `TransferItem` without breaking existing
  positional construction.
- [ ] Populate it only where the transfer plan already has a trustworthy size;
  do not add speculative filesystem scans.
- [ ] Maintain item-id-to-row and item-id-to-progress-widget maps in
  `TransferActivityPanel`.
- [ ] Replace queue progress scans and repeated local `stat()` calls with map
  lookup and the cached size, retaining a safe fallback when size is unknown.
- [ ] Add focused tests for direct row lookup and no repeated size lookup after
  the item is cached.

Allowed files: `transfer_dialog.py`, `ftp_widget.py`, the narrow plan-building
site in `remote_dir_panel.py` if needed, and focused tests. No broad extraction.

### DS-16D — Incremental visible-list synchronization (Medium)

- [ ] Stop rebuilding all three `TransferActivityPanel` trees for a progress
  update or a single item status change.
- [ ] Update, move, insert, or remove only affected visible rows; keep the
  existing maximum visible-row cap and remaining-count row.
- [ ] Ensure failed/completed history and context-menu item identity remain
  correct.
- [ ] Add regression coverage for queued → transferring → completed/failed
  transitions and bounded lists.

Allowed files: `ftp_widget.py` and focused tests. This packet must not change
transfer execution or controller ownership.

## Validation

- [ ] `$env:PYTHONPATH = "src"; python -m pytest tests/test_ftp_widget.py -q`
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] No real remote or cluster operation is used.
- [ ] PASS verdict exists for DS-16A, DS-16B, DS-16C, and DS-16D.

## Exit Gate

1. A plan with thousands of items creates only the bounded preflight rows.
2. Backend progress callbacks remain unthrottled, while GUI progress
   publication is bounded to roughly 5–10 Hz per item and includes completion.
3. Visible transfer progress uses O(1) item lookup and does not repeatedly stat
   already-sized files.
4. Normal queue transitions update the affected rows without full tree rebuilds.
5. Existing transfer, cancellation, retry, conflict, and resume tests remain
   green.

## Deferred Future Waves

- A separate transfer-controller extraction is deferred until this wave is
  measured and the remaining coupling is evidenced.
- `remote_dir_panel.py` decomposition is deferred to a separate architecture
  wave; its proposed eight-module split is too broad for one delivery packet.
- `jobs_outputs_widget.py`, `login_widget.py`, `main_window.py`, `cli/main.py`,
  `local_dir_panel.py`, `editor_widget.py`, `directories_widget.py`,
  `settings_dialog.py`, `services/files_ssh.py`, and `ssh/client.py` have no
  evidence here requiring immediate splitting. Size alone is not a task.

## Completion Notes

- Completed at:
- Packet verdicts:
- Files changed:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex changes `Status` to `done` and fills Completion Notes.
- Codex moves this file to `waves/done/` only after all gates PASS.
- Stop the prompt; report the next waiting wave but do not start it.
