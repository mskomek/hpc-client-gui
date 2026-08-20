# Hızlı Başlangıç

> English: [[Quick-Start]]

Bu sayfa sizi indirmeden çalışan bir Slurm işine götürür.
`src/hpc_gui/docs/HELP_tr.md` içindeki kanonik "5 dakikada ilk iş" akışını
izler.

## 1. Kurun

- **Windows:** [sürümler
  sayfasından](https://github.com/mskomek/hpc-client-gui/releases) taşınabilir
  ZIP dosyasını indirin, **Tümünü ayıkla** deyin ve `hpc-client-gui.exe`
  dosyasını çalıştırın. Python gerekmez.
  Bkz. [[Windows Kurulumu|Installation-Windows-TR]].
- **Linux:** x86_64 için AppImage veya `.deb` dosyasını indirin, eşleşen
  `.sha256` dosyasını doğrulayın ve çalıştırın. Bkz.
  [[Linux Kurulumu|Installation-Linux-TR]].
- **Kaynaktan:** Python 3.10+, bir sanal ortam ve `pip install -e .[test]`.
  Bkz. [[Kaynaktan kurulum|Installation-From-Source-TR]].

## 2. Bağlanın

1. Küme sunucu adınız ve kullanıcı adınızla bir bağlantı profili oluşturun.
2. Anahtar tabanlı veya parola ile kimlik doğrulamayı seçin.
3. Bağlanın. İlk bağlantıda bilinmeyen bir ana bilgisayar anahtarı için
   güvenip kaydetme, bir kerelik güvenme veya iptal seçenekleri sunulur.

Ayrıntılar: [[Bağlantı ve Profiller|Connecting-and-Profiles-TR]] ve
[[Güvenlik Modeli|Security-Model-TR]].

## 3. Girdilerinizi kümeye kopyalayın

Betiğinizi ve verinizi uzak dosya yöneticisiyle yükleyin. Büyük veri ve uzun
çalışmalar için scratch veya proje dizinini tercih edin; scratch küme
yöneticileri tarafından düzenli olarak temizlenir, bu yüzden önemsediğiniz
sonuçları home veya proje deposunda tutun.

Ayrıntılar: [[Uzak Dosya Yöneticisi|Remote-File-Manager-TR]] ve
[[Dosya Aktarımları|File-Transfers-TR]].

## 4. Bir iş betiği yazın

Basit bir `job.sh` oluşturun — ya da hazır bir şablondan başlayın. Örnek:

```bash
#!/bin/bash
#SBATCH --job-name=first
#SBATCH --time=00:10:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G

echo "hello from $(hostname)"
```

Şablonlar: [[İş Betiği Şablonları|Job-Script-Templates-TR]]. Düzenleme:
[[Betik Düzenleyici|Script-Editor-TR]].

## 5. Gönderin ve izleyin

Betiği gönderin, ardından işi işler görünümünden takip edin. Eşdeğer Slurm
komutları şunlardır:

```bash
sbatch job.sh
squeue -u $USER
```

Ayrıntılar: [[Slurm İşleri|Slurm-Jobs-TR]] ve
[[İş Çıktıları|Job-Outputs-TR]].

## 6. Bir şey çalışmazsa

Arayüz yanıt vermeyi sürdürmeli ve hataları
`~/.truba_slurm_gui/app.log` yolundaki döngüsel günlük dosyasına yazmalıdır.
Yardım isterken bu günlüğü ekleyin.

Bkz. [[Sorun Giderme|Troubleshooting-TR]] ve
[[Günlükler ve Tanılama|Logs-and-Diagnostics-TR]].

## X11'e ihtiyacım var mı?

Yalnızca MATLAB veya ParaView gibi uzak **grafiksel** uygulamalar için.
Terminal iş yükleri — Python betikleri, toplu çözücüler, eğitim işleri — buna
ihtiyaç duymaz. Bkz. [[X11 Yönlendirme|X11-Forwarding-TR]].
