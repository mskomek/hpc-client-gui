# macOS Kurulumu

HPC Client GUI macOS paketleri, Mac App Store dışında, release kapısı
tamamlandığında imzalı ve notarize edilmiş DMG olarak yayımlanır. macOS 13 veya
daha yenisi gerekir.

## Doğru DMG'yi seçin

- Apple Silicon (M1/M2/M3/M4): `hpc-client-gui_macos_arm64.dmg`
- Intel: `hpc-client-gui_macos_x86_64.dmg`

Mac'inizin mimarisine uygun olmayan paketi kullanmayın. Her DMG'nin yanında
`.sha256` dosyası ve release içinde `MANIFEST.json` envanteri bulunur.

## Kurulum

1. Uygun DMG'yi [GitHub Releases](https://github.com/mskomek/hpc-client-gui/releases/latest) sayfasından indirin.
2. İsterseniz yanındaki SHA-256 dosyasıyla doğrulayın.
3. DMG'yi açın.
4. **HPC Client GUI.app** dosyasını **Applications** klasörüne sürükleyin.
5. Finder üzerinden başlatın.

Bağlantı parolasını kaydettiğinizde Keychain erişim isteği görülebilir. Ayar
dosyasına yalnızca opak Keychain referansı yazılır; düz parola loglara,
tanılamalara veya yapılandırmaya yazılmaz.

## X11 ve XQuartz

XQuartz isteğe bağlıdır; yalnızca uzak grafiksel X11 uygulamalarına ihtiyacınız
varsa kurun. Uygulama XQuartz, `/opt/X11/bin/xauth` ve geçerli bir `DISPLAY`
bekler; XQuartz'u indirmez veya kapatmaz. macOS X11 için SSH anahtarı veya agent
gerekir; yalnızca parolalı kimlik doğrulama ile X11 başlatılmaz.

## Güncelleme ve kaldırma

Güncellemeler manueldir: aynı mimariye ait yeni DMG'yi indirin, yeni uygulamayı
Applications içindeki eskisinin üzerine sürükleyin ve başlatın. Kaldırmak için
uygulamayı Çöp Kutusu'na taşıyın. Kullanıcı verileri
`~/Library/Application Support/HPC Client GUI` altında kalır.

Bu proje resmi TRUBA uygulaması değil, istemci tarafı bir araçtır.
