# AUDIT A2 — Independent implementation audit (WAVE-V2-G01 repair follow-up)

- Model: `opencode-go/muse-spark-1.3-contributor` (required model; fresh separate OpenCode execution context, not the implementation session).
- Repo: `D:\Projeler\.tmp\hpc-client-gui\v2-master-repair-20261017`, branch `codex/v2-master-repair-20261017`, HEAD `24b41444a4e68802383ba462b7c359ee9c3ef84a` (verified via `git rev-parse HEAD`).
- Source/test fingerprint recomputed with `.tmp/muse-v2-m04/fp_after.py`: **`c96b01bb35083b5449f421708266a4af997f21d908f570b3d847c7253c10f42b`** — matches `expected current source/test fingerprint` in `audit-a2-request.md`. Recomputed before static gates and again after the synchronous FILE003 run; identical both times. `git status --porcelain -- src tests` count stayed 124 (62 modified + 62 untracked) throughout; no source/test changes during this audit. Every result below is bound to this fingerprint.
- Read-only: no product source, tests, tracker, or acceptance evidence were edited. New files only under `.tmp/muse-v2-g01/` with the `audit-a2-` prefix (`audit-a2.md`, `audit-a2-file003.log/.json`, `audit-a2-test-cli.log`, `audit-a2-ruff-whole.log`, `audit-a2-compileall.log`, `audit-a2-i18n.log`, `audit-a2-arch-project.log`, `audit-a2-arch-changed.log`, `audit-a2-fingerprint-before.log`, `audit-a2-git-status.log`, `audit-a2-git-diff-stat.log`, `audit-a2-probe-*.log`). No commit/push, no packaging, no guest actions.
- Python used: `D:\Projeler\hpc-client-gui\.venv\Scripts\python.exe` = Python 3.14.0, pytest 9.1.1.

## Prior interrupted run — determined, not claimed

- On entry the prior session claimed to be "waiting on background FILE003 aggregate", but verification showed: **no `python` pytest process running, no `.tmp/muse-v2-g01/audit-a2-file003.log`, and `.tmp/file003-scoreboard/` contained only 1 stale record** (`right-click_retarget.json`) — consistent with the earlier 120 s-timeout foreground attempt plus a background job that never completed.
- This audit **does not claim that run passed**. The scoreboard dir was cleaned and the exact five-file group was **rerun synchronously to completion in the foreground** (no background job). All FILE003 evidence below comes from that fresh synchronous run.

## Commands run (raw logs under `.tmp/muse-v2-g01/`)

| # | Command | Log | Exit |
|---|---|---|---|
| 1 | `venv-python .tmp/muse-v2-m04/fp_after.py` (before + after FILE003) | `audit-a2-fingerprint-before.log` (+ shell recheck) | 0 — `c96b01bb…` both times |
| 2 | `git rev-parse HEAD / --abbrev-ref HEAD / status --short -- src tests / diff HEAD --stat -- src tests` | `audit-a2-git-status.log`, `audit-a2-git-diff-stat.log` | 0 |
| 3 | `venv-python -m pytest -q --tb=short -rfs tests/test_cli.py` (whole file, `PYTHONPATH=src`, headless env) | `audit-a2-test-cli.log` | 0 — **156 passed** in 9.58 s |
| 4 | Exact five-file FILE003 grouping, **one process, `-s`, broad release marker, canonical file ordering**: `venv-python -m pytest -q --tb=short -rfs -m "not packaging and not artifact_dependent" -s tests/test_wx_file003_final_stress.py tests/test_wx_file003_final_stress_lifecycle_races.py tests/test_wx_file003_final_stress_reconnect_invariants.py tests/test_wx_file003_final_stress_transfer_unicode.py tests/test_wx_file003_zzz_scoreboard.py` (scoreboard dir cleaned first; synchronous foreground, no xdist) | `audit-a2-file003.log`, `audit-a2-file003.json` | 0 — **11 passed** in 210.03 s pytest (215 s wall) |
| 5 | `venv-python -m ruff check src scripts tests --output-format concise` (whole tree) | `audit-a2-ruff-whole.log` | 0 — All checks passed |
| 6 | Canonical validator project scope: `venv-python D:/Projeler/.agents-core/validators/validate-source-architecture.py --root <worktree> --scope project` | `audit-a2-arch-project.log` | 0 — PASS, 974 sources, 94 warnings (400–500 LOC watch zone), **over_limit_count 0**, dependency_errors [] |
| 7 | Canonical validator changed scope: `... --scope changed --base HEAD` | `audit-a2-arch-changed.log` | 0 — PASS, 125 sources, 23 warnings, **over_limit_count 0**, dependency_errors [] |
| 8 | `venv-python -m compileall -q src/hpc_gui` | `audit-a2-compileall.log` | 0 |
| 9 | `venv-python scripts/check_i18n.py` | `audit-a2-i18n.log` | 0 — key/reference/hardcoded checks OK |
| 10 | Compat + release-selection probes (read-only imports, `release_test_suite` introspection) | `audit-a2-probe-compat.log`, `audit-a2-probe-helpers.log`, `audit-a2-probe-release.log` | 0 |

## Finding 1 — `hpc_gui.cli.main._jobs_username` compat export: FIXED

- `src/hpc_gui/cli/main.py:21` imports `_jobs_username` from `._shared`; `__all__` at lines 85–109 explicitly lists `"_jobs_username"` (line 94).
- Probe: `from hpc_gui.cli.main import _jobs_username` succeeds; `is` identical to `hpc_gui.cli._shared._jobs_username` (same object, behavior unchanged — still resolves explicit `args.username` → profile username → `""` via `effective_profile_name`/`resolve_profile`).
- The two previously failing helpers (`tests/_cli_access_settings.py:223,236`, reached via `tests/test_cli.py`) now resolve: **whole-file `tests/test_cli.py` = 156 passed, 0 failed** (Audit A had 154 passed + 2 ImportError failed). No other dropped names are imported from `cli.main` (Audit A blast-radius analysis still holds; not re-grepped here beyond the two helper sites, but the full-file pass covers it).
- Independently verified; implementer's summary not taken as evidence.

## Finding 2 — scoreboard ordering + process-boundary design: FIXED for canonical release

- **Canonical release selection** (independently introspected from `scripts/release_test_suite.py`, not from the repair note): `PYTEST_BASE = (python, -m, pytest, -q, --tb=short, -rfs, -m, "not packaging and not artifact_dependent", "tests")`; `ISOLATED_FILES`/`ISOLATED_TEST_NODES` contain **zero `file003` entries**; `build_commands` broad bulk command applies `--ignore` only to isolated files, so all FILE003 modules run in the **broad bulk single process**. No xdist in canonical commands. Marker expression in the audit FILE003 run is byte-identical to `PYTEST_BASE`'s `-m` value.
- **Ordering**: canonical pytest collection is directory-alphabetical. Sorted `tests/test_wx_file003*.py`: `…_final_stress.py` < `…_lifecycle_races.py` < `…_reconnect_invariants.py` < `…_transfer_unicode.py` < `…_wx_lifecycle.py` < `…_zzz_scoreboard.py`. The old aggregate (`test_zz_measured_invariants` inside `…_reconnect_invariants.py`) therefore ran **before** `…_transfer_unicode.py`; the extracted `tests/test_wx_file003_zzz_scoreboard.py` (`zzz` prefix, docstring states it sorts after every `…_final_stress*` contributor) runs **last**. The audit's five-file order matches this canonical order; the aggregate ran 11th/last in the fresh run.
- **Shared cross-process records**: `tests/support/test_wx_file003_final_stress_shared.py` adds `REQUIRED_STRESS_GROUPS` (9 groups), `MERGED_METRIC_KEYS`, `_scoreboard_dir()` (override `HPC_FILE003_SCOREBOARD_DIR` else `.tmp/file003-scoreboard`), `_write_scoreboard_record()`, and `_record()` now writes a JSON record per contributor. `test_wx_file003_zzz_scoreboard.py::_merged_scoreboard()` merges in-process `EXECUTED`/`METRICS` with file-backed records via MAX semantics; completeness requires the 9 file-backed groups (skips only when both empty and non-distributed). Fresh synchronous run produced **9 JSON records** (one per `_record` group); `reconnect session snapshots 20/20` appears in the printed `GUI-FILE-003 executed stress counts` via in-process `EXECUTED` (set directly at `…_reconnect_invariants.py:80`) and its `mixed_session_transfer_operations` invariant is additionally asserted locally in that module — so the one non-file-backed group is still checked in both single-process and split-process layouts (each contributor's own file snapshot also carries its process's metric values, merged by MAX).
- **Fresh synchronous result**: 10/10 group lines PASS at exact required counts (200/200, 100/100 ×2, 200/200, 200/200, 50/50, 25/25, 20/20, 100/100, 50/50); all 9 zero-invariants 0; `peak_local 1`, `peak_remote 1`, `lost_remote_mutations 0`. Counts/durations bound to fingerprint `c96b01bb…` in `audit-a2-file003.json`.
- These files are **not isolated into incompatible separate processes**: verified absent from `ISOLATED_FILES`/`ISOLATED_NODES`; audit ran them as one process per the canonical broad partition. The file-backed merge is a compatible extra that also survives hypothetical partitions; it does not split the canonical run.

## Scope limitations (not defects)

- Full `scripts/ci.py release` / portable-vs-acceptance suite was **not** rerun per the brief; this audit covers the specified `test_cli.py` whole file + exact five-file FILE003 grouping + Ruff/compileall/i18n/architecture only.
- Qt-removal readiness is a **broader separate gate, not an implementation defect in this scope**: the Qt/wx dual tree is retained by design and Audit A recorded NO-GO (148 Qt import points, P0 parity uncovered). The Qt gate was not re-run here and does not affect the G01 verdict unless this scope actually required Qt removal (it does not).
- The `…_wx_lifecycle.py` subprocess predecessor was not part of the five-file aggregate (matches `repair2-file003.json`); its absence here is by specification, not an omission.

## Verdict: PASS_WITH_OBSERVATIONS

- Both prior findings are independently fixed on fingerprint `c96b01bb35083b5449f421708266a4af997f21d908f570b3d847c7253c10f42b`: (1) `_jobs_username` compat export restored with identical behavior, `tests/test_cli.py` 156/156; (2) scoreboard extracted to `…_zzz_scoreboard.py` so it runs last in canonical order, same-process as all contributors under the canonical broad partition, with file-backed MAX-merge records preserving all behavioral assertions.
- Observations (non-blocking): (a) `reconnect session snapshots` is the one group without a file-backed record — covered by its local assert + in-process merge, acceptable for the canonical single-process run; (b) 94 project / 23 changed warnings are 400–500 LOC watch-zone files, zero over-limit; (c) Qt-removal NO-GO remains a separate program-level gate.
