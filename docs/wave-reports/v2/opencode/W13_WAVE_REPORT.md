# W13 Wave Report — Real Slurm, failure and cross-protocol state validation

Wave: `W13`
Canonical report path: `docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA: `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb` (current checkout baseline for this repair; working tree dirty with unrelated changes preserved)
Current HEAD: `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb` (no commit made this session; tested tree = HEAD + preserved working-tree changes)
Tested implementation state: current HEAD includes the W13 implementation snapshot in `src/hpc_gui/services/slurm_models.py`, `src/hpc_gui/services/slurm_ssh.py`, and `tests/test_w13_slurm_state.py`; this repair changed evidence/reporting only.
Plugin/external repo SHA(s): `D:\Projeler\hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin; no plugin change, no plugin claim)
First started: 2026-09-19
Last updated: 2026-09-22 (repair cycle 2: REOPEN-W13-001/002 addressed with LOCAL_REAL replay and current identity; no product-code change)
Session status: READY FOR AUDIT
Wave decision: GO (two in-scope defects closed with real-integration proof; every owned row evidenced at requirement-by-requirement granularity; no owned blocker remains; GUI + EXTERNAL classes satisfied by real evidence)

Runtime truth: Python `3.12.4`, wx `4.3.1 msw (phoenix) wxWidgets 3.3.3`, paramiko `3.5.1`, `DEFAULT_GUI_RUNTIME=qt`.

## Objective

Validate real Slurm submit/query/cancel/output plus failure/recovery and cross-protocol state coherency through the application/service path (Workstreams C/D/E; 55 owned IDs, 0 TODOs).

## Owned scope (55 stable IDs)

All rows read before implementation (`HPC-W03-SLURM-001..055`, Owning Wave `W13`; `TODO_OWNERSHIP_MAP` owns none to W13). Mandatory sources read: `opencode/sources/WAVE_V2_FINAL_03.md` Entry criteria, Ownership boundary, Scope, Workstreams C/D/E, Test matrix, Acceptance criteria, Required evidence, Rollback, Handoff to W04. Live owners inspected before editing: `services/slurm_ssh.py` (`SSHSlurmBackend`, `SlurmCommandResult`), `services/slurm_models.py` (`parse_squeue`/`parse_sacct`/`parse_scontrol`/`format_job_details`), `services/slurm_base.py`, `config/system_profile.py` (shipped scheduler commands), `cli/main.py` + `cli/jobs.py` (jobs backend + error mapping), `services/adapter_registry.py`, `wx_jobs.py` (refresh/details/accounting flows), `ui/widgets/jobs_widget.py` (Qt consumer). SSH routed to W11, SFTP to W12 — not absorbed.

## Baseline capture (pre-edit)

Main: branch `develop`; HEAD `0f8902a023bac76071527232c2287af96478ed2b` == `origin/develop`; dirty with pre-existing unrelated changes (W04/W08/W11 file-views/i18n/`test_wave10_release_gate.py` work + untracked W03/W04/W08/W09/W11/W12 test files) — preserved untouched. Plugin: `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb`, dirty only with untracked `.github/social-preview.jpg` — untouched.

Narrow pre-edit baseline (`EV-W13-BASE-001`): `test_slurm_ssh + test_slurm_models + test_slurm_script_parser` → **16 passed**, exit 0.

## Discovery pass + WAVE_FINDINGS

Real-lab probes (`EV-W13-BEFORE-001`, script outside repo in approved Temp dir, password via `HPC_LAB_PASSWORD` env only) exercised `SSHSlurmBackend` against the authorized containerized lab before any edit: full lifecycle works end-to-end (submit job 4 → RUNNING in squeue bytes → scontrol parses → stdout marker fetched → cancel → CANCELLED → sacct records → cleanup verified), but two gaps reproduced:

| Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Countable fix? | Status |
|---|---|---|---|---|---|---|---|
| `DEF-W13-001` | P1 | Slurm list parsing (`HPC-W03-SLURM-013/016/025`) | `EV-W13-BEFORE-001`: squeue bytes contain job 4 RUNNING (`hasjid=True`) but `parse_squeue` returns **0 jobs** | `_rows` unconditionally dropped line 1 assuming a header, while the shipped commands request headerless output (`squeue -h`, `sacct -n -P`) | running jobs invisible in job views; single-job queue reads as empty (stale/masquerading view) | yes → FIX-A | CLOSED |
| `DEF-W13-002` | P2 | Empty-success rendering (`HPC-W03-SLURM-028`) | `EV-W13-BEFORE-001`: `SQUEUE code=0 ... text='[exit=0]'` for a healthy empty queue | `SlurmCommandResult.text` fell through to the failure token when stdout was empty, even on success | users see a pseudo-error `[exit=0]` for "no jobs" (Qt jobs pane, CLI `jobs list`) | yes → FIX-B (independent root cause: result rendering vs parser header assumption; different file) | CLOSED |
| `DEF-W13-003` | P2 | Error-text-as-job phantom rows (`HPC-W03-SLURM-014/025`) | post-probe analysis: `parse_squeue` on multi-line scheduler error text yields a phantom `SlurmJob(job_id='slurm_load_jobs', ...)` | parser accepted any long-enough line as a data row | scheduler failures could display as bogus job rows (Qt `jobs_widget.refresh` parses string API without status) | folded into FIX-A (same function, same parser-robustness root cause; explicitly NOT counted separately) | CLOSED |

Second-defect search (12 dimensions): negative paths — CHECKED (unknown-job, bad-path, nonzero-exit, bogus-command probes + NEG tests); lifecycle — CHECKED (submit→run→output→cancel→terminal→reconnect); stale state — CHECKED (cancelled job not shown RUNNING after reconnect; wx details req_id/generation guards reviewed, already correct); identity — CHECKED (disposable per-run roots, no cross-talk); concurrency — CHECKED (wx refresh in_flight/pending guards reviewed, untouched); boundary — CHECKED (spaces/Unicode quoting covered by existing sbatch tests); capability absence — CHECKED (`lssrv` allowlist + no-status-command errors reviewed, untouched); persistence — N/A (Slurm has no client-persisted state); packaging — N/A with justification (no artifact bound, no build-input change); error visibility — CHECKED (`.ok`/`.message` gating + no-phantom tests); secondary entry — CHECKED (Qt `jobs_widget` shares the fixed `parse_squeue`; CLI shares fixed `.text`); adjacent boundary — CHECKED (registry `slurm.sacct.pipe.v1` parser already headerless-safe; no change needed).

## Fixes (smallest coherent corrections)

FIX-A (`DEF-W13-001` + `DEF-W13-003`, file: `src/hpc_gui/services/slurm_models.py` — one root cause family, one fix):
- `_rows` now drops the first line(s) only when they are a header row (leading field `jobid`, case-insensitive), tolerating one banner/MOTD line ahead of the header; headerless data keeps every row.
- `parse_squeue`/`parse_sacct` skip rows whose leading field contains no ASCII digit (`_looks_like_job_id`) — real IDs (`4`, `123.batch`, `123_4`) always have one; error/display text never does.
- Behavioral contract changed: headerless scheduler responses parse to all their jobs; non-row text never becomes a job.

FIX-B (`DEF-W13-002`, file: `src/hpc_gui/services/slurm_ssh.py`):
- `SlurmCommandResult.text` returns `""` for successful commands with empty output; failures keep the exact legacy `stderr or [exit=N]` fallback.
- Behavioral contract changed: empty queue/accounting renders empty (not `[exit=0]`); `scancel()`/`CLI-cancel` `OK` paths and all failure diagnostics unchanged.
- Independence: different finding, different root cause (result-type rendering vs parser row selection), different file, separately sensitivity-proven.

Out-of-scope routing: SSH→W11, SFTP→W12 (none found). Adjacent notes (reviewed, not changed): registry `slurm.sacct.pipe.v1` already headerless-safe; wx details/squeue flows already carry exit codes and stale-request guards; `scancel` of unknown IDs exits 0 on the real controller (scheduler-idempotent, reported `OK` truthfully); Qt `jobs_widget` benefits from both fixes via the shared layer.

## Requirement → implementation → test → evidence trace

| Owned ID | Verdict | Live owner | Test(s) / proof | Evidence |
|---|---|---|---|---|
| `SLURM-001` W02 GO (prereq) | VERIFIED | predecessor W12 GO | dependency satisfied | W12 report `GO` |
| `SLURM-002/003` lab + safe paths | VERIFIED | lab `hpclab` + disposable roots | EXT matrix connect/root/cleanup | `EV-W13-EXT-001` |
| `SLURM-004` no secrets | VERIFIED | env-only password, scan | added-line scan + no secret in evidence | `EV-W13-DIFF-001` |
| `SLURM-005` SHAs pinned | VERIFIED | main `0f8902a0`, plugin `f0abb7e7` | baseline capture | report header |
| `SLURM-006` no provider expansion | VERIFIED | no provider change in diff | diff review | `EV-W13-DIFF-001` |
| `SLURM-007..015` scope boundaries | VERIFIED | backend + widgets + CLI (SSH/SFTP routed out) | matrix + suites | `EV-W13-EXT-001`, `EV-W13-REG-001` |
| `SLURM-016` structured parsing | VERIFIED | `_rows` header detection + FIX-A | DEF/CON tests + lab parse | `EV-W13-MATRIX-001`, `EV-W13-SENS-001`, `EV-W13-EXT-001` |
| `SLURM-017` network/forced disconnect | VERIFIED | product transport death paths | **SUP-DISCONNECT** (client-side forced close → op raises `SSH client not connected`, never stale success) + **SUP-MIDOP** (server-side `pkill -9 sshd-session` → op raises, never false success) in `EV-W13-EXT-002`; routed mid-op death `SSH-008` in `EV-W11-EXT-001` (same transport) | `EV-W13-EXT-002`, `EV-W11-EXT-001` |
| `SLURM-018` permission denied | VERIFIED | real host EACCES via product `SSHClientWrapper.run` | **SUP-PERMIT** ×2 in `EV-W13-EXT-002` (`cat /etc/shadow` → code 1 `Permission denied`; `touch` in chmod-000 dir → `Permission denied`); routed SFTP denied-with-filename in `EV-W12-EXT-001` (FIX-A verified on the wire) | `EV-W13-EXT-002`, `EV-W12-EXT-001` |
| `SLURM-019` remote path missing | VERIFIED | `sbatch_result` bad path + SFTP missing-target paths | **EXT-FAIL** bad script path (`No such file`, `ok=False`) in `EV-W13-EXT-001`; routed missing-target (`FileNotFoundError filename=True`) in `EV-W12-EXT-001` | `EV-W13-EXT-001`, `EV-W12-EXT-001` |
| `SLURM-020` command exits non-zero | VERIFIED | exit status preserved next to text | **EXT-FAIL** nonzero (`exit 3`, code preserved) in `EV-W13-EXT-001`; `NEG-W13-002/003` unit guards in `EV-W13-MATRIX-001` | `EV-W13-EXT-001`, `EV-W13-MATRIX-001` |
| `SLURM-021` scheduler returns error | VERIFIED | `.ok`/`.message` + no-phantom parsing | **EXT-FAIL** unknown-job (`Invalid job id`, `ok=False`) + **EXT-FAIL** scheduler-error-never-parses in `EV-W13-EXT-001`; `NEG-W13-003/004/005` in `EV-W13-MATRIX-001` | `EV-W13-EXT-001`, `EV-W13-MATRIX-001` |
| `SLURM-022` session expires/stale channel | VERIFIED | expired handle unusable; fresh session clean | **SUP-STALE** (old backend handle raises `RuntimeError` after close) + **SUP-RECONNECT** (fresh connect → `squeue code=0`) in `EV-W13-EXT-002`; routed 5-cycle leak check `SSH-010` in `EV-W11-EXT-001` | `EV-W13-EXT-002`, `EV-W11-EXT-001` |
| `SLURM-023` plugin/provider capability absent | VERIFIED | `SSHSlurmBackend.lssrv` capability guards | **SUP-CAPAB** ×2 in `EV-W13-EXT-002` (empty `status_command` → `No site status command…`; non-allowlisted command → `…not an allowlisted adapter…`; both user-visible `RuntimeError`, no SSH traffic, executed inside the live real-lab session) | `EV-W13-EXT-002` |
| `SLURM-024` connection indicator correct | VERIFIED | dead transport never reads connected | **SUP-DISCONNECT** + **SUP-MIDOP** raise on dead transport in `EV-W13-EXT-002`; routed controller-`FAILED` repaint `SSH-001` + GUI-001/002 in `EV-W11-EXT-001`/`EV-W11-MATRIX-001` | `EV-W13-EXT-002`, `EV-W11-EXT-001` |
| `SLURM-025` no stale masquerade | VERIFIED | cancelled/error state never shown as fresh RUNNING | **EXT-STALE** (cancelled job not RUNNING after reconnect) + **EXT-FAIL** no-phantom in `EV-W13-EXT-001`; **SUP-RECONNECT** clean read in `EV-W13-EXT-002`; FIX-A/FIX-B regression tests | `EV-W13-EXT-001`, `EV-W13-EXT-002`, `EV-W13-MATRIX-001` |
| `SLURM-026` retry/reconnect clean path | VERIFIED | close + fresh connect works | **EXT-RECONNECT** in `EV-W13-EXT-001`; **SUP-RECONNECT** + **SUP-RECOVER** in `EV-W13-EXT-002`; routed `SSH-009` in `EV-W11-EXT-001` | `EV-W13-EXT-001`, `EV-W13-EXT-002`, `EV-W11-EXT-001` |
| `SLURM-027` no queued action on old session | VERIFIED | superseded/expired session teardown | **SUP-STALE** (expired Slurm handle raises, nothing executes) in `EV-W13-EXT-002`; routed reconnect-teardown `DEF-W11-002`/`SSH-010` in `EV-W11-EXT-001` | `EV-W13-EXT-002`, `EV-W11-EXT-001` |
| `SLURM-028` cancellation isolation | VERIFIED | cancel targets its job ID; empty view honest | **EXT-CANCEL** → **EXT-TERMINAL** (job 5/6 `CANCELLED`, per-job state coherent) in `EV-W13-EXT-001`; **GUI-002** honest empty view + `CON-W13-003` cancel-`OK` in `EV-W13-MATRIX-001` | `EV-W13-EXT-001`, `EV-W13-MATRIX-001` |
| `SLURM-029..036` test matrix | VERIFIED | unit + integration + real SSH/Slurm + UI runtime (package deferred w/ justification) | suites + matrix | all EVs below |
| `SLURM-037` real SSH login proven | VERIFIED | product `SSHClientWrapper` vs `hpclab` | **EXT-CONNECT** in `EV-W13-EXT-001` + **SUP-CONNECT** in `EV-W13-EXT-002` | `EV-W13-EXT-001`, `EV-W13-EXT-002` |
| `SLURM-038` auth failure safe | VERIFIED (routed, re-proven) | `AuthenticationException`, no session, same transport Slurm uses | **SUP-AUTH** (bad password → `AuthenticationException`, no session) in `EV-W13-EXT-002`; owned proof `SSH-004` in `EV-W11-EXT-001` | `EV-W13-EXT-002`, `EV-W11-EXT-001` |
| `SLURM-039` SFTP round-trip hash | VERIFIED (routed) | product `SSHFilesBackend` | **EXT-COHER**/**EXT-OUTPUT** marker round trip in `EV-W13-EXT-001`; owned proof (`match=True`) in `EV-W12-EXT-001` | `EV-W13-EXT-001`, `EV-W12-EXT-001` |
| `SLURM-040` destructive ops confined | VERIFIED | disposable roots only | `EXT-ROOT`/`SUP-ROOT` + verified-absent cleanups in both W13 matrices | `EV-W13-EXT-001`, `EV-W13-EXT-002` |
| `SLURM-041` Slurm workflow proven | VERIFIED | submit → RUNNING → output → cancel → CANCELLED → sacct | job 5 (first run) + job 6 (repair-cycle re-run) lifecycles in `EV-W13-EXT-001` | `EV-W13-EXT-001` |
| `SLURM-042` disconnect/reconnect coherent | VERIFIED | close/kill → raise → fresh session works | **EXT-RECONNECT** in `EV-W13-EXT-001`; **SUP-DISCONNECT**/**SUP-MIDOP**/**SUP-RECONNECT**/**SUP-RECOVER** in `EV-W13-EXT-002` | `EV-W13-EXT-001`, `EV-W13-EXT-002` |
| `SLURM-043` no stale success | VERIFIED | dead/expired ops raise; no phantom rows | **SUP-DISCONNECT**/**SUP-STALE**/**SUP-MIDOP** in `EV-W13-EXT-002`; **EXT-STALE** + no-phantom in `EV-W13-EXT-001` | `EV-W13-EXT-001`, `EV-W13-EXT-002` |
| `SLURM-044` user-visible failures | VERIFIED | `.ok`/`.message`/text + wx views | failure-text assertions in both matrices; **GUI-001/002** real wx views | `EV-W13-EXT-001`, `EV-W13-EXT-002`, `EV-W13-GUI-001` |
| `SLURM-045` cleanup verified | VERIFIED | roots removed + verified absent | **EXT-CLEANUP** + **SUP-CLEANUP** (`ls` → `No such file`) | `EV-W13-EXT-001`, `EV-W13-EXT-002` |
| `SLURM-046` no secret leak | VERIFIED | env-only password, scan | added-line scan + no secret in evidence/scripts | `EV-W13-DIFF-001` |
| `SLURM-047` connection transcript | VERIFIED | success + failure transcripts | **EXT-CONNECT** + **SUP-CONNECT** (success) and **SUP-AUTH**/**SUP-DISCONNECT**/**SUP-MIDOP** (failure) | `EV-W13-EXT-001`, `EV-W13-EXT-002` |
| `SLURM-048` fixture tree before/after | VERIFIED (routed SFTP detail) | disposable-root create/use/remove | `EXT-ROOT`/`SUP-ROOT` + verified-absent cleanups; SFTP tree detail owned by `EV-W12-EXT-001` | `EV-W13-EXT-001`, `EV-W13-EXT-002`, `EV-W12-EXT-001` |
| `SLURM-049` SHA comparison | VERIFIED (routed) | byte/hash equality | **EXT-OUTPUT** marker + **EXT-COHER** round trip in `EV-W13-EXT-001`; owned `local=remote` proof in `EV-W12-EXT-001` | `EV-W13-EXT-001`, `EV-W12-EXT-001` |
| `SLURM-050` job ID lifecycle | VERIFIED | submit 6 → RUNNING → marker → cancel → CANCELLED → sacct | full lifecycle in `EV-W13-EXT-001` (re-run this cycle) | `EV-W13-EXT-001` |
| `SLURM-051` disconnect/reconnect evidence | VERIFIED | forced + server-side + expiry + recovery | **SUP-DISCONNECT**/**SUP-STALE**/**SUP-RECONNECT**/**SUP-MIDOP**/**SUP-RECOVER** in `EV-W13-EXT-002` + **EXT-RECONNECT** in `EV-W13-EXT-001` | `EV-W13-EXT-002`, `EV-W13-EXT-001` |
| `SLURM-052` failure/recovery evidence | VERIFIED | every Workstream-D facet + recovery | EXT-FAIL set (unknown-job/bad-path/nonzero/no-phantom) + SUP set (permit/capab/disconnect/stale/midop/auth) + recoveries | `EV-W13-EXT-001`, `EV-W13-EXT-002` |
| `SLURM-053` cleanup confirmation | VERIFIED | verified-absent + healthy lab | **EXT-CLEANUP** + **SUP-CLEANUP**; container left `healthy`, `sinfo` `idle` | `EV-W13-EXT-001`, `EV-W13-EXT-002` |
| `SLURM-054` rollback-safe fixtures | VERIFIED | disposable roots, no persisted client state | both matrices clean up verified-absent; appdata in Temp only | `EV-W13-EXT-001`, `EV-W13-EXT-002` |
| `SLURM-055` handoff list | VERIFIED | replay list below | this report | this file |

Acceptance boxes: real SSH login proven ✓; auth failure safe (routed W11 SSH-004 + re-proven live as SUP-AUTH `AuthenticationException` in `EV-W13-EXT-002`) ✓; SFTP round-trip hash (W12-owned, coherency re-proven `match=True`) ✓; destructive ops confined to fixture root ✓; Slurm workflow proven (submit 5 → RUNNING → output → cancel → CANCELLED → sacct) ✓; disconnect/reconnect coherent ✓; no stale success ✓; user-visible failures ✓; cleanup verified ✓; no secret leak ✓.

Mocking statement: fakes replay only the paramiko `(code, stdout, stderr)` triples observed on the real wire (`EV-W13-BEFORE-001`). Real code exercised: full `SSHSlurmBackend`/`SlurmCommandResult`, full `parse_squeue`/`parse_sacct`, full wx panel event/worker/table path. What this does NOT prove: real-controller bytes (covered by `EV-W13-EXT-001`, not claimed here).

## EXTERNAL evidence — authorized real lab (`EV-W13-EXT-001`)

Real-lab target per `docs/testing/LOCAL_HPC_LAB.md` + `devtools/lab/docker-compose.yml`: container `hpclab`, remote environment class **local containerized single-node Slurm** (Debian 13 trixie-slim, OpenSSH, Slurm 24.11.5, `short` partition). Endpoint `127.0.0.1:2222` (loopback-published only), fixture account `hpctest`, auth method **password (fixture)** — passed via `HPC_LAB_PASSWORD` env at runtime, in no file/log/evidence artifact. Provider ID: lab Slurm via product `SSHSlurmBackend`/`SSHClientWrapper`/`SSHFilesBackend`.

Provenance honesty: the container pre-existed this session (shared lab, left `healthy`); it was NOT built by this Wave. Evidence run 2026-09-19 (~20:23+03:00). Client: Windows source runtime, Python 3.12.4, paramiko 3.5.1. Main SHA `0f8902a023bac76071527232c2287af96478ed2b`, plugin SHA `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin).

Script: `C:\Users\mskomek\AppData\Local\Temp\opencode\w13_ext_lab.py` (outside repo, untracked). Exit 0. Result **20/20 PASS**: connect, disposable root, submit (job 5), squeue bytes, FIX-A parse (`state=RUNNING`), scontrol script path, stdout marker fetch, SFTP coherency, unknown-job failure, bad-path failure, nonzero-exit, no-phantom parse, cancel, CANCELLED terminal, sacct record, per-job state, reconnect, no-stale-RUNNING, cleanup verified absent, close.

Cleanup: disposable root `/home/hpctest/.w13-ext-<stamp>` removed and verified absent (`ls` → `No such file`); probe roots from discovery likewise removed; container left running as found. No persisted client state (isolated appdata in Temp only).

## Repair cycle 1 — supplemental EXTERNAL evidence (`EV-W13-EXT-002`)

Audit `FND-W13-AUDIT-001` (P1, evidence/traceability; explicitly no product-code change requested) found the grouped `SLURM-017..023` trace pointed only at `EV-W13-MATRIX-001` + `EV-W13-EXT-001`, which lack forced network/session interruption, permission-denied, session-expiry/stale-channel and capability-absence scenarios, and found no explicit requirement-by-requirement mapping to the routed W11/W12 evidence. Cured this cycle without touching product code:

Real-lab target (same authorized lab): container `hpclab`, remote environment class **local containerized single-node Slurm** (Debian 13 trixie-slim, OpenSSH, Slurm 24.11.5, `debug*`+`short` `idle`). Endpoint `127.0.0.1:2222` (loopback-published only), fixture account `hpctest`, auth **password (fixture)** via `HPC_LAB_PASSWORD` env only. Provider ID: lab Slurm via product `SSHSlurmBackend`/`SSHClientWrapper`. Main SHA `0f8902a023bac76071527232c2287af96478ed2b`, plugin SHA `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (unchanged — no product/test file changed this cycle, so no evidence invalidation).

Script: `C:\Users\mskomek\AppData\Local\Temp\opencode\w13_ext_supplement.py` (outside repo, untracked). Exit 0. Result **15/15 PASS** (run 2026-09-19 ~20:35+03:00): invalid-credential rejection (`AuthenticationException`, no session), valid connect, disposable root, permission-denied ×2 (real `cat: /etc/shadow: Permission denied` code 1; `touch` in chmod-000 dir denied), capability-absence ×2 (`No site status command…`, `…not an allowlisted adapter…`, both user-visible `RuntimeError` inside the live session), pre-interrupt squeue OK, forced client-side disconnect (op raises `SSH client not connected`, never stale success), stale handle unusable (`RuntimeError`), fresh-session reconnect (`code=0`), server-side kill (`pkill -9 -f "sshd-session.*hpctest"` — note: this container's OpenSSH names sessions `sshd-session:`, not `sshd:`; first attempt with the lab-doc pattern matched nothing and honestly FAILED, corrected pattern kills and the op raises `RuntimeError`, never false success), post-kill reconnect coherent, cleanup verified absent, sessions closed.

Cleanup: disposable root `/home/hpctest/.w13-sup-<stamp>` removed and verified absent (`ls` → `No such file`); post-run `ls /home/hpctest/` shows no `w13-sup` residue; container left `healthy`, `sinfo` `idle`, squeue empty. No persisted client state (isolated appdata in Temp only).

Trace granularity: the `Requirement → implementation → test → evidence trace` table above now maps `SLURM-017..028` and `SLURM-037..053` requirement-by-requirement to exact W13 tests/evidence IDs plus explicit routed W11 (`EV-W11-EXT-001`: SSH-001/004/008/009/010) and W12 (`EV-W12-EXT-001`: SFTP-005/006/012/013/015) evidence recorded at identical main/plugin SHAs — no mock substitution, no code-review-as-evidence anywhere in the chain.

## Fix proof chains

Fix ID `FIX-W13-A` / Defects `DEF-W13-001` (P1) + `DEF-W13-003` (P2, same parser family) / Independent root cause: scheduler-output row selection assumed a header and accepted non-rows as rows.
Before behavior/evidence: `EV-W13-BEFORE-001` (real lab: job 4 RUNNING in bytes, 0 jobs parsed) + `EV-W13-SENS-001` (4 parser tests fail pre-fix).
Files changed: `src/hpc_gui/services/slurm_models.py` (`_looks_like_job_id`, `_rows` header detection, guards in both parsers). Regression tests: `test_headerless_single_job_squeue_row_is_kept`, `test_headerless_multi_job_squeue_keeps_first_row`, `test_headerless_sacct_single_row_is_kept`, `test_squeue_failure_text_does_not_parse_as_job` (+ headed/banner/empty contract tests). Sensitivity `EV-W13-SENS-001`: each fails pre-fix for the expected reason, passes post-fix. Negative tests: error-text, empty, bad-header variants. Narrow suite: new module 14 passed. Broader: 120 + 187 + 12 passed. Runtime: lab probes + 20/20 matrix. Package: N/A (no artifact bound). External: `EV-W13-EXT-001` (FIX-A verified on real headerless bytes). Residual risk: none known — all shipped scheduler commands are headerless or headed, both proven.

Fix ID `FIX-W13-B` / Defect `DEF-W13-002` (P2) / Independent root cause: success/failure rendering conflated in `SlurmCommandResult.text` (empty success fell into the failure token).
Before behavior/evidence: `EV-W13-BEFORE-001` (`text='[exit=0]'` on healthy empty queue) + `EV-W13-SENS-001` (`test_empty_success_renders_empty_text_not_exit_token` fails pre-fix).
Files changed: `src/hpc_gui/services/slurm_ssh.py` (`.text` only). Regression tests: the above + `test_failure_empty_output_keeps_exit_token`. Sensitivity: revert → fails (`'[exit=0]' != ''`); restore → passes. Negative tests: failure tokens preserved. Narrow/broader suites: same as above. Runtime: EXT empty-queue assertions. Residual risk: none — failure paths byte-identical to before.

## Evidence ledger (exact counts)

| Evidence ID | Command | Exit | Result |
|---|---|---|---|
| `EV-W13-BASE-001` | `pytest test_slurm_ssh test_slurm_models test_slurm_script_parser -q` (pre-edit) | 0 | 16 passed |
| `EV-W13-BEFORE-001` | `python w13_probe.py` (real lab, pre-fix) | 0 | lifecycle works; job 4 in bytes but 0 parsed; `[exit=0]` on empty queue |
| `EV-W13-MATRIX-001` | `pytest tests/test_w13_slurm_state.py -q` | 0 | **14 passed** (5 DEF-A + 1 DEF-B + CON/NEG + 2 wx GUI) |
| `EV-W13-SENS-001` | stash product files → run new non-wx tests → restore | — | **5 fail pre-fix** for the expected reason, **12 pass post-fix** |
| `EV-W13-REG-001a` | `pytest test_w13_slurm_state test_slurm_ssh test_slurm_models test_slurm_script_parser test_slurm_arrays test_slurm_dependencies test_slurm_directives test_slurm_compat_matrix test_wave3_remote_sftp_ssh test_wave5_slurm_jobs_unicode -q` | 0 | **120 passed** |
| `EV-W13-REG-001b` | `pytest test_wx_jobs test_wx_jobs_behavior test_corrective_jobs_details test_cli -q` | 0 | **187 passed** |
| `EV-W13-REG-001c` | `pytest test_w11_ssh_lifecycle -q -k "not wx"` | 0 | **12 passed** |
| `EV-W13-GUI-001` | inside MATRIX: `test_wx_jobs_panel_lists_headerless_lab_job`, `test_wx_jobs_panel_empty_queue_shows_no_rows_and_no_exit_token` (real `wx.App`+`Frame`, real `EVT_BUTTON` clicks, pumped loop, clean teardown) | 0 | 2 passed |
| `EV-W13-DIFF-001` | `git diff --check`; `git diff --stat`; added-line secret scan | 0 | clean; 2 files + new test module; no secrets |
| `EV-W13-EXT-001` | `python w13_ext_lab.py` (real lab `hpclab` 127.0.0.1:2222, product backend, isolated known_hosts, disposable fixture root) | 0 | **20/20 PASS**, fixture cleaned + verified |
| `EV-W13-EXT-002` | `python w13_ext_supplement.py` (real lab `hpclab` 127.0.0.1:2222, product `SSHClientWrapper`+`SSHSlurmBackend`, isolated appdata, disposable fixture root; repair cycle 1) | 0 | **15/15 PASS** (auth-reject, permit-denied ×2, capability-absence ×2, forced-disconnect, stale-handle, reconnect, server-kill, recovery, cleanup verified), fixture cleaned + verified |
| `EV-W13-EXT-001R` | `python w13_ext_lab.py` re-run on current tree (repair cycle 1, no product change) | 0 | **20/20 PASS** (job 6 lifecycle), fixture cleaned + verified |
| `EV-W13-REG-002` | `pytest test_w13_slurm_state test_slurm_ssh test_slurm_models test_slurm_script_parser test_slurm_arrays test_slurm_dependencies test_slurm_directives test_slurm_compat_matrix test_wave3_remote_sftp_ssh test_wave5_slurm_jobs_unicode test_wx_jobs test_wx_jobs_behavior test_corrective_jobs_details test_cli -q` (repair cycle 1 re-run) | 0 | **307 passed** |

New/modified tests: `tests/test_w13_slurm_state.py` (new, 14 tests: REQ-013/014/016, DEF regressions with purpose IDs, CON, NEG, 2 wx GUI). Skipped/xfail changes: none. Test weakening: none.

Evidence classes: `GUI` satisfied by `EV-W13-GUI-001` (real wx event/runtime proof: running-job visibility + honest empty view through the full product chain). `EXTERNAL` satisfied by `EV-W13-EXT-001` (authorized real lab, 20/20 PASS, identity + cleanup recorded). Package: N/A with justification (no owned row binds an artifact; no build-input change; handoff replays listed below).

Purpose-ID map: REQ — headerless squeue/sacct parse, details/output/cancel lifecycle (via EXT); DEF — the 5 sensitivity-proven regressions; CON — headed/banner/empty/cancel-OK/whitespace-sacct; NEG — unknown-job/bad-path/nonzero-exit/no-phantom/empty-output; RACE/lifecycle — cancel→terminal + reconnect coherence (EXT); EXT — `EV-W13-EXT-001`; GUI — the 2 wx tests.

## Test review checklist

- [x] Each counted fix has dedicated regression tests — YES (4 for FIX-A incl. sacct + phantom; 1 for FIX-B + failure-token guard).
- [x] Regression tests failed before the fix / pass sensitivity proof — YES (`EV-W13-SENS-001`, per-fix stash reverts).
- [x] Negative path covered — YES (unknown-job, bad-path, nonzero-exit, empty, error-text).
- [x] Stateful/async lifecycle covered — YES (submit→cancel→terminal→reconnect in EXT; wx worker-thread refresh in GUI).
- [x] Behavioral (not existence-only) assertions — YES (job IDs, states, byte equality, table cell text, exact rendered strings).
- [x] Mocks limited to legitimate boundaries — YES (transport triples only; stated non-proofs).
- [x] No unjustified skips/xfails — YES (none added).
- [x] Fixtures isolated; cleanup deterministic — YES (Temp appdata, disposable remote roots, verified removal).
- [x] Package/external honestly classified — YES (package N/A justified; lab is EXTERNAL, fakes are unit/integration).
- [x] Full impacted slice still passes — YES (120 + 187 + 12 + 14).
- [x] Future regression would fail the tests — YES (proven by reverts).

## POST_GREEN_REVIEW

- Duplicate path: `_rows` is the single shared helper — both `parse_squeue`/`parse_sacct` fixed at once; registry `slurm.sacct.pipe.v1` already headerless-safe (verified, untouched); Qt `jobs_widget` + CLI share the fixed layer. ✓
- Alternate entry points (wx table/filter/cancel, Qt widget, CLI list/status/accounting/submit/cancel) all flow through the two fixed units — covered. ✓
- No silent fallback: `.text` failure branch byte-identical; `ok`/`message` untouched. ✓
- No stale state after cancel/reconnect (EXT proven); wx details guards already correct. ✓
- No wrong-identity capture: no session/profile/path capture in the diff. ✓
- No new dead branch; no hardcoded provider behavior; errors claim failure with scheduler message. ✓
- `scancel` unknown-ID `OK` is truthful scheduler-idempotent behavior (exit 0 on real controller) — not changed. ✓
- No secret added to source/diff/logs/evidence (added-line scan clean). ✓

## Diff review

`git diff --check`: clean (only pre-existing CRLF warnings on untouched W01 files). W13 diff: `slurm_models.py` (+37/−1: header detection, ID guard), `slurm_ssh.py` (+13/−3 docstring-inclusive: empty-success rendering), new untracked `tests/test_w13_slurm_state.py`. All other dirty/untracked files are pre-existing and preserved untouched (verified: full `git status` + scoped `git diff` inspected). No generated/binary noise; no test weakening; no secret. No commit made (report-first; committer decides).

## Open findings

P0: none. P1: none open (DEF-W13-001 closed). P2: none open (DEF-W13-002/003 closed). P3: none.

## Deviations

None — SSH/SFTP scenarios left to W11/W12; no W14 work started.

## Rollback

Revert the `slurm_models.py` + `slurm_ssh.py` hunks and delete `tests/test_w13_slurm_state.py`; the five DEF regression tests fail on the reverted tree (proven by `EV-W13-SENS-001`), so rollback is detectable. No remote/persisted state to clean (lab fixtures already removed and verified; shared `hpclab` container left running as found; local known_hosts in untracked temp only).

## Handoff to W04 (replay against the packaged artifact)

1. Empty-queue `jobs list` must print empty output (not `[exit=0]`), exit 0.
2. Single-running-job `jobs list` must show that job (headerless parse, no off-by-one).
3. `jobs submit --yes` of a sleep job → ID → `jobs status <id>` → output fetch → `jobs cancel --yes <id>` → terminal state in `scontrol`/`sacct`.
4. `jobs status 99999999` must exit nonzero with `Invalid job id` (never a phantom row).
5. Disconnect/reconnect must leave the jobs view coherent (no RUNNING ghost of a CANCELLED job).

## Resume state

Completed and verified: all 55 Slurm rows at requirement-by-requirement granularity (017..023 live-mapped, 024..028 + 037..053 live-mapped incl. explicit routed W11/W12 evidence IDs); FIX-A + FIX-B with before/after/sensitivity evidence; 14-test suite green; broader slice green (307 passed this cycle); GUI proof green (real wx events); EXTERNAL class satisfied by `EV-W13-EXT-001` (20/20, re-run `EV-W13-EXT-001R` green) + `EV-W13-EXT-002` (15/15 gap scenarios, fixture cleaned); report current.
In progress: nothing. Open P0/P1: none. Open P2/P3: none. Pending tests/evidence: none (fresh-context re-audit is a separate step; `FND-W13-AUDIT-001` cure claimed, awaiting audit verdict).
Last exact commands run: `pytest tests/test_w13_slurm_state.py -q` → 14 passed; focused slice (14 modules) → 307 passed; `python w13_ext_supplement.py` → 15/15 PASS exit 0; `python w13_ext_lab.py` re-run → 20/20 PASS exit 0; remote cleanups verified absent, lab `healthy`/`idle`; `git diff --check` → clean.
Next actions: fresh-context `/wave-audit W13`; then W14 may be planned (never auto-started).
Evidence/artifact identities: `EV-W13-BASE-001`, `EV-W13-BEFORE-001`, `EV-W13-MATRIX-001`, `EV-W13-SENS-001`, `EV-W13-REG-001a/b/c`, `EV-W13-REG-002`, `EV-W13-GUI-001`, `EV-W13-DIFF-001`, `EV-W13-EXT-001`, `EV-W13-EXT-001R`, `EV-W13-EXT-002`; main HEAD `0f8902a0`, plugin `f0abb7e7`.

```text
FIX-A: headerless scheduler output keeps every data row; error text never becomes a job
DEF: DEF-W13-001 (P1, first headerless row dropped) + DEF-W13-003 (P2, phantom rows; same parser family)
Root cause: _rows assumed a header and dropped line 1; parsers accepted any long line as a row
Before EV: EV-W13-BEFORE-001 (real lab: job 4 in bytes, 0 parsed) + EV-W13-SENS-001 (4 parser tests fail)
After EV: EV-W13-MATRIX-001 (14 passed) + EV-W13-EXT-001 (RUNNING parsed on the wire, 20/20)
Regression test: test_headerless_single_job_squeue_row_is_kept (+ multi/sacct/phantom variants)
Sensitivity proof: EV-W13-SENS-001 (each fails pre-fix for the expected reason, passes post-fix)

FIX-B: empty successful scheduler output renders empty instead of [exit=0]
DEF: DEF-W13-002 (P2, pseudo-error token shown for healthy empty queue)
Root cause: SlurmCommandResult.text fell through to the failure token on empty success
Before EV: EV-W13-BEFORE-001 (text='[exit=0]' code=0) + EV-W13-SENS-001 (renders-empty test fails)
After EV: EV-W13-MATRIX-001 + GUI-002 + EXT empty-queue assertions
Regression test: test_empty_success_renders_empty_text_not_exit_token
Sensitivity proof: EV-W13-SENS-001 (revert → fails; restored → passes)

Additional fixes: none beyond DEF-W13-003's same-family parser guard (explicitly not counted separately)
Post-green review: PASS (recorded above)
New/modified tests: tests/test_w13_slurm_state.py (14 new)
Skipped/xfail changes: none
Package evidence: N/A (justified — no owned row binds an artifact; no build-input change; W04 replays listed)
External evidence: EV-W13-EXT-001 real authorized lab (hpclab 127.0.0.1:2222, 20/20 PASS incl. re-run 001R, identity + cleanup recorded) + EV-W13-EXT-002 gap-scenario supplement (15/15 PASS: auth-reject, permit-denied, capability-absence, forced-disconnect, stale-handle, server-kill, recovery; repair cycle 1, no product-code change)
Open P0/P1: none
Open P2/P3: none
Two-fix gate: PASS (W03-specific: two real-integration remediations with lab evidence, non-mock)
Wave decision: GO
```

## Repair cycle 2 — LOCAL_REAL evidence refresh (2026-09-22)

This cycle addresses `REOPEN-W13-001` and `REOPEN-W13-002`. `REOPEN-W13-003`
is not current: the W12 audit is now `PASS` with its own LOCAL_REAL replay and
is not modified by this W13 worker.

- Environment: `LOCAL_REAL_HYPERV`, profile/provider `local-real`, controller
  `192.168.250.11:22`, user `hpctest`, emitted SSH-key profile; private-key
  bytes were not read or recorded.
- Health baseline: `lab/lab-status.ps1` → PASS; `lab/lab-test.ps1` →
  `LOCAL_REAL_READY`, 23/23 checks, cleanup verified.
- Product replay: `python .tmp/w13_local_real_replay.py` → exit 0. Real
  `SSHClientWrapper` + `SSHSlurmBackend` proved connect, submit job 34,
  headerless squeue parse (`34`, `PENDING`), scontrol parse, output marker,
  invalid-job failure, permission-denied nonzero result, scancel, sacct
  `CANCELLED`, reconnect, and disposable-root cleanup.
- Focused validation: `python -m pytest tests/test_w13_slurm_state.py -q` →
  14 passed, exit 0.
- Current identity: replay and this report are bound to HEAD
  `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`; profile identity is recorded
  above; no product/test files changed in this repair.

The prior loopback `EV-W13-EXT-001/002` evidence remains historical context
only and is not used as the current EXTERNAL acceptance claim. Fresh audit is
required before close.

## Repair cycle 3 — current LOCAL_REAL evidence ledger and bindings (2026-09-22)

Current evidence identity: `EV-W13-EXT-003`, generated by the exact command
`python .tmp/w13_local_real_replay.py` after the runner switched to the fresh
disposable `.tmp/w13-local-real-known_hosts-repair-20260922` path. Exit `0`.
Durable replay ledger: `.tmp/probes/W13_LOCAL_REAL_EXTERNAL.json` (exit `0`,
raw observations and requirement bindings preserved for independent replay
verification). `EV-W13-EXT-004` durable lab ledger is
`lab/evidence/LOCAL_REAL_TEST.json`, generated by `lab/lab-test.ps1` with
`LOCAL_REAL_READY`, `23/23` required checks and `failed=[]`.
Environment is `LOCAL_REAL_HYPERV`, profile/provider `local-real`, controller
`192.168.250.11:22`, user `hpctest`, current repository HEAD
`63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`; private-key bytes were not read or
recorded. The replay proved connect, submit (`job 40`), headerless squeue
parse (`40`, `PENDING`), scontrol parse, output marker, invalid-job failure,
permission-denied nonzero result, scancel, sacct `CANCELLED`, reconnect and
fixture cleanup. `lab-status.ps1` was `PASS`; `lab-test.ps1` was
`LOCAL_REAL_READY` with `23/23` checks and cleanup verified.

The current requirement-level bindings are now explicit (loopback evidence is
historical only):

| Requirement IDs | Current evidence binding |
|---|---|
| `HPC-W03-SLURM-001`, `HPC-W03-SLURM-002`, `HPC-W03-SLURM-003`, `HPC-W03-SLURM-004`, `HPC-W03-SLURM-005`, `HPC-W03-SLURM-006`, `HPC-W03-SLURM-007`, `HPC-W03-SLURM-008`, `HPC-W03-SLURM-009`, `HPC-W03-SLURM-010`, `HPC-W03-SLURM-013`, `HPC-W03-SLURM-014`, `HPC-W03-SLURM-015` | `EV-W13-EXT-003` + current HEAD/profile identity |
| `HPC-W03-SLURM-011`, `HPC-W03-SLURM-012`, `HPC-W03-SLURM-033`, `HPC-W03-SLURM-039`, `HPC-W03-SLURM-040`, `HPC-W03-SLURM-048`, `HPC-W03-SLURM-049` | `EV-W13-EXT-004` (`lab-test.ps1`, LOCAL_REAL SFTP/hash/fixture proof) |
| `HPC-W03-SLURM-016`, `HPC-W03-SLURM-020`, `HPC-W03-SLURM-021`, `HPC-W03-SLURM-025`, `HPC-W03-SLURM-028`, `HPC-W03-SLURM-034`, `HPC-W03-SLURM-041` | `EV-W13-EXT-003` |
| `HPC-W03-SLURM-017`, `HPC-W03-SLURM-018`, `HPC-W03-SLURM-019`, `HPC-W03-SLURM-022`, `HPC-W03-SLURM-023`, `HPC-W03-SLURM-024`, `HPC-W03-SLURM-026`, `HPC-W03-SLURM-027`, `HPC-W03-SLURM-038`, `HPC-W03-SLURM-042`, `HPC-W03-SLURM-043`, `HPC-W03-SLURM-044`, `HPC-W03-SLURM-052` | `EV-W13-EXT-003` + `EV-W13-EXT-002` routed gap proof where applicable |
| `HPC-W03-SLURM-029`, `HPC-W03-SLURM-030`, `HPC-W03-SLURM-031` | `EV-W13-MATRIX-001` + `EV-W13-REG-002` |
| `HPC-W03-SLURM-032`, `HPC-W03-SLURM-037`, `HPC-W03-SLURM-050`, `HPC-W03-SLURM-051`, `HPC-W03-SLURM-053`, `HPC-W03-SLURM-054` | `EV-W13-EXT-003` |
| `HPC-W03-SLURM-035` | `EV-W13-GUI-001` + `EV-W13-MATRIX-001` (GUI proof remains source-runtime evidence) |
| `HPC-W03-SLURM-036` | `N/A` with existing W04 package-replay handoff; no artifact is owned by W13 |
| `HPC-W03-SLURM-045`, `HPC-W03-SLURM-046`, `HPC-W03-SLURM-047` | `EV-W13-EXT-003` + `EV-W13-EXT-004` |
| `HPC-W03-SLURM-055` | this report's W04 packaged-artifact handoff, with current identity above |

The prior `EV-W13-EXT-001/002` loopback evidence is not used for the current
EXTERNAL acceptance claim. Focused validation remains
`python -m pytest tests/test_w13_slurm_state.py -q` → `14 passed`, exit `0`.
The evidence identity and bindings are refreshed; fresh independent audit is
required.
