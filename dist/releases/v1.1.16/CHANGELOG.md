## v1.1.16
- CLI: the CLI now resolves an already-saved, DPAPI-protected profile
  password automatically when `--profile NAME` is given, instead of
  requiring `--password-stdin` on every invocation; a new
  `--no-saved-password` flag opts back into the previous stdin-only
  behavior. Falls back unchanged whenever DPAPI is unavailable, no saved
  secret exists, or key-based auth is configured. The resolved value is
  never printed, logged, or included in any output.
- CLI: `files ls/stat/checksum/download/cp/mv/rm` now report "not found" and
  "permission denied" failures with the same message shape and the affected
  remote path attached, instead of raw SFTP/shell error text. An existing,
  empty remote directory still returns a successful empty listing.
- CLI: added a new, off-by-default Settings toggle ("Allow external CLI
  access to remote commands") that gates every remote-session CLI command
  (`files *`, `jobs *`, `profile test`, `doctor connection/smoke`); denied
  commands fail with one clear message before any connection attempt.
  `profile list/show`, `doctor environment`, `version`, `gui`, and the new
  `commands` subcommand stay available regardless.
- CLI: added a saved default-profile setting so `--profile` can be omitted
  on repeated invocations; an explicit `--profile` always overrides it.
- CLI: added a new `commands` subcommand that prints the full command
  inventory (every command path, flag, and help text) plus the exit-code
  table, in text or `--format json`, for scripting and automation.
- CLI: an unknown or incomplete command now prints that command's full help
  text (not just the one-line usage string) before exiting; the root
  `--help` output now includes real, working example invocations.
- Settings: added a checkbox and a saved-profile picker for the two new CLI
  settings above, in the Connection and X11 group.
- Release packaging: packaged releases now include a `help/` folder next to
  the executable with the Turkish and English GUI help and CLI guides; an
  automated release-smoke check fails packaging if any of the four files is
  missing or if a CLI command path is undocumented in either CLI guide.
- Documentation: both CLI guides document the saved-secret resolution order,
  the external-access toggle and its security implications, the
  default-profile fallback, and the `commands` output shape.
