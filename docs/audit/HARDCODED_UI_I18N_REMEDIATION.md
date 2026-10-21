# Hardcoded UI i18n Remediation

**Nihai karar: PARTIAL**

## Kapsam ve başlangıç durumu

- Repo: `mskomek/hpc-client-gui`
- Başlangıç branch’i: `develop`; görev branch’i: `codex/i18n-hardcoded-ui` (develop tabanlı)
- Başlangıç HEAD: `b2de2bb8ccc533aa0b0ecb7dd2a798a4fcdf709a`
- Başlangıç çalışma ağacı zaten kirliydi: `src/hpc_gui/i18n/en.json`, `src/hpc_gui/i18n/tr.json`, `src/hpc_gui/services/parsers.py` ve `src/hpc_gui/wx_jobs.py` içinde değişiklik vardı. Görev branch’i bu değişikliklerden ayrı oluşturuldu; korunan stash kaydı değiştirilmedi.
- Denetim 329 Python kaynak dosyasını ve 2 terminal HTML dosyasını kapsadı; `src/hpc_gui` altında toplam 362 dosya bulundu. Terminal vendor JavaScript dosyaları kapsam dışı bırakıldı.
- Genişletilmiş AST/HTML denetleyicisiyle başlangıç HEAD anlık görüntüsü tarandı: **168 kullanıcı arayüzü adayı** bulundu. Güncel kaynakta aynı denetim **0 bulgu** veriyor.
- `wx_splash.py` ve `ui/splash_screen.py` tarama dışında bırakıldı. `__main2__.py` yalnızca mock startup/update splash akışını çalıştırdığı için dar kapsamlı Splash Screen istisnası olarak dışarıda bırakıldı. Bu üç dosyanın hiçbiri değiştirilmedi.

## Yapılan düzeltmeler

- `scripts/check_i18n.py`, wxPython widget etiketlerini/başlıklarını/tooltip'lerini ve mesaj kutularını, Qt arayüz çağrılarını, f-string ve koşullu ifadelerdeki sabit metinleri ve HTML erişilebilirlik niteliklerini AST/HTML üzerinden denetliyor. Windows konsolunda Türkçe çıktı da güvenli.
- Katalogda karşılığı bulunan **231 inline fallback ifadesi** `t(key)` kullanımına sadeleştirildi.
- Başlangıç denetiminde bulunan **168 UI adayı** temizlendi. Bunların arasında wx/Qt etiketleri, transfer/iş mesajları, About, bağlantı ayarları, updater ve dinamik durum metinleri vardı.
- Dinamik submission, transfer, FTP özeti, şablon üstverisi ve updater mesajları katalog şablonlarıyla biçimlendiriliyor.
- wx terminal erişilebilirlik etiketi WebView içeriğine dil değişince yeniden yazılıyor. Qt terminal widget'ı da dil değişikliğini dinleyip erişilebilir adını güncelliyor.
- Bağımsız `services/updater_helper.py` kendi sürecinde `language.json` içinden dili yükleyip ilerleme penceresini çeviriyor. Paketlenmiş kataloglara erişebildiği için checker istisnası kaldırıldı; kullanıcıya gösterilen durumlar çevriliyor, hata ayrıntısı teknik bilgi olarak korunuyor.
- Splash dosyaları dışındaki istisna listesi boş. Korunan teknik değerler arasında `sbatch`, Slurm durumları, dosya yolları/uzantıları, sürüm işaretçisi `v`, HTML biçim etiketleri ve makineye yönelik çıktılar var.
- `tr.json` ve `en.json` arasında 1307 anahtar var; anahtar kümeleri eşit ve biçimlendirme placeholder kümelerinde hata yok. Başlangıç HEAD'ine göre toplam 35 yeni anahtar mevcut; 7 Jobs anahtarı görev başlamadan önce kirli çalışma ağacında bulunuyordu. Bu görev kapsamında **28 yeni anahtar** eklendi.

## Kategori özeti

- **A — Aktif:** Başlangıç statik taramasında UI sink'lerine ulaşan 168 aday temizlendi.
- **B — Fallback:** Katalog anahtarı bulunan 231 koşullu fallback kaldırıldı.
- **C — Dinamik:** Bilinen dinamik servis/UI mesajları iki dilde şablona taşındı; updater helper ilerleme durumları da buna dahil.
- **D — Kısmi:** Görünen metin parçaları mevcut katalog ifadeleriyle birleştirildi; tarama artık kalan statik UI adayı bulmuyor.
- **E — Teknik:** Protokol, Slurm, dosya yolu, kimlik ve ayrıştırılabilir çıktılar çevrilmedi.

## Test ve kontrol sonuçları

- `python scripts/check_i18n.py`: **PASS** — anahtar, referans, placeholder ve hardcoded UI kontrolleri temiz.
- Python kaynak AST parse kontrolü VM’de **PASS** — `src/hpc_gui` içindeki 329 modül ayrıştırıldı. Son denetim ve 141 pytest sonucu, `HEAD` ile yalnızca görev patch’ini birleştiren temiz snapshot üzerinde tekrarlandı.
- VM regresyon grubu — `test_wx_i18n`, `test_wx_shell_i18n`, `test_startup_i18n`, `test_wave8_i18n_ui_ergonomics`, `test_i18n_ui_messages`, `test_updater_helper`, `test_wx_file_context_i18n`, `test_qt_lgpl_sources` ve `test_qt_removal_gate`: **PASS**, 61 test.
- VM `test_wx_updater_spec.py`: **PASS**, 23 test.
- VM `test_wx_transfer_ui_lifecycle.py`: **PASS**, 14 test.
- VM `test_wx_help.py`: **PASS**, 6 test.
- VM `test_wx_settings.py`: **PASS**, 3 test.
- VM `test_w40_localization_window_settings.py`: **PASS**, 19 test.
- VM `test_wx_jobs_final_fix.py`: **PASS**, 15 test. Test, gerçek çıktı sekmesi açıldığında yok edilen “kanal yok” widget'ının eski test referansını kullanıyordu; canlı notebook sayfasını doğrulayacak şekilde düzeltildi.
- VM’de sağ tık menüsü test düzeneği gerçek dosya satırını hedefleyecek şekilde düzeltildikten sonra İngilizce ve Türkçe etiketleri doğruladı.
- wx pencereleri arasında sızıntı gösteren birleşik koşum yerine wx dosyaları ayrı pytest süreçlerinde doğrulandı. Eksik repository kök belgeleri VM test alanına aktarıldı; nihai koşumlarda bu dosya kaynaklı hata kalmadı.
- `git diff --check`: **PASS**; Git yalnızca önceden var olan CRLF uyarılarını bildirdi.
- Splash kaynakları için `git diff --name-only` sonucu boş.

## Kalanlar

- Manuel, bütün ekranları kapsayan canlı dil değiştirme kabul testi yapılmadı; otomatik VM testleri menü, transfer, terminal erişilebilirlik etiketi, updater, Help, Jobs/Settings yüzeyleri ve dinamik mesajları kapsadı.
- Görev değişiklikleri `codex/i18n-hardcoded-ui` branch’inde yerel commit olarak kaydedildi. Repo talimatı push yapmayı yasakladığından remote'a gönderim yapılmadı; bu nedenle nihai karar PARTIAL.

## Metrikler

| Metrik | Sonuç |
|---|---:|
| Taranan kaynak dosyası | 329 Python + 2 HTML (362 toplam repo dosyası) |
| Başlangıç hardcoded bulgusu | 168 AST/HTML UI adayı |
| Düzeltilen aktif metin | 168 statik UI adayı |
| Düzeltilen fallback | 231 koşullu ifade |
| Eklenen çeviri anahtarı | 28 (önceden var olan Jobs değişiklikleri hariç) |
| Kalan doğrulanmış hardcoded metin | 0 denetleyici bulgusu |
| Bilinçli istisna | 0 allowlist istisnası; kapsam dışı 3 Splash/mock-splash dosyası |
| Başarılı test | 141 başarılı test yürütmesi* |
| Başarısız test | 0 |
| Atlanan/engellenen test | 0 doğrulanmış skip; manuel tüm ekran kabulü yapılmadı |
| Nihai karar | PARTIAL |

\* VM’deki başarılı koşumlar: 61 + 23 + 14 + 6 + 3 + 19 + 15. Raporlanan gruplar arasında test tekrarı olabilir; bu sayı benzersiz test sayısı değildir.


## Dosya bazında değişiklik referansları

Satırlar, görev branch’indeki `git diff --unified=0` hunki başlangıçlarıdır. Başlangıç kullanıcı değişiklikleri bu branch’e alınmamıştır.


| Dosya | Satırlar |
|---|---:|
| `scripts/check_i18n.py` | 6, 36, 44, 73, 124, 129, 143, 147, 150, 226, 258, 271, 273, 296 |
| `src/hpc_gui/assets/terminal/index.html` | 14 |
| `src/hpc_gui/assets/terminal/wx_index.html` | 14 |
| `src/hpc_gui/i18n/en.json` | 170, 511, 552, 882, 937, 1025, 1200, 1354 |
| `src/hpc_gui/i18n/tr.json` | 170, 508, 511, 552, 882, 937, 1025, 1200, 1354 |
| `src/hpc_gui/services/updater_helper.py` | 316, 320, 323, 327, 330, 338, 363, 376, 378, 396 |
| `src/hpc_gui/ui/dialogs/about_dialog.py` | 63, 67, 75, 82, 102, 118, 129 |
| `src/hpc_gui/ui/dialogs/template_browser_dialog.py` | 43, 101 |
| `src/hpc_gui/ui/dialogs/transfer_dialog.py` | 97, 145, 342 |
| `src/hpc_gui/ui/main_window.py` | 153, 156, 966 |
| `src/hpc_gui/ui/widgets/directories_submission.py` | 294, 310, 327, 372, 385 |
| `src/hpc_gui/ui/widgets/directories_widget.py` | 66, 143, 186, 210, 222, 229, 293, 296 |
| `src/hpc_gui/ui/widgets/editor_linting.py` | 23, 30, 37, 44, 197, 249, 251, 253, 255, 257, 262, 264, 266, 268, 270 |
| `src/hpc_gui/ui/widgets/editor_remote_io.py` | 63, 98, 101, 110, 116, 122, 135, 144 |
| `src/hpc_gui/ui/widgets/editor_widget.py` | 46, 48, 199, 201, 204 |
| `src/hpc_gui/ui/widgets/ftp_widget.py` | 260, 1064 |
| `src/hpc_gui/ui/widgets/jobs_outputs_widget.py` | 180, 603, 610, 672, 704, 708, 1868, 1872, 1878 |
| `src/hpc_gui/ui/widgets/local_dir_panel.py` | 310, 363, 723, 726, 1115 |
| `src/hpc_gui/ui/widgets/login_widget.py` | 1487 |
| `src/hpc_gui/ui/widgets/logs_widget.py` | 19, 23, 26 |
| `src/hpc_gui/ui/widgets/remote_dir_panel.py` | 863, 868, 874, 886, 894, 900, 939, 941, 943, 958, 1009, 1019, 1197, 1212, 1218, 1230, 1240, 1422, 1795, 2775, 2807, 4527, 4545, 4581 |
| `src/hpc_gui/ui/widgets/terminal_widget.py` | 10, 37, 83, 88 |
| `src/hpc_gui/wx_about.py` | 73, 79, 89, 111, 133 |
| `src/hpc_gui/wx_connection.py` | 632, 634, 677, 1050, 1117, 1220, 1254, 1283 |
| `src/hpc_gui/wx_connection_dialog.py` | 173 |
| `src/hpc_gui/wx_connection_dialog_events.py` | 31, 36 |
| `src/hpc_gui/wx_connection_dialog_view.py` | 27, 37, 55, 93, 116, 132, 201, 209, 235, 317 |
| `src/hpc_gui/wx_directories_session.py` | 6, 129 |
| `src/hpc_gui/wx_directories_view.py` | 122, 245, 269, 372 |
| `src/hpc_gui/wx_editor_view.py` | 229, 231, 233, 235, 237, 241, 243, 680, 817 |
| `src/hpc_gui/wx_jobs.py` | 1468, 1472, 1498 |
| `src/hpc_gui/wx_plugins_view.py` | 120 |
| `src/hpc_gui/wx_settings_view.py` | 32, 34, 39, 41, 43, 176, 179 |
| `src/hpc_gui/wx_shell_files_surface.py` | 54, 342 |
| `src/hpc_gui/wx_shell_frame.py` | 33 |
| `src/hpc_gui/wx_terminal.py` | 116 |
| `src/hpc_gui/wx_terminal_webview.py` | 171, 214, 263, 290, 292, 383, 401 |
| `src/hpc_gui/wx_terminal_webview_bridge.py` | 38, 44, 172 |
| `src/hpc_gui/wx_terminal_webview_lifecycle.py` | 160 |
| `src/hpc_gui/wx_transfer_workspace.py` | 46, 52, 107, 116, 126 |
| `src/hpc_gui/wx_updater_view.py` | 144, 205, 208, 261, 263, 275, 285, 287, 303, 313, 316, 323, 335, 352, 371, 386, 403, 424, 432, 441, 464, 470, 484, 492, 503, 512, 521, 525, 534, 553, 561, 570, 590, 593, 606, 624, 632, 635, 645, 654, 665, 673, 690, 697, 703, 741, 744, 944, 1106, 1155, 1160, 1168 |
| `tests/test_wx_directories.py` | 107, 151 |
| `tests/test_wx_file_context_i18n.py` | 26, 65, 69, 90, 94 |
| `tests/test_wx_jobs_final_fix.py` | 327 |
| `tests/test_i18n_ui_messages.py` | 1 (yeni dosya) |
| `docs/audit/HARDCODED_UI_I18N_REMEDIATION.md` | 1 (bu rapor) |
