# Uyumluluk ve Destek Matrisi

> English: [[Compatibility-and-Support-Matrix]]

Geçerli sürüm: **1.5.9** (`pyproject.toml`).

## Platformlar ve paketleme

| Platform | Biçim | Notlar |
|---|---|---|
| Windows 10 / 11 | `hpc-client-gui.exe` içeren taşınabilir ZIP | Python gerekmez |
| macOS 13+ Apple Silicon | `hpc-client-gui_macos_arm64.dmg` | İmzalı/notarize release DMG'si |
| macOS 13+ Intel | `hpc-client-gui_macos_x86_64.dmg` | İmzalı/notarize release DMG'si |
| Linux x86_64 | AppImage | Kurulum olmadan çalışır |
| Linux x86_64 (Debian tabanlı) | `.deb` | Sistem geneline kurulur |
| Tüm desteklenen platformlar | Kaynaktan | Python 3.14.x, `pip install -e .` |

Flatpak isteğe bağlıdır ve standart sürüm setinin parçası değildir; çalışma
zamanı ve SDK'sı belirgin biçimde daha büyüktür. ARM64 derlemesi yoktur.

Linux'ta kaynaktan kullanım x86_64 üzerinde Ubuntu LTS, Fedora ve openSUSE için
belgelenmiştir. Qt platform kitaplıkları (`libegl1` sınıfı) artık gerekmez: V2
üretim çalışma zamanı wxPython'dır (wxWidgets); Qt/PySide6 yalnızca eski
(legacy) kullanıma yöneliktir (tanıtılmayan `legacy-qt` extrası) ve V2 üretim
paketinde yer almaz. Linux'ta kaynaktan wxPython derlemek için
`docs/v2/WX_DEPENDENCY_CLOSURE.md` belgesindeki GTK/WebKit derleme
bağımlılıkları gerekir.

## Çalışma zamanı gereksinimleri

| Gereksinim | Taşınabilir / paketli | Kaynaktan |
|---|---|---|
| Python 3.14.x | Gerekmez | Gerekir |
| wxWidgets çalışma zamanı (wxPython 4.3.1) | Birlikte gelir | `wxPython>=4.3.1` gerekir |
| Qt/PySide6 | Gönderilmez (yalnızca eski kullanım için `legacy-qt` extrası) | İsteğe bağlı, yalnızca eski kullanım, gerekmez |
| `plink.exe` (PuTTY) | İsteğe bağlı, yalnızca X11, Windows | İsteğe bağlı, yalnızca X11 |
| VcXsrv | İsteğe bağlı, yalnızca X11, Windows | İsteğe bağlı, yalnızca X11 |
| Sistem OpenSSH istemcisi | Windows'ta X11 için kullanılmaz | Linux'ta X11 için gerekir |
| XQuartz | Gerekmez | Yalnızca macOS X11 için gerekir |

## Küme tarafı gereksinimleri

Uygulama sağlayıcıdan bağımsızdır. SSH erişimi olan, Slurm komutlarının
bulunduğu (`sbatch`, `squeue`, `sacct`, …) ve — yalnızca uzak grafiksel
uygulamalara ihtiyaç duyuyorsanız — X11 yönlendirmesine izin verilen her yerde
çalışır.

Siteniz komut çıktısını değiştiren oturum açma başlıkları veya uyarıları
yazdırıyorsa, Slurm çıktısının ayrıştırılması bozulabilir. Uygulama tahmin
yürütmek yerine yumuşak biçimde başarısız olmak ve ayrıntıyı günlüğe yazmak
üzere yazılmıştır.

## Bağlantı ve X11 desteği

| Senaryo | Durum | Notlar |
|---|---|---|
| Anahtar tabanlı kimlik doğrulama | Destekleniyor | Ana oturum yolu |
| Parola ile kimlik doğrulama | Destekleniyor | Profilde korunarak saklanabilir |
| plink + VcXsrv ile X11 (Windows) | Önerilen | Windows'ta en güvenilir yol |
| Anahtarla OpenSSH üzerinden X11 | Destekleniyor | `ssh -X/-Y` kullanır |
| Parolayla OpenSSH üzerinden X11 | Sınırlı | Gizli TTY istemleri kilitleyebilir; plink tercih edilir |
| macOS X11 ve parola | Sınırlı | SSH anahtarı veya agent gerekir; yalnızca parolalı X11 başlatılmaz |
| Ana bilgisayar anahtarı ilkesi `accept-new` | Destekleniyor | Bilinmeyen anahtarlar için güvenip kaydet, bir kerelik güven veya iptal sorulur |
| Ana bilgisayar anahtarı ilkesi `strict` | Destekleniyor | Bilinmeyen anahtarlar reddedilir; değişen anahtarlar her zaman reddedilir |

Kaydedilen ana bilgisayar anahtarları `~/.truba_slurm_gui/known_hosts` dosyasına
yazılır.

## Bilinen sınırlamalar

- Kullanıcı deneyimi öncelikli olarak Windows içindir.
- Slurm çıktısının ayrıştırılması site özelleştirmesine göre değişir.
- X11 yanıt süresi büyük ölçüde ağ kalitesine bağlıdır.

Ayrıca bkz. [[Windows Kurulumu|Installation-Windows-TR]],
[[Linux Kurulumu|Installation-Linux-TR]] ve
[[macOS Kurulumu|Installation-macOS-TR]],
[[X11 Yönlendirme|X11-Forwarding-TR]].

## Dondurulmuş sürüm adayı 1.5.9 (W57.4 son destek beyanı)

Bu bölüm W11'e devredilen dondurulmuş aday için bağlayıcıdır; yukarıdaki
platform tablosu projenin üretebildiği sürüm *setini* anlatır.

| Kalem | Bu aday için durum | Kanıt |
|---|---|---|
| Windows 10/11 AMD64, taşınabilir `hpc-client-gui.exe` (SHA-256 `B3019DEA16783C8AB859FA36D2B0FEF2FB70DB075633E54EB0F36587295374FD`) | **Destekleniyor** | birebir artefakt üzerinde paket smoke 20/20; W57.1 paket fonksiyonel tekrar 110/110; LOCAL_REAL Hyper-V küme `lab-test` LOCAL_REAL_READY (0 hata) |
| GUI çalışma zamanı | **wxPython 4.3.1 (wx V2)**; Qt/PySide6 pakette yok | pakette sıfır Qt dosyası (freeze beyanı) |
| Küme tarafı | SSH/SFTP + Slurm (`sbatch`/`squeue`/`sacct`/`scancel`) | LOCAL_REAL lab: SSH, SFTP gidiş-dönüş, sbatch, iptal, ortak home |
| macOS (Apple Silicon / Intel) DMG | **Bu adayın parçası değil** | bu freeze için macOS artefaktı üretilmedi/sınanmadı |
| Linux AppImage / `.deb` | **Bu adayın parçası değil** | bu freeze için Linux artefaktı üretilmedi/sınanmadı |
| Kaynaktan (Python 3.14.x) | Yalnız geliştirici kullanımı, sürüm artefaktı değil | W57.4 raporundaki tam otomatik test takımı |

Artefakttaki her bayt değişikliği yeni bir SHA-256 üretir ve bu beyanı geçersiz kılar.
