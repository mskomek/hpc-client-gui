# Linux Kurulumu

> English: [[Installation-Linux]]

Linux sürümleri **x86_64** hedefler ve AppImage ile `.deb` paketi olarak
yayımlanır. Flatpak isteğe bağlıdır ve standart sürüm setinin parçası
değildir. ARM64 derlemesi yoktur.

## Çıktı dosya adları

1.2.6 sürümü için sürüm araçları şunları üretir:

- `hpc-client-gui-1.2.6-x86_64.AppImage`
- `hpc-client-gui_1.2.6_amd64.deb`

Her dosya, eşleşen bir `.sha256` dosyasıyla birlikte yayımlanır.

## İndirmeyi doğrulayın

```bash
sha256sum -c hpc-client-gui-1.2.6-x86_64.AppImage.sha256
```

Sağlama toplamı doğrulanmayan bir dosyayı kurmayın.

## AppImage

```bash
chmod +x hpc-client-gui-1.2.6-x86_64.AppImage
./hpc-client-gui-1.2.6-x86_64.AppImage
```

AppImage kurulum gerektirmeden çalışır.

## Debian paketi

```bash
sudo apt install ./hpc-client-gui_1.2.6_amd64.deb
```

## Qt platform kitaplıkları

Uygulama bir Qt (PySide6) masaüstü programıdır ve Qt'nin başlangıçta yüklediği
platform kitaplıklarına ihtiyaç duyar. Ubuntu ve Debian'da:

```bash
sudo apt install libegl1
```

Fedora ve openSUSE eşdeğer paketleri kendi adlarıyla sunar. Eksik bir platform
kitaplığı genellikle `xcb` platform eklentisinden söz eden bir başlatma
hatası olarak görünür — bkz. [[Sorun Giderme|Troubleshooting-TR]].

## Linux'ta X11 yönlendirme

Linux'ta X11 yönlendirmesi **sistem OpenSSH istemcisini** (`ssh -X/-Y`)
kullanır. Windows'un plink/VcXsrv yolunu kullanmaz ve hiçbir yardımcı
indirilmez. Uzak grafiksel uygulamaları başlatmadan önce istemcinin kurulu
olduğundan ve oturumunuzda `DISPLAY` değişkeninin ayarlı olduğundan emin olun.
Ayrıntılar: [[X11 Yönlendirme|X11-Forwarding-TR]].

## Uygulama verileri

Yapılandırma, döngüsel günlük ve kaydedilen ana bilgisayar anahtarları
`~/.truba_slurm_gui` dizininde bulunur. Dizin adı eskiden kalmadır ve mevcut
kurulumlarla uyumluluk için korunmaktadır.

## Sonraki adımlar

[[Hızlı Başlangıç|Quick-Start-TR]] ·
[[Kaynaktan kurulum|Installation-From-Source-TR]] ·
[[Yükseltme ve kaldırma|Upgrading-and-Uninstalling-TR]]
