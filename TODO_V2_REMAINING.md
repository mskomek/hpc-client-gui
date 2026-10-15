# HPC Client GUI V2 — Kalan İşler

**Audit tarihi:** 2026-10-15  
**Başlangıç HEAD:** `develop` `b80a06e419fbe77f485b9c5924f1e86c764201f0`
**Amaç:** V2 tamamlanması için kalan kod, doğrulama, provider, acceptance ve release işlerini tek yerde izlemek.

## Durum ve kanıt kuralları

- Bu dosya çalışma TODO'sudur; release kabul belgesi değildir.
- Bir madde yalnızca kod mevcut diye tamamlanmaz. Kanıt, test edilen tam commit ve mümkünse paket SHA-256 ile eşleşmelidir.
- Önceki Candidate 6/7/8/9 sonuçları kendi commit ve paketlerine aittir; güncel `develop` için kabul kanıtı sayılmaz.
- GitHub CI run `38688191566`, `4a7170ad` üzerinde 15 Ekim'de aynı `ruff check src scripts tests` komutuyla **413** bulgu kaydetti; temiz detached worktree'de Ruff 0.16.8 ile bu sonuç yeniden üretildi. Sonraki temiz `53bc413d` HEAD'inde aynı Ruff sürümü ve komut **245** verdi; geniş `ruff check .` sayısı 252. Aradaki 81 dosyalık değişiklikte F401 123→1, F841 25→2 ve E402 20→0 oldu; dolayısıyla tarihsel 413 farkı commit içeriğindeki değişikliklerle açıklanıyor, araç sürümü/kapsam farkıyla değil. `src/` altında güncel Ruff bulgusu yok; kalan 245 bulgu validator/test yüzeylerinde. Mevcut `develop`'da `.github/workflows/ci.yml` silinmiş olduğundan `a759aebc` push'u için yeni CI çalışması oluşmadı.
- Bu çalışmaya başlamadan önce checkout'ta var olan kullanıcı değişiklikleri korunur.

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
- [ ] Splitter kalıcılığı açık: varsayılan wx oranı 960/1200/1600 genişliklerinde okundu (2/2 PASS), ancak kullanıcı oranı kaydedilip açılışta yüklenmiyor. Python 3.14 tam shell testi 400 resize ve 2.800 tab seçimini çalıştırdı; FAIL: 553 sıfır geometri ve 546 clipping. Görünürlük tanısında 474/468 ölçüm gizli sekme kontrollerinden (`IsShown()` kullanımı), 79/78 görünür kontrollerden geldi. İlk görünür kusur `1355x929` boyutunda Files sekmesindeki yerel `btn_refresh` genişliğinin `0` olması: 166 px navigation sidebar ve 300 px splitter minimumu, beş düğmeli toolbar'a sığmıyor. Test ölçümü `IsShownOnScreen()` ile düzeltilmeli ve toolbar dar genişliklerde yeniden düzenlenmeli; splitter kalıcılığı ayrıca doğrulanmalı.
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
- [ ] Kalan 245 Ruff bulgusunu kapat; current source `src/` temiz, bulgular validator ve test yüzeyinde.
- [ ] `develop`'da silinmiş `.github/workflows/ci.yml` gate'inin geri çalıştırılabilirliğini doğrula; `a759aebc` için GitHub CI run yok.
- [ ] Uygulama/test/script kaynaklarındaki gerçek Ruff hatalarını, dosya sorumluluklarını ve 500 satır mimari sınırını koruyarak düzelt.
- [ ] Linux wxPython/GTK3 kurulum ve test ortamını düzelt; gerçek Linux ortamında doğrula. Mevcut Ubuntu-Test ölçümü **BLOCKED_ENV**: Python 3.12.3; pip/wxPython/wx-config/pkg-config eksik; sudo parola istiyor.
- [ ] Windows PySide6 test bağımlılığı/opsiyonel bağımlılık çözümünü güncel release preflight runner'ında doğrula.
- [ ] macOS test başarısızlıklarını macOS ortamında gider ve doğrula.
- [ ] SSH, SFTP, terminal, Slurm ve transfer regresyonlarını güncel `develop` üzerinde çalıştır.
- [ ] Güncel `develop` HEAD'de zorunlu test matrisinin tamamının PASS olduğunu kanıtla.

## 2. GUI V2

- [x] Dosya türü ikonlarını wx dosya listelerine uygula ve doğrula.
- [x] wx local ve remote dosya listelerinde zebra satırlarını uygula ve GUI'de doğrula.
- [ ] Splitter oranlarını wx içinde sakla ve yeniden açılışta geri yükle; tam shell'de oran ve geometriyi doğrula.
- [ ] Uygulama açılışında doğru bağlantı ekranının gösterildiğini paketlenmiş GUI'de doğrula.
- [ ] Terminal WebView2 yaşam döngüsü ve native crash senaryolarını kapat.
- [ ] Birden fazla ekran çözünürlüğü ile %100/%150/%200 DPI ölçeklerinde doğrula.
- [ ] Klavye kısayolları, context menüler ve erişilebilirlik denetimlerini tamamla.

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
- [x] `TransferController` retry sonrası ikinci `start()` çağrısının eski worker canlı görünürken sessizce atlanması düzeltildi; `_done` artık worker kapanış bildirimlerinden sonra set ediliyor.
- [x] CLI test parçalarındaki eksik ortak autouse fixture bağlantıları eklendi; CLI erişim kapısı artık testleri yanlışlıkla erken kesmiyor. CLI/W18 hedefli grup 90/90 PASS.
- [x] W15/W21/W28/W37/W40 testlerindeki gerçek kullanılmayan import/değişkenler temizlendi; W37 ve W40 büyük test dosyaları GUI/contract sorumluluklarına göre bölündü.
- [x] W15 fresh-user env testi gerçek helper modülüne yöneltildi; W40 testleri wx shell facade'ı yerine menü sahibi modülü denetliyor ve açılışta Connection sekmesi politikasını doğruluyor.
- [x] W15/W37/W40 hedefli grupları sırasıyla 11/11, 31/31 ve 25/25 PASS; W21/W28 grubu 31/31 PASS; CLI/W18 grubu 90/90 PASS; W11/W13/W32/W35/W38/W43 ve wx thread-affinity grubu 84/84 PASS. Toplam **272 hedefli test PASS**.
- [x] Kaynak mimari doğrulayıcısı değişen 38 kaynak/test dosyasında PASS; 500 satır üstü dosya yok, bağımlılık çevrimi yok. 11 dosya 400–500 satırlık uyarı bölgesinde.
- [ ] Linux guest `Ubuntu-Test` başlatıldı; canlı durum, strict SSH host-key ve `ubuntu-doctor` PASS. Ancak guest'te Python 3.12.3 var, `pip`, wxPython, `wx-config` ve `pkg-config` yok; `test` hesabında parolasız sudo yok. Linux wxPython/GTK doğrulaması **BLOCKED_ENV**.
- [ ] Büyük dosya, Unicode dosya adı ve paralel transferleri doğrula.
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
| JUWELS | Eksik provider paketini oluşturma, yayımlama ve doğrulama. |

- [ ] Tüm sağlayıcılarda kurulum, etkinleştirme, devre dışı bırakma, güncelleme ve kaldırmayı doğrula.
- [ ] Registry güvenliği, şeması, hash ve sürüm uyumluluğu kontrollerini tamamla.

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

1. İzlenen kaynak dosyalarına göre Ruff bulgularını ayrıştır ve gerçek CI kapsamını belirle.
2. Uygulama kodu ve testlerindeki güvenli, anlamlı lint düzeltmelerinden başla.
3. Platform ve GUI doğrulamalarını uygun Windows/Linux/macOS ortamlarında, her sonucu tam commit ve artifact kimliğine bağlayarak ilerlet.
