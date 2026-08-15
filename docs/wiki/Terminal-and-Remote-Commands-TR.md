# Terminal ve Uzak Komutlar

> English: [[Terminal-and-Remote-Commands]]

Uzakta bir şey çalıştırmanın iki yolu vardır: tek seferlik bir komut ya da
etkileşimli bir terminal.

## Tek seferlik komutlar

Bağlantı görünümünde bir **Command** alanı vardır — komutu yazıp Enter'a basın
ya da **Run** düğmesini kullanın. Çıktı konsolda görünür; hatalar uzak taraftan
gelen iletiyle bildirilir ve `STDERR`, standart çıktıdan ayrı gösterilir;
böylece bir hata normal çıktının içinde kaybolmaz.

Uygulamanın ayrıştırılmış görünümlerinin neye dayandığını denetlemenin en hızlı
yolu budur:

```text
squeue -u $USER
sinfo -o "%P %a %l %D %t"
```

## Etkileşimli terminal

Gömülü terminal, ana ve alternatif ekran arabelleği olan gerçek bir terminal
öykünücüsüdür — böylece bir düzenleyici ya da `htop` gibi tam ekran programlar
doğru davranır — ve bir geri kaydırma arabelleği taşır. Boyutu açıkça
belirtilebilir:

```bash
hpc-client-gui --profile mycluster terminal --cols 120 --rows 40
```

Dosya yöneticisindeki kabuk betikleri **Run in terminal** ile doğrudan buraya
gönderilebilir; bir seçim için **Run all in terminal** kullanılır.
Düzenleyicinin **Save + Run** eylemi de düzenlenen dosya için aynısını yapar.
Tamamlanma ve başarısızlık ayrı ayrı bildirilir.

## Komut geçmişi

Çalıştırdığınız komutlar, sonradan geri çağrılabilmesi için
`~/.truba_slurm_gui/history.jsonl` altındaki bir geçmişte tutulur.

Geçmiş, **gizli bilgi içeriyor gibi görünen komutları bilinçli olarak atlar**.
Süzgeç tasarım gereği ihtiyatlıdır: kararsız kaldığında komutu saklamaz. Doğru
denge budur — eksik bir geçmiş kaydı size yeniden yazma maliyeti çıkarır,
saklanan bir kayıt ise diskteki bir dosyaya kimlik bilgisi koyar.

Bir parolayı uzak bir komuta yapıştırmamanızın nedeni de budur. Anahtar tabanlı
kimlik doğrulamayı ya da betiklenmiş kullanım için `--password-stdin`
seçeneğini kullanın. Bkz. [[Betik Örnekleri|Scripting-Examples-TR]] ve
[[Güvenlik Modeli|Security-Model-TR]].

## Komut satırından

```bash
# Tek bir uzak komut; -- onu bu arayüzün kendi seçeneklerinden ayırır
hpc-client-gui --profile mycluster sh -- sacct -j 123456 --format=JobID,State,Elapsed

# Argümanlarla uzak bir betik
hpc-client-gui --profile mycluster run /scratch/$USER/analyze.sh input.csv

# Bu arayüzün kendisi için etkileşimli istem
hpc-client-gui --profile mycluster interactive
```

`sh` tek bir uzak komut çalıştırır; `run` uzak bir betik çalıştırır;
`interactive` ise uzak bir kabuk değil, bu uygulamanın kendi komutları için bir
istem açar. Bkz. [[CLI Komut Referansı|CLI-Command-Reference-TR]].

## Oturum düşerse

Düşen oturum, nedeniyle birlikte bildirilir ve yeniden bağlanma önerilir — `r`
tuşuna basın ya da Evet yanıtını verin. Bkz.
[[Bağlantı ve Profiller|Connecting-and-Profiles-TR]].

## Ayrıca bkz.

[[Betik Düzenleyici|Script-Editor-TR]] ·
[[X11 Yönlendirme|X11-Forwarding-TR]] ·
[[Slurm Yardım Kütüphanesi|Slurm-Help-Library-TR]]
