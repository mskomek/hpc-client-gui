# Günlükler ve Tanılama

> English: [[Logs-and-Diagnostics]]

## Günlük nerede

```text
~/.truba_slurm_gui/app.log
```

Windows'ta bu `C:\Users\<siz>\.truba_slurm_gui\app.log` yoludur. Dizin adı
eskiden kalmadır ve mevcut kurulumlarla uyumluluk için korunur — uygulamanın
belirli bir kümeye bağlı olduğu anlamına gelmez.

Günlük döngüseldir: eski içerik `app.log.1`, `app.log.2` ve devamına taşınır.
Diskteki günlük bilinçli olarak **maskelenmez**, çünkü yerel hata ayıklama
kaydınızdır. Maskeleme, bir günlüğün makineden ayrıldığı noktalarda yapılır —
bkz. [[Veri ve Gizlilik|Data-and-Privacy-TR]].

Yanında `crash.log` (çökme raporlayıcısının kaydı) ve `vcxsrv_stdout.log` /
`vcxsrv_stderr.log` (Windows'ta X11 yardımcı çıktısı) dosyalarını
bulabilirsiniz.

## Bir şeyler ters gittiğinde

Arayüz, donmak veya işe yaramaz bir iletişim kutusu göstermek yerine yanıt
vermeyi sürdürecek ve hatayı günlüğe yazacak şekilde tasarlanmıştır. Uzak bir
işlem başarısız olursa ilk bakılacak yer günlüktür; hata bildirimine eklemek
işi çok hızlandırır.

## Tanılama komutları

Üç `doctor` alt komutu yerel denetimleri, bağlanabilirliği ve gerçek bir
gidiş-dönüşü kapsar:

```bash
hpc-client-gui doctor environment
hpc-client-gui --profile mycluster doctor connection
hpc-client-gui --profile mycluster doctor smoke
```

| Komut | Ne yapar |
|---|---|
| `doctor environment` | Uygulamanın bağlı olduğu yerel ortamı denetler |
| `doctor connection` | Oturum açar ve dosya taşımasını başlatır |
| `doctor smoke` | Dosya taşıması üzerinden bir deneme dosyasını gidiş-dönüş aktarır |

`doctor smoke` iki seçenek kabul eder:

- `--keep`, uzak deneme dizinini silmek yerine korur; ne yazıldığını incelemek
  gerektiğinde yardımcı olur.
- `--artifact PATH`, deneme sonucunu JSON olarak yerel bir yola yazar;
  betiklenmiş denetimlerde istediğiniz budur.

Her komut standart çıkış kodu sözleşmesiyle sonuç bildirir; böylece bir betik
gerçek işe başlamadan bağlanabilirliği denetleyebilir:

```bash
hpc-client-gui --profile mycluster doctor connection || exit $?
```

Bkz. [[CLI Çıkış Kodları|CLI-Exit-Codes-TR]].

## Ayrıntıyı artırma

`--verbose` herhangi bir komutun çıktısına tanılama ekler; `--quiet` hata dışı
çıktıyı bastırır. Hiçbiri çıkış kodunu veya günlük dosyasını değiştirmez.

## Paket dışa aktarma

Günlük gönderme iletişim kutusu, bir bildirime ekleyebileceğiniz maskelenmiş
bir tanılama paketi toplar. Bkz.
[[Çökme Raporları ve Günlük Gönderme|Crash-Reports-and-Send-Logs-TR]].

## Ayrıca bkz.

[[Sorun Giderme|Troubleshooting-TR]] ·
[[Veri ve Gizlilik|Data-and-Privacy-TR]] ·
[[Güvenlik Modeli|Security-Model-TR]]
