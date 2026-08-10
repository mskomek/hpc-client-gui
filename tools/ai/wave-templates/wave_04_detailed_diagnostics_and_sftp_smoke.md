# Wave 04 — Detailed Diagnostics and SFTP Smoke

Status: waiting
Owner: Codex
Priority: P1
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Produce stage-specific connection diagnostics and deterministic local SFTP
smoke evidence without contacting a real host.

## Why This Wave Exists

Connection and transfer failures must be diagnosable by stage. The local smoke
schema must exist before release and live-cluster validation consume it.

## Depends On

- Waves 01 and 02 are under `waves/done/`
- shared error, JSON, and profile contracts are PASS

## Target Files

- `src/truba_gui/cli/`
- narrowly justified diagnostics service
- existing `FilesBackend` fake
- `tests/test_cli.py`
- one focused smoke-test file when necessary

## In Scope

- port, connection/authentication, SFTP, and checksum-tool stages
- fake-backed temporary directory, upload, list, download, checksum, cleanup
- partial-failure JSON artifacts

## Out of Scope

- live network/SFTP calls
- sensitive stores or production paths
- UI and release-script changes

## Packets and Tasks

### DS-04A — Stage-based diagnostics (Medium)

- [ ] Report each diagnostic stage independently.
- [ ] Preserve completed-stage results when another stage fails.
- [ ] Keep text and JSON stage sets identical.
- [ ] Test each stage failure using fake sessions.

### DS-04B1 — SFTP smoke command and transfer stages (Medium)

- [ ] Add the fake-backed smoke command surface.
- [ ] Create a disposable test directory.
- [ ] Exercise upload, listing, and download stages.
- [ ] Reuse existing file abstractions without live calls.

### DS-04B2 — Checksum, cleanup, and artifact contract (Small)

- [ ] Add SHA-256 comparison and optional cleanup.
- [ ] Record PASS/FAIL and actionable diagnostics per stage.
- [ ] Write the JSON artifact even after partial failure.
- [ ] Reuse DS-04B1; do not replace its command surface.

## Validation

- [ ] Fake diagnostic matrix passes for every independent stage failure.
- [ ] Fake SFTP success and per-stage failure matrices pass.
- [ ] Temporary artifacts and cleanup behavior are verified.
- [ ] `$env:PYTHONPATH = "src"; python -m pytest tests/test_cli.py -q`
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-04A, DS-04B1, and DS-04B2.

## Done Criteria

1. Diagnostics remain useful after partial failure.
2. Deterministic local smoke JSON is produced and validated.
3. No live connection or production path is used.
4. The smoke-result schema is ready for Wave 07 consumption.

## Possible Blockers

- diagnostics would require a security/provider decision
- fake backend cannot represent a required stage
- partial-failure artifact cannot be proven locally

## Completion Notes

- Completed at:
- Packet verdicts:
- Smoke schema/artifact:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex marks this file done and moves it to `waves/done/` after all gates PASS.
- Stop the prompt; report Wave 05 as next but do not start it.
