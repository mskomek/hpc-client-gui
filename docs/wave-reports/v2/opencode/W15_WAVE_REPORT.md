# W15 Wave Report — Fresh-user clean packaged startup (PKG-GJ-01)

```text
Wave: W15 (original planning Wave W04; provenance only)
Canonical report path: docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: 0f8902a023bac76071527232c2287af96478ed2b
Current HEAD: 0f8902a023bac76071527232c2287af96478ed2b (+ W15 working-tree changes, uncommitted)
Plugin repo SHA: f0abb7e7037e66ab451d463c699fecf4e00c89eb (develop)
First started: 2026-09-19
Last updated: 2026-09-19 (resume cycle 1: REOPEN-W15-001/002 closed, re-bound to d2aab99d… — see §Resume cycle 1)
Session status: COMPLETE (PKG-GJ-01 PASS on fresh exe, solo run)
Wave decision: READY_FOR_AUDIT
```

## Objective

Prove the exact package starts from an isolated clean configuration root and
reaches a usable first-run path without source-tree assistance
(`HPC-W04-CLEAN-001..005`, `HPC-W04-FRESH-001..009`; no TODO-detail rows owned).

## Baseline (pre-change, both repos pinned)

- Main `develop` == `origin/develop` ==
  `0f8902a023bac76071527232c2287af96478ed2b`; working tree dirty with
  pre-existing unrelated changes (W01–W14 working state, preserved untouched).
- Plugin `develop` == `f0abb7e7037e66ab451d463c699fecf4e00c89eb`
  (+ untracked `.github/social-preview.jpg`, preserved).
- `DEFAULT_GUI_RUNTIME=qt` (`src/hpc_gui/runtime.py`); Python 3.12.4;
  PyInstaller 6.19.0; wxPython 4.3.1.
- Narrow pre-change slice green (W14 43-test set):
  `python -m pytest tests/test_w14_provenance_manifest.py
  tests/test_release_manifest.py tests/test_version_consistency.py
  tests/test_release_surface.py tests/test_sync_version.py
  tests/test_wave10_release_gate.py tests/test_release_test_suite.py -q`
  → `43 passed`, exit 0.
- Pre-existing `dist/hpc-client-gui/hpc-client-gui.exe` (2026-09-15,
  SHA-256 `b8fb56d79a086482b2c9714b19be8eebb4966c674366bcf539b0d6afa2a9cf2e`)
  predates the pinned HEAD (2026-09-16) with unknown provenance → declared
  STALE, never used for W15 acceptance. W14 smoke evidence
  `build/audit/w14-packaged-smoke-r1.json` is `result: FAIL`
  (`unsupported artifact type: .whl`) — wheel is not GUI evidence.

## Requirement → owner → test → evidence trace (14 owned rows)

| Requirement | Live implementation owner | Test(s) | Evidence |
|---|---|---|---|
| `HPC-W04-CLEAN-001` (true fresh-user mode) | `scripts/wx_packaged_smoke.py::run_fresh_user_smoke` (`--fresh-user`, PKG-GJ-01) + `HPC_GUI_CONFIG_ROOT` mechanism | `tests/test_w15_fresh_user_startup.py` (11 tests) + packaged run | PASS (exe `d2aab99d…`, solo run, 10/10 checks, exits `[0,0]`) |
| `HPC-W04-CLEAN-002` (launch outside repo) | parent runner `cwd=workdir` under system temp; `details.workdir_outside_repo=true`; parent itself invoked from `C:\Users\mskomek\AppData\Local\Temp\opencode` | `NEG-W15-MISSING`; packaged run | PASS |
| `HPC-W04-CLEAN-003` (no source PYTHONPATH) | `fresh_user_env()` drops `PYTHONPATH`; child env asserted (`assert "PYTHONPATH" not in env`) | `PKG-W15-ENV`; packaged run | PASS |
| `HPC-W04-CLEAN-004` (no dev-only env) | `fresh_user_env()` drops `HPC_GUI_DISABLE_WEBENGINE`; `isolated_config_root()` replaces `Path.home()` | `PKG-W15-ENV`, `REQ-W15-ROOT`; packaged run | PASS |
| `HPC-W04-CLEAN-005` (packaged resource resolution) | `_fresh_src_leakage()` (frozen→module under `sys._MEIPASS`) | packaged run `no_src_leakage` | PASS (frozen exe, `isolated_from_src:true`) |
| `HPC-W04-FRESH-001` (no prior settings/DB) | parent pre-asserts clean root; in-app `first_run_empty_state` | `CON-W15-PROFILE-DIALOG` (fresh env); packaged run | PASS |
| `HPC-W04-FRESH-002` (init logs+settings) | `isolated_config_root()` creates root; `app_log_dir()`→`<root>/logs` | `REQ-W15-ROOT`; packaged run | PASS |
| `HPC-W04-FRESH-003` (first-run/empty-state path) | in-app `first_run_empty_state` (no config.json + zero profiles) | packaged run | PASS |
| `HPC-W04-FRESH-004` (profile via visible controls) | real AddConnection→modal dialog→Save driven by wx events | `CON-W15-PROFILE-DIALOG` + packaged run | PASS |
| `HPC-W04-FRESH-005` (no hand-edited config) | whole flow uses GUI controls + env only | `CON-W15-PROFILE-DIALOG` + packaged run | PASS |
| `HPC-W04-FRESH-006` (success or safe failure) | loopback connect + dead-port connect via ConnectSelected | `NEG-W15-SAFE-FAILURE`, `REQ-W15-CONNECT-STATE` + packaged run | PASS |
| `HPC-W04-FRESH-007` (close + relaunch persistence) | parent run1→run2 same root; in-app `relaunch_state_present` from disk | packaged run | PASS (run2 exit 0, disk-byte proof) |
| `HPC-W04-FRESH-008` (no src-checkout resolution) | `_fresh_src_leakage()` + parent output scan | packaged run | PASS |
| `HPC-W04-FRESH-009` (PKG-GJ-01 captured) | `run_fresh_user_smoke` schema `wx-fresh-user-smoke/1` + this report | CLI `--fresh-user` solo run | PASS |

## WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
DEF-W15-001 | P1 | core/paths app_data_dir+app_log_dir | rg: no HPC_GUI_* override; Path.home() unconditional | no isolated-root mechanism exists | fresh-user packaged run impossible without contaminating developer profile | HPC_GUI_CONFIG_ROOT override | YES (FIX-A) | FIXED
DEF-W15-002 | P1 | scripts/wx_packaged_smoke.py + wx_shell smoke | smoke supports only generic .py/.exe launch; no fresh root, no first-run/profile-via-controls, no safe-failure, no relaunch, weak src flag | PKG-GJ-01 never implemented | C0 contract unevidenced on any artifact | --fresh-user mode + in-app fresh phase | YES (FIX-B) | FIXED (packaged-proven)
DEF-W15-003 | P2 | wx_shell finish() verdict | sibling packaged run: all in-app checks PASS yet runtime result FAIL + process exit 1 | mark_all() runs before clean_shutdown is set; no recompute after close | packaged verdict self-contradicts despite genuine success | recompute verdict in finish() after clean close | YES (FIX-B refinement) | FIXED
```

DEF-W15-003 was found during this Wave's own packaged acceptance loop
(sibling run `w15-fresh-user-windows-sibling-2217.json`: 10/10 parent checks
PASS but in-app `result: FAIL`, exits `[1,1]`), fixed in the working tree
(`finish()` recomputes the verdict after `frame.Close()` sets
`clean_shutdown`), and re-proven by the final solo run below (in-app
`result: PASS`, exits `[0,0]`).

## FIX-A — isolated config-root mechanism (`src/hpc_gui/core/paths.py`)

- `ISOLATED_CONFIG_ROOT_ENV = "HPC_GUI_CONFIG_ROOT"` + `isolated_config_root()`:
  blank/unset → `None` (default path, zero behavior change); otherwise create
  (parents) with `0o700` on posix; uncreatable → `RuntimeError` (loud, never
  silent fallback).
- `app_data_dir()` returns the override; `app_log_dir()` returns
  `<override>/logs`. All storage/history/i18n/diagnostics consumers inherit
  isolation with no call-site changes.
- Why root cause (not symptom): every per-user path funnels through these two
  functions; an env override at this layer isolates config, logs, history and
  third-party state atomically.

## FIX-B — PKG-GJ-01 fresh-user procedure

- Parent (`scripts/wx_packaged_smoke.py`): `fresh_user_env()` (drops
  `PYTHONPATH` + `HPC_GUI_DISABLE_WEBENGINE`; sets `HPC_GUI_CONFIG_ROOT`,
  `HPC_GUI_FRESH_USER=1`, `HPC_GUI_FRESH_RUN=1|2`) and
  `run_fresh_user_smoke()` (fresh temp root outside repo, clean-room cwd,
  loopback SSH fixture, run1 fresh + run2 relaunch, identity header + exact
  artifact SHA-256, schema `wx-fresh-user-smoke/1`, per-run `output_tail` for
  teardown diagnostics). `.whl` is refused as GUI evidence (FAIL with
  `GUI-capable` reason — never whl-as-GUI).
- In-app (`src/hpc_gui/wx_shell.py`): `_run_fresh_user_acceptance` runs when
  `HPC_GUI_FRESH_USER=1` — fresh root assertion, first-run empty state,
  profile creation via real AddConnection→modal dialog→Save wx events (dialog
  values taken from the loopback env so the saved profile genuinely describes
  the connection; password stays transient, never persisted), loopback success
  via ListBox selection + ConnectSelected events, dead-port safe failure via
  the same visible path, disk-byte persistence proof, frozen-bundle
  src-leakage proof, clean close (with DEF-W15-003 verdict recompute). Run2
  proves relaunch from disk.
- `_connect_packaged_smoke_session` gained optional endpoint overrides so the
  GUI-created profile's endpoint is honored (dead-port profile truly fails).

## Tests

New `tests/test_w15_fresh_user_startup.py` (11 tests):
`REQ-W15-ROOT`, `NEG-W15-ROOT-BLANK`, `NEG-W15-ROOT-BAD`, `REQ-W15-STORE`,
`NEG-W15-CORRUPT`, `NEG-W15-WHL`, `NEG-W15-MISSING`, `PKG-W15-ENV`,
`CON-W15-PROFILE-DIALOG` (GUI event/integration),
`NEG-W15-SAFE-FAILURE` (GUI event/integration),
`REQ-W15-CONNECT-STATE` (GUI event/integration, transport mocked at the
documented boundary).
Taxonomy: unit + packaging + GUI event/integration. No wx surface changed by
FIX-A (paths only) beyond the smoke branch; no cluster claim at repo level
(loopback MockSSHServer only in packaged run) → EXTERNAL N/A at repo level.

- Exact commands (final tree, this session):
  - `python -m pytest tests/test_w15_fresh_user_startup.py -q` → `11 passed`
  - Impacted: W14 43-set + W15 + wx_connection + wx_connection_profiles +
    config_storage_atomic → `91 passed`
  - `test_wx_connection_71_2 + test_wx_connection_71_3 + test_cli` →
    `169 passed`
- Sensitivity (final tree): `git stash push --
  src/hpc_gui/core/paths.py scripts/wx_packaged_smoke.py
  src/hpc_gui/wx_shell.py` → 9 of 11 fix-coupled tests FAIL
  (root/blank/bad/store/corrupt/whl/missing/env/dialog); `git stash pop`
  restores → `11 passed`. The 2 still-passing tests prove pre-existing panel
  behavior (contract, not regression) and pass before/after by design.
- No skips/xfails added; no test weakened; fixtures tmp-based, no real home
  touched; dialogs/frames destroyed per test.

## Second-defect search (12 dims)

negative ✓ (blank/bad root, corrupt config, whl, missing exe, dead port) ·
lifecycle ✓ (close/relaunch run1→run2; modal watchdog cancels without hang) ·
stale state ✓ (dead-port uses a rebuilt panel; reconnect tears down session) ·
identity ✓ (name-selected profiles; no cross-profile state) ·
concurrency/race ✓ (autofill retries until dialog captured; watchdog can only
EndModal the modal dialog — panel host is a `wx.Panel`, verified in
`wx_host.py`) · boundary ✓ (dialog port/host validation; empty-password
key-auth norm verified) · capability absence N/A (no optional provider in
this slice) · persistence ✓ (disk-byte reload + relaunch run) · packaging ✓
(frozen exe strictly proven; see PACKAGE) · error visibility ✓ (FAIL
checks + details, no success-claiming; `finish(error)` recorded) ·
secondary entry ✓ (`show_connection` shares `_build_connection` core) ·
adjacent boundary ✓ (`svc_save` empty-password norm; resolver needs no prompt
for key-auth profiles — proven by passing GUI tests).

## POST_GREEN_REVIEW

Duplicate path: none (single override helper; single fresh runner). Alternate
entry: `show_connection` shares the fixed core. Silent fallback: none added
(uncreatable root raises). Stale state: panel rebuilt per profile; session
teardown on reconnect pre-exists. Wrong identity: endpoint overrides honor
the transient profile. Cleanup: loopback server/root handling mirrors W14;
fresh temp parent path recorded in evidence (`fresh_parent_kept`) for audit.
Error-claims-success: result PASS requires every check PASS + isolation.
Packaged divergence: `.py` runs record paths without strict-frozen assertion;
strict bundle proof binds to the `.exe` acceptance below.

## PACKAGE evidence (exact artifact binding)

Canonical artifact: `dist/hpc-client-gui/hpc-client-gui.exe`
(`hpc-client-gui` onedir bundle, fully rebuilt from the current tree with
`pyinstaller -y --clean build/windows/hpc-client-gui.spec`, build completed
2026-09-19 23:19 local).

- SHA-256: `d2aab99d998a1dd0d912098f319f9bbf6c227ba0b4b82c9db9303bcf6c863cfd`
  (freshly verified: evidence-header SHA == recomputed disk SHA, MATCH true)
- Size 7414472 bytes; written 2026-09-19 23:19 local; PYZ-verified to contain
  `hpc_gui.wx_shell` and `hpc_gui.core.paths` (via `build/hpc-client-gui/PYZ-00.toc`).
- Superseded non-canonical artifacts (never used for acceptance):
  `597a39ca…` (partial 4 MB build artifact, missing `hpc_gui.wx_shell` in PYZ
  → honest FAIL, investigated, discarded);
  `cc4fd240…` (full build that predated the DEF-W15-003 recompute;
  sibling run `w15-fresh-user-windows-sibling-2217.json` binds this SHA with
  in-app runtime `result: FAIL`, exits `[1,1]` — the superseded FAIL evidence
  that produced DEF-W15-003, explicitly NOT corroboration);
  `a2a0f079…` (build-3 acceptance artifact: its solo + r2 PASS evidence files
  are preserved as `w15-fresh-user-windows-a2a0-superseded.json` and
  `w15-fresh-user-windows-r2.json`, but the `a2a0…` bytes were overwritten in
  `dist/` by the concurrent session's build-4 `bd7fbbf8…` and no immutable
  copy was retained, so `a2a0…` acceptance is no longer independently
  verifiable and is NOT cited);
  `bd7fbbf8…` (build-4, built from the concurrent session's unreverted
  mitigation state; solo evidence `w15-fresh-user-bd7fbbf8.json` honestly
  records `result: FAIL`, exits `[1,0]`, `NameError: name
  'build_connection_panel' is not defined` — never cited for acceptance).

## GUI evidence (PKG-GJ-01 solo acceptance run, canonical)

Command (parent cwd outside repo, clean env with no `PYTHONPATH` /
`HPC_GUI_DISABLE_WEBENGINE`):

```text
[cwd C:\Users\mskomek\AppData\Local\Temp\opencode]
python D:\Projeler\hpc-client-gui\scripts\wx_packaged_smoke.py --fresh-user \
  --artifact D:\Projeler\hpc-client-gui\dist\hpc-client-gui\hpc-client-gui.exe \
  --output D:\Projeler\hpc-client-gui\build\audit\w15-fresh-user-windows.json
```

Evidence: `build/audit/w15-fresh-user-windows.json`
(+ `w15-fresh-user-windows.run1.runtime.json`,
`w15-fresh-user-windows.run2.runtime.json`), schema `wx-fresh-user-smoke/1`:

- `result: PASS`; all 10 checks PASS (8 run1 + `clean_shutdown`, 2 run2 +
  `clean_shutdown`); `exit_codes: [0, 0]`; in-app runtimes both
  `result: PASS` (`wx-fresh-user-runtime/1`).
- Identity header binds `hpc-client-gui.exe /
  d2aab99d…863cfd / main 0f8902a0 / plugin f0abb7e7 / 1.5.9 /
  windows/amd64`; `generated_utc: 2026-09-19T20:20:48.374368+00:00`.
  Disk SHA recomputed after the run equals the evidence SHA (MATCH true),
  so the exact accepted bytes remain available at the recorded path.
- Single isolated root `hpc-fresh-user-r9_ocgy4` shared by parent, run1 and
  run2 (`fresh_root == app_data_dir`, `frozen: true`,
  `workdir_outside_repo: true`, `isolated_from_src: true`).
- Real wx event proof: profile created through the visible AddConnection
  modal dialog, loopback connect + dead-port failure both driven through
  ListBox selection + ConnectSelected events; run2 relaunches from disk
  bytes with zero secrets persisted.
- No corroboration claim: the only same-tree second run cited previously
  (`-r2`, `a2a0…`-bound) is superseded with its artifact bytes unavailable,
  and the sibling file (`cc4fd240…`-bound, runtime FAIL, exits `[1,1]`) is
  superseded pre-fix FAIL evidence. Solo PASS on the exact available SHA is
  the acceptance; nothing else is presented as corroboration.
- Concurrency note (honest record): this solo re-run was sequenced alone —
  no other packaged GUI acceptance was running (verified: no
  `hpc-client-gui` process before rebuild or run). Residual `DestroyWindow`
  teardown warnings in `output_tail` are benign wx noise with process exit 0.

## Diff review

- `git diff --check`: clean (only pre-existing CRLF warnings on unrelated
  W01/i18n files).
- `git diff --stat`: 20 files, 1289+/149- (W15-owned deltas: `paths.py`
  +39, `wx_shell.py` +651 incl. FIX-B + DEF-W15-003 recompute,
  `wx_packaged_smoke.py` +229, `tests/test_w15_fresh_user_startup.py` new;
  remainder is pre-existing unrelated W01–W14 working state, untouched).
- Untracked W15 additions: the new test file, canonical evidence JSONs
  under `build/audit/` (superseded `*-a2a0-superseded*` / `*-r2*` /
  `*-sibling-*` / `*-bd7fbbf8*` files preserved as history only, never
  cited for acceptance), this report.
- No secrets in diff; no test weakening; no binary noise committed.

## Resume state

Completed and verified:
- Baseline pin (main `0f8902a0`, plugin `f0abb7e7`) + W14 43-test pre-slice green.
- Discovery (paths/storage/smoke/connection owners) + WAVE_FINDINGS
  (DEF-W15-001/002/003, all FIXED).
- FIX-A + FIX-B (+DEF-W15-003 recompute) implemented; 11 new tests green;
  sensitivity 9-fail proven; impacted suites green (91 + 169).
- Fresh exe rebuilt from final tree (`d2aab99d…`) → solo PKG-GJ-01 PASS
  (10/10 checks, exits `[0,0]`, single isolated root, GUI+PACKAGE binding,
  disk SHA == evidence SHA).

### Post-acceptance session notes (2026-09-19, no re-acceptance)

A concurrent continuation session (same working tree) observed teardown
noise from overlapping packaged runs and briefly diverged the tree:

- `DEF-W15-004` (suspected frozen-teardown crash `0xC0000022` post-evidence)
  was recorded by the continuation, then withdrawn as a product defect: the
  crash signature appears only when two packaged GUI acceptances run
  concurrently (shared canonical runtime-file paths + foreground contention),
  never in solo runs. Retained only as the harness rule below.
- The continuation's driver-side teardown-mitigation refactor briefly added
  (then removed) `_fresh_run1_visible_flow_inner` + explicit host destroy;
  the refactor introduced a `NameError` (missing import in the inner split),
  caught by the honest FAIL before any acceptance cited it. Fully reverted;
  remnant scan clean, `py_compile` OK, unit file 11/11 green.
- `output_tail` (parent runner always retains the child output tail) is kept:
  harness-only evidence enrichment, zero product impact, already reflected
  in the procedure description above.
- Superseded extra builds (never cited): `bd7fbbf8…` (mitigation state +
  NameError; solo evidence `w15-fresh-user-bd7fbbf8.json` honestly FAIL) and
  the post-revert completion build (mitigation-state bytes, FAILED with
  `PermissionError` removing `dist\…\_rust.pyd`: a lingering foreign
  `hpc-client-gui` process held the lock — left untouched; no rebuild
  needed at that time). At resume cycle 1 no lingering process remained,
  `dist/` was rebuilt cleanly, and acceptance binds solely to the fresh
  exe SHA `d2aab99d…` (see §Resume cycle 1).
- Harness rule (learned): never run two packaged GUI acceptances
  concurrently — shared runtime-file names and foreground contention
  contaminate evidence. Solo sequencing is mandatory for PKG-GJ-01.
- Canonical evidence (superseded by resume cycle 1, kept as history):
  `build/audit/w15-fresh-user-windows-a2a0-superseded.json` (solo on exe
  `a2a0f079…`, exits `[0,0]`),
  `build/audit/w15-fresh-user-windows-r2.json` (second run on `a2a0f079…`,
  `[0,0]`), `build/audit/w15-fresh-user-windows-sibling-2217.json`
  (`cc4fd240…`-bound, runtime FAIL, exits `[1,1]` — pre-DEF-W15-003-fix
  evidence, never corroboration).
- Tree state re-verified after revert: packaged-source files contain only
  FIX-A + FIX-B + DEF-W15-003 recompute (no `_fresh_run1_visible_flow_inner`
  remnants; `build_connection_panel` via proper local imports);
  `git diff --check` clean; no secrets; unrelated working-tree changes
  preserved.

## Resume cycle 1 (2026-09-19, closes REOPEN-W15-001/002)

Fresh Luna-medium audit (`W15_AUDIT_REPORT.md`, REOPEN) found the `a2a0…`
bytes no longer on disk (`dist/` held build-4 `bd7fbbf8…`) and the sibling
file mischaracterized as corroboration. Truthful correction applied:

- REOPEN-W15-001: `a2a0…` bytes unrecoverable (overwritten, no immutable
  copy) → rebuilt from the current reverted tree (identical FIX-A + FIX-B +
  DEF-W15-003-recompute source; no concurrent runs; no lingering
  `hpc-client-gui` process) with `pyinstaller -y --clean
  build/windows/hpc-client-gui.spec` → new exe `d2aab99d…` (7414472 bytes,
  23:19 local, PYZ contains `hpc_gui.wx_shell` + `hpc_gui.core.paths`) →
  fresh solo PKG-GJ-01 PASS (10/10 checks, exits `[0,0]`, both runtimes
  PASS; `generated_utc: 2026-09-19T20:20:48.374368+00:00`; disk SHA ==
  evidence SHA). Stale `a2a0…` evidence renamed to
  `*-a2a0-superseded.json` (history only). Acceptance re-bound solely to
  `d2aab99d…`.
- REOPEN-W15-002: sibling `w15-fresh-user-windows-sibling-2217.json`
  corrected to superseded pre-fix FAIL evidence (`cc4fd240…`, runtime FAIL,
  exits `[1,1]`); all corroboration claims removed. Solo PASS on the exact
  available SHA is the acceptance.
- Re-verified this cycle (final tree): unit file `11 passed`; impacted
  `91 passed` (W14 43-set + W15 + wx_connection + wx_connection_profiles +
  config_storage_atomic); `test_wx_connection_71_2 + test_wx_connection_71_3
  + test_cli` → `169 passed`; `git diff --check` clean (only pre-existing
  CRLF warnings); W15-scope secrets scan clean; no test weakened; no
  skips/xfails; unrelated working-tree changes preserved byte-for-byte
  (no reset/clean/push).

Open P0/P1: none. Open P2/P3: none.
Pending tests/evidence: none.

## Final summary

```text
FIX-A: isolated HPC_GUI_CONFIG_ROOT (DEF-W15-001, paths.py)
FIX-B: PKG-GJ-01 fresh-user procedure (DEF-W15-002 + DEF-W15-003 recompute,
  smoke runner + wx_shell)
New/modified tests: tests/test_w15_fresh_user_startup.py (11 new)
Skipped/xfail changes: none
Package evidence: PASS — exe d2aab99d998a1dd0d912098f319f9bbf6c227ba0b4b82c9db9303bcf6c863cfd
  (build/audit/w15-fresh-user-windows.json, solo, exits [0,0], disk SHA == evidence SHA)
External evidence: N/A (loopback fixture only)
Open P0/P1: none
Two-fix gate: N/A per HPC-GOV-017 (zero-defect PASS valid; two independent
  remediations delivered regardless: FIX-A product, FIX-B harness)
Wave decision: READY_FOR_AUDIT
```
