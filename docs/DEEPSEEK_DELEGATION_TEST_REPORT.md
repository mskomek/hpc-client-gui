# DeepSeek delegation test report

Status: **live validation completed where the installed account permits it.**

- Date/local time: 2026-08-01 Europe/Istanbul (initial setup)
- Git HEAD: `275ebf4`
- Codex CLI: `0.116.0`
- Claude Code: `2.1.104`
- OpenCode: `1.18.11`
- PowerShell: Windows PowerShell `5.1.26100.8875`; PowerShell `7.6.3`
- Discovered DeepSeek model IDs: `opencode/deepseek-v4-flash-free`, `opencode-go/deepseek-v4-flash`, `opencode-go/deepseek-v4-pro`, `ollama-cloud/deepseek-v4-flash`, `ollama-cloud/deepseek-v4-pro`

## Offline tests

Run: `powershell -NoProfile -File tools/ai/test-deepseek-integration.ps1 -OfflineOnly`

| Test | Result |
| --- | --- |
| PowerShell scripts parse | PASS |
| Dry-run does not invoke a model | PASS |
| Missing task is rejected | PASS |
| Both task inputs are rejected | PASS |
| Missing TaskFile is rejected | PASS |
| Empty task is rejected | PASS |
| Implement without WorktreePath is rejected | PASS |
| Implement primary repository is rejected | PASS |
| Analyze edit request is rejected | PASS |
| Review edit request is rejected | PASS |
| Dangerous Git commands are rejected | PASS |
| HPC commands are rejected | PASS |
| Secret paths are rejected | PASS |
| `.agent-runs` is ignored by Git | PASS |
| No model ID is guessed | PASS |
| Governance files and pre-existing user changes were preserved during test | PASS |

`git diff --check` also completed successfully after the offline run.

## Live tests

No credential was requested, read, stored, or logged.

- Model discovery: **PASS** — `opencode models` returned `opencode-go/deepseek-v4-flash` and `opencode-go/deepseek-v4-pro`. The wrapper selected Flash for read-only work and Pro for implementation; no non-OpenCode-Go model was selected.
- Exact smoke response: **PASS** — the shared worker exited `0` with `opencode-go/deepseek-v4-flash` and returned its generated exact `TRUBAGUI_DEEPSEEK_OK_…` nonce. The ephemeral nonce is deliberately not retained in this report.
- Read-only TRUBAGUI analysis: **PASS** — the Flash worker identified Python/PySide6 from `pyproject.toml`, supporting files including `src/truba_gui/app.py`, and `python scripts/smoke_test.py` from `rules.md`. These claims were checked locally. `git status --porcelain` and `git diff --name-only` showed no model-caused project changes.
- Synthetic review: **PASS** — against a disposable external Git repository, Flash identified `cp.exec(userInput)` as shell/command injection and recommended `execFile`/`spawn` with argument arrays. It did not edit the repository or commit.
- Disposable implementation: **PASS** — in a separate disposable Git worktree, Pro created only `deepseek-integration-proof.txt` with the exact generated content and newline. The parent disposable worktree was clean, the starting commit was unchanged, and TRUBAGUI was unchanged.
- Codex orchestration: **PASS** — this Codex task invoked the shared worker for smoke, analysis, review, and implementation, then checked its repository claims and the resulting Git states independently.
- Claude orchestration: **SKIPPED** — `claude -p` is installed but returned: `Your organization does not have access to Claude. Please login again or contact your administrator.` The repository status was unchanged before and after the attempt.

Disposable live-test paths were created under `D:\Projeler\deepseek-live-*`, outside TRUBAGUI. Automatic removal was prevented by the host's destructive-command policy after canonical-path validation; they contain only synthetic test repositories and no credentials or production data.

## Project validation

- `powershell -NoProfile -File tools/ai/test-deepseek-integration.ps1 -OfflineOnly`: **PASS**.
- `PYTHONPATH=src .\.venv\Scripts\python.exe scripts\smoke_test.py`: **PASS** (`smoke test: OK`).
- `python scripts/smoke_test.py` and `.\.venv\Scripts\python.exe scripts\smoke_test.py` without `PYTHONPATH=src`: **FAIL** (`ModuleNotFoundError: No module named 'truba_gui'`). This is the established source-layout invocation requirement, not a DeepSeek integration failure.
- `git diff --check`: **PASS**.

## Current policy note

After the recorded live test, project policy changed on 2026-08-01: OpenCode Go DeepSeek v4 Flash is now the default for every mode, including implementation. The earlier Pro implementation result above remains an accurate historical test observation; it is not the current default-selection rule.

The updated default was live-checked with `deepseek-worker.ps1 -Mode smoke-test`: the worker selected `opencode-go/deepseek-v4-flash`, exited `0`, and returned its exact generated nonce. The nonce is intentionally not retained.
