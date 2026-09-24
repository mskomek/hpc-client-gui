# W25 - Transfer workspace, overwrite and integrity - Wave Report

```text
Wave: W25
Canonical report: docs/wave-reports/v2/opencode/W25_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui / develop
Branch: develop
Baseline SHA: ccaf871ffc139973db826363859ca2933b216e9c
Tested implementation: working tree at ccaf871f + W25-owned hunks only
  (src/hpc_gui/services/transfer_controller.py,
   src/hpc_gui/services/transfer_session_controller.py,
   src/hpc_gui/wx_transfer_workspace.py,
   src/hpc_gui/wx_shell.py [W25 hunks only],
   src/hpc_gui/wx_editor_view.py,
   src/hpc_gui/wx_settings.py, src/hpc_gui/wx_settings_view.py,
   src/hpc_gui/i18n/en.json + tr.json [7 keys each],
   tests/test_w25_transfer_workspace_integrity.py [new])
Current HEAD: ccaf871ffc139973db826363859ca2933b216e9c
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: READY_FOR_AUDIT (independent audit pending, controller-owned)
```

## Scope

W25 owns `HPC-W06-XFER-001..019` plus TODO-details `HPC-W06-TODO-013`
(settings review) and `HPC-W06-TODO-043` (SHA-256 integrity +
cancel/retry/failure/conflict) per `waves/pending/W25.md` frontmatter.
Mandatory authority read before edits: all
`opencode/REQUIREMENT_REGISTRY.md` W25 rows (19 XFER), all
`opencode/TODO_OWNERSHIP_MAP.md` W25 rows (2 ACTIVE), and
`opencode/sources/WAVE_V2_FINAL_06.md` sections **Scope / Transfer
workspace**, **Workstream D - Transfers**, **Workstream E -
Overwrite/conflict matrix**. Live code inspected before editing
(`wx_transfer_workspace.py`, `services/transfer_controller.py`,
`services/transfer_session_controller.py`, `services/transfer_integrity.py`,
`services/transfer_mode.py`, `services/files_ssh.py`, `wx_shell.py`
transfer/editor paths, `wx_editor_view.py`, `wx_editor.py`,
`services/editor_controller.py`, `wx_settings.py`, `wx_settings_view.py`,
`config/storage.py`, Qt `remote_dir_panel.py` verify path as parity
reference). No cross-Wave worktree/report/temp edits; no user prompting
(unattended). The controller handoff carried a PASS audit receipt for W24
only; it is an integration reference, not W25 evidence, and no W24 state
was reused as acceptance.

## Discovery (WAVE_FINDINGS, condensed)

| Finding ID | Severity | Surface | Evidence | Root cause |
|---|---|---|---|---|
| DEF-W25-001 | P1 | Embedded transfer panel rows | debug script: `SetItemData` stored `549380912` for `id()` `2079313552176`; queue rows never removed/updated | 64-bit `id()` truncated by 32-bit C `long` in `wx.ListCtrl.SetItemData` on Windows; `_find_row` could never match |
| DEF-W25-002 | P1 | Retry UI state | source read: `retry_failed` restores items without re-announcing; panel never evicts failed/completed rows for reused identity | no `queued` re-emit; panel only appends on queued/started |
| DEF-W25-003 | P2 | Disconnect + transfers | source read: `on_disconnected` drops session/generation but never touches `transfer_sessions` | no invalidation entry point; transfers parked on dead transport until socket timeout |
| DEF-W25-004 | P1 | wx SHA-256 path | source read: `checksum_enabled`/`set_checksum` stored a flag no transfer path reads; wx settings checkbox persisted nowhere; shell never called `set_checksum_enabled` | unwired opt-in across three layers |
| DEF-W25-005 | P1 | Editor Save As | source read: `save_document` parsed the header path then `pass`; no Save As exists anywhere in `src/hpc_gui` | header-path redirect never implemented |
| DEF-W25-006 | P2 | Editor external change | source read: local save is blind `write_text`; remote save is silent last-writer-wins with no named policy | no baseline, no prompt, no explicit policy |

Pre-change baseline (narrow, before edits): `test_transfer_controller.py +
test_transfer_integrity.py + test_transfer_wave17.py +
test_transfer_cancel_recovery.py + test_wx_transfer_workspace.py` ->
`32 passed`. Broader transfer/conflict/lifecycle suites were green except
for the defects above (proven by failing new nodes pre-fix, see
Sensitivity).

## Requirement trace (requirement -> live owner -> test -> evidence)

- XFER-001 (queue/list state): owner embedded 3-tab `build_transfers_panel`
  (queue/failed/completed `ListCtrl`s) + FIX-A row tokens + FIX-B retry
  eviction. Runtime proof: new panel tests assert exact row counts through
  fail -> retry -> complete.
- XFER-002 (progress): owner SSH backend per-chunk `progress_cb`
  (`files_ssh._download/_upload` increment-only counters) forwarded by the
  engine to per-row cells + status line + detached gauge
  (`SetRange(max(1,total))`). Runtime proof: concurrent panel test drives
  `progress(0,2)`/`progress(2,2)` into isolated rows.
- XFER-003 (success/failure): owner engine `completed`/`failed` lists +
  `completed`/`errors` tabs + `finish()` labels. External proof: replay
  `download_bytes` identical + `upload_sha256` VERIFIED.
- XFER-004 (cancellation): owner `cancel_all` -> `TransferCancelled` inside
  chunk loop + between items; window close cancels in-flight; cancel button
  disables with `transfer.cancelled` label. External proof: replay
  mid-32MiB cancel -> `failed=[(..., 'cancelled')]`.
- XFER-005 (overwrite/conflict behavior): owner `create_transfer_conflict_dialog`
  (Overwrite/Resume?/Skip/Rename/Cancel) + session `ask` policy + `_destination_exists`
  (remote probe for uploads, `os.path.exists` for downloads). 11 conflict-UI
  tests green, unchanged.
- XFER-006 (cleanup of partial results): owner `clear_pending` /
  `stop_after_current` / close-cancel + disposable-fixture discipline.
  External proof: replay `cleanup: removed`, lab `NONE_LEFT`.
- XFER-007 (monotonic progress): backend counters only increase
  (`downloaded +=`, `sent +=`, resume starts at existing size then grows);
  completion is a terminal `progress(1,1)` sentinel, not a regression.
  Verified by source read of both transfer directions + runtime replay.
- XFER-008 (unknown total honest): no percentage math anywhere; labels show
  `done/total` verbatim; gauge uses `max(1,total)` so total 0 cannot
  divide-by-zero or fake 100%. Verified by source read.
- XFER-009 (cancel never flips to success): engine `_one` re-checks cancel
  after `run_item`, and terminal `progress(1,1)` raises when cancelled.
  Proof: `test_controller_cancel_keeps_item_failed_without_finalization` +
  replay `cancel_no_success_flip`.
- XFER-010 (retry is a new clear state): FIX-B - engine re-emits `queued`
  for restored items; panel evicts stale failed/completed rows on
  queued/started. Proof: new engine + panel retry tests; replay
  `retry_clean_upload` VERIFIED after cancel.
- XFER-011 (partials under explicit policy): raw SSH path writes in place
  with strict-prefix resume (`resume_upload/download` reject larger
  destinations via `RESUME_DEST_LARGER`); mode path uses `.part` + atomic
  rename (`transfer_mode`, Wave-17 suite green); cancel/failure lands
  visibly in `failed`, never success. Policy codified in code comments and
  here.
- XFER-012 (transfers cannot steal each other's UI status): per-row token
  updates via `_find_row`; status line shows the last active item only.
  Proof: new concurrent-isolation test (block both, assert 2 queue rows;
  finish one mid-flight, other row undisturbed; both complete).
- XFER-013 (disconnect invalidates predictably): FIX-C -
  `_cancel_transfer_sessions` + `on_disconnected` wiring. Proof: new unit
  node (session cancel + engine fallback + junk tolerance).
- XFER-014 (matrix header): per-item `conflict_check` + resolver routing in
  `_start_file_transfers`; each matrix leg traced below.
- XFER-015 (local->remote exists): prompt/policy/cancel-safe via conflict
  dialog + pre-run check (cancel path never touches the backend). External
  proof: replay `overwrite_cancel_safe` (remote digest unchanged,
  engine `cancelled`).
- XFER-016 (remote->local exists): same dialog path; existence probed with
  `os.path.exists` (remote-`exists` would miss real conflicts and invent
  phantom ones). Covered by download-direction conflict tests + download
  integration tests, unchanged and green.
- XFER-017 (editor local save changed externally): FIX-E - at-open
  `(mtime_ns, size)` baseline per local document (`_note_disk_baseline` at
  build + `load_document` + post-save refresh); stat change triggers a
  content-compare prompt; decline preserves disk and edits. Proof: new
  cancel/overwrite wx tests + no-prompt regression. Known limitation: a
  same-tick same-size rewrite is invisible to stat (documented).
- XFER-018 (editor remote save conflict policy explicit): codified
  last-writer-wins policy comment on `_editor_action_factory` (no
  versioned compare-and-swap exists server-side); failed saves keep dirty
  state; Save As to existing remote targets prompts via `target_exists`.
- XFER-019 (Save As target exists): FIX-E - header-path edit redirects the
  save; existing targets prompt (local `os.path.exists`, remote
  `target_exists` probe); decline is side-effect free; success adopts the
  new document identity (model path + header). Proof: 3 new wx tests
  (cancel-safe, overwrite+adopt, remote redirect with prompt text
  containing the target).
- TODO-013 (settings review): reviewed each named item against live code -
  transfer type (`ftp_transfer_type` choice in Files header + stored
  default `auto`, Qt+wx present); upload confirmation (standalone
  preflight confirmation exists stored-default-true with Qt UI; wx file
  transfers confirm via the overwrite/conflict dialog; no blocking gap);
  checksum (FIX-D: previously decorative in wx, now persisted + honored);
  transfer speed test (service `run_transfer_speed_test` + unit tests;
  trigger lives in Qt settings; no wx trigger - noted non-blocking parity
  observation, no W25-owned defect); CLI access/default profile/remote
  defaults/file associations/shortcut preferences/provider-profile
  settings (present: CLI `files` surface, profile/SSH settings, shortcut
  preferences model; review-only, no change).
- TODO-043 (SHA-256 integrity + cancel/retry/failure/conflict): FIX-D -
  optional `verify` hook on `TransferSessionController` (mismatch raises ->
  engine FAILED; unsupported passes); wx `_verify_transfer_item` mirrors
  Qt semantics (OFF/UNSUPPORTED/VERIFIED/FAILED); checksum bridge makes
  the wx checkbox persist to the stored setting. Proof: 4 new unit nodes
  + `test_streaming_match_and_mismatch` et al green + replay digest match.

## Fixes (proof chains)

FIX-A (DEF-W25-001, XFER-001/003/012):
- Before: every embedded row stored raw `id(item)` via `SetItemData`;
  on 64-bit Windows the value truncated (`2079313552176` ->
  `549380912`, debug script `.tmp/w25-panel-debug.py`), so `_find_row`
  always returned -1: queue rows never cleared, progress cells never
  updated, failed/completed removal silently no-oped.
- Change: `+_row_token` (small per-panel sequence; owning refs held in
  state maps so `id()` keys cannot recycle) + all three
  `SetItemData`/`GetItemData` sites use tokens.
- Regression: `test_embedded_panel_retry_clears_failed_rows`,
  `test_embedded_panel_tracks_concurrent_transfers_in_isolated_rows`.
- Sensitivity: both fail pre-fix (row counts never converge); pass post-fix.

FIX-B (DEF-W25-002, XFER-010):
- Before: `retry_failed` restored pending silently; panel kept the stale
  failed row, showing the item twice after restart.
- Change: engine re-emits `queued` per restored item (mirrors `enqueue`);
  panel evicts failed/completed rows on queued/started.
- Regression: `test_engine_retry_failed_reannounces_queued` + panel retry
  test. Sensitivity: fail pre-fix, pass post-fix.

FIX-C (DEF-W25-003, XFER-013):
- Before: disconnect left `transfer_sessions` running against a dead
  transport until socket timeout.
- Change: `+_cancel_transfer_sessions(session_state)` (cancel() preferred,
  engine `cancel_all` fallback, never raises) + `on_disconnected` call.
- Regression: `test_cancel_transfer_sessions_cancels_and_tolerates_junk`.
  Sensitivity: fails pre-fix (`AttributeError`/0 count), passes post-fix.

FIX-D (DEF-W25-004, TODO-043 + TODO-013 checksum):
- Before: checksum flag stored nowhere-consumed; wx checkbox in-memory only;
  shell never enabled verification.
- Change: `verify=` hook on `TransferSessionController`;
  `+_verify_transfer_item` (Qt-parity OFF/UNSUPPORTED/FAILED semantics);
  shell passes the hook and enables it from the stored setting;
  `+persist_transfer_checksum_to_storage` + settings-apply wiring.
- Regression: mismatch/unsupported/disabled/persist unit nodes.
  Sensitivity: all fail pre-fix, pass post-fix.

FIX-E (DEF-W25-005/006, XFER-017/018/019):
- Before: header path parsed then ignored (`pass`); local saves blind;
  remote policy unnamed.
- Change: Save As redirect + exists prompts + cancel-safe decline +
  identity adoption; at-open disk baselines + external-change prompts;
  explicit last-writer-wins remote policy comment + `target_exists`
  probe; 7 new `editor.*` i18n keys in EN+TR (parity test green).
- Regression: 6 new editor wx tests. Sensitivity: 4 fail pre-fix
  (Save As never lands; prompts never fire); 2 no-prompt guards pass
  both ways by design.
- Design note: a first naive content-only detector fired on documents
  legitimately opened with content != disk (broke 8 cross-view tests);
  replaced with the at-open stat baseline (changed hypothesis, same run).

Post-green review: `verify` defaults None (all existing controllers
unchanged); prompts fire only on genuine save-as/external states (full
editor suites green with real `MessageBox` unmocked); i18n sets match;
no alternate save bypass (single `save_document` choke point); mocks in
new tests are in-memory backends + dialog fakes only.

## Tests and evidence (exact)

- New: `tests/test_w25_transfer_workspace_integrity.py` -> `14 passed`
  (6 unit + 8 wx runtime). Exit 0.
- Sensitivity: owned `src` hunks stashed -> `12 failed, 2 passed`;
  popped -> `14 passed`. The 2 pass-both-ways nodes are intentional
  no-prompt regression guards.
- Focused transfer: controller/integrity/wave17/cancel/concurrency/resume/
  speed/key-release/parallelism-migration/performance/directory-controllers
  -> `99 passed, 3 subtests passed`. Exit 0.
- Transfer UI (per-file, crash-safe): conflict-ui `11 passed`;
  ui-lifecycle `14 passed`; file-transfer-integration `29 passed`;
  wx_transfer_workspace `2 passed`. Exit 0 each.
- Editor (per-file): w25-new `14` (above) + editor/tabs/parity/
  cross-view/remote-flow/controller/flow/shortcut/lint all green
  per-file (`11/14/7/3/14/2/8` + `41` for editor+cross-view batch).
- Shell/settings/i18n: `test_wx_shell.py 5`, `p0 13`, `w01_truth 16`,
  `i18n 3`, `p0_stress 1` (189s), `w12_sftp 16` (with
  directory-controllers), i18n+profile+wave8 `23`, file-context-i18n `5`,
  w03-settings `17`. Exit 0 each.
- `git diff --check` on owned paths: clean. `ruff check` on all 9 owned
  files: pass (one `wx_shell.py:1454` F401 is pre-existing on `HEAD`,
  verified via stash; untouched).
- GUI FULL (real wx, native Windows, unattended): conflict dialog buttons
  incl. direction-gated Resume; embedded queue/failed/completed row
  transitions with exact counts; retry clearing; concurrent isolation;
  Save As prompts with target in text; cancel-safe statuses
  (`save_as_cancelled`, `external_change_cancelled`); remote redirect
  delivering the new path to `save_remote`.
- EXTERNAL (LOCAL_REAL_HYPERV, `192.168.250.11:22`, `hpctest`, key auth,
  profile SHA `a99c96fd...`, image pin PASS): replay
  `.tmp/w25-external-replay/W25_SFTP_REPLAY.json` - connect, namespace,
  `upload_sha256` (local==remote `93a5a4e7dfae`), `download_bytes`
  (106496 identical), `overwrite_cancel_safe` (digest unchanged,
  engine `cancelled`), 32MiB `cancel_no_success_flip`,
  `retry_clean_upload` digest-verified, `cleanup: removed` (lab
  re-checked `NONE_LEFT`). No credentials in logs (key path only).
- Lab health note: `lab-status.ps1` reports `FAIL` solely for Slurm
  (`compute01|down`); all transports/services healthy, image pin and
  profile valid. SFTP-scope evidence is unaffected and truthful; no lab
  rebuild performed (out of scope; Slurm recovery is lab-ops owned).
- PACKAGE: N/A with reason - W25 required evidence classes are
  GUI+EXTERNAL only; no artifact built or claimed (matches TODO-041-style
  scoping; cf. W24 TODO-032/044 handling).
- Closeout validator: not run as gate here (manifest/closeout is
  controller-owned at CLOSE phase).

## Diff review

Owned `git diff --stat`: 9 files, +352/-24, all intended hunks (details in
header). `wx_shell.py` additionally carries pre-existing stacked hunks
(directories panel registration, sash gravity, connect-rebind - authored
outside W25, preserved, not claimed). `en.json`/`tr.json`: +7 keys each,
sets match (`test_translation_key_sets_match_for_wx_surfaces` green). No
secrets/keys/tokens in added lines (key_path is a filesystem path, no
secret material). No binary noise. No weakened tests (no new skip/xfail;
new assertions are behavioral: row counts, digests, paths, labels,
engine states). Pre-existing dirty tree preserved untouched
(`git status` reviewed; unrelated M files not staged/touched).
`.tmp/w25-panel-debug.py`, `.tmp/w25-external-replay/*`,
`.tmp/w25-reg.txt` are run state under `.tmp/` only. Pre-existing
`wx_shell.py:1454` ruff F401 left as-is (not W25 scope).

## Findings / routing

- All six W25-owned defects repaired in-scope with first-try hypotheses
  except FIX-E detection, which required one changed hypothesis
  (content-compare -> at-open stat baseline) after the naive variant
  broke 8 cross-view tests; no no-progress cycle (content identity
  changed with the hypothesis).
- Cross-scope observations (not blockers, no owner repair attempted):
  (a) multi-file single-session wx runs crash with an access violation
  in teardown - reproduced identically on pristine `HEAD`, pre-existing
  harness fragility, evidence taken per-file instead; (b) wx settings
  surface persists only the checksum bridge - further wx<->stored
  settings parity belongs to the settings owner; (c) `compute01|down`
  is lab-ops owned.
- No `AWAITING_INPUT`, no `HUMAN_DEFERRED`, no `EXTERNAL_BLOCKED`: every
  owned requirement has local/package-independent GUI evidence plus real
  SFTP evidence where the matrix demands it.

## Risks / resume

- Same-tick same-size external rewrites are invisible to the stat
  baseline (accepted limitation, documented in code + here).
- Remote Save As without an `exists` probe proceeds (capability-dependent
  limitation, documented); all shipped backends expose `exists`.
- Retry-while-running against a live engine keeps prior engine semantics
  (unchanged); UI now reflects requeue honestly.
- Resume point if audit reopens: rerun `tests/test_w25_transfer_workspace_integrity.py`
  + replay script (disposable namespace, ~3 min) on the new candidate.
