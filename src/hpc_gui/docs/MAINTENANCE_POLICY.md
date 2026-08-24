# HPC Client GUI — Maintenance and GUI/CLI Parity Policy

This policy governs how new GUI actions relate to the CLI, and which gates a
change must pass before release. Written in English per the project's policy
that technical reports and CHANGELOG entries stay in English.

## 1) CLI-counterpart evaluation for new GUI actions

Whenever a new GUI action is added that performs a remote operation (file
transfer, scheduler operation, connection/profile management, diagnostics),
evaluate whether it needs a CLI counterpart:

- If the action maps to an operation already exposed by the CLI's service
  layer (see `files`/`jobs`/`profile`/`doctor` in
  [CLI_GUIDE_en.md](CLI_GUIDE_en.md)), no new CLI subcommand is required —
  the GUI action must call the same shared service, not duplicate logic.
- If the action is genuinely new (no existing CLI subcommand covers it),
  add a matching CLI subcommand in the same wave or capture it as a tracked
  follow-up in `CHANGELOG.md`/TODO — do not let GUI-only functionality
  silently diverge from the CLI surface.

## 2) Shared-service or explicit GUI-only rationale

Every GUI action that touches remote state must either:

- Call the same service-layer function used by the CLI (no duplicated
  request-building or parsing logic in the GUI layer), or
- Carry an explicit, written rationale for why it is GUI-only (for example,
  a purely presentational action with no remote side effect, or a
  GUI-specific convenience that has no meaningful CLI analog). Record this
  rationale next to the change (commit message or CHANGELOG entry), not
  only in review comments.

## 3) Connected gates

Before a change is considered release-ready, the following must be
consistent with each other — a change to one without updating the others is
a defect:

- **Help output** (`--help` text for any new/changed CLI subcommand or flag)
- **JSON output contract** (error and success shapes stay consistent with
  [CLI_GUIDE_en.md](CLI_GUIDE_en.md)'s text/JSON contract)
- **Unit tests** covering the new/changed behavior
- **Smoke test** (`doctor smoke`) coverage, if the change touches remote
  file transfer
- **Release checklist** ([PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md))
- **TODO** tracking for any deferred follow-up
- **CHANGELOG.md** entry describing the change

## 4) Language policy

New CHANGELOG entries and technical/maintenance reports (this document,
architecture notes, release checklists written for engineering use) are
written in English. User-facing GUI strings and the CLI guides continue to
be maintained in both Turkish and English per the project's internal
i18n requirements — this policy applies to internal/engineering
documentation only, not user-facing UI text.
