# Wave 10 — CLI DPAPI Credential Resolution

Status: waiting
Owner: Codex; RES-10B decisions reserved to Codex/user
Priority: P1
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Let the CLI resolve an already-saved, DPAPI-protected profile secret (the
same `password_dpapi` field the GUI's login widget writes via
`truba_gui.core.secret_store.protect_secret`/`unprotect_secret`) instead of
requiring `--password-stdin` on every single invocation, while never
weakening the existing protection model.

## Why This Wave Exists

TODO.md section 2 ("Güvenli kayıtlı parolayı mevcut DPAPI/Credential Store
akışıyla çöz") has been open since the CLI's first wave. Today every CLI
call that needs a password must read it fresh from stdin even when the same
Windows user already saved that exact profile's password from the GUI
(`login_widget.py`'s "remember password" flow, gated on
`os_secret_store_available()`), which makes multi-command CLI sessions and
scripting impractical on a machine where the GUI already trusts the account.

## Depends On

- Wave 02 is present under `waves/done/` (profile lifecycle/session-security
  contract)
- `src/truba_gui/core/secret_store.py`'s `is_available`/`protect_secret`/
  `unprotect_secret` functions are unchanged in behavior

## Target Files

- `src/truba_gui/cli/session.py` (`build_ssh_conn_info`)
- `src/truba_gui/cli/main.py` only for a new flag's help text/wiring
- `src/truba_gui/docs/CLI_GUIDE_tr.md`, `src/truba_gui/docs/CLI_GUIDE_en.md`
- `tests/test_cli.py`
- `tests/test_optional_ssh_credentials.py`

## In Scope

- Reading an existing profile's `password_dpapi` field via
  `truba_gui.core.secret_store.unprotect_secret` when `--profile NAME` is
  given, no `--password-stdin`/`--host` password override is present, and
  `secret_store.is_available()` is true
- A new explicit opt-out flag (e.g. `--no-saved-password`) so a caller can
  force the existing `--password-stdin` behavior even when a saved secret
  exists
- Falling back to the current stdin-based behavior unchanged whenever DPAPI
  is unavailable (non-Windows, or `is_available()` false), no saved secret
  exists for the profile, or key-based auth is already configured
  (`key_path` set)
- Tests proving: a saved-secret profile connects without stdin input, a
  profile without a saved secret still requires `--password-stdin` exactly
  as today, and the opt-out flag is honored

## Out of Scope

- Any new persistence format or field beyond the existing `password_dpapi`
- Cross-platform (non-Windows) secret-store equivalents
- Changing what the GUI itself stores or how "remember password" works
- Printing, logging, or echoing the resolved plaintext password anywhere
- Real network/SSH connections in tests (fake/mocked secret store and
  session only)

## Packets and Tasks

### DS-10A — Profile secret resolution in `build_ssh_conn_info` (Small)

- [ ] Add the DPAPI resolution path behind the conditions listed in scope.
- [ ] Add the `--no-saved-password` opt-out flag and wire it through.
- [ ] Ensure the resolved password never appears in `--verbose` logs, error
  messages, or JSON output under any failure path.
- [ ] Add fake-secret-store-backed unit tests for: saved-secret success,
  no-saved-secret fallback, opt-out flag, and DPAPI-unavailable fallback.

### RES-10B — Windows-only scope confirmation (Reserved, analyze/review only)

- [ ] DeepSeek performs analyze/review only against masked fixtures; no
  credential value appears in any task or log.
- [ ] Codex confirms the feature stays a no-op (falls back to
  `--password-stdin`) on any platform where
  `truba_gui.core.secret_store.is_available()` is false, rather than raising
  or behaving inconsistently.
- [ ] Codex confirms no plaintext password reaches disk, an environment
  variable, or a command-line argument at any point in the resolution path.

## Validation

- [ ] `$env:PYTHONPATH = "src"; python -m pytest tests/test_cli.py -q`
- [ ] `python -m unittest tests/test_optional_ssh_credentials.py`
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-10A and RES-10B.

## Done Criteria

1. A CLI call against a profile with a saved, DPAPI-protected password
   connects without any stdin input, on Windows, when the opt-out flag is
   not given.
2. Every existing password/stdin/key-based CLI behavior is unchanged when no
   saved secret applies.
3. No resolved plaintext password is ever printed, logged, or included in
   JSON/text output, including on failure.
4. `src/truba_gui/docs/CLI_GUIDE_tr.md`/`_en.md` document the new flag and resolution
   order.

## Possible Blockers

- `secret_store.is_available()` behaves differently than assumed on the
  target CI/test environment
- ambiguity about whether the opt-out flag name collides with a planned
  future flag

## Completion Notes

- Completed at:
- Packet verdicts:
- Security decisions:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex changes `Status` to `done`, fills Completion Notes, and moves this
  file to `waves/done/`.
- Stop the prompt; report Wave 11 as next but do not start it.
