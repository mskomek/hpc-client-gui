# W11 Wave Report — Real SSH lifecycle validation

Wave: `W11`
Canonical report path: `docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA: `0f8902a023bac76071527232c2287af96478ed2b` (== `origin/develop` tip at session start; working tree dirty with pre-existing unrelated changes — all preserved, none touched)
Current HEAD: `0f8902a023bac76071527232c2287af96478ed2b` (no commit made this session; tested tree = HEAD + uncommitted W11 diff below)
Tested implementation state: HEAD `0f8902a0` + uncommitted diff in `src/hpc_gui/wx_connection.py`, `src/hpc_gui/services/connection_controller.py`, new `tests/test_w11_ssh_lifecycle.py` (+ this report, untracked)
Plugin/external repo SHA(s): `D:\Projeler\hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin; no plugin change, no plugin claim)
First started: 2026-09-19
Last updated: 2026-09-19 (repair cycle 1: FND-W11-AUDIT-001 cured with real-lab EXTERNAL evidence)
Session status: READY FOR AUDIT
Wave decision: GO (two in-scope P1 defects closed with real-integration proof; every owned row evidenced; no owned blocker remains; EXTERNAL class now satisfied by authorized real lab infrastructure)

Runtime truth: Python `3.12.4`, wx `4.3.1 msw (phoenix) wxWidgets 3.3.3`, paramiko `3.5.1`.

## Objective

Validate real SSH authentication, host-key, lifecycle, reconnect, Unicode and negative behavior against the declared laboratory environment (Workstream A — SSH lifecycle; 11 owned IDs, 0 TODOs).

## Owned scope (11 stable IDs, all MANDATORY REQUIREMENT)

All rows read before implementation (`HPC-W03-SSH-001..011`, Owning Wave `W11`; `TODO_OWNERSHIP_MAP` owns none to W11). Mandatory source read: `opencode/sources/WAVE_V2_FINAL_03.md` Workstream A (§83–98) + shared execution contract. Live owners inspected before editing: `ssh/client.py` (`SSHClientWrapper`, `_KnownHostsPolicy`, `HostKeyChangedError`), `ssh/shell_session.py` (`InteractiveShellSession`), `ssh/sftp_channels.py`, `services/connection_controller.py`, `wx_connection.py` (`connect_profile`, `WxConnectionModel`, panel builder), `tests/support/mock_ssh_server.py`. SFTP semantics routed to W12, Slurm to W13 — not absorbed.

## Baseline capture (pre-edit)

Main: branch `develop`; HEAD `0f8902a023bac76071527232c2287af96478ed2b`; dirty with pre-existing unrelated changes (W08 validator/loader, i18n, wx shell/settings, `test_wave10_release_gate.py`, untracked W03/W04/W08/W09 test files) — preserved untouched. `git diff --check`: clean apart from pre-existing CRLF notices.

Narrow pre-edit baseline (`EV-W11-BASE-001`): `test_connection_controller + test_ssh_terminal_stream + test_ssh_directory_listing_wire` → **12 passed**, exit 0.

## Discovery pass + WAVE_FINDINGS

| Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Countable fix? | Status |
|---|---|---|---|---|---|---|---|
| `DEF-W11-001` | P1 | transport-failure UI state (`HPC-W03-SSH-001`) | `EV-W11-BEFORE-001`: lab script killed the live transport; `wrapper._disconnect_cb is None`, controller stayed `connected`, `wrapper.client` already `None` | `connect_profile` never passed `disconnect_cb` to `SSHClientWrapper`, and no controller transition repainted the wx status label (`model.controller` created with no `emit`) | dead transport masquerades as live session; user keeps working against nothing | yes → FIX-A | CLOSED |
| `DEF-W11-002` | P1 | reconnect session ownership (`HPC-W03-SSH-010`) | `EV-W11-BEFORE-001`: two `connect_selected()` calls; first live `ssh` never closed, controller silently repointed | neither `WxConnectionModel.connect_selected` nor the wx worker tore down the superseded session before the new attempt | orphaned transport/shell-thread/SFTP channels; queued actions could execute against the old session | yes → FIX-B (independent root cause: missing teardown vs unwired notification) | CLOSED |

Second-defect search (12 dimensions): negative paths — CHECKED (10 lab scenarios); lifecycle — CHECKED (connect/idle-death/mid-op-death/reconnect/cycles); stale state — CHECKED (superseded-session teardown); identity — CHECKED (per-profile sessions, no cross-talk); concurrency — CHECKED (CallAfter marshalling, no off-thread UI touch); boundary — CHECKED (empty password/key-auth path, Unicode, closed-port); capability absence — N/A (SSH lifecycle has no optional provider caps); persistence — CHECKED (known_hosts save/reject round trip); packaging — N/A with justification (no artifact bound, no build-input change); error visibility — CHECKED (failed label preserved across language refresh); secondary entry — CHECKED (button/double-click/context-menu share `connect_selected`); adjacent boundary — CHECKED (Qt `login_widget` already wires `disconnect_cb`; untouched).

## Fixes (smallest coherent corrections)

FIX-A (`DEF-W11-001`, files: `src/hpc_gui/wx_connection.py`):
- new `_controller_disconnect_cb(model)` — transport-death callback that fails the controller on the GUI thread (`wx.CallAfter` when a live `wx.App` exists, synchronous otherwise; never touches UI off-thread);
- `connect_profile` now passes it as `disconnect_cb`;
- panel wires `model.controller._emit` to repaint the status indicator on every transition (background-safe);
- `refresh_labels` preserves the `failed` state across language changes (was silently reset to "disconnected").
- Behavioral contract changed: after transport failure the controller leaves `CONNECTED` for `FAILED` and the wx status label shows the failed state, never "Connected".

FIX-B (`DEF-W11-002`, files: `src/hpc_gui/services/connection_controller.py` + `src/hpc_gui/wx_connection.py`):
- new framework-neutral `close_session(session)` helper (best-effort `ssh.close()`, teardown failures swallowed);
- `WxConnectionModel.connect_selected` and the wx worker both close the superseded session up-front; a failed re-attempt honestly ends `FAILED/DISCONNECTED`, never on a revived stale session.
- Independence: different finding, different root cause (missing reconnect teardown vs unwired failure notification), different files/layers, separately sensitivity-proven.

Out-of-scope routing: none (no cross-Wave defect found). Port-scoped host-key pins (`[host]:port`, OpenSSH behaviour) noted as observed semantics, not a defect.

## Requirement → implementation → test → evidence trace

Committed test module lab (integration class, NOT the EXTERNAL class): `tests/support/mock_ssh_server.py` loopback `127.0.0.1`/ephemeral port, fresh host key, fixture account only; real `paramiko` wire both ends. Auth method: password (fixture). Cleanup: every test closes wrapper/server; disposable roots under pytest `tmp_path`. This loopback evidence proves real-wire behavior but does NOT satisfy the EXTERNAL class (see FND-W11-AUDIT-001); the EXTERNAL class is satisfied separately by `EV-W11-EXT-001` against the authorized real lab below.

| Owned ID | Verdict | Live owner | Test(s) in `tests/test_w11_ssh_lifecycle.py` | Evidence |
|---|---|---|---|---|
| `SSH-001` transport-failure UI state | VERIFIED | `_controller_disconnect_cb` + `_emit_to_status` + `refresh_labels` | `test_transport_failure_drives_controller_out_of_connected` (DEF-W11-001), GUI-001, GUI-002 | `EV-W11-MATRIX-001`, `EV-W11-SENS-001` |
| `SSH-002` valid connection | VERIFIED | `SSHClientWrapper.connect/run` | `test_valid_connection_runs_remote_command` | `EV-W11-MATRIX-001` |
| `SSH-003` unreachable host | VERIFIED | `connect` error propagation, `client is None` | `test_unreachable_host_fails_without_session` | `EV-W11-MATRIX-001` |
| `SSH-004` invalid credentials | VERIFIED | `AuthenticationException`, no session | `test_invalid_credentials_are_rejected` | `EV-W11-MATRIX-001` |
| `SSH-005` first-contact policy | VERIFIED | `_KnownHostsPolicy` save/reject | `test_host_key_first_contact_save_and_reject` | `EV-W11-MATRIX-001` |
| `SSH-006` mismatch policy | VERIFIED | `BadHostKey → HostKeyChangedError` map, real round trip vs stale pin | `test_host_key_mismatch_is_refused` | `EV-W11-MATRIX-001` |
| `SSH-007` idle disconnect | VERIFIED | `close()` releases transport/client | `test_disconnect_while_idle_releases_transport` + DEF-W11-001 | `EV-W11-MATRIX-001` |
| `SSH-008` mid-op disconnect | VERIFIED | `run()` raises on dead transport (never false success) + shell `on_disconnect → close → notify` | `test_command_against_dead_transport_raises` + DEF-W11-001 | `EV-W11-MATRIX-001` |
| `SSH-009` reconnect | VERIFIED | `close` + fresh `connect_profile` | `test_reconnect_after_close_succeeds` | `EV-W11-MATRIX-001` |
| `SSH-010` repeated cycles / leak | VERIFIED | `close_session` on reconnect path; no live `hpc_gui_ssh_shell` threads after 5 cycles | `test_repeated_connect_disconnect_leaks_no_session_state` + `test_reconnect_closes_superseded_model_session` (DEF-W11-002) | `EV-W11-MATRIX-001`, `EV-W11-SENS-001` |
| `SSH-011` Unicode | VERIFIED | `_decode_remote_text` UTF-8 + shell echo round trip | `test_unicode_command_output_roundtrip` (`İstanbul_日本語_✓`) | `EV-W11-MATRIX-001` |

Mocking statement: `app_data_dir` + `load_system_host_keys` isolated to `tmp_path` (developer-machine independence); the SSH wire, auth, KEX, host-key verification, exec/shell/SFTP negotiation are all real. What this does NOT prove: trust decisions against the real user keyring (not claimed). Classification note (post-audit correction): this loopback module is integration/real-wire evidence only — it never was and is not claimed to be the EXTERNAL class.

## EXTERNAL evidence — authorized real lab (`EV-W11-EXT-001`)

Real-lab target per `docs/testing/LOCAL_HPC_LAB.md` + `devtools/lab/docker-compose.yml`: container `hpclab` (image `hpc-client-gui-lab:latest`), remote environment class **local containerized single-node Slurm** (Debian 13 trixie-slim, OpenSSH 10.0p2, Slurm 24.11.5, `debug*`+`short` partitions `idle` on node `hpclab`, `slurmctld UP`). Endpoint `127.0.0.1:2222` (loopback-published only), fixture account `hpctest`, auth method **password (fixture)** — the password was passed via `HPC_LAB_PASSWORD` env at runtime and appears in no file, log, or evidence artifact.

Provenance honesty: the container pre-existed this session (started 2026-09-16T11:36:33Z, `Up 3 days (healthy)` at resume time); it was NOT built by this Wave. Identity verified at evidence time via `docker inspect` (health `healthy`, ports `127.0.0.1:2222->22/tcp`), `docker exec hpclab sinfo` (`debug*`/`short` both `idle hpclab`), and `scontrol ping` (`Slurmctld(primary) at hpclab is UP`). Evidence run timestamp 2026-09-19T17:02:03+03:00. Client: Windows source runtime, Python 3.12.4, paramiko 3.5.1, product `SSHClientWrapper` (real code, isolated `known_hosts` in untracked temp dir). Main SHA `0f8902a023bac76071527232c2287af96478ed2b`, plugin SHA `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (read-only pin).

Script: `C:\Users\mskomek\AppData\Local\Temp\opencode\w11_ext_lab.py` (outside repo, untracked; secret never written to disk by the run). Exit 0. Result **12/12 PASS**: SSH-002 valid connect+exec, SSH-003 unreachable (closed port, no session), SSH-004 bad password (`AuthenticationException`, no session), SSH-005 first-contact save+reject round trip, SSH-006 stale pin refused (`HostKeyChangedError`), SSH-007 idle disconnect (transport released), SSH-008 mid-op death (raises, never false success), SSH-009 reconnect (close+fresh connect), SSH-010 five cycles (no live `hpc_gui_ssh_shell` threads), SSH-011 Unicode round trip (`İstanbul_日本語_✓`), disposable remote fixture dir `/home/hpctest/.w11-ext-fixture` (created, verified, removed), SSH-001 `disconnect_cb` wired and controller left `connected` for `failed` on transport death.

Cleanup: every wrapper closed; remote fixture dir removed (verified post-run: `test ! -e /home/hpctest/.w11-ext-fixture` → `FIXTURE_CLEANED`); local `known_hosts` in untracked temp only. The shared container was deliberately NOT torn down (`down -v` would destroy pre-existing shared state); post-run health still `healthy`, `sinfo` still `idle`. No Slurm job submitted (W11 owns SSH lifecycle only; jobs belong to W13 — not absorbed).

## Fix proof chains

Fix ID `FIX-W11-A` / Defect `DEF-W11-001` / Severity P1 / Independent root cause: unwired failure notification (`disconnect_cb=None`, no `emit`).
Before behavior/evidence: `EV-W11-BEFORE-001` (`C:\Users\mskomek\AppData\Local\Temp\opencode\w11_lab_before.py`, exit 0) — `wrapper._disconnect_cb = None`; after transport kill, controller `connected`, `DEF-W11-001 REPRODUCED`.
Files changed: `src/hpc_gui/wx_connection.py`. Regression test: `test_transport_failure_drives_controller_out_of_connected` (+ GUI-001/GUI-002). Sensitivity `EV-W11-SENS-001`: with the two product files stashed, the test FAILS (controller stuck `connected`); with fix restored it PASSES. Negative test: rejected-key + mismatch + dead-transport-`run()` cases. Narrow suite: file suite 14 passed. Broader: 45 + 105 (+9 subtests) + 30 passed (below). Runtime/manual: loopback lab 10 scenarios green. Package: N/A (no artifact bound). External: `EV-W11-EXT-001` real authorized lab (12/12 PASS; see EXTERNAL section). Residual risk: none known; exec-path death relies on caller-visible exceptions (truthful) plus shell-path notification.

Fix ID `FIX-W11-B` / Defect `DEF-W11-002` / Severity P1 / Independent root cause: missing reconnect teardown (session orphaned, never closed).
Before behavior/evidence: `EV-W11-BEFORE-001` — second `connect_selected()` left `session-1` unclosed, `DEF-W11-002 REPRODUCED`.
Files changed: `src/hpc_gui/services/connection_controller.py` (new `close_session`), `src/hpc_gui/wx_connection.py` (both connect paths). Regression test: `test_reconnect_closes_superseded_model_session`. Sensitivity `EV-W11-SENS-001`: FAILS pre-fix (old session unclosed), PASSES post-fix. Negative test: failed re-attempt ends FAILED/DISCONNECTED (no stale revival; covered by `connect_selected is False → fail` path + wx `done(error)` path). Narrow/broader suites: same as above. Residual risk: reconnect-while-connected drops a possibly healthy old session up-front — documented and honest (reconnect supersedes).

## Evidence ledger (exact counts)

| Evidence ID | Command | Exit | Result |
|---|---|---|---|
| `EV-W11-BASE-001` | `pytest test_connection_controller test_ssh_terminal_stream test_ssh_directory_listing_wire -q` (pre-edit) | 0 | 12 passed |
| `EV-W11-BEFORE-001` | `python w11_lab_before.py` (loopback lab, pre-fix) | 0 | both defects REPRODUCED (quoted above) |
| `EV-W11-MATRIX-001` | `pytest tests/test_w11_ssh_lifecycle.py -q` | 0 | **14 passed** (10 scenarios + 2 DEF regressions + 2 wx GUI), ~12 s |
| `EV-W11-SENS-001` | stash 2 product files → run 2 DEF tests → pop | — | **2 failed** pre-fix, **2 passed** post-fix (same tests) |
| `EV-W11-REG-001a` | `pytest test_w11_ssh_lifecycle test_connection_controller test_connection_profile_service test_connection_advanced_settings -q` | 0 | **45 passed** |
| `EV-W11-REG-001b` | `pytest test_wx_connection test_optional_ssh_credentials test_ssh_credential_flow test_ssh_jump_host test_wave3_remote_sftp_ssh test_ssh_terminal_stream test_ssh_directory_listing_wire test_ssh_files_byte_preservation -q` | 0 | **105 passed, 9 subtests passed** |
| `EV-W11-REG-001c` | `pytest test_wx_connection_71_2 test_wx_connection_71_3 test_wx_connection_71_4 test_wx_connection_71_5 -q` | 0 | **30 passed** |
| `EV-W11-GUI-001` | inside MATRIX: `test_wx_panel_reports_failed_connect_as_failed`, `test_wx_panel_transport_failure_repaints_status` (real `wx.App`+`Frame`, posted `EVT_LISTBOX`/`EVT_BUTTON`, pumped loop, clean teardown) | 0 | 2 passed |
| `EV-W11-DIFF-001` | `git diff --check` on W11 files; `git diff --stat`: 2 files, 95 insertions, 2 deletions; added-line secret scan clean | 0 | clean |
| `EV-W11-EXT-001` | `HPC_LAB_PASSWORD=<fixture-pw-per-LOCAL_HPC_LAB.md> python w11_ext_lab.py` (real lab `hpclab` 127.0.0.1:2222, product `SSHClientWrapper`, isolated known_hosts, disposable remote fixture dir) | 0 | **12/12 PASS** (SSH-001..011 + remote-fixture create/verify/remove), 2026-09-19T17:02:03+03:00; secret in env only, never in evidence |

New/modified tests: `tests/test_w11_ssh_lifecycle.py` (new, 14 tests: REQ-SSH-001…011 coverage + DEF regressions + wx GUI proof). Skipped/xfail changes: none. Test weakening: none.

Evidence classes: `GUI` satisfied by `EV-W11-GUI-001` (real wx event/runtime proof). `EXTERNAL` satisfied by `EV-W11-EXT-001` (authorized real lab: containerized single-node Slurm `hpclab` at 127.0.0.1:2222, environment identity + fixture-cleanup recorded; 12/12 PASS). The committed loopback module is supporting integration/real-wire evidence, not the EXTERNAL class. Package: N/A with justification (no owned row binds an artifact; no build-input change).

## POST_GREEN_REVIEW

- Duplicate path: Qt `login_widget` already wires `disconnect_cb` — untouched, unaffected. ✓
- Alternate entry points (button / double-click / context menu) share `connect_selected` — all covered by the same fix. ✓
- No silent fallback: `_emit_to_status` drops (never mis-touches UI) without an app; `_on_transport_failure` fails synchronously headless. ✓
- No stale state after cancel: cancel path unchanged; reconnect path now tears down up-front. ✓
- No wrong-identity capture: `close_session` only closes the superseded dict's `ssh`. ✓
- No new dead branch; no hardcoded provider behaviour; error text claims failure, never success. ✓
- No secret added to source/diff/logs/evidence (added-line scan clean). ✓

## Diff review

`git diff --check`: clean. `git diff --stat` (W11 files): `connection_controller.py` +25/-1, `wx_connection.py` +72/-2 (new test file untracked). Unrelated pre-existing dirty/untracked files preserved untouched; no generated/binary noise; no test weakening; no secret. One self-inflicted edit mishap during the session (joined `def` line) was immediately reverted via `git checkout --` and verified pristine before the real edits.

## Open findings

P0: none. P1: none open (both closed). P2/P3: none.

Repair cycle 1 (audit `FND-W11-AUDIT-001`, P1, fresh Luna audit 2026-09-19): the report had falsely classified the loopback `MockSSHServer` module as the EXTERNAL class. CURED this cycle — no product-code change needed (GUI/behavioral proof stood); the fix is evidential: `EV-W11-EXT-001` provides genuine real-lab EXTERNAL evidence (authorized containerized single-node Slurm `hpclab`, 12/12 PASS, identity + cleanup recorded), and every prior "loopback EXTERNAL" claim in this report has been reworded to integration/real-wire supporting evidence. No EXTERNAL_BLOCKED needed; the lab was available and truthfully exercised.

## Deviations

None — SFTP/Slurm scenarios explicitly left to W12/W13; no W12 work started.

## Rollback

Revert `src/hpc_gui/wx_connection.py` + `src/hpc_gui/services/connection_controller.py` and delete `tests/test_w11_ssh_lifecycle.py`; the two DEF regression tests fail on the reverted tree (proven by `EV-W11-SENS-001`), so rollback is detectable. No remote/persisted state to clean (loopback fixtures are per-test `tmp_path`; real-lab fixture dir `/home/hpctest/.w11-ext-fixture` already removed and verified; shared `hpclab` container left running healthy as found).

## Resume state

Completed and verified: all 11 SSH rows; FIX-A + FIX-B with before/after/sensitivity evidence; 14-test suite green; broader slices green; GUI proof green; EXTERNAL class satisfied by `EV-W11-EXT-001` real-lab run (12/12, 2026-09-19T17:02:03+03:00, fixture cleaned, container left healthy); report current.
In progress: nothing. Open P0/P1: none. Open P2/P3: none. Pending tests/evidence: none (audit is a separate fresh-context step).
Last exact commands run: `pytest tests/test_w11_ssh_lifecycle.py -q` → 14 passed; broader slices → 45 / 105+9 / 30 passed; `HPC_LAB_PASSWORD=<fixture-pw> python w11_ext_lab.py` → 12/12 PASS exit 0; remote cleanup verified (`FIXTURE_CLEANED`), lab still `healthy`/`idle`; `git diff --check` → clean.
Next actions: fresh-context `/wave-audit W11`; then W12 may be planned (never auto-started).
Evidence/artifact identities: `EV-W11-BASE-001`, `EV-W11-BEFORE-001`, `EV-W11-MATRIX-001`, `EV-W11-SENS-001`, `EV-W11-REG-001a/b/c`, `EV-W11-GUI-001`, `EV-W11-DIFF-001`, `EV-W11-EXT-001`; main HEAD `0f8902a0`, plugin `f0abb7e7`.

```text
FIX-A: wire transport-failure notification (disconnect_cb + controller emit + failed-label retention)
DEF: DEF-W11-001 (P1, controller/UI stuck "connected" after transport death)
Root cause: connect_profile never passed disconnect_cb; no controller transition repainted wx status
Before EV: EV-W11-BEFORE-001 (cb None, state stays connected)
After EV: EV-W11-MATRIX-001 (14 passed incl. DEF regression + 2 wx GUI proofs)
Regression test: test_transport_failure_drives_controller_out_of_connected
Sensitivity proof: EV-W11-SENS-001 (fails pre-fix, passes post-fix)

FIX-B: tear down superseded session on reconnect (close_session, both connect paths)
DEF: DEF-W11-002 (P1, reconnect orphaned previous live session)
Root cause: no teardown of controller.session before new attempt
Before EV: EV-W11-BEFORE-001 (old session never closed)
After EV: EV-W11-MATRIX-001
Regression test: test_reconnect_closes_superseded_model_session
Sensitivity proof: EV-W11-SENS-001 (fails pre-fix, passes post-fix)

Additional fixes: none (floor met with the two highest-ranked P1 findings)
Post-green review: PASS (recorded above)
New/modified tests: tests/test_w11_ssh_lifecycle.py (14 new)
Skipped/xfail changes: none
Package evidence: N/A (justified)
External evidence: EV-W11-EXT-001 real authorized lab (hpclab 127.0.0.1:2222, 12/12 PASS incl. SSH-001..011 + fixture cleanup; loopback module is supporting integration evidence only)
Open P0/P1: none
Open P2/P3: none
Two-fix gate: PASS (W03-specific: two real-integration remediations, non-mock)
Wave decision: GO
```
