# DeepSeek worker

This directory provides the project-local OpenCode delegation wrapper shared by Codex and Claude Code. It uses only model identifiers returned by `opencode models`; it does not store or handle OpenCode credentials. The project default for every mode is the discovered OpenCode Go DeepSeek v4 Flash model. A different discovered OpenCode Go DeepSeek model requires an explicit `-Model` override.

## Git boundary

When the repository is opened from WSL, Codex/Claude create a clean clone or
worktree on local Linux storage and a temporary local branch. The OpenCode
worker runs only in its supplied separate worktree. It may inspect, edit, and
test there, but it must never stage, commit, push, reset, clean, or alter a
remote. Codex alone commits the reviewed work.

Temporary, feature, worker, and `codex/develop` branches are local-only. The
only branch ever pushed to `origin` is the final verified `main`, following
`MAIN_SYNC_PROTOCOL.md`.

Run `powershell -NoProfile -File tools/ai/deepseek-worker.ps1 -Mode dry-run` to check selection without a model call. See `docs/DEEPSEEK_DELEGATION.md` for the operating procedure and safety limits.

Wave work starts through `start-deepseek-background.ps1`. It returns a PID,
log path, atomic `completed.json` signal path, and a five-minute fallback check
time. Launch it once per proven-independent packet to run disjoint work in
parallel; phases within one packet remain sequential.

Wave calls should supply `-Wave` and `-Card` and must keep logs enabled. When the
caller (Codex or Claude) already knows which repository files a packet needs,
pass them as `-ContextFiles <path[]>` (relative to the target directory, or
absolute and inside it) for `analyze`/`implement`/`review` calls. Their content
is attached to the same one-shot message via OpenCode's `--file`, so the model
does not have to spend its own Glob/Grep/Read turns rediscovering them — the
call stays exactly as stateless as before, it just starts with more of the
right material already in front of it. Paths must resolve inside the target
directory and must not look secret-related; invalid entries fail before any
model call is made. Each
run records its request, stdout, stderr, raw child and effective worker exit
codes, response presence, timing, model, worktree, Git heads, and implement-mode
change summary under `.agent-runs/`.
Mode defaults are intentionally generous: analyze 20 minutes, implement 30,
review 20, and smoke-test 10. Every metadata file records the effective timeout
budget; callers may override it within the 1–120 minute hard boundary.
Codex records its independent packet verdict separately; the worker never marks
its own result as accepted.

The machine-readable contracts are `run-metadata.schema.json` and
`packet-verdict.schema.json`.

`wave-queue.ps1` provides the guarded local wave state machine (`recover`,
`audit`, `status`, `claim`, `verify`, `complete`, and `release`). Canonical
ignored-manifest recovery sources are under `wave-templates/`. Run
`powershell -NoProfile -File tools/ai/test-wave-queue.ps1` for the fully offline
ordering, lock, ownership, capacity, recovery, and archival test pack.
Use `docs/OPENCODE_WAVE_MASTER_PROMPT.md` verbatim to start the next wave. The
long-form packet templates are reference-only in
`docs/OPENCODE_PACKET_PROMPT_REFERENCE.md`.
