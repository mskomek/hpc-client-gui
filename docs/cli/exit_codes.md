# CLI Exit Codes

The TRUBAGUI command-line surface exposes a stable numeric exit-code contract.
Constants live in `src/truba_gui/cli/errors.py` (`ExitCode`) and are the single
source of truth for every path in the CLI dispatch; do not hard-code bare
integers in `main.py`.

| Exit code | Name | Meaning |
|-----------|------|---------|
| `0` | `SUCCESS` | The command completed successfully. |
| `1` | `OPERATION_FAILED` | Generic operation failure (e.g. a file operation failed, or a `profile show MISSING` lookup for an unknown profile name). |
| `2` | `USAGE` | Usage or confirmation refusal: unsupported subcommand/argument, or a destructive `files rm` issued without `--yes`. argparse's own parsing errors also exit with `2`. |
| `3` | `CONNECTION` | Connection failure (`CLIConnectionError` raised while opening a session). A missing profile requested for connection via `--profile` raises such a failure and maps to exit `3`. |
| `124` | `TIMEOUT` | Operation timed out. The value originates in the remote-channel client's `run()` implementation, which reports `124` on a socket timeout; CLI dispatch routes a `TimeoutError` from a remote operation to exit `124` through `emit_error`. The CLI `--timeout` option applies to the four connection knobs (`timeout`, `banner_timeout`, `auth_timeout`, `channel_timeout`) and becomes the default per-operation timeout for `run()`. |

## Error output

When a command fails the dispatch routes the failure through `emit_error`
(`src/truba_gui/cli/errors.py`):

- **text mode** — an actionable human message is written to `sys.stderr` with the
  existing detail preserved.
- **json mode** — a single parseable object is written to `sys.stdout`:

  ```json
  {
    "error": {
      "message": "...",
      "exit_code": 1
    }
  }
  ```

The detail is never duplicated: the same message appears on stderr in text mode
or inside the JSON `message` field in json mode, never both.
