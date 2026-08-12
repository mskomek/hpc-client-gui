# Wave 07 — Local Release Gates

Status: waiting
Owner: Codex
Priority: P2
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Make CLI release verification reproducible and entirely local before any
live-cluster release step is considered.

## Why This Wave Exists

Release artifacts must stop on CLI, transfer, JSON, checksum, or packaging-gate
failures and preserve exact evidence under the canonical version directory.

## Depends On

- Waves 04, 05, and 06 are under `waves/done/`
- Waves 05 and 06 provide the final CLI surface
- release layout remains `dist/releases/v<version>/`

## Target Files

- `scripts/release_smoke.ps1`
- narrowly justified `scripts/release.ps1` changes
- local transfer-test script
- production/release checklist
- script tests

## In Scope

- packaged EXE `--help`, `version`, and `doctor environment` gates
- disposable local Turkish-name transfer fixture
- placement of the existing Wave 04 smoke JSON artifact
- English checklist and new CHANGELOG test records

## Out of Scope

- DeepSeek executing the packaged EXE
- live cluster or transfer access
- version changes, publishing, deployment, signing
- overwriting an existing version
- defining a second smoke JSON schema

## Packets and Tasks

### DS-07A — Packaged-EXE CLI smoke script (Small)

- [ ] DeepSeek changes/reviews only the script diff.
- [ ] Stop artifact production on any nonzero command.
- [ ] Preserve stdout and stderr.
- [ ] Codex performs the clean build and actual EXE smoke run.

### DS-07B — Local transfer and JSON artifact gate (Medium)

- [ ] Exercise a disposable local fixture with a Turkish name.
- [ ] Validate and place the Wave 04 JSON under the version folder.
- [ ] Stop release flow on every failed gate.
- [ ] Record exact English checklist/CHANGELOG test evidence.

## Validation

- [ ] Codex observes actual packaged-EXE exit codes from a clean build.
- [ ] Local transfer fixture and Turkish-name gate pass.
- [ ] Existing Wave 04 artifact validates and lands in the canonical folder.
- [ ] Release scripts refuse overwrite and stop on failure.
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-07A and DS-07B.

## Done Criteria

1. Release verification is fully local and reproducible.
2. EXE CLI smoke and transfer gates stop on failure.
3. Required artifacts remain inside `dist/releases/v<version>/`.
4. No publication, deployment, or live operation occurs.

## Possible Blockers

- no clean Windows build environment
- an existing version folder would be overwritten
- Wave 04 artifact/schema is incomplete

## Completion Notes

- Completed at:
- Packet verdicts:
- Build and artifact paths:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex marks this file done and moves it to `waves/done/` after all gates PASS.
- Stop the prompt; report Wave 08 as next but do not start it.
