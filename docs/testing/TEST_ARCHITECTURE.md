# Test Architecture

This tracked document defines the repository test-governance taxonomy and evidence rules. It supplements local development guidance; it does not replace local rules.md or migration status records.

## Primary categories

Every collected test will eventually have exactly one primary category. Choose by the behavior the test exercises, not by filename, fixture name, or historical label.

- unit — one isolated logical unit.
- integration — multiple real production components collaborate.
- gui — a real GUI framework object, action, or event produces observable GUI state or an effect. A static API-existence claim is the exception.
- e2e — a meaningful composed user workflow crosses major application/runtime boundaries. Validator-only or dictionary-only tests are not E2E.
- runtime_smoke — broad operability: does it start, import, or execute? This does not establish semantic correctness.
- contract — API, schema, config, import, i18n, or interface compatibility.
- audit — static repository, source, architecture, or governance checks.
- reporting — evidence, report-validator, aggregator, or manifest logic.
- release — packaging, build, installer, signing, or release-specific behavior.

A test is not GUI because its path contains wx, qt, panel, dialog, menu, or toolbar. A report validator is not E2E because it supports release evidence.

## Qualifiers

Qualifiers describe orthogonal constraints or claims. They never replace a primary category.

semantic, regression, performance, resource, concurrency, slow, subprocess, windows, linux, macos, hardware, synthetic_hardware, license, acceptance, artifact_dependent, wx, qt, packaging

The packaging qualifier is retained from the existing pytest configuration.

## Governance rules

- Exactly one primary: eventually each collected test must resolve to exactly one of the nine primary categories. Inherited module and class markers count.
- Canonical ownership: keep one canonical owner for an observable behavior where practical. Other tests may protect distinct contracts or failure modes.
- No test-calling-test duplication: tests may share fixtures, helpers, data builders, and production seams; one test must not call another test function as a wrapper.
- GUI truthfulness: GUI claims require a real framework object, event or action, and observable UI effect or state, except when the claim is only static API existence.
- E2E truthfulness: static files and report validators do not become E2E just because they support release evidence.
- Source-text tests: source-text checks are valid for genuine audit, contract, architecture, security-policy, or workflow-policy claims. Source text alone cannot prove runtime behavior.
- hasattr: hasattr proves presence only; it does not prove lifecycle, resource, or event semantics.
- Resource tests: allocate and hold the resource before testing release behavior.
- Concurrency tests: assert ordering, ownership, cancellation, or stale-result invariants, not merely completion.
- Mocking: mock at true external seams. Do not mock the exact logic the test claims to validate.
- Hardware truthfulness: distinguish real hardware from synthetic hardware.
- Determinism: control randomness, isolate the filesystem, avoid real network in normal tests, bound waits, clean up resources, and declare platform/environment constraints.
- Skip policy: do not skip merely because a test is flaky, broken, hard, slow, or deferred for later.
- XFail: make temporary xfail explicit and preferably strict; record its removal condition.
- Retry: a retry pass does not erase the first failure.
- Deletion gate: do not delete a test until the inventory exists, its unique assertions are recorded, a canonical owner is identified, the replacement passes targeted validation, node references and CI/report references are searched, and the mapping is recorded.
- No arbitrary count target: do not optimize only to reduce the number of tests.

## Taxonomy debt ratchet

`--mode report` derives categories from actual pytest markers, emits JSON, and remains non-gating for legacy zero-primary debt. `--mode ratchet --baseline <path>` uses the exact recorded nodeids and classification map. Existing zero-primary nodes may remain only when they are listed in that baseline; the zero-primary and multi-primary counts may not increase. Every new node must have exactly one primary, and a previously classified node must keep at least one. Removed nodeids are reported for review but do not fail the ratchet, so approved cleanup can delete tests. A newly detected generic catch-all test filename fails ratchet mode. Filename heuristics never assign a primary category. The ratchet is local and is not wired into automatic CI.

## Test Plan by Category

Unit:
Integration:
GUI:
E2E:
Runtime smoke:
Contract/Audit:
Reporting/Release:
Performance/Resource/Concurrency/Hardware/License/Acceptance:

Use “Not required — reason” where a category is not needed for a change.

For each new significant test, document or make clear:

- Primary category:
- Qualifiers:
- Canonical owner:
- Observable behavior:
- Positive case:
- Negative case:
- Cleanup/teardown case:
- Mutation expectation:
- Why existing tests do not already own this behavior:
