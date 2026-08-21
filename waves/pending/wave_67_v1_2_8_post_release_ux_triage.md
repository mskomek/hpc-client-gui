# Wave 67 — v1.2.8 Post-Release UX and Error-Surface Triage

Status: planned
Owner: Codex
Delegated worker: DeepSeek v4 Flash, one card at a time only
Priority: P1
Execution: offline audit and bounded UX fixes; no publication
Depends on: v1.2.8 release `ad38a62`
Planning baseline: public `main` after the v1.2.8 release, inspected 2026-08-21

## Goal

Turn the remaining user-visible connection problems into clear, testable work:

- remove visual noise or unintended black text-box styling behind the
  connection status/header surface near the saved connection list;
- replace opaque errors such as `common.error_code: ssh fbcbbe` with a useful
  bilingual explanation and an actionable next step;
- preserve the current connection, SSH, SFTP, transfer, and release behavior
  while improving only the affected presentation and diagnostics.

This wave is triage-first. Existing implementation must be inspected before a
new fix is proposed; do not duplicate Wave 57 connection-dialog work or Wave
11 error-message work when the current main already contains the behavior.

## Non-Negotiable Boundaries

- Read `AGENTS.md`, `rules.md`, and `MAIN_SYNC_PROTOCOL.md` first.
- Work from a clean Linux `linux-develop` branch when the session runs in WSL;
  hand off only verified changes to the Windows worktree.
- Do not access real SSH servers, TRUBA, Slurm, credentials, tokens, or secret
  stores.
- Do not publish, tag, push a branch, change release metadata, or rewrite
  history.
- Do not add dependencies, redesign the connection architecture, or perform a
  broad stylesheet rewrite.
- Any new visible string must be added to both `i18n/tr.json` and `i18n/en.json`.
- Every implementation card needs a narrow regression test and `git diff
  --check`.

## Cards

### DS-67A — Current-surface audit (Audit)

Inspect the saved-connection list, its item delegate/widgets, stylesheets, and
error rendering paths. Reproduce the reported visual and diagnostic symptoms
with existing offline fixtures or mocks only.

Allowed files: read-only repository inspection; no edits.

Deliver:

- exact widget/class and stylesheet selectors responsible for the black box or
  two-line label;
- exact error construction path for `common.error_code`;
- existing tests and the smallest safe correction point;
- `BLOCKED_BY_REPOSITORY_DRIFT` if the reported surface is absent.

### DS-67B — Connection status/header presentation (Small)

Fix only the confirmed connection status/header presentation defect. Keep the
status text single-line, preserve keyboard focus/selection/accessible text,
and keep light/dark themes consistent. If a separate saved-profile row defect
is reproduced, record it as a follow-up instead of broadening this card.

Allowed files: the identified connection-list widget/delegate and narrow UI
tests; i18n files only if a visible fallback string is required.

Acceptance:

- no unintended black text-box frame behind the connection status;
- `Connected`/`Bağlı` and disconnected text remain single-line;
- saved profile selection behavior remains unchanged;
- the narrow regression test passes offscreen.

### DS-67C — Actionable SSH diagnostic mapping (Small/Medium)

Trace opaque `common.error_code` output to its shared error boundary. Add the
smallest mapping or formatting correction that gives users:

1. what failed;
2. the likely cause when known;
3. one concrete next action;
4. the short technical code for logs/support.

Keep secrets, passwords, private keys, and full command lines out of dialogs.
Unknown codes must remain safe and readable rather than being discarded.

Allowed files: the shared error/diagnostic service, bilingual resources, and
narrow tests covering SSH/SFTP connection failures.

Acceptance:

- `ssh fbcbbe` no longer renders as an unexplained translation key;
- Turkish and English output are both covered;
- known and unknown error codes retain actionable diagnostics;
- no real network operation is used by tests.

### DS-67D — Release-safe verification (Codex)

Run the focused tests, i18n check, source smoke checks, and the relevant full
offline suite. Inspect the parent-to-branch diff and record the exact Windows
handoff commit if implementation was performed in WSL.

Publication is not part of this card.

## Exit Gate

- The reported black-box and opaque-error paths are either fixed with tests or
  explicitly marked `NOT_REPRODUCED` with evidence.
- No duplicate work from Waves 11 or 57 is introduced.
- Turkish and English resources remain synchronized.
- Focused checks and the full relevant offline suite pass.
- No real SSH/HPC operation, publication, tag, or remote branch push occurs.

## Completion Notes

- Audit verdict: PASS; the black box was traced to `TerminalHeader.status_label`
  using `QFrame.StyledPanel`, and the opaque connection error path was traced to
  the synchronous `connect_clicked` catch in `LoginWidget`.
- Cards completed: DS-67A, DS-67B, DS-67C.
- Files changed: `src/hpc_gui/ui/widgets/terminal_header.py`,
  `src/hpc_gui/ui/widgets/login_widget.py`,
  `tests/test_terminal_boundaries.py`, `tests/test_ui_errors.py`.
- Tests and exit codes: Windows focused UI/error suite -> exit 0,
  `7 passed, 5 subtests`; Linux `compileall` and bilingual JSON parse -> exit 0.
- Windows handoff commit: pending; the mounted worktree `.git` is read-only and
  `waves/` is intentionally ignored.
- Remaining uncertainty: no screenshot-based visual check was available; the
  offending frame property is covered directly by the offscreen regression test.
