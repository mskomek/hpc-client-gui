# Wave 24 — Transfer Execution Ownership

Status: waiting
Owner: Codex
Priority: P0
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Make transfer execution independent of hidden dialogs and make each upload's
temporary-file completion use one isolated SFTP channel from open through
rename and close.

## Dependencies

- Waves 16 and 17 are complete.
- Wave 19 supplies a trustworthy offline test baseline.

## Evidence

- `RemoteDirPanel` creates `TransferDialog` even when the dialog is hidden;
  that dialog still owns queue state, workers, cancellation, and progress.
- `TransferActivityPanel` receives a second callback representation of the
  same dialog state.
- `SSHFilesBackend.upload()` opens an isolated transfer channel, but
  `SSHFilesBackend.rename()` uses shared `ssh.sftp`; an upload to `.part` and
  its final rename are therefore not one channel-scoped transaction.
- Download already uses a local `.part` followed by `os.replace`; its remaining
  concerns are cancellation, cleanup, and resume identity rather than another
  atomic-finalization redesign.

## Packets

### DS-24A — Transfer ownership and cancellation audit (Audit)

- Map every producer and consumer of transfer queue, progress, retry, cancel,
  and completion state.
- Identify the smallest controller boundary that can be observed by both the
  dialog and activity panel without changing transfer behavior.
- State exact files, test doubles, migration order, and capacity risk; do not
  edit source or select a new retry/reconnect policy.

Allowed: read-only inspection of existing transfer UI/services/tests. Forbidden:
all edits, real transfers, credentials, performance redesign, and policy
decisions.

### DS-24B — Headless transfer controller ownership (Medium)

- Move queue lifecycle, worker scheduling, retry, cancel, and progress state
  behind one non-dialog controller, reusing existing worker behavior.
- Make `TransferDialog` and `TransferActivityPanel` observers/controllers of
  that state rather than separate owners of copied lists.
- Preserve visible limits, retry, stop-after-current, final progress emission,
  and no-GUI-thread blocking behavior.

Allowed: one new controller module, `transfer_dialog.py`, `ftp_widget.py`, the
narrow creation site in `remote_dir_panel.py`, and focused transfer tests.
Forbidden: new dependencies, persistence, retry-policy changes, broad UI
splitting, and live operations. Stop and split if this exceeds 5 files or 400
changed lines.

### DS-24C — Channel-scoped atomic upload completion (Medium)

- For SFTP backends that support isolated transfer channels, perform open,
  resume/upload to `.part`, optional verification already in the current flow,
  rename, and close on that same channel.
- Preserve capability fallback for non-SFTP backends and existing progress,
  error, and `.part` behavior.
- Add offline fake-channel tests proving no shared client performs the rename,
  including failure and cleanup paths.

Allowed: `services/files_ssh.py`, `services/transfer_mode.py` only when needed,
and focused transfer tests. Forbidden: Paramiko performance tuning, chunked
transfer, connection recovery, checksum-policy changes, and live servers.

### DS-24D — Cancellation and partial-file regression matrix (Small)

- Add deterministic tests for cancel/failure during upload, rename, download,
  local replacement, and ASCII conversion.
- Assert that final names never expose a partial file and document the retained
  `.part` cleanup/resume behavior already implemented.
- Do not add automatic reconnect or a stronger resume identity in this packet.

Allowed: focused transfer tests and a narrow existing helper only if a test seam
is essential. Forbidden: production UI changes, new persistence, live
connections, or a new transfer protocol.

## Exit Gate

One controller owns transfer state, UI surfaces observe it without duplicate
queue state, an SFTP upload's rename shares its isolated channel, and all
cancellation/failure cases are proven offline.

## Deferred

Benchmark `put/get/prefetch/pipelining` before changing fast paths. Automatic
reconnect, resume fingerprints, chunking, delegate-based rendering, and history
storage require separate evidence and product decisions.

## Completion Notes

- Completed at:
- Packet verdicts:
- Files changed:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex archives this wave only through `wave-queue.ps1` after every packet
  has PASS evidence.
- Stop; report the next waiting wave but do not start it.
