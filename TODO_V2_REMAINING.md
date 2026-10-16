# HPC Client GUI V2 — Kalan İşler

## Güncel noninteractive devam doğrulaması — 2026-10-16

Bu bölüm, aşağıdaki 2026-10-15/önceki kampanya tablosunun güncel durumla çelişen broad-suite satırlarını supersede eder. Son kaynak commit `d31dcb71edbe6f1f822948c6ca4beba92d0bace4`; commit'in `b76aa72aa30c087923e52b77416c10a79c78848b` üzerine patch SHA-256'sı `ac14c68a13804adea3561a0c78479f0301b7b62e0fd4d230f0dbc46a4d99ed32` (`source-tree-manifest.json`). Broad koşu commit edilmemiş eşdeğer source/test diff üzerinde başladı; diff SHA-256 `8067f4af78059ee47ff2e8ff2c9536241a5d0e1553609b26ba27cc31a78363f0`. Commit öncesi yalnızca üç dosyanın trailing blank line'ları kaldırıldı; çalıştırılabilir ifade/test assertion'ları değişmedi. Candidate temiz `d31dcb71` commit'inden build edildi. Binding notu `.tmp/evidence-windows-v2-final/source-binding.md` içindedir.

| Alan | Durum | Kanıt | Kalan iş |
|---|---|---|---|
| Windows broad release suite | **FAILED; 1 açıklanmış transient/environment FAIL** | Güncel `scripts/release_test_suite.py`: ana suite 3,006 PASS / 1 FAIL / 29 SKIP / 62 DESELECTED / 29 subtest PASS, 801.44 sn. Tek hata `test_w37_wx_apply_event_persists_to_storage`: Windows `os.replace` `WinError 5 Access is denied`. Aynı test ayrı süreçte 1/1, tüm `tests/test_w37_settings_plugin_gui.py` 8/8 PASS. Bu failure bastırılmadı; isolated tekrar product/test defect'i yeniden üretmedi, Windows geçici file lock/environment flake olarak sınıflandırıldı. İzole runner dosyalarının hepsi PASS. W04 supplied evidence prerequisite eksik olduğundan runner bunu açıkça BLOCKED kaydetti. Kanıt `release-test-suite.log`. | Windows broad suite ana sürecinde sıfır FAIL elde etmek için host file-lock kaynağını belirle ve gerekirse Windows CI’da tekrarla. |
| Windows Candidate ve paket smoke | **COMPLETED (host packaged smoke)** | Commit `d31dcb71` kaynaklı onedir Candidate `.tmp/candidates/windows-v2-d31dcb71/hpc-client-gui/hpc-client-gui.exe`; SHA-256 `f6de90677ea16c9fe62cc321ac6a060b445b46387a1963ece99f5ccd4dab7138`; `wx_packaged_smoke.py` 20/20 PASS, `clean_shutdown` PASS. Build/smoke manifesti `.tmp/evidence-windows-v2-final/`. | Release imzalama/preflight; WER/reconnect guest acceptance. |
| Windows 11 guest | **PARTIAL** | Canonical `Invoke-Windows11Interactive.ps1`, `test\home` Explorer session, host/guest EXE SHA `f6de906...b7138` eşleşti. `version` exit 0, timeout yok, cleanup tamamlandı; JSON/stdout aynı evidence dizininde. GUI no-argument ve harness-env olmadan `--wx-smoke` çalıştırmaları timeout oldu, runner yalnızca sahip olduğu test process tree'lerini durdurdu ve temizledi. | Guest GUI startup/UIA, WER, reconnect ve guest clean-shutdown; host packaged smoke guest GUI acceptance yerine sayılmaz. |
| Ubuntu terminal ve güvenlik | **COMPLETED (hedefli tarihsel + güncel broad source regresyonları)** | `32c174c` Ubuntu 24.04.5 WebKitGTK bridge/fragment davranışı 42/42, W19 GDB lifecycle 20/20; CSP `script-src 'self'`, `connect-src 'none'` korunuyor. Güncel Windows source broad suite'te WebView bridge/input/lifecycle/output/readback süreç izolasyonlarında PASS. Hassas terminal metni kanıt loglarına yazılmadı. | Ubuntu güncel kaynakta yüksek hacimli/soak ve gerçek reconnect matrisi tekrar edilmedi; bu kanıt Windows source testlerinin yerine geçmez. |
| Linux `.deb` | **PARTIAL / BLOCKED_ENV** | Yeniden kullanılan eski Candidate `.tmp/hpc-client-gui_1.5.9_0e3e555b_amd64.deb` SHA-256 `dae29a464d8195cbeb88ae9dbee40cc9d1f64b92692f22b3beb62ab0b5073424`; eski `0e3e555` kaynak kimliğine bağlıdır. Güncel source ondan sonra değiştiği için güncel `.deb` olarak sunulmuyor. Ubuntu-Test'te `dpkg-deb` metadata/extract kontrolü yapıldı; gerçek dpkg install/upgrade/rollback için `sudo -n` yok ve GUI/Xvfb doğrulaması mümkün olmadı. | Güncel kaynakla yeni `.deb` Candidate; isolated install/upgrade/rollback/uninstall ve packaged GUI smoke. |
| Ubuntu AppImage / Flatpak | **BLOCKED_ENV** | Ubuntu-Test'te `appimagetool`, `flatpak` ve `flatpak-builder` mevcut değil; sistem geneli paket kurulumu yapılmadı. | CI veya izole build image içinde artifact üretimi/smoke/hash. |
| Mimari ve lint | **COMPLETED (changed scope)** | Canonical Agent Core architecture validator PASS: 43 değişen kaynak, 0 over-limit, 0 dependency error; 10 dosya 400–500 LOC warning bandında. Değişen Python dosyalarında Ruff PASS. Editor ve directories modülleri sorumluluklara göre bölündü. | Tüm proje legacy >500 LOC taraması ayrı teknik borç; bu devamda ilgili eski modüller yeniden yazılmadı. |
| İki denetim katmanı | **PARTIAL** | Audit A kaynak/davranış/mimari: source split, SFTP display-vs-edit strict decoding, hedefli 135/135 ve architecture/Ruff PASS; geniş koşuda tek açıklanmış Windows transient IO failure. Audit B kanıt/hash: host/guest artifact SHA eşleşti, 20/20 packaged smoke kaydı doğrulandı, broad log ve W04 blocker açıkça saklandı. Ayrıntı `.tmp/evidence-windows-v2-final/audit-*.md`. | Temiz broad ana süreci ve Ubuntu paket evidence'i olmadan iki katman da V2 acceptance tamamı için PASS değildir. |
| V2 acceptance | **PENDING** | Bu tur Windows host otomatik paket doğrulamasını ilerletti; Linux install/upgrade, guest GUI/WER/reconnect, tam iki-OS otomatik matrix ve etkileşimli kullanıcı kabulü tamamlanmadı. | Açık blocker'ları kapat; V2'yi COMPLETED ilan etme. |

Yerel commitler: `32c174c` terminal transport, `0e3e555` Linux metadata, `b76aa72` önceki evidence, `d31dcb71` V2 regression fixes/UI modularization. GitHub'a push/PR/release yapılmadı.

**Önceki snapshot (aşağıdaki tablo):** 2026-10-15 ve ilk devam doğrulamasındaki sayıları içerir; güncel devam kanıtı yerine kullanılmamalıdır.

## Güncel yerel non-interactive kampanya — 2026-10-16

Kaynak: `origin/develop` `062773261040fe3d3194c64ab74e461e14609481`; çalışma dalı `codex/v2-noninteractive-completion`. Kullanıcının kirli ana checkout'u değiştirilmedi; ayrı worktree kullanıldı. Bu kampanyada yerel commit'ler `32c174cba96c93e1e94c4e02b69b94c25372c295` ve `0e3e555bcaa820dc2274aa65a97b93537f818ac8`; GitHub'a push yapılmadı.

Durum sözlüğü: **COMPLETED** = exact source/artifact üzerinde kanıt var; **PARTIAL** = uygulandı, matris veya bağımsız kanıt eksik; **BLOCKED** = ortam/bağımlılık engeli kanıtlandı; **FAILED** = çalıştırılan test başarısız; **PENDING** = henüz yürütülmedi.

| Alan | Güncel durum | Kanıt ve kalan iş |
|---|---|---|
| Terminal IPC, CSP ve içerik mahremiyeti | **COMPLETED (hedefli)** | `32c174c` Ubuntu 24.04.5 üzerinde WebKitGTK terminal/fragment suite 42/42, davranış suite 19/19 ve W19 GDB lifecycle 20/20 PASS; inferior normal çıktı. Fragment queue 2 MiB / 4096-entry limitli; output tekrar gönderimi kapalı; ACK timeout/retry, sıra ve per-panel channel testleri eklendi. CSP `script-src 'self'`, `connect-src 'none'` korunuyor; URL/history'den terminal fragment kaldırılıyor. Geniş/high-volume soak ve gerçek ağ reconnect acceptance **PARTIAL/PENDING**. Kanıt `.tmp/evidence-linux-v2-32c174cb/`. |
| Ubuntu onedir Candidate | **COMPLETED (smoke)** | `32c174c` onedir tar SHA-256 `7c5b7e585b6817e598f200c397a051f6a8294dfecb2a2d4b8d3b763094362978`, 254 dosya; Linux packaged CLI, doctor ve GUI startup smoke PASS. |
| Ubuntu `.deb` | **COMPLETED (build/extract smoke)** | `0e3e555` kaynak kimliğiyle `.deb` üretildi, SHA-256 `dae29a464d8195cbeb88ae9dbee40cc9d1f64b92692f22b3beb62ab0b5073424`, 152,519,014 byte. `dpkg-deb -I`/contents doğrulandı; extracted packaged binary, Xvfb altında `linux_release_smoke.py --gui` PASS. Kontrol açıklamasındaki eski PySide6 ibaresi wxPython/WebKitGTK olarak düzeltildi. `.deb` root yetkisi olmadan kurulmadı; gerçek kurulum/upgrade/rollback **PENDING**. |
| Ubuntu AppImage / Flatpak | **BLOCKED** | Paylaşımlı Ubuntu-Test VM'de `appimagetool`, `flatpak` ve `flatpak-builder` yok; VM'ye sistem paketi kurma yetkisi kullanılmadı. CI/Docker release builder hattında artifact üretme ve smoke kanıtı gerekli. |
| Windows onedir Candidate | **COMPLETED (host smoke)** | `32c174c` kaynaklı EXE SHA-256 `10ea19d78d48667393dac2f5ade4aa0d8254ef5170e21bbe47760505f754b9bf`; smoke 20/20 PASS, `clean_shutdown` PASS. Manifest/log `.tmp/evidence-windows-v2-32c174cb/`. |
| Windows 11 guest | **PARTIAL** | Canonical runner `test\\home` oturumunda aynı EXE SHA ile `version` CLI çalıştı (exit 0, timeout yok, cleanup tamam). Bu GUI/UIA, WER lifecycle veya guest packaged full smoke değildir. Normal GUI başlangıç/UIA otomasyonu kanıtı eksik; eski runner geçici görev çakışması raporu var. |
| Ortak regresyonlar | **PARTIAL; geniş koşu FAILED** | `32c174c` Windows broad release suite **3020 PASS / 32 SKIP / 39 deselected / 49 FAIL** (1024.77 sn). Üç stale WebView/test path/facade varsayımı düzeltildi ve ilgili hedefli grup 25/25 geçti; geniş suite düzeltmelerden sonra yeniden çalıştırılmadı. Bu nedenle tüm suite **FAILED (yeniden doğrulama gerekli)**; kalan hataları yalnızca ortam kaynaklı sayma. FTP 168, transfer cancel 4, editor 14, remote listing 8 ve ilgili Jobs/transfer hedefli testleri PASS. Gerçek HPC LOCAL_REAL credential/endpoint kullanılmadı; uzak sistem davranışı bu kanıtta yok. |
| Kaynak mimarisi | **COMPLETED (değişen kapsam)** | Agent Core `validate-source-architecture.py --scope changed` her iki commit'te 0 limit aşımı / 0 dependency error verdi. Linux release validation ayrıştırmasından sonra `release_linux.py` 477 satır (uyarı bandı). Tüm proje kapsamlı taraması mevcut legacy dosyalardaki 500+ LOC ihlalleri nedeniyle **FAILED**; bunlar bu değişikliğin tamamlanmış kapısı değildir ve ayrı modülerleştirme işi olarak kalır. |
| Güvenlik, SBOM ve release integrity | **PARTIAL** | Strict CSP regression testleri ve candidate SHA/manifest kanıtları var. Linux `.deb` SHA sabit; Windows EXE SHA sabit. İki bağımsız audit katmanı, tam CI matrisi, tüm formatlar için imzalı/hash'li manifest ve release preflight henüz tamamlanmadı. |
| V2 acceptance | **PENDING** | Otomatik hedefli doğrulama ilerledi; geniş suite failure/retest, AppImage/Flatpak, Windows guest GUI lifecycle, Linux install/upgrade/rollback ve bağımsız auditler açık. İnteraktif kullanıcı testleri kapsam dışı. V2 **COMPLETED ilan edilmemelidir**. |

### `0e3e555` Linux metadata follow-up

- [x] Debian paket kontrol metni güncel wxPython/WebKitGTK runtime'ını tanımlıyor; release validator yanlış Qt runtime açıklamasını reddediyor. `tests/test_linux_release.py`: 28/28 PASS; Ruff PASS; changed-source architecture PASS.
- [x] Ubuntu 24.04.5'te yeni kaynak arşivi (`0e3e555` archive SHA-256 `06246dd7ad7fab6a8788286571af99c883a6c1bbe7eb99f85865fa656431d5be`) üzerinden `.deb` üretildi ve extracted packaged smoke PASS oldu. Paket, 32c'den 0e3e'ye değişmeyen onedir ürün içeriğini kullanıyor; metadata/test/release-validator kaynakları 0e3e commit'indendir.
- [ ] Ubuntu release planı dry-run PASS; tam release artifact seti (AppImage, `.deb`, Flatpak) ve bu formatların CI smoke/hash imzaları henüz yok.

**Audit tarihi:** 2026-10-15  
**Son uygulama/doğrulama:** 2026-10-16 — PR #44, Ubuntu WebKitGTK + Windows Actions
**Başlangıç HEAD:** `develop` `b80a06e419fbe77f485b9c5924f1e86c764201f0`
**Amaç:** V2 tamamlanması için kalan kod, doğrulama, provider, acceptance ve release işlerini tek yerde izlemek.

### W19 Ubuntu native sonuç — 2026-10-16 (PR #44, henüz develop'a birleşmedi)

- [x] Ubuntu 24.04 GitHub-hosted CI'de Python 3.14.8, resmi SHA-256 pinli wxPython 4.3.1 Ubuntu wheel, GTK3/WebKitGTK 4.1, Xvfb/D-Bus ve GDB ile tekrarlanabilir native W19 tanı hattı kuruldu. Workflow: `.github/workflows/w19-ubuntu-webkit-diagnostic.yml`.
- [x] Native SIGSEGV iki gerçek embedded native sahiplik hatasıyla ilişkilendirildi. `wx_jobs.py` gömülü Jobs host'unu doğrudan Destroy ediyordu (wxNotebook stale page; `wxBookCtrlBase::DeletePage`); `wx_remote_files_view.py` gömülü Remote Files host'unu Destroy ediyordu (wxSplitterWindow stale pane; `DoGetBestSize`). Gömülü sayfaların native yıkımı artık parent notebook/splitter'a bırakılıyor, standalone pencereler kendi Destroy davranışını koruyor.
- [x] W19 shell testlerinde `frame.Destroy()` yerine gerçek `EVT_CLOSE` / `frame.Close()` kullanıldı. `test_profile_switch_invalidates_navigation_and_filters` OS keyring olmayan CI'de yalnızca test düzeyinde private-store arayüzü mock'u kullanıyor; production encryption şartı değiştirilmedi.
- [x] **Ubuntu W19 native lifecycle 20/20 PASS, GDB normal exit**: PR #44 ürün/test HEAD `23c33fb0d68a02d772d513b5129e03331e89b5cd`, Actions `38870168010`. Bu yalnızca bu exact commit ve hosted Ubuntu runner'da doğrulandı; Ubuntu-Test VM ve tam karma GUI suite henüz doğrulanmadı.
- [x] **Ubuntu W19 CSP terminal readback / alternate screen FIXED on hosted Ubuntu:** `RunScript('1+1')` dahil tüm JS değerlendirmesi strict CSP yüzünden red veriyordu. Linux'ta sadece izinli terminal komutlarını taşıyan local `file://` same-document fragment IPC, sıralı ACK ve JS→Python yapılandırılmış ekran durumu yanıtı eklendi; `script-src 'self'`, `connect-src 'none'` değişmedi. W19 readback/alternate buffer test **1/1 PASS**, native lifecycle **20/20 PASS**, normal GDB exit: Actions `38872300689`, product/test HEAD `8bd7a492eb06638aba876016aceb0ecea16c8533`. Kaynak CI **4/4 PASS** (`38872300694`), Windows hosted onedir packaged smoke PASS (`38872300669`). Ek kapanış kuyruğu temizliği ve WebView URL-fragment hijyen kontrolüyle commit `3a450dbbc524c656298ec8969e993c7dbf3e2916` üzerinde Ubuntu W19 native run `38872889770` **PASS** (readback/alternate-screen 1/1, lifecycle 20/20; GDB normal exit). Aynı HEAD source CI `38872889779` **4/4 PASS** ve Windows hosted onedir smoke `38872889753` **20/20 PASS** (EXE SHA-256 `ad8db3c0cd916852a53311e6d1fb42f502a0d4a324de8ffe797871b7a4f2bfd9`). PR merge, Ubuntu VM, terminal yüksek hacim/URL-history performans-güvenlik incelemesi ve nihai release acceptance hâlâ açık.
- [ ] W19 takip işleri: Ubuntu-Test VM'de native interaktif olmayan yeniden yürütme, yüksek hacimli terminal fragmanı/ACK performans ve hassas çıktıların history/URL'de kalmama kanıtı, Linux onedir paket ve karma GUI stres regresyonu. PR #44 henüz birleşmedi; final release/freeze kabulü değildir.

### Windows onedir tanı kampanyası — 2026-10-16 (PR #43)

- [x] PR #42 birleşti: `develop` HEAD `2d8a34c920bc771d7c370b4d73236b96c8c56c65`. W55/W16 kaynak düzeltmeleri ve temizleme hata tanıları güncel dalda.
- [x] **GitHub-hosted Windows onedir paket tanısı 20/20 PASS:** PR #43 head `afdfb2b4b29a4ee5836f7f1dec723d688f5ae621` / workflow checkout PR merge snapshot `7bc405f3b7747545f7cc07f4240c89bae60fee47`; Actions run `38865908045` PASS. Python 3.14.8 + `requirements-release.lock` + PyInstaller onedir; EXE SHA-256 `1b645db42a425b5312dcd1f152e39e1c0c0967d501b6dca67c1b950a34e78d7c`. Packaged loopback SSH/PTY, all 20 smoke checks PASS, child exit 0, frame_destroyed=true, cleanup_callbacks_drained=true, cleanup_failures=[], transport_closed=true, event_loop_exited=true. Candidate ve runtime JSON logları run artifactlerinde yedi gün tutulur. **GitHub-hosted Windows Server 2025 kanıtıdır; Windows11 interactive guest/release kabulü değildir.**
- [ ] **Windows11 gerçek kullanıcı oturumu acceptance hâlâ açık:** PR #43 `develop` `10ac46557c81b8f0445fd9ee06b35faf0cec8dc3` olarak birleşti; bu güncel branch ve PR #44'teki embedded owner düzeltmeleriyle Windows11 VM'de immutable onedir, WER/native teardown ve canonical interactive 20/20 yeniden doğrulanmalı. GitHub-hosted Windows 20/20, Win11 interaktif VM'nin yerine geçmez.
- [x] **W19 GitHub-hosted Ubuntu native + terminal CSP readback düzeltildi:** GTK notebook/splitter gömülü sahipliği ve strict-CSP same-document terminal köprüsü onarıldı. İlk birleşik W19 **PASS** run `38872300689`; kullanıcı Ubuntu VM/karma GUI, Linux paket, performans ve privacy regresyonları hâlâ açık.
- [x] **W55 kapanış zinciri kök neden ve düzeltme:** `src/hpc_gui/wx_jobs.py` eski `host.Hide` cleanup callback'i yıkılmış wx panelde `RuntimeError` üretiyordu; callback kaldırıldı ve cleanup boş hata listesiyle PASS oldu. Son sahte FAIL, silinmiş wx Frame C++ wrapper'ında Python üyelik/eşitlik karşılaştırmasından kaynaklanıyordu; identity ve gerçek C++ silinme işareti ile fail-closed doğrulandı. Bounded 25-poll negative/positive unit regressions PASS.
- [x] **PR #43 head source CI:** Ubuntu+Windows source quality ve portable tests `38865908160` üzerinde **4/4 PASS** (head `afdfb2b4`).

### Güncel ilerleme — 2026-10-16

**Güncel develop:** `935bc1c57b14438d7b657f3c6cddab2328ecc3e2` (PR #41 squash-merge). GitHub Actions run `38861669606`: **4/4 PASS**. Aşağıdaki 15 Ekim raporları tarihsel kayıtlardır; eski 245 Ruff bulgusu güncel HEAD sonucu değildir.

- [x] `.github/workflows/ci.yml` restore edildi. Ubuntu+Windows Python 3.14/Ruff 0.16.8/compileall/i18n ve iki portable test PASS; bu tam V2 acceptance veya packaged GUI testi değildir.
- [x] Tarihsel Ruff hatalarını oluşturan emekli Agent Core kodları (4 script + 4 test) kaldırıldı; iki gerçek F841 düzeltildi. Kaynak CI 4/4 PASS.
- [x] POSIX path ve wx plugin owner statik testleri düzeltildi; Ubuntu+Windows'ta hedefli iki test PASS.
- [x] `tests/test_wx_a11y.py` sahte `IsShown() or True` olumlaması kaldırıldı; GUI a11y kabulü ayrıca açık.
- [ ] **W55/W16 clean_shutdown:** Bu takip dalında `clean_shutdown` ilk değerinin `FAIL` yerine `PENDING` olması, olmayan `wx.IsDestroyed` çağrısının kaldırılması ve 100ms deferred registry gözlemi kodlandı; headless pozitif/negatif shutdown testleri CI'ye eklendi; `WxLifecycleController` artık başarısız cleanup callback adını ve yalnızca exception sınıfını (`cleanup_failures`) runtime JSON'a taşıyor, gizli exception mesajlarını taşımıyor. Headless source/contract CI `38862771589` (HEAD `1a2bc1514a2f6cdc468a17fa4e40bd39c988567c`) Ubuntu+Windows **4/4 PASS**; yeni Windows11 immutable Candidate / packaged 20/20 / native WER PASS kanıtı **yok**.
- [ ] **W19/Linux:** WebKitGTK CSP `RunScript` readback ve `libjavascriptcoregtk-4.1.so.0` SIGSEGV hâlâ açık. Headless CI bu alanı kapsamıyor.
- [ ] **Windows UIA:** Normal packaged Connection startup runner kanıtı eksik (önceden proses başlamadan runner hatası).
- [ ] **Tam V2:** LOCAL_REAL, full GUI suite, Windows/Linux/macOS paketler, DPI/accessibility, artifact+SHA, çift audit, freeze ve release açık.

**Kanıt ayrımı:** W55 source/contract doğrulaması `1a2bc151` üzerinde 4/4 PASS ile sonuçlandı. Bu native shutdown başarı kanıtı değildir; yeni immutable Windows11 packaged smoke ve WER doğrulaması zorunludur.

### Yeniden audit — 2026-10-15, güncel `develop` `ea27d75c`

Önceki başlıklardaki commit kimlikleri tarihsel test kayıtlarıdır; aşağıdaki bulgular güncel `develop` üzerindeki son kontrolleri gösterir.

- [ ] Güncel Ruff 0.16.8 taraması `ruff check src scripts tests` ile **245** bulgu verdi: `src/` 0, `tests/` 127, `scripts/` 118. Dağılım: E702 123, E701 64, F405 50, E401 3, F841 2, E703 1, F401 1, F403 1. Önceki 413 bulguluk rapora göre azalmış olsa da CI/lint işi tamamlanmış değildir.
- [ ] Ubuntu-Test üzerinde wxPython 4.3.1 + GTK3 GUI testlerinde WebKitGTK `RunScript` CSP tarafından reddediliyor (`unsafe-eval`); terminal ekran durumu readback testi bu yüzden başarısız. `test_w19_connection_lifecycle.py` teardown sırasında `libjavascriptcoregtk-4.1.so.0` içinde SIGSEGV verdi. Ayrıca POSIX testinde Windows yolu beklenmesi ve wx plugin testinin eski facade sembolünü araması olmak üzere iki dar test uyumsuzluğu var. Güvenlik politikasını zayıflatmadan WebKit köprüsü/owner çözümü gerekli.
- [ ] Windows11 guest'te güncel kaynak arşivinden üretilen wx packaged smoke 20 kontrolden 19'unu geçti; `clean_shutdown` başarısız. WER/Application Error sorgusunda son iki saatte uygulamayla eşleşen olay yok; bu tam crash/lifecycle kampanyası yerine geçmez.
- [ ] Windows11 normal başlangıç/Connection sekmesi UIA probe'u uygulamaya ulaşmadan runner'ın geçici görev başlatma hatasıyla durdu (`Cannot create a file when that file already exists`). Bu uygulama FAIL kanıtı değildir; probe/runner yürütme kanıtı eksiktir.
- [ ] Linux odaklı grubun güncel kaydı 26/27 PASS; kalan yukarıdaki path/facade/WebKit/lifecycle hataları açık. Önceki başarılı hedefli testler kendi commit kimliklerine aittir ve yeni HEAD için toplu kabul sayılmaz.
- [ ] Canonical Wave preflight daha önce proje WAVE profile'ı ile W55/W16 owner tanımlarının mevcut kaynakta bulunmadığını bildirdi. İlgili kapalı-Wave onarımını kanonik owner işlemi olmadan yapma; resmi authority kaynağını geri kazan veya eksikliği belgeleyerek bağımsız TODO maddelerinde ilerle.
- [ ] Bu audit sırasında çalışma ağacında önceden var olan `.gitignore`, `docs/wave-reports/v2/luna/W64_WAVE_REPORT.md` değişiklikleri ile `W57_FREEZE_DECLARATION.md` ve `rapor` silmeleri korundu; bu dosyalar V2 TODO commit'ine dahil edilmemelidir.

## Durum ve kanıt kuralları

- Bu dosya çalışma TODO'sudur; release kabul belgesi değildir.
- Bir madde yalnızca kod mevcut diye tamamlanmaz. Kanıt, test edilen tam commit ve mümkünse paket SHA-256 ile eşleşmelidir.
- Önceki Candidate 6/7/8/9 sonuçları kendi commit ve paketlerine aittir; güncel `develop` için kabul kanıtı sayılmaz.
- GitHub CI run `38688191566`, `4a7170ad` üzerinde 15 Ekim'de aynı `ruff check src scripts tests` komutuyla **413** bulgu kaydetti; temiz detached worktree'de Ruff 0.16.8 ile bu sonuç yeniden üretildi. Sonraki temiz `53bc413d` HEAD'inde aynı Ruff sürümü ve komut **245** verdi; geniş `ruff check .` sayısı 252. Aradaki 81 dosyalık değişiklikte F401 123→1, F841 25→2 ve E402 20→0 oldu; dolayısıyla tarihsel 413 farkı commit içeriğindeki değişikliklerle açıklanıyor, araç sürümü/kapsam farkıyla değil. `src/` altında güncel Ruff bulgusu yok; kalan 245 bulgu validator/test yüzeylerinde. Mevcut `develop`'da `.github/workflows/ci.yml` silinmiş olduğundan `a759aebc` push'u için yeni CI çalışması oluşmadı.
- Bu çalışmaya başlamadan önce checkout'ta var olan kullanıcı değişiklikleri korunur.

### Güncel doğrulama kaydı — 2026-10-15, `develop` `dd488023`

- [x] Python 3.14 yerel bağlantı/profil grupları: servis kimliği, profil saklama ve auth 33/33; Qt gelişmiş ayarlar/profil koruma 34/34; wx bağlantı, profil, hardening, host-key, lifecycle ve migration 124/124. Toplam **191 hedefli test PASS**. Bunlar paketlenmiş GUI ya da gerçek uzak host kabulü değildir.
- [x] Provider/plugin yerel testleri, `HPC_GUI_CONTRACT_REPO=D:\Projeler\hpc-client-gui-plugins` ve plugin checkout HEAD `8cce85446a8db72ea6b89b56bcb3df8916cbb0a8` ile **215/215 PASS, 0 skip** verdi. Ayrı Qt plugin manager grubu 37/37 yeni test, wx plugin manager grubu 17/17 PASS; toplam **269 yerel provider/plugin testi PASS**. Bu, resmi registry yayını veya gerçek HPC bağlantısını kanıtlamaz.
- [x] Aynı plugin checkout'unda `python scripts/validate_registry.py` **OK**, tam pytest paketi **188/188 PASS**, `ruff check --no-cache scripts tests` **PASS**. Yerel registry Perlmutter, Frontera, Stampede3, Delta, LUMI, Leonardo, Setonix ve JUWELS 1.0.0 profillerini içeriyor; TRUBA 1.5.0 da mevcut. Bu profillerin resmi yayımı/gerçek host kullanımı bu kanıtın dışında.
- [ ] Windows onedir candidate `dd488023` kaynak kimliğiyle üretildi: EXE SHA-256 `ad9d83cb5b4a3c79561a250c52d3f1218f15eba068d177cb72713212ffcd8bee`, plugin SHA `8cce85446a8db72ea6b89b56bcb3df8916cbb0a8`, Python 3.14 / PyInstaller 6.22.2. Aynı EXE üzerinde iki packaged smoke da **19/20 PASS** verdi; tüm UI, SSH/PTY, resize, dosya/job roundtrip ve transfer kontrolleri geçti, `clean_shutdown` kaldı.
- [ ] Kapanış tanısı tekrar üretildi: wxPython 4.3.1'de `wx.IsDestroyed` API'si yok; mevcut finalizer bu çağrıdaki `AttributeError`'ı yutup `frame_destroyed=false` yazıyor. Ayrıca lifecycle cleanup kaydında `Panel.Hide()` callback'i panel yok edildikten sonra `RuntimeError: wrapped C/C++ object of type Panel has been deleted` veriyor; bu yüzden `cleanup_complete=false`. Gecikmeli gözlemde de callback hatası sürüyor. Kaynak alanı kapalı W55'e (HPC-W10-GJ2-051), smoke/gate gözlem düzeltmesi kapalı W16'ya yönlendirilmeli; kod/evidence gate değiştirilmedi. Kapalı owner düzeltmesi yapılmadan bu FAIL kabul edilmemeli veya PASS'a çevrilmemeli.
- [ ] Bu candidate host Windows'ta çalıştırılmıştır; Hyper-V guest acceptance, native crash/WER ve gerçek bağlantı testi değildir. Windows11 `test\home` kimliği ve guest IP'leri PowerShell Direct ile doğrulandı; ancak guest'ten geçici SSH/SFTP fixture'ına Default Switch (`172.28.144.1`) ve `hpc-lab` (`192.168.250.1`) üzerinden TCP erişimi başarısız oldu. Firewall/VM ayarı değiştirilmedi; guest packaged smoke **BLOCKED_ENV** (guest'ten test servisine erişim yok). Candidate geçici `.tmp` altında tutuluyor; immutable release candidate değildir.

### Devam doğrulaması — 2026-10-15, `develop` `cec26ae352d0d2bcee29e79d0bafdc7198135d03`

- [x] wx splitters artık oranı `wx_splitter_ratios` ayarıyla kaydedip yeniden açılışta yüklüyor; Directories, Files local/remote ve Files browser/transfers ayraçları oranı resize sırasında koruyor.
- [x] Windows wx GUI testleri: `tests/test_wx_shell_layout.py` **7/7 PASS**; dar Files workspace'te local toolbar **1/1 PASS**. Sash oranını kaydetme/yeniden yükleme simülasyonu ve gerçek dikey/yatay splitter resize senaryoları kapsandı.
- [x] `tests/test_wx_layout_resize.py::test_wx_layout_resize` **1/1 PASS**: EN/TR **400/400** resize ve **2.800/2.800** tab seçimi; sıfır geometri, kırpılma, overflow, layout exception ve detached-frame invariantlarının tümü **0**. Test commit `cec26ae3` üzerinde çalıştırıldı.
- [x] Değişen kaynak/test Ruff ve Agent Core source architecture gate PASS; 500 satır üstü dosya yok, bağımlılık hatası yok.
- [ ] Bu GUI turunda wxWebView2 teardown sırasında `0x80004004 Operation aborted` stderr satırı görüldü; test ve layout invariantları PASS olsa da terminal WebView2 lifecycle/native-crash kabul maddesi açık kalıyor.

### Transfer integration turu — 2026-10-15, `develop` `7336764cbd95b99e9130974595ee282b718c8faa`

- [x] `tests/test_transfer_concurrency.py` **10/10 PASS**: FTP paralel upload'larında ayrı bağlantılar ve SHA-256 içerik eşitliği; SFTP paralel upload'larında ayrı kanal; iptal/başarısızlık/yeniden denemede backend resource kapanışı.
- [x] `tests/test_download_cancel_wire.py` **4/4 PASS**: yerel mock SSH/SFTP wire üzerinde 48 MiB indirmeyi iptal etme, kısmi dosyayı koruma, resume ile tamamlayıp boyutu doğrulama, ayrıca overwrite/skip davranışları.
- [ ] Bu fixture sonuçları gerçek HPC endpointindeki transfer/resume kanıtı değildir; credential/proje erişimi olan gerçek sistem doğrulaması açık kalıyor.

### Klavye ve erişilebilirlik turu — 2026-10-15, `develop` `7ea65ef5eea149277b79ed05a18939ba0b5313ca`

- [x] `tests/test_wx_file_keyboard_parity.py` **17/17 PASS**, `tests/test_wx_file_context_i18n.py` **5/5 PASS** ve `tests/test_wx_a11y.py` **2/2 PASS**. Yerel klavye eylemleri, EN/TR context-menu etiketleri, tab/menu metinleri ve temel sekme seçimi denetlendi.
- [ ] Tam erişilebilirlik kabulü açık: W61 testi `files_page.IsShown() or True` ile görünürlüğü gerçekte doğrulamıyor; focus traversal, screen reader ve görsel/DPI denetimleri bu test turunda kanıtlanmadı. Keyboard test sonrasında wxWidgets `UnregisterClass ... Class still has open windows` stderr uyarısı da görüldü; GUI lifecycle kabulü ayrı açık.

### Startup ve terminal kaynak GUI turu — 2026-10-15, `develop` `2d9126546571383b3a2da97e3511532bdffef064`

- [x] `tests/test_w40_gui_acceptance.py` **6/6 PASS**; source wx shell'de yeni oturum Connection sekmesinde başlıyor ve EN/TR 1280×760 / 1440×900 geometry kontrolleri geçti.
- [x] İzole `tests/test_wx_terminal_webview.py` **29/29 PASS**; local WebView/xterm, input/output, resize, reconnect generation guard, close/destroy-before-ready ve reconnect döngüleri denetlendi.
- [ ] Bu izole kaynak turu paketlenmiş WebView2/WER veya karma GUI suite native-heap kabulü değildir. Daha önceki layout kapanışında `0x80004004 Operation aborted` stderr görüldü; mixed-suite native crash maddesi açık kalıyor.

### VM devamı — 2026-10-15, test anındaki `develop` HEAD `a66ed9a2`, test edilen kaynak `8499f2b2`

- [x] Windows 11 `test\home` aktif Explorer oturumunda GUI smoke çalıştırıldı. Temiz worktree'den üretilen onedir GUI EXE SHA-256 `f250ba6752a889444821ac02ed24634254cc63c88725cf079d2510921ca3c1d6`; `Invoke-Windows11Interactive.ps1` host/guest EXE hash eşleşmesini, oturum 2 kimliğini ve başarılı cleanup'ı doğruladı. Runner `ExitCode=0`, `Timeout=false`, `CleanupStatus=completed`; smoke runtime SHA-256 `6be21794c566117ead49c65e2aee6b154fd8789388b967e3a39306d30f8b0eac` ve yerel kanıt `.tmp/w11-vm-acceptance-8499f2b2/w11-runtime.json`.
- [ ] W11 runtime raporunda 19 kontrolün 17'si PASS, `clean_shutdown=FAIL`, `pty_resize=PENDING`. Kapanışta `frame_destroyed=false` ve `cleanup_callbacks_drained=false`; resize için istek `(123,45)` kaydedildi ancak gözlenen PTY ölçümü yok. Üst seviye JSON `result=PASS` dese de alt kontroller acceptance PASS sağlamıyor. Bulgular W55 lifecycle ve W16 smoke/evidence sahiplerine kapalı-owner repair akışıyla yönlendirilmeli.
- [ ] Paket, `8499f2b2` commit'inden üretildi. Test anındaki `develop` HEAD `a66ed9a2` ile arasındaki değişikliklerde `src/`, `tests/`, `scripts/` ve `build/` aynı kaldı; yine de bu çıktı güncel HEAD kimliğinde immutable Candidate değildir ve V2 acceptance maddelerini kapatmaz.
- [x] W11 guest'te host fixture erişimi `172.23.128.1:53665` için başarısız oldu; firewall/VM ağı değiştirilmedi. SSH/SFTP adımlarını sınamak için smoke fixture'ı W11 içinde yalnızca loopback'e bağlandı.
- [ ] Ubuntu-Test canlı `Running`; `ubuntu-doctor` strict SSH ile PASS ve registry'deki Linux hesabı `test`. Guest Python `3.12.3`, proje ise `==3.14.*` istiyor. Sistem `pip`, pytest, wxPython, `wx-config`, `pkg-config` ve `xvfb-run` yok; kullanıcı venv'i ve pip 24.0 oluşturulabildi, ancak PyPI wheel isteği guest DNS çözümleme hatasıyla başarısız oldu ve parolasız sudo yok. Linux wxPython/pytest turu **BLOCKED_ENV**; bu turda Linux testi çalıştırılmadı.

### Linux VM devamı — 2026-10-15, `develop` `5bc6ea29`

- [x] Ubuntu-Test `Ubuntu 24.04.5 LTS`, `Running`; `ubuntu-doctor` ve strict SSH (`test`) PASS. Guest DNS/PyPI erişimi bu turda çalıştı. Güncel commit kaynak arşivi `git archive 5bc6ea29` ile üretildi (SHA-256 `cec2f788c1f568bd99434df021ce1ed10f4ce856b11f286fe361b393eaaab061`) ve guest `.tmp` altına açıldı; guest'e Git kurulmadığından test kaynağının kimliği arşiv hash'iyle tutuldu.
- [x] Guest `.tmp` içinde uv ile Python **3.14.8**, test venv'i ve `requirements-legacy-qt-test.lock`'tan PySide6 **6.11.2** kuruldu. wxPython **4.3.1+ubuntu2404** CPython 3.14 wheel'ı [wxPython'ın resmi indirme sayfasındaki](https://wxpython.org/pages/downloads/) GitHub release'inden kuruldu; eksik SDL2 runtime ve Xvfb paketleri sistem kurulumuna dokunmadan `.tmp` içine indirip açıldı. Xvfb/GTK3 altında `wx.Frame` açma-kapama smoke'u PASS.
- [ ] `test_wx_lifecycle.py`, `test_wx_runtime_observation.py`, `test_wx_packaged_smoke.py`, `test_wx_packaged_smoke_raw_runtime.py`: **26/27 PASS**. Tek fail `test_workdir_outside_repo_excludes_repo_tmp`: test Linux'ta da Windows yolu `C:/Windows/Temp` veriyor; POSIX `Path` bunu mutlak yol saymıyor.
- [ ] wx işaretli testlerde `test_hardening_additional.py::test_wx_dispatch_uses_host` ilk hata: **15 PASS, 1 FAIL**. Test `WxPluginMenuHost` sembolünün `src/hpc_gui/wx_shell.py` facade dosyasında bulunmasını bekliyor; güncel facade bu parçayı başka modüllerden birleştiriyor.
- [ ] `test_w19_connection_lifecycle.py` Ubuntu/Xvfb altında 16 testten sonra fixture teardown sırasında native **SIGSEGV** verdi; C-stack `libjavascriptcoregtk-4.1.so.0` içinde. Xvfb-only ve private D-Bus/software-render tekrarlarında da aynı crash oluştu. Tam wx işaretli run aynı crash'te kesildi; toplam suite sonucu alınamadı.
- [ ] `test_wx_terminal_webview.py` özel D-Bus oturumu + Xvfb + GTK X11 + software-render ayarlarıyla **28/29 PASS**. Bridge-ready testi artık geçiyor; tek fail `test_wx_terminal_screen_state_readback_and_alternate_buffer`, yazımdan sonra gerçek `hpc_get_screen_state()` sonucu `None`. Xvfb-only ilk koşuda bridge-ready timeout ve pytest hang'i oldu; sadece bu pytest süreci durduruldu, VM açık kaldı.
- [x] Linux readback teşhisi: WebKitGTK bridge `ready=true` olduktan sonra bile `RunScript("1+1")` `(False, "")` döndü; `RunScriptAsync("JSON.stringify({ok:true})")` `wxEVT_WEBVIEW_SCRIPT_RESULT` üzerinden CSP `EvalError` verdi: `script-src 'self'` eval'e izin vermiyor. Bu, readback hatasının payload boyutundan değil, wx terminal Python→JavaScript çağrılarının Linux CSP sınırından kaynaklandığını gösteriyor; güvenlik politikasını koruyan uyumlu bridge çözümü açık. Probe `5bc6ea29` üzerinde yapıldı; bu commit ile güncel HEAD arasında `src/`, `tests/`, `scripts/` değişikliği yok.
- [ ] Güncel commit'te `tests/test_wave_controller_regressions.py` ve `tests/test_wave_state_engine.py`, kaldırılmış `.opencode/scripts` dosyalarını import ediyor. Canonical preflight managed Core dosyalarını yeniledi ancak proje profili olmadığı için boş template oluşturdu ve compatibility exit 10 ile durdu. Tarihsel commit'te W55/W16 owner spec'leri yok; kapalı-owner onarımını gerçek authority olmadan başlatmak veya bu testleri yok sayarak suite PASS saymak mümkün değil.

### Güncel Windows11 paket kabulü — 2026-10-15, kaynak `f5b4d66f`

- [x] Temiz `git archive` kaynağından Python **3.14.0**, PyInstaller **6.22.2**, wxPython **4.3.1** ile geçici onedir GUI paketi üretildi. Kaynak arşiv SHA-256 `a6d4a130ae828bb637db249080c28db516c0a06f2e98e88e3527a2327c0095fe`; GUI EXE SHA-256 `ee47f0b835bfdf6752859e10743451527b819be5a4c040e731f61fff7e0fe97a`. Candidate manifest SHA-256 `4afe9b4e6ce9fef030c94907d61b90b844500e67b5bd87dddd762ace505d927e`; bütün geçici artefaktlar `.tmp/w11-current-f5b4d66f/` altında.
- [x] Canonical `Invoke-Windows11Interactive.ps1`, aktif `test\home` Explorer oturumunu (session 2) kullandı. Host/guest smoke launcher SHA-256 `54ad5276d9494d1614d0eed1711ee36a11761a42d5425ddb77acae2f8e43a6e7`; GUI EXE ve candidate manifest hash'leri de guest'te eşleşti. RunId `6a406bceee2f42a59491a36e295198a8`; timeout yok, runner cleanup tamamlandı.
- [ ] Canonical `wx_packaged_smoke` sonucu **FAIL**: 20 kontrolden **19 PASS**, `clean_shutdown=FAIL`; PTY resize loopback sunucusuna ulaştığı için PASS. Runner exit 1, timeout yok. Gate rapor özeti SHA-256 `76ca38b50865197e3c35330615359b97e2c64227184e4f8d8ce94c9cf091e9e7` (`.tmp/w11-current-f5b4d66f/canonical-smoke-report.json`).
- [ ] Paketli uygulamanın normal modda `Connection` seçili açılması hâlâ doğrulanmadı. UIA probe'un onefile ve onedir sürümleri runner task'ında GUI PID/stdout oluşmadan `Cannot create a file when that file already exists` hatasıyla durdu (RunId `83c9454818a441fc8c2291654f980860`, `d224e0f744c542d2ac5546f577512ed9`); bunlar uygulama açılış sonucu değildir.
- [x] Son iki saatin W11 Application log sorgusunda uygulama adına eşleşen WER/Application Error olayı yoktu; çalıştırma sonrası smoke/app süreci kalmadı. Bu tek koşu için olay yokluğu geniş native-crash kampanyasını tamamlamaz.

### Başlangıç çalışma kaydı — 2026-10-15

- [x] İlk yerel Ruff baseline'ı ve kaynak/test/script dağılımı çıkarıldı.
- [x] Kullanılmayan wx kodu/importları temizlendi ve `wx_shell.py` facade importları düzenlendi; toplam yerel Ruff bulgusu 434'ten 313'e indi.
- [x] Değişen wx modüllerinde hedefli Ruff kontrolü geçti.
- [x] Güncel değişen kaynak/testler için Agent Core mimari doğrulayıcısı geçti; `wx_shell_files.py` 404, `wx_shell_fresh_smoke.py` 448, `wx_shell_packaged_smoke.py` 485 ve `tests/test_wx_packaged_smoke.py` 402 satırla uyarı bölgesinde.
- [x] Ruff'taki gerçek kullanılmayan transfer facade importları explicit re-export olarak işaretlendi; packaged-smoke script/test import temizliği yapıldı; CI lint kapsamı 306'dan 292'ye indi.
- [x] File-manager başlangıç testleri TODO-025 kaynak-checkout korumasına uyumlu hale getirildi; file-manager profili 10/10, local-directory politikası 18/18 PASS.
- [x] İlk odaklı GUI regresyon turu 54/54 PASS verdi.
- [x] 1.408 satırlık `wx_remote_files_view.py`, listeleme, gezinme, etkileşim, aksiyon ve işlem bileşenlerine ayrıldı; ana facade 447 satır, yeni bileşenlerin en uzunu 322 satır. İlgili Ruff kontrolü temiz, değişen kaynak mimari doğrulaması PASS.
- [x] Refaktör sonrası remote dosya eylemleri, sekmeler, yaşam döngüsü, klavye, undo, editör ve transfer regresyonları 125/125 PASS; remote kaynak sözleşmeleri 19/19 PASS; 200 sağ-tık seçim stres kontrolü 1/1 PASS.
- [x] `wx_local_files.py` 1.183 satırdan 249 satıra, toolkit-free model, destek, liste/gezinme, etkileşim, mutation ve lifecycle modüllerine ayrıldı. Local ve remote wx listelerine sistem paletinden türetilen zebra satırları eklendi.
- [x] Local ve remote dosya listesi zebra GUI testleri geçti. 133 local/remote dosya, sekme, eylem ve model regresyonu; 12 GUI-FILE-003 stres testi PASS. Stres kampanyasında 200 sağ-tık, 100+100 mutation, 200 navigation yarışı, 50 aç/kapat, 25 in-flight close, 100 transfer, 50 Unicode/boşluk adı ve 20 reconnect snapshot tamamlandı; kaçak/stale/yanlış hedef/kayıp/çift transfer ölçümleri sıfır.
- [x] Dosya türü ikonları için Qt ve wx arayüzlerinin paylaştığı framework bağımsız uzantı sınıflandırması eklendi; wx local/remote listelerinde dosya türü ve klasör ikonları satırlara bağlandı. Gerçek wx `ListCtrl` öğelerindeki ikon indeksleri test edildi; odaklı local/remote GUI ve regresyon grubu 95/95 PASS, değişen Ruff ve kaynak mimarisi kontrolleri PASS.
- [x] `cec26ae3` ile wx splitter oranlarının saklanması/geri yüklenmesi ve resize davranışı tamamlandı; önceki `dd488023` baseline'ındaki layout ölçüm sorunu `IsShownOnScreen()` ölçümüne, `1355x929` dar local toolbar sorunu `wx.WrapSizer` düzenine geçirildi. Commit'e bağlı 400 resize / 2.800 tab kabul testi ve ayrıntılar yeni devam doğrulama kaydında.
- [ ] SSH/SFTP/terminal/Slurm/transfer turu güncel `a759aebc` ve Python 3.14'te 120 test çalıştırdı: 119 PASS, 1 FAIL (`test_ssh_backend_rejects_invalid_utf8_text`). `W57.4_WAVE_REPORT.md`, testin W29 öncesi strict-decode beklentisi olduğunu ve W29 OUT-005 replacement davranışının doğru kabul edildiğini kaydediyor; bu nedenle FAIL doğrulanmış ürün hatası değil, kapalı W03 test beklentisinin owner-routed güncelleme işi. Test güncellenip tekrar çalışana kadar suite kırmızı kalır.
- [ ] `wx_shell.py` facade düzenlemesinden sonraki geniş regresyon turunda native Windows access violation oluşturan Qt transfer-iptal senaryosunu kapat; test ayrı süreçte geçiyor, karışık GUI suite içinde doğrulama sürüyor.
- [x] Transfer retry worker-race düzeltmesi yapıldı; ilgili birim grubu 5/5 ve yeniden deneme regresyonu 10/10 PASS verdi.
- [x] Linux/Windows release preflight için pinlenmiş test-only Qt lock eklendi; testlerden sonra Qt paketleri kaldırılarak wx release build ortamı temiz tutuluyor.
- [x] Bu checkout'taki Git-ignore edilmiş yerel `uv.lock`, `uv lock --offline` ile yeniden üretildi ve `uv lock --check --offline --quiet` geçti; bu dosya izlenen release/CI lock girdisi değil.
- [x] Qt transfer-iptal test dosyası release suite'te ayrı prosese alındı; izole dosya 3/3 PASS verdi. Geniş release suite sonucu henüz alınmadı.
- [ ] Windows Qt transfer-iptal testinde native access violation inceleniyor; guest runner çalışıyor ama guest'te proje checkout'u bulunmuyor (`D:\Projeler\hpc-client-gui` yok).
- [x] Proje `.venv` Python 3.14 ortamında pytest 9.1.1, wxPython 4.3.1, PySide6 6.11.2, PyInstaller 6.22.2 ve Paramiko 5.0.0 bulundu; GUI doğrulamalarında bu yorumlayıcı kullanılıyor. Global `py -3.14` yorumlayıcısında bu paketler hâlâ yok.
- [ ] Tam release preflight yerel ortamda henüz sonuçlanmadı. PATH'teki `python` 3.12 olduğundan proje `.venv\Scripts\python.exe` kullanılmalı; önceki 3.12 pytest collection turunda yerel `.opencode` dosya silmeleri iki Wave testini görünmez kılmıştı. Paket/build ve tam test matrisinin güncel, temiz kaynakta çalışması hâlâ açık.
- [x] `wx_remote_files_view.py` dosyasını sorumluluklarına göre böl; iki Ruff bulgusunu kapatıp mimari sınırı doğrula.
- [ ] Güncel `develop`'daki 245 Ruff bulgusunu dosya sahipliğine göre yönlendirip kaynağın/testlerin mimari sınırını koruyarak kapat.
- [x] Remote dosya tarayıcısı refaktörü için odaklı wx regresyon grubunu tamamla; kalan GUI V2 kabul testleri ayrı maddeler olarak açık.

## 1. Kod ve test hataları

- [x] Tarihsel 413 bulgusunu GitHub CI run `38688191566` / `4a7170ad` ile eşleştir ve temiz worktree'de doğrula; aynı Ruff 0.16.8/komut `53bc413d`'de 245 verdi, düşüş commit aralığındaki kod/test değişiklikleriyle açıklanıyor.
- [x] Tarihsel `362ece5e` Ruff 245 bulgusu PR #41 sonrası `develop` `935bc1c5` için ortadan kalktı. Ubuntu ve Windows kaynak kalite gate'i Ruff 0.16.8 ile PASS (`38861669606`); eski silinen Agent Core dosyaları artık tarama kapsamının parçası değil.
- [x] `.github/workflows/ci.yml` PR #41 ile `develop` üzerine geri alındı; GitHub Actions run `38861669606` **4/4 PASS**. Tam GUI/LOCAL_REAL/packaged acceptance ayrıca açık.
- [x] Güncel `develop` için `ruff check src scripts tests` gate'i Ubuntu+Windows CI'da PASS. Proje genelinde 500 satır sınırı ve GUI mimari uyumluluğunun bağımsız auditi ayrıca açık.
- [ ] Ubuntu-Test Linux GUI ortamı artık `.tmp` içine kurulu Python **3.14.8**, wxPython **4.3.1+ubuntu2404**, Xvfb ve yerel runtime bağımlılıklarıyla çalışıyor; GTK3 `wx.Frame` smoke'u PASS. Kalan test bulguları 26/27 ve WebView 28/29 PASS ile sınırlı değil: bir POSIX path varsayımı, güncel facade'a uymayan dispatch testi, screen-state readback `None` ve tekrarlanan W19 fixture teardown SIGSEGV var (ayrıntı Linux VM devam kaydında).
- [ ] Windows PySide6 test bağımlılığı/opsiyonel bağımlılık çözümünü güncel release preflight runner'ında doğrula.
- [ ] macOS test başarısızlıklarını macOS ortamında gider ve doğrula.
- [ ] SSH, SFTP, terminal, Slurm ve transfer regresyonlarını güncel `develop` üzerinde çalıştır.
- [ ] Güncel `develop` HEAD'de zorunlu test matrisinin tamamının PASS olduğunu kanıtla.

## 2. GUI V2

- [x] Dosya türü ikonlarını wx dosya listelerine uygula ve doğrula.
- [x] wx local ve remote dosya listelerinde zebra satırlarını uygula ve GUI'de doğrula.
- [x] Splitter oranlarını wx içinde sakla ve yeniden açılışta geri yükle; tam shell'de oran ve geometriyi doğrula (`cec26ae3`, devam doğrulama kaydı).
- [x] `1355x929` boyutunda ve minimum local pane genişliğinde wx local-files araç çubuğunun taşmadan görünmesini doğrula (`wx.WrapSizer`, tam resize testinde tüm geometri invariantları 0).
- [ ] Uygulama açılışında doğru bağlantı ekranının gösterildiğini paketlenmiş GUI'de doğrula.
- [ ] Terminal WebView2 yaşam döngüsü ve native crash senaryolarını kapat.
- [ ] Birden fazla ekran çözünürlüğü ile %100/%150/%200 DPI ölçeklerinde doğrula.
- [ ] Paketlenmiş GUI klavye/context-menu kabulü ile gerçek focus traversal, screen reader ve görsel erişilebilirlik denetimlerini tamamla.
- [x] Source GUI startup ve locale geometry kontrolleri güncel `develop` üzerinde `tests/test_w40_gui_acceptance.py` 6/6 PASS; paketlenmiş GUI doğrulaması ayrıca açık.
- [x] wx terminal WebView source lifecycle/regression dosyası izole süreçte 29/29 PASS; karma GUI native-crash ve WER doğrulaması ayrıca açık.
- [x] Kaynak checkout'unda wx keyboard/context smoke grubu 24/24 PASS; bu, erişilebilirlik kabulünün tamamlandığı anlamına gelmez (eksik kanıt yeni devam doğrulama kaydında).

## 3. Bağlantı ve güvenlik

- [ ] Paketlenmiş GUI'de profil ekleme, düzenleme, kopyalama, silme ve kalıcılığı doğrula.
- [ ] Save & Connect akışını tekrarlı koşularda doğrula.
- [ ] SSH key, password, yanlış parola ve iptal senaryolarını doğrula.
- [ ] Host key değişimi, bilinmeyen host ve güvenilmeyen sunucu davranışlarını doğrula.
- [ ] Destek kapsamındaki jump host ve MFA akışlarını doğrula.
- [ ] Bağlantı kopması, yeniden bağlanma ve profil değiştirme akışlarını doğrula.

## 4. Dosya ve transfer sistemi

- [ ] Gerçek ortamda upload/download resume işlemlerini doğrula.
- [ ] Çakışma durumlarında overwrite/skip/rename seçeneklerini doğrula.
- [ ] Kuyrukta iptal, tekrar deneme ve başarısızlık akışlarını doğrula.
- [x] Yerel mock FTP/SFTP integration turunda paralel transfer, ayrı bağlantı/kanal, 48 MiB iptal/resume, overwrite/skip ve SHA-256 içeriği doğrulandı (10 + 4 test PASS); gerçek HPC endpointi ayrıca açık.
- [x] `TransferController` retry sonrası ikinci `start()` çağrısının eski worker canlı görünürken sessizce atlanması düzeltildi; `_done` artık worker kapanış bildirimlerinden sonra set ediliyor.
- [x] CLI test parçalarındaki eksik ortak autouse fixture bağlantıları eklendi; CLI erişim kapısı artık testleri yanlışlıkla erken kesmiyor. CLI/W18 hedefli grup 90/90 PASS.
- [x] W15/W21/W28/W37/W40 testlerindeki gerçek kullanılmayan import/değişkenler temizlendi; W37 ve W40 büyük test dosyaları GUI/contract sorumluluklarına göre bölündü.
- [x] W15 fresh-user env testi gerçek helper modülüne yöneltildi; W40 testleri wx shell facade'ı yerine menü sahibi modülü denetliyor ve açılışta Connection sekmesi politikasını doğruluyor.
- [x] W15/W37/W40 hedefli grupları sırasıyla 11/11, 31/31 ve 25/25 PASS; W21/W28 grubu 31/31 PASS; CLI/W18 grubu 90/90 PASS; W11/W13/W32/W35/W38/W43 ve wx thread-affinity grubu 84/84 PASS. Toplam **272 hedefli test PASS**.
- [x] Kaynak mimari doğrulayıcısı değişen 38 kaynak/test dosyasında PASS; 500 satır üstü dosya yok, bağımlılık çevrimi yok. 11 dosya 400–500 satırlık uyarı bölgesinde.
- [ ] Linux guest `Ubuntu-Test` başlatıldı; canlı durum, strict SSH host-key ve `ubuntu-doctor` PASS. Ancak guest'te Python 3.12.3 var, `pip`, wxPython, `wx-config` ve `pkg-config` yok; `test` hesabında parolasız sudo yok. Linux wxPython/GTK doğrulaması **BLOCKED_ENV**.
- [ ] Gerçek HPC endpointinde büyük dosya, Unicode dosya adı ve paralel transferleri doğrula; yerel mock/stress kanıtı ayrı kaydedildi.
- [ ] GUI üzerinden SHA-256 doğrulamasını doğrula.
- [ ] SFTP dizin gezinmesi ve yetki hatalarını doğrula.

## 5. Slurm, Editor ve terminal

- [ ] Güncel paket üzerinde Save, Submit ve Save + Submit akışlarını doğrula.
- [ ] PENDING/RUNNING/COMPLETED/FAILED/CANCELLED durumlarını doğrula.
- [ ] Job output, stdout/stderr ve canlı takip akışlarını doğrula.
- [ ] Terminal resize, Unicode, paste, uzun çıktı ve reconnect senaryolarını tamamla.
- [ ] Eski oturumlara ait geçersiz sonuçların yeni oturuma uygulanmadığını kanıtla.

## 6. HPC sağlayıcıları

| Sağlayıcı | Kalan iş |
| --- | --- |
| TRUBA | Registry güncel; gerçek kullanım ve güncel GUI doğrulaması açık. |
| Perlmutter | Resmî registry'ye yayımlama ve doğrulama. |
| Frontera | Resmî registry'ye yayımlama ve doğrulama. |
| Stampede3 | Resmî registry'ye yayımlama ve doğrulama. |
| Delta | Resmî registry'ye yayımlama ve doğrulama. |
| LUMI | Yerel kanıtlardan sonra resmî yayımlama ve doğrulama. |
| Leonardo | Yerel kanıtlardan sonra resmî yayımlama ve doğrulama. |
| Setonix | Yerel kanıtlardan sonra resmî yayımlama ve doğrulama. |
| JUWELS | Yerel `1.0.0` paketi mevcut ve registry doğrulamasından geçiyor; resmi yayımlama ve gerçek kullanım doğrulaması açık. |

- [ ] Tüm sağlayıcılarda kurulum, etkinleştirme, devre dışı bırakma, güncelleme ve kaldırmayı doğrula.
- [x] Yerel plugin checkout'unda registry şeması, manifest/payload hash'leri, sürüm uyumluluğu ve güvenli yol/rol kontrolleri doğrulandı (`validate_registry.py` + 188 test).
- [ ] Resmi yayımlanmış registry kimliğinde provider paketlerini ve uygulama uyumluluğunu tekrar doğrula.

## 7. V2 acceptance

- [ ] Güncel `develop` HEAD'den yeni immutable Candidate üret.
- [ ] EXE, ZIP, kaynak commit ve manifest SHA-256 kimliklerini eşleştir.
- [ ] GUI aksiyon envanterini güncel paketten yeniden çıkar.
- [ ] Desteklenen her aksiyonu paketlenmiş GUI'de çalıştırıp sonuç/readback kanıtı üret.
- [ ] Açıklanmamış `FAIL`, `NOT_RUN` ve `BLOCKED` sayısını sıfıra indir.
- [ ] LOCAL_REAL testlerini tamamla.
- [ ] Native crash, WER ve memory/lifecycle kampanyasını tamamla.
- [ ] İki bağımsız audit katmanından PASS al.

## 8. Nihai release

- [ ] Windows paketini güncel kaynak kimliğine bağlı olarak doğrula.
- [ ] Linux ve macOS release paketlerini doğrula.
- [ ] Eski kullanıcı profili ve ayarları için migration testlerini tamamla.
- [ ] Güncelleme ve rollback senaryolarını doğrula.
- [ ] Release manifest, SBOM ve güvenlik kanıtlarını üret.
- [ ] V2 final freeze yap ve release gate PASS al.
- [ ] Yayınlama için ayrıca açık onay al.

## Bilinen dar kapsamlı tamamlanmalar

- [x] Önceki istekte ele alınan 46 test hatasına yönelik düzeltmeler `develop`'a pushlandı. Bu, 413 Ruff bulgusunun veya zorunlu test matrisinin tamamlandığını göstermez.
- [x] Release workflow manuel tetikleme politikasında bırakıldı.
- [x] Eski Candidate'larda bazı Save + Submit, terminal, job output ve profil bağlantı akışları geçti; bunlar güncel `develop` kabulü değildir.
- [x] TRUBA 1.5.0 resmî provider registry'de yayımlanmış durumda.

## Şimdi yürütülecek sıra

1. W55/W16: takip dalı CI PASS sonucunu al; aynı commit'ten Windows11 guest immutable onedir candidate üretip hash/20-check runtime JSON/exit code/WER ve temiz kapanışı tekrar doğrula. Sorun sürerse lifecycle callback kök nedenini ve native stack'i ayrı düzelt.
2. W19 Ubuntu: WebKitGTK CSP `RunScript` readback ve JavaScriptCore SIGSEGV için minimal native repro/stack ile ürün-tarafı düzeltme ve GUI tekrar testini tamamla.
3. Windows packaged normal başlangıç Connection UIA runner'ını onar ve aynı Candidate üzerinde gerçek açılış doğrula.
4. Bölünmüş GUI ve SSH/SFTP/Slurm/transfer suite, LOCAL_REAL, %100/%150/%200 DPI, erişilebilirlik, Linux/macOS paketleri için güncel HEAD test matrisi tamamla.
5. Immutable artifact/SHA/SBOM, iki bağımsız audit, freeze/release gate PASS ve açık yayın izni tamamlanmadan V2 COMPLETED deme.
