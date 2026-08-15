# CLI Genel Bakış

> English: [[CLI-Overview]]

Uygulama, masaüstü arayüzünün yanında bir komut satırı arayüzü de sunar.
Amacı, bağlantı profillerinin, dosya işlemlerinin ve Slurm iş işlemlerinin
grafik oturum olmadan betiklenebilmesidir.

## Çağırma

```bash
python -m hpc_gui --help
```

Yardım çıktısında görünen program adı `hpc-client-gui` şeklindedir. Paketli
Windows ve Linux derlemeleri aynı arayüzü sunar.

## Komutları keşfetme

```bash
hpc-client-gui commands
hpc-client-gui --format json commands
```

`commands`, komut ağacının tamamını, her seçeneği, takma ad tablosunu ve çıkış
kodu tablosunu yazdırır. Yetkili envanter budur; bu wiki onu
[[CLI Komut Referansı|CLI-Command-Reference-TR]] sayfasında yansıtır.

## Dış erişim kapısı

Uzak komutlar bir kapı ardındadır. Ayarlar'daki **"Allow external CLI access to
remote commands"** seçeneği **öntanımlı olarak kapalıdır**. Kapalıyken kümeye
ulaşan komutlar çalışmayı reddeder ve şunu yazdırır:

> Remote CLI access is disabled. Enable "Allow external CLI access to remote
> commands" in Settings to use this command.

Seçenek açıkken, bu uygulamanın komut satırı arayüzünü çalıştıran her yerel
süreç kayıtlı profilleri kullanarak uzak komutlara — dosyalar, işler,
düzenleme, kabuk ve tanılama — grafik oturum olmadan ulaşabilir. Ayarlar
ayrıca bir komut `--profile` belirtmediğinde kullanılacak öntanımlı CLI
profilini seçmenize izin verir. Bkz.
[[Ayarlar Referansı|Settings-Reference-TR]] ve
[[Güvenlik Modeli|Security-Model-TR]].

## Genel seçenekler

Bunlar her komut için geçerlidir ve tam listesi
[[CLI Komut Referansı|CLI-Command-Reference-TR]] sayfasındadır:

| Seçenek | Amacı |
|---|---|
| `--format {text,json}` | Komut sonuçları için çıktı biçimi |
| `--quiet` | Hata dışı çıktıyı bastırır |
| `--verbose` | Ayrıntılı tanılamayı açar |
| `--timeout TIMEOUT` | Saniye cinsinden öntanımlı işlem zaman aşımı |
| `--profile PROFILE` | Kayıtlı bağlantı profili adı |
| `--host`, `--port`, `--user`, `--key` | Çağrı başına bağlantı geçersiz kılmaları |
| `--transport {sftp,ftp}` | Dosya taşıması, öntanımlı `sftp` |
| `--password-stdin` | Oturum parolasını stdin'den okur |
| `--password-prompt` | Ekrana yansıtmadan sorar (yalnızca terminal) |
| `--no-saved-password` | Profilde saklanan gizli değeri yok sayar |
| `--strict-host-key` | Bilinmeyen ana bilgisayar anahtarlarını reddeder |

## Çıktı ve çıkış kodları

Sonuçlar metin veya JSON olarak yazdırılır ve her çağrı belgelenmiş bir çıkış
koduyla sonlanır. Otomasyon, ileti metnine değil çıkış koduna dallanmalıdır.
Bkz. [[CLI Çıktı Sözleşmesi|CLI-Output-Contract-TR]] ve
[[CLI Çıkış Kodları|CLI-Exit-Codes-TR]].

## Sonraki adımlar

[[CLI Komut Referansı|CLI-Command-Reference-TR]] ·
[[Betik Örnekleri|Scripting-Examples-TR]]
