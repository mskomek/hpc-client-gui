# W12 Wave Report — Real SFTP semantics validation

Wave: `W12`
Canonical report path: `docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA: `0f8902a023bac76071527232c2287af96478ed2b` (== `origin/develop` tip at session start; working tree dirty with pre-existing unrelated changes — all preserved, none touched)
Current HEAD: `0f8902a023bac76071527232c2287af96478ed2b` (no commit made this session; tested tree = HEAD + uncommitted W12 diff below)
Tested implementation state: HEAD `0f8902a0` + uncommitted diff in `src/hpc_gui/services/files_ssh.py`, `src/hpc_gui/wx_shell.py`, new `tests/test_w12_sftp_semantics.py` (+ this report)
Plugin/external repo SHA(s): `D:\Projeler\hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin; no plugin change, no plugin claim)
First started: 2026-09-19
Last updated: 2026-09-19
Session status: READY FOR AUDIT
Wave decision: GO (two in-scope defects closed with real-integration proof; every owned row evidenced; no owned blocker remains; GUI + EXTERNAL classes satisfied by real evidence)

Runtime truth: Python `3.12.4`, wx `4.3.1 msw (phoenix) wxWidgets 3.3.3`, paramiko `3.5.1`.

## Objective

Validate real SFTP CRUD, metadata, round-trip integrity, overwrite/cancel, path and failure semantics with bounded cleanup (Workstream B — SFTP semantics; 15 owned IDs, 0 TODOs).

## Owned scope (15 stable IDs, all MANDATORY REQUIREMENT)

All rows read before implementation (`HPC-W03-SFTP-001..015`, Owning Wave `W12`; `TODO_OWNERSHIP_MAP` owns none to W12). Mandatory source read: `opencode/sources/WAVE_V2_FINAL_03.md` Workstream B §§100–118 + shared execution contract. Live owners inspected before editing: `services/files_ssh.py` (`SSHFilesBackend`), `services/transfer_controller.py`, `services/transfer_session_controller.py`, `services/transfer_mode.py`, `services/sftp_smoke.py`, `services/file_context_actions.py`, `wx_transfer_workspace.py` (conflict dialog + transfers panel), `wx_shell.py` (`_start_file_transfers`/`run_item`), `tests/support/mock_ssh_server.py`. SSH routed to W11, Slurm to W13 — not absorbed.

## Baseline capture (pre-edit)

Main: branch `develop`; HEAD `0f8902a023bac76071527232c2287af96478ed2b` == `origin/develop`; dirty with pre-existing unrelated changes (W04/W08/W11 work, i18n, `test_wave10_release_gate.py`, untracked W03/W04/W08/W09/W11 test files) — preserved untouched. Plugin: `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb`, dirty only with untracked `.github/social-preview.jpg` — untouched.

Narrow pre-edit baseline (`EV-W12-BASE-001`): `test_wave3_remote_sftp_ssh + test_ssh_files_byte_preservation + test_sftp_channel_manager` → **42 passed**, exit 0.

## Discovery pass + WAVE_FINDINGS

Real-lab probes (`EV-W12-BEFORE-001`, scripts outside repo in approved Temp dir, password via `HPC_LAB_PASSWORD` env only) exercised `SSHFilesBackend` against the authorized containerized lab before any edit: all 13 semantic steps work end-to-end (hashes match), but two diagnostic/cancellation gaps reproduced, plus one probe artifact (console-codec UnicodeEncodeError on `print`, not a product failure — re-proven ascii-safe) and one corrected expectation (renaming a chmod-000 directory itself legitimately succeeds — POSIX rename needs rights on the parent, not the object).

| Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Countable fix? | Status |
|---|---|---|---|---|---|---|---|
| `DEF-W12-001` | P1 | SFTP failure diagnostics (`HPC-W03-SFTP-006/012/013`) | `EV-W12-BEFORE-001`: real-lab `rename(missing)` → `FileNotFoundError errno=2 filename=None`; real-lab upload into chmod-000 dir → `PermissionError errno=13 filename=None` | `SSHFilesBackend.rename` and the transfer `sftp.open` paths bypass `_translate_remote_errors`, unlike listdir/stat/download-stat | failure evidence not attributable: user/CLI sees bare `[Errno N] ...` with no path; violates diagnosability | yes → FIX-A | CLOSED |
| `DEF-W12-002` | P1 | wx file-view mid-transfer state + cancel (`HPC-W03-SFTP-014`) | `EV-W12-BEFORE-002`: new regression tests fail pre-fix — backend never receives progress; cancelling progress never fires | `wx_shell._start_file_transfers.run_item` called `files.upload/download(src, dst)` without `progress_cb`; engine cancel is only observed inside the progress wrapper | cancel during a large file-view transfer cannot interrupt it (bytes flow to completion, then mis-reported `cancelled`); panel shows no mid-transfer progress | yes → FIX-B (independent root cause: missing progress plumbing vs missing error translation; different layer) | CLOSED |

Second-defect search (12 dimensions): negative paths — CHECKED (denied/missing/unsupported-op probes + tests); lifecycle — CHECKED (mid-transfer kill, reconnect, cancel); stale state — CHECKED (cancel marks `cancelled`, no stale revival); identity — CHECKED (disposable per-run fixture roots, no cross-talk); concurrency — CHECKED (engine cancel-thread semantics unchanged); boundary — CHECKED (spaces/Unicode/empty-name validation in dialog); capability absence — CHECKED (legacy-backend-no-progress_cb fallback + resume-hidden logic); persistence — N/A (SFTP has no client-persisted state); packaging — N/A with justification (no artifact bound, no build-input change); error visibility — CHECKED (translated errors + errors-tab path); secondary entry — CHECKED (Qt `remote_dir_panel` already forwards `progress_cb`; untouched); adjacent boundary — CHECKED (`upload_with_mode` `.part`+`rename` routes through fixed `rename`).

## Fixes (smallest coherent corrections)

FIX-A (`DEF-W12-001`, file: `src/hpc_gui/services/files_ssh.py` — one root cause, one fix, five adjacent call sites):
- `rename()` wrapped in `_translate_remote_errors(remote_path)` — missing/denied source now carries `.filename`.
- `_download` full + resume `sftp.open` and `_upload` full + resume `sftp.open` wrapped in `_translate_remote_errors(remote_path)`. Local-filesystem calls (`os.makedirs`, local `open`/`getsize`) deliberately left outside so local failures keep local attribution. Resume-download `makedirs` moved ahead of the remote open (behavior-neutral) for the same reason.
- Behavioral contract changed: SFTP rename/transfer failures now report WHICH remote path failed, consistent with listdir/stat.
- Explicitly NOT counted separately: upload-open/download-open wraps are the same root cause in adjacent lines, not independent fixes.

FIX-B (`DEF-W12-002`, file: `src/hpc_gui/wx_shell.py` + `import inspect`):
- extracted module-level `_run_file_view_item(files, item, progress, conflict_decision)` (pure move first, behavior identical) and `_call_transfer_with_progress`, which forwards the engine `progress` as `progress_cb` when the backend signature accepts it (mirrors the `transfer_mode` probing pattern) and keeps the old positional call for legacy backends; closure `run_item` now delegates.
- Behavioral contract changed: wx file-view transfers emit per-chunk progress (panel mid-transfer state) and engine `cancel_all` raises `TransferCancelled` inside the chunk loop, interrupting in-flight transfers instead of running them to completion.
- Independence: different finding, different root cause (unwired progress/cancel plumbing in the wx controller layer vs missing error-translation wrapper in the SFTP backend), different files, separately sensitivity-proven.

Out-of-scope routing: none (no cross-Wave defect). Adjacent notes (reviewed, not changed): `read_text`/`write_text` bare opens are editor paths (W26 owns editor behaviors); `upload_and_rename` has no live callers (CLI/GUI atomic uploads route through the fixed `rename`); `_upload` pre-flight `stat` still swallows `EACCES` into `remote_size=0` but the eventual open error is now translated, so the user-visible failure is correct.

## Requirement → implementation → test → evidence trace

| Owned ID | Verdict | Live owner | Test(s) / proof | Evidence |
|---|---|---|---|---|
| `SFTP-001` whole-contract | VERIFIED | all below | new module (13) + lab matrix | `EV-W12-MATRIX-001`, `EV-W12-EXT-001` |
| `SFTP-002` mkdir | VERIFIED | `SSHFilesBackend.mkdir` | lab matrix step | `EV-W12-EXT-001` |
| `SFTP-003` upload | VERIFIED | `_upload` + FIX-A open wrap | `test_upload_denied_attaches_remote_path` + lab matrix | `EV-W12-MATRIX-001`, `EV-W12-SENS-001`, `EV-W12-EXT-001` |
| `SFTP-004` list/metadata | VERIFIED | `listdir_entries`/`stat_entry` | lab matrix step (name/size/mtime asserted) | `EV-W12-EXT-001` |
| `SFTP-005` download+hash | VERIFIED | `_download` + FIX-A open wrap | `test_download_denied_attaches_remote_path` + lab matrix | `EV-W12-MATRIX-001`, `EV-W12-SENS-001`, `EV-W12-EXT-001` |
| `SFTP-006` rename | VERIFIED | `rename` + FIX-A | `test_rename_missing/denied/success` + lab matrix | `EV-W12-MATRIX-001`, `EV-W12-SENS-001`, `EV-W12-EXT-001` |
| `SFTP-007` overwrite-confirm | VERIFIED | `TransferSessionController` + `wx_conflict_resolver` | `test_conflict_overwrite_replaces_remote_bytes` + GUI-002 + lab matrix | `EV-W12-MATRIX-001`, `EV-W12-GUI-001`, `EV-W12-EXT-001` |
| `SFTP-008` cancel-overwrite | VERIFIED | conflict `cancel` → `TransferCancelled` (backend never runs) | `test_conflict_cancel_leaves_remote_bytes_intact` + GUI-001 + lab matrix (bytes + hash proven intact) | `EV-W12-MATRIX-001`, `EV-W12-GUI-001`, `EV-W12-EXT-001` |
| `SFTP-009` delete | VERIFIED | `remove` (rm -f) | lab matrix step | `EV-W12-EXT-001` |
| `SFTP-010` rmdir | VERIFIED | `remove(recursive)` | lab matrix step (removal verified absent) | `EV-W12-EXT-001` |
| `SFTP-011` spaces+Unicode | VERIFIED | backend (UTF-8 Passthrough) | lab matrix round trip (`sp ace_caf_é_日本語.txt`) | `EV-W12-EXT-001` |
| `SFTP-012` permission-denied | VERIFIED | FIX-A wraps | denied tests + lab matrix (upload/list/rename all `PermissionError filename=True` on real errors) | `EV-W12-MATRIX-001`, `EV-W12-SENS-001`, `EV-W12-EXT-001` |
| `SFTP-013` missing target | VERIFIED | `_translate_remote_errors` | rename-missing test + lab matrix (stat/download/rename all `FileNotFoundError filename=True`) | `EV-W12-MATRIX-001`, `EV-W12-SENS-001`, `EV-W12-EXT-001` |
| `SFTP-014` mid-transfer | VERIFIED | FIX-B + truthful transport errors | `test_run_item_forwards_progress_to_backend`, `test_run_item_cancel_interrupts_inflight_upload`, legacy/unsupported-op guards + lab kill step (`OSError`, no false success) + reconnect coherence | `EV-W12-MATRIX-001`, `EV-W12-SENS-001`, `EV-W12-EXT-001` |
| `SFTP-015` hashes | VERIFIED | `sha256` (remote) + `hashlib` (local) | lab matrix (`local=82f100670e8176a0 remote=82f100670e8176a0 match=True`) | `EV-W12-EXT-001` |

Mocking statement: fakes stand in only for the paramiko SFTP client (rename/stat/open raising the same bare subclasses paramiko raises on the real wire, as verified by `EV-W12-BEFORE-001`) and for the files backend behind `_run_file_view_item`. Real code exercised: full `SSHFilesBackend` rename/transfer error paths, full `_run_file_view_item` dispatch, full `TransferSessionController` conflict engine. What this does NOT prove: real-server errno mapping and real-wire transfers (covered by `EV-W12-EXT-001`, not claimed here).

## EXTERNAL evidence — authorized real lab (`EV-W12-EXT-001`)

Real-lab target per `docs/testing/LOCAL_HPC_LAB.md` + `devtools/lab/docker-compose.yml`: container `hpclab` (image `hpc-client-gui-lab:latest`), remote environment class **local containerized single-node Slurm** (Debian 13 trixie-slim, OpenSSH, Slurm 24.11.5, `debug*`+`short` `idle` on `hpclab`, `slurmctld UP`). Endpoint `127.0.0.1:2222` (loopback-published only), fixture account `hpctest`, auth method **password (fixture)** — passed via `HPC_LAB_PASSWORD` env at runtime, in no file/log/evidence artifact. Provider ID: lab file backend via product `SSHFilesBackend`/`SSHClientWrapper`.

Provenance honesty: the container pre-existed this session (W11 left it `healthy`); it was NOT built by this Wave. Identity verified at evidence time via `docker inspect` (`healthy`) and `sinfo`. Evidence run 2026-09-19 (~19:35+03:00). Client: Windows source runtime, Python 3.12.4, paramiko 3.5.1. Main SHA `0f8902a023bac76071527232c2287af96478ed2b`, plugin SHA `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin).

Script: `C:\Users\mskomek\AppData\Local\Temp\opencode\w12_ext_lab.py` (outside repo, untracked). Exit 0. Result **14/14 PASS**: SFTP-002 mkdir, SFTP-003 upload, SFTP-004 list+metadata, SFTP-005/015 download+hash (`match=True`), SFTP-006 rename, SFTP-007 overwrite-confirm (bytes replaced, hash logged), SFTP-008 cancel-overwrite (backend never invoked, hash intact, engine `cancelled`), SFTP-011 spaces+Unicode round trip, SFTP-012 permission-denied (upload/list/rename all `PermissionError filename=True` against real errors — FIX-A verified on the wire), SFTP-013 missing (stat/download/rename all `FileNotFoundError filename=True`), SFTP-014 mid-transfer kill (`OSError` after 3 callbacks, never false success), STATE reconnect (coherent), SFTP-009 delete, SFTP-010 rmdir.

Cleanup: disposable root `/home/hpctest/.w12-ext-<stamp>` removed and verified absent (`exists → False`); post-run `ls /home/hpctest/` shows no `w12-ext` residue; container left `healthy` (deliberately not torn down — shared pre-existing state). No Slurm job submitted (jobs belong to W13 — not absorbed). One script-expectation correction during the run (renaming a chmod-000 dir itself legitimately succeeds per POSIX; probe narrowed to entries inside the denied dir) — product behavior was correct; recorded honestly above.

## Fix proof chains

Fix ID `FIX-W12-A` / Defect `DEF-W12-001` / Severity P1 / Independent root cause: SFTP mutating paths bypassed the error-translation wrapper (diagnostic attribution missing).
Before behavior/evidence: `EV-W12-BEFORE-001` (real lab: `filename=None` on rename-missing and upload-denied) + `EV-W12-BEFORE-002` (4 DEF tests fail; rename×2 shown failing).
Files changed: `src/hpc_gui/services/files_ssh.py` (rename + 4 transfer-open wraps + resume makedirs reorder). Regression tests: `test_rename_missing_attaches_source_path`, `test_rename_denied_attaches_source_path`, `test_upload_denied_attaches_remote_path`, `test_download_denied_attaches_remote_path`. Sensitivity `EV-W12-SENS-001`: each reverted in isolation → fails for the expected reason (`filename is None`); restored → passes. (One test-design correction: the first download-denied variant passed pre-fix because the stat path was already translated — rewritten to deny at open, the actually-changed line — then properly failed pre-fix.) Negative tests: denied variants + unsupported-op + legacy-backend guards. Narrow suite: new module 13 passed. Broader: 88 + 45 + 211 + 40 passed (below; two flaky occurrences, both green on re-run — see ledger). Runtime/manual: lab probes + 14/14 matrix. Package: N/A (no artifact bound). External: `EV-W12-EXT-001` (FIX-A verified on real wire errors). Residual risk: `_upload` pre-flight stat still swallows `EACCES` into `remote_size=0` — end-user failure is now correctly attributed at open time, so impact is nil; noted for future hardening, not a blocker.

Fix ID `FIX-W12-B` / Defect `DEF-W12-002` / Severity P1 / Independent root cause: wx file-view transfer path never threaded engine progress into the backend (mid-transfer blindness + uninterruptible in-flight transfers).
Before behavior/evidence: `EV-W12-BEFORE-002` (`test_run_item_forwards_progress_to_backend` sees only `[(1, 1)]`; `test_run_item_cancel_interrupts_inflight_upload` DID NOT RAISE).
Files changed: `src/hpc_gui/wx_shell.py` (`import inspect`, `_run_file_view_item`, `_call_transfer_with_progress`, closure delegates). Regression tests: the two above. Sensitivity `EV-W12-SENS-001`: helper body reverted to `method(src, dst)` → both fail; restored → pass. Negative/lifecycle tests: cancel-interrupt, unsupported-op RuntimeError, legacy-backend compat. Narrow/broader suites: same as above. Runtime: lab mid-transfer kill + reconnect coherence. Residual risk: cancelling a wx file-view upload mid-flight can leave a partial remote file at the final name (pre-existing direct-to-final design; CLI uses `.part`+rename). Previously the bytes always landed fully and were then mis-reported `cancelled`; now the transfer genuinely stops — strictly improved, documented, not a blocker.

## Evidence ledger (exact counts)

| Evidence ID | Command | Exit | Result |
|---|---|---|---|
| `EV-W12-BASE-001` | `pytest test_wave3_remote_sftp_ssh test_ssh_files_byte_preservation test_sftp_channel_manager -q` (pre-edit) | 0 | 42 passed |
| `EV-W12-BEFORE-001` | `HPC_LAB_PASSWORD=… python w12_probe.py` + `w12_probe2.py` (real lab, pre-fix) | 0 | gaps reproduced (`filename=None` ×2); hashes match; unicode round trip OK |
| `EV-W12-BEFORE-002` | `pytest tests/test_w12_sftp_semantics.py -q` (pre-fix) | 1 | 4 failed (all DEF regressions), 7 passed |
| `EV-W12-MATRIX-001` | `pytest tests/test_w12_sftp_semantics.py -q` | 0 | **13 passed** (4 DEF-A + 2 DEF-B + happy/negative/compat/REQ + 2 wx GUI) |
| `EV-W12-SENS-001` | per-fix revert → run DEF tests → restore | — | rename×2 + denied×2 + progress×2 **fail pre-fix** for the expected reason, **pass post-fix** |
| `EV-W12-REG-001a` | `pytest test_w12_sftp_semantics test_wave3_remote_sftp_ssh test_ssh_files_byte_preservation test_sftp_channel_manager test_transfer_controller test_transfer_resume_semantics test_transfer_integrity test_transfer_concurrency test_transfer_key_release -q` | 0 on re-run | **89 passed** (see flake note F1/F2) |
| `EV-W12-REG-001b` | `pytest test_transfer_cancel_recovery test_transfer_concurrency test_transfer_key_release test_wx_transfer_conflict_ui test_wx_transfer_ui_lifecycle test_wx_transfer_workspace test_transfer_directory_controllers -q` | 0 | **45 passed** |
| `EV-W12-REG-001c` | `pytest test_w11_ssh_lifecycle test_ssh_directory_listing_wire test_download_cancel_wire test_wx_file_transfer_integration test_local_transfer_gate test_cli -q` | 0 on re-run | **211 passed** (see flake note F3) |
| `EV-W12-REG-001d` | `pytest test_w12_sftp_semantics test_wx_transfer_conflict_ui test_wx_transfer_ui_lifecycle test_wx_transfer_workspace -q` | 0 | **40 passed** |
| `EV-W12-GUI-001` | inside MATRIX: `test_wx_conflict_dialog_cancel_button_returns_cancel`, `test_wx_conflict_dialog_overwrite_button_returns_overwrite` (real `wx.App`+`Frame`, real `EVT_BUTTON` clicks, pumped loop, clean teardown) | 0 | 2 passed |
| `EV-W12-DIFF-001` | `git diff --check` on W12 files; `git diff --stat`; added-line secret scan | 0 | clean; 2 files + new test module; no secrets |
| `EV-W12-EXT-001` | `HPC_LAB_PASSWORD=<fixture-pw-per-LOCAL_HPC_LAB.md> python w12_ext_lab.py` (real lab `hpclab` 127.0.0.1:2222, product backend, isolated known_hosts, disposable fixture root) | 0 | **14/14 PASS**, fixture cleaned + verified, lab left `healthy` |

Flake notes (honest, all green on re-run; none on W12-touched code paths): F1 — one `Windows fatal exception: access violation` in `test_transfer_key_release` (Qt native teardown) in a mixed wx+Qt batch; module passes in isolation (2 passed) and the batch passes on re-run. F2 — one `test_cancel_releases_the_keys…` timing assertion in the same Qt module; passes on re-run (89). F3 — one `test_skipping_a_partial_leaves_it_alone` cancel-race failure in REG-001c first run (210 passed + 1 failed); exact batch re-run → 211 passed. Pre-existing timing/native-teardown sensitivity (LIFECYCLE-NATIVE class), not W12 regressions: the failing paths (`transfer_dialog`, `remote_dir_panel`, download planner) are untouched by this Wave's diff.

New/modified tests: `tests/test_w12_sftp_semantics.py` (new, 13 tests: REQ-SFTP-003/005/006/007/008/012/013/014 coverage + DEF regressions + wx GUI proof). Skipped/xfail changes: none. Test weakening: none.

Evidence classes: `GUI` satisfied by `EV-W12-GUI-001` (real wx event/runtime proof: happy overwrite-click + cancel-overwrite-click + mid-transfer progress/cancel + failure-visibility via engine `failed` state). `EXTERNAL` satisfied by `EV-W12-EXT-001` (authorized real lab, 14/14 PASS, identity + cleanup recorded). Package: N/A with justification (no owned row binds an artifact; no build-input change).

## Test review checklist

- [x] Each counted fix has dedicated regression tests (4 for FIX-A incl. extended open-path scope; 2 for FIX-B) — YES (`EV-W12-MATRIX-001`, `EV-W12-SENS-001`).
- [x] Regression tests failed before the fix / pass sensitivity proof — YES (`EV-W12-BEFORE-002`, `EV-W12-SENS-001` per-fix reverts).
- [x] Negative path covered — YES (denied/missing/unsupported-op/legacy-backend/no-resolver-cancel).
- [x] Stateful/async lifecycle covered — YES (mid-transfer cancel interrupt, cancel-overwrite idempotence, reconnect coherence).
- [x] Behavioral (not existence-only) assertions — YES (filenames, byte equality, hash equality, progress sequences, engine states).
- [x] Mocks limited to legitimate boundaries — YES (paramiko client / backend only; stated non-proofs).
- [x] No unjustified skips/xfails — YES (none added).
- [x] Fixtures isolated; cleanup deterministic — YES (`tmp_path`, disposable remote roots, verified removal).
- [x] Package/external honestly classified — YES (package N/A justified; lab is EXTERNAL, fakes are unit/integration).
- [x] Full impacted slice still passes — YES (88/89 + 45 + 211 + 40; flakes re-run green).
- [x] Future regression would fail the tests — YES (proven by reverts).

## POST_GREEN_REVIEW

- Duplicate path: all live `rename` callers (`SSHFilesBackend.rename`, `transfer_mode._upload_remote` via `files.rename`) route through the fix; `upload_and_rename` has no live callers — recorded, untouched. Qt `remote_dir_panel` already forwards `progress_cb` — untouched, unaffected. ✓
- Alternate entry points (button/double-click/context-menu → `connect_selected` pattern equivalent: upload/download header + toolbar + conflict dialog) share the fixed `run_item`/backend — covered. ✓
- No silent fallback: inspect-fallback is explicit and compat-tested; `TransferCancelled` propagates, never swallowed. ✓
- No stale state after cancel: engine records `cancelled`; reconnect verified coherent on the lab. ✓
- No wrong-identity capture: no session/profile/path capture in the diff. ✓
- No new dead branch; no hardcoded provider behavior; errors claim failure with path. ✓
- Partial-file-on-cancel residual documented (strictly improved vs pre-fix). ✓
- No secret added to source/diff/logs/evidence (added-line scan clean). ✓

## Diff review

`git diff --check` (W12 files): clean. `git diff --stat` (W12 files): `files_ssh.py` (rename + 4 open wraps + resume makedirs reorder), `wx_shell.py` (`import inspect`, `_run_file_view_item`, `_call_transfer_with_progress`, closure delegation), new test module untracked. All other dirty/untracked files are pre-existing and preserved untouched (verified: full `git diff` inspected — unrelated W02/W04/W08/W11 hunks not mine, none modified). No generated/binary noise; no test weakening; no secret. No commit made (report-first; committer decides).

## Open findings

P0: none. P1: none open (both closed). P2: none. P3: none open (upload pre-flight stat swallow noted as future hardening inside FIX-A residual, not a standalone open item).

## Deviations

None — SSH/Slurm scenarios explicitly left to W11/W13; no W13 work started.

## Rollback

Revert `src/hpc_gui/services/files_ssh.py` + `src/hpc_gui/wx_shell.py` hunks and delete `tests/test_w12_sftp_semantics.py`; the six DEF regression tests fail on the reverted tree (proven by `EV-W12-SENS-001`), so rollback is detectable. No remote/persisted state to clean (lab fixture already removed and verified; shared `hpclab` container left running healthy as found; local known_hosts in untracked temp only).

## Resume state

Completed and verified: all 15 SFTP rows; FIX-A + FIX-B with before/after/sensitivity evidence; 13-test suite green; broader slices green (with documented flaky re-runs); GUI proof green (real wx events); EXTERNAL class satisfied by `EV-W12-EXT-001` real-lab run (14/14, fixture cleaned, container healthy); report current.
In progress: nothing. Open P0/P1: none. Open P2/P3: none. Pending tests/evidence: none (fresh-context audit is a separate step; `W12_AUDIT_REPORT.md` to be produced by audit).
Last exact commands run: `pytest tests/test_w12_sftp_semantics.py -q` → 13 passed; broader slices → 89 / 45 / 211 / 40 passed; `HPC_LAB_PASSWORD=<fixture-pw> python w12_ext_lab.py` → 14/14 PASS exit 0; remote cleanup verified absent, lab `healthy`; `git diff --check` → clean.
Next actions: fresh-context `/wave-audit W12`; then W13 may be planned (never auto-started).
Evidence/artifact identities: `EV-W12-BASE-001`, `EV-W12-BEFORE-001/002`, `EV-W12-MATRIX-001`, `EV-W12-SENS-001`, `EV-W12-REG-001a/b/c/d`, `EV-W12-GUI-001`, `EV-W12-DIFF-001`, `EV-W12-EXT-001`; main HEAD `0f8902a0`, plugin `f0abb7e7`.

```text
FIX-A: translate SFTP rename/transfer-open failures with the remote path
DEF: DEF-W12-001 (P1, bare paramiko errors with filename=None)
Root cause: rename() and transfer sftp.open paths bypassed _translate_remote_errors
Before EV: EV-W12-BEFORE-001 (real-lab filename=None) + EV-W12-BEFORE-002 (4 DEF tests fail)
After EV: EV-W12-MATRIX-001 (13 passed) + EV-W12-EXT-001 (real denied/missing errors carry filename)
Regression test: test_rename_missing_attaches_source_path (+ denied/upload/download variants)
Sensitivity proof: EV-W12-SENS-001 (each fails pre-fix for the expected reason, passes post-fix)

FIX-B: forward engine progress into wx file-view backend transfers
DEF: DEF-W12-002 (P1, no mid-transfer progress; cancel cannot interrupt in-flight transfer)
Root cause: run_item dropped progress_cb; engine cancel only observed in progress wrapper
Before EV: EV-W12-BEFORE-002 (only [(1,1)] seen; cancel DID NOT RAISE)
After EV: EV-W12-MATRIX-001 + lab mid-transfer kill/reconnect coherence
Regression test: test_run_item_forwards_progress_to_backend
Sensitivity proof: EV-W12-SENS-001 (helper revert → both fail; restored → pass)

Additional fixes: none beyond FIX-A's same-root-cause open-path wraps (explicitly not counted separately)
Post-green review: PASS (recorded above)
New/modified tests: tests/test_w12_sftp_semantics.py (13 new)
Skipped/xfail changes: none
Package evidence: N/A (justified — no owned row binds an artifact; no build-input change)
External evidence: EV-W12-EXT-001 real authorized lab (hpclab 127.0.0.1:2222, 14/14 PASS, identity + cleanup recorded)
Open P0/P1: none
Open P2/P3: none
Two-fix gate: PASS (W03-specific: two real-integration remediations, non-mock)
Wave decision: GO
```
