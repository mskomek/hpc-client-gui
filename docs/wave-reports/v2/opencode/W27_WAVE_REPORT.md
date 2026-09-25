# W27 — Editor conflicts, content edge cases and package acceptance - Wave Report

```text
Wave: W27
Canonical report: docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
Repository: hpc-client-gui / develop
Branch: develop
Baseline SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Tested implementation: working tree at 3e9635ba + W27-owned hunks
  (src/hpc_gui/wx_editor_view.py [find/previous+case/wrap/status, stale-open
   sequencing, initial-binary refusal + save block],
   src/hpc_gui/i18n/en.json + tr.json [9 new editor keys],
   tests/test_w27_editor_conflicts.py [new, 11 tests])
  Plus pre-existing uncommitted W26 hunks (preserved, not owned by W27):
  src/hpc_gui/wx_editor_view.py [find/replace bar + helpers],
  src/hpc_gui/wx_plugins_view.py [compat/enabled details],
  tests/test_w26_run_supplement.py [untracked, W26-owned]
Current HEAD: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Content handoff: controller content_identity
  0869b586b8abcbd89cf9b5b771e3d104ff47997faa6487ea4fe259f7033f27ae;
  observed waves/pending/W27.md SHA-256 (raw LF bytes, no BOM):
  0b3a36b2138f2f933c79b3224c977b0c43f608286c1abb40d9dd4e34ed625f93
  (see OBS-W27-005; frontmatter IDs/counts/policies verified consistent)
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: READY_FOR_AUDIT (independent audit pending, controller-owned)
```

## Scope

W27 owns `HPC-W06-EDITX-001..050` plus TODO-detail `HPC-W11-TODO-002` per
`waves/pending/W27.md` frontmatter (50 + 1 = 51 IDs).
Mandatory authority read before edits: all `opencode/REQUIREMENT_REGISTRY.md`
W27 rows (51), the single `opencode/TODO_OWNERSHIP_MAP.md` W27 row
(`HPC-W11-TODO-002`, ACTIVE), and `opencode/sources/WAVE_V2_FINAL_06.md`
sections **Workstream H — Find/replace**, **Workstream I — Binary/large-file
guard**, **Targeted tasks**, **Test matrix**, **Acceptance criteria**,
**P0 examples**. Live code inspected before editing
(`wx_editor_view.py`, `services/editor_controller.py`, `wx_editor.py`,
`wx_shell.py` editor factory, `wx_local_files.py`, `wx_remote_files_view.py`,
`wx_transfer_workspace.py`, `i18n/en.json` + `tr.json`).
Unattended, non-interactive; no user questions asked. No cross-Wave
worktree/report/temp edits. Pre-existing W26 dirty hunks preserved verbatim
(stash pop verified byte-identical via `git status` + rerun).

## Discovery

| Finding ID | Severity | Surface | Evidence | Root cause |
|---|---|---|---|---|
| DEF-W27-001 | P1 | wx find/replace: previous | source read: `_build_editor` exposes `_wx_find_next` only; no previous control, helper, or i18n key | Workstream H half-implemented (EDITX-001 requires next/previous) |
| DEF-W27-002 | P2 | wx find/replace: case option | source read: no case toggle in bar/controls/i18n; `str.find` always case-sensitive with no user control | EDITX-005/042 have no UI option to match |
| DEF-W27-003 | P1 | async editor-open ordering | source read: `load_document` comment `handle stale: if in-flight, queue? For now direct open`; any late open unconditionally replaces model/tabs/buffer | no request sequencing (TODO-002 open defect) |
| DEF-W27-004 | P2 | binary guard bypass | source read: `editor_binary_guard_reason` enforced only in `load_document`; initial `_build_editor(path, content)` path sets the value with no guard, and nothing blocks saving refused content | guard not applied to the initial-open path |
| OBS-W27-005 | P3 | content-identity reconciliation | controller handoff `0869b586…`; observed file bytes hash `0b3a36b2…` under raw/CRLF/frontmatter normalizations | controller snapshot serialization differs; frontmatter IDs (50+1), counts, policies verified consistent — no spec tampering; controller-owned reconciliation |
| OBS-W27-006 | P3 | combined-process wx crash | `test_wx_editor.py + test_editor_flow.py` in one pytest process crashes identically on stashed-HEAD product code | pre-existing harness fragility (wx App lifecycle), not a W27 regression; suites run in compatible batches |

Pre-change narrow baseline: `test_w26_run_supplement -k find_replace`
`1 passed`; `test_w26_editor_identity + test_wx_editor_tabs +
test_editor_controller` `26 passed`.

Second-defect search (dimensions checked): negative (empty/no-match queries,
refused binary save), lifecycle (stale open, tab activate vs open, save-as
cancel), stale state (FIX-B), identity (session-pin refusal cited from W26,
canonical_key local-vs-remote), concurrency (save `in_flight` guard cited),
boundary (2 MiB guard, NUL detection, Unicode model test cited), capability
absence (header buttons disabled without callback, new test), persistence
(disk-baseline external-change prompt cited), packaging (fresh wheel + smoke),
error visibility (all find/replace no-ops write the status line), context
menus (49-test cohort green), adjacent boundary (shell `save_remote`
unavailable raises visibly, `_editor_action_factory`).

## Requirement trace (requirement -> live owner -> test -> evidence)

Workstream H (EDITX-001..008) — owner: `_build_editor` find bar
(`find_in`/`replace_in`/`find_next`/`find_prev`/`match_case`/`replace`/
`replace_all`) + `_wx_find_next`/`_wx_find_previous`/`_wx_replace_current`/
`_wx_replace_all` + status readback:
- EDITX-001 (next/previous): IMPLEMENT. `test_w27_find_next_previous_wrap_and_selection`.
- EDITX-002 (wrap): IMPLEMENT. Same test; wrap returns to top/bottom *and*
  writes `find_wrapped_top/bottom` to the status line.
- EDITX-003 (replace current): IMPLEMENT. `test_w27_replace_current_advances_and_marks_dirty`.
- EDITX-004 (replace all): IMPLEMENT. `test_w27_match_case_toggle_controls_find_and_replace`,
  `test_w27_match_case_insensitive_replace_all`, `test_w27_replace_all_no_match_is_visible_noop`.
- EDITX-005 (case option): IMPLEMENT (FIX-A exposes `Match case` checkbox).
  Case-sensitive and insensitive proofs above.
- EDITX-006 (empty search): IMPLEMENT. `test_w27_find_empty_query_is_visible_noop`
  (all four ops diagnosed no-ops, document untouched, still clean).
- EDITX-007 (selection): IMPLEMENT. Selection assertions in the wrap test.
- EDITX-008 (dirty after replace): IMPLEMENT. Dirty assertions in replace tests.

Workstream I (EDITX-009..011) — owner: `editor_binary_guard_reason` +
`load_document` refusal + NEW initial-open refusal + save block:
- EDITX-009/010/011: IMPLEMENT. Existing `test_w26_binary_and_large_guard_reasons`,
  `test_w26_wx_binary_content_refused_with_visible_diagnostic`, plus new
  `test_w27_initial_binary_content_refused_and_save_blocked` (refused content
  never enters the control, save blocked with diagnostic, safe load restores).

Targeted tasks (EDITX-012..021):
- EDITX-012 (menu inventory): IMPLEMENT. Trace: `wx_local_files.py:548/627-628`
  context menu, `wx_remote_files_view.py:132/148/453/728/937/1307` context
  menus, editor header `_update_header_enabled` (buttons disabled without a
  real callback). Proof: `test_wx_file_context_i18n` (local/remote reopen),
  new `test_w27_editor_header_buttons_truthfully_enabled` /
  `test_w27_editor_header_open_enabled_with_callback`.
- EDITX-013 (path semantics): IMPLEMENT (no change; proven). Owner
  `DocumentModel.canonical_key` (local lower-normalized, remote exact POSIX
  with provider/profile/session). Proof: existing W26 local-vs-remote
  distinction test + `test_w26_wx_same_path_other_session_opens_distinct_tab`.
- EDITX-014 (overwrite/delete cancel): IMPLEMENT. Editor half:
  `_confirm_save_as` + new `test_w27_save_as_cancel_is_side_effect_free`
  (disk + dirty + status). Remote half: existing
  `test_wx_remote_delete_confirmation_cancel_preserves_selection`.
- EDITX-015 (transfer transitions): IMPLEMENT (no change; proven by sibling
  service). Proof: `test_download_cancel_wire` 4 passed (cancel keeps partial
  + session usable, resume completes, overwrite/skip policies).
- EDITX-016 (identity/dirty/save): IMPLEMENT. FIX-A/C + new tests + W26
  dirty/save groundwork (all green in batch A).
- EDITX-017 (reconnect/profile drift): IMPLEMENT (no change; proven). Owner:
  session-pinned `save_remote` refusal (`wx_shell.py:2610`). Proof: existing
  `test_w26_wx_connection_switch_blocks_remote_save`.
- EDITX-018 (find/replace regressions): IMPLEMENT. 6 new find/replace tests
  + sensitivity proof (8 fail pre-fix / 8 pass post-fix).
- EDITX-019 (binary/large safeguards): IMPLEMENT. FIX-C + guard tests above.
- EDITX-020 (real SFTP round-trip): EXTERNAL_BLOCKED. Lab host
  `192.168.250.11:22` reachable but key auth unavailable in this environment
  (`Permission denied (publickey)`, BatchMode); no credentials requested or
  invented. All safe local/package/GUI checks completed.
- EDITX-021 (packaged acceptance): IMPLEMENT with noted residual. Fresh wheel
  built from the candidate tree with Python 3.14:
  `.tmp/w27_pkg/hpc_client_gui-1.5.9-py3-none-any.whl`,
  SHA-256 `be2bbf81f24d65612320be9c66f7408b2c48268d2d69d4d7ae5032a59b81d5b8`;
  packaged smoke (installed wheel: guard reasons + all four W27 seams present)
  PASS. Full installer-launch workflow is audit-residual.

Test matrix (EDITX-022..034): 022 header row N/A (structural). 023 local
browse/actions: automated gui yes (`test_wx_file_actions_behavior` cohort in
the 49-pass run). 024 remote browse/actions: automated yes (same cohort);
real-SFTP dimension EXTERNAL_BLOCKED. 025 context menus: GUI/event yes
(`test_wx_file_context_i18n`); representative SFTP EXTERNAL_BLOCKED. 026
upload/download: yes (`test_download_cancel_wire` + transfer gate in the
49-pass run); SFTP EXTERNAL_BLOCKED. 027 overwrite cancel: yes (new Save-As
cancel test + remote delete-cancel test); SFTP EXTERNAL_BLOCKED. 028
transfer cancel: yes (4 download-cancel tests); SFTP EXTERNAL_BLOCKED. 029
local editor save: yes (W26 save-as/CRLF tests, green). 030 remote editor
save: yes mocked-service (W26 server-content test); SFTP EXTERNAL_BLOCKED.
031 dirty close: yes/GUI (W26 close/dirty groundwork green; save paths
covered). 032 reconnect+remote tab: yes mocked (W26 switch-blocks-save);
SFTP EXTERNAL_BLOCKED. 033 find/replace: yes (11 new W27 tests). 034
binary/large guard: CONDITIONAL branch active (guard implemented + refused):
yes local/GUI; SFTP optional not exercised (EXTERNAL_BLOCKED).

Acceptance gates (EDITX-035..046): 035 menus truthfully enabled — VERIFIED
(context-menu cohort + header enablement tests). 036 path semantics —
VERIFIED (canonical_key + distinction tests). 037 cancel side-effect free —
VERIFIED (Save-As cancel + delete cancel + download cancel tests). 038
failure/cancel never shows success — VERIFIED (status diagnostics on every
no-op/refusal; transfer cancel states keep session usable). 039 dirty
accuracy — VERIFIED (replace/find tests assert dirty both ways; failed-save
dirty cited from W26 disconnect test). 040 remote save targets intended
profile/path — VERIFIED (W26 session-pin refusal test). 041 failed save
recoverable — VERIFIED (W26 disconnect test asserts dirty + content kept;
Save-As cancel test asserts the same locally). 042 find/replace matches UI
options — VERIFIED (Match-case toggle governs both ops under test). 043
binary/large safe — VERIFIED (refusal + save block + restore tests). 044
real SFTP round trip — EXTERNAL_BLOCKED (see EDITX-020). 045 packaged
artifact representative workflow — PARTIAL (fresh wheel + packaged smoke
PASS; installer-launch residual for audit). 046 no P0/P1 — VERIFIED for
owned scope (findings table: no open P0/P1; P0 examples 047..050 each have a
targeted proof: 047 wrong-target overwrite blocked by Save-As confirm +
session pin; 048 dirty/content preserved on failed save; 049 reconnect drift
refused; 050 transfer cancel keeps partial + session usable).

TODO-detail: HPC-W11-TODO-002 — IMPLEMENT (FIX-B).
`test_w27_stale_open_request_is_ignored` (+ sensitivity: fails pre-fix).

## Fixes (proof chains)

FIX-A (DEF-W27-001/002; EDITX-001..008/042):
Root cause: the wx find bar implemented only find-next over an always
case-sensitive `str.find`, with silent no-ops — half of Workstream H.
Change: `btn_find_prev` + `Match case` checkbox + `_wx_find_previous`
(backward search with bottom-wrap readback); case toggle honored by all four
ops (case-insensitive replace-all rebuilds spans from the original text);
wrap/empty/no-match all write the status line. Files: `wx_editor_view.py`,
`en.json` + `tr.json` (9 keys).
Before EV (EV-W27-A1): stashed-HEAD run — 8/8 new conflict tests fail
(missing `_wx_editor_find_previous`, no `match_case` control, silent
empty-query behavior).
After EV (EV-W27-A2): `test_w27_editor_conflicts.py` 11 passed (includes the
8 sensitivity subjects).
Regression: the 8 find/stale/binary tests. Sensitivity: same tests fail on
reverted production code (8 failed), pass with fix (8 passed).
Negative: empty query + no-match tests. Narrow: batch A 43 passed.
Runtime: wx GUI event/integration (real controls, real selections, real
status readback). Package: seams present in installed wheel (PACKAGED_SMOKE_OK).
Residual: case folding uses `str.lower` (documented; Turkic dotted-I edge
acceptable for find highlighting).

FIX-B (DEF-W27-003; HPC-W11-TODO-002):
Root cause: `load_document` applied every request unconditionally, so a late
async open clobbered the newer document (comment admitted the gap).
Change: monotonic `open_seq` counter; `_wx_editor_begin_open_request`
stamps dispatch order; `load_document(..., request_seq=...)` ignores stale
requests with a visible diagnostic before touching model/tabs/buffer;
returns `opened`/`activated`/`refused-binary`/`stale-ignored` sentinels.
Before EV (EV-W27-B1): pre-fix run of
`test_w27_stale_open_request_is_ignored` fails (no sequencer; stale content
opens a third tab and replaces the buffer).
After EV (EV-W27-B2): passes (stale ignored, 2 tabs, buffer `B`, diagnostic).
Sensitivity: covered by the 8-fail/8-pass revert proof.
Negative/lifecycle: the stale-ignore path *is* the async-lifecycle case.
Residual: current in-tree callers are synchronous (pass no seq, always
newest); async producers adopt the token API.

FIX-C (DEF-W27-004; EDITX-009/010/011):
Root cause: the binary/large guard ran only in `load_document`; the initial
panel document bypassed it, and nothing stopped a refused buffer being saved
as text.
Change: initial-open guard (refused content kept out of the control,
read-only, visible diagnostic, `binary_refused` state); `save_document`
refuses while `binary_refused` with a diagnostic; any safe `load_document`
clears the flag and restores editing.
Before EV (EV-W27-C1): pre-fix, a panel built with `ab\x00cd` shows the
bytes editable and save writes them out.
After EV (EV-W27-C2):
`test_w27_initial_binary_content_refused_and_save_blocked` passes (empty
control, `Binary` diagnostic, zero writes, blocked-save diagnostic, restore
+ verified server write of the later safe document).
Residual: model holds the refused bytes (view-level refusal); Save-As while
refused is blocked as well (safe direction).

Two-fix gate: PASS (FIX-A and FIX-B independent: UI-search semantics vs
async-ordering; FIX-C additional).

## Tests and evidence required

Environment: Windows, repo `develop`, HEAD `3e9635ba`, Python 3.12.4 for
pytest (project test harness runs here), Python 3.14.0 for packaging,
wxPython GUI tests (`@pytest.mark.gui @pytest.mark.wx`).

| Evidence ID | Command / action | Exit | Scope / result |
|---|---|---|---|
| EV-W27-BASE1 | `pytest test_w26_run_supplement -k find_replace` | 0 | 1 passed (pre-change) |
| EV-W27-BASE2 | `pytest test_w26_editor_identity test_wx_editor_tabs test_editor_controller` | 0 | 26 passed (pre-change) |
| EV-W27-A1/B1/C1 (sensitivity) | stash W27+W26 view/i18n hunks; `pytest test_w27_editor_conflicts` | 0 (8 failed) | 8 failed pre-fix — regression sensitivity proven |
| EV-W27-A2/B2/C2 | restore (stash pop, hunks byte-identical); `pytest test_w27_editor_conflicts` | 0 | 11 passed post-fix |
| EV-W27-NARROW | batch A: w27 + w26supp + identity + tabs + controller | 0 | 43 passed |
| EV-W27-WXTRIO | `test_wx_editor + cross_view_actions + window_parity` | 0 | 42 passed |
| EV-W27-EDITCOHORT | `test_editor_flow + shortcut_safety + v2_lint + local_edit_flow` | 0 | 32 passed |
| EV-W27-REMOTE | `test_wx_remote_editor_flow` | 0 | 7 passed |
| EV-W27-CTX | `test_wx_file_context_i18n + test_wx_file_actions_behavior + test_wx_remote_file_actions_behavior + test_local_transfer_gate` | 0 | 49 passed |
| EV-W27-XFER | `test_download_cancel_wire` | 0 | 4 passed |
| EV-W27-PKG | py3.14 `pip wheel . --no-deps` + sha256 + install-to-target smoke | 0 | wheel `be2bbf81…b81d5b8`, PACKAGED_SMOKE_OK |
| EV-W27-EXT | `ssh BatchMode hpctest@192.168.250.11` (25 s bound) | denied | EXTERNAL_BLOCKED (no key auth in env; nothing invented) |
| EV-W27-STATIC | `git diff --check`; `scripts/check_i18n.py` | 0 | clean; i18n key/reference/hardcoded-text OK |

New/changed tests: `tests/test_w27_editor_conflicts.py` (new, 11 tests:
REQ find/replace x6, DEF stale-open, DEF initial-binary, CON header
enablement x2, NEG save-as-cancel). Purpose IDs: REQ-W27-001..008,
DEF-W27-001..004, CON-W27-035, NEG-W27-014/037, RACE-W27-TODO-002,
PKG-W27-021 (smoke). Taxonomy: 11 x GUI event/integration. Mocks: exactly
one (`wx.MessageBox -> wx.NO` in the cancel test; legitimate dialog
boundary; proves disk/dirty/status, not the dialog). No skips/xfails added
or weakened; no existing test modified. Cleanup: disposable `tmp_path`
fixtures + frame teardown; no real user config touched. Full-process
combination of all wx files crashes on stashed HEAD too (OBS-W27-006);
compatible batches above are the honest impacted slices, each green.

## Diff review

`git diff --check`: clean. `git diff --stat`: `en.json` +8, `tr.json` +8,
`wx_editor_view.py` +306/-~7 (W26 bar preserved, W27 blocks appended beside
it), `wx_plugins_view.py` +9/-2 (pre-existing W26 hunk, untouched).
Untracked addition: `tests/test_w27_editor_conflicts.py`. No generated,
binary, cache, secret, or user-specific data in the diff. No weakened
tests. One root cause counted once per fix (A=search semantics, B=ordering,
C=guard coverage). `.tmp/w27_fix_backup.diff` + `.tmp/w27_pkg/` are
run-state under `.tmp/` (policy-correct location).

## Post-green review (POST_GREEN_REVIEW)

Duplicate paths: Qt `editor_widget` find path untouched (wx-only Wave;
Qt parity out of scope, routed nowhere). Alternate entry: Enter-key find
binding retained; new Previous button bound once; checkbox needs no binding.
Silent fallbacks: none added — every no-op writes the status line. Stale
state: save `in_flight` + disk-baseline + session-pin logic untouched and
green. Identity: `canonical_key` untouched. Cleanup: no new processes/files
outside fixtures. Dead branches: the `For now direct open` comment replaced
by the sequencer. Hardcoded provider: none. Success-claiming errors: none
(replace counts returned exactly; 0-count paths diagnosed). Packaged
divergence: seams verified inside the installed wheel.

## Handoff / resume

Completed and verified: FIX-A, FIX-B, FIX-C with revert-proven regression
tests; 11 new GUI tests; batch A (43) + WXTRIO (42) + edit cohort (32) +
remote (7) + context/actions (49) + transfer-cancel (4) all green; fresh
wheel + packaged smoke; i18n parity; diff review; canonical report current.
In progress: none (run work complete).
Open P0/P1: none in owned scope.
Open P2/P3: none newly found (OBS-005/006 are process observations, not
product defects).
Pending tests/evidence: independent fresh-context audit (controller-owned);
installer-launch packaged workflow residual; real-SFTP dimensions blocked on
lab key auth (controller/lab-owned).
Last exact commands: batch-A `43 passed`; `git diff --check` clean;
`check_i18n.py` OK; wheel SHA `be2bbf81…b81d5b8`.
Next actions (controller): schedule fresh independent audit of W27; auditor
re-verifies content identity (OBS-005), reruns batch A + packaged smoke,
adjudicates 044/045 residuals.
Evidence identities: HEAD `3e9635ba`; wheel `.tmp/w27_pkg/…be2bbf81…`;
backup diff `.tmp/w27_fix_backup.diff`; report this file.

```text
FIX-A: find-previous + Match-case + wrap/empty/no-match status readback
DEF: DEF-W27-001/002
Root cause: wx find bar implemented only case-sensitive find-next with silent no-ops
Before EV: EV-W27-A1 (8/8 new conflict tests fail on reverted code)
After EV: EV-W27-A2 (11 passed incl. all sensitivity subjects)
Regression test: test_w27_find_next_previous_wrap_and_selection (+5 find/replace mates)
Sensitivity proof: 8 failed pre-fix / 8 passed post-fix (stash revert/run/restore)

FIX-B: monotonic open-request sequencing; stale async opens ignored
DEF: DEF-W27-003 (HPC-W11-TODO-002)
Root cause: load_document applied every request unconditionally
Before EV: EV-W27-B1 (stale content opens 3rd tab, replaces buffer)
After EV: EV-W27-B2 (stale-ignored, 2 tabs, buffer B, diagnostic)
Regression test: test_w27_stale_open_request_is_ignored
Sensitivity proof: same 8-fail/8-pass revert proof

Additional fixes: FIX-C initial-binary refusal + text-save block
Post-green review: POST_GREEN_REVIEW (above, no new defect)
New/modified tests: tests/test_w27_editor_conflicts.py (new, 11 GUI tests)
Skipped/xfail changes: none
Package evidence: wheel be2bbf81…b81d5b8 + PACKAGED_SMOKE_OK (installer-launch residual)
External evidence: EXTERNAL_BLOCKED (lab key auth unavailable; host reachable)
Open P0/P1: none (owned scope)
Open P2/P3: none (OBS-005/006 are process observations)
Two-fix gate: PASS
Wave decision: READY_FOR_AUDIT
```
