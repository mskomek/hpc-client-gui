# Wave 22 — Product Surface Cleanup

Status: waiting
Owner: Codex
Priority: P2
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Remove misleading UI affordances after higher-priority reliability work is
complete.

## Packets

### DS-22A — Files terminology audit (Small)

- Inspect visible `FTP` labels and rename only where the actual product
  behavior is SFTP/SSH file management.
- Update Turkish and English resources and user-facing docs together.

### DS-22B — Unsupported-action cleanup (Small)

- Hide or disable menu/actions that are selectable but not implemented, with an
  actionable state where appropriate.
- Add a focused UI regression test; do not silently change supported actions.

Allowed: UI resources, affected widgets/dialogs, paired docs, and focused tests.
Forbidden: broad widget decomposition, new AI features, and unrelated styling.

## Exit gate

Every visible action either works or clearly communicates its state, and the
file-management terminology matches the actual transport.

## Deferred

AI log analysis remains low priority until transfer reliability, connection
safety, scheduler workflow, and test gates are solid.
