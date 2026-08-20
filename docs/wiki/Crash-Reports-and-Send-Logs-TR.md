# Çökme Raporları ve Günlük Gönderme

> English: [[Crash-Reports-and-Send-Logs]]

## Çökme raporlayıcı

Uygulama beklenmedik biçimde sonlanırsa `~/.truba_slurm_gui` altına bir çökme
kaydı ve bir çökme bayrağı yazar. Bir sonraki başlangıçta bayrak algılanır ve
bir çökme iletişim kutusu sunulur; böylece ayrıntılar hâlâ elde edilebilirken
durumu bildirebilirsiniz. İşlendikten sonra bayrak temizlenir ve iletişim
kutusu yeniden görünmez.

## Günlük gönderme iletişim kutusu

Bu iletişim kutusu, makinenizden hiçbir şey ayrılmadan önce toplanan günlük
metnini gösterir ve iki eylem sunar:

![Crash Reports and Send Logs](https://raw.githubusercontent.com/wiki/mskomek/hpc-client-gui/assets/send-logs.png)

*Günlük gönderme iletişim kutusu. Maskelemeye dikkat: hesap adı ve ana bilgisayar zaten `<user>` ve `<host>` olarak görünüyor.*

- **Panoya kopyala** — görüntülenen metni kopyalar; bir bildirime
  yapıştırabilirsiniz.
- **Tanılamayı dışa aktar** — seçtiğiniz bir konuma ZIP paketi yazar.

Kopyalamadan veya eklemeden önce görüntülenen metni gözden geçirin. Son
denetim sizsiniz.

## Paketin içeriği

`create_diagnostic_bundle`, `~/.truba_slurm_gui` altındaki şu dosyaları —
varsa — toplar:

| Dosya | İçeriği |
|---|---|
| `app.log` | Uygulama günlüğü |
| `history.json`, `history.jsonl` | Komut ve iş geçmişi |
| `last_batch.json` | En son toplu gönderim kaydı |
| `processes.json` | İzlenen yardımcı süreçler |
| `transfer_journal.jsonl` | Sürdürme için kullanılan aktarım günlüğü |
| `vcxsrv_stdout.log`, `vcxsrv_stderr.log` | X11 yardımcı çıktısı (Windows) |
| `language.json` | Seçilen arayüz dili |
| `manifest.json` | Oluşturma zaman damgası ve paket adı (dışa aktarma ekler) |

Her metin dosyası ZIP'e yazılmadan önce maskelemeden geçer. Metin olarak
okunamayan bir dosya sessizce atılmak yerine olduğu gibi eklenir; böylece
hiçbir şey haberiniz olmadan kaybolmaz.

## Paketin bilinçli olarak dışarıda bıraktığı

`config.json` **asla** dâhil edilmez. Kayıtlı bağlantı profillerinizi — ana
bilgisayar adları ve kullanıcı adları — ve şifrelenmiş parola verisiyle tuz
değerlerini barındırır. Bunların hiçbiri günlüklerden hata ayıklamak için
gerekli değildir; bu yüzden "günlüklerini gönder" paketinde yolculuk etmezler.

## Maskeleme ne yapar

Maskeleme; yerel hesap adınızı, kayıtlı her profilin uzak kullanıcı adını ve
kayıtlı her profilin ana bilgisayar adını veya IP'sini `<user>` ve `<host>` ile
değiştirir. Bu, yolların içinde de çalışır: `/home/adiniz/run.sh` ve
`C:\Users\adiniz\...` sırasıyla `/home/<user>/run.sh` ve `C:\Users\<user>\...`
olur.

Maskeleme, garanti değil, elden gelenin en iyisi olan bir örüntü değişimidir.
Profil olarak hiç kaydetmediğiniz bir ana bilgisayar adını ya da yalnızca
kendi iş çıktınızda geçen bir tanımlayıcıyı bilemez. Paylaşmadan önce paketi
okuyun.

Ayrıntılar: [[Veri ve Gizlilik|Data-and-Privacy-TR]].

## Bildirim

Paketi bir GitHub bildirimine ekleyin. Güvenlik etkisi olan her şey için genel
bir bildirim yerine `SECURITY.md` içinde anlatılan gizli kanalı kullanın —
bkz. [[Güvenlik Modeli|Security-Model-TR]].

## Ayrıca bkz.

[[Günlükler ve Tanılama|Logs-and-Diagnostics-TR]] · [[Sorun Giderme|Troubleshooting-TR]] · [[Destek ve Bağış|Support-and-Donations-TR]]
