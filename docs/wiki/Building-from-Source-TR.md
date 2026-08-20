# Kaynaktan Derleme

> English: [[Building-from-Source]]

Bu sayfa dağıtılabilir çıktı üretmeyi anlatır. Yalnızca kaynaktan *çalıştırmak*
için bkz. [[Kaynaktan kurulum|Installation-From-Source-TR]].

## Ön koşullar

- Geliştirme kurulumu yapılmış çalışan bir kaynak kopyası
  (`pip install -e .[test]`).
- Windows paketi için Windows.
- Linux çıktıları için Docker; bunlar bir kapsayıcı görüntüsünde derlenir
  (öntanımlı olarak `hpc-client-gui-linux-build:24.04`).

## Windows'tan her iki platformu derleme

```powershell
.\scripts\build_release.ps1 -Version 1.2.6
```

Yalnızca önbellekte olanı kullanmak ve hiçbir şey indirmemek için:

```powershell
.\scripts\build_release.ps1 -Version 1.2.6 -Offline
```

`-Offline`, eksik girdileri indirme yerine hata sayar. Linux derleme görüntüsü,
AppImage aracı, derleme sanal ortamı ya da Flatpak çalışma zamanı ve SDK'sı
önbellekte yoksa betik onları getirmek yerine başarısız olur.

## Derleme girdileri ve çıktıları nerede durur

- Önbelleğe alınan derleme girdileri: `.cache/release`.
- Sürüm çıktıları: tek bir birleşik `dist/releases/v<version>` dizini.

Önbellekteki girdiler eksik olmadıkça yeniden indirilmez.

## Windows paketleme

`scripts/package_release.ps1`, Windows onedir derlemesini sürüm dizini içinde
`hpc-client-gui_windows_onedir.zip` dosyasında toplar ve yanına eşleşen bir
`.sha256` dosyası yazar.

```powershell
.\scripts\package_release.ps1 -Version 1.2.6
```

## Linux paketleme

`scripts/release_linux.py`, Linux sürüm girdilerini doğrular ve Linux
çıktılarını üretir:

- `hpc-client-gui-<version>-x86_64.AppImage`
- `hpc-client-gui_<version>_amd64.deb`

Paketlemeden önce doğrular: AppImage `.desktop` girdisinde `Exec=` ve `Name=`
satırlarını taşıyan bir `[Desktop Entry]` bölümü bulunmalı, `AppRun`
başlatıcısı var olmalı ve bir shebang ile başlamalı, `.deb` control dosyası
gerekli alanlarını ve sürüm yer tutucusunu taşımalıdır. Hatalı bir girdi,
bozuk üst veriyi yayımlamak yerine derlemeyi başarısız kılar.

## Sağlama toplamları

Yayımlanan her çıktının eşleşen bir `.sha256` dosyası olur. Kurmadan önce
doğrulayın:

```bash
sha256sum -c hpc-client-gui-1.2.6-x86_64.AppImage.sha256
```

## Ayrıca bkz.

[[Sürüm Süreci|Release-Process-TR]] · [[Test ve CI|Testing-and-CI-TR]] · [[Mimari|Architecture-TR]]
