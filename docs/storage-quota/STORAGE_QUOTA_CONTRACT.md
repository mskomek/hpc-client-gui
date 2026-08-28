# Storage and quota contract (Wave 01)

This is an additive contract for a future application release. It does not
change Plugin API v1 and does not change `plugins/truba/1.0.0`.

## Compatibility

`storage` is optional. A consumer must continue accepting the legacy
`paths.home_dir` and `paths.scratch_dir` fields. If both representations are
present, the storage entry is authoritative only when its `path_template`
matches the corresponding legacy path; otherwise the profile is rejected as
ambiguous. The consumer must never silently choose a different path.

Plugin API version, payload schema version, and plugin release version remain
separate values. A future profile carrying `storage` must declare the minimum
application version that implements this contract.

## Declarative profile shape

```json
{
  "storage": [{
    "id": "home", "label": "Home", "kind": "home",
    "path_template": "/arf/home/{user}", "quota_scope": "user",
    "quota_pool_id": "arf-user-storage",
    "quota_provider": {"id": "<application-allowlisted-id>", "options": {}},
    "documentation_url": "https://docs.truba.gov.tr/1-kaynaklar/arf/arf_depolama_kaynaklari.html",
    "policy_summary": "Source-backed text only."
  }]
}
```

`kind` is one of `home`, `scratch`, `project`, or `custom`. `id` is stable
within a profile and `label` is display text. `path_template` uses only the
existing safe placeholders; no plugin may supply an arbitrary command.

`quota_scope` is one of `user`, `group`, or `project`. `quota_pool_id` groups
paths that consume the same quota and prevents displaying one shared pool as
independent capacities. Capacity and inode values are normalized to
nonnegative integer bytes/counts. Missing, unlimited, and unreported limits
are represented as `null` plus status metadata, never as zero.

`quota_provider.id` is selected from an application allowlist. `options` is
provider-specific and strictly validated; an unrecognized provider or option
must be rejected. This contract intentionally defines no TRUBA command.

## Normalized runtime result

The app-owned result contains:

```text
area_id, quota_pool_id, scope, scope_identity,
used_bytes, soft_limit_bytes, hard_limit_bytes,
file_count, soft_file_limit, hard_file_limit,
grace_state, measured_at, freshness, source_status, error
```

`source_status` distinguishes `ok`, `unsupported`, `unknown`, `stale`, and
`error`; `error` is structured (`code`, safe `message`, optional `retryable`).
The result is a snapshot, not a reservation that a transfer or job will fit.

## TRUBA discovery status

The official [TRUBA storage documentation](https://docs.truba.gov.tr/1-kaynaklar/arf/arf_depolama_kaynaklari.html)
says that quota information is available after signing in to the `arf-ui1`
user interface and describes `/arf/home` and `/arf/scratch`. It does not
publish a verified read-only CLI command, machine-readable output format, or
scope/pool mapping that this app can safely parse. The page's stated quota
figures are documentation facts only, not plugin defaults.

Wave 01 is blocked for runtime provider implementation until an authorized
account verifies the exact read-only mechanism and sanitized output variants.
No live cluster connection was made.
