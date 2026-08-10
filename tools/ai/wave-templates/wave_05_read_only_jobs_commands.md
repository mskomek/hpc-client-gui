# Wave 05 — Read-Only Jobs Commands

Status: waiting
Owner: Codex
Priority: P1
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Deliver the complete read-only jobs CLI through the existing scheduler service
with structured text/JSON output and preserved remote diagnostics.

## Why This Wave Exists

Read-only scheduler behavior must be stable and mock-proven before submit or
cancel is exposed.

## Depends On

- Waves 01 and 02 are done
- the shared scheduler service is available

## Target Files

- `src/truba_gui/cli/`
- `src/truba_gui/__main__.py` for top-level jobs dispatch
- narrowly justified parser/service helpers
- `tests/test_cli.py`
- `tests/test_slurm_ssh.py`

## In Scope

- `jobs list`, `jobs status`, `jobs accounting`, `jobs lssrv`
- shared job record parser and output helper
- text/JSON parity, stderr, and remote exit codes

## Out of Scope

- Jobs UI
- live cluster access
- submit/cancel behavior
- CLI-side remote command composition
- new scheduler provider or resource policy

## Packets and Tasks

### DS-05A1 — Dispatch and shared output foundation (Small)

- [ ] Add top-level jobs dispatch.
- [ ] Establish shared parsing and text/JSON/stderr helpers.
- [ ] Keep remote command composition inside the scheduler service.

### DS-05A2 — List and status (Medium)

- [ ] Implement list and status using DS-05A1.
- [ ] Assert mock calls and arguments.
- [ ] Test help, text, JSON, stderr, and error outcomes.

### DS-05B — Accounting and lssrv (Medium)

- [ ] Implement accounting and lssrv through the same foundation.
- [ ] Avoid duplicating service parsing or command composition.
- [ ] Complete the four-command read-only matrix.

## Validation

- [ ] `$env:PYTHONPATH = "src"; python -m pytest tests/test_cli.py -q`
- [ ] `python -m unittest tests/test_slurm_ssh.py`
- [ ] Mock commands and arguments match service contracts.
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-05A1, DS-05A2, and DS-05B.

## Done Criteria

1. All four read-only commands have help, text/JSON, and error tests.
2. CLI handlers remain thin and reuse one output foundation.
3. Remote stderr and exit codes remain visible.
4. No mutating or live scheduler operation occurs.

## Possible Blockers

- scheduler service lacks a mockable operation
- a parser contract requires an architecture decision
- Wave 01 error/JSON contract regression

## Completion Notes

- Completed at:
- Packet verdicts:
- Files changed:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex marks this file done and moves it to `waves/done/` after all gates PASS.
- Stop the prompt; report Wave 06 as next but do not start it.
