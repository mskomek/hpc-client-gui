# Main Sync Protocol

Before syncing `codex/develop` to local `main`, list the candidate root paths in
this file and obtain the user's approval. List only first-level repository
paths, never recursive subdirectories.

## Eligible root paths

- `.github/`
- `build/` — packaging definitions only
- `dist/` — only a newly validated `dist/releases/v<version>/` release
- `scripts/`
- `src/`
- `templates/`
- `tests/`
- `.gitignore`, `CONTRIBUTING.md`, `LICENSE`, `MAIN_SYNC_PROTOCOL.md`, `README.md`, `SECURITY.md`,
  `SUPPORT.md`, `pyproject.toml`, `requirements.txt`, and `template.slurm`

## Always excluded

- `.agent-runs/`, `dist/`, `tools/`, `waves/`, root `docs/`, `devtools/`
- `AGENTS.md`, `CLAUDE.md`, `rules.md`, local notes, caches,
  logs, virtual environments, and non-versioned build output

## Release gate

For a release, first update the version and changelog, run the release checks,
commit the approved paths, then sync only the approved root paths to `main` and
push only `main` to `origin`.
