# Main Sync Protocol

## Branch and push boundary

WSL work must happen in a clean clone or worktree on local Linux storage, on a
temporary local branch. Codex reviews and commits the result, then fast-forwards
local `codex/develop`. OpenCode/DeepSeek/Claude worker worktrees never stage,
commit, push, reset, clean, or alter remotes.

Temporary, feature, worker, and `codex/develop` branches are never pushed to
`origin`. Only the final verified `main` branch may be pushed, and only after
the candidate-path approval below and the relevant validation gates pass.

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
- `AGENTS.md`, `CLAUDE.md`, and `tools/ai/README.md` — repository workflow and
  delegated-worker safety instructions
- `QT_LGPL_SOURCE_OFFER.md`, `THIRD_PARTY_NOTICES.md`, and
  `requirements-release.lock` — release licensing and dependency metadata

## Always excluded

- `.agent-runs/`, `dist/`, `tools/` except `tools/ai/README.md`, `waves/`, root
  `docs/`, `devtools/`
- `rules.md`, local notes, caches,
  logs, virtual environments, and non-versioned build output

## Release gate

For a release, first update the version and changelog, run the release checks,
commit the approved paths, then sync only the approved root paths to `main` and
push only `main` to `origin`. Never use `git push --all`, `git push --mirror`,
or a branch wildcard.
