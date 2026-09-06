# Wave 62A — Parity Evidence Integrity (PROVEN / PARTIAL / STRUCTURAL / MISSING)

**Tarih:** 2026-09-06
**SHA:** 7fb3108 (develop)
**Kural:** `PROVEN` için `real wx event → visible UI → adapter/controller/service → fake backend → completion → visible UI result` zinciri şart. Kaynak-string/helper/model-only testler tek başına yetersiz.

| ID | Mevcut Statü (parity_matrix) | Evidence Sınıfı | Gerekçe | Kanıt |
|---|---|---|---|---|
| GUI-WORKSPACE-001 | COVERED | **PROVEN** | 7 sekmeli notebook gömülü, 0 launcher, chrome row — `test_wx_shell` ve capture ile | `test_wx_shell.py`, `audit/WINDOWS_AUDIT_954783e.md`, `HASHES.json` |
| GUI-VISUAL-001 | PARTIAL | **PARTIAL** | wx set 9 duplicate 0, Qt 7 set eşleşiyor, ansys Qt eksik, DPI 150/200 manuel eksik | `test_wx_layout_resize`, screenshots |
| GUI-SHELL-001 | COVERED | **PROVEN** | App startup, splash, versioned shell — `test_cli_entrypoint` |  |
| GUI-SHELL-002 | COVERED | **PROVEN** | Update check/cancel/install — `test_app_updater` |  |
| GUI-SHELL-003 | COVERED | **PROVEN** | Tray, shutdown, generation, EVT_CLOSE — `test_wx_shell_p0` 24 test, `p0_stress` 50 close |  |
| GUI-I18N-001 | COVERED | **PROVEN** | EN/TR radio, flag bitmap, live retranslation — `test_wx_shell_i18n` 100 EN/TR |  |
| GUI-CONN-001 | COVERED | **PROVEN** | Profile select/connect — `test_wx_connection` (real wx event → adapter → fake backend → visible) |  |
| GUI-CONN-002 | COVERED | **PROVEN** | MFA/host-key — `test_optional_ssh_credentials` |  |
| GUI-CONN-003 | COVERED | **STRUCTURAL** | Provider/template metadata — `test_provider_capabilities` (declarative, no UI event) → PARTIAL olarak değerlendirilebilir ama data-only olduğu için STRUCTURAL kabul |  |
| GUI-CONN-004 | COVERED | **PROVEN** | Quota consent/backend — `test_quota_monitor` |  |
| GUI-CONN-005 | COVERED | **STRUCTURAL** | X11 (Linux/macOS) — `test_linux_x11`/`test_macos_x11` (platform-specific, Windows'ta STRUCTURAL) |  |
| GUI-TERM-001 | PARTIAL | **PARTIAL** | Terminal TextCtrl chain PROVEN (Find/Clear/font via TextCtrl), but **xterm.js chain MISSING** — no VT/ANSI, no \r overwrite, no SGR, no alt-screen, no FitAddon PTY, no Unicode/paste-remote per TERMINAL_PARITY_CONTRACT_72.md | 	est_wx_embedded_terminal 9 (TextCtrl) — not xterm |
| GUI-TERM-002 | COVERED | **PROVEN** | Run in terminal dispatch — `test_wx_term002` + embedded 9 |  |
| GUI-FILE-001 | COVERED | **PROVEN** | Local browsing — `test_wx_local_files` (real list, tabs, keyboard) |  |
| GUI-FILE-002 | COVERED | **PROVEN** | Remote/local edit, new window — `test_wx_editor*` 60 PASS |  |
| GUI-FILE-003 | COVERED | **PROVEN** | Context actions, transfer chain — `test_wx_file003_final_stress` 11 PASS invariants 0 |  |
| GUI-XFER-001 | COVERED | **PROVEN** | SyncRoots service local_to_remote etc. — `test_wx_files_sync_compare` 4 PROVEN (real checkbox → service → fake FS → visible) |  |
| GUI-XFER-002 | COVERED | **PROVEN** | Compare directory_comparison — `test_wx_files_sync_compare` 4 PROVEN (real button → service → visible TextCtrl, stale, close) |  |
| GUI-JOBS-001 | COVERED | **PROVEN** | Job list/refresh — `test_wx_jobs` |  |
| GUI-JOBS-002 | COVERED | **PROVEN** | Files/Outputs tabs — `test_wx_jobs_files_outputs` 7 PROVEN (real sub-tab selection → adapter → fake backend → visible ListCtrl/TextCtrl, stale, pause) |  |
| GUI-JOBS-003 | COVERED | **STRUCTURAL** | History/provenance — `test_job_history_dashboard` (advisory, no live UI) |  |
| GUI-JOBS-004 | COVERED | **STRUCTURAL** | Walltime suggestion — `test_walltime_suggestions` (service, not UI) |  |
| GUI-EDIT-001 | COVERED | **PROVEN** | Editor single-doc lint/dirty — `test_wx_editor_tabs` 11 PROVEN (real Notebook events) |  |
| GUI-EDIT-002 | COVERED | **PROVEN** | Multi-doc, save/submit/run — `test_wx_editor_tabs` 11 PROVEN |  |
| GUI-PLUGIN-001 | COVERED | **PROVEN** | Plugin manager discovery/install — `test_wx_plugins` |  |
| GUI-PLUGIN-002 | COVERED | **PROVEN** | ANSYS lint — `test_wx_ansys_view` 8 PROVEN (real Pick Files→engine→ListCtrl) |  |
| GUI-SET-001 | COVERED | **PROVEN** | Settings persistence/scope — `test_wx_settings` |  |
| GUI-LOG-001 | COVERED | **PROVEN** | Logs bounded/redaction — `test_wx_logs` |  |
| GUI-HELP-001 | COVERED | **PROVEN** | Help/search — `test_wx_help` |  |
| GUI-I18N-001 | COVERED | **PROVEN** | (duplicate, already) |  |
| GUI-A11Y-001 | COVERED | **PROVEN** | Tab order, labels, keyboard — `test_wx_a11y` 2/2, `audit/A11Y_AUDIT.md` |  |

**Karar (pre-72):** Tüm COVERED satırlar PROVEN/STRUCTURAL zannedildi. **Wave 72 rebaseline (2026-09-06, HEAD da44f639):** `GUI-TERM-001` **PARTIAL** — `TERMINAL_PARITY_CONTRACT_72.md` 35 gap (#1-35) proves TextCtrl != xterm; xterm renderer, FitAddon PTY, Unicode/paste-remote absent. `GUI-TERM-002` remains COVERED (independent editor/file -> terminal dispatch via `test_wx_term002`). **Wave 62A: PARTIAL pending Waves 73-76 xterm chain; regenerated 62A required after 76.**

**Not:** `GUI-VISUAL-001` PARTIAL (Qt ansys eksik, DPI 150/200 manuel) — görsel parity ayrı boyut, davranışsalı gizlemiyor. `GUI-CONN-003/005`, `GUI-JOBS-003/004` STRUCTURAL olarak kabul (data-only, UI event gerekmiyor).