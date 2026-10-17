# HPC Client GUI V2 — Final Noninteractive Acceptance Report

**Tarih:** 2026-10-17 (Europe/Istanbul)
**Final state:** `V2_ACCEPTED` — noninteractive acceptance scope
**Branch:** `codex/v2-noninteractive-completion`
**Test edilen ürün/source HEAD:** `e41cb02613b6bad32c41480a88308750bd05ce15`
**Worktree:** `D:\Projeler\.tmp\worktrees\hpc-v2-noninteractive-completion`

## Özet

Ubuntu-Test üzerinde yetkili sudo erişimi verildikten sonra daha önce açık kalan Linux package-manager kapısı tamamlandı: gerçek `.deb` install, upgrade, rollback, kurulu paketin GUI smoke'u ve purge/cleanup yürütüldü. Kurulu paket GUI smoke'u **21/21 PASS** verdi. Son salt okunur VM kontrolü paketlerin, payload'ın, test geçici dizininin ve uygulama prosesinin kalmadığını; geçici sudoers drop-in'in kaldırıldığını ve `dpkg --audit` sonucunun temiz olduğunu doğruladı.

Windows broad suite **3052 PASS / 0 FAIL / 2 SKIP / 65 DESELECTED / 29 subtest PASS** ile exit 0 tamamlandı. Windows 11 guest Candidate, UIA, reconnect, WER ve clean shutdown kanıtları mevcut. W04 supplied evidence repository'nin canonical path'inde bulundu ve doğrulandı. Ayrı implementation ve evidence-integrity auditleri PASS verdi. Bu rapor yalnız interaktif kullanıcı kabulünü ve gerçek HPC endpoint credential'ı gerektiren akışları kapsam dışında bırakır.

## Final acceptance matrisi

| Alan | Başlangıç | Son durum | Kanıt | Kalan iş |
|---|---|---|---|---|
| Git / user changes | Ana checkout ayrıydı; önceki gözlemde 34 status girdisi vardı. | Test edilen HEAD `e41cb026`; ürün kodu değişmedi. Son salt-okunur kontrolde ana checkout'ta 35 status girdisi vardı; hiçbirine dokunulmadı. | `git status`, branch/log; `.tmp/evidence-v2-final-closure/closure-final-identity.json`. | — |
| Windows broad | Önceki broad kampanyada W37 transient failure vardı; izole testler geçiyordu. | **3052 PASS, 0 FAIL, 2 SKIP, 65 DESELECTED, 29 subtest PASS; exit 0; 1022.09 s.** | `.tmp/evidence-v2-final-closure/release-suite-zero-fail.log`, `.log.exit`, `release-suite-zero-fail-skips.jsonl`; release preflight PASS. POSIX skip'leri Ubuntu'da 2/2 PASS. | 65 deselected test broad kapsamı dışında; interaktif/manual akışlar ayrı. |
| W37 | Atomic replace sırasında Windows `WinError 5` broad suite'te görülmüştü. | **PASS**; testte config read / replace yarışı giderildi; production retry/sleep eklenmedi. W37 file 8/8 ve broad 0 FAIL. | `w37-race-fix-targeted.log` ve broad log. | — |
| Architecture / lint | Önceki audit kayıtları eski SHA'lara bağlıydı. | Canonical architecture PASS: 25 source, 0 over-limit, 0 dependency violation; Ruff PASS; `git diff --check` PASS. | `.tmp/evidence-v2-final-closure/architecture-final-acceptance-rerun.json`, Ruff ve diff-check logları. | 400–500 LOC warning'leri ve kapsam dışı legacy borç ayrı kalır. |
| Windows Candidate | Immutable onedir Candidate hazırlanmıştı. | **Host/guest smoke 21/21 PASS.** Candidate SHA-256 `77a82b273c97b0d6168fdd718509032a1f49d49f2e5a52e38582c5607c4f9216`. | `.tmp/evidence-v2-final-closure/windows-candidate-manifest-final.json`; hash diskten yeniden hesaplandı. | İmzalama/yayın kapsam dışı. |
| Windows 11 guest GUI/UIA | Guest Candidate hash eşleşmesi vardı; GUI/UIA/WER kapanış kanıtları tamamlanmalıydı. | GUI startup ve UIA PASS; 22 visible control; normal Window close exit 0; host/guest Candidate SHA eşleşti. | `.tmp/evidence-windows-v2-final/windows11-uia-final-current-retry.json`; canonical runner kanıtı. | Manuel kullanıcı kabulü kapsam dışı. |
| Reconnect | Packaged loopback reconnect doğrulaması vardı. | `reconnect_fresh_identity` PASS, yeni session identity doğrulandı. | Windows ve Ubuntu packaged smoke kayıtları. | Bu, gerçek HPC endpoint reconnect testi değildir. |
| WER | Crash/WER sorgusu yapılmıştı. | Test aralığında Candidate ile ilişkili WER kaydı veya kalan Candidate process yok. | `.tmp/evidence-windows-v2-final/windows11-wer-final-current.json`. | — |
| Guest clean shutdown | Kapanış yolu ayrıca kanıtlanmalıydı. | UIA normal pencere kapatma exit 0; packaged `clean_shutdown` PASS; timeout kill kullanılmadı. | UIA evidence ve 21/21 guest smoke. | — |
| Linux `.deb` | Rootless extract/smoke geçiyordu; install migration eksikti. | **PASS.** `hpc-client-gui` 1.5.9 amd64; package SHA-256 `1eaeb425b8a52df14b33abc60960f686946142e001a9272d51ee9383d5c46892`; executable SHA-256 `309dd25c9fb3c61c28afdc2b367ee84fa463921c2e8e9e048d504b807dcb9e95`. | `.tmp/evidence-v2-final-closure/linux-deb-manifest-final.json`, migration JSON ve apt history. | AppImage, baseline `.deb` alternatifi olduğu için zorunlu değil; Flatpak optional. |
| Install / upgrade / rollback | Yetkili sudo eksikti; external blocker olarak sınıflandırılmıştı. | **PASS:** Candidate install → version-only test package upgrade → downgrade/rollback → installed-path GUI smoke → purge. Test upgrade artifact'i release Candidate değildir; payload hash Candidate ile aynıydı. | `ubuntu-package-apt-history-final.log`; `ubuntu-system-package-migration.json`; kurulu paket GUI smoke özeti. | — |
| Linux installed GUI smoke | Önceden rootless packaged smoke vardı. | Gerçek kurulu `/usr/lib/hpc-client-gui/hpc-client-gui` ile **21/21 PASS**, `clean_shutdown` PASS, exit 0. | `ubuntu-installed-package-smoke-summary.json`; terminal içeriği kayda alınmadı. | — |
| Linux cleanup / privilege | Test sonrası privileged cleanup bekleniyordu. | Uygulama/dependency purge edildi; package ve payload yolları, temp root, process ve sudoers drop-in yok; `sudo -n` devre dışı; `dpkg --audit` clean. | `ubuntu-cleanup-recheck.json`, `ubuntu-package-cleanup-final.json`; apt history purge kaydı. | — |
| Terminal security/performance | CSP, fragment IPC ve native lifecycle önceki kanıtlarla doğrulanmıştı. | WebKitGTK 51/51; W19 native lifecycle 20/20; queue 10/10; GDB native teardown normal exit. 2 MiB/4096 item cap, ACK/timeout/reconnect/stale callback/privacy kontrolleri PASS. CSP `script-src 'self'`, `connect-src 'none'` korundu. | Önceki `.tmp/evidence-v2-final-closure/` terminal/native kayıtları. | Throughput sentetik queue-drain ölçümüdür; gerçek cluster ağ soak'u değildir. |
| W04 | Supplied evidence bulunamadığı için açık görünüyordu. | **RESOLVED:** canonical support freeze mevcut; SHA-256 `6c41e085a1ecaeaedf6261316ea483cccaafc9b3dbea2ba71bda313fc56d6ed5`; 28 hedefli test ve probe PASS. | `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md`; W04 test kayıtları. | — |
| Audit A | Ubuntu package migration blokluydu. | **PASS** — implementasyon, execution, kaynak kapsamı ve gerçek apt/GUI/cleanup sonucu kontrol edildi. | `.tmp/evidence-v2-final-closure/audit-a-implementation.md`. | — |
| Audit B | Evidence integrity ayrı kontrol gerektiriyordu. | **PASS** — artifact SHA'ları, broad exit/summary, guest identity, apt işlem zinciri, smoke ve cleanup kanıtı bağımsız kontrol edildi. | `.tmp/evidence-v2-final-closure/audit-b-evidence.md`, `audit-b-verification.json`. | — |
| V2 acceptance | Linux system install/upgrade/rollback external blocker idi. | **`V2_ACCEPTED` — noninteractive scope.** Bütün zorunlu noninteractive kapılar PASS. | Bu rapor ve audit kayıtları. | Manuel kullanıcı acceptance ve gerçek HPC endpoint credential'ı gerektiren testler kapsam dışı. |

## Ubuntu package migration ayrıntısı

Ubuntu-Test, Ubuntu 24.04'tür. Gerçek Candidate `.deb` kuruldu; apt history install işlemini kaydediyor. Upgrade/rollback doğrulaması için yalnız DEBIAN control içindeki Version alanı `1.5.9+v2acceptance1` yapılan geçici bir paket oluşturuldu; extracted binary Candidate ile aynı SHA-256'ya sahipti. Apt önce upgrade, sonra `--allow-downgrades` ile 1.5.9'a rollback yaptı. Ardından gerçek kurulu binary ile otomatik GUI smoke 21/21 PASS oldu ve `clean_shutdown` PASS verdi. Paket ve test eklenen `libxcb-xinerama0` purge edildi. Son salt-okunur probe bütün test kalıntılarının kaldırıldığını doğruladı. Geçici sudoers kuralı da kaldırılmıştır; Ubuntu VM açık bırakılmış ve VM konfigürasyonu değiştirilmemiştir.

## Artifact ve source identity

- **Test edilen ürün/source HEAD:** `e41cb02613b6bad32c41480a88308750bd05ce15`.
- **Windows Candidate SHA-256:** `77a82b273c97b0d6168fdd718509032a1f49d49f2e5a52e38582c5607c4f9216`.
- **Linux `.deb` SHA-256:** `1eaeb425b8a52df14b33abc60960f686946142e001a9272d51ee9383d5c46892`.
- **Linux executable payload SHA-256:** `309dd25c9fb3c61c28afdc2b367ee84fa463921c2e8e9e048d504b807dcb9e95`.
- Candidate ve `.deb` build-tree manifest SHA-256: `80351095cd0a0a69a153bc6b42bf0bdcaacbf00cb9dd611d4d8b60176cab2fb2`. Bunlar daha sonra değişen test/TODO acceptance tree'den yeniden üretilmiş gibi sunulmuyor; product build girdileri ayrıca kayıtlıdır.
- W04 SHA-256: `6c41e085a1ecaeaedf6261316ea483cccaafc9b3dbea2ba71bda313fc56d6ed5`.

## Yerel commitler ve GitHub işlemleri

Mevcut ürün/test commitleri: `32c174c`, `0e3e555`, `b76aa72`, `d31dcb71`, `7b626d29`, `8345c825`, `e41cb026`. Final rapor ve TODO ayrı yerel dokümantasyon commitleri olarak kaydedilmiştir. GitHub'a push, PR merge veya release yapılmamıştır. Ana checkout'taki 35 status girdisi değiştirilmeden bırakılmıştır.
