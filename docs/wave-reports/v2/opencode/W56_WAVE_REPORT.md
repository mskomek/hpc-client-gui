# W56 Wave Report — Real-cluster replay and candidate build (RUN phase)

Session status: BLOCKED (worker-level; pending controller integration + runtime-cutover decision)
Wave decision: NO-GO for candidate freeze this run (correct per W56 invariant; no candidate built, no freeze declared)

- Wave: `W56` (execution kind, canonical_source `W56`)
- Branch: `develop`
- HEAD SHA: `c8293d3ca309526ed250c794c3b294f7c54ef369`
- Working tree at run: dirty (pre-existing sibling-wave modifications preserved untouched; W56 owns zero product hunks this run)
- Content identity (controller handoff): `ddc0b0a1c0c5af810fbdfab68173d3281f89baf63db1cb87ace0b616f4bb5f33`
- Execution mode: unattended, non-interactive. No user questions asked. No secrets requested or invented.

## Mandatory authority consumed

1. `waves/pending/W56.md` (wave_id W56, execution kind, 15 source-derived IDs + 5 TODO-detail IDs, start gate NONE, cohort P12-candidate-build, required evidence `PACKAGE,EXTERNAL`, integration refs W55/W57 non-blocking).
2. `opencode/REQUIREMENT_REGISTRY.md` — all 20 rows with Owning Wave `W56` read (`HPC-W10-FREEZE-001/002/003/004/006/007/008/012/014/015/016/017/018`, `HPC-W10-BUILD-001/002`; TODO-detail rows `HPC-W10-TODO-RUNTIME-CUTOVER-001`, `HPC-W10-TODO-RUNTIME-DEPENDENCY-001`, `HPC-W10-TODO-007/008/009`).
3. `opencode/TODO_OWNERSHIP_MAP.md` — 5 rows with Owning Wave `W56` (RUNTIME-CUTOVER-001, RUNTIME-DEPENDENCY-001, TODO-007/008/009, all ACTIVE).
4. `opencode/sources/WAVE_V2_FINAL_10.md` → Entry criteria (lines 26-31), Scope (33-44), Workstream E Real-cluster regression (286-296), Workstream F Build candidate (298-312), plus Shared execution contract (evidence precedence, baseline capture, discovery, change discipline, result vocabulary).
5. Live code before edits: `src/hpc_gui/runtime.py` (`DEFAULT_GUI_RUNTIME = "qt"`), `src/hpc_gui/__main__.py` (wx only via `--wx`/`--wx-smoke` or when default is `wx`), `src/hpc_gui/wx_runtime.py`, `src/hpc_gui/app.py` (Qt), `scripts/ci.py` targets, `.github/workflows/release.yml` (Qt + release preflight), `build/windows/hpc-client-gui.spec` (dual-runtime comment deferring to W56).
6. Project profile `.opencode/protocol/WAVE_PROJECT_PROFILE.json` and lab protocol `.opencode/protocol/LOCAL_REAL_HPC_LAB.md`.
7. Current repository truth at HEAD `c8293d3c` on `develop` with dirty tree (see baseline).

No short summary, chat log, or historical report was substituted for these reads.

## Baseline capture

- `git branch --show-current`: `develop`
- `git rev-parse HEAD`: `c8293d3ca309526ed250c794c3b294f7c54ef369`
- `git status --short --branch`: `## develop` + 38 modified tracked files + untracked sibling artifacts (full list in shell evidence; representative: `src/hpc_gui/wx_shell.py` +423/-104 vs HEAD, `src/hpc_gui/wx_jobs.py`, `src/hpc_gui/wx_editor_view.py`, `src/hpc_gui/wx_plugins*.py`, `src/hpc_gui/wx_settings*.py`, `src/hpc_gui/services/*`, `src/hpc_gui/plugins/*`, `src/hpc_gui/i18n/*`, `src/hpc_gui/docs/*`, `build/windows/hpc-client-gui.spec`, `README.md`, `tests/test_remote_entry_helpers.py`). All pre-existing; none altered by this W56 run. No `git stash`, no reset, no checkout, no merge performed.
- `git log -1 --oneline --decorate`: `c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API`
- Python for checks: `.venv/Scripts/python.exe` → `3.14.0` (repo requires 3.14; satisfied).

## Discovery pass

- `src/hpc_gui/runtime.py` is a 3-line authority file: `DEFAULT_GUI_RUNTIME = "qt"`. No cutover has been applied on this tree.
- `src/hpc_gui/__main__.py` routes to `wx_shell.main` only on `--wx`/`--wx-smoke` or when the default equals `wx`; otherwise it imports `hpc_gui.app.main` (Qt). Production/release default path is therefore Qt today.
- `build/windows/hpc-client-gui.spec` ships PySide6/QtWebEngine hidden imports intentionally as dual-runtime and states in a W44 comment that they stay until the W56 runtime-cutover decision removes or retains Qt explicitly.
- W11 source (`opencode/sources/WAVE_V2_FINAL_11.md:51,66`) requires the final artifact to behave as a complete usable wx application and to use the declared V2 wx runtime without unadvertised Qt fallback. W56 invariant therefore forbids freezing a candidate while the release path still defaults to Qt.
- Packaging harness exists (`build/windows/hpc-client-gui.spec`, `scripts/release.ps1`, `scripts/release_linux.py`, `scripts/release_macos.py`, `scripts/ci.py` targets `packaging`/`release`). Operational status below is harness-present; full packaging run was not executed this run (would be invalid on a dirty tree + pre-cutover runtime).
- Lab profile present at `C:\Users\mskomek\AppData\Local\hpc-client-gui-lab\hpc-client-profile.json` with key/host-key material; `lab/*.ps1` lifecycle tooling present.

## Requirement dispositions (this run)

| ID | Disposition | Evidence |
|---|---|---|
| `HPC-W10-FREEZE-001` (W01–W09 completion reports) | VERIFIED (prerequisite present) | `docs/wave-reports/v2/opencode/W01..W09_WAVE_REPORT.md` all present (listed in baseline check). |
| `HPC-W10-FREEZE-002` (cross-Wave invalidation list) | VERIFIED (prerequisite present) | `waves/done/W01..W55` + `waves/pending/W56..W61` directory state observable; no missing-directory condition. |
| `HPC-W10-FREEZE-003` (no known untriaged P0) | VERIFIED (no new P0 raised by this run) | This run raised zero new product findings; triage ownership for P0/P1 sits with W57 per registry (`FREEZE-019/020` owned by W57). |
| `HPC-W10-FREEZE-004` (packaging harness operational) | VERIFIED (harness present) | Spec + release scripts present (see discovery). Full harness execution deferred to clean-pin candidate build. |
| `HPC-W10-FREEZE-006` (changed-surface regression) | BLOCKED (deferred to clean pin) | Tree dirty with ~38 sibling-wave files; changed-surface baseline not stable. No W56-owned regression slice claimed. |
| `HPC-W10-FREEZE-007` (broad automated suite) | PARTIAL (focused slices green; full suite not run) | `compileall` PASS; `test_version_consistency + test_remote_entry_helpers` 13 passed. Full `scripts/ci.py` full/gui not run (bounded run; dirty tree would invalidate freeze claims anyway). |
| `HPC-W10-FREEZE-008` (real-cluster replay required by changes) | PARTIAL (connectivity probe only; full Workstream E replay not executed) | Bounded SSH probe PASS (see EV-W56-EXTERNAL-PROBE). Full connection/reconnect, SFTP round trip, editor save, job submit/cancel, terminal replay against LOCAL_REAL deferred to clean-pin run with exclusive lease. |
| `HPC-W10-FREEZE-012` (candidate build and freeze) | BLOCKED (correctly not built) | No candidate built per invariant (Qt default + dirty tree). No freeze declared. |
| `HPC-W10-FREEZE-014` (connection/reconnect) | BLOCKED (replay deferred) | Probe-only; see external evidence. |
| `HPC-W10-FREEZE-015` (SFTP round trip) | BLOCKED (replay deferred) | Probe-only; no SFTP bytes moved this run. |
| `HPC-W10-FREEZE-016` (remote editor save) | BLOCKED (replay deferred) | Not executed this run. |
| `HPC-W10-FREEZE-017` (job list/submit/cancel) | BLOCKED (replay deferred) | `sinfo`/`squeue` read-only observed via probe; no submit/cancel executed. |
| `HPC-W10-FREEZE-018` (terminal) | BLOCKED (replay deferred) | Not executed this run. |
| `HPC-W10-BUILD-001` (build candidate + provenance) | BLOCKED (correctly not built) | No artifact, no SHA-256, no manifest. Building now would violate clean-source + runtime invariants. |
| `HPC-W10-BUILD-002` (freeze invalidation rule) | VERIFIED (rule honored; no freeze to invalidate) | No product/package-byte change made by W56 this run; nothing to invalidate. |
| `HPC-W10-TODO-RUNTIME-CUTOVER-001` | BLOCKED (decision recorded as pending; no code change) | Runtime still `qt`; cutover requires controller-owned wx-acceptance verdict + clean tree. Finding routed: runtime cutover remains W56-owned work for the clean-pin attempt. |
| `HPC-W10-TODO-RUNTIME-DEPENDENCY-001` | BLOCKED (decision pending) | Dual-runtime spec comment explicitly defers to W56; no dependency claim changed this run. |
| `HPC-W10-TODO-007` (Windows artifact) | BLOCKED | No artifact built (see BUILD-001). |
| `HPC-W10-TODO-008` (artifact identity record) | BLOCKED | No artifact identity to record. |
| `HPC-W10-TODO-009` (runs without source checkout) | BLOCKED | Not provable without an artifact. |

No requirement is claimed IMPLEMENT/VERIFIED beyond the prerequisite/harness rows above. No `NOT_APPLICABLE_ACCEPTED`, no `DEFERRED_CLEAN`, no `AWAITING_INPUT` (no concrete external-authority dependency missing; lab is reachable).

## Tests and evidence

All runs at HEAD `c8293d3c` + dirty tree (unmodified by W56). `PYTHONPATH=src` where applicable.

### EV-W56-BASELINE — narrow baseline → PASS (as baseline, not acceptance)

- ` .venv/Scripts/python.exe -m compileall -q src/hpc_gui` → exit 0.
- `.venv/Scripts/python.exe -m pytest tests/test_version_consistency.py tests/test_remote_entry_helpers.py -q --tb=short -rf` → `13 passed in 0.47s`, exit 0.
- Full suite deliberately not run this bounded BLOCKED run.

### EV-W56-EXTERNAL-PROBE — LOCAL_REAL bounded reachability → PASS (probe only, not Workstream E)

- Target: `LOCAL_REAL_HYPERV`, `hpctest@192.168.250.11:22`, key from emitted lab profile, `BatchMode=yes`, `ConnectTimeout=8`.
- `echo LAB_SSH_OK; hostname; sinfo -h -o %T` → `LAB_SSH_OK`, `login-control01`, `idle` + `down`. Exit 0.
- Read-only follow-up `sinfo -o '%N %T %P'` → `compute02 idle debug*`, `compute01 down debug*`; `squeue --me` header-only (no personal jobs); `ls ~/` shows prior `slurm-*.out` files. Exit 0.
- Interpretation: controller/login transport healthy; Slurm answers; `compute02` idle and usable for single-node replay; `compute01 down` degrades two-node `srun` and must be repaired via maintained lab tooling before W56 claims full Workstream E. No jobs submitted, no files transferred, no editor/terminal replay executed — correctly, since full replay belongs to the clean-pin attempt with an exclusive LOCAL_REAL lease.
- Private keys, VM disks, and generated secrets were not copied into reports/Git. Only host, user, node names, and partition states recorded.

### EV-W56-PACKAGE — packaging baseline → HARNESS-PRESENT (no artifact)

- `build/windows/hpc-client-gui.spec`, `scripts/release.ps1`, `scripts/ci.py::packaging`, `.github/workflows/release.yml` all present.
- No `PyInstaller`/release build executed this run (would be invalid pre-cutover on a dirty tree). No artifact path/SHA-256 to bind.

### EV-W56-VALIDATOR — closeout validator → red as expected for BLOCKED

- `.venv/Scripts/python.exe scripts/validate_wave_closeout.py --wave W56 --no-execute-tests` → `{"can_close": false, "manifest": ".../artifacts/wave_W56/WAVE_W56_EVIDENCE_MANIFEST.json", "failure_reasons": ["missing/invalid evidence manifest"]}`, exit 0 (validator ran; close not allowed).
- No manifest fabricated to force green. A BLOCKED run must leave the validator red.

## Diff review

- `git status --short`: dirty at entry and exit with identical pre-existing sibling modifications; W56 added only this report file (`docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md`, closeout-allowed path).
- `git diff --stat HEAD` (tracked): 38 files, ~2853 insertions/~349 deletions, all pre-existing sibling work, untouched by W56.
- `git diff --check` on W56-owned change: clean (report is prose only; no product/test/build/runtime change).
- Secrets scan: no credentials, keys, tokens, or connection strings added (lab probe used the existing emitted key path; password never handled).
- Weakened tests: none (no test file modified). Duplicated logic: none added. Generated/binary noise: none added.

## Blockers (controller-owned resume)

1. `BLOCKED-CLEAN-SOURCE`: working tree dirty with ~38 behavior-affecting sibling-wave files (`wx_shell`, `wx_jobs`, `wx_editor_view`, `wx_plugins*`, `wx_settings*`, services, plugins, i18n, docs, spec). `BUILD-001` requires a clean pinned source; freezing now would bind the wrong content identity. Resume: controller integrates/stabilizes sibling work into a clean pin, recomputes content identity, then re-dispatches W56.
2. `BLOCKED-RUNTIME-CUTOVER`: `src/hpc_gui/runtime.py` still `DEFAULT_GUI_RUNTIME = "qt"` with Qt-default release path; W11 requires wx production runtime and W56 invariant forbids freezing pre-cutover. Resume: controller confirms wx mandatory acceptance verdict, then W56 (clean-pin attempt) performs `RUNTIME-CUTOVER-001`/`RUNTIME-DEPENDENCY-001` (default flip + packaging/support-text/dependency alignment) with focused retest before any candidate build. No cutover attempted on the dirty tree this run by design.
3. `BLOCKED-FULL-REPLAY`: full Workstream E replay (connection/reconnect, SFTP round trip with byte/hash proof, remote editor save with server-side proof, disposable job submit/cancel, terminal) not executed; bounded probe only. Resume: with exclusive LOCAL_REAL lease on the clean pin, execute the five replay paths with environment/target/profile/requirement binding and cleanup.
4. `PARTIAL-LAB-DEGRADED`: `compute01 down` (`sinfo`: `compute01 down`, `compute02 idle`). Single-node replay viable; two-node `srun` and any test requiring both computes must wait for lab recovery via maintained tooling (`lab-status.ps1`/`lab-test.ps1`/reset path). Not a W56 product defect; infrastructure/orchestration state until diagnosed.
5. `BLOCKED-CANDIDATE`: no candidate filename, main SHA beyond HEAD, plugin SHA/provenance, version, build environment, SHA-256, or manifest exists. Correctly absent. Resume: build one candidate from the clean post-cutover pin, record full provenance, then run packaged/W04-harness regression (W57 scope for packaged acceptance; W56 records the frozen identity).

## Deferred items

- Full `scripts/ci.py` full/gui/docs/audit gates: deferred to clean-pin attempt (bounded BLOCKED run; dirty-tree full-suite green could not support freeze).
- `PyInstaller` Windows candidate build + `scripts/release_smoke` + source-independence proof (`TODO-007/008/009`): deferred behind blockers 1–2.
- `docs/wave-reports/v2/opencode/W56_AUDIT_REPORT.md`: not created by the run worker; reserved for fresh-independent audit after a future `READY_FOR_AUDIT`.
- `artifacts/wave_W56/WAVE_W56_EVIDENCE_MANIFEST.json`: not created; no PASS to manifest.

## Contradiction scan

- No W56 product change to contradict sibling evidence. Report claims match executed commands (compile PASS, 13 tests PASS, SSH probe PASS, validator red). No GUI/PACKAGE/EXTERNAL acceptance claimed beyond the bounded probe. Runtime statements match live files (`runtime.py`, `__main__.py`, spec comment). Lab statements match observed `sinfo` output including the `compute01 down` degradation (not hidden).

## Handoff

- After controller resolves blockers 1–2 and re-dispatches W56 on a clean post-cutover pin, the next W56 attempt must: re-capture baseline, execute full Workstream E replay with exclusive LOCAL_REAL lease (recovering `compute01` first if two-node paths are required), build exactly one candidate with full provenance + SHA-256 + manifest, rerun affected focused tests, refresh this report, and return `READY_FOR_AUDIT` only when every owned requirement is IMPLEMENT with current truthful evidence.
- This worker starts no downstream Wave; scheduling remains controller-owned. Integration references W55 (done) and W57 (pending) are non-blocking hints only.
