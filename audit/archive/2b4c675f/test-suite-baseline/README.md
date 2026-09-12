# Governance execution evidence snapshot

Captured from `test-suite-governance-20260912-v2` at `2b4c675f31ae5aba4b1a2cf9b005b919c53be208`, before the Packet O report commit. This is not a new remediation baseline.

- Frozen audit baseline: `12ce79935bf076e1062c57dc7dbd148bad2bfae1` (2,673 nodes).
- Committed remediation baseline used by this governance branch: `54f7376f3e3e1fccd672f121e33b68d2e8df2652` (2,678 nodes).
- Governance-branch snapshot: 2,685 node IDs, zero collection errors.
- The original `develop` worktree still has uncommitted changes absent from the committed remediation baseline; see the final report. Results here describe this governance branch only.
- `taxonomy-report.json` is the marker-derived primary/qualifier inventory; `taxonomy-enforce.json` and `taxonomy-ratchet.json` preserve checker outcomes.
- `nodeids.txt` and the two delta JSON files preserve exact node IDs. No probable rename is asserted.
- `release-suite-outcomes.json` captures release suite results and manually continued selected process groups.
- `performance-report.json` combines current process durations with explicitly identified partial node timings from the frozen baseline; node-level timing summaries are not current benchmarks.

Artifact-dependent smoke and other external release evidence are not inferred from pytest reporting. See `docs/testing/TEST_SUITE_CLEANUP_FINAL_REPORT_2026-09-12.md`.
