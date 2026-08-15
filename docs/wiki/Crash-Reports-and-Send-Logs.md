# Crash Reports and Send Logs

> Türkçe: [[Crash-Reports-and-Send-Logs-TR]]

## The crash reporter

If the application terminates unexpectedly, it writes a crash record under
`~/.truba_slurm_gui` together with a crash flag. On the next start the flag is
detected and a crash dialog is offered, so you can report what happened while
the details are still available. Once handled, the flag is cleared and the
dialog does not reappear.

## The send-logs dialog

The send-logs dialog shows the collected log text before anything leaves your
machine, and gives you two actions:

![Crash Reports and Send Logs](https://raw.githubusercontent.com/wiki/mskomek/hpc-client-gui/assets/send-logs.png)

*The send-logs dialog. Note the redaction: the account name and host already read `<user>` and `<host>`.*

- **Copy to clipboard** — copies the displayed text so you can paste it into an
  issue.
- **Export diagnostics** — writes a ZIP bundle to a location you choose.

Review the displayed text before you copy or attach it. You are the last check.

## What the bundle contains

`create_diagnostic_bundle` collects the following files from
`~/.truba_slurm_gui`, if they exist:

| File | Contents |
|---|---|
| `app.log` | The application log |
| `history.json`, `history.jsonl` | Command and job history |
| `last_batch.json` | The most recent batch submission record |
| `processes.json` | Tracked helper processes |
| `transfer_journal.jsonl` | The transfer journal used for resume |
| `vcxsrv_stdout.log`, `vcxsrv_stderr.log` | X11 helper output (Windows) |
| `language.json` | The selected interface language |
| `manifest.json` | Generation timestamp and bundle name (added by the export) |

Each text file is passed through redaction before it is written into the ZIP.
A file that cannot be read as text is included as-is rather than dropped
silently, so nothing disappears without you knowing.

## What the bundle deliberately excludes

`config.json` is **never** included. It holds your saved connection profiles —
hostnames and usernames — plus encrypted password material and salts. None of
that is needed to debug from logs, so it does not travel in a "send me your
logs" bundle.

## What redaction does

Redaction replaces your local account name, every saved profile's remote
username, and every saved profile's hostname or IP with `<user>` and `<host>`.
This works inside paths as well, so `/home/yourname/run.sh` and
`C:\Users\yourname\...` become `/home/<user>/run.sh` and `C:\Users\<user>\...`.

Redaction is best-effort pattern replacement, not a guarantee. It cannot know
about a hostname you never saved as a profile, or an identifier that appears
only inside your own job output. Read the bundle before you share it.

Details: [[Data and Privacy|Data-and-Privacy]].

## Reporting

Attach the bundle to a GitHub issue. For anything with security impact, use
the confidential channel described in `SECURITY.md` instead of a public issue —
see [[Security Model|Security-Model]].

## See also

[[Logs and Diagnostics|Logs-and-Diagnostics]] ·
[[Troubleshooting|Troubleshooting]] ·
[[Support and Donations|Support-and-Donations]]
