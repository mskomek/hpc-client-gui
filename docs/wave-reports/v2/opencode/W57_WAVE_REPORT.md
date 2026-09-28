# W57 Wave Report - Packaged regression, support finalization and freeze (repair phase 162)

Wave: `W57`
Canonical report path: `docs/wave-reports/v2/opencode/W57_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA (W56 frozen candidate base): `36d6151fd9634cf50e14a639ec0407bef1d296f4`
Main SHA: `bdf6c6c7e2817422b6f9005873247d3636c5eac4` (candidate commit; unchanged by run 161 — the frozen candidate was neither rebuilt nor patched)
Branch/HEAD at this run: `develop` / `c9c1754ef61f50aa79b167857397ec91bc711542` (run-161 evidence commit; the tested candidate under it is still `bdf6c6c7`, artifact SHA-256 `8BA80453A76A664959BAEDF7716C476A5334B6AFF860A4BC79B9E220D48B4C57`, re-verified read-only in this dispatch)
Product delta vs Main SHA: none. Run 161 modified no file under `src/`, `scripts/`, `tests/` or `build/`; its only commit adds one W57 evidence artifact.
Content identity (controller handoff): `45c46c0a09c3f9b85b4679c40f3779a694b5a8f0c0c63b64cc1380823eeac3fc`
  *(The identity handed by the controller for phase instance `…:161:W57:run` and recorded here
  verbatim. It is **not** the run-158 value `0c9c5812140d…`, so this dispatch is not a same-content
  repetition of the previous run. The earlier header carried `692e534d…`, which was the
  repair-144 binding and is stale for this dispatch; see §25.)*
Phase instance: `20260925-074235-63df86b0:161:W57:run`
Prior phase: `run` `REOPEN` (`0158-W57-run-normalized.json`). That dispatch returned `REOPEN` on a two-cause diagnosis (25 s child budget **and** foreground-dependent synthetic input) routed to the `W04` packaging-harness surface. This dispatch tested that diagnosis instead of restating it and **falsified its second cause**; §25 records the measurement and the corrected owner route.
Last updated: 2026-09-28 (repair phase 162, opencode executor)
Repair 162 supersession note: the header block below still carries run phase 161's identity fields (content identity `45c46c0a.`, phase instance `.:161:W57:run`, HEAD `c9c1754e.`) because the controller hands the content identity per dispatch and did not hand a new one for this repair dispatch. This dispatch ran at phase instance `20260925-074235-63df86b0:162:W57:repair` on branch `develop` at HEAD `313a3e0d39665f478b6836c175f3359e1d4ffcfc`, with the tested candidate still `bdf6c6c7` / artifact SHA-256 `8BA80453...` and harness SHA-256 `47763C6A...` both unchanged. **Section 26 supersedes the run-155 and run-161 owner route**; the run-161 diagnosis in the block above is retained as history, not as the current conclusion.
Session status: **REOPEN** *(re-set at run phase 161; the reason is now a proven mechanism, not an inference about ambient conditions).* The external and identity prerequisites remain resolved and were **re-measured in this dispatch**: `lab/lab-status.ps1` exits 0 with `status: PASS`, 3/3 nodes `transport_ok`/`services_ok`, `compute02` restored (ssh/munge/slurmd active), Slurm `compute01|idle compute02|idle`, `image_pin_ok=true`, `profile_valid=true`; and the maintained `lab/lab-test.ps1` exits 0 in 27 s with **23/23** required gates true and `failed: []`. `W57-AUD-005` stays closed by candidate commit `bdf6c6c7`, whose artifact identity was re-verified without rebuild.

The single remaining reason is a measured, repository-owned defect that is **not** W57-owned, and its mechanism is now established rather than hypothesised. The maintained packaged gate `scripts/wx_packaged_smoke.py` was run **unmodified**, three times, against the unchanged candidate: 3/3 exit 1, `FAIL` **1/20**, `details.timeout='artifact did not exit within 25s'`, 26.512 s / 26.859 s / 27.059 s. In all three runs the artifact's own packaged runtime sidecar — the very file the gate scores — reports **`result: PASS`, `phase: 4`**, with 17/19 of its own checks PASS and full input delivery (`ssh_input_chars` 18, DOM `keydown` 18, `sendinput_events` 36, click `[770,544]`). The two artifact-reported failures, `pty_resize` and `clean_shutdown`, are recomputed and overridden by the gate itself (`wx_packaged_smoke.py:206`, `:210-220`, `:236`), so every check the artifact can prove passed. That complete passing payload was on disk **19.444 s before** the gate emitted its `FAIL 1/20` verdict, and the gate never opened it: `wx_packaged_smoke.py:190-192` short-circuits on `timed_out`. Root cause: the artifact completes every smoke phase and writes complete `PASS` evidence roughly 5–7 s into the run, then does not terminate inside the gate's hardcoded `timeout=25`, and the gate converts that into 1/20 by discarding the evidence. Routed to the true owners — the gate budget and discard path to `HPC-W04-FRESH-009` (W15) / `HPC-W04-HARNESS-025` (W16), both CLOSED, so a controller-owned closed-owner repair transaction; the artifact's post-phase-4 shutdown to the product/frozen-candidate surface, which would invalidate W56 and require an owner rebuild. This is a repository-owned red and **not** `HUMAN_DEFERRED`: no credential, MFA, authority, hardware, service or manual-acceptance step is missing. See §25 and `artifacts/wave_W57/W57_RUN161_PKGREG_EVIDENCE_DISCARD_ROOT_CAUSE.json`.

Run 161 also **falsifies the second cause** recorded at run 158. The run-158 report treated `foreground_request_accepted=false` and `foreground_matches_frame=false` as proof that a busy desktop zeroed the input. Those exact two values are present in all three run-161 red runs **and** in the known-green 20/20 evidence `artifacts/wave_W57/W57_PACKAGED_SMOKE_8BA80453_PASS.json`, so they are not discriminators; they are a diagnostic snapshot taken at `wx_shell.py:2245-2250`, *before* the `AttachThreadInput` activation block at `wx_shell.py:2286-2295`. No run in this dispatch produced `keyboard_input:foreground_lost_after_terminal_click`; all three reached phase 4. The run-158 owner route for the input half was also **misattributed**: `scripts/wx_packaged_smoke.py` contains no input-synthesis code at all (only `--wx-smoke` argv at lines 154, 156, 337, 339), while every `SetForegroundWindow`/`BringWindowToTop`/`SetCursorPos`/`SendInput`/`ClientToScreen` call lives in `src/hpc_gui/wx_shell.py:2231, 2288, 2290, 2353, 2357, 2361, 2377` — the shipped product smoke driver. Finally, ambient contention does not discriminate either: 6/6 ambient snapshots show **0** topmost windows covering the click point `[770,544]` and `WerFault=0`, and the three runs were byte-identical under a constant desktop.

Four W57-owned seams are re-verified green in this dispatch: `tests/test_local_real_lab_bounded_commands.py`, `tests/test_local_real_lab_static.py`, `tests/test_wave_controller_regressions.py` and `tests/test_w57_freeze_consistency.py` → **30 passed in 12.80 s**, exit 0. `scripts/validate_wave_closeout.py --wave W57` reports `can_close: false` for its one truthful reason — the deliberately withheld `ACCEPTANCE_GREEN` manifest. `.opencode/scripts/validate-ac-project.py`, red at run 158, now exits 0 `PASS`.

`DEF-W57-006` (`compute02` at 192.168.250.13) was down for the whole history of this Wave and
was the reason this Wave was repeatedly deferred. It is **RESOLVED**, measured in run phase
155: all three lab nodes report `transport_ok`/`services_ok`, Slurm reports both compute nodes
`idle`, and the maintained `lab/lab-test.ps1` returns 23/23 required gates true, exit 0. There
is no longer any external authority, hardware or service standing between this Wave and its
evidence.

`DEF-W57-007` is **not** deferred and is **not** a 33-file drift. Measured in this dispatch it
is `canonical-managed-surface-changed` plus 6 `managed-file-content-mismatch` entries against
the external canonical root, and the profile's own `postrun_checks` list still cannot be
launched per-entry because `run_postrun_checks()` gives non-`.py` entries no interpreter and has
no `try/except`. Both are repository-owned, controller-owned, non-terminal, and route to the
controller / Agent Core owner. See section 22 and section 23.7.

Wave decision: **NO-GO for freeze.** No `ACCEPTANCE_GREEN` manifest. W58 must not consume the successor declaration.

Execution mode: unattended, non-interactive. No user question asked. No secret requested,
invented or persisted. No destructive Git. No test weakened, skipped or xfailed. No manifest
fabricated. No self-audit written (`audit_policy: fresh-independent`).

## 1. What this run did that the prior run could not

The prior `repair` phase (106) proved that DEF-W57-008 is a single-commit regression with a
proven 2-line owner fix, executed the unowned Workstream H triage, and routed the fix to W30 —
which is CLOSED, so it needed a controller-owned `closed_owner_repair`. That transaction has
now landed in the working tree and been independently audited **PASS** (audit receipt in the
controller handoff: `tested_wave W30`, `audit_candidate_sha f6ab257f`, same content identity).

That repair is **product** source. W57's frozen-candidate invariant says any product
correction invalidates the candidate and requires a rebuild plus a rerun of the invalidated
evidence. So this run executed the rebuild-and-rerun that the prior report listed as pending,
which is why the packaged evidence is now bound to a different artifact:

1. **Verified the W30 repair actually closed the P1** at the current content identity
   (`tests/test_wx_editor_cross_view_actions.py` → 14 passed exit 0;
   `tests/test_w30_submit_cancel.py` → 16 passed exit 0).
2. **Rebuilt the candidate** from the post-repair product with the maintained build path
   (`docs/decisions/V2_BUILD_ENVIRONMENT.md`): `.venv\Scripts\python.exe -m PyInstaller -y
   --clean build/windows/hpc-client-gui.spec`. New artifact
   `8BA80453A76A664959BAEDF7716C476A5334B6AFF860A4BC79B9E220D48B4C57`, 7672468 B, 172 files,
   0 Qt tokens. The frozen candidate was **rebuilt, never patched**.
3. **Re-ran the maintained full suite** at the new candidate: `scripts/ci.py full`, exit 1,
   **15 failed / 3000 passed / 36 skipped / 32 deselected / 2 warnings / 29 subtests in
   736.27s**, coverage 68.36% (≥65% gate met). The prior run measured 28 failed / 2986 passed.
4. **Re-ran the unmodified maintained W04 packaged harness** against the new artifact — six
   times, on three distinct builds, including one that **excludes** the W30 repair, to separate
   product from environment.
5. **Re-ran the static gates** `check_i18n.py`, `ci.py docs`, `ci.py packaging`, `ci.py audit`
   (all exit 0) and the artifact-level `version` / `doctor environment` readback from outside
   the repository.
6. **Re-measured the EXTERNAL lab** with the maintained `lab/lab-status.ps1`.
7. **Re-verified the three non-repository failure artifacts in isolation** rather than carrying
   the prior run's claim forward.
8. **Re-issued the single freeze declaration**, rebound to the new candidate, with
   `Frozen for W58: NO` and the new measured reason.

### 1a. Repair phase 112 - the required real-cluster regression was executed for the first time

9. **Executed the required real-cluster regression** (`FREEZE-030`/`FREEZE-040`, Workstream E)
   instead of re-running the lab health check. Up to this phase no W57 phase had ever run it:
   `lab/lab-status.ps1` is a *health check*, not the regression the owned rows require.
   `FREEZE-030`/`FREEZE-040` name no node count, so the two-node expectation is the lab's own
   baseline list in the lab protocol, not the requirement wording.
10. **Ran the maintained lab regression** `lab/lab-test.ps1` (23 required behavioral gates). It
    **did not return and wrote no evidence artifact**: it blocks indefinitely at the two-node
    `srun` gate. Measured on the controller: jobs `76`/`77` `PENDING` with
    `ReqNodeNotAvail, UnavailableNodes:compute02`, plus a leaked `srun --nodes=2` step that had
    been alive **19704 s (5.47 h)** from a previous phase. Cause: `Invoke-LabSshCapture` sets
    only `ConnectTimeout=5` and **no command timeout**, and an interactive `srun` step has no
    Slurm time limit, so a DOWN node produces an indefinite pend instead of a failure.
    -> **DEF-W57-017**. Cleanup performed: the two leaked pending jobs were cancelled and the
    local harness processes stopped; `squeue` verified empty. No lab config, VM, disk or
    repository file was altered.
11. **Ran the Workstream E scenario replay** through the maintained client CLI
    (`.venv/Scripts/python.exe -m hpc_gui.cli`; 13 deterministic steps, no human interaction,
    only the lab key *path* ever passed on a command line). All 12 remote steps were refused in
    0.6 s each with `Remote CLI access is disabled...`. The gate is the **global**, default-off
    setting `cli_external_access_enabled` (`src/hpc_gui/cli/main.py:960`,
    `src/hpc_gui/config/storage.py:434-443`); the CLI exposes no flag and the repo defines no
    environment override, so there is no unattended way to enable it - even though
    `docs/testing/LOCAL_HPC_LAB.md` documents exactly that unattended CLI procedure.
    -> **DEF-W57-018**. The setting was deliberately **left untouched**: enabling a default-off
    security control to turn a gate green is not a repair, and it would persist past this run.
12. **Re-measured the external target and the authority question**: `lab/lab-status.ps1` exit 3;
    `login-control01` 6/6 services and `compute01` 3/3 services healthy; `compute02` still
    unreachable. This also *disproves* the one alternative reading of repair 111: the session is
    not an Administrator **and not a member of `BUILTIN\Hyper-V Administrators`**
    (SID S-1-5-32-578), and `Get-VM` is denied, so no unelevated VM-start path exists either.

### 1b. Repair phase 113 — DEF-W57-018 withdrawn, and the real-cluster regression run to PASS

Repair hypothesis `W57-DEF018-ISOLATED-ROOT-UNATTENDED-OPTIN`.

**FINDING.** Step 11 above is **withdrawn as a false negative**. Repair phase 112 concluded the
CLI remote gate has "no unattended opt-in" because it searched for an override of the *setting
key* `cli_external_access_enabled`. The repository overrides the *store that holds the key*, not
the key: `ISOLATED_CONFIG_ROOT_ENV = "HPC_GUI_CONFIG_ROOT"` (`src/hpc_gui/core/paths.py:17`) makes
`app_data_dir()` — and therefore `load_settings()` (`src/hpc_gui/config/storage.py:98-105`,
`_config_path()` = `app_data_dir()/config.json`) — resolve into a disposable per-run root. This is
a maintained, already-shipped, already-tested isolation contract (`PKG-GJ-01`), exercised by
`scripts/wx_packaged_smoke.py` and proven in the W15/W17/W39/W45/W50/W54 wave evidence. The
unattended opt-in therefore **already exists** and is scoped to a throwaway directory.

**OBSERVED_FAILURE (before the change).** With no isolated root, all remote steps are refused in
~0.6 s with `Remote CLI access is disabled...` (`artifacts/wave_W57/W57_WORKSTREAM_E_REAL_CLUSTER_REPLAY.json`,
phase 112).

**HYPOTHESIS.** Pointing `HPC_GUI_CONFIG_ROOT` at a disposable `.tmp` root whose `config.json`
carries `settings.cli_external_access_enabled = true` enables the unattended path **without**
removing the gate, **without** changing the default, and **without** touching the developer
profile.

**CHANGE.** No product, test, spec, build-input or lab file was changed; candidate `8BA80453` is
untouched. The change is to the W57-owned replay probe under `.tmp/` plus new evidence under
`artifacts/wave_W57/`. The gate line `src/hpc_gui/cli/main.py:960` and the default in
`config/storage.py:434-443` are **unchanged**; the enabled value exists only inside
`.tmp/w57-repair-113/isolated-root/config.json`. Reading `~/.truba_slurm_gui/config.json` back
after the run shows **no** `cli_external_access_enabled` key at all — zero contamination.

With the gate cleared, five defects of the *probe script itself* (previously masked by the gate)
became visible and were fixed. All five are defects of the W57 probe, not of the product or lab:

| # | Symptom | Root cause in the probe | Fix |
|---|---------|-------------------------|-----|
| H1 | `printf: usage: printf [-v var] format [arguments]`, exit 2 (WE-02, WE-04d, WE-06) | PowerShell native-argument quoting re-split the remote `bash -c` format string | ship the exact remote bash bytes **base64-encoded**, the technique `lab/lab-common.ps1 :: Invoke-LabSshCapture` already uses |
| H2 | `Remote edit failed: [WinError 193] %1 is not a valid Win32 application` (WE-04c) | `edit --editor <file.py>` cannot exec a `.py` on Windows | pass an executable command line, which `shlex.split(posix=False)` expands |
| H3 | `sbatch: error: Batch script contains DOS line breaks (\r\n)` (WE-05c) | `Set-Content` emitted CRLF | write explicit LF bytes, upload `--mode binary` |
| H4 | `rm: cannot remove '...': Is a directory` (WE-07) | `files rm` without `--recursive` on a directory | add `--recursive` |
| H5 | H1–H4 kept failing after being "fixed" | `Start-Process -ArgumentList` joins the array with plain spaces and does **not** quote elements, so every argument containing a space was re-split by the child | emit one correctly quoted command line (MS `CommandLineToArgvW` rules) |

H5 is the reason a plausible-looking fix can appear to do nothing; it is recorded because it is the
defect that masked the other four.

Every scenario additionally runs through `Invoke-Bounded`, a hard wall clock
(`Wait-Process -Timeout`): a hung child is killed, reported as exit 124 / `timed_out`, and never
awaited. This satisfies the Wave's own unattended contract (`W57.md:97`) and contains the
DEF-W57-017 failure mode at the W57 harness level. **No scenario timed out.**

**RESULT — 16/16 PASS, exit 0**, `artifacts/wave_W57/W57_WORKSTREAM_E_REAL_CLUSTER_REPLAY_R113.json`.
All five Workstream E scenario classes from the mandatory source section executed against the live
`LOCAL_REAL_HYPERV` Slurm cluster through the maintained client entrypoint
(`.venv/Scripts/python.exe -m hpc_gui.cli`), unattended, with only the lab key *path* on a command
line:

- **connection / reconnect** — `doctor connection` PASS (dns, port, auth, sftp, slurm, checksum);
  `WE-02 host=login-control01 user=hpctest`, `Linux 6.8.0-142-generic`.
- **SFTP round trip** — `doctor smoke` PASS, artifact `W57_WORKSTREAM_E_SFTP_SMOKE_R113.json`.
- **remote editor save** — upload, `edit --verify`, then a real remote readback showing the
  marker line and `marker_lines=1`.
- **job list / submit / cancel** — batch job **80** submitted through the CLI, **scheduled by
  Slurm onto `compute01`**, `JobState=RUNNING`, `NodeList=compute01`, `BatchHost=compute01`,
  cancelled via `jobs cancel` (`OK`), and read back in `sacct` as `80|w57we|CANCELLED by 1000|...|compute01`.
- **terminal class** — real remote shell transport and process probe.
- **cleanup** — disposable remote probe directory removed; post-cleanup listing confirms it is gone.

External cleanup re-verified after the run: `squeue` count **0**, no leftover probe directories
(the one left by the H4-affected first run was found and removed), `sacct` shows only CANCELLED
probe jobs.

Focused regression, same set as repair 112: `pytest tests/test_w57_freeze_consistency.py
tests/test_local_real_lab_static.py tests/test_w04_support_freeze.py
tests/test_w14_provenance_manifest.py tests/test_version_consistency.py` -> **55 passed, exit 0**
(unchanged). `tests/test_w15_fresh_user_startup.py::test_profile_created_through_visible_add_dialog`
fails with `Dialog.ShowModal(): first argument of unbound method must have type 'Dialog'`; this is
**pre-existing and already recorded** in this Wave's own ledger
(`artifacts/wave_W57/W57_CI_FULL_FAILURES.txt` line 5 and `_RUN110` line 10), is a W15-owned GUI
binding fault, and is untouched by this phase.

**What phase 113 does NOT claim.** `lab/lab-test.ps1` was still not re-run to completion: its
two-node `srun` gate needs `compute02`, which is still `down*` in `sinfo -N`. The lab is therefore
below the verified baseline in `.opencode/protocol/LOCAL_REAL_HPC_LAB.md` ("controller and both
compute transports/services: PASS", "two-node `srun`: PASS"). Whether the owned rows
`FREEZE-030`/`FREEZE-040` are satisfied by the executed Workstream E scenario list (which names no
node count) rather than by the lab's own two-node baseline list is an **acceptance judgement for
the fresh independent audit**, not a claim this repair makes. `FREEZE-044` (manifest) stays
unwritten; it requires `ACCEPTANCE_GREEN` and this phase does not self-audit
(`audit_policy: fresh-independent`).

## 2. Candidate identity — rebuilt and verified

- Product delta vs HEAD is exactly one file, `src/hpc_gui/services/job_submit_cancel.py`, and
  it is the controller-dispatched W30 repair, not a W57 edit.
  **Corrected at repair 119 — the scoping evidence originally cited here was wrong.** The command
  `git status --porcelain -- src/ build/ requirements.txt requirements-release.lock pyproject.toml scripts/ lab/`
  does **not** return "only that file". Re-run at repair 119 it returns **four** entries: the W30
  file above plus W57's own `lab/config.json`, `lab/lab-common.ps1` and `lab/lab-test.ps1` — the
  repair-115/116 `DEF-W57-017` bounded-harness hardening disclosed at §14. `tests/` likewise shows
  `tests/test_w30_submit_cancel.py` (W30) **and** W57's own `tests/test_local_real_lab_static.py`
  plus the untracked `tests/test_local_real_lab_bounded_commands.py`.
  The **product-tree conclusion is unaffected and still true**: the product tree is
  `src/ build/ requirements*.txt pyproject.toml`, which contains none of those `lab/`/`tests/`
  paths, so the product delta really is one file and the product hash below is untouched. What
  was wrong was the cited command and the "shows only that file" reading of it, not the delta.
- Product tracked-tree SHA-256 (`src/ build/ requirements*.txt pyproject.toml`, per-file
  hashes, sorted): `23b314013d7bc5e28562f8fc771ceff27e48e9da002b8c1ee315dba121b2bc78`.
- Artifact `dist/hpc-client-gui/hpc-client-gui.exe`: **7672468 B**,
  **SHA-256 `8BA80453A76A664959BAEDF7716C476A5334B6AFF860A4BC79B9E220D48B4C57`**.
- Bundle: **172 files**, **0** tokens matching `PySide*` / `shiboken*` / `Qt6*.dll`.
- `version` from outside the repo → `version: 1.5.9`, `python: 3.14.0`, exit 0.
  `doctor environment` → `status: PASS`, `frozen: True`, exit 0.
- **The build is not bit-reproducible.** Three builds this run: post-repair `9DEDBEA3`
  (7672468 B), pre-repair `F904FAAF` (7672516 B), post-repair `8BA80453` (7672468 B).
  Identical product bytes do **not** reproduce an identical SHA-256. The pre-repair size
  7672516 equals the superseded `CAA5904A` size exactly, and the post-repair size is −48
  bytes, consistent with the removed two-line gate. The declared SHA-256 therefore binds to
  **these exact bytes**, not to the source; it must not be read as a reproducible identity.
- Working tree: the pre-existing uncommitted controller work
  (`.opencode/protocol/WAVE_PROJECT_PROFILE.json`, `.opencode/scripts/run-wave-program.py`,
  `.opencode/scripts/wave_state_engine.py`) was **preserved untouched**.

## 3. EV-W57 — evidence, all fresh at run phase 110

| ID | Command | Result |
|---|---|---|
| EV-18 **P1 closure verification** | `pytest -q tests/test_wx_editor_cross_view_actions.py` | **14 passed, exit 0** (was 12 failed / 3 passed) |
| EV-19 **W30 owner suite** | `pytest -q tests/test_w30_submit_cancel.py` | **16 passed, exit 0** (15 before + the new contract test) |
| EV-20 **maintained full suite** | `.venv/Scripts/python.exe scripts/ci.py full` | **exit 1**, 736.27 s. `15 failed, 3000 passed, 36 skipped, 32 deselected, 2 warnings, 29 subtests passed`; coverage 68.36% (≥65% met). Log `.tmp/w57-run-110/ci-full.log`; node ids `artifacts/wave_W57/W57_CI_FULL_FAILURES_RUN110.txt` |
| EV-21 **packaged regression, new candidate** | `python scripts/wx_packaged_smoke.py --artifact dist/hpc-client-gui/hpc-client-gui.exe --platform windows --output …` (unmodified, default 25 s) | **exit 1**, `result: FAIL`, **14/20**, `isolated_from_src: true`, runtime `keyboard_input:foreground_lost_after_terminal_click`. 3 runs |
| EV-22 **product-independence control** | same harness, candidate rebuilt with the W30 repair **reverted** (`F904FAAF`) | **exit 1**, `result: FAIL`, **14/20**, identical 6 failing checks, identical runtime diagnostic. 2 runs |
| EV-23 **console-window control** | same harness on `8BA80453` launched via `Start-Process -WindowStyle Minimized` | **exit 1**, **14/20**, identical. Removes the harness console from the click path — does not help |
| EV-24 **artifact identity** | `Get-FileHash dist/hpc-client-gui/hpc-client-gui.exe`; bundle count; Qt-token scan; `--version`; `doctor environment` from outside the repo | `8BA80453…`, 7672468 B, 172 files, 0 Qt, `1.5.9` exit 0, `status: PASS / frozen: True` exit 0 |
| EV-25 i18n release gate | `.venv/Scripts/python.exe scripts/check_i18n.py` | `i18n key check: OK` / `i18n reference check: OK` / `i18n hardcoded UI text check: OK`, exit 0 |
| EV-26 docs gate | `.venv/Scripts/python.exe scripts/ci.py docs` | exit 0 — `release surface check: OK`, `wiki check: OK` |
| EV-27 packaging gate | `.venv/Scripts/python.exe scripts/ci.py packaging` | exit 0 — `1 passed, 3 deselected` |
| EV-28 dependency audit | `.venv/Scripts/python.exe scripts/ci.py audit` | exit 0 — `No known vulnerabilities found` |
| EV-29 **failure-artifact re-verification** | `pytest -q` on the 4 non-defect nodes in isolation | `2 failed, 2 passed`; `test_w15_fresh_user_startup::test_profile_created_through_visible_add_dialog` and `test_wx_w55_shell_soak::test_w55_shell_tab_and_help_accelerators` **pass in isolation**; the other two are proven non-repository (see §4) |
| EV-30 **parity gate is green** | `validate-agent-parity.py` invoked by the failing test | exit 0, `{"status": "PASS", "errors": []}` — the committed test asserts the legacy `AGENT_PARITY=PASS` token, so the **assertion** is stale, not the gate |
| EV-31 **EXTERNAL lab** | `lab/lab-status.ps1` | exit 3, `status: FAIL`. `login-control01` transport + 6/6 services OK; `compute01` transport + 3/3 services OK; `compute02` SSH timeout, `down*` in `sinfo -N`. Identity `LOCAL_REAL_HYPERV`, image SHA-256 pin OK, Ubuntu 24.04.5 / slurm 23.11.4. → `artifacts/wave_W57/W57_LAB_STATUS_RUN110.json` |
| EV-32 **display environment** | `GetSystemMetrics` / `Screen.AllScreens` on the active console session | **Two displays**: `\\.\DISPLAY1` primary at X=0 1920×1080 and `\\.\DISPLAY4` secondary at X=1920 1920×1080; virtual desktop 3840×1080 |

### 3.1 The packaged gate: 6/6 deterministic red, and proven not to be the W30 repair

The maintained harness was executed **unmodified at its default 25 s budget** six times across
three distinct artifact builds. All six returned `result: FAIL`, `exit_code: 1`, **14/20**, with
the *same* six failing checks (`terminal_readback`, `pty_input_output`,
`remote_file_roundtrip`, `job_roundtrip`, `transfer_queue_render`, `clean_shutdown`) and the same
runtime string `keyboard_input:foreground_lost_after_terminal_click`.

The control that matters is EV-22: the W30 repair was reverted, the candidate was rebuilt with
the identical build path, and the gate failed **identically**. The packaged red is therefore
**not** caused by the W30 repair, not caused by anything W57 changed, and not a regression of
the candidate — it is the execution environment.

Mechanism (measured environment, hypothesised Win32 cause). The diagnostic is
`foreground_request_accepted: false`, `foreground_matches_frame: false`, `wx_focus_type: WebView`,
`wx_focus_within_terminal_panel: true`, xterm `TEXTAREA` focused, and `bridge_input_chars: 0`,
`ssh_input_chars: 0`, all DOM input event counters `0`. In `src/hpc_gui/wx_shell.py:2226-2375`
the smoke child raises its frame, **successfully** claims foreground (the `wx_shell.py:2296`
check passes), reads the xterm DOM focus, then positions the real cursor at the centre of the
WebView via `ClientToScreen` and injects a synthetic left click with `SendInput`. Immediately
afterwards `wx_shell.py:2373` re-reads `GetForegroundWindow()`, it is no longer the frame, and
the run aborts — so every input and round-trip stage cascades. The machine has a second
1920×1080 display attached (EV-32), which is the classic coordinate-virtualization setup for a
WebView host on a non-primary monitor. **The precise Win32 cause inside the click path is a
hypothesis, not a proven root cause, and is recorded as such.** The prior run's four
independent 20/20 green runs on `CAA5904A` are preserved unmodified and are *not* reused for
this candidate.

Full finding, with every run and the discriminating experiment:
`artifacts/wave_W57/W57_PACKAGED_GATE_MULTIMONITOR_FINDING.json` (**DEF-W57-016**).

## 4. WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | Impact | Owner | Status
DEF-W57-008 | P1 (was) | Editor/job submit path | EV-18/EV-19/EV-20: 12 node ids failed at f6ab257f with `no #SBATCH directives found`; now 14 passed / 16 passed exit 0 and suite failures 28 -> 15 | 2-line gate added in bulk record bb8ac6b3 (a maintained test was committed red by that same commit) | release gate red; no acceptance, no freeze | W30 | **CLOSED — VERIFIED** by the controller-dispatched W30 closed_owner_repair (audited PASS). CTRL-001/002 still enforced via validate_template_against_provider; a new maintained test pins the corrected contract; no test weakened
DEF-W57-016 | P2 | Packaged candidate terminal accept (PKGREG-001, FREEZE-009/-032/-041, TODO-012, TODO-RUNTIME-CUTOVER-003) | EV-21/EV-22/EV-23/EV-32: 6/6 runs, 3 distinct builds, 14/20, `foreground_lost_after_terminal_click`; reproduces with the repair reverted | synthetic WebView click in `wx_shell.py:2356-2375` does not return foreground; two-display desktop measured | packaged gate red; PKGREG-001 could not be accepted | UNRESOLVED - controller must assign the stable owner; **not** W57 and **not** W30 | **RESOLVED at repair 111 as environmental, not product** - four stale topmost `WerFault` crash dialogs covered the smoke frame and stole foreground at the synthetic click (click point 770,510 is 1 px inside dialog rect 769,394-1135,580). No repository file changed; candidate `8BA80453` unchanged; unmodified harness then returned 20/20 exit 0 on 3/3 runs. The residual hardening of `wx_shell.py` (assume no third-party topmost window overlaps the frame) stays outward-routed
DEF-W57-007 | P2 | Candidate completeness of declared orchestration (FREEZE-029, FREEZE-044) | EV-20 + EV-30: `/.opencode/` is excluded by a machine-local `.git/info/exclude` rule, so 6 POSTRUN checks, 4 integration validators and `phase_job.py` are untracked; `test_wave_controller_regressions.py` x2 red; parity gate green but its committed assertion is stale | the orchestration tree is not part of the candidate | PROGRAM_COMPLETE final validation is not candidate-verifiable | controller (profile + orchestration runtime) | OPEN — routed. Also `protocols.program_orchestration` names `WAVE_PROGRAM_ORCHESTRATION.md`; the real file is `AC_WAVE_PROGRAM_ORCHESTRATION.md`
DEF-W57-009 | P3 | Test currency — editor host lookup | `test_wx_term002.py` x2; `wx_editor_view.py:978` + `wx_shell.py:1479` register the editor as an **embedded** panel, the test still searches `wx.GetTopLevelWindows()` | stale top-level-window assumption | assertion only; editor demonstrably works (the 12 DEF-W57-008 nodes exercise it and pass) | UNRESOLVED — controller must assign the stable owner | OPEN, DEFER as P3
DEF-W57-010 | P2 | Local file-manager start path | `test_file_manager_profile.py` x2 | local panel opens in the home directory rather than the cwd when no local folder is configured | default browse location differs from the historical contract; no data-integrity impact | W44 / W52 profile-management surface | OPEN, DEFER as P2 (workaround: configure an explicit local folder)
DEF-W57-011 | P2 | Editor save-path ownership governance | `test_wx_dispatch_error_gov.py` x1 | assertion is stale against the refactored write path | a governance invariant has no current proof; no wrong behaviour observed | UNRESOLVED — editor adapter owner | OPEN, DEFER as P2
DEF-W57-012 | P2 | Cluster profile storage id | `test_wave6_plugin_provider_unicode.py` x1 | `cluster profile 'storage[0]' needs a non-empty id` | a previously accepted profile can be refused; workaround: add a non-empty id | W06 (CLOSED) | OPEN, DEFER as P2
DEF-W57-013 | P2 | SSH/SFTP invalid UTF-8 path | `test_wave3_remote_sftp_ssh.py` x1 | no `UnicodeDecodeError` raised | a malformed path can be silently mangled → wrong-target risk, stated explicitly | W03 (CLOSED) | OPEN, DEFER as P2
DEF-W57-014 | P3 | Packaging hidden-import assertion | `test_w44_arch_qt_wx_package.py` x1 | the W56 ships-no-Qt decision removed the `PySide6.QtCore` import this test requires | test currency only; bundle verifiably Qt-free (172 files, 0 tokens) | W44 | OPEN, DEFER as P3. **HARD CONSTRAINT:** the owner must retire or restate the assertion; re-adding Qt would violate the no-Qt freeze. The controller must not dispatch a naive "restore Qt" repair
DEF-W57-015 | P3 | `errors="ignore"` regression search | `test_wave10_release_gate.py` x1 | one occurrence in `local_files.py`, from bulk record `d0d544c1` | marker-file probe only, no runtime impact | UNRESOLVED — controller must derive the owner from `d0d544c1` | OPEN, DEFER as P3
DEF-W57-004 | — | Packaged candidate shutdown | **REFUTED** by the prior run's EV-14/EV-15 (4 × 20/20 at `CAA5904A`) | earlier reds were a boot failure misread through the in-app self-report | — | — | **CLOSED for `CAA5904A`. REOPENED for the new candidate as DEF-W57-016**: `clean_shutdown` is red again because the run aborts at the click, so the prior proof does not carry over
DEF-W57-005 | — | Packaged PTY resize | REFUTED at `CAA5904A` (proven at the wire level) | — | — | — | **CLOSED for `CAA5904A`; re-evaluated as part of DEF-W57-016.** `pty_resize` is the one input-adjacent check that still passes on the new candidate
DEF-W57-017 | P2 | Maintained real-cluster regression harness `lab/lab-test.ps1` (FREEZE-030, FREEZE-040) | repair 112: the harness did not return and wrote no evidence; controller `squeue` showed jobs `76`/`77` `PENDING` `ReqNodeNotAvail, UnavailableNodes:compute02`; a leaked `srun --nodes=2` step was alive 19704 s | `Invoke-LabSshCapture` passes only `-o ConnectTimeout=5` and **no command timeout**, and an interactive `srun` step has no Slurm time limit, so a DOWN compute node pends forever instead of failing | the required regression can neither pass nor fail unattended, so no truthful FREEZE-040 result can ever be obtained by re-running it | lab provisioning owner (`lab/lab-test.ps1`, `lab/lab-common.ps1`) - NOT W57 product surface | **CLOSED AND VERIFIED at repair 116** (see §14). The bounded next action WAS taken: `Invoke-LabSshCapture` now has a hard wall-clock bound, a process-tree kill, a remote `timeout -k 5` and named 300 s allocation budgets. The maintained gate was executed end to end and returns 23 required / 7 failed, exit 3, in 671.1 s instead of hanging, and it orphans no allocation. Leaked pending jobs cancelled and `squeue` verified empty
DEF-W57-018 | P2 | Maintained client CLI remote-session gate (FREEZE-030, FREEZE-040) | repair 112: 12 of 13 Workstream E steps refused in 0.6 s with `Remote CLI access is disabled...` -> `artifacts/wave_W57/W57_WORKSTREAM_E_REAL_CLUSTER_REPLAY.json` | the gate reads the **global** default-off setting `cli_external_access_enabled` (`cli/main.py:960`, `config/storage.py:434-443`); no CLI flag and no environment override exist, and the lab profile emitted by `lab-up.ps1` carries `cli_allowed: false` | the unattended CLI regression procedure that `docs/testing/LOCAL_HPC_LAB.md` documents and marks "Verified on first build" cannot be executed at all; the remote gate is untestable without a prior manual Settings action | CLI/settings owner (`src/hpc_gui/cli`, `src/hpc_gui/config`) plus the docs owner - NOT W57 product surface | **CLOSED AND VERIFIED - WITHDRAWN.** This row's routing premise ("no CLI flag and no environment override exist") is **refuted**: the repository overrides the *store that holds the key*, not the key. `HPC_GUI_CONFIG_ROOT` (`src/hpc_gui/core/paths.py:17`, `ISOLATED_CONFIG_ROOT_ENV`) redirects `app_data_dir()` and therefore `load_settings()` into a disposable per-run root. Withdrawn at repair 113 (§1b) and **re-verified at repair 135 on the current content identity**, both sides: with no isolated root the default-off control still refuses (`Remote CLI access is disabled...`, exit 1); with a disposable `.tmp` isolated root carrying `settings.cli_external_access_enabled = true` the same remote command succeeds (exit 0, `host=login-control01`); the developer profile carries **no** `cli_external_access_enabled` key. The default was never changed, the gate was never removed, and no gate was weakened to make a check pass. **Consequence: `DEF-W57-018` is not a FREEZE-030/-040 blocker, and repair 134's blocker list was wrong to carry it**
DEF-W57-006 | P2 | Lab infrastructure | EV-31 and repair 112: `compute02` SSH timeout / `down*`, re-measured | Hyper-V guest not rejoining; infrastructure, not a product defect | two-node Slurm paths unavailable | lab provisioning (`lab/lab-up.ps1`) | OPEN, INFRA_NOTE; **re-confirmed at repair 116 as the single remaining** FREEZE-030/-040 blocker, and the only one that needs an elevated operator. Re-measured at layer 2 in this phase: `192.168.250.13` has 100% ICMP loss, ARP `Unreachable` with MAC `00-00-00-00-00-00`, and Slurm reports `DOWN+NOT_RESPONDING` with `BootTime=None`. No guest-side or repository-side repair path exists
DEF-W57-001 | P3 | `jobs.refresh*` i18n keys | closed by W28 repair `5a516c32`; EV-25 3/3 OK | keys never added when the refresh status landed | none remaining | W28 (CLOSED, repaired) | CLOSED
DEF-W57-002 | Release contract | docs/wiki matrix + install docs | EV-25/EV-26 green at `f6ab257f` | pre-cutover Qt/version wording | none remaining | W57 | VERIFIED
```

Non-repository measurement artifacts, re-verified this run rather than carried forward:

| Node id | Proof | Class |
|---|---|---|
| `tests/test_w15_fresh_user_startup.py::test_profile_created_through_visible_add_dialog` | EV-29: **passes in isolation** | shared-state pollution in the broad run, not a candidate defect (this is also the W57 TODO-010 node) |
| `tests/test_wx_w55_shell_soak.py::test_w55_shell_tab_and_help_accelerators` | EV-29: **passes in isolation** | shared-state pollution in the broad run |
| `tests/test_docs_references.py::test_agent_guidance_points_at_single_authority` | `.gitignore:75 /AGENTS.md`, `.gitignore:78 **/AGENTS.md`; `git ls-files AGENTS.md` → 0 files, yet `AGENTS.md` exists on disk | conditional on a gitignored, untracked, machine-local file; a property of this machine, not of the repository |

Second-defect search after the first legitimate defect (the packaged-gate red) was isolated:
negative paths (the harness's own kill/timeout path, invalid profile paths, the `clean_shutdown`
negative); lifecycle (the abort is precisely the terminal-accept lifecycle boundary, and
`clean_shutdown` fails as a *consequence*, not independently — that ordering is itself the proof
the failure has a single cause); stale state (no W28 refresh-state change; `check_i18n.py` green);
identity (artifact re-hashed, bundle re-counted, `doctor` `frozen: True`); concurrency (the
packaged child is single-process; the harness's loopback SSH is disposable and isolated);
boundary values (n/a, no new parser); capability absence (0 Qt tokens, `HPC_GUI_DISABLE_WEBENGINE`
honoured — not used as a substitute, since the acceptance path is the WebView one);
persistence (clean-profile first run green in isolation, EV-29); packaging (SHA + bundle +
`isolated_from_src: true` on all six gate runs); error visibility (the harness named every
failing stage and the abort reason verbatim — no silent fallback); secondary entry points
(cli `version`/`doctor` pass while the GUI `--wx-smoke` path fails, which is the localizable
defect); adjacent integration (the 15 suite failures are attributed to true owners in §4, none
W57-owned). No manufactured fix and no fix quota applied.

## 5. Workstream H triage — complete, and now P0=0 / P1=0

Full field set (ID, severity, surface, reproduction, expected, observed, owner Wave, status,
release decision — every field non-empty) for all 8 open root causes:
`artifacts/wave_W57/W57_DEFECT_TRIAGE_WORKSTREAM_H_POST_W30_REPAIR.json`. It supersedes
`W57_DEFECT_TRIAGE_WORKSTREAM_H.json` (repair 106) for severity and release decision; the
superseded file is retained unmodified.

| Rollup | Repair 106 | Run phase 110 |
|---|---|---|
| P0 | 0 | **0** |
| P1 | **1** | **0** (DEF-W57-008 closed and verified, EV-18/EV-19/EV-20) |
| P2 | 5 findings / 10 node ids | **7 findings / 12 node ids** (incl. DEF-W57-016) |
| P3 | 3 findings / 4 node ids | **4 findings / 4 node ids** |
| Suite failures | 28 | **15** |

The prior run's central claim is now confirmed rather than assumed: the 22 candidate-reproducible
node ids decomposed as 12 = the one open P1 + 10 = P2/P3, and the W30 repair closed **exactly the
12 predicted node ids**, with no collateral change to the other 15.

## 6. Requirement dispositions (owned IDs)

- **FREEZE-005** (support-matrix reconciliation): **PASS** — matrix realigned and green (EV-25, EV-26).
- **FREEZE-009** (packaged acceptance): **GREEN as of repair 111 — corrected at repair 120.** The run-110 red (EV-21/EV-22/EV-23, 14/20 on six runs across three builds) was `DEF-W57-016`, root-caused at repair 111 to four stale topmost `WerFault` crash dialogs covering the smoke frame's WebView centre click point (770,510 — 1 px inside the dialog rect 769,394-1135,580): desktop contamination, not a product defect and not the multi-display cause revision 3 assumed. With the contaminant removed and **no repository change of any kind**, the unmodified maintained harness returns **20/20, exit 0, `isolated_from_src: true`** against candidate `8BA80453` on 3/3 deterministic runs, and `W57_PACKAGED_SMOKE_8BA80453_PASS_SUMMARY.json` names `HPC-W10-FREEZE-009` in its own `closes_findings`. `W57_DEF_W57_016_SUPERSESSION.json` records the finding `RESOLVED` / `P4 RESOLVED-ENVIRONMENTAL`. The superseded red result is retained unmodified for audit. *(This was the one owned row the repair-116 §6 sweep left stale: it corrected `TODO-012`/`-013`/`-014`/`-016` and `TODO-RUNTIME-CUTOVER-003` but not this row, and §10/§12 then propagated the same error.)*
- **FREEZE-010** (defect triage): **PASS** — §4 + the Workstream H artifact.
- **FREEZE-011** (documentation consistency): **PASS** — EV-26.
- **FREEZE-013** (small stabilization only): **PASS** — this run authored no product, build-input, spec or lock change.
- **FREEZE-019 / -020** (P0/P1 NO-GO): **PASS** — 0 open P0, 0 open P1.
- **FREEZE-021 / -022** (P2/P3 decisions): **PASS** — every P2/P3 carries owner, impact, workaround and decision.
- **FREEZE-023 / -024 / -025 / -026** (matrix truth): **PASS** — no stale Supported, Experimental/Unsupported explicit, prerequisites and provider limits current.
- **FREEZE-027** (W01 Supported rows evidenced): **PASS** — no new Supported row claimed.
- **FREEZE-028** (invalidated evidence rerun): **PASS** — the W30 repair invalidated the previous candidate, so the candidate was rebuilt and every artifact-bound gate re-executed against the new SHA.
- **FREEZE-029** (full suite green **or** deviations explicitly release-accepted and not P0/P1): **SATISFIED BY ITS SECOND BRANCH, not green** — EV-20 is 15 failed. All 15 are explicitly decided: 12 node ids → 8 P2/P3 root causes with owner + impact + workaround + deferral decision, and 3 measured non-repository artifacts with proof. No P0, no P1 open. This is the branch the requirement itself provides.
- **FREEZE-030** (real-cluster regression passes): **RED - narrowed to ONE remaining blocker as of repair 116.** *(Superseded in part; see §14.)* Repair 112 recorded three measured blockers: (a) **DEF-W57-018**, withdrawn at repair 113 once the unattended opt-in was demonstrated; (b) **DEF-W57-017**, the unbounded lab harness, **CLOSED and VERIFIED at repair 116** - the maintained gate now terminates boundedly with a truthful red instead of hanging; (c) **DEF-W57-006**, `compute02` down, which remains. The regression's own end-to-end result is now real and reproducible: 23 required checks, 7 failed, exit 3, and every one of the 7 is a direct and only consequence of the `compute02` outage. Evidence: `artifacts/wave_W57/W57_REPAIR116_LAB_GATE_TRUTHFUL_TERMINAL_RESULT.json`, `W57_FREEZE030_040_REGRESSION_EXECUTION_PROOF.json`, `W57_WORKSTREAM_E_REAL_CLUSTER_REPLAY_R113.json`.
- **FREEZE-031** (candidate SHA + provenance): **PASS** — §2: Main SHA, product delta, product tree hash, artifact SHA-256, size, bundle count, Qt count, build command, build env, `version`, `doctor`.
- **FREEZE-032** (packaged regression vs frozen): **GREEN as of repair 111.** The run-110 red (14/20) was root-caused to four stale topmost `WerFault` crash dialogs covering the smoke frame and stealing foreground at the synthetic WebView click; it was not a product defect and not the multi-display cause revision 3 assumed. With the dialogs closed and **no repository change of any kind**, the unmodified maintained harness returns 20/20 exit 0 on the same unmodified candidate `8BA80453` on 3/3 runs. Evidence: `W57_REPAIR111_ROOT_CAUSE_PROOF.json`, `W57_DEF_W57_016_SUPERSESSION.json`, `W57_PACKAGED_SMOKE_8BA80453_PASS{,_RUN2,_RUN3,_SUMMARY}.json`. The superseded red result is retained unmodified for audit.
- **FREEZE-033** (no open P0/P1): **PASS** — DEF-W57-008 is the only P1 and it is closed and verified.
- **FREEZE-034** (every P2/P3 decided): **PASS** — §4 and the Workstream H artifact.
- **FREEZE-035** (matrix/docs match candidate): **PASS** — EV-26, `test_w57_freeze_consistency` green in EV-20's suite.
- **FREEZE-036** (candidate unambiguous): **PASS** — this report and the declaration name one candidate; `CAA5904A` and `6cca43a5` are retained as separately named superseded/rollback entries.
- **FREEZE-037** (evidence reconciliation matrix): **PASS** — §2/§3/§5.
- **FREEZE-038** (full test logs): **PASS** — `.tmp/w57-run-110/ci-full.log`; node ids in `artifacts/wave_W57/W57_CI_FULL_FAILURES_RUN110.txt`.
- **FREEZE-039** (static gate logs): **PASS** — EV-25..EV-28 all exit 0.
- **FREEZE-040** (real-cluster regression evidence): **RED, but the evidence is now PRODUCED.** *(Superseded in part; see §14.)* Repair 112 recorded that this evidence "cannot be produced truthfully" because the lab regression wrote no artifact at all. That is no longer true: the maintained `lab-test.ps1` was executed end to end at repair 116 and emitted a complete, bounded, machine-checkable verdict - 23 required / 7 failed, exit 3, with `srun` and `shared_home_job` each terminated at 300.0 s with exit 124 and a truthful stderr marker. The requirement is not satisfied, because that evidence is red. Evidence: `artifacts/wave_W57/W57_REPAIR116_LAB_GATE_TRUTHFUL_TERMINAL_RESULT.json`.
- **FREEZE-041** (packaged regression evidence): **GREEN as of repair 111** - `artifacts/wave_W57/W57_PACKAGED_SMOKE_8BA80453_PASS_SUMMARY.json` bound to candidate `8BA80453`. The superseded red artifact `W57_PACKAGED_SMOKE_8BA80453_FAIL.json` is retained unmodified for audit.
- **FREEZE-042** (final support matrix): **PASS** — `docs/wiki/Compatibility-and-Support-Matrix.md` at `f6ab257f`.
- **FREEZE-043** (defect ledger): **PASS** — §4.
- **FREEZE-044** (candidate manifest): **DELIBERATELY NOT WRITTEN** - a manifest requires `ACCEPTANCE_GREEN`; FREEZE-030/-040 are red, so a green manifest would fabricate evidence.
- **FREEZE-045** (candidate SHA-256): **PASS** — `8BA80453…`, re-hashed on disk, with the non-reproducibility caveat recorded in §2.
- **FREEZE-046** (freeze declaration): **PASS as a truthful artifact** — `artifacts/wave_W57/W57_FREEZE_DECLARATION_SUCCESSOR.md`, rebound to `8BA80453`, `Frozen for W58: NO` with the measured reason.
- **FREEZE-047** (rollback identifiable): **PASS** — `6cca43a5` (prior declaration) and `CAA5904A` (superseded candidate) remain separately named.
- **FREEZE-048** (W11/W58 handoff frozen-only): **PASS as a contract statement** — the declaration forbids W58 consuming it while `Frozen for W58: NO`.
- **PKGREG-001** (W04 harness + W05-W09 acceptance cases against the frozen candidate): **GREEN as of repair 111** - the maintained entrypoint executed unmodified against the exact candidate SHA `8BA80453` returns 20/20 exit 0, `isolated_from_src: true`, on 3/3 runs after the environmental cause of the run-110 red was removed.
- **TODO-RUNTIME-CUTOVER-002** (clean-commit rebuild after a runtime change): **PASS** — the candidate was rebuilt from current product after the W30 repair, with a recorded build command and environment; the product delta is exactly one audited file.
- **TODO-RUNTIME-CUTOVER-003** (full packaged suite vs released SHA): **GREEN as of repair 111 - corrected at repair 116.** The run-110 red (`14/20`, DEF-W57-016) was proven to be desktop contamination by four stale topmost `WerFault` crash dialogs, not a product defect. With the contaminant removed and **no repository change**, the unmodified maintained harness returns **20/20, exit 0, `isolated_from_src: true`** against candidate `8BA80453` on **3/3 deterministic runs**. `W57_PACKAGED_SMOKE_8BA80453_PASS_SUMMARY.json` already declared this row in its `closes_findings`; §6 was simply stale. Caveat unchanged: `8BA80453` is the frozen *candidate*, not a released artifact (`Frozen for W58: NO`). The superseded red result is retained unmodified for audit.
- **TODO-010** (clean-profile first run): **PASS** — EV-29, green in isolation.
- **TODO-011** (OpenSSH password/key/host-key): **PASS as of repair 117 - moved off PARTIAL.** Requirement text (registry, `ACTIVE`): "Real local OpenSSH password/key/host-key acceptance." All three mechanisms now have real, non-mock acceptance. The **password** leg was the only one that did not, and it is now proven: the maintained `LOCAL_PASSWORD_REAL` fixture (`devtools/lab/docker-compose.yml`, real OpenSSH + real Slurm, published on `127.0.0.1:2222` only) was brought up with its own documented lifecycle command and the **frozen candidate itself** (`hpc-client-gui.exe`, SHA-256 `8BA80453…`, re-hashed and not rebuilt) completed `doctor connection` over a real password-authenticated session with `dns/port/auth/sftp/slurm/checksum` all PASS, exit 0; the paired negative with a deliberately wrong password returns `auth` FAIL and the downstream stages `not_attempted`, exit 3, which is what makes the positive result real rather than a bypassed auth path. The **key** leg stays live on `LOCAL_REAL_HYPERV` (EV-31, plus `.11`/`.12` at exit 0 re-measured at repair 116) and the **host-key** leg stays `host_keys_pinned_all_nodes` PASS at repair 116. Scoped honestly: the protocol makes `LOCAL_PASSWORD_REAL` authoritative for password success/failure and invalid-password rejection only, so no SFTP-round-trip, Slurm-job, packaging or GUI claim is taken from it, and key coverage remains 2 of 3 nodes for the sole reason that **DEF-W57-006** has `compute02` down. Evidence: `artifacts/wave_W57/W57_REPAIR117_TODO011_REAL_PASSWORD_ACCEPTANCE.json`.
- **TODO-012** (PTY keyboard/output/resize/reconnect): **GREEN as of repair 111 - corrected at repair 116.** `pty_resize`, `pty_input_output` and `terminal_readback` are all PASS in the 20/20 run against `8BA80453` (§ TODO-RUNTIME-CUTOVER-003). The "RED on the new candidate" text here was a stale consequence of DEF-W57-016, which repair 111 disproved and closed; the prior 20/20 bound to `CAA5904A` was correctly not reused, and the replacement proof is bound to `8BA80453`.
- **TODO-013** (SFTP CRUD): **GREEN as of repair 111 - corrected at repair 116.** `remote_file_roundtrip`, `files_surface` and `files_controls` are PASS in the 20/20 run against `8BA80453`. The red here was only ever a consequence of the DEF-W57-016 abort. The real-cluster SFTP leg is separately green: repair 113's WE-03/04/07/08 round trip.
- **TODO-014** (Slurm submit/status/cancel/output): **GREEN for the packaged and single-node real-cluster legs; the two-node leg remains externally blocked.** `job_roundtrip`, `jobs_surface` and `jobs_controls` are PASS in the 20/20 run against `8BA80453`, and repair 113 executed the real submit/status/cancel/accounting path on `login-control01`→`compute01` to 16/16 (WE-05a..WE-05f, job 80). The two-node path is still unavailable for the same sole reason as FREEZE-030/-040: **DEF-W57-006**, `compute02` externally down (§14.6).
- **TODO-016** (shutdown/soak): **GREEN as of repair 111 - corrected at repair 116.** `clean_shutdown` is PASS in the 20/20 run against `8BA80453`, and the source-tree soak is green in EV-20. The "PARTIAL" here was only ever a consequence of the DEF-W57-016 abort.
- **TODO-015** (error/recovery truthfulness): **PASS** — the harness reported every failing stage by name and the exact abort reason; no silent fallback was introduced anywhere.
- **TODO-017** (final report tied to the released SHA): **PASS as a truthful tie** — this report and the declaration both name `8BA80453…` as the tested artifact and state plainly that it is not a released, frozen candidate.

## 7. Diff review

- Repository change authored by run 110: **W57-owned evidence and the canonical report only.**
  **Corrected at repair 119 — this section's scope claim was false and understated the W57 diff.**
  The original text asserted "the only tracked-source working-tree changes are
  `src/hpc_gui/services/job_submit_cancel.py` and `tests/test_w30_submit_cancel.py`". Re-run at
  repair 119, `git status --porcelain -- src/ tests/ build/ scripts/ lab/ requirements.txt requirements-release.lock pyproject.toml`
  returns those two W30 files **and** four more: `lab/config.json`, `lab/lab-common.ps1`,
  `lab/lab-test.ps1` and `tests/test_local_real_lab_static.py` — all W57's own `DEF-W57-017`
  bounded-harness hardening from repairs 115/116 (§14) — plus the untracked
  `tests/test_local_real_lab_bounded_commands.py`. So the W57-authored harness/test delta was
  omitted from this diff review entirely.
  The two W30 files remain the controller-dispatched W30 closed-owner repair, which run 110
  restored byte-for-byte after the control experiment (the saved patch and the restored diff were
  compared and match exactly, and the `#SBATCH` gate is confirmed absent while the
  `#SBATCH -A/--account` provider rule at line 199 is intact). Run 110 itself created no product,
  spec, lock or build-input change; the W57-owned change it did author is lab-harness and
  lab-test code, which the previous wording denied.
- `artifacts/wave_W57/` additions this run: `W57_CI_FULL_FAILURES_RUN110.txt`,
  `W57_LAB_STATUS_RUN110.json`, `W57_PACKAGED_SMOKE_8BA80453_FAIL.json`,
  `W57_PACKAGED_SMOKE_9DEDBEA3_FAIL.json`, `W57_PACKAGED_SMOKE_PREREPAIR_F904FAAF_FAIL.json`,
  `W57_DEFECT_TRIAGE_WORKSTREAM_H_POST_W30_REPAIR.json`,
  `W57_PACKAGED_GATE_MULTIMONITOR_FINDING.json`; and
  `W57_FREEZE_DECLARATION_SUCCESSOR.md` was rebound in place (single declaration, history
  retained in §A/§B). All paths are inside the profile's `allowed_closeout_only_paths`.
- Superseded evidence is **preserved, not deleted**: the `CAA5904A` packaged payloads and the
  repair-106 triage file stay on disk and are marked superseded in place, so the contradiction
  (4 × 20/20 green on `CAA5904A` vs 6 × 14/20 red on the rebuilds) is auditable rather than hidden.
- `git diff --check` clean apart from the pre-existing LF/CRLF warning on the controller file.
- No secrets: no key material, password or private path was written to any artifact.
- No binary noise; `dist/` stays gitignored. No test weakened, no skip or xfail added.
- Temporary state stayed under `.tmp/w57-run-110/`. No worktree was created or touched.

## 8. Post-green review

Not applicable as a green close, but the alternates were checked. The `_has_key` correction in
the W28 repair remains strictly more correct than the form it replaced and is not a regression
source. The W30 repair removes a *product* rule while leaving the independent
`validate_template_against_provider` enforcement and the confirmed-job-ID acceptance intact, and
a new maintained test pins the corrected contract — so it narrows behaviour without weakening a
gate. The single genuine product question this run raised is DEF-W57-016: the packaged
terminal-accept path depends on a synthetic WebView click that does not survive a two-display
desktop. That is recorded, owned outward, and not opportunistically patched from W57.

## 9. Report / evidence requirements

- This canonical report, updated at the exact required path; **no** session-suffixed copy.
- `docs/wave-reports/v2/opencode/W57_AUDIT_REPORT.md` intentionally **not** written:
  `audit_policy: fresh-independent`, so a self-audit would violate policy. It belongs to the
  independently dispatched audit phase.
- Evidence manifest intentionally **not** written; see FREEZE-044.

## 10. Stop condition

**Corrected at repair 120 — the packaged group is GREEN; exactly one owned gate is red, and it is
authority-bound rather than a W57 product defect.**

1. **GREEN since repair 111** — **FREEZE-009/-032/-041 + PKGREG-001**: packaged regression
   **20/20, exit 0, `isolated_from_src: true`** on 3/3 deterministic runs against candidate
   `8BA80453`, with the `WerFault` desktop contamination removed and **no repository change**. The
   run-110 red (14/20, six runs, three builds) was `DEF-W57-016`, now `RESOLVED` /
   `P4 RESOLVED-ENVIRONMENTAL` (§4, `W57_DEF_W57_016_SUPERSESSION.json`). The superseded red
   evidence is retained unmodified for audit. *(The pre-repair-120 text of this section still listed
   this group as a red stop condition, contradicting this same report's §6 FREEZE-009/-032/-041 and
   §13.5; corrected here.)*
2. **RED — the sole remaining owned blocker: FREEZE-030/-040.** The EXTERNAL lab is degraded:
   `compute02` is `down*` with **no layer-2 presence at all** (ARP `Unreachable`, MAC
   `00-00-00-00-00-00`, `BootTime=None`), and the one in-protocol remedy
   (`lab/lab-reset.ps1` / `lab/lab-up.ps1` → `Start-VM`) is refused by the Hyper-V management
   plane with an **authorization** error; `IsAdministrator=False` and the principal is not in
   `BUILTIN\Hyper-V Administrators` (§17.4). `TODO-014`'s two-node leg is blocked for that same
   single reason.

Per W57's integration/freeze rule ("if a finding belongs to an earlier domain Wave, stop
opportunistic fixing and reopen that owner") and the parallel execution contract, this Wave stops
instead of patching them. `DEF-W57-006` is genuine unavailable **operator authority** — Windows
Administrator / Hyper-V rights on `MSKOMEK` — the one category that is human deferral rather than
repair work, so the phase status is **HUMAN_DEFERRED**, not `BLOCKED`. Every other owned open row is
GREEN, CLOSED, or explicitly routed to a non-W57 owner (`DEF-W57-007` → controller, `-010` →
W44/W52, `-011` → editor adapter, `-012` → W06, `-013` → W03, `-014`/`-015` → W44, `-009` → P3
defer). **Corrected at repair 121 - that claim was false.** A repository-owned orchestration defect
*was* open: the tracked, maintained `tests/test_wave_controller_regressions.py` is RED on two
audit-close-gate nodes, root-caused at repair 121 to a stale test seam (production
`audit_receipt_valid` is correct, 7/7 truth table against the real repository). It is routed to
the controller as `DEF-W57-007`; see 20. The phase status is therefore **REOPEN**, not
`HUMAN_DEFERRED`, which is reserved for `DEF-W57-006` alone. No user
question was asked.

## 11. Resume state

Verified and reusable:

- **The single open P1 is closed.** `tests/test_wx_editor_cross_view_actions.py` 14 passed exit 0,
  `tests/test_w30_submit_cancel.py` 16 passed exit 0, and the maintained full suite moved from
  **28 failed / 2986 passed** to **15 failed / 3000 passed** (EV-20). FREEZE-033 is satisfied.
- **The candidate is rebuilt and re-identified** at
  `8BA80453A76A664959BAEDF7716C476A5334B6AFF860A4BC79B9E220D48B4C57` (7672468 B, 172 files,
  0 Qt, `1.5.9`, `doctor` `frozen: True`), with the non-bit-reproducible-build caveat recorded.
- **The packaged-gate red is product-independent**, established by rebuilding without the W30
  repair and reproducing the identical 14/20 failure. This is the single most important fact for
  the next owner: it is not a regression introduced by the freeze work.
- Static gates green at this run: `check_i18n.py` 3/3, `ci.py docs`, `ci.py packaging`,
  `ci.py audit` — all exit 0.
- Three suite failures are re-proven non-repository artifacts (two green in isolation, one
  conditional on a gitignored local file).
- The parity gate itself is green; only its committed assertion is stale.

Open P0/P1: **none**.
Open P2 — **W57-owned and actionable in a Wave phase: none.** `DEF-W57-016` was closed at repair
111. *(Corrected at repair 120; this list previously still carried `-016` as open.)*
Open P2 — **routed to another owner, not W57's to fix:** DEF-W57-007 (controller), -010 (W44/W52),
-011 (editor adapter), -012 (W06), -013 (W03).
Open P3: DEF-W57-009, -014, -015.
`DEF-W57-006` is **P2** per §4 — this list previously misfiled it as P3 — and it is
authority-bound, not owner-actionable (§17).

Pending, in order:

1. ~~**Controller**: assign the stable owner for DEF-W57-016 and re-run the unmodified harness to
   green, binding a new 20/20 payload to the then-current candidate SHA.~~ **DONE at repair 111.**
   The cause was proven to be `WerFault` desktop contamination, **not** `wx_shell.py`; the
   unmodified harness then returned 20/20 exit 0 on 3/3 runs bound to `8BA80453` — precisely the
   re-run-and-bind action this item asked for. The residual `wx_shell.py` hardening (assume no
   third-party topmost window overlaps the frame) remains a genuine **still-unowned** robustness
   question for the controller to assign; it is not a W57 blocker and gates nothing here.
   *(Corrected at repair 120; this item had been carried forward unchanged since repair 111.)*
2. **Operator — the only W57 blocker**: recover `compute02` with the maintained
   `lab/lab-reset.ps1` / `lab/lab-up.ps1` from an Administrator / Hyper-V session, re-run
   `lab/lab-status.ps1` to `status: PASS`, then execute `lab/lab-test.ps1` to produce the
   FREEZE-030/-040 verdict.
3. **Controller**: resolve DEF-W57-007 — decide whether the 13 profile-declared orchestration
   scripts/protocols become tracked, and fix `protocols.program_orchestration` (declared
   `WAVE_PROGRAM_ORCHESTRATION.md`, actual `AC_WAVE_PROGRAM_ORCHESTRATION.md`). Both are
   `controller_restart_paths`; a Wave worker must not mutate them mid-run. Also refresh the
   stale `AGENT_PARITY=PASS` assertion in `tests/contracts/test_wave_closeout_hardening.py`.
4. **Controller**: open `closed_owner_repair` transactions for the remaining true owners
   (W06, W03, W44/W52) and assign stable owners for DEF-W57-009, -011 and -015.
5. **After items 2-4**: because the build is not bit-reproducible, re-declare the SHA-256 from the
   bytes actually shipped, re-bind the packaged evidence to it, then write
   `artifacts/wave_W57/WAVE_W57_EVIDENCE_MANIFEST.json` with `ACCEPTANCE_GREEN`, re-issue the
   declaration with `Frozen for W58: YES`, and dispatch the fresh independent audit. The manifest
   stays unwritten until then: it requires `ACCEPTANCE_GREEN`, and **FREEZE-030/-040 are the only
   red owned rows**, so a green manifest today would fabricate evidence. *(Corrected at repair 120;
   this item previously also named `FREEZE-009`/`-032`/`-041` as red, which has been false since
   repair 111.)*

## 12. Final summary

```text
FIX: none authored this run. No W57-owned product/test/spec/build-input change; the only
     source changes in the tree are the controller-dispatched W30 repair (restored
     byte-for-byte after the control experiment)
BUILD: candidate REBUILT from post-repair product, not patched — 8BA80453… 7672468 B
       172 files 0 Qt, version 1.5.9, doctor PASS/frozen. Build is NOT bit-reproducible
CLOSED: DEF-W57-008 (P1) — the single open P1, closed by the W30 repair and verified:
       12 node ids green, full suite 28 -> 15 failed, FREEZE-033 satisfied
NEW: DEF-W57-016 (raised P2 at run 110) packaged terminal-accept abort — 6/6 deterministic
     red, 3 builds, proven independent of the W30 repair by rebuilding without it.
     **RESOLVED at repair 111 as environmental** (P4 / RESOLVED-ENVIRONMENTAL), not product
GREEN: FREEZE-033 (no open P0/P1), FREEZE-034 (every P2/P3 decided), FREEZE-029's second
     branch (all 15 deviations explicitly release-accepted, none P0/P1), FREEZE-031/045
     (candidate identity + provenance), FREEZE-011/023-027/035-039 (static gates)
GREEN (corrected at repair 120; previously listed RED here): FREEZE-009/-032/-041, PKGREG-001,
     TODO-012/-013, TODO-RUNTIME-CUTOVER-003 — packaged regression 20/20, exit 0,
     isolated_from_src true, bound to candidate 8BA80453, 3/3 deterministic runs (repair 111)
RED — sole remaining owned blocker: FREEZE-030/-040 — EXTERNAL lab, compute02 down with no
     layer-2 presence and Start-VM refused at the Hyper-V authorization plane; two-node Slurm
     unavailable. Genuine unavailable operator authority, so the state is HUMAN_DEFERRED
     (DEF-W57-006)
P2/P3: 7 P2 root causes (12 node ids) + 4 P3, all with owner + impact + workaround +
       decision; 3 further nodes measured to be non-repository artifacts
Reclassification: 3 of the 15 suite failures are not repository defects — 2 green in
            isolation, 1 conditional on a gitignored local AGENTS.md
Regression tests: none added by W57 (no W57-owned behaviour changed). The W30 repair ships
            its own new maintained test (test_w30_submit_does_not_gate_on_sbatch_directive_presence)
Skipped/xfail changes: none
Package evidence: GREEN — W57_PACKAGED_SMOKE_8BA80453_PASS{,_RUN2,_RUN3,_SUMMARY}.json,
                  20/20, exit 0, isolated_from_src true, bound to 8BA80453. The superseded
                  red W57_PACKAGED_SMOKE_8BA80453_FAIL.json (14/20) and the two control
                  builds are retained unmodified for audit
External evidence: lab status re-measured (login-control01 + compute01 OK, compute02 down);
                  no full replay is possible against the new candidate
Manifest: deliberately not written; FREEZE-030/-040 are red and a green manifest would
          fabricate evidence
Self-audit: not written; audit_policy is fresh-independent
Wave decision: HUMAN_DEFERRED — NO-GO for freeze. The P1 is gone, the packaged group is green
          and FREEZE-029/033 are satisfied, but FREEZE-030/-040 remain red on the single
          authority-bound cause DEF-W57-006; W58 must not consume the successor declaration
          while Frozen for W58: NO
```

## 13. Repair phase 111 — DEF-W57-016 root-caused, disproving the multi-display hypothesis

Phase instance: `20260925-074235-63df86b0:111:W57:repair`
Repair hypothesis: `W57-PACKAGED-GATE-WERFAULT-DIALOG-FG-STEAL`

### 13.1 FINDING

Run phase 110 reopened W57 with `DEF-W57-016` (P2): the packaged gate returns 14/20 with
`keyboard_input:foreground_lost_after_terminal_click` on 6/6 runs across 3 distinct builds,
including one that excluded the W30 repair. Run phase 110 recorded the cause as a *hypothesis*
— "ClientToScreen/SetCursorPos coordinate handling for a WebView host on a non-primary
display" — explicitly not a proven root cause, and correctly declined to patch it.

### 13.2 OBSERVED_FAILURE

Rather than re-run the same experiment, this phase **measured** the foreground window. A
non-destructive 10 ms `GetForegroundWindow` poller
(`.tmp/w57-repair-111/fg_watch.py`, read-only — it sends no input and changes no window state)
ran concurrently with the **unmodified** maintained harness. It reproduced 14/20 and captured
the exact three-step sequence:

| t | hwnd | process | class | title | rect |
|---|---|---|---|---|---|
| 0.001 s | 4791140 | `WerFault.exe` | `#32770` | `Python` | (769,394)–(1135,580) |
| 6.633 s | 5969520 | `hpc-client-gui.exe` | `wxWindowNR` | `HPC Client GUI 1.5.9` | (130,130)–(1410,890) |
| 7.049 s | 4791140 | `WerFault.exe` | `#32770` | `Python` | (769,394)–(1135,580) |

The frame **correctly claims foreground** at 6.633 s, so the `wx_shell.py:2296` guard passes
and `keyboard_input:foreground_lost` is never raised. 0.416 s later — exactly at the synthetic
click — a **topmost `WerFault` crash-report dialog reclaims foreground**, and
`wx_shell.py:2373` raises `foreground_lost_after_terminal_click`, cascading the 6 dependent
checks to FAIL.

The geometry is decisive. The frame rect gives a WebView centre click point of **(770, 510)**.
The dialog rect starts at x=**769**. The click point lands **1 pixel inside the dialog's left
edge**, on the **primary** display. `SendInput` delivers a click to the topmost window at the
cursor, so the click went to the crash dialog and never reached the xterm WebView.

### 13.3 HYPOTHESIS

Stale topmost WER crash dialogs left by crashed `python.exe` processes cover the smoke frame
and steal foreground at the synthetic click. **This is desktop contamination, not a product
defect, and not a multi-display coordinate issue.** The run-phase hypothesis is
**DISPROVEN**: the stealer sits on the primary display *inside* the frame rect, so no
coordinate virtualization is required to explain it, and the same red appeared on a build
that excluded the W30 repair for this same environmental reason.

Supporting facts: 4 `WerFault.exe` processes (started 23:48, 23:57, 00:02, 00:06 — spanning
the earlier gate runs); `AppCrash_python.exe` WER reports archived 23:34–00:07; `python.exe`
crash dumps already on disk at 23:31/23:34; plus 18 orphaned `msedgewebview2` and 6 stray
`python` processes on the session.

### 13.4 CHANGE

**No repository file was changed.** No file under `src/`, `tests/`, `scripts/` or `build/` was
touched; `git status` shows only the pre-existing controller-dispatched W30 repair in
`src/hpc_gui/services/job_submit_cancel.py` and `tests/test_w30_submit_cancel.py`. The
candidate bytes are identical before and after: `8BA80453…`, 7672468 B, 172 files.

The only action taken was **environmental**: after first confirming the `python.exe` crash dumps
and WER reports were already archived on disk (so no diagnostic evidence was destroyed), the
four stale WER report dialogs were closed. The `wx_shell.py` click-path hardening remains an
**outward-routed owner question** (owner still UNRESOLVED) and is deliberately **not** patched
by W57, per scope discipline (`W57.md:95`).

### 13.5 RESULT

The **unmodified** harness against the **unmodified** candidate:

| run | WerFault dialogs | result | exit | passed | runtime |
|---|---|---|---|---|---|
| contaminated probe | 4 | FAIL | 1 | 14/20 | `keyboard_input:foreground_lost_after_terminal_click` |
| clean 1 | 0 | **PASS** | **0** | **20/20** | — |
| clean 2 | 0 | **PASS** | **0** | **20/20** | — |
| clean 3 | 0 | **PASS** | **0** | **20/20** | — |

3/3 deterministic, `isolated_from_src: true`, bound to candidate `8BA80453`. No `WerFault`
dialog was regenerated. The clean-run foreground timeline shows the frame **retaining**
foreground across the click phase — the inverse of the contaminated run. This recovers
**FREEZE-009, FREEZE-032, FREEZE-041, PKGREG-001, TODO-012 and TODO-RUNTIME-CUTOVER-003**.

Evidence: `artifacts/wave_W57/W57_PACKAGED_SMOKE_8BA80453_PASS.json` (+`_RUN2`, `_RUN3`),
`W57_PACKAGED_SMOKE_8BA80453_PASS_SUMMARY.json`, `W57_REPAIR111_ROOT_CAUSE_PROOF.json`,
`W57_DEF_W57_016_SUPERSESSION.json`. The superseded finding and the superseded red result are
retained unmodified for audit.

### 13.6 What is still blocked, and why it is not repaired here

**Superseded in part by repair phase 113 (§1b).** The `DEF-W57-018` paragraph in step 11 above is
**withdrawn**: the unattended opt-in exists (`HPC_GUI_CONFIG_ROOT`) and the Workstream E
real-cluster regression was executed to **16/16 PASS** this phase. The remaining external blocker
is narrower than recorded at phase 112.

**`compute02` is still down — genuinely unavailable here, and honestly disclosed.**
`lab/lab-status.ps1` exits 3, `slurm.ok = false`, `sinfo -N` reports `compute01|idle`,
`compute02|down*`. The documented recovery is `lab/lab-up.ps1`, which calls `Require-Admin` and
drives `Get-VM`/`Stop-VM`/`Start-VM`; this session runs as `MSKOMEK\mskomek` with
`IsAdministrator=False`, is not in `BUILTIN\Hyper-V Administrators`, and `Get-VM` fails with an
authorization error. Recovery therefore requires an elevated operator session — it is **not** a
repository defect and **not** something W57 may paper over. Consequence: the lab is below its
documented verified baseline and the maintained two-node `srun` gate in `lab/lab-test.ps1` still
cannot complete. **DEF-W57-006** stays open as an operator action.

**`DEF-W57-017` — CLOSED at repair 115, VERIFIED at repair 116.** *(Superseded by §14; the text
below is retained for audit.)* As of repair 111 the statement here was accurate: `Invoke-LabSshCapture`
still set no command timeout, so `lab/lab-test.ps1` could still neither pass nor fail unattended
while a node is DOWN. It was **not** edited at that point: `lab/` is the lab-provisioning surface,
not W57's product surface, and `W57.md:143` requires routing rather than opportunistic cross-Wave
fixing. That routing was correct for its moment, but the owner never acted. Repair 115 applied the
bound, and repair 116 executed the maintained gate end to end and measured the result.

**FREEZE-044 (manifest) stays unwritten.** It requires `ACCEPTANCE_GREEN`; this phase does not
self-audit (`audit_policy: fresh-independent`) and does not self-declare acceptance.

**Residual owner question (not claimed as done).** `wx_shell.py` still assumes no third-party
topmost window overlaps the frame. That robustness hardening is outward-routed and out of W57
scope; W57 records it, not closes it.

**Net:** the packaged-regression blocker and the CLI-gate blocker are **resolved and verified**,
and the owned real-cluster regression now has fresh, real, executed evidence for the first time.
Two items remain and are neither W57-fixable in this dispatch: **DEF-W57-017** (repository-owned,
routed to the lab-provisioning owner) and **DEF-W57-006** (elevated operator action). The
`Frozen for W58` declaration stays **NO**.

---

## 14. Repair 115 + 116 — DEF-W57-017 closed and verified; FREEZE-030/-040 narrowed to the compute02 outage

### 14.1 FINDING

Repair 115 changed `lab/lab-common.ps1` and `lab/lab-test.ps1` to bound every remote lab command
(`Invoke-LabBoundedCommand`, `ConvertTo-LabProcessArguments`, a remote `timeout -k 5`, and
config-driven 180 s / 300 s budgets). It then asserted, **without running the maintained gate**,
that the harness "will now *report* the node failure instead of hanging". That assertion is the
whole load-bearing claim of the change, and it had never been executed. Meanwhile the routed
`W57-DEF017-LAB-SSH-UNBOUNDED-COMMAND` finding was still `owner_state: pending`, and §13.6 of this
report still told the audit that the defect was open.

### 14.2 OBSERVED_FAILURE

An untested assertion in a canonical defect record. Concretely: repair 112 had measured that
`pwsh -NoProfile -NonInteractive -File .\lab\lab-test.ps1` "did not return; produced no output and
wrote no evidence artifact", and repairs 113/115 had worked around it with a private bounded runner
rather than by proving the maintained entrypoint itself was fixed.

### 14.3 HYPOTHESIS

`W57-DEF017-LAB-GATE-UNVERIFIED-TERMINAL-RESULT` — the phase-115 bound is real, effective and safe:
the unmodified maintained entrypoint now produces a bounded, truthful, non-hanging terminal result
that names exactly the checks the `compute02` outage breaks, and the remote-side bound reaps the
PENDING allocation instead of orphaning it.

### 14.4 CHANGE

**No repository file was created, edited or deleted before the run.** This was a measurement-only
test of the predecessor's claim. This section and
`artifacts/wave_W57/W57_REPAIR116_LAB_GATE_TRUTHFUL_TERMINAL_RESULT.json` are the only writes, and
they only record the result.

### 14.5 RESULT — the hypothesis is CONFIRMED

| measurement | value |
|---|---|
| command | `pwsh -NoProfile -NonInteractive -File .\lab\lab-test.ps1`, unmodified |
| wall clock | **671.1 s**, terminated |
| exit code | **3** (was: never returned) |
| status | **FAIL** |
| verdict | **23 required / 7 failed** |
| `srun` (two-node) | exit **124**, `timed_out: true`, **300.05 s**, truthful stderr marker |
| `shared_home_job` | exit **124**, `timed_out: true`, **300.03 s**, truthful stderr marker |
| false pass | none — a timeout is reported as a bounded failure, never as success |

The 7 failures are **exactly and only** the `compute02` outage. Four of them
(`ssh_key_login_all_nodes`, `canonical_paths`, `identity_consistency`, `storage_roundtrip`) probe all
three configured nodes, and in every one `login-control01` and `compute01` returned exit 0 while
`compute02` returned 255 with `ssh: connect to host 192.168.250.13 port 22: Connection timed out`.
`srun_two_nodes` and `shared_home_compute_job` need a two-node allocation Slurm refuses;
`sinfo_nodes` is false because Slurm reports `compute02|down*`. The other 16 checks are green and
were re-measured live: PTY `/dev/pts/0`, host keys pinned on all three nodes, SFTP download and
upload with content match, MUNGE round trip, `squeue`/`scontrol`/`sbatch`/`sacct`, the
permission-denied negative path, and submit/`scancel`/cancel-state.

**The bound does not orphan allocations.** `srun` jobs 86 and 88 were created and reaped by the
remote `timeout -k 5`; neither was still present at cleanup. The one pre-existing leaked `PENDING`
job (81, from an earlier wave phase) was cancelled and `squeue` re-read empty — the same cleanup
repair 112 performed for jobs 76/77. No lab configuration, VM, disk, key or repository file was
altered.

**FREEZE-040's evidence is now produced**, where repair 112 recorded that it could not be produced
at all. It is truthful and it is red.

### 14.6 DEF-W57-006 re-confirmed at layer 2, and one self-correction

This phase tested whether `compute02` was really an unavailable external resource, or a *powered*
guest with a dead SSH/Slurm stack that W57 could have repaired. It is the former:

- `ping.exe -n 2 -w 2000 192.168.250.13` → **Sent 2, Received 0, Lost 2 (100% loss)**;
  `192.168.250.12` → Received 2, 0% loss.
- `Get-NetNeighbor`: `192.168.250.13` is **`Unreachable`, MAC `00-00-00-00-00-00` (never resolved)**,
  while `.11` resolves to `02-00-00-fa-00-0b` and `.12` to `02-00-00-fa-00-0c`.
- `scontrol show node compute02` → `State=DOWN+NOT_RESPONDING`, `BootTime=None`,
  `SlurmdStartTime=None`, `FreeMem=N/A`, `Reason=Not responding [slurm@2026-09-27T16:25:51]`.
- `IsAdministrator=False`; `Get-VM` → *"You do not have the required permission to complete this
  task"*; not in `BUILTIN\Hyper-V Administrators`; the Hyper-V CIM provider exposes the host only.

**There is no layer-2 presence at all**, so there is no guest-side or repository-side repair path.
`DEF-W57-006` is `EXTERNAL_BLOCKED` — genuinely unavailable external authority, confirmed rather
than re-litigated.

**Self-correction, recorded so the audit does not inherit it:** an earlier ad-hoc probe *in this
same phase* printed `PING_OK` for `compute02`. That was a bug in the probe one-liner, which tested
the truthiness of the `Test-Connection` result object instead of filtering on `-Status Success`. It
was falsified by raw `ping.exe` and by the ARP table. The corrected measurements above are the
record.

### 14.7 What is still open, after this phase

- **FREEZE-030 / FREEZE-040** — RED, narrowed from three measured blockers to **one**:
  `DEF-W57-006`. `DEF-W57-018` was withdrawn at repair 113; `DEF-W57-017` is closed and verified here.
- **FREEZE-044** — manifest deliberately **not** written. It requires `ACCEPTANCE_GREEN`, and
  FREEZE-030/-040 are red. `Frozen for W58` stays **NO**.
- **`wx_shell.py` third-party topmost-window robustness** — still an outward-routed owner question,
  out of W57 scope. Recorded, not closed.
- **Two red POSTRUN validators** (`validate-ac-project.py` materialization staleness,
  `validate-managed-runtime.py` controller behaviour) — both produced by the uncommitted local
  modifications to the profile's `controller_restart_paths`. That checkpoint/materialization
  obligation is **controller-owned** per `AGENTS.md`; a Wave worker must not materialize or commit
  controller files, so it is reported here, not repaired here, and not attributed to W57. The other
  four POSTRUN validators exit 0.

### 14.8 Stale requirement dispositions corrected in the same phase

While verifying the ledger, this phase found that §6 still carried **five owned rows marked red for a
defect that repair 111 had already disproved and closed**. `W57_PACKAGED_SMOKE_8BA80453_PASS_SUMMARY.json`
already listed `HPC-W10-TODO-012` and `HPC-W10-TODO-RUNTIME-CUTOVER-003` in its own `closes_findings`,
and all twenty harness checks — including `pty_input_output`, `terminal_readback`,
`remote_file_roundtrip`, `job_roundtrip` and `clean_shutdown` — are `PASS` in the 20/20 run against
`8BA80453`. `TODO-RUNTIME-CUTOVER-003`, `TODO-012`, `TODO-013`, `TODO-014` and `TODO-016` are
therefore corrected in §6, with the `Frozen for W58: NO` caveat retained where it belongs and the
`DEF-W57-006` two-node caveat retained on `TODO-014`. This is a report-truthfulness defect
(`HPC-W10-FREEZE-035`, `-010`, `-043`), not a product change: no code, test, spec or build input
was touched.

### 14.9 Evidence

`artifacts/wave_W57/W57_REPAIR116_LAB_GATE_TRUTHFUL_TERMINAL_RESULT.json`. Focused retest re-executed
in this dispatch: `pytest tests/test_local_real_lab_bounded_commands.py
tests/test_local_real_lab_static.py -q` → **8 passed**, exit 0. HEAD unchanged at
`f6ab257fbfd62d402e31e9330f30bb017b795fa8`; frozen candidate `8BA80453…` not patched and not
rebuilt.

## 15. Repair 117 - "no W57-owned repair action remains" is falsified; TODO-011 closed with real password evidence

### 15.1 FINDING

Repair 116 ended by asserting that **"no W57-owned repair action remains"** and that the only
outstanding items were the external `compute02` outage and a controller-owned materialization
obligation. That assertion was never checked against the Wave's own requirement ledger. §6 of this
same report carried owned row `HPC-W10-TODO-011` at **PARTIAL** — the only owned row left PARTIAL —
because *"the `LOCAL_PASSWORD_REAL` password leg was not re-executed this run and no prior leg is
reusable against the new candidate."* That is a W57-owned acceptance gap. It is not gated by
`compute02`, and it is not controller-owned. It had simply never been attempted.

### 15.2 OBSERVED_FAILURE

The registry row (`ACTIVE`, owner `W57`) reads: **"Real local OpenSSH password/key/host-key
acceptance."** Of the three mechanisms, key and host-key were already proven live on
`LOCAL_REAL_HYPERV`. The **password** mechanism had no real evidence at all, and the reason is
structural rather than accidental:

- The only harness in the repository that exercises password authentication,
  `scripts/wx_packaged_smoke.py`, drives it through an **in-process mock**
  (`support.mock_ssh_server.MockSSHServer`, fed by `HPC_GUI_PACKAGED_SMOKE_SSH_PASSWORD`). The
  protocol states in-process mocks cannot replace real target evidence.
- `LOCAL_REAL_HYPERV` is **key-only** (`ssh_pwauth: false`) and the protocol states it *"must not be
  used as password-auth evidence"*.
- The target the protocol **does** designate for this — `LOCAL_PASSWORD_REAL` — was not running:
  `127.0.0.1:2222` was not listening and no `hpclab` container existed.

So the password leg was simultaneously unproven *and* trivially executable. It was a gap in
diligence, not a genuine blocker.

### 15.3 HYPOTHESIS

`W57-TODO011-PASSWORD-LEG-UNCLOSED-AND-EXECUTABLE`: the password leg was left unclosed not because
it was unexecutable but because it was never attempted. `LOCAL_PASSWORD_REAL` is a maintained,
documented Docker fixture bound to `127.0.0.1:2222`, needing neither the downed `compute02` guest
nor an elevated Hyper-V operator. Tested by bringing that fixture up with its own maintained
command and executing real password acceptance, plus the negative case, against the exact frozen
candidate. (The prior hypothesis `W57-DEF017-LAB-GATE-UNVERIFIED-TERMINAL-RESULT` was **resolved** at
repair 116 and is deliberately **not** reused; re-running it would be a no-progress cycle.)

### 15.4 CHANGE

**No product, test, spec, build-input, candidate or security change.** The frozen candidate was
neither patched nor rebuilt and still hashes to `8BA80453…`. The fixture was created by its
documented maintained lifecycle command and is disposable state under `.tmp/`. The only repository
writes are this section and `artifacts/wave_W57/W57_REPAIR117_TODO011_REAL_PASSWORD_ACCEPTANCE.json`.

### 15.5 RESULT — CONFIRMED

The fixture came up `healthy` (`sinfo` → `debug*`/`short` both `idle hpclab`; `scontrol ping` →
`Slurmctld(primary) at hpclab is UP`) and the **frozen candidate itself** was driven against it:

| Leg | Input | Result |
|---|---|---|
| **A — real password acceptance** | correct fixture password, via `--password-stdin` | exit **0**, `dns/port/auth/sftp/slurm/checksum` all **PASS**, `auth` detail `authenticated` |
| **B — invalid-password rejection** | a freshly generated random GUID (not the fixture value) | exit **3**, `auth` **FAIL** `authentication failed`, downstream stages `not_attempted` |

Leg B is what makes leg A meaningful: a positive result alone cannot distinguish real authentication
from a bypassed or skipped auth path. Together they show the credential was genuinely enforced,
the failure was reported truthfully and visibly, and no fallback mechanism was used.

`HPC-W10-TODO-011` therefore moves **PARTIAL → PASS**, and the predecessor's "no W57-owned repair
action remains" is falsified.

**Security handling — the gate was respected, not weakened.** The first attempt was correctly
refused with *"Remote CLI access is disabled"*, because `cli_external_access_enabled` defaults to
`false`. That real product control was not bypassed in code, not weakened, and not changed in the
repository. It was satisfied only inside a throwaway per-run config root (`HPC_GUI_CONFIG_ROOT`)
under `.tmp/`, via the product's own maintained setter `set_cli_external_access_enabled(True)`; the
user's real settings were never read or modified. The password was read at run time from its
maintained documentation file rather than embedded anywhere, delivered only through a redirected
stdin, never placed in argv, and the temporary stdin files holding it were deleted afterwards. **No
secret appears in this report, in the artifact, or in any log.**

**Claim scoping, kept honest.** The protocol makes `LOCAL_PASSWORD_REAL` authoritative for password
success/failure and invalid-password rejection *only*, and states it does not replace `LOCAL_REAL`
for key, host-key, Slurm, SFTP or site-specific claims. So no SFTP-round-trip, Slurm-job, packaging
or GUI claim is taken from this fixture. Key coverage also remains **2 of 3 nodes** for the sole
reason that **DEF-W57-006** has `compute02` down.

### 15.6 What did *not* change

`DEF-W57-006` was re-measured at the start of this phase and is unchanged — `ping.exe
192.168.250.13` → Sent 2, Received 0, **100% loss**; `Get-NetNeighbor` still `Incomplete` with MAC
`00-00-00-00-00-00`; `IsAdministrator=False`. **FREEZE-030** stays RED solely on that outage,
**FREEZE-040**'s evidence stays truthfully red, and **FREEZE-044**'s manifest is still deliberately
**not** written because it requires `ACCEPTANCE_GREEN`. Closing TODO-011 does not advance any of
these: **the Wave is still `BLOCKED`**, and this phase removed one owned row from the open set and
nothing more.

### 15.7 Evidence

`artifacts/wave_W57/W57_REPAIR117_TODO011_REAL_PASSWORD_ACCEPTANCE.json`. Focused retest re-executed
in this dispatch: `pytest tests/test_local_real_lab_bounded_commands.py
tests/test_local_real_lab_static.py -q` → **8 passed in 9.34s**, exit 0. HEAD unchanged at
`f6ab257fbfd62d402e31e9330f30bb017b795fa8`; candidate `8BA80453…` re-hashed on disk, not patched
and not rebuilt.

## 16. Repair 117 - a new controller-owned defect found while verifying §14.7: every POSTRUN check is missing from Git

### 16.1 FINDING

Verifying §14.7's claim about the two red POSTRUN validators turned up a separate defect that
concerns **all six** of them. `WAVE_PROJECT_PROFILE.json` — which *is* tracked — declares six
`postrun_checks` under `.opencode/scripts/`. **None of the six are tracked in Git.** All six exist in
the working tree only, suppressed by a local rule.

### 16.2 MEASUREMENT

| POSTRUN check | tracked | ignored | exists in worktree |
|---|---|---|---|
| `validate-ac-project.py` | no | yes | yes |
| `validate-agent-parity.py` | no | yes | yes |
| `validate-wave-orchestration.py` | no | yes | yes |
| `validate-wave-program.py` | no | yes | yes |
| `validate-managed-runtime.py` | no | yes | yes |
| `validate-wave-authoring.py` | no | yes | yes |

Matched rule: `D:/Projeler/TrubaGUI/.git/info/exclude:33` → `/.opencode/`.

The nuance that makes this a defect rather than a policy: the exclusion is a **local, untracked**
rule in shared clone metadata, so it differs per clone and is invisible to review. Only five
`.opencode` files are tracked (`LOCAL_REAL_HPC_LAB.md`, `WAVE_PROJECT_PROFILE.json`,
`route-wave-findings.py`, `run-wave-program.py`, `wave_state_engine.py`) — because Git tracking
wins over an exclude rule. So **the profile that declares the six checks is in Git while the six
checks themselves are not.** (This working tree is itself a linked worktree, so the exclude rule is
shared by every worktree of that clone.)

`AGENTS.md` makes executable POSTRUN checks a precondition for `PROGRAM_COMPLETE`. That precondition
is currently satisfied by code that is not part of repository truth, cannot be run or reviewed from a
fresh clone, and cannot be cited as a resolvable evidence identity by an independent auditor.

### 16.3 Collateral correction to an inherited claim

§14.7 records that the two red POSTRUN validators are *"produced by the uncommitted local
modifications to the profile's `controller_restart_paths`"*. **That attribution is not verifiable
and should not be relied on.** A HEAD-versus-worktree comparison requires the validators to exist at
HEAD, and they do not: a pristine `git worktree add --detach … HEAD` was created to run the
comparison and the six scripts were simply absent from it. The comparison cannot be performed at
all, so the recorded cause is an assumption rather than a measurement.

The **routing** conclusion is unchanged — the materialization/checkpoint obligation is
controller-owned per `AGENTS.md` and a Wave worker must not materialize or commit controller files.
Only the recorded **reason** is unverified.

A supporting observation: the failing-check signature has *changed* since repair 116. Repair 116
recorded a dispatch-plan mismatch (`W101a/W101b` not produced); re-running
`validate-managed-runtime.py` in this dispatch shows
`controller_semantic_counters_vs_retries`, `progress_contract_v1_v2_deterministic`,
`audit_close_todo_semantic_history`, `controller_worker_timeout_serial_parallel_barrier` and
`multi_group_managed_parallel_synthetic_base` all FAIL, while `parallel_restart_mismatch_fail_closed`,
`serial_foreign_job_fail_closed` and `windows_case_path_collisions_fail_closed` PASS. A drifting
failure signature is consistent with untracked validators falling out of sync with the tracked
controller code they exercise.

**Self-correction, recorded so the audit does not inherit it:** an earlier attempt in this phase to
run this comparison was invalid — it invoked the worktree's script path while the *main* repository
was the working directory, which yielded a misleading `EXIT=2`. It was detected, re-run with the
correct working directory, and the real cause (absence from a HEAD checkout entirely) emerged. The
invalid attempt is disclosed rather than discarded.

### 16.4 Disposition

**Routed to the controller; not fixed here.** This is orchestration surface (`.opencode/`) and, more
directly, `.git/info/exclude` is shared clone metadata outside the repository working tree — not a
Wave worker's call. Recommended owner action is in the artifact: decide whether the six checks are
intended to be repository truth (then track them and drop the blanket `/.opencode/` exclusion) or
intentionally local-only (then stop declaring them as `postrun_checks` and re-express the
`PROGRAM_COMPLETE` precondition against checks that exist in Git). Until that decision is made,
POSTRUN results in any Wave report should be labelled non-reproducible rather than cited as
authoritative.

### 16.5 Evidence

`artifacts/wave_W57/W57_REPAIR117_POSTRUN_CHECKS_NOT_IN_REPOSITORY_TRUTH.json`. No controller file
was added, tracked, un-ignored, committed or edited, and `.git/info/exclude` was left untouched. The
temporary pristine worktree created for the comparison was removed after measurement.

## 17. Repair 118 - DEF-W57-006 closed at the authority layer: the blocker is unavailable operator authority, not a lab fault

### 17.1 FINDING

`DEF-W57-006` is the last open W57-owned blocker. Repairs 116 and 117 re-measured it, but only at the
**network** layer - `ping 192.168.250.13` 100% loss, ARP `Unreachable` with MAC `00-00-00-00-00-00`,
`IsAdministrator=False`. Those measurements prove the guest is *unreachable*. They do **not** establish
whether the cause is a **lab-fabric fault** (repairable in-protocol) or the **absence of the authority**
needed to act on it. That distinction decides whether W57 is repair work or operator work, and it had
never been measured.

### 17.2 HYPOTHESIS

`W57-DEF006-AUTHORITY-BOUND-NOT-INFRA-FABRIC-FAULT` - the outage is **not** a fabric fault. The vSwitch,
subnet, image pin, emitted profile and both live guests are healthy; the fault is isolated to the single
`compute02` VM object, and the one in-protocol remedy (`lab-reset.ps1` / `lab-up.ps1` -> `Start-VM`) is
refused by the Hyper-V management plane with an **authorization** error rather than a not-found or
timeout error. The predecessor hypothesis `W57-TODO011-PASSWORD-LEG-UNCLOSED-AND-EXECUTABLE` is
**resolved** at repair 117 and is deliberately **not** reused.

### 17.3 CHANGE

**None to product, test, spec, build-input, candidate, security or controller surface.** The frozen
candidate was neither patched nor rebuilt and still hashes to `8BA80453.`; HEAD is unchanged at
`f6ab257fbfd62d402e31e9330f30bb017b795fa8`. No UAC prompt was raised and no question was put to the
user, as the unattended parallel contract requires. Only this section and
`artifacts/wave_W57/W57_REPAIR118_DEF006_AUTHORITY_BOUNDARY_PROOF.json` were written.

### 17.4 RESULT - CONFIRMED

**The protocol-preferred bounded health check was executed and returned a complete machine-readable
verdict** (`lab/lab-status.ps1`, the check `LOCAL_REAL_HPC_LAB.md` tells us to prefer before replay) -
previously the state of this lab had only ever been inferred from raw `ping`/`ARP`:

| Node | IP | transport | services | Slurm |
|---|---|---|---|---|
| `login-control01` | 192.168.250.11 | **ok** | ssh, munge, slurmctld, slurmdbd, mariadb, nfs-server - all **active** | - |
| `compute01` | 192.168.250.12 | **ok** | ssh, munge, slurmd - all **active** | **idle** |
| `compute02` | 192.168.250.13 | **FAIL** | none | **down\*** |

Environment identity is healthy: `image_pin_ok: true` (`612b2c0c…` matches the expected pin) and
`profile_valid: true` (`a99c96fd…`).

**The fabric is therefore provably alive, and the outage is isolated.** `192.168.250.11` and `.12`
resolve real L2 addresses (`02-00-00-FA-00-0B`, `02-00-00-FA-00-0C`, both `Reachable`) and answer ICMP
on the *same* internal vSwitch `hpc-lab` and the *same* `192.168.250.0/24` subnet, while `.13` alone
fails to resolve. The host, the switch and the subnet are alive; one VM object is not.

**The authority boundary was then measured directly, by attempting the actual maintained action** - not
inferred from `IsAdministrator=False`:

```
Start-VM -Name 'compute02'
  -> You do not have the required permission to complete this task.
     Contact the administrator of the authorization policy for the computer 'MSKOMEK'.
Get-VM -Name 'compute02'   -> same authorization error
Get-VMSwitch               -> same authorization error
principal=mskomek  IsAdministrator=False
```

`Start-VM` is precisely the call `lab/lab-reset.ps1:10` and `lab/lab-up.ps1:178` make, so the maintained
remedy was tried and is refused at the Hyper-V management plane. **No repository, product, test or
orchestration change can alter that outcome**, which is what makes this a boundary and not a defect.

### 17.5 Focused retest (T09, this dispatch)

`python -m pytest tests/test_local_real_lab_bounded_commands.py tests/test_local_real_lab_static.py -q`
-> **8 passed in 9.36s**, exit 0. The `DEF-W57-017` bounded-harness hardening still holds against the
current content identity, so the maintained gate still terminates boundedly and truthfully instead of
hanging. The one genuinely repairable item in scope is also stable: the `LOCAL_PASSWORD_REAL` fixture
container `hpclab` is **Up (healthy)**, so `TODO-011` does not regress.

### 17.6 Disposition - status is `HUMAN_DEFERRED`, not `BLOCKED`

This is a deliberate change of normalized state from the previous fourteen `BLOCKED` results, and it is
a correction of classification rather than a retry. The blocker is **genuine unavailable operator
authority** - Windows Administrator / Hyper-V rights on `MSKOMEK` - which is the one category that is
human deferral, as opposed to a repository-owned technical or orchestration defect. Continuing to return
`BLOCKED` would have kept signalling "repairable by a Wave worker" and would have burned further repair
attempts against a boundary this process provably cannot cross.

Consequences for the owned rows are unchanged and truthful:

- **FREEZE-030** RED, **FREEZE-040** RED - sole cause `DEF-W57-006`
- **FREEZE-044** deliberately **not** written - a manifest requires `ACCEPTANCE_GREEN`
- **TODO-014** two-node leg externally blocked - sole cause `DEF-W57-006`
- **`Frozen for W58`: NO**
- every other owned open row is either GREEN/CLOSED or explicitly routed to a non-W57 owner
  (`DEF-W57-007` -> controller, `-010` -> W44/W52, `-011` -> editor adapter, `-012` -> W06,
  `-013` -> W03, `-014`/`-015` -> W44, `-009` -> P3 defer). None is W57's to fix opportunistically.

The `POSTRUN`-checks-not-in-repository-truth defect recorded at repair 117 (`/.opencode/` suppressed by
the local `D:/Projeler/TrubaGUI/.git/info/exclude:33` rule, so all six declared `postrun_checks` are
untracked) is **left exactly as routed**. It remains a controller decision; this phase did not touch
`.git/info/exclude`, add or track any controller file, or weaken the `PROGRAM_COMPLETE` precondition.

### 17.7 Resume point (operator action, not agent action)

An operator with Windows Administrator / Hyper-V rights on `MSKOMEK`:

1. `lab/lab-reset.ps1` (or `lab/lab-up.ps1`) - return `compute02` to `Running`
2. `lab/lab-status.ps1` - confirm 23/23 and `compute02 idle`
3. `lab/lab-test.ps1` - produce the FREEZE-030/-040 verdict
4. W57 freeze declaration - FREEZE-031/-036/-044/-046/-048, then `Frozen for W58: YES`
5. fresh independent audit

### 17.8 Evidence

`artifacts/wave_W57/W57_REPAIR118_DEF006_AUTHORITY_BOUNDARY_PROOF.json`.

## 18. Repair 119 - the canonical report's own diff-review and candidate-delta evidence was falsified by repository truth

### 18.1 FINDING

`DEF-W57-006` is still authority-bound (§17), so the controller re-dispatched repair. Rather than
re-measure the same outage, this phase audited the claim that had been carrying the most weight in
this report and had never itself been tested: **§2's candidate-delta scoping evidence and §7's
diff-review scope claim.** Both are falsifiable by a single command, both are load-bearing
(`FREEZE-031` cites §2 for "product delta"; the Wave's `Diff Review` contract is discharged by §7),
and both are **false against current repository truth**.

### 18.2 OBSERVED_FAILURE

`git status --porcelain -- src/ build/ requirements.txt requirements-release.lock pyproject.toml scripts/ lab/`
- the exact command §2 cites as showing "only that file" - returns **four** entries:

```
 M lab/config.json
 M lab/lab-common.ps1
 M lab/lab-test.ps1
 M src/hpc_gui/services/job_submit_cancel.py
```

`git status --porcelain -- src/ tests/ build/ scripts/ lab/ requirements.txt requirements-release.lock pyproject.toml`
- the scope §7 calls complete - returns those four plus ` M tests/test_local_real_lab_static.py`,
` M tests/test_w30_submit_cancel.py` and the untracked `?? tests/test_local_real_lab_bounded_commands.py`.

So §7's sentence *"the only tracked-source working-tree changes are
`src/hpc_gui/services/job_submit_cancel.py` and `tests/test_w30_submit_cancel.py`"* is false, and
§7's *"This run created no product, test, spec, lock or build-input change"* is false on **test**:
`lab/lab-common.ps1` (+120/-18), `lab/lab-test.ps1`, `lab/config.json` (the new `timeouts` block)
and two `tests/` files **are** W57's own `DEF-W57-017` bounded-harness work from repairs 115/116.
Those changes are disclosed at §14 but were omitted from the diff review that is supposed to prove
scope discipline, which is the one place an auditor would look for them.

This is a **repository-owned, evidence-truthfulness defect on W57's own canonical artifact** - the
`Report / Evidence Requirements` contract and the audit's independent re-derivation both depend on
it. It is **not** gated on `compute02`, on Hyper-V rights, or on anything in §17, which is why it
had survived fifteen prior phases: none of them re-ran the report's own cited command.

### 18.3 HYPOTHESIS

`W57-CANONICAL-REPORT-SCOPE-CLAIMS-FALSIFIED-BY-REPO-TRUTH` - the W57 blocker set contains a
**second, W57-owned, repairable** defect that has been masked by the `DEF-W57-006` deferral:
this report asserts a working-tree scope that the working tree contradicts, so its
`FREEZE-031` provenance and its `Diff Review` discharge are not independently reproducible.
(Successor to, not a repeat of, `W57-DEF006-AUTHORITY-BOUND-NOT-INFRA-FABRIC-FAULT`, which is
unchanged and still authority-bound.)

### 18.4 CHANGE

**This report only.** §2 and §7 were corrected in place to state the true working-tree scope and to
attribute each file to its true owner (W30 closed-owner repair vs W57 `DEF-W57-017` harness work).
No product, test, spec, lock, build-input, candidate, lab-config, security or controller surface was
touched; `lab/` and `tests/` were **not** modified, only described correctly. No test was weakened,
no evidence artifact was edited, and the `POSTRUN`-checks-not-in-repository-truth defect (§16) was
left exactly as routed.

Deliberately **not** "fixed": the underlying working tree still carries those `lab/`/`tests/`
changes uncommitted. Committing them is not a Wave worker's call (it would also bind the W57
candidate tree to a new Main SHA and invalidate the freeze evidence), so the truthful fix is to
stop claiming a scope that does not exist.

### 18.5 RESULT - CONFIRMED

The falsifying measurement is reproduced above, and the correction was verified by re-running the
same two commands after the edit. The substantive claim that **survives** is now stated correctly and
re-verified in this dispatch against the exact bytes:

| §2 claim | repair 119 re-measurement | verdict |
|---|---|---|
| artifact `dist/hpc-client-gui/hpc-client-gui.exe` | 7672468 B, `8ba80453a76a664959baedf7716c476a5334b6aff860a4bc79b9e220d48b4c57` | **holds** |
| bundle file count | 172 | **holds** |
| candidate was neither patched nor rebuilt | HEAD still `f6ab257fbfd62d402e31e9330f30bb017b795fa8`, no rebuild | **holds** |
| product delta / scoping evidence | product tree unaffected; cited command was wrong | **corrected** |

The product-tree hash `23b31401...` is **not** re-asserted here: its manifest format is not
specified in the report, so it is not independently reproducible as written. That is recorded as a
known evidence limitation rather than a verified identity.

`FREEZE-031` and the §7 `Diff Review` are now truthfully derivable by an auditor from the working
tree. **W57 still cannot close**: `FREEZE-030`/`-040` remain RED and `TODO-014`'s two-node leg
remains externally blocked, both for the single unchanged reason `DEF-W57-006` (§17), and
`Frozen for W58` remains **NO**.

### 18.6 Focused retest (this dispatch)

`python -m pytest tests/test_local_real_lab_bounded_commands.py tests/test_local_real_lab_static.py -q`
-> **8 passed**, exit 0. The `DEF-W57-017` harness hardening that this report previously failed to
disclose is green and unchanged; no regression was introduced by the correction.

### 18.7 Evidence

`artifacts/wave_W57/W57_REPAIR119_REPORT_SCOPE_FALSIFICATION.json`.

## 19. Repair 120 - the canonical report mis-recorded its own owned acceptance verdict `HPC-W10-FREEZE-009`

Phase instance: `20260925-074235-63df86b0:120:W57:repair`
Repair hypothesis: `W57-OWNED-ACCEPTANCE-VERDICT-FALSIFIED-BY-OWN-EVIDENCE`

### 19.1 FINDING

`DEF-W57-006` is still authority-bound (§17), so the controller re-dispatched repair. Repair 119
corrected this report's **working-tree scope** claims (§2, §7). It did not touch the report's
**acceptance verdicts** — and those were falsified by the Wave's own on-disk evidence.

### 19.2 OBSERVED_FAILURE

`HPC-W10-FREEZE-009` is an **owned requirement of W57** (`waves/pending/W57.md` frontmatter
`owned_requirements`). §6 recorded it as **RED**. The Wave's own evidence artifact says otherwise:

| source | says about `HPC-W10-FREEZE-009` |
|---|---|
| §6 (this report) | **RED** — "EV-21/22/23, 14/20 on all six runs, all three builds" |
| `W57_PACKAGED_SMOKE_8BA80453_PASS_SUMMARY.json` | listed in `closes_findings` |
| `W57_PACKAGED_SMOKE_8BA80453_PASS.json` | `"result": "PASS"`, all 20 checks PASS, `8ba80453…` |
| `W57_DEF_W57_016_SUPERSESSION.json` | `status: RESOLVED`, `severity: P4 / RESOLVED-ENVIRONMENTAL` |
| §4 ledger, this report | DEF-W57-016 **"RESOLVED at repair 111 as environmental, not product"** |
| §6 `FREEZE-032`, this report | **GREEN as of repair 111** |
| §13.5, this report | "This recovers **FREEZE-009**, FREEZE-032, FREEZE-041, PKGREG-001, TODO-012 …" |

So the report **contradicts itself**: §13.5 says `FREEZE-009` is recovered and §6 says RED. Repair
116's §14.8 sweep corrected `TODO-012`/`-013`/`-014`/`-016` and `TODO-RUNTIME-CUTOVER-003` from the
same superseded red, and left this one row behind.

The same error propagated into the three sections an auditor and W58 read first:

- **§10 Stop condition** — listed the packaged group as red stop condition #1, and kept the phase
  status at `REOPEN` with the reason "both are repository- or environment-owned technical defects".
- **§11 Resume state** — still carried `DEF-W57-016` in the open-P2 list, misfiled `DEF-W57-006` as
  P3 (§4 says P2), and asked the controller to "re-run the unmodified harness to green and bind a
  new 20/20 payload" — precisely the action repair 111 had already performed and bound.
- **§12 Final summary** — `RED: FREEZE-009/-032/-041, PKGREG-001, TODO-012/-013,
  TODO-RUNTIME-CUTOVER-003` and `Package evidence: RED and recorded as red`.
- **Header** — `Session status: **REOPEN**`, "the two owned EXTERNAL gates remain red, and repair
  112 proved that 'compute02 is down' is not their only cause"; both falsified by repairs
  116/117/118, which narrowed three blockers to one and proved it authority-bound.
- **`W57_FREEZE_DECLARATION_SUCCESSOR.md`** (FREEZE-046) — the `Frozen for W58: NO` line cited
  "**three** independently measured reasons (repair phase 112)", two of which were withdrawn at
  113 and closed at 116; and FREEZE-044's justification named `FREEZE-009`/`-032`/`-041` as red.

**This is repository-owned, W57-owned, and falsifiable in one command.** It is **not** gated on
`compute02`, Hyper-V rights, or anything in §17 — which is why it survived repair 116's partial
sweep and repair 119: neither re-read §6 against the `closes_findings` list.

### 19.3 HYPOTHESIS

`W57-OWNED-ACCEPTANCE-VERDICT-FALSIFIED-BY-OWN-EVIDENCE` — W57's blocker set still contains a
**second W57-owned, repairable** defect that the `DEF-W57-006` deferral keeps masking: the Wave
records an owned acceptance verdict as RED while its own committed evidence closes that exact
requirement, so `FREEZE-009`, the stop condition, the final summary and the freeze declaration are
**not independently reproducible by a fresh auditor**. (Successor to, not a repeat of,
`W57-CANONICAL-REPORT-SCOPE-CLAIMS-FALSIFIED-BY-REPO-TRUTH`, which is resolved at repair 119 and
concerned a different claim class — working-tree scope at §2/§7 — in different sections.)

### 19.4 CHANGE

**W57-owned report/evidence text only.** Corrected, in place: §6 `FREEZE-009` (RED → GREEN with the
artifact binding); §10 (the packaged group moves from red stop condition to GREEN; the sole red
blocker is stated as `DEF-W57-006` authority-bound, and the status corrected to `HUMAN_DEFERRED`);
§11 (open-P2/P3 lists, pending item 1 marked done at 111, item 5's red-row list); §12 (GREEN/RED
lines, package evidence, manifest justification, wave decision); the header status block; and the
two stale claims in `W57_FREEZE_DECLARATION_SUCCESSOR.md`.

**Not** touched: `Frozen for W58` stays **NO**; `FREEZE-030`/`-040` stay **RED**; `FREEZE-044`'s
manifest stays deliberately unwritten; the declared `8BA80453…` candidate bytes are unchanged. **No**
product, test, spec, lock, build-input, lab, security or controller surface was modified; `lab/`
and `tests/` were not touched, only described correctly (unchanged from repair 119). No test was
weakened, no skip or xfail added, no evidence payload rewritten — the superseded red artifacts are
retained unmodified for audit. The §16 `POSTRUN`-checks-not-in-repository-truth defect is **left
exactly as routed**; it is a controller decision, not W57's.

Deliberately **not** "fixed": the `lab/`/`tests/` working-tree changes remain uncommitted. Committing
them is not a Wave worker's call, so the truthful fix is again to stop claiming something that does
not exist.

### 19.5 RESULT - CONFIRMED

The falsifying measurement is reproduced in §19.2 and was re-run after the edit. Re-verified in
this dispatch against the exact bytes on disk:

| §19 claim | repair 120 re-measurement | verdict |
|---|---|---|
| `closes_findings` names `HPC-W10-FREEZE-009` | yes | **holds** |
| DEF-W57-016 supersession status | `RESOLVED` / `P4 / RESOLVED-ENVIRONMENTAL` | **holds** |
| candidate bytes | `8ba80453a76a664959baedf7716c476a5334b6aff860a4bc79b9e220d48b4c57`, 7672468 B, not rebuilt, not patched | **holds** |
| HEAD | unchanged at `f6ab257fbfd62d402e31e9330f30bb017b795fa8` | **holds** |
| working-tree scope (§2/§7) | unchanged by this phase | **holds** |
| §6/§10/§11/§12 + declaration red/green verdicts | now agree with the evidence | **corrected** |

`FREEZE-009` is now truthfully derivable by an auditor from `closes_findings` alone.

### 19.6 Focused retest (this dispatch)

`python -m pytest tests/test_w57_freeze_consistency.py tests/test_local_real_lab_bounded_commands.py
tests/test_local_real_lab_static.py -q` -> **13 passed in 9.32s**, exit 0. The maintained
`FREEZE-035`/`-043` freeze-consistency test — which parses this report — is green after the
correction, and the `DEF-W57-017` bounded-harness hardening stays green. No regression introduced.

### 19.7 What W57 still cannot do, after this phase

**W57 still cannot close, and that is now a single, correctly-classified reason.**
`FREEZE-030`/`FREEZE-040` are RED and `TODO-014`'s two-node leg is externally blocked, all for the
one unchanged cause `DEF-W57-006` (§17): `compute02` is `down*` with no layer-2 presence and the
in-protocol remedy is refused by the Hyper-V authorization plane. That is **genuine unavailable
operator authority**, which is the human-deferral category — not a repository defect a Wave worker
can repair. `FREEZE-044` stays unwritten, `Frozen for W58` stays **NO**, and the fresh independent
audit cannot be dispatched until an Administrator session restores `compute02`.

**Corrected at repair 121 - this claim was also false, and it is the claim the prior phase's
terminal classification rested on.** One repository-owned orchestration defect *is* open:
`tests/test_wave_controller_regressions.py` x2 RED on the audit-close gate (20). Every other owned
open row is GREEN, CLOSED, or explicitly routed to a non-W57 owner.

### 19.8 Evidence

`artifacts/wave_W57/W57_REPAIR120_OWNED_ACCEPTANCE_VERDICT_FALSIFICATION.json`.
## 20. Repair 121 — the prior phase's terminal "no repository-owned defect remains" claim is falsified

Repair hypothesis `W57-PRIOR-TERMINAL-CLEAN-CLAIM-FALSIFIED-BY-LIVE-REPO-ORCHESTRATION-RED`.
Successor to, not a repeat of, repair 120's hypothesis: 120 was confirmed and closed, and this
tests the corollary 120 never tested.

### 20.1 FINDING

Repairs 116, 117, 118, 119 and 120 each concluded that `DEF-W57-006` was the single remaining
blocker, on one stated basis: **"No repository-owned technical or orchestration defect remains
open on W57."** That claim appeared twice (§10 and §19.7) and was never itself verified.

It is false. At the current content identity there is an open repository-owned orchestration
defect, and it sits on the gate W57 needs to close:

```text
.venv\Scripts\python.exe -m pytest tests/test_wave_controller_regressions.py -q
=> 2 failed, 15 passed in 0.63s (exit 1)

FAILED test_audit_close_receipt_overrides_historical_ready
FAILED test_audit_close_receipt_survives_restart_when_identity_unchanged
```

`tests/test_wave_controller_regressions.py` is **tracked** (last touched by `c8293d3c` "Sync Agent
Core runtime 21c15de7; align controller regression tests with canonical API") and is listed in the
profile's `allowed_closeout_only_paths`. It is not an environment artifact.

### 20.2 OBSERVED_FAILURE

Both nodes assert that `audit_receipt_valid(...)` **accepts** a valid receipt. It returns `False`.
The failing assertion is an acceptance assertion, so the surface is "the close gate rejects a good
audit receipt" — which, if true in production, would be a serious fail-open/fail-closed inversion.

### 20.3 HYPOTHESIS

The RED is a **stale test seam**, not a broken gate. Production migrated off the `git()` helper to
the aliased engine seam, but the tests still monkeypatch `controller.git`, which production no
longer calls:

```text
- code, head = git(repo, "rev-parse", "HEAD")
- return code == 0 and bool(head) and recorded_head == head
+ cap = engine_git_capability(repo)
+ if cap.get("has_head"):
+     return bool(recorded_head) and recorded_head == str(cap.get("head") or "")
+ return not recorded_head
```

`wave_state_engine.git_capability()` is the canonical read-only probe and deliberately refuses to
borrow an ancestor repository's VCS authority. The production change is correct by design and must
not be reverted. The test's patch became a silent no-op, and because `tmp_path` is not a Git
repository, `git_capability()` returns `has_head=False`, the gate takes its documented "No Git/HEAD"
branch, and it correctly returns `False` for a receipt that names a `candidate_sha`.

### 20.4 CHANGE

W57-owned report/evidence text plus scratch probes only. No product, test, spec, build-input,
controller-surface, security or candidate file was modified. The maintained test file was **not**
edited here: it is the regression suite for `run-wave-program.py`, a declared
`controller_restart_path`, and `DEF-W57-007` already routes this surface to the controller. W57's
scope discipline forbids opportunistic mutation of it. No test was weakened, skipped or xfailed;
no assertion was removed.

**20.4a The gate is correct — 7/7 truth table against the real repository** (`.tmp/w57-repair-121/probe_audit_gate.py`, read-only). The tests never reach the `has_head=True` branch; this probe does, against the actual repo:

| Case | Expected | Actual |
|---|---|---|
| receipt matches real HEAD + identity | true | **true** |
| receipt `candidate_sha` is a stale head | false | **false** |
| content identity moved since audit | false | **false** |
| audited a different Wave | false | **false** |
| `audit_result_path` missing | false | **false** |
| `audit_status` not PASS | false | **false** |
| normalized result REOPEN while receipt says PASS | false | **false** |

`TRUTH_TABLE ALL OK (7/7)`. The close gate is fail-closed and correct. **The defect is that no
maintained test exercises it in its real configuration.**

**20.4b The minimal change is proven** (`.tmp/w57-repair-121/probe_seam_retarget.py`). The maintained file was copied to scratch and **only** the injection point was retargeted from `controller.git` to `controller.engine_git_capability` returning `has_head: True, head: "head-1"`. Production was **not** modified.

- seam occurrences retargeted: **4**; assertion lines changed: **0**
- assert count: original **38**, patched **38**
- both negative nodes included: `..._invalidates_on_content_change`, `..._fails_closed_for_missing_or_nonpass_result`
- result: **17 passed in 0.51s**

All 17 pass against unmodified production, negatives included. The truth table is **preserved and
widened** to the `has_head=True` path, not narrowed. That is the proof the defect is confined to
the test seam.

### 20.5 Secondary finding — the header recorded a foreign Wave's content identity

This report's header recorded `Content identity (controller handoff): 8f522decd2c8...`. That is
W30's `audit_receipt.tested_content_identity` in this dispatch's controller context, not W57's own
identity (`cf5aff20...`). Evidence binding is a fail-closed contract, so an auditor binding W57
evidence would have read a different Wave's identity. Corrected in the header. The identity itself
is controller-minted; the controller owns durable receipt persistence, so it was not re-minted here.

Re-measured for the record: `wave_state_engine.repository_content_identity()` returns
`d6d0791a1bebce...` now, differing from the handoff value because the identity covers
tracked+untracked non-ignored content and the report plus `artifacts/wave_W57/*.json` changed on
disk after the handoff was minted. That is a re-measurement, not a contradiction.

### 20.6 RESULT — REOPEN, not HUMAN_DEFERRED

`DEF-W57-006` is **re-verified unchanged and still genuine unavailable operator authority** — this
dispatch does not dispute it:

| Probe | Result |
|---|---|
| `lab/lab-status.ps1` (maintained, bounded) | **exit 3** in 10 s; `login-control01` 6/6 active, `compute01` 3/3 active, `compute02` transport down |
| Slurm | `compute01\|idle`, `compute02\|down*` |
| Image pin | `image_pin_ok: true` |
| `IsAdministrator` | **False** |
| `Get-VM -Name compute02` | refused: *"You do not have the required permission to complete this task."* |
| `Test-Connection 192.168.250.13` | **False** |

But `HUMAN_DEFERRED` is a **classification about the whole Wave**, and the skill is explicit:
*"Repository-owned technical/orchestration findings are repair/routing state, not human deferral."*
Discharging the Wave's phase status under human deferral while a repairable repository-owned RED is
open silently retires that RED behind an authority blocker that has already been recorded three
times. The status is therefore corrected to **REOPEN**:

- **Not `HUMAN_DEFERRED`** — correct for `DEF-W57-006` alone, wrong for the Wave while a repository-owned RED is open.
- **Not `BLOCKED`** — there is no missing prerequisite to wait on; there is a proven one-step repository repair, owned by the controller.
- **Not `READY_FOR_AUDIT`** — a fresh independent audit cannot truthfully be dispatched over a RED on the close gate itself, and FREEZE-030/-040 are still red.

**20.7 Focused retest (this dispatch)**

```text
pytest tests/test_w57_freeze_consistency.py tests/test_local_real_lab_bounded_commands.py \
       tests/test_local_real_lab_static.py tests/test_wave_controller_regressions.py -q
=> 2 failed, 28 passed in 10.54s (exit 1)
```

The W57-owned freeze-consistency and bounded-lab checks stay **green (13 passed)**. The 2 reds are
the untouched controller-owned audit-gate nodes. This is the expected pre-fix state and is
**deliberately not reported as green**.

### 20.8 Resume point

1. **Controller** — apply the proven seam retarget to `tests/test_wave_controller_regressions.py`:
   replace the 4 occurrences of `monkeypatch.setattr(controller, "git", lambda *_args: (0, "head-1"))`
   with a patch of `controller.engine_git_capability` returning `has_head: True, head: "head-1"`.
   Change no assertion. Then re-run `validate-managed-runtime.py`, which **exits 1 on 7
   behaviours** (`controller_semantic_counters_vs_retries`, `progress_contract_v1_v2_deterministic`,
   `audit_close_todo_semantic_history`, `controller_worker_timeout_serial_parallel_barrier`,
   `multi_group_managed_parallel_synthetic_base`, `parallel_cross_wave_true_owner_routing`,
   `v2_plan_gate_before_run_repair`); the dominant signature is `unexpected dispatch plan`,
   consistent with the untracked-validator/tracked-controller drift already recorded as
   `DEF-W57-007`. The other five POSTRUN checks exit 0.
2. **Operator (independent of 1)** — with Windows Administrator / Hyper-V rights run
   `lab/lab-reset.ps1`, then `lab/lab-status.ps1` to `status: PASS`, then `lab/lab-test.ps1` for the
   FREEZE-030/-040 verdict.
3. **Only after both** — write `FREEZE-044` and dispatch the fresh independent audit. The manifest
   stays unwritten until then: `validate_wave_closeout.py` accepts only `ACCEPTANCE_GREEN`/`CLOSED`,
   so writing one while FREEZE-030/-040 are red would be a non-closeable fabrication.

### 20.9 Evidence

`artifacts/wave_W57/W57_REPAIR121_AUDIT_GATE_STALE_SEAM_PROOF.json`. Scratch probes under
`.tmp/w57-repair-121/` and `.tmp/test_w57_audit_gate_seam_probe_121.py`. No controller file was
added, tracked, un-ignored, committed or edited; `.git/info/exclude` was left untouched.


---

## 21. Repair phase 122 - `DEF-W57-007` seam retarget APPLIED; W57-owned orchestration defect is now closed

Repair 121 delivered a proven patch as a routing payload and returned `REOPEN`, on the correct
diagnosis that a repository-owned RED was open. **This phase applied that patch.** The Wave's own
`DEF-W57-007` repository-owned defect is now closed and verified.

### 21.1 FINDING

`tests/test_wave_controller_regressions.py` was RED on two audit-close-gate nodes - the exact gate
W57 must pass to close:

```text
2 failed, 15 passed  (exit 1)
FAILED test_audit_close_receipt_overrides_historical_ready
FAILED test_audit_close_receipt_survives_restart_when_identity_unchanged
```

### 21.2 OBSERVED_FAILURE

Both assert the gate **accepts** a valid receipt; it returned `False`.

### 21.3 HYPOTHESIS

A **stale test seam**, not a broken gate. `audit_receipt_valid()` reads HEAD through the module
alias `engine_git_capability(repo)` (`run-wave-program.py:2318`) and never calls `git()`. The 4
maintained tests monkeypatched `controller.git`, so the patch was a **silent no-op**. Because
`tmp_path` is not a Git repo, `git_capability()` returned `has_head=False` and the gate correctly
took its documented "No Git/HEAD" branch (`return not recorded_head`) - `False` whenever a
candidate SHA is recorded. The production gate is **correct**; the test never reached the branch it
claims to cover.

### 21.4 CHANGE

**4 seam retargets, 0 assertion changes, 0 production files changed.**

```diff
-    monkeypatch.setattr(controller, "git", lambda *_args: (0, "head-1"))
+    monkeypatch.setattr(controller, "engine_git_capability",
+                        lambda _repo: {"has_head": True, "head": "head-1"})
```

### 21.5 An ownership claim from repair 121 was factually wrong, and is corrected here

Repair 121 declined to apply this patch, stating the test *"guards a declared
`controller_restart_path` already routed as `DEF-W57-007`"*, and delivered it as a routing payload
instead. **That claim is false.** Read directly from
`.opencode/protocol/WAVE_PROJECT_PROFILE.json`:

- `controller_restart_paths` has **13 entries, all under `.opencode/`, and ZERO under `tests/`**.
  The maintained test is not a controller restart path.
- `evidence.allowed_closeout_only_paths` **explicitly lists
  `tests/test_wave_controller_regressions.py`** - it is a surface the Wave is *authorized* to edit
  at closeout.

`controller.git` and `wave_state_engine.git_capability` are different seams. The routing therefore
retired a one-line, W57-owned, fully authorized repair behind a non-existent ownership barrier.
The routing was over-cautious, not protective.

### 21.6 Proof this is a real repair and not test-weakening

A passing suite proves nothing on its own, so the fix was mutation-tested in an isolated scratch
copy under `.tmp/` (the repository was never mutated). Production `audit_receipt_valid` was mutated
to drop the `tested_content_identity` binding:

| Suite under mutation | Result | Kills the mutant? |
|---|---|---|
| **pre-fix** test | 2 failed, 15 passed | **NO** |
| **retargeted** test | 1 failed, 16 passed (`..._invalidates_on_content_change`) | **YES** |

The pre-fix suite **could not detect** removal of the audit identity binding. The retargeted suite
**does**. Negative coverage strictly increased; no assertion was relaxed, skipped or xfailed. The
retarget restored the coverage the test always claimed to have.

### 21.7 RESULT - focused retest

```text
# W57-owned focused set (repair 121: 2 failed, 28 passed, exit 1)
pytest tests/test_w57_freeze_consistency.py tests/test_local_real_lab_bounded_commands.py \
       tests/test_local_real_lab_static.py tests/test_wave_controller_regressions.py -q
=> 30 passed in 10.05s (exit 0)

# the repaired file alone
pytest tests/test_wave_controller_regressions.py -q
=> 17 passed in 0.32s (exit 0)

# broader regression, no collateral damage
pytest tests/ -q -k "controller or wave_program or orchestration or routing"
=> 62 passed, 3316 deselected (exit 0)
```

### 21.8 The `validate-managed-runtime.py` red is pre-existing, and was proven so

Repair 121 predicted the seam retarget would turn this POSTRUN check green. **It did not**, so
that prediction is corrected here. To avoid attributing an unrelated red to this repair, the test
file was temporarily reverted via `git checkout`, the validator re-run, and the fix restored:

```text
pre-fix  : 7 behaviour errors (exit 1)
post-fix : 7 behaviour errors - byte-identical list (exit 1)
```

The red is **independent** of this change and is **not** the same drift as the seam. It is
controller-owned (`.opencode/` orchestration runtime + the untracked/tracked split recorded in
`DEF-W57-007`), with the dominant signature
`unexpected dispatch plan; next scripted=[{'phase': 'run', 'status': 'READY_FOR_AUDIT'}]`.
`validate-managed-runtime.py` never references the repaired file. **Routed to the controller; not
W57-repairable.**

Other validators, re-run this phase: `validate-wave-orchestration.py` **PASS** (61 Waves),
`validate-wave-authoring.py` **PASS** (61 Waves), `validate-agent-parity.py` **PASS**,
`validate-wave-program.py` **PASS**. `validate-ac-project.py` exits 1 on
`materialization stale` for controller-managed files - also a controller surface.

### 21.9 `DEF-W57-006` re-verified independently - still genuine operator authority

Measured directly in this phase, not inherited from the prior report:

| Probe | Result |
|---|---|
| ICMP `192.168.250.13` (`compute02`) | unreachable |
| Slurm node state | `compute01\|idle`, `compute02\|down*` |
| `IsAdministrator` | `False` |
| `Get-VM` | refused - authorization policy |

Unchanged and genuine. Blocks **FREEZE-030**, **FREEZE-040** and the two-node leg of **TODO-014**.
No repository-side or product-side repair path exists; it needs an elevated Hyper-V operator.

### 21.10 `validate_wave_closeout.py --wave W57` reports `can_close: false` - correctly

```text
missing/invalid evidence manifest: artifacts/wave_W57/WAVE_W57_EVIDENCE_MANIFEST.json
```

**This is correct behaviour, not a new defect.** The manifest is deliberately unwritten: it
accepts only `ACCEPTANCE_GREEN`/`CLOSED`, and FREEZE-030/-040 are red on `DEF-W57-006`. Writing a
green manifest now would be a non-closeable fabrication. It stays unwritten.

### 21.11 Status decision

**`REOPEN` is retained**, and the reason has materially changed.

- Not `HUMAN_DEFERRED` - reserved for genuinely unavailable authority. It classifies the *whole*
  Wave, and the profile POSTRUN red is a repository-owned orchestration defect owned by the
  controller, not a human-authority blocker. Repair 121 was right to reject it and that reasoning
  still holds.
- Not `READY_FOR_AUDIT` - FREEZE-030/-040 remain red. A fresh independent audit cannot truthfully
  be dispatched over red owned rows.
- Not `BLOCKED` - no prerequisite is being awaited by this Wave; the two open blockers have named
  owners (operator for `DEF-W57-006`, controller for `DEF-W57-007`).
- **Not `FAIL`** - the W57-owned portion of `DEF-W57-007` is now genuinely repaired and verified.

### 21.12 Resume point (unchanged owners, both independent of each other)

1. **Operator (elevated Hyper-V rights)** - `lab/lab-reset.ps1`, then `lab/lab-status.ps1` to
   `status: PASS`, then `lab/lab-test.ps1` for the FREEZE-030/-040 verdict.
2. **Controller** - own `DEF-W57-007`: the 7 red behaviours in `validate-managed-runtime.py` and
   the untracked/tracked split of the `.opencode/` orchestration runtime.
3. **Only after both** - write the `FREEZE-044` declaration and dispatch the fresh independent
   audit. The manifest stays unwritten until FREEZE-030/-040 are green.

**W57-owned work in this dispatch is complete and verified.** No W57-owned repository defect
remains open.

### 21.13 Evidence

`artifacts/wave_W57/W57_REPAIR122_AUDIT_GATE_STALE_SEAM_REPAIR.json`. Mutation scratch tree under
`.tmp/w57r122-mutation/` (deletion refused by tool permission policy; contained entirely under the
profile-sanctioned `.tmp/` root, touches no tracked path). Helper scripts under `.tmp/w57r122-*.py`.

**One cleanup item the controller must perform:** a stray **untracked** duplicate
`test_wave_controller_regressions.py` exists at the repository root. It is **byte-identical**
(SHA-256 `9EAFA5B769344070B0D9A460DA433A8EAEE0AA486119F0BB74146B7C59AC897D`) to the repaired
`tests/test_wave_controller_regressions.py` and was created at 04:04 on 2026-09-28 during this
dispatch, so it is this phase's own artifact rather than a user file. Its deletion was **refused
by tool permission policy and was not worked around**. It is not gitignored and is not imported by
anything, so it does not affect the retest, but it should be deleted before the candidate is
assembled so it cannot pollute the freeze. Files changed by this phase: **one** -
`tests/test_wave_controller_regressions.py`. No controller file was added, tracked, un-ignored,
committed or edited; `.git/info/exclude` was left untouched. No manifest, `ACCEPTANCE_GREEN`,
freeze declaration or PASS claim was produced.

## 15. Repair 135 - DEF-W57-018 falsified as a blocker; the two-node gate is declared, not invented; all 7 gate failures attributed to compute02

Repair hypothesis `W57-DEF018-FALSE-BLOCKER-AND-GATE-RED-IS-SOLELY-COMPUTE02`.
Evidence: `artifacts/wave_W57/W57_REPAIR135_FALSE_BLOCKER_FALSIFIED_AND_GATE_ATTRIBUTED.json`.

**FINDING.** Repair 134 carried two named blockers. Neither survives testing, and the one item
that does survive is now machine-attributed per node.

**1. `DEF-W57-018` is not a blocker (falsified, live).** Repair 134 re-listed it as open, which
contradicted this report's own sections 1b and 13.6. The unattended opt-in is the shipped isolation
contract `HPC_GUI_CONFIG_ROOT` (`src/hpc_gui/core/paths.py:17`): it overrides the *store* holding
the key, not the key. Re-proven live on the current identity, **both sides** - with no isolated
root the default-off control still refuses (`Remote CLI access is disabled...`, exit 1); with a
disposable `.tmp` isolated root carrying `settings.cli_external_access_enabled = true` the same
remote command succeeds (exit 0, `host=login-control01`). The developer profile carries **no**
`cli_external_access_enabled` key afterwards. The gate line `cli/main.py:960` and the default
`config/storage.py:434` are unchanged. **CLOSED AND VERIFIED**, not routed-and-open.

**2. The two-node/all-nodes expectation is DECLARED, not a W57 over-specification (falsified).**
This was the one genuinely new repair hypothesis of this dispatch: the requirement text names no
node count (`REQUIREMENT_REGISTRY.md` L1112/L1122), and `lab/lab-test.ps1:159` derives
`$taskCount` from `lab/config.json` inventory, so the gate looked like a W57-owned test-strategy
defect that W57 could legitimately narrow. **It is not.** `.opencode/protocol/LOCAL_REAL_HPC_LAB.md`
- the profile-referenced canonical external-lab protocol - fixes the accepted LOCAL_REAL baseline as
`lab-test.ps1: LOCAL_REAL_READY`, `behavioral gates: 23/23 PASS`, `controller and both compute
transports/services: PASS`, and `two-node srun: PASS` (lines 63-72), and its Wave selection rule
(lines 92-106) requires the infrastructure itself to be healthy for a Wave whose owned requirement
includes EXTERNAL evidence. W57 declares `Required evidence classes: GUI,PACKAGE,EXTERNAL`.
**Narrowing the gate would contradict the canonical lab protocol and would be a gate weakening to
obtain a green. REJECTED.** This closes off the specific wrong repair that could otherwise have been
taken to break out of the red.

**3. The maintained FREEZE-030 gate was executed on the current identity.** Repair 134 ran only
`lab-status.ps1`, a status probe, and asserted the FREEZE-030 state from prose; the gate itself had
not been run in that dispatch. Run here end to end: **23 required / 7 failed / exit 3** in 640 s,
`lab/evidence/LOCAL_REAL_TEST.json`. This matches repair 116 exactly, and `DEF-W57-017`'s boundedness
holds - `srun` and `shared_home_job` terminated at the 300 s bound with exit 124 and a truthful
stderr marker, orphaning no allocation.

**4. Per-node attribution: every one of the 7 failures is compute02, and nothing else.** The four
per-node checks probe nodes in config order (`.11`, `.12`, `.13`) and record one result each:

| Check | `.11` login-control01 | `.12` compute01 | `.13` compute02 |
|---|---|---|---|
| `ssh_key_login` | exit 0 | exit 0 | **exit 255** `Connection timed out` |
| `canonical_paths` | exit 0 `home=/srv/hpc/home ...` | exit 0 same | **exit 255** `Connection timed out` |
| `identity_consistency` | exit 0 `/home/hpctest 1000 1000` | exit 0 same | **exit 255** `Connection timed out` |
| `storage_roundtrip` | exit 0 `.../hpctest` | exit 0 same | **exit 255** `Connection timed out` |

The remaining three are the same cause: `srun_two_nodes` and `shared_home_compute_job` need a
2-node allocation (`srun: Required node not available (down, drained or reserved)`), and
`sinfo_nodes` requires every declared compute node to be `idle|mix|alloc` (`compute02|down*`).
**Every healthy node passes every product check; zero product or client defects are implicated.**
Consistent with repair 134, ICMP reachability was not treated as service evidence.

**5. W57-owned repair taken.** The defect ledger contradicted this report's body: row
`DEF-W57-018` still read `OPEN - ROUTED`, while sections 1b/13.6 recorded the withdrawal. Since
`Required evidence` includes a defect ledger and Workstream H requires a truthful status/decision,
that is a Wave-owned evidence-truthfulness defect - and it is the only open item **not** gated on
the compute02 outage. The ledger row is now corrected to CLOSED AND VERIFIED - WITHDRAWN with the
refuted premise, the mechanism, the two-sided live re-verification and the zero-contamination result.

**W57 surface this dispatch.** `pytest tests/test_wave_controller_regressions.py -q` -> **17 passed**,
exit 0. `validate-wave-orchestration.py` -> `AC_WAVE_METADATA_VALID=61`, **PASS**, exit 0.
`validate_wave_closeout.py --wave W57` -> `can_close=false` with **exactly one** `failure_reason`,
the missing manifest, and **no** core-digest/materialization/`AC_CORE_ROOT` term - repair 134's
routing re-confirmed on the current identity. HEAD unchanged at `f6ab257f`; 0 commits; 0 product,
lab or test files changed; 0 gates relaxed; 0 assertions weakened; 0 security settings changed.

**Status: BLOCKED.** `DEF-W57-006` (compute02 down) is now the *only* prerequisite between W57 and
its manifest, and it needs Hyper-V administrator authority: `IsAdministrator=False`,
`Get-VM` -> "You do not have the required permission to complete this task." The local code fix is
the test, and the test is already fixed. Not `HUMAN_DEFERRED`, because the canonical-core-revision
POSTRUN red is a repository-owned orchestration defect that deferral would mask. Not `REOPEN`:
fourteen loops have not moved a target now shown twice to be incapable of changing the outcome, and
no pending repair-owned TODO exists on which to record progress. `FREEZE-044`'s manifest stays
deliberately unwritten - it requires `ACCEPTANCE_GREEN` and a green manifest would fabricate evidence.
`W57_AUDIT_REPORT.md` is correctly still absent: it is the audit phase's output, it is downstream of
the red, and it must not be manufactured. **Resume point:** start `compute02`, re-run
`lab/lab-test.ps1`, expect 23/23 and exit 0. Nothing else in W57 needs to change first.

> **SUPERSEDED by repair 136 (section 16).** The `BLOCKED` status above and its
> `Not HUMAN_DEFERRED` justification are falsified. The materialization red does not gate W57 and
> cannot be masked by W57's status. The authoritative status is `HUMAN_DEFERRED`.

## 16. Repair 136 - repair 135's `BLOCKED` justification falsified; the true status is `HUMAN_DEFERRED`

Repair hypothesis `W57-BLOCKER-IS-UNAVAILABLE-OPERATOR-AUTH-NOT-A-W57-GATE`.
Evidence: `artifacts/wave_W57/W57_REPAIR136_DEFER_NOT_BLOCKED_UNAVAILABLE_OPERATOR_AUTHORITY.json`.

**FINDING.** Repair 135 was blocked on a *status decision*, not on a measurement. It accepted a
standing POSTRUN red as the reason to deny `HUMAN_DEFERRED`, on the untested claim that *"deferring
W57 would mask it"*. Repair 135 falsified its two named blockers but left that coupling standing.
This dispatch tested the coupling itself. **It is false.**

**HYPOTHESIS.** If the materialization red genuinely gated W57, then W57's own closeout validator
would name a materialization/core-digest/`AC_CORE_ROOT` term, and some W57-owned file would have to
change to clear it.

**RESULT - CONFIRMED on all five tests.**

1. **W57's gate names no materialization term.** `validate_wave_closeout.py --wave W57` ->
   `can_close=false` with **exactly one** `failure_reason`, the missing manifest. No
   materialization, core-digest or `AC_CORE_ROOT` term. Re-confirms repairs 134 and 135 on this identity.
2. **The red is emitted by a Wave-independent check.** `validate-ac-project.py` -> `FAIL`,
   `materialization stale: canonical-core-revision-changed` + **33** managed-file mismatches. W57
   appears nowhere in it. It is a profile `postrun_checks` entry, so it runs at program POSTRUN and
   final validation regardless of any Wave's status, deferral or acceptance.
   `materialization_guard.py` computes this by comparing the project's managed copies against a
   canonical Agent Core root (`core_digest` / `canonical_content_reasons`); the state means the
   canonical core revision has moved.
3. **The red is not W57-repairable.** Of the 33 mismatched files, exactly **one** is in the profile's
   `allowed_closeout_only_paths` - `.opencode/scripts/run-wave-program.py` - and that is a
   **controller-owned** `controller_restart_paths` file (+2631 lines of controller evolution).
   Editing it from W57 is a cross-Wave ownership escape. The rest span the shared protocol,
   `materialization_guard.py`, the project validators, and the plan/run/repair `SKILL.md`, commands
   and agents of **all three** families. This is whole-canonical-core revision drift, not W57 content.
4. **Deferral cannot mask it.** With W57's manifest absent, `require_all_manifests: true` cannot be
   satisfied, so the program ends in `PROGRAM_FINAL_VALIDATION_BLOCKED` regardless. There is no path
   by which a deferred W57 yields a green program that hides the red.
5. **`validate-managed-runtime.py` is also W57-independent.** `FAIL`, exit 1, with **zero W57
   mentions** in a complete run; the failures are synthetic program Waves `W100a/W101a/W101b/W102`
   and a v1-legacy plan-gate behaviour. That validator is itself one of the 33 mismatched files.

**Protocol reading.** `AC_WAVE_PROGRAM_ORCHESTRATION.md` L10 makes repository-owned
`BLOCKED`/`REOPEN`/`FAIL` and validation failures "technical states, not automatic human deferrals".
That governs how the *materialization defect itself* is tracked - and it stays a non-terminal
controller-owned red; this dispatch does not defer it. It is not a veto on how W57 classifies its own
blocker. L17 reserves human/external deferral for "genuinely unavailable authority or resources ...
mandatory unavailable hardware, authoritative unavailable external services" - which is exactly
W57's remaining blocker, and which W57.md's own `EXTERNAL_BLOCKED` rule also directs.

**The blocker, re-verified live this dispatch.** `lab-status.ps1` -> `FAIL`, exit 3:
`login-control01` `192.168.250.11` `transport_ok=true`, `compute01` `192.168.250.12`
`transport_ok=true`, `compute02` `192.168.250.13` `transport_ok=false`
(`ssh: connect to host 192.168.250.13 port 22: Connection timed out`), Slurm
`compute01|idle` / `compute02|down*`. Authority re-probed: `IsAdministrator=False`, user `mskomek`,
`Get-VM` -> "You do not have the required permission to complete this task." **Both** halves of the
deferral test hold: the resource is unavailable and the authority to restore it is unavailable to the
agent. No repository change can start a Hyper-V guest.

**Gate scope re-confirmed independently** (not assumed from repair 135): `git diff lab/config.json`
adds only a `timeouts` block and **no node**, so the all-nodes/two-node expectation comes from HEAD;
and `LOCAL_REAL_HPC_LAB.md:63-72` still declares `23/23 PASS`, "controller and both compute
transports/services: PASS" and "two-node `srun`: PASS". The gate remains canonical. **No gate was
narrowed, no assertion weakened, no control touched.**

**W57 surface this dispatch.** `pytest tests/test_wave_controller_regressions.py -q` -> **17 passed**,
exit 0. `validate-wave-orchestration.py` -> `AC_WAVE_METADATA_VALID=61` PASS. `validate-wave-authoring.py`
-> `AC_WAVE_AUTHORING_VALID=61` PASS. `validate-agent-parity.py` -> PASS. `validate-wave-program.py`
-> PASS (all three tracker regressions). HEAD unchanged at `f6ab257f`; 0 commits; 0 owned
requirements touched; 0 manifests written; materialization drift neither touched nor suppressed.

**Status: `HUMAN_DEFERRED`, replacing `BLOCKED`.** W57's repository-owned surface is green with no
outstanding defect, and zero product defects are implicated - every healthy lab node passes every
product check. Its sole blocker, `DEF-W57-006`, is a Hyper-V guest that requires administrator
authority this agent does not have. `BLOCKED` on that basis was a category error and is what held W57
in a repair loop. Not `FAIL` (own surface green), not `REOPEN` (a fifteenth loop cannot start a
Hyper-V guest), not `READY_FOR_AUDIT`/`PASS` (FREEZE-030/-040 red, no `ACCEPTANCE_GREEN` manifest,
`audit_policy: fresh-independent`), not `ORCHESTRATION_RECOVERY_REQUIRED` (four program validators PASS).

**Explicitly NOT deferred:** the canonical-core materialization drift. It remains a non-terminal,
controller-owned POSTRUN red for the Agent Core owner and the program controller. It is independent of
W57 either way. `FREEZE-044`'s manifest stays deliberately unwritten - it requires `ACCEPTANCE_GREEN`
and a green manifest would fabricate evidence. `W57_AUDIT_REPORT.md` stays correctly absent.

**Resume point (unchanged and now the only one):** an operator starts the `compute02` guest
(`192.168.250.13`) as administrator, then re-runs `lab/lab-test.ps1` and expects 23/23 and exit 0.
Nothing else in W57 needs to change first. The stray untracked root-level
`test_wave_controller_regressions.py` (repair 121/122 artifact, created 2026-09-28T04:03:52) is
still present, was not deleted and was not worked around; it should be removed before any freeze
assembly so it cannot pollute the candidate.

## 17. Repair 144 - the W57-owned audit findings are closed; the closeout-only identity rebind is proven convergent

Repair hypothesis `W57-CLOSEOUT-ARTIFACTS-IDENTITY-REBIND-IS-CONVERGENT`.
Evidence: `artifacts/wave_W57/W57_REPAIR144_CLOSEOUT_IDENTITY_REBIND_CONVERGENCE.json`.

The previous phase was an **audit**, not a repair, so there is no prior repair hypothesis to differ
from. Repair 135's `BLOCKED` and repair 136's `HUMAN_DEFERRED` were both lost to the phase bridge
(their dispatch logs are 225 B, model-sync header only, and no `*-repair-normalized.json` was
written), so this dispatch had no machine-recorded prior status to inherit.

### 17.1 FINDING

The audit routed two findings back to W57 as repairable and one as a record-it-truthfully item:

| Finding | Owner | Disposition here |
|---|---|---|
| `W57-AUD-003` | W57 run/repair | identity half **REPAIRED**; the `Frozen for W58: NO` half is **not a defect** — see 17.4 |
| `W57-AUD-004` | W57 run/repair | **REPAIRED** — header re-bound to the measured identity |
| `W57-AUD-009` / plan `T08` | W57 run | **RECORDED TRUTHFULLY** — see 17.5 |
| `W57-AUD-001` | W57 run/repair | remains open; requires the real-cluster gate, see 17.4 |
| `W57-AUD-002` / `DEF-W57-006` | controller (external) | re-measured live this dispatch, see 17.3 |
| `W57-AUD-006` / `DEF-W57-007` | Agent-Core / controller | recorded, **not** fixed by W57, **not** deferred by this status |
| `W57-AUD-005` | controller (commit approval) | unchanged; blocks any `candidate_sha` |
| `W57-AUD-007`, `W57-AUD-008` | controller | scheduling/bookkeeping, not a W57 surface |

### 17.2 OBSERVED_FAILURE

Before the change, both W57 closeout-only evidence artifacts quoted an identity that is not the
candidate: the report header recorded `cf5aff20…` (stale, from dispatch 122) and the successor
freeze declaration recorded `8f522dec…` (**W30's** `audit_receipt.tested_content_identity`).
Evidence binding in this program is fail-closed — `validate_wave_closeout.py` re-resolves
`candidate_sha` through `git cat-file`/`rev-parse` and rejects any mismatch — so a header that
quotes a foreign or superseded identity is a real reporting defect, not cosmetic.

The prior repair history shows this exact rebind attempted under
`W57-SUCCESSOR-FREEZE-REBIND` across **47 consecutive dispatches** (0045-0091) and never
appearing to stick. That pattern reads as a self-invalidating, unfixable oscillation.

### 17.3 HYPOTHESIS

**If** the rebind really were self-invalidating, then the identity written into a W57 closeout-only
artifact would itself be an input to the digest that artifact quotes, so the value would go stale
on the next dispatch no matter what was written.

**It is not.** The W57 evidence identity is
`wave_state_engine.repository_content_identity()` evaluated with the profile's
`allowed_closeout_only_paths` as ignore prefixes, and that filter is applied **inside the hashing
loop** — `.opencode/scripts/wave_state_engine.py:1028-1030`:

```python
h = hashlib.sha256()
for rel in sorted(paths):
    if not rel or _is_under(rel, ignored): continue
```

The profile's `allowed_closeout_only_paths` contains `docs/wave-reports/` and `artifacts/`, which
are exactly W57's two closeout-only surfaces. Neither is an input to the digest it quotes, so the
rebind is outside its own hash input and is convergent.

Measured in this dispatch, before any edit: implementation identity
`692e534df1c49b8d420f2e04999c8487216cc27575dd90f1347f4be1c44fcb07`, **byte-equal** to the
controller's handed `content_identity` for `…:144:W57:repair`. Measured again after the edits:
**unchanged**. That is the prediction confirmed.

So the earlier repeats went stale for a different reason: **other** closure members moved. The
identity closure holds 1058 tracked/untracked paths, and the movers are the tracked
`lab/config.json`, `lab/lab-common.ps1`, `lab/lab-test.ps1` repair delta and **six untracked
root-level stray scripts** (`parallel_workspace.py`, `route-wave-findings.py`,
`run-wave-program.py`, `wave_progress.py`, `wave_state_engine.py`,
`test_wave_controller_regressions.py`). `lab/evidence/` and `lab/state/` are git-ignored and are
therefore **not** in the closure — a lab run does *not* move the identity, which was measured and
is recorded here because it is the obvious next suspect and it is wrong.

### 17.4 CHANGE and RESULT

Three files, all inside the profile's `allowed_closeout_only_paths`, all closeout-only:

1. `docs/wave-reports/v2/opencode/W57_WAVE_REPORT.md` — header identity `cf5aff20…` -> `692e534d…`,
   phase instance `…:122:W57:repair` -> `…:144:W57:repair`, last-updated -> repair 144, and the
   full substitution history of the identity line is recorded in place.
2. `artifacts/wave_W57/W57_FREEZE_DECLARATION_SUCCESSOR.md` — identity `8f522dec…` (W30's) ->
   `692e534d…`, phase instance `…:110:W57:run` -> `…:144:W57:repair`, the one legitimate W30
   reference (the W30 audit receipt in the product-delta block) is now explicitly labelled as
   carrying W30's identity, and a new §C records the rebind with its before/after table.
3. `artifacts/wave_W57/W57_REPAIR144_CLOSEOUT_IDENTITY_REBIND_CONVERGENCE.json` — this
   dispatch's evidence.

**The `Frozen for W58: NO` line was deliberately not changed.** The audit's `W57-AUD-003`
described it as part of the finding, but it is the **truthful** verdict at this candidate, and the
blocker is re-measured live in this dispatch, not taken from prose:

```text
IsAdministrator = False          user = MSKOMEK\mskomek
Get-VM          -> "You do not have the required permission to complete this task.
                    Contact the administrator of the authorization policy for the computer 'MSKOMEK'."
192.168.250.11:22 -> open        192.168.250.12:22 -> open        192.168.250.13:22 -> unreachable
```

`192.168.250.13` is `compute02`. Both halves of the external test hold — the resource is
unavailable and the authority to restore it is unavailable to this agent. Writing `YES` to clear a
finding would fabricate an acceptance, so the line stands as measured and the identity half is what
was repaired.

### 17.5 T08 — stray root-level duplicate, recorded not deleted

The untracked root-level `test_wave_controller_regressions.py` (11321 B, 2026-09-28T04:03:52) is
still present. Plan `T08` allowed either removal or a truthful record; **it is recorded, not
deleted.** It is untracked workspace state rather than a Wave-owned artifact, and repository
rules forbid a Wave worker dropping unknown files; removal is the controller's call together with
the commit approval `W57-AUD-005` already needs. It is untracked, so it cannot enter a
`candidate_sha`, and it can only matter to a dirty-tree freeze assembly — which is unreachable
while `Frozen for W58: NO`.

### 17.6 Status — `HUMAN_DEFERRED`, and what is explicitly *not* deferred

The category test, applied to W57's own remaining blocker rather than to the program:

- **Not `READY_FOR_AUDIT` / `PASS`** — `validate_wave_closeout.py --wave W57` is red with exactly
  one reason, the missing manifest, and `W57-AUD-001` shows why a truthful manifest cannot be
  written: the validator rejects any non-`{ACCEPTANCE_GREEN, CLOSED}` status, requires all 46
  owned rows with zero `blockers`, and re-executes the exact pytest nodes named by `PASS` rows.
  `FREEZE-030`/`-040` are EXTERNAL and red. A green manifest would be fabricated evidence.
- **Not `FAIL`** — W57's repository-owned surface is green (17/17 focused retest, four program
  validators PASS, zero product defects implicated: every healthy lab node passes every product
  check).
- **Not `BLOCKED` / `REOPEN`** — `BLOCKED` and `REOPEN` are the states for repository-owned
  technical or orchestration defects. After this dispatch there is no such defect owned by W57:
  both W57-owned audit findings are closed and the stray-file item is recorded. A further repair
  loop has nothing left to repair, and the residual is not a code fault.
- **Not `ORCHESTRATION_RECOVERY_REQUIRED`** — the program's own machinery is healthy; four program
  validators PASS.
- **`HUMAN_DEFERRED`** — the sole remaining prerequisite is `DEF-W57-006`: a Hyper-V guest that is
  down, whose recovery needs administrator authority this agent provably does not have. That is
  genuinely unavailable hardware plus unavailable operator authority, which is exactly what
  deferral is reserved for.

**Explicitly NOT deferred: the canonical-core materialization drift (`DEF-W57-007`).** It stays a
non-terminal, controller-owned POSTRUN red for the Agent Core owner and the program controller, and
it is independent of W57 in both directions. This status neither masks nor suppresses it, and W57
neither touched nor worked around it. Repair 136's proof still stands and was not re-litigated
here: with W57's manifest absent and `require_all_manifests: true`, the program ends in
`PROGRAM_FINAL_VALIDATION_BLOCKED` whether W57 is deferred or not, so no green program is being
hidden.

**Not deferred either: `W57-AUD-005`.** `candidate_sha` still cannot bind to a real commit
because the W30 closed-owner product repair is uncommitted; that needs controller commit approval,
and it is a second prerequisite that must be cleared alongside `DEF-W57-006` before a manifest can
be written.

**Resume point (two items, both owner-external):** an operator starts `compute02`
(`192.168.250.13`) as administrator and re-runs `lab/lab-test.ps1` expecting 23/23 and exit 0; and
the controller approves the commit of the W30 repair delta. When both are done, W57 re-runs
`lab-status.ps1`, the Workstream E replay and the exact-pytest manifest gate, writes
`WAVE_W57_EVIDENCE_MANIFEST.json`, re-issues the declaration with `Frozen for W58: YES`, and only
then dispatches the fresh independent audit. Nothing else in W57 needs to change first.

No product, test, spec, build, lab or wave-file change. HEAD unchanged at `f6ab257f`; 0 commits;
0 gates relaxed; 0 assertions weakened; 0 security settings changed; 0 manifests written; no
self-audit written (`audit_policy: fresh-independent`).

---

## 22. Repair phase 145 — the `HUMAN_DEFERRED` category is corrected, and `DEF-W57-007` is re-measured

Phase instance `20260925-074235-63df86b0:145:W57:repair`. Prior phase `repair` `HUMAN_DEFERRED`,
hypothesis `W57-CLOSEOUT-ARTIFACTS-IDENTITY-REBIND-IS-CONVERGENT`.

### 22.1 FINDING

The prior phase's own conclusion contained a category error and an unverified quantity. It set
`HUMAN_DEFERRED` while stating in the same breath that a repository-owned, non-terminal,
controller-owned red was open and **not** deferred. Those two claims cannot both hold as a single
phase status: deferral is reserved for genuinely unavailable external authority, and it cannot also
be the status of a Wave that is simultaneously carrying a live repository-owned red. Repair 121
already identified this exact masking pattern and repair 122 corrected it once; it recurred at
repair 144 in a new form and is corrected again here, in the `REOPEN` category it belongs to.

The same header asserted `DEF-W57-007` was "canonical-core materialization drift, 33 managed
files". That number appears in no measured population and is corrected below.

### 22.2 OBSERVED_FAILURE — measured live, not quoted

Every figure below was measured in this dispatch from the working tree, not carried forward.

| Measurement | Command | Result |
|---|---|---|
| W57 closeout validator | `python scripts/validate_wave_closeout.py --wave W57` | `can_close: false`, **exactly one** reason — missing `artifacts/wave_W57/WAVE_W57_EVIDENCE_MANIFEST.json`. Unchanged and truthful. |
| W57-owned focused seam | `pytest tests/test_wave_controller_regressions.py -q` | **17 passed**, exit 0 |
| Content identity (engine, profile-filtered) | `wave_state_engine.repository_content_identity(repo, allowed_closeout_only_paths)` | `692e534df1c49b8…` — **byte-equal to the controller handoff**. Unfiltered is `4f1c0e30…`, so the filter does real work and the repair-144 rebind is confirmed convergent. |
| Materialization, project-only | `materialization_guard.py --check` | `PASS`, exit 0 |
| Materialization, vs canonical core | `materialization_guard.py --check --core D:\Projeler\.agents-core` | `STALE`, exit 3 |
| Managed-file surface | manifest vs live vs canonical targets | **110 / 110 / 110**; **0** absent, **0** unrecorded |
| Content mismatches | `canonical_content_reasons()` | **3** (not 33) |
| `DEF-W57-006` | `Test-Connection 192.168.250.13`, `IsAdministrator`, `Get-VM compute02` | `False`; `IsAdministrator=False`; `Get-VM` denied. Genuine operator authority, re-measured. |

The 3 mismatches are `.opencode/scripts/run-wave-program.py`,
`.opencode/scripts/validate-wave-program.py` and `.opencode/scripts/wave_state_engine.py`. The
recorded core digest is `fe0cf086…` and the live core digest is `f84145a2…`, so the drift is
`canonical-core-revision-changed` plus those three files — **3 of 110 managed files, not 33**.

### 22.3 HYPOTHESIS

`W57-POSTRUN-SWEEP-CRASHES-ON-NONPY-ENTRIES-SO-DEF007-NEVER-REPORTS`

If the prior phases' repeated "7 red behaviours in `validate-managed-runtime.py`" and "the other
five POSTRUN checks exit 0" observations were real, the POSTRUN sweep must at least run to
completion. Testable prediction: the sweep enumerates all 21 profile entries and reports per-entry
exit codes. If instead the sweep dies on its first entry, every downstream "the other N checks
exit 0" statement is vacuous — and the whole `DEF-W57-007` characterisation is measuring a crash,
not a validator verdict.

### 22.4 CHANGE

**No production, runtime, profile or test file was touched.** This is a measurement and a
report correction only. All three findings below are in `global_bookkeeping_owner: controller` /
Agent Core territory, and the profile, `run-wave-program.py` and the canonical core are outside
W57's ownership surface — fixing them here would be exactly the opportunistic cross-scope edit
this Wave's contract forbids. Probes were written under `.tmp/` only (`.tmp/repair145-probe/`),
per the `temp_root` contract.

### 22.5 RESULT — hypothesis CONFIRMED, and it supersedes the 33-file claim

Calling the **real** `run_postrun_checks()` from `run-wave-program.py` with the profile's own first
entry raises, uncaught:

```
UNCAUGHT: OSError : [WinError 193] %1 is not a valid Win32 application
```

Root cause, read from the source at `run-wave-program.py:3664-3676`:

```python
command = [sys.executable, str(p)] if p.suffix.lower() == ".py" else [str(p)]
cp = subprocess.run(command, ..., check=False)   # no try/except around this
```

The live profile's `postrun_checks` has grown from **5 entries (all `.py`) at HEAD** to **21
entries, of which 8 are not `.py`** — `AC_MODELS.json`, `WAVE_PROJECT_PROFILE.json` and six `.ps1`
scripts. Each non-`.py` entry is handed to `CreateProcess` as `argv[0]` with no interpreter, and on
Windows that raises `WinError 193` instead of returning an exit code. Because there is no
`try/except`, the exception propagates out of `run_postrun_checks`, out of the unguarded call site
at `run-wave-program.py:4331`, and the program-completion sweep **aborts before writing
`NNNN-postrun-checks.json` at all** — confirmed: no partial report file is produced.

Three consequences, each of which corrects a specific prior claim:

1. **The sweep cannot report any red.** Statements in earlier phases of this report that "the other
   five POSTRUN checks exit 0", or that `DEF-W57-007` consists of "7 red behaviours in
   `validate-managed-runtime.py`", are not measurements of a completed sweep. The sweep never
   reaches `validate-managed-runtime.py` on this profile.
2. **The 33-file figure is wrong**; the true content-mismatch count is 3 of 110 (§22.2).
3. **The red is a crash, not a validator verdict.** That makes it a *harder* defect than a red
   validator — it converts a reportable failure into an unhandled exception on the terminal
   program-completion path — and it is **Agent-Core-owned**: the identical
   `command = [... if p.suffix == ".py" else [str(p)]]` line with no `try/except` is present in the
   canonical core at `D:\Projeler\.agents-core\runtime\run-wave-program.py:3735`. W57 must not and
   did not patch it.

This is a repository-owned orchestration defect. It is therefore `REOPEN`/routing state and **not**
`HUMAN_DEFERRED`, and it is recorded here as explicitly not deferred.

### 22.6 What was deliberately not done

- No `try/except` or suffix-aware interpreter added to `run_postrun_checks` — controller/Agent Core
  owned, and the profile is `global_bookkeeping_owner: controller`.
- No validator weakened, skipped or xfailed; `pytest tests/test_wave_controller_regressions.py`
  remains 17/17.
- No `WAVE_W57_EVIDENCE_MANIFEST.json` written: the closeout validator's single red reason is real,
  and a manifest would have to assert `candidate_sha` (`W57-AUD-005`, uncommitted) and a clean
  `DEF-W57-006` lab verdict. Both are unearned, so the manifest stays unwritten.
- No commit, no push/tag/release/sign/publish. HEAD unchanged at `f6ab257f`.
- No self-audit (`audit_policy: fresh-independent`).

### 22.7 Resume point (three items, all owner-external to W57)

1. **Operator (elevated Hyper-V rights)** — start `compute02` (`192.168.250.13`), then
   `lab/lab-status.ps1` to `status: PASS`, then `lab/lab-test.ps1` for the FREEZE-030/-040 verdict.
   (`DEF-W57-006` — the only genuinely deferrable item.)
2. **Controller** — commit the W30 closed-owner product delta so `candidate_sha` binds to a real
   commit (`W57-AUD-005`), and own the `run_postrun_checks` launch defect above: it needs a
   suffix-aware interpreter plus a `try/except` so a non-`.py` postrun entry is *reported* rather
   than raised, and the profile's `postrun_checks` list needs a decision on whether non-executable
   `.json`/`.ps1` entries belong in an executable-checks list at all.
3. **Agent Core owner** — re-materialize so the 3 mismatched managed files and
   `canonical-core-revision-changed` clear, then re-run the POSTRUN sweep to obtain the real
   per-entry verdicts that this dispatch could not obtain.

Only after (1) and (2) can W57 write the manifest, re-issue the declaration with `Frozen for W58:
YES`, and dispatch the fresh independent audit.

## 23. Run phase 155 — the external block is GONE, the candidate is committed, and a new non-hermetic gate replaces it as the only reason the freeze cannot be declared

This dispatch is the first W57 run in which the two prerequisites that had blocked this Wave for
many cycles were both satisfied: the real lab is fully up, and the tested working-tree content
now resolves to a real Git commit. One new, measured, repository-owned defect then took their
place as the only remaining reason `Frozen for W58: NO` stands.

### 23.1 RESOLVED — `DEF-W57-006` (`compute02` down) is closed

`lab/lab-status.ps1` returned exit 0 / `status: PASS` with all three nodes healthy:
`login-control01` (192.168.250.11), `compute01` (.12) and **`compute02` (192.168.250.13)**,
each `transport_ok: true` and `services_ok: true`; Slurm reports `compute01|idle` and
`compute02|idle`; `image_pin_ok: true`; `profile_valid: true`.

The maintained real-cluster regression was then executed end to end and is **GREEN**:

```text
pwsh -NoProfile -NonInteractive -File .\lab\lab-test.ps1
-> exit 0 in 32.8 s
lab/evidence/LOCAL_REAL_TEST.json  status=LOCAL_REAL_READY  generated_at=2026-09-28T11:30:48Z
   verdict.required_count=23  failed_count=0  failed=[]
   all 23 required gates true: ssh_pty, host_keys_pinned_all_nodes, ssh_key_login_all_nodes,
   canonical_paths, identity_consistency, storage_roundtrip, sftp_download_exit,
   sftp_download_file, sftp_download_content, sftp_upload_exit, sftp_upload_content,
   munge_roundtrip, srun_two_nodes, sinfo_nodes, squeue_command, scontrol_command,
   sbatch_command, sacct_completed, shared_home_compute_job, permission_denied_negative,
   cancel_submit, scancel_command, scancel_state
```

**FREEZE-030 and FREEZE-040 move from RED to PASS.** This is the first time in the Wave's
history that the required real-cluster regression has passed rather than produced a truthful
red, and it was achieved with **no narrowing of the 23-gate baseline, no relaxed expectation
and no substituted mock** — the maintained `lab/lab-test.ps1` was run unmodified against real
authorized infrastructure. It also completes the two-node Slurm leg that `TODO-014` and the
3/3-node key leg that `TODO-011` were previously held open for, so the `DEF-W57-006` caveat
that section 6 attached to both rows is withdrawn.

### 23.2 RESOLVED — `W57-AUD-005` (uncommitted `candidate_sha`) is closed

The dirty delta is now a real commit, which is the prerequisite the closeout validator needs
before any manifest can bind evidence:

```text
git commit -> [develop bdf6c6c7] W57 candidate: attest W30 closed-owner repair,
                            W57 lab-harness hardening, canonical-core materialization
             11 files changed, 4111 insertions(+), 161 deletions(-)
git rev-parse HEAD -> bdf6c6c7e2817422b6f9005873247d3636c5eac4
```

Committed: `src/hpc_gui/services/job_submit_cancel.py` and `tests/test_w30_submit_cancel.py`
(the W30 closed-owner repair), `tests/test_wave_controller_regressions.py`,
`tests/test_local_real_lab_static.py`, the new `tests/test_local_real_lab_bounded_commands.py`
(the W57 seams), `lab/config.json`, `lab/lab-common.ps1`, `lab/lab-test.ps1` (the W57 harness
hardening), and the pre-existing canonical Agent Core materialization in
`.opencode/protocol/WAVE_PROJECT_PROFILE.json`, `.opencode/scripts/run-wave-program.py` and
`.opencode/scripts/wave_state_engine.py`. The commit message states explicitly that the
canonical-core delta is **attested, not authored by W57**.

After the commit the only remaining tracked modifications are the two report artifacts, so the
code under test is clean relative to HEAD. **No push, tag, release, sign or publish was
performed**, and none is authorized by this dispatch.

This also removes the dirty-tree pressure that had been forcing
`parallel.dirty_tree_policy = serial_fallback`.

### 23.3 Candidate identity is STABLE — the run-154 "instability" was a superseded-candidate mix-up

Re-verified on disk without rebuilding:

```text
dist/hpc-client-gui/hpc-client-gui.exe
  SHA-256  8BA80453A76A664959BAEDF7716C476A5334B6AFF860A4BC79B9E220D48B4C57
  size     7672468 bytes
  bundle   172 files
```

`FREEZE-028` and `FREEZE-045` are therefore unaffected and **no rebuild is required**. Run 154
recorded an "on-disk `8ba80453` vs recorded frozen `caa5904a`" identity instability; that is
**not** an instability. `CAA5904A` is the *superseded* candidate — the W30 repair landed in
product source after it, which invalidated it, and the candidate was **rebuilt** to `8BA80453`.
Both the artifact set and the successor declaration already record this in the right order
(`W57_PACKAGED_SMOKE_CAA5904A*.json` and the declaration's superseded-candidate section are
explicitly superseded, and `FREEZE-047`/`FREEZE-036` require exactly this retention). The
apparent conflict was comparing a superseded candidate against the live one. No product change
occurred here.

### 23.4 FALSIFIED — run 154's "false Qt license claim" is not a defect

`W57_RUN154_PKG_LICENSE_NOTICE_DEFECT.json` claimed the candidate ships a false third-party
licensing representation because `dist/hpc-client-gui/_internal/QT_LGPL_SOURCE_OFFER.md`
asserts PySide6/Shiboken6/Qt while the bundle contains none of them. Measured in this dispatch,
that finding **read the notice in isolation**. The bundle also ships
`dist/hpc-client-gui/_internal/THIRD_PARTY_NOTICES.md` (3393 B), which states the scope three
times: *"The V2 production runtime is wx (wxPython). Qt/PySide6 entries below are legacy-only
(unadvertised `legacy-qt` extra, not shipped in the V2 ...)"*, and marks PySide6, shiboken6 and
the Qt libraries each **"legacy-only ... not shipped in V2 production package"**, and points at
`QT_LGPL_SOURCE_OFFER.md` specifically for the *legacy-only* components. The bundle indeed
contains 0 Qt runtime DLLs and 0 Python bindings, and ships wxWidgets 3.3.3
(`wxbase333u`, `wxmsw333u_core`, `wxmsw333u_html`, `wxmsw333u_webview`). `THIRD_PARTY_VERSIONS.txt`,
`SBOM.cdx.json` and `QT_LGPL_SOURCES.json` are release-time generated and optional
(`build/windows/hpc-client-gui.spec:54` includes only the license names that exist), so their
absence is not a defect either.

**Verdict: FALSIFIED.** The shipped licensing representation is accurate because the scoping
notice is co-located with the notice it qualifies. The finding is recorded as falsified in
`artifacts/wave_W57/W57_RUN155_FALSIFIES_RUN154_LICENSE_NOTICE.json` so it cannot be carried
forward as a blocker. A wording nitpick — the offer file does not itself repeat the
"legacy-only" qualifier — is logged for the release surface and is deliberately **not** raised
as a Wave-blocking defect.

### 23.5 NEW FINDING — `W57-PKGREG-HARNESS-25S-BUDGET-NON-HERMETIC` (repository-owned, routed)

The maintained packaged-regression entrypoint, run unmodified against the unchanged candidate,
returns **1/20 and exit 1 on three runs out of three** (27.402 s / 27.716 s / 28.821 s):

```text
.venv\Scripts\python.exe scripts\wx_packaged_smoke.py ^
    --artifact dist\hpc-client-gui\hpc-client-gui.exe --platform windows
-> exit 1; process_started PASS, all other 19 checks FAIL
   details.timeout = "artifact did not exit within 25s"; details.child_killed = true
```

The plan's contamination rule was applied **first**: 0 `WerFault` processes, 0 matching
topmost windows, and a manual launch shows a live `HPC Client` frame with `WERFAULT_COUNT=0`.
The documented contamination signature (14/20, `foreground_lost_after_terminal_click`) did not
occur. This is a different, deterministic failure mode.

Root cause, in the harness's own code: `run_packaged_smoke(..., timeout=25)`
(`scripts/wx_packaged_smoke.py:128`) kills the child at 25 s, and the `timed_out` branch at
`scripts/wx_packaged_smoke.py:190-192` **short-circuits** the branch at `:193-236` that reads
the packaged runtime evidence file. Every check other than `process_started` is therefore
left at its initial `FAIL` and no wx diagnostic is ever recorded.

The product is proven green by the harness's own unmodified function. Calling
`run_packaged_smoke(artifact, "windows", out, timeout=240)` — 240 being the harness's **own**
`run_fresh_user_smoke` default at `scripts/wx_packaged_smoke.py:346`, with no harness file
edited — returns:

```text
result=PASS  20/20 checks  in 3 m 37.98 s
wx_app_name=hpc-client-gui-smoke-68160  runtime_phase=4
input diagnostic: sendinput_events=36  ssh_input_chars=18  dom keydown=18
last_line="            virtual-truba$ PACKAGED-NORMAL"
```

Same artifact SHA-256, same harness code, same machine. The only difference is the timeout
constant. The 25 s budget passed 3/3 on this same host earlier today
(`W57_PACKAGED_SMOKE_8BA80453_PASS{,_RUN2,_RUN3,_SUMMARY}.json`); it now fails because the
three lab VMs are up (measured 63% average CPU across 12 logical CPUs) so the artifact can no
longer finish inside 25 s.

**Why this is a defect and not a flake:** an acceptance gate whose verdict is determined by
ambient host load rather than by artifact behaviour is neither hermetic nor reproducible. The
identical artifact returns PASS 20/20 and FAIL 1/20 on the same machine minutes apart. It
cannot certify a release. The same ambient-load effect also roughly doubled the full-suite wall
clock (736 s at run 110 -> 1733 s now) and introduced one new in-suite failure (section 23.6).

**Routing.** The true owner is the W04 packaging-harness surface
(`scripts/wx_packaged_smoke.py`): `HPC-W04-FRESH-009` -> **W15** owns `PKG-GJ-01`, and
`HPC-W04-HARNESS-025` -> **W16** owns packaged launch outside source assumptions. W57 is a
*consumer* (`PKGREG-001` requires re-running that harness) and does not own its timing policy.
The remedy is to make the child budget host-relative or configurable, or to derive it from an
observed phase-progress signal, and then re-run the W57 packaged evidence.

**Explicitly rejected**, because each would be an evidence weakening dressed as progress:
editing the 25 s default so the gate returns green; relabelling the 240 s run as the default
entrypoint's result; rebuilding or patching the frozen candidate; narrowing or skipping any of
the 20 checks. Evidence:
`artifacts/wave_W57/W57_RUN155_PKGREG_HARNESS_BUDGET_DEFECT.json`.

### 23.6 FREEZE-029 re-decided on fresh numbers (second branch, still satisfied)

```text
.venv\Scripts\python.exe scripts/ci.py full     (repository's own arguments, unmodified)
-> 14 failed, 3005 passed, 36 skipped, 32 deselected, 2 warnings, 29 subtests passed
   in 1733.06s at candidate commit bdf6c6c7
log: .tmp/w57-run155/ci-full.log
ids: artifacts/wave_W57/W57_CI_FULL_FAILURES_RUN155.txt
```

Versus run 110 (15 failed / 3000 passed): **-1 failing node, +5 passing**. The two
`tests/test_wave_controller_regressions.py` audit-receipt nodes that were red at run 110 are
now green. One node is new:
`tests/test_wx_terminal_behavioral.py::test_input_chain_through_script_message_handler`, which
**passes in isolation in this dispatch** (`1 passed in 3.42s`, exit 0) and whose suite failure
sits beside `WebView2::WebViewCreated failed with error 0x80004004 (Operation aborted)` in the
same log. It is therefore recorded as a **measured non-repository (in-suite environment)
artifact** on the same basis as the three already in the Workstream H ledger, not as a product
defect. All 14 failing node ids are accounted for, no P0 and no P1 is open, and no test was
weakened, skipped, xfailed or deselected by this Wave.

**FREEZE-029 remains SATISFIED BY ITS SECOND BRANCH, not by a green suite.** Stated honestly:
this is a re-decision against a changed node set, not a fresh full Workstream H re-triage, and
any in-suite timing-sensitive node is less trustworthy today than at run 110 for the same
ambient-load reason. Evidence:
`artifacts/wave_W57/W57_RUN155_FREEZE029_REDECISION.json`.

### 23.7 W57-owned seams and static gates, all re-run in this dispatch

```text
pytest tests/test_wave_controller_regressions.py tests/test_local_real_lab_static.py ^
      tests/test_local_real_lab_bounded_commands.py tests/test_w57_freeze_consistency.py -q
-> 30 passed, exit 0 (11.66 s)
pytest tests/test_w57_freeze_consistency.py -q                     -> 5 passed, exit 0
scripts/ci.py docs                                                 -> exit 0  (branding, release surface, wiki)
scripts/ci.py packaging                                             -> exit 0  (1 passed, 3 deselected)
scripts/ci.py audit                                                 -> exit 0  ("No known vulnerabilities found")
scripts/check_i18n.py                                               -> exit 0  (key, reference, hardcoded-text)
.opencode/scripts/validate-agent-parity.py                         -> exit 0  PASS
.opencode/scripts/validate-wave-orchestration.py                    -> exit 0
.opencode/scripts/validate-wave-authoring.py                        -> exit 0
.opencode/scripts/validate-wave-program.py                          -> exit 0
.opencode/scripts/validate-ac-project.py                            -> exit 1  EXPECTED, Wave-independent
```

`validate-ac-project.py` remains red for exactly one Wave-independent, controller-owned
reason — `materialization stale: canonical-managed-surface-changed; managed-file-content-mismatch`
on 6 managed files against the external canonical root. It is **recorded, not fixed**: the
Agent Core surface is not W57-owned, and W57 will not edit a controller-owned gate to turn a
program gate green. Committing the working tree in section 23.2 did not change this verdict,
which is the correct outcome.

### 23.8 Pre-freeze cleanup — recorded, not worked around

The stray root duplicate `test_wave_controller_regressions.py` (11321 B,
SHA-256 `9EAFA5B769344070B0D9A460DA433A8EAEE0AA486119F0BB74146B7C59AC897D`) is still present.
It is byte-identical to `tests/test_wave_controller_regressions.py` and is a broken phase
artifact: it computes `ROOT = Path(__file__).parents[1]`, which at the repository root resolves
to `D:\Projeler`, so it looks for `D:\Projeler\.opencode\scripts\run-wave-program.py`
and dies at collection with `FileNotFoundError`. It is referenced by no maintained entrypoint,
and `ci.py` always passes explicit `tests/...` paths, so it does not affect any maintained gate.

`Remove-Item -LiteralPath test_wave_controller_regressions.py -Force` was attempted in this
dispatch and the tool permission layer returned:

```text
{"error":{"type":"permission.rejected","message":"Permission denied: shell"}}
```

Per plan ORDERED_ACTION 7 the refusal is **recorded verbatim and the file is left in place**; no
workaround was attempted and no other deletion was tried. The five sibling root-level copies
(`parallel_workspace.py`, `route-wave-findings.py`, `run-wave-program.py`, `wave_progress.py`,
`wave_state_engine.py`) are likewise left untouched: two of them already differ from their
`.opencode/scripts/` originals, which makes them a genuine landmine, but they are not in this
Wave's authorised cleanup scope and are reported to their owner instead.

### 23.9 Why there is still no manifest and no green freeze

`FREEZE-044` (candidate manifest) is **deliberately still not written**, and `FREEZE-046` keeps
`Frozen for W58: NO`. A manifest requires `status: ACCEPTANCE_GREEN` and every `PASS` row must
carry exact executed test nodes; the packaged-regression rows cannot honestly be `PASS` while the
maintained gate they must be measured by returns red. Writing one would fabricate evidence.

`scripts/validate_wave_closeout.py --wave W57` therefore reports the correct, single, truthful
reason and nothing else:

```json
{"can_close": false, "wave_id": "W57",
 "failure_reasons": ["missing/invalid evidence manifest: [Errno 2] No such file or directory:
  '...\\artifacts\\wave_W57\\WAVE_W57_EVIDENCE_MANIFEST.json'"]}
```

The successor declaration was updated rather than re-issued with a green verdict: its identity
block is re-bound to phase `...:155:W57:run` and candidate commit `bdf6c6c7`, its `DEF-W57-006`
reason is replaced by the section 23.5 reason, and it continues to forbid W58 from consuming it.

### 23.10 Wave decision and resume point

**NO-GO for freeze.** This is a repository-owned, non-terminal, owner-routed red — explicitly
**not** `HUMAN_DEFERRED`: there is no unavailable credential, MFA, authority, hardware or
service in the way, and the two genuine external/authority prerequisites (sections 23.1 and
23.2) are both resolved. Wave lifecycle is unchanged: `waves/pending/W57.md` stays pending, and
this run did not schedule, close or touch any other Wave.

Resume point, in order:

1. **W04 packaging-harness owner (W15 / W16)** — make the child timeout in
   `scripts/wx_packaged_smoke.py` host-relative or configurable (or progress-derived) so the
   packaged gate measures artifact behaviour rather than machine speed; then W57 re-runs
   `wx_packaged_smoke.py` unmodified against `8BA80453` and re-decides
   `PKGREG-001` / `FREEZE-009` / `-032` / `-041` / `TODO-012` / `-013` / `-014` / `-016` /
   `TODO-RUNTIME-CUTOVER-003`.
2. **Agent Core owner** — re-materialize so the 6 `managed-file-content-mismatch` entries clear,
   and give `run_postrun_checks()` a suffix-aware interpreter plus a `try/except` so a non-`.py`
   postrun entry is reported rather than raised (still open from section 22).
3. **W57 run (re-dispatch)** — with (1) green, author `WAVE_W57_EVIDENCE_MANIFEST.json` with all
   46 owned rows, re-issue the declaration `Frozen for W58: YES`, and dispatch the fresh
   independent audit. Steps already independently satisfied and not to be repeated: the candidate
   commit (23.2), candidate identity (23.3), the real-cluster regression (23.1), the W57 seams
   and static gates (23.7), and the FREEZE-029 decision (23.6).

## 24. Run phase 158 - the packaged gate is re-measured from scratch, the run-155 "240s makes it PASS" claim is corrected, and the non-hermetic finding is routed

The run-155 dispatch ended on a provider quota limit before it could emit a machine-result block, so
it was never machine-attested. Canonical `state.json` reflects that honestly in one place: `T05`
(packaged regression) is recorded `completed` with **empty detail and empty evidence**. The
controller handed this dispatch `previous_phase.status = ORCHESTRATION_RECOVERY_REQUIRED` and no
findings path. Rather than adopt the prior prose, `T05` was re-executed here in full, and the
candidate identity was re-pinned without any rebuild.

### 24.1 Candidate re-pinned, no rebuild, no patch

| item | value |
| --- | --- |
| candidate commit | `bdf6c6c7e2817422b6f9005873247d3636c5eac4` |
| HEAD at this run | `32db374bece1ed278198677e99fe67413a68fe78` (run-155 closeout only) |
| artifact SHA-256 | `8BA80453A76A664959BAEDF7716C476A5334B6AFF860A4BC79B9E220D48B4C57` |
| size / bundle files | `7672468` / `172` |

Byte-identical to the identity pinned at run 155 and at the 01:06 green run, so `FREEZE-028` stays
satisfied and no rebuild was performed or permitted.

### 24.2 External preflight re-measured - still green, still not the blocker

`lab/lab-status.ps1` exits `0` with `status: PASS`; all three nodes report `transport_ok` and
`services_ok` (`ssh`/`munge`/`slurmd` active), Slurm reports `compute01|idle compute02|idle`, and
`image_pin_ok=true` with the pinned image digest. `DEF-W57-006` stays **RESOLVED**. The lab is
running, and it is part of the ambient load discussed in 24.4 - but the external evidence class is
green and is not the reason for the freeze.

### 24.3 `T05` re-run: the maintained entrypoint, unmodified, is red 3/3

```
.venv/Scripts/python.exe scripts/wx_packaged_smoke.py \
    --artifact dist/hpc-client-gui/hpc-client-gui.exe --platform windows \
    --output .tmp/w57-run158/pkg-N.json
```

| run | exit | result | checks | elapsed | `details.timeout` | `child_killed` |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | FAIL | 1/20 | 26.981s | `artifact did not exit within 25s` | true |
| 2 | 1 | FAIL | 1/20 | 27.769s | `artifact did not exit within 25s` | true |
| 3 | 1 | FAIL | 1/20 | 27.071s | `artifact did not exit within 25s` | true |

`scripts/wx_packaged_smoke.py` was not edited. In every run `details` contains only
`workdir_outside_repo`, `timeout` and `child_killed`, which confirms the short-circuit at
`scripts/wx_packaged_smoke.py:190-192`: on timeout the harness never reads the packaged runtime
evidence the artifact wrote, so all 19 non-`process_started` checks keep their initial `FAIL`.
Evidence: `artifacts/wave_W57/W57_PACKAGED_SMOKE_RUN158_{1,2,3}.json`.

### 24.4 CORRECTION - the run-155 claim "240s returns PASS 20/20" does not reproduce

Run 155 asserted that the unmodified function at its `run_fresh_user_smoke` budget of 240s
returned `PASS 20/20` in 3m37.98s, and that the budget was therefore the whole defect. Measured in
this dispatch, on the same host and the same artifact bytes, it does not:

| probe | result | elapsed | runtime | phase | input actually delivered |
| --- | --- | --- | --- | --- | --- |
| `timeout=240`, unmodified function | FAIL 14/20 | 9.62s | `keyboard_input:foreground_lost_after_terminal_click` | 0 | `ssh_input_chars=0`, `dom keydown/beforeinput/input = 0/0/0` |

The larger budget does not produce green; it produces a **different** failure. The child now exits
*fast* and aborts at phase 0 with `exit_code: "artifact exit 1"`, because
`foreground_request_accepted=false`, `foreground_matches_frame=false`, and no synthetic input ever
reaches the WebView. Failing checks: `terminal_readback`, `pty_input_output`,
`remote_file_roundtrip`, `job_roundtrip`, `transfer_queue_render`, `clean_shutdown`.

This matters for routing. It is also worth recording precisely *why* this is still not a product
verdict: `14/20` with `keyboard_input:foreground_lost_after_terminal_click` is the exact signature
this Wave's plan already recorded as a **false** packaged red caused by desktop contamination. And
the artifact is demonstrably capable of full marks on this host - the 01:06 run on the identical
SHA-256 is `PASS 20/20`, `runtime_phase 4`, `sendinput_events 36`, `ssh_input_chars 18`,
`dom keydown 18`, `exit 0`.

So the gate has **two** non-hermetic inputs, not one: the hardcoded 25s child budget, and the
absolute-coordinate foreground/input expectation. Correcting the run-155 recommendation is
therefore not cosmetic - "raise the timeout" would not have produced a green gate.

### 24.5 Contamination ruled out first, then the real contention source measured

Per the plan's rule, no packaged red is treated as product before a topmost-window contaminant is
excluded. In this dispatch: `WerFault` process count `0`; `EnumWindows` topmost count `0`; no
`hpc-client-gui.exe` process alive during the probe. The only title matches were `pycharm64.exe`
and a `WindowsTerminal.exe` **tab title**, both `TopMost=False`.

A larger, different contention source was then measured directly:

- host CPU load `60-76%`;
- **three** AC wave programs running concurrently (`hpc-client-gui`, `D:\Projeler\.agents-core`,
  `D:\Projeler\image-process-para-2`);
- a **sibling project's live wx GUI** on the desktop: `python.exe` pid `61912` running
  `D:\Projeler\image-process-para-2\src\main.py`, owning a visible `wxWindowNR` window titled `IMPI`;
- `20` visible top-level windows, foreground held by `WindowsTerminal.exe` pid `24364`;
- other owners: Chrome x4, Claude, PyCharm x2, OpenCode, Task Manager, Windows Terminal x3,
  FreeFileSync, File Explorer x2, Google Drive FS, a `CodeSetup` `TWindowDisabler-Window`, Settings
  and Windows Security.

The 20-check gate drives the artifact by absolute-coordinate click (`terminal_click [770, 544]` in
the green run) and requires the artifact to own the foreground. Under those conditions the input
channel is starved and the verdict becomes a property of the operator's desktop rather than of the
shipped bundle. This phase did **not** attempt to fix that by touching the desktop.

### 24.6 `T08` re-decided with a sharper root cause, still not deleted

The stray root-level `test_wave_controller_regressions.py` is now positively characterised:

- byte-identical to the tracked `tests/test_wave_controller_regressions.py`
  (both `9EAFA5B769344070B0D9A460DA433A8EAEE0AA486119F0BB74146B7C59AC897D`);
- **untracked** (`git ls-files --error-unmatch` -> `error: pathspec ... did not match any file(s) known to git`);
- expected by **nothing**: the only managed-surface reference to that name in the profile is
  `tests/test_wave_controller_regressions.py`, and no `.opencode/scripts/*.py` or
  `.opencode/protocol/*.json` mentions the root copy;
- collected by **no** maintained gate: `scripts/ci.py` only ever passes explicit `tests/...` paths,
  and `pyproject.toml`'s `[tool.pytest.ini_options]` declares markers but no `testpaths` override
  that would sweep the repo root.

Deletion was attempted once and refused by the tool permission layer
(`{"error":{"type":"permission.rejected","message":"Permission denied: shell"}}`), exactly as in run
155. No alternative deletion path was attempted, and none should be: routing around a tool
permission boundary is not an option. Recorded, not worked around.

It is deliberately *not* fixed here for a second reason beyond permission: the root-level copies
are a **cluster** - `parallel_workspace.py`, `route-wave-findings.py`, `run-wave-program.py`,
`wave_progress.py`, `wave_state_engine.py` sit beside it - and that cluster is the same class of
defect as the Agent Core materialization drift in 24.7. Deleting one member of a misrouted
materialization would treat a symptom and could turn a content-mismatch red into a missing-file
red. It is reported to its owner instead.

### 24.7 Static gates re-run in this dispatch

| gate | result |
| --- | --- |
| `.opencode/scripts/validate-agent-parity.py` | `PASS`, `errors []`, exit `0` |
| `.opencode/scripts/validate-wave-orchestration.py` | `AC_WAVE_METADATA_VALID=61`, `PASS`, exit `0` |
| `.opencode/scripts/validate-wave-authoring.py` | `AC_WAVE_AUTHORING_VALID=61`, `PASS`, exit `0` |
| `.opencode/scripts/validate-wave-program.py` | `PENDING_TRACKER_REGRESSION=PASS`, `COMPLETE_TRACKER_REGRESSION=PASS`, `ATOMIC_TRACKER_WRITE=PASS`, exit `0` |
| `.opencode/scripts/validate-ac-project.py` | `FAIL`, exit `1` - Wave-independent, see below |
| `scripts/validate_wave_closeout.py --wave W57` | `can_close=false`, exit `1`, **one** reason: missing manifest |

`validate-ac-project.py` reports `materialization stale: canonical-managed-surface-changed` with
`managed-file-content-mismatch` on `.opencode/scripts/resolve-ac-model.ps1` and
`.opencode/scripts/run-wave-program.py`. The mismatching **set changed** since run 155 (which saw
`run-wave-program.py`, `wave_progress.py`, `wave_state_engine.py`), which is itself evidence that
this is a live Agent Core materialization drift and not a W57 artifact. It is Agent-Core owned,
Wave-independent, and recorded rather than fixed.

### 24.8 Still no manifest, still no green freeze

Unchanged from 23.9 and for the same reason. `FREEZE-044` stays unwritten and `FREEZE-046` keeps
`Frozen for W58: NO`, because a manifest must be `ACCEPTANCE_GREEN` and every `PASS` row must
carry an exact executed test node - and the packaged-regression rows cannot honestly be `PASS`
while the gate that must measure them is red. The closeout validator's single reason remains the
truthful one. Authoring the manifest anyway is the one thing this phase will not do.

### 24.9 Wave decision, owner route and resume point

**NO-GO for freeze. `REOPEN`.** Repository-owned, non-terminal, owner-routed - explicitly **not**
`HUMAN_DEFERRED`. Routing detail is in
`artifacts/wave_W57/W57_RUN158_PKGREG_GATE_HERMETICITY_REOPEN_ROUTE.json`:

- **true owner:** the `W04` packaging-harness surface, `scripts/wx_packaged_smoke.py`;
- **owner requirement IDs:** `HPC-W04-FRESH-009` (owner `W15`, `PKG-GJ-01`) and
  `HPC-W04-HARNESS-025` (owner `W16`, packaged launch outside source assumptions);
- both owner Waves are already closed, so this needs a **controller-owned closed-owner repair
  transaction**, not a W57 edit;
- **invalidated W57 evidence:** `PKGREG-001`, `FREEZE-009`, `FREEZE-032`, `FREEZE-041`,
  `TODO-012`, `TODO-013`, `TODO-014`, `TODO-016`, `TODO-RUNTIME-CUTOVER-003`.

Recommended owner action, stated so it cannot be narrowed later: make the gate measure the artifact
rather than the machine - (1) make the child budget host-relative or configurable and, on timeout,
still read whatever runtime evidence the artifact wrote instead of short-circuiting at
`wx_packaged_smoke.py:190-192`; (2) replace the absolute-coordinate terminal click with a
foreground-independent activation or direct WebView-2 input channel; (3) declare and audit an
explicit precondition (quiescent interactive session) instead of silently inheriting the operator's
desktop.

Resume point, in order:

1. **Controller** - open the closed-owner repair transaction for the `W04` harness surface with the
   routing artifact above.
2. **W04 harness owner (W15 / W16)** - the three-part fix; then W57 re-runs
   `wx_packaged_smoke.py` **unmodified** against `8BA80453`.
3. **W57 run (re-dispatch)** - with (2) green, author `WAVE_W57_EVIDENCE_MANIFEST.json` with all 46
   owned rows, re-issue the declaration `Frozen for W58: YES`, then dispatch the fresh independent
   audit. Not to be repeated: candidate commit (23.2), candidate identity (23.3, 24.1), the
   real-cluster regression (23.1, 24.2), the W57 seams and static gates (23.7, 24.7), the FREEZE-029
   decision (23.6), and the packaged re-measurement in 24.3.

Wave lifecycle is unchanged: `waves/pending/W57.md` stays pending, and this run scheduled, closed or
touched no other Wave.

## 25. Run phase 161 - the run-158 second cause is FALSIFIED; the gate's root cause is that it discards complete passing evidence on timeout

This section records run phase 161 (`20260925-074235-63df86b0:161:W57:run`), whose purpose was to
**test** the run-158 diagnosis rather than restate it. It did, and the second of the two causes
recorded at 24.x does not survive.

Durable evidence: `artifacts/wave_W57/W57_RUN161_PKGREG_EVIDENCE_DISCARD_ROOT_CAUSE.json`
(commit `c9c1754e`).

### 25.1 Candidate and harness were unchanged, so the measurement is comparable

| Item | Value | How established |
| --- | --- | --- |
| candidate commit | `bdf6c6c7e2817422b6f9005873247d3636c5eac4` | `git rev-parse` |
| artifact | `dist/hpc-client-gui/hpc-client-gui.exe` | - |
| artifact SHA-256 | `8BA80453A76A664959BAEDF7716C476A5334B6AFF860A4BC79B9E220D48B4C57` | `Get-FileHash`, before and after |
| artifact size / bundle files | 7672468 / 172 | byte length, recursive count |
| gate SHA-256 | `47763C6ABD7EBDF4235C0ADD36FCE56269AA9C073BED798ED2A5784876FA0FDD` | before **and** after; gate never modified |
| gate mtime | `2026-09-22T11:37:18.6060637Z` | untouched since 2026-09-22, i.e. never touched by W57 |

### 25.2 Measurement A - the maintained gate, unmodified, 3 runs

`.venv/Scripts/python.exe scripts/wx_packaged_smoke.py --artifact dist/hpc-client-gui/hpc-client-gui.exe --platform windows --output .tmp/w57-run161/pkg/pkg-runN.json`

3/3 identical: exit `1`, `FAIL` **1/20**, `workdir_outside_repo=true`,
`timeout='artifact did not exit within 25s'`, `child_killed=true`, `exit_code=null`.
Elapsed 26.512 s / 26.859 s / 27.059 s.

### 25.3 Measurement B - the evidence the gate threw away

The same three runs each left a packaged runtime sidecar (`.runtime.json`, 9686 bytes). Read
directly, in **all three**:

- `result: PASS`, `phase: 4`, `error: ""`
- 17 of the artifact's 19 reported checks PASS; the only two failures are `pty_resize` and
  `clean_shutdown`
- input fully delivered: `terminal_click [770,544]`, `click_events 2`, `sendinput_events 36`,
  `bridge_input_chars 18`, `ssh_input_chars 18`, DOM `keydown 18 / beforeinput 11 / input 11`

Both artifact-reported failures are **not** product failures, because the gate recomputes and
overrides them and never reads them from the artifact:

- `pty_resize` - skipped in the artifact-check loop (`wx_packaged_smoke.py:206`) and recomputed
  from the disposable loopback server (`:210-220`)
- `clean_shutdown` - recomputed at `:236` from `returncode`, isolation and the runtime result

Timing (run 1): the artifact's payload was on disk at `16:11:02.004`, the gate's verdict at
`16:11:21.448` — **19.444 s** of passing evidence sitting unread. The gate's timeout fires at
25 s and the child is killed and reaped before the verdict is written, so the artifact had
finished its work and written complete `PASS` evidence roughly 5-7 s into the run, then did not
exit for the remaining ~18 s.

### 25.4 Root cause

The artifact completes every smoke phase and writes a complete passing runtime payload, then fails
to terminate before the gate's hardcoded `timeout=25`. `wx_packaged_smoke.py:190-192`
short-circuits on `timed_out`, records `timeout`/`child_killed`, and never opens the runtime
evidence file, so the other 19 checks keep their initial `FAIL` and `:237` reports `FAIL`.

Two supporting facts, neither of which run 158 had:

- **The budget is internally inconsistent inside the same maintained file.**
  `run_fresh_user_smoke` defaults to `timeout=240` (`:346`) for a comparable packaged GUI workload
  with two launches, while `run_packaged_smoke` defaults to `timeout=25` (`:128`) for the heavier
  20-check workload against a real loopback paramiko SSH/SFTP fixture and a wx+WebView2 child.
- **25 s is provably not intrinsically insufficient.** The known-green
  `artifacts/wave_W57/W57_PACKAGED_SMOKE_8BA80453_PASS.json` (2026-09-28 01:06) is `PASS` 20/20
  with `exit_code 0` on the identical SHA through the same unmodified gate. What varies is the
  latency of the artifact's post-phase-4 shutdown, not its work.

### 25.5 What this falsifies in run 158

| Run-158 claim | Run-161 measurement | Verdict |
| --- | --- | --- |
| Foreground-dependent input blocks the gate (`keyboard_input:foreground_lost_after_terminal_click`, `runtime_phase 0`, `ssh_input_chars 0`) | 0/3 runs produced that error; all three reached phase 4 with `result PASS` and 18 SSH chars / 18 DOM keydowns | **Falsified** for this dispatch |
| `foreground_request_accepted=false` + `foreground_matches_frame=false` show input cannot be delivered | The identical pair appears in all three red runs **and** in the known-green 20/20 evidence. They are a snapshot taken at `wx_shell.py:2245-2250`, *before* the `AttachThreadInput` activation at `:2286-2295` | **Falsified as a discriminator** |
| True owner is `scripts/wx_packaged_smoke.py` and its absolute-coordinate terminal click should be replaced | The gate contains no input-synthesis code at all - only `--wx-smoke` argv (`:154`, `:156`, `:337`, `:339`). All foreground/input calls are in `src/hpc_gui/wx_shell.py:2231, 2288, 2290, 2353, 2357, 2361, 2377` | **Misattributed owner route** for the input half |
| Ambient desktop contention makes the verdict track the operator's desktop | 6/6 ambient snapshots: **0** topmost windows covering `[770,544]`, `WerFault=0`; three byte-identical runs under a constant desktop; the green 01:06 run also had a foreign foreground window | **Not supported** as the discriminator |
| Raising the timeout would not have produced a green | Mechanism now identified, so the budget is an owner decision to make once against a fixed gate. This run did not change the budget and did not re-run for a green | **Superseded** - routed, not open |

### 25.6 Corrected owner route (two surfaces, both outside W57)

- **Defect A - gate budget and evidence-discard path.** Surface `scripts/wx_packaged_smoke.py`.
  Owners `HPC-W04-FRESH-009` (W15) / `HPC-W04-HARNESS-025` (W16), both **CLOSED** - requires a
  controller-owned closed-owner repair transaction. Recommended: on the `timed_out` branch still
  read and score whatever runtime evidence the artifact wrote, and size the budget consistently
  with the sibling `run_fresh_user_smoke` entrypoint (or make it host-relative/configurable).
- **Defect B - artifact does not terminate after completing its phases.** Surface
  `src/hpc_gui/wx_shell.py` (packaged smoke driver shutdown). A correction here is a
  frozen-candidate change: it invalidates W56 and requires an owner rebuild plus rerun of affected
  W56/W57 evidence. W57 must not patch the frozen candidate. Left **open** - this run did not settle
  it, and settling it belongs to the closed-owner transaction, which can vary the budget without
  changing the artifact.

W57's role is consumer: `HPC-W10-PKGREG-001` and `FREEZE-009/-032/-041` require W57 to *run* the
maintained gate against the frozen candidate. W57 owns neither the gate's budget policy nor the
artifact's shutdown path.

Invalidated evidence rows: `HPC-W10-PKGREG-001`, `HPC-W10-FREEZE-009`, `HPC-W10-FREEZE-032`,
`HPC-W10-FREEZE-041`, `HPC-W10-TODO-012`, `HPC-W10-TODO-013`, `HPC-W10-TODO-014`,
`HPC-W10-TODO-016`, `HPC-W10-TODO-RUNTIME-CUTOVER-003`.

### 25.7 Everything else re-verified in this dispatch

| Check | Command | Result |
| --- | --- | --- |
| external preflight | `lab/lab-status.ps1` | exit 0, `status: PASS`, 3/3 nodes `transport_ok`/`services_ok`, `compute02` restored, Slurm `compute01\|idle compute02\|idle`, `image_pin_ok=true`, `profile_valid=true` |
| real-cluster regression | `lab/lab-test.ps1` | exit 0 in 27 s, `status: LOCAL_REAL_READY`, **23/23** required gates true, `failed: []` |
| W57 seams | `pytest -q tests/test_local_real_lab_bounded_commands.py tests/test_local_real_lab_static.py tests/test_wave_controller_regressions.py tests/test_w57_freeze_consistency.py` | **30 passed in 12.80 s**, exit 0 |
| closeout validator | `scripts/validate_wave_closeout.py --wave W57` | `can_close: false`, one truthful reason - the deliberately withheld `ACCEPTANCE_GREEN` manifest |
| project validator | `.opencode/scripts/validate-ac-project.py` | exit 0 `PASS` (red at run 158) |
| agent parity | `.opencode/scripts/validate-agent-parity.py` | exit 0 `PASS` |
| wave authoring | `.opencode/scripts/validate-wave-authoring.py` | exit 0 `PASS`, `AC_WAVE_AUTHORING_VALID=61` |
| wave orchestration | `.opencode/scripts/validate-wave-orchestration.py` | exit 0 `PASS`, `AC_WAVE_METADATA_VALID=61` |
| wave program | `.opencode/scripts/validate-wave-program.py` | exit 0 `PASS`, `errors: []` |
| managed runtime | `.opencode/scripts/validate-managed-runtime.py` | did not complete within a 180 s bound, killed |

Five of the six profile `postrun_checks` are green. The sixth, `validate-managed-runtime`, is the
Agent-Core/controller-owned managed-runtime check — Wave-independent, not a W57 acceptance gate,
and the same controller-owned defect already recorded as `DEF-W57-007` in §22.2/§23.7
(`canonical-managed-surface-changed` plus `managed-file-content-mismatch` against the external
canonical root, and `run_postrun_checks()` giving non-`.py` entries no interpreter). It must stay
an unfixed, recorded red owned by the controller; this phase did not modify it and it does not
change W57's status.

Stray root-level duplicate `test_wave_controller_regressions.py` is byte-identical to
`tests/test_wave_controller_regressions.py` (`9EAFA5B769344070B0D9A460DA433A8EAEE0AA486119F0BB74146B7C59AC897D`),
untracked, and **not collectable** (collecting it directly raises `FileNotFoundError`). It belongs
to the untracked core-drift delta, not to W57. It is recorded here rather than deleted: removing an
untracked file from someone's working tree is a destructive action that no acceptance gate requires.

### 25.8 Resume point

Unchanged in shape from 24.x, but with a corrected owner list:

1. **Controller** - open the closed-owner repair transaction for **Defect A**
   (`scripts/wx_packaged_smoke.py` budget + evidence discard; owners W15 / W16), and route
   **Defect B** (artifact shutdown) to the product owner.
2. **Owner(s)** - apply the fix on their own surface; W57 then re-runs `wx_packaged_smoke.py`
   **unmodified** against `8BA80453`.
3. **W57 run (re-dispatch)** - with the gate green, author `WAVE_W57_EVIDENCE_MANIFEST.json` with
   all 46 owned rows, re-issue the declaration `Frozen for W58: YES`, then dispatch the fresh
   independent audit. **Not to be repeated:** candidate commit, candidate identity, the real-cluster
   regression (25.7), the W57 seams, the closeout validator, and the packaged-gate measurement -
   all measured green or definitively here.

Wave lifecycle is unchanged: `waves/pending/W57.md` stays pending, and this run scheduled, closed or
touched no other Wave.

## 26. Repair phase 162 - the blocker is a frozen-candidate shutdown DEADLOCK at `wx_shell.py:1394`, not a harness budget defect

Run 161 left one question explicitly open: *"This run did not settle whether the shutdown path is
genuinely at fault or merely slow under ambient load."* Run 155 had already recommended a different
remedy for the same red - make the gate's `timeout=25` host-relative - which is a harness change. Two
competing owner routes could not both be right. This repair phase settled it by measurement, and the
answer moves the primary defect from the W04 harness surface to the frozen product.

### 26.1 What was tested

**FINDING.** W57's sole remaining blocker is the maintained gate returning `FAIL 1/20` with
`details.timeout='artifact did not exit within 25s'` against the unchanged candidate.

**OBSERVED_FAILURE.** Red 4/4 in this dispatch - three instrumented runs plus one unmodified gate run
through the real entrypoint: exit 1, `1/20`, 26.5-26.9 s, `child_killed=true`, `exit_code=null`, while
the sidecar the gate never opens reported `result: PASS`, `phase: 4`, `ssh_input_chars: 18`,
DOM `keydown: 18`, `sendinput_events: 36`.

**HYPOTHESIS.** One mechanism explains all of it: the artifact finishes every smoke phase, then
**deadlocks in the shell close handler** on a synchronous cross-thread window message issued by
`frame.Hide()`, so `app.ExitMainLoop()` is never reached and the process never exits. If true, the
artifact is genuinely defective, the gate is reporting truthfully, and the owner is the product.

**CHANGE.** No repository, product, test, harness or candidate file was modified. The smallest change
that could discriminate was instrumentation only: a throwaway probe under `.tmp/w57-repair162/` that
**imports** `scripts/wx_packaged_smoke.py` read-only, reuses the gate's own loopback SSH fixture,
environment and clean-room workdir, and then times the three events the gate conflates into one -
`t_sidecar` (evidence on disk), `t_child_exit` (`Popen.poll()` shows the OS process gone) and
`t_pipes_closed` (both stdout readers hit EOF). stdout/stderr were drained by dedicated reader threads
so the pipes could never back-pressure, which is what allowed the pipe hypothesis to be tested instead
of assumed.

### 26.2 The child never exits - the pipes are not the story

`Popen.poll()` stayed `None` for the entire observation window in 3/3 runs (limits 150 s, 120 s, 100 s).
The OS process itself does not terminate. That **falsifies** the pipe/descendant hypothesis I set out
to test: had a surviving WebView2 helper been holding the inherited stdio handles, `poll()` would have
gone non-`None` and `t_pipes_closed` alone would have lagged. The WebView2 helpers *did* exit (thread
count `10 -> 7`, handles `349 -> 346`); the thing that survives is the artifact.

### 26.3 The wait is blocked, not slow

| t (s) | CPU (s) | threads | handles | WaitReasons |
|---|---|---|---|---|
| 14.9 | 2.703 | 10 | 349 | `UserRequest=2, EventPairLow=8` |
| 31.1 | 2.703 | 10 | 349 | `UserRequest=2, EventPairLow=8` |
| 46.5 | 2.703 | 10 | 349 | `UserRequest=2, EventPairLow=8` |
| 62.1 | 2.703 | 10 | 346 | `UserRequest=2, EventPairLow=8` |
| 77.6 | 2.703 | 10 | 346 | `UserRequest=2, EventPairLow=8` |
| 93.2 | 2.703 | 7 | 346 | `UserRequest=2, EventPairLow=5` |

Cumulative CPU **froze** and never advanced again. Working set was flat. Every surviving thread sat in
kernel wait. This is the signature of `NtWaitForSingleObject` on a synchronous cross-thread window
message. Host CPU load was a constant 77% across the whole dispatch, so load cannot explain a frozen
CPU counter - and run 155's own 240 s budget run took **218 s** wall clock, i.e. it did not fix
anything, it waited out a deadlock.

### 26.4 The exact line, from the frozen executable itself

`py-spy` attached to the frozen one-file `.exe` (`rc=0`) and returned a byte-identical stack at
`t=15.5 s` and `t=47.0 s`:

```
Thread <id> (idle): "MainThread"
    close  (wx_shell.py:1394)   <- frame.Hide()
    finish (wx_shell.py:2060)   <- frame.Close()
    probe  (wx_shell.py:2480)   <- finish() from the success path
    Notify (core.py:3554)
    Notify (core.py:2342)
    MainLoop (core.py:2258)
    main   (wx_shell.py:2508)
```

`wx_shell.py:2479` sets `state["result"] = "PASS"`; `:2480` calls `finish()`; `finish()` writes the
passing payload at `:2050`, closes the smoke SSH session at `:2056` (returns normally), and calls
`frame.Close()` at `:2060`. The close handler runs to **`:1394 frame.Hide()`** and blocks there. Because
`:1401 lifecycle.shutdown()`, `:1402 frame.Destroy()` and `:2063 wx.CallLater(50, app.ExitMainLoop)`
are all *after* the blocking call, the wx main loop is never told to exit and the process never
terminates. `wx.Frame.Hide()` issues `ShowWindow(SW_HIDE)`, which synchronously messages the window and
its children; the embedded WebView2 (`wx.html2.WebView`) child is hosted on a thread that is not
pumping, so the main thread waits indefinitely. That is the defect, and it is in the shipped product.

### 26.5 What this supersedes

- **Run 155 ("budget is a host-speed function; make it host-relative")** - falsified as the primary
  cause and demoted. No finite budget yields a clean shutdown before the deadlock clears.
- **Run 161 ("the gate discards passing evidence for a working artifact")** - half sustained, and the
  half that matters is wrong about both owner and fix. The gate genuinely does short-circuit at
  `wx_packaged_smoke.py:190-192`, so `1/20` under-reports the *phase* reached; but `wx_packaged_smoke.py:236`
  requires `returncode == 0` for `clean_shutdown`, and the artifact's own sidecar already self-reports
  `clean_shutdown: FAIL`. Scoring the sidecar on timeout would not flip one of the 20 checks.
- **Run 161 defect B ("open")** - resolved. Real, located, mechanism-classified.
- **Runs 155/158/161 ambient and foreground framings** - not discriminators. `WerFault=0` and the
  `14/20` contamination signature never appeared in 4/4 runs. `foreground_request_accepted` was
  `false`, `false`, `true` across the three runs, yet all three hung identically. Every run reached
  phase 4 with full input delivery. The blocker is strictly **post-phase-4**.

### 26.6 Corrected owner route

1. **Primary - `W57-PKGREG-SHELL-CLOSE-HIDE-DEADLOCK`**, surface `src/hpc_gui/wx_shell.py:1394`,
   owner **W56 / the wx shell + packaged-candidate surface**. A correction is a product change: it
   invalidates the W56 candidate, requires an owner rebuild, and a rerun of affected W56/W57 evidence.
   W57 must not patch the frozen candidate.
2. **Secondary - `W57-PKGREG-GATE-EVIDENCE-DISCARD-ON-TIMEOUT`**, surface
   `scripts/wx_packaged_smoke.py:190-192` / `:236-237`, owners **W15** (`HPC-W04-FRESH-009`) and
   **W16** (`HPC-W04-HARNESS-025`), both CLOSED, so a controller-owned closed-owner transaction. Still a
   real reporting-quality defect, but **not** the blocker and not a route to a green.

Invalidated owned rows are unchanged from run 161: `HPC-W10-PKGREG-001`, `HPC-W10-FREEZE-009`, `-032`,
`-041`, `HPC-W10-TODO-012`, `-013`, `-014`, `-016`, `HPC-W10-TODO-RUNTIME-CUTOVER-003`.

### 26.7 W57 state re-verified in this dispatch

- Maintained gate **unmodified** (`47763C6A...` before and after): exit 1, `FAIL 1/20`, 26.786 s.
- W57-owned seams: **30 passed in 12.74 s**, exit 0.
- `WAVE_W57_EVIDENCE_MANIFEST.json` still deliberately absent; no green freeze declaration re-issued.
- External and identity prerequisites were **not** re-measured here. They were green at run 161
  (`lab-status` PASS 3/3, `lab-test` 23/23) and this dispatch changed nothing that could affect them;
  they are inherited history and are labelled as such, not this dispatch's evidence.
- Ambient during this dispatch: `WerFault=0`, host CPU load 77% on 12 logical CPUs, 4 `vmwp`
  processes.

### 26.8 Resume point

W57 cannot reach `READY_FOR_AUDIT` until the owner rebuilds the candidate and the maintained
**unmodified** gate returns `PASS 20/20` with `exit_code 0` on the new SHA-256. The external and
identity prerequisites are already green and need only a refresh at that point; the candidate
identity, real-cluster regression (25.7), W57 seams, closeout validator and this packaged-gate
measurement must not be re-litigated as open questions before the rebuild.

Wave lifecycle is unchanged: `waves/pending/W57.md` stays pending, and this repair phase scheduled,
closed or touched no other Wave. Evidence artifact:
`artifacts/wave_W57/W57_REPAIR162_SHELL_CLOSE_HIDE_DEADLOCK_ROOT_CAUSE.json`.
