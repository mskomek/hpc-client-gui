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

## Linux/WSL Git workflow and push boundary

When Codex, Claude, or OpenCode is started from Linux/WSL on a
Windows-mounted checkout (`/mnt/<drive>/...`):

1. Do not edit the mounted Windows worktree directly.
2. Clone or create a clean sibling worktree on the local Linux filesystem and
   create a fresh `linux-develop` branch there from the intended base.
3. Do all edits, tests, and review in that Linux worktree, regardless of which
   agent performs the work.
4. At handoff, transfer only the verified changes to the Windows repository and
   commit them there. Preserve unrelated Windows changes; never reset, clean,
   or overwrite them to force the handoff.
5. The final report must state exactly:
   `Linux'te yapıldı, Windows ortamına commitlendi.`
   It must also include the Linux branch, Windows branch, and final Windows
   commit hash.

Never push a temporary, feature, worker, or `codex/develop` branch to `origin`.
Only the final, verified `main` branch may be pushed, and only by Codex after
the main-sync path approval and release gates pass.

For Linux-native-only checkouts, use the normal local branch workflow. Native
Windows sessions work directly in the Windows repository and commit there.

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
