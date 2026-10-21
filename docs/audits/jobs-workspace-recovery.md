# Jobs Workspace Recovery audit

Date: 2026-10-20

## Decision

**Jobs workspace recovery is functionally validated on Windows and Ubuntu, including persistent restore, packaged Windows smoke, and an Ubuntu packaged GUI launch.** The profile-scoped store and Jobs/Details/Files/Outputs repairs are committed locally on `codex/jobs-workspace-recovery`; the final regression/harness repairs and evidence are committed in `8a27b784` and pushed to `origin/codex/jobs-workspace-recovery`. The final full `release_test_suite.py` invocation passed after the mock-SSH lifetime fix. The Windows candidate was rebuilt from this worktree, passed 21/21 packaged smoke checks, and ran `--help` successfully in the Windows11 interactive user session with matching host/guest SHA-256. Ubuntu Jobs service/provider regressions passed. A persistent per-user Ubuntu Python/build environment was provisioned. Linux PyInstaller build, packaged CLI smoke, and Xvfb GUI launch all pass using the persistent per-user wxPython 4.2.1 environment. **The 2026-10-20 modularization follow-up reduced `wx_jobs.py` to 485 physical lines, extracted its stateful workflows into cohesive Jobs controllers, and removed the expired LOC exception.** See the dated follow-up below for the post-refactor regression evidence.

## Starting state

- Repository: `mskomek/hpc-client-gui`
- Starting branch: `develop`
- Starting commit: `b2de2bb8ccc533aa0b0ecb7dd2a798a4fcdf709a`
- `origin/develop` matched that commit after fetch; the main checkout was left untouched.
- Work used a separate worktree on `codex/jobs-workspace-recovery`.
- Related plugin repository started at `8cce85446a8db72ea6b89b56bcb3df8916cbb0a8`; its pre-existing untracked `.github/social-preview.jpg` was preserved.

## Root causes found

- Job history storage was keyed by bare scheduler job ID, so identical IDs from different profiles/clusters could collide. The old store mostly represented submitted jobs and did not restore full workspaces into Jobs.
- Queue/accounting observations were not consistently persisted or combined with local records.
- Selected-job context omitted profile/provider identity and important path/script metadata.
- Files navigation could fall back to `/` and swallowed navigation errors; path selection was local to the Jobs UI.
- Output resolution did not receive known script content/path, and output snapshot status/fallback was incomplete.
- Jobs list was single-select and lacked local-only bulk details deletion.
- TRUBA 1.5.0 history configuration does not request WorkDir/StdOut/StdErr. The application now retains known paths and uses explicit fallback; plugin field support was not assumed.
- Job scripts and observation metadata used separate, narrow redaction paths. Raw details in metadata could bypass size limits/redaction, and prefixed secret keys or quoted CLI values could escape the old pattern.
- The SSH facade did not re-export `_KnownHostsPolicy`, breaking collection of the SSH jump-host tests; forwarding-denied/authentication errors could be retried and masked by a later transport error.

## Changes made

- Added versioned SQLite workspace storage keyed by profile, cluster, provider, scheduler ID and component ID, with v2 migration, non-empty merge semantics, snapshot size limits, shared secret redaction, and delete tombstones.
- Persisted submitted provenance and discovered scheduler observations; Jobs history merges scheduler results with scoped local records and can show the local archive offline.
- Added a shared remote directory resolver with path provenance and no invented root fallback.
- Extended selected context with full scope/script/path data and retained last known successful fields across empty updates.
- Added multi-select while keeping a primary Details selection, confirmed bulk **Delete Details**, per-profile deletion scope, and error reporting for Files navigation. Delete does not cancel jobs or remove remote files.
- Persisted raw Details/Accounting and output snapshots; cached output includes capture time, and known script data is passed to the output resolver.
- Added tests for migration, duplicate scheduler IDs, tombstones, redaction/bounds, path recovery, GUI bulk deletion, SSH jump errors, and relevant Files/output behaviors.
- Fixed stale Wave80 assertions to match existing English/Turkish labels; fixed the Files stress test to select a file row after directory-first sorting; updated the download-wire fake to accept the provider's `direction` argument.
- Added test-process isolation for wx files that demonstrably crash the Windows combined GUI process.
- Added the Files header Upload/Download controls required by the W04 support freeze and wired them through the existing local/remote `run_action` paths.
- Fixed async SFTP upload/download cancellation propagation and WebView2 teardown ownership, then aligned lifecycle assertions with parent-owned native destruction.
- Split the 1,489-line Wave 65A file stress test into cohesive sub-500-line modules with shared support and preserved group metric gates.
- Updated file UI tests to treat the `..` parent navigation entry correctly and keep system clipboard tests isolated from the user's clipboard.
- Updated the release harness to discover all pytest-marked native GUI files and isolate them from the mixed-toolkit process.
- Fixed the mock SSH fixture's fixed 20-second transport shutdown, which interrupted legitimate long SFTP transfers; the server now remains alive until its client closes or fixture teardown begins.
- Extracted Wave0's golden Unicode filesystem tests and shared fixtures into dedicated sub-500-line modules to preserve the repository's source/test LOC rule.

## Validation

| Check | Result | Evidence |
|---|---|---|
| Ruff over `src scripts tests` | PASS | `.venv` from the untouched main checkout: `All checks passed!`. |
| `git diff --check` | PASS | Clean on the final worktree diff. |
| Compile, i18n and headless smoke preflight | PASS | Final release harness compileall, `check_i18n.py`, and `smoke_test.py` all passed. |
| Focused Jobs/storage/provider regression on Windows | PASS | Existing focused coverage plus the complete final release harness; final Jobs Details, outputs, identity, submit/cancel, race/lifecycle, Files/Outputs modules passed in isolated partitions. |
| Focused Jobs/storage/provider regression on Ubuntu-Test | PASS | Persistent GUI-capable `/home/test/.venvs/hpc-client-gui-py312` Python 3.12.3 venv: 158 passed across job store/history/selection, output resolver, provider contract, and Unicode filesystem tests. Ruff and `pip check` also passed in this venv. |
| Release harness broad partition | PASS | `1,848 passed, 29 skipped, 61 deselected, 22 subtests passed`; compileall, i18n and headless smoke passed. |
| Release harness isolated partitions | PASS | Final run completed every isolated wire/native-GUI partition. Heavy `wx_shell_p0_stress` passed twice (675.63 s and 453.56 s); `wx_65a_integrated_stress` passed (678.89 s); layout resize passed (290.56 s); split File003 stress partitions passed. |
| Release harness overall | PASS | `scripts/release_test_suite.py` completed with exit code 0 and `all release preflight gates passed`. |
| Windows PyInstaller build | PASS | Rebuilt from worktree HEAD `4f1179d37cd4cbc96a32323f2b4f07cd35c1998e` with Python 3.14.0 / PyInstaller 6.22.2. Isolated onedir artifact: `.tmp/jobs-vm-final-20261020/dist/hpc-client-gui/hpc-client-gui.exe`, SHA256 `7cbd5073db7a3a43bc343a0029ebadad688c08f4090792f1cb44136ff10094dc`. |
| Packaged Windows smoke | PASS | Same artifact SHA passed all 21/21 checks: runtime/frame/settings, terminal/PTY, remote file roundtrip, Jobs, Files, editor, transfer queue, reconnect identity, and clean shutdown. Host runner recorded Python 3.12.4 and isolated execution outside `src`. |
| Windows11 VM package launch | PASS (narrow) | Canonical interactive runner launched the staged artifact in `test\\home` Explorer session with `--help`; exit code 0, no timeout, and guest SHA256 exactly matched host SHA256. This is CLI/package launch evidence, not a second full GUI workflow replay. |
| Windows11 VM GUI workflow | PARTIAL / BLOCKED_ENV | A pre-commit build with the same functional source staged successfully, created the main frame, and shut down cleanly; smoke then correctly failed because the isolated guest had no test SSH service. For the commit-bound build, host/guest SHA matched, but the canonical runner failed in guest bootstrap with `Cannot create a file when that file already exists` before launching the executable. No update or real cluster was used. |
| Persistent Ubuntu toolchain | PASS | Python 3.14.8 and Python 3.12.3 venvs with release-locked runtime/test libraries (wxPython supplied separately), PyInstaller 6.22.2 and Ruff 0.15.5 live under `/home/test/.venvs/`. Official Ubuntu 24.04 `python3-wxgtk4.0` 4.2.1 plus its three wx runtime `.deb` packages are persistently cached under `/home/test/.cache/hpc-client-gui/wx-debs` and extracted under `/home/test/.local/opt/hpc-client-gui/wx`; `/home/test/.local/bin/hpc-client-gui-python312` sets Python/library paths. GNU binutils 2.42 is extracted under `/home/test/.local/opt/hpc-client-gui/binutils` with `objdump`/`objcopy` wrappers in `/home/test/.local/bin`. No sudo or system package database changes were needed. |
| Ubuntu Linux PyInstaller build | PASS | GUI-capable build using Python 3.12.3 + wxPython 4.2.1: `/tmp/jobs-workspace-recovery-4f1179d/build-wx42/dist/hpc-client-gui/hpc-client-gui`; SHA256 `c05622024c411446a33ec7e880429ce44e47f1bffa8832ea3b69a5d60ab28ce2`. `ldd` reported no missing shared libraries. |
| Ubuntu packaged CLI smoke | PASS | Built artifact `--help` returned 0 and printed the expected CLI command inventory. |
| Ubuntu GUI runtime smoke | PASS (Xvfb) | Built artifact launched `gui` under `dbus-run-session` + Xvfb and exposed the `HPC Client` 760x560 main window; safely terminated the isolated test process. wx 4.2.1 also created and showed a frame. |
| Windows GUI teardown warnings | PASS WITH WARNINGS | Some passing native wx partitions emitted WebView2 `Operation aborted` / Windows `UnregisterClass` teardown warnings; their pytest results were PASS. |
| Real Slurm and remote destructive actions | SKIP | No real Slurm job was submitted/cancelled and no remote file was deleted. |

## Architecture and plugin status

The 2026-10-20 modularization follow-up brings `src/hpc_gui/wx_jobs.py` from the pre-refactor 3,055-line state down to 484 physical lines. Details, Files, job list/refresh/selection/actions, provider status, output channel lifecycle/refresh/interactions, localization, and workspace teardown/navigation now have separate modules under `src/hpc_gui/jobs/`; all Jobs modules remain below 500 lines. The LOC exception manifest is empty. The shared Agent Core source architecture validator passed in changed-source scope: 27 files checked, no over-limit files or dependency errors; four changed files are in the 400–500 warning zone (`details_controller.py` 439, `workspace_views.py` 490, `wx_jobs.py` 484, and `tests/support/mock_ssh_server.py` 482). The full-project scan still fails on 50 existing over-limit files outside this Jobs change; dependency errors are zero. The Jobs factory and view factory are composition boundaries and should not absorb new behavior without another cohesive extraction.

No change was made to `mskomek/hpc-client-gui-plugins`. TRUBA `1.5.0` history fields were inspected and do not include WorkDir/stdout/stderr; application fallback handles old packages without claiming unsupported fields.

## Known deviations and follow-up

- The legacy 3,055-line statement above describes the pre-modularization snapshot; the dated follow-up supersedes it. `wx_jobs.py` is now 485 lines and has no exception entry.
- Ubuntu runtime validation used the official Ubuntu wxPython 4.2.1 package with Python 3.12.3; it differs from the 4.3.1 release-lock pin. Packaged build, GUI startup, and 158 Jobs tests passed with the distro version. Building the pinned wxPython 4.3.1 from source would require authorized admin provisioning of the missing compiler/GTK development dependencies.
- Windows11 guest CLI launch passed under `test\home` Explorer; a full GUI guest run remains blocked by the startup update modal and subsequent canonical-runner bootstrap state-file collision. The full 21/21 packaged workflow smoke passed on the Windows host.
- The previously pushed branch predates this modularization change; current changed-source and GUI regression results are recorded in the final addendum below.

## Modularization follow-up (2026-10-20)

- Reduced `wx_jobs.py` from 3,055 to 484 physical lines by moving selection, safe cancellation, asynchronous queue refresh, Details/Accounting, Files navigation, provider status, output channels/followers/search, localization, and workspace lifecycle into separate controllers.
- Kept the Jobs factory as the composition root, with provider callback aliases normalized at the UI boundary. The Files and Outputs controllers use the same retained workspace context and selection generation.
- Fixed the Accounting callback reference discovered by the extracted controller's GUI regression. Fixed Show in Files to read the path field associated with the active output channel and to compare wx wrapper objects by equality.
- Removed the obsolete `wx_jobs.py` exception from `docs/architecture/source-loc-exceptions.json`; reformatted workspace state so state entries remain auditable one per line.
- Updated controller/source-boundary tests and reran targeted GUI regressions. The shared source architecture validator passed for changed files (27 checked, 0 over limit, 0 dependency errors); the full-project scan remains FAIL on 50 unrelated legacy over-limit files. Final aggregate test results and the exact source revision are recorded after the final test pass.

## Local commits

- `72359f27` — profile-scoped workspace records
- `32aae234` — workspace restoration and safe details deletion
- `7051a62c` — persistence and path recovery tests
- `2de6fc06` — initial audit record
- `cd780e09` — SSH jump failure/settings contracts
- `a043d8d5` — snapshot secret redaction
- `f119e2e7` — wx isolation and regression fixture updates
- `4f1179d3` — Windows performance probe isolation and audit update
- `8a27b784` — GUI workflow, release harness and Ubuntu/Windows validation follow-up
- `596f8603` — final cross-platform Jobs evidence and push record

Push: [origin/codex/jobs-workspace-recovery](https://github.com/mskomek/hpc-client-gui/tree/codex/jobs-workspace-recovery). Code/test commit `8a27b784b260994887827c5451550511e30d782f` and audit commit `596f860396d98f0a6955fd78a0fd60a8f71168c8` were pushed; this follow-up records the Windows11 GUI runner block.

## Follow-up — output module extraction and VM retest (2026-10-20)

- Extracted the independent detached-output model and live output window from `src/hpc_gui/wx_jobs.py` into `src/hpc_gui/jobs/output_workspace.py` (285 LOC). The public imports from `hpc_gui.wx_jobs` remain compatible. `wx_jobs.py` is now 3055 LOC; its documented exception remains because the panel composition and its nested callbacks still form one large closure. This extraction reduces the monolith but does not close the architecture migration.
- Updated source LOC exception metadata to 3055 and recorded the remaining cohesive extraction target. New source files remain below the 500-line limit.
- Windows host verification on the rebuilt package: PyInstaller 6.19.0 / Python 3.12.4 build passed; packaged application smoke passed 21/21 including Jobs, Files, reconnect, and clean shutdown. Artifact SHA256 was `19b7369412d40e3a361518126424001830ca1a061b5fa39073a618c12bb6ae41`. The final artifact was rebuilt after commit `f96ec99debbe29d2930a6ff8fad9fe957d5b9820`; its embedded main SHA matches that commit.
- Windows11 interactive VM verification: canonical runner staged the same executable with matching host/guest SHA256, verified active `test\\home` Explorer session 2, launched the GUI, observed `main_frame_created=PASS`, and observed clean shutdown. That run's guest smoke exited 1 because the isolated guest run was intentionally not given its test SSH server; smoke reports `packaged smoke SSH environment is missing`. A second run of the commit-bound artifact was blocked by the runner's `state.json`/file-exists bootstrap error before process start. No real cluster or startup update was used. This is partial GUI launch evidence, not full guest acceptance; full 21/21 Windows host smoke remains PASS.
- Ubuntu-Test verification: the changed source and tests were copied into a temporary isolated source tree; under Xvfb + D-Bus and the persistent GUI Python 3.12.3 environment, the focused Jobs/storage/provider suite passed `249 passed`. The first attempt without a null keyring backend hit Secret Service activation timeouts and was stopped by the 900-second runner limit; rerun with `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring` completed in 63.64 seconds. The extracted `test_wx_jobs.py` was then rerun against the final import ordering: `5 passed`.
- Quality gates on the follow-up diff: Ruff PASS; `git diff --check` PASS. The pre-existing full release suite result remains the recorded `1,848 passed, 29 skipped, 61 deselected, 22 subtests passed`; it was not rerun after this mechanical output-module extraction.
- Remaining acceptance limitation: a full Windows11 guest workflow replay with the bundled loopback SSH fixture has not been established. The GUI smoke output and host 21/21 result are retained separately and are not conflated.

- Commit-bound Windows build after `f96ec99d`: SHA256 `98bcf27b9c83f7d04a2d9d7a489b9f275db8353010ccfe8ab3dc237b51ce3eba`; embedded main SHA `f96ec99debbe29d2930a6ff8fad9fe957d5b9820`. Its Windows host packaged smoke again passed 21/21.

## Follow-up — isolated Windows11 fixture attempt (2026-10-20)

- Extended `tests/support/mock_ssh_server.py` with an explicit bind-interface option while keeping loopback as the default. Added a focused regression proving both the explicit loopback setting and default listener accept a local TCP connection. The server was also started on the isolated `hpc-lab` host interface for a Windows11 guest smoke attempt, using only the fake test account.
- The `hpc-lab` guest-to-host connection probe was blocked by the Windows host firewall. Adding a temporary rule restricted to the fixture port, guest address `192.168.250.14`, host address `192.168.250.1`, and `vEthernet (hpc-lab)` returned `Access is denied` before a rule was created. No firewall policy was broadened. The temporary fixture process was stopped. Full Windows11 GUI workflow remains `BLOCKED_ENV` until the runner has permission to install that narrowly scoped temporary rule or an approved guest-local SSH fixture is available.
- Focused regression: `tests/test_mock_ssh_server_binding.py`, `tests/test_w11_ssh_lifecycle.py`, and `tests/test_mock_cluster_roundtrip.py` passed (18 tests); Ruff on the changed fixture/tests passed; `git diff --check` passed.
- The Jobs panel extraction remains incomplete: `src/hpc_gui/wx_jobs.py` is still 3,055 LOC under its documented, expiring exception. No claim is made that the 500-line architecture target has been met.

## Follow-up — job-list preparation extraction (2026-10-20)

- Moved framework-neutral row normalization, identity-field filtering, and list filtering/sorting preparation into `src/hpc_gui/jobs/job_rows.py`. `hpc_gui.wx_jobs._parse_job_row` remains a compatible import alias for existing consumers. The panel now delegates list preparation to the leaf module; the source LOC exception was updated from 3,055 to 3,010.
- Added mapping, pipe/whitespace format, filter, terminal-hide, input-immutability, and active-first tests. Focused Jobs list/history regressions passed (35 tests). The Windows11 runner is being retried with a guest-local packaged fixture to avoid host firewall changes.

## Follow-up — Windows11 guest-local packaged acceptance (2026-10-20)

- Built the final Windows onedir artifact from the current worktree source using Python 3.12.4 and PyInstaller 6.19.0. The artifact's embedded main revision is `76520aa2eb1b0ebb539ffb42d637e6821b075942`; the worktree also contained the listed uncommitted job-row extraction and mock-fixture binding changes. GUI artifact SHA256: `efd0942b3a83cb391627e0f50e487576bfca37a31654011aec1a1144df0803b0`.
- The final artifact's host packaged smoke passed all 21/21 checks. A one-file test-only launcher bundled the existing mock SSH/SFTP fixture and ran it on guest loopback; the canonical Windows11 interactive runner staged the bundle into the active `test\home` Explorer session, confirmed launcher SHA256 `761352630a220adcf6449448daed5df055d977148d1c4bcbc86b0eabb2d1dbc3` and GUI artifact SHA256 matched on host/guest, returned exit code 0, did not time out, and cleaned its staged guest artifacts.
- The guest runtime evidence was finalized using the repository's `finalize_runtime_observation` contract plus the fixture's wire observation. Result `PASS`, all 21 checks `PASS`, PTY initial size `96×31`, PTY resize `123×45`, transport closed, cleanup callbacks drained, frame destroyed, event loop exited, exit code 0. No firewall rule, real cluster, or real Slurm job was used.
- `wx_jobs.py` now measures 3,010 LOC. The broad Windows Jobs/storage/provider regression set passed `238 tests`; full `ruff check .` and `git diff --check` passed. The larger historical full release suite was not rerun after this small leaf-module extraction; its previous result remains historical evidence, not a claim about this exact worktree state.

## Final modularization and VM acceptance addendum (2026-10-20)

- The worktree started from `76520aa2eb1b0ebb539ffb42d637e6821b075942` on `codex/jobs-workspace-recovery`. The modularization was committed as `90876b1aa2d9eb02f930dde5f9735d58f2902aec`; guest-fixture and virtual terminal harness changes were committed as `abb214c780796f42ff155a4ab427e385ff6000e1`. This evidence addendum is included in a separate documentation commit. The branch is not pushed because the project instructions prohibit pushing. `src/hpc_gui/wx_jobs.py` is now 485 physical lines. The Jobs components are split by responsibility under `src/hpc_gui/jobs/`; the shared changed-scope architecture validator checked 31 source files and passed with 0 files over 500 lines and 0 dependency errors. Four files are in the 400–500 LOC warning band. `docs/architecture/source-loc-exceptions.json` has no Jobs exception. The full-project scan still reports 50 pre-existing over-limit files outside this change.
- Kept the historical `hpc_gui.wx_jobs._parse_job_row` import as a compatibility alias to `hpc_gui.jobs.job_rows.parse_job_row`, verified by the existing W13 test after the extraction.
- `python -m ruff check .` passed. `git diff --check` passed (Git printed only its Windows LF-to-CRLF working-copy notice).
- Windows host packaged workflow: the release artifact rebuilt after restoring the `_parse_job_row` compatibility alias passed all 21 packaged smoke checks. Artifact SHA256: `e5b8a578af7b0e3338a4033c0f3f31371ccb45422fa5dd4f42040d6563a78218`.
- Windows11 packaged guest workflow: the canonical interactive runner staged that exact artifact and the isolated fixture launcher into the active `test\\home` Explorer session. Host and guest SHA256 values matched for both files; the guest loopback-only fake SSH/SFTP workflow passed all 21 checks, including Jobs roundtrip, Files/editor surfaces, reconnect identity, PTY input/resize, and clean shutdown. Runner exit code was 0, timeout was false, and staged-artifact cleanup completed. No real cluster or Slurm job was used.
- Ubuntu-Test packaged workflow: after adding the missing wx WebView binding and runtime library to the existing user-level package cache/extract tree, the Linux artifact was rebuilt after the compatibility alias change and passed all 21 packaged checks under Xvfb. SHA256: `f45dd45ac8606f3ac0d73fe6fb3d8a799e4bf6c7e8aa75e1309a3edd2671cafb`. `ldd` reported no missing shared libraries. The persistent guest wrapper uses Python 3.12.3 and wxPython 4.2.1; this differs from the Windows release wx pin.
- Ubuntu dependency repair used the user cache `/home/test/.cache/hpc-client-gui/wx-debs` and extraction root `/home/test/.local/opt/hpc-client-gui/wx`, without sudo or system package database changes. Cached packages: `python3-wxgtk-webview4.0_4.2.1+dfsg-3build2_amd64.deb` SHA256 `286426fc39d24e56cf547fed4827ff6e089538e6a7463525e2ab75be704f72e2`; `libwxgtk-webview3.2-1t64_3.2.4+dfsg-4build1_amd64.deb` SHA256 `d9bc437888476d75c14ead4b4c5fe14de8f28cde38f0c80c6d5300c2ecca5456`.
- Windows Jobs/storage/provider focused regressions passed `274 tests` before the compatibility alias was restored. After the alias change, `tests/test_w13_slurm_state.py` passed all `14` tests on both Windows and Ubuntu. On Ubuntu, 15 of 17 selected Jobs GUI/storage/provider modules passed, totaling `237 passed`; `tests/test_wx_jobs_behavior.py` and `tests/test_w28_jobs_identity_refresh.py` exited with native wxGTK `wx._core` segmentation faults when run as complete modules. All `37` collected nodes in those two modules passed across their pre-crash module results and fresh per-test processes; the remaining 10 GUI nodes were rerun separately with `10/10 PASS`. The module-level native event-loop crashes remain explicit platform-test limitations, and are not represented as module passes.
- The full repository release suite was not rerun on this final modularization worktree. The earlier `1,848 passed, 29 skipped, 61 deselected, 22 subtests passed` result remains historical and is not attributed to this source snapshot. Real Slurm submit/cancel and remote file deletion were skipped throughout.
- No plugin repository files were changed; TRUBA 1.5.0’s missing history paths remain handled by the application fallback described above. The Linux/Windows smoke evidence exercises only isolated fake loopback endpoints.

## Final Python 3.14 VM regression and build continuation (2026-10-21)

- The task worktree was on `codex/jobs-workspace-recovery` at `a091e14c9a6ccb27a329f257c7c9542b0aade592`, based on `develop` / `origin/develop` commit `b2de2bb8ccc533aa0b0ecb7dd2a798a4fcdf709a`. The original `D:\Projeler\hpc-client-gui` checkout was left untouched.
- Ubuntu-Test now has a persistent `/home/test/.venvs/hpc-client-gui-py314` environment running Python `3.14.8`, wxPython `4.3.1`, PySide6 `6.11.2`, and PyInstaller `6.22.2`. User-level Binutils `2.42` and SDL2 `2.30.0` are persisted under `/home/test/.local/opt`; no system package database change or sudo was used.
- Ubuntu full release suite ran all `169` commands and exited `1` due to `32` failures in eight non-Jobs wxGTK Files/layout modules. The same failed node set (`comm` comparison returned no differences) reproduced on a clean source archive at `a091e14` with the same Python 3.14.8/Xvfb/DBus environment. No Jobs test failed. These baseline failures are recorded as existing Linux headless-GTK test limitations, not as a pass for the whole Ubuntu suite.
- Linux PyInstaller GUI build initially reported missing SDL2. After adding the user-level SDL2 and Binutils packages, the second build completed with exit `0` and no unresolved-library warnings. The packaged GUI process remained alive for a five-second Xvfb launch smoke using an isolated scratch profile. The Python 3.14 wheel also built successfully.
- Windows 11 VM uses persistent Python `3.14.7`, wxPython `4.3.1`, PySide6 `6.11.2`, and PyInstaller `6.22.2`. GUI and CLI packages built; the packaged CLI reported version `1.5.9` on Python `3.14.7`, and the packaged GUI main window launch smoke passed in the active `test\home` session.
- Windows full release run `r2` had one transient WebView ready timeout. The same node then passed in an isolated interactive-session retry (`1 passed in 1.64s`). A clean full release rerun (`r3`) completed with exit `0`, `158` pytest invocations, `0` failures; its broad batch reported `1,877 passed, 33 skipped, 58 deselected, 22 subtests passed`. The suite emitted nonfatal wx native teardown/WebView2 warnings despite the successful exit.
- Final quality gates: changed-scope architecture validator `PASS` (`36` source files, `0` over 500 LOC, `0` dependency errors; eight files in the warning band); Ruff on changed Python files `PASS`; `git diff --check HEAD` `PASS` (only Windows LF/CRLF notices). No real Slurm job was submitted or cancelled, and no remote user file was deleted.
- No plugin repository source or package was changed. TRUBA 1.5.0’s absent history paths continue to be handled by the application’s retained-metadata fallback.
- The final shell-workspace and test-harness modularization was committed as `753db9f69eaf053a4e2bced63411543cc24d4e0c`. A post-commit-equivalent focused regression on this exact tree passed `145` tests on the Windows host; full Ruff, `compileall`, `git diff --check`, and the changed-source architecture gate also passed (`105` source files checked, `0` over 500 LOC, `0` dependency errors). The architecture gate reports 17 files in its warning band.
- The main `develop` checkout contains pre-existing unstaged edits in `src/hpc_gui/i18n/en.json`, `src/hpc_gui/i18n/tr.json`, `src/hpc_gui/services/parsers.py`, and `src/hpc_gui/wx_jobs.py`. These overlap feature paths and were left untouched. A clean integration worktree based on `origin/develop` is being prepared for the requested merge; no push is being made under the repository's explicit no-push instruction.
