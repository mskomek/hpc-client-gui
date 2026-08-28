# Wave 01 result — contract and TRUBA discovery

## Repositories and commits

- Application: `TrubaGUI-develop-work`, branch `codex/update-01-shared-foundation`.
- Plugins: `hpc-client-gui-plugins-work`, branch `ci/consumer-contract-hardening`.
- Starting hashes were not recorded before this wave; unrelated dirty changes
  were preserved.

## Changes

- Added `docs/storage-quota/STORAGE_QUOTA_CONTRACT.md`.
- Added `schema/storage-contract.schema.json`.
- Kept legacy profile paths and published `plugins/truba/1.0.0` unchanged.
- Recorded compatibility, allowlist, shared-pool, and unknown-vs-zero rules.

## Checks

- Application: `PYTHONPATH=src python -m pytest -q tests/test_plugin_contract.py tests/test_plugin_core.py` → **41 passed, 9 skipped**.
- Plugins: `python -m pytest -q tests/test_truba_plugin.py tests/test_compatibility.py tests/test_registry.py` → baseline fixture tests passed, but registry tests errored because pytest could not create temporary lock files under `C:\Users\mskomek\AppData\Local\Temp`.
- No live TRUBA command was executed.

## Compatibility and security

The proposal is additive and does not authorize plugin-supplied shell
commands. Provider IDs remain application-allowlisted and provider options
remain closed objects. Runtime timeouts, bounded output, control-sequence
stripping, and disconnect behavior belong to later application code.

## Verified facts and blocker

The official TRUBA storage page documents `/arf/home`, `/arf/scratch`, and
quota visibility through `arf-ui1`; it does not expose a verified CLI/output
contract. The exact quota command, output variants, and whether the areas
share a quota pool remain unverified. Runtime quota discovery is blocked
pending authorized, read-only verification.

## Handoff

Wave 02 may implement app-owned neutral models/cache/error states, but must not
implement or select a TRUBA provider until this blocker is resolved.
