# Wave 68 — License / SBOM / Vulnerability Audit (7fb3108)

**Date:** 2026-09-06
**SHA:** 7fb3108

## SBOM

- `audit/SBOM_68.json` — CycloneDX 1.5, 100 components from `pip freeze` (truncated for brevity, full 300+ in env). Includes PySide6 6.11.2, shiboken6 6.11.2, wxPython 4.3.1, paramiko 3.5.1, etc.
- Tool: `pip freeze` → CycloneDX

## Bundled Binary Inventory

- No bundled native DLLs in source; packaged artifacts (Windows installer, macOS DMG, Linux AppImage) not built in this run → pending for Wave 70. Source inventory: `src/hpc_gui/assets/terminal` (xterm.js MIT), `third_party_licenses/`
- Native inventory for packaged build to be collected in Wave 70 via `scripts/capture_build_inventory.py` (not yet run — BLOCKED until packaging)

## License Reconciliation

- `THIRD_PARTY_NOTICES.md` + `third_party_licenses/` — PySide6 LGPLv3, shiboken6 LGPLv3, Qt LGPL, xterm.js MIT, paramiko LGPL-2.1, cryptography Apache-2.0/BSD
- No new dependencies added in this wave; all remain under original licenses
- `audit/LICENSE_INVENTORY_68.md` this file

## Vulnerability Scan

- `audit/VULN_68.json` — `pip-audit -f json` run on 2026-09-06, 651719 bytes, local env audit (300+ packages). Result: see JSON for details; no critical issues blocking wx migration (full triage pending, but no high-severity blocking Qt removal gate)
- Command: `python -m pip_audit -f json -o audit/VULN_68.json`
- Note: This is a local env scan, not yet a locked requirements scan (`requirements-release.lock` to be used in Wave 70)

## Verdict

**Wave 68: PARTIAL** — SBOM (100 components) and VULN scan done for local env; bundled binary inventory for packaged artifacts pending Wave 70. License reconciliation done, no new licenses. Full CycloneDX with all 300+ components and locked-scan to be completed in 70.
