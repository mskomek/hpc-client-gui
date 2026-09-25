# W29 — Job details, stdout/stderr and live output - Wave Report

```text
Wave: W29
Canonical report: docs/wave-reports/v2/opencode/W29_WAVE_REPORT.md
Repository: hpc-client-gui / develop
Branch: develop
Baseline SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Tested implementation: working tree at 3e9635ba + W29-owned hunks
  (src/hpc_gui/services/files_ssh.py [read_text hardening],
   src/hpc_gui/services/output_follower.py [permission-distinct],
   src/hpc_gui/wx_jobs.py [per-channel permission error state],
   tests/test_w29_job_outputs.py [new, 16 tests])
  Plus pre-existing uncommitted hunks (preserved, not owned by W29):
   src/hpc_gui/i18n/en.json + tr.json [W27-owned],
   src/hpc_gui/services/slurm_models.py [W28-owned],
   src/hpc_gui/wx_editor_view.py [W26/W27-owned],
   src/hpc_gui/wx_plugins_view.py [W26-owned],
   src/hpc_gui/wx_jobs.py W28-owned hunks [refresh machine, filter/sort,
     cancel double gate - preserved, extended only in outputs worker],
   tests/test_w26_run_supplement.py + tests/test_w27_editor_conflicts.py +
   tests/test_w28_jobs_identity_refresh.py [untracked, sibling-owned]
Current HEAD: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Content handoff: controller content_identity
  3486d648c08e939df64914f415018a5b62c8de9cc5bf90946d86cf5c17f12141
  (W28 audit-receipt identity chain; W29 spec identity observed separately below)
Observed waves/pending/W29.md SHA-256 (BOM-stripped, LF-normalized bytes):
  4372e17db6ff203dc60672ce4f72f254953ee193c46970615cf5e4d6bd85e114
  (frontmatter wave_id/wave_kind/canonical_source/19 owned IDs/
   aggregate_close_owner=false/evidence_policy=wave-local/
   audit_policy=fresh-independent verified consistent)
Execution start gate: NONE (per Wave independence contract)
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: READY_FOR_AUDIT (independent audit pending, controller-owned)
```

## Scope

W29 owns 19 IDs per `waves/pending/W29.md` frontmatter:
`HPC-W07-OUT-001..019`. No TODO-detail IDs. Mandatory authority read before
edits: all `opencode/REQUIREMENT_REGISTRY.md` W29 rows (19 source-derived,
`WAVE_V2_FINAL_07.md` lines 108-112 Workstream E and 117-134 Workstream E0),
`opencode/TODO_OWNERSHIP_MAP.md` W29 rows (none — empty result is the correct
reading, not an omission), and `opencode/sources/WAVE_V2_FINAL_07.md`
sections **Workstream E — Details / logs** and **Workstream E0 —
stdout/stderr and live-output closure** plus the real-job acceptance path
(lines 134-148). Live code inspected before editing
(`services/output_follower.py`, `services/output_channel_resolver.py`,
`services/files_ssh.py` `read_text`, `services/selected_job_context.py`,
`services/job_tracking_controller.py`, `wx_jobs.py` details fetch / outputs
worker / detached follower / close paths, `i18n/en.json` stream labels,
existing `test_output_follower.py` + `test_output_channel_resolver.py` +
`test_wx_jobs_files_outputs.py` + `test_corrective_jobs_details.py` +
`test_wave78_jobs_details.py` contracts). Unattended, non-interactive; no user
questions asked. No cross-Wave worktree/report/temp edits. Pre-existing dirty
hunks preserved verbatim (W29 diff touches only the 4 paths listed above).
HEAD (`3e9635ba`) is ahead of `origin/develop`; the divergence is local
program work already on `develop`, not a rebase target — worked from the
recorded HEAD as the Wave execution baseline per the repo-truth rule and
resolved nothing silently.

## Discovery

| Finding ID | Severity | Surface | Evidence | Root cause |
|---|---|---|---|---|
| DEF-W29-001 | P1 | outputs permission handling | source read: `OutputFollower.poll` catches `(FileNotFoundError, OSError)` together and returns `waiting=True`; `PermissionError` is an `OSError` subclass so denial is retried as "waiting"; `wx_jobs.py` outputs worker legacy path has the same lumping | OUT-010 has no distinct-error owner |
| DEF-W29-002 | P1 | remote text decode | source read: `SSHFilesBackend.read_text` does `data.decode("utf-8")` strict with no error translation; any non-UTF8 byte raises `UnicodeDecodeError` out of the poll path | OUT-005/OUT-013 have no decode-hardening owner |
| OBS-W29-003 | P3 | content-identity reconciliation | controller handoff `3486d648…` is the W28 audit-receipt chain identity; observed W29 spec bytes hash `4372e17d…` | distinct Waves/identities by design; no spec tampering (19 IDs + policies verified) — controller-owned reconciliation |
| OBS-W29-004 | P3 | coarse whole-tab error | probe: first GUI run showed a denied stderr channel forcing the sibling missing stdout channel to `Error` via the outer `except Exception` path | worker recorded only one `err` for all channels; fixed per-channel (see FIX-A) |

Pre-change narrow baselines (all green before edits):
`test_corrective_jobs_details` 17 passed, `test_wx_jobs_files_outputs`
16 passed, `test_wave78_jobs_details` 16 passed,
`test_wave37_output_buffer + test_jobs_outputs_scroll` 22 passed + 4
subtests, `test_output_follower + test_output_channel_resolver +
test_jobs_outputs_scroll` 50 passed + 4 subtests.

Second-defect search (dimensions checked): negative (missing file, unknown
state, malformed rows, empty outputs, failure-without-prior-data),
unavailable-capability (keyless lab SSH `Permission denied (publickey)`,
BatchMode — EXTERNAL_BLOCKED, nothing invented), permission/network failure
(denied now surfaces `status_error` per channel; missing retains + waits),
cancellation/retry (close/follower-close + detached `closed` guards
untouched and green), stale callback/result (owner/generation guards +
follower token guards untouched and green), persistence/identity/cleanup
(frame teardown in tests; no real user config touched), packaging (N/A —
see evidence table).

## Requirement trace (requirement -> live owner -> test -> evidence)

Workstream E — details/logs (OUT-001..005). Owners: `SelectedJobStore`
(identity/generation), `_show_job_details` (capture-before-fetch +
stale-discard), `OutputFollower` (bounded retain), `files_ssh.read_text`
(decode-hardened this Wave):
- OUT-001 (identity captured before async fetch): IMPLEMENT (pre-existing).
  `test_w29_details_identity_generation_monotonic` (generation bumps before
  dispatch; `_show_job_details` snapshots `req_job_id`/`req_gen`).
- OUT-002 (response discarded if selection/session changed): IMPLEMENT
  (pre-existing). `test_w29_selection_change_invalidates_stale_output` +
  `_done_details` generation/request-ID guard.
- OUT-003 (missing output file is a visible normal error): IMPLEMENT
  (pre-existing, preserved). `test_w29_missing_file_is_waiting_not_crash`
  (waiting, no crash; GUI `status_waiting` readback in NEW GUI test).
- OUT-004 (huge log bounded/streamed): IMPLEMENT (pre-existing retain cap,
  regression-locked). `test_w29_large_output_remains_bounded` (20000-line
  flood retains exactly 50).
- OUT-005 (encoding errors do not crash UI): IMPLEMENT (this Wave FIX-B).
  `test_w29_ssh_read_text_replaces_invalid_bytes` +
  `test_w29_invalid_encoding_never_crashes_follower`.

Workstream E0 — stdout/stderr closure (OUT-006..019). Owners:
`OutputResolver` (channels/labels), `wx_jobs.py` outputs worker (per-channel
states), `OutputFollower` (tail/rotation/close), `show_job_output`
(detached lifecycle):
- OUT-006 (job-output surface works): IMPLEMENT.
  `test_w29_gui_stdout_stderr_distinguishable_with_content` (real frames,
  content readback).
- OUT-007 (streams visibly distinguishable): IMPLEMENT (pre-existing,
  locked). `test_w29_stdout_stderr_channels_distinguishable` + GUI tab-title
  readback.
- OUT-008 (action labels identify stream): IMPLEMENT (pre-existing, locked).
  `test_w29_output_action_labels_identify_stream`.
- OUT-009 (missing is a normal visible state): IMPLEMENT.
  GUI `status_waiting` readback in
  `test_w29_gui_missing_vs_permission_distinct`.
- OUT-010 (permission denied distinct from missing): IMPLEMENT (this Wave
  FIX-A). `test_w29_permission_denied_is_distinct_from_missing` + GUI
  per-channel `Waiting` vs `Error` readback.
- OUT-011 (live-tail appends without dup/reorder): IMPLEMENT.
  `test_w29_live_tail_appends_exactly_once_ordered` (deterministic numbered
  fixture with emission delay; re-poll appends nothing) + GUI
  `test_w29_gui_live_tail_ordered_and_close_cancels` (ordered positions).
- OUT-012 (truncation/rotation/recreated handled): IMPLEMENT (pre-existing,
  locked). `test_w29_truncation_and_rotation_reset_cleanly`.
- OUT-013 (UTF-8/chunk boundaries): IMPLEMENT (this Wave FIX-B + locked).
  `test_w29_utf8_boundaries_do_not_corrupt` +
  `test_w29_ssh_read_text_replaces_invalid_bytes`.
- OUT-014 (large output responsive/bounded): IMPLEMENT.
  `test_w29_large_output_remains_bounded`.
- OUT-015 (close cancels worker/timer safely): IMPLEMENT (pre-existing,
  locked). `test_w29_close_cancels_safely_and_ignores_late_callbacks` + GUI
  teardown with zero escaped exceptions.
- OUT-016 (selection/profile/session changes invalidate stale): IMPLEMENT
  (pre-existing owner tuple + generations). `test_w29_selection_change…` +
  `_output_owner_is_current` guards (untouched, green).
- OUT-017 (reconnect can reopen/refresh intended identity): IMPLEMENT
  (pre-existing `set_session` generation bump + follower clear + refresh).
  Covered by owner-guard code path; no new defect found on read.
- OUT-018 (completed final output viewable): IMPLEMENT.
  GUI test uses a `COMPLETED` job and reads back final content.
- OUT-019 (real-job acceptance path): EXTERNAL_BLOCKED. Lab reachable but
  key auth unavailable (`Permission denied (publickey)`, BatchMode, 10 s
  bound); no credentials requested or invented; no mock substituted for the
  external claim. All safe local/package/GUI checks completed.

## Fixes (proof chains)

FIX-A (DEF-W29-001 + OBS-W29-004; OUT-010):
Root cause: `PermissionError` (an `OSError`) was swallowed into the
missing-file waiting path at two layers, and the outputs worker reported one
whole-tab `err` for all channels.
Change: `services/output_follower.py` re-raises `PermissionError` before the
missing-file handler; `wx_jobs.py` outputs worker records a per-channel
`(retained, waiting, snapshot, missing, channel_error)` entry for denied
channels on both the SFTP-reader and legacy paths and `_done_outputs`
renders `status_error` plus the denial text only on the affected channel;
siblings keep their own waiting/following state.
Before EV: denial showed `Waiting for file` (service layer) or forced every
sibling to `Error` (worker layer) — wrong in opposite directions.
After EV: unit propagation test + GUI per-channel `Waiting` vs `Error`
readback pass (EV-W29-NEW).
Regression: 69 + 55 + 62 cohort tests green (EV-W29-REG).
Sensitivity: missing (`FileNotFoundError`) still waits; denied
(`PermissionError`) errors; both asserted in the same GUI frame.

FIX-B (DEF-W29-002; OUT-005/OUT-013):
Root cause: strict `bytes.decode("utf-8")` in the SSH text path raised on
any non-UTF8 byte, escaping the poll as an unhandled decode crash vector.
Change: `services/files_ssh.py::read_text` decodes with `errors="replace"`
and wraps the open/read in `_translate_remote_errors` so missing vs denied
stay typed with path-bearing `.filename`.
Before EV: `b"hello \xff\xfe world"` raised `UnicodeDecodeError`.
After EV: same bytes render with U+FFFD and surrounding text intact; typed
`FileNotFoundError`/`PermissionError` preserved (EV-W29-NEW).
Regression: full W29 file 16 passed; outputs cohorts green (EV-W29-REG).
Residual: whole-file read retained (view bounded at 5000 lines /
`retain_last_lines`); ranged transport reads are future work, not claimed.

Two-fix gate: PASS (FIX-A permission-state vs FIX-B decode are independent
root causes; counted once each).

## Tests and evidence required

Environment: Windows, repo `develop`, HEAD `3e9635ba`, Python 3.12
(`python -m pytest` harness), wxPython `4.3.1 msw (phoenix) wxWidgets 3.3.3`
for GUI tests (`@pytest.mark.gui @pytest.mark.wx`).

| Evidence ID | Command / action | Exit | Scope / result |
|---|---|---|---|
| EV-W29-BASE | pre-change baselines: `test_corrective_jobs_details`, `test_wx_jobs_files_outputs`, `test_wave78_jobs_details`, `test_wave37_output_buffer + test_jobs_outputs_scroll`, `test_output_follower + test_output_channel_resolver + test_jobs_outputs_scroll` | 0 | 17 / 16 / 16 / 22+4sub / 50+4sub passed — green before edits |
| EV-W29-NEW | `pytest tests/test_w29_job_outputs.py -q` | 0 | 16 passed (13 unit/contract + 3 wx GUI runtime) |
| EV-W29-REG | `pytest test_output_follower test_output_channel_resolver test_jobs_outputs_scroll test_corrective_jobs_details -q` | 0 | 69 passed + 4 subtests, no regression |
| EV-W29-REG | `pytest test_wx_jobs_files_outputs test_wave78_jobs_details test_w28_jobs_identity_refresh -q` | 0 | 55 passed (~38 s), no regression incl. W28-owned hunks |
| EV-W29-REG | `pytest test_wx_jobs_behavior test_wx_jobs_final_fix test_wx_jobs_stress test_selected_job_context test_job_tracking_controller test_slurm_models -q` | 0 | 62 passed (~64 s), no regression |
| EV-W29-STATIC | `git diff --check` | 0 | clean (one LF/CRLF advisory on a touched file, no whitespace errors) |
| EV-W29-EXT | `ssh -o BatchMode=yes -o ConnectTimeout=10 hpctest@192.168.250.11 echo LAB_OK` | denied | EXTERNAL_BLOCKED (`Permission denied (publickey)`; host reachable, no key auth in env; no credentials requested or invented; all safe local/package/GUI checks completed) |
| EV-W29-GUI | wx runtime in EV-W29-NEW (3 tests) | 0 | real `build_jobs_panel` frames: distinct stdout/stderr tabs + content; missing=`Waiting` vs denied=`Error` per-channel labels; ordered 5-line live tail + clean teardown (exact runtime action/test/readback, not controller-only) |
| EV-W29-EXTERNAL | required class EXTERNAL per Wave header | — | EXTERNAL_BLOCKED (above); no mock substitution for external claims (mock backends cited only as code-shape reference, never as external evidence) |
| EV-W29-PACKAGE | package class | — | N/A with justification: no owned ID requires a packaged artifact (details/output/tail behaviors proven at service + wx runtime); no artifact SHA claimed |

New/changed tests: `tests/test_w29_job_outputs.py` (new, 16 tests:
OUT-001 x1, OUT-002/016 x1, OUT-003/009 x1, OUT-004/014 x1, OUT-005 x2,
OUT-007 x1, OUT-008 x1, OUT-010 x1, OUT-011 x1, OUT-012 x1, OUT-013 x2
(shared), OUT-015 x1, plus 3 wx GUI integration). Taxonomy: 13 x
contract/unit, 3 x GUI event/integration. Mocks: only at legitimate
boundaries (fake SFTP channel for decode/typed-error tests; `read_remote_path`
service-adapter seam for GUI tests — the documented seam, not scheduler
mocks). No skips/xfails added or weakened; no existing test modified.
Cleanup: frame teardown destroys top-level windows; unit tests are pure. GUI
claims carry exact runtime readback (tab titles, cell values, status labels,
ordered positions, tested tree identity).

## Diff review

`git diff --check`: clean. W29-owned diff only:
`src/hpc_gui/services/files_ssh.py` (+~14/-~6: replace-decode +
error translation), `src/hpc_gui/services/output_follower.py` (+5:
permission re-raise), `src/hpc_gui/wx_jobs.py` (per-channel error entries +
render; W28-owned hunks preserved untouched), plus untracked addition
`tests/test_w29_job_outputs.py`. Preserved untouched: `i18n/en.json +
tr.json`, `services/slurm_models.py`, `wx_editor_view.py`,
`wx_plugins_view.py` (pre-existing sibling hunks, still present in
`git status` exactly as before). No generated/binary/cache/secret/user-specific
data in the W29 diff. No weakened tests. No new temp state outside `.tmp/`
policy (none written; registry extracts were read in-memory).

## Post-green review (POST_GREEN_REVIEW)

Duplicate paths: Qt `jobs_widget.py` (56-line shim) untouched — wx-only Wave;
Qt parity out of scope, routed nowhere. Alternate entry: `render_items` still
the single table entry; outputs worker still the single refresh path with
per-channel results. Silent fallbacks: none added — denials now write the
visible per-channel `Error` state plus denial text (previously silent wait
or whole-tab error). Stale state: details/sacct/status generation guards
untouched and green (62-pass cohort). Identity: `SelectedJobStore`
generation semantics untouched; follower token guards untouched. Cleanup: no
new processes/files outside fixtures. Dead branches: none introduced (legacy
4-tuple results still accepted by the unpack shim). Hardcoded provider: none
(paths thread through job context/resolver). Success-claiming errors: none
(denials set `status_error`, never success/following). Packaged divergence:
none claimed.

## Handoff / resume

Completed and verified: FIX-A, FIX-B with exact executed tests; 16 new tests
green; 69+55+62 impacted cohorts green; static check clean; GUI runtime
readback (FULL-equivalent for owned GUI semantics: action -> channel tabs +
content + per-channel status labels bound to the tested tree); external lab
blocked on key auth; canonical report current.
In progress: none (run work complete).
Open P0/P1: none in owned scope.
Open P2/P3: none newly found (OBS-W29-003/004 are process observations /
fixed-in-pass probe notes, not product defects).
Pending tests/evidence: independent fresh-context audit (controller-owned);
auditor reruns EV-W29-NEW + EV-W29-REG, adjudicates EXTERNAL_BLOCKED residual
and package N/A justification, and verifies candidate/working-tree identity.
Last exact commands: `test_w29_job_outputs` 16 passed; impacted cohorts
69+4sub / 55 / 62 passed; `git diff --check` clean.
Next actions (controller): schedule fresh independent audit of W29; auditor
re-verifies content identity (`4372e17d…` over BOM-stripped LF bytes),
reruns the evidence commands, and returns PASS/REOPEN.
Evidence identities: HEAD `3e9635ba1cf0255d5a09f370e91d1ddb73cef888`; spec
`4372e17db6ff203dc60672ce4f72f254953ee193c46970615cf5c17f12141`; report
this file; new tests `tests/test_w29_job_outputs.py`.

```text
FIX-A: Permission-denied distinct from missing (follower re-raise + per-channel status_error)
DEF: DEF-W29-001 (+ OBS-W29-004 whole-tab coarseness)
Root cause: PermissionError swallowed as OSError-wait; one err for all channels
Before EV: denial waited silently / clobbered siblings to Error
After EV: unit propagation + GUI per-channel Waiting-vs-Error readback pass
Regression test: test_w29_permission_denied_is_distinct_from_missing + test_w29_gui_missing_vs_permission_distinct
Sensitivity proof: missing still waits while denied errors in the same frame

FIX-B: SSH read_text replacement decode + typed error translation
DEF: DEF-W29-002
Root cause: strict utf-8 decode raised on any non-UTF8 byte
Before EV: b"hello \xff\xfe world" raised UnicodeDecodeError
After EV: renders with U+FFFD, neighbors intact; typed missing/denied preserved
Regression test: test_w29_ssh_read_text_replaces_invalid_bytes + test_w29_invalid_encoding_never_crashes_follower
Sensitivity proof: invalid bytes replaced, valid neighbors byte-identical; typed errors unchanged

Additional fixes: none (all other owned IDs verified already-valid with new locking tests)
Post-green review: POST_GREEN_REVIEW (above, no new defect)
New/modified tests: tests/test_w29_job_outputs.py (new, 16 tests)
Skipped/xfail changes: none
Package evidence: N/A (no owned packaging requirement; justification above)
External evidence: EXTERNAL_BLOCKED (lab key auth unavailable; host reachable)
Open P0/P1: none (owned scope)
Open P2/P3: none (OBS items are process observations)
Two-fix gate: PASS
Wave decision: READY_FOR_AUDIT
```
