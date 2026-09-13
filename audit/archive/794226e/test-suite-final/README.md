# Final test-governance evidence

Captured on branch `test-suite-governance-20260912-v4` at validated test-code commit `794226e7339be439486100a859d5703967c78002`; source tree `fe1943dbf18c3fb46f8510f1c5667cb5204361ba`. The documentation closeout commit changes docs and evidence only.

- `baseline.json`: collection and provenance summary.
- `nodeids.txt`: current exact 2,649 nodeids.
- `nodeid-delta.json`: exact comparisons to frozen, remediation, and previous governance inventories.
- `semantic-taxonomy-review.json`, `taxonomy-report.json`, `taxonomy-enforce.json`: reviewed node evidence and checker outputs.
- `marker-lane-reconciliation.json`: exact existing/candidate lane node sets.
- `timing-report.json`: per-node timing and diagnostic process-group outcomes.
- `release-suite-outcomes.json`: authoritative release-runner and coverage results.

The timing report was first generated at commit `2a24d1d0b3ef4d5f91e4b46e0a92306916c18d7c`; its source tree matches the validated v4 tree byte-for-byte. It is a diagnostic sweep, not a replacement for the authoritative release-suite result.
