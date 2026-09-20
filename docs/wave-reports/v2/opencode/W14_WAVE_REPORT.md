# W14 Wave Report — Package provenance, build manifest and artifact identity

```text
Wave: W14 (provenance only; original planning Wave W04)
Canonical report path: docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: 0f8902a023bac76071527232c2287af96478ed2b
Current HEAD: 0f8902a023bac76071527232c2287af96478ed2b
Plugin repo SHA: f0abb7e7037e66ab451d463c699fecf4e00c89eb (develop)
First started: 2026-09-19
Last updated: 2026-09-19 (repair cycle 2 of max 2 — FINAL)
Session status: READY FOR FINAL REVIEW
Wave decision: GO (pending fresh-context re-audit)
```

## Objective

Create reproducible clean build provenance, immutable manifest fields and
artifact/evidence identity tied to exact hashes
(`HPC-W04-ART-001`, `HPC-W04-PROV-001..003`, `HPC-W04-MANIFEST-001..002`,
`HPC-W04-IDENTITY-001..002`; no TODO-detail rows owned).

## Baseline (pre-change, both repos pinned)

- Main `develop` == `origin/develop` ==
  `0f8902a023bac76071527232c2287af96478ed2b`; working tree dirty with
  pre-existing unrelated changes (preserved untouched).
- Plugin `develop` == `f0abb7e7037e66ab451d463c699fecf4e00c89eb`;
  only untracked `.github/social-preview.jpg` (preserved).
- `DEFAULT_GUI_RUNTIME=qt` (`src/hpc_gui/runtime.py`); Python 3.12.4
  primary, Python 3.14.0 used for the wheel build (requires-python
  `==3.14.*`).
- Narrow pre-change slice green: `test_release_manifest`,
  `test_version_consistency`, `test_release_surface`, `test_sync_version`
  → 7 passed.

## Requirement → owner → test → evidence trace (8 owned rows)

Written for repair cycle 2 from live code/tests/evidence on the current
tree (main `0f8902a0…`, plugin `f0abb7e7…`); not copied from the audit table.

| Requirement | Live implementation owner | Test(s) | Evidence |
|---|---|---|---|
| `HPC-W04-ART-001` (clean package path) | Manifest + provenance + smoke package path: `scripts/generate_release_manifest.py::build_manifest`, `scripts/capture_build_provenance.py` (pre-build gate), `scripts/wx_packaged_smoke.py` (evidence embed) | `test_manifest_contains_all_provenance_fields`, `test_provenance_captures_git_identity_and_toolchain`, `test_smoke_evidence_carries_identity_header`, `test_staged_manifest_json_is_machine_readable` | `dist/w14-candidate-r1/MANIFEST.json` + wheel `3b2849b7…fcda48` + `build/audit/w14-packaged-smoke-r1.json` |
| `HPC-W04-PROV-001` (record status + HEAD) | `scripts/capture_build_provenance.py::capture_provenance` — records `git status --short` + `git rev-parse HEAD` for main and plugin repos, `"unknown"` degradation | `test_provenance_captures_git_identity_and_toolchain` (+ `test_provenance_degrades_truthfully_without_repos` negative) | Live provenance record on current tree: main `0f8902a023bac76071527232c2287af96478ed2b`, plugin `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; rerun `capture_provenance(ROOT)` green in 43-test suite |
| `HPC-W04-PROV-002` (toolchain/lock versions) | `scripts/capture_build_provenance.py::capture_provenance` toolchain block (`python_runtime`, `packager_version`, `target_os_arch`) + `dependency_lock_sha256` of `requirements-release.lock` | `test_provenance_captures_git_identity_and_toolchain` (asserts `toolchain.python`, `os_arch`, 64-hex lock hash) | Provenance JSON fields + `dist/w14-candidate-r1/MANIFEST.json` (`python_runtime 3.14.0`, lock hash, packager fallback chain) |
| `HPC-W04-PROV-003` (never reuse unidentified exe) | `scripts/capture_build_provenance.py::guard_candidate_dir` / `find_stale_executables` + CLI `--candidate-dir` / `--known-fresh` (`main()` exit 2 fail-closed, quarantine outside candidate path) | `test_stale_guard_rejects_unidentified_executable`, `test_stale_guard_accepts_clean_candidate`, `test_stale_guard_accepts_declared_fresh_artifact`, `test_stale_guard_cli_known_fresh_exempts_declared_artifact`, `test_stale_guard_quarantines_outside_candidate`, `test_stale_guard_refuses_archive_inside_candidate` | CLI reruns on current tree: without `--known-fresh` → exit 2 / 13 stale paths; with `--known-fresh hpc_client_gui-1.5.9-py3-none-any.whl` → exit 2 / 12 stale paths, fresh wheel exempt |
| `HPC-W04-MANIFEST-001` (11-field build manifest) | `scripts/generate_release_manifest.py::build_manifest` — `main_commit`, `plugin_commit`, `plugin_bundle_revision`, `build_timestamp_utc`, `app_version`, `python_runtime`, `packager_version`, `target_os_arch`, `build_command`, `dependency_lock_sha256`, per-artifact filename + SHA256 (pre-W14 keys preserved) | `test_manifest_contains_all_provenance_fields`, `test_manifest_rejects_empty_release_dir`, `test_manifest_rejects_missing_release_dir`, `test_staged_manifest_json_is_machine_readable`, plus pre-existing `test_release_manifest.py` (3) | `dist/w14-candidate-r1/MANIFEST.json` (11 fields + per-artifact hash `3b2849b7…fcda48`, `python_runtime 3.14.0`, explicit `build_command`) |
| `HPC-W04-MANIFEST-002` (packaged version consistency) | Manifest `app_version` from `__version__` vs `CLI_VERSION` / `pyproject` / changelog `## v1.5.9` / `version_info.txt` consistency path | `test_manifest_app_version_matches_product_metadata` + pre-existing `test_version_consistency.py::test_repository_version_views_match` + isolated wheel probe | Manifest `app_version 1.5.9` == isolated `pip install --no-deps --target <tmp>` import `hpc_gui.__version__ == 1.5.9` on exact wheel `3b2849b7…fcda48` |
| `HPC-W04-IDENTITY-001` (identity header helper) | `scripts/artifact_identity.py::format_artifact_identity` / `parse_` round-trip, wired into `scripts/wx_packaged_smoke.py` (`identity_header` in evidence JSON, printed first) and `generate_release_manifest.py` per-artifact print | `test_identity_header_has_six_required_lines`, `test_identity_header_rejects_malformed_input`, `test_smoke_evidence_carries_identity_header` | Six-line `Artifact/SHA256/Main SHA/Plugin SHA/Version/OS-arch` header at head of `build/audit/w14-packaged-smoke-r1.json` and per-artifact manifest output |
| `HPC-W04-IDENTITY-002` (exact SHA binding) | Exact-hash binding: per-artifact SHA256 in `build_manifest` + `format_artifact_identity` header; any byte change invalidates evidence | `test_manifest_identity_headers_bind_exact_hashes` (rebuild with changed bytes → changed identity) + `test_sha256_matches_hashlib_for_known_content` (pre-existing) | Wheel SHA-256 `3b2849b7916741455aaff47625043ee343b32a921cfb713e8c80bb8c66fcda48` verified three ways (pip build report, independent `hashlib`, `MANIFEST.json`); payload-identity note: 266 entries, 0 content diffs vs superseded `78f9da8e…` (mtime-only) |

## Discovery + WAVE_FINDINGS

| Finding ID | Severity | Surface | Evidence | Root cause | Impact | Fix | Countable | Status |
|---|---|---|---|---|---|---|---|---|
| DEF-W14-001 | P1 | `scripts/generate_release_manifest.py::build_manifest` | Before-run printed keys `['artifacts','release','sbom','schema']` only | Manifest schema omitted all Workstream B provenance fields | Package untied to source identity | FIX-W14-A | yes | CLOSED |
| DEF-W14-002 | P1 | pre-build pipeline | No provenance capture existed (`grep` for status/rev-parse recording: none) | Nothing recorded git identity/toolchain before build | Unidentified builds possible | FIX-W14-B (part 1) | yes (with -003 as one independent fix) | CLOSED |
| DEF-W14-003 | P1 | `dist/`, `build/`, candidate dir | `dist/` holds stale onedir exes, old whl/tar.gz, updater demo; nothing rejects them | No stale-output guard; independent roots never cross-checked | Stale exe confusable with candidate | FIX-W14-B (part 2) | yes | CLOSED |
| DEF-W14-004 | P1 | package evidence logs | No `Artifact:`/`identity_header` helper anywhere (`grep`: no matches) | Identity helper missing; smoke evidence lacked 6-line header | Evidence not bound to hash at log head | IDENTITY fix | supporting (ships with FIX-A/B) | CLOSED |

FIX-A vs FIX-B independence: FIX-A corrects the artifact *description*
(manifest schema completeness); FIX-B corrects build-*input* validation
(pre-build provenance recording + stale-output rejection across
independent roots). Different defect IDs, different failure modes,
different files.

## Fixes

### Repair cycle 1 (audit REOPEN response, 2026-09-19)

Fresh-context audit returned REOPEN with two P1 findings
(`W14_AUDIT_REPORT.md`):

- REOPEN-W14-001: PACKAGE plugin identity stale — report/manifest bound
  plugin `f0abb7e7037e66ab451d463c699fecf4e00c89eb` while the auditor
  observed plugin HEAD `0788169cdc6aeeadee2a14015a85f3ee7e44fa20` (dirty).
- REOPEN-W14-002: stale-guard rerun listed 13 stale artifacts including
  the candidate wheel itself vs the reported 12; CLI had no
  fresh-artifact declaration although the API supports `known_fresh`.

Re-pin truth recorded this cycle (no destructive reset/clean performed):

- Main `develop` == `0f8902a023bac76071527232c2287af96478ed2b` (dirty with
  pre-existing unrelated changes + W14 scope files; preserved untouched).
- Plugin `develop` == `f0abb7e7037e66ab451d463c699fecf4e00c89eb`, status
  only untracked `.github/social-preview.jpg` (preserved).
- The audit-cited `0788169...` object is **absent** from the plugin
  repository (`git cat-file -t 0788169...` → fatal: could not get object
  info; `git log --all` shows no such commit). Current plugin truth
  therefore still matches the originally bound SHA, but per the audit
  instruction the candidate evidence was NOT reused: a fresh wheel +
  manifest + identity header were rebuilt from the explicitly pinned
  SHAs into a new candidate directory `dist/w14-candidate-r1` (old
  `dist/w14-candidate` left untouched as superseded evidence).

| Finding ID | Severity | Surface | Evidence | Root cause | Impact | Fix | Countable | Status |
|---|---|---|---|---|---|---|---|---|
| DEF-W14-005 | P1 | `capture_build_provenance.py` CLI | CLI accepted no `--known-fresh`; documented guard command counted the fresh wheel as stale (13 vs claimed 12) | Fresh-artifact declaration existed only in the API, not the CLI | Reported acceptance invocation non-reproducible | FIX-W14-C | yes | CLOSED |

### FIX-C — `--known-fresh` CLI passthrough (`scripts/capture_build_provenance.py`)

`main()` gained repeatable `--known-fresh NAME`, forwarded as
`known_fresh=set(...)` to `guard_candidate_dir()`. Reproducible record:

- `python scripts/capture_build_provenance.py --candidate-dir
  dist/w14-candidate-r1` → exit 2 listing **13** stale paths (fresh
  candidate wheel included — fail-closed pre-build state).
- Same plus `--known-fresh hpc_client_gui-1.5.9-py3-none-any.whl` →
  exit 2 listing **12** stale paths across `dist/` + `build/`
  independent roots + superseded `dist/w14-candidate/` wheel; the
  declared fresh wheel is exempt. Post-build re-verification that still
  fails closed on genuine pre-existing stales (correct: they remain
  confusable until cleaned/quarantined, which is out of scope to do
  destructively here).
- New regression test
  `test_stale_guard_cli_known_fresh_exempts_declared_artifact`
  (sensitivity: reverted CLI → `unrecognized arguments: --known-fresh`,
  test FAILS; restored → passes).

### FIX-A — full 11-field build manifest (`scripts/generate_release_manifest.py`)

`build_manifest()` now emits `main_commit`, `plugin_commit`,
`plugin_bundle_revision`, `build_timestamp_utc`, `app_version` (from
`__version__`), `python_runtime`, `packager_version`
(pyinstaller→pip→setuptools→wheel fallback), `target_os_arch`,
`build_command`, `dependency_lock_sha256` (hash of
`requirements-release.lock`), plus per-artifact filename + SHA256.
Pre-W14 keys (`schema`/`release`/`sbom`/`artifacts`) preserved, so all
pre-existing manifest tests still pass. CLI gained `--build-command` and
prints the per-artifact identity header.

### FIX-B — provenance capture + stale-dist guard (`scripts/capture_build_provenance.py`, new)

- `capture_provenance()` records `git status --short` + `git rev-parse
  HEAD` for main and plugin repos, toolchain versions, dependency-lock
  hash and UTC capture time; degrades to explicit `"unknown"`, never a
  fake SHA.
- `guard_candidate_dir()` / `find_stale_executables()` fail closed
  (exit 2 / `ValueError`) listing stale executables across independent
  roots (candidate dir, `dist/`, `build/`), support quarantining to an
  explicitly named archive *outside* the candidate path, and support
  post-build re-verification via `known_fresh`.

### IDENTITY — six-line header (`scripts/artifact_identity.py`, new; wired into smoke)

`format_artifact_identity()` renders `Artifact/SHA256/Main
SHA/Plugin SHA/Version/OS-arch` with a strict `parse_` round-trip.
`wx_packaged_smoke.py` now embeds `identity_header` in evidence JSON and
prints it first; `generate_release_manifest.py` prints it per artifact.

Version consistency (`HPC-W04-MANIFEST-002`): manifest `app_version`
asserted equal to `__version__` == `CLI_VERSION` == `pyproject` ==
changelog `## v1.5.9` == `version_info.txt`
(`test_manifest_app_version_matches_product_metadata` +
pre-existing `test_version_consistency.py`).

## Tests

New `tests/test_w14_provenance_manifest.py` (17 tests: 16 original +
`test_stale_guard_cli_known_fresh_exempts_declared_artifact` for
FIX-W14-C): REQ-W14-MANIFEST,
REQ-W14-PROV, REQ-W04-GUARD, REQ-W14-IDENTITY, REQ-W14-VERSION,
NEG-W14-MANIFEST/GUARD/IDENTITY/PROV, PKG-W14-MANIFEST/IDENTITY.
Taxonomy: unit + packaging + static contract, no mocks (real code, tmp
fixtures, read-only git). No wx surface change → no GUI proof applicable;
no cluster claim → EXTERNAL N/A.

- Narrow + impacted suite: 43 passed, 0 failed, exit 0
- Exact command (repair cycle 2 re-run on current tree, main
  `0f8902a023bac76071527232c2287af96478ed2b`):
- `python -m pytest tests/test_w14_provenance_manifest.py
  tests/test_release_manifest.py tests/test_version_consistency.py
  tests/test_release_surface.py tests/test_sync_version.py
  tests/test_wave10_release_gate.py tests/test_release_test_suite.py -q`
  → `43 passed in 8.35s` (17 W14 + 3 release-manifest + 1
  version-consistency + 2 release-surface + 1 sync-version + 16
  wave10-release-gate + 3 release-test-suite). The prior `40 passed`
  figure was stale: it predated `test_release_test_suite.py` (3 tests)
  being part of the named impacted set (40 + 3 = 43).
- Sensitivity FIX-A/IDENTITY: reverted tracked fixes → 5 failed
  (`TypeError`/`AttributeError`/`KeyError` on exactly the new behavior),
  restored → all pass.
- Sensitivity FIX-B: removed new module → collection `ImportError`;
  restored → all pass.
- `git diff --check` clean; unrelated working-tree changes preserved.

## Second-defect search (12 dims)

negative ✓ (missing/empty dir, stale present, malformed header,
non-repo roots) · lifecycle ✓ (quarantine + re-verify + known_fresh) ·
stale state ✓ (MANIFEST.json self-exclusion; regen still 1 artifact) ·
identity ✓ (absent plugin repo → `unknown`) · concurrency N/A (single-
process CLIs) · boundary ✓ (empty/missing dirs) · capability absence ✓
(non-repo degradation test) · persistence ✓ (MANIFEST round-trip) ·
packaging ✓ (repair cycle 1 rebuild payload-identical: 266 entries,
0 content diffs, mtime-only outer hash change) · error
visibility ✓ (exit 2 + listings on stderr) · secondary entry N/A (no UI)
· adjacent boundary ✓ (smoke helper import fallback; `check_release_
consistency.ps1`/`release_gate.py` untouched). No further in-scope
defect found; post-green review found no duplicate path, silent
fallback, or error-claiming-success.

## PACKAGE evidence (exact artifact binding) — repair cycle 1 candidate

Fresh candidate rebuilt 2026-09-19 from explicitly pinned SHAs
(main `0f8902a…`, plugin `f0abb7e…`) with Python 3.14.0
(`requires-python ==3.14.*`); prior `dist/w14-candidate` evidence
superseded, not reused:

```text
Artifact: hpc_client_gui-1.5.9-py3-none-any.whl
SHA256: 3b2849b7916741455aaff47625043ee343b32a921cfb713e8c80bb8c66fcda48
Main SHA: 0f8902a023bac76071527232c2287af96478ed2b
Plugin SHA: f0abb7e7037e66ab451d463c699fecf4e00c89eb
Version: 1.5.9
OS/arch: windows/amd64
```

- Wheel SHA-256 verified three ways: pip build report
  (`sha256=3b2849b7…`), independent `hashlib` check (`3b2849b7…`),
  `MANIFEST.json` (`dist/w14-candidate-r1/MANIFEST.json`, 11 fields +
  per-artifact hash, `python_runtime 3.14.0`, explicit `build_command`).
  Any byte change invalidates all evidence tied to this hash.
- Payload-identity note: old vs new wheel compared entry-wise (266
  entries, identical name set, **0** content-differing entries); only 5
  `dist-info` entries differ by zip mtime (build timestamps). The hash
  change vs the superseded `78f9da8e…` candidate is mtime-only, not a
  source/payload drift — consistent with unchanged pinned SHAs
  (W14 `scripts/` helpers are not packaged into the wheel).
- Stale guard (FIX-W14-C, corrected explicit invocations, both exit 2
  fail-closed): without `--known-fresh` → 13 stale paths incl. the fresh
  wheel; with `--known-fresh hpc_client_gui-1.5.9-py3-none-any.whl` →
  12 stale paths across `dist/` + `build/` independent roots plus the
  superseded candidate wheel, fresh wheel exempt. Confusion with the
  candidate is blocked, not assumed away.
- Packaged smoke on exact tree: `wx_packaged_smoke` supports `.py`/`.exe`
  only and rejects `.whl` by design (`ValueError: unsupported artifact
  type: .whl` — diagnostic harness behavior, recorded in
  `build/audit/w14-packaged-smoke-r1.json` with the fresh identity
  header bound). Wheel runtime proof instead: isolated
  `pip install --no-deps --target <tmp>` of the exact wheel under
  Python 3.14 imports `hpc_gui.__version__ == 1.5.9` (matches manifest
  `app_version`; deeper `CLI_VERSION` import needs third-party
  `paramiko`, absent from the bare `--no-deps` target — environmental,
  not a product defect). Probe-based smoke identity wiring remains
  covered by `test_smoke_evidence_carries_identity_header` (green in the
  43-test suite).
- GUI evidence class: N/A (no wx surface change — packaging harness
  only). EXTERNAL: N/A (no cluster claim).

> Superseded cycle-0 record (retained for traceability; do NOT use as
> acceptance evidence): prior candidate `dist/w14-candidate` bound
> SHA-256 `78f9da8e0023f112c84d553a90c73c1807c84113e1a0fc760b2167d88d675511`
> with the guard's undeclared-fresh invocation listing 12 stale paths.
> Replaced by the `3b2849b7…` candidate above per REOPEN-W14-001/002.

## Files changed (W14 scope only)

- `scripts/generate_release_manifest.py` (FIX-A + IDENTITY wiring)
- `scripts/wx_packaged_smoke.py` (identity header in evidence)
- `scripts/artifact_identity.py` (new)
- `scripts/capture_build_provenance.py` (new, FIX-B + FIX-W14-C `--known-fresh`)
- `tests/test_w14_provenance_manifest.py` (new, 17 tests)
- Untracked build evidence (not for commit): `dist/w14-candidate/`
  (superseded cycle-0), `dist/w14-candidate-r1/` (current),
  `build/audit/w14-packaged-smoke-r1.json` (current)

## Resume state

Completed: FIX-A, FIX-B, IDENTITY, FIX-W14-C, 17 regression tests,
PACKAGE evidence bound to SHA-256 `3b2849b7…fcda48`
(`dist/w14-candidate-r1`), report current.
REOPEN-W14-001: re-pinned both repos (plugin truth still `f0abb7e…`;
audit-cited `0788169…` absent from plugin object DB), rebuilt fresh
candidate from pinned SHAs — old evidence superseded, not reused.
REOPEN-W14-002: CLI `--known-fresh` added; guard re-verified exit 2 with
13 (undeclared) / 12 (declared-fresh) stale paths.
Repair cycle 2 (FINAL): added mandatory eight-row
requirement→owner→test→evidence trace above (REOPEN-W14-003); corrected
impacted count to exact 43 passed with full command + partition breakdown
(REOPEN-W14-004); re-ran exact impacted command on current tree
(main `0f8902a0…`, plugin `f0abb7e7…`) → 43 passed.
Open P0/P1: none. Open P2/P3: none in scope.
Pending: fresh-context re-audit (`W14_AUDIT_REPORT.md`) by the audit agent.
Next: never auto-start W15.

```text
FIX-A: manifest 11 fields / DEF-W14-001 / root cause: schema omitted provenance / Before EV: keys [artifacts,release,sbom,schema] / After EV: MANIFEST.json w/ 11 fields, 43-test suite green / Regression: test_manifest_contains_all_provenance_fields / Sensitivity: 5 fail pre-fix, pass post-fix
FIX-B: provenance capture + stale-dist guard / DEF-W14-002/003 / root cause: no pre-build identity recording, no cross-root stale rejection / Before EV: no capture module, guard absent / After EV: provenance JSON pinned, guard exit 2 fail-closed / Regression: test_stale_guard_rejects_unidentified_executable et al / Sensitivity: ImportError without module, pass with it
FIX-C: CLI --known-fresh passthrough / DEF-W14-005 (REOPEN-W14-002) / root cause: fresh-artifact declaration API-only / Before EV: CLI exit 2 listing 13 incl. fresh wheel vs claimed 12 / After EV: --known-fresh exempts declared wheel (12 stale, still exit 2) / Regression: test_stale_guard_cli_known_fresh_exempts_declared_artifact / Sensitivity: unrecognized-arguments FAIL pre-fix, pass post-fix
REOPEN-W14-001: re-pin + fresh rebuild / audit-cited 0788169 absent from plugin DB; plugin truth f0abb7e confirmed; new wheel 3b2849b7 payload-identical (0 content diffs, mtime-only) / old 78f9da8e evidence superseded
Three-fix gate: PASS
Wave decision: GO (pending fresh-context re-audit)
```
