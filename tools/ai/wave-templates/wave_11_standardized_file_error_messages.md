# Wave 11 — Standardized Remote File Error Messages

Status: waiting
Owner: Codex
Priority: P2
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Give every `files` subcommand a consistent, documented error shape for the
three most common real-world failure cases — path not found, permission
denied, and an empty (but existing) directory listing — instead of whatever
raw SFTP/OS error text happens to surface today.

## Why This Wave Exists

TODO.md section 4 ("Boş klasör, erişim hatası ve bulunamayan yol hatalarını
standardize et") is open. Today `_run_files` in `src/truba_gui/cli/main.py`
catches only `CLIConnectionError` and `TimeoutError` specifically; every
other failure (a missing remote path, a permission-denied SFTP error, etc.)
falls through to whatever exception message
`truba_gui.services.files_ssh.SSHFilesBackend` happened to raise, which is
often a raw remote errno string. `_raise_on_failed_run` in `files_ssh.py`
already distinguishes a shell-timeout (exit 124) from a generic failure, but
does not distinguish "not found" from "permission denied" from other
failures. An empty directory listing (`files ls` on a real, existing, empty
folder) is not a failure at all today and must stay that way — this wave
must not turn a legitimately empty listing into an error.

## Depends On

- Wave 03 is present under `waves/done/` (file contracts and conflict
  policy)

## Target Files

- `src/truba_gui/services/files_ssh.py`
- `src/truba_gui/cli/main.py` (`_run_files` error handling only)
- `src/truba_gui/cli/errors.py` only if a new shared exception type is
  justified
- `src/truba_gui/docs/CLI_GUIDE_tr.md`, `src/truba_gui/docs/CLI_GUIDE_en.md`
- `tests/test_cli.py`

## In Scope

- Distinguishing, at the `SSHFilesBackend` layer, "remote path does not
  exist" (SFTP `ENOENT`/`IOError` with `errno.ENOENT`) from "permission
  denied" (`errno.EACCES`/`EPERM`) from other remote failures, using
  `paramiko`'s existing `IOError`/`OSError` errno on SFTP operations — no new
  remote-side probing or extra round trips
- Mapping "not found" to a clear, consistent message across `ls`, `stat`,
  `checksum`, `download`, `cp`, `mv`, `rm` (same wording pattern each time)
- Mapping "permission denied" to a clear, consistent message across the same
  commands
- Keeping `files ls` on a real, existing, empty directory as a **successful**
  empty-list result (`[]` in JSON, no output rows in text), never an error
- A small table in `src/truba_gui/docs/CLI_GUIDE_tr.md`/`_en.md` documenting the three
  cases and their exact message shape

## Out of Scope

- Changing exit codes (`OPERATION_FAILED`/`CONNECTION`/`TIMEOUT` stay as
  documented in `docs/cli/exit_codes.md`)
- Retrying or auto-creating a missing path
- Any GUI-side error-message change
- Real network/SSH connections in tests (mocked/fake SFTP client only,
  raising `OSError`/`IOError` with the relevant `errno` value)

## Packets and Tasks

### DS-11A — Errno-based message mapping in `SSHFilesBackend` (Small)

- [ ] Add a small errno-to-message helper used by the affected methods.
- [ ] Apply it to `ls`, `stat`, `checksum`, `download`, `cp`, `mv`, `rm`.
- [ ] Confirm `mkdir`/`upload` keep their existing, already-reasonable
  create-time error behavior (not in scope to change).
- [ ] Add unit tests with a fake SFTP client raising `OSError(errno.ENOENT,
  ...)` and `OSError(errno.EACCES, ...)` for each affected command, plus a
  regression test proving an empty-but-existing directory still returns a
  successful empty list.

### DS-11B — CLI guide documentation (Small)

- [ ] Add the "not found" / "permission denied" message table to both CLI
  guides, cross-referenced with the existing exit-code table.
- [ ] No command/flag/topology changes — text only, matching the existing
  guides' structure and tone.

## Validation

- [ ] `$env:PYTHONPATH = "src"; python -m pytest tests/test_cli.py -q`
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-11A and DS-11B.

## Done Criteria

1. A missing remote path produces the same message shape across every
   affected `files` subcommand.
2. A permission-denied remote path produces the same message shape across
   every affected `files` subcommand, distinct from "not found".
3. `files ls` on a real, existing, empty directory still returns a
   successful empty result, not an error.
4. Both CLI guides document the three cases.

## Possible Blockers

- the real SFTP server's errno values for "not found" vs "permission denied"
  differ from paramiko's usual mapping on some remote systems (if so,
  document the observed exception shape instead of guessing)

## Completion Notes

- Completed at:
- Packet verdicts:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex changes `Status` to `done`, fills Completion Notes, and moves this
  file to `waves/done/`.
- Stop the prompt; report that no further wave is currently queued.
