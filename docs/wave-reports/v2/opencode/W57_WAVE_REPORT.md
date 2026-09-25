# W57 Wave Report — Packaged regression, support finalization and freeze (run phase)

Wave:
Canonical report path: `docs/wave-reports/v2/opencode/W57_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA: `36d6151fd9634cf50e14a639ec0407bef1d296f4` (W56 frozen main SHA; packaged candidate base)
Tested implementation SHA: `7f3e92b3ba3818b16923388b30ad7bd7aae024c0` (docs/test-only delta over baseline; no src/build/requirements diff)
Current HEAD: `7f3e92b3ba3818b16923388b30ad7bd7aae024c0`
Plugin/external repo SHA(s), if applicable: in-tree at same HEAD (no separate registry repo)
Content identity (controller handoff): `c159f8bff53256a034239b5b5bdc19ff0f5823f4c088d15a9f2f08fa5c62e244`
Audit receipt (authoritative handoff): W56 `PASS` at `36d6151f` (normalized receipt `.tmp/agent-runs/ac-wave-opencode-parallel/20260925-074235-63df86b0/0019-W56-audit-normalized.json`)
First started: 2026-09-25 (prior run session `ses_f28c68d44ffeNNM52nDfznGacI`)
Last updated: 2026-09-25 (this run phase, opencode executor)
Session status: COMPLETE (run evidence current; ownership escape recorded)
Wave decision: NO-GO for freeze this run (P3 DEF-W57-001 routed to owner W28; rebuild + rerun required)

Execution mode: unattended, non-interactive. No user questions asked. No secrets requested or invented. No destructive Git performed.

## Mandatory authority consumed

1. `waves/pending/W57.md` (wave_id W57, execution kind, canonical_source W57, 36 source-derived IDs + 10 TODO-detail IDs, start gate NONE, cohort P13-candidate-freeze, required evidence GUI/PACKAGE/EXTERNAL).
2. `opencode/REQUIREMENT_REGISTRY.md` — all rows with Owning Wave `W57` read (FREEZE-005/009/010/011/013/019-048, PKGREG-001).
3. `opencode/TODO_OWNERSHIP_MAP.md` — all 10 rows with Owning Wave `W57` read (RUNTIME-CUTOVER-002/003, TODO-010/011/012/013/014/015/016/017, all ACTIVE).
4. `opencode/sources/WAVE_V2_FINAL_10.md` → Scope (35-44), Workstream G Packaged regression (314-316), Workstream H Defect triage (318-339), Workstream I Support matrix finalization (341-348), Acceptance criteria (350-361), Required evidence (375-386), Rollback (404-406), Handoff to W11 (408-410), plus strict execution protocol and repo-truth rule.
5. Project profile `.opencode/protocol/WAVE_PROJECT_PROFILE.json` (HPC, W01-W61, temp root `.tmp/`).
6. Lab protocol `.opencode/protocol/LOCAL_REAL_HPC_LAB.md` (LOCAL_REAL_HYPERV + LOCAL_PASSWORD_REAL fixture).
7. Live code/tests before edits: `src/hpc_gui/wx_jobs.py` (refresh label paths), `src/hpc_gui/i18n/en.json` + `tr.json` (jobs keys), `src/hpc_gui/runtime.py` (wx default), `docs/wiki/` matrix + install docs, `tests/test_w57_freeze_consistency.py`, `dist/hpc-client-gui/hpc-client-gui.exe` (frozen artifact).

No short summary, chat log, or historical report was substituted for these reads.

## Baseline capture

- `git branch --show-current`: `develop`
- `git rev-parse HEAD`: `7f3e92b3ba3818b16923388b30ad7bd7aae024c0`
- `git status --short --branch`: `## develop`, `?? artifacts/wave_W57/` (run freeze-declaration artifact, untracked; no product modification in working tree)
- `git log -1 --oneline --decorate`: `7f3e92b3 W57 run: wx-only support-matrix/install docs realignment + freeze-consistency regression test`
- `git diff 36d6151f..HEAD --stat`: wave-report/audit artifacts for W56 + `docs/wiki/` (6 files) + `tests/test_w57_freeze_consistency.py`; `git diff 36d6151f..HEAD -- src/ build/ requirements.txt requirements-release.lock pyproject.toml`: empty (no product/package/runtime change; W56 freeze intact)
- `git diff --check`: clean. Scoped `ruff` (`wx_jobs.py`, `runtime.py`, `test_w57_freeze_consistency.py`): clean.
- Build/verify Python: system `3.12.4` for hermetic checks; frozen artifact reports `python: 3.14.0`, wxPython `4.3.1`, PyInstaller `6.22.2`.

## Discovery pass

- Pinned SHAs above; working tree clean except untracked run artifact.
- Rediscovered live symbols: `t("jobs.refreshing")` at `wx_jobs.py:1319` (no `_has_key` fallback, unlike the three sibling paths at 1354/1360/1383 which have English fallbacks); `t("jobs.refresh")` Qt-widget fallbacks use `"Yenile"` literal; i18n bundles define `jobs` + `jobs_outputs` only (no `jobs.refresh*` family).
- Existing tests touching paths: `tests/test_w57_freeze_consistency.py` (new, contract), `tests/test_w04_support_freeze.py` (matrix freeze), `tests/test_wx_w55_shell_soak.py` (lifecycle soak), `scripts/check_i18n.py` (release preflight gate).
- Narrow pre-change slice: `test_w57_freeze_consistency` 5 passed; `check_i18n.py` FAILED (4 missing keys) — reproduced before any edit by this run.
- Adjacent boundaries inspected: `jobs_refresh_state.py` service (sequence/stale semantics intact), `command_registry.py` (`JOB-REFRESH` mapping intact), `wx_jobs.py` refresh state machine (in_flight/pending/sequence guards intact).

WAVE_FINDINGS:

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
DEF-W57-001 | P3 | Jobs tab refresh status label (wx_jobs.py:1319) | scripts/check_i18n.py FAILED (4 missing keys); en/tr.json lack jobs.refreshing/refresh_updated/refresh_failed_stale/refresh_failed | i18n keys never added when W28 refresh status landed; refreshing path lacks _has_key fallback | status label renders raw key jobs.refreshing during refresh; other three paths fall back to English | add 4 keys EN+TR in owner Wave (product/i18n change) | NO (not fixed here; cross-owner) | ROUTED to W28 (CLOSED) via controller closed-owner repair; W57 does not patch frozen candidate
DEF-W57-002 | Release-contract | docs/wiki matrix + install docs advertised Qt/PySide6 + 1.2.6 vs frozen 1.5.9 wx candidate | pre-7f3e92b3 text vs pyproject 1.5.9 + artifact 6cca43a5 | stale pre-cutover wording | users misled about runtime/deps | realign EN+TR matrix + Linux/Windows install docs | YES (done, committed at 7f3e92b3; docs/test only) | VERIFIED
```

Second-defect search (12 dimensions): negative paths checked (invalid-password rejection via LOCAL_PASSWORD_REAL in prior replay; packaged invalid-profile path via doctor); lifecycle checked (soak 2 passed; shutdown semantics owned by W53, not re-proven here); stale state checked (refresh sequence guards intact); identity checked (profile isolation owned by W52, not re-proven); concurrency checked (overlapping-refresh guard intact); boundary values N/A (no new parser); capability absence checked (Qt tokens absent); persistence checked (clean-profile probe profiles:0); packaging checked (SHA + frozen:True + zero-Qt); error visibility checked (DEF-W57-001 is the open visibility gap); secondary entry points checked (Qt widget path has literal fallback, wx path is the gap); adjacent integration checked (service/state separation intact). Two legitimate defects found (one fixed docs-contract, one routed product P3); no manufactured fixes.

## Implementation (this Wave)

Committed at HEAD `7f3e92b3` (prior run commit, verified — not rebuilt — by this run):

- `docs/wiki/Compatibility-and-Support-Matrix.md` + `-TR.md`: wx-only realignment (version = pyproject `1.5.9`, wxPython production runtime, no Qt-runtime row, no PySide6-provided claim).
- `docs/wiki/Installation-Linux.md` + `-TR.md`: wxPython (wxWidgets) prerequisite, no Qt platform libs, current version artifacts only.
- `docs/wiki/Installation-Windows.md` + `-TR.md`: version alignment.
- `tests/test_w57_freeze_consistency.py` (92 lines): 5 contract/regression tests (REQ-FREEZE-035/042/011) with purpose IDs, taxonomy, no mocks, behavioral assertions on committed text.
- Deliberately NOT changed: any product/i18n/bundle/spec/lock file (would invalidate W56 freeze). DEF-W57-001 left for owner W28.

This run added no new product diff; it re-verified the above and produced this canonical report plus the untracked freeze-declaration artifact `artifacts/wave_W57/W57_FREEZE_DECLARATION.md` (run ledger; controller persists).

## Tests and evidence (fresh, at 7f3e92b3 unless noted)

- EV-W57-001 `test_w57_freeze_consistency`: `python -m pytest tests/test_w57_freeze_consistency.py -q` → 5 passed, 0 failed/skipped, exit 0. Sensitivity proven by fault injection (prior run record; assertions fail if Qt row/version drift reintroduced).
- EV-W57-002 `test_w04_support_freeze`: 28 passed, exit 0.
- EV-W57-003 version/entry helpers: `test_version_consistency + test_remote_entry_helpers` → 13 passed, exit 0.
- EV-W57-004 qt/unicode/wheel: `test_qt_removal_gate + test_wave0_unicode_baseline + test_wheel_packaging` → 61 passed, exit 0.
- EV-W57-005 lifecycle soak: `test_wx_w55_shell_soak` → 2 passed, exit 0.
- EV-W57-006 static: `compileall src` exit 0; scoped `ruff` clean; `git diff --check` clean; whole-repo `ruff` 281 pre-existing errors (static-debt record, not introduced by W57).
- EV-W57-007 maintained gates: `scripts/ci.py docs` PASS (branding/release-surface/wiki/wheel all OK); `scripts/ci.py packaging` PASS; `scripts/ci.py audit` PASS (no vulnerabilities); `scripts/ci.py full` FAIL at `check_i18n.py` (4 missing keys = DEF-W57-001). This is the single red gate.
- EV-W57-008 packaged probes (exact artifact `6cca43a5…e530e`, cwd outside repo): `hpc-client-gui.exe version` → `1.5.9 / python 3.14.0`; `doctor environment` (isolated `HPC_GUI_CONFIG_ROOT`) → `status: PASS, frozen: True, profiles: 0`; `--help`/commands inventory OK; exe size 7672473; bundle 172 files, zero Qt tokens (no PySide6/shiboken6/Qt6.dll). Source-independence proven (outside-repo cwd).
- EV-W57-009 external (same artifact SHA; prior held-lease replay carried over truthfully, behavior diff empty): LOCAL_REAL_HYPERV connection + reconnect PASS, SFTP 65536-byte round trip SHA-match PASS, remote editor save server-hash PASS, Slurm submit → RUNNING on compute02 → cancel → CANCELLED PASS, PTY /dev/pts/0 PASS, lab cleanup done; LOCAL_PASSWORD_REAL password-success + invalid-password-rejection PASS via product transport library, fixture torn down, no secrets persisted. Lab profile present this run (`hpc-client-profile.json` exists); no new external run executed this phase because the single red gate already forces owner-repair + rebuild + full rerun — a second concurrent lease would not advance acceptance.
- EV-W57-010 GUI: wx event/runtime proof via soak suite (above) + prior Workstream E replay; no static-only substitution for owned GUI claims. Full GJ-01..GJ-10 replay belongs to W45-W53/W58 cohorts, not re-proven here.

## Requirement dispositions (owned IDs)

- FREEZE-005 (support-matrix reconciliation): VERIFIED (matrix realigned, EV-001/002).
- FREEZE-009 (packaged acceptance): PARTIAL (packaged probes PASS on frozen SHA, but FREEZE-029 red blocks acceptance).
- FREEZE-010 (defect triage): VERIFIED (ledger current: 0 P0/P1, 0 open P2, 1 open P3 with owner/decision).
- FREEZE-011 (documentation consistency): VERIFIED (wiki/install aligned, `ci docs` PASS).
- FREEZE-013 (small stabilization only): VERIFIED (docs/test-only delta; no product patch).
- FREEZE-019/020 (P0/P1 NO-GO): VERIFIED (0 open).
- FREEZE-021/022 (P2/P3 deferral): VERIFIED (P2 none; P3 DEF-W57-001 with impact/owner/decision).
- FREEZE-023/024/025/026 (matrix truth): VERIFIED (no stale Supported; Experimental explicit; prerequisites + provider limits current per realigned matrix + W04 freeze).
- FREEZE-027 (W01 Supported rows evidenced): VERIFIED via W04 freeze + realigned matrix (no new Supported claimed here).
- FREEZE-028 (invalidated evidence rerun): VERIFIED (behavior diff empty; affected slices re-run above).
- FREEZE-029 (full suite green or accepted deviation): FAILED (ci full red on P3 i18n; not release-accepted as green — owner repair required).
- FREEZE-030 (real-cluster regression): VERIFIED for current SHA via carried replay (same bytes); must rerun after rebuild.
- FREEZE-031 (candidate SHA + provenance): VERIFIED (`36d6151f` + artifact `6cca43a5…e530e`, wx 4.3.1 / PyInstaller 6.22.2 / Win11 AMD64).
- FREEZE-032 (packaged regression vs frozen): PARTIAL (probes PASS; gate blocked by FREEZE-029).
- FREEZE-033 (no P0/P1): VERIFIED.
- FREEZE-034 (every P2/P3 decided): VERIFIED (DEF-W57-001 decided + routed).
- FREEZE-035 (matrix/docs match candidate): VERIFIED (EV-001).
- FREEZE-036 (candidate unambiguous): VERIFIED (rollback section in freeze declaration; no ambiguous overwrite).
- FREEZE-037..046 (evidence set): VERIFIED except 029-red noted (matrix, logs, static logs, cluster replay, packaged probes, matrix, ledger, manifest, SHA, declaration all present).
- FREEZE-047 (rollback identifiable): VERIFIED.
- FREEZE-048 (W11 handoff frozen-only): BLOCKED (no frozen successor yet; W58 consumes successor, not this record).
- PKGREG-001: VERIFIED (exact-SHA packaged regression executed, not source execution).
- TODO RUNTIME-CUTOVER-002/003: VERIFIED (no rebuild by W57; packaged suite re-run against post-cutover SHA `6cca43a5`).
- TODO-010 (clean-profile first run): VERIFIED (isolated first run PASS).
- TODO-011 (OpenSSH password/key/host-key): VERIFIED via carried LOCAL_PASSWORD_REAL + LOCAL_REAL replay.
- TODO-012 (PTY): VERIFIED via carried replay.
- TODO-013 (SFTP CRUD): VERIFIED via carried replay.
- TODO-014 (Slurm): VERIFIED via carried replay.
- TODO-015 (error/recovery): PARTIAL (negative paths proven except DEF-W57-001 visibility gap).
- TODO-016 (shutdown/soak): VERIFIED (soak 2 passed).
- TODO-017 (final report tied to SHA): BLOCKED until rebuild (this report ties to current SHA truthfully but is not the frozen successor).

## Diff review

- `git diff --stat 36d6151f..HEAD`: only W56 artifacts + docs/wiki (6) + 1 test file. No src/build/requirements/pyproject diff.
- `git diff --check`: clean. No secrets, no binaries, no generated noise, no weakened tests, no duplicated logic.
- Untracked `artifacts/wave_W57/W57_FREEZE_DECLARATION.md`: run ledger only (no product bytes).

## Post-green review

Green suites do not close the Wave because `ci full` is red. Alternate paths checked: Qt widget `jobs.refresh` path has literal fallback (safe); wx refreshing path is the sole raw-key renderer. No silent fallback hides backend errors elsewhere in owned surface. No wrong-identity/cleanup regression introduced (docs/test-only delta). No dead branch added. Packaged resource divergence: none (bundle unchanged).

## Report / evidence requirements

- This canonical report: created/updated at the exact required path (no session-suffixed copies).
- Fresh-context audit report `W57_AUDIT_REPORT.md`: NOT written by this run worker (independent audit owns it; self-audit would violate `audit_policy: fresh-independent`).
- Freeze declaration `artifacts/wave_W57/W57_FREEZE_DECLARATION.md`: run artifact truthfully marked `Frozen for W58: NO`, successor required.

## Stop condition

Cross-Wave ownership escape (DEF-W57-001 owned by CLOSED W28) + red mandatory gate FREEZE-029. No user question asked. Exact blocker + resume point recorded; exit cleanly without patching the frozen candidate and without starting downstream Waves.

## Resume state

Completed and verified:
- Support-matrix/install wx-only realignment + freeze-consistency tests (7f3e92b3)
- Focused suites (5+28+13+61+2) green; static/diff gates clean; ci docs/packaging/audit PASS
- Packaged identity proven (SHA 6cca43a5, frozen True, 1.5.9, zero Qt)
- External replay carried over for same bytes; defect ledger current

In progress: none (run evidence current)

Open P0/P1: none

Open P2/P3:
- DEF-W57-001 P3 (jobs.refresh* i18n keys; owner W28 CLOSED) — controller closed-owner repair, then rebuild, then rerun affected W56/W57 evidence

Pending tests/evidence:
- Rerun `scripts/ci.py full` + packaged regression + LOCAL_REAL replay against the post-repair NEW candidate SHA
- Issue successor freeze declaration; W58 consumes successor unchanged

Last exact commands run:
- `python -m pytest tests/test_w57_freeze_consistency.py -q` → 5 passed
- `python -m pytest tests/test_w04_support_freeze.py -q` → 28 passed
- `python -m pytest tests/test_version_consistency.py tests/test_remote_entry_helpers.py -q` → 13 passed
- `python -m pytest tests/test_qt_removal_gate.py tests/test_wave0_unicode_baseline.py tests/test_wheel_packaging.py -q` → 61 passed
- `python -m pytest tests/test_wx_w55_shell_soak.py -q` → 2 passed
- `python scripts/ci.py docs|packaging|audit` → PASS; `scripts/ci.py full` → FAIL (check_i18n 4 missing)
- packaged `version` + `doctor environment` (outside-repo cwd, isolated config root) → PASS
- artifact SHA-256 recomputed → `6cca43a5a98a2c7049aae182b58473db4c491dabc06b13cf599bd429e45e530e`

Next actions:
1. Controller routes DEF-W57-001 to W28 via closed-owner repair transaction (add 4 EN+TR keys with fallback discipline).
2. Rebuild candidate from repaired commit; record NEW main/plugin/artifact SHAs.
3. Rerun affected W56/W57 evidence (ci full, packaged regression, LOCAL_REAL replay) against NEW SHA; issue successor freeze declaration.
4. Dispatch independent audit for W57 against successor; W58 consumes successor unchanged.

Evidence/artifact identities:
- Candidate main SHA: `36d6151fd9634cf50e14a639ec0407bef1d296f4`
- Tested HEAD: `7f3e92b3ba3818b16923388b30ad7bd7aae024c0` (docs/test-only)
- Artifact: `dist/hpc-client-gui/hpc-client-gui.exe` SHA-256 `6cca43a5a98a2c7049aae182b58473db4c491dabc06b13cf599bd429e45e530e`
- Support matrix rev: `docs/wiki/Compatibility-and-Support-Matrix.md` at `7f3e92b3` + `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md`

## Final summary

```text
FIX-A: docs/wiki wx-only support-matrix/install realignment (DEF-W57-002)
DEF: stale Qt/PySide6 + 1.2.6 claims vs 1.5.9 wx candidate
Root cause: pre-cutover wording never realigned after V2 runtime decision
Before EV: matrix/install text named Qt runtime + old version
After EV: EV-W57-001 5 passed; ci docs PASS; matrix/install match pyproject 1.5.9 + wx default
Regression test: tests/test_w57_freeze_consistency.py (5 tests)
Sensitivity proof: fault-injection record (assertions fail on Qt/version drift)

FIX-B: none (second legitimate defect DEF-W57-001 is cross-owner; W57 does not patch frozen candidate)
DEF: DEF-W57-001 P3 jobs.refresh* i18n keys (owner W28)
Root cause: W28 refresh status landed without bundle keys; refreshing path lacks fallback
Before EV: scripts/check_i18n.py FAILED (4 missing)
After EV: N/A (routed, not fixed here)
Regression test: scripts/check_i18n.py (release preflight; currently red, must go green after owner repair)
Sensitivity proof: currently failing for the expected reason (detector proven)

Additional fixes: none
Post-green review: done (alternate Qt path safe; no silent fallback; no identity/cleanup regression)
New/modified tests: tests/test_w57_freeze_consistency.py (new, 5 tests; no weakened tests; no new skips/xfails)
Skipped/xfail changes: none
Package evidence: EV-W57-008 PASS on exact SHA 6cca43a5 (version/doctor/help, frozen True, zero Qt, outside-repo cwd)
External evidence: EV-W57-009 carried LOCAL_REAL_HYPERV + LOCAL_PASSWORD_REAL replay PASS on same bytes; rerun required after rebuild
Open P0/P1: none
Open P2/P3: DEF-W57-001 P3 (owner W28, explicit decision, rebuild + rerun required)
Two-fix gate: docs-contract fix VERIFIED + cross-owner defect ROUTED (no manufactured second product fix; freeze invariant respected)
Wave decision: NO-GO for freeze this run (truthful; successor after owner repair)
```
