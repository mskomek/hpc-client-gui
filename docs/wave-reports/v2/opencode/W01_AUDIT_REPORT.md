# W01 Audit Report

## Decision

**REOPEN** — the current implementation and focused GUI checks are green, but
the canonical W01 report is not current for the repository truth it claims.

## Authority and repository truth

- Audited exactly `waves/pending/W01.md`; it is present and unambiguous. No file
  under `waves/bak/` was read, and no other Wave was audited or started.
- Re-read `CORE_EXECUTION_RULES.md`, all 21 W01 registry rows, the eight
  directly W01-owned TODO rows, the ownership map, source sections A0,
  `TASK-W01-002`, and `TASK-W01-003`, plus the canonical W01 report and raw
  W01 evidence files.
- Branch/SHA: `develop` / `f94adb640136181dbaafa84f62c753b013f0b94e`.
- Pending authority check: 61 definitions (`W01.md`–`W61.md`), exactly one
  `W01.md`; W01 dependencies are `None`.
- Independently measured working tree: 25 status entries, 23 tracked modified
  paths, 1,662 insertions and 408 deletions in the tracked diff, plus two
  untracked paths. The canonical W01 report instead records 20 entries, 18
  tracked paths, 1,433 insertions and 278 deletions.
- Plugin repository identity: `develop` /
  `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; only unrelated
  `.github/social-preview.jpg` is untracked. No package/final artifact SHA is
  applicable to this GUI-inventory Wave.

## Independent verification

- Focused command:
  `.venv\Scripts\python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\opencode\w01-audit-20260921-final" tests/test_w04_support_freeze.py tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py tests/test_wx_help.py tests/test_command_palette.py tests/test_command_palette_regression.py tests/test_help_shortcut_reference.py tests/test_about_dialog.py tests/test_wx_shell.py tests/test_help_search.py tests/test_help_catalog.py tests/test_platform_keymap.py`
  — **72 passed**, exit 0; temporary output was removed.
- Fresh wx runtime probe at the current checkout exited 0: 7 pages in the
  required order, 5 menus, `Ready` status, real About dialog/buttons, and
  controlled shutdown. Non-fatal duplicate-image/WebView2 teardown messages
  were observed.
- Source/test checks confirm the reported W01 surface decisions, dispatch
  reachability, stable `page_controls`, context-menu bindings, and absence of
  an advertised standalone command palette.
- `git diff --check` exited 0 apart from normal LF/CRLF conversion warnings.
  The current diff was reviewed for scope, secrets, generated noise, and test
  weakening; the changed paths are unrelated lab/FFS/evidence/report work and
  no W01 product/test change is credited.

## Findings

| Finding | Severity | Owner/state |
|---|---|---|
| `W01-AUDIT-005`: `W01_WAVE_REPORT.md` current-execution identity is stale: it records 20 status entries / 18 tracked paths / 1,433 insertions / 278 deletions, while the current checkout has 25 / 23 / 1,662 / 408. Its “report current” and diff-review claims therefore cannot be accepted for close. | P1 | W01 report refresh required; OPEN |
| `W01-AUDIT-006`: retained raw artifacts `EV-W01-001`–`EV-W01-005` are pinned to historical SHA `afd4fb1d6ed3d0bbd87b9b6db6115eb159f63a87`, not current HEAD `f94adb640136181dbaafa84f62c753b013f0b94e`. Current runtime/test commands are independently green, but the canonical evidence identity must be reconciled before close. | P1 | W01/W05 report-evidence reconciliation; OPEN |

The owned GUI requirements and TODO decisions otherwise pass the independent
source, test, and runtime checks. W01 requires GUI evidence only; LOCAL_REAL
HPC lab protocol is not applicable because no W01 row requires `EXTERNAL`
evidence.

## Final result

Do not close W01 until the canonical report/evidence identity is refreshed to
the current tree and a fresh independent audit is run afterward. No product or
test files were changed by this audit.

WAVE_PHASE_STATUS: REOPEN
