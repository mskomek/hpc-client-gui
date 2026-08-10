# Wave 21 — Structured Slurm Visibility and HPC Workflow

Status: waiting
Owner: Codex
Priority: P1
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Make the core upload → submit → monitor → results flow easier to use without
removing raw scheduler output or changing command policy.

## Evidence

- `services/slurm_base.py`, `slurm_ssh.py`, and `slurm_mock.py` currently expose
  raw text for queue/accounting/server queries.
- `ui/widgets/jobs_widget.py` renders the raw queue text directly.
- Existing script/template and editor flows already cover much of job creation.

## Packets

### DS-21A — Parse-once structured job model (Medium)

- Add a small `SlurmJob` model and parser in the service layer.
- Keep raw output available and preserve current command/error behavior.
- Use mock output fixtures for queue and accounting variants.

### DS-21B — Job-linked file actions (Medium)

- Add or improve direct access to script, `.out`, `.err`, and result directory
  using existing file-panel/editor actions.
- Keep UI handlers thin and all remote path/command construction explicit.
- Cover unavailable/missing output files with actionable errors.

### DS-21C — Clone/resubmit (Medium)

- Reuse the existing editor and submit flow: open a prior script, allow edits,
  then require the existing confirmation before resubmission.
- Do not create a second template system or invent scheduler parameters.

Allowed: Slurm services/models/parsers, jobs UI, existing editor/file actions,
mock tests, and paired i18n files if visible strings are needed. Forbidden:
live scheduler calls, new partitions/accounts/limits, and broad UI splitting.

## Exit gate

Structured job data powers a useful view while raw output remains available,
related files are one action away, and resubmission reuses existing safety
gates.
