# wx Migration Wave Status Ledger — Waves 00–77 (historical ledger + current verification)

> **Historical ledger baseline:** `da44f639` (2026-09-06) — supersedes `e3408fd`; not the current repository HEAD
> **Current verification source HEAD:** `12ce79935bf076e1062c57dc7dbd148bad2bfae1` (`develop`, 2026-09-12)
> **Branch:** `develop`
> **Wave 72 note:** Terminal rebaselined — Wave 45 downgraded to PARTIAL per `docs/v2/TERMINAL_PARITY_CONTRACT_72.md`; `GUI-TERM-001` = PARTIAL until Waves 73-76 prove xterm.js chain. Do not mark VERIFIED_COMPLETE before measured evidence.
> **Rule:** Qt remains production runtime (`DEFAULT_GUI_RUNTIME="qt"`). wx is optional.
> **Evidence standard:** `PROVEN` requires `real wx event → visible wx control → adapter → controller/service → fake/disposable backend → completion → visible UI result` with lifecycle/generation/stale protection. Model-only, source-string, import-only, or `wx.Yield` loops do NOT count as PROVEN.
> **Screenshots:** canonical set at `audit/gui-screenshots/{qt,wx}/` with `HASHES.json` SHA256. Windows package smoke must be real artifact, not `src` import.

## Current verification supplement — 2026-09-12

- `GUI-TERM-001` remains **PARTIAL**. The current packaged Windows artifact
  reached the wx frame; its xterm DOM focus readback and loopback PTY resize
  succeeded, but this dirty-tree run is not a dedicated clean-HEAD packaged
  WebView2 readiness PASS. The
  latest artifact (`c83c1b05c157a97b040c705efe722855cd1511ee3b59de19c87341e18a38394f`)
  could not be foregrounded, so guarded input was not sent (DOM/bridge/SSH event
  counts were zero). A preceding artifact (`21141a8b3bb272269234bb18136afefe49927fa5530f85ca8aa5cec64c6c8394`)
  was foregrounded and accepted 36/36 `SendInput` events, but produced no
  terminal output. Both are dirty-tree artifacts based on HEAD `12ce799`; the
  full packaged smoke remains **FAIL**, not parity evidence or a clean-HEAD run.
- The native `0x80004004 (Operation aborted)` was reproduced when WebView2
  creation was deliberately cancelled by destroying its host before async
  controller creation completed. This is a teardown-cancellation reproduction,
  not the latest packaged smoke failure; that report's error is
  `keyboard_input:foreground_lost`. The exact internal WebView2 COM method that
  surfaced the HRESULT was not captured, so it is not claimed as a diagnosed
  native-runtime root cause.
- A current Ubuntu 24.04 Qt onedir artifact passed `--help`, version, doctor,
  and 20-second offscreen GUI startup smoke. The build excluded only
  `wxPython==4.3.1`: installing the complete release lock failed because this
  cached image has no C compiler to build wxPython. This is not Linux wx/WebKit
  or a complete official release build. macOS packaging remains NOT EVIDENCED.
- Current source wx screenshots were captured with disposable mock data. They
  are not packaged screenshots or human sign-off. The capture helper now finds
  pages by their actual notebook handles; synthetic native context-menu capture
  is omitted because it blocks the audit loop.
- Existing-user migration remains **PARTIAL**; complete authentic historical
  keychain/provider/updater/terminal fixtures were unavailable. No live TRUBA,
  scheduler, production SSH/SFTP, or production data was used.
- Follow-up lifecycle revalidation found two unresolved runtime defects. In
  `test_wx_shell_p0_stress_real_wx_paths`, a remote-files completion callback
  accessed `notebook.GetSelection()` after its Notebook was destroyed
  (`src/hpc_gui/wx_remote_files_view.py:592`). In
  `test_find_next_prev_advances_through_matches`, closing the WebView2 panel
  produced a Windows native access violation at
  `src/hpc_gui/wx_terminal_webview.py:979`. These findings qualify the earlier
  passing test snapshot: lifecycle status is **PARTIAL**, not a current
  unqualified PASS. No production code was changed in response.

### Existing-user state category audit — 2026-09-12

| Category | Status | Evidence / limit |
|---|---|---|
| Profiles | **PASS (narrow legacy shape)** | Version-1 profile fixture migrates missing IDs, preserves Unicode/unknown nested fields, backs up original bytes, and is idempotent (`test_wx_migration.py`). No archived customer config fixture was available. |
| Normal settings | **PARTIAL** | Legacy global transfer parallelism is copied into profiles and remains idempotent (`test_transfer_parallelism_migration.py`); this is not a full historical settings migration. |
| Language | **NOT EVIDENCED** | No representative historical language-preference fixture/migration test. |
| GUI preferences | **NOT EVIDENCED** | No complete old-format GUI preference fixture. |
| Shortcuts/keymap | **PASS (narrow legacy shape)** | `shortcut_preferences` legacy map and bindings are preserved/versioned (`test_shortcut_preferences.py`); no archived user file was available. |
| Provider/plugin configuration | **NOT EVIDENCED** | Current provider behavior tests are not proof of old-user migration. |
| Provider storage mappings | **NOT EVIDENCED** | No old-format storage mapping fixture. |
| Quota/provider settings | **NOT EVIDENCED** | No representative historical quota/provider settings fixture. |
| Updater settings | **NOT EVIDENCED** | No old-format updater preference fixture. |
| Terminal settings/history | **NOT EVIDENCED** | No historical terminal settings/history fixture. |
| Credential/keychain references | **NOT EVIDENCED** | No real legacy credential-reference/keyring fixture; no secrets were fabricated. |
| Legacy Qt-era configuration as a whole | **PARTIAL** | Only the tested profile/settings/keymap legacy shapes are covered; no complete Qt-era user-data fixture. |
| Unknown keys and Unicode | **PASS (tested config path)** | Nested future fields and Turkish/Japanese profile values survive the version-1 migration fixture. |
| Interrupted/corrupt migration safety | **PASS (tested recovery path)** | Save failure preserves source bytes and backup; malformed roots are moved to unique recovery backups (`test_wx_migration.py`). Restoring every user-data store is not covered. |
| Idempotence | **PASS (tested paths)** | Profile ID/global transfer-parallelism and keymap migrations are repeatable without data loss. |
| Secret exclusion | **PARTIAL** | Diagnostic bundle omits `config.json` and tests assert the sample password is absent; migration log/redaction coverage across all stores is not established. |

Overall existing-user migration remains **PARTIAL**. The narrow PASS entries
are not evidence of complete historical migration or a customer-data rehearsal.

## 1) Qt Reference

`src/hpc_gui/ui/main_window.py:138-157` — 6 embedded `QTabWidget` pages: Connection, Jobs & Outputs, Directories, Files, Script Editor, Logs. Terminal is wx-only primary-tab deviation (documented). Help, Settings, Plugins, ANSYS dialog are top-level.

## 2) Historical Wave Table Snapshot (HEAD da44f639 → rebaselined via Wave 72)

> **Wave 72 rebaseline (2026-09-06):** Wave 45 was `VERIFIED_COMPLETE` on TextCtrl evidence (`test_wx_terminal` 2 + `test_wx_embedded_terminal` 9 real-button→model→visible TextCtrl). That chain does NOT prove xterm.js parity (see `TERMINAL_PARITY_CONTRACT_72.md` gaps #1-35). Wave 45 is now **PARTIAL**; `GUI-TERM-001` is **PARTIAL** (TextCtrl chain PROVEN, xterm chain MISSING). `GUI-TERM-002` remains COVERED independently. Waves 73–76 must prove the `WebView/xterm → bridge → ssh.send_shell_input/resize_shell_pty` chain before `GUI-TERM-001` may return to COVERED.

Behavioral / visual / platform / packaged / release are separate. `VERIFIED_COMPLETE` only if all acceptance criteria for that wave are met. `PARTIAL` = exists but incomplete. `FAILED_VERIFICATION` = claim does not survive evidence standard. `BLOCKED` = prerequisite/environment absent. `NO-GO` = gate blocks.

| Wave | Requirement | Current Implementation | Evidence Type | Real Test(s) | Observed Result | Status | Remaining Blocker |
|---|---|---|---|---|---|---|---|
| 42 wx Shell | wx.App/bootstrap, 7-tab notebook, chrome row, language menu, tray, lifecycle | `wx_shell.py:72-900` notebook 7 tabs, chrome row, tray adapter, lifecycle shutdown | PROVEN (shell) + STRUCTURAL (tray) | `test_wx_shell.py`, `test_wx_shell_p0.py`, `test_wx_shell_p0_stress.py` | 24/24 P0 + 50 close PASS; tray notify works, chrome parenting not leaking | **PARTIAL** | Canonical screenshots current HEAD not yet regenerated; DPI 150/200 not proven (resize only) |
| 43 Help/Command Palette | Help searchable, command palette, shortcut settings | `wx_help.py` present, command_registry wired | PARTIAL | `test_wx_help.py` | Help dialog keyboard accessible, palette wired but visual parity incomplete | **PARTIAL** | Visual parity + shortcut settings wiring proof |
| 44 Connection | Profile lifecycle, X11, keepalive, provider selection | `wx_connection.py` complete | PROVEN | `test_wx_connection.py` | Real wx event → adapter → fake backend → visible profile list | **VERIFIED_COMPLETE** | Visual parity DPI |
| 45 Terminal (pre-72 TextCtrl) | PTY, Find/Clear/font, Ctrl-C vs copy, i18n, bounded 5000 — TextCtrl only | `wx_terminal.py:16-305` `TerminalModel` + `build_terminal_panel` via `wx.TextCtrl` TE_MULTILINE/TE_RICH2, `splitlines()` 5000, fixed `8x18` estimate, `Ctrl→C/D/Z` only | PROVEN (TextCtrl) but **NOT xterm** | `test_wx_terminal.py` (2 model), `test_wx_embedded_terminal.py` (9 PROVEN real-button→model→visible TextCtrl) | All 11 PASS on TextCtrl, **0 xterm/ANSI/\r/alt-screen/Unicode/paste/PTY-fit evidence** | **PARTIAL** (rebaselined Wave 72) | xterm renderer absent — blocked by Waves 73-76: needs WebView/xterm.js + FitAddon + single JSON bridge + output queue + readiness + navigation/Ctrl/Unicode/paste → real PTY |
| 46 Local File Browser | tabs, path, drives, sort, columns, menu, Ctrl-C/X/V, middle-click | `wx_local_files.py:50-810` complete | PROVEN | `test_wx_local_files.py`, `test_wx_file_context_matrix.py`, `test_wx_file003_final_stress` | Context matrix + stress 200 retarget PASS | **VERIFIED_COMPLETE** | — |
| 47 Remote Directory Browser | listing cache, batch, tabs, path state | `wx_remote_files.py` + `wx_remote_files_view.py` | PROVEN | `test_wx_remote_files.py` | Listing with cache, batch, tabs | **VERIFIED_COMPLETE** | — |
| 48 FTP/Transfer Workspace (sync browsing + compare) | sync roots, guard, compare with generation, visible result | `wx_shell.py:156-560` Files header sync_cb/compare_btn + `services/synchronized_browsing.py`, `services/directory_comparison.py`; generation+stale check, worker thread, visible TextCtrl | PROVEN | `test_wx_files_sync_compare.py` (8 PROVEN: real checkbox/button → service → fake FS → visible) | 8/8 PASS | **VERIFIED_COMPLETE** | DPI/resize |
| 49 Directories Workspace | provider-generic remote panes, splitter | `wx_directories_view.py` | PARTIAL | manual | Two panes splitter, generic proof; TRUBA/GENERIC provider-specific checks PARTIAL | **PARTIAL** | Provider capability wiring proof |
| 50 Jobs & Outputs | 3 sub-tabs (Details/Files/Outputs) datasource, live-tail, backoff, ANSI | `wx_jobs.py:346-570` Files ListCtrl via `list_job_files`, Outputs stdout/stderr via `read_output`, off-GUI-thread, stale generation, pause/resume, notebook isolation, EN/TR | PROVEN | `test_wx_jobs_files_outputs.py` (7 PROVEN: real sub-tab → adapter → fake backend → visible ListCtrl/TextCtrl, stale, pause) | 7/7 PASS | **VERIFIED_COMPLETE** | — |
| 51 Editor | multi-doc, movable/closable tabs, dirty *, duplicate suppression, standalone independence | `wx_editor_view.py:48-390` always Notebook, dirty *, duplicate reuse, close save/discard/cancel, reorder, lifecycle safe | PROVEN | `test_wx_editor_tabs.py` (11 PROVEN: real Notebook events) | 11/11 PASS | **VERIFIED_COMPLETE** | — |
| 52 Plugin Manager | discovery/install/lifecycle, Online/Cached/Offline, allowlist | `wx_plugins.py` + view | PARTIAL | `test_wx_plugins.py` | Manager discover/install lifecycle partial; card/detail/capability visual parity gap | **PARTIAL** | Card/detail/capability parity |
| 53 Framework-Neutral ANSYS Presentation | neutral contract isolates engine from UI | `services/ansys_tool_presentation.py` + `wx_ansys.py` adapter | PROVEN | `test_ansys_tool_presentation.py` | Contract 29-48 | **VERIFIED_COMPLETE** | — |
| 54 ANSYS Trusted Tool UI | file/folder lint, suffix filter, grouped severity, explanation/copy/open docs/line nav, quick lint + Send to plugin, folder 200 cap, broken containment, responsive | `wx_ansys_view.py` Frame Pick Files/Folder/Lint → model → engine → grouped ListCtrl + severity + detail (why/confidence/fix/src) + Copy diagnostic/suggestion + Open docs (allowlist `is_allowed_external_url`) + summary EN/TR i18n + lifecycle closed guard | PROVEN | `test_wx_ansys.py` (2) + `test_wx_ansys_view.py` (8 PROVEN: real PickFiles/PickFolder button → engine → ListCtrl, details, close-in-flight, i18n) | 10/10 PASS | **VERIFIED_COMPLETE** (behavioral) | Visual `ansys.png` current HEAD pending regen; DPI 150/200 manual |
| 55 Settings | global vs profile scope, persistence, runtime propagation, failure recovery, EN→TR→EN, no raw `[key]` | `wx_settings.py:11-54` GLOBAL/PROFILE + LEGACY_IGNORED; `wx_settings_view.py` panel with remote_cache, checksum, parallelism, timeout, Apply thread, closed guard, i18n | **STRUCTURAL** | `test_wx_settings.py` (3 model-only: round-trip, legacy ignored, macOS shortcuts) | Model tests only; **no real wx event → Apply → persistence → reopen → profile isolation → visible propagation proof** | **PARTIAL** | Real wx event tests required: open Settings → change global cache → Apply → close→reopen preserved; profile A vs B isolation; runtime propagation measurable; save failure + close-in-flight no destroyed callback; EN→TR→EN while open |
| 56 Logs/Diagnostics | refresh off-GUI-thread, redaction, bounded, Copy, Export ZIP via worker, lifecycle no leaks | `wx_logs.py:12-36` bounded + redaction; `wx_logs_view.py` TextCtrl + Refresh/Copy/CopyPath/Export Diagnostics (DirDialog → worker Thread → bundle) | **STRUCTURAL** | `test_wx_logs.py` (2 model-only: tail 5100 lines bounded, missing file) | Model tests only; **no real Refresh click → worker → visible TextCtrl, no Copy clipboard, no Export ZIP worker thread ≠ GUI thread proof, no close-in-flight leak** | **PARTIAL** | Real wx event tests required as above |
| 57 Updater/Tray/Shutdown | check, download bytes/%, progress bar, cancel, verified→install decision, install progress, close-in-flight, tray | `wx_lifecycle.py:18-75` UpdateProgress, cancel Event, tray_notify, notified_jobs, cleanup; `wx_shell.py` chrome Update/Plugins/SendLogs/Settings/Help | **STRUCTURAL** | `test_wx_lifecycle.py` (model) + `test_app_updater.py` (service) | Model/service only; **no real Check click → fake updater → visible versions/changelog, no download progress bar %, no cancel visible canceled, no install confirmation, no close-in-flight destroyed check** | **PARTIAL** | Real wx event tests required |
| 57A Visual Parity | canonical Qt/wx screenshot pairs, DPI, layout invariants | `audit/gui-screenshots/wx/{main,connection,jobs,directories,files,editor,terminal,logs,ansys}.png` + `HASHES.json`; shell 7 tabs, 0 launcher, 0 detached, min 960x640 | **PARTIAL** | `test_wx_layout_resize.py` (resize 400, duplicate 0, clipped 0) | 1100x720 capture duplicate 0 (main 1px wider), tab order correct, terminal wx-only intentional; missing: 1366x768, 960x640, 150%/200% DPI manual, layout invariants at 150/200 not measured | **PARTIAL** | Regenerate current HEAD screenshots, add 1366/1100/960 sizes + DPI manual where Windows permits, SHA256 |
| 58 Windows | packaged wx audit: startup, 7 tabs, Settings/Plugins/ANSYS/Updater/Help/Files/Transfers/Jobs/Editor/Logs/shutdown, mock backend, artifact SHA | Historical artifact `31efff023feeb684c61c6916398f27a2c1b8e73a75cbfbcd7c7af6c66badb47e` passed an earlier smoke; latest dirty-tree artifact `c83c1b05…` could not be foregrounded, so guarded input sent no keys; preceding artifact `21141a8b…` accepted 36/36 native input events with focus but yielded no output | **PARTIAL** | `python scripts/wx_packaged_smoke.py --artifact dist/hpc-client-gui/hpc-client-gui.exe --platform windows` | Current packaged result **FAIL**; latest run had no input attempt, earlier focused attempt had no terminal echo, and downstream checks fail | **PARTIAL** | Reproduce keyboard input and visible terminal output in an interactive packaged Windows session |
| 59 Linux | wx install, import, packaged build, launch, main frame, workspace, files/jobs/editor/logs/shutdown, X11/Wayland docs | A Qt-only onedir artifact was built and passed offscreen packaged startup; full release lock cannot install pinned wxPython without a C compiler in the cached container | **PARTIAL** for Qt package evidence; wx remains **NOT EVIDENCED** | Ubuntu 24.04 container, Python 3.12.3, PyInstaller spec + `scripts/linux_release_smoke.py --gui` | `--help`, version, doctor, and 20-second offscreen GUI passed; wxPython was excluded from the lock install, so this is not Linux wx/WebKit evidence | **BLOCKED** | Add/use a documented Linux build environment with wxPython toolchain before claiming the wx platform wave |
| 60 macOS | wx install, package .app launch, main frame, workspace, shutdown; signing/notarization per arch | No .app, no codesign | **BLOCKED** | — | No macOS runner evidence; unsigned policy documented | **BLOCKED** | Produce .app per arch (arm64/x86_64) or BLOCKED; signing credentials require `codesign`/`notarization`/`stapling`/`Gatekeeper` otherwise `UNSIGNED WITH DOCUMENTED POLICY` |
| 61 Accessibility | Tab/Shift+Tab order, visible focus, Alt/menu, F1 Help, Shift+F10, Ctrl/Cmd shortcuts, keyboard primary workflows, dialog cancel, no traps, non-color cues, accessible name/role | `wx_shell.py` 7 tabs + chrome buttons `GetLabel()!= ""`, menu bar, `audit/A11Y_AUDIT.md` | **PARTIAL** | `test_wx_a11y.py` (2: focus order SetSelection 0..6, labels, menu) | Keyboard operability PROVEN for tab order + labels; **no real Tab/Shift+Tab traversal, visible focus, Alt/menu, F1, Shift+F10, shortcuts full coverage, no screen-reader certification** | **PARTIAL** | Real keyboard-only evidence; screen-reader = PARTIAL |
| 62 Parity Matrix | all IDs current app vs status | `services/parity_matrix.py:18-46` all COVERED; `V2_PARITY_STATUS.md` COVERED vs PARTIAL mismatch | **PARTIAL** | `audit/PARITY_EVIDENCE_INTEGRITY_62A.md` | Matrix says COVERED but 57A visual PARTIAL, 55-57 structural → should be PARTIAL | **PARTIAL** | Align matrix with real evidence classes |
| 62A Evidence Integrity | PROVEN/PARTIAL/STRUCTURAL/MISSING classification via real wx event chain | `audit/PARITY_EVIDENCE_INTEGRITY_62A.md` 29 IDs PROVEN/STRUCTURAL | **PARTIAL** | that doc | Based on prior ledger where 55-57 were claimed COVERED; now downgraded → needs regen | **PARTIAL** | Regenerate for current HEAD with downgraded waves |
| 63 Manual Acceptance | SHA-bound checklist 16 items, Qt vs wx, resize, EN/TR, detached, ANSYS, Settings/Plugins/Updater/Tray/Terminal/Files/Jobs/Editor/Logs/Shutdown | `docs/v2/V2_MANUAL_GUI_TEST_PLAN_954783e.md` + `audit/WINDOWS_AUDIT_954783e.md` | **STALE** | Manual plan for 954783e ≠ e3408fd | Plan exists for old SHA; current HEAD not manually signed off | **PARTIAL** | Regenerate plan for e3408fd + execute + signed evidence |
| 64 Migration/Rollback | V1 config fixture → real V2 startup/load → real migration → pre-migration backup → V2 visible → rollback → original restored byte-for-byte; profiles/settings/keymap/hosts/plugins/connection/updater; secrets not exposed; atomic/idempotent | `config/storage.py:569-591` `load_profiles()` now creates a unique `config.json.bak*` copy before legacy profile/id/parallelism migration, then uses atomic `save_config`; `test_wx_migration.py` verifies the production backup and failed-save original readability | **PARTIAL** | `test_wx_migration.py` (4) | Narrow profile/config migration and rollback copy are proven; full V1→V2 user-data migration (settings/history/favorites/keymap/plugins/connection/updater) and visible rollback are not | **PARTIAL** | Extend the same real backup/rollback fixture across every user-data store before claiming Wave 64 complete |
| 65 Packaged E2E | per-platform packaged artifact E2E same SHA | Windows dirty-tree artifact `c83c1b05…`: wx runtime/frame, UI surfaces and PTY resize pass, but foreground activation was denied and no keys were sent. Earlier focused artifact `21141a8b…` accepted native input events without output. Linux Qt-only smoke passed; no macOS artifact | **PARTIAL** | Current `scripts/wx_packaged_smoke.py` report + Linux Qt `scripts/linux_release_smoke.py --gui` | Windows full smoke **FAIL**; Linux result is Qt-only and excludes wxPython; macOS **NOT EVIDENCED** | **PARTIAL** | Prove focused Windows terminal input/output; test full Linux wx environment; produce macOS package |
| 65A Integrated Stress & Resource Leak Gate | 500 tab switches, 300 dispatches, 300 embedded refreshes, 200 EN/TR, 200 resizes, 100 session/reconnect, 200 jobs races, 200 navigation races, 200 file mutations, 100 transfer items, 100 editor cycles, 100 logs refreshes, 100 detached, 50 shell open/close, 50 close-in-flight; measured invariants 0; GUI thread vs worker | `test_wx_65a_stress.py:1-520` **repaired 2026-09-05 e3408fd**: real wx events for all counts: 500 SetSelection, 300 sync checkbox ProcessEvent, 300 embedded (100 logs +100 jobs +100 compare ProcessEvent), 200 language menu ProcessEvent, 200 SetSize, 100 generation swap, 200 jobs refresh ProcessEvent, 200 local model navigate, 200 file ops, 100 TransferItem→TransferSessionController→fake backend→session cleanup, 100 editor build + SetValue + Destroy, 100 logs ProcessEvent, 100 build_ansys_frame, 50 shell create/close, 50 close-in-flight isolated frames; probes for destroyed/leaked/duplicate/stale; worker_ids vs GUI thread; 442s (7.3 min) PASS invariants 0 (leaked ≤1 after pump) | **VERIFIED_COMPLETE** | `test_wx_65a_stress.py` 1/1 PASS (442s) + `test_wx_file003_final_stress` 11/11 | Previously FAILED_VERIFICATION (wx.Yield no-ops) now real; invariants measured via Probe (destroyed 0 after fix) and window accounting | **VERIFIED_COMPLETE** (short soak; long soak separate Wave 69) |
| 65B Provenance/CI | machine-readable commit/branch/OS/Python/wx/version/commands/exit codes/totals/stress counts/invariants/screenshot hashes/artifact SHA/CI run IDs/current-SHA | `audit/PROVENANCE_65B.json` tested_commit 954783e (≠ e3408fd), Win11 Py3.12.4 wx4.3.1, 58 passed, stresses 500/300..., screenshots SHA, artifact SHA pending, ci windows local PASS, linux/macos BLOCKED, generated_utc 2026-09-06T19:00:00Z (future/dated) | **STALE** | that file | Points to historical SHA, artifact SHA pending, generated at fixed time, linux/macos CI BLOCKED | **PARTIAL** | Regenerate for current HEAD e3408fd with real commands/exit codes, runtime screenshot hashes, artifact SHA when available, CI IDs, generated at runtime |
| 66 Qt Removal Readiness | P0 COVERED + GUI-WORKSPACE-001 + GUI-VISUAL-001 + a11y + Windows/Linux/macOS packaged current SHA + manual current + 65A real + migration real + no dirty tree + default runtime wx | `scripts/qt_removal_gate.py` now correctly includes GUI-WORKSPACE-001/GUI-VISUAL-001 (fixed 2026-09-05), but still reports P0 blockers: GUI-VISUAL-001 PARTIAL, Qt imports 113, deps 6, packaging 30, packaged evidence MISSING all platforms, manual MISSING, dirty file `scripts/qt_removal_gate.py` until commit | **NO-GO** | `python scripts/qt_removal_gate.py` | P0 1, Qt imports 113, packaging 30, packaged/manual MISSING (expected, Qt remains), visual PARTIAL → NO-GO | **NO-GO** (truthful) | Keep Qt production until all gates PASS |
| 67 Remove Qt | controlled removal only after 66 GO | Not started | **BLOCKED** | — | 66 NO-GO | **BLOCKED** | Await 66 GO |
| 68 SBOM/License/Vuln | isolated venv SBOM CycloneDX from lock, direct/transitive + bundled natives (DLL/PYD/EXE/.so/.dylib/frameworks), THIRD_PARTY_NOTICES, vulnerability scan on release closure | `audit/SBOM_68.json` 450 components (up from 100) + bundled inventory per previous commit; `audit/VULN_68.json` 651KB; `audit/LICENSE_INVENTORY_68.md`; `THIRD_PARTY_NOTICES.md` | **PARTIAL** | SBOM file | SBOM now from isolated env (fixed) but bundled binary inventory for actual packaged artifacts (Windows DLL, Linux .so/AppImage, macOS .dylib) still pending Wave 70 packaging | **PARTIAL** | Inspect actual packaged artifact natives and reconcile |
| 69 Performance Soak | short CI mode + long release mode, measure RSS/CPU/threads/workers/wx windows/USER/GDI/throughput/latency/reconnect/stale over extended duration; repeat tab switch/nav/file/transfer/editor/jobs/terminal/EN_TR/detached/reconnect | `audit/PERFORMANCE_SOAK_69.md` short soak ~136s 65A + 185s file003 = 5 min, leaked 0, USER reclaimed; long soak (hours) BLOCKED | **PARTIAL** | 65A + file003 | Short soak PASS; long soak not run | **PARTIAL** | Add soak runner `scripts/soak_runner.py --duration --iterations` with configurable short/long, report start/peak/end/growth/slope/failures |
| 70 Release Prep | checklist: Windows/Linux/macOS packages + SHA256, smoke, manual sign-off, updater manifest + signature, notes/migration/rollback, known limits, SBOM/license/vuln/provenance/soak, signing classification SIGNED/UNSIGNED WITH DOCUMENTED POLICY/BLOCKED | `audit/RELEASE_PREP_70.md` Windows package done for old SHA, SBOM/license done, artifact SHA from HASHES.json, updater manifest pending `capture_build_inventory.py`, signing pending | **BLOCKED** | that file | Many items pending packaging + signature | **BLOCKED** | Complete packaging + signatures or documented UNSIGNED policy |
| 72 Terminal Rebaseline | Audit Qt vs wx, freeze behavioral contract, correct false parity (`quick_command_row` hidden/dead) | `docs/v2/TERMINAL_PARITY_CONTRACT_72.md` + `TERMINAL_PARITY_GAPS_72.json` (35 gaps #1-35), ledger downgrades Wave 45 & `GUI-TERM-001` | STRUCTURAL (docs) | contract gaps measured | 35 behaviors classified; hidden `quick_command_row` `setVisible(False)` documented, no visible UI added to wx | **VERIFIED_COMPLETE** | — |
| 73 Terminal WebView Renderer | xterm.js inside `wx.html2.WebView` with single JSON bridge, bounded queue, readiness, local-only page | `wx_terminal_webview.py` (988 lines) WxTerminalWebViewPanel + `wx_bridge.js` + `wx_index.html` vendored | **VERIFIED_COMPLETE** | `test_wx_terminal_webview.py` (30 tests, subprocess-isolated) | xterm.js WebView renderer with JSON bridge, bounded pending queue, readiness handshake, local-only vendored assets, navigation guard | **VERIFIED_COMPLETE** | — |
| 74 Input/Keyboard/Paste/Unicode/PTY | xterm onData → bridge → `send_shell_input`, Ctrl A-_, nav keys, multiline paste, Unicode, FitAddon PTY re-fit | `wx_terminal_webview.py` bridge/adapter handlers + `wx_bridge.js` terminal.onData | **PARTIAL** | `test_wx_terminal_input_chain_ctrl_a_to_z`, Unicode/paste/resize tests; current packaged smoke | Source bridge tests exercise structured messages and adapter callbacks; current package did not render simulated keyboard echo, so real user keyboard → xterm → PTY remains unproven | **PARTIAL** | Demonstrate real focused wx/WebView keyboard input and visible loopback PTY output |
| 75 Header/Find/Lifecycle | status/identity/dimensions from xterm, Find vs buffer, Clear isolation, font re-fit, embedded+detached same renderer, reconnect invariant, i18n, a11y | `wx_terminal_webview.py` _update_status/_update_identity/hpc_find/hpc_find_next/hpc_find_prev + `wx_bridge.js` _searchBuffer | **VERIFIED_COMPLETE** | `test_wx_terminal_header_status_updates`, `test_wx_terminal_find_next_and_prev`, `test_wx_terminal_destroy_before_ready_no_xfail`, `test_wx_terminal_100_reconnects_no_leak`, `test_wx_terminal_generation_guard_rejects_stale_output` | Live header, Find/Next/Prev with wraparound, destroy-before-ready safety, generation guard, 100 reconnects | **VERIFIED_COMPLETE** | — |
| 76 Behavioral Evidence Gate | real wx→WebView→adapter→fake PTY→xterm-visible chain, VT fixture, stress invariants | `test_wx_terminal_parity_evidence.py` (11 tests) + evidence JSON | **PARTIAL** | `test_vt_sgr_*`, `test_vt_carriage_return_*`, `test_unicode_round_trip`, `test_multiline_paste`, `test_resize_*`, `test_stress_*`, `test_close_while_output_in_flight`, `test_generate_parity_evidence` | VT fixtures/stress pass in source tests; alternate-screen and current packaged keyboard-to-output evidence remain incomplete | **PARTIAL** | Prove complete visible behavior chain |
| 77 Platform/Packaging | Windows WebView2, macOS WebKit, Linux GTK/WebKit, packaged asset offline, no CDN/log | Latest Windows dirty-tree artifact `c83c1b05…` returned xterm DOM focus readback and PTY resize, but could not be foregrounded; preceding artifact `21141a8b…` accepted input events but produced no terminal output. Linux Qt-only package passed offscreen startup; no macOS artifact | **PARTIAL** | Windows package smoke SHA `c83c1b05…` + Linux Qt package smoke | Dedicated clean-HEAD WebView2 packaged readiness **NOT EVIDENCED**; terminal input/readback gate **FAIL**; Linux wx/WebKit and macOS **NOT EVIDENCED** | **PARTIAL** | Reproduce clean-HEAD packaged WebView2 readiness and foregrounded keyboard/output; produce Linux wx and macOS artifacts |

**Historical summary counts at HEAD `da44f639`:** VERIFIED_COMPLETE 12 (44,46-48,50-51,54,65A,72-75), PARTIAL 11 (42-43,45,49,52,55-57,57A,61-62,62A,65,76) + `GUI-TERM-001` PARTIAL, BLOCKED 6 (59-60,67-70,77), NO-GO 1 (66). These counts predate the current verification supplement and are not current release metrics.

## 3) Blockers recorded at the historical Wave 77 snapshot

1. **72 terminal rebaseline done** — `TERMINAL_PARITY_CONTRACT_72.md` + gaps JSON committed; Wave 45 now PARTIAL, `GUI-TERM-001` PARTIAL.
2. **73-75 terminal waves are VERIFIED_COMPLETE; Wave 76 is PARTIAL** — WebView/xterm renderer, input/geometry and header/lifecycle are proven locally; the behavioral evidence gate still lacks alternate-screen rendered-state proof. `GUI-TERM-001` remains PARTIAL due to alternate screen (BLOCKED without real display) and packaged WebView2 (BLOCKED).
3. **55/56/57 real wx event proofs still missing** — model-only tests not sufficient (capture global/profile persistence, logs worker thread, updater progress).
4. **57A visual DPI 150/200 manual + 1366/960 sizes + ansys Qt comparison missing.**
5. **58 Windows packaged evidence stale** — need real artifact for current HEAD (isolated).
6. **59/60 Linux/macOS BLOCKED** — no runners/credentials (wx has wheel for macOS/Windows 3.14 but Linux requires source build with gtk).
7. **61 keyboard-only full coverage missing** — Tab/Shift+Tab, visible focus, Alt, F1, Shift+F10, shortcuts not fully proven.
8. **62A needs regen after downgrades** — 55-57,65A,72 (terminal) status changed.
9. **63 manual plan stale (954783e)** — regenerate for current HEAD.
10. **64 full migration still incomplete** — production config migration backup is now proven, but the complete user-data backup/rollback matrix is not.
11. **65B provenance stale sharealike.**
12. **68 bundled native inventory pending.**
13. **69 long soak not run.**
14. **45 terminal now correctly PARTIAL** — do not revert to VERIFIED_COMPLETE without xterm chain.

## 4) Historical Chronology (archived)

- **8a23fd7→7dae696** recovered workspace, wave 42-53 baseline
- **beb3ca1** Wave54 ANSYS surface + terminal toolbar
- **c694b5c / 1636d37** Wave45 terminal unified
- **457b3af / 8f53dbc / 8479e2d / 1d550fc / b384581** Waves 48-51 sequential VERIFIED
- **4dc2f90** Waves 55-57 sweep claimed VERIFIED (overclaim—now downgraded to PARTIAL)
- **954783e** Visual 9 screenshots duplicate 0 + ansys capture
- **207b2a5** Windows audit 954783e VERIFIED (now stale vs eb37cb7)
- **f0c3138** A11Y COVERED (now PARTIAL)
- **8c5c252 / 212164c** 45-54 closure docs
- **7fb3108** 65A 100 detached + 65B provenance (stale, 954783e, pending artifact)
- **131234f** 62A integrity + SBOM 100
- **90efe74** Soak short + release prep checklist
- **d2f4064** SBOM 450 components + bundled inventory
- **eb37cb7** Gate fixed (GUI-VISUAL-001 enforced), wx dependency closure (pyproject wx extra, lock wxPython==4.3.1, docs/WX_DEPENDENCY_CLOSURE.md), CI now covers `develop` + wx-smoke matrix
- **8232b8c** Ledger truthfulness: downgrade overclaims, FAILED_VERIFICATION for 65A
- **8414eee** Packaged smoke real (isolated from src, FAIL due to missing artifact truthful) + visual parity regen for current HEAD duplicate 0
- **e3408fd** 65A repaired: real wx events for all counts, 442s PASS
- **da44f639 → Wave 72** terminal rebaseline: 35-gap contract frozen, hidden `quick_command_row` documented as dead, Wave 45 downgraded VERIFIED_COMPLETE→PARTIAL, `GUI-TERM-001` COVERED→PARTIAL, `GUI-TERM-002` kept COVERED (independent)

Previous overclaims found and downgraded: 45 (terminal TextCtrl ≠ xterm), 55,56,57,58,61,62,62A,63,64,65B,68,69,70 statuses lowered to reflect `wx.Yield`/model-only/source-string evidence not sufficient; 65A now repaired to VERIFIED. Wave 66 remains **NO-GO** — Qt stays production runtime until Wave 66 legitimately returns GO (do not start Wave 67).

## 5) Integration Evidence

All implementation commits reachable from `develop` (da44f639). Delegate work not complete until merged. Before merging: `git diff --check`, `python -m ruff check`, `python -m compileall -q src`, focused tests. Wave 72: docs-only, no renderer changed; `git diff --check` clean.

## 6) Acceptance Order

Sequential: **72 (done)** → **73 (done)** → **74 (done)** → **75 (done)** → **76 (PARTIAL — alternate screen BLOCKED)** → **77 (BLOCKED — packaged gate)** → then unrelated: 55 (settings real wx) → 56 (logs real) → 57 (updater real) → 57A visual current → 61 a11y harden → 64 real migration → 65A already VERIFIED → packaged smoke real → 58 Windows real → 59/60 platform → CI current-SHA → provenance regen → SBOM/vuln/soak/release cleanup.

## 7) Historical Test Evidence (reverify before use)

Run relevant suites after integration (do not use wildcard as literal):

```powershell
$wxTests = Get-ChildItem -Path tests -Filter 'test_wx_*.py' | ForEach-Object { $_.FullName }
python -m pytest -q @wxTests --cache-clear
```

Record passed/failed/skipped/duration; classify skips, do not ignore parity-affecting skips.

Quality gates:

```powershell
python -m ruff check src scripts tests
python -m compileall -q src
git diff --check
python scripts/qt_removal_gate.py
python tests/parity..? # audit integrity
```

Packaging: verify `wxPython` installed from declared inputs, artifact builds, launch without `src` in sys.path.

## 8) Provenance Regeneration

After real tests exist, regenerate `audit/PROVENANCE_65B.json` with machine-readable: commit, branch, OS, Python, wxPython, wxWidgets, commands, exit codes, totals, stress counts, invariants, screenshot hashes, artifact path/SHA, CI IDs, platform results. Generate time at runtime, no future dates, no stale SHA.

## 9) Audit Directory Policy

Current authoritative files (this HEAD):

- `audit/WINDOWS_AUDIT_*.md` — historical per-SHA, not current until e3408fd regenerated
- `audit/PROVENANCE_65B.json` — stale (954783e), needs regen for e3408fd
- `audit/GUI_VISUAL_PARITY_REPORT.*` — regenerated for e3408fd/8414eee (delegate9b stale archived)
- `audit/PARITY_EVIDENCE_INTEGRITY_62A.md` — needs regen after downgrades (55-57,65A)
- `audit/SBOM_68.json` — 450 components current (isolated venv) but bundled natives pending Wave 70
- `audit/PERFORMANCE_SOAK_69.md` — short soak 442s 65A + file003, long soak pending
- `audit/RELEASE_PREP_70.md` — BLOCKED pending packaging

Stale files not deleted silently; moved to `audit/archive/<sha>/` or labelled historical in README. `audit/README.md` must identify CURRENT authoritative files.

## 10) Qt Remains Production

`src/hpc_gui/runtime.py:3` `DEFAULT_GUI_RUNTIME="qt"` unchanged. `PySide6`/`shiboken6` remain. No Wave 67 removal until Wave 66 GO. Wave 72 does not change runtime; wx optional.
