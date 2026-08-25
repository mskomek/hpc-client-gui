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

`.github/workflows/release.yml`; sürümü, açık bir `publish` anahtarını
(öntanımlı `false` — normal bir prova asla yayımlamaz) ve bir `macos_mode`
seçimini (`signed` öntanımlı, ya da `unsigned`) girdi olarak alan,
üç platformu derleyen elle tetiklenen bir iş akışıdır:

**Linux çıktıları (Ubuntu 24.04)** — sürüm bağımlılık önbelleğini geri yükler,
Qt ve paketleme çalışma zamanını kurar, paylaşılan sürüm ön kontrol paketini
(`scripts/release_test_suite.py`) çalıştırır, Linux paketleme planını doğrular,
Flatpak çalışma zamanını ve AppImage aracını kurar, çıktıları derleyip
hazırlar, sonra yüklemeden önce paketli bir CLI duman testi ve offscreen
paketli bir GUI duman testi çalıştırır.

**Windows çıktıları** — aynı paylaşılan ön kontrol paketini çalıştırır, sonra
Windows onedir ZIP dosyasını derler ve paketler.

**macOS arm64 / x86_64 çıktıları** — DevTools hariç tutmalı PyInstaller spec'i
ile her zaman imzasız aday üretir, paketli duman testlerini üretilen `.app`
içinden çalıştırır, sıralı bir paket boyut raporu tutar ve sıkıştırılmış DMG
boyut bütçesini (öntanımlı 600 MiB) uygular.

İmzalı modda özel işler her mimarinin adayını imzalar, notarize eder ve
staple'lar; ardından bir doğrulama işi her iki DMG'yi bağlayıp sağlama
değerini, `codesign --verify --deep --strict` ve `spctl --assess` kontrollerini
üst veri üretilmeden önce yapar. İmzasız modda ayrı bir envanter işi sağlama
değerlerini doğrulayıp açıklama notları üretir — hiçbir zaman imza aracı
çalıştırmaz.

Paketli duman adımları önemlidir: derlendikleri kaynak ağacını değil, gerçekten
yayımlanacak çıktıyı sınarlar.

## Son kapı (release gate)

`release-gate` işi tüm zorunlu iş sonuçlarını seçilen moda göre değerlendirir
(`scripts/release_gate.py`): dört derleme işi her modda başarılı olmalıdır;
imzalı mod ayrıca iki imza işinin ve imzalı doğrulamanın başarısını isterken,
imzasız mod bu işlerin atlanmış olmasını ve imzasız envanter kontrolünün
geçmesini ister. Eksik, başarısız, iptal edilmiş ya da beklenmedik biçimde
atlanan sonuçlar kapının düşmesine yol açar. `publish-release` bu kapıya
bağlıdır; yukarıdaki her şey başarılı olmadan yayım mümkün değildir.

## Sürüm güvenlik üst verisi

Doğrulanmış her aday `RELEASE_SECURITY.json` üretir: sürüm, kaynak commit,
macOS modu (`signed-notarized` veya `unsigned`), Developer ID / notarizasyon /
staple / Gatekeeper sonuçları ve çıktı mimari listesi. Bu dosya
`MANIFEST.json`'a girer, sürüm varlığı olur ve kanıtlanan konulara dâhildir.
İmzasız sürümlerde notlarda Gatekeeper'ın ilk açılışı engelleyebileceği ve
SHA-256/kanitın Apple kod imzasının yerine geçmeyeceği üzerine belirgin bir
uyarı bulunur. İmzalı notlar, doğrulama işi başarıldıktan sonra imzadan söz
edebilir.

## Yayımlama

Çıktılar, `.sha256` dosyaları, `MANIFEST.json` ve `RELEASE_SECURITY.json`,
etikete ait GitHub sürümüne eklenir. Üretilen `RELEASE_NOTES.md` (değişiklik
günlüğü bölümü artı mod açıklaması) sürüm notu gövdesidir — bkz.
[[Sürüm Geçmişi|Release-History-TR]].

## Yayımlanmış bir sürümü doğrulama

```bash
sha256sum -c hpc-client-gui-<version>-x86_64.AppImage.sha256
```

## Ayrıca bkz.

[[Kaynaktan Derleme|Building-from-Source-TR]] · [[Test ve CI|Testing-and-CI-TR]] · [[Sürüm Geçmişi|Release-History-TR]]
