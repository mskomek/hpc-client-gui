# HPC Client GUI Wiki

> English: [[Home]]

HPC Client GUI, Slurm tabanlı HPC kümelerinde SSH, Slurm ve isteğe bağlı X11
iş akışları için bağımsız, **istemci tarafında** çalışan bir masaüstü
uygulamasıdır. Bağlanır, dosyaları gezip aktarır, zamanlayıcı işlerini izler ve
uzak grafiksel uygulamaları başlatır. Uzak HPC altyapısını **değiştirmez**.

## Bu wiki nasıl çalışır

Bu wiki, [ana depodaki](https://github.com/mskomek/hpc-client-gui)
`docs/wiki/` dizininden **üretilir** ve `scripts/sync_wiki.py` ile aynalanır.
Sayfaları github.com üzerinde düzenlemeyin — bu düzenlemeler bir sonraki
eşitlemede üzerine yazılır. Bunun yerine `docs/wiki/` için bir pull request
açın.

Ürün davranışı için kanonik kaynak `src/hpc_gui/docs/` (`HELP_en.md`,
`CLI_GUIDE_en.md`, `ARCHITECTURE.md`, `CHANGELOG.md`) ve depo kökündeki
`README.md` dosyasıdır. Buradaki sayfalar o içeriği özetler ve birbirine
bağlar.

## Buradan başlayın

- [[Hızlı Başlangıç|Quick-Start-TR]] — kurun, bağlanın ve ilk işinizi
  gönderin.
- [[Uyumluluk ve Destek Matrisi|Compatibility-and-Support-Matrix-TR]] — hangi
  platformda neyin desteklendiği.
- [[Küme Gereksinimleri|Cluster-Requirements-TR]] — kümemde çalışır mı?
- [[SSS|FAQ-TR]] — belirtiye göre gruplanmış kısa yanıtlar.

## Kurulum

[[Windows|Installation-Windows-TR]] · [[Linux|Installation-Linux-TR]] · [[Kaynaktan|Installation-From-Source-TR]] · [[Yükseltme ve kaldırma|Upgrading-and-Uninstalling-TR]]

## Uygulamayı kullanma

[[Bağlantı ve Profiller|Connecting-and-Profiles-TR]] · [[Uzak Dosya Yöneticisi|Remote-File-Manager-TR]] · [[Dosya Aktarımları|File-Transfers-TR]] · [[Slurm İşleri|Slurm-Jobs-TR]] · [[İş Çıktıları|Job-Outputs-TR]] · [[Betik Düzenleyici|Script-Editor-TR]] · [[Terminal ve Uzak Komutlar|Terminal-and-Remote-Commands-TR]] · [[X11 Yönlendirme|X11-Forwarding-TR]] · [[Eklentiler|Plugins-TR]] · [[Ayarlar Referansı|Settings-Reference-TR]] · [[Arayüz Dili ve i18n|Interface-Language-and-i18n-TR]]

## Otomasyon

[[CLI Kılavuzu|CLI-Guide-TR]] · [[Betik Örnekleri|Scripting-Examples-TR]]

## İşletim ve sorun giderme

[[Günlükler ve Tanılama|Logs-and-Diagnostics-TR]] · [[Çökme Raporları ve Günlük Gönderme|Crash-Reports-and-Send-Logs-TR]] · [[Sorun Giderme|Troubleshooting-TR]] · [[Güvenlik Modeli|Security-Model-TR]] · [[Veri ve Gizlilik|Data-and-Privacy-TR]]

## Slurm

[[Slurm Yardım Kütüphanesi|Slurm-Help-Library-TR]] · [[İş Betiği Şablonları|Job-Script-Templates-TR]]

## Proje

[[Mimari|Architecture-TR]] · [[Kaynaktan Derleme|Building-from-Source-TR]] · [[Sürüm Süreci|Release-Process-TR]] · [[Test ve CI|Testing-and-CI-TR]] · [[Katkıda Bulunma|Contributing-TR]] · [[Lisanslama ve Ticari Kullanım|Licensing-and-Commercial-Use-TR]] · [[Destek ve Bağış|Support-and-Donations-TR]] · [[Sürüm Geçmişi|Release-History-TR]] · [[Sözlük|Glossary-TR]]
