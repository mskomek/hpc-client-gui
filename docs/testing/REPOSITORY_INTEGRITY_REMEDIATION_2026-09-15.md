# Repository-integrity remediation — 2026-09-15

Closes the three governance gaps left by the previous audit. No release, tag,
published artifact, or `main` merge was created.

| Gap | Verdict |
| --- | --- |
| Application ignores registry `compatibility_override` | **PASS** — fixed |
| Publication ledger protects only what it lists | **PASS** — fixed |
| Consumer contract is not a required `main` status check | **PASS** — fixed |

Starting state: application `develop` `578bc103`, plugin `develop` `9880283f`,
both verified against their remotes before any change.

---

## 1. Application — `compatibility_override` end to end

### The defect

The registry can correct a compatibility decision without touching an
immutable published package's bytes. The plugin repository understood the
field; the application resolver still read raw `entry["requires_app"]`. A
correction therefore looked applied and did nothing at runtime — the worst
possible state, because it hides the problem it claims to fix.

### One source of truth

`src/hpc_gui/plugins/compatibility.py`:

| Function | Contract |
| --- | --- |
| `effective_requires_app(entry)` | The published range when there is no override, the override's range when it is valid, `None` when the entry or override is malformed. |
| `entry_is_app_compatible(entry, app_version)` | The single registry-level "may this release be offered this entry?" answer. Fail-closed: `None` never falls back to the wider published range. |
| `validate_compatibility_override(entry)` | Structure, range syntax, non-empty `reason`, ISO `recorded`, unknown keys, and the narrowing rule. |

Supporting: `maximum_admitted_version()` mirrors the existing
`minimum_admitted_version()` so a raised ceiling is caught as widening too.

### Narrowing only

An override may raise the floor; it may never admit anything the published
range rejects.

| Published | Override | Result |
| --- | --- | --- |
| `>=1.5.9` | `>=1.6.0` | valid, effective `>=1.6.0` |
| `>=1.5.9` | `>=1.5.8` | **rejected** (lower floor) |
| `>=1.5.0,<1.6.0` | `>=1.5.0,<2.0.0` | **rejected** (raised ceiling) |

The application validates this itself in `validate_registry_dict`. A separate
repository is a separate trust boundary: the registry's own validation is
never taken on trust, and this runs on the cached-registry path too, so a
poisoned cache file cannot smuggle a widening override in.

### Call-site classification

Every registry-level decision goes through `entry_is_app_compatible`:

| Site | Decision |
| --- | --- |
| `registry_client.find_registry_entry` | discovery and latest-compatible resolution |
| `plugin_manager_dialog` — best-version pool | offerability |
| `plugin_manager_dialog` — entry card | Install button enable/disable |
| `plugin_manager_dialog` — update scan | upgrade candidate selection |
| `plugin_manager_dialog` — detail lines | displays the **effective** range |

Deliberately still raw, and why:

| Site | Why raw |
| --- | --- |
| `installer.py` (`manifest.requires_app`) | The downloaded immutable manifest is the installer's authority. A registry that claims an older floor must not make a package installable. |
| `loader.py` (`manifest.requires_app`) | Same authority, applied to what is already on disk. |
| `validator.py` manifest branch | Validates the manifest's own declared field. |
| `validator.py` registry branch, line 578 | Validates the **published** field's syntax on its own; an override never excuses an invalid published range. |
| `compatibility.py` internals | This is where the rule is defined. |

A read-only grep for `entry["requires_app"]` / `entry.get("requires_app")` in
`src/hpc_gui/` after the change returns only those last two rows.

### Layering

```
registry effective compatibility  ->  discovery / offerability
        -> download immutable manifest
        -> manifest validation            (authoritative)
        -> schema capability validation   (independent, fail-closed)
        -> installation
```

An override narrows availability. It can never widen what installs.

### Tests

`tests/test_plugin_compatibility_override.py` — **19 passed**. Drives the
production resolver, not a standalone helper:

- no override: resolution byte-for-byte as before; an absent field is not an
  error;
- narrowing override: `find_registry_entry` gives 1.3.0 to an app the override
  excludes and 1.4.0 to one it admits; a narrowed-out plugin raises
  `RegistryError`;
- widening (floor and ceiling) rejected by `validate_registry_dict` and by
  `parse_registry`;
- seven malformed shapes rejected; malformed fails closed in resolution;
- a registry lie cannot beat the manifest (`requires app >=1.5.9`);
- schema 3 on a 1.5.8 line still fails with an override present;
- override semantics survive the cached-registry round trip, and a poisoned
  cache is rejected.

`tests/test_plugin_contract.py` — **20 passed, 0 skipped** against a real
plugin checkout, including a new drift guard asserting both repositories
compute the same effective range for every real registry entry, and a test
that the production resolver honours an override applied to the real registry.

### Non-regression

Against the real registry, through the production resolver:

| | |
| --- | --- |
| TRUBA 1.3.0 ↔ 1.5.8 | compatible; latest compatible is **1.3.0** |
| TRUBA 1.4.0 ↔ 1.5.8 | **not** compatible |
| TRUBA 1.5.0 ↔ 1.5.8 | **not** compatible |
| Fluent for 1.5.8 / 1.5.5 | 0.3.0 / 0.2.0 — unchanged |
| Community providers for 1.5.8 | 1.0.0 each — unchanged |
| Overrides in the real registry today | none; the field is unused so far |

---

## 2. Plugin registry — publication completeness

Implemented in the plugin repository; recorded here for the cross-repository
picture. See `docs/PUBLISHED_PLUGIN_IMMUTABILITY.md` there.

The ledger protected only what it listed, so the escape was to stop listing
something. `published-plugin-lock.json` now separates `publication_index` (the
append-only roster of everything ever published) from `published` (the frozen
digests), and validation enforces both directions:

1. **Everything published is frozen.** The authoritative published set is
   `main`'s own `registry.json`, read through git — a topic branch cannot
   rewrite it. CI checks out full history for this.
2. **Everything frozen still exists.** Each indexed version must still have a
   digest record, a registry row, a manifest, and every declared payload, all
   matching. The check walks from the ledger outwards.

So deleting a lock record, a registry row, a package directory, a manifest, or
a declared payload each fails closed, and "unfreeze, edit, regenerate every
hash" fails too.

`--record` verifies the manifest against the registry hash and every payload
against its declared digest before freezing, and refuses an unregistered
version. A version still in development stays unfrozen and free to change; a
published version without a freeze fails validation.

`tests/test_published_immutability.py` — **23 passed**, no hardcoded version
list as the completeness proof. The four documented one-time frozen exceptions
keep their accepted baselines, asserted explicitly.

---

## 3. Plugin `main` ruleset

`Protect main` (ruleset `21248984`) required only `Validate (3.10)`,
`Validate (3.12)`, and `Lint (Ruff)`. Removing `continue-on-error` from the
workflow made the job fail, but a failing job that is not a required status
check does not block a merge.

**A second, larger problem was found while fixing this**: the ruleset's
`conditions.ref_name.include` was empty, so it matched no branch at all.
`GET /repos/.../rules/branches/main` returned an empty list — `main` was
effectively unprotected, required checks or not.

Both were fixed. Final state, re-fetched from GitHub after the change:

```
conditions: {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}}
required_status_checks (strict: true):
  Validate (3.10)
  Validate (3.12)
  Lint (Ruff)
  Validate (3.14)
  Consumer contract (schema-capable application pin)
```

`GET /repos/.../rules/branches/main` now returns `deletion`,
`non_fast_forward`, `pull_request`, `required_status_checks`.

Nothing was weakened: a before/after diff of the ruleset shows the `deletion`,
`non_fast_forward`, and `pull_request` rules byte-identical (including
`required_review_thread_resolution: true`), bypass actors unchanged,
enforcement unchanged, `strict_required_status_checks_policy` unchanged, and
two checks added with none removed.

Context strings were taken from a real run's check-run names, not guessed.
The workflow's triggers were not changed to manufacture enforcement.

---

## 4. Validation

### Application

| Command | Result |
| --- | --- |
| `python -m compileall -q src/hpc_gui` | exit 0 |
| `python -m ruff check src tests scripts` | exit 0 |
| `python scripts/check_i18n.py` | exit 0 |
| `python scripts/smoke_test.py` | exit 0 |
| `python -m pytest tests --collect-only -q` | 2733 collected, 0 errors |
| `check_test_taxonomy.py --mode report` | zero-primary 0, multi-primary 0 |
| `check_test_taxonomy.py --mode ratchet` | PASS, no new zero-primary |
| `python -m pytest tests/test_plugin_compatibility_override.py` | 19 passed |
| `python -m pytest tests/test_plugin_contract.py` (real checkout) | 20 passed, 0 skipped |
| `python -X faulthandler scripts/release_test_suite.py` | **exit 0** — 2406 passed, 30 skipped, 6 deselected, 29 subtests, 585 s |
| `python scripts/release_test_suite.py --coverage` | **exit 0** — 66.86% ≥ 65% |
| `git diff --check` | exit 0 |

### Plugin registry

| Command | Result |
| --- | --- |
| `python -m pytest tests -q` | 188 passed |
| `python scripts/validate_registry.py` | OK |
| `python scripts/published_lock.py --check` | OK — ledger complete |
| `python -m ruff check scripts tests plugins` | All checks passed |
| `python scripts/check_docs_links.py` | OK |

### Real CI

Workflow `Validate plugin registry`, run `34937752043`, head SHA
`f0abb7e7037e66ab451d463c699fecf4e00c89eb`, event `workflow_dispatch`:

| Job | Conclusion |
| --- | --- |
| Validate (3.10) | success |
| Validate (3.12) | success |
| Validate (3.14) | success |
| Lint (Ruff) | success |
| Consumer contract (schema-capable application pin) | success |

No job was `continue-on-error`, neutral, skipped, or cancelled.

`APPLICATION_REF` advanced to `68a492a5dcdec842ed9dcbbd24b2fa22b0c45357`, the
immutable application commit that resolves through `compatibility_override`,
so the consumer contract exercises the production resolver.

---

## 5. Out of scope

No new evidence is claimed for packaged Windows smoke, Linux or macOS packaged
runtime, live TRUBA cluster, or manual GUI testing. None was run in this
remediation, and none of the earlier evidence for those is restated here as if
it were. Their status remains as recorded in
[FINAL_RELEASE_READINESS_REPORT_2026-09-15.md](FINAL_RELEASE_READINESS_REPORT_2026-09-15.md).
