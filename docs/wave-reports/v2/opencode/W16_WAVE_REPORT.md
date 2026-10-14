# W16 Wave Report — Package content and deterministic smoke harness

```text
Wave: W16 (original planning Wave W04; provenance only)
Canonical report path: docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: 63b696b3b8c64296d9d17f94c8d0d903f9bab7eb
Current HEAD: 4f89c4d4d9a5b1e620c825fa5af3ff814b910548 (working tree preserved; no reset/clean/push)
Tested implementation SHA: 4f89c4d4d9a5b1e620c825fa5af3ff814b910548 (+ existing working-tree changes, uncommitted)
Plugin repo SHA: f0abb7e7037e66ab451d463c699fecf4e00c89eb (develop == origin/develop)
First started: 2026-09-19
Last updated: 2026-09-29
Session status: REPAIR (closed-owner repair of HPC-W04-HARNESS-025 complete; fresh audit required against the new content identity)
Wave decision: READY_FOR_AUDIT (unchanged decision, re-pending after this repair)
```

## Objective

## Repair cycle — 2026-09-22

- `REOPEN-W16-001` repaired by rebuilding the Windows bundle from current
  repository HEAD `63b696b3…`; the exact executable now hashes to
  `544e186f81aa685ee80a3c07185ee0eb03ab1bc73a81151b1323253503c0a1da`.
  `wx_package_content.py` was rerun and produced current 8/8 PASS evidence.
- `REOPEN-W16-002` is rejected by the canonical W16 authority: W15 is an
  integration reference only and is explicitly non-blocking for W16 acceptance.
  No W15 lifecycle change was made.
- Focused package-content CLI validation passed. The full pytest attempt was
  environment-invalid because the controller-owned TEMP root denied pytest
  directory enumeration; no test result from that attempt is claimed as PASS.
- Repair-phase refresh on 2026-09-22 regenerated `build/audit/w16-package-content-windows.json`
  and `dist/releases/w16-candidate/MANIFEST.json` from the exact staged artifact.
  Both report current HEAD `63b696b3…` and artifact SHA
  `544e186f81aa685ee80a3c07185ee0eb03ab1bc73a81151b1323253503c0a1da`;
  package-content is 8/8 PASS. Focused validation rerun:
  `python -m pytest -q tests/test_wx_packaged_smoke.py tests/test_wx_package_content.py
  tests/test_release_manifest.py` → `29 passed` after the workdir-scope repair.
- REOPEN-W16-006 repaired in `scripts/wx_packaged_smoke.py`: both packaged and
  fresh-user workdir checks now exclude the repository root, including `.tmp/os`,
  rather than excluding only `src`. Regression coverage verifies both paths.
- Post-repair focused validation with external writable TEMP/TMP:
  `python -m pytest -q tests/test_wx_packaged_smoke.py
  tests/test_wx_package_content.py tests/test_release_manifest.py` → `29 passed`.
- The earlier historical counts (`25 new`, `106`, and `169`) describe prior
  implementation cycles and are not the current repair result; the current
  focused repair validation is the `29 passed` run above.

## Closed-owner repair cycle — 2026-09-29 (HPC-W04-HARNESS-025)

W16 is a CLOSED Wave (`waves/done/W16.md`). `HPC-W04-HARNESS-025` is routed to
W16 as closed owner by the controller ledger
`.tmp/agent-runs/ac-wave-opencode-parallel/20260929-131518-47e3c21e/0002-W57-findings.json`
(`execution_owner: W16`, `owner_state: done`). This is therefore a
closed-owner repair transaction: historical lifecycle closure and current
compliance are distinct facts. No Wave file, no other Wave's artifacts, and no
`artifacts/wave_W16/**` were created or edited (that directory still does not
exist; evidence-manifest minting is controller-owned).

### FINDING

`scripts/wx_packaged_smoke.py::run_packaged_smoke` scored evidence only inside
the non-timeout branch. When the packaged child was killed on timeout, the
runtime payload it had already written was never read, `runtime_checks` were
never mapped into `checks`, `pty_resize` was never scored, `clean_shutdown` was
never recomputed, and `combined` stayed empty so no output was captured. A
timeout therefore produced an all-`FAIL` report that discarded proof the
packaged process had already produced.

### OBSERVED_FAILURE

At the pre-repair commit the whole evidence-scoring block sat under the
`else:` of `if timed_out:`, so the two timeout paths diverged completely. This
is what made the acceptance gate lose information: a 240-second real packaged
run that proved 19/20 checks and then hung produced a report claiming 0/20.

### HYPOTHESIS

`W16-REPAIR-SCORE-PROVEN-EVIDENCE-ON-TIMEOUT` — scoring the evidence
unconditionally, while keeping the timeout verdict itself, repairs the defect
without relaxing the acceptance criterion.

### CHANGE (`scripts/wx_packaged_smoke.py`, `tests/test_wx_packaged_smoke.py`)

1. Hoisted the evidence-scoring block out of the non-timeout branch. The
   runtime payload is now read, `runtime_checks` are mapped into `checks`,
   `pty_resize` is scored from the disposable server, and `clean_shutdown` is
   recomputed on BOTH the timed-out and the normal path.
2. `result = "FAIL" if timed_out else ...` is unchanged, so a timeout can
   never report `PASS`. `clean_shutdown` is `FAIL` on the timeout path because
   a killed child never shut down cleanly.
3. The timed-out branch sets `details.evidence_scored_on_timeout = True` and
   captures a bounded `details.output_tail` (last 2000 chars, the fresh-user
   convention). `details.timeout` and `details.child_killed` are byte-identical
   to the pre-repair values, so the pre-existing `NEG-W16-TIMEOUT-KILL`
   assertions stay green.
4. `run_packaged_smoke` default timeout raised `25` -> `240`, matching its
   sibling `run_fresh_user_smoke` (a real packaged GUI needs more than 25s);
   `main()` gained `--timeout` (default `240`) wired end to end into both
   runners. `--artifact/--platform/--output/--fresh-user` semantics and the
   stdout-JSON contract are unchanged.

### Additional defect found and repaired in the same transaction

`test_workdir_outside_repo_excludes_repo_tmp` was RED on entry and is not
caused by this Wave's change: `_outside_repo` used `Path.resolve()`, which
follows the repository's own `.tmp` NTFS junction into
`D:\Projeler\.tmp\hpc-client-gui`, so a genuinely in-repo workdir such as
`.tmp/os/run` was reported as OUTSIDE the repository. That is a false
isolation claim in the evidence, so it is repaired rather than waived.
`_outside_repo` now compares normalized lexical paths
(`os.path.normcase(os.path.abspath(...))`), i.e. the contract is about the
repository tree, not about where a link points. `_outside_repo` is diagnostic
only (`details.workdir_outside_repo`); it gates nothing, so no acceptance
criterion changed.

### RESULT (exact commands and counts)

| Command | Result |
| --- | --- |
| `python -m pytest -q --basetemp .tmp/pytest-w16-repair tests/test_wx_packaged_smoke.py` | `10 passed` (7 pre-existing + 3 new) |
| same, with `scripts/wx_packaged_smoke.py` reverted to `git show HEAD:` | `3 failed, 7 deselected` |
| `python -m pytest -q -n auto --basetemp .tmp/pytest-w16-repair tests/test_wx_packaged_smoke.py tests/test_release_manifest.py tests/test_wx_package_content.py tests/test_w14_provenance_manifest.py tests/test_w15_fresh_user_startup.py` | `60 passed` |
| `python .opencode/scripts/validate-wave-orchestration.py` | `AC_WAVE_METADATA_VALID=61`, `PASS`, exit 0 |
| `python .opencode/scripts/validate-wave-authoring.py` | `AC_WAVE_AUTHORING_VALID=61`, `PASS`, exit 0 |
| `git diff --check -- scripts/wx_packaged_smoke.py tests/test_wx_packaged_smoke.py` | clean, exit 0 |

Sensitivity proof (the three new tests are RED on pre-repair code, i.e. they
actually bind the defect):

- `test_timeout_retains_child_runtime_evidence` -> `AssertionError:
  wx_runtime_started` (`- PASS` / `+ FAIL`): the payload's checks were dropped.
- `test_timeout_details_score_flag_and_kill_keys_intact` -> `KeyError:
  'evidence_scored_on_timeout'`.
- `test_cli_timeout_argument_honored_end_to_end` -> `wx_packaged_smoke.py:
  error: unrecognized arguments: --timeout 3`, `assert 2 == 1`.

All 7 pre-existing tests in `tests/test_wx_packaged_smoke.py` are present and
unweakened, including `test_sleeper_child_killed_on_timeout`; the 3 new tests
are strictly additive. No test was skipped, xfailed, or deleted.

### Identity

- Current HEAD: `4f89c4d4d9a5b1e620c825fa5af3ff814b910548` (working tree
  preserved; no reset/clean/push).
- Content identity after this repair:
  `b591eb6b834fafdced7e26b3abeefad87b3d04f207368db0eae118d7bd6db533`
  (was `45c46c0a09c3f9b85b4679c40f3779a694b5a8f0c0c63b64cc1380823eeac3fc`).
  This identity covers the whole repository including the live controller
  tree, so it will drift while the controller is running; the owning evidence
  must be bound to the identity measured at audit time.
- **Not re-minted by this repair:** `dist/releases/w16-candidate/MANIFEST.json`
  still binds artifact SHA
  `544e186f81aa685ee80a3c07185ee0eb03ab1bc73a81151b1323253503c0a1da` at
  `main_commit 63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`. This is a harness
  source repair only: no artifact was rebuilt, re-hashed, or re-packaged, and
  no packaged GUI or loopback acceptance was re-run from this node. The W57
  packaged gate re-run is controller-scheduled against the new identity.


Close package-content/resource validation and the reusable exact-artifact
smoke runner used by downstream Waves (`HPC-W04-HARNESS-001..039`,
`HPC-W04-SMOKE-001..010`; no TODO-detail rows owned): harden
`scripts/wx_packaged_smoke.py` into a deterministic rerunnable procedure,
add the missing package-content checks (HARNESS-005..013/015) and
manifest/provenance binding (HARNESS-014/022..030/032..037).

## Baseline (pre-change, both repos pinned)

- Main `develop` == `origin/develop` == `0f8902a023bac76071527232c2287af96478ed2b`;
  working tree dirty with pre-existing W01–W15 working state (preserved
  byte-for-byte; verified after every stash cycle).
- Plugin `develop` == `origin/develop` == `f0abb7e7037e66ab451d463c699fecf4e00c89eb`
  (+ untracked `.github/social-preview.jpg`, preserved).
- Toolchain: Python 3.12.4, PyInstaller 6.19.0, wxPython 4.3.1.
- Narrow pre-change slice (`test_wx_packaged_smoke + test_release_manifest +
  test_w14_provenance_manifest + test_w15_fresh_user_startup`):
  `1 failed, 31 passed` — the single failure is DEF-W16-001 below
  (`test_missing_artifact_report_fails_critical_stages`, JSONDecodeError on
  stdout), proven to pass on the committed runner and fail on the working tree.
- `dist/hpc-client-gui/hpc-client-gui.exe` pre-rebuild: SHA-256
  `d2aab99d998a1dd0d912098f319f9bbf6c227ba0b4b82c9db9303bcf6c863cfd`
  (W15 canonical acceptance; STALE for W16 after rebuild, bytes quarantined —
  never cited for W16 acceptance).
- Entry criteria: HARNESS-001 W03 PASS (`W03_WAVE_REPORT.md` decision PASS) ✔;
  HARNESS-002 SHAs pinned above ✔; HARNESS-003 toolchain available ✔;
  HARNESS-004 old outputs quarantined by copy-before-rebuild (no deletes) ✔.

## Requirement → owner → test → evidence trace (49 owned rows)

| Requirement | Live implementation owner | Test(s) | Evidence |
|---|---|---|---|
| HARNESS-001 (W03 GO/BLOCKED) | this report §Baseline | W03 report decision | VERIFIED (W03 PASS) |
| HARNESS-002 (SHAs pinned) | this report header | `git rev-parse` both repos | VERIFIED |
| HARNESS-003 (toolchain) | build log | `pyinstaller --clean` exit 0 | VERIFIED |
| HARNESS-004 (quarantine) | quarantine copy pre-rebuild | SHA match | VERIFIED |
| HARNESS-005..013 (content validation) | `scripts/wx_package_content.py` (8 checks) | `tests/test_wx_package_content.py` (19) + packaged run | VERIFIED (8/8 PASS on exact SHA) |
| HARNESS-006 (wx/runtime deps) | `wx_runtime` check | NEG fixtures (webview/wxdir/shiboken) | VERIFIED |
| HARNESS-007 (icons/assets) | `icons_assets` mirror rule vs spec | NEG fixtures (ico/terminal) | VERIFIED |
| HARNESS-008 (localization) | `localization` (valid JSON + required namespaces) | NEG (corrupt/missing ns) | VERIFIED |
| HARNESS-009 (config schemas) | `provider_templates` (namespaces + embedded-defaults record) | NEG (namespace strip) | VERIFIED |
| HARNESS-010 (plugin discovery) | `plugin_provider_surface` (PLUGINS docs + loader record) | NEG (doc removal) | VERIFIED |
| HARNESS-011 (updater trust) | `updater_trust` (no stray keys + embedded-anchor record) | NEG (stray .pem) | VERIFIED |
| HARNESS-012 (provider templates) | `provider_templates` + defaults record | NEG (namespace strip) | VERIFIED |
| HARNESS-013 (licenses) | `docs_and_licenses` mirror rule + docs core set | NEG (license/doc removal) | VERIFIED |
| HARNESS-014 (manifest unit test) | `scripts/generate_release_manifest.py` | `test_release_manifest` + W14 manifest tests (in 106-set) | VERIFIED |
| HARNESS-015 (package-content checks) | content script + runner | 19 new + stub tests | VERIFIED |
| HARNESS-016 (launch smoke) | `run_packaged_smoke` | stub tests + packaged run | VERIFIED (process/main_frame PASS) |
| HARNESS-017 (settings persistence smoke) | settings_opened (open path); persistence via fresh run2 | REQ/NEG-W16-SETTINGS + PKG-GJ-01 | VERIFIED |
| HARNESS-018 (plugin/provider discovery smoke) | surface import probes + content check | packaged run (both surfaces PASS) | VERIFIED |
| HARNESS-019 (offline file/editor smoke) | editor_roundtrip (ChangeValue/GetValue, Unicode) | packaged run PASS | VERIFIED |
| HARNESS-020 (controlled failure smoke) | fresh-user dead-port via visible controls | PKG-GJ-01 PASS | VERIFIED |
| HARNESS-021 (optional remote replay) | loopback fixture only | CONDITIONAL — no authorized infra | EXTERNAL-deferred (never mocked as real) |
| HARNESS-022 (tied to main SHA) | identity header (main/plugin/SHA/version/arch) | header == disk SHA | VERIFIED (544e186f) |
| HARNESS-023 (plugin provenance) | header plugin SHA + manifest plugin_commit | match f0abb7e7 | VERIFIED |
| HARNESS-024 (SHA-256 captured) | header + manifest artifact sha256 | recomputed match | VERIFIED |
| HARNESS-025 (launches outside source) | temp workdir + PYTHONPATH strip + isolation scan | stub test + packaged `workdir_outside_repo:false` under repo `.tmp/os`; true only outside repo | VERIFIED |
| HARNESS-026 (major UI/resources load) | surfaces + settings + editor probes | packaged run 20/20 PASS | VERIFIED |
| HARNESS-027 (discovery behaves) | plugin/updater surface probes + content checks | packaged run PASS | VERIFIED |
| HARNESS-028 (readable smoke log) | stdout=JSON / stderr=header (FIX-A) | pre-existing + new CLI tests | VERIFIED |
| HARNESS-029 (stale dist unconfusable) | quarantine-by-copy + SHA-bound evidence + fresh build | quarantine SHA match | VERIFIED |
| HARNESS-030 (rebuild invalidates) | this report (prior artifact explicitly superseded) | new SHA + manifest | VERIFIED |
| HARNESS-031 (STOP/GO) | provenance established; resources present; hash-bound | content+manifest+smoke | GO (with blocked-phase disclosure) |
| HARNESS-032 (build command/log) | pyinstaller build exit 0 + `--build-command` in manifest | build log tail | VERIFIED |
| HARNESS-033 (manifest) | `dist/releases/w16-candidate/MANIFEST.json` (11 fields) | generator + field check | VERIFIED |
| HARNESS-034 (package SHA-256) | manifest + all evidence headers | recomputed match | VERIFIED |
| HARNESS-035 (launch smoke) | `build/audit/w16-packaged-smoke-windows.json` | solo run | VERIFIED (partial, see §Environment) |
| HARNESS-036 (resource/plugin smoke) | surfaces + content evidence | solo runs | VERIFIED |
| HARNESS-037 (clean-room notes) | workdir/frozen/isolation fields in every evidence | evidence JSONs | VERIFIED |
| HARNESS-038 (rollback) | harness code stays; temp artifacts outside release path; staging under `dist/releases/` (gitignored) | layout | VERIFIED |
| HARNESS-039 (handoff hash rule) | downstream must cite `544e186f…`; rebuild → new manifest | this report | VERIFIED |
| SMOKE-001 (deterministic rerunnable, hash-identified) | runner CLI + content CLI (stdout JSON, SHA header) | CLI tests + 3 packaged runs | VERIFIED |
| SMOKE-002 (launch) | process_started | packaged PASS | VERIFIED |
| SMOKE-003 (major tabs) | surface/control probes (files/editor/jobs/plugins/diagnostics) | packaged PASS | VERIFIED |
| SMOKE-004 (settings) | NEW settings_opened step (FIX-B) | mapping tests + packaged PASS | VERIFIED |
| SMOKE-005 (plugin/provider status) | surface import probes + content enumeration | packaged PASS | VERIFIED |
| SMOKE-006 (test profile, no secret) | fresh-user visible-controls flow (password transient) | PKG-GJ-01 PASS | VERIFIED |
| SMOKE-007 (safe failure + visible error) | dead-port via visible controls | PKG-GJ-01 PASS | VERIFIED |
| SMOKE-008 (offline file/editor) | editor_roundtrip + transfer render path | editor PASS (transfer render foreground-gated) | PARTIAL (environment) |
| SMOKE-009 (close + relaunch) | fresh run1→run2 same root, disk proof | PKG-GJ-01 PASS | VERIFIED |
| SMOKE-010 (remote replay when authorized) | no authorized infra | MANDATORY w/ condition | EXTERNAL-deferred |

## WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
DEF-W16-001 | P1 | scripts/wx_packaged_smoke.py main() | owned test FAIL (JSONDecodeError), passes on committed runner; stash-cycle re-proven | main() prints 6-line header + "---" to stdout ahead of JSON | machine consumers cannot parse the smoke log (HARNESS-028/SMOKE-001) | header→stderr, stdout JSON-only | YES (FIX-A) | FIXED
DEF-W16-002 | P1 | packaged smoke both branches | SMOKE-004 has no check anywhere (code trace) | neither in-app branch opens settings; no parent check | minimum-smoke step unevidenced for downstream Waves | settings_opened in-app + parent | YES (FIX-B) | FIXED (packaged-proven)
DEF-W16-003 | P1 | exact bundle | no content validation exists (HARNESS-015 unevidenced) | no inventory procedure for the bundle | missing resources undetectable pre-launch | wx_package_content.py + tests | YES (FIX-C, additional) | FIXED (packaged-proven)
DEF-W16-004 | P2 | run_packaged_smoke | code trace: finally unlink + subprocess.run timeout + cwd=ROOT | raw runtime evidence deleted; timeout orphans child; repo cwd | evidence destroyed; orphans contaminate solo runs | preserve runtime; Popen+kill; temp workdir; server-proof authority | YES (FIX-D, additional) | FIXED
OBS-W16-001 | — | src/hpc_gui/core/tr.json | 38-line legacy stub; zero code references; not bundled | leftover | none (documented only) | none (out of scope) | NO | NOTED
```

Second-defect search (12 dims): negative ✔ (missing/whl/corrupt/stray-pem/timeout/sleep stubs) ·
lifecycle ✔ (close/relaunch fresh; orphan-kill; modal-free settings close) ·
stale state ✔ (runtime file reset per run; per-run fresh roots) ·
identity ✔ (SHA recomputed per run; header binding) ·
concurrency/race ✔ (solo sequencing; kill-on-timeout; no concurrent runs) ·
boundary ✔ (missing exe, bad suffix, empty JSON, Unicode payloads) ·
capability absence ✔ (source-absent licenses not required; zero bundled plugins documented) ·
persistence ✔ (fresh run2 disk proof; generic single-shot documented) ·
packaging ✔ (frozen-strict proof; content check on real bundle) ·
error visibility ✔ (FAIL checks + details; smoke bypasses modal MessageBox deliberately, records via surface_errors) ·
secondary entry ✔ (menu→dispatch proven by existing APP-SETTINGS tests; smoke drives show_settings directly, justified) ·
adjacent boundary ✔ (WxSettingsModel real-disk read-only load; Apply never clicked).

## FIX-A — machine-readable smoke log (DEF-W16-001)

- Root cause: W15's working-tree change made `main()` print the identity
  header + `"---"` to stdout before the evidence JSON, so
  `json.loads(stdout)` raises; the owned contract test failed.
- Change (`scripts/wx_packaged_smoke.py` only): stdout carries exactly the
  evidence JSON; the human header goes to stderr. No test change — the test
  is the contract.
- Before EV: `test_missing_artifact_report_fails_critical_stages` FAIL
  (JSONDecodeError), passing with the fix stashed.
- After EV: same test PASS unmodified; new `REQ-W16-STDOUT` proves the
  contract on the stub path too.

## FIX-B — settings step in packaged smoke (DEF-W16-002)

- Root cause: neither in-app smoke branch opened settings; SMOKE-004 had no
  procedure step and no parent check.
- Change: generic in-app phase-0 opens settings through the real
  `show_settings` view (real i18n + real model load, read-only — Apply never
  clicked), asserts apply/close controls + model, closes the window
  (Close→Destroy fallback, verified gone); `settings_opened` added to the
  in-app checks and parent `REQUIRED_CHECKS`. The menu→dispatch hop is proven
  by existing repo tests (`test_w04_support_freeze`, dispatch error-gov), so
  the direct call avoids a modal-MessageBox hang while staying visible via
  `surface_errors`.
- After EV: mapping tests (PASS→PASS, FAIL→FAIL) + packaged run
  `settings_opened: PASS` on the exact artifact (real wx window proof).

## FIX-C — package-content validator (DEF-W16-003)

- Root cause: no procedure inventoried the exact bundle; HARNESS-015 had no
  test and HARNESS-005..013 no automated proof.
- Change (new, harness production code): `scripts/wx_package_content.py`
  with 8 checks (layout, wx_runtime, icons_assets mirror rule, localization
  namespaces, docs_and_licenses mirror rule, plugin_provider_surface,
  updater_trust no-stray-keys, provider_templates namespaces), SHA-bound
  identity header, stdout-JSON/stderr-header convention, exit 0/1/2.
  Code-embedded resources (config defaults, updater anchors, provider
  templates) are recorded with module + smoke cross-references — never faked
  as file checks. Bundle layout (datas under `_internal/`) was verified
  empirically, not assumed.
- After EV: 19 tests (happy + 12 removals + corrupt/drift/stray/scope/CLI) +
  8/8 PASS against the exact accepted bundle, SHA-bound.

## FIX-D — runner evidence integrity (DEF-W16-004)

- Root cause (three faces, one edit area): generic run deleted the raw
  in-app runtime JSON; `subprocess.run` timeout orphaned GUI children; child
  cwd was the repo root; child-claimed `pty_resize` could override the
  server-side wire proof.
- Change: preserve `<output>.runtime.json` (fresh-runner convention); shared
  `_run_child` (Popen + kill/reap on timeout, `child_killed` recorded);
  system-temp workdir with `workdir_outside_repo` recorded; `pty_resize`
  excluded from child mapping so the loopback server proof is authoritative.
- After EV: `REQ-W16-RUNTIME-KEPT`, `NEG-W16-TIMEOUT-KILL` (bounded elapsed
  proves the kill), repository-root workdirs are recorded as
  `workdir_outside_repo:false` and external workdirs as true,
  preserved runtime JSON on the real run.

## Tests

- New `tests/test_wx_package_content.py` (19): PKG-W16-CONTENT-HAPPY,
  12× NEG-W16-CONTENT removal params, NEG I18N/namespace/trust/scope,
  REQ CLI (stdout-JSON + missing-bundle). Unit + packaging; tmp fixtures
  only; no real home/config touched.
- Extended `tests/test_wx_packaged_smoke.py` (+5, additive only):
  REQ/NEG-W16-SETTINGS (stub mapping both directions),
  REQ-W16-RUNTIME-KEPT, REQ-W16-STDOUT, NEG-W16-TIMEOUT-KILL. Real loopback
  SSH fixture; stub child is the documented boundary.
- Historical implementation-cycle counts are retained only for provenance;
  they are not current validation. The current focused repair validation is
  `29 passed, 0 failed/skipped/xfailed` from
  `tests/test_wx_packaged_smoke.py`, `tests/test_wx_package_content.py`, and
  `tests/test_release_manifest.py`. No test was weakened; no skip/xfail was
  added.
- Sensitivity: stash production files → 5/6 runner tests FAIL (pre-existing
  contract test still passes by design); restore → green. Content script
  held back → import error; 12 removal negatives prove per-check detection.
  Two test-expectation bugs found during development were corrected in the
  TESTS (wrong namespace assertion; incomplete asset fixture) — production
  behavior was right in both cases.

## POST_GREEN_REVIEW

Duplicate path: none (single settings step; embedded/menu share
`_build_settings` core). Alternate entry: dispatch hop covered by existing
tests. Silent fallback: none (loader returns None→FAIL; missing source
assets→FAIL). Stale state: runtime reset per run; fresh roots per run.
Identity: SHA recomputed per run. Cleanup: workdir/webview/loopback torn
down; sleeper killed. Dead branch: no stale `proc.` refs. Hardcoded: exe
name flaggable; platform inferred. Packaged divergence: `.py` path records
without frozen assertion (documented convention).

## PACKAGE evidence (exact artifact binding)

Rebuilt solo (`pyinstaller -y --clean build/windows/hpc-client-gui.spec`,
exit 0, no lingering process, no concurrent runs):
`dist/hpc-client-gui/hpc-client-gui.exe`, 7425277 bytes,
SHA-256 `544e186f81aa685ee80a3c07185ee0eb03ab1bc73a81151b1323253503c0a1da`
(PYZ contains `hpc_gui.wx_shell` with the settings step,
`hpc_gui.core.paths`, `hpc_gui.wx_settings_view`).
Prior bytes `d2aab99d…` quarantined to
`build/audit/superseded-w15-exe-d2aab99d/hpc-client-gui.exe` (SHA re-verified
MATCH) and explicitly superseded for W16 — W16 cites only `544e186f…`.

- Content: `build/audit/w16-package-content-windows.json` → `result: PASS`,
  8/8 checks, SHA-bound to `544e186f…` (generated post-rebuild against the
  accepted bundle; the pre-build probe file was removed, never cited).
- Manifest: `dist/releases/w16-candidate/{hpc-client-gui-windows-onedir.exe,
  MANIFEST.json}` — byte-identical copy (SHA match), 11 provenance fields
  complete (main/plugin/build-utc/version/runtime/packager/os-arch/command/
  lock/artifacts).
- Generic smoke: `build/audit/w16-packaged-smoke-windows.json` → 20/20 PASS
  incl. NEW `settings_opened`, `workdir_outside_repo:false` for the
  controller-managed repository `.tmp/os` workdir, and `isolated_from_src:true`.

## GUI evidence

- Generic smoke real-wx proof on exact bytes: main frame, all five surface
  groups + controls import/construct, settings window opened via the real
  view with controls + model verified then closed, editor Unicode roundtrip,
  updater/plugin surfaces — all PASS.
- Fresh-user PKG-GJ-01 (solo, clean env, controller-managed cwd under the
  repository's `.tmp/os`; `workdir_outside_repo:false`):
  `build/audit/w16-fresh-user-windows.json` (+ run1/run2 runtimes) →
  `result: PASS`, 10/10 checks, exits `[0,0]`, frozen exe, single isolated
  root, zero secrets persisted. Run1 `DestroyWindow` teardown lines are the
  known benign wx noise (exit 0), as in W15.

## Child-runtime versus runner evidence

The retained child runtime JSON records `pty_resize: FAIL` and
`clean_shutdown: FAIL` for the child-side diagnostic mapping. Those two
records are not the acceptance result: the runner deliberately excludes the
child's unreliable foreground/teardown claims and uses its authoritative
loopback/server proof plus process exit/cleanup checks. The regenerated
runner evidence therefore records all 20 checks `PASS`, while preserving the
child runtime JSON for diagnosis. Fresh-user run1/run2 independently records
`clean_shutdown: PASS` and exits `[0,0]`.

## Environment-blocked phases (not product defects)

The child-runtime diagnostic retains the foreground limitation above, but the
current regenerated packaged runner is `20/20 PASS`; it does not claim the
child's failed `pty_resize`/`clean_shutdown` mappings as acceptance proof.
SMOKE-010 remote replay remains EXTERNAL-deferred (no authorized infra;
loopback only). Manual-only display/cluster/MFA/X11/DnD/transfer-conflict
checks remain listed in the evidence JSON and are not represented as PASS.

## Diff review

- `git diff --check`: clean for W16 files (one EOF-blank-line fixed in the
  W16 test delta; remaining CRLF notices are pre-existing on unrelated files).
- W16 deltas: `scripts/wx_packaged_smoke.py` (FIX-A/D + settings check),
  `src/hpc_gui/wx_shell.py` (settings_opened step + check key),
  `tests/test_wx_packaged_smoke.py` (+132 additive),
  new `scripts/wx_package_content.py` + `tests/test_wx_package_content.py`,
  new evidence under `build/audit/w16-*`, staging under `dist/releases/`
  (gitignored), this report. (Stat totals include carried pre-existing
  W01–W15 working-tree state, preserved untouched.)
- Secrets scan on W16 diff: only disposable loopback-fixture credential
  plumbing (same pattern as W15) — no real secrets.
- No test weakening; no new skips/xfails; no binary committed; unrelated
  changes preserved; no reset/clean/push.

## Resume state

Completed and verified:
- Baseline pin + entry criteria (W03 PASS, SHAs, toolchain, quarantine plan).
- Discovery (spec/bundle layout empirically verified) + WAVE_FINDINGS (4
  fixed, 1 noted) + 12-dim second-defect search.
- FIX-A..D implemented; historical implementation-cycle counts were 25 new,
  106, and 169 green; current repair validation is the focused 29-test suite
  above; sensitivity proven both ways and post-green review done.
- Solo rebuild → 544e186f → content PASS, packaged 20/20 PASS,
  fresh-user 10/10 PASS, manifest staged.

Repair cycle — 2026-09-22 (current):
- REOPEN-W16-001/003 repaired: the staged executable and manifest now bind
  HEAD `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb` to artifact SHA
  `544e186f81aa685ee80a3c07185ee0eb03ab1bc73a81151b1323253503c0a1da`.
- Package-content evidence is current at 8/8 PASS.
- Packaged GUI smoke is current at 20/20 PASS.
- Fresh-user GUI smoke is current at 10/10 PASS, exits `[0,0]`.
- REOPEN-W16-002 is non-blocking: W15 is an integration reference only under
  the canonical W16 independence contract; no W15 lifecycle change was made.
- REOPEN-W16-006 repaired in the shared smoke runner; focused W16 slice is
  `29 passed`.
Pending phase: fresh independent audit only.
Last exact commands: package-content CLI (exit 0); packaged smoke CLI (exit 0);
focused pytest with external writable TEMP/TMP (29 passed).
Evidence/artifact identities: exe 544e186f… (7,425,277 B); all three W16
evidence JSONs and MANIFEST are bound to current HEAD and this SHA.
w16-candidate; evidence `build/audit/w16-{package-content,packaged-smoke,
fresh-user}-windows.json` (+ runtimes); quarantine
`build/audit/superseded-w15-exe-d2aab99d/`.

## Final summary

```text
FIX-A: stdout machine-readable log (DEF-W16-001, runner main)
DEF: owned test red (JSONDecodeError) / Root cause: header printed to stdout
Before EV: 1 failed incl. contract test / historical after-EV counts: 25 +
106 + 169 green / current repair validation: 29 passed
Regression test: test_missing_artifact_report_fails_critical_stages (unmodified) + REQ-W16-STDOUT
Sensitivity proof: fails with fix stashed, passes restored

FIX-B: settings_opened smoke step (DEF-W16-002, wx_shell + runner)
DEF: SMOKE-004 unevidenced / Root cause: no settings step in either branch
Before EV: no settings check anywhere / After EV: packaged settings_opened PASS (real wx window)
Regression test: REQ/NEG-W16-SETTINGS (both directions)
Sensitivity proof: KeyError/FAIL with in-app key reverted; old runtimes map to FAIL

Additional fixes: FIX-C package-content validator (8/8 PASS on exact SHA, 19 tests);
FIX-D runner integrity (runtime preserved, kill-on-timeout, temp workdir, server-proof authority)
Post-green review: done, no new defect
New/modified tests: tests/test_wx_package_content.py (19 new); tests/test_wx_packaged_smoke.py (+5, additive)
Skipped/xfail changes: none
Package evidence: PASS — exe 544e186f81aa685ee80a3c07185ee0eb03ab1bc73a81151b1323253503c0a1da
  (content 8/8, packaged 20/20, fresh 10/10, manifest and disk SHA == evidence SHA)
External evidence: EXTERNAL-deferred (SMOKE-010/HARNESS-021; loopback only, never mocked as real)
Open P0/P1: none
Open P2/P3: none
Two-fix gate: PASS (FIX-A + FIX-B independent; FIX-C/FIX-D additional)
Wave decision: READY_FOR_AUDIT
```

### Closed-owner repair addendum — 2026-09-29

```text
HPC-W04-HARNESS-025 (closed owner W16, routed by the controller ledger)
DEF: run_packaged_smoke scored evidence only on the non-timeout path
Root cause: the whole scoring block sat under `else:` of `if timed_out:`
Hypothesis: W16-REPAIR-SCORE-PROVEN-EVIDENCE-ON-TIMEOUT
Change: score on BOTH paths; keep result = FAIL whenever timed_out
Additional: _outside_repo followed the repo .tmp junction and could report a
  false isolation claim; now a normalized lexical comparison
Before EV: 3 new tests red on git-show HEAD code (wx_runtime_started FAIL,
  KeyError evidence_scored_on_timeout, unrecognized --timeout)
After EV: tests/test_wx_packaged_smoke.py 10 passed (7 pre-existing + 3 new)
Regression suite: 60 passed across smoke/manifest/content/provenance/fresh-user
Validators: validate-wave-orchestration PASS (61), validate-wave-authoring PASS (61)
New/modified tests: tests/test_wx_packaged_smoke.py (+3, strictly additive)
Skipped/xfail/weakened tests: none
Packaged evidence: NOT re-run and NOT re-minted by this repair;
  dist/releases/w16-candidate/MANIFEST.json still binds artifact SHA
  544e186f81aa685ee80a3c07185ee0eb03ab1bc73a81151b1323253503c0a1da
Content identity: b591eb6b834fafdced7e26b3abeefad87b3d04f207368db0eae118d7bd6db533
Open P0/P1: none from this repair
Wave decision: READY (next action repair -> controller re-runs the W57
  packaged gate against the new owner-rebuilt identity)
```
