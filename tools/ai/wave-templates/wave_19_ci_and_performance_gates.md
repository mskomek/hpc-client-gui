# Wave 19 — Product CI Baseline

Status: waiting
Owner: Codex
Priority: P0
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Restore a trustworthy product-CI baseline before adding product features. The
normal Linux job must run application tests only, with the Qt runtime it needs.

## Evidence

- `main` retains `tests/test_runner_ollama.py` but no longer contains its
  `runner/` development-only package; full pytest collection therefore cannot
  be a product-CI gate until that test is excluded or relocated.
- `.github/workflows/ci.yml` runs the full test suite on Ubuntu without an
  explicit Qt/EGL runtime setup.
- The current workflow is a single job, so a Qt collection failure hides
  non-GUI regression results.

## Packets

### DS-19A — Exclude development-runner diagnostics from product CI (Small)

- Keep `tests/test_runner_ollama.py` available for its development-tool context,
  but ensure the product workflow never collects it when `runner/` is absent.
- Use the smallest workflow-level exclusion or a test-local conditional skip;
  do not restore the retired development runner to `main`.
- Add a deterministic check only when needed to prove the selected boundary.

Allowed: `.github/workflows/ci.yml`, `tests/test_runner_ollama.py`, and one
narrow CI/test check. Forbidden: runner implementation, application source,
new CI services, and dependency changes.

### DS-19B — Prepare the Ubuntu Qt test runtime (Small)

- Inspect the failing GitHub Actions log before choosing packages; install only
  the missing runtime libraries required for offscreen PySide6 collection.
- Preserve `QT_QPA_PLATFORM=offscreen` where it is required.
- Do not add a display server, GPU runner, or a new GUI test framework.

Allowed: `.github/workflows/ci.yml` and a narrow workflow check only. Forbidden:
application source, PySide6 workarounds, live cluster access, and packaging.

### DS-19C — Separate core and GUI CI evidence (Medium)

- Split the existing offline suite into a core/SSH-SFTP job and a GUI job only
  after DS-19A and DS-19B are green.
- Keep the existing local/mock integration tests as mandatory gates.
- Add a Windows smoke job only if it can reuse existing checks without release
  packaging; do not publish or build release artefacts in pull-request CI.

Allowed: CI workflow, existing test selection helpers, and focused CI tests.
Forbidden: release workflow changes, new hosted services, live operations, and
performance benchmarks.

## Exit Gate

The product test suite collects on Linux, runner diagnostics cannot break it,
core failures are visible independently of GUI-runtime failures, and no CI job
uses a live host or credential.

## Deferred

Performance experiments, GUI delegate rewrites, and release packaging belong to
later evidence-backed waves.

## Completion Notes

- Completed at:
- Packet verdicts:
- Files changed:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex archives this wave only through `wave-queue.ps1` after every packet
  has PASS evidence.
- Stop; report the next waiting wave but do not start it.
