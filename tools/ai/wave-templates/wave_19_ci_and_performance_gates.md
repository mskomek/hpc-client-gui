# Wave 19 — CI and GUI Performance Gates

Status: waiting
Owner: Codex
Priority: P0
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Make regressions visible in CI and measure the transfer-freeze scenarios that
Wave 16 changes.

## Evidence

- `.github/workflows/ci.yml` currently runs compile, i18n, and a small smoke
  test but not the repository test suite.
- `tests/support/mock_ssh_server.py` and mock-cluster tests provide an offline
  integration surface.
- `core/debug_telemetry.py` and `tests/test_performance_probe.py` already cover
  event-loop/performance instrumentation.

## Packets

### DS-19A — CI test-suite gate (Small)

- Add the existing offline unit/integration suite to CI with the correct source
  path setup.
- Keep live cluster access, credentials, and platform-only release actions out
  of normal CI.
- Make failures retain useful output.

### DS-19B — Offline transfer integration gate (Small)

- Connect the existing local fake/mock transfer or SFTP harness to CI.
- Do not create a second server or invoke a real cluster.
- Cover upload, download, listing, and checksum behavior already represented by
  the harness.

### DS-19C — Event-loop performance scenarios (Medium)

- Add bounded scenarios for 100, 1,000, and 10,000 queue items, burst progress,
  and 2–4 fake transfers.
- Record event-loop delay and rendering/update counts, not network throughput.
- Avoid flaky absolute timing thresholds; use deterministic counters and broad
  regression limits.

Allowed: `.github/workflows/ci.yml`, existing performance helpers, mock tests,
and focused scripts/tests. Forbidden: benchmark frameworks, nightly FileZilla
comparison, live cluster actions, and new production abstractions.

## Exit gate

CI runs the authoritative offline suite, the existing integration harness is
gated, and transfer UI regressions have a reproducible measurement.
