# Wave 02 — Profile Lifecycle and Session Security

Status: waiting
Owner: Codex; SEC-02C decisions reserved to Codex/user
Priority: P0
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Provide safe profile lifecycle, common profile selection, and fake-backed
connection testing without exposing or weakening sensitive-value handling.

## Why This Wave Exists

Every later remote command depends on one predictable profile-resolution and
session-security path. Parallel connection or sensitive-storage behavior would
create security and maintenance risk.

## Depends On

- Wave 01 is present under `waves/done/`
- Wave 01 exit/error/JSON contracts are PASS

## Target Files

- `src/truba_gui/cli/`
- `src/truba_gui/config/storage.py` only when narrowly justified
- `tests/test_cli.py`
- `tests/test_optional_ssh_credentials.py` only when justified

## In Scope

- profile create, update, list, show, delete, test
- common `--profile NAME` resolution
- existing key-path and strict/accept-new behavior
- stdin-based sensitive input and existing protected storage

## Out of Scope

- GUI profile flows
- new persistence format
- plaintext sensitive storage
- command-line sensitive values
- live connections

## Packets and Tasks

### DS-02A — Profile CRUD (Medium)

- [ ] Add create and update using existing storage helpers.
- [ ] Preserve fields omitted from an update.
- [ ] Require explicit confirmation for deletion.
- [ ] Ensure list/show never expose sensitive fields.
- [ ] Add round-trip and refusal tests.

### DS-02B1 — Profile selection and test command (Small)

- [ ] Add `profile test NAME` using fake sessions only.
- [ ] Reuse one common profile-resolution path for remote commands.
- [ ] Standardize profile-not-found behavior.
- [ ] Return equivalent PASS/FAIL text and JSON results.

### DS-02B2 — Existing key and host policy verification (Small)

- [ ] Prove existing key-path behavior with regression evidence.
- [ ] Prove strict and accept-new host-key paths without reimplementation.
- [ ] Deliver code only for a gap established by DS-01A.

### SEC-02C — Stored-secret resolution policy (Reserved, analyze/review only)

- [ ] DeepSeek performs analyze/review only against masked fixtures.
- [ ] Codex decides Windows protected-store and non-Windows behavior.
- [ ] Reject command-line sensitive values.
- [ ] Keep interactive prompting blocked until the user decides; stdin-only is
  the recommended default.

## Validation

- [ ] Fake `CLISession` profile matrix passes.
- [ ] `$env:PYTHONPATH = "src"; python -m pytest tests/test_cli.py -q`
- [ ] `python -m unittest tests/test_optional_ssh_credentials.py`
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-02A, DS-02B1, DS-02B2, and applicable SEC-02C
  analysis/review evidence.

## Done Criteria

1. Profile lifecycle and connection test behavior are mock-tested.
2. All remote commands share one profile-resolution path.
3. Logs, text, and JSON reveal no sensitive value.
4. Reserved policy decisions are explicitly recorded by Codex.

## Possible Blockers

- missing user decision on interactive sensitive input
- security-policy or persistence-format ambiguity
- Wave 01 contract not complete

## Completion Notes

- Completed at:
- Packet verdicts:
- Security decisions:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex changes `Status` to `done`, fills Completion Notes, and moves this file
  to `waves/done/`.
- Stop the prompt; report Wave 03 as next but do not start it.
