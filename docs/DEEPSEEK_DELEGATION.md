# DeepSeek delegation through OpenCode

## Architecture

Codex CLI and Claude Code remain the primary orchestrators. Both call the same project-local PowerShell worker, which discovers a DeepSeek identifier from the locally installed OpenCode CLI and then invokes OpenCode as a child process:

```text
Codex CLI or Claude Code -> tools/ai/deepseek-worker.ps1 -> OpenCode CLI -> OpenCode Go -> DeepSeek
```

The worker is not a proxy for either native agent. It is a bounded delegated-worker process.

## Prerequisites and connection

Observed on this machine: OpenCode `1.18.11` supports `opencode models` and `opencode run --model provider/model --file prompt-file`. Model IDs are discovered at run time; they are never guessed or committed. The installed list currently includes `opencode-go/deepseek-v4-flash` and `opencode-go/deepseek-v4-pro`, but an entry in that list is not proof that a live call is authorized.

Do not put secrets in a task. In particular, do not include credentials, private keys, patient data, or production-cluster credentials.

To connect OpenCode Go, use another terminal and enter the credential only in OpenCode's own UI:

```text
opencode
/connect
select OpenCode Go
enter the API key directly in OpenCode
/models
exit OpenCode
```

The worker neither reads nor writes OpenCode credential storage.

## Commands

Use PowerShell 5.1 or PowerShell 7; the wrapper was designed for both.

```powershell
powershell -NoProfile -File tools/ai/deepseek-worker.ps1 -Mode analyze -Task "Identify the test command from repository files."
powershell -NoProfile -File tools/ai/deepseek-worker.ps1 -Mode review -Task "Review the current diff for correctness and scope."
powershell -NoProfile -File tools/ai/deepseek-worker.ps1 -Mode implement -TaskFile TASK.md -WorktreePath "D:\Projeler\feature-worktree"
powershell -NoProfile -File tools/ai/deepseek-worker.ps1 -Mode smoke-test
powershell -NoProfile -File tools/ai/deepseek-worker.ps1 -Mode dry-run
powershell -NoProfile -File tools/ai/test-deepseek-integration.ps1 -OfflineOnly
```

Analyze, review, and implement require exactly one of `-Task` or `-TaskFile`. A task file must be inside this repository unless `-AllowExternalTaskFile` is explicit. `-Model`, `-FlashModel`, and `-ProModel` override selection only with a model ID returned by `opencode models`. `DEEPSEEK_FLASH_MODEL` and `DEEPSEEK_PRO_MODEL` may hold non-secret model IDs. `-TimeoutMinutes`, `-NoLogs`, `-OutputFormat`, and `-VerboseWorker` are also available.

Timeouts are deliberately generous for DeepSeek v4 Flash: analyze defaults to
20 minutes, implement to 30 minutes, review to 20 minutes, and smoke-test to 10
minutes. An explicit `-TimeoutMinutes` overrides the mode default. Values remain
bounded to 1–120 minutes; a timeout is a failed run and never an implicit PASS.

Wave execution additionally supplies safe identifiers through `-Wave` and
`-Card`. These identifiers are written to `metadata.json`; the worker never
infers them from prose. `-NoLogs` must not be used for wave work.

The discovered OpenCode Go DeepSeek v4 Flash model is the default for analysis, implementation, review, smoke tests, Codex, and Claude. This keeps one predictable project default. A different OpenCode Go DeepSeek model is used only through an explicit `-Model` override, and the override must still appear in `opencode models`. `-AllowFlashImplementation` remains accepted for compatibility but is no longer required because Flash is the project default.

## Boundaries and isolation

Analyze and review are read-only by contract and reject editing language in their supplied tasks. Implement requires a clean Git worktree under the parent directory of the main checkout; it refuses the primary worktree, non-Git paths, dirty worktrees, and paths outside that approved parent. The worker never stages, commits, pushes, resets, or cleans.

The wrapper rejects tasks that request secrets or real remote/HPC commands, including `sbatch`, `scancel`, `srun`, `ssh`, `scp`, and `rsync`. DeepSeek can inspect such commands as repository text only. No real TRUBA action is authorized by this integration.

OpenCode 1.18.11's installed help did not provide a verified project-local permission-file schema, so no speculative `.opencode` permission file was created. The wrapper and its contracts are the enforced project-local boundary; they complement, but do not replace, primary-agent review.

## Logging and troubleshooting

Unless `-NoLogs` is passed, each call writes `.agent-runs/<timestamp>-<mode>/` with the request, separated stdout/stderr, and non-secret metadata. `.agent-runs/` is ignored by Git. Never assume logs are appropriate for sensitive task text.

The metadata schema records the run ID, wave/card identifiers, mode, discovered
model, OpenCode version, worktree, starting and ending Git heads, timestamps,
duration, configured timeout budget, real child exit code, timeout state, and artifact paths. Implement
runs also record changed paths and diff statistics; read-only runs leave these
fields null so a dirty primary tree is not falsely attributed to DeepSeek.

The worker separately records the raw child exit code and its effective exit
code. A zero child exit with an empty model response is an effective failure and
sets `responsePresent` to false; it must never be treated as a completed review.
Unexpected wrapper failures are recorded in `failureMessage` before the error is
returned to the caller.

Codex must inspect `request.md`, `stdout.log`, `stderr.log`, and `metadata.json`
and then write the independent packet verdict described in
`docs/WAVE_PLAN.md`. A worker response is evidence, not a verdict.

## Sequential wave queue

`tools/ai/wave-queue.ps1` is the only supported way to claim, verify, release,
recover, or archive local wave manifests. It uses an exclusive filesystem lock
and an owner token, validates packet verdicts and Flash capacity evidence, and
refuses out-of-order or manual archival. `tools/ai/test-wave-queue.ps1` exercises
the state machine entirely against disposable offline fixtures. DeepSeek never
runs `complete`; Codex owns final gate verification and archival.

`docs/OPENCODE_WAVE_MASTER_PROMPT.md` is the paste-ready command that starts the
next wave immediately. Reusable per-packet analyze/delivery/review wording is
kept separately in `docs/OPENCODE_PACKET_PROMPT_REFERENCE.md`; passing the
reference document alone is not a wave-execution request.

If no DeepSeek ID is returned, run `opencode models`, complete the interactive connection above if necessary, then rerun. If IDs change, use the current discovered ID with `-Model` or update the non-secret environment variable. If the integration must be disabled, do not invoke the worker; no global configuration was changed.

## Codex and Claude workflow

For a non-trivial task, the primary agent calls analyze, verifies repository evidence, sends only a bounded implementation request to a separate worktree, calls review on the resulting diff, independently checks it, and then runs authoritative validation. Codex/Claude retain architecture, security, authorization, schema, product, documentation, staging, commit, and handoff authority. The older project-local Ollama/Qwen pipeline is inactive and must not be selected unless the user explicitly re-enables it.

Claude Code has a supported non-interactive `--print` mode on this machine. It may be asked to invoke the same worker for a read-only smoke or analysis task, but live Claude orchestration is only reported as passed after the returned DeepSeek nonce is verified and Git remains unchanged.
