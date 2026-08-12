# WAVE_19 / DS-19C analysis

Goal: map existing event-loop and transfer performance helpers and design the smallest deterministic regression scenarios for 100, 1,000, and 10,000 queue items, burst progress, and 2 to 4 fake transfers.

In scope: existing performance helpers, focused tests, mock transfer controllers, and CI workflow only when required.

Forbidden: benchmark frameworks, real external operations, nightly comparisons, production abstractions, and unrelated refactors.

Acceptance: identify reusable code and the narrowest files to change, define deterministic counters for event-loop delay and render/update counts, and recommend broad non-flaky regression limits. Findings only; no file changes.
