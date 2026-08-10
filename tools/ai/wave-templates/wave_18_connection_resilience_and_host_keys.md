# Wave 18 — Connection Resilience and Host-Key Safety

Status: waiting
Owner: Codex; host-key policy decisions reserved to Codex/user
Priority: P1
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Improve long-session reliability and key compatibility while making host-key
trust behavior explicit and persistent.

## Evidence

- `ssh/client.py` uses `AutoAddPolicy()` for `accept-new` and does not set an
  explicit transport keepalive.
- Key-path loading is limited to `RSAKey.from_private_key_file()`.
- Timeout knobs already exist and must not be replaced by a parallel connection
  implementation.

## Packets

### DS-18A — Keepalive and profile-scoped connection knobs (Small)

- Add a bounded keepalive setting through the existing connection/profile path.
- Preserve current timeout defaults and fake-client observability.
- Test transport configuration without opening a real connection.

### SEC-18B — Host-key trust lifecycle (Reserved)

- First define the user-visible policy: trust/save, trust once, and cancel.
- Use Paramiko known-hosts support for persistent verification.
- Warn on a changed key and never silently downgrade strict verification.
- Codex owns policy, migration, and any UI/i18n changes; DeepSeek may only
  analyze or review masked fixtures.

### DS-18C — Multi-format private-key loading (Small)

- Reuse Paramiko’s supported key loaders or a minimal existing helper for RSA,
  Ed25519, and ECDSA keys.
- Preserve agent and password fallback behavior.
- Test key selection with fake files and no credential material.

Allowed: `src/truba_gui/ssh/client.py`, connection config models, and focused
tests. Forbidden: live connections, credential-store inspection, protocol
rewrites, and unrelated UI refactors.

## Exit gate

Keepalive is mock-observable, supported key formats load through one path, and
host-key behavior is documented and tested without real network access.

## Deferred

Profile-specific tuning beyond the minimum connection contract is deferred
until multiple real profile requirements are evidenced.

## Completion Notes
