# Slurm Yardım Kütüphanesi

> English: [[Slurm-Help-Library]]

Uygulama, Yardım iletişim kutusundaki kütüphane seçicisinden erişilen yerleşik
bir Slurm referansı ile gelir:

- **Çekirdek Yardım** — uygulama kullanımı ve sık iş akışları.
- **Sağlayıcı Kılavuzları** — isteğe bağlı, siteye özgü işletim notları.
- **Genel Slurm/HPC** — her Slurm kümesi için geçerli taşınabilir rehberlik.

Genel kütüphane depodaki `src/hpc_gui/docs/HELP_LIBRARY_GENERIC_en.md` (ve
`_tr.md`) dosyasıdır ve kanoniktir. Bu sayfa onun kopyası değil, içindekilerin
haritasıdır.

## Genel kütüphanenin kapsamı

| Bölüm | Konu |
|---|---|
| 1 | Başlamadan önce ortamınızı tanıma |
| 2 | Günlük iş akışı için temel Slurm komutları |
| 3 | İlk başarılı iş, en yalın örnek |
| 4 | İş betiği anatomisi ve kaynakları doğru isteme |
| 5 | CPU, MPI ve GPU işleri için şablonlar |
| 6 | Hata ayıklama ve hızlı denemeler için etkileşimli kip |
| 7 | İş dizileri ve bağımlılıklarla iş hattı akışları |
| 8 | Bir hata ayıklama akışı |
| 9 | Veri yerleşimi ve G/Ç başarımı |
| 10 | Yazılım ortamları: modüller, conda, kapsayıcılar |
| 11 | Güvenlik ve işletim iyi uygulamaları |
| 12 | Sık hatalar ve hızlı çözümler |
| 13 | Üretim öncesi denetim listesi |

## En çok kullanacağınız komutlar

```bash
sbatch job.sh                      # gönder
squeue -u $USER                    # kuyrukta veya çalışan işler
scontrol show job <JOBID>          # tek bir işin ayrıntıları
sacct -j <JOBID> --format=JobID,JobName,State,Elapsed,MaxRSS,ExitCode
scancel <JOBID>                    # iptal
sinfo                              # bölümler ve durumları
```

Aynı işlemler uygulama üzerinden de yapılabilir — bkz.
[[Slurm İşleri|Slurm-Jobs-TR]] — ve komut satırından da; `jobs list`,
`jobs status`, `jobs accounting`, `jobs submit` ve `jobs cancel` komutları
[[CLI Kılavuzu|CLI-Guide-TR]] sayfasında belgelenmiştir.

## Yeni bir kümede ilk işinizden önce

Her site; bölüm adları, hesap ve QOS sınırları, depolama yerleşimi ve modül
yığını bakımından farklıdır. Bir iş betiği yazmadan önce bunları denetleyin:

```bash
sinfo
module avail
```

Hesabınızın hangi bölümleri kullanabildiğini; zaman, CPU, bellek ve GPU
sınırlarının ne olduğunu; hangi depolama alanlarının bulunduğunu ve kota ile
temizlik ilkelerini doğrulayın. Uygulamadaki Slurm çıktı ayrıştırmasının site
özelleştirmesine göre değişmesinin nedeni tam olarak budur.

## Ayrıca bkz.

[[İş Betiği Şablonları|Job-Script-Templates-TR]] · [[Slurm İşleri|Slurm-Jobs-TR]] · [[Hızlı Başlangıç|Quick-Start-TR]]
