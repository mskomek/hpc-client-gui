# Wave 09 — Live-Cluster Release Verification

Status: blocked — explicit user authorization required
Owner: User and Codex
Priority: blocked until authorized
Execution: sequential, one prompt invocation; no automatic start
DeepSeek authority: analysis/review of sanitized evidence only; no delivery or execution
Timeouts: determined by Codex only after authorization

## Goal

Verify the final release against an isolated least-privilege SFTP test account
without exposing production data or sensitive values.

## Why This Wave Exists

Mock and local gates cannot prove live-cluster transfer behavior. This wave is a
human-authorized evidence exercise, not an automatic DeepSeek delivery wave.

## Depends On

- Waves 04, 07, and 08 are under `waves/done/`
- target host, dedicated account owner, isolated directory, cleanup policy, and
  permitted commands are explicitly approved by the user
- production data is provably out of scope

## Target Files

- sanitized release JSON evidence
- release checklist
- new English CHANGELOG test record
- no credential, key, token, or authentication-store file

## In Scope After Explicit Authorization

- provision or obtain a dedicated release-test account through its owner
- verify least privilege and production-data isolation
- authorized upload, download, directory, and checksum checks
- cleanup verification and sanitized evidence recording

## Out of Scope

- automatic start from Wave 08
- DeepSeek executing SSH, SFTP, Slurm, transfer, or credential operations
- production directories or data
- sensitive values in prompts, logs, JSON, checklist, or CHANGELOG
- deployment or publication unless separately authorized

## Authorization and Tasks

### LIVE-09 — User/Codex execution only

- [ ] Record explicit user authorization and exact allowed target/scope.
- [ ] Confirm the test account cannot reach production data.
- [ ] Confirm the disposable directory and cleanup policy.
- [ ] Execute only the approved upload, download, directory, and checksum checks.
- [ ] Record every operation, exit status, checksum, and cleanup result.
- [ ] Store only sanitized English evidence.
- [ ] Block release on any failure or incomplete cleanup.

## Validation

- [ ] Explicit authorization evidence exists.
- [ ] Least privilege and isolation are demonstrated.
- [ ] All approved operations and cleanup have observed results.
- [ ] No sensitive value appears in artifacts or logs.
- [ ] Release JSON/checklist/CHANGELOG records agree.
- [ ] Codex independently verifies the complete evidence set.

## Done Criteria

1. The user explicitly authorized the exact live scope.
2. The account and directory are isolated from production data.
3. Every authorized transfer/checksum and cleanup operation is recorded.
4. Failure blocks release and no sensitive value is retained.

## Possible Blockers

- missing user authorization
- no dedicated least-privilege account
- isolation or cleanup cannot be proven
- any requested action exceeds the approved scope

## Blocked Session Notes

- This file must remain under `waves/waiting/` while authorization is absent.
- Source inspection, mocks, or local smoke tests cannot close this wave.
- DeepSeek must return BLOCKED and must not attempt live operations.

## Completion Notes

- Authorized by / at:
- Exact approved scope:
- Evidence paths:
- Operations and exit codes:
- Cleanup result:
- Remaining uncertainty:

## On Completion

- Only Codex may change `Status` to `done` and move this file to `waves/done/`.
- Do not archive it without explicit authorization and complete live evidence.
- Stop after archival; there is no next wave.
