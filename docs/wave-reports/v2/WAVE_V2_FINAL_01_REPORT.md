# WAVE V2 FINAL 01 — R5 Remediation and Strict Re-Audit

| Field | Value |
|---|---|
| Wave | W01 — Live Inventory, Feature Truth Map, and Support Freeze |
| Canonical report path | `docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md` |
| Repository | `mskomek/hpc-client-gui` |
| Branch | `develop` |
| Original baseline SHA | `eb86dea6afe830fa0c11962836bb5ecc00761fa9` |
| Current remediation baseline SHA | `2c1c7ce9b18e6e4bf81365ef8ef571182bfed745` |
| Tested implementation SHA | `2c1c7ce9b18e6e4bf81365ef8ef571182bfed745` |
| Evidence/report-only closure SHA | pending; report is not self-referential evidence |
| Current HEAD | `2c1c7ce9b18e6e4bf81365ef8ef571182bfed745` |
| Main remote develop | `468cc4f4dd683cd3c280cf5d2bf78559c8eec80a` (direct `ls-remote`; fetch failed) |
| Plugin checkout | `main` at `602e904bfd4120b3bd65b3f172d14638fe817f50` |
| Plugin develop pin | `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (direct `ls-remote`; checkout is not develop) |
| First started | 2026-09-16 |
| Last updated | 2026-09-16 |
| Session status | Remediation complete; mandatory cross-repository fetch gate blocked |
| Wave decision | **BLOCKED / NO-GO** |

```text
TARGET_WAVE: W01
SESSION_TYPE: REMEDIATION + RE-AUDIT
SESSION_SCOPE_LOCKED: YES
W02_EXECUTED: NO
W03_EXECUTED: NO
```

## Resume state

Completed and verified:

- Read current R5 planning authority (`V2-FINAL-PLAN-R5-2026-09-15`).
- Reconciled the current wx inventory and W01 evidence.
- Updated `artifacts/v2-final/W01/SUPPORT_MATRIX.md` with Quick Tour disposition, evidence classes, verification owners, open gaps, and exact freeze totals.
- Marked historical reports `SUPERSEDED` and pointed them here.
- Revalidated both historical fixes with real temporary production reverts and actual regression assertions.
- Ran real wx shell launch/shutdown and About-dialog runtime probes.

In progress: none locally.

Open P0: 0.

Open P1: `W01-PLUGIN-PIN-001` — live plugin revision is known from `git ls-remote`, but `git fetch` could not complete in this linked-worktree/network environment; checkout remains `main`, not `develop`.

Open P2/P3: 0 new W01 closure defects.

Pending: successful plugin `develop` fetch/pin and a normal pytest run with a writable temp root. The host's pytest temp-root locks are currently denied.

Last exact commands:

```text
git status --short --branch
git rev-parse HEAD
git ls-remote origin refs/heads/develop
git -C ..\hpc-client-gui-plugins ls-remote origin refs/heads/develop refs/heads/main
pytest -q tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py
PYTHONPATH=src python -c "...create_shell_frame(...); ...MainLoop(); ..."
PYTHONPATH=src python -u -c "...show_about(...); ...EndModal(...); ...MainLoop()"
```

Next action: re-run this W01 audit after plugin `develop` is fetched/pinned; do not start W02 or W03.

Evidence identities: `EV-W01-R5-001` repo pins; `EV-W01-R5-002` wx launch; `EV-W01-R5-003` About runtime; `EV-W01-R5-004/005` real sensitivity; `EV-W01-R5-006` inventory/support freeze.

## 1. Authority and repository truth

The R5 package was applied over the historical W01 `GO`; that decision was treated as stale. Main fetch failed because the linked worktree uses a shared Git directory whose `FETCH_HEAD` is permission-denied; direct `git ls-remote` returned the live remote revision. The plugin checkout is `main`, while its live `develop` pin is recorded separately. This is a blocker, not a successful fetch claim. Existing W02/W03 product and lab work was preserved and not executed or closed.

## 2. Reconciled findings

| Finding | Severity | R5 result | Evidence |
|---|---|---|---|
| `W01-REM-001` plugin not pinned | P1 | BLOCKED pending permitted fetch | EV-W01-R5-001 |
| `W01-REM-002` launch inferred from tests | P1 | FIXED / VERIFIED locally | EV-W01-R5-002 |
| `W01-REM-003` Quick Tour disappeared | P1 | FIXED; explicit `NOT-IN-V2` row | EV-W01-R5-006 |
| `W01-REM-004` optimistic support matrix | P1 | REPAIRED with evidence/owner fields | EV-W01-R5-006 |
| `W01-REM-005` self-referential sensitivity | P1 | REPAIRED with real temporary reverts | EV-W01-R5-004/005 |
| `W01-REM-006` About lacked GUI proof | P1 | FIXED / VERIFIED by wx runtime | EV-W01-R5-003 |
| `W01-REM-007` stale SHA model | P1 | REPAIRED in this report | EV-W01-R5-001 |
| `W01-REM-008` competing reports | P1 | REPAIRED; historical reports superseded | EV-W01-R5-006 |
| `W01-REM-009` report not resumable | P1 | FIXED in this report | this report |

## 3. Historical fixes and sensitivity

FIX-W01-001 keeps `help_items["tour"] = None`, omits the menu append and dead dispatch, and now has ledger row `APP-QUICKTOUR`, disposition `NOT-IN-V2`, decision `DEC-W01-QUICKTOUR`, owner W01.

FIX-W01-002 routes APP-ABOUT to `wx_about.show_about`. The About probe constructed a real `wx.Dialog`, observed version/description and four buttons for repository, license, third-party notices and close, then closed cleanly.

The historical `tests/test_w01_sensitivity.py` remains historical self-check evidence only; its mutation helpers do not close the R5 gate. The acceptance proof ran the actual W01 regression assertions against temporary production defects, then restored the tree:

| Evidence | Temporary defect | Actual assertion | Result |
|---|---|---|---|
| `EV-W01-R5-004` | Restored old Quick Tour `help_menu.Append(...)` | `TestQuickTourGhostRemoval` | exit 1, expected assertion failure, restored |
| `EV-W01-R5-005` | Restored old `wx.MessageBox(...)` APP-ABOUT branch | `TestWxAboutDialog.test_dispatch_about_not_messagebox` | exit 1, expected assertion failure, restored |

The About detector was tightened to inspect the actual APP-ABOUT branch. Test purpose IDs are `REG-W01-001` and `GUI-W01-001`.

## 4. Runtime and test evidence

Evidence class: **DEVELOPMENT WX RUNTIME**.

The controlled current-source launch observed `WX_RUNTIME=wx`, `FRAME=Frame`, `NOTEBOOK_PAGES=7`, `MENUS=5`, `STATUS=True`, `SHUTDOWN=controlled`, exit 0. Native image-handler warnings and a WebView abort during teardown were observed; no startup exception occurred. The About probe observed `ABOUT_DIALOG=Dialog`, three static-text labels, four buttons, `ABOUT_RETURN=closed`, `ABOUT_SHUTDOWN=controlled`, exit 0. This is not packaged evidence.

| Evidence | Command | Exit | Result | Does not prove |
|---|---|---:|---|---|
| `EV-W01-TEST-001` | `pytest -q tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py` | 1 | 19 setup errors from denied pytest temp-root locks | product regression result |
| `EV-W01-TEST-002` | direct invocation of all actual W01 test functions after restoration | 0 | 19 assertions pass | pytest fixture integration |
| `EV-W01-R5-002/003` | controlled real wx runtime probes | 0 | shell/About runtime passed | packaged/external behavior |

No assertion, skip, or xfail was weakened. The pytest failure is recorded as an environment failure, not relabelled as a product pass.

## 5. Cross-document and downstream consistency

- This is the only authoritative W01 final report.
- `SUPPORT_MATRIX.md` §11 is the authoritative R5 support-freeze table.
- Quick Tour is `NOT-IN-V2` in the current ledger and report.
- Historical reports are `SUPERSEDED` and contain no competing decision.
- Counts are P0 `0`, P1 `1` blocked prerequisite gate, P2 `0`, P3 `0`.
- Downstream invalidation: **NO**. W02/W03 evidence was not altered or closed; this session changed only W01 evidence/support/test governance.

## 6. Final W01 audit from zero

| Gate | Result |
|---|---|
| Main repository identity captured | VERIFIED |
| Main remote fetch completed | BLOCKED |
| Plugin develop fetched and pinned | BLOCKED |
| Actual wx launch/shutdown | VERIFIED |
| Complete visible inventory reconciled | VERIFIED |
| Removed/hidden features retain disposition | VERIFIED |
| Quick Tour final disposition | VERIFIED (`NOT-IN-V2`) |
| Support matrix has owners/evidence/gaps | VERIFIED |
| Support states match evidence class | VERIFIED for R5 freeze groups |
| FIX-W01-001 detector and sensitivity | VERIFIED |
| FIX-W01-002 detector and sensitivity | VERIFIED |
| About visible GUI/runtime proof | VERIFIED |
| Exact test counts recorded | VERIFIED per command |
| Exactly one canonical report | VERIFIED |
| Historical reports superseded | VERIFIED |
| SHA/evidence identity | PARTIAL — closure commit pending; plugin fetch blocked |
| Cross-document consistency | VERIFIED |
| Open W01 P0 | 0 |
| Open W01 P1 | 1 blocked prerequisite gate |
| Final W01 audit | **BLOCKED** |

## 7. Decision

| Field | Value |
|---|---|
| W01 remediation result | **BLOCKED / NO-GO** |
| Historical FIX-A | REPAIRED |
| Historical FIX-B | REPAIRED |
| New P0 | 0 |
| New P1 | `W01-PLUGIN-PIN-001` |
| New P2 | 0 |
| New P3 | 0 |
| Actual wx launch | PASS |
| Regression sensitivity | PASS |
| Support matrix reconciliation | PASS |
| Canonical-report uniqueness | PASS |
| Evidence identity | PARTIAL |
| Cross-document consistency | PASS |
| Downstream W02/W03 evidence invalidated | NO |
| Next recommended session | W01 pin revalidation only; then a fresh W01 audit. Do not start W02/W03. |

The historical two-fix floor is satisfied, but R5 does not permit `GO` while the mandatory current plugin pin/fetch gate and evidence-identity prerequisite remain blocked.
