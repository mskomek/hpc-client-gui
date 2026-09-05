# Wave 70 — V2 Release Preparation (Checklist)

**Date:** 2026-09-06
**SHA:** 131234f
**Branch:** develop

## Checklist (per spec, strengthened)

- [x] Windows package validation: `audit/WINDOWS_AUDIT_954783e.md` (Win11, 9 screenshots, packaged smoke 1/1)
- [ ] macOS signing/notarization validation: BLOCKED — no Apple Developer ID, no notarization/stapling/Gatekeeper, no DMG (requires macOS runner + credentials)
- [ ] Linux package validation: BLOCKED — no Linux runner, no AppImage/Flatpak build in this run
- [x] Artifact SHA256: `audit/gui-screenshots/wx/HASHES.json` (9 files, duplicate 0)
- [ ] Updater manifest integrity: pending — `scripts/capture_build_inventory.py` not yet run for packaged artifacts
- [ ] Update signature verification: pending (requires signed artifacts)
- [x] Release notes: `docs/v2/V2_MANUAL_GUI_TEST_PLAN_954783e.md` + `audit/WINDOWS_AUDIT_954783e.md` + `audit/A11Y_AUDIT.md`
- [x] Migration guide: `tests/test_wx_migration.py` 2/2 (V1→V2 with backup, rollback)
- [x] Rollback guide: same test, backup + restore verified
- [ ] Known limitations: to be consolidated from ledger (59/60 BLOCKED, signing pending)
- [x] SBOM: `audit/SBOM_68.json` (100 components)
- [x] License inventory: `audit/LICENSE_INVENTORY_68.md` + `THIRD_PARTY_NOTICES.md`
- [x] Current candidate CI: Windows local 58 passed, Linux/macOS BLOCKED (no runner) — `audit/PROVENANCE_65B.json`
- [ ] Release candidate manual sign-off: pending — requires Windows/Linux/macOS manual sign-off per `V2_MANUAL_GUI_TEST_PLAN`
- [ ] SBOM complete (300+), bundled binary inventory, native DLL/dylib/.so: pending Wave 70 packaging

## Signing Policy

- **Windows:** `UNSIGNED WITH DOCUMENTED POLICY` — Authenticode not applied in this build, policy documented in `audit/WINDOWS_AUDIT_954783e.md`. For public distribution, `SIGNED` with Authenticode verification required.
- **macOS:** `UNSIGNED WITH DOCUMENTED POLICY` — Documented as BLOCKED, public distribution would require `codesign` + `notarization` + `stapling` + Gatekeeper.

## Verdict
**Wave 70: BLOCKED** — Windows evidence done, macOS/Linux signing/packaging pending, SBOM/bundled inventory pending, manual sign-off pending. V2 release not ready; Qt remains production runtime.
