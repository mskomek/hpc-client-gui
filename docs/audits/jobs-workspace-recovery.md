# Jobs Workspace Recovery audit

Date: 2026-10-19

## Decision

**Not accepted for push.** The implementation and local Windows packaged smoke are available on `codex/jobs-workspace-recovery`, but mandatory validation remains blocked by two baseline stale tests, full-suite environment/native test blockers, and unavailable Windows11 interactive Explorer access. No remote push was performed.

## Starting state

- Repository: `mskomek/hpc-client-gui`
- Starting branch: `develop`
- Starting commit: `b2de2bb8ccc533aa0b0ecb7dd2a798a4fcdf709a`
- `origin/develop` matched that commit after fetch.
- Work was performed in a separate worktree on `codex/jobs-workspace-recovery`.
- Related plugin repository was at `8cce85446a8db72ea6b89b56bcb3df8916cbb0a8`; its pre-existing untracked `.github/social-preview.jpg` was preserved.

## Root causes found

- Job history storage was keyed by bare scheduler job ID, causing collisions between profiles and clusters. The prior store primarily covered submitted jobs and did not restore complete job workspaces into the UI.
- Queue/history observations were not consistently persisted or merged with local saved jobs.
- Selected-job context omitted profile/provider identity and important path/script metadata.
- Files navigation could fall back to `/` and swallowed navigation errors; path selection logic was local to the Jobs UI.
- Output resolution did not pass known script content/path into the resolver, and output cache fallback/status was incomplete.
- Jobs list was single-select and lacked local-only bulk details deletion.
- TRUBA 1.5.0 history configuration does not request WorkDir/StdOut/StdErr. The application must retain known values and fall back safely; the plugin was not changed or assumed to support unverified fields.

## Changes made

- Replaced the job record schema with versioned SQLite workspace storage, composite profile/cluster/provider/job/component identity, v2 migration, scoped listing, non-empty field merging, bounded/redacted snapshots, and delete tombstones.
- Captured scoped submitted-job provenance and added observed-job persistence/restoration from scheduler history.
- Added a shared job directory resolver that tracks the source and does not invent `/` when no usable path is known.
- Extended selected context with scope and script/path data; preserved prior useful values when observations omit them.
- Added multi-select Jobs UI support, primary selection retention, confirmed bulk **Delete Details**, and error reporting for Files navigation. Delete removes local record data only and does not cancel jobs or remove remote files.
- Persisted raw details/accounting and output snapshots; cached output is labeled with its capture time. Passed script text and remote path to output resolution.
- Added regression tests for migration, scoped IDs, non-erasure, tombstones, redaction, path resolution, context scope, and bulk deletion.

## Validation

| Check | Result | Evidence |
|---|---|---|
| Ruff on changed Python modules/tests | PASS | `All checks passed!` |
| `git diff --check` | PASS | No whitespace errors |
| Focused Jobs/storage/provider regression | 250 PASS, 2 FAIL | `python -m pytest -q` over 16 targeted files; two failures below |
| Wave80 label checks | FAIL (baseline) | Both assert `dirs.tab_all == "All"`; unchanged application translation returns `"All files"`. These same failures were verified against pristine starting `develop`. |
| Full suite collection | BLOCKED/FAIL (baseline) | `tests/test_ssh_jump_host.py` cannot import `_KnownHostsPolicy` from `hpc_gui.ssh.client`; reproduced on pristine starting source. |
| Full suite excluding that collection error | BLOCKED | Native Windows access violation during `tests/test_editor_flow.py`; repository release harness documents isolation for this GUI test. |
| Isolated full-suite diagnostics check | FAIL (environment-induced baseline) | `HPC_GUI_CONFIG_ROOT` override redirects app log away from path expected by a test; same result on pristine source with that override. |
| Windows PyInstaller build | PASS | Built from worktree source with project spec; artifact SHA256 `b55a2de2a276552ef934bcaaffd1e45957a5187d1d7ad5178d159f13fd98090b`. |
| Packaged smoke | PASS | 21/21 checks, including Jobs, Files, output roundtrip, reconnect identity and clean shutdown. |
| Windows11 guest interactive launch | BLOCKED_ENV | Canonical runner reports: `No Explorer process is running in an interactive session.` Artifact staging/hash succeeded; no guest exit result was fabricated. |
| Live Slurm / remote destructive actions | SKIP | No real Slurm job was submitted/cancelled and no remote files were deleted. Mock/local scenarios only. |

The requested repository architecture check was searched for but no source-LOC architecture gate was found. `wx_jobs.py` was already a 3,222-line first-party file at the starting commit and remains far above the repository's 500-line policy; this implementation added UI code there. This is an unresolved architecture-policy violation and needs a cohesive extraction before acceptance.

## Plugin status

No change was made to `mskomek/hpc-client-gui-plugins`. TRUBA `1.5.0` history fields were inspected and do not include WorkDir/stdout/stderr. The application changes retain previously known paths and use safe fallback paths; a plugin version bump was not justified without validating field support.

## Remaining acceptance work

- Resolve or formally update the two stale Wave80 expectations without changing unrelated Files behavior.
- Repair/reconcile the baseline SSH test import and execute the repository's release suite in its supported partitioning; investigate the native GUI access violation.
- Extract new Jobs UI behavior from the oversized `wx_jobs.py` into cohesive modules and rerun focused regressions.
- Obtain an active Windows11 Explorer session and rerun guest GUI acceptance through the canonical interactive runner.
- After all required gates pass, push the existing local commits on `codex/jobs-workspace-recovery` and verify `origin` HEAD.

## Commits and remote

- Local commits: `72359f27`, `32aae234`, `7051a62c`, plus this audit report commit.
- Push: none; held because validation gates remain open.
- Remote feature branch URL: not published
