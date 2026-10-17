# HPC Client GUI V2 — Final Noninteractive Acceptance Report

**Tarih:** 2026-10-17 (Europe/Istanbul)
**Durum:** `V2_BLOCKED_EXTERNAL`
**Çalışma branch'i:** `codex/v2-noninteractive-completion`
**Kaynak HEAD (test sırasında):** `8345c82526635b485afd42a3678a1f3c59b222f1`
**Acceptance worktree manifest SHA-256:** `321d5bdf25fe8a3e2359c223b27e1a928968ab67973f69342087766a92f509f3`

## Yönetici özeti

Windows noninteractive broad regression, Windows 11 guest Candidate testleri, Linux `.deb` extraction/package smoke, terminal/WebKitGTK regresyonları, mimari/lint kontrolleri ve iki ayrı audit tamamlandı. Son Windows broad koşusu **3052 PASS, 0 FAIL, 2 SKIP, 65 DESELECTED ve 29 subtest PASS** verdi; release preflight exit code 0 ile tamamlandı. İki platform koşullu skip Ubuntu'da ayrıca 2/2 PASS oldu.

V2 henüz `ACCEPTED` değil. Tek zorunlu otomatik kapı olan Ubuntu sistem paket yöneticisi üzerinden install → upgrade → rollback → cleanup, mevcut Ubuntu-Test VM'de yetkili root erişimi bulunmadığından çalıştırılamadı. Rootless isolated dpkg install/status/remove ve `.deb` smoke başarıları bu ayrıcalıklı migration testinin yerine sayılmadı. Sonuç `V2_BLOCKED_EXTERNAL` olarak tutuldu.

## Git ve kaynak kimliği

- Repository worktree: `D:\Projeler\.tmp\worktrees\hpc-v2-noninteractive-completion`
- Branch: `codex/v2-noninteractive-completion`
- Test edilen HEAD: `8345c82526635b485afd42a3678a1f3c59b222f1`
- Önceki yerel commitler: `d31dcb71`, `7b626d29`, `8345c825`
- Ana checkout `D:\Projeler\hpc-client-gui` üzerindeki 34 kullanıcı değişikliği korunmuştur.
- Windows Candidate ve Linux `.deb`, build-time source-tree manifest SHA `80351095cd0a0a69a153bc6b42bf0bdcaacbf00cb9dd611d4d8b60176cab2fb2` ile eşleştirilmiştir. Son acceptance worktree'nin ayrı manifest hash'i yukarıda verilmiştir. Candidate/paket üretiminden sonra release test harness'ında ve test dosyalarında değişiklikler olmuştur; Candidate yeni dirty worktree'den üretilmiş gibi gösterilmemiştir. Ürün kaynakları build snapshot'ından sonra değişmemiştir.
- Çalışma ağacında 18 tracked değişiklik ve 10 yeni dosya vardır. Bunlar V2 modülerleştirme, release-test izolasyonu, regression düzeltmeleri ve TODO/evidence kayıtlarıdır.

## Windows broad regression

Canonical komut `python scripts/release_test_suite.py` son HEAD üzerinde tamamlandı:

| Sonuç | Adet |
|---|---:|
| PASS | 3052 |
| FAIL | 0 |
| SKIP | 2 |
| DESELECTED | 65 |
| Subtest PASS | 29 |
| Süre | 1022.09 s |
| Exit code | 0 |

Runner `all release preflight gates passed` satırıyla tamamlandı. İki skip Windows ortamına özel olmayan POSIX testleridir; Ubuntu'da karşılık gelen testler 2/2 PASS verdi. 65 deselected test Windows broad tanımının dışındadır; platform/ayrı kabul grupları ilgili hedefli kampanyalarda çalıştırıldı.

Önceki W37 `os.replace` WinError 5 geniş koşuda tekrarlanmadı. Kök neden testin atomic replace sırasında config dosyasını okuma yarışıydı. Testin bekleme/senkronizasyonu düzeltildi; production koda retry veya sleep eklenmedi. W37 hedefli test dosyası 8/8 PASS.

W19 GUI ve shell lifecycle testleri ayrı pytest process'lerinde çalıştırıldı; testler skip edilmedi. Native W19 GUI 8/8 ve shell 5/5 PASS. P0 shell stress, production ile aynı deferred WebView creation yolunu kullanarak tamamlandı.

## Windows 11 Candidate ve guest

- Immutable onedir Candidate: `.tmp/candidates/windows-v2-final-current/hpc-client-gui/hpc-client-gui.exe`
- Candidate SHA-256: `77a82b273c97b0d6168fdd718509032a1f49d49f2e5a52e38582c5607c4f9216`
- Host packaged smoke: 21/21 PASS.
- Canonical Windows 11 guest packaged smoke: 21/21 PASS; guest ile host Candidate hash'i eşleşti.
- UIA gerçek `HPC Client GUI 1.5.9` ana penceresini açtı, 22 görünür kontrol buldu, gerekli bağlantı kontrollerini doğruladı ve normal kapatma ile exit 0 aldı.
- Guest WER sorgusu başarılı; test penceresinde Candidate ile ilişkili crash kaydı veya kalan Candidate process'i yoktu.
- `clean_shutdown` ve `reconnect_fresh_identity` packaged smoke kontrolleri PASS. Reconnect sonucu loopback packaged harness kapsamındadır; gerçek HPC endpoint reconnect'i olarak sunulmamıştır.

Runner timeout ile process öldürülmesi clean-shutdown kanıtı olarak kullanılmadı.

## Ubuntu 24.04 ve Linux paketleme

Linux Candidate `.deb`:

- Paket: `hpc-client-gui` 1.5.9, amd64
- SHA-256: `1eaeb425b8a52df14b33abc60960f686946142e001a9272d51ee9383d5c46892`
- Paket içindeki executable SHA-256: `309dd25c9fb3c61c28afdc2b367ee84fa463921c2e8e9e048d504b807dcb9e95`
- Metadata, dependency ve file listing doğrulandı.
- Paketten çıkarılan gerçek executable ile CLI version ve GUI packaged smoke 21/21 PASS.
- Rootless isolated dpkg install/status/remove PASS.

Gerçek system package install/upgrade/rollback/cleanup yapılmadı. Ubuntu-Test'te `sudo -n` parola istiyor, user namespace `Operation not permitted`, dpkg database kullanıcı tarafından yazılamıyor ve Docker/Podman/LXC/Proot/debootstrap/mmdebstrap/QEMU/virt-install araçları bulunmuyor. Canonical Hyper-V/SSH/doctor discovery alternatif yetkili disposable root ortamı bulmadı. Güvenlik mekanizmaları aşılmadı, credential tahmin edilmedi ve VM sistemi değiştirilmedi. Bu nedenle bu gate `BLOCKED_EXTERNAL` durumundadır.

V2 baseline Linux için AppImage veya `.deb` kabul ediyor; Flatpak optional. `.deb` doğrulandığından AppImage ve Flatpak zorunlu kapı değildir.

## Terminal, güvenlik ve native lifecycle

- WebKitGTK terminal suite: 51/51 PASS.
- W19 native lifecycle: 20/20 PASS; GDB teardown probe 12 create/write/close çevriminden sonra normal exit verdi, SIGSEGV olmadı.
- Fragment queue hedefli grup: 10/10 PASS; 2 MiB / 4096-item sınırı, ANSI/Unicode, sıra/ACK kaybı, timeout, bozuk mesaj, reconnect ve stale callback davranışları kapsandı.
- Terminal hassas içeriğinin URL/history üzerinden sızmaması test edildi.
- CSP korundu: `script-src 'self'` ve `connect-src 'none'`; `unsafe-eval`, CDN veya güvensiz ağ yolu eklenmedi.
- Sentetik queue-drain ölçümü 20 × 624,000 byte için Windows 38.06 MiB/s, Ubuntu 62.35 MiB/s gösterdi; tepe buffered payload 652032 byte oldu. Bu ölçüm gerçek cluster ağ throughput'u değildir.

## W04 supplied evidence

`artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md` canonical path'te mevcuttur. SHA-256 `6c41e085a1ecaeaedf6261316ea483cccaafc9b3dbea2ba71bda313fc56d6ed5`. W04 hedefli 28 test ve GUI probe PASS. Eksik görünen evidence repository tarafından üretilebilir/sağlanabilir durumdaydı; path/availability zinciri düzeltilerek W04 çözüldü.

## İki bağımsız audit

**Audit A — Implementation/execution:** PASS. Kaynak ve test sahipliği, strict CSP, queue sınırları, native teardown, release runner, broad suite ham çıktısı, Ubuntu terminal/native kanıtı, Candidate ve paketleme sınırları yeniden incelendi. Ayrıcalıklı Linux migration'ın yapılmadığı açıkça korundu.

**Audit B — Evidence/integrity:** PASS_WITH_EXTERNAL_BLOCKER. EXE, `.deb` ve W04 SHA'ları diskten tekrar hesaplandı; host/guest Candidate eşleşmesi, guest UIA/WER sonucu, broad exit/summary/skip kayıtları ve build-time/current-worktree manifest ayrımı çapraz kontrol edildi. Rootless dpkg kanıtı system upgrade/rollback diye sunulmadı.

Evidence dosyaları `.tmp/evidence-v2-final-closure/` altındadır: `audit-a-implementation.md`, `audit-b-evidence.md`, `audit-b-verification.json`, `acceptance-source-identity-final.json`.

## Acceptance kararı ve kalan iş

**Final state: `V2_BLOCKED_EXTERNAL`.** Uygulanabilir repository-owned otomatik işler tamamlandı. `V2_ACCEPTED` için yetkili disposable/root-capable Ubuntu ortamında gerçek package install → upgrade → rollback → cleanup çalıştırılmalı; ardından Audit A ve Audit B bu kanıtı kontrol ederek güncellenmelidir. Ortam hazırsa kalan test ve kanıt çalışması yaklaşık 1–2 saat sürer; bu tahmin provisioning süresini kapsamaz.

İnteraktif manuel kullanıcı kabulü ve yayınlama bu raporun kapsamı dışındadır.

## Push / commit kaydı

Bu rapor yazıldığı sırada çalışma dalı upstream'den üç commit ilerideydi ve V2 değişiklikleri worktree'de commit edilmemişti. İstek üzerine rapor ve çalışma değişiklikleri yerel commit'e alınarak normal fast-forward push hedeflenecektir. Push öncesinde origin durumu yeniden fetch edilip kontrol edilecektir; remote branch ilerlemiş veya fast-forward mümkün değilse push durdurulacaktır. Force push, PR merge ve release publication yapılmayacaktır.
