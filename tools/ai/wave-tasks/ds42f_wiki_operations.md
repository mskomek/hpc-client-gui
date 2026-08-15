# DS-42F — Wiki operations, security, and troubleshooting cluster (English)

## Outcome

Replace the stub content of exactly these six files under `docs/wiki/`:

`Logs-and-Diagnostics.md`, `Crash-Reports-and-Send-Logs.md`,
`Troubleshooting.md`, `Security-Model.md`, `Data-and-Privacy.md`, `FAQ.md`.

Keep the existing pattern: an H1 title, then `> Türkçe: [[<Page>-TR]]`.
Do not create, rename, or delete files.

## Source of truth

- `src/hpc_gui/core/log_redaction.py`, `core/diagnostics.py`,
  `core/crash_reporter.py`, `core/secret_store.py`, `core/crypto_master.py`
- the send-logs dialog under `src/hpc_gui/ui/`
- `src/hpc_gui/cli/main.py` (`doctor environment|connection|smoke`)
- `SECURITY.md`, `src/hpc_gui/docs/HELP_en.md`

## Content requirements

- State the real log location `~/.truba_slurm_gui/app.log` (rotating) and say
  plainly that the legacy directory name is retained for compatibility.
- Cover `doctor environment`, `doctor connection`, `doctor smoke`, the crash
  reporter, the send-logs dialog, and log redaction.
- `Security-Model.md`: client-side-only scope, secret storage, the rule that
  credentials are never logged, host-key checking, X11 process cleanup on exit,
  and the `SECURITY.md` reporting channel.
- `Data-and-Privacy.md`: exactly what a sent log bundle contains and what is
  redacted before it leaves the machine, traceable to `log_redaction.py` and
  `diagnostics.py`.
- `Troubleshooting.md` and `FAQ.md` are organized by observed symptom.
- Internal wiki links use `[[Page-Name]]` and must target existing files.

## Forbidden

- Security claims not backed by code.
- Recommending that host-key checking be disabled as a routine fix, or any step
  that weakens verification by default without an explicit, scoped warning.
- Recommending that unredacted logs be shared.
- Any mention of `waves/`, `.agent-runs/`, DeepSeek, or internal AI
  orchestration tooling.
- Editing any file other than the six listed pages.

## Acceptance

- Every redaction claim is traceable to `log_redaction.py` behavior.
- The send-logs page lists bundle contents matching the dialog and
  `diagnostics.py`.
- No troubleshooting step exposes a secret.
- No corrupted branding token (`Lreate`, `LLI`, `conoig`, `JSnN`, `HPL`).
