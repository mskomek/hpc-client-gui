# Wave 12 — Saved-Settings CLI Access for External/AI Tools

Status: waiting
Owner: Codex
Priority: P2
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Let an external tool (an AI assistant, a script, a scheduled job) drive the
TRUBAGUI CLI against the user's already-saved profile — e.g. `arf` — without
repeating host/user/key flags, and only when the user has explicitly turned
that access on in Settings. Add a machine-readable command inventory so the
tool can discover the surface instead of guessing.

## Why This Wave Exists

Everything needed is already half-present but not connected:

- `src/truba_gui/cli/session.py` already resolves `--profile NAME` against
  `truba_gui.config.storage.load_profiles()`, but the name must be passed on
  every single invocation; there is no saved default.
- `truba_gui.config.storage` already has `load_settings()`/`update_settings()`
  over `~/.truba_slurm_gui/config.json`, and the Settings dialog already
  renders boolean settings — but nothing gates the CLI.
- `--help` already exists per TODO section 1, but it is human prose only.
  An agent enumerating commands has to scrape text.

Consequence today: a saved profile is a GUI-only convenience, and any process
that can run the exe gets the full remote surface with no user-visible switch
to allow or revoke it. This wave makes saved settings usable from the CLI and
puts the access behind one explicit, off-by-default setting.

## Depends On

- Wave 01 (CLI contracts) is present under `waves/done/`
- Wave 10 (`cli_dpapi_credential_resolution`) is **not** a dependency; this
  wave must not resolve or read any stored secret

## Target Files

- `src/truba_gui/config/storage.py` (two typed getters/setters only)
- `src/truba_gui/cli/session.py` (default-profile fallback)
- `src/truba_gui/cli/main.py` (access gate, `commands` subcommand)
- `src/truba_gui/ui/dialogs/settings_dialog.py` (checkbox + default-profile
  selector)
- `src/truba_gui/i18n/tr.json`, `src/truba_gui/i18n/en.json`
- `src/truba_gui/docs/CLI_GUIDE_tr.md`, `src/truba_gui/docs/CLI_GUIDE_en.md`
- `src/truba_gui/docs/HELP_tr.md`, `src/truba_gui/docs/HELP_en.md` (the new
  Settings checkbox, in the existing settings section only)
- `scripts/package_release.ps1`, `scripts/release_smoke.ps1`
- `tests/test_cli.py`

## In Scope

- Setting `cli_external_access_enabled` (bool, **default `False`**) stored in
  the existing settings block via `update_settings`.
- Setting `cli_default_profile` (str, default `""`).
- A gate in `main()`: every command that opens a remote session (`profile
  test`, `doctor connection`, `doctor smoke`, all `files *`, all `jobs *`)
  fails with `ExitCode.OPERATION_FAILED` and one clear message naming the
  Settings toggle when `cli_external_access_enabled` is false.
- Commands that stay allowed regardless: `--help`/`-h` (including every
  subparser help), `version`, `gui`, `commands`, `doctor environment`,
  `profile list`, `profile show`.
- `--profile` omitted → fall back to `cli_default_profile`; an explicit
  `--profile` always wins. A configured default that no longer exists must
  produce the existing `Profile not found: NAME` error, not a silent skip.
- New `commands` subcommand printing the argparse tree (command path, help
  text, options) plus the exit-code table, honoring the existing
  `--format text|json` flag. Implement by walking the parser built in
  `_parser()` — no hand-maintained second list, no new dependency.
- Settings dialog: one checkbox for the toggle and one combo listing saved
  profile names (plus an empty "no default" entry), wired through the
  existing `_apply_settings` path.
- Both CLI guides document the toggle, the default-profile fallback, and the
  `commands` output shape, with an explicit note that enabling the toggle
  grants any local process the remote surface.

## Out of Scope

- Reading, resolving, storing, or printing any password, key passphrase, or
  DPAPI/Credential-Store secret (Wave 10 owns credential resolution)
- Any network daemon, RPC socket, HTTP endpoint, or MCP server
- Per-command or per-tool permission granularity, allowlists, audit logging
- New exit codes (`OPERATION_FAILED` covers the denied case)
- Changing existing command names, flags, or JSON contracts
- Real network/SSH connections in tests

## Packets and Tasks

### DS-12A — Settings, default profile, access gate (Medium)

- [ ] Add `get_cli_external_access_enabled(default=False)` /
  `set_cli_external_access_enabled` and `get_cli_default_profile()` /
  `set_cli_default_profile` to `config/storage.py`, matching the existing
  getter/setter style and bool coercion.
- [ ] In `session.py`, fall back to `cli_default_profile` when `--profile` is
  absent or empty.
- [ ] In `main.py`, gate the remote-session commands on the toggle; leave the
  allowed list above untouched.
- [ ] Tests (monkeypatched settings, no real SSH): denied command exits
  `OPERATION_FAILED` with the message and does **not** attempt a connection;
  allowed commands still work with the toggle off; default profile is used
  when `--profile` is omitted; explicit `--profile` overrides the default; a
  stale default profile name yields `Profile not found`.

### DS-12B — `commands` inventory subcommand (Small)

- [ ] Add `commands` to `_parser()` and a `_run_commands` that walks the
  parser tree and emits text and JSON forms.
- [ ] Test: `commands --format json` parses, contains `files ls` and
  `jobs submit`, and includes the exit-code values from `ExitCode`.

### DS-12D — Full help and usage examples on a bad command (Small)

Today a wrong or incomplete command prints only the one-line `usage:` plus
argparse's "invalid choice" list and exits `2` (verified: `files`, `fles`,
`files lss`). The valid choices are listed but the flags and any example are
not, so the caller has to re-run with `--help`.

- [ ] Subclass `argparse.ArgumentParser` with an `error()` override that
  prints that parser's **full** help to `sys.stderr` before exiting `2`, and
  use it for the root parser and every subparser (`parser_class=`). Keep the
  exit code at `ExitCode.USAGE` — the contract in `docs/cli/exit_codes.md`
  does not change.
- [ ] Add an `epilog` with 3–4 real one-line examples to the root parser only
  (e.g. `hpc-client-gui files ls /truba/home --profile arf`), using
  `RawDescriptionHelpFormatter` so the lines do not re-wrap. No per-subcommand
  epilogs — the per-command flag help plus `commands --format json` already
  cover that.
- [ ] Tests: `files`, an unknown group, and an unknown subcommand each exit
  `2` and their stderr contains the parser's option list (not just the
  `usage:` line); root `--help` contains the example block.

### DS-12E — `help/` folder in the release and a freshness gate (Small)

Today the docs ship only inside `_internal/truba_gui/docs/` (via the spec's
`datas` entry) — buried next to the frozen runtime, not where a user looks.
`scripts/package_release.ps1` copies `dist/*` plus `CHANGELOG.md` into
`dist/releases/v<version>/` and nothing else.

- [ ] In `scripts/package_release.ps1`, copy `HELP_tr.md`, `HELP_en.md`,
  `CLI_GUIDE_tr.md`, `CLI_GUIDE_en.md` from `src/truba_gui/docs/` into
  `<versionDir>/help/`. Copy only — `src/truba_gui/docs/` stays the single
  source of truth, and the existing `_internal` bundle is untouched (the
  in-app help still reads it).
- [ ] Fail packaging with a clear message if any of the four files is
  missing.
- [ ] Extend `scripts/release_smoke.ps1` (or the existing CLI gate script) to
  assert `help/` exists with the four files, and that every command path from
  `commands --format json` (DS-12B) appears in both CLI guides — this is the
  automatic staleness check the Release Packaging Rule now requires.
- [ ] Do not add a doc generator, a docs site, or an HTML build.

### DS-12C — Settings dialog + i18n + guides (Small)

- [ ] Checkbox and default-profile combo in the settings dialog, persisted on
  apply.
- [ ] Turkish and English strings added together.
- [ ] Both CLI guides updated, including the security note.
- [ ] `HELP_tr.md`/`HELP_en.md` gain one line for the new Settings checkbox in
  the existing settings section (no new section, no exit-code duplication —
  `docs/cli/exit_codes.md` stays unchanged since no code is added).

## Validation

- [ ] `$env:PYTHONPATH = "src"; python -m pytest tests/test_cli.py -q`
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-12A, DS-12B, and DS-12C.

## Done Criteria

1. With the toggle off (the default), every remote CLI command fails with one
   actionable message and no connection attempt.
2. With the toggle on and a default profile saved, `files ls /path` works with
   no `--profile` flag.
3. `commands --format json` enumerates the full command tree and exit codes.
4. The toggle and default profile are settable from the Settings dialog and
   documented in both CLI guides.
5. A wrong or incomplete command prints the full help for that command, not
   just the `usage:` line, and the root help shows real examples.
6. A packaged release has a `help/` folder next to the `.exe` with the four
   Turkish/English GUI and CLI documents, and packaging fails if one is
   missing or a CLI command is undocumented.

## Possible Blockers

- The settings dialog's profile list may need the profile names loaded at
  dialog-open time; if the dialog has no existing access to `load_profiles`,
  add the import rather than threading new state through the caller.

## Completion Notes

- Completed at:
- Packet verdicts:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex changes `Status` to `done`, fills Completion Notes, and moves this
  file to `waves/done/`.
- Stop the prompt; report that no further wave is currently queued.
