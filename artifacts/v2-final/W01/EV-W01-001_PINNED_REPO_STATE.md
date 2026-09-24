# EV-W01-001 — Pinned Repository State

**Timestamp:** 2026-09-21T00:00:00+03:00
**Agent:** opencode / mimo-v2.5

---

## Main repo: `mskomek/hpc-client-gui`

| Field | Value |
|---|---|
| Branch | `develop` |
| HEAD | `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb` |
| origin/develop | Not queried in this refresh |
| Working tree | Nine tracked W01 evidence/report files modified by this identity refresh (44 insertions, 46 deletions); one unrelated untracked path: `new 4.ps1` |
| Last commit | `63b696b3 wave orchestration baseline` |

## Plugin repo: `mskomek/hpc-client-gui-plugins`

| Field | Value |
|---|---|
| Status | Not fetched (no plugin changes in this session) |
| Baseline SHA (from V2_BASELINE.md) | `4e79325873a3eda232071339b367722ccacbb8f8` |

## Verification commands

```bash
$ git branch --show-current
develop

$ git rev-parse HEAD
63b696b3b8c64296d9d17f94c8d0d903f9bab7eb

$ git log -1 --oneline --decorate
63b696b3 (HEAD -> develop) wave orchestration baseline

$ git status --short --branch
## develop
 M artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md
 M artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md
 M artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md
 M artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md
 M artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md
 M artifacts/v2-final/W01/SUPPORT_MATRIX.md
 M artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md
 M docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md
?? new 4.ps1
```
