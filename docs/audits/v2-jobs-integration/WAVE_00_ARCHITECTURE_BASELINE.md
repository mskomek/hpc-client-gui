# WAVE 00 Architecture Baseline

Baseline commit: `f61919bad12be5f328cb9db3fee3c8de8563fa5b`.

The shared Agent Core validator scanned 803 project source files: 60 were in the warning range and 52 exceeded 500 physical lines. All 52 are first-party Python files. The exact list and counts are in [ARCHITECTURE_BASELINE.md](ARCHITECTURE_BASELINE.md), with machine-readable details in [ARCHITECTURE_BASELINE.json](ARCHITECTURE_BASELINE.json) and `docs/architecture/source-loc-baseline.json`.

The staged gate is implemented by `scripts/check_source_architecture.py`. It delegates LOC enforcement to shared Agent Core using `changed` scope and adds project-specific unresolved-import, cycle, and facade API checks. A full `project` scope is required after all baseline debt is removed. The CI job uses the same pinned shared Core revision and does not claim a run before GitHub Actions executes it.

The baseline contains 8 static import-cycle groups and 2 unresolved internal symbol imports. Both are pre-existing and tracked for repair in the SSH and GUI-dialog waves. Final architecture acceptance requires zero dependency errors, zero cycles, and zero files over 500 lines; the LOC baseline will then be removed while the public API contract remains.
