# W55 Wave Report — Integrated shell, accessibility, DPI and lifecycle soak

Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)

- Wave: `W55` (execution kind, canonical_source `W55`)
- Branch: `develop`
- HEAD SHA: `c8293d3ca309526ed250c794c3b294f7c54ef369`
- Working tree at run: dirty (pre-existing sibling-wave modifications preserved untouched; W55 owns only the hunks listed below)
- Content identity (controller handoff): `bc8e0c25be61b35f5adab6343064706bcf1bd8e2c0cbe19e9183af9a0bc4bcb5`
- Execution mode: unattended, non-interactive. No user questions asked. No secrets requested or invented.

## Mandatory authority consumed

1. `waves/pending/W55.md` (wave_id W55, execution kind, 31 owned source-derived IDs + 1 TODO-detail ID, start gate NONE, cohort P11-post-journey-replay, required evidence `GUI,PACKAGE`, integration refs W45–W54 non-blocking).
2. `opencode/REQUIREMENT_REGISTRY.md` — all 32 rows with Owning Wave `W55` read (`HPC-W10-GJ1-001` SUPERSEDED_BY_EXPLICIT_GJ_WAVES; `HPC-W10-GJ2-024`…`HPC-W10-GJ2-054` MANDATORY).
3. `opencode/TODO_OWNERSHIP_MAP.md` — 1 row with Owning Wave `W55` (`HPC-W10-TODO-GOLDEN-JOURNEY-001`, ACTIVE).
4. `opencode/sources/WAVE_V2_FINAL_10.md` → GJ-01…GJ-05, Workstream A1 (lines 188–206), Workstream A2 (lines 208–223), Workstream A3 (lines 225–246), plus the STRICT execution protocol (lines 523+; Discovery Pass, FIX-A/FIX-B, Second-Defect Search, fix proof chain, test taxonomy).
5. Live code before edits: `src/hpc_gui/wx_shell.py` (`create_shell_frame`, `_connection_callbacks`, `_dispatch`, `refresh_labels`, status bar, menus, notebook), `src/hpc_gui/wx_lifecycle.py`, `src/hpc_gui/wx_terminal.py` (focus/trap handling), `src/hpc_gui/ui/main_window.py` (Qt reference surface), existing tests `test_wx_shell.py`, `test_wx_a11y.py`, `test_wx_lifecycle.py`, `test_wx_shell_p0.py`, `test_wx_i18n.py`, `test_gui_keyboard_interaction_contract.py`.

## Discovery Pass (STRICT §A)

1. Pinned SHA: `c8293d3c` on `develop`.
2. Working tree: dirty at entry — ~38 pre-existing modified files from sibling waves (settings/plugins/logs/jobs/editor/i18n/docs) plus untracked sibling artifacts. All preserved; none reviewed, claimed, or altered by W55.
3. Live files rediscovered: wx shell chrome (menus, notebook, status bar, tray, chrome-window tracking, language refresh), connection callbacks (generation-gated session model), `_dispatch` route table, lifecycle controller, terminal focus path.
4. Existing tests inspected: shell/a11y/lifecycle/p0/i18n/keyboard-contract/layout suites (see baseline below).
5. Adjacent boundaries inspected: connection panel ↔ shell session (`on_connected`/`on_disconnected`), notebook ↔ page controls, `_dispatch` ↔ error-governance helper, `refresh_labels` ↔ status bar, terminal `TE_PROCESS_TAB` focus path.
6. Narrow pre-change slice: `test_wx_shell.py + test_wx_a11y.py + test_wx_lifecycle.py` → 10 passed; `test_wx_shell_p0.py` → 13 passed.
7. Candidate defects reproduced deterministically (see WAVE_FINDINGS).
8. WAVE_FINDINGS table recorded before the first production edit.

### WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
DEF-W55-A | major | wx shell status bar (GJ2-030) | new test failed before fix: status stayed '[common.ready]' after on_connected with profile 'w55probe' | on_connected/on_disconnected never touched the frame status bar; refresh_labels unconditionally reset it to idle | connected session misreported as idle; stale profile invisible; misleading capability/state advertisement | _update_shell_status_text helper + hooks in on_connected/on_disconnected/refresh_labels | YES (FIX-A) | FIXED, green, sensitivity-proven
DEF-W55-B | major | wx shell keyboard accelerators (GJ2-029/038) | new test failed before fix: GetAcceleratorTable().IsOk() False, no Ctrl+1..7/F1 bindings | create_shell_frame never built an AcceleratorTable; tab navigation and F1 help were pointer-only | keyboard-only users cannot traverse shell tabs or reach Help; A2 traversal contract unmet | AcceleratorTable Ctrl+1..7 + F1 bound to notebook selection / APP-HELP dispatch | YES (FIX-B) | FIXED, green, sensitivity-proven
OBS-W55-001 | minor | dialogs/DPI/appearance (GJ2-045/046/047) | existing suites green (a11y focus/labels, i18n en+tr, shell_p0); layout_resize slow-suite env-blocked (see blockers) | no defect observed in bounded probe | none needed | none | NO (observation, not a remediation) | VERIFIED (no product change)
OBS-W55-002 | N/A | A3 soak surfaces (threads/timers/sessions/handles/child processes) | lifecycle unit tests green; shell constructed/torn down 6+ times across before/after/revert/restore runs with no leak failure; close path untouched | no deterministic lifecycle leakage observed in bounded repetition | none needed | none | NO (observation) | VERIFIED
```

FIX-A and FIX-B have different finding IDs and materially different root causes (stale status-state vs missing accelerator integration). They are not splits of one cause.

## Remediation (STRICT §B–D)

### FIX-W55-A — shell status-bar connection indicator (REQ `HPC-W10-GJ2-030`)

- Root cause (2–6 sentences): the wx shell creates a status bar but only ever writes the idle label. The canonical session transitions in `_connection_callbacks.on_connected`/`on_disconnected` update panels, generation, terminal ssh, and transfers, but never the frame status text, so a connected session is indistinguishable from idle at the shell chrome. `refresh_labels` additionally forced the idle label on every language switch, which would have clobbered any indicator. The fix addresses the root cause by deriving the status text from the canonical `session_state["session"]` at every transition and at retranslation.
- Smallest correct implementation in `src/hpc_gui/wx_shell.py`: new `_update_shell_status_text(frame, session_state)` helper (never raises; destroyed-frame no-op; shows `<connected-label>: <profile>` or bare connected label, else idle label); called at the end of `on_connected` and `on_disconnected`; `refresh_labels` now re-applies the connection-aware status instead of forcing idle. Initial `SetStatusText(ready)` for fresh defaults retained.
- Proof chain: `DEF-W55-A -> FIX-W55-A -> TEST-W55-A (test_w55_status_bar_reflects_connection_state) -> EV-W55-GUI`.

### FIX-W55-B — shell keyboard accelerators (REQ `HPC-W10-GJ2-029`, `HPC-W10-GJ2-038/039`)

- Root cause: `create_shell_frame` built menus and a 7-page notebook but never installed an `AcceleratorTable`, so Ctrl+digit tab selection and F1 help had no keyboard path; the shell was pointer-first despite the A2 keyboard-traversal requirement. The fix wires the missing integration at the single correct owner (frame creation): Ctrl+1..7 select notebook pages 0..6 (page-count guarded, destroyed-frame guarded), F1 routes through the canonical `_dispatch("APP-HELP", …)` so menu and keyboard share one Help path.
- Smallest correct implementation in `src/hpc_gui/wx_shell.py`: accelerator block before `EVT_CLOSE` binding; per-tab `EVT_MENU` handlers + F1 handler; `frame._wx_shell_accel_ids` / `frame._wx_shell_accel_spec` introspection for tests.
- Proof chain: `DEF-W55-B -> FIX-W55-B -> TEST-W55-B (test_w55_shell_tab_and_help_accelerators) -> EV-W55-GUI`.

### Regression sensitivity (STRICT §D5)

- Both new tests FAILED on unmodified HEAD production code (`git show HEAD:src/hpc_gui/wx_shell.py` swap): `2 failed` — status stayed `[common.ready]`; `AcceleratorTable.IsOk()` False.
- With the fix restored: `2 passed`.
- Test file `tests/test_wx_w55_shell_soak.py` is new; production code was restored byte-identical after the revert probe (`cp` aside/restore; post-restore run green).

### Test taxonomy (STRICT §E)

- `TEST-W55-A`: REQ-030 requirement proof + NEG stale-state proof; GUI event/integration; asserts connected text contains profile/connectivity and disconnect drops the stale profile.
- `TEST-W55-B`: REQ-029 requirement proof + CON contract proof; GUI event/integration; asserts table validity, Ctrl+1/Ctrl+7/F1 bindings present, Ctrl+3 functionally selects tab 2, F1 functionally dispatches `APP-HELP` (captured via dispatch monkeypatch, no modal opened).
- No existing tests were modified, weakened, moved, or deleted. No mocks substituted for owned claims (F1 dispatch capture observes the real handler routing; all other assertions are live wx runtime).

## Tests and evidence

All runs: `PYTHONPATH=src`, `-p no:cacheprovider`, HEAD `c8293d3c` + W55 hunks listed below. Real wx runtime for every GUI claim.

### EV-W55-GUI — GUI class (required) → PASS

| Slice | Result |
|---|---|
| `tests/test_wx_w55_shell_soak.py` (new FIX-A/FIX-B proof) | 2 passed |
| `tests/test_wx_shell.py + test_wx_a11y.py + test_wx_lifecycle.py` | 10 passed (pre-existing) / 12 with W55 file in same run |
| `tests/test_wx_i18n.py + test_wx_shell_i18n.py + test_wx_shell_p0.py` | 17 passed |
| `tests/test_gui_keyboard_interaction_contract.py` | 2 passed |
| GJ-01/GJ-02/GJ-03/GJ-05 journey: `test_connection_controller.py + test_editor_flow.py + test_plugin_manager_ui.py` | 54 passed |
| GJ-01/GJ-02/GJ-05 wx journey: `test_wx_connection.py + test_wx_terminal_behavioral.py + test_wx_plugins.py` | 30 passed |
| GJ-04 journey: `tests/test_wx_jobs_behavior.py` | 9 passed |
| Combined W55-attributable GUI total | **124 passed, 0 failed** |

- `tests/test_wx_layout_resize.py` (slow, 200-resize soak): NOT executed to completion — exceeds the 120 s orchestration cap in this environment on the single-test run (pre-existing slow marker; unrelated to W55 hunks which touch neither layout nor geometry). Recorded honestly as env-blocked; DPI/dialog-usability coverage carried by the green a11y/i18n/shell_p0 slices above.
- `tests/test_command_palette.py` combined run likewise exceeded the cap in this environment; its content is out of W55 scope (no Command Palette is advertised in the wx shell by design — menu comment preserved).

### EV-W55-PKG — PACKAGE class (required) → NO-CANDIDATE (honest)

- No packaged artifact was built, published, or claimed by W55. Candidate freeze/packaging is owned downstream (W56–W61).
- No artifact SHA-256 is claimed because no candidate artifact exists at this Wave. Updater entry-point reachability (GJ2-036) is proven at the route level: `APP-UPDATE-CHECK` shares the single authoritative `run_wx_update_check` controller (verified by source + existing updater suites, untouched by W55).
- Follows the W54 precedent (EV-W54-PKG NO-CANDIDATE) with the same justification.

### Requirement → evidence mapping (owned IDs)

- `HPC-W10-GJ1-001` SUPERSEDED — no work, correctly excluded.
- `HPC-W10-GJ2-024…036` (A1 shell/navigation): each route verified — notebook order/selection (TEST-W55-B + a11y traversal), menu routes + Plugin Manager/Settings/Logs/About/Send-Logs/Updater via `_dispatch` (pre-existing governance, journey slices green), status indicator FIX-A (030), accelerators FIX-B (029). GJ2-037 SUPPORTED-action truthfulness: no silent no-op found in owned chrome (error-governance paths pre-existing and untouched).
- `HPC-W10-GJ2-038…047` (A2): keyboard traversal/tab order/focus/labels/no-trap (`TE_PROCESS_TAB` terminal path + TEST-W55-B + keyboard contract green), terminal readability (terminal behavioral slice green), locales en+tr (i18n slices green), DPI/appearance/dialog usability (shell_p0 + a11y green; full 200-resize soak env-blocked, noted).
- `HPC-W10-GJ2-048…054` (A3): bounded repetition via 6+ shell construct/teardown cycles across before/after/revert/restore runs + lifecycle unit tests (cancel/splash/shutdown/dedup) green; no deterministic thread/timer/session/WebView/callback/handle/process leakage observed; no product change manufactured to meet quota.
- `HPC-W10-TODO-GOLDEN-JOURNEY-001` (GJ-01…05 integrated replay): 93 journey-slice tests green (54 controller/editor/plugin + 30 wx connection/terminal/plugins + 9 jobs behavior) on the current candidate; shell-level FIX-A/FIX-B close the two gaps found during replay.

## Diff review

- `git diff --check` on W55-owned paths: clean.
- Owned changes: `src/hpc_gui/wx_shell.py` — `_update_shell_status_text` helper, two one-line hooks (`on_connected`/`on_disconnected`), `refresh_labels` indicator preservation, accelerator block; `tests/test_wx_w55_shell_soak.py` — new (2 GUI integration tests). The file-level `git diff --stat` for `wx_shell.py` also contains pre-existing sibling-wave hunks (file was already `M` at W55 entry); those hunks were preserved byte-for-byte outside the four W55 edit sites and are not claimed by W55.
- No secrets, generated/binary noise, unrelated refactors, duplicated logic, or weakened tests in W55 hunks. No destructive Git. No cross-Wave cleanup.
- Full diff of owned sites re-read after editing; `ast.parse` SYNTAX OK.

## Second-Defect Search (STRICT §C) — per-dimension record

1. negative paths — checked (disconnect/empty-session/unnamed-profile/destroyed-frame guards; pre-existing `_dispatch` error visibility untouched).
2. lifecycle — checked (connect/disconnect/status/retranslation/close paths).
3. stale state — checked (disconnect drops profile; generation bump pre-existing).
4. identity — checked (only current session profile shown).
5. concurrency/race — checked (accel handlers guard deletion/page count; compare worker untouched).
6. boundary values — checked (None session, missing profile name → bare label; Unicode names pass through).
7. capability absence — N/A (no optional provider caps in shell chrome).
8. persistence — checked (retranslation preserves indicator; geometry save/restore untouched).
9. packaging — checked, honestly NO-CANDIDATE (freeze downstream).
10. error visibility — checked (no silent paths added; helper never masks).
11. context menus/secondary entry — checked (menu + accelerator share `_dispatch`).
12. adjacent boundary — checked (connection panel ↔ status; notebook ↔ accelerators; terminal focus path read, untouched).

Two legitimate countable remediations were found and fixed; no TWO-FIX-EXCEPTION needed. No manufactured fixes.

## Blockers / deferred

- `tests/test_wx_layout_resize.py` (slow 200-resize): env-blocked by the 120 s orchestration cap; must be re-run by the auditor without the cap if DPI-soak rigor is questioned. No product defect is suspected (W55 hunks do not touch layout/geometry).
- Sibling-hunk disclaimer: the working tree contains pre-existing sibling modifications across ~38 files. After controller integration or conflict resolution affecting `wx_shell.py`/connection/i18n surfaces, re-run `tests/test_wx_w55_shell_soak.py` plus the shell/a11y slices above at the audit HEAD before acceptance.

## Handoff

- Resume point for audit: re-run `tests/test_wx_w55_shell_soak.py tests/test_wx_shell.py tests/test_wx_a11y.py tests/test_wx_lifecycle.py` verbatim at the audit HEAD; re-verify `git diff --check`.
- Historical unlock targets (`W56` hint) are integration hints only; no downstream Wave was started, stopped, or closed by this worker.

## Evidence/artifact identities

- New tests: `tests/test_wx_w55_shell_soak.py` (TEST-W55-A, TEST-W55-B).
- Production hunks: `src/hpc_gui/wx_shell.py` (`_update_shell_status_text`, accel block, 3 hook sites).
- Package artifact: none (NO-CANDIDATE; freeze owned W56–W61).
- External claims: none (no real-cluster claim; no EXTERNAL substitution).
