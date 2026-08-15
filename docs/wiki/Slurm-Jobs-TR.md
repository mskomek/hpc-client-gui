# Slurm İşleri

> English: [[Slurm-Jobs]]

**Jobs & Outputs** alanı iş gönderme, izleme ve iptal etmeyi kapsar. Çıktı
takibinin kendi sayfası vardır: [[İş Çıktıları|Job-Outputs-TR]].

![Slurm Jobs](https://raw.githubusercontent.com/wiki/mskomek/hpc-client-gui/assets/jobs.png)

*İşler görünümü; geçerli kullanıcı için ayrıştırılmış `squeue` çıktısı.*

## Gönderme

Üçü de `sbatch` ile biten üç yol:

- Dosya yöneticisinden: **Submit with sbatch** ya da çoklu seçim için **Submit
  all with sbatch**. Toplu gönderim, kaç betiğin gönderildiğini ve kaçının
  başarısız olduğunu bildirir.
- Düzenleyiciden: **Submit (sbatch)** veya **Save + Submit**. Bkz.
  [[Betik Düzenleyici|Script-Editor-TR]].
- Komut satırından:

  ```bash
  hpc-client-gui --profile mycluster jobs submit /scratch/$USER/job.sh --yes
  ```

Başarılı bir gönderim **iş kimliğini** bildirir. Başarısız olursa ileti neye
bakılacağını önerir — hesap, bölüm, süre, bellek ve betiğin kendi
yönergeleri — ve hesabınız için geçersiz bir QOS ayrıca belirtilir; bu, sık
karşılaşılan ve kafa karıştırıcı biçimde ifade edilen bir Slurm reddidir.

## Kuyruğu izleme

**Jobs** görünümü işlerinizi bir **Refresh** eylemiyle listeler ve
yapılandırılan aralıkta kendiliğinden yenilenebilir. **Cluster Servers
(lssrv)** paneli küme kaynak durumunu kendi yenilemesiyle gösterir; komut
hiçbir şey döndürmez ya da başarısız olursa panel eski bir görünüm göstermek
yerine bunu söyler.

## İş ayrıntıları ve muhasebe

**Accounting & Job Details**, `sacct` ve `scontrol` sonuçlarını barındırır;
verilen bir **Job ID** için **Refresh sacct** ve **Show job details** eylemleri
vardır (kimlik zorunludur — eksikse görünüm bunu söyler). İşin **Script path**
değeri de yanında gösterilir.

`squeue`, `sacct` ve `lssrv` için kendiliğinden yenileme ayrı ayrı
yapılandırılır — bkz. [[Ayarlar Referansı|Settings-Reference-TR]].

## İptal

**Cancel Job**, seçili işi iptal eder. Komut satırında:

```bash
hpc-client-gui --profile mycluster jobs cancel 123456 --yes
```

`--yes` zorunludur; olmadan komut `2` ile çıkar. Bkz.
[[CLI Çıkış Kodları|CLI-Exit-Codes-TR]].

## Bildirimler

İzlenen bir iş sona erdiğinde uygulama bunu bildirir — başarıyla tamamlandı ya
da başka bir durumda sona erdi, durum adıyla birlikte. Öğrenmek için kuyruk
görünümünü açık tutmanız gerekmez.

## Gönderimden sonra

Sonrasında ne olacağı yapılandırılabilir: takipçi yok, var olan Outputs
sekmesi, yeni bir takip sekmesi, tek bir birleşik takip penceresi ya da ayrı
çıktı ve hata pencereleri. Bkz. [[İş Çıktıları|Job-Outputs-TR]] ve
[[Ayarlar Referansı|Settings-Reference-TR]].

## Site farklılıkları

Bu eylemlerin arkasındaki komutlar bağlantı profilinden gelir — `squeue`,
`sbatch`, `scancel`, `sacct`, `scontrol` ve isteğe bağlı özel durum komutları —
böylece farklı araçlara sahip bir site yamalanmak yerine yapılandırılır. Bkz.
[[Bağlantı ve Profiller|Connecting-and-Profiles-TR]].

Slurm çıktısının ayrıştırılması site özelleştirmesine göre değişir;
ayrıştırılmış bir görünüm yanlış görünüyorsa
[[Terminal ve Uzak Komutlar|Terminal-and-Remote-Commands-TR]] üzerinden ham
komutla karşılaştırın.

## Komut satırından

```bash
hpc-client-gui --profile mycluster jobs list
hpc-client-gui --profile mycluster jobs status 123456
hpc-client-gui --profile mycluster jobs accounting
hpc-client-gui --profile mycluster jobs lssrv
```

`squeue`, `scontrol`, `sacct`, `sbatch`, `scancel` ve `lssrv` takma adları
bunlara karşılık gelir. Bkz.
[[CLI Komut Referansı|CLI-Command-Reference-TR]].

## Ayrıca bkz.

[[İş Betiği Şablonları|Job-Script-Templates-TR]] ·
[[Slurm Yardım Kütüphanesi|Slurm-Help-Library-TR]] ·
[[İş Çıktıları|Job-Outputs-TR]]
