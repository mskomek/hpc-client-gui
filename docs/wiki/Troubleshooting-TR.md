# Sorun Giderme

> English: [[Troubleshooting]]

Gözlemlediğiniz duruma göre düzenlenmiştir. Her durumda ayrıntı
`~/.truba_slurm_gui/app.log` içindedir — bkz.
[[Günlükler ve Tanılama|Logs-and-Diagnostics-TR]].

## Uygulama başlamıyor

**Linux'ta `xcb` platform eklentisinden söz eden bir hatayla çıkıyor.**
Qt'nin platform kitaplıkları eksiktir. Kurun:

```bash
sudo apt install libegl1
```

Fedora ve openSUSE eşdeğerlerini kendi adlarıyla sunar. Bkz.
[[Linux Kurulumu|Installation-Linux-TR]].

**Windows'ta çalıştırılabilir dosyaya çift tıklayınca bir şey olmuyor.** ZIP
görüntüleyicisinin içinden çalıştırmak yerine ayıkladığınızdan emin olun ve
virüsten koruma ya da uygulama denetimi ilkesinin engelleyip engellemediğine
bakın. Bkz. [[Windows Kurulumu|Installation-Windows-TR]].

**Bir kez çalıştı, yükseltme veya sürüm düşürmeden sonra başarısız oluyor.**
Eski bir derleme, yeni bir derlemenin yazdığı yapılandırmayı anlamayabilir.
`~/.truba_slurm_gui/config.json` dosyasını başka yere taşıyın ve uygulamanın
yeniden oluşturmasına izin verin — profillerinizi yeniden girmeniz gerekir.

## Bağlantı başarısız

Yerel sorunları uzak sorunlardan ayıran tanılamayla başlayın:

```bash
hpc-client-gui doctor environment
hpc-client-gui --profile mycluster doctor connection
```

**Çıkış kodu 3.** Oturum açılamadı veya kimlik doğrulanamadı. Ana bilgisayar
adını, portu, kullanıcı adını ve anahtar yolunuzun doğru olup olmadığını
denetleyin. Var olmayan bir profil adı da bağlantı için istendiğinde `3`
üretir.

**Çıkış kodu 124.** İşlem zaman aşımına uğradı. `--timeout` değerini artırın ve
bu ağdan ana bilgisayara hiç ulaşıp ulaşamadığınıza bakın — VPN gerekliliği
sık rastlanan bir nedendir.

**Başka yerde çalışan bir anahtarla kimlik doğrulama başarısız oluyor.**
Profildeki anahtar yolunun özel anahtarı gösterdiğini ve kümenin eşleşen genel
anahtara sahip olduğunu doğrulayın. Bazı siteler anahtarın ayrıca
kaydedilmesini ister.

## Bilinmeyen veya değişen ana bilgisayar anahtarı

**Bilinmeyen anahtar.** `accept-new` ilkesinde güvenip kaydetmeniz, bir kerelik
güvenmeniz veya iptal etmeniz istenir. Güvenmek anahtarı
`~/.truba_slurm_gui/known_hosts` dosyasına kaydeder. `strict` ilkesinde ise
bağlantı reddedilir.

**Değişen anahtar.** Bu, her iki ilkede de her zaman reddedilir. Susturmak için
`known_hosts` girdisini silmeyin ve geçici çözüm olarak daha gevşek bir ilkeye
geçmeyin — ikisi de elinizdeki tek denetimi ortadan kaldırır. Yeni parmak izini
küme yöneticilerinizle bağlantının kendisi dışında bir kanaldan doğrulayın ve
değişikliğin meşru olduğunu öğrendikten sonra girdiyi güncelleyin.

## Komut satırı komutu çalışmayı reddediyor

**"Remote CLI access is disabled."** Dış erişim kapısı kapalıdır. Ayarlar'da
"Allow external CLI access to remote commands" seçeneğini etkinleştirin. Bkz.
[[CLI Genel Bakış|CLI-Overview-TR]].

**Silme, gönderme veya iptalde çıkış kodu 2.** Komut açık onay gerektirir.
`--yes` ekleyin. Bkz. [[CLI Çıkış Kodları|CLI-Exit-Codes-TR]].

## Aktarımlar

**Büyük bir aktarım kesildi.** `--if-exists resume` ile yeniden başlatın ya da
çakışma iletişim kutusunda sürdürmeyi seçin. Bkz.
[[Dosya Aktarımları|File-Transfers-TR]].

**Dosyanın sağlam ulaştığından emin olmak istiyorsunuz.** Aktarımdan sonra
SHA-256 denetleyen `--verify` seçeneğini kullanın veya `files checksum`
çıktısını yerel bir özetle karşılaştırın.

## Slurm çıktısı yanlış veya boş görünüyor

Slurm çıktısının ayrıştırılması site özelleştirmesine göre değişir ve komut
çıktısına karışan oturum açma başlıkları veya uyarılar bunu bozabilir. Uygulama
tahmin yürütmek yerine yumuşak biçimde başarısız olup ayrıntıyı günlüğe
yazacak şekilde yazılmıştır. Ham komutla karşılaştırın:

```bash
hpc-client-gui --profile mycluster sh -- squeue -u $USER
```

Ham çıktı doğru ama ayrıştırılmış görünüm değilse, o işlemin günlük kaydı bir
bildirime eklenecek şeydir.

## X11 uygulamaları görünmüyor

**Windows'ta.** Uzak uygulamayı başlatmadan önce VcXsrv'i çalıştırın ve
`plink.exe` dosyasının bulunduğunu doğrulayın. İkisi de isteğe bağlı
yardımcıdır ve çalıştırılabilir dosyayla birlikte gelmez.

**Linux'ta.** X11, sistem OpenSSH istemcisini kullanır. Kurulu olduğunu ve
oturumunuzda `DISPLAY` değişkeninin ayarlı olduğunu doğrulayın. Windows'un
plink/VcXsrv yolu burada geçerli değildir.

**Her şey bağlanıyor ama pencere yavaş.** X11 yanıt süresi büyük ölçüde ağ
kalitesine bağlıdır; yüksek gecikmeli bir bağlantıyı telafi eden bir istemci
ayarı yoktur. Bkz. [[X11 Yönlendirme|X11-Forwarding-TR]].

## Hâlâ takıldıysanız

Bir tanılama paketi dışa aktarın, okuyun ve bir bildirime ekleyin. Güvenlik
etkisi olan durumlarda bunun yerine gizli bildirim kanalını kullanın. Bkz.
[[Çökme Raporları ve Günlük Gönderme|Crash-Reports-and-Send-Logs-TR]] ve
[[Güvenlik Modeli|Security-Model-TR]].
