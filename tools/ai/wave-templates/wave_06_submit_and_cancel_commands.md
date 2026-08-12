# Wave 06 — Submit and Cancel Commands

Status: waiting
Owner: Codex
Priority: P1
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Add confirmation-gated submit and cancel commands through the existing
scheduler service, proven entirely with fake behavior.

## Why This Wave Exists

Mutating scheduler actions require stronger refusal, validation, logging, and
mock evidence than read-only commands.

## Depends On

- Wave 05 is under `waves/done/`
- shared jobs dispatch, output, and scheduler-service contracts are PASS

## Target Files

- `src/truba_gui/cli/`
- existing scheduler service
- focused CLI and scheduler-service tests

## In Scope

- `jobs submit SCRIPT --yes`
- `jobs cancel JOB_ID --yes`
- script-path and job-ID validation
- text/JSON results, stderr, exit codes, and redaction

## Out of Scope

- live submission or cancellation
- UI changes
- invented partition, account, constraint, or resource policy
- command composition in UI or CLI

## Packets and Tasks

### DS-06A — Submit (Medium)

- [ ] Add mandatory `--yes` confirmation.
- [ ] Prove no backend call occurs without confirmation.
- [ ] Pass the script path safely to the scheduler service.
- [ ] Test fake success, refusal, and failure in text/JSON.

### DS-06B — Cancel (Medium)

- [ ] Add mandatory `--yes` confirmation.
- [ ] Validate job IDs and reject unsafe special-character input.
- [ ] Preserve actionable diagnostics without leaking sensitive values.
- [ ] Prove no backend call occurs without confirmation.

## Validation

- [ ] Focused confirmation and input-rejection CLI tests pass.
- [ ] `$env:PYTHONPATH = "src"; python -m pytest tests/test_cli.py -q`
- [ ] `python -m unittest tests/test_slurm_ssh.py`
- [ ] Fake backend success/failure calls and arguments are asserted.
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-06A and DS-06B.

## Done Criteria

1. Both mutating commands require explicit confirmation.
2. Refusal paths never call the backend.
3. Inputs are safely passed through shared services.
4. Text/JSON and error behavior match earlier waves.

## Possible Blockers

- scheduler service cannot accept safely separated arguments
- a resource-policy decision is required
- user confirmation semantics conflict with Wave 01

## Completion Notes

- Completed at:
- Packet verdicts:
- Files changed:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex marks this file done and moves it to `waves/done/` after all gates PASS.
- Stop the prompt; report Wave 07 as next but do not start it.
