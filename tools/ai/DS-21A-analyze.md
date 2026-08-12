Analyze DS-21A only: map the smallest safe SlurmJob dataclass/parser addition in the service layer for existing raw squeue and sacct output.

In scope: src/truba_gui/services/slurm_base.py, slurm_mock.py, slurm_ssh.py, and focused tests.
Forbidden: remote or cluster actions, changing scheduler command policy, UI refactors, new accounts/partitions/limits, and edits.

Acceptance: recommend concrete symbols/files, preserve raw output and current return behavior, and identify representative queue/accounting fixtures. Do not edit.
