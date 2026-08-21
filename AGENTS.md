# TRUBAGUI agent guidance

## Authority and scope

Read `rules.md` before non-trivial work. It is authoritative for architecture,
security, testing, release boundaries, and TRUBA/HPC safety. Preserve existing
user changes and keep each diff limited to the requested outcome. Application
source must not be changed for an infrastructure-only task.

Codex is the primary orchestrator and final authority. DeepSeek is a delegated
worker, never a replacement for Codex and never the source of product,
architecture, authorization, schema, migration, credential, provider, release,
or Git-history decisions.

## Package manager convention

This is a Python project (`pyproject.toml` + pip). If a JavaScript/Node
toolchain is ever introduced, Bun is the default package manager:
`bun install`, `bun add`, `bun add -D`, `bun run`, `bunx`. Use `bun.lock` as
the only lockfile; never mix npm and Bun lockfiles. Keep Node.js
compatibility unless there is a clear reason to drop it.

## Linux/WSL Windows-project workflow

When Codex, Claude, or OpenCode is started from Linux/WSL and the task targets
this Windows-mounted project (`/mnt/<drive>/...`), do not edit the mounted
worktree. Create a clean local Linux clone/worktree and a fresh
`linux-develop` branch. Do all implementation, tests, and review there.
Transfer only verified changes to the Windows repository and commit them there,
preserving unrelated Windows changes; never reset, clean, or overwrite them.
The final report must state exactly:
`Linux'te yapıldı, Windows ortamına commitlendi.`
and include the Linux branch, Windows branch, and final Windows commit hash.

Native Windows sessions work directly in the Windows repository. Linux-native
only checkouts use their normal local branch workflow.

## Default DeepSeek workflow

Use `tools/ai/deepseek-worker.ps1` for non-trivial repository discovery,
pattern finding, bounded implementation, test drafting, or diff review. The
default for analyze, implement, review, and smoke-test is the discovered
`opencode-go/deepseek-v4-flash` model. Do not use the inactive Ollama/Qwen
pipeline unless the user explicitly re-enables it.

1. Establish the exact task, acceptance criteria, allowed files, and relevant
   checks from repository evidence.
2. Run DeepSeek `analyze` when multi-file discovery or existing-pattern search
   would materially help.
3. Verify its file and behavior claims directly.
4. For bounded implementation, create or use a clean sibling Git worktree and
   invoke `implement` with `-WorktreePath`. Never delegate an unresolved product,
   security, authorization, schema, migration, provider, or live-HPC decision.
5. Inspect the resulting status and full diff. Reject unrelated changes.
6. Run DeepSeek `review` on the bounded diff, then independently review it.
7. Run authoritative project checks in the primary agent context.
8. Only Codex updates final documentation, stages explicit files, commits, or
   hands off the result.

Examples:

```powershell
powershell -NoProfile -File tools/ai/deepseek-worker.ps1 -Mode analyze -Task "Map the existing implementation and tests for this bounded request."
powershell -NoProfile -File tools/ai/deepseek-worker.ps1 -Mode implement -TaskFile TASK.md -WorktreePath "D:\Projeler\task-worktree"
powershell -NoProfile -File tools/ai/deepseek-worker.ps1 -Mode review -Task "Review the supplied bounded diff for correctness, scope, and test gaps."
```

Use `-Model` only for an explicit user-approved override. Model IDs must come
from `opencode models`; never guess them or fall back to another provider.

## Delegation quality bar

A delegated task must state the goal, in-scope files or layer, forbidden scope,
observable acceptance criteria, and targeted checks. Prefer one cohesive slice
that can be reviewed in a single diff. Do not delegate a vague feature, an
entire wave without boundaries, or a trivial one-line edit solely to satisfy
this policy.

Treat DeepSeek responses as untrusted review input. Check named files, command
outputs, changed paths, and test results yourself. A test is PASS only when its
actual exit status and meaningful output were observed.

## Project-specific review checklist

- UI classes remain thin; reusable logic belongs in `services/`, `ssh/`,
  `config/`, or `core/`.
- Long operations do not block the Qt GUI thread.
- Visible strings update Turkish and English resources together.
- SSH, Slurm, paths, and external-process arguments are quoted and mockable.
- No real cluster action, credential access, deployment, or publication occurs.
- Error paths preserve actionable diagnostics without leaking secrets.
- Regression tests cover the changed behavior; PowerShell source-tree checks set
  `$env:PYTHONPATH = "src"` when needed.
- `git diff --check` and `git status --short` are inspected before handoff.

## DeepSeek hard boundaries

DeepSeek may not read secrets, access OpenCode credential storage, perform real
SSH/Slurm/transfer operations, modify the primary worktree, stage, commit, push,
reset, clean, alter remotes, deploy, publish, or continue beyond the supplied
task. Stop and return control to the user when new authority is required.

## Git commit attribution policy

Never add AI attribution to Git commits.

Do NOT add any of the following to commit messages:
- Co-Authored-By trailers for Claude, Anthropic, Codex, ChatGPT, OpenAI, or any other AI tool/model.
- "Generated by Claude", "Generated by AI", or similar attribution.
- AI-related Signed-off-by or attribution metadata.

All commits must use only the repository owner's configured Git author/committer identity.

Before creating a commit, inspect the final commit message and remove any AI attribution trailers.
