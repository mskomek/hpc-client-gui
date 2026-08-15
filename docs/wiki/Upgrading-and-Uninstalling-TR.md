# Yükseltme ve Kaldırma

> English: [[Upgrading-and-Uninstalling]]

## Verileriniz nerede

Uygulamanın yerel olarak sakladığı her şey `~/.truba_slurm_gui` altındadır
(Windows'ta `C:\Users\<siz>\.truba_slurm_gui`). Dizin adı eskiden kalmadır ve
mevcut kurulumların çalışmayı sürdürmesi için bilinçli olarak korunur.

Tipik içerik:

| Girdi | İçeriği |
|---|---|
| `config.json` | Uygulama yapılandırması ve bağlantı profilleri |
| `language.json` | Seçilen arayüz dili |
| `known_hosts` | Güvenip kaydettiğiniz ana bilgisayar anahtarları |
| `app.log`, `app.log.1`, … | Döngüsel uygulama günlüğü |
| `crash.log` | Çökme raporlayıcısının kaydı |
| `history.json`, `history.jsonl` | Komut ve iş geçmişi |
| `processes.json` | İzlenen yardımcı süreçler |
| `downloads` | İndirilen dosyalar |
| `third_party` | Onayınızla indirilen isteğe bağlı yardımcılar |

Yükseltmeler bu dizini korur; sürüme göre ayrı tutulmaz.

## Yükseltme

**Windows taşınabilir ZIP** — yeni ZIP dosyasını indirin, yeni bir klasöre
ayıklayın ve `hpc-client-gui.exe` dosyasını oradan çalıştırın. Sonuçtan emin
olunca eski klasörü silin. Profilleriniz ve ayarlarınız uygulama klasörünün
dışında yaşadığı için etkilenmez.

**Linux AppImage** — yeni AppImage dosyasını indirin, `.sha256` doğrulamasını
yapın, çalıştırılabilir yapın ve eski dosyanın yerine koyun.

**Linux `.deb`** — yeni paketi eskisinin üzerine kurun:

```bash
sudo apt install ./hpc-client-gui_1.2.6_amd64.deb
```

**Kaynaktan** — yeni sürümü çekip aynı sanal ortama yeniden kurun:

```bash
pip install -e .[test]
```

## Sürüm düşürme

Sürüm düşürme yükseltmeyle aynı şekilde yapılır: eski dosyayı çalıştırın.
Yapılandırma sürümler arasında paylaşıldığı için eski bir derleme, yeni bir
derlemenin yazdığı ayarları anlamayabilir. Sürüm düşürdükten sonra eski sürüm
hatalı davranırsa `~/.truba_slurm_gui/config.json` dosyasını başka bir yere
taşıyın ve uygulamanın yeniden oluşturmasına izin verin.

## Kaldırma

1. Uygulamayı kaldırın:
   - Windows taşınabilir ZIP: ayıkladığınız klasörü silin.
   - Linux AppImage: AppImage dosyasını silin.
   - Linux `.deb`: `sudo apt remove hpc-client-gui`.
   - Kaynaktan: sanal ortamı ve çalışma kopyasını silin.
2. İsterseniz `~/.truba_slurm_gui` dizinini silerek verilerinizi kaldırın.

Bu dizini silmek kayıtlı profillerinizi, güvenilen ana bilgisayar
anahtarlarınızı, günlüklerinizi ve geçmişinizi kaldırır. Saklamak istediğiniz
her şeyi önce kopyalayın.

## Ayrıca bkz.

[[Windows Kurulumu|Installation-Windows-TR]] ·
[[Linux Kurulumu|Installation-Linux-TR]] ·
[[Veri ve Gizlilik|Data-and-Privacy-TR]]
