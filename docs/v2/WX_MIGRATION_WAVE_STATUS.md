# wx Migration Wave Status Ledger — Waves 00–70 (Current HEAD)

> **Current HEAD:** `eb37cb7` (2026-09-05)
> **Branch:** `develop`
> **Rule:** Qt remains production runtime (`DEFAULT_GUI_RUNTIME="qt"`). wx is optional.
> **Evidence standard:** `PROVEN` requires `real wx event → visible wx control → adapter → controller/service → fake/disposable backend → completion → visible UI result` with lifecycle/generation/stale protection. Model-only, source-string, import-only, or `wx.Yield` loops do NOT count as PROVEN.
> **Screenshots:** canonical set at `audit/gui-screenshots/{qt,wx}/` with `HASHES.json` SHA256. Windows package smoke must be real artifact, not `src` import.

## 1) Qt Reference

`src/hpc_gui/ui/main_window.py:138-157` — 6 embedded `QTabWidget` pages: Connection, Jobs & Outputs, Directories, Files, Script Editor, Logs. Terminal is wx-only primary-tab deviation (documented). Help, Settings, Plugins, ANSYS dialog are top-level.

## 2) Current Authoritative Wave Table (HEAD eb37cb7)

Behavioral / visual / platform / packaged / release are separate. `VERIFIED_COMPLETE` only if all acceptance criteria for that wave are met. `PARTIAL` = exists but incomplete. `FAILED_VERIFICATION` = claim does not survive evidence standard. `BLOCKED` = prerequisite/environment absent. `NO-GO` = gate blocks.

| Wave | Requirement | Current Implementation | Evidence Type | Real Test(s) | Observed Result | Status | Remaining Blocker |
|---|---|---|---|---|---|---|---|
| 42 wx Shell | wx.App/bootstrap, 7-tab notebook, chrome row, language menu, tray, lifecycle | `wx_shell.py:72-900` notebook 7 tabs, chrome row, tray adapter, lifecycle shutdown | PROVEN (shell) + STRUCTURAL (tray) | `test_wx_shell.py`, `test_wx_shell_p0.py`, `test_wx_shell_p0_stress.py` | 24/24 P0 + 50 close PASS; tray notify works, chrome parenting not leaking | **PARTIAL** | Canonical screenshots current HEAD not yet regenerated; DPI 150/200 not proven (resize only) |
| 43 Help/Command Palette | Help searchable, command palette, shortcut settings | `wx_help.py` present, command_registry wired | PARTIAL | `test_wx_help.py` | Help dialog keyboard accessible, palette wired but visual parity incomplete | **PARTIAL** | Visual parity + shortcut settings wiring proof |
| 44 Connection | Profile lifecycle, X11, keepalive, provider selection | `wx_connection.py` complete | PROVEN | `test_wx_connection.py` | Real wx event → adapter → fake backend → visible profile list | **VERIFIED_COMPLETE** | Visual parity DPI |
| 45 Terminal | PTY, Find/Clear/font, Ctrl-C vs copy, i18n, bounded 5000 | `wx_terminal.py:63-260` unified `build_terminal_panel` toolbar Find/Clear/A-/A+ + model resize/PTY; detached `show_terminal` wraps same panel | PROVEN | `test_wx_terminal.py` (2), `test_wx_embedded_terminal.py` (9 PROVEN: real button → model → visible) | All 11 PASS | **VERIFIED_COMPLETE** | — (visual captured) |
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
| 58 Windows | packaged wx audit: startup, 7 tabs, Settings/Plugins/ANSYS/Updater/Help/Files/Transfers/Jobs/Editor/Logs/shutdown, mock backend, artifact SHA | `audit/WINDOWS_AUDIT_954783e.md` Win11 26200 Py3.12.4 wx4.3.1 9 screenshots duplicate 0, test_windows_audit 1/1, packaged_smoke 1/1 (import), file003 11/11 | **STALE** | `test_wx_windows_audit.py` (1), `test_wx_packaged_smoke.py` (1 import-only) | **Stale SHA 954783e ≠ current eb37cb7**; packaged smoke is source import, not real artifact; artifact SHA pending | **PARTIAL** | Rebuild current HEAD wx artifact (wheel/pyinstaller), real launch → wx runtime → main frame → workspace → shutdown smoke with isolation proof, current SHA audit |
| 59 Linux | wx install, import, packaged build, launch, main frame, workspace, files/jobs/editor/logs/shutdown, X11/Wayland docs | No artifact, no Xvfb run | **BLOCKED** | — | No Linux runner evidence; wxPython has no manylinux wheel (must build from source with gtk-webkit); CI wx-smoke continue-on-error | **BLOCKED** | Build with gtk deps or document BLOCKED policy; X11 vs Wayland differences not documented |
| 60 macOS | wx install, package .app launch, main frame, workspace, shutdown; signing/notarization per arch | No .app, no codesign | **BLOCKED** | — | No macOS runner evidence; unsigned policy documented | **BLOCKED** | Produce .app per arch (arm64/x86_64) or BLOCKED; signing credentials require `codesign`/`notarization`/`stapling`/`Gatekeeper` otherwise `UNSIGNED WITH DOCUMENTED POLICY` |
| 61 Accessibility | Tab/Shift+Tab order, visible focus, Alt/menu, F1 Help, Shift+F10, Ctrl/Cmd shortcuts, keyboard primary workflows, dialog cancel, no traps, non-color cues, accessible name/role | `wx_shell.py` 7 tabs + chrome buttons `GetLabel()!= ""`, menu bar, `audit/A11Y_AUDIT.md` | **PARTIAL** | `test_wx_a11y.py` (2: focus order SetSelection 0..6, labels, menu) | Keyboard operability PROVEN for tab order + labels; **no real Tab/Shift+Tab traversal, visible focus, Alt/menu, F1, Shift+F10, shortcuts full coverage, no screen-reader certification** | **PARTIAL** | Real keyboard-only evidence; screen-reader = PARTIAL |
| 62 Parity Matrix | all IDs current app vs status | `services/parity_matrix.py:18-46` all COVERED; `V2_PARITY_STATUS.md` COVERED vs PARTIAL mismatch | **PARTIAL** | `audit/PARITY_EVIDENCE_INTEGRITY_62A.md` | Matrix says COVERED but 57A visual PARTIAL, 55-57 structural → should be PARTIAL | **PARTIAL** | Align matrix with real evidence classes |
| 62A Evidence Integrity | PROVEN/PARTIAL/STRUCTURAL/MISSING classification via real wx event chain | `audit/PARITY_EVIDENCE_INTEGRITY_62A.md` 29 IDs PROVEN/STRUCTURAL | **PARTIAL** | that doc | Based on prior ledger where 55-57 were claimed COVERED; now downgraded → needs regen | **PARTIAL** | Regenerate for current HEAD with downgraded waves |
| 63 Manual Acceptance | SHA-bound checklist 16 items, Qt vs wx, resize, EN/TR, detached, ANSYS, Settings/Plugins/Updater/Tray/Terminal/Files/Jobs/Editor/Logs/Shutdown | `docs/v2/V2_MANUAL_GUI_TEST_PLAN_954783e.md` + `audit/WINDOWS_AUDIT_954783e.md` | **STALE** | Manual plan for 954783e ≠ eb37cb7 | Plan exists for old SHA; current HEAD not manually signed off | **PARTIAL** | Regenerate plan for eb37cb7 + execute + signed evidence |
| 64 Migration/Rollback | V1 config fixture → real V2 startup/load → real migration → pre-migration backup → V2 visible → rollback → original restored byte-for-byte; profiles/settings/keymap/hosts/plugins/connection/updater; secrets not exposed; atomic/idempotent | `config/storage.py:56-68` load_config backup only on corrupted JSON, not on version migration; `test_wx_migration.py` creates own `.bak` manually, not app's real migration backup | **STRUCTURAL** | `test_wx_migration.py` (2) | Test creates backup file manually instead of app's real backup; no real V1→V2 migration path proven | **PARTIAL** | Implement real migration framework with pre-migration backup before destructive write, then test via actual V2 load path |
| 65 Packaged E2E | per-platform packaged artifact E2E same SHA | `test_wx_packaged_smoke.py` import-only | **PARTIAL** | that file | Import `src` modules, not artifact; artifact SHA pending; Linux/macOS BLOCKED | **PARTIAL** | Real packaged smoke (artifact → launch → wx runtime → main frame → shutdown) per platform |
| 65A Integrated Stress & Resource Leak Gate | 500 tab switches, 300 dispatches, 300 embedded refreshes, 200 EN/TR, 200 resizes, 100 session/reconnect, 200 jobs races, 200 navigation races, 200 file mutations, 100 transfer items, 100 editor cycles, 100 logs refreshes, 100 detached, 50 shell open/close, 50 close-in-flight; measured invariants 0; GUI thread vs worker | `test_wx_65a_stress.py:1-140` simplified: 500 tab switches real, 200 EN/TR real via `set_language`, 200 resizes real, 100 detached real via `build_ansys_frame`, but **300 dispatches, 300 refreshes, 200 jobs races, 200 navigation races, 200 mutations, 100 transfers, 100 editor, 100 logs, 50 open/close, 50 close-in-flight are `wx.Yield()` no-ops reporting as counts; invariants hardcoded 0 without measurement; no threading assert** | **FAILED_VERIFICATION** | `test_wx_65a_stress.py` | Claims 300 dispatches but executes `wx.Yield()` only; similarly 300 refreshes, 200 jobs races etc are no-ops; invariants never measured | **FAILED_VERIFICATION** | Replace with real campaign where each count is actual operation via real wx event → adapter → fake backend → visible result; instrument `wrong_workspace_targets`, `stale_ui_overwrites`, `destroyed_control_callbacks`, `leaked_wx_windows`, `leaked_workers`, `leaked_transfer_sessions`, `duplicate_primary_panels`, `clipped_required_controls` etc; assert GUI work off main thread where required |
| 65B Provenance/CI | machine-readable commit/branch/OS/Python/wx/version/commands/exit codes/totals/stress counts/invariants/screenshot hashes/artifact SHA/CI run IDs/current-SHA | `audit/PROVENANCE_65B.json` tested_commit 954783e (≠ eb37cb7), Win11 Py3.12.4 wx4.3.1, 58 passed, stresses 500/300..., screenshots SHA, artifact SHA pending, ci windows local PASS, linux/macos BLOCKED, generated_utc 2026-09-06T19:00:00Z (future/dated) | **STALE** | that file | Points to historical SHA, artifact SHA pending, generated at fixed time, linux/macos CI BLOCKED | **PARTIAL** | Regenerate for current HEAD eb37cb7 with real commands/exit codes, runtime screenshot hashes, artifact SHA when available, CI IDs, generated at runtime |
| 66 Qt Removal Readiness | P0 COVERED + GUI-WORKSPACE-001 + GUI-VISUAL-001 + a11y + Windows/Linux/macOS packaged current SHA + manual current + 65A real + migration real + no dirty tree + default runtime wx | `scripts/qt_removal_gate.py` now correctly includes GUI-WORKSPACE-001/GUI-VISUAL-001 (fixed 2026-09-05), but still reports P0 blockers: GUI-VISUAL-001 PARTIAL, Qt imports 113, deps 6, packaging 30, packaged evidence MISSING all platforms, manual MISSING, dirty file `scripts/qt_removal_gate.py` until commit | **NO-GO** | `python scripts/qt_removal_gate.py` | P0 1, Qt imports 113, packaging 30, packaged/manual MISSING (expected, Qt remains), visual PARTIAL → NO-GO | **NO-GO** (truthful) | Keep Qt production until all gates PASS |
| 67 Remove Qt | controlled removal only after 66 GO | Not started | **BLOCKED** | — | 66 NO-GO | **BLOCKED** | Await 66 GO |
| 68 SBOM/License/Vuln | isolated venv SBOM CycloneDX from lock, direct/transitive + bundled natives (DLL/PYD/EXE/.so/.dylib/frameworks), THIRD_PARTY_NOTICES, vulnerability scan on release closure | `audit/SBOM_68.json` 450 components (up from 100) + bundled inventory per previous commit; `audit/VULN_68.json` 651KB; `audit/LICENSE_INVENTORY_68.md`; `THIRD_PARTY_NOTICES.md` | **PARTIAL** | SBOM file | SBOM now from isolated env (fixed) but bundled binary inventory for actual packaged artifacts (Windows DLL, Linux .so/AppImage, macOS .dylib) still pending Wave 70 packaging | **PARTIAL** | Inspect actual packaged artifact natives and reconcile |
| 69 Performance Soak | short CI mode + long release mode, measure RSS/CPU/threads/workers/wx windows/USER/GDI/throughput/latency/reconnect/stale over extended duration; repeat tab switch/nav/file/transfer/editor/jobs/terminal/EN_TR/detached/reconnect | `audit/PERFORMANCE_SOAK_69.md` short soak ~136s 65A + 185s file003 = 5 min, leaked 0, USER reclaimed; long soak (hours) BLOCKED | **PARTIAL** | 65A + file003 | Short soak PASS; long soak not run | **PARTIAL** | Add soak runner `scripts/soak_runner.py --duration --iterations` with configurable short/long, report start/peak/end/growth/slope/failures |
| 70 Release Prep | checklist: Windows/Linux/macOS packages + SHA256, smoke, manual sign-off, updater manifest + signature, notes/migration/rollback, known limits, SBOM/license/vuln/provenance/soak, signing classification SIGNED/UNSIGNED WITH DOCUMENTED POLICY/BLOCKED | `audit/RELEASE_PREP_70.md` Windows package done for old SHA, SBOM/license done, artifact SHA from HASHES.json, updater manifest pending `capture_build_inventory.py`, signing pending | **BLOCKED** | that file | Many items pending packaging + signature | **BLOCKED** | Complete packaging + signatures or documented UNSIGNED policy |

**Summary counts (current HEAD):** VERIFIED_COMPLETE 6 (44-48,50-51,54), PARTIAL 12, FAILED_VERIFICATION 1 (65A), BLOCKED 8, NO-GO 1 (66), SUPERSEDED 0. **No wave >55 is VERIFIED_COMPLETE** until settings/logs/updater real proofs, visual DPI, packaged evidence, 65A real, provenance current.

## 3) Current Blockers (eb37cb7)

1. **65A real campaign missing** — 300 dispatches, 300 refreshes, 200 jobs races etc are `wx.Yield` no-ops.
2. **55/56/57 real wx event proofs missing** — model-only tests not sufficient.
3. **57A visual DPI 150/200 manual + 1366/960 sizes + ansys Qt comparison missing.**
4. **58 Windows packaged evidence stale** — need real artifact for eb37cb7.
5. **59/60 Linux/macOS BLOCKED** — no runners/credentials.
6. **61 keyboard-only full coverage missing.**
7. **62A needs regen after downgrades.**
8. **63 manual plan stale (954783e).**
9. **64 real migration backup not proven.**
10. **65B provenance stale sharealike.**
11. **68 bundled native inventory pending.**
12. **69 long soak not run.**

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

Previous overclaims found and downgraded: 55,56,57,58,61,62,62A,63,64,65A,65B,68,69,70 statuses lowered to reflect `wx.Yield`/model-only/source-string evidence not sufficient. Wave 66 remains **NO-GO** — Qt stays production runtime until Wave 66 legitimately returns GO (do not start Wave 67).

## 5) Integration Evidence

All implementation commits reachable from `develop` (eb37cb7). Delegate work not complete until merged. Before merging: `git diff --check`, `python -m ruff check`, `python -m compileall -q src`, focused tests.

## 6) Acceptance Order

Sequential still: 55 (settings real wx) → 56 (logs real) → 57 (updater real) → 57A visual current → 61 a11y harden → 64 real migration → 65A real integrated stress → wx closure (done) → packaged smoke real → 58 Windows real → 59/60 platform → CI current-SHA → gate harden (done) → provenance regen → SBOM/vuln/soak/release cleanup.

## 7) Test Evidence Current

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

- `audit/WINDOWS_AUDIT_*.md` — historical per-SHA, not current until eb37cb7 regenerated
- `audit/PROVENANCE_65B.json` — stale (954783e), needs regen
- `audit/GUI_VISUAL_PARITY_REPORT.*` — stale delegate9b branch refs, needs regen
- `audit/PARITY_EVIDENCE_INTEGRITY_62A.md` — needs regen after downgrades
- `audit/SBOM_68.json` — 450 components current but bundled natives pending
- `audit/PERFORMANCE_SOAK_69.md` — short soak only, long pending
- `audit/RELEASE_PREP_70.md` — BLOCKED pending packaging

Stale files not deleted silently; moved to `audit/archive/<sha>/` or labelled historical in README. `audit/README.md` must identify CURRENT authoritative files.

## 10) Qt Remains Production

`src/hpc_gui/runtime.py:3` `DEFAULT_GUI_RUNTIME="qt"` unchanged. `PySide6`/`shiboken6` remain. No Wave 67 removal until Wave 66 GO.
