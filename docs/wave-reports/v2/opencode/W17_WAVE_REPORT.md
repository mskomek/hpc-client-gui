# W17 — Profile CRUD and persistence — Wave Report

```text
Wave: W17
Canonical report path: docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui (main)
Branch: develop
Baseline SHA: 0f8902a023bac76071527232c2287af96478ed2b
Current HEAD: 0f8902a023bac76071527232c2287af96478ed2b
Plugin/external repo SHA(s): f0abb7e7037e66ab451d463c699fecf4e00c89eb (pinned baseline per wave order; no plugin changes planned, no plugin claims made)
First started: 2026-09-20
Last updated: 2026-09-20
Session status: READY FOR FINAL REVIEW
Wave decision: READY_FOR_AUDIT
```

Predecessor gate: W16 closed PASS (READY_FOR_AUDIT + AUDIT PASS + CLOSE PASS per wave order).
Dependencies: W16 — satisfied. Required evidence: GUI. Execution model:
`opencode-go/muse-spark-1.3-contributor`.

## Baseline capture

```text
git rev-parse HEAD: 0f8902a023bac76071527232c2287af96478ed2b
git rev-parse origin/develop: 0f8902a023bac76071527232c2287af96478ed2b (equal; no divergence)
git diff --check: clean (only pre-existing CRLF warnings on unrelated files)
git status: dirty — pre-existing unrelated working-tree changes preserved byte-for-byte
  (CONTRIBUTING.md, README.md, artifacts/v2-final/W01/*, docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md,
   scripts/generate_release_manifest.py, scripts/wx_packaged_smoke.py, src/hpc_gui/core/paths.py,
   src/hpc_gui/i18n/en.json + tr.json, src/hpc_gui/plugins/loader.py + validator.py,
   src/hpc_gui/services/{connection_controller,files_ssh,slurm_models,slurm_ssh}.py,
   src/hpc_gui/{wx_connection,wx_settings_view,wx_shell}.py, tests/test_wave10_release_gate.py,
   tests/test_wx_packaged_smoke.py, plus untracked W15/W16 audit artefacts and helper scripts)
```

`waves/pending/` contains exactly one copy of each W01–W61 file (verified by listing;
W17.md is the single canonical copy). `waves/bak/` never read.

Secrets scan: `git diff --check` clean; no password/secret material in diff scope.
No `.env`/credentials/tokens/keys exposed.

## Authority reads (all completed before implementation)

1. `opencode/protocol/CORE_EXECUTION_RULES.md` — read.
2. `waves/pending/W17.md` — read (14 owned IDs, 0 TODOs, Workstream 0 only).
3. Owned registry rows `HPC-W05-PROF-001..014` — read (13 MANDATORY + PROF-014 CONDITIONAL).
4. `REQUIREMENT_WAVE_INDEX.md` + `TODO_OWNERSHIP_MAP.md` — 0 TODO rows for W17, confirmed.
5. `opencode/sources/WAVE_V2_FINAL_05.md` Workstream 0 + connection/profile test matrix — read.
   Auth/host-key/state-machine depth (Workstreams 0.1/0.2/0.3) belongs to W18/W19 — routed, not absorbed.
6. Live code truth rediscovered (see Discovery). 7. W16 close truth used as predecessor background only.

Owned requirements trace:

```text
PROF-001 first profile create from clean config -> WxConnectionModel/_build_connection Add + WxConnectionDialog + save_profile + storage.upsert_profile
PROF-002 edit existing profile -> _open_dialog("edit") + verify_edit_authorization + save_profile (patch merge)
PROF-003 select active profile -> WxConnectionModel.select + choices EVT_LISTBOX + context-menu retarget
PROF-004 delete with safe confirmation -> _delete_selected (YES/NO + active-connected block) + storage.delete_profile
PROF-005 duplicate/copy -> profile_duplicate.duplicate_profile (fresh id, secrets stripped) + dialog
PROF-006 provider selection -> provider/system-template menu in dialog (_rebuild_system_template_menu, builtin + plugin + user templates)
PROF-007 hostname/port/user validation -> _collect_profile (port numeric+range, host required, jump-host required)
PROF-008 authentication-method selection -> password/key fields + prompt-policy radios + ssh_info_from_profile mapping (depth -> W18)
PROF-009 profile-specific vs global values -> transfer_parallelism migration, keepalive/ssh-timeout coercion, per-profile file_manager/jump_host
PROF-010 save/apply semantics -> on_save / on_save_and_connect (exactly one save) + _handle_save + _refresh_list
PROF-011 invalid/incomplete profile feedback -> dialog MessageBox validation + connect-time profile_not_found/failed states
PROF-012 reconnect using persisted profile -> connect_selected + resolve_password_for_connect + fresh transient (password never persisted)
PROF-013 Profile A -> B without stale ownership -> session teardown before (re)connect in both model and panel worker + close_session
PROF-014 no hidden file editing on first run -> HPC_GUI_CONFIG_ROOT isolated fresh-user flow (PKG-GJ-01, W15/W16 evidence)
Identity: id survives rename; upsert by id fallback name; last_profile/last_profile_id maintained; secrets never plaintext.
```

## Narrow baseline (pre-edit)

```text
Command: python -m pytest tests/test_wx_connection.py tests/test_wx_connection_71_2.py
  tests/test_wx_connection_71_3.py tests/test_connection_profile_service.py
  tests/test_profile_patch_preservation.py tests/test_w15_fresh_user_startup.py -q
Result (combined run): 54 passed, 2 failed
  FAILED tests/test_w15_fresh_user_startup.py::test_closed_port_connect_fails_visibly_without_connected_state
  FAILED tests/test_w15_fresh_user_startup.py::test_visible_connect_drives_controller_to_connected
Re-run solo: python -m pytest tests/test_w15_fresh_user_startup.py -q -> 11 passed in 1.31s
Single-test re-run of test_visible_connect_drives_controller_to_connected -> 1 passed in 0.34s
Conclusion: order/display-contention flake when the 6 GUI files share one wx session, not a product
defect (both tests pass solo and in-file). GUI suites are run solo-sequenced for all W17 evidence.
```

## Discovery pass (completed before first production edit)

Live implementation owners rediscovered at baseline SHA:

```text
- src/hpc_gui/services/connection_profile_service.py (save_profile, resolve/decrypt, verify_edit_authorization)
- src/hpc_gui/config/storage.py (merge_profile_patch, load_profiles+id stamping, upsert_profile by id fallback name,
  delete_profile+secret/navigation cleanup, get_last_profile_name, last_profile/last_profile_id)
- src/hpc_gui/wx_connection.py (_build_connection panel: Add/Edit/Duplicate/Delete/Connect, _handle_save, _open_dialog,
  connect_selected worker, context menu, selection retarget, status marshalling)
- src/hpc_gui/wx_connection_dialog.py (WxConnectionDialog: _collect_profile validation, provider template menu,
  _save_clicked/_save_and_connect_clicked, storage/quota/cluster sections)
- src/hpc_gui/services/profile_duplicate.py + profile_exchange._clean (fresh id, secrets incl. keychain refs stripped)
- src/hpc_gui/cli/main.py (_run_profile create/update/delete/test — no rename path; delete requires --yes)
- Qt parity anchor src/hpc_gui/ui/widgets/login_widget.py (same upsert-by-name semantics; no last-profile restore
  on startup in either runtime — parity, not a defect)
```

Adjacent boundaries inspected: `ssh_info_from_profile` (never prompts; master secrets resolved on GUI thread),
`connect_profile`/`close_session`, `delete_profile_navigation`, `protect/unprotect_keychain_secret`,
`HPC_GUI_CONFIG_ROOT` isolation (`src/hpc_gui/core/paths.py` — the ONLY supported config override).

Process note (remediated): the first service probe mistakenly used invented env vars
(`HPC_GUI_CONFIG_DIR`/`HPC_GUI_DATA_DIR`) which storage ignores, writing 2 probe profiles into the real
user config dir. Detected immediately via row inspection, removed surgically (both probe rows +
4 probe-created `.bak` files), verified real config back to its single pre-existing `loop` profile with
`last_profile=loop`. All later probes use `HPC_GUI_CONFIG_ROOT` tempdirs. No user data lost.

## WAVE_FINDINGS (before first production edit)

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
DEF-W17-001 | P2 | save_profile rename path (wx Edit + shared service) | EV-W17-001 isolated probe: rename beta->alpha created 2 same-named rows (ids a4b2ff53 / 434e9235), last_profile ambiguous | no target-name ownership check on rename; upsert matches by id so the collision is never detected | select/connect/delete/last_profile are all name-keyed -> ambiguous identity, wrong-profile connect, double delete | reject rename onto a name owned by a different id (ValueError -> GUI warning) | yes (P2 in-scope, distinct failure mode) | FIX PLANNED
DEF-W17-002 | P3 | save_profile return contract (Add path) | EV-W17-001 probe: Add returned dict has id None while edit path echoes stored id | upsert_profile assigns the uuid internally without syncing it back to the caller's dict | callers receiving an identity-less record; inconsistent Add vs Edit contract for the wave's profile-identity objective | populate prof["id"] from the persisted record after upsert | yes (contract, distinct root cause) | FIX PLANNED
FIND-W17-003 | — | Add with duplicate name overwrites in place | EV-W17-001 PROBE1: Add 'alpha' overwrote stored alpha (h1->EVIL), single row, id stable | upsert-by-name fallback — the exact "upsert by id fallback name" semantic the wave objective blesses; identical in Qt | converges to consistent state; documented as designed, NOT a defect | none (behaviour locked by new test) | documented
FIND-W17-004 | — | last_profile written but never consumed for startup selection | grep: get_last_profile_name has zero src callers; both wx and Qt start unselected | forward-compat state, identical in both runtimes (parity) | no user impact; changing it would break Qt/wx parity and exceed PROF scope | none | documented
FIND-W17-005 | — | duplicate shares keychain secret? | profile_exchange._clean strips password|...|keychain keys; duplicate_profile additionally strips key paths | no sharing; verified by code trace + existing test_duplicate tests | none | no defect
```

## Second-Defect Search (12 dimensions)

```text
1. negative paths — port non-numeric/out-of-range, empty host, jump-enabled-without-host, provider-required project/account: dialog blocks with warning (existing tests + W17 GUI runtime proof). Rename-collision NEG was missing -> DEF-W17-001.
2. lifecycle — first-run create, save/apply, reconnect-from-disk, close/relaunch persistence: covered (W15/W16 + W17 runtime proof).
3. stale state — A->B teardown before connect (model + panel worker), generation via fresh transient: covered by existing tests + runtime proof.
4. identity — id survives rename (existing tests); rename-collision gap -> DEF-W17-001; Add return-id gap -> DEF-W17-002; duplicate fresh-id + secret strip verified.
5. concurrency/race — connect button disabled while connecting; second attempt transitions: existing hardening tests.
6. boundary values — empty/blank names fall back to user@host; port range enforced; Unicode covered by editor/i18n suites. Duplicate-name boundary -> DEF-W17-001.
7. capability absence — keychain/DPAPI/master fallbacks preserved (existing 71_x tests).
8. persistence — JSON round-trip, unknown-key preservation, migration id-stamping: existing tests + reconnect-from-disk runtime proof.
9. packaging — source-only wave for profile logic; W16 owns packaged proof (reused, not re-claimed).
10. error visibility — save failure prevents connect; connect failure keeps profile; secrets redacted: existing tests.
11. context menus / secondary entry points — menu actions share panel handlers; right-click retargets selection: existing code+tests.
12. adjacent integration boundary — CLI create/update/delete consistent (no rename path; delete requires --yes); Qt parity verified for upsert + selection behaviour.
```

## Fixes

```text
FIX-W17-001 (DEF-W17-001, P2 — rename-collision guard):
  Files: src/hpc_gui/services/connection_profile_service.py (guard in save_profile),
         src/hpc_gui/wx_connection.py (panel _handle_save maps profile_name_taken -> i18n warning),
         src/hpc_gui/i18n/en.json + tr.json (connection.rename_name_taken)
  Behavioral contract changed: renaming a profile onto a name owned by a different
  profile id is now rejected with ValueError("profile_name_taken:<name>") before any
  secret handling or disk write; the wx panel shows a dedicated warning and keeps both
  profiles untouched. Add-path upsert-by-name and clean renames are unchanged (Qt parity kept).
  Regression tests: test_rename_onto_existing_name_raises_and_preserves_both (service),
    test_real_dialog_rename_onto_existing_name_rejected (real WxConnectionDialog + real Save
    button event + real service), test_panel_save_maps_rename_conflict_to_warning (real panel
    _handle_save), i18n key presence extended in test_i18n_en_tr_labels (en+tr, additive only).
  Sensitivity proof: with the service guard reverted, all three collision tests fail
    (no ValueError; save succeeds; EndModal called / no warning). With only the panel
    mapping reverted, the panel test fails showing raw "profile_name_taken:alpha" leaks
    to the user. Both reverts restored byte-identical (patch round-trip verified).
  Negative test: rename rejected (above). Lifecycle: failed save leaves disk + list intact.
  Narrow suite: test_connection_profile_service 12 passed; test_wx_connection_profiles 29 passed.
  Broader suites: profile_identity/patch_preservation/duplicate 20 passed; wx_connection +
    71_2 (14), 71_3/71_4/71_5 (24), hardening (20), controller+w15 (14) — all green, solo runs.

FIX-W17-002 (DEF-W17-002, P3 — Add-path return-id sync):
  Files: src/hpc_gui/services/connection_profile_service.py (prof["id"] synced from disk after upsert)
  Behavioral contract changed: save_profile now returns the persisted stable id on every path
  (Add previously returned id None while Edit echoed the merged id).
  Regression tests: test_add_returns_stored_stable_id (+ test_add_duplicate_name_upserts_in_place_by_design
    locks the designed upsert semantic and id stability).
  Sensitivity proof: with the sync reverted, test_add_returns_stored_stable_id fails
    (saved.get("id") is None) and the upsert lock-in test fails with KeyError: 'id'.
  Negative/lifecycle: n/a beyond the above (pure contract sync; no new failure mode).
```

## Tests

```text
New tests (5, all with behavioral assertions, isolated temp storage, no real user config):
  tests/test_connection_profile_service.py:
    - test_rename_onto_existing_name_raises_and_preserves_both (NEG + identity)
    - test_add_duplicate_name_upserts_in_place_by_design (contract lock-in)
    - test_add_returns_stored_stable_id (contract)
  tests/test_wx_connection_profiles.py:
    - test_real_dialog_rename_onto_existing_name_rejected (real wx dialog + real button event)
    - test_panel_save_maps_rename_conflict_to_warning (real panel handler)
    - test_i18n_en_tr_labels extended additively with connection.rename_name_taken (en+tr)
  Mocking boundary: GUI tests mock only wx.MessageBox/EndModal (event-loop necessities) and the
  modal dialog frame in W17.2; the dialog widgets, collect/validation, service, storage and panel
  handler under test are all real code. What tests do NOT prove: full modal loop orchestration
  (covered separately by the GUI runtime matrix script below).
  No skips/xfails added; no existing test weakened (i18n change is additive).
  Test-quality checklist: regression-per-fix YES (sensitivity proven); negative path YES;
  lifecycle/stale YES (failed save leaves state intact; A->B covered by existing + runtime);
  behavioral assertions YES (row counts, ids, hosts, literal warning text, EndModal not called);
  mocks minimal YES; fixtures isolated YES (tempdir + Path.home patch / HPC_GUI_CONFIG_ROOT);
  cleanup deterministic YES; full impacted slice green YES; future regression would fail YES (proven).
```

## GUI runtime evidence

```text
Evidence ID: EV-W17-RT01 (source runtime, real wx events, single GUI process)
Command: python -u <outside-repo-temp>/w17_gui_runtime.py (HPC_GUI_CONFIG_ROOT=fresh tempdir)
Exit code: 0, overall: True, 17/17 steps PASS — raw: build/audit/w17-gui-runtime.json (+ .stderr.txt)
Scope: full W17 matrix with real modal WxConnectionDialog driven by timer (custom dialogs)
  and OS-level UIActionSimulator keys in a helper thread (native confirm dialog)
Observed (each a real wx event/runtime proof):
  first-run-empty-add-enabled PASS | add-dialog-save PASS (alpha/h1.example, key_path persisted,
  stable id assigned) | add-list-refresh PASS | secret-hygiene-add PASS |
  validation-neg PASS ("Port must be numeric.", "Host / IP is required...", no row created) |
  rename-collision-neg PASS (literal new warning shown, both rows intact) |
  edit-save PASS | duplicate-unique-fresh-id PASS ("beta (copy)", all ids distinct) |
  select-detail PASS | provider-selection-state PASS ("Provider: Truba") |
  connect-A PASS | A-to-B-no-stale PASS (old session closed: ['alpha'], active beta) |
  reconnect-from-disk PASS (fresh panel instance lists all 4 disk profiles) |
  delete-active-blocked PASS ("Cannot delete the active connected profile...") |
  delete-no-keeps PASS | delete-yes-removes PASS | secret-hygiene-final PASS (3 rows, no plaintext)
Expected: same. Notes: stderr carries only benign pre-existing wx parenting/SetFocus notices
  (also present in committed GUI tests); secrets never in JSON/logs (asserted twice + scanned).

Evidence ID: EV-W17-001 (before-fix service probe) — raw: build/audit/w17-service-before.json
  Add returned id None; rename beta->alpha silently created 2 same-named rows (ids f0f7ba95/e5ca944f).
Evidence ID: EV-W17-002 (after-fix service probe) — raw: build/audit/w17-service-after.json
  Add returns ids; rename rejected (profile_name_taken:alpha); rows alpha/h1 + beta/h2 intact; last_profile=beta.
```

## POST_GREEN_REVIEW

```text
- Single-point guard in shared save_profile; no duplicate implementation path added.
- Alternate entry (Qt login_widget.save_profile) untouched — separate code, same upsert semantics; change is wx-service-only.
- No silent fallback: guard raises before secret handling/disk write; panel maps to a literal warning (sensitivity-proven).
- Failed save leaves disk + last_profile untouched (asserted: both rows, hosts, ids intact).
- Add echo uses get_profile_id(name); consistent with upsert's first-match semantics even with hypothetical legacy dupes.
- No new deps/resources -> no packaging divergence (W16 packaged proof reused, not re-claimed).
- No test weakened; no skips/xfails; i18n change additive with en/tr parity + presence test.
- Residual: pre-existing combined-run GUI flake (2 W15 tests fail only when 6 GUI files share one session; green solo and in-file) — environmental, not product; all W17 evidence runs solo-sequenced.
```

## Resume state

```text
Completed and verified:
- Authority reads, baseline capture (HEAD == origin/develop == 0f8902a0), narrow baseline, discovery,
  WAVE_FINDINGS, 12-dim second-defect search
- FIX-W17-001 (P2 rename-collision guard + panel i18n mapping) and FIX-W17-002 (P3 return-id sync)
- 5 new regression tests + additive i18n assertions, all with two-sided sensitivity proof
- Full impacted suites green (solo-sequenced): service 12, profiles-GUI 29, identity/patch/duplicate 20,
  wx+71_2 14, 71_3/4/5 24, hardening 20, controller+w15+advanced 33, CLI-profile 35
- GUI runtime matrix EV-W17-RT01: 17/17 PASS in one real wx process (raw JSON preserved)
- Before/after service probes EV-W17-001/002 preserved; POST_GREEN_REVIEW done; diff reviewed
- Real-user config incident remediated and re-verified clean (single 'loop' profile)
- Repair cycle 1 (2026-09-20, closer REOPEN reconciliation, report-only): REP-W17-001 CLOSED —
  the canonical report contained two POST_GREEN_REVIEW sections (one complete 8-bullet review,
  one stale duplicate previously marked pending). The stale duplicate was removed; exactly one current
  POST_GREEN_REVIEW remains as truth (no product semantics changed, no test touched).
  Closer REOPEN finding CLOSED. Re-verified: focused suites
  `tests/test_connection_profile_service.py + test_profile_identity.py +
  test_profile_patch_preservation.py + test_profile_duplicate.py` -> 32 passed,
  `tests/test_wx_connection_profiles.py` -> 29 passed, `git diff --check` clean (exit 0,
  only pre-existing CRLF warnings), evidence EV-W17-001/002 + EV-W17-RT01 files still bound.
- Repair cycle 2 (2026-09-20, re-audit REOPEN reconciliation, report-only): REP-W17-002 CLOSED —
  the cycle-1 history note itself still quoted the old stale-duplicate marker text, so a literal
  file-wide search still matched one occurrence at line 258. Rephrased that history note to plain
  prose with no marker token; no product semantics changed, no test touched, audit report untouched.
  Re-verified: literal file-wide search for the parenthesised pending marker returns zero matches;
  exactly one POST_GREEN_REVIEW section header remains; suites and evidence unchanged from cycle 1.

In progress: none (implementation complete; report current)

Open P0/P1: none
Open P2/P3: none (DEF-W17-001/002 fixed and proven)

Pending tests/evidence: none

Last exact commands run:
- python -m pytest tests/test_connection_profile_service.py tests/test_profile_identity.py tests/test_profile_patch_preservation.py tests/test_profile_duplicate.py -q -> 32 passed
- python -m pytest tests/test_wx_connection_profiles.py -q -> 29 passed
- python -m pytest tests/test_wx_connection.py tests/test_wx_connection_71_2.py ..._71_5.py tests/test_wx_connection_hardening.py -q -> 58 passed
- python -m pytest tests/test_connection_controller.py tests/test_w15_fresh_user_startup.py tests/test_connection_advanced_settings.py -q -> 33 passed
- python -m pytest tests/test_cli.py -q -k profile -> 35 passed
- GUI runtime matrix -> exit 0, 17/17 PASS (build/audit/w17-gui-runtime.json)

Next actions:
1. Fresh-context audit (W17_AUDIT_REPORT.md is owned by the audit step, not this implementation session)
2. /wave-close W17 (do NOT start W18)

Evidence/artifact identities:
- EV-W17-001 build/audit/w17-service-before.json; EV-W17-002 build/audit/w17-service-after.json
- EV-W17-RT01 build/audit/w17-gui-runtime.json + w17-gui-runtime.stderr.txt
- Tested implementation SHA: 0f8902a023bac76071527232c2287af96478ed2b + uncommitted W17 diff (product+tests only)
```

## Final summary

```text
FIX-W17-001 (P2): rename-onto-existing-name guard in save_profile + wx i18n warning mapping.
  DEF: DEF-W17-001 — rename created duplicate-named rows, ambiguous name-keyed identity.
  Root cause: upsert matches by id so a rename collision was never detected; no target-name ownership check.
  Before EV: EV-W17-001 (two 'alpha' rows). After EV: EV-W17-002 + EV-W17-RT01 rename-collision-neg PASS.
  Regression tests: service + real-dialog + real-panel (3). Sensitivity proof: revert->fail on both layers, restored.

FIX-W17-002 (P3): save_profile returns the persisted stable id on the Add path.
  DEF: DEF-W17-002 — Add returned id None, Edit echoed stored id (contract inconsistency).
  Root cause: upsert_profile assigns the uuid internally without syncing back to the caller's dict.
  Before EV: EV-W17-001 (ret id None). After EV: EV-W17-002 (ids present, match disk).
  Regression tests: test_add_returns_stored_stable_id + upsert lock-in. Sensitivity proof: revert->fail, restored.

Additional fixes: none (FIND-W17-003/004/005 documented as designed/parity/verified, no change).
Post-green review: done (see section; no new defects).
New/modified tests: 5 new + 1 additive i18n extension; zero weakened/skipped/xfailed.
Skipped/xfail changes: none.
Package evidence: N/A (no new deps/resources; W16 packaged proof reused, not re-claimed).
External evidence: N/A (no real-cluster claim; transports faked at the documented mock boundary).
Open P0/P1: none. Open P2/P3: none.
Two-fix gate: SUPERSEDED by HPC-GOV-017 (no quota); every genuine in-scope defect resolved with proof.
Wave decision: READY_FOR_AUDIT (implementation complete; audit/close own the remaining gates).
```
