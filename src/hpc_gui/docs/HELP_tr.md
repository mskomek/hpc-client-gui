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
