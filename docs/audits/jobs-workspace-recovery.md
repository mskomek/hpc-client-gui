# Jobs Workspace Recovery audit

Date: 2026-10-20

## Decision

**Not accepted for push.** The profile-scoped store, Jobs/Details/Files/Outputs repairs and regression additions are committed locally on `codex/jobs-workspace-recovery`. The required release suite still stops on a native Windows wx access violation in its combined process, `wx_jobs.py` remains over the repository's 500-line source limit, and the Windows11 interactive runner reports that no Explorer process exists in the guest session. No push was made.

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

## Validation

| Check | Result | Evidence |
|---|---|---|
| Ruff over `src scripts tests` | PASS | `All checks passed!` |
| Compile, i18n and headless smoke preflight | PASS | Release harness compileall, `check_i18n.py`, and `smoke_test.py` all passed. |
| Focused Jobs/storage/provider/SSH/Files/wire regression | PASS | 283 passed in 303.16s. |
| Release harness combined pytest partition | FAIL / BLOCKED | The latest full run again terminated its combined Windows pytest process with native access violation `0xC000041D` at about 25% progress. `test_performance_probe.py` passed 3/3 when run alone and is now isolated in the release harness, but the broad run still crashes elsewhere. The subsequent isolated `test_wx_shell_p0_stress_real_wx_paths` did not complete within the observed run and was interrupted; it is not counted as a pass. Earlier crash sites (`jobs_outputs_scroll`, `local_dir_panel`, `lssrv_auto_refresh`) passed when isolated and remain separate harness boundaries. |
| Release harness evidence-gated W04 tests | BLOCKED | `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md` is absent, so four repository-defined evidence tests are not run. |
| Windows PyInstaller build | PASS | Project spec build succeeded. Artifact SHA256 `edad31f7c65cc2fe29dadb40b0b8b085d3bf623790281dd9dfa9c29c01b71098`; built from HEAD `2de6fc065fc3e617d5186b6c20d21750aafece9f` plus the then-uncommitted fixes. |
| Packaged smoke | PASS | Retry passed 21/21 checks, including Jobs, Files, output roundtrip, reconnect identity and clean shutdown. The first run had a transient Turkish keyboard-layout input mismatch and failed; the repeat passed. |
| Windows11 guest interactive launch | BLOCKED_ENV | Canonical runner returned: `No Explorer process is running in an interactive session.` Host staging/hash completed on the earlier attempt; no guest GUI success was claimed. |
| Real Slurm and remote destructive actions | SKIP | No real job was submitted/cancelled and no remote file was deleted. |

## Architecture and plugin status

No repository-defined source-LOC architecture checker was found. `wx_jobs.py` measured 3,222 lines at the starting commit and 3,325 lines in the current worktree, exceeding the 500-line policy. This change added UI code to that module; the required cohesive extraction is unresolved and blocks acceptance.

No change was made to `mskomek/hpc-client-gui-plugins`. TRUBA `1.5.0` history fields were inspected and do not include WorkDir/stdout/stderr; application fallback handles old packages without claiming unsupported fields.

## Remaining acceptance work

- Split the oversized Jobs UI by cohesive responsibility and bring first-party source files within policy (or add a repository-owned, time-bounded migration exception with LOC and target).
- Rerun the full repository release harness after the final native GUI isolation changes and confirm all other partitions.
- Obtain an active Windows11 Explorer session and rerun guest acceptance with the canonical interactive runner.
- Once all gates pass, push the existing local commits to `origin/codex/jobs-workspace-recovery` and verify the remote HEAD.

## Local commits

- `72359f27` — profile-scoped workspace records
- `32aae234` — workspace restoration and safe details deletion
- `7051a62c` — persistence and path recovery tests
- `2de6fc06` — initial audit record
- `cd780e09` — SSH jump failure/settings contracts
- `a043d8d5` — snapshot secret redaction
- `f119e2e7` — wx isolation and regression fixture updates
- Windows performance probe isolation and audit update (this commit)

Push: none; validation gates remain open. No remote feature URL exists yet.
