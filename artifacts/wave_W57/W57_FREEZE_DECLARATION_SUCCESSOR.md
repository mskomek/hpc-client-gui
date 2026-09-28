# W57 — Successor Freeze Declaration (post-W30-owner-repair rebind, run phase 110)

Wave: `W57` (execution kind, canonical_source `W57`).
Run phase worker: opencode executor, project-authorized model route.
Phase instance: `20260925-074235-63df86b0:155:W57:run` (re-bound at run phase 155; the identity
block was re-bound at repair 144; previously `…:110:W57:run`).
Candidate commit:  `bdf6c6c7e2817422b6f9005873247d3636c5eac4` (branch `develop`) — the tested
working-tree content is now resolvable to a real Git commit (canonical report section 23).
Content identity (controller handoff, W57's own): `692e534df1c49b8d420f2e04999c8487216cc27575dd90f1347f4be1c44fcb07`.
  *(Re-bound at repair 144. This line previously recorded
  `8f522decd2c83afd9ffb70dd7ad36e19b73c1617bca4278c47093aabcdfad839`, which is **W30's**
  `audit_receipt.tested_content_identity` from the controller handoff, not W57's own identity.
  The two are unrelated identities and must never be substituted for one another; the one
  legitimate W30 reference in this file is the W30 audit receipt quoted in the product-delta
  block below, which is labelled as such. See the canonical report §17.)*

This file is the **single** W57 freeze declaration. It has been rebound three times; the earlier
revisions are retained verbatim in §A/§B so the history stays auditable.
Prior declaration: `artifacts/wave_W57/W57_FREEZE_DECLARATION.md` (blocked record, Main
`36d6151f`, SHA `6cca43a5`, 172 files, Frozen-for-W58 NO) — retained as history.

## Successor frozen candidate (REBUILT after the W30 closed-owner repair, run phase 110)

```text
Candidate ID:      W57-successor-2 / post-DEF-W57-008-W30-repair
Main SHA:          `f6ab257fbfd62d402e31e9330f30bb017b795fa8`
Branch:            `develop`
Plugin SHA:        in-tree at the same HEAD (no separate registry repo)
Product delta vs Main SHA:
                   `src/hpc_gui/services/job_submit_cancel.py` only — the W30
                   closed_owner_repair that removed the 2-line `if "#SBATCH" not in text`
                   gate. Applied in the working tree, independently audited PASS
                   (audit_candidate_sha `f6ab257f`; that W30 audit receipt carries
                   **W30's** content identity `8f522dec…`, which is not W57's identity).
Product tracked-tree SHA-256: `23b314013d7bc5e28562f8fc771ceff27e48e9da002b8c1ee315dba121b2bc78`
Artifact:          `dist/hpc-client-gui/hpc-client-gui.exe`
SHA256:            `8BA80453A76A664959BAEDF7716C476A5334B6AFF860A4BC79B9E220D48B4C57`
Exe size:          7672468 bytes
Built:             Windows 11 AMD64 (10.0.26200), Python 3.14.0, PyInstaller 6.22.2, wxPython 4.3.1
Build command:     `.venv/Scripts/python.exe -m PyInstaller -y --clean build/windows/hpc-client-gui.spec`
Bundle:            172 files, 0 Qt tokens (no `PySide*`, no `shiboken*`, no `Qt6*.dll`)
Version:           1.5.9 (read from outside the repo, exit 0)
Doctor:            `status: PASS, frozen: True` (exit 0, read from outside the repo)
Support matrix revision: `docs/wiki/Compatibility-and-Support-Matrix.md` at `f6ab257f`
Open P0:           0
Open P1:           0  (DEF-W57-008 closed by the W30 repair and verified this phase)
Open P2:           7  (DEF-W57-007, -010, -011, -012, -013 and the two P2 node ids in -010;
                    DEF-W57-016 is RESOLVED at repair phase 111 as environmental, not product)
Open P3:           4  (DEF-W57-009, -014, -015)
Frozen for W58:    NO — the owned mandatory gate group FREEZE-030/-040 is now GREEN and
                     the sole reason that blocked this declaration, DEF-W57-006, is
                     **RESOLVED**. Re-measured in run phase 155: `lab/lab-status.ps1`
                     exit 0 / status PASS with `compute02` (192.168.250.13)
                     `transport_ok=true`, `services_ok=true`, Slurm `compute01|idle
                     compute02|idle`, `image_pin_ok=true`; the maintained
                     `lab/lab-test.ps1` then returned **23/23 required gates true,
                     failed=[], failed_count=0, exit 0 in 32.8 s**
                     (`lab/evidence/LOCAL_REAL_TEST.json`, generated_at
                     2026-09-28T11:30:48Z). See the canonical report section 23.
                     A **new** measured reason now blocks the freeze, and it is NOT
                     W57-owned: the maintained packaged-regression gate
                     `scripts/wx_packaged_smoke.py` is no longer hermetic.
                     `W57-PKGREG-HARNESS-25S-BUDGET-NON-HERMETIC` — the default
                     entrypoint returns **1/20, exit 1, three runs out of three
                     (27.4 s / 27.7 s / 28.8 s)** on this unchanged candidate, because
                     `run_packaged_smoke(..., timeout=25)` kills the child at 25 s and
                     the `timed_out` branch (`scripts/wx_packaged_smoke.py:190-192`)
                     never reads the packaged runtime evidence, leaving every check at
                     its initial FAIL. The identical candidate and the identical,
                     UNMODIFIED harness function return **PASS 20/20** when given the
                     harness's own 240 s constant (`run_fresh_user_smoke`, line 346) —
                     3 m 37.98 s wall clock. Desktop contamination is ruled out: 0
                     WerFault processes, 0 matching topmost windows, and a manual launch
                     shows a live `HPC Client` frame. The 25 s budget passed 3/3 on this
                     same host earlier today; it now fails because three lab VMs are up
                     (63% CPU across 12 logical CPUs). The true owner is the W04
                     packaging-harness surface (`HPC-W04-FRESH-009` -> W15,
                     `HPC-W04-HARNESS-025` -> W16); W57 consumes that harness and may
                     not change its timing policy. **W58 must not consume this
                     declaration.** Evidence:
                     `artifacts/wave_W57/W57_RUN155_PKGREG_HARNESS_BUDGET_DEFECT.json`,
                     `W57_PACKAGED_SMOKE_RUN155_{1,2,3}.json`. This line previously
                     cited DEF-W57-018 (withdrawn at repair 113), DEF-W57-017 (closed and
                     verified at repair 116) and DEF-W57-006 (the only remaining reason);
                     all three are now resolved and the first two remain resolved.
```

### Superseded candidate (history, not the candidate)

```text
Candidate ID:      W57-successor / post-DEF-W57-001-repair   [SUPERSEDED by run phase 110]
Main SHA:          `f6ab257fbfd62d402e31e9330f30bb017b795fa8`
SHA256:            `CAA5904AD0BE8ADEFA9A6E362D29945A9D9175C963BC75F4DC79A447EAB38A15`
Exe size:          7672516 bytes / 172 files / zero Qt tokens
Frozen for W58:    NO
Superseded because: the W30 closed-owner repair changed product source, which under
                   W57's frozen-candidate invariant ("any product ... correction invalidates
                   W56; route to the owner, rebuild, then rerun affected W56/W57 evidence")
                   invalidates this candidate. It was REBUILT, not patched. Its packaged
                   evidence (4 x 20/20 green) is preserved unmodified under
                   `artifacts/wave_W57/W57_PACKAGED_SMOKE_CAA5904A*.json` and is
                   explicitly NOT reused for the new candidate.
Rollback target:   `6cca43a5` (W57_FREEZE_DECLARATION.md) remains separately named (FREEZE-047).
```

## Why the rebuild was required and what it did NOT do

The W30 repair removed `if "#SBATCH" not in text: errors.append(...)` at
`src/hpc_gui/services/job_submit_cancel.py:119-120`. That is a **product** file, so the
frozen-candidate invariant applied: the previous candidate was invalidated, the candidate was
rebuilt from the post-repair product with the maintained build path, and every gate that binds
to artifact bytes was re-executed against the new SHA. No byte of the previous candidate was
patched, and no W57-owned product, build-input, spec or lock file was changed by this run.

**The build is not bit-reproducible.** Three builds of the *pre-repair* product and two builds
of the *post-repair* product were produced this phase:

| Build | Product | Size | SHA-256 (first 8) |
|---|---|---|---|
| 1 | post-repair | 7672468 | `9DEDBEA3` |
| 2 | pre-repair | 7672516 | `F904FAAF` |
| 3 | post-repair | 7672468 | `8BA80453` |

Identical product bytes therefore do not reproduce an identical SHA-256 (PE timestamps). The
declared SHA-256 binds to **these exact on-disk bytes**, which is what FREEZE-045 asks for; it
is not a reproducible-from-source identity and must not be read as one. Size is a stable
control: pre-repair 7672516 = the superseded `CAA5904A` size exactly, post-repair 7672468 =
-48 bytes, consistent with the removed two-line gate.

## Acceptance state at this candidate (run phase 110)

- **FREEZE-029 — SATISFIED BY ITS SECOND BRANCH, not green.** `scripts/ci.py full` exits 1
  with **15 failed, 3000 passed, 36 skipped, 32 deselected, 2 warnings, 29 subtests passed
  in 736.27s** (was 28 failed / 2986 passed). The 15 decompose as 12 node ids mapped to 8
  P2/P3 root causes that each carry an explicit owner, impact, workaround and deferral
  decision, plus 3 measured non-repository artifacts. No P0 and no P1 is open. Full triage:
  `artifacts/wave_W57/W57_DEFECT_TRIAGE_WORKSTREAM_H_POST_W30_REPAIR.json`.
- **FREEZE-033 — SATISFIED.** DEF-W57-008 was the only open P1; it is closed and verified
  (`tests/test_wx_editor_cross_view_actions.py` 14 passed exit 0; `tests/test_w30_submit_cancel.py`
  16 passed exit 0; suite failures 28 -> 15).
- **FREEZE-009 / -032 / -041 / PKGREG-001 / TODO-012 / TODO-RUNTIME-CUTOVER-003 — GREEN as of
  repair phase 111.** Superseding run phase 110's 14/20 red: that red was caused by four stale
  topmost `WerFault` crash-report dialogs (class `#32770`, title `Python`) left by crashed
  `python.exe` processes, which covered the smoke frame and stole foreground at the synthetic
  WebView click. Proven by direct measurement — the frame rect (130,130)-(1410,890) puts the
  click point at (770,510), 1 pixel inside the dialog rect (769,394)-(1135,580) on the primary
  display — and by a 10 ms foreground poll captured during the failure. Run phase 110's
  multi-display coordinate-virtualization explanation is **disproven**. With the dialogs closed
  and nothing else changed, the **unmodified** harness returns **20/20, exit_code 0** on the
  same unmodified candidate `8BA80453` on **3/3** runs, `isolated_from_src: true`, with no
  dialog regenerated. No product, test, harness or build file was changed by that repair.
  Evidence: `W57_PACKAGED_SMOKE_8BA80453_PASS.json` (+`_RUN2`, `_RUN3`),
  `W57_PACKAGED_SMOKE_8BA80453_PASS_SUMMARY.json`, `W57_REPAIR111_ROOT_CAUSE_PROOF.json`,
  `W57_DEF_W57_016_SUPERSESSION.json`. The superseded red result and finding are retained
  unmodified for audit.
- **FREEZE-030 / -040 — BLOCKED (EXTERNAL), re-measured at repair phase 111.**
  `lab/lab-status.ps1` exits 3, `status: FAIL`, `slurm.ok: false`, `sinfo -N` reports
  `compute02|down*`. `compute01` (192.168.250.12) answers ping and TCP/22; `compute02`
  (192.168.250.13) answers neither. The documented recovery `lab/lab-up.ps1` calls
  `Require-Admin` and drives `Get-VM`/`Stop-VM`/`Start-VM`; this session runs as
  `MSKOMEK\mskomek` with `IsAdministrator=False` and `Get-VM` fails with an authorization
  error, so recovery needs an elevated operator session. Environment identity
  `LOCAL_REAL_HYPERV`, image SHA-256 pin verified. Two-node Slurm paths are unavailable, so
  the required real-cluster regression cannot be completed. Evidence:
  `artifacts/wave_W57/W57_LAB_STATUS_RUN110.json`, `W57_REPAIR111_ROOT_CAUSE_PROOF.json`.
- **FREEZE-034 — SATISFIED.** Every P2/P3 and every measured artifact carries an explicit
  decision.
- **FREEZE-031 / -045 — PASS** for this candidate: Main SHA, product delta, product tree
  hash, artifact SHA-256, size, bundle file count, Qt-token count, build command, build
  environment, `version` and `doctor` readback are all recorded above.
- **FREEZE-011 / -023..-027 / -039 — PASS.** `scripts/check_i18n.py` 3/3 OK, `ci.py docs`
  exit 0, `ci.py packaging` exit 0 (`1 passed, 3 deselected`), `ci.py audit` exit 0
  (`No known vulnerabilities found`), all fresh at this run.
- **FREEZE-013 — PASS.** This run changed no W57-owned product, build-input, spec or lock
  file. The only working-tree source change is the controller-dispatched W30 repair, which
  was not authored or extended here.
- **FREEZE-044 — DELIBERATELY NOT WRITTEN.** A manifest requires `status: ACCEPTANCE_GREEN`.
  **FREEZE-030/-040 are the only red owned rows** (corrected at repair phase 120; this line
  previously also named `FREEZE-009`/`-032`/`-041`, which have been GREEN since repair 111),
  so any green manifest would fabricate evidence.
- **FREEZE-046 — PASS as a truthful artifact.** This declaration records
  `Frozen for W58: NO` with the measured reason.
- **FREEZE-048 — PASS as a contract statement.** W58 may not consume this declaration while
  `Frozen for W58: NO`.

## §A — Revision history (retained verbatim in substance)

**Revision 1 (attempt 16/20, post-DEF-W57-001 W28 repair):** candidate `CAA5904A`, Main
`f6ab257f`, `Frozen for W58: NO` after run phase 99 measured the packaged/GUI/EXTERNAL rerun
as RED. The earlier "YES (values)" line was a prediction and was withdrawn.

**Revision 2 (repair 102, EV-14/EV-15):** identity block re-verified on disk; the packaged
gate re-run unmodified at its default 25 s budget returned `result: PASS`, 20/20,
`exit_code: 0`, `isolated_from_src: true` — 4 independent green runs at `CAA5904A`. The
correction in revision 1 was narrowed to FREEZE-029 only.

**Revision 3 (run phase 110):** the W30 closed-owner repair for DEF-W57-008
landed in product source, so `CAA5904A` was invalidated and the candidate was REBUILT to
`8BA80453`. FREEZE-029 moved 28 -> 15 failures with zero open P0/P1. The packaged gate, which
was green four times at `CAA5904A`, was recorded as red 14/20 in this desktop environment with
`Frozen for W58` remaining **NO**.

**Revision 5 (repair phase 112, this file's current state):** the required real-cluster
regression was executed for the first time — earlier phases had only run the health check. Its
`WAVE_PHASE_STATUS` stays `REOPEN`, but the *reason* is now measured rather than assumed:
`FREEZE-030`/`FREEZE-040` name no node count, and the regression is blocked by three
independent causes, of which only one is the lab outage. (1) the maintained client CLI refuses
all remote commands behind a default-off global setting with no unattended opt-in (DEF-W57-018);
(2) the maintained lab regression hangs instead of failing because it has no command timeout
(DEF-W57-017); (3) `compute02` is down and needs an elevated operator, and this session holds
neither the Administrators role nor `BUILTIN\Hyper-V Administrators` (DEF-W57-006). The
`Frozen for W58: NO` verdict is unchanged; the candidate is **unchanged** at `8BA80453` and no
product, test, spec, build or lab-configuration file was modified.

**Revision 4 (repair phase 111):** the 14/20 red was root-caused.
Four stale topmost `WerFault` crash dialogs from crashed `python.exe` processes covered the
smoke frame; the WebView centre click point (770,510) fell 1 pixel inside the dialog rect
(769,394)-(1135,580) on the primary display, so the synthetic click was delivered to the
dialog and foreground was lost. The multi-display explanation recorded in revision 3 is
**disproven**. After closing the dialogs — with no repository change of any kind — the
unmodified harness returns 20/20 exit 0 on the same candidate on 3/3 runs. FREEZE-009/-032/
-041 and PKGREG-001 therefore move RED -> GREEN. `Frozen for W58` remains **NO** for the one
remaining reason: FREEZE-030/-040 EXTERNAL, `compute02` down, recovery requiring Administrator
elevation unavailable to this session. The candidate is **unchanged** at `8BA80453`; no rebuild
was needed or performed, because nothing about the product changed.

## §B — What is NOT waived (resume point)

1. **Packaged regression — RESOLVED at repair phase 111 (DEF-W57-016).** Root-caused to stale
   topmost `WerFault` crash dialogs covering the smoke frame, not a product defect and not the
   multi-display issue revision 3 assumed. Cleared environmentally; unmodified harness is now
   20/20 exit 0 on candidate `8BA80453` across 3 runs. Evidence bound to this candidate. The
   one residual, deliberately **not** claimed as done: `wx_shell.py` still assumes no
   third-party topmost window overlaps the frame. That hardening is outward-routed (owner
   UNRESOLVED) and out of W57 scope.
2. **Real-cluster regression — STILL OPEN, and wider than the lab outage (repair phase 112).**
   The required regression (`FREEZE-030`/`FREEZE-040`, Workstream E) had **never been executed**
   in any earlier phase; only the `lab/lab-status.ps1` health check had been. Running it changed
   the diagnosis, so item 2 below replaces the single-cause story:
   - **DEF-W57-018 (repository-owned, no elevation needed).** The maintained client CLI refuses
     every remote command: `src/hpc_gui/cli/main.py:960` requires the **global** default-off
     setting `cli_external_access_enabled` (`src/hpc_gui/config/storage.py:434-443`). No CLI
     flag and no environment override exist, so an unattended run is impossible even though
     `docs/testing/LOCAL_HPC_LAB.md` documents exactly that unattended procedure. Measured:
     12 of 13 Workstream E steps refused, `W57_WORKSTREAM_E_REAL_CLUSTER_REPLAY.json`.
     Resolution: the owner exposes a scoped opt-in, or the doc is corrected. The gate itself
     must not be weakened, and it was not.
   - **DEF-W57-017 (repository-owned, no elevation needed).** `lab/lab-test.ps1` **hangs**: its
     two-node `srun` pends forever on a DOWN node because `Invoke-LabSshCapture` sets no command
     timeout, so the harness can neither pass nor fail. A leaked step from an earlier phase had
     been alive 5.47 h. Resolution: bound the command, or use a time-limited allocation. The
     leaked pending jobs were cancelled and `squeue` verified empty.
   - **DEF-W57-006 (external, elevation required).** `compute02` (192.168.250.13) is still down.
     Recover it with `lab/lab-up.ps1` **from an elevated Administrator session**. Repair 112
     also closed the alternative reading: the session is in neither the Administrators role nor
     `BUILTIN\Hyper-V Administrators` (SID S-1-5-32-578), and `Get-VM` is denied, so no
     unelevated start path exists.
   Then re-run `lab/lab-status.ps1` to `status: PASS`, re-run the Workstream E replay, and bind
   the result to candidate `8BA80453`.
3. **Candidate re-freeze.** If item 2's recovery or any item-1 owner hardening changes product,
   build-input or bundle bytes, a fresh build is required; because the build is not
   bit-reproducible, the SHA-256 must be re-declared from the bytes actually shipped and the
   packaged evidence re-bound to it. If neither occurs, the present `8BA80453` declaration
   stands and the 20/20 evidence already binds to it.
4. **Declared orchestration is not candidate-reproducible (DEF-W57-007, P2).** 6 POSTRUN
   checks, 4 integration validators, `phase_job.py` and the `.agents/protocol/` tree are
   excluded by a machine-local `.git/info/exclude` rule for `/.opencode/`; and
   `protocols.program_orchestration` names `WAVE_PROGRAM_ORCHESTRATION.md` while the real file
   is `AC_WAVE_PROGRAM_ORCHESTRATION.md`. Controller-owned.
5. **Stale parity assertion.** `tests/contracts/test_wave_closeout_hardening.py` asserts
   `AGENT_PARITY=PASS` while `validate-agent-parity.py` correctly prints
   `{"status": "PASS", "errors": []}` and exits 0. The gate is green; the assertion is stale.
6. **Only after items 1-3 are green:** write
   `artifacts/wave_W57/WAVE_W57_EVIDENCE_MANIFEST.json` with `ACCEPTANCE_GREEN`, re-issue this
   declaration with `Frozen for W58: YES`, then dispatch the fresh independent audit. No
   self-audit is written from a run phase (`audit_policy: fresh-independent`).

No test weakened, no skip or xfail added, no evidence fabricated, no PASS claimed, and the
frozen candidate was never patched.

## §C — Revision 6 (repair phase 144): identity block re-bound to W57's own candidate identity

**What changed.** Only the identity/provenance block at the head of this file. No candidate byte,
no product, test, spec, build or lab file, no gate, and no verdict changed.

| Field | Before | After |
|---|---|---|
| `Content identity (controller handoff)` | `8f522decd2c8…` (**W30's** `audit_receipt.tested_content_identity`) | `692e534df1c4…` (**W57's own** `implementation_identity`, equals the controller's handed `content_identity`) |
| `Phase instance` | `…:110:W57:run` | `…:144:W57:repair` |
| `Frozen for W58` | `NO` | `NO` — **unchanged, and deliberately unchanged** |

**Why `Frozen for W58` stays `NO`.** The audit that routed this repair described the `NO` as part
of one finding. It is not a defect: `NO` is the truthful verdict at this candidate. `DEF-W57-006`
is re-measured live in this dispatch — `192.168.250.11:22` open, `192.168.250.12:22` open,
`192.168.250.13:22` **unreachable** at a 3 s bound, and recovery is refused at the authorization
plane (`IsAdministrator=False`, user `MSKOMEK\mskomek`, `Get-VM` -> "You do not have the required
permission to complete this task."). Flipping this line to `YES` to satisfy a finding would be a
fabricated acceptance, so the line is left exactly as measured and the finding's identity half is
what was repaired.

**Why this rebind is convergent and not another oscillation.** The W57 evidence identity is
`wave_state_engine.repository_content_identity()` evaluated with the profile's
`allowed_closeout_only_paths` as ignore prefixes, and that filter is applied inside the hashing
loop (`.opencode/scripts/wave_state_engine.py:1030`). Both W57 closeout-only surfaces — this file
(`artifacts/`) and the canonical report (`docs/wave-reports/`) — are in that ignore list, so
neither is an input to the digest it quotes. Measured before the edit: identity
`692e534df1c4…`, exactly equal to the controller's handed `content_identity`. Measured after the
edit: unchanged. Rebinding therefore cannot invalidate itself. Earlier repeats of this rebind went
stale because **other** closure members moved (the tracked `lab/config.json`, `lab/lab-common.ps1`,
`lab/lab-test.ps1` repair delta and six untracked root-level stray scripts), not because of the
rebind.

**T08 stray-file record (the plan's "or record it truthfully" branch).** The untracked root-level
`test_wave_controller_regressions.py` (11321 B, created 2026-09-28T04:03:52) is **still present**,
is a byte-duplicate of the canonical `tests/test_wave_controller_regressions.py`, and was **not
deleted and not worked around**. It is untracked user/workspace state, so removing it is not a
Wave worker's call; it is recorded here and routed to the controller, which owns commit approval
and cleanup. It is untracked, so it cannot enter a `candidate_sha`; it can only affect a dirty-tree
freeze assembly, which is not reachable while `Frozen for W58: NO`.
