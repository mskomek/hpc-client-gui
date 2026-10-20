# Jobs Workspace Recovery audit

Date: 2026-10-20

## Decision

**Jobs workspace recovery is functionally validated on Windows and Ubuntu, including persistent restore, packaged Windows smoke, and an Ubuntu packaged GUI launch.** The profile-scoped store and Jobs/Details/Files/Outputs repairs are committed locally on `codex/jobs-workspace-recovery`; the final regression/harness repairs and evidence are committed in `8a27b784` and pushed to `origin/codex/jobs-workspace-recovery`. The final full `release_test_suite.py` invocation passed after the mock-SSH lifetime fix. The Windows candidate was rebuilt from this worktree, passed 21/21 packaged smoke checks, and ran `--help` successfully in the Windows11 interactive user session with matching host/guest SHA-256. Ubuntu Jobs service/provider regressions passed. A persistent per-user Ubuntu Python/build environment was provisioned. Linux PyInstaller build, packaged CLI smoke, and Xvfb GUI launch all pass using the persistent per-user wxPython 4.2.1 environment. `wx_jobs.py` remains over 500 lines under a time-bounded, documented exception. The remaining architecture exception for the legacy Jobs UI is explicit, time-bounded, and records its migration target.

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
| Windows11 VM GUI workflow | PARTIAL / BLOCKED_ENV | Follow-up canonical interactive run staged and hash-verified the fresh build, created the main frame, and shut down cleanly. Full smoke remained FAIL because the guest was intentionally not given the isolated loopback SSH test service (`packaged smoke SSH environment is missing`); no update or real cluster was used. |
| Persistent Ubuntu toolchain | PASS | Python 3.14.8 and Python 3.12.3 venvs with release-locked runtime/test libraries (wxPython supplied separately), PyInstaller 6.22.2 and Ruff 0.15.5 live under `/home/test/.venvs/`. Official Ubuntu 24.04 `python3-wxgtk4.0` 4.2.1 plus its three wx runtime `.deb` packages are persistently cached under `/home/test/.cache/hpc-client-gui/wx-debs` and extracted under `/home/test/.local/opt/hpc-client-gui/wx`; `/home/test/.local/bin/hpc-client-gui-python312` sets Python/library paths. GNU binutils 2.42 is extracted under `/home/test/.local/opt/hpc-client-gui/binutils` with `objdump`/`objcopy` wrappers in `/home/test/.local/bin`. No sudo or system package database changes were needed. |
| Ubuntu Linux PyInstaller build | PASS | GUI-capable build using Python 3.12.3 + wxPython 4.2.1: `/tmp/jobs-workspace-recovery-4f1179d/build-wx42/dist/hpc-client-gui/hpc-client-gui`; SHA256 `c05622024c411446a33ec7e880429ce44e47f1bffa8832ea3b69a5d60ab28ce2`. `ldd` reported no missing shared libraries. |
| Ubuntu packaged CLI smoke | PASS | Built artifact `--help` returned 0 and printed the expected CLI command inventory. |
| Ubuntu GUI runtime smoke | PASS (Xvfb) | Built artifact launched `gui` under `dbus-run-session` + Xvfb and exposed the `HPC Client` 760x560 main window; safely terminated the isolated test process. wx 4.2.1 also created and showed a frame. |
| Windows GUI teardown warnings | PASS WITH WARNINGS | Some passing native wx partitions emitted WebView2 `Operation aborted` / Windows `UnregisterClass` teardown warnings; their pytest results were PASS. |
| Real Slurm and remote destructive actions | SKIP | No real Slurm job was submitted/cancelled and no remote file was deleted. |

## Architecture and plugin status

No repository-defined source-LOC architecture checker was found. `wx_jobs.py` measured 3,222 lines at the starting commit and 3,325 lines before this follow-up extraction; it now measures 3,055 lines, still exceeding the 500-line policy. The repository exception file records the current LOC, rationale, expiry (`2026-10-23`) and cohesive migration target (`src/hpc_gui/jobs/`). A full extraction remains architecture debt, but the exception is explicit and time-bounded. The plugin repository remains unchanged: TRUBA 1.5.0 history omits WorkDir/stdout/stderr, so app fallback preserves known values without claiming unsupported fields.

No change was made to `mskomek/hpc-client-gui-plugins`. TRUBA `1.5.0` history fields were inspected and do not include WorkDir/stdout/stderr; application fallback handles old packages without claiming unsupported fields.

## Known deviations and follow-up

- The 3,055-line `wx_jobs.py` still uses the repository-owned exception (expires `2026-10-23`) while cohesive extraction of the remaining panel responsibilities to `src/hpc_gui/jobs/` is pending; no other newly changed first-party file exceeds 500 lines.
- Ubuntu runtime validation used the official Ubuntu wxPython 4.2.1 package with Python 3.12.3; it differs from the 4.3.1 release-lock pin. Packaged build, GUI startup, and 158 Jobs tests passed with the distro version. Building the pinned wxPython 4.3.1 from source would require authorized admin provisioning of the missing compiler/GTK development dependencies.
- Windows11 guest CLI launch passed under `test\home` Explorer; a full GUI guest run remains blocked by the startup update modal and subsequent canonical-runner bootstrap state-file collision. The full 21/21 packaged workflow smoke passed on the Windows host.
- The feature branch was pushed after the final diff/test gates; the legacy Jobs UI exception remains time-bounded.

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
- Windows host verification on the rebuilt package: PyInstaller 6.19.0 / Python 3.12.4 build passed; packaged application smoke passed 21/21 including Jobs, Files, reconnect, and clean shutdown. Artifact SHA256 was `19b7369412d40e3a361518126424001830ca1a061b5fa39073a618c12bb6ae41`. This pre-commit artifact identifies the preceding HEAD in its embedded header; it will be rebuilt after this follow-up commit for exact revision evidence.
- Windows11 interactive VM verification: canonical runner staged the same executable with matching host/guest SHA256, verified active `test\\home` Explorer session 2, launched the GUI, observed `main_frame_created=PASS`, and observed clean shutdown. The guest smoke exited 1 because the isolated guest run was intentionally not given its test SSH server; smoke reports `packaged smoke SSH environment is missing` and leaves full workflow checks FAIL. No real cluster or startup update was used. This is GUI launch evidence, not full guest acceptance; full 21/21 Windows host smoke remains PASS.
- Ubuntu-Test verification: the changed source and tests were copied into a temporary isolated source tree; under Xvfb + D-Bus and the persistent GUI Python 3.12.3 environment, the focused Jobs/storage/provider suite passed `249 passed`. The first attempt without a null keyring backend hit Secret Service activation timeouts and was stopped by the 900-second runner limit; rerun with `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring` completed in 63.64 seconds. The extracted `test_wx_jobs.py` was then rerun against the final import ordering: `5 passed`.
- Quality gates on the follow-up diff: Ruff PASS; `git diff --check` PASS. The pre-existing full release suite result remains the recorded `1,848 passed, 29 skipped, 61 deselected, 22 subtests passed`; it was not rerun after this mechanical output-module extraction.
- Remaining acceptance limitation: a full Windows11 guest workflow replay with the bundled loopback SSH fixture has not been established. The GUI smoke output and host 21/21 result are retained separately and are not conflated.
