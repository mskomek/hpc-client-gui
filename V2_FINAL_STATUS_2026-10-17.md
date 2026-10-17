# HPC Client GUI V2 — Final Status (2026-10-17)

**Verdict: V2_FAILED.** This report is for the current repair worktree. The earlier root-level acceptance, traceability and audit files are preserved as starting evidence; they describe an older base and are not current acceptance results.

## Git identity

- Branch: codex/v2-master-repair-20261017
- Validation parent HEAD: c4d4be9c349cd1abf025202b01197051ed5eca59. The report and worktree changes are being published at the user's request.
- Main checkout was not used for source edits. Its close-time Git status showed 34 entries, while the supplied starting summary reported 35; no initial status snapshot was available to explain that one-entry difference.

## Results

- **Architecture:** 43 of the 55 baseline over-limit files now meet the 500-line cap. The global validator still fails with 12 production files over limit and 0 dependency errors. The JSON manifest contains the full baseline inventory and new source/test modules. Test node mapping and split plan are in .tmp/v2-final-architecture-20261017/test-nodeid-map-wave1.json and test-split-plan-wave1.json.
- **Ruff:** ruff check src tests scripts passed. Full collection passed: 3,448 tests.
- **Targeted:** W04/runner focused suite 37/37 passed (28 W04 + 9 runner tests); focused official plugin-checkout tests 38/38 passed; the two POSIX semantic tests passed on the Ubuntu guest from the current snapshot (run with --noconftest because the project autouse fixture imports wx).
- **Release:** python scripts/ci.py release exited 3221226525. The broad pytest process terminated with a native wx teardown/access violation before emitting a summary. The runner then completed 24 isolated partitions with 163 passed tests; this does not turn the release run into PASS. Raw log: .tmp/v2-final-architecture-20261017/ci-release-current.log.
- **Wheel:** the current release invocation built .tmp/w31-package/hpc_client_gui-1.5.9-py3-none-any.whl, SHA-256 BE24AF11B20695CF8AD47E8A40AF9FA0CB075B6C5CA123964759CEB07A5376A. The current W31 artifact-content test passed separately against this exact wheel. Its source-input fingerprint is 24667ef49591eeefe18c2af3bfaeb9fe2100e498f11c456aecee4a2a092daac9 (1,070 files). The old audit and manifest hashes (1b0377… and f27c0c…) are distinct; prior wheel files and complete build metadata are unavailable, so their exact build provenance remains unresolved. The focused current run confirms 37 (28 W04 + 9 runner) passes; Audit A's 36 count is inconsistent and its raw output is unavailable.
- **Windows GUI / artifacts:** the previously recorded Windows EXE was rehashed and matches 77a82b273c97b0d6168fdd718509032a1f49d49f2e5a52e38582c5607c4f9216, but it is an older artifact and was not rebuilt for this source. No current-source Windows or Linux package was built. The requested profile create/edit/save/reopen loopback/connect/reconnect workflow was not verified. The old Pane-only UIA evidence and old EXE hash are not accepted for this source tree.
- **Audits:** previous Audit A/B are tied to an older base. No current independent Audit A/B was completed.

## Remaining blockers

The 12 source files listed in the adjacent JSON, release-run native crash, unverified exact-candidate GUI workflow, missing fresh Windows/Linux artifact acceptance, partly unresolved historical wheel provenance and absent current independent audits keep the result at **V2_FAILED**.

No PR, merge or product release was performed.
