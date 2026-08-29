# WAVE 03 — release packaging verification and artifact inventory

## Goal

Prove that the optimized package is complete, reproducible, and safe to
publish before a GitHub Release is created.

## In scope

- `scripts/release_macos.py`
- `scripts/report_bundle_sizes.py`
- `scripts/generate_release_manifest.py`
- `scripts/generate_release_security.py`
- `.github/workflows/release.yml`
- focused tests for release inventory and macOS packaging

## Procedure

1. Run the release workflow with:
   - version set to the exact source version;
   - `publish=false` for the first verification run;
   - `macos_mode=unsigned` when signing credentials are unavailable.
2. Confirm the final release gate rejects any failed, cancelled, or skipped
   required build job.
3. Download every candidate artifact and validate:
   - Windows GUI/CLI archive and checksums;
   - Linux AppImage, `.deb`, Flatpak, and checksums;
   - macOS arm64 and x86_64 DMGs and checksums;
   - `MANIFEST.json`, `RELEASE_SECURITY.json`, `RELEASE_NOTES.md`, and bundle
     size reports.
4. Recompute SHA-256 hashes independently.
5. Inspect manifest platform labels, sizes, and architecture names.
6. Verify unsigned notes explicitly warn about Gatekeeper and do not claim
   Developer ID signing, notarization, stapling, or Gatekeeper success.
7. Confirm the source changelog section is copied into release notes with:
   - release summary;
   - user-visible changes;
   - packaging and compatibility notes;
   - known limitations;
   - artifact table;
   - verification instructions.

## Forbidden

- Do not publish a candidate with missing platform artifacts.
- Do not manually upload a locally built macOS binary in place of CI output.
- Do not overwrite a release whose artifacts do not match the manifest.
- Do not mark an unsigned build as signed.
- Do not bypass branch protection or required checks.

## Acceptance criteria

- Dry-run release gate passes with all required jobs successful.
- All artifact names, hashes, sizes, and platforms agree across files.
- Both macOS DMGs remain below the enforced budget.
- Release notes are generated from the canonical changelog, not GitHub’s
  generic PR summary.
- A reviewer can reproduce the verification from the workflow URL and listed
  commands.
