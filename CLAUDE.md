# TRUBAGUI Claude Code guidance

## Linux/WSL Git workflow and push boundary

When running in WSL from a Windows-mounted checkout (`/mnt/<drive>/...`), use
an ordinary clone or clean Git worktree on the local Linux filesystem and make
a temporary local branch for the task. Work and test there. Codex remains the
only agent that stages and commits the reviewed result; OpenCode/DeepSeek may
only work in their supplied separate worktree and must never stage, commit,
push, reset, clean, or alter remotes.

After review, Codex fast-forwards local `codex/develop`, then follows
`MAIN_SYNC_PROTOCOL.md` to sync approved paths into local `main`.
Never push a temporary, feature, worker, or `codex/develop` branch. Only the
final verified `main` branch may be pushed to `origin`.

Read `rules.md` first. Project architecture, safety, testing, and release rules
remain authoritative. Preserve pre-existing changes and keep work narrowly
scoped.

Claude is the primary orchestrator and final authority. Use the same shared
worker as Codex for non-trivial repository analysis, bounded implementation,
and review:

```powershell
powershell -NoProfile -File tools/ai/deepseek-worker.ps1 -Mode analyze -Task "..."
powershell -NoProfile -File tools/ai/deepseek-worker.ps1 -Mode implement -TaskFile TASK.md -WorktreePath "D:\Projeler\task-worktree"
powershell -NoProfile -File tools/ai/deepseek-worker.ps1 -Mode review -Task "..."
```

The default delegated model for every mode is the discovered OpenCode Go
DeepSeek v4 Flash model. Do not use the project-local Ollama/Qwen runner unless
the user explicitly re-enables it. Do not invent Claude hooks, proxy Claude's
native model, or treat DeepSeek output as authoritative.

## Required workflow

1. Define the bounded outcome, allowed files, acceptance criteria, and tests.
2. Use DeepSeek analysis when repository mapping or pattern discovery helps.
3. Verify every material claim against repository files.
4. Delegate implementation only in a clean, separate Git worktree and only when
   no product, security, authorization, schema, migration, provider, or live-HPC
   decision remains open.
5. Inspect the full diff, run DeepSeek review, and independently review it.
6. Run authoritative checks yourself. For source-tree Python checks on
   PowerShell, set `$env:PYTHONPATH = "src"` when required.
7. Claude owns final architecture, security judgment, documentation accuracy,
   staging, commit, and handoff.

## Orchestration mechanics

See `rules.md`'s "Orchestration mechanics" section (under "AI Collaboration
Rule") for the authoritative, shared policy — it applies to Claude the same
as Codex. In short: drive `deepseek-worker.ps1`/wave calls as direct
background OS processes, never inside a nested Agent/subagent call; verify
everything yourself; use `tools/ai/parse-run-log.js` to read only the
decision-relevant lines from a run's log instead of the raw output.

## Quality and safety

- Keep Qt UI thin and move reusable behavior to the established service layers.
- Keep long SSH, transfer, and process work off the GUI thread.
- Update Turkish and English resources together for visible strings.
- Quote and mock SSH/Slurm/process arguments; never invent cluster settings.
- Never expose secrets or ask DeepSeek to read `.env`, SSH keys, credentials,
  tokens, passwords, or OpenCode authentication state.
- DeepSeek may not perform real TRUBA/HPC operations, edit the primary worktree,
  stage, commit, push, reset, clean, deploy, or publish.
- A PASS requires observed command output, exit status, and an independently
  inspected diff.
