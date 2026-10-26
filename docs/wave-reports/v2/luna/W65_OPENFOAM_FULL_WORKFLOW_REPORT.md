# W65 r1 — OpenFOAM v2312 Full Workflow Builder + Linter (engine round)

Status: PARTIAL (engine + linter core DONE; FINAL GO forbidden — VM/runtime BLOCKED_ENV).
Date: 2026-10-25. Head: `e764299070e7b7945d51c8980959ca2759208fcf` (branch `wave-auto`, clean at dispatch).
Backend used for implementation: opencode. No stage/commit/push performed.

## 1. What was built (new canonical sources, authorized by the spec's own matrix/TODO)

`src/hpc_gui/openfoam_core/` (new facade + lexer/parser/safe-patch/case-scan):
`__init__.py`, `lexer.py`, `parser.py`, `safe_patch.py`, `case_scan.py`.
`src/hpc_gui/plugins/openfoam_studio/` (Case Studio 0.3.0-w65r1, base 0.2.1):
`__init__.py`, `catalog_inventory.py`, `command_schemas.py`, `availability.py`,
`geometry_import.py`, `cad_gate.py`, `blockmesh.py`, `snappy.py`, `mesh_quality.py`,
`mesh_regions.py`, `physics.py`, `cht.py`, `boundary.py`, `numerics.py`, `solver.py`,
`monitor.py`, `post.py`, `workflow.py`, `selection.py`, `hpc.py`, `security.py`, `host_adapter.py`.
`src/hpc_gui/plugins/openfoam_lint/` (Linter 0.2.0-w65r1, base 0.1.0):
`__init__.py`, `api.py`, `rules_cross.py`, `rules_physics.py`.
i18n TR+EN: `openfoam` section added to `src/hpc_gui/i18n/en.json`, `tr.json`.
Tests: `tests/test_w65_{core_roundtrip,catalog,mesh,physics,workflow,lint,sftp_slurm,evidence}.py` (45 tests).

No Drive snapshots (S/L), no `waves/done` receipts, no v2312 binary, and no Hyper-V
runners were reachable from this checkout; S/L rows stay SOURCE_UNVERIFIED and
runtime/VM rows BLOCKED_ENV (recorded per-row, never waived).

## 2. Verification (real runs, this head)

- `python -m pytest tests/test_w65_*.py -q` → **45 passed** (log: `artifacts/wave_W65/logs/w65_focused_tests.txt`).
- `python scripts/check_i18n.py` → key/reference/hardcoded checks OK.
- 500-line gate: max owned file 156 lines → PASS (matrix in `artifacts/wave_W65/W65_SOURCE_ARCHITECTURE_500_LINE.md`).
- Baseline at dispatch: clean tree; legacy 8-command catalog preserved and tested.

## 3. Coverage (honest counts)

- Catalog: 35 curated entries (8 legacy 0.2.1 preserved), 20 ACTIVE-TYPED schemas with
  v2312 source anchors; exhaustive site-binary claim BLOCKED_ENV (no v2312 host).
- Gaps: DONE 29/48, PARTIAL 16/48, BLOCKED_ENV 3/48 (`W65_GAP_REGISTER.json/.csv`).
- Journeys: J01–J05/J08 static+draft; J06 BLOCKED_EXTERNAL (no converter, correctly gated);
  J07/J11 live stages BLOCKED_ENV; J09/J10 RAW-ADVANCED/UNSUPPORTED as designed; J12 partial.
- R1–R5 physical runs: NOT_RUN (BLOCKED_ENV). Screenshots: NOT_PRODUCED (no guests).

## 4. Mandatory final summary

WAVE: W65 (r1) | CASE_STUDIO_BASE: 0.2.1 → 0.3.0-w65r1 | LINTER_BASE: 0.1.0 → 0.2.0-w65r1
CURRENT_SOURCE_HASHES: see `W65_SOURCE_BINDINGS.json` (per-file SHA256 + HEAD above)
REQUIREMENT_RESULTS: 22/22 annotated (PARTIAL overall)
CATALOG: discovered 35 / classified 35 / active_typed 20 / runtime_proven 0 / unsupported 1 (reactingFoam)
WORKFLOWS: T1–T8 static/GUI-contract evidence; runtime NOT_RUN
OPENFOAM: esi / target v2312 / binary NOT_FOUND on PATH / MPI n/a
GUI: engine-only round; Windows11/Ubuntu-Test evidence BLOCKED_ENV; DESIGN_PARITY only
LINTER: 16 rules, positive+negative fixtures, standalone importable; CLI/GUI pending
FILES: byte-identity + single-token patch + BOM/CRLF tested; live SFTP injection BLOCKED_ENV
JOBS: Slurm draft-only + rank agreement tested; TRUBA NOT EXECUTED
PACKAGE: install/upgrade/rollback/uninstall NOT_RUN (BLOCKED_ENV)
TESTS: 45 passed / 0 failed / BLOCKED: R1–R5, VM lifecycle, lab SFTP
SECURITY / 500_LINE / REGRESSION: no exec of dynamic directives; max 156 LOC; focused suite green, full host suite not run
GIT: branch wave-auto, HEAD e7642990, no commits/stash/push (PUSH=NO)
RELEASE_VERDICT: **PARTIAL** (FINAL GO forbidden until VM/runtime + independent audit)
UNRESOLVED: W65_REMAINING_EXECUTION_DEBT.md items 1–6; reactivation = lab VM + v2312 host + reviewer
INDEPENDENT_AUDIT: pending (r1 file is implementer self-review only)

## 5. Machine-readable evidence (all under `artifacts/wave_W65/`)

`WAVE_W65_EVIDENCE_MANIFEST.json`, `W65_SOURCE_BINDINGS.json`, `W65_GAP_REGISTER.json/.csv`,
`W65_V2312_COMMAND_COVERAGE.json`, `coverage/CATALOG_COVERAGE_MATRIX.csv`,
`W65_PHYSICS_NUMERICS_BC_SCHEMAS.json`, `W65_JOURNEY_RECEIPTS.json`,
`coverage/WORKFLOW_JOURNEY_MATRIX.md`, `coverage/GUI_PARITY_MATRIX.md`,
`W65_RUNTIME_RECEIPTS.json`, `W65_REMOTE_FILE_TRANSACTION.json`, `W65_LINTER_COVERAGE.json`,
`W65_VM_PACKAGE_MATRIX.json`, `W65_SOURCE_ARCHITECTURE_500_LINE.md`,
`W65_FINAL_INDEPENDENT_AUDIT.md`, `W65_REMAINING_EXECUTION_DEBT.md`, `logs/w65_focused_tests.txt`.

---

# W65 r2 addendum — audit findings F1–F7 (same head `e7642990`, no stage/commit/push)

Assumptions: no Hyper-V runners and no v2312 binary reachable from this checkout
(G44/G45 stay BLOCKED_ENV); matplotlib + wxPython present for headless export/panel-data tests.

## Fixes implemented (all spec-matrix/TODO-named files)

- **F1/G31** — `patch_plan.py` (PatchOp/PatchPlan/preview/apply via `safe_patch`) +
  `workflow_compiler.py` (`compile_patch_plan`, `journey_dag` T1–T12, typed per-file
  bytes from the existing blockMesh/snappy/boundary/numerics/physics/CHT/solver/post
  writers). Guards tested: stale-input edges, solver-before-mesh (tightened:
  `checkMesh` no longer counts as mesh producer), duplicate destructive
  `decomposePar`, destructive-overwrite confirm on apply, unknown tool/param
  rejection. T1–T9/T11–T12 compile; T10 (reactingFoam) correctly refused
  (RAW-ADVANCED/UNSUPPORTED by design).
- **F2/G33 + F7/G35** — `wx_flow.py` (flow cards, DnD reorder model, lazy wx panel via
  host contract, no dead buttons) + `wx_panels.py` (inspector/selector/diff/validation/
  results data + lazy wx builders, TR/EN labels; `openfoam.flow/inspector/source_diff/
  validation/run_preview/results/apply_confirm/revert/linter_unavailable` keys added to
  `en.json` + `tr.json`). Headless interaction trace:
  `artifacts/wave_W65/W65_GUI_INTERACTION_TRACE.json`. Guest DPI/dark-light/TR-EN
  receipts: BLOCKED_ENV (exact runner unblock recorded in the trace).
- **F3/G38** — `openfoam_lint/cli.py` (JSON, exit 0/1/2, counts match `lint_text`
  positions) + `openfoam_lint/policy.py` (disable/enable/severity-override/
  suppress-with-reason, unknown rules rejected). Studio-import-free verified in a
  subprocess.
- **F4/G29** — `plot_export.py` (matplotlib PNG/PDF residual charts + probes over real
  sampled bytes, MISSING on empty, formula/units/provenance; ParaView/VTK handoff with
  real `.foam` stub + ASCII VTK + `foamToVTK` argv).
- **F5/G39/G42** — `job_links.py` (JobLinkStore JSON persist + restart reload +
  best-effort mirror into host `JobRecordStore.job_workspaces`; draft-only kept,
  PARTIAL-never-green preserved). G39 stays PARTIAL: live SFTP multi-file injection
  still needs the lab endpoint.
- **F6/G46** — repo-approved host set run before (pristine HEAD worktree
  `w65-reg-before-20261025`) vs after (this tree); full-set run crashes at HEAD in Qt
  `qapp` teardown (Windows access violation, environmental, pre-existing) — recorded
  in `EV_regression_before.log`; headless-safe subset compared in
  `EV_regression_before_headless.log` / `EV_regression_after_headless.log`.
- **F7** — `surface_actions.py` (G07 quality wizard + featureExtractDict writer/argv),
  `mesh_regions.py` += topoSet writer + zone/split argv + rollback notes (G12),
  `cht.py` += per-region thermophysicalProperties + coupled T-field (G16),
  `advanced_physics.py` (G17 verified multiphase/compressible/buoyant subsets;
  reacting UNSUPPORTED), `advanced_boundaries.py` (G19 cyclic/coupled/mappedWall
  profiles). All with positive + negative fixtures.

## Verification (r2, this tree)

- `python -m pytest tests/test_w65_*.py tests/test_w65_r2_*.py -q` → **84 passed**
  (45 r1 + 39 r2: `test_w65_r2_{compiler,typed,gui,lintcli,post,jobs}.py`).
- 500-line gate: max owned file 370 lines (`workflow_compiler.py`) → PASS.
- Changed files: 11 new sources + 6 new test files + `mesh_regions.py`, `cht.py`,
  `workflow.py` (guard tightening + dead-code removal), `wx_panels.py` (new-file fix),
  `en.json`/`tr.json` (8 panel keys each), evidence JSONs/CSV + this report.
  No stage/commit/push; no `waves/` edits.

## Remaining genuine blockers

- G44/G45/G47: no Windows11/Ubuntu-Test runners, no v2312 binary, no installer
  lifecycle run from this checkout → FINAL GO forbidden; verdict stays **PARTIAL**.
- G03/G13/G39 remainder: exhaustive site-binary inventory + live converter/SFTP
  proof need the lab host; G48 independent audit still pending a reviewer.


# W65 r3 addendum - defect pass + first real guest run (same head e7642990, no stage/commit/push)

Assumptions: no AGENTS.md/rules.md/CLAUDE.md in this checkout; waves/done absent so no predecessor receipt applies; S/L Drive snapshots and v2312 binary unreachable; Hyper-V Windows11 runner reachable (VMs Running) so G44 gets a staged pytest run instead of BLOCKED_ENV-no-contact.

## Fixes implemented (spec-matrix-owned files only)

- G30/workflow.py compile_to_effects: solver branch now covers every classified solver binary (endswith Foam minus ToFoam converters) instead of 4 hardcoded names; pisoFoam/buoyant/rho/inter/reacting/potential/chtMultiRegionFoam previously fell through to a wrong system/<tool>.dict effect. Converter names (meshConverter, fluentMeshToFoam, foamToVTK) explicitly excluded.
- G23/solver.py check_solver_compat: families with no typed models (reacting) now refuse with an explicit RAW-ADVANCED/UNSUPPORTED message instead of a bare model-incompatible error. Behavior unchanged (still raises); T10 journey still refused.
- tests/test_w65_r3_guards.py: 17 new tests (per-solver effect mapping, converter exclusion, explicit refusal messages).

## Verification (r3, this tree)

- Host: python -m pytest tests/test_w65_*.py tests/test_w65_r2_*.py tests/test_w65_r3_guards.py -q -> 104 passed (log artifacts/wave_W65/logs/w65_focused_tests_r3.txt).
- python scripts/check_i18n.py -> key/reference/hardcoded checks OK.
- 500-line gate: max owned source 370 lines (workflow_compiler.py) -> PASS (W65_SOURCE_ARCHITECTURE_500_LINE.md regenerated).
- Bindings regenerated from tree bytes: 59 files with fresh SHA256/LOC (W65_SOURCE_BINDINGS.json round 3).
- Guest (Windows11, test/home, Python 3.14.7, pytest 9.1.1) via C:/Users/mskomek/.hyperv-tools/Invoke-Windows11.ps1 + Copy-VMFile: 63 zip files SHA-verified 63/63 on arrival + 5 host-service files hash-matched; focused suite 102 passed, 2 failed env-only (test_w65_r2_post chart tests need matplotlib, absent in guest, no install per policy). One interim lintcli failure was a CWD artifact of the guest invocation (test hardcodes PYTHONPATH=src); rerun from C:/w65-r3/candidate passes. Full log artifacts/wave_W65/logs/w65_guest_r3.txt.

## Changed files

- src/hpc_gui/plugins/openfoam_studio/workflow.py, solver.py (edits above); tests/test_w65_r3_guards.py (new); artifacts/wave_W65/{WAVE_W65_EVIDENCE_MANIFEST.json, W65_SOURCE_BINDINGS.json, W65_GAP_REGISTER.json, W65_SOURCE_ARCHITECTURE_500_LINE.md, logs/w65_focused_tests_r3.txt, logs/w65_guest_r3.txt} refreshed; this report. No stage/commit/push; no waves/ edits; nothing written to D:/MyDrive/Projeler.

## Remaining genuine blockers

- G44 remainder: guest pytest staged-run DONE; full install/upgrade/rollback/uninstall matrix + Ubuntu-Test + GUI screenshots still BLOCKED_ENV (need packaging + interactive runner).
- G45/G47: no v2312 binary, no installer lifecycle -> FINAL GO forbidden; verdict stays PARTIAL.
- G03/G13/G39 remainder + G48 independent audit: unchanged from r2.


# W65 r4 addendum - manual-audit G30 workflow-effect mismatch (same head e7642990, no stage/commit/push)

Assumptions: no AGENTS.md/rules.md/CLAUDE.md in this checkout (AGENTS.md verified absent);
waves/done absent so no predecessor receipt applies; Drive snapshots and v2312 binary
unreachable; Windows11 runner reachable (all 5 VMs Running) so the focused suite runs
staged in the guest instead of claiming host-only success. Changed files below are
authorized by the round-4 operator finding (implementation finding, not env blocker).

## Finding (independent source review after r3 PASS)

`compile_to_effects()` claimed to map node file mutations but emitted fictitious
`system/<tool>.dict` paths for supported/non-dictionary nodes: `surfaceFeatureExtract`
actually compiles to `system/surfaceFeatureExtractDict`; `splitMeshRegions` compiles to
`constant/regionProperties`; `meshConverter` compiles to a verify/import target under
`constant/polyMesh`; read-only/utility nodes must not be assigned fake dictionaries.
Round-3 `test_converters_not_mapped_to_solver_triple` only asserted inequality and
missed the false fallback.

## Fix (spec-matrix-owned files only)

- G30/workflow.py `compile_to_effects`: audited every node type accepted by
  `workflow_compiler._ops_for_tool` against its PatchOp targets/modes. Now:
  `surfaceFeatureExtract` -> `system/surfaceFeatureExtractDict`; `splitMeshRegions` ->
  `constant/regionProperties`; `postProcess`/`foamToVTK`/`reconstructPar` (verify-only
  `postProcessing/<tool>.report` previews) -> `[]`; `meshConverter`/`checkMesh`/`cadGate`/
  `sftpStage`/`lifecycleGate`/`meshIntake`/`surfaceIntake` (verify-only) -> `[]`;
  `forces`/`forceCoeffs`/`yPlus`/`wallShearStress` join `probes`/`fieldAverage` at
  `system/controlDict#functions`; solver set pinned to `SOLVER_BINARIES` keys
  (new `SOLVER_TOOLS`, drift-tested) instead of the `endswith("Foam")` heuristic, so
  unclassified `*Foam` names no longer map to the triple; unknown/RAW-ADVANCED tools ->
  `[]` (no fictitious `system/<tool>.dict`). Solver-triple mapping preserved; no
  execution behavior changed (function is static).
- tests/test_w65_r3_guards.py: 27 new assertions - exact positive tests for all 5
  dictionary targets, all 6 function objects, all 10 verify-only tools; negative tests
  for `fluentMeshToFoam`/`gmshToFoam`/unknown tools (exact `[]`, not just inequality),
  unclassified `customFoam`, and `SOLVER_TOOLS == set(SOLVER_BINARIES)` drift guard.

## Verification (r4, this tree; guest-only per gate, no host pytest claimed)

- Guest (Windows11, test/home, Python 3.14.7, pytest 9.1.1) via
  C:/Users/mskomek/.hyperv-tools/Invoke-Windows11.ps1 + Copy-VMFile: candidate zip
  sha256 5654972c4586fa017c60184e2e1f7b1569c6b98aca605ef2e8fd97a98f8d5edc verified
  identical host==guest, expanded to C:/w65-r4/candidate, run with PYTHONPATH=src from
  that dir: 129 passed, 2 failed env-only (test_w65_r2_post chart tests need matplotlib,
  absent in guest, no install per policy). Focused trio
  (test_w65_workflow + test_w65_r3_guards + test_w65_r2_compiler): 72 passed.
  Full log artifacts/wave_W65/logs/w65_guest_r4.txt.
- 500-line gate: max owned source 370 lines (workflow_compiler.py); workflow.py 199 lines
  -> PASS (W65_SOURCE_ARCHITECTURE_500_LINE.md regenerated).
- Bindings regenerated from tree bytes: 59 files with fresh SHA256/LOC
  (W65_SOURCE_BINDINGS.json round 4; workflow.py 9c196f2b..., test_w65_r3_guards.py c7f09ff3...).

## Changed files

- src/hpc_gui/plugins/openfoam_studio/workflow.py (fix above);
  tests/test_w65_r3_guards.py (27 new assertions);
  artifacts/wave_W65/{WAVE_W65_EVIDENCE_MANIFEST.json, W65_SOURCE_BINDINGS.json,
  W65_SOURCE_ARCHITECTURE_500_LINE.md, logs/w65_focused_tests_r4.txt, logs/w65_guest_r4.txt}
  refreshed; this report. No stage/commit/push; no waves/ edits; nothing written to
  D:/MyDrive/Projeler.

## Remaining genuine blockers

- G44 remainder: guest pytest staged-run DONE (r4: 129 green + 2 matplotlib-env fails);
  full install/upgrade/rollback/uninstall matrix + Ubuntu-Test + GUI screenshots still
  BLOCKED_ENV (need packaging + interactive runner).
- G45/G47: no v2312 binary, no installer lifecycle -> FINAL GO forbidden; verdict stays PARTIAL.
- G03/G13/G39 remainder + G48 independent audit: unchanged from r3.


# W65 r5 addendum - manual-audit solver-effect completeness (same head e7642990, no stage/commit/push)

Assumptions: no AGENTS.md/rules.md/CLAUDE.md in this checkout (AGENTS.md verified absent);
waves/done absent so no predecessor receipt applies; Drive snapshots and v2312 binary
unreachable; Windows11 runner reachable (Running) so the focused suite runs
staged in the guest instead of claiming host-only success. Changed files below are
authorized by the round-5 operator finding (implementation finding, not env blocker).

## Finding (independent source review after round-4 PASS)

Round-4 audit proved only that each solver's numerics triple is a SUBSET of
`_ops_for_tool` PatchOp targets. `compile_to_effects()` claims a complete map of
files a node mutates and its docstring says it mirrors exact PatchOp targets, but
`workflow_compiler._solver_files()` emits additional target files for valid solver
nodes: `0/<field>`, `constant/transportProperties`, `constant/turbulenceProperties`,
and family-specific `constant/thermophysicalProperties` / CHT
`constant/regionProperties` and per-region thermophysical files. The solver mapping
and tests asserted only the three numerics paths, so G30 effects were incomplete
and preview consumers could miss mutations.

## Fix (spec-matrix-owned files only)

- New leaf `solver_effects.py` (openfoam_studio, 107 lines, imports only
  foundation `hpc_gui.openfoam_core.physics`): canonical `SOLVER_BINARIES`,
  `bound_state()` (family/model/fields/regions binding with compiler-identical
  defaults + explicit RAW-ADVANCED/UNSUPPORTED refusal for reacting/potential,
  incompatible models, missing fields, empty CHT regions) and
  `solver_effect_paths()` (complete ordered path list mirroring `_solver_files`
  relpaths exactly). No dependency cycles: `workflow.py` and `workflow_compiler.py`
  both bind through this leaf; `workflow.py` no longer duplicates the solver set
  (`SOLVER_TOOLS = frozenset(SOLVER_BINARIES)` via the leaf) and `solver.py`
  re-exports the canonical mapping plus an explicit (no-KeyError) refusal for
  unknown families such as potential.
- `workflow_compiler._solver_files` now binds via `solver_effects.bound_state`
  (also fixing its CHT default inconsistency: bound default regions instead of
  raising on absent `regions`, identical to the preview binding); content
  rendering unchanged, path order identical to `solver_effect_paths`.
- Bare/default params bind identically in both: simpleFoam (schema-required only),
  interFoam (bare), rhoSimpleFoam (model default would be invalid, so explicit
  model) all assert preview == compiler PatchOp targets == shared-source paths.
  CHT custom regions (`fluidA/fluidB/solidA`) assert exact per-region file lists.
- tests/test_w65_r3_guards.py: replaced subset-only triple assertion with
  equality tests (effect paths == ALL mutating PatchOp targets, action in
  create/replace/append-token) for representative valid simple, transient,
  compressible, buoyant, multiphase and CHT solver nodes; default-binding
  equality; custom-CHT-region exact paths; reacting/potential refusal in BOTH
  effects and compiler (no weakening: old inequality test superseded by exact
  positive + negative coverage).

## Verification (r5, this tree; guest-only per gate, no host pytest claimed)

- Guest (Windows11, test/home, Python 3.14.7, pytest 9.1.1) via
  C:/Users/mskomek/.hyperv-tools/Invoke-Windows11.ps1 + Copy-VMFile: candidate zip
  sha256 80c26148232903e7089b125b2a90fde5c13235132914efa0b91725ca3aff587 verified
  identical host==guest (artifacts zip 21af3ecd2277b6ce9132f83a2614d0b77db17db3fa60e912588613a37f6ddaa4,
  also host==guest), expanded to C:/w65-r5/candidate (+C:/w65-r5/artifacts for the
  REPO-relative evidence test), run with PYTHONPATH=src from that dir:
  135 passed, 2 failed env-only (test_w65_r2_post chart tests need matplotlib,
  absent in guest, no install per policy). Focused trio
  (test_w65_workflow + test_w65_r3_guards + test_w65_r2_compiler): 78 passed.
  Full log artifacts/wave_W65/logs/w65_guest_r5.txt (byte-exact guest output).
- 500-line gate: max owned source 376 lines (workflow_compiler.py); solver_effects.py
  107 lines -> PASS (W65_SOURCE_ARCHITECTURE_500_LINE.md regenerated).
- Bindings regenerated from tree bytes: 60 files with fresh SHA256/LOC
  (W65_SOURCE_BINDINGS.json round 5, +solver_effects.py; head e7642990 unchanged).

## Changed files

- src/hpc_gui/plugins/openfoam_studio/solver_effects.py (new, leaf);
  workflow.py, workflow_compiler.py, solver.py (shared-source binding);
  tests/test_w65_r3_guards.py (equality + refusal tests);
  artifacts/wave_W65/{WAVE_W65_EVIDENCE_MANIFEST.json (round 5, G30 row),
  W65_SOURCE_BINDINGS.json (round 5, 60 files), W65_SOURCE_ARCHITECTURE_500_LINE.md,
  logs/w65_focused_tests_r5.txt, logs/w65_guest_r5.txt} refreshed; this report.
  No stage/commit/push; no waves/ edits; nothing written to D:/MyDrive/Projeler.

## Remaining genuine blockers

- G44 remainder: guest pytest staged-run DONE (r5: 135 green + 2 matplotlib-env fails);
  full install/upgrade/rollback/uninstall matrix + Ubuntu-Test + GUI screenshots still
  BLOCKED_ENV (need packaging + interactive runner).
- G45/G47: no v2312 binary, no installer lifecycle -> FINAL GO forbidden; verdict stays PARTIAL.
- G03/G13/G39 remainder + G48 independent audit: unchanged from r4 (audit/confirm run
  by the loop controller as a separate fresh-independent step, not in this implement round).



# W65 r6 addendum - exhaustive G30 effect-target equality (same head e7642990, no stage/commit/push)

Assumptions: no AGENTS.md/rules.md/CLAUDE.md in this checkout (verified absent);
waves/done absent so no predecessor receipt applies; Drive snapshots and v2312 binary
unreachable; Windows11 runner reachable (Running) so the focused suite runs
staged in the guest instead of claiming host-only success. Changed files below are
authorized by the round-3/round-4 operator findings (implementation findings on G30
truthfulness, not env blockers); no product-code change was needed in r6.

## Finding (leftover weak assertion from rounds 4-5)

`test_converters_not_mapped_to_solver_triple` still asserted only inequality
(`!= SOLVER_TRIPLE`) for `meshConverter`/`fluentMeshToFoam`/`foamToVTK`, while every
other G30 test had moved to exact equality. Inequality cannot catch a fictitious
`system/<tool>.dict` fallback or a dropped verify-only path. The round-4 finding
required exact positive/negative tests for these cases; the round-5 finding required
equality (not subset) between effect paths and ALL mutating PatchOp targets, but its
new tests covered only solver nodes, leaving all non-solver typed tools without a
preview==compiler equality proof.

## Fix (tests only; product code already truthful)

- Audited every tool branch accepted by `workflow_compiler._ops_for_tool` against
  `workflow.compile_to_effects`: blockMesh / surfaceFeatureExtract / snappyHexMesh /
  decomposePar / splitMeshRegions / meshConverter(verify) / 6 function objects
  (append-token) / postProcess+foamToVTK+reconstructPar(verify) / 12 classified
  solvers via shared leaf `solver_effects` / 6 VERIFY_ONLY gates -> all exact
  matches; unknown/RAW-ADVANCED tools -> `[]` in preview while the compiler raises
  (deliberate preview-vs-compile difference, no fictitious path). No product-code
  edit required; no solver-triple/behavior change.
- tests/test_w65_r3_guards.py (293 lines): strengthened the converter test to exact
  `== []` plus compiler-side zero-mutating-op proof for meshConverter/foamToVTK
  chains; new `test_effects_equal_mutating_patchop_targets_all_typed_tools` (one
  guard-satisfying DAG over every typed non-solver tool, per-node effects == all
  create/replace/append-token PatchOp relpaths); new meshConverter-chain and
  6-way parametrized function-object equality tests. Restored
  `test_reacting_refusal_names_raw_advanced` after an edit slip (verified present).
  No test weakening: old inequality kept as a secondary assertion.

## Verification (r6, this tree; guest-only per gate, no host pytest claimed)

- Guest (Windows11, test/home, Python 3.14.7, pytest 9.1.1) via
  C:/Users/mskomek/.hyperv-tools/Invoke-Windows11.ps1 + Copy-VMFile: candidate zip
  sha256 c6d85edf80b0b68968cc1ae678860469c31d3dc823b347a0c37258e0d0680393 verified
  identical host==guest, expanded to C:/w65-r6/candidate (artifacts/wave_W65 bundled
  inside so the REPO-relative evidence test resolves), run with PYTHONPATH=src from
  that dir: 143 passed, 2 failed env-only (test_w65_r2_post chart tests need
  matplotlib, absent in guest, no install per policy). Focused trio
  (test_w65_workflow + test_w65_r3_guards + test_w65_r2_compiler): 86 passed.
  Full log artifacts/wave_W65/logs/w65_guest_r6.txt (byte-exact guest output).
- 500-line gate: test_w65_r3_guards.py 293 lines; max owned source 376 lines
  (workflow_compiler.py); solver_effects.py 107 lines -> PASS.
- Manifest/bindings heads already e7642990 == current HEAD -> no regeneration needed.

## Changed files

- tests/test_w65_r3_guards.py (exact converter assertions + exhaustive equality tests);
  artifacts/wave_W65/{logs/w65_focused_tests_r6.txt, logs/w65_guest_r6.txt} new;
  this report (r6 addendum). No stage/commit/push; no waves/ edits; nothing written
  to D:/MyDrive/Projeler.

## Remaining genuine blockers

- G44 remainder: guest pytest staged-run DONE (r6: 143 green + 2 matplotlib-env fails);
  full install/upgrade/rollback/uninstall matrix + Ubuntu-Test + GUI screenshots still
  BLOCKED_ENV (need packaging + interactive runner).
- G45/G47: no v2312 binary, no installer lifecycle -> FINAL GO forbidden; verdict stays PARTIAL.
- G03/G13/G39 remainder + G48 independent audit: unchanged from r5 (audit/confirm run
  by the loop controller as a separate fresh-independent step, not in this implement round).



