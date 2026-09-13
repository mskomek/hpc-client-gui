# Test-suite remediation baseline

- Original frozen audit SHA: `12ce79935bf076e1062c57dc7dbd148bad2bfae1` — 2,673 nodes.
- Previous committed remediation SHA: `54f7376f3e3e1fccd672f121e33b68d2e8df2652` — 2,678 nodes.
- Intermediate reconciled remediation SHA: `87e1e709a879b52300a5eec660cbfae04e700ee29` — 2,679 nodes.
- New remediation base SHA: `1de2dce3aa8af037033882b26029fb33f39f9f57` — 2,679 nodes, 0 collection errors.
- Governance snapshot previously reported: `2b4c675f31ae5aba4b1a2cf9b005b919c53be208` — 2,685 nodes.

The `87e1e709` and `1de2dce3` node lists are identical. The new commit removes two resolved non-strict WebView xfail annotations; collection does not change. An earlier summary field gave 2,678 for the intermediate baseline, but its archived node list and fresh collection both contain 2,679.

Compared with the frozen audit, this baseline has seven added nodeids and one removed nodeid (net +6). The packaged-smoke reporting node was changed to a fail-closed missing-artifact check; that is not equivalent evidence of packaged runtime. The embedded terminal shared-implementation owner remains; a separate dirty-tree controls test was not treated as a rename or replacement.

Exact collected nodeids: `nodeids.txt`. Full machine-readable counts, deltas, and behavior mapping: `baseline.json`. Collection verifies discovery only, not test success or release readiness.
