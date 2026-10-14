# Candidate 6 Final Acceptance — 2026-10-09

**Verdict: `CANDIDATE6_READY_NO_PUSH`**

Candidate 6 is frozen locally after the shared interactive guest runner validation, fresh-user acceptance (3/3), and ordinary packaged acceptance (10/10). No push was performed. Candidate 5 remains immutable and unchanged.

## Shared runner root cause

PowerShell Direct is suitable for guest control-plane commands, but an inline custom scriptblock is not a reliable way to launch a GUI process on the logged-on desktop and keep its lifetime/results independent of the remote invocation. The old flow could wait on the wrong process/session boundary and had no reusable asynchronous task/result contract. The earlier packaged batch also launched multiple GUI runs under one long-lived Python harness; the second run lost foreground input (`keyboard_input:foreground_lost`). Running each acceptance in its own one-shot interactive task removed that orchestration failure.

The canonical interactive runner now verifies the active Explorer session, stages and hashes files, launches through a unique one-shot Scheduled Task using `InteractiveToken`, polls structured result/evidence, captures stdout/stderr and the actual child exit code, and cleans up only its owned task/process tree. A controlled `exit 7` returned exit code 7 and its sentinel output. A controlled timeout stopped only its owned process tree.

## Global system changes

The shared runner lives outside Git. Before/after hashes and a backup are recorded at `C:\Users\mskomek\.hyperv-tools\backups\candidate6-runner-repair-20261009\changed-file-hashes.json`.

| File | Before SHA-256 | After SHA-256 | Backup |
|---|---|---|---|
| `C:\Users\mskomek\.hyperv-tools\Invoke-Windows11Interactive.ps1` | `79F00C5074DBAC74A02F6EF6D020C3420F27D774CA96ED89266EF07395A3A356` | `759485fcd23d88d88a35f2254df915a8e366e5667294a49d5fd8702150869f78` | `C:\Users\mskomek\.hyperv-tools\backups\candidate6-runner-repair-20261009\Invoke-Windows11Interactive.ps1.pre-exit-code-fix-20261009` |
| `C:\Users\mskomek\.hyperv-tools\Invoke-Windows11.ps1` | unchanged | `BF1454CF594F61EA1B56717A3127C4C353767236B1A429FA6A0C6BA8E1A95377` | no change required |
| `C:\Users\mskomek\.hyperv-tools\ubuntu-ssh.ps1` | recorded in hash inventory | `87824D0583AC2366CB24AD690CFDE70E2F7DB3FD1508BAFB2F5868D8F92D4D90` | recorded in hash inventory |
| `C:\Users\mskomek\.hyperv-tools\Ubuntu-HyperV.Common.psm1` | recorded in hash inventory | `19F0B0FE1FD7C4F3EFB4B150FEE490683A7EE342655FBA4A0723FBCA9ED22956` | recorded in hash inventory |

Ubuntu shared helper validation passed: doctor, three bounded SSH commands, controlled timeout, and SCP. No VM restart or reconfiguration was done. Basic `Invoke-Windows11.ps1` behavior was preserved. Global changes are outside Git and therefore have no Git commit; backup and exact hash inventory are retained. No credential contents were accessed or copied.

## Consumers

Inventory covered HPC Client GUI, Agent Core, Image Process Para, and global Codex/OpenCode/Claude helper structures, searching runner references, VM PowerShell Direct, Scheduled Task, `InteractiveToken`, and `test\home` usage. No active consumer-specific duplicate GUI Scheduled Task implementation or inline PowerShell Direct GUI acceptance flow requiring migration was found. The shared instructions point GUI acceptance to the canonical interactive runner; no project-specific Scheduled Task copy was introduced.

## Runner validation

- Basic noninteractive `whoami`: PASS.
- Interactive identity: `test\home`; Explorer PID 5116 and GUI task both in session 2.
- GUI smoke and actual GUI acceptance ran on the verified interactive desktop.
- Exit-code probe: child `exit 7` surfaced as exit code 7; stdout sentinel captured.
- Timeout probe: 3-second timeout reported `Timeout=true`; owned PID 9628 stopped; cleanup `owned-process-tree-stopped`.
- Three consecutive interactive invocations passed as `test\home`, session 2, exit 0, cleanup completed. Receipt names: `candidate6-consecutive-1.json`, `candidate6-consecutive-2.json`, `candidate6-consecutive-3.json` under `D:\Projeler\.tmp\hpc-client-gui\runner-smoke\results`.
- Ubuntu shared helper: doctor, bounded commands, timeout, and SCP PASS; receipts under `D:\Projeler\.tmp\hpc-client-gui\ubuntu-runner-validation`.

## HPC source

Branch: `codex/c5-final-closure`.

Repair commits include `15377b05` (marshal fresh smoke session attach to wx thread) and `602ed9985634994a4d48655ae1fd4e37e8c9dd43` (isolate native wx lifecycle boundaries). The final source commit used for Candidate 6 is `d40f03d0289be158294241b8542e64ba6a0947be`.

The final shutdown repair synchronously invokes the production close handler on the wx thread and captures teardown/transport/destroy-request evidence before event-loop exit. Focused regression set: **31 passed**. The changed-source architecture validator passed for the two changed first-party files.

## Validation artifact

Repair-validation input was source commit `602ed9985634994a4d48655ae1fd4e37e8c9dd43`; its EXE SHA-256 was `bcaf831603c3526d9a801f91c72b670b915bcacf0eab0643fd421026b68d4f63` and archive SHA-256 was `d21a7be26635632b97923423af58e15bc95c7bfced35c3eed6399b5f6d99bd97`. The guest staging hash was checked against the host hash. Candidate 6 was then built once from the final source commit and frozen separately.

## Fresh guest acceptance

Three consecutive isolated runs passed, each with unique config root, WebView2 profile, evidence folder, and staged copy of the exact Candidate 6 EXE. All ran as `test\home` in session 2 with runner exit 0, no timeout, and completed cleanup.

| Run | Runner ID | Result |
|---|---|---|
| 1 | `4e4388a43f044d6fbff770f70cbc0200` | PASS |
| 2 | `b846d2dbc55a4313b876a791116a3311` | PASS |
| 3 | `abc1ca22e7124ac6bea27fbee2a7db1f` | PASS |

Every run reported fresh config root, empty first-run state, profile creation via visible controls, loopback success via controls, safe visible failure, nonsecret persistence, relaunch persistence, clean shutdown, and process exit 0. Each guest-stage hash matched the host EXE hash. No matching run-owned WER APPCRASH or dump was found in the post-run guest diagnostic. Fresh acceptance output contained three `0x80004004 E_ABORT` occurrences total (one per run); this was counted and did not fail acceptance.

## Packaged acceptance

The first batched attempt passed its first run but the second lost foreground input (`keyboard_input:foreground_lost`), so that batch stopped. The runner model was changed to a separate one-shot interactive task for each invocation. The required subsequent **10/10** ordinary packaged runs all passed on the same exact Candidate 6 executable, as `test\home` session 2, process exit 0, runner exit 0, no timeout, cleanup complete.

| Run | Runner ID | Result |
|---|---|---|
| 1 | `6f41be7e4b8c41dd80f602bfa4242b04` | PASS |
| 2 | `875a0c7c7c8b40cabf5a296910903208` | PASS |
| 3 | `44a8ce87dbc14898ac21acfabc62f25f` | PASS |
| 4 | `0382c7a881ec4d9eb37724e90353eaaa` | PASS |
| 5 | `e54035ebc41349dcb287dcc2a2cdc5a4` | PASS |
| 6 | `5223b58a769f4d1fb46b68ca89ab7fa3` | PASS |
| 7 | `0ac2774a24e84bd188987945ba805c0e` | PASS |
| 8 | `b0c272e392654b938ccf89d2b40e99eb` | PASS |
| 9 | `f945adeae23543a389f47da9bf423c53` | PASS |
| 10 | `495b5582a3a4444ab4115787739a2f61` | PASS |

Successful packaged smoke receipts do not expose an E_ABORT count. No zero count is inferred for those runs.

## Native

Accepted Candidate 5 canonical native evidence remains: WER 0, crash dump 0, `0xC0000005=0`, `0xC000041D=0`, `0xC0000409=0`, `wxRecursionGuard=0`, and `WindowDestroyEvent=0`; W19 isolated and terminal WebView suites were 3/3 clean. A read-only post-acceptance guest diagnostic found no matching Application Error/WER event, hpc dump, remaining run task, app process, or run-owned Python process. Per-run packaged receipts do not expose all native counters, so this report does not claim per-run native event counters beyond the evidence available. OS-owned SearchHost WebView2 processes were left untouched.

## Candidate 6

Frozen directory: `D:\Projeler\.worktrees\hpc-c5-final\artifacts\candidate6`.

- Source branch: `codex/c5-final-closure`
- Source commit: `d40f03d0289be158294241b8542e64ba6a0947be`
- EXE SHA-256: `67f60b50f1ea0ff45347b1c9afa942eb12172b21523d67011ec2d28e9379aae6`
- EXE bytes: `7,549,252`
- Archive SHA-256: `41714332b3fbf6568684e2baf14339e7377240bdbb52835131c933692fd1d212`
- Archive bytes: `27,998,208`
- Package file count: `158`
- Python: `D:\Python\Python312\python.exe`
- PyInstaller: `6.19.0`
- wxPython: `4.3.1`; wxWidgets: `3.3.3`
- Build-input manifest: `artifacts/candidate6/manifest.json`
- Freeze hash receipt: `artifacts/candidate6/freeze.sha256`
- Acceptance/runner receipts: `artifacts/candidate6/receipts/`

Candidate 6 was frozen once. It was not rebuilt after freeze. The frozen artifact files are unmodified.

## Cleanup

Post-acceptance guest diagnostics found no stale `CodexGuestRun_*` task, hpc-client-gui process, run-owned Python process, matching WER event, or hpc crash dump. Only owned task/process trees were eligible for runner cleanup. No user processes were killed. Credentials, VM configuration, WER LocalDumps settings, and WPR state were not changed. Candidate receipts and Ubuntu/runner validation receipts were retained. Candidate 5 and unrelated main-checkout changes were preserved.

Task-created `.tmp` runner/build/acceptance helper scripts were removed after their receipts were retained. The active `codex/c5-final-closure` worktree is clean. The repository has numerous pre-existing historical worktrees and branches. In the older Candidate 5 experiment group, `candidate5-repair-ab/CONTROL`, `candidate5-repair-ab/PATCHED`, and `candidate5-repair-control-no-patch` contain substantial dirty/untracked Wave and test data, so they were preserved. The clean `candidate5-repair-baseline` was also retained as a reference. The `v2-candidate-20261008-r5` worktree contains an untracked `artifacts/candidate5/`; other inspected v2-candidate worktrees were clean. These historical worktrees/branches were not removed because doing so could destroy useful evidence or user data. No credentials, user VM state, or unrelated checkout data were removed. No push was performed.

## Candidate 5

Candidate 5 immutable EXE SHA-256 remains `2966a977edc0fe5525c8591df6108e731cd944e2b9d396ee72847792afca654c`. Candidate 5 immutable archive SHA-256 remains `7ae23f2d6cea49d4c4b422dacdf88cbac8eba7f43aff58a44e0c92a041d7e953`. Candidate 5 was not rebuilt or overwritten.

## Push

**NO** — all changes and the Candidate 6 artifact are local only.
