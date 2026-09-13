# Test Suite Cleanup Wave — 2026-09-12

Status: COMPLETE as a governance Wave. Integration closeout on 2026-09-13 is `DEFECT_FOUND` / NOT READY TO MERGE; the authoritative release runner completed its broad child with two failures. See [the integration closeout report](TEST_SUITE_INTEGRATION_CLOSEOUT_2026-09-13.md).

Frozen baseline: `12ce79935bf076e1062c57dc7dbd148bad2bfae1`

Current packet: O

Dependency: Phase 1 test-suite audit completed

This is an executable cleanup Wave and implementation plan. The repository has no root ACTIVE_WAVE/WAVES execution system; this file does not claim to be its official active Wave ledger.

## Operating rules

- Automatic GitHub Actions CI stays disabled. Do not restore `.github/workflows/ci.yml` or add `push`/`pull_request` triggers. The manual release workflow remains `workflow_dispatch` only.
- Qt/PySide6 remains the production runtime. Keep PySide6 and shiboken6. Do not change the default GUI runtime.
- Unless a packet explicitly authorizes otherwise, do not modify `src/hpc_gui/**`, `.github/workflows/**`, migration/parity completion ledgers, protected local guidance, or `.tmp/**`.
- If a truthful test exposes a product defect, keep the failing test, do not weaken it or silently change production, mark the packet `DEFECT_FOUND`, and stop that packet.
- Call a failure pre-existing only with frozen-baseline, node, outcome/signature, and test-body evidence. Execute one packet at a time; do not broaden scope.

## Packet status

| Packet | Status | Scope / evidence |
| --- | --- | --- |
| A | DONE | Frozen baseline and inventory: `audit/archive/12ce7993/test-suite-baseline/` |
| B | DONE | Marker registry, architecture specification, actual-state REPORT checker |
| C | DONE | Exact zero-primary RATCHET and lane comparison |
| D | DONE | Seven duplicate groups and false-gate review |
| E | DONE | Weak lifecycle test rewrites |
| F | DONE | GUI truthfulness review and focused rename-selection defect remediation |
| G | DONE | Historical/Wave ownership review |
| H | DONE | Settings/config isolation; the original setup hang was corrected at the test seam |
| I | DONE | Source-text behavior review and runtime replacements |
| J | DONE | Resource/concurrency ownership and bounded-wait review |
| K | DONE | Reporting/E2E ownership review |
| L | DONE | Legacy static/migration ownership review |
| M | DONE | Two latent wx product defects fixed; actual taxonomy and six baseline exceptions reconciled |
| N | NOT APPLICABLE | Explicit local/release selectors remain clearer; no selector or workflow migration |
| O | DONE | Final mapping, closeout evidence, independent audit, and integration-readiness review |

## Packet M closeout

**Jobs output reads.** The truthful test reproduced two overlapping remote readers (`max_active_reads == 2`). The production refresh path now reserves one reader for the active job/output generation, coalesces refreshes into one pending follow-up, rejects stale results, and releases the reservation on completion, error, thread-start failure, and close. The exact overlap node and four Jobs modules pass; four focused Jobs nodes cover coalescing, follower reads, error recovery, and close.

**Plugin menu lifecycle.** The bounded lifecycle test reproduced a connected→hidden hang. The rebuild had detached a native menu item with `Remove`, then separately destroyed its submenu. It now uses `DestroyItem`, inserts submenus with `Menu.Insert(..., submenu)`, and unbinds tracked dynamic handlers before rebuilding. The existing test checks 25 transitions, Unicode labels, ordering, hide/disable behavior, separators, duplicate roots, and teardown; it passes twice in isolation. Plugin contribution/menu coverage passes.

The seven required wx resource modules ran sequentially in one pytest process: **52 passed**, with no `UnregisterClass` or open-window teardown warning. See the detailed chronology and command evidence in [`PHASE_2_EXECUTION_REPORT.md`](PHASE_2_EXECUTION_REPORT.md).

Actual REPORT snapshot `6cad198dca6c0f69bc8196f5030a7aebcba9d696`: **2,656** collected; unit 760, integration 362, gui 671, e2e 7, runtime_smoke 6, contract 566, audit 156, reporting 21, release 101; **6 zero-primary exceptions, 0 multi-primary**. The six are exactly the documented archived/supplemental baseline failures. RATCHET passes with six allowlisted nodes, zero new zero-primary, and zero multi-primary. The frozen-to-current collection comparison is 2,673→2,656: 36 current additions, 53 removed old nodeids, including 19 renamed mappings.

The official release suite was attempted with and without coverage. `pytest-cov` is installed and compile, i18n, and smoke preflight pass. The broad pytest child terminates with Windows native exit `3221226525` while entering `tests/test_jobs_outputs_scroll.py::JobsOutputsScrollTests::setUp`; that module passes by itself (20 passed, 4 subtests). A fail-fast diagnostic reproduced the archived screenshot-manifest failure at its stale-commit assertion. Neither interrupted run has authoritative full-suite totals, and no full-suite PASS is claimed. These findings remain separate from the two fixed product defects and the seven archived baseline failures.

## Packet O closeout

The final machine mapping is `audit/test-taxonomy/taxonomy-final-mapping.json`; the human summary is `docs/testing/TEST_TAXONOMY_FINAL_REPORT.md`. The independent read-only audit verdict is **PASS WITH FOLLOW-UP**. Its two documentation findings were corrected: the native process exit is reported without assigning an unsupported failure type, and the archived ratchet’s 2,654 collection count is labeled as historical snapshot metadata. The current collection and report reconcile at 2,656.

The governance branch is based on `develop` at frozen SHA `12ce79935bf076e1062c57dc7dbd148bad2bfae1`. At closeout review it is 14 commits ahead and 0 behind `origin/develop`; the governance remote was at `7a45496b4929a578db9a77b8a051e822fadc9011` before the Packet O push. The diff contains 267 test files, 3 production files (the explicitly authorized Packet F and M fixes), 6 documentation files, 13 audit files, one script, and `pyproject.toml`; no workflow, migration/parity ledger, protected guidance, CI selector, or `.tmp/` changes are included. Recommend **NOT READY TO MERGE** until a supported broad release-suite run completes; do not merge or push to `develop` in this Wave.

Wave verdict: **COMPLETE**. This records completion of the governance work and does not claim that the interrupted full suite passed.

## Evidence and history

- [`PHASE_2_EXECUTION_REPORT.md`](PHASE_2_EXECUTION_REPORT.md) — chronological packet execution and validation evidence.
- [`ZERO_PRIMARY_DISPOSITION.md`](ZERO_PRIMARY_DISPOSITION.md) — six explicit baseline-failure exceptions.
- [`TEST_ARCHITECTURE.md`](TEST_ARCHITECTURE.md) — tracked taxonomy and test-quality rules.
- [`TEST_SUITE_CLEANUP_WAVE_2026-09-12_HISTORY.md`](TEST_SUITE_CLEANUP_WAVE_2026-09-12_HISTORY.md) — preserved prior long-form Wave journal and packet candidate details.
- `audit/test-taxonomy/` — actual REPORT, zero-primary registry, and final node mapping.

Automatic GitHub Actions CI remains disabled. Packet O is complete; the broad-suite limitation and separate **NOT READY TO MERGE** recommendation remain explicit in the final report.
