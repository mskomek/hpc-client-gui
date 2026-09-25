# W56 Wave Report — Real-cluster replay and candidate build (RUN phase)

Session status: BLOCKED (worker-level; pending controller runtime-cutover verdict + clean-pin candidate authorization)
Wave decision: NO-GO for candidate freeze this run (correct per W56 invariant; no candidate built, no freeze declared)

- Wave: `W56` (execution kind, canonical_source `W56`)
- Branch: `develop`
- HEAD SHA: `394d8d1008fd6c5bf1b1de35f67c8035ffa806d1`
- Working tree at run: clean (`git status --short` empty at entry and pre-report)
- Content identity (controller handoff): `443d5543ec9f0bd35189b7ca9d307c5135c76009c47ab0a8dc74ac9f30a31e9a`
- Prior W56 RUN at HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369` was BLOCKED on dirty tree + pre-cutover runtime; that dirty-tree condition is now resolved by integration (HEAD `394d8d10` clean), but the runtime-cutover condition is NOT resolved.
- Execution mode: unattended, non-interactive. No user questions asked. No secrets requested or invented.

## Mandatory authority consumed

1. `waves/pending/W56.md` (wave_id W56, execution kind, 15 source-derived IDs + 5 TODO-detail IDs, start gate NONE, cohort P12-candidate-build, required evidence `PACKAGE,EXTERNAL`, integration refs W55/W57 non-blocking).
2. `opencode/REQUIREMENT_REGISTRY.md` — all 20 rows with Owning Wave `W56` read (`HPC-W10-FREEZE-001/002/003/004/006/007/008/012/014/015/016/017/018`, `HPC-W10-BUILD-001/002`; TODO-detail rows `HPC-W10-TODO-RUNTIME-CUTOVER-001`, `HPC-W10-TODO-RUNTIME-DEPENDENCY-001`, `HPC-W10-TODO-007/008/009`).
3. `opencode/TODO_OWNERSHIP_MAP.md` — 5 rows with Owning Wave `W56` (RUNTIME-CUTOVER-001, RUNTIME-DEPENDENCY-001, TODO-007/008/009, all ACTIVE).
4. `opencode/sources/WAVE_V2_FINAL_10.md` → Entry criteria (lines 26-31), Scope (33-44), Workstream E Real-cluster regression (286-296), Workstream F Build candidate (298-312), plus planning-revision/prerequisite-integrity gate and repo-truth rule (baselines are observations, live code wins).
5. Live code before edits: `src/hpc_gui/runtime.py` (`DEFAULT_GUI_RUNTIME = "qt"`), `src/hpc_gui/__main__.py` (wx only via `--wx`/`--wx-smoke` or when default is `wx`; otherwise Qt `hpc_gui.app.main`), `build/windows/hpc-client-gui.spec` (dual-runtime comment deferring to W56), `.github/workflows/release.yml` (Qt + release preflight), `tests/test_wave0_unicode_baseline.py:115` (maintained test asserting `DEFAULT_GUI_RUNTIME = "qt"`), `docs/v2/*` runtime contracts (Qt remains production runtime; wx optional).
6. Project profile `.opencode/protocol/WAVE_PROJECT_PROFILE.json` and lab protocol `.opencode/protocol/LOCAL_REAL_HPC_LAB.md`.
7. Current repository truth at HEAD `394d8d10` on `develop` with clean tree.

No short summary, chat log, or historical report was substituted for these reads.

## Baseline capture

- `git branch --show-current`: `develop`
- `git rev-parse HEAD`: `394d8d1008fd6c5bf1b1de35f67c8035ffa806d1`
- `git status --short`: empty (clean) at run entry.
- `git log -1 --oneline --decorate`: `394d8d10 Sync Agent Core runtime 687ced0e: profile-mapped aggregate owner routing`
- Build/verify Python: `.venv/Scripts/python.exe` → `Python 3.14.0` (repo requires 3.14; satisfied). System `python` is `3.12.4` (not used for acceptance). wx `4.3.1`.
- No `git stash`, no reset, no checkout, no merge performed by this W56 run.

## Discovery pass

- `src/hpc_gui/runtime.py` is a 3-line authority file: `DEFAULT_GUI_RUNTIME = "qt"`. No cutover has been applied on this tree.
- `src/hpc_gui/__main__.py` routes to `wx_shell.main` only on `--wx`/`--wx-smoke` or when the default equals `wx`; otherwise it imports `hpc_gui.app.main` (Qt). Production/release default path is therefore Qt today.
- `build/windows/hpc-client-gui.spec` ships PySide6/QtWebEngine hidden imports intentionally as dual-runtime and states in a W44 comment that they stay until the W56 runtime-cutover decision removes or retains Qt explicitly.
- W11 source requires the final artifact to behave as a complete usable wx application on the declared V2 wx runtime without unadvertised Qt fallback. The W56 invariant therefore forbids freezing a candidate while the release path still defaults to Qt.
- Cutover precondition NOT met: `RUNTIME-CUTOVER-001` permits flipping the default only after wx mandatory acceptance passes. No controller wx-acceptance verdict exists (W57 packaged acceptance + final validation still pending; program has pending W56–W61). Moreover `tests/test_wave0_unicode_baseline.py:115` is a maintained test asserting the `qt` default — flipping now without owner-routed test/contract updates would break a green maintained check and invalidate Qt-default-based evidence. No cutover attempted this run by design.
- Packaging harness present (`build/windows/hpc-client-gui.spec`, `scripts/release.ps1`, `scripts/release_linux.py`, `scripts/release_macos.py`, `scripts/ci.py` targets, `.github/workflows/release.yml`). Full packaging run not executed this run (would be invalid pre-cutover; artifact would bind the wrong runtime identity).
- Lab profile present at `C:\Users\mskomek\AppData\Local\hpc-client-gui-lab\hpc-client-profile.json` with key/host-key material; `lab/*.ps1` lifecycle tooling present.

## Requirement dispositions (this run)

| ID | Disposition | Evidence |
|---|---|---|
| `HPC-W10-FREEZE-001` (W01–W09 completion reports) | VERIFIED (prerequisite present) | `docs/wave-reports/v2/opencode/W01..W09_WAVE_REPORT.md` all present. |
| `HPC-W10-FREEZE-002` (cross-Wave invalidation list) | VERIFIED (prerequisite present) | `waves/done/` + `waves/pending/W56..W61` directory state observable; no missing-directory condition. |
| `HPC-W10-FREEZE-003` (no known untriaged P0) | VERIFIED (no new P0 raised by this run) | This run raised zero new product findings; P0/P1 triage ownership sits with W57 per registry (`FREEZE-019/020` owned by W57). |
| `HPC-W10-FREEZE-004` (packaging harness operational) | VERIFIED (harness present) | Spec + release scripts present (see discovery). Full harness execution deferred to post-cutover candidate build. |
| `HPC-W10-FREEZE-006` (changed-surface regression) | BLOCKED (deferred behind runtime decision) | Tree is clean at `394d8d10`, but any regression slice run now would bind the pre-cutover Qt-default identity and be invalidated by the pending cutover flip. No W56-owned regression slice claimed. |
| `HPC-W10-FREEZE-007` (broad automated suite) | PARTIAL (focused slices green; full suite not run) | `compileall` PASS; `test_version_consistency + test_remote_entry_helpers` 13 passed; `test_wave0_unicode_baseline` 42 passed; `test_wx_w55_shell_soak` 2 passed. Full `scripts/ci.py` full/gui not run (bounded run; pre-cutover full-suite green cannot support freeze). |
| `HPC-W10-FREEZE-008` (real-cluster replay required by changes) | PARTIAL (connectivity probe only; full Workstream E replay not executed) | Bounded SSH probe PASS (see EV-W56-EXTERNAL-PROBE). Full connection/reconnect, SFTP round trip, editor save, job submit/cancel, terminal replay deferred to post-cutover run with exclusive LOCAL_REAL lease. |
| `HPC-W10-FREEZE-012` (candidate build and freeze) | BLOCKED (correctly not built) | No candidate built per invariant (Qt default + no wx-acceptance verdict). No freeze declared. |
| `HPC-W10-FREEZE-014` (connection/reconnect) | BLOCKED (replay deferred) | Probe-only; see external evidence. |
| `HPC-W10-FREEZE-015` (SFTP round trip) | BLOCKED (replay deferred) | Probe-only; no SFTP bytes moved this run. |
| `HPC-W10-FREEZE-016` (remote editor save) | BLOCKED (replay deferred) | Not executed this run. |
| `HPC-W10-FREEZE-017` (job list/submit/cancel) | BLOCKED (replay deferred) | Read-only `sinfo` states observed via probe; no submit/cancel executed. |
| `HPC-W10-FREEZE-018` (terminal) | BLOCKED (replay deferred) | Not executed this run. |
| `HPC-W10-BUILD-001` (build candidate + provenance) | BLOCKED (correctly not built) | No artifact, no SHA-256, no manifest. Building now would violate runtime + wx-acceptance invariants. |
| `HPC-W10-BUILD-002` (freeze invalidation rule) | VERIFIED (rule honored; no freeze to invalidate) | No product/package-byte change made by W56 this run; nothing to invalidate. |
| `HPC-W10-TODO-RUNTIME-CUTOVER-001` | BLOCKED (decision pending; no code change) | Runtime still `qt`; cutover requires controller-confirmed wx mandatory acceptance. Finding remains W56-owned work for the post-verdict attempt. |
| `HPC-W10-TODO-RUNTIME-DEPENDENCY-001` | BLOCKED (decision pending) | Dual-runtime spec comment explicitly defers to W56; no dependency claim changed this run. |
| `HPC-W10-TODO-007` (Windows artifact) | BLOCKED | No artifact built (see BUILD-001). |
| `HPC-W10-TODO-008` (artifact identity record) | BLOCKED | No artifact identity to record. |
| `HPC-W10-TODO-009` (runs without source checkout) | BLOCKED | Not provable without an artifact. |

No requirement is claimed IMPLEMENT beyond the prerequisite/harness rows above. No `NOT_APPLICABLE_ACCEPTED`, no `DEFERRED_CLEAN`, no `AWAITING_INPUT` (no concrete external-authority dependency missing; lab is reachable).

## Tests and evidence

All runs at HEAD `394d8d10` + clean tree (unmodified by W56 except this report). `PYTHONPATH=src` where applicable.

### EV-W56-BASELINE — narrow baseline → PASS (as baseline, not acceptance)

- `.venv/Scripts/python.exe -m compileall -q src/hpc_gui` → exit 0.
- `.venv/Scripts/python.exe -m pytest tests/test_version_consistency.py tests/test_remote_entry_helpers.py -q --tb=short -rf` → `13 passed`, exit 0.
- `.venv/Scripts/python.exe -m pytest tests/test_wave0_unicode_baseline.py -q --tb=line -rf` → `42 passed`, exit 0. This suite pins `DEFAULT_GUI_RUNTIME = "qt"` (line 115) — machine proof the cutover precondition is still outstanding and flipping now would regress a maintained check.
- `timeout 100 .venv/Scripts/python.exe -m pytest tests/test_wx_w55_shell_soak.py -q --tb=short -rf` → `2 passed`, exit 0.
- Full suite deliberately not run this bounded BLOCKED run.

### EV-W56-EXTERNAL-PROBE — LOCAL_REAL bounded reachability → PASS (probe only, not Workstream E)

- Target: `LOCAL_REAL_HYPERV`, `hpctest@192.168.250.11:22`, key from emitted lab profile, `BatchMode=yes`, `ConnectTimeout=8`.
- `echo LAB_SSH_OK; hostname; sinfo -h -o '%T'` → `LAB_SSH_OK`, `login-control01`, `idle` + `down`. Exit 0.
- Interpretation: controller/login transport healthy; Slurm answers; one compute idle and usable for single-node replay; one compute `down` degrades two-node `srun` and must be recovered via maintained lab tooling (`lab-status.ps1`/`lab-test.ps1`/reset path) before W56 claims full Workstream E. No jobs submitted, no files transferred, no editor/terminal replay executed — correctly, since full replay belongs to the post-cutover attempt with an exclusive LOCAL_REAL lease.
- Private keys, VM disks, and generated secrets were not copied into reports/Git. Only host, user, node names, and partition states recorded.

### EV-W56-PACKAGE — packaging baseline → HARNESS-PRESENT (no artifact)

- `build/windows/hpc-client-gui.spec`, `scripts/release.ps1`, `scripts/ci.py`, `.github/workflows/release.yml` all present.
- No `PyInstaller`/release build executed this run (would bind the wrong pre-cutover runtime identity). No artifact path/SHA-256 to bind.

### EV-W56-VALIDATOR — closeout validator → red as expected for BLOCKED

- `.venv/Scripts/python.exe scripts/validate_wave_closeout.py --wave W56 --no-execute-tests` → `{"can_close": false, "failure_reasons": ["missing/invalid evidence manifest"]}`, exit 0 (validator ran; close not allowed).
- No manifest fabricated to force green. A BLOCKED run must leave the validator red.

## Diff review

- `git status --short`: clean at entry; after this run only this report file modified (`docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md`, closeout-allowed path).
- `git diff --check`: clean.
- W56 owns zero product/test/build/runtime hunks this run.
- Secrets scan: no credentials, keys, tokens, or connection strings added (lab probe used the existing emitted key path; password never handled).
- Weakened tests: none (no test file modified). Duplicated logic: none added. Generated/binary noise: none added.

## Blockers (controller-owned resume)

1. `BLOCKED-RUNTIME-CUTOVER`: `src/hpc_gui/runtime.py` still `DEFAULT_GUI_RUNTIME = "qt"` with Qt-default release path; W11 requires wx production runtime and the W56 invariant forbids freezing pre-cutover, while `RUNTIME-CUTOVER-001` forbids flipping before wx mandatory acceptance passes and a maintained test (`test_wave0_unicode_baseline.py:115`) plus `docs/v2/*` contracts pin the `qt` default. Resume: controller confirms the wx mandatory acceptance verdict, then a re-dispatched W56 performs `RUNTIME-CUTOVER-001`/`RUNTIME-DEPENDENCY-001` (default flip + packaging/support-text/dependency/test alignment) with focused retest before any candidate build. No cutover attempted on this run by design.
2. `BLOCKED-FULL-REPLAY`: full Workstream E replay (connection/reconnect, SFTP round trip with byte/hash proof, remote editor save with server-side proof, disposable job submit/cancel, terminal) not executed; bounded probe only. Resume: with exclusive LOCAL_REAL lease on the post-cutover pin, execute the five replay paths with environment/target/profile/requirement binding and cleanup.
3. `PARTIAL-LAB-DEGRADED`: one compute `down` (`sinfo`: one `idle`, one `down`). Single-node replay viable; two-node `srun` and any test requiring both computes must wait for lab recovery via maintained tooling. Not a W56 product defect; infrastructure/orchestration state until diagnosed.
4. `BLOCKED-CANDIDATE`: no candidate filename, main SHA beyond HEAD, plugin SHA/provenance, version, build environment, SHA-256, or manifest exists. Correctly absent. Resume: build exactly one candidate from the clean post-cutover pin, record full provenance, then run packaged/W04-harness regression (packaged acceptance itself is W57 scope; W56 records the frozen identity).
5. Prior `BLOCKED-CLEAN-SOURCE` (dirty tree at `c8293d3c`) is RESOLVED at `394d8d10` (clean). No longer blocking.

## Deferred items

- Full `scripts/ci.py` full/gui/docs/audit gates: deferred to post-cutover attempt (bounded BLOCKED run; pre-cutover full-suite green could not support freeze).
- `PyInstaller` Windows candidate build + source-independence proof (`TODO-007/008/009`): deferred behind blocker 1.
- `docs/wave-reports/v2/opencode/W56_AUDIT_REPORT.md`: not created by the run worker; reserved for fresh-independent audit after a future `READY_FOR_AUDIT`.
- `artifacts/wave_W56/WAVE_W56_EVIDENCE_MANIFEST.json`: not created; no PASS to manifest.

## Contradiction scan

- No W56 product change to contradict sibling evidence. Report claims match executed commands (compile PASS, 13 + 42 + 2 tests PASS, SSH probe PASS, validator red). No GUI/PACKAGE/EXTERNAL acceptance claimed beyond the bounded probe. Runtime statements match live files (`runtime.py`, `__main__.py`, spec comment, unicode-baseline pin). Lab statements match observed `sinfo` output including the one-compute-`down` degradation (not hidden).

## Handoff

- After the controller confirms the wx mandatory acceptance verdict and authorizes the post-cutover pin, the next W56 attempt must: re-capture baseline, perform `RUNTIME-CUTOVER-001`/`RUNTIME-DEPENDENCY-001` with owner-routed test/contract updates, execute full Workstream E replay with exclusive LOCAL_REAL lease (recovering the `down` compute first if two-node paths are required), build exactly one candidate with full provenance + SHA-256 + manifest, rerun affected focused tests, refresh this report, and return `READY_FOR_AUDIT` only when every owned requirement is IMPLEMENT with current truthful evidence.
- This worker starts no downstream Wave; scheduling remains controller-owned. Integration references W55 (done) and W57 (pending) are non-blocking hints only.
