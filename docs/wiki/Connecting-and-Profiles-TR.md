# Bağlantı ve Profiller

> English: [[Connecting-and-Profiles]]

## Bağlantı formu

| Alan | Notlar |
|---|---|
| **Host / IP** | Kümenin oturum açma düğümü |
| **Port** | SSH portu |
| **Username (optional)** | Küme hesabınız |
| **Password (optional)** | Anahtar kullanırken boş bırakın |
| **SSH key file (opt.)** | Özel anahtarınızın yolu; **Browse** dosya seçiciyi açar |
| **Enable X11 forwarding (for GUI apps)** | Yalnızca uzak grafiksel uygulamalar için gerekir |
| **Strict host key checking** | Bilinmeyen ana bilgisayar anahtarlarını sormak yerine reddeder |
| **Remember password** | Parolayı düz metin olarak değil, korunarak saklar |
| **Save profile** | Bağlantıyı yeniden kullanmak üzere saklar |
| **Simulation / Dry-run (UI test without a remote system)** | Arayüzü hiç küme olmadan inceler |

**Connect** oturumu başlatır; durum satırı *Connecting…* üzerinden *Connected*
durumuna geçer ya da kuru çalıştırmada *Mock mode (simulation)* bildirir.
**Disconnect** oturumu sonlandırır. **Console** paneli bağlantı ve SSH
iletilerini anlık gösterir — bir bağlantı kurulamadığında ilk bakılacak yer
burasıdır.

## Profil kaydetme

**Add Connection** iletişim kutusunu açar; **Save** profili saklar,
**Save & Connect** saklayıp hemen bağlanır. **Edit** var olan bir profili
değiştirir. Bir profilde kayıtlı parola varsa düzenlemek önce o parolanın
girilmesini gerektirir; doğrulama başarısız olursa profil değişmeden kalır.

Profil başına ek seçenekler:

- **Do not ask for the password again when connecting.**
- **Allow this connection to be used from the CLI** — genel dış erişim
  kapısının profil başına karşılığı.
- **Remember the encryption password for this Windows account.**
- **Profile transfer parallelism** — bu bağlantı için genel paralel aktarım
  sayısını geçersiz kılar.
- **SSH timeout (0 = default).**

Bir parola hesabınız için korunamıyorsa uygulama bunu söyler; sessizce
korumasız saklamaz.

## Sistem ön ayarları

Bir profil, uygulamanın kullandığı kümeye özgü komutları ve yolları da taşır;
böylece standart dışı araçlara sahip siteler kod değişikliği olmadan çalışır:

| Alan | Amacı |
|---|---|
| **System name** | Ön ayar için bir etiket |
| **Home directory**, **Job / scratch directory** | Dosya yöneticisinin açıldığı öntanımlı yollar |
| **List jobs command** | Normalde `squeue` |
| **Submit job command** | Normalde `sbatch` |
| **Cancel job command** | Normalde `scancel` |
| **Accounting command** | Normalde `sacct` |
| **Job details command** | Normalde `scontrol` |
| **Custom status command**, **Active job IDs command**, **Completed job state command** | Siteye özgü geçersiz kılmalar |

**System Defaults** standart kümeyi geri getirir. Ön ayarlar şablon olarak
kaydedilip (**Add as template**) yeniden kullanılabilir; hem sistem ön ayarları
hem de kendi kullanıcı şablonlarınız ön ayar menüsünde görünür.

## Ana bilgisayarı doğrulama

Bilinmeyen bir ana bilgisayara ilk bağlantıda sunucu kimliğini doğrulamanız
istenir; üç seçenek vardır: **Trust and save**, **Trust once** veya iptal.
Güvenip kaydetmek anahtarı `~/.truba_slurm_gui/known_hosts` dosyasına yazar.

**Strict host key checking** açıkken bilinmeyen bir anahtar sorulmadan
reddedilir. *Değişen* bir anahtar her iki ayarda da her zaman reddedilir. Bkz.
[[Güvenlik Modeli|Security-Model-TR]].

## Oturum düşerse

Uygulama düşen oturumu fark eder, nedenini bildirir ve yeniden bağlanmayı
önerir — `r` tuşuna basın ya da istemde Evet yanıtını verin. Komut yer tutucusu
oturumun kesildiğini anımsatacak biçimde değişir.

## Komut satırından

```bash
hpc-client-gui profile list
hpc-client-gui profile show mycluster
hpc-client-gui profile create mycluster --host login.example.org --user me --key ~/.ssh/id_ed25519
hpc-client-gui profile test mycluster
```

`profile create` ve `profile update` yalnızca gizli olmayan alanları kabul
eder; böylece hiçbir parola komut satırında görünmez. `profile delete`, `--yes`
gerektirir. Bkz. [[CLI Kılavuzu|CLI-Guide-TR]].

## Ayrıca bkz.

[[Hızlı Başlangıç|Quick-Start-TR]] · [[Ayarlar Referansı|Settings-Reference-TR]] · [[Sorun Giderme|Troubleshooting-TR]]
