# Wave 70 — V2 Release Preparation (Checklist)

**Date:** 2026-09-05
**SHA:** bd40fe6 (e3408fd)
**Branch:** develop

## Checklist (per spec, strengthened)

- [x] Windows screenshots current: `audit/gui-screenshots/wx/HASHES.json` (9 files, duplicate 0, current for bd40fe6, 8414eee capture)
- [ ] Windows package validation: BLOCKED — `audit/WINDOWS_AUDIT_954783e.md` is stale (954783e), current bd40fe6 needs real artifact smoke (now `wx_packaged_smoke.py` isolated but artifact missing → FAIL)
- [ ] macOS signing/notarization validation: BLOCKED — no Apple Developer ID, no notarization/stapling/Gatekeeper, no DMG (requires macOS runner + credentials)
- [ ] Linux package validation: BLOCKED — no Linux runner, no AppImage/Flatpak build in this run (wx requires source build with gtk)
- [x] Artifact SHA256 for screenshots: `audit/gui-screenshots/wx/HASHES.json` (9 files, duplicate 0)
- [ ] Artifact SHA256 for packages: pending — no packaged artifact built for bd40fe6 (pending `pyinstaller` build per platform)
- [ ] Updater manifest integrity: pending — `scripts/capture_build_inventory.py` not yet run for packaged artifacts
- [ ] Update signature verification: pending (requires signed artifacts)
- [x] Release notes: `docs/v2/V2_MANUAL_GUI_TEST_PLAN_954783e.md` (stale) + `audit/WINDOWS_AUDIT_954783e.md` (stale) + `audit/A11Y_AUDIT.md` (keyboard PROVEN, screen reader PARTIAL)
- [x] Migration guide: `tests/test_wx_migration.py` 2/2 (V1→V2 with backup, rollback) but real app backup not proven → PARTIAL
- [x] Rollback guide: same test, backup + restore verified (manual .bak, not app's real pre-migration backup)
- [ ] Known limitations: to be consolidated from ledger (59/60 BLOCKED, signing pending, 55-57 PARTIAL)
- [x] SBOM: `audit/SBOM_68.json` (450 components, isolated venv) — updated from 100
- [x] License inventory: `audit/LICENSE_INVENTORY_68.md` + `THIRD_PARTY_NOTICES.md`
- [x] Current candidate CI: Windows local 65A 442s PASS, visual duplicate 0, Linux/macOS BLOCKED (no runner) — `audit/PROVENANCE_65B.json` (bd40fe6)
- [ ] Release candidate manual sign-off: pending — requires Windows/Linux/macOS manual sign-off per `V2_MANUAL_GUI_TEST_PLAN` for bd40fe6
- [ ] SBOM bundled binary inventory, native DLL/dylib/.so: pending Wave 70 packaging (inspect actual artifact)

## Signing Policy

- **Windows:** `UNSIGNED WITH DOCUMENTED POLICY` — Authenticode not applied in this build, policy documented in `audit/WINDOWS_AUDIT_954783e.md`. For public distribution, `SIGNED` with Authenticode verification required.
- **macOS:** `UNSIGNED WITH DOCUMENTED POLICY` — Documented as BLOCKED, public distribution would require `codesign` + `notarization` + `stapling` + Gatekeeper.

## Verdict
**Wave 70: BLOCKED** — Windows evidence done, macOS/Linux signing/packaging pending, SBOM/bundled inventory pending, manual sign-off pending. V2 release not ready; Qt remains production runtime.
