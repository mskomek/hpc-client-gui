# Linux Kurulumu

> English: [[Installation-Linux]]

Linux sürümleri **x86_64** hedefler ve AppImage ile `.deb` paketi olarak
yayımlanır. Flatpak isteğe bağlıdır ve standart sürüm setinin parçası
değildir. ARM64 derlemesi yoktur.

## Çıktı dosya adları

1.5.9 sürümü için sürüm araçları şunları üretir:

- `hpc-client-gui-1.5.9-x86_64.AppImage`
- `hpc-client-gui_1.5.9_amd64.deb`

Her dosya, eşleşen bir `.sha256` dosyasıyla birlikte yayımlanır.

## İndirmeyi doğrulayın

```bash
sha256sum -c hpc-client-gui-1.5.9-x86_64.AppImage.sha256
```

Sağlama toplamı doğrulanmayan bir dosyayı kurmayın.

## AppImage

```bash
chmod +x hpc-client-gui-1.5.9-x86_64.AppImage
./hpc-client-gui-1.5.9-x86_64.AppImage
```

AppImage kurulum gerektirmeden çalışır.

## Debian paketi

```bash
sudo apt install ./hpc-client-gui_1.5.9_amd64.deb
```

## wxWidgets sistem kitaplıkları

Uygulama bir wxPython (wxWidgets) masaüstü programıdır. Qt (PySide6) platform
kitaplıkları gerekmez: Qt yalnızca eski (legacy) kullanıma yöneliktir ve V2
üretim paketinde yer almaz. Başlatma hatasının Qt `xcb` platform eklentisinden
söz etmesi beklenmez; uygulama başlatma sırasında başarısız olursa bkz.
[[Sorun Giderme|Troubleshooting-TR]].

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

[[Hızlı Başlangıç|Quick-Start-TR]] · [[Kaynaktan kurulum|Installation-From-Source-TR]] · [[Yükseltme ve kaldırma|Upgrading-and-Uninstalling-TR]]
