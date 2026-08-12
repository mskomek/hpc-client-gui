# Wave 01 — CLI Contracts and Current-State Audit

Status: waiting
Owner: Codex
Priority: P0
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Establish one verified CLI exit-code, JSON, error, timeout, and verbosity
contract before later commands expand the surface.

## Why This Wave Exists

The TODO list mixes missing behavior with features that may already exist.
Later waves must not duplicate existing work or invent incompatible contracts.

## Depends On

- no earlier wave
- `rules.md`, `AGENTS.md`, and `docs/WAVE_PLAN.md` are authoritative

## Target Files

- `TODO.md`
- `src/truba_gui/cli/`
- narrowly relevant services
- `tests/test_cli.py`
- CLI contract documentation

## In Scope

- evidence-backed TODO audit
- shared exit-code and error mapping
- text/JSON error parity
- timeout and verbosity behavior
- `files ls` and `files stat` metadata contracts

## Out of Scope

- GUI behavior
- live remote operations
- persistence-schema or release changes
- later-wave commands

## Packets and Tasks

### DS-01A — Audit unchecked items (Audit, analyze only)

- [ ] Classify every unchecked TODO as missing, partial,
  implemented-tests-missing, or complete.
- [ ] Record file and line evidence for profile selection, key paths, stdin
  sensitive input, host-key policy, timeout, verbosity, and file JSON metadata.
- [ ] Do not change TODO checkboxes without independently verified evidence.

### DS-01B — Exit-code and shared error contract (Medium)

- [ ] Obtain Codex approval for numeric exit values before delivery.
- [ ] Define success, usage/refusal, connection, operation, and timeout mappings.
- [ ] Preserve actionable stderr in text and JSON errors.
- [ ] Add focused CLI regression tests.

### DS-01C — Existing flags and file JSON completion (Medium)

- [ ] Verify already-claimed timeout and verbosity behavior first.
- [ ] Fill only evidence-backed gaps.
- [ ] Standardize size, mtime, type, and permissions metadata.
- [ ] Cover empty directory, access failure, and not-found outcomes.

## Validation

- [ ] `$env:PYTHONPATH = "src"; python -m pytest tests/test_cli.py -q`
- [ ] `python -m truba_gui --format json version`
- [ ] `python -m truba_gui doctor environment`
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-01A, DS-01B, and DS-01C.

## Done Criteria

1. The current-state audit is approved.
2. Exit-code, JSON, stderr, timeout, and verbosity contracts are documented and
   tested.
3. File metadata and standard error outcomes reuse the same contract.
4. Later waves have one stable contract to consume.

## Possible Blockers

- unresolved numeric exit-code decision
- audit evidence contradicts TODO state
- unrelated dirty-worktree changes overlap allowed files

## Completion Notes

- Completed at:
- Packet verdicts:
- Files changed:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex changes `Status` to `done` and fills Completion Notes.
- Codex moves this file to `waves/done/` only after all gates PASS.
- Stop the prompt; report Wave 02 as next but do not start it.
