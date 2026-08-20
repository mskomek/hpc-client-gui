# Wave53 repository hygiene evidence

- Removed path: `dist/releases/v1.2.4/**`
- Tracked files removed: 284
- Approximate working-tree reduction: 242 MB
- Kept: `build/` packaging definitions, release scripts, legal notices, and
  source documentation.
- Added release-surface protection: tracked `dist/releases` paths now fail the
  checker with the offending count and remediation.
- Verified: release-surface check, i18n check, wiki check, and Windows release
  surface tests.

This is a current-tree cleanup only. Git history was not rewritten and GitHub
release tags/assets were not modified.
