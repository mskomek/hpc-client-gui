# CLI Exit Codes

> Türkçe: [[CLI-Exit-Codes-TR]]

The command-line interface has a stable numeric exit-code contract. The
constants live in `src/hpc_gui/cli/errors.py` (`ExitCode`) and the canonical
table is `docs/cli/exit_codes.md` in the repository. This page cites that
table; it does not fork it.

| Exit code | Name | Meaning |
|---|---|---|
| `0` | `SUCCESS` | The command completed successfully. |
| `1` | `OPERATION_FAILED` | Generic operation failure — for example a failed file operation, or `profile show` for a name that does not exist. |
| `2` | `USAGE` | Usage error or refused confirmation: an unsupported subcommand or argument, or a destructive command such as `files rm` issued without `--yes`. Argument-parsing errors also exit `2`. |
| `3` | `CONNECTION` | Connection failure while opening a session. Requesting a missing profile for a connection maps here. |
| `124` | `TIMEOUT` | The operation timed out. |

## Notes for automation

- Branch on the exit code, never on message text. Messages are localized and
  may be reworded; codes are contractual.
- `2` means *you asked for something the interface would not do* — usually a
  missing `--yes` on a destructive command. Retrying without fixing the
  invocation will fail identically.
- `3` distinguishes "could not reach or authenticate to the cluster" from "the
  operation ran and failed" (`1`). Retry logic belongs on `3`, not on `1`.
- `124` follows the conventional timeout code. `--timeout` sets the connection
  knobs and the default per-operation timeout.

## See also

[[CLI Output Contract|CLI-Output-Contract]] ·
[[Scripting Examples|Scripting-Examples]] ·
[[Troubleshooting|Troubleshooting]]
