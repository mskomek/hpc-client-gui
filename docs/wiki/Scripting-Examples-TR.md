# Betik Örnekleri

> English: [[Scripting-Examples]]

Etkileşimsiz kullanım için tarifler. Hepsinde iki kural geçerlidir:

1. **Hiçbir gizli değeri komut satırına koymayın.** Komut satırları diğer
   yerel süreçlerce görülebilir ve kabuk geçmişine kaydedilir. Anahtar tabanlı
   kimlik doğrulamayı tercih edin; parola kaçınılmazsa ekrana yansıtılmayan bir
   kaynaktan `--password-stdin` ile verin.
2. **İleti metnine değil çıkış koduna dallanın.** Bkz.
   [[CLI Kılavuzu|CLI-Guide-TR]].

Bunların çalışması için Ayarlar'da "Allow external CLI access to remote
commands" etkin olmalıdır — bkz. [[CLI Kılavuzu|CLI-Guide-TR]].

## Ortamın sağlıklı olduğunu denetleyin

```bash
hpc-client-gui doctor environment || exit $?
hpc-client-gui --profile mycluster doctor connection || exit $?
```

## Sonuçları listeleyin ve indirin

```bash
hpc-client-gui --profile mycluster --format json files ls /scratch/$USER/results
hpc-client-gui --profile mycluster files download \
  /scratch/$USER/results/out.csv ./out.csv --verify
```

`--verify`, aktarımdan sonra SHA-256 değerlerini karşılaştırır.

## Girdileri yükleyin, kesilen aktarımı sürdürün

```bash
hpc-client-gui --profile mycluster files upload \
  ./inputs /scratch/$USER/inputs --recursive --if-exists resume
```

## İş gönderin — **değiştirici, `--yes` gerektirir**

```bash
hpc-client-gui --profile mycluster jobs submit /scratch/$USER/job.sh --yes
```

`--yes` olmadan komut reddeder ve `2` ile çıkar.

## İş kuyruktan çıkana dek yoklayın

```bash
job_id=$1
while hpc-client-gui --profile mycluster --format json jobs status "$job_id" \
      | grep -q '"RUNNING"\|"PENDING"'; do
  sleep 60
done
```

Durum denetimini sitenizin `scontrol` çıktısına göre uyarlayın; Slurm çıktısı
site özelleştirmesine göre değişir.

## İş iptal edin — **değiştirici, `--yes` gerektirir**

```bash
hpc-client-gui --profile mycluster jobs cancel "$job_id" --yes
```

## Uzak dosya silin — **yıkıcı, `--yes` gerektirir**

```bash
hpc-client-gui --profile mycluster files rm /scratch/$USER/tmp --recursive --yes
```

## Tek bir uzak komut çalıştırın

```bash
hpc-client-gui --profile mycluster sh -- sinfo -o "%P %a %l %D %t"
```

`--` ayırıcısı zorunludur; böylece uzak komutun kendi seçenekleri bu arayüz
tarafından tüketilmez.

## Parolayı açığa çıkarmadan verme

Anahtar tabanlı kimlik doğrulama mümkün değilse, parolayı diske veya komut
satırına hiç yazmayan bir süreçten okuyun:

```bash
# Parola boruya yazılır, hiçbir yerde saklanmaz.
read -rs pw && printf '%s' "$pw" \
  | hpc-client-gui --profile mycluster --password-stdin --no-saved-password files ls /home
unset pw
```

`--no-saved-password`, profilde korunarak saklanan gizli değeri yok sayar ve
`--password-stdin` gerektirir; saklanan değerin bilinçli olarak atlanmasını
istediğiniz CI benzeri ortamlarda yararlıdır.

Parolayı bir betiğe, ortam değişkenine veya depoya gömmeyin. Bkz.
[[Güvenlik Modeli|Security-Model-TR]].

## Bilinmeyen ana bilgisayarlara karşı sıkılaştırın

```bash
hpc-client-gui --profile mycluster --strict-host-key jobs list
```

`--strict-host-key`, bilinmeyen ana bilgisayar anahtarlarını sormak yerine
reddeder; gözetimsiz otomasyon için doğru öntanım budur.

## Ayrıca bkz.

[[CLI Kılavuzu|CLI-Guide-TR]] · [[İş Betiği Şablonları|Job-Script-Templates-TR]]
