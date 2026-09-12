# Test-suite remediation baseline

- Original frozen audit SHA: `12ce79935bf076e1062c57dc7dbd148bad2bfae1` (2673 collected nodes).
- Previous remediation SHA: `54f7376f3e3e1fccd672f121e33b68d2e8df2652` (2678 collected nodes).
- New remediation baseline SHA: `87e1e709a879b52300a5eec660bfae04e700ee29` (2679 collected nodes).
- Collection errors: 0.
- Exact current node IDs: `nodeids.txt`; machine-readable metadata and node deltas: `baseline.json`.

The new base adds the five updater lifecycle/verification tests already present at the earlier remediation base, a deferred terminal-mount test, and a fail-closed packaged-smoke reporting test. It removes the old packaged-smoke gate test, which asserted PASS when no package artifact existed. The replacement is related but not equivalent: it verifies a reporting result for missing-artifact failure and does not claim packaged runtime evidence.

The deferred-mount test owns separate behavior from the embedded/detached control-parity test; no rename is asserted. Collection confirms discovery only, not test success or release readiness.
