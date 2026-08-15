# DS-42E — Wiki CLI and automation cluster (English)

## Outcome

Replace the stub content of exactly these five files under `docs/wiki/`:

`CLI-Overview.md`, `CLI-Command-Reference.md`, `CLI-Exit-Codes.md`,
`CLI-Output-Contract.md`, `Scripting-Examples.md`.

Keep the existing pattern: an H1 title, then `> Türkçe: [[<Page>-TR]]`.
Do not create, rename, or delete files.

## Source of truth

- `src/hpc_gui/cli/main.py` (argument parser is authoritative for commands,
  subcommands, flags, and help text)
- `src/hpc_gui/cli/errors.py` and `docs/cli/exit_codes.md` (exit codes)
- `src/hpc_gui/docs/CLI_GUIDE_en.md`

Derive the command inventory from the parser in `main.py` and reconcile it with
`CLI_GUIDE_en.md`. Cover all groups: `gui`, `version`, `commands`, `profile`,
`doctor`, `files`, `edit`, `sh`, `run`, `terminal`, `interactive`, `jobs`.

## Content requirements

- Document global options, the saved-secret resolution order for `--profile`,
  the stdin-based sensitive-value input flag (`--password-stdin`), strict
  host-key checking, and the external-CLI-access gate.
- `CLI-Exit-Codes.md` must be consistent with `docs/cli/exit_codes.md` and
  `errors.py`. Cite that table; do not fork or renumber it.
- `CLI-Output-Contract.md` documents the text-versus-JSON contract, including
  the single-object error form `{"error": {"message": "...", "exit_code": N}}`
  and the rule that the message text is never duplicated across both formats.
- `Scripting-Examples.md` shows non-interactive automation. Every example that
  the CLI requires confirmation for must be shown with its confirmation flag and
  marked as mutating.
- Internal wiki links use `[[Page-Name]]` and must target existing files.

## Forbidden

- Inventing flags or changing exit-code semantics.
- Any example that embeds a password, token, or key material in a command line,
  environment variable, or file shown in the page.
- Any mention of `waves/`, `.agent-runs/`, DeepSeek, or internal AI
  orchestration tooling.
- Editing any file other than the five listed pages.

## Acceptance

- The documented command inventory matches the parser in `main.py` exactly.
- Every exit code cited exists in `errors.py`.
- No example contains a credential.
- No corrupted branding token (`Lreate`, `LLI`, `conoig`, `JSnN`, `HPL`).
