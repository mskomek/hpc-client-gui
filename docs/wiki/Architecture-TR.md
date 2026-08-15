# Mimari

> English: [[Architecture]]

Kanonik kaynak olan `src/hpc_gui/docs/ARCHITECTURE.md` dosyasının özeti.

Uygulama, SSH ve Slurm iş akışları için yazılmış, dış yardımcılar aracılığıyla
isteğe bağlı X11 desteği sunan bir **PySide6 masaüstü programıdır**. Ürün
döngüsü şudur: başlat, uzak oturumu kur veya yeniden kullan, uzak içeriği gez
ya da düzenle, Slurm betiklerini hazırla veya gönder, kuyruk ve muhasebe
durumunu gözle, tanılama ile günlükleri incele.

## Katmanlar

| Paket | Sahip olduğu | Sahip olmadığı |
|---|---|---|
| `src/hpc_gui/ui/` | Pencereler, iletişim kutuları, bileşenler, kullanıcı etkileşimi, ilerleme ve durum gösterimi | Yeniden kullanılabilir Slurm ayrıştırma, derin oturum mantığı, gizli iş kuralları |
| `src/hpc_gui/services/` | Slurm servis soyutlamaları, uzak dosya işlemleri, süreç kaydı, X11 yardımcı düzenlemesi, PuTTY ve VcXsrv tümleştirmesi | — |
| `src/hpc_gui/ssh/` | Uzak istemci davranışı ve bağlantı düzeyi sarmalayıcılar | — |
| `src/hpc_gui/config/` | Yerel yapılandırma modelleri, kullanıcı tercihlerinin saklanması, güvenli kalıcılık yardımcıları | — |
| `src/hpc_gui/core/` | Günlük kurulumu, i18n, tanılama yardımcıları, yol ve kaynak yardımcıları | — |
| `src/hpc_gui/cli/` | Komut satırı yüzeyi ve çıkış kodu sözleşmesi | Servislerin zaten sunmadığı davranışlar |
| `templates/` | CPU, GPU ve MPI akışları için başlangıç Slurm betiği şablonları | — |
| `scripts/` | Depo doğrulaması, duman testleri, paketleme ve sürüm yardımcıları | — |

## Öncelikler

Aralarında çatışma olduğunda projenin çözdüğü sıra:

1. Arayüz yanıt verebilirliği
2. Açık, incelenebilir uzak işlemler
3. Yeniden kullanılabilir servis ve alan mantığı
4. Gözlemlenebilir hatalar
5. i18n tutarlılığı
6. Kullanışlı paketleme

## Tasarım kuralları

- **Qt katmanını ince tutun.** Mantık bir bileşenin dışında test edilebiliyorsa
  bileşenden çıkarıp bir servise taşıyın.
- **Uzun süren işi arayüz iş parçacığından uzak tutun.** Oturum, aktarım ve
  süreç işleri eşzamansız çalışır; pencere ağ üzerinde asla bloke olmaz.
- **Kullanıcıya görünen metinleri dil katmanında tutun.** Türkçe ve İngilizce
  kaynaklar birlikte güncellenir — bkz.
  [[Arayüz Dili ve i18n|Interface-Language-and-i18n-TR]].
- **Dış komut çalıştırmayı anlaşılır tutun.** Argümanlar serbest metinden
  birleştirilmek yerine açık ve tırnaklanmış olur.
- **Test dikişlerini kullanılabilir tutun**; `tests/test_editor_flow.py`
  örneğindeki gibi sahte dosya ve Slurm katmanları için. Çevrimdışı paketin
  aktarım ve iş akışlarını kümesiz sınayabilmesinin nedeni budur — bkz.
  [[Test ve CI|Testing-and-CI-TR]].

## Arayüz neden hiç bloke olmaz

Her uzak işlem — bağlanma, dizin listeleme, dosya aktarma, zamanlayıcıyı
sorgulama — keyfi olarak uzun sürebilir veya başarısız olabilir. Bunların
herhangi birini arayüz iş parçacığında çalıştırmak pencereyi dondururdu.
Servis katmanı kısmen bu işin bir bileşen olmayan bir yerde yaşaması için
vardır ve hatalar donmuş bir arayüz olarak değil, günlüğe yazılan
gözlemlenebilir olaylar olarak yüzeye çıkar.

## Ayrıca bkz.

[[Kaynaktan Derleme|Building-from-Source-TR]] ·
[[Test ve CI|Testing-and-CI-TR]] ·
[[Katkıda Bulunma|Contributing-TR]]
