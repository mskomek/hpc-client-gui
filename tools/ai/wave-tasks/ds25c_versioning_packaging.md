# DS-25C — Versioned packaging and release notes (Wave 25)

DS-25B already replaced LICENSE with PolyForm Noncommercial 1.0.0, added
COMMERCIAL_LICENSE.md and THIRD_PARTY_NOTICES.md, updated README's Licensing
section, added license/authors metadata to both pyproject.toml files, updated
build/windows/version_info.txt copyright, added license files to both
PyInstaller .spec datas, and updated scripts/release.ps1 to stage them. Do
not redo that work; build on top of it.

## Task

1. Bump every authoritative version reference from 1.1.21 to 1.2.0
   consistently: both `pyproject.toml` files' `version` field,
   `src/truba_gui/__init__.py` `__version__`, `src/truba_gui/cli/main.py`
   `CLI_VERSION`, `build/windows/version_info.txt` FileVersion/ProductVersion
   fields, and any other authoritative version constant found by grepping for
   `1.1.21` in source (not historical changelog entries, which stay as-is).
   Update `scripts/test_release_consistency.ps1` wherever it pins `1.1.21` to
   `1.2.0`.

2. Add a new `## v1.2.0` section at the top of the authoritative changelog
   `src/truba_gui/docs/CHANGELOG.md` (above the existing `## Unreleased` or
   `## v1.1.21` entry, whichever is topmost) with a clearly visible
   "### Licensing Change" subsection stating: starting with v1.2.0 the
   project moves from MIT to the PolyForm Noncommercial License 1.0.0 with a
   separate commercial license path (link `COMMERCIAL_LICENSE.md`); prior
   releases remain MIT-licensed and that MIT grant is not revoked. Do not
   touch the stale `src/truba_gui/CHANGELOG.md` (separate, already known to
   be stale and out of scope).

3. Untrack the accidentally committed build artifact directory
   `dist/hpc-client-cli/` from Git: run `git rm -r --cached dist/hpc-client-cli`
   (removes it from the index only, keeps the files on disk) and add
   `/dist/hpc-client-cli/` to `.gitignore` next to the existing
   `/dist/hpc-client-gui/` and `/dist/releases/` entries. Do not delete the
   files from disk and do not touch any other tracked path under `dist/`.

## Allowed files

`pyproject.toml`, `src/truba_gui/pyproject.toml`, `src/truba_gui/__init__.py`,
`src/truba_gui/cli/main.py`, `build/windows/version_info.txt`,
`scripts/test_release_consistency.ps1`, `src/truba_gui/docs/CHANGELOG.md`,
`.gitignore`, and the Git index removal of `dist/hpc-client-cli/` (tracked
files only, no working-tree deletion).

Forbidden: publishing a release, deleting any Git tag/branch/history,
deleting release assets, changing application functionality, editing
`src/truba_gui/CHANGELOG.md` (the stale one), and any commit/push/GitHub
action — leave changes unstaged/uncommitted for review.
