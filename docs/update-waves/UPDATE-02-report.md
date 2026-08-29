# UPDATE-02 report — verification and release contract

Status: PASS for the offline verification primitives; production publication remains blocked until the owner supplies reviewed signing keys and CI signing configuration.

## Changes

- Added Ed25519 signed-metadata verification with an explicit schema and exact base64 payload bytes.
- Unknown key IDs, invalid signatures, malformed/oversized metadata, unsupported schema, duplicate artifact targets, non-HTTPS URLs, invalid size, and invalid SHA-256 values are rejected.
- Added local artifact size and digest verification.
- No private or production key was generated or committed.
- Installation and package execution are intentionally not implemented in this wave.

## Verification

- `python -m pytest -q tests/test_update_verification.py tests/test_app_updater.py` — 13 passed.
- Ruff on changed verification/updater files — passed.
- `git diff --check` — passed.

Tests use an ephemeral Ed25519 fixture key and local bytes only. No release download, package installation, signing service, or external publication was performed.

## Blockers and follow-up

- Production trust cannot be claimed without an owner-provided public-key policy, protected signing workflow, key rotation/recovery documentation, and immutable artifact publication.
- DEB metadata inspection, AppImage executable validation, bounded network staging, and macOS Sparkle authority remain subsequent implementation work.
- UPDATE-03 may proceed only after this contract is reviewed; it must use the verification primitives rather than bypassing them.
