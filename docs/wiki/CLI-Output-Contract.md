# CLI Output Contract

> Türkçe: [[CLI-Output-Contract-TR]]

Every command honours `--format {text,json}`. The contract below is enforced by
`src/hpc_gui/cli/errors.py` and documented canonically in
`docs/cli/exit_codes.md`.

## Success output

- **Text mode** (default): human-readable results on `stdout`.
- **JSON mode**: a single parseable object on `stdout`.

```bash
hpc-client-gui --format json commands
```

`--quiet` suppresses non-error output; `--verbose` adds diagnostics. Neither
changes the exit code.

## Error output

Failures are routed through `emit_error`:

- **Text mode** — an actionable human message on `stderr`, with the underlying
  detail preserved.
- **JSON mode** — a single object on `stdout`:

```json
{
  "error": {
    "message": "...",
    "exit_code": 1
  }
}
```

## The no-duplication rule

The same message text is never emitted twice. In text mode it appears only on
`stderr`; in JSON mode it appears only inside the `message` field. A parser
consuming JSON on `stdout` will not also find the message on `stderr`, and a
shell script capturing `stderr` in text mode will not find a stray copy on
`stdout`.

## Consuming the output

```bash
if output=$(hpc-client-gui --format json files ls /home/$USER); then
  printf '%s\n' "$output" | jq '.'
else
  status=$?
  printf '%s\n' "$output" | jq -r '.error.message'
  exit "$status"
fi
```

`exit_code` inside the error object matches the process exit status, so either
source is usable — but the process exit status is the simpler one to branch on.

## See also

[[CLI Exit Codes|CLI-Exit-Codes]] ·
[[CLI Command Reference|CLI-Command-Reference]]
