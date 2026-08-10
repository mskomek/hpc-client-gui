# WAVE_19 / DS-19C implementation

Goal: add deterministic regression scenarios for transfer queue rendering and progress behavior.

Allowed file: `tests/test_transfer_performance_scenarios.py` only.

Reuse existing `TransferDialog`, `TransferActivityPanel`, `PerformanceSession`, Qt offscreen setup, fake controllers, and test seams. Cover queue sizes 100, 1,000, and 10,000 through direct bounded render paths; burst progress with deterministic counters and final publication; and 2 to 4 fake transfers with bounded completion checks. Record event-loop delay and render/update counters. Keep limits broad and deterministic. Do not drive the 10,000 case through the real worker.

Forbidden: production source changes, CI workflow changes, benchmark frameworks, external operations, new dependencies, visible strings, and unrelated refactors.

Acceptance: one focused test module, no more than 400 changed lines, tests run headlessly and remain offline. Run the focused new test plus existing performance/FTP tests and report exact outcomes. Do not stage or commit.
