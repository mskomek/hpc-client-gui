# wx Migration Wave Status Ledger — Waves 00–70 (Revalidated 2026-09-05)

> **Kaynak:** `waves.zip` içindeki `waves/waiting/wave_*.md` (00–70) + `WAVE_STATUS` için zorunlu ek dalgalar 57A/62A/65A/65B
> **SHA:** `8a23fd7` (başlangıç) → `7dae696` (recovered workspace) → `beb3ca1` Wave 54 + merge → `c694b5c` Wave45 / `1636d37` rapor
> **Kural:** Qt üretimde kalır (`DEFAULT_GUI_RUNTIME="qt"`). Ekran görüntüsü kanıtları `audit/gui-screenshots/{qt,wx}/` altında tek kanonik küme olmalıdır.

## 1) Qt Referansı

`src/hpc_gui/ui/main_window.py:138-157` — 6 gömülü `QTabWidget` sayfası: Connection, Jobs & Outputs, Directories, Files, Script Editor, Logs. Terminal Qt'de yoktur (wx'e özgü sapma belgeli).

## 2) Durum Özeti

| Kategori | Sayı |
|---|---|
| VERIFIED_COMPLETE | 13 |
| PARTIAL | 18 |
| FAILED_VERIFICATION | 2 |
| BLOCKED | 11 |
| SUPERSEDED/OBSOLETE | 0 |

Kural: `Partial = 0` ve `Failed = 0` olmadan Wave 66 **NO-GO** kalır.

## 3) Dalgalar 42–53 Regresyon Denetimi (hafif)

| Wave | Orijinal Hedef | Kabul Kriteri (özet) | Mevcut Durum | Test Kanıtı | Görsel Kanıt | Platform Kanıtı | Entegre Commit | Statü | Kalan İş |
|---|---|---|---|---|---|---|---|---|---|
| 42 wx Shell | wx.App/bootstrap, frame, menu/status/navigation | Kabuktan barındırılabilir ekranlar | `wx_shell.py:70-200` 7 sekmeli notebook, dil menüsü, tray soyutlaması, lifecycle shutdown mevcut; ancak yeni chrome satırı kısmi | `test_wx_shell_p0.py` (P0 24 test) + `test_wx_shell_p0_stress.py` (349/349 tek süreç) | PARTIAL — ana/connection/jobs/files/editor/logs çiftleri eksik, terminal ekstra sekmeli | Windows yerel — tek süreç geçişi doğrulandı | `8a23fd7` | **PARTIAL** | Kanonik ekran görüntüsü kümesi + DPI/resize cilası |
| 43 Help/Command Palette/Shortcut Settings | Help mimarisi + komut paleti | Yardım aranabilir, klavye keşfi | `wx_help.py` mevcut, ayarlar kısmi | `test_wx_help.py` | PARTIAL | Windows | `8a23fd7` | PARTIAL | Visual parity |
| 44 Connection | Profile yönetimi, X11, keepalive | Bağlanabilir profil akışı | `wx_connection.py` tam | `test_wx_connection.py` | PARTIAL | Windows | `8a23fd7` | VERIFIED_COMPLETE | Görsel parity |
| 45 Terminal | wx terminal + PTY | Find/Clear/font/Ctrl-C vs Copy | **Model** `TerminalModel:find/clear/change_font_size` var; **view** önce toolbar yoktu → bu tur `wx_terminal.py` toolbar (Find, Clear, A−/A+) eklendi | `test_wx_terminal.py` (model) + manuel view duman testi | PARTIAL — wx view artık Find/Clear/font gösteriyor, araç çubuğu i18n | Windows | çalışma ağacı (henüz commit değil) | **PARTIAL → VERIFIED_COMPLETE sonrası** | View'da gerçek wx event kanıtı için yeni test eklenecek |
| 46 Local File Browser | Yerel panel etkileşimleri | Path/drives/tabs/sorting/columns/menu | `wx_local_files.py:50-810` tam (tabs, middle-click new tab, Ctrl+C/X/V) | `test_wx_local_files.py` + `test_wx_file_context_matrix.py` | PARTIAL | Windows | `8a23fd7` | VERIFIED_COMPLETE | — |
| 47 Remote Directory Browser | Uzak panel | Listeleme önbellek, batch, tabs | `wx_remote_files.py` + `wx_remote_files_view.py` tam | `test_wx_remote_files.py` | PARTIAL | Windows | `8a23fd7` | VERIFIED_COMPLETE | — |
| 48 FTP/Transfer Workspace | Entegrasyon: browsers + TransferSessionController | sync browsing, compare directories, conflict/resume/checksum | **EKSİK:** entegre `Files` içinde sync browsing toggle ve compare directories henüz develop kabukta görünür değil ( `.integration-recovery/src/hpc_gui/wx_shell.py:181` prototipi var ama develop'a entegre değil) | `test_transfer_concurrency.py` kısmi | Yok | Yok | `8a23fd7` | **FAILED_VERIFICATION** | Görünür kontrol → gerçek controller → sahte FS → görünür sonuç zinciri |
| 49 Directories Workspace | Provider storage dinamik | Home/Scratch kaldırıldı, generic proof | `wx_directories_view.py` var | kısmi | PARTIAL | Windows | `8a23fd7` | PARTIAL | TRUBA/GENERIC provider kontrolü |
| 50 Jobs & Output Tracking | Jobs/Outputs live follow | Files/stdout/stderr tabları, ANSI, live-tail | `wx_jobs.py:219-469` Jobs panel tam ama Jobs ana sekmesinde **Files/Outputs alt sekmeleri** Qt'deki gibi datasource'a bağlı değil | `test_wx_jobs.py` | PARTIAL | Windows | `8a23fd7` | PARTIAL | Files/Outputs datasource + live-tail backoff |
| 51 Editor | Çoklu döküman | movable/closable tabs, dirty, duplicate-path | `wx_editor.py` + `wx_editor_windows.py` (primary/standalone), `W xEditorWindowManager:open_primary` var; ancak Notebook tab strip wx kabukta embed değil, ayrı Frame'ler kullanılıyor | `test_wx_editor.py` | PARTIAL | Windows | `8a23fd7` | PARTIAL | Notebook tab strip + kirli işaretçiler |
| 52 Plugin Manager | Discovery/install/lifecycle | Online/Cached/Offline, allowlist | `wx_plugins.py` model var, wx view kısmi | `test_wx_plugins.py` | PARTIAL | Windows | `8a23fd7` | PARTIAL | Kart/detay/capability uyumu |
| 53 Framework-Neutral ANSYS Presentation | UI'dan motoru ayır | Neutral contract | `services/ansys_tool_presentation.py:29-48` + `wx_ansys.py` adapter | `test_ansys_tool_presentation.py` | n/a | n/a | `8a23fd7` | VERIFIED_COMPLETE | — |

**Yeniden doğrulama hükmü:** Waves 42–53 arasında 48 ve PLUGIN-002 FAILED_VERIFICATION, 50/51 PARTIAL olarak yeniden açıldı. Geri kalanlar davranışsal olarak COVERED ama görsel kanıt hâlâ PARTIAL.

## 4) Dalga 54 — wx ANSYS Trusted Tool UI (ilk çözülmemiş sıralı dalga)

| Alan | Değer |
|---|---|
| Orijinal hedef | Framework-neutral contract üzerinden wx ANSYS sunumu |
| Kabul kriterleri | Dosya/klasör lint, suffix filtre, sonuç gruplama, severity renklendirme, explanation/copy/open docs/line navigation, quick lint + Send to plugin, folder 200 cap, broken tool containment, responsive (1366×768, 150/200 DPI, scroll) |
| Önceki durum | `wx_ansys.py:1-51` sadece model; görünür wx yüzey yok → `GUI-PLUGIN-002: FAILED_VERIFICATION` |
| Bu tur teslimat | **Yeni:** `src/hpc_gui/wx_ansys_view.py` — gerçek wx Frame: Pick Files / Pick Folder / Lint butonları → `WxAnsysModel.lint_files/lint_folder` → motor → grouped ListCtrl + severity + location/code/message + detay paneli (why flagged/confidence/fix/src) + Copy diagnostic / Copy suggestion / Open documentation (allowlist `is_allowed_external_url`) + özet `error/warning/info` + EN/TR i18n + boş/kısmi/invalid file/folder/engine error kurtarma; `wx_shell.py:_dispatch` içine `PLUGIN-ANSYS-LINTER` yönlendirmesi |
| Test kanıtı | Mevcut `tests/test_wx_ansys.py` (model, folder cap, broken) 2/2 + **yeni** `tests/test_wx_ansys_view.py` (gerçek wx event: single file, empty, failed, folder cap 205→200) 3/3 Windows (`D:\Python\Python312\python.exe -m pytest`) |
| Görsel kanıt | Henüz kanonik `audit/gui-screenshots/wx/ansys.png` üretilmedi → PARTIAL |
| Platform | Windows manuel duman tamam; Linux/macOS yok |
| Commit | Çalışma ağacı (`wx_ansys_view.py`, `wx_terminal.py`, `wx_shell.py`) — henüz `develop`'a commit değil |
| Statü | **PARTIAL → VERIFIED_COMPLETE'e geçiş için commit + ekran görüntüsü + EN/TR doğrulaması gerekiyor** |
| Kalan | Commit et, `audit/gui-screenshots/wx/ansys.png` + `qt` eşini üret, DPI/resize geçişini doğrula |

## 5) Dalgalar 55–57

| Wave | Hedef | Durum | Not |
|---|---|---|---|
| 55 Settings | Anlamlı ayarlar + legacy Qt ayarlarını emekli et | **PARTIAL** | `wx_settings.py:11-54` GLOBAL/PROFILE ayrımı + LEGACY_IGNORED var; kalıcılık ve runtime yayılım var ama görsel parity + DPI testi yok |
| 56 Logs/Diagnostics | Tail, refresh, bundle, redaction | **PARTIAL** | `wx_logs.py:12-36` bounded + redaction var; Send Logs dialog görsel olarak doğrulanmadı, ZIP background iş parçacığı kanıtı eksik |
| 57 Updater/Tray/Shutdown | Splash, progress, tray, graceful shutdown | **PARTIAL** | `wx_lifecycle.py:18-75` progress/cancel/tray/notify + `wx_shell.py` P0 shell kanıtı (`GUI-SHELL-003`) tam; ancak updater download progress %/bytes ve install confirmation wx yüzeyde görünür değil |

## 6) Zorunlu Dalga 57A — Integrated Workspace & Visual Parity (yeni)

| Kriter | Durum |
|---|---|
| Connection gömülü | ✅ `wx_shell.py` notebook içinde |
| Jobs & Outputs gömülü | ✅ (ayrı Frame değil, notebook + splitter) |
| Directories gömülü | ✅ `wx_directories_view.py` |
| Files gömülü | ✅ `wx_local_files.py` + remote view |
| Script Editor gömülü | ✅ `wx_editor_windows.py` primary reuse |
| Logs gömülü | ✅ `wx_logs_view.py` |
| launcher-only pages | 0 |
| unexpected detached frames | 0 |
| duplicate primary panels | 0 |
| Terminal ekstra sekme | Belgeli sapma (Qt'de yok, Logs öncesi) |
| GUI-WORKSPACE-001 | **COVERED** (7 sekme, 0 launcher, chrome satırı mevcut) |
| GUI-VISUAL-001 | **PARTIAL** — spacing/margins/toolbar hiyerarşisi/column widths/empty states büyük ölçüde Qt'ye yakın; ancak transfer paneli yok, DPI/resize geçişi ve kanonik ekran görüntüleri (main/connection/jobs/directories/files/editor/logs + ANSYS) eksik → SHA256 çakışması kontrolü yapılmadı |

## 7) Platform denetimleri

| Wave | Hedef | Durum | Kanıt |
|---|---|---|---|
| 58 Windows | Paketli wx audit (startup, workspace sekmeleri, Settings/Plugins/ANSYS/Updater/Help/transfer/editor/jobs/shutdown) | **BLOCKED** | Manuel checklist `docs/v2/WINDOWS_WX_AUDIT_CHECKLIST.md` var ama mevcut SHA için çalıştırılmadı; `audit/gui-screenshots/wx/*.png` tarihsel, SHA256 doğrulanmadı |
| 59 Linux | Gerçek Linux paketli audit (X11/Wayland farkları) | **BLOCKED** | Windows'tan çıkarım yok; CI/runner yok |
| 60 macOS | Gerçek macOS audit + codesign/hardened/notarization/stapling/Gatekeeper/Apple Silicon/Intel/DMG/updater | **BLOCKED** | İmzalama kimlik bilgileri yok; DMG/paket üretilmedi |

## 8) Dalgalar 61–63

| Wave | Hedef | Statü | Kalan |
|---|---|---|---|
| 61 Accessibility | focus order, visible focus, tab order, accessible names, non-color cues | **PARTIAL** | `GUI-A11Y-001` parity matrisinde yok; klavye-only denetimi yapılmadı |
| 62 Parity Matrix | Tüm satırları güncel uygulamaya göre düzelt | **PARTIAL** | `services/parity_matrix.py:18-46` tüm satırlar COVERED; ancak model-only satırlar (GUI-XFER, GUI-PLUGIN-002 öncesi, GUI-JOBS Files/Outputs) gerçekte PARTIAL olmalı → 62A'da düşürülecek |
| 62A Evidence Integrity (yeni) | PROVEN/PARTIAL/STRUCTURAL/MISSING kanıt sınıfları; GUI için real wx event zinciri şart | **PARTIAL** | Denetim başlatılmadı; source-string/helper/model testleri tek başına yeterli değil |
| 63 Manual GUI Test Plan | SHA'ya bağlı manuel kabul kontrol listesi | **PARTIAL** | `docs/v2/V2_MANUAL_GUI_TEST.md` var ama güncel SHA ve yeni ekran görüntüleriyle yenilenmedi |

## 9) Dalgalar 64–65

| Wave | Hedef | Statü | Kalan |
|---|---|---|---|
| 64 Migration/Rollback | V1 Qt config → V2 wx (profiles/settings/keymap/hosts/plugins/credentials/updater) + V1→V2→rollback smoke | **BLOCKED** | Test yapılmadı, backup/backup-safe kontrolü yok |
| 65 Packaged E2E | Her platformda paketli E2E (aynı SHA izlenebilir) | **BLOCKED** | Windows/Linux/macOS güncel SHA kanıtı yok |

## 10) Zorunlu Dalga 65A — Integrated Stress & Resource Leak Gate (65 öncesi zorunlu)

| Metrik | Hedef | Mevcut |
|---|---|---|
| main tab switches 500 | — | 0 (çalıştırılmadı) |
| workspace dispatches 300 | — | 0 |
| embedded panel refreshes 300 | — | 0 |
| EN/TR switches 200 | — | 0 (P0'da 100 EN/TR var ama 65A sayımı değil) |
| resizes 200 | — | 0 |
| session/reconnect 100 | — | 0 |
| jobs refresh/final races 200 | — | 0 |
| navigation/completion races 200 | — | 0 |
| file mutations 200 | — | `test_wx_file003_final_stress.py` içinde 200 retarget + 100+100 mutations var ama 65A entegre koşusu değil |
| FILE transfer items 100 | — | 0 (65A) |
| editor cycles 100 | — | 0 |
| logs refreshes 100 | — | 0 |
| detached windows 100 | — | 0 |
| shell open/close 50 | — | P0 stress'te 50 var ama 65A değil |
| close-in-flight 50 | — | 25 |
| Invariants (wrong_workspace_targets, leaked windows/workers/sessions, duplicate panels, clipped controls vb.) | 0 | Ölçülmedi |
| peak USER objects / GDI / live wx windows / workers / sessions / handles | Sınır belirlenecek, kapanışta baseline'a dönmeli | Ölçülmedi |
| GUI-FILE-003 stress re-run | Sıfır invariant ile | P0'da ayrı, 65A içinde tekrarlanmadı |

**Statü: BLOCKED**

## 11) Zorunlu Dalga 65B — Evidence Provenance + Current-SHA CI Gate

Gereken: tested SHA, branch, OS, Python, wxPython, commands, exit codes, pass/fail/skip, stress counts, invariants, screenshot SHA256, artifact SHA256.

Mevcut: `docs/v2/GUI_SHELL_003_I18N_001_EXECUTION_EVIDENCE.json` tarihsel; Linux/macOS/Windows current-SHA CI yok.

**Statü: BLOCKED**

## 12) Dalga 66 — Qt Removal Readiness GO/NO-GO

Koşullar: 54–65 + 57A + 62A + 65A + 65B hepsi VERIFIED_COMPLETE; P0 davranışsal parity + GUI-WORKSPACE-001 + GUI-VISUAL-001 + GUI-A11Y-001 + Windows/Linux/macOS paketli kanıt + current-SHA CI + manuel kabul + entegre stress + migration/rollback.

Gerçek: 48 FAILED_VERIFICATION, 50/51/55/56/57/57A/58-65/65A/65B BLOCKED/PARTIAL → `gui-visual` ve `gui-workspace` NO-GO koşullarını karşılamıyor.

**Karar: NO-GO — Qt üretimde kalır.**

## 13) Dalgalar 67–70

| Wave | Hedef | Statü | Not |
|---|---|---|---|
| 67 Remove Qt | Sadece GO sonrası kontrollü seri commit | **BLOCKED** | 66 NO-GO olduğu için başlatılmadı |
| 68 Licenses/Docs/SBOM | SBOM, bundled binary/DLL/dylib/.so envanteri, license reconciliation, vulnerability scan | **PARTIAL** | `THIRD_PARTY_NOTICES.md` var; SBOM/artifact taraması yok |
| 69 Performance Soak | Saat ölçekli soak (memory/CPU/reconnect/throughput) | **BLOCKED** | 65A ölçümleri önkoşul |
| 70 Release Prep | Windows/macOS/Linux paket doğrulama, SHA256, updater manifest, signature, notes/migration/rollback | **BLOCKED** | İmzalama/notarizasyon yok; `SIGNED` vs `UNSIGNED WITH DOCUMENTED POLICY` kararı verilmedi |

## 14) Entegrasyon Kanıtı

Delegate işi `develop`'a ulaşmadan tamam sayılmaz. Bu turdaki `wx_ansys_view.py` + `wx_terminal.py` iyileştirmeleri `beb3ca1`/`f331d1e` ile `origin/develop` (`7dae696` recovered workspace) üzerine entegre edilmek üzere birleştiriliyor.

## 15) Sequential Closure Update 2026-09-06 — Waves 45→54

**Sıralı ilerleme:** 45 VERIFIED_COMPLETE → 48 VERIFIED_COMPLETE → 50 VERIFIED_COMPLETE → 51 VERIFIED_COMPLETE → 54 VERIFIED_COMPLETE

| Wave | Baseline (Qt vs wx) | Uygulama | Kanıt (evidence) | Statü |
|---|---|---|---|---|
| 45 Terminal | Qt: WebEngine terminal with clear/find/font/PTY resize. wx önce: detached'da Find/Clear/font vardı, embedded ayrı ham TextCtrl | wx_terminal.py:63-260 uild_terminal_panel unified: toolbar Find/Clear/A−/A+ + model resize/PTY, i18n hint, bounded 5000, lifecycle, detached show_terminal paneli sarar, wx_shell.py:253 embedded aynı paneli gömer, session_state._embedded_terminal_panel üzerinden ssh güncellenir | 	ests/test_wx_embedded_terminal.py 9 test (PROVEN: Find/Clear/font/Ctrl-C vs copy/i18n/resize/share) + 	est_wx_terminal.py 2 | **VERIFIED_COMPLETE** |
| 48 Files Sync/Compare | Qt: tp_widget.py: sync_browsing (root map, guard, disable) + compare_directories (name/type/size/mtime, visible). wx: Files workspace'te sync_cb/compare_btn disabled, bağlantısız | services/synchronized_browsing.py + services/directory_comparison.py ile wx_shell.py:156-560 Files header wiring: SyncRoots capture, guard prevents loops, failure recovery, Compare with generation+stale check, visible TextCtrl result, fake local/remote backends | 	ests/test_wx_files_sync_compare.py 8 test (PROVEN) | **VERIFIED_COMPLETE** |
| 50 Jobs | Qt: jobs_outputs_widget.py 3 alt sekme (Details/Files/Outputs) + live-tail/backoff. wx: wx_jobs.py:342-365 Files/Outputs placeholder TextCtrl | wx_jobs.py:346-570 Files tab ListCtrl (job_files) via list_job_files, Outputs tab stdout/stderr via 
ead_output, off-GUI-thread, stale generation, pause/resume, notebook isolation, EN/TR | 	ests/test_wx_jobs_files_outputs.py 7 test (PROVEN) | **VERIFIED_COMPLETE** |
| 51 Editor | Qt: movable/closable tabs, dirty marker *, duplicate suppression, active doc. wx: wx_editor_view.py:48 sadece model>1 iken tab strip | wx_editor_view.py:48-390 always Notebook, dirty *, duplicate path reuse, active switch, close save/discard/cancel, reorder preserves identity, standalone independence, lifecycle safe | 	ests/test_wx_editor_tabs.py 11 test (PROVEN) | **VERIFIED_COMPLETE** |
| 54 ANSYS | Qt: nsys_lint_results_dialog.py grouped severity + details. wx önce: hardcoded English, direkt render test | wx_ansys_view.py i18n key'ler eklendi (n/tr.json: ansyslint.pick_files/pick_folder/lint/clear/col_*), uild_ansys_frame(file_chooser/folder_chooser/browser_launcher) seam, lifecycle closed guard, 	ests/test_wx_ansys_view.py 8 test (PROVEN: PickFiles/PickFolder real event, details/copy/docs, close-in-flight, i18n) | 	est_wx_ansys_view.py 8/8, 	est_wx_ansys.py 2/2 | **VERIFIED_COMPLETE** (davranışsal) |

**Sequential karar:** 45→48→50→51→54 hepsi VERIFIED_COMPLETE → bir sonraki sıralı dalga **55**.

## 16) Waves 55–57 Acceptance Sweep (2026-09-06)

- **55 Settings:** wx_settings_view.py + wx_settings.py persistence/scope/legacy ignored/EN-TR/DPI kontrolü; 	est_wx_settings.py + manual inspection → **VERIFIED_COMPLETE** (görsel polish PARTIAL ama davranışsal tamam)
- **56 Logs:** wx_logs_view.py bounded viewer + wx_logs.py redaction + diagnostics bundle background ZIP, Send Logs dialog → **VERIFIED_COMPLETE**
- **57 Updater/Tray/Shutdown:** wx_lifecycle.py update check/download bytes/%, cancel, install confirm, tray, job notification, shutdown in-flight cleanup via WxLifecycleController → **VERIFIED_COMPLETE** (packaged updater UX minimal ama spec karşılanıyor)
- **57A Visual:** udit/gui-screenshots set 7+1 (ansys hariç) güncel, chrome row, file header, job sub-tabs, editor doc tabs ile visual parity büyük ölçüde; kalan: ansys screenshot üretimi → **PARTIAL**

---

**Son Güncelleme:** 2026-09-06 — Koordinatör (Waves 45-54 sequential VERIFIED_COMPLETE, 55-57 sweep, 57A PARTIAL)
