> SUPERSEDED (W05, 2026-09-18) — historical W01 completion report. The single
> canonical W01 report is `docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md`
> (decision PASS at main `0f8902a0` / plugin `f0abb7e7`). This file carries no
> competing decision; history preserved.

# W01 COMPLETION REPORT

**Wave:** W01 — Live Inventory, Feature Truth Map, and Support Freeze
**Date:** 2026-09-15
**Pinned SHA:** `afd4fb1d6ed3d0bbd87b9b6db6115eb159f63a87`

---

## 1. Files changed

| File | Change | Purpose |
|---|---|---|
| `src/hpc_gui/wx_shell.py` | `-16 / +3` lines | FIX-A: removed Quick Tour no-op; FIX-B: wired About to new dialog |
| `src/hpc_gui/wx_about.py` | NEW (143 lines) | FIX-B: proper wx About dialog with version, repo, license, notices |

## 2. User-visible behavior changed

| Before | After |
|---|---|
| Help > Quick Tour menu item visible, click does nothing | Quick Tour menu item removed from Help menu |
| Help > About shows plain wx.MessageBox with minimal text | Help > About shows proper dialog with version, description, repository URL, license, third-party notices |

## 3. Tests added/changed

No tests were added or changed. All pre-existing tests pass (89+ across narrow and broader suites).

## 4. Evidence files

| File | Content |
|---|---|
| `EV-W01-001_PINNED_REPO_STATE.md` | Repository state at session start |
| `EV-W01-002_VISIBLE_SURFACE_INVENTORY.md` | Complete menu, tab, header, dispatch inventory |
| `EV-W01-003_EVENT_SERVICE_TRACE.md` | 10 event-to-backend trace samples proving real wiring |
| `EV-W01-004_CONTEXT_MENU_INVENTORY.md` | 19 context menus inventoried (13 wx + 6 Qt) |
| `EV-W01-005_SETTINGS_DRIFT.md` | Settings drift classification (75 settings audited) |
| `SUPPORT_MATRIX.md` | Full support matrix with classifications |
| `WAVE_01_SESSION_REPORT.md` | Complete session report with FIX-A/FIX-B details |

## 5. Open findings

| ID | Severity | Status | Notes |
|---|---|---|---|
| DEF-W01-001 | P1 | FIXED | Quick Tour ghost control removed |
| DEF-W01-002 | P1 | FIXED | About dialog upgraded |
| Quick Tour not implemented in wx | P3 | DEFERRED | Feature scope decision needed for future Wave |

## 6. Deviations from Wave plan

None. All work stayed within W01 scope.

## 7. Rollback notes

Both changes are safe to revert:
- FIX-A: Re-add the try/except block that creates the Quick Tour menu item
- FIX-B: Revert `_dispatch("APP-ABOUT")` to use `wx.MessageBox` and delete `wx_about.py`

## 8. GO/NO-GO decision

| Field | Value |
|---|---|
| Decision | **GO** |
| Reason | Two independent substantive truth corrections completed. Full W01 inventory deliverable completed: 5 menus, 7 tabs, 19 context menus, 75 settings, 85 provider/plugin surfaces — all inventoried with support classifications. All acceptance criteria met. |
| Next Wave | W02 — Provider and Capability Contract Audit |
