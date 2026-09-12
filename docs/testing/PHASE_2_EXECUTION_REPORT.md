# Test Governance Phase 2 — Execution Report

Status: Packets A, B, and C DONE; next packet D is NOT STARTED.

- Frozen baseline: `12ce79935bf076e1062c57dc7dbd148bad2bfae1`
- Governance branch: `test-suite-governance-20260912`
- Phase B commit: `058c83bb3318ddaee85bf98ba430079a4acd4a02`
- Phase C commit: `1b792ffc`

The original checkout at `D:\Projeler\hpc-client-gui` was read-only for this work. It was on `develop` at `12ce79935bf076e1062c57dc7dbd148bad2bfae1` at task start; the final safety check showed it on `develop` at `ccfeb1b81c304b79b426b599d46ebf2b831b15fe`, still dirty. No Phase 2 paths appear in its status, and this work made no writes there. Work was done in the clean governance worktree at `D:\Projeler\hpc-client-gui-test-governance`. No push was performed.

## Packet A — frozen baseline and inventory

Frozen-baseline collection completed with exit code 0: **2,673 tests, 0 collection errors**. The full suite did not complete, so full-suite passed/failed/skipped/xfail/xpass totals and duration remain unknown.

The full-suite limitation is specific: `scripts/ci.py full` could not enter its normal pytest coverage run because `pytest-cov` was missing in the audit environment; the release runner reproducibly hung during setup at `tests/test_connection_advanced_settings.py::ParallelismSourceOfTruthTests::test_settings_dialog_has_no_global_parallelism_editor`; and seven isolated baseline failures were reproduced. These are evidence about the frozen baseline, not a complete full-suite result.

The seven known isolated baseline failures are:

- `tests/test_macos_ci.py::test_macos_ci_matrix_covers_both_native_architectures`
- `tests/test_macos_ci.py::test_macos_ci_has_no_release_upload_or_signing_step`
- `tests/test_macos_release_workflow.py::test_release_preflight_shares_the_ci_test_suite`
- `tests/test_wave9_ci_unicode_matrix.py::TestResultsVerification::test_wx_unicode_smoke_cannot_fail_open`
- `tests/test_workflow_action_pins.py::test_every_workflow_exists`
- `tests/test_wx_packaged_smoke.py::test_packaged_wx_smoke_gate_reports_critical_stages`
- `tests/test_gui_audit_screenshots.py::test_manifest_exists_and_commit_current`

The archive is [audit/archive/12ce7993/test-suite-baseline](../../audit/archive/12ce7993/test-suite-baseline/). It contains `README.md`, `baseline.json`, `nodeids.txt`, `inventory-enriched.json`, `proposed-taxonomy-heuristic.json`, `lane-inventory.json`, `duration-partial.json`, and `static-findings.json`. The baseline JSON is schema version 1 and leaves unavailable full-suite totals null.

## Packet B — taxonomy and REPORT checker

`pyproject.toml` registers these primary markers: `unit`, `integration`, `gui`, `e2e`, `runtime_smoke`, `contract`, `audit`, `reporting`, and `release`. It registers the qualifiers `semantic`, `regression`, `performance`, `resource`, `concurrency`, `slow`, `subprocess`, `windows`, `linux`, `macos`, `hardware`, `synthetic_hardware`, `license`, `acceptance`, `artifact_dependent`, `wx`, `qt`, and the existing `packaging` marker. Strict marker enforcement remains off; no existing test was mass-marked.

The tracked specifications are [TEST_ARCHITECTURE.md](TEST_ARCHITECTURE.md) and [TEST_SUITE_CLEANUP_WAVE_2026-09-12.md](TEST_SUITE_CLEANUP_WAVE_2026-09-12.md). The checker is [scripts/check_test_taxonomy.py](../../scripts/check_test_taxonomy.py), with focused tests in [tests/test_test_taxonomy_checker.py](../../tests/test_test_taxonomy_checker.py).

REPORT counts actual pytest markers; it never assigns a primary by filename or heuristic. At Packet B, collection was 2,682: 9 `audit`, 2,673 zero-primary, and 0 multi-primary. The other eight primary categories were 0. The only nonzero qualifier was `packaging` at 2; other qualifier counts were 0. Phase 1 proposed taxonomy remained a heuristic proposal, not marker truth.

## Packet C — ratchet and lane comparison

The local RATCHET mode compares actual marker state against [taxonomy-ratchet.json](../../audit/archive/12ce7993/test-suite-baseline/taxonomy-ratchet.json), captured at the Phase B commit. It allows only the exact 2,673 baseline zero-primary nodeids and fails on any new zero-primary nodeid or any multi-primary item. A legacy nodeid must be removed from the allowlist when that node is classified. REPORT remains non-gating, and RATCHET is not wired into CI.

The selector comparison is [lane-comparison-phase2.json](../../audit/archive/12ce7993/test-suite-baseline/lane-comparison-phase2.json). It applies recorded file and marker selectors to pytest collection records and their actual markers. All frozen lane counts reproduced. Current broad release selectors collect 2,682 nodes: 2,671 frozen non-packaging nodes plus 11 checker audit tests. The explicit CI and archived lanes retain their frozen counts, including 54 nodes in each release macOS architecture list.

| Selector | Frozen | Current | Zero-primary | Audit |
| --- | ---: | ---: | ---: | ---: |
| `scripts/ci.py packaging` | 1 | 1 | 1 | 0 |
| `scripts/ci.py compat` | 202 | 202 | 202 | 0 |
| `scripts/ci.py cli` | 164 | 164 | 164 | 0 |
| `scripts/ci.py ssh` | 45 | 45 | 45 | 0 |
| `scripts/ci.py windows` pytest selector | 6 | 6 | 6 | 0 |
| `scripts/ci.py macos` | 55 | 55 | 55 | 0 |
| `scripts/ci.py contract` | 10 | 10 | 10 | 0 |
| shared release suite; workflow Linux/Windows; archived GUI | 2,671 | 2,682 | 2,671 | 11 |
| release workflow macOS arm64 / x86_64 | 54 / 54 | 54 / 54 | 54 / 54 | 0 |
| archived CI compat / cli / ssh_sftp | 286 / 164 / 45 | same | same | 0 |
| archived CI macos / windows / contract / packaging / wx-smoke | 69 / 41 / 10 / 1 / 59 | same | same | 0 |

The active release workflow is `workflow_dispatch` only. Its pytest job union leaves two packaging-marked nodes uncovered: `tests/test_wheel_packaging.py::test_built_wheel_contains_required_assets` and `tests/test_wx_packaged_smoke.py::test_packaged_wx_smoke_gate_reports_critical_stages`. The local `scripts/ci.py` selector union plus the shared release suite leaves the wx packaged smoke node uncovered. The Windows lane also invokes `unittest discover`; those commands are outside this pytest nodeid comparison. No CI files or selectors were changed. Automatic PR/push CI remains absent.

## Validation and current state

- `python -m pytest tests/test_test_taxonomy_checker.py -q` — **11 passed**.
- `python scripts/check_test_taxonomy.py --mode report --json-out <path>` — **exit 0**; current state is 2,684 collected, 11 `audit`, 2,673 zero-primary, 0 multi-primary; `packaging` qualifier count 2.
- `python scripts/check_test_taxonomy.py --mode ratchet --baseline audit/archive/12ce7993/test-suite-baseline/taxonomy-ratchet.json --json-out <path>` — **exit 0, RATCHET PASS**; 0 new zero-primary, 0 multi-primary.
- `python -m pytest tests --collect-only -q` — **exit 0, 2,684 collected**.
- Node comparison to the frozen inventory — **11 added, 0 removed**. Every added node is in `tests/test_test_taxonomy_checker.py`; all have the `audit` primary.
- `python -m ruff check scripts/check_test_taxonomy.py tests/test_test_taxonomy_checker.py` — **passed**.
- `git diff --check` — **passed**.
- Full-suite execution remains incomplete for the Packet A reasons above. The seven isolated failures and the settings-dialog setup hang remain intentionally untouched.

No production files, CI workflow files/selectors, migration completion ledgers, or protected local guidance files changed. Packets D–O remain NOT STARTED. A Google Docs copy was not created: the Drive connector rejected create calls for missing OAuth scopes, and browser access was denied because the admin-enforced security check could not be verified. This tracked report is the current updateable copy until Docs access is restored.
