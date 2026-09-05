# V2 Manual GUI Test Plan — Candidate SHA f0c3138 (954783e wx screenshots)

**Tarih:** 2026-09-06
**Branch:** develop
**SHA:** f0c3138 (Wave 61 A11Y) / 954783e (screenshots)
**OS:** Windows 11 Pro 10.0.26200, Python 3.12.4, wx 4.3.1
**Qt baseline:** aynı SHA (Qt üretim), wx candidate: aynı SHA
**Dil:** en ve tr (runtime switch)
**Ekran:** 1100x720 capture, 960x640 MinSize, 100% DPI (150/200% ayrı kontrol)

## Kapsam (Wave 63 gereksinimi)

Her madde için `PASS/FAIL/N/A` ve gerekirse redakte ekran görüntüsü/log referansı ekleyin. Aynı adımları Qt baseline ve wx candidate için tekrarlayın, farkları `V2_PARITY_STATUS.md`'de `INTENTIONALLY_CHANGED` ile belgeleyin.

| # | Alan | Adımlar | Beklenen |
|---|---|---|---|
| 1 | **Ana sekmeler** | Connection→Jobs→Directories→Files→Editor→Terminal→Logs sırayla tıklayın, her biri için `t("tabs.*")` label kontrolü | 7 sekme Qt sırasıyla eşleşir, Terminal wx-only ek (Logs öncesi) belgeli |
| 2 | **Primary actions** | Her sekmede ana butonlara tıklayın: Connect, Refresh (Jobs), New Folder (Directories), Upload/Download (Files), Save/Submit (Editor), Find/Clear/A−/A+ (Terminal), Refresh/Copy (Logs) | Butonlar enabled, tıklama visible sonuç üretir, disabled placeholder yok |
| 3 | **Resize** | Pencereyi 1366×768, 1100x720, 960x640 arasında sürükleyin, splitter'ları hareket ettirin | Overlap yok, primary actions erişilebilir, scroll/adaptive layout korunuyor, tablo/pane çökmez |
| 4 | **Runtime dil** | Help→Language en→tr→en 200 kez (otomatik) ve manuel 3 kez, her sekme açıkken | Tüm label'lar canlı yenilenir, eksik çeviri `[key]` yok, post-close callback yok |
| 5 | **Detached workflows** | Editor "Edit in New Window", Jobs "Open Output" (detached), ANSYS detached frame açın | Detached pencereler `GetParent()==frame` değil, ayrı TopLevel, lifecycle ile kapanır |
| 6 | **ANSYS** | Plugin Manager'dan ANSYS linter'ı açın, Pick Files (1 dosya), Pick Folder (5 dosya), Lint, detay seç, Copy diagnostic, Open docs (allowlist) | `test_wx_ansys_view` 8/8 ile aynı: grouped severity, details, clipboard, allowlist, folder cap 200, close-in-flight güvenli |
| 7 | **Settings** | Settings dialog: Jobs refresh interval, remote cache, transfer parallelism değiştir, Apply, restart | Değerler persist olur, runtime davranış güncellenir, global/profile ayrımı korunur |
| 8 | **Plugins** | Plugin Manager: Online/Cached/Offline, Search, Install/Update/Enable/Disable/Remove, Request Plugin link | Allowlist korunur, `test_wx_plugins` PASS |
| 9 | **Updater** | Help→Update: Check, progress bytes/%/cancel, changelog, install confirm | `WxLifecycleController` progress/cancel, tray notification |
| 10 | **Tray** | Job completion tray balonu (Windows) ve `tray.destroy()` | `test_wx_shell_p0` tray-unavailable tracking |
| 11 | **Terminal** | Embedded Terminal: Find (world), Clear, A−/A+, Ctrl+C interrupt vs Cmd/Ctrl+Shift+C copy, resize→PTY, EN/TR | `test_wx_embedded_terminal` 9/9 |
| 12 | **Files** | Files: local/remote nav, Sync Browsing on/off, Compare Directories, DnD, transfer queue | `test_wx_files_sync_compare` 8/8 |
| 13 | **Jobs** | Jobs: list/refresh, select job → Details/Files/Outputs alt sekmeleri, stdout/stderr follow/pause, stale koruması | `test_wx_jobs_files_outputs` 7/7 |
| 14 | **Editor** | Editor: open second/third doc, switch tab, dirty `*`, save clears, close save/discard/cancel, duplicate reuse, reorder, standalone | `test_wx_editor_tabs` 11/11 |
| 15 | **Logs** | Logs: refresh, Copy, Export Diagnostics (ZIP background), redaction (no password/token) | `test_wx_logs` PASS |
| 16 | **Shutdown** | Transfer/Job polling/ANSYS lint in-flight iken pencereyi kapatın | Late callback yok, leaked windows/workers 0, `test_wx_shell_p0_stress` 50 close PASS |

## Platform Varyantları

- Windows: Ctrl tabanlı dosya/terminal gesture'ları, Explorer DnD, clipboard file URL
- macOS: Cmd, XQuartz (beklenen yok, BLOCKED)
- Wayland/X11 ve 100/150/200% DPI: focus, dialog, DnD, tray, live-output tekrar (DPI 150/200 manuel, bu build'de 100% ile sınırlı)

## Güvenlik/Kanıt

- Disposable profile ve non-sensitive dosyalar kullanın, asla password/MFA/private key/token kaydetmeyin
- Her `FAIL` için ekran görüntüsü ve log referansı ekleyin, `V2_PARITY_STATUS.md`'de `INTENTIONALLY_CHANGED` ile belgeleyin
- Bu plan otomatik testleri tamamlar, otomatik iddia içermez

## İmza

- Tester: __________
- Tarih: __________
- Sonuç: PASS / FAIL (her madde için ayrı)
- Ekler: `audit/gui-screenshots/wx/HASHES.json` (9 dosya, duplicate 0), `audit/WINDOWS_AUDIT_954783e.md`

**Bu plan f0c3138/954783e için güncel kanoniktir; eski revizyonlar arşivlenmiştir.**
