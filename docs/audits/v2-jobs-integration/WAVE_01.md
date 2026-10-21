# WAVE 01 — Jobs Persistence and History

Status: **WAVE_COMPLETE** on the isolated integration branch.

## Source identity

- Integration start: `179fb47dfc94765cbec5d9eb058ba0d0f6247232`.
- Integration source commit: `c1d8e66f5b5b4a06abcf79511c48bf97017df0cf` (`feat(jobs): integrate profile-scoped persistent workspace records`).
- Integration source tree: `fb33231d4639cc9af45d642c062e716ee524f324`.
- Jobs source branch: `codex/jobs-workspace-recovery-merge` at `713949fb752b90601e007812ebf2bd765da5ad52`.
- Selected Jobs source commits: `72359f2788f7c598904e4f35837f081ed60503de`, `32aae234c3360172cc1d40592f3e7427912384eb` (selected context test only), `7051a62c516b921d21030391f06621bd0e04bd3e`, and `a043d8d59bd5cec717b103c6f959a37abd7e7cba`.
- Integrated-source fingerprint (11 sorted Python paths and file SHA-256 values): `3f6fc206a44fed61fa8b53636f32444d4e76db417b34ed95677a1f6f4bbc6b74`.

## Scope and line counts

| File | Start | End |
|---|---:|---:|
| `src/hpc_gui/services/job_record_store.py` | 108 | 262 |
| `src/hpc_gui/services/job_paths.py` | 0 | 37 |
| `src/hpc_gui/services/job_provenance.py` | 25 | 34 |
| `src/hpc_gui/services/job_security.py` | 0 | 24 |
| `src/hpc_gui/services/jobs_history.py` | 135 | 137 |
| `src/hpc_gui/services/selected_job_context.py` | 190 | 214 |
| `tests/test_job_record_store.py` | 29 | 123 |
| `tests/test_job_paths.py` | 0 | 20 |
| `tests/test_job_provenance.py` | 25 | 46 |
| `tests/test_jobs_history.py` | 91 | 93 |
| `tests/test_selected_job_context.py` | 228 | 238 |

Two application modules and one test module were added. All 11 changed Python files remain at or below 500 lines. The inventory is now 782 Python files; the 52 pre-existing over-limit files remain unchanged in count.

## Behavior carried forward

- Workspace rows are keyed by profile, cluster, provider, scheduler job ID, and component.
- The v2 SQLite `job_records` schema migrates to v4 while preserving submitted script, resources, paths, timing, state, and exit data. Corrupt databases are moved to a timestamped backup before a fresh store is created.
- Empty observations preserve last-known paths/details; deleted detail identities are tombstoned so ordinary observations do not recreate them. Explicit submitted records can recreate their identity.
- Stored scripts and output snapshots redact sensitive assignments; snapshots are bounded and can be reopened after restart.
- Directory provenance prefers verified workdir data and marks submit/cache/output-parent fallbacks as unverified.
- Selected job state now includes profile/cluster/provider identity, preventing same-ID jobs from different profiles from sharing enrichment state.
- Accounting history identifies the source of a recovered work directory.

## Verification on the integration source

- `python -m pytest tests/test_job_record_store.py tests/test_job_paths.py tests/test_job_provenance.py tests/test_jobs_history.py tests/test_selected_job_context.py -q` — **45 passed, 0 failed, 0 skipped**, exit 0, on source commit `c1d8e66f5b5b4a06abcf79511c48bf97017df0cf`.
- `python -m ruff check` over the 11 changed files — passed, exit 0.
- `python -m compileall -q` over the six service modules — passed, exit 0.
- `python scripts/check_source_architecture.py --mode gate --base 179fb47dfc94765cbec5d9eb058ba0d0f6247232` — passed, exit 0; no new LOC, import, cycle, or facade-contract errors.
- Full project architecture check — **FAIL, exit 1**, as required by existing debt: 52 over-limit files, 2 unresolved internal symbols, 8 dependency cycles, 0 public API errors. The full report is `.tmp/source-architecture-wave01-full.json` and is not a committed test artifact.
- An initial exploratory run selected the Jobs branch’s later test-only patch that targets `hpc_gui.wx_shell_jobs_history`, a module introduced by its Wave 02 extraction. That run had 44 passes and 1 source-incompatible failure. Commit `753db9f69eaf053a4e2bced63411543cc24d4e0c` owns that test rewrite; it was excluded from Wave 01, the pre-extraction test was retained, and two workdir-provenance assertions were added. The final suite then passed 45/45.
- GitHub Actions, native GUI acceptance, and Linux/Ubuntu acceptance were not run.

## Protected behavior and remaining checks

The focused tests cover legacy v2 migration using a synthetic database, scoped identity, output/detail persistence, tombstone behavior, secret redaction, path fallback, history parsing, and selected-profile identity. Multi-row UI deletion, finished-job Details/Files/Outputs restoration, refresh/reconnect, and wx event lifecycle remain for Wave 02. No live Slurm job or remote file operation was performed.

## Integration state

Wave 01 is committed on `codex/integration/v2-jobs-staged-20261021`. Local `develop` remains unchanged because it is checked out in another worktree. No push or remote mutation occurred.
