# WAVE 05 — Connection and SSH

Status: **WAVE_COMPLETE** on the isolated integration branch. No local `develop` or remote branch was changed.

## Source identity and selection

- Wave start: `fabc11b01b517f53c55ebf882972c6529a441a9f` (after the current-develop synchronization closeout).
- Source commits: `b0f8f4cbb8deb59169c8ee5f10274b9fc4abf089` and whitespace-only test cleanup `b7e6cac89cc8f2efa48c0a4cbbbfbfe834ea8825`.
- Final source tree: `9ad65473fa6d6f0d5d944de65d2a7057ce952a05`.
- Jobs source: `713949fb752b90601e007812ebf2bd765da5ad52`; selected the 59-line SSH command runner and its connection delegation, plus non-retryable jump-host authentication and forwarding errors. The Jobs secret-fragment extraction was already present from earlier integration and remains in use.
- V2 source: `c0c6d0e956c9283f0c05f25b799e1b1f57ecb240`; selected the auth-policy extraction and the SSH credential/jump-host test splits.
- Changed files: 13 Python files. Added 2 application modules and 6 test/support modules.
- Source fingerprint: `e43d66cbaa374901a18a465c2fdaa0e3e793b8a902b692893de59c517a47f483`, calculated over sorted `path + NUL + SHA256(committed blob bytes) + newline` records for all changed Python files.

The preserved V2 dirty snapshot remains unchanged with aggregate fingerprint `889fb7432500705ff44281ad2c76407d5ec334de17f2ab777128e33ad0d4980b`. Its uncommitted `login_widget.py` facade and `_login_*` modules were reviewed for this wave. WIP test edits change patch targets to match that modularized login implementation; they are deferred with that source to the later UI wave. The exact committed V2 test splits were selected instead. No WIP connection-profile service, auth-policy, or SSH-client source was found in the snapshot.

## Changes and compatibility

- Moved allow-listed password/public-key/keyboard-interactive metadata handling to `connection_auth_policy.py`. `connection_profile_service.py` remains the public facade and re-exports the existing constants and functions.
- Kept `connection_profile_secrets.py` as the secure persistence implementation. The facade continues to pass its existing OS credential store, keychain, master-password, and decryption functions into the helper, preserving patch points used by wx and CLI callers.
- Extracted SSH command execution into `ssh/command_runner.py` without changing command output, timeout status, terminal control filtering, or sensitive-command redaction.
- Marked jump-host authentication and forwarding-denied errors non-retryable. Added regression checks that each error stops after one connection attempt.
- Split the two oversized SSH tests into V2's focused modules and shared fixtures. An AST comparison found all 45 test functions from the two source files in the selected V2 split, with no missing or duplicate test names.

## Physical line counts

| Python file | Start | End |
|---|---:|---:|
| `src/hpc_gui/services/connection_profile_service.py` | 484 | 434 |
| `src/hpc_gui/services/connection_auth_policy.py` | 0 | 74 |
| `src/hpc_gui/ssh/client.py` | 500 | 477 |
| `src/hpc_gui/ssh/command_runner.py` | 0 | 59 |
| `tests/test_ssh_credential_flow.py` | 673 | 307 |
| `tests/test_ssh_jump_host.py` | 538 | 176 |
| `tests/test_ssh_connection_retry.py` | 77 | 94 |

All 13 changed Python files are at or below 500 physical lines. No exception was added.

## Verification on source commit `b7e6cac8`

| Check | Result | Exit | Evidence |
|---|---|---:|---|
| SSH/profile/CLI/SFTP regression suites, including auth metadata, credential save/redaction, jump-host failure/persistence, retry policy and command runner | 139 passed; 9 subtests passed | 0 | `.tmp/wave05-ssh-core-final.log` |
| wx connection, profiles, hardening and lifecycle suites with English translations initialized | 87 passed, 0 failed, 0 skipped | 0 | `.tmp/wave05-wx-connection-final.log` |
| Ruff over all 13 changed Python files | passed | 0 | committed-source command output |
| `compileall` over changed application modules | passed | 0 | committed-source command output |
| Changed-source architecture gate, base `fabc11b0` | PASS; 831 Python files scanned; 48 over-limit files remain; no new LOC/import/cycle/API errors | 0 | `.tmp/wave05-architecture-final.json` and `.md` |

The first wx batch invocation omitted the English locale setup and produced fallback translation-key labels in `test_selected_vs_active_profile` (86 passed, 1 failed). Loading English before the isolated test made it pass; the full wx batch then passed 87/87. This was a test precondition issue, not a product failure. The locale-initialized full-batch rerun is the recorded result.

No real SSH host, Slurm job, remote file mutation, or destructive transfer was used. GitHub Actions, Windows11 guest acceptance, Linux package acceptance, and full release acceptance were not run.

## Integration state

The WAVE 05 commits are on `codex/integration/v2-jobs-staged-20261021` only. The branch contains current `develop` through sync merge `1995d7f5cb28de5cdf34737f95202e9d4fb7af9b`; local `develop` and `origin/develop` remain at `d91c84f1d784fd3391bf132a54134faef44e63c9`. No remote mutation was made.
