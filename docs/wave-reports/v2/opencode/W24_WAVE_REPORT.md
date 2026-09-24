# W24 — Directories, storage roots and session rebinding - Wave Report

```text
Wave: W24
Canonical report: docs/wave-reports/v2/opencode/W24_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui / develop
Branch: develop
Baseline SHA: ccaf871ffc139973db826363859ca2933b216e9c
Tested implementation: working tree at ccaf871f + W24-owned hunks only
  (src/hpc_gui/wx_directories.py, src/hpc_gui/wx_directories_view.py,
   src/hpc_gui/wx_shell.py [3 hunks], tests/test_wx_directories.py)
Current HEAD: ccaf871ffc139973db826363859ca2933b216e9c
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24
Session status: READY FOR FINAL REVIEW
Wave decision: READY_FOR_AUDIT (independent audit pending, controller-owned)
```

## Scope

W24 owns `HPC-W06-DIR-001..011` plus TODO-details
`HPC-W06-TODO-DIR-SESSION-001, SESSION-REBIND-001, SESSION-REBIND-002,
SESSION-DISCONNECT-001, DIR-SESSION-002, 006, EDITOR-ROUTE-001, 016, 017,
018, 019, 020, 021, 022, 023, 032, 041, 044` per `waves/pending/W24.md`
frontmatter. Mandatory authority read before edits: all
`opencode/REQUIREMENT_REGISTRY.md` W24 rows (11 DIR), all
`opencode/TODO_OWNERSHIP_MAP.md` W24 rows (18 ACTIVE), and
`waves/bak/WAVE_V2_FINAL_06.md` section **Scope / Directories / storage
areas**. Live code inspected before editing
(`wx_directories.py`, `wx_directories_view.py`, `wx_shell.py`,
`wx_remote_files.py`, `services/remote_directory_controller.py`);
no cross-Wave worktree/report/temp edits; no user prompting (unattended).

## Discovery (WAVE_FINDINGS, condensed)

| Finding ID | Severity | Surface | Evidence | Root cause |
|---|---|---|---|---|
| DEF-W24-001 | P1 | New-Slurm destination | `_new_slurm` used build-time `scratch_dir` capture (`wx_directories_view.py:295` pre-fix) | startup-captured path reused at click time |
| DEF-W24-002 | P1 | Directories files backend | `_files()` preferred build-time `snapshot_files` over live session (`:88` pre-fix) | snapshot shadows reconnect/provider-switch backend |
| DEF-W24-003 | P1 | Directory navigation target | `WxDirectoriesWorkspace.double_click(..., is_dir=True)` always navigated the FIRST pane | no selected-storage targeting |
| DEF-W24-004 | P1 | Connect/disconnect rebind | shell `on_connected`/`on_disconnected` never touched the directories panel (verified by source read) | no rebind entry point; labels/models frozen at build |
| DEF-W24-005 | P3 | Splitter/layout/titles | sash `460`, raw-path labels (`:229/:246/:261` pre-fix) | TODO-019/020 non-compliance |

Pre-change baseline: `test_wx_directories.py + test_remote_directory_listing.py
+ test_transfer_directory_controllers.py` -> 13 passed (narrow slice of the
65 below excluding new nodes).

## Requirement trace (requirement -> live owner -> test -> evidence)

- DIR-001 (directories UX is first-class, not inferred from remote files):
  owner `wx_shell.py` embedded `NAV-DIRECTORIES` page + `build_directories_panel`
  (dedicated splitter with two remote panes). GUI runtime proof below.
- DIR-002 (storage areas only when truthfully declared): owner
  `_resolve_scratch_home` (derives scratch/home from session
  `system_settings` via `normalize_system_settings`/`format_remote_path`,
  never hardcoded) + EXTERNAL SFTP listing proving declared roots exist.
- DIR-003 (CONDITIONAL quota/status not fabricated): no quota/status widgets
  exist on the directories surface (source read); nothing to fabricate.
- DIR-004 (root switching updates actual remote path): owner
  `WxRemoteDirectoryModel.navigate` (`PurePosixPath` + tab sync) + FIX-C
  selected-pane targeting.
- DIR-005 (dir actions target selected storage area): FIX-C
  (`double_click(..., storage_id=...)`); per-pane loader/operation closures
  already pane-scoped.
- DIR-006 (breadcrumb/parent cannot escape): owner
  `RemoteDirectoryController._normalize` + `PurePosixPath` navigation;
  no synthesized-path escape (existing `test_remote_directory_listing.py` green).
- DIR-007 (context menus = real toolbar actions): both panes built by shared
  `build_remote_files_panel`, so menu/toolbar dispatch is identical by
  construction (same builder, same callbacks).
- DIR-008 (provider switch rebuilds roots, discards stale callbacks): FIX-B
  (live-first `_resolve_live_files`) + `rebind_directories_storage` (navigate
  + invalidate + history clear) + shell `on_connected` wiring.
- DIR-009 (empty/unavailable distinguishable from loading/error): FIX-D
  (`mark_directories_disconnected` -> "Scratch/Home — disconnected" +
  cache drop) + shell `on_disconnected` wiring.
- DIR-010 (POSIX remote semantics on Windows client): remote navigation uses
  `PurePosixPath` exclusively (`wx_remote_files.py:72-78`); local `pathlib`
  never normalizes remote paths. Client ran on native Windows here.
- DIR-011 (distinct Directories tab accepted): embedded tab exists and was
  constructed in GUI runtime proof (EV-GUI-BUILD).
- TODO DIR-SESSION-001 / SESSION-REBIND-001 (rebind Home/Scratch after
  connect/reconnect): `rebind_directories_storage` + `host._wx_dirs_rebind`
  + shell `on_connected` hook; runtime proof EV-GUI-REBIND.
- TODO SESSION-REBIND-002 (A->B switch replaces all A state): live-first
  backend + rebind (labels/models/caches/history) + shell wiring.
- TODO SESSION-DISCONNECT-001: explicit disconnected labels, stale caches
  dropped, no placeholder `/` presented (fallback `/` only when no session
  data exists at all, i.e. pre-connect build).
- TODO DIR-SESSION-002: FIX-A (`_resolve_new_slurm_target` at click time).
- TODO-006 (favorites/history/filter/navigation rebind): history cleared on
  rebind, navigation store re-pointed via `model.navigate`;
  favorites persist by design (explicit user saves, not provider state).
- TODO EDITOR-ROUTE-001: directories `open_editor` delegates to
  `editor_manager.open_primary(path, content, is_local=False,
  request_id=...)` with request-aware wrapper (same embedded Script Editor
  path as Files; source-read verified, unchanged).
- TODO-016 (no duplicate detached primary windows): embedded dispatch uses
  `_select_embedded_page` (existing page selected, verified by read);
  detached `show_directories` remains as headless/service fallback by design.
- TODO-017 (one shell session-generation contract): shell mints
  `session_state["generation"]` on connect/disconnect; directories consumes
  the same canonical `session_state` live (no parallel contract).
- TODO-018 (toolbar/action inventory): surface exposes `New Slurm/Edit`
  button + per-pane remote-files actions from the shared builder; inventory
  recorded here (no new toolbar introduced).
- TODO-019 (balanced split, preserve user movement): sash `500` (~50/50 of
  1000px host) + `SetSashGravity(0.5)`; runtime readback sash=492.
- TODO-020 (semantic pane titles): labels now `Scratch — <path>` /
  `Home — <path>` (runtime verified).
- TODO-021 (explicit directories toolbar profile): each pane exposes only
  the shared remote-files action set + the single directories-level
  New-Slurm action; no foreign actions added (read-verified).
- TODO-022 (provider panes structurally consistent): both panes built by the
  same code path with distinct models (read + runtime verified).
- TODO-023 (responsive columns/wrapping): minimum pane 260 + proportional
  gravity; verified at 1000x650 build size; narrow-window behavior is a
  residual P3 (see Risks), not a blocker.
- TODO-032: `AWAITING_INPUT` — synchronized-browsing/Compare acceptance must
  run on the exact release candidate, which does not exist in this run;
  no such artifact identity available. All other owned work continued.
- TODO-041: N/A with reason — this run introduces no new shell/session/
  editor/directories/logs/settings/plugins/runtime/release surfaces, so no
  new stable IDs were required; all owned IDs preserved byte-for-byte.
- TODO-044: covered at source/runtime level for Files/Directories/Editor
  routing (`open_primary is_local=False` path + runtime panel proof);
  full packaged-acceptance binds to the release-candidate artifact and rides
  TODO-032's input (no package built in this run; required evidence classes
  for W24 are GUI+EXTERNAL only).

## Fixes (proof chains)

FIX-A (DEF-W24-001, DIR-SESSION-002):
- Before: `_new_slurm` computed `scratch_dir.rstrip()/name` from the
  panel-build capture; switching provider/scratch then creating a Slurm file
  targeted the stale scratch. Before-evidence: source trace + new test fails
  on pre-fix code (3 failed, stash proof).
- Change: `+_resolve_new_slurm_target(session_state, name)` (click-time
  `_resolve_scratch_home`) + `_new_slurm` uses it with live files backend.
- Regression: `test_w24_new_slurm_target_resolves_from_current_session_at_click_time`
  (happy: two sessions -> two targets; negative: stale != live).
- Sensitivity: fails pre-fix (`FAILED ..._click_time`), passes post-fix.
- Suites: focused 65 passed; adjacent 32 passed.

FIX-B (DEF-W24-002, DIR-008/SESSION-REBIND-002):
- Before: `_files()` returned build-time `snapshot_files` whenever non-None,
  so reconnect/provider-switch kept driving the dead backend. Before-evidence:
  source trace + new test fails pre-fix.
- Change: `+_resolve_live_files` (live-first, snapshot only as fallback)
  + `_files()` delegates to it.
- Regression: `test_w24_directories_backend_rebind_prefers_live_session_files`
  (happy: live wins; negative: disconnect falls back safely, empty -> None).
- Sensitivity: fails pre-fix, passes post-fix.

FIX-C (DEF-W24-003, DIR-005):
- Before: `double_click(is_dir=True)` navigated `next(iter(self.remote))`
  regardless of selected pane. Before-evidence: `TypeError` pre-fix (no
  `storage_id` param) + wrong-pane behavior by read.
- Change: `double_click(..., storage_id="")` targets
  `self.remote[storage_id]`, compat fallback to first pane.
- Regression: `test_w24_double_click_targets_selected_storage_area`
  (happy: home navigates, scratch untouched; negative: compat path preserved).
- Sensitivity: fails pre-fix, passes post-fix.

FIX-D (DEF-W24-004, DIR-SESSION-001/REBIND-001/DISCONNECT-001/DIR-009):
- Before: shell never rebound the directories panel (source-read proof).
- Change: `+rebind_directories_storage` (labels/models/caches/history),
  `+mark_directories_disconnected`, host hooks `_wx_dirs_rebind` /
  `_wx_dirs_disconnected`, `wx_shell.py` 3 hunks (panel registration in
  `session_state`, `on_connected` rebind, `on_disconnected` disconnect mark).
- Regression: `test_w24_directories_rebind_and_disconnect_helpers`
  (happy: paths/labels/models update; negative: disconnect labels, history
  cleared). Runtime: EV-GUI-REBIND + EV-GUI-DISCONNECT below.
- Additional (DEF-W24-005, TODO-019/020): sash 460->500 + gravity 0.5,
  semantic labels; covered by runtime readback (no dedicated unit node;
  supporting evidence only, not counted toward the floor).

Post-green review: detached `show_directories` shares `_build_directories`
so all fixes apply to both entry points; `_files` None-path returns `()`
with visible `no_connection` warning (no silent fallback); error paths use
existing `MessageBox` contract; no alternate UI bypass found; mocks limited
to in-memory backends in unit nodes only (real wx + real SFTP prove the rest).

## Tests and evidence (exact)

- Focused: `test_wx_directories.py + test_remote_directory_listing.py +
  test_transfer_directory_controllers.py + test_wave2_directories_local_files.py`
  -> `65 passed in ~10.8s` (`.tmp/w24-run/w24-focused.txt`). Exit 0.
- Adjacent: `test_wx_shell.py + test_wx_lifecycle.py + test_wx_remote_files.py
  + test_directory_comparison.py` -> `32 passed in ~2.3s`
  (`.tmp/w24-run/w24-adjacent.txt`). Exit 0.
- Sensitivity: `git stash push` of the two model/view files -> the 3 new
  unit nodes FAIL (`3 failed, 2 passed`); `git stash pop` -> `5 passed`.
- `git diff --check` on all 4 owned paths: clean (exit 0).
- GUI FULL (real wx 4.3.1, native Windows, no mocks):
  `EV-GUI-BUILD` labels `Scratch — /scratch/hpctest | Home — /home/hpctest`,
  models bound, sash=492 gravity=0.5;
  `EV-GUI-REBIND` switch to `/scratch/other + /home/other` reflected in
  labels AND models; `EV-GUI-DISCONNECT` labels `— disconnected`;
  `EV-GUI-SHELL-WIRING` (`_embedded_directories_panel`, `_wx_dirs_rebind`,
  `_wx_dirs_disconnected` present in `wx_shell.py`).
- EXTERNAL (LOCAL_REAL_HYPERV, controller 192.168.250.11:22, user hpctest,
  profile SHA `a99c96fd...`, image pin PASS): real key-auth SFTP listing
  `EV-EXT-LIST /srv/hpc/scratch/hpctest -> []` (truthfully empty) and
  `/home/hpctest -> [slurm-*.out, .cache, ...]` (8 entries). No mutation,
  no credentials in logs. Lab health note: `lab-status.ps1` reports
  `FAIL` solely because `compute01|down` (Slurm); controller/compute02
  transports+services healthy — storage-root listing evidence is unaffected
  and truthful; no lab rebuild performed.
- Closeout validator: not run as gate here (manifest/closeout is
  controller-owned at CLOSE phase).

## Diff review

Owned `git diff --stat`: 4 files, +251/-13, all intended hunks.
`wx_shell.py` shows one additional pre-existing stacked hunk
(`top_splitter.SetSashGravity(0.5)`, not authored here — preserved, not
claimed). No secrets/keys/tokens in added lines (scanned; only `key`
loop-var false positives). No binary noise. No weakened tests (no new
skip/xfail; all assertions behavioral: target identity, backend identity,
label text, model paths). Unrelated dirty tree preserved untouched.

## Findings / routing

- All four W24-owned P1 defects repaired in-scope with changed hypotheses
  (stale-capture -> live-resolve; snapshot-first -> live-first; first-pane
  -> selected-pane; no-rebind -> shell-wired rebind).
- TODO-032 rides `AWAITING_INPUT` (missing release-candidate identity) for
  that item only; TODO-041 N/A with reason; TODO-044 source/runtime covered,
  package binding deferred with TODO-032 input.
- No cross-scope defects; nothing routed to another owner.

## Residual risks / P3

- Narrow-window (<~600px) directories ergonomics not exhaustively proven
  (P3, workaround: proportional splitter + 260px minimums hold).
- `lab-status` Slurm `compute01|down` is infrastructure state, not a product
  finding; flagged for lab maintenance, no product routing.

## Resume state

Implementation complete; evidence current at candidate HEAD `ccaf871f` +
owned working-tree hunks above. Next: controller-owned fresh independent
audit, then controller-owned manifest/closeout. This worker starts no
downstream Wave.

```text
FIX-A: _resolve_new_slurm_target (click-time scratch resolve)
FIX-B: _resolve_live_files (live-first backend rebind)
FIX-C: double_click storage_id targeting
FIX-D: shell-wired connect/disconnect rebind
Two-fix gate: PASS (4 independent substantive remediations)
Wave decision: READY_FOR_AUDIT
```
