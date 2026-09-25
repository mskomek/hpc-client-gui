# W26 — Editor routing, document identity and save targets - Wave Report

```text
Wave: W26
Canonical report: docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
Repository: hpc-client-gui / develop
Branch: develop
Baseline SHA: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Tested implementation: working tree at 3e9635ba + W26-owned hunks only
  (src/hpc_gui/wx_editor_view.py [wx find/replace bar + helpers],
   src/hpc_gui/wx_plugins_view.py [compat/enabled details],
   tests/test_w26_run_supplement.py [new])
Current HEAD: 3e9635ba1cf0255d5a09f370e91d1ddb73cef888
Content handoff: controller content_identity 25d604650880c0265c641c6f8f5d3fa4cd6657301fc9ba8503f6292e403a1820;
  current waves/pending/W26.md normalized SHA-256 e635913ceb0026b68a071bc8209d168e026407d7be62ec7ffba89cda347bae10
  (waves/ ignored by .gitignore:104 /waves/; working from current repository truth)
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: READY_FOR_AUDIT (independent audit pending, controller-owned)
```

## Scope

W26 owns `HPC-W06-EDIT-001..022` plus TODO-details `HPC-W06-TODO-007/008/009/010`,
`HPC-W06-TODO-EDITOR-ROUTE-002`, `HPC-W11-TODO-001`, `HPC-W06-TODO-PLUGIN-COMPAT-001`,
`HPC-W06-TODO-034/035/036/037/038/039/040`, `HPC-W06-TODO-CI-PR-002` per
`waves/pending/W26.md` frontmatter (22 + 15 = 37 IDs).
Mandatory authority read before edits: all `opencode/REQUIREMENT_REGISTRY.md` W26 rows,
all `opencode/TODO_OWNERSHIP_MAP.md` W26 rows (15 ACTIVE), and
`opencode/sources/WAVE_V2_FINAL_06.md` sections **Scope / Editor**,
**Workstream F — Editor document model**, **Workstream G — Editor save guarantees**.
Live code inspected before editing (`services/editor_controller.py`,
`wx_editor.py`, `wx_editor_view.py`, `wx_editor_windows.py`, `wx_shell.py`
editor factory/routing, `wx_plugins.py`/`wx_plugins_view.py`, Qt
`ui/widgets/editor_widget.py` as parity reference, `i18n/en.json` labels,
`scripts/ci.py`, `docs/ci-disabled/`). No cross-Wave worktree/report/temp edits;
unattended, non-interactive. Prior commit `d0d544c1` provided W26 identity
groundwork (`DocumentModel` pins, newline preservation, binary guard, session-pin
refusal, 12 W26 identity tests); this run closes remaining wx parity gaps.

## Discovery (condensed)

| Finding ID | Severity | Surface | Evidence | Root cause |
|---|---|---|---|---|
| DEF-W26-001 | P1 | wx editor find/replace | source read: `wx_editor_view.py` has zero `find`/`replace` symbols (only `dataclasses.replace`); Qt `editor_widget.py` has full find bar + `find_next`/`replace_all` | wx parity gap; EDIT-005 only satisfied on Qt path |
| DEF-W26-002 | P2 | Plugin manager details | source read: `_refresh_list` shows `version + installed` only; `PluginCard` carries `enabled`/`compatible` never rendered | details column drops owned compat/enabled state |
| OBS-W26-003 | P3 | CI PR gate | `docs/ci-disabled/README.md`: CI intentionally disabled; `scripts/ci.py quick` covers compile/i18n/smoke/lint locally; `.github/workflows/release.yml` manual-only | CI-PR-002 cannot re-enable CI in worker scope; local lanes + documented deferral |

Pre-change narrow baseline: `tests/test_w26_editor_identity.py` -> `12 passed`;
editor cohort (`test_editor_controller + test_editor_flow + test_wx_editor +
test_wx_editor_tabs + test_wx_editor_window_parity + test_wx_editor_cross_view_actions +
test_wx_remote_editor_flow + test_w26_editor_identity`) -> `89 passed`.

## Requirement trace (requirement -> live owner -> test -> evidence)

- EDIT-001 (local open/save/save-as): owner `_build_editor.save_document` is_local
  branch + header-path Save As redirect + `_write_local_text(newline="")`.
  Proof: `test_w26_wx_crlf_local_save_preserves_line_endings`,
  `test_w26_wx_save_as_header_redirect_creates_new_target`, supplement vanished-parent test.
- EDIT-002 (remote open/save): owner `action_factory.save_remote` (`files.write_text`)
  via async worker; header redirect also applies to remote.
  Proof: supplement `test_w26_supplement_remote_gui_save_proves_server_content`
  asserts server dict equals GUI text; `test_wx_remote_save_backend_runs_off_gui_thread`.
- EDIT-003 (dirty state): owner `DocumentModel.dirty` + `_update_dirty_marker` (`" *"`)
  + `content_changed`. Proof: dirty cleared after save, retained after failure
  (encoding/vanished/disconnect tests).
- EDIT-004 (close/reload conflict): owner at-open `(mtime_ns,size)` baseline
  (`_note_disk_baseline`), `_confirm_external_change` prompt, `close()` YES/NO/CANCEL
  + `close_tab` save/discard/cancel. Proof: existing W25 external-change tests +
  `test_wx_editor_dirty_close_save_changes_popup_saves_then_closes`, tabs close tests.
- EDIT-005 (find/replace): owner Qt find bar (pre-existing) + FIX-W26-A wx find bar
  (`find_in`/`replace_in`/`find_next`/`replace`/`replace_all`, wrap, empty-query no-op).
  Proof: supplement `test_w26_supplement_wx_find_replace` (find selects, replace_all count 2,
  empty no-op); Qt `test_editor_flow` find/replace unchanged green.
- EDIT-006 (encoding/newline): owner `detect_newline`/`normalize_newlines_for_save`,
  `DocumentModel.newline`, `_write_local_text` with pre-lookup + `newline=""`.
  Proof: `test_w26_newline_detect_and_normalize_round_trip`, CRLF local save, unicode test.
- EDIT-007 (large/binary guard): owner `editor_binary_guard_reason` (NUL -> Binary,
  >2MiB -> large) + `load_document` refusal with status.
  Proof: `test_w26_binary_and_large_guard_reasons`, `test_w26_wx_binary_content_refused_with_visible_diagnostic`.
- EDIT-008 (remote disconnect during save): owner pinned-session refusal +
  async error -> status, `saved=False` keeps dirty, followup suppressed.
  Proof: supplement disconnect test (`disconnected session`, dirty retained);
  `test_wx_remote_save_failure_prevents_followup`.
- EDIT-009 (tab/document identity): owner `canonical_key` + `EditorController.open`
  duplicate suppression + wx `_refresh_tabs`/`_on_tab_changed`/`_reorder_tabs`.
  Proof: identity distinct-tabs tests, `test_wx_editor_reorder_tabs_preserves_document_identity`,
  supplement distinct-session tab test.
- EDIT-010/011/012/013/014/015 (document model fields): owner `DocumentModel`
  (`is_local`, `path`, `provider`/`profile`/`session_key`, `encoding`/`newline`,
  `dirty`, `version`). Proof: W26 identity unit tests + newline/unicode tests.
- EDIT-016 (connection switch must not misdirect Save): owner `_editor_session_key`
  pin + `_require_pinned_session` refusal (locale-independent non-empty message).
  Proof: `test_w26_session_pin_refuses_save_to_wrong_host`,
  `test_w26_wx_connection_switch_blocks_remote_save` (writes == [], dirty retained).
- EDIT-017/018/019/020/021/022 (save guarantees): owner backend-confirmation-only
  success (`saved` flag), worker exception -> `status.SetLabel`, no `mark_saved`,
  followup (`submit`/`run`) suppressed when `not saved`. Local `_write_local_text`
  validates codec before truncate. Proof: encoding-failure test (dirty + file unchanged),
  vanished-parent supplement, disconnect supplement, remote-failure tests,
  `test_wx_remote_submit_failure_keeps_saved_document_and_surfaces_error`.
- TODO-007 (Save+Submit = sbatch): owner `_editor_action_factory.submit`
  (`slurm.sbatch`; local uploads then `sbatch(remote_path)`), `run` uses
  `ssh.send_shell_text("bash -- ...")` never sbatch; labels `Submit (sbatch)` /
  `Save + Submit` / `Save + Run` match actions.
  Proof: supplement `test_w26_supplement_save_submit_uses_sbatch_not_shell`
  (sbatch path exact, shell contains bash+path, no cross-call).
- TODO-008 (labels match action): owner `i18n/en.json` (`save=Save`,
  `submit=Submit (sbatch)`, `save_run=Save + Run`, `save_submit=Save + Submit`)
  + `_update_save_actions`/`refresh_labels`. Proof: source read + button-label
  assertions in GUI tests (visible labels unchanged by this run).
- TODO-009 (remote-path field is real target): owner header `remote_path` doubles as
  Save As (`hdr_path or snapshot.path`, adopt on success). Editable-but-ignored forbidden
  by construction. Proof: save-as redirect tests (remote + local).
- TODO-010 (prove server content after GUI save): owner same as EDIT-002.
  Proof: supplement server-content test (exact equality, not just dirty-cleared).
- EDITOR-ROUTE-002 (detached only for explicit New Window): owner
  `WxEditorWindowManager.open_new_window` (sole standalone creator) vs
  `open_primary` (reuses `primary_frame`, generation-guarded, in-flight queue).
  Proof: `test_wx_editor_window_parity` suite green (primary reuse, stale-request drop).
- TODO-001 (NAV-EDITOR reuses embedded): owner `wx_shell` `NAV-EDITOR` ->
  `_select_embedded_page` first, `open_primary` fallback.
  Proof: source read + parity suite; no detached frame on normal nav.
- PLUGIN-COMPAT-001: owner `PluginCard` (`version`, `installed`, `enabled`,
  `compatible`) + FIX-W26-B details `"1.0 installed / enabled"` /
  `"2.0 installed / disabled / incompatible"`. Capabilities/provider/tool/template/
  linter types live in installer/loader models; listing now surfaces the
  card-owned subset where relevant. Proof: supplement plugin test.
- TODO-034 (Open wired): owner header `Open` -> `action_factory.on_open` or direct
  `on_open`, `remote_path` ENTER triggers open; local `open_local_file` path.
  Proof: existing remote-editor flow tests + header enabled logic.
- TODO-035 (New from Template): owner header template -> `on_new_template` or
  fallback (`load_job_templates`, none-installed message, first-template preview render).
  Proof: source read + no-crash fallback; template packs load in existing suites.
- TODO-036 (Lint wired): owner header Lint -> `on_lint` or fallback
  (`_collect_lint_issues` + `_show_lint_dialog` with navigation).
  Proof: lint dialog + `run_lint` paths; v2 lint engine tests green.
- TODO-037 (multi-doc verify): owner tabs + dirty marker + close save/discard/cancel +
  duplicate suppression + `_reorder_tabs`. Proof: tabs suite (close variants, reorder),
  W26 duplicate-suppression tests.
- TODO-038 (Save variants separately): owner `save_document(mode="save"|"submit"|"run")`
  + local/remote branches + Save As redirect. Proof: local save, save-as, remote save,
  submit-order, run-order tests (supplement + `test_wx_editor` submit/run order).
- TODO-039 (unicode/line endings): owner UTF-8 throughout + newline pin.
  Proof: unicode model test, CRLF round-trip + GUI CRLF test.
- TODO-040 (failures visible/semantic): owner every failure -> `status.SetLabel`
  or dialog, never silent; dirty retained unless `saved`.
  Proof: encoding/vanished/disconnect/binary/submit-failure tests assert non-empty status.
- CI-PR-002: `scripts/ci.py quick` runs compile + i18n + smoke + ruff; `docs/ci-disabled/`
  preserves the PR workflow for reference while CI is intentionally disabled.
  Worker does not re-enable CI (controller/human-owned). Disposition `DEFERRED_CLEAN`
  with justification recorded here; local lanes verified green (compile OK, i18n OK, ruff clean
  on touched files). No fast-lane weakening.

## Fixes (proof chains)

FIX-W26-A (DEF-W26-001, EDIT-005):
- Before: wx editor had no find UI; EDIT-005 only true on Qt.
- Change: `src/hpc_gui/wx_editor_view.py` +find bar (WrapSizer, i18n hints),
  `+_wx_find_next` (selection-relative + wrap + ShowPosition),
  `+_wx_replace_current` (match-or-find then Replace + model sync),
  `+_wx_replace_all` (count + ChangeValue + model sync), button/ENTER bindings,
  retranslation, host seams `_wx_editor_find_next/_replace_current/_replace_all`,
  controls-dict additions (backward compatible: old keys preserved).
- Regression: supplement wx find/replace test. Sensitivity: pre-fix the test
  cannot import seams (`AttributeError`); post-fix `6 passed` in supplement file.
- No Qt changes; no behavior change to save/open paths.

FIX-W26-B (DEF-W26-002, PLUGIN-COMPAT-001):
- Before: details showed only version/installed.
- Change: `src/hpc_gui/wx_plugins_view.py` details now
  `"{version} {installed|available} / {enabled|disabled}[ / incompatible]"`.
- Regression: supplement plugin test asserts both rows. Sensitivity: pre-fix
  `incompatible`/`disabled` absent; post-fix present.

## Tests and evidence required

- Narrow baseline before edits: `test_w26_editor_identity` -> `12 passed`;
  editor cohort -> `89 passed`.
- Focused post-fix: `test_w26_editor_identity + test_w26_run_supplement +
  test_wx_editor + test_wx_editor_tabs + test_editor_controller` -> `46 passed`.
  Supplement alone -> `6 passed`.
- Governance: `compileall` OK; `scripts/check_i18n.py` OK (keys + references +
  hardcoded-text); `ruff check` clean on touched files; `git diff --check` clean.
- GUI claims: every GUI disposition above backed by wx event/runtime proof
  (`_click` Button events, `SetValue`, `ProcessPendingEvents` pump, readback of
  server dict / file bytes / status label / selection / tab counts), bound to
  candidate `3e9635ba` working tree. `pytest --collect-only` not used as execution.
- External claims: none; no real HPC lab used. `EXTERNAL_BLOCKED` not needed;
  all proofs local/package/GUI with disposable fixtures. Lab identity N/A with
  justification (no owned requirement needs live scheduler for run; submit proven
  at scheduler-abstraction boundary via fake `slurm.sbatch`).
- Package claims: N/A (no artifact SHA required by owned rows).

## Diff review

`git status`: only `M src/hpc_gui/wx_editor_view.py`, `M src/hpc_gui/wx_plugins_view.py`,
`?? tests/test_w26_run_supplement.py` (plus pre-existing unrelated untracked
`.agent-legacy-backup (1)/`, `new 4.ps1`, `tests/contracts (1)/`, `tests/contracts (2)/`
left untouched). `git diff --stat`: 2 files, +140/-2. `git diff --check`: clean.
Full diff inspected: no secrets, no generated/binary noise, no unrelated refactors,
no duplicated business logic into wx views (find helpers are view-local text ops),
no weakened tests/assertions. New tests have meaningful assertions and legitimate
mock boundaries (fake files/slurm/ssh, tmp_path, disposable wx frames).

## Handoff / resume

Run complete. All 37 owned IDs traced to live owners with exact executed validation
except CI-PR-002 recorded as `DEFERRED_CLEAN` (CI intentionally disabled per
`docs/ci-disabled/README.md`; local `scripts/ci.py quick` lanes green; re-enable is
controller/human-owned). No `AWAITING_INPUT` (no concrete missing artifact; W23/W24
integration hints non-blocking per independence contract). No owned blocking defect
remains. Candidate: working tree at `3e9635ba` + W26 hunks listed above.
Next: fresh independent audit (controller-owned) must re-verify dispositions on the
same candidate before close; any behavior-affecting integration change invalidates
this evidence.
