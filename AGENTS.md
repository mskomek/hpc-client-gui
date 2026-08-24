# Agent guidance

`rules.md` — maintained by the repository owner on the internal development
line — is the single authoritative source for architecture, security,
testing, release boundaries, and cluster-safety rules. It is intentionally
not part of this public repository; never duplicate its content into other
tracked files.

Tracked, user-facing documentation lives in `README.md`, `CONTRIBUTING.md`,
`SECURITY.md`, `SUPPORT.md`, and `docs/`. Keep those files consistent with
each other instead of restating rules in multiple places.

## Workflow

- Never commit directly to `main`; open a pull request from a short-lived
  feature branch.
- Delete feature branches (local and remote) immediately after merge.
- Required status checks must pass before merging; see `.github/workflows/`.
- Preserve unrelated work in progress when preparing changes.
