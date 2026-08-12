# DS-25B — License and documentation transition (Wave 25)

Confirmed decisions (user-approved, do not re-litigate):
- Copyright holder for all new/updated copyright metadata: `Mehmed Sinan KÖMEK`.
- Standard LGPL-2.1+/LGPLv3 compliance via included license text + notices is
  sufficient (no custom legal wording needed) for paramiko and PySide6.

## Task

Replace the project license for v1.2.0 onward with the unmodified, publicly
documented PolyForm Noncommercial License 1.0.0 text in `LICENSE`. Add
`COMMERCIAL_LICENSE.md` describing that commercial embedding, incorporation,
OEM/bundling, redistribution as a commercial product, or proprietary
commercial derivatives require a separate commercial license from the
copyright holder — do not invent prices, contractual terms, or affiliation
with TRUBA, TÜBİTAK, ANSYS, or any other organization; state that interested
parties should contact the copyright holder for terms.

Update `README.md`'s license/contributions section to a plain-language
"Licensing" section: free personal/academic/educational/public-research/
other permitted non-commercial use stays easy under PolyForm Noncommercial
1.0.0; commercial use requires a separate license (link `COMMERCIAL_LICENSE.md`);
state the historical boundary exactly — releases before v1.2.0 were MIT and
that MIT grant is not revoked for those already-distributed copies; keep the
existing "not an official TRUBA product" independent-project statement.

Add `license`/`authors` metadata (holder `Mehmed Sinan KÖMEK`) to both
`pyproject.toml` (root and `src/truba_gui/pyproject.toml`) referencing
PolyForm Noncommercial 1.0.0 — do not bump version numbers here (that is
DS-25C). Update `build/windows/version_info.txt` `LegalCopyright` to
`Copyright (c) 2026 Mehmed Sinan KÖMEK`.

Add a new `THIRD_PARTY_NOTICES.md` at repo root listing each bundled runtime
dependency (PySide6/shiboken6 — LGPLv3, paramiko — LGPL-2.1+, cryptography —
Apache-2.0/BSD) with its license name and a note that full license text ships
alongside the packaged application. Do not remove the existing
`cryptography-46.0.5.dist-info` bundling.

Add `LICENSE`, `COMMERCIAL_LICENSE.md`, and `THIRD_PARTY_NOTICES.md` to the
`datas` list in `build/windows/hpc-client-gui.spec` and
`build/windows/hpc-client-cli.spec` so they land in the packaged
`_internal` output. Update `scripts/release.ps1` to copy these three files
into `dist/releases/v<version>/` alongside the existing help-docs staging
step, so both the GUI and CLI release zips (and the legacy migration zip)
include them.

## Explicitly out of scope for this packet

- Version bump to 1.2.0 anywhere (DS-25C).
- Changelog "Licensing Change" section (DS-25C).
- `dist/hpc-client-cli/` git-tracking cleanup (DS-25C).
- Source header changes (none exist repo-wide; do not add any).
- Any release, tag, commit, push, or GitHub action.

## Allowed files

`LICENSE`, `COMMERCIAL_LICENSE.md` (new), `THIRD_PARTY_NOTICES.md` (new),
`README.md`, `pyproject.toml`, `src/truba_gui/pyproject.toml`,
`build/windows/version_info.txt`, `build/windows/hpc-client-gui.spec`,
`build/windows/hpc-client-cli.spec`, `scripts/release.ps1`.

Forbidden: application behavior changes, dependency-license changes, Git
history rewrites, release/tag/asset operations, version-number changes,
custom license wording beyond the established PolyForm Noncommercial text.
