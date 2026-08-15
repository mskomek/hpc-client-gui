# Küme Gereksinimleri

> English: [[Cluster-Requirements]]

**Benim HPC sistemimde çalışır mı?** Genellikle evet. Bu sayfa denetim
listesidir.

## Kümenin sağlaması gerekenler

| Gereksinim | Neden |
|---|---|
| Kendi hesabınızla SSH erişimi | Her oturum, komut ve aktarım bunun üzerinden yürür |
| SFTP alt sistemi | Öntanımlı dosya taşıması (alternatifi `--transport ftp`) |
| Slurm | İş özellikleri için `squeue`, `sbatch`, `scancel` |
| `sacct` | Muhasebe ve tamamlanmış iş geçmişi — önerilir, zorunlu değil |
| X11 yönlendirmesine izin | Yalnızca uzak grafiksel uygulamalara ihtiyacınız varsa |

Slurm yoksa bağlantı, dosya yöneticisi, aktarımlar, terminal ve düzenleyici
yine çalışır; yalnızca iş özellikleri kullanılamaz.

## Kümenin ihtiyaç duymadıkları

- **Sunucu bileşeni yok.** Bu projenin hiçbir parçası kümede çalışmaz.
- **Arka plan servisi veya daemon yok.**
- **Root erişimi gerekmez.**
- **Kümeye kurulum gerekmez** — ev dizininize bile.
- **Yönetici katılımı gerekmez.** Kümeye halihazırda bir SSH istemcisiyle
  ulaşabiliyorsanız bu uygulamayı da kullanabilirsiniz.

Bu, Slurm'ü sürmeyi bilen sıradan bir SSH ve SFTP istemcisidir. Sitenizin kendi
ilkeleri — kimlik doğrulama gereksinimleri, tahsis sınırları, X11'e izin verilip
verilmediği — yürürlükte kalır ve uygulamanın gevşetebileceği şeyler değildir.

## Kümenizi denetleme

Normal şekilde oturum açtıktan sonra kümede şunları çalıştırın:

```bash
sinfo                 # Slurm var ve bölümleri görebiliyorsunuz
squeue -u $USER       # kuyruğunuz okunabiliyor
sacct -u $USER        # muhasebe kullanılabilir (isteğe bağlı)
```

Ya da bir profil oluşturduktan sonra denetimi uygulamaya bırakın:

```bash
hpc-client-gui --profile mycluster doctor connection
hpc-client-gui --profile mycluster doctor smoke
```

`doctor smoke`, taşıma üzerinden gerçek bir dosyayı gidiş-dönüş aktarır; kurulumun
çalıştığına dair tek başına en güçlü denetim budur. Bkz.
[[Günlükler ve Tanılama|Logs-and-Diagnostics-TR]].

## Siteye özgü araçlar

Slurm komutlarını saran veya yeniden adlandıran siteler yamalanmaz,
yapılandırılır: her bağlantı profili kendi iş listeleme, gönderme, iptal,
muhasebe ve iş ayrıntısı komutlarını, ayrıca özel durum komutlarını taşır. Bkz.
[[Bağlantı ve Profiller|Connecting-and-Profiles-TR]].

Komut çıktısına karışan oturum açma başlıkları veya uyarılar Slurm çıktısının
ayrıştırılmasını bozabilir. Uygulama tahmin yürütmek yerine yumuşak biçimde
başarısız olur ve ayrıntıyı günlüğe yazar — bkz.
[[Sorun Giderme|Troubleshooting-TR]].

## Ayrıca bkz.

[[Uyumluluk ve Destek Matrisi|Compatibility-and-Support-Matrix-TR]] ·
[[Hızlı Başlangıç|Quick-Start-TR]] ·
[[X11 Yönlendirme|X11-Forwarding-TR]]
