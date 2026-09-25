# W56 Wave Report — Real-cluster replay and candidate build (REPAIR phase)

Session status: BLOCKED (worker-level; wx cutover default + dependency/spec/support-text re-audit applied at source on durable product-owner decision; pending real-build verification + full Workstream E replay + clean-pin candidate)
Wave decision: NO-GO for candidate freeze this run (correct per W56 invariant staging; source re-audit applied, no PyInstaller build executed, no candidate built, no freeze declared)

- Wave: `W56` (execution kind, canonical_source `W56`)
- Branch: `develop`
- HEAD SHA: `4fb752ad0f846fb198e63c21b5d570b603efae79`
- Working tree at run: `4fb752ad` clean at entry (prior repair's cutover flip committed); this repair modifies `pyproject.toml`, `build/windows/hpc-client-gui.spec`, `tests/test_wave0_unicode_baseline.py`, `README.md`, `THIRD_PARTY_NOTICES.md` (dependency/spec/support-text re-audit) plus this report (closeout-allowed path).
- Content identity (controller handoff): `d2bb2d74cdaeb0d427462459e605da59752d5dea4de99e7ed9e73657deb91e13`
- Prior W56 repair at HEAD `6014f198` was BLOCKED-staged (`W56-wx-cutover-flip-staged`): durable decision recorded + `runtime.py` default flipped to `"wx"` + test aligned + focused green, with packaging/deps/support-text explicitly deferred. That staged condition is ADVANCED by this repair: the deferred `RUNTIME-DEPENDENCY-001` source re-audit is now applied (see Repair follow-up). Remaining gates are build verification, full replay, and candidate freeze.
- Execution mode: unattended, non-interactive. No user questions asked. No secrets requested or invented.

## Mandatory authority consumed

1. `waves/pending/W56.md` (wave_id W56, execution kind, 15 source-derived IDs + 5 TODO-detail IDs, start gate NONE, cohort P12-candidate-build, required evidence `PACKAGE,EXTERNAL`, integration refs W55/W57 non-blocking).
2. `opencode/REQUIREMENT_REGISTRY.md` — all 20 rows with Owning Wave `W56` read (`HPC-W10-FREEZE-001/002/003/004/006/007/008/012/014/015/016/017/018`, `HPC-W10-BUILD-001/002`; TODO-detail rows `HPC-W10-TODO-RUNTIME-CUTOVER-001`, `HPC-W10-TODO-RUNTIME-DEPENDENCY-001`, `HPC-W10-TODO-007/008/009`).
3. `opencode/TODO_OWNERSHIP_MAP.md` — 5 rows with Owning Wave `W56` (RUNTIME-CUTOVER-001, RUNTIME-DEPENDENCY-001, TODO-007/008/009, all ACTIVE).
4. `opencode/sources/WAVE_V2_FINAL_10.md` → Entry criteria (lines 26-31), Scope (33-44), Workstream E Real-cluster regression (286-296), Workstream F Build candidate (298-312), plus planning-revision/prerequisite-integrity gate and repo-truth rule (baselines are observations, live code wins).
5. Live code before edits: `src/hpc_gui/runtime.py` (`DEFAULT_GUI_RUNTIME = "qt"` at entry), `src/hpc_gui/__main__.py` (wx only via `--wx`/`--wx-smoke` or when default is `wx`; otherwise Qt `hpc_gui.app.main`), `build/windows/hpc-client-gui.spec` (dual-runtime comment deferring to W56), `.github/workflows/release.yml` (Qt + release preflight), `tests/test_wave0_unicode_baseline.py:111` (maintained test asserting `DEFAULT_GUI_RUNTIME = "qt"`), `docs/v2/*` runtime contracts (Qt remains production runtime; wx optional).
6. Project profile `.opencode/protocol/WAVE_PROJECT_PROFILE.json` and lab protocol `.opencode/protocol/LOCAL_REAL_HPC_LAB.md`.
7. Current repository truth at HEAD `6014f198` on `develop`.
8. Durable decision authority (new this repair): tracked `docs/decisions/V2_RUNTIME_DECISION.md` (committed at `6014f198`, product owner, status DECIDED 2026-09-25): wx is the V2 production runtime (`DEFAULT_GUI_RUNTIME` becomes `"wx"`); Qt stays in-tree as legacy code only, not shipped in the V2 production package/dependencies/support text (explicit unadvertised `legacy-qt` opt-in at most); wx must not import Qt UI modules; tests pinning the Qt default encode the superseded decision and are updated to assert wx; packaging/README/support text/third-party notices are re-audited; the flip invalidates pre-cutover final evidence (W56 builds the new candidate; W57 `RUNTIME-CUTOVER-002/003` does packaged acceptance). Acceptance prerequisite: controller-accepted wx Waves `W26`–`W55` present in `waves/done/`. This supersedes the prior run's git-excluded-authority note: the decision is now durable Git authority. The on-disk git-excluded `opencode/V2_RUNTIME_DECISION.md` remains planning input only.

No short summary, chat log, or historical report was substituted for these reads.

## Baseline capture

- `git branch --show-current`: `develop`
- `git rev-parse HEAD`: `6014f19867fc3dcbf89ac49b5ab73c4e93b267cf`
- `git status --short`: clean at run entry (prior-run report modification had been committed as `ae97a177`; entry tree clean).
- `git log -1 --oneline --decorate`: `6014f198 Record V2 runtime decision: wx production runtime, Qt legacy-only (product owner)`
- Build/verify Python: `.venv/Scripts/python.exe` → `Python 3.14.0` (repo requires 3.14; satisfied). System `python` is `3.12.4` (not used for acceptance). wx `4.3.1`.
- No `git stash`, no reset, no checkout, no merge performed by this W56 run.

## Repair action (this phase)

Owned cutover flip applied on the new durable authority (`docs/decisions/V2_RUNTIME_DECISION.md` at `6014f198`):

- `src/hpc_gui/runtime.py`: `DEFAULT_GUI_RUNTIME = "qt"` → `"wx"` (production launch path `python -m hpc_gui` now starts wx; `--wx`/`--wx-smoke` flags unchanged).
- `tests/test_wave0_unicode_baseline.py`: `test_qt_is_default_runtime` → `test_wx_is_default_runtime`, asserting `'DEFAULT_GUI_RUNTIME = "wx"'`. This is the exact test update the product-owner decision authorizes ("tests that pin Qt as the default encode the superseded decision and are updated to assert the wx default") — an authority-directed contract update, not a weakening: the assertion is equally strict, now pinned to the decided runtime.
- Verified pre-edit that no other tracked file pins the Qt default: only this test + historical (immutable) wave reports + `docs/v2/*` contracts (W57-owned documentation consistency; routed, not rewritten here) + the decision doc itself (as superseded-example reference).
- Verified `src/hpc_gui/wx_shell/` has zero `PySide6`/Qt-UI imports (decision point 3 holds for the wx runtime path).
- Deliberately deferred to staged follow-up (see blockers): `pyproject.toml` dependency move (`PySide6` → `legacy-qt` extra), `build/windows/hpc-client-gui.spec` Qt hidden-import/`shiboken6` removal, README/support-text/third-party-notice re-audit — these require a real packaging build to verify and overlap W57 packaged-acceptance scope. The intermediate tree (wx default + dual-runtime bundle still containing Qt) is coherent: Qt code is present but unreached on the production path. `test_pyside6_in_dependencies` still passes unmodified (`PySide6` remains in dependencies until the verified re-audit).

## Repair follow-up (this phase — `RUNTIME-DEPENDENCY-001` source re-audit)

On the same durable authority (`docs/decisions/V2_RUNTIME_DECISION.md`), the previously deferred dependency/spec/support-text re-audit is now applied at source level (prior hypothesis `W56-wx-cutover-flip-staged` advanced; new hypothesis `W56-wx-deps-spec-reaudit`):

- `pyproject.toml`: `wxPython>=4.3.1` is now a mandatory production dependency; `PySide6>=6.5` moved out of mandatory dependencies into a new unadvertised `legacy-qt` extra (existing `wx` extra kept for compatibility). Production installs (`pip install -e .`) therefore ship wx, not Qt.
- `build/windows/hpc-client-gui.spec`: removed all `PySide6.*`/`shiboken6` hidden imports and the `collect_dynamic_libs("shiboken6")` binary collection (including its now-unused import); `binaries` starts empty with only the wx `WebView2Loader.dll` retained; dropped the stale `PySide6.scripts.deploy_lib` exclude; rewrote the W44 dual-runtime comment and the QtWebEngine-devtools comment to the W56 removal-from-shipment semantics. The packaged bundle no longer references Qt.
- `tests/test_wave0_unicode_baseline.py`: `test_pyside6_in_dependencies` → `test_wx_production_dependencies_match_runtime_decision`, asserting `wxPython` present, `legacy-qt` extra present with `PySide6`, and `PySide6` absent from the mandatory dependency block. Authority-directed contract update, equally strict (four assertions replacing one).
- `README.md`: run-from-source requirement now names wxPython (wxWidgets) as the V2 production runtime; Qt/PySide6 noted legacy-only, not required.
- `THIRD_PARTY_NOTICES.md`: runtime table now lists wxPython as the V2 production runtime and marks PySide6/shiboken6/Qt-libraries rows legacy-only (not shipped in V2 production packages); LGPL manifest sentence aligned (dependency versions shipped; Qt/PySide6 corresponding-source note scoped to the source-checkout `legacy-qt` extra).
- Deliberately NOT changed this phase (see blockers): `requirements-release.lock` still pins `PySide6` (lock regeneration belongs to the verified build step), no `PyInstaller` build executed (the re-audit ships-no-Qt claim needs a real build to verify), `docs/v2/*` contracts untouched (W57 documentation-consistency ownership), Qt-legacy test files untouched (legacy coverage under the `qt` marker stays).

## Discovery pass

- `src/hpc_gui/runtime.py` was a 3-line authority file: `DEFAULT_GUI_RUNTIME = "qt"`. This repair flipped it to `"wx"` per the durable decision (see Repair action).
- `src/hpc_gui/__main__.py` routes to `wx_shell.main` only on `--wx`/`--wx-smoke` or when the default equals `wx`; otherwise it imports `hpc_gui.app.main` (Qt). Production/release default path is therefore wx after this repair (previously Qt).
- `build/windows/hpc-client-gui.spec` ships PySide6/QtWebEngine hidden imports intentionally as dual-runtime and states in a W44 comment that they stay until the W56 runtime-cutover decision removes or retains Qt explicitly. Decision now says remove-from-shipment; spec slim deferred to verified packaging re-audit (see blockers) — not silently dropped here.
- W11 source requires the final artifact to behave as a complete usable wx application on the declared V2 wx runtime without unadvertised Qt fallback. The W56 invariant therefore forbade freezing a candidate while the release path still defaulted to Qt — that invariant is now satisfied at source level by this repair's flip; the remaining freeze gate is the packaging re-audit + fresh candidate + replay.
- Cutover precondition MET for the default flip: `RUNTIME-CUTOVER-001` permits flipping the default after wx mandatory acceptance passes; the durable decision records the prerequisite as controller-accepted `W26`–`W55` in `waves/done/` (verified present on disk). `tests/test_wave0_unicode_baseline.py` no longer pins `qt` (updated to `wx` by this repair with equal strictness). `W57` packaged acceptance + final validation remain pending (program has pending W56–W61).
- Packaging harness present (`build/windows/hpc-client-gui.spec`, `scripts/release.ps1`, `scripts/release_linux.py`, `scripts/release_macos.py`, `scripts/ci.py` targets, `.github/workflows/release.yml`). Full packaging run not executed this run (would be invalid pre-cutover; artifact would bind the wrong runtime identity).
- Lab profile present at `C:\Users\mskomek\AppData\Local\hpc-client-gui-lab\hpc-client-profile.json` with key/host-key material; `lab/*.ps1` lifecycle tooling present.

## Requirement dispositions (this run)

| ID | Disposition | Evidence |
|---|---|---|
| `HPC-W10-FREEZE-001` (W01–W09 completion reports) | VERIFIED (prerequisite present) | `docs/wave-reports/v2/opencode/W01..W09_WAVE_REPORT.md` all present. |
| `HPC-W10-FREEZE-002` (cross-Wave invalidation list) | VERIFIED (prerequisite present) | `waves/done/` + `waves/pending/W56..W61` directory state observable; no missing-directory condition. |
| `HPC-W10-FREEZE-003` (no known untriaged P0) | VERIFIED (no new P0 raised by this run) | This run raised zero new product findings; P0/P1 triage ownership sits with W57 per registry (`FREEZE-019/020` owned by W57). |
| `HPC-W10-FREEZE-004` (packaging harness operational) | VERIFIED (harness present) | Spec + release scripts present (see discovery). Full harness execution deferred to post-cutover candidate build. |
| `HPC-W10-FREEZE-006` (changed-surface regression) | PARTIAL (re-audit-focused slices green; full changed-surface slice pending build verification) | Dependency/spec/support-text re-audit covered by `test_wave0_unicode_baseline` 42 passed (incl. new wx-default + new deps-contract assertions), `test_version_consistency + test_remote_entry_helpers + test_qt_removal_gate` 27 passed / 1 environmental failure (see below), `test_wx_w55_shell_soak` 2 passed, `__main__` wx-route import smoke PASS, spec syntax parse PASS. |
| `HPC-W10-FREEZE-007` (broad automated suite) | PARTIAL (focused slices green; full suite not run) | Same focused evidence as FREEZE-006. Full `scripts/ci.py` full/gui not run (bounded repair; full-suite green belongs to the post-packaging-attempt). Non-blocking observation: `tests/test_qt_removal_gate.py::test_git_tracked_enumeration_rejects_git_failure` fails (`DID NOT RAISE Exception`) — causally independent of this repair (operates on `tmp_path`, none of the changed files imported); pre-existing/environmental; gate script is Wave 66/67 migration scope, routed to its owner, not fixed opportunistically here. |
| `HPC-W10-FREEZE-008` (real-cluster replay required by changes) | PARTIAL (connectivity probe only; full Workstream E replay not executed) | Bounded SSH probe PASS (see EV-W56-EXTERNAL-PROBE). Full connection/reconnect, SFTP round trip, editor save, job submit/cancel, terminal replay deferred to post-cutover run with exclusive LOCAL_REAL lease. |
| `HPC-W10-FREEZE-012` (candidate build and freeze) | BLOCKED (correctly not built) | No candidate built: the re-audit ships-no-Qt claim is source-applied but not yet build-verified. No freeze declared. |
| `HPC-W10-FREEZE-014` (connection/reconnect) | BLOCKED (replay deferred) | Probe-only; see external evidence. |
| `HPC-W10-FREEZE-015` (SFTP round trip) | BLOCKED (replay deferred) | Probe-only; no SFTP bytes moved this run. |
| `HPC-W10-FREEZE-016` (remote editor save) | BLOCKED (replay deferred) | Not executed this run. |
| `HPC-W10-FREEZE-017` (job list/submit/cancel) | BLOCKED (replay deferred) | Read-only `sinfo` states observed via probe; no submit/cancel executed. |
| `HPC-W10-FREEZE-018` (terminal) | BLOCKED (replay deferred) | Not executed this run. |
| `HPC-W10-BUILD-001` (build candidate + provenance) | BLOCKED (correctly not built) | No artifact, no SHA-256, no manifest. Building now would precede the ships-no-Qt build verification. |
| `HPC-W10-BUILD-002` (freeze invalidation rule) | VERIFIED (rule honored; no freeze to invalidate) | No freeze exists; this run's source/config/text changes precede the freeze, so nothing is invalidated. |
| `HPC-W10-TODO-RUNTIME-CUTOVER-001` | IMPLEMENT (decision durable + default flipped + test aligned + focused retest green) | Tracked `docs/decisions/V2_RUNTIME_DECISION.md`; `runtime.py` now `"wx"` (committed at `4fb752ad`); `test_wx_is_default_runtime` PASS; `__main__` wx-route import smoke PASS. |
| `HPC-W10-TODO-RUNTIME-DEPENDENCY-001` | IMPLEMENT-AT-SOURCE (code/config/text aligned; build verification pending) | `wxPython` mandatory + `PySide6` in `legacy-qt` extra only (`pyproject.toml`); Qt hidden imports/binaries removed from spec; README + third-party notices aligned; new deps-contract test PASS; spec syntax PASS. Still pending: real `PyInstaller` build proving the bundle ships no Qt, `requirements-release.lock` regeneration, install/CI proof for the extra split. |
| `HPC-W10-TODO-007` (Windows artifact) | BLOCKED | No artifact built (see BUILD-001). |
| `HPC-W10-TODO-008` (artifact identity record) | BLOCKED | No artifact identity to record. |
| `HPC-W10-TODO-009` (runs without source checkout) | BLOCKED | Not provable without an artifact. |

No requirement is claimed IMPLEMENT beyond the prerequisite/harness rows above. No `NOT_APPLICABLE_ACCEPTED`, no `DEFERRED_CLEAN`, no `AWAITING_INPUT` (no concrete external-authority dependency missing; lab is reachable).

## Tests and evidence

### EV-W56-BASELINE — narrow baseline + re-audit regression → PASS (as baseline, not acceptance)

All runs at HEAD `4fb752ad` + this repair's 5-file re-audit diff (plus this report). Fresh runs this phase (not reused from prior phases):

- `.venv/Scripts/python.exe -m compileall -q src/hpc_gui` → exit 0.
- `.venv/Scripts/python.exe -m pytest tests/test_version_consistency.py tests/test_remote_entry_helpers.py tests/test_qt_removal_gate.py -q --tb=short -rf` → `27 passed, 1 failed` (`test_git_tracked_enumeration_rejects_git_failure`, environmental/pre-existing, routed — see FREEZE-007), exit 1 on that single unrelated case.
- `.venv/Scripts/python.exe -m pytest tests/test_wave0_unicode_baseline.py -q --tb=short -rf` → `42 passed`, exit 0 — including `test_wx_is_default_runtime` (decided wx default) and the new `test_wx_production_dependencies_match_runtime_decision` (wxPython mandatory, PySide6 in `legacy-qt` extra only).
- `timeout 100 .venv/Scripts/python.exe -m pytest tests/test_wx_w55_shell_soak.py -q --tb=short -rf` → `2 passed`, exit 0 (wx production path healthy after re-audit).
- `.venv/Scripts/python.exe -m ruff check src/hpc_gui/runtime.py tests/test_wave0_unicode_baseline.py` → `All checks passed!`.
- Spec syntax: `ast.parse(open('build/windows/hpc-client-gui.spec').read())` → OK; `tomllib` read of `pyproject.toml` confirms deps `['wxPython>=4.3.1', 'paramiko>=3.4', 'cryptography>=41.0', 'packaging>=23', 'keyring>=25.0']` and extras `['test', 'dev', 'wx', 'legacy-qt']`.
- `python -c "from hpc_gui.runtime import DEFAULT_GUI_RUNTIME"` → `wx`; `hpc_gui.__main__` import smoke with wx-route check → PASS (no GUI launched).
- Full suite deliberately not run this bounded BLOCKED repair.

### EV-W56-EXTERNAL-PROBE — LOCAL_REAL bounded reachability → PASS (probe only, not Workstream E, fresh this repair)

- Target: `LOCAL_REAL_HYPERV`, `hpctest@192.168.250.11:22`, key `-i <lab>/id_ed25519` from emitted lab profile (`key_path` field; profile file has UTF-8 BOM — parse accordingly), `BatchMode=yes`, `ConnectTimeout=8`.
- `echo LAB_SSH_OK; hostname; sinfo -h -o '%T'` → `LAB_SSH_OK`, `login-control01`, `idle` + `down`. Exit 0 (re-run at `4fb752ad` + repair diff).
- Interpretation: controller/login transport healthy; Slurm answers; one compute idle and usable for single-node replay; one compute `down` degrades two-node `srun` and must be recovered via maintained lab tooling (`lab-status.ps1`/`lab-test.ps1`/reset path) before W56 claims full Workstream E. No jobs submitted, no files transferred, no editor/terminal replay executed — correctly, since full replay belongs to the post-verification attempt with an exclusive LOCAL_REAL lease.
- Private keys, VM disks, and generated secrets were not copied into reports/Git. Only host, user, node names, and partition states recorded.

### EV-W56-PACKAGE — packaging re-audit at source → SOURCE-ALIGNED (no artifact)

- `build/windows/hpc-client-gui.spec` now contains zero `PySide6`/`shiboken6` references (verified via syntax parse + text search); `pyproject.toml` production deps contain zero `PySide6` (verified via `tomllib`).
- `requirements-release.lock` still pins `PySide6==6.11.2`/`shiboken6` — regeneration belongs to the verified build step, not this source edit.
- No `PyInstaller`/release build executed this run (the ships-no-Qt claim needs a real build to verify). No artifact path/SHA-256 to bind.

### EV-W56-VALIDATOR — closeout validator → red as expected for BLOCKED

- `.venv/Scripts/python.exe scripts/validate_wave_closeout.py --wave W56 --no-execute-tests` → `can_close false` (`missing/invalid evidence manifest`), exit 0 (validator ran at `4fb752ad` + repair diff; close not allowed).
- No manifest fabricated to force green. A BLOCKED repair must leave the validator red.

## Diff review

- `git status --short`: clean at entry (`4fb752ad`); after this repair: `M pyproject.toml` (wxPython mandatory, PySide6 → `legacy-qt` extra), `M build/windows/hpc-client-gui.spec` (Qt hidden imports/binaries removed), `M tests/test_wave0_unicode_baseline.py` (deps-contract test update), `M README.md` + `M THIRD_PARTY_NOTICES.md` (support-text alignment), `M docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md` (closeout-allowed path).
- `git diff --check`: clean except repo-wide CRLF carriage-return notes on added lines of CRLF files (no real trailing spaces; pre-existing file style).
- W56 owns all five product/test/config/text hunks this run; no sibling worktree/file touched.
- Secrets scan: no credentials, keys, tokens, or connection strings added (lab probe used the existing emitted key path; password never handled).
- Weakened tests: none — the updated deps-contract test is authority-directed (product-owner decision requires packaging/dependency claims to match) and strictly stronger (four assertions replacing one). Duplicated logic: none added. Generated/binary noise: none added (`__pycache__` untracked/ignored, not staged).

## Blockers (controller-owned resume)

1. `BLOCKED-BUILD-VERIFICATION`: `RUNTIME-DEPENDENCY-001` source re-audit is applied but the ships-no-Qt claim is not yet build-verified — `requirements-release.lock` still pins `PySide6==6.11.2`/`shiboken6==6.11.2` (regeneration belongs to the verified build step); `requirements.txt` realigned to wxPython by this repair (test-guarded); `build/linux` + `build/macos` specs still carry Qt hidden imports (20 gate blockers; re-audit at the verified build step, sibling platform scope); no `PyInstaller` build has proven the wx-default bundle ships no Qt; no install/CI proof for the `legacy-qt` extra split. Resume: regenerate/verify the release lock, run a real packaging build from the clean pin, prove Qt absence in the bundle + `pip install -e .` pulls wx without Qt, then run packaged/W04-harness regression (packaged acceptance itself is W57 scope; W56 records the frozen identity). Overlaps W57 packaged-acceptance scope — controller routes the boundary.
2. `BLOCKED-FULL-REPLAY`: full Workstream E replay (connection/reconnect, SFTP round trip with byte/hash proof, remote editor save with server-side proof, disposable job submit/cancel, terminal) not executed; bounded probe only (fresh PASS this repair: `LAB_SSH_OK`, `login-control01`, `idle` + `down`). Resume: with exclusive LOCAL_REAL lease on the post-verification pin, execute the five replay paths with environment/target/profile/requirement binding and cleanup.
3. `PARTIAL-LAB-DEGRADED`: one compute `down` (`sinfo`: one `idle`, one `down`; unchanged since `ae97a177`). Single-node replay viable; two-node `srun` and any test requiring both computes must wait for lab recovery via maintained tooling. Not a W56 product defect; infrastructure/orchestration state until diagnosed.
4. `BLOCKED-CANDIDATE`: no candidate filename, main SHA beyond HEAD, plugin SHA/provenance, version, build environment, SHA-256, or manifest exists. Correctly absent (building before the ships-no-Qt build verification would risk binding a Qt-bundled artifact against the wx-only decision). Resume: after blocker 1, build exactly one candidate from the clean post-re-audit pin, record full provenance, then run packaged/W04-harness regression.
5. Prior `BLOCKED-RUNTIME-CUTOVER` (no durable decision; `qt` default) is RESOLVED: durable decision + default flip committed at `4fb752ad`. Prior `BLOCKED-PACKAGING-REAUDIT` source items are APPLIED by this repair; only build verification (blocker 1) remains.
6. Prior `BLOCKED-CLEAN-SOURCE` (dirty tree at `c8293d3c`) remains resolved (entry tree clean at `4fb752ad`; this repair's diff is owned W56 work, not contamination).

## Deferred items

- Full `scripts/ci.py` full/gui/docs/audit gates: deferred to post-cutover attempt (bounded BLOCKED run; pre-cutover full-suite green could not support freeze).
- `PyInstaller` Windows candidate build + source-independence proof (`TODO-007/008/009`): deferred behind blocker 1.
- `docs/wave-reports/v2/opencode/W56_AUDIT_REPORT.md`: not created by the run worker; reserved for fresh-independent audit after a future `READY_FOR_AUDIT`.
- `artifacts/wave_W56/WAVE_W56_EVIDENCE_MANIFEST.json`: not created; no PASS to manifest.

## Contradiction scan

- W56 product change this repair (dependency/spec/support-text re-audit + deps-contract test update) is consistent with sibling evidence: report claims match executed commands (compile PASS, 42 baseline PASS incl. wx-default + new deps-contract assertions, 27 + 1-environmental gate/consistency/helpers, 2 soak PASS, ruff PASS, spec parse PASS, `tomllib` deps/extras readback, SSH probe PASS, validator red). No GUI/PACKAGE/EXTERNAL acceptance claimed beyond the bounded probe. Config statements match live files (`pyproject.toml` mandatory deps wx-only, `legacy-qt` extra holds PySide6; spec holds zero Qt references; lock file explicitly still pins Qt pending the verified build step — not hidden). Lab statements match observed `sinfo` output including the one-compute-`down` degradation (not hidden). The `test_qt_removal_gate` single failure is recorded with its exact identity and routed, not hidden.

## Repair follow-up 2 (this phase — production requirements realignment, hypothesis `W56-prod-requirements-realign`)

Prior hypothesis `W56-wx-deps-spec-reaudit` left two gate-scanned production
dependency files still advertising Qt. This repair advances with a materially
different diagnosis (remaining production requirements files, not the
pyproject/spec/support-text surface already committed at `ebce9e9f`):

- `requirements.txt`: `PySide6>=6.5` → `wxPython>=4.3.1` (gate-scanned
  production dependency file; now ships the wx runtime, no Qt).
- `tests/test_wave0_unicode_baseline.py::test_wx_production_dependencies_match_runtime_decision`:
  strengthened with two `requirements.txt` assertions (wxPython present, no
  `PySide6`/`shiboken6` lines) — authority-directed, strictly stronger.
- Gate scan: Qt dependency records `6 → 5` (`requirements.txt` clean).
  Remaining records are truthfully out of this edit's reach: `pyproject.toml`
  `legacy-qt` extra (explicitly authorized by the decision as unadvertised
  developer opt-in; the gate has no extra-scoping and is Wave 66/67 scope) and
  `requirements-release.lock` (4 records; hand-editing a freeze lock without a
  real resolve would fabricate provenance — regeneration belongs to the
  verified build step with a clean wx-only venv, blocker 1).
- Deliberately NOT changed: `build/linux/...spec` + `build/macos/...spec`
  still carry Qt hidden imports (20 gate packaging blockers). The durable
  decision names the Windows spec; Linux/macOS bundle scope overlaps sibling
  platform waves, and editing those specs without build-verification ability on
  those platforms risks cross-scope breakage. Routed as follow-up inside
  blocker 1 (verified build step re-audits all shipped specs) — not fixed
  opportunistically here.
- Fresh verification this repair (HEAD `ebce9e9f` + this 2-file diff):
  `test_wave0_unicode_baseline` 42 passed, `test_wheel_packaging` 4 passed,
  `test_qt_removal_gate` 14 passed + 1 pre-existing environmental failure
  (`test_git_tracked_enumeration_rejects_git_failure`, Wave 66/67 scope,
  routed), `ruff check tests/test_wave0_unicode_baseline.py` clean,
  `git diff --check` clean.

## Handoff

- After the build verification (blocker 1) lands on a verified pin, the next W56 attempt must: re-capture baseline, execute full Workstream E replay with exclusive LOCAL_REAL lease (recovering the `down` compute first if two-node paths are required), build exactly one candidate with full provenance + SHA-256 + manifest, rerun affected focused tests, refresh this report, and return `READY_FOR_AUDIT` only when every owned requirement is IMPLEMENT with current truthful evidence. The wx-default flip (`4fb752ad`) and this repair's dependency/spec/support-text re-audit must not be reverted: both implement the durable product-owner decision.
- This worker starts no downstream Wave; scheduling remains controller-owned. Integration references W55 (done) and W57 (pending) are non-blocking hints only.
