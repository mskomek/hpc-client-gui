# WAVE 06 — CLI modularization

Status: **WAVE_COMPLETE** on the isolated integration branch. Local `develop` and remotes were not changed.

## Source identity and selection

- Wave start: `2d08506d85bc287b21c92c2e28e4e81bfa1b4efb`.
- Source commit: `7675422c1d077572f96ff4fad1b8c703d53ffb31`; tree `eeab892b309b65d4d3bd88d9eacc86e71f8ff3f1`.
- Jobs source: `713949fb752b90601e007812ebf2bd765da5ad52`. Current Jobs/develop command grammar and behavior were retained.
- V2 source: `c0c6d0e956c9283f0c05f25b799e1b1f57ecb240`. The CLI handler facade was selected and reconciled with current behavior.
- Selected dirty V2 snapshot files: `main.py` (`f1b31d147bcbf1adb09b48ca8b60b82202f5f4e156a025292f1a9d7400fbafcb`), `_remote_commands.py` (`023e287b7ead8035583973aa70ee8fce5e2b43732b974d753b87d11d76e16deb`), and `_shared.py` (`73df43717a74a6535c01573e1339d9f153b8152b588471937157446ab1e16bf5`). Snapshot aggregate fingerprint remains `889fb7432500705ff44281ad2c76407d5ec334de17f2ab777128e33ad0d4980b`; it was not modified.
- Changed files: 17 Python files; 8 new application modules. Source fingerprint over sorted `path + NUL + SHA256(committed blob bytes) + newline` records: `e88f1f29f2fc1db360bc84acca16280008e65be87505978e4fea3d24b8c2554c`.

The selected modules are `_contracts.py`, `_doctor_commands.py`, `_file_commands.py`, `_job_commands.py`, `_parser.py`, `_profile_commands.py`, `_remote_commands.py`, and `_shared.py`. `main.py` is now the 190-line public facade. Test patch targets were updated in the CLI support and entrypoint tests; the existing Jobs command and exit-code assertions remain.

V2's changed `session.py` was not selected because it removed saved master-password and keyboard-interactive handling. The existing `session.py`, `terminal_input.py`, `tests/test_cli_saved_credentials.py`, and `tests/test_cli_terminal_output.py` remain. The full raw-key terminal lifecycle and shell output activation were preserved. V2's narrower job ID expression was replaced with the canonical `services.job_identity.is_valid_job_id`, retaining compact-array and heterogeneous ID handling. No existing test was deleted.

## Physical line counts

| Python file | Start | End |
|---|---:|---:|
| `src/hpc_gui/cli/main.py` | 1023 | 190 |
| `src/hpc_gui/cli/_contracts.py` | 0 | 13 |
| `src/hpc_gui/cli/_doctor_commands.py` | 0 | 75 |
| `src/hpc_gui/cli/_file_commands.py` | 0 | 130 |
| `src/hpc_gui/cli/_job_commands.py` | 0 | 82 |
| `src/hpc_gui/cli/_parser.py` | 0 | 221 |
| `src/hpc_gui/cli/_profile_commands.py` | 0 | 112 |
| `src/hpc_gui/cli/_remote_commands.py` | 0 | 175 |
| `src/hpc_gui/cli/_shared.py` | 0 | 154 |

All 17 changed Python files are at or below 500 physical lines. The CLI facade API check found no missing public symbols. No exception was added.

## Verification on source commit `7675422c`

| Check | Result | Exit | Evidence |
|---|---|---:|---|
| CLI, entrypoint, saved credentials, and terminal output regressions | 177 passed, 0 failed, 0 skipped | 0 | `.tmp/wave06-cli-tests.log` |
| Ruff over all 17 changed Python files | passed | 0 | committed-source command output |
| `compileall` over `src/hpc_gui/cli` | passed | 0 | committed-source command output |
| Changed-source architecture gate, base `2d08506d` | PASS; 839 Python files scanned; 47 inherited over-limit files remain; no new dependency/cycle/API errors | 0 | `.tmp/wave06-architecture-final.json` and `.md` |

The architecture gate reduced the over-limit count from 48 to 47. One unresolved internal import and eight dependency cycles remain inherited from the baseline. A cycle between `_remote_commands` and the facade was detected during the first gate run and fixed by injecting the nested-command dispatcher; the final gate reports no new cycle. No real Slurm command, remote connection, or remote file operation was used.

## Integration state

WAVE 06 is committed on `codex/integration/v2-jobs-staged-20261021` only. The branch includes current `develop` through sync merge `1995d7f5cb28de5cdf34737f95202e9d4fb7af9b`. Local `develop` and `origin/develop` remain at `d91c84f1d784fd3391bf132a54134faef44e63c9`. The V2 snapshot and original Jobs/V2 branches remain unchanged. GitHub Actions, Windows11 guest acceptance, Linux package acceptance, and full release acceptance were not run.
