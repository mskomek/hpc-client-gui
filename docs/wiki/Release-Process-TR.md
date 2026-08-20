# Sürüm Süreci

> English: [[Release-Process]]

## Tutarlılık kapısı

`scripts/check_release_consistency.ps1`, bir sürümün ilerlemesine izin
verilmeden önce çalışır ve herhangi bir uyuşmazlıkta başarısız olur:

- `pyproject.toml` içindeki sürüm, paketin `__version__` değeri ve CLI'ın
  `CLI_VERSION` değeri istenen sürümle aynı olmalıdır.
- Sürüm etiketi istenen sürümle eşleşmelidir.
- `build/windows/version_info.txt` alanları — sürüm demeti dâhil —
  eşleşmelidir.
- Değişiklik günlüğü `v<version>` için bir bölüm içermelidir.
- Gerekli her yardım dosyası bulunmalıdır.

Tutarsız sürüm metinleri ya da eksik bir değişiklik günlüğü girdisiyle
yayımlanacak bir sürüm, yayımlanmak yerine burada durur.

## Çıktıları derleme

```powershell
.\scripts\build_release.ps1 -Version 1.2.6
.\scripts\package_release.ps1 -Version 1.2.6
```

Linux çıktıları, paketlemeden önce AppImage masaüstü girdisini, `AppRun`
başlatıcısını ve `.deb` control dosyasını doğrulayan `scripts/release_linux.py`
tarafından üretilir. Bkz. [[Kaynaktan Derleme|Building-from-Source-TR]].

Çıktılar, her biri bir `.sha256` dosyasıyla birlikte `dist/releases/v<version>`
dizinine iner.

## Sürüm iş akışı

`.github/workflows/release.yml`, sürümü girdi olarak alan ve her iki platformu
derleyen, elle tetiklenen bir iş akışıdır:

**Linux çıktıları (Ubuntu 24.04)** — sürüm bağımlılık önbelleğini geri yükler,
Qt ve paketleme çalışma zamanını kurar, kaynak denetimlerini çalıştırır, Linux
paketleme planını doğrular, Flatpak çalışma zamanını ve AppImage aracını
kurar, çıktıları derleyip hazırlar, sonra yüklemeden önce paketli bir CLI
duman testi ve offscreen paketli bir GUI duman testi çalıştırır.

**Windows çıktıları** — Windows onedir ZIP dosyasını derler ve paketler.

Paketli duman adımları önemlidir: derlendikleri kaynak ağacını değil, gerçekten
yayımlanacak çıktıyı sınarlar.

## Yayımlama

Çıktılar ve `.sha256` dosyaları, etikete ait GitHub sürümüne eklenir. O sürümün
değişiklik günlüğü bölümü sürüm notlarının kaynağıdır — bkz.
[[Sürüm Geçmişi|Release-History-TR]].

## Yayımlanmış bir sürümü doğrulama

```bash
sha256sum -c hpc-client-gui-1.2.6-x86_64.AppImage.sha256
```

## Ayrıca bkz.

[[Kaynaktan Derleme|Building-from-Source-TR]] · [[Test ve CI|Testing-and-CI-TR]] · [[Sürüm Geçmişi|Release-History-TR]]
