# EV-W01-001 — Pinned Repository State

**Timestamp:** 2026-09-15T21:25:00+03:00
**Agent:** opencode / mimo-v2.5

---

## Main repo: `mskomek/hpc-client-gui`

| Field | Value |
|---|---|
| Branch | `develop` |
| HEAD | `afd4fb1d6ed3d0bbd87b9b6db6115eb159f63a87` |
| origin/develop | `afd4fb1d6ed3d0bbd87b9b6db6115eb159f63a87` (in sync) |
| Working tree | Clean on tracked files; untracked: `.integration-recovery/`, `audit.zip`, `docs.zip`, `docs/TEST_SUITE_AUDIT_REPORT_12ce7993.md`, `scripts/*.py`, `tests/WAVE2_REMAINING_TEST_PROMPTS.md`, `waves.zip`, `src/hpc_gui/wx_about.py` (NEW), `artifacts/` |
| Last commit | `afd4fb1d docs: record the 2026-09-15 repository-integrity remediation` |

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
afd4fb1d6ed3d0bbd87b9b6db6115eb159f63a87

$ git log -1 --oneline --decorate
afd4fb1d (HEAD -> develop, origin/develop) docs: record the 2026-09-15 repository-integrity remediation

$ git status --short --branch
## develop...origin/develop
?? .integration-recovery/
?? audit.zip
?? docs.zip
?? docs/TEST_SUITE_AUDIT_REPORT_12ce7993.md
?? scripts/check_keys.py
?? scripts/check_line.py
?? scripts/find_mojibake.py
?? scripts/fix_missing_keys.py
?? scripts/fix_mojibake.py
?? tests/WAVE2_REMAINING_TEST_PROMPTS.md
?? waves.zip
```
