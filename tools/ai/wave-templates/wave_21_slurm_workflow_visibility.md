# Wave 21 — Structured Slurm Visibility

Status: waiting
Owner: Codex
Priority: P1
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Make the active Jobs & Outputs screen use structured scheduler data while
preserving raw output for expert diagnostics.

## Evidence

- `services/slurm_models.py` already has `SlurmJob`, `parse_squeue`, and
  `parse_sacct`, but the application mounts `JobsOutputsWidget`, not the legacy
  `JobsWidget` that currently consumes `SlurmJob`.
- Default `squeue` output is presentation-oriented; default `sacct` output is
  not requested with the parser-safe `-P/-n` form.
- User-configured command templates must remain supported; a parser failure
  must leave raw output visible rather than hiding scheduler diagnostics.

## Packets

### DS-21A — Stable scheduler records and parser coverage (Medium)

- Define machine-readable default templates with an explicit delimiter and
  stable field order, while preserving existing user overrides.
- Extend `SlurmJob` only with fields directly used by the next UI packet:
  reason, nodes, CPUs, node list, and completion exit/failure information when
  the source provides them.
- Add fixture-based parser tests for empty fields, embedded delimiters, and raw
  fallback; do not contact a scheduler.

Allowed: `config/system_profile.py`, `services/slurm_models.py`, narrow Slurm
tests, and paired resources only when necessary. Forbidden: UI changes, live
commands, profiles/schema migration, or invented scheduler settings.

### DS-21B — Structured view in the active Jobs & Outputs widget (Medium)

- Feed parsed queue/accounting records into `JobsOutputsWidget` without moving
  command composition into the UI.
- Keep raw `squeue`/`sacct` text reachable in the same screen and fall back to
  it on malformed or custom output.
- Show only fields supplied by DS-21A; avoid a new job-details screen or file
  actions in this packet.

Allowed: `ui/widgets/jobs_outputs_widget.py`, focused widget tests, and both
i18n files for new visible text. Forbidden: a second job widget, remote file
actions, polling-policy changes, or broad widget decomposition.

## Exit Gate

The active screen presents reliable structured queue/accounting data, raw text
remains available, custom command output degrades safely, and all coverage is
fixture/mock based.

## Deferred

Job-linked files, clone/resubmit, and notifications need a separate workflow
wave after structured records are proven in the active UI.

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
