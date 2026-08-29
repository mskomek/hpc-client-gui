# WAVE 04 — controlled v1.5.1 publication

## Goal

Publish the optimized v1.5.1 only after the packaging evidence and all
required CI checks are green.

## Preconditions

- WAVE 01–03 acceptance criteria are complete.
- The exact source commit is on `main` through the protected PR flow.
- No unreviewed release or tag already exists for `v1.5.1`.
- macOS mode is explicitly chosen. Default to unsigned only when signing
  credentials are unavailable, and preserve the warning in the notes.

## Procedure

1. Dispatch `.github/workflows/release.yml` from the exact `main` commit.
2. Set `version=1.5.1`, `publish=true`, and the explicitly approved
   `macos_mode`.
3. Wait for Linux, Windows, arm64 macOS, x86_64 macOS, verification, final
   gate, provenance, and publication jobs to finish.
4. Verify the GitHub Release has all expected assets and the generated notes.
5. Check the release tag points to the intended `main` commit.
6. Verify the release page does not contain a stale empty asset list or generic
   auto-generated-only notes.

## Forbidden

- Do not publish while any required job is red, cancelled, or unexpectedly
  skipped.
- Do not bypass branch protection.
- Do not force-update a published tag.
- Do not silently replace a failed release; stop and obtain explicit approval
  before deleting a remote release/tag.

## Acceptance criteria

- v1.5.1 is published once, from the intended main commit.
- Release assets include Windows, Linux, both macOS architectures, checksums,
  manifest, security metadata, and release notes.
- The release page clearly states unsigned/signed macOS status.
- The published changelog is the canonical v1.5.1 section and lists the
  user-visible changes in readable language.
- Final report includes workflow URL, artifact sizes, hashes, and any skipped
  platform validation.
