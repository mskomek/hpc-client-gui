# HPC Client GUI — Yardım

> **Slurm tabanlı HPC** sistemlerinde **SSH / Slurm / X11** iş akışını kolaylaştıran **resmî olmayan** istemci GUI.
>
> Bu, herhangi bir sağlayıcıya bağlı olmayan bağımsız bir topluluk projesidir.

---

## Yeni başlayanlar için

Bu programın mantığı çok basit:

- **SSH**: Uzaktan HPC’ye bağlanırsın.
- **Slurm**: İşlerini kuyruğa gönderir, kaynak ayırır ve çalıştırır.
- **X11**: Sadece **grafik arayüzlü** uygulamalar (MATLAB, ParaView vb.) için gerekir.

### 5 Dakikada ilk iş

1. **Bağlan**
2. Dosyalarını (girdi, script, veri) **Scratch / proje dizinine** kopyala
3. Basit bir `job.sh` oluştur
4. Terminalde çalıştır:
   - `sbatch job.sh`
5. Job durumunu kontrol et:
   - `squeue -u $USER`

### X11 ne zaman gerekir?

- ✅ MATLAB, ParaView, GUI tabanlı araçlar
- ❌ Terminal işleri (Python script, CFD batch, eğitim amaçlı komutlar) için gerekmez

### Bir şey çalışmazsa

- GUI donmamalı; hatalar **log dosyasına** yazılır.
- Log yolu:
  - `~/.truba_slurm_gui/app.log`
- Yardım isterken bu dosyayı paylaşmak teşhis süresini çok kısaltır.

---

## Gömülü SSH terminali

Bağlantı sekmesindeki terminal, uzak kabuğu uygulamanın içinde açar. Terminal
alanı pencereyle birlikte yeniden boyutlanır; **Bul**, **Temizle**, **A−** ve
**A+** araçları yerel görünümü yönetir. Terminal dosyaları paket içinde gelir;
CDN veya çalışma anında indirme kullanılmaz.

Bağlantı kurulamazsa pencere olası nedeni ve kontrol edilmesi gerekenleri
gösterir. `SSH-XXXXXX` biçimindeki tanı kodu, aynı hatayı günlükte bulmak içindir.

---

## Dosya yöneticisi özellikleri

### Varsayılan yerel klasör (profil başına)

**Gelişmiş → Dosya tarayıcı** altında her bağlantı profili bir **Varsayılan
yerel klasör** tanımlayabilir. Profil bağlandığında yerel dosya bölmesi bu
klasörü açar. Boş bırakılırsa normal davranış korunur (son gezilen yerel
klasör). Scratch ve Home, profilin ayrı *uzak* varsayılanları olmaya devam
eder.

### Eşzamanlı gezinme

Dosyalar sekmesindeki **Eşzamanlı gezinme** düğmesi, yalnızca *dizin
gezinmesini* yerel bölme ile etkin uzak bölme arasında aynalar. Hiçbir
zaman dosya yüklemez/indirmez/oluşturmaz/adlandırma yapmaz/silmez.

- İlk açılışta görünen soru, **o an görünür yerel ve uzak klasörlerin**
  eşzamanlı kök çifti olarak kaydedilmesini sağlar.
- Kök çifti içindeki gezinme göreli yol ile eşlenir; kökün dışına çıkınca
  yansıtma durur.
- Yerelde karşılığı olmayan uzak klasör için uyarı sessizce durum satırında
  gösterilir; klasör otomatik oluşturulmaz.
- Düğmenin menüsünde **Eşzamanlı kökleri geçerli klasörlere sıfırla** ve
  **Eşzamanlı gezmeyi kapat** bulunur. Kök çifti profil başına saklanır.

### Dizinleri karşılaştır

**Dizinleri karşılaştır** düğmesi, yerel ve etkin uzak dosya tablolarına bir
**Karşılaştırma** sütunu ekler. Yalnızca *geçerli anlık dizin* karşılaştırılır
ve panellerin çoktan indirdiği üst veriler kullanılır:

- tam ad eşleşmesi (uzak taraf büyük/küçük harfe duyarlıdır);
- durumlar: Aynı, Yalnızca yerel, Yalnızca uzak, Tür farklı, Boyut farklı,
  Yerel daha yeni, Uzak daha yeni;
- değişim zamanlarında küçük bir tolerans (2 saniye) kullanılır;
- alt klasörlere inilmez, içerik/SHA karşılaştırması yapılmaz;
- açmak veya yeniden hesaplamak **ek SFTP listeleme/stat trafiği üretmez**;
  sonuçlar mevcut anlık görüntülerden güncellenir.

### En fazla eşzamanlı aktarım

Bağlantı profiline özgüdür (**Gelişmiş → Aktarımlar**). Bu ayar oturum içinde
aynı anda kaç dosya aktarımı çalışacağını belirler; ek kullanıcı oturumu
açmaz. Aktarım penceresi hem **ayarlanan** değeri hem de bağlantı için
**geçerli** limiti gösterir: birden çok dosya paralel gidebilir; tek büyük
dosya şu anda parçalara bölünerek aktarılmaz. Hızlı hatlarda 2–4 değerleri
verimi artırabilir; paylaşılan HPC giriş düğümlerinde ölçülü olun. Düz FTP,
bazı sunucular eşzamanlı veri kanallarını düşürdüğü için her zaman tek
aktarımla sınırlıdır; yalıtılmış kanalları destekleyen SFTP ayarlanan
paralelliği kullanabilir.

### Eklentiler

Sağ üstteki **Eklentiler** düğmesiyle Eklenti Yöneticisi'ni açın. Kayıt
defteri açılışta otomatik yüklenir — durum *Eklentiler yükleniyor…*, sonra
*Çevrimiçi*, *Önbellek* veya *Çevrimdışı* olur. **Keşfet** sekmesinden küme
profili, iş şablonu ve lint paklerini kurun; kurmadan önce karttaki
**Ayrıntılar** ile tam kaydı inceleyin. Eksik bir eklenti mi var? Başlıktaki
**Eklenti iste** düğmesi resmî eklenti deposundaki istek formunu açar. Tam
kılavuz: [PLUGINS_tr.md](PLUGINS_tr.md).

Bir denetleyici aracı eklentisi kurduktan sonra (örnek: gayriresmî ANSYS
Script & Journal Linter), **Kurulu** kartında **Aracı aç** düğmesi görünür.
Yerel ve uzak dosya panellerinde desteklenen dosyalara sağ tıklayınca hızlı
**ANSYS Journal Denetimi** ve seçili dosyayı destekleyen kurulu her aracı
listeleyen **Eklentiye gönder ▸** alt menüsü çıkar; bir araç seçince o
eklenti dosya önceden yüklenmiş şekilde açılır. Denetim sonuç penceresindeki
**Düzelt (Eklentide aç)** düğmesi de aynı yönlendirmeyi yapar.
Ayrıntılar: [PLUGINS_tr.md](PLUGINS_tr.md).

### Gelişmiş SSH ayarları

- **Sunucu anahtarı doğrulaması**: *Yeni sunuculara güven, değişen anahtarı
  reddet* (`accept-new`; bilinmeyen sunucular parmak izi sorar) ya da
  *Yalnızca önceden güvenilen sunucu* (`strict`). Değişen anahtar her koşulda
  bağlantıyı keser; "tümünü kabul" gibi güvensiz bir seçenek yoktur.
- **SSH canlı tutma aralığı**: keepalive sinyalleri arasındaki saniye; `0`
  kapatır. Kopan bağlantıları fark etmeye yarar, aktarım hızı ayarı değildir.
- **SSH zaman aşımı geçersiz kılma**: `0` uygulama varsayılanlarını kullanır;
  pozitif değer SSH bağlantı/kanal zaman aşımını değiştirir.

### Jump (bastion) sunucu üzerinden bağlan

Gelişmiş → SSH altında tek atlamlı jump sunucu desteği vardır: uygulama önce
jump sunucusuna bağlanır ve hedef kümeye SSH `direct-tcpip` kanalı üzerinden
ulaşır.

- Bu sürümde yalnızca tek atlam desteklenir; zincirleme atlama yoktur.
- Jump sunucuda kimlik doğrulama **SSH anahtarı veya ajan** ile yapılır;
  jump şifre alanı yoktur ve hedef şifreniz asla jump için kullanılmaz.
- Hem jump hem hedef sunucu anahtarları bağımsız doğrulanır; parmak izi
  pencereleri hangi sunucuya ait olduğunu belirtir.
- Terminal, dosya gezinme ve Slurm özellikleri doğrudan bağlantıda olduğu
  gibi hedef bağlantı üzerinde çalışır.

---

## Kurulum ve çalıştırma

### Standalone (EXE)

- Bu yöntem için **Python gerekmez**.
- Dış bağımlılıklar:
  - `plink.exe` (PuTTY)
  - X11/GUI uygulamalar için: **VcXsrv** (Windows X server)

Adımlar:
1. EXE paketini indir ve çalıştır.
2. X11 kullanacaksan VcXsrv’yi kur/çalıştır.
3. `plink.exe` yolunu ayarla (uygulama ayarından veya paketle aynı klasöre koyarak).

---

## Uygulama içi yardım kütüphaneleri

Yardım penceresindeki kütüphane seçicisinden:

- **Temel Yardım**: uygulama kullanımı ve genel akış
- **Sağlayıcı Rehberleri**: siteye özel isteğe bağlı operasyon notları
- **Genel Slurm/HPC**: diğer kümeler için taşınabilir öneriler

---

## Siteye özel notlar

## Betik Editörü klavye kısayolları

Kısayollar etkin olan dosya sekmesine uygulanır:

| Kısayol | İşlem |
|---|---|
| `Ctrl+S` | Etkin dosyayı kaydet |
| `Ctrl+Shift+S` | Etkin Slurm dosyasını kaydet ve gönder |
| `Ctrl+Z` | Geri al |
| `Ctrl+Y` | Yinele |
| `Ctrl+X` | Kes |
| `Ctrl+C` | Kopyala |
| `Ctrl+V` | Yapıştır |
| `Ctrl+A` | Tüm metni seç |
| `Ctrl+F` | Etkin dosyada metin ara |
| `F3` | Sonraki eşleşmeyi bul |
| `Ctrl+O` | Uzak dosya yolu alanına git; Enter ile dosyayı aç |
| `Ctrl+W` | Etkin dosya sekmesini kapat |
| `Ctrl+Tab` | Sonraki dosya sekmesine geç |
| `Ctrl+Shift+Tab` | Önceki dosya sekmesine geç |
| `Page Up` / `Page Down` | Bir ekran yukarı/aşağı ilerle |
| `End` | Dosyanın sonuna git |

- Kümelerde **Home** kotası sınırlı olabilir; büyük işler için kurumunuzun önerdiği çalışma alanını kullanın.
- Geçici çalışma alanlarında otomatik temizleme olabilir; önemli dosyaları kalıcı bir alanda saklayın.

---

## Diğer Slurm tabanlı HPC sistemler

Bu uygulama herhangi bir sağlayıcıya bağlı değildir. Aşağıdaki şartlar varsa çalışır:

- SSH erişimi
- Slurm komutları (`squeue`, `sbatch`, `sacct` vb.)
- (Opsiyonel) X11 forwarding desteği

Kurum banner/alias/modül çıktıları farklıysa bazı parse senaryolarında log’a uyarı düşebilir.

---

## Güvenlik

- Şifre/Token:
  - History’ye yazılmaz
  - Log’a düşmez
  - UI’de görünmez
- "Harici CLI'nin uzak komutlara erişmesine izin ver" (Ayarlar): varsayılan
  olarak kapalıdır. Açıldığında, bu uygulamanın komut satırı arayüzünü
  çalıştıran herhangi bir yerel süreç, GUI oturumu olmadan kayıtlı
  profillerle uzak komutlara (dosya/iş/düzenleme/kabuk/tanılama) erişebilir. Ayarlar'dan,
  `--profile` belirtilmediğinde kullanılacak varsayılan bir CLI profili de
  seçilebilir.
- X11:
  - Paramiko ile yapılmaz
  - `plink.exe -X` + VcXsrv ile arka planda çalışır

---

## Sınırlamalar

- Windows odaklıdır.
- Ağ gecikmesi X11 deneyimini etkiler.
- Kuruma özel çok farklı Slurm formatlarında parse uyarlaması gerekebilir.

---

## Destek matrisi

| Senaryo | Durum | Not |
|---|---|---|
| Paramiko + key auth | Desteklenir | Ana SSH/oturum yolu |
| Paramiko + parola auth | Desteklenir | Profilde şifreli saklama var |
| X11 + plink + VcXsrv | Önerilen | Windows'ta en stabil yol |
| X11 + OpenSSH + key | Desteklenir | Sistem/paket ssh ile `-Y/-X` |
| X11 + OpenSSH + parola | Kısıtlı | Gizli TTY prompt bloklayabilir, plink önerilir |
| macOS X11 + parola | Kısıtlı | SSH anahtarı veya agent kullanın; yalnız parolalı X11 başlatılmaz |
| Host key policy = `accept-new` | Desteklenir | Bilinmeyen anahtarda güvenip kaydetme, bir kez güvenme veya iptal seçenekleri sunulur; kayıtlar `~/.truba_slurm_gui/known_hosts` dosyasına yazılır |
| Host key policy = `strict` | Desteklenir | Bilinmeyen anahtar reddedilir; değişmiş anahtar her zaman reddedilir |

---

## Destek

- Sorun bildirirken `~/.truba_slurm_gui/app.log` dosyasını eklemek çok faydalıdır.

---

## SLURM Quick Commands (Sık kullanılan komutlar)

### Job gönderme
- `sbatch job.sh`
- `sbatch --time=01:00:00 --mem=8G --cpus-per-task=4 job.sh`

### Job listeleme
- `squeue -u $USER`
- `squeue -j <JOBID>`

### Job iptali
- `scancel <JOBID>`
- `scancel -u $USER`  *(dikkat: tüm joblar)*

### Partition / kaynak durumu
- `sinfo`
- `sinfo -o "%P %a %l %D %t"`

### Job geçmişi (accounting)
- `sacct -u $USER --format=JobID,JobName,State,Elapsed,MaxRSS,AllocTRES`
- `sacct -j <JOBID> --format=JobID,State,ExitCode,Elapsed,MaxRSS`

### Detaylı job inceleme
- `scontrol show job <JOBID>`

### İnteraktif iş (örn. debug / GUI hazırlığı)
- `salloc -N 1 -n 1 -c 4 --mem=8G -t 01:00:00`
- `srun --pty bash`

---

## Linux destegi

Linux x86_64 sürümü GitHub Releases sayfasında AppImage, Debian `.deb` ve
Flatpak paketleri olarak yayımlanır. Her paketin yanında SHA-256 dosyası bulunur.

### Gereksinimler

- Desteklenen bir Linux dagitim (su an Ubuntu LTS, Fedora veya openSUSE), x86_64.
- Python 3.10+.
- PySide6'nin ihtiyac duydugu Qt platform kutuphaneleri (orn. Ubuntu/Debian'da libegl1).

### Kaynak kodundan calistirma

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[test]
python -m hpc_gui
```


CLI ayni sekilde kullanilabilir: python -m hpc_gui --help.

### X11 notu

Linux'ta X11 iletimi **sistem OpenSSH istemcisini** (ssh -X/-Y) kullanir. Windows plink/VcXsrv yolunu kullanmaz. X11 uygulamalari kullanmadan once ssh kurulu oldugundan emin olun.
