# Wave 03 — File Contracts and Conflict Policy

Status: waiting
Owner: Codex
Priority: P1
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Expose loss-averse upload/download conflict choices and preserve Unicode,
metadata, error, and JSON behavior from Wave 01.

## Why This Wave Exists

File transfer commands must never silently overwrite data, and Turkish paths
must behave identically in text and JSON output.

## Depends On

- Wave 01 is done
- Wave 02 is done when profile-based verification is needed

## Target Files

- `src/truba_gui/cli/files.py`
- `src/truba_gui/cli/main.py`
- narrowly justified file-service helpers
- existing file/backend test doubles
- focused CLI and file tests

## In Scope

- overwrite, skip, rename, and resume policies
- existing backend resume behavior
- Turkish file and directory names
- empty-directory and standard error outcomes

## Out of Scope

- GUI conflict dialog changes
- silent overwrite
- live transfers or production data
- redefining Wave 01 mappings

## Packets and Tasks

### DS-03A — Existing-file policy (Medium)

- [ ] Add explicit overwrite, skip, rename, and resume choices.
- [ ] Ensure rename never overwrites an existing destination.
- [ ] Report skip as a successful no-op.
- [ ] Define equivalent text/JSON outcomes.
- [ ] Test confirmation and verification behavior with fakes.

### DS-03B — Unicode and error matrix (Small)

- [ ] Exercise Turkish file and directory names in text and JSON.
- [ ] Preserve Wave 01 metadata names and exit codes.
- [ ] Treat empty directories as successful empty results.
- [ ] Cover not-found, access, and backend error cases.

## Validation

- [ ] `$env:PYTHONPATH = "src"; python -m pytest tests/test_cli.py -q`
- [ ] Relevant local file/backend tests pass.
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-03A and DS-03B.

## Done Criteria

1. Every transfer conflict has an explicit, documented outcome.
2. No path silently overwrites data.
3. Turkish names remain intact in text and JSON.
4. Error and metadata contracts match Wave 01.

## Possible Blockers

- backend resume semantics conflict with CLI policy
- profile resolution from Wave 02 is incomplete
- an allowed-path expansion would cross the packet ceiling

## Completion Notes

- Completed at:
- Packet verdicts:
- Files changed:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex marks this file done and moves it to `waves/done/` after all gates PASS.
- Stop the prompt; report Wave 04 as next but do not start it.
