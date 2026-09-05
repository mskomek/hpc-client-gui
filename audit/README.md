# GUI audit evidence — Current HEAD: bd40fe6 (develop)

This directory contains reproducible validation notes for the Qt reference
screens and the current wx migration screens. The screenshots use disposable
mock data; they are not packaged or real-cluster evidence.

## Current authoritative files (HEAD bd40fe6)

- **Visual parity:** `audit/GUI_VISUAL_PARITY_REPORT.md` + `.json` — regenerated 2026-09-05 18:46 UTC for 8414eee (still current for bd40fe6, same screenshots, duplicate 0), `HASHES.json` SHA256. Previous `delegate9b` report is historical.
- **Screenshots:** `audit/gui-screenshots/qt/` (7 Qt reference) + `audit/gui-screenshots/wx/` (9 wx candidate at 1100x720) + `HASHES.json` (a38c, 5ff3, 1afd, 7675, 69e8, bf60, 06db, c13b, f6e4)
- **Windows audit:** `audit/WINDOWS_AUDIT_954783e.md` — historical (SHA 954783e, duplicate 0, 58 passed). Current HEAD bd40fe6 audit pending (screenshots regenerated but full audit doc not yet rerun, smoke is FAIL due to missing artifact).
- **Provenance:** `audit/PROVENANCE_65B.json` — regenerated 2026-09-05 for bd40fe6, 68 passed, 442s 65A PASS, screenshots current, artifact pending
- **Evidence integrity:** `audit/PARITY_EVIDENCE_INTEGRITY_62A.md` — needs regen after ledger downgrades (55-57,65A now VERIFIED)
- **SBOM:** `audit/SBOM_68.json` (450 components, isolated venv) + `VULN_68.json` + `LICENSE_INVENTORY_68.md`
- **Performance:** `audit/PERFORMANCE_SOAK_69.md` — short soak 442s 65A + file003, long soak pending
- **Release prep:** `audit/RELEASE_PREP_70.md` — BLOCKED pending packaging/DPI, updated for bd40fe6
- **Accessibility:** `audit/A11Y_AUDIT.md` — keyboard PROVEN, screen reader PARTIAL

## Historical / stale

- `audit/GUI_VISUAL_PARITY_REPORT.*` previous delegate branch (archived via overwrite, ledger §4 records history)
- `audit/WINDOWS_AUDIT_954783e.md` per-SHA, not current until eb37/8414 regenerated
- `audit/PROVENANCE_65B.json` points to 954783e not current
- `audit/test-results.md` old run
- `audit/screenshots/{qt,wx}/` legacy sets replaced by `audit/gui-screenshots/`

## Conventions

- English guide: [`docs/wiki/GUI-Feature-Guide.md`](../docs/wiki/GUI-Feature-Guide.md)
- Turkish guide: [`docs/wiki/GUI-Feature-Guide-TR.md`](../docs/wiki/GUI-Feature-Guide-TR.md)
- Mock cluster tests use loopback-only, disposable SSH/SFTP/Slurm data. No credentials, real cluster, or `.tmp/` content is used.
- Do not mix obsolete pre-fix status without clear boundaries; first table in `docs/v2/WX_MIGRATION_WAVE_STATUS.md` is CURRENT HEAD only.
