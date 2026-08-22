# rules.md

Last updated: 2026-08-08

## Mission

This repository exists to make real **TRUBA / Slurm / SSH** workflows easier to execute from a desktop GUI without hiding what the system is doing.

The application must remain useful for:
- connection setup
- remote file browsing and editing
- Slurm script preparation
- job submission
- queue / accounting inspection
- diagnostics and troubleshooting
- optional X11 launch workflows

## Architecture Rules

### UI must stay thin
- widgets and dialogs should focus on interaction and display
- heavy logic should move into `services/`, `ssh/`, `config/`, or `core/`
- Slurm command composition or parsing should not be buried in UI classes when it can be reused elsewhere

### Services should stay explicit
- remote file operations belong in file services
- Slurm operations belong in Slurm services
- external process helpers belong in dedicated service modules
- parsing logic should be reusable and testable

### External tools must stay visible
The application may rely on external tools such as:
- `plink.exe`
- `VcXsrv`
- SSH subsystem tools

When those tools are used:
- commands should be understandable
- stderr should not be silently swallowed
- logs should help explain what failed

## Responsiveness Rule

Long-running operations must not freeze the GUI.

Examples:
- SSH connect
- remote directory load
- file upload/download
- `sbatch`, `squeue`, `sacct`
- X11 helper startup
- packaging helpers if surfaced through the app

## Logging and Diagnostics

- Silent failure is unacceptable.
- Logs should help reconstruct user-visible failures.
- Error dialogs should contain actionable clues when possible.
- Startup and shutdown paths should remain defensive.

## Security and Secrets

- never commit credentials, private keys, tokens, or real secrets
- never hardcode TRUBA host credentials
- local persistence changes must remain reviewable
- commands can be logged, but secrets must not leak into logs

## i18n Rule

Visible UI strings should use the language resource system.
If a task adds new visible strings, update both language files consistently unless the task explicitly limits scope.

## Testing Rule

Every task must define checks.
Common checks for this repo include:
- `$env:PYTHONPATH = "src"` before source-tree Python checks on PowerShell
- `python -m unittest tests/test_editor_flow.py`
- `python scripts/check_i18n.py`
- `python scripts/smoke_test.py`
- import / syntax checks
- narrow manual reasoning for Windows-only flows when platform execution is unavailable

Do not claim success without recording what was checked.

- Every bug fix must include a narrow regression test when the behavior can be
  exercised automatically.
- Tests must assert the observable behavior at the relevant boundary, not only
  that an internal dependency was called.
- Parsers for Slurm or other external tools should use anonymized real output
  fixtures when practical; prefer machine-readable external formats first.
- CI must run the relevant automated checks for changes to `main`; CI workflow
  edits require the same review and validation as product code.

## Reliability and Persistence

- SSH, transfer, Slurm, and other network operations must use explicit
  timeouts and leave an actionable error on timeout.
- Long-running operations must honour cancellation and release temporary files,
  sockets, and processes on success, failure, or cancellation.
- Local configuration, downloads, exports, and generated output must write to
  a temporary path and atomically replace the final path only after success.
- Persisted configuration changes must preserve backward compatibility or use
  a deliberate, testable migration; never silently discard user settings.

## AI Collaboration Rule

### Linux/WSL to Windows repository handoff

This rule applies equally to Codex, Claude, and OpenCode. When a Linux/WSL
session works on a file in this Windows-mounted repository, do not edit the
mounted worktree. Create a clean local Linux clone/worktree and a fresh
`linux-develop` branch; perform all edits, tests, and review there. Once
verified, transfer only those changes to the Windows repository and commit
them there, preserving unrelated Windows changes and never using reset, clean,
or overwrite to force the handoff.

The final report must state exactly `Linux'te yapıldı, Windows ortamına
commitlendi.` and include the Linux branch, Windows branch, and final Windows
commit hash. Native Windows sessions work directly in the Windows repository;
Linux-native-only checkouts use the normal local branch workflow.

`rules.md` defines product and architecture constraints. `AGENTS.md` defines the
Codex workflow, and `CLAUDE.md` defines the Claude Code workflow. When they
overlap, the stricter safety or validation rule applies; no agent instruction
may weaken this file.

Codex and Claude remain the primary orchestrators. For non-trivial discovery,
implementation, and review they should invoke the shared project worker:

`powershell -NoProfile -File tools/ai/deepseek-worker.ps1`

The default delegated model is the OpenCode Go DeepSeek v4 Flash identifier
returned by `opencode models`. Never route DeepSeek through an undocumented
Codex/Claude proxy. Project-local Ollama/Qwen agents are inactive until the user
explicitly re-enables them.

Delegated work must be narrow and reviewable:

- analyze and review are read-only
- implementation requires a clean, separate Git worktree
- DeepSeek never stages, commits, pushes, deploys, or chooses product policy
- the primary agent verifies repository claims and reruns authoritative tests
- real SSH, TRUBA, Slurm, transfer, credential, and production operations remain
  prohibited without explicit user authorization
- no agent may read `.env`, SSH keys, credential stores, tokens, passwords, or
  OpenCode authentication state

DeepSeek is preferred for repository mapping, pattern search, repetitive UI or
serialization work, test drafting, parsing, bounded bug fixes, documentation
drafts, and diff review. The primary agent retains architecture, security,
authorization, schema, migration, release, Git, and final handoff authority.

Use OpenCode through `tools/ai/deepseek-worker.ps1` as much as safely and
practically possible. Default to delegating drafting work to DeepSeek even
when a packet is small
enough that the primary agent could write it directly in fewer total tokens.
The goal is minimizing the primary agent's own usage specifically, not total
system usage, so a DeepSeek round-trip is preferred over self-authoring
unless the task is a genuinely tiny edit (a few lines) or requires a judgment
call DeepSeek cannot make.

For every delegated implementation, the primary agent must record the bounded
task, approved files, selected model, worktree path, tests run, exact outcomes,
and remaining uncertainty. DeepSeek output is evidence to inspect, not proof.

### Orchestration mechanics — no nested subagents for DeepSeek delegation

Delegating to DeepSeek exists to keep the primary agent's own token/context
usage low. Wrapping `deepseek-worker.ps1`/wave calls in a nested subagent (an
Agent/Task-tool call, a second Codex/Claude session, etc.) defeats that
purpose: spawning a subagent itself spends the primary agent's tokens on
orchestration. Both Codex and Claude must drive delegation directly instead:

1. Do not wrap `deepseek-worker.ps1` or wave-queue calls in a nested subagent.
   Launch them directly as a background OS process (PowerShell `Start-Job`/
   background invocation, or the host tool's own background-process support)
   so the actual DeepSeek work happens in a separate process and never enters
   the primary agent's context.
2. Redirect each background call's output to a log file
   (`> path/to/run.log 2>&1`).
3. When a call finishes, do not read the raw log into context. Extract only
   the decision-relevant lines (progress narration, the final report,
   verdicts, exit codes) — `tools/ai/parse-run-log.js <log-file> [--tail N]`
   does this filtering; use it (or an equivalent one-off filter) rather than
   dumping the full log.
4. The primary agent performs verification directly — never delegate
   verification to a subagent. Inspect `git status`/`git diff` yourself,
   check claims against the actual source, and rerun real build/test commands
   yourself when needed. A model's self-report is evidence, never proof.
5. For implementation packets, use a clean sibling Git worktree, verify the
   work there, integrate with a fast-forward-only merge once independently
   verified, then clean up the worktree.
6. When starting a background delegation call in an interactive session, tell
   the user the exact log file path so they can tail it themselves, and
   **always** (never optional, never skipped even for a "quick" call) open a
   live, self-closing tracking window for it in the same step as launching
   the call, not as an afterthought: launch
   `tools/ai/tail-and-close.ps1 -LogFile <log> -MatchCommandLine <unique
   substring of the launched command line, e.g. the task-file path>` via
   `Start-Process powershell -ArgumentList '-NoProfile','-File',
   'tools/ai/tail-and-close.ps1','-LogFile','<log>','-MatchCommandLine',
   '<match>' -WindowStyle Minimized`. It finds the running process, streams
   new log content as it appears, and closes itself a few seconds after that
   process exits. The background runner must also deliver a completion signal
   to the primary interactive session; when that signal arrives and the tail
   window closes, the primary agent resumes from the completed OpenCode result.
   Do not require the user to send a follow-up message. Always pass
   `-WindowStyle Minimized` so the tracking window does not steal focus.
7. Guard against a silent API/connection drop between the primary agent and
   the launched process — do not just fire the background call and assume it
   is running, and do not wait passively for a completion notification.
   **Fixed procedure, every single delegation call:**
   - `deepseek-worker.ps1` writes an immediate start marker to the log within
     ~1–2 seconds of launch (`Selected DeepSeek model: ...`,
     `Timeout budget: ...`, `Run log directory: ...`, all via `Write-Host`,
     captured into the redirected log file). **5 minutes after launch**,
     check the log for that marker. If it is missing, the launch itself is
     failed/hung (this marker needs no network I/O and should be
     near-instant) — stop that process and relaunch once.
   - Until the first worker output appears after the start marker, actively
     poll the log and process state rather than assuming the request is
     running. Confirm that the worker process is alive and that output has
     begun before moving to periodic monitoring; otherwise stop and relaunch
     once.
   - If the marker is present (launch succeeded), **check status again every
     5–15 minutes** for as long as the call is in flight (use 5 minutes when
     output is active or failure risk is elevated, otherwise up to 15):
     confirm the launched process/job is still alive, and check whether the OpenCode CLI
     itself reports an error state (process exited, or its own status/log
     shows a queue or connection error) rather than assuming silence means
     it is still working. OpenCode/DeepSeek calls can fail mid-run, not just
     at launch (API queue errors, dropped connections) — a stalled log does
     not by itself mean the model is still thinking.
   - If the process has exited or the CLI reports an error at any of these
     5-minute checks, treat the call as failed and relaunch. If it is still
     alive with no new log output, that is consistent with genuine slow
     thinking; only escalate to stop-and-retry if a single call stalls past
     15–20 minutes total without any further log progress.
8. If packet dependencies look circular or contradictory, do not resolve that
   ambiguity alone — summarize the exact conflict to the user with a concrete
   set of options and let them decide.

`-ContextFiles <path[]>` on `deepseek-worker.ps1` (attach known-relevant files
directly to a one-shot call so DeepSeek skips its own Glob/Grep/Read
discovery) and `Assert-SafeTask`'s word-boundary-based safety filter (never
weaken it; word-fused identifiers like `SSHSlurmBackend` pass, bare/punctuated
occurrences of a blocked word do not — verify task-file text against its
regexes with a literal-string search tool, not a live PowerShell regex test
against previously-rejected content, before invoking) apply the same way
regardless of which agent drives the call.

## TRUBAGUI Change Quality

- Preserve the `src/hpc_gui` layer boundaries: UI interaction in `ui/`, remote
  behavior in `ssh/`, reusable operations in `services/`, and persistence in
  `config/` or `core/`.
- Keep SSH/Slurm command construction explicit, quoted, mockable, and covered by
  narrow tests. Never invent partitions, accounts, constraints, remote paths, or
  resource limits.
- New GUI-visible text must update both `i18n/tr.json` and `i18n/en.json`.
- Long-running SSH, transfer, parsing, or process work must stay off the GUI
  thread and preserve cancellation/shutdown behavior.
- Prefer existing services and widgets over parallel implementations. Avoid
  broad refactors unless the task explicitly requires them.
- A completed change includes error handling, relevant regression tests, and a
  concise user-visible behavior summary when behavior changed.

## Scope Control

- prefer narrow diffs
- do not mix release work with UI logic changes unless required
- do not touch `third_party/` assets unless the task explicitly requires it
- do not edit docs, tests, and source together unless the task truly needs all of them
- read-only MCP bridge work must stay localhost-only and must not add write or shell execution paths
- Keep commits focused: do not combine behavior changes with unrelated
  refactors, and do not mix feature work with release-only metadata unless
  required.

## Release Packaging Rule

- Windows release artifacts must live under `dist/releases/v<version>/`.
- Single-file releases may be published directly; multi-file releases (such as Windows onedir) must be distributed as an archive (`.zip` or `.tar.gz`) with its checksum, and must not leave loose executables beside the archive.
- Do not leave release assets loose at the root of `dist/`.
- Build scripts and GitHub release workflow should treat `dist/releases/v<version>/` as the canonical release location.
- If a packaging change creates a new version, create a matching version folder instead of overwriting another release.
- Each Windows archive must contain a `help/` folder next to the executable, holding the Turkish and English GUI help and CLI guide (`HELP_tr.md`, `HELP_en.md`, `CLI_GUIDE_tr.md`, `CLI_GUIDE_en.md`).
- `help/` is copied from `src/hpc_gui/docs/` at packaging time; those files stay the single source of truth and are never edited inside `dist/`.
- Any user-visible GUI or CLI change updates the Turkish and English docs in the same commit as the code, exactly like the i18n rule.
- Release is blocked if `help/` is missing a file, or if the CLI guides do not cover every command reported by the CLI's own command inventory.
- Before a release, inspect the parent-to-release diff. Unexpected source,
  test, or deleted-file changes block the release until explicitly explained.
- Release packaging must not overwrite tracked source files. Generated files
  must be identifiable, and version/configuration metadata should have one
  authoritative source where practical.
- Linux release artifacts must use the same canonical `dist/releases/v<version>/`
  folder as Windows releases; never leave Linux artifacts loose under `dist/`.
- The Linux artifact set is `hpc-client-gui-<version>-x86_64.AppImage`,
  `hpc-client-gui_<version>_amd64.deb`, and
  `hpc-client-gui-<version>.flatpak`; each artifact must have a sibling
  `<artifact>.sha256` file.
- Linux packaging definitions belong under `build/linux/`; the executable
  source of truth remains `src/`, and generated AppImage, `.deb`, Flatpak, and
  temporary build directories are not source-controlled.
- Linux release packaging must copy the bilingual `help/` files, changelog,
  license files, and third-party notices into the version folder; the canonical
  sources remain `src/hpc_gui/docs/`, repository license files, and
  `third_party_licenses/`.
- The Linux release gate must validate version consistency, package metadata,
  executable permissions, artifact contents, SHA-256 files, CLI smoke
  (`--help`, `version`, `doctor environment`), and offscreen GUI startup before
  an artifact is considered releasable.
- Linux release artifacts are built on Ubuntu LTS; the release workflow starts
  its Ubuntu and Windows artifact jobs in parallel, while publication waits for
  both jobs. Fedora and openSUSE remain CI coverage targets as configured.
- WSL Ubuntu is an approved local Linux build and smoke-test environment, but
  its output is not publication evidence; the Ubuntu CI artifact build remains
  the release gate.
- Linux publication is blocked until the real CI artifact build and smoke run
  have passed; workflow artifact upload is not equivalent to GitHub Release
  publication or user approval.

## Remote Branch Protocol

- GitHub (`origin`) carries exactly one branch: `main`. No other branch is ever
  pushed to `origin`.
- `codex/develop` (and any other working branch) stays local-only. Do all
  day-to-day work there.
- To publish, sync the local working branch's changes onto local `main`
  (cherry-pick or merge, whichever preserves history without fabricating
  conflicts — see prior release commits for the pattern) and push only `main`.
- Never `git push origin <branch>` for anything other than `main`, and never
  leave a non-`main` branch on the remote after a release; delete it if one
  appears.

### Main Sync Inclusion Gate

- Before syncing `codex/develop` to `main`, classify every changed path from
  `main...codex/develop` at the repository root.
- Only root files and folders explicitly allowed by `MAIN_SYNC_PROTOCOL.md`
  may be candidates for the sync.
- Never stage, merge, cherry-pick, or push excluded content such as `waves/`,
  `tools/`, root `docs/`, `.agent-runs/`, agent instruction files, local
  protocol/rules files, caches, logs, virtual environments, or temporary
  build outputs.
- `build/` and `dist/` are selective: include only approved packaging
  definitions and validated versioned release artifacts; never synchronize
  their temporary or historical local outputs by default.
- If a changed root path is not explicitly classified as allowed, stop before
  staging and ask the user for confirmation. The excluded path remains local
  to `codex/develop` and is never part of the `main` sync.

## Wave Discipline

- only one wave is active at a time
- tasks come from the active wave only
- future-wave ideas go into future wave docs, not into current implementation
- when a wave is completed and verified, its manifest moves from
  `waves/pending/` to `waves/done/` as part of closing the wave; do not leave
  finished manifests in `pending`. `waves/pending/` keeps only active/queued
  manifests and queue state (`manifest.json`, `README.md`)
- the move is a local filesystem action: `waves/` stays Git-ignored, so
  archiving never creates a commit or reaches `origin`

## Local-Only Agent Files (never on main)

- `CLAUDE.md`, `MAIN_SYNC_PROTOCOL.md`, `AGENTS.md`, and similar agent
  guidance/protocol files must **not exist inside the `main` working tree at
  all** — neither tracked nor as loose local copies. Keep them in a dedicated
  directory *outside* the repository (for example
  `<repo>-local/agent-guides/`) so the local `main` checkout mirrors what is
  pushed.
- Allowed exceptions inside the working tree are local environments and
  caches only: `.venv*/`, `.pytest_cache/`, `.ruff_cache/`, `.idea/`,
  `.claude/`, `.agent-runs/`.
- Before pushing, verify with `git ls-tree -r origin/main --name-only` (or
  `git ls-files`) that none of these paths are tracked. If one ever appears,
  remove it with `git rm --cached <path>` in the same session and commit that
  removal separately; never keep an untracked copy of such a file at the
  repository root afterwards — move it to the external location instead.
- `rules.md` is the tracked exception: rule additions belong in a dedicated
  commit and ride with the next approved `main` push.
- After finishing a wave session, re-check the root: only tracked files plus
  the allowed exceptions above should remain.
