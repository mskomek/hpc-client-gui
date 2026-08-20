# X11 Yönlendirme

> English: [[X11-Forwarding]]

X11 yönlendirme, uzak bir **grafiksel** uygulamayı — MATLAB, ParaView ve
benzerleri — yerel ekranınızda gösterir. Toplu işler, terminal iş yükleri,
dosya aktarımları veya iş yönetimi için **gerekmez** ve kapalı bırakmanın hiçbir
maliyeti yoktur.

X11 arka planda çalışır. Ayrı bir X11 sekmesi yoktur: bağlantıda
etkinleştirirsiniz ve grafiksel uygulamaları komut olarak başlatırsınız.

## Etkinleştirme

Bağlantı formundaki **Enable X11 forwarding (for GUI apps)** seçeneği. İlgili
üç seçenek Ayarlar'da, Connection and X11 bölümünde bulunur:

- **When X11 is enabled, check/download/start required tools** — bağlanırken
  gerekli yardımcılar denetlenir ve eksikse onayınızla indirilip başlatılır.
- **Close VcXsrv when the app exits** — VcXsrv'i uygulama başlattıysa PID ile
  kapatılır.
- **Close X11/SSH processes on exit** — uygulamanın başlattığı plink/ssh
  süreçleri sonlandırılır.

## Windows: plink + VcXsrv

Windows'ta yol, `127.0.0.1:6000` üzerinde dinleyen **VcXsrv** X sunucusuyla
birlikte `plink.exe -X` şeklindedir.

**İkisi de çalıştırılabilir dosyayla birlikte gelmez.** Biri eksik olduğunda
hiçbir şey indirilmeden önce size sorulur — istem dosyanın adını ve boyutunu
belirtir — ve dilerseniz onları kendiniz kurabilirsiniz. Bir kurulum dosyası
için kararlı bir sağlama toplamı veya imza yoksa uygulama bunu söyler ve
çalıştırmadan önce yeniden sorar; reddetmek, sessizce devam etmek yerine
doğrulanmamış kurulum dosyasını geri çevirir.

Sık karşılaşılan hatalar ayrı ayrı bildirilir: `plink.exe` hazırlanamadı,
VcXsrv başlatılamadı (güvenlik duvarı veya izin sorunu), VcXsrv başlayıp hemen
çıktı ya da VcXsrv çalışıyor görünüyor ama 6000 portu hiç açılmadı.

Uzak bir grafiksel uygulamayı başlatmadan önce VcXsrv'i çalıştırın. Oturum
başladığında çalıştırılan komut ekrana yazılır ve pencere ayrı olarak açılır.

## Linux: sistem OpenSSH

Linux'ta X11 yönlendirme **sistem OpenSSH istemcisini** `-X` veya `-Y` ile
kullanır. Windows'un plink/VcXsrv yolunu **kullanmaz** ve hiçbir şey
indirilmez.

Gereksinimler: OpenSSH istemcisinin kurulu olması, zaten çalışan bir X sunucusu
(masaüstü oturumunuz) ve ortamda ayarlı bir `DISPLAY` değişkeni.

Başlatma bilinçli olarak etkileşimsizdir: yönlendirme hataları X11 olmadan
sessizce devam etmek yerine açıkça bildirilir ve ana bilgisayar anahtarı
denetimi profilin ilkesini izler — `strict` katı denetime, aksi hâlde
`accept-new` değerine karşılık gelir. Bu yolda parola ile kimlik doğrulama
denenmez, çünkü istem gizli bir konsolda görünüp kilitlenirdi; **Linux'ta
anahtar kullanın**.

## Hangi bayrak: `-X` mi `-Y` mi

`-Y` güvenilen yönlendirme, `-X` ise güvenilmeyen yönlendirmedir.
Güvenilmeyen yönlendirme daha kısıtlayıcıdır ve bazı uygulamalar altında
çalışmaz; güvenilen yönlendirme uzak uygulamaya yerel X sunucunuz üzerinde daha
fazla erişim verir. Bu seçimi bağlantı taşır.

## Destek özeti

| Senaryo | Durum | Notlar |
|---|---|---|
| Windows, plink + VcXsrv | Önerilen | Windows'ta en güvenilir yol |
| Herhangi bir platform, anahtarla OpenSSH | Destekleniyor | `ssh -X/-Y` |
| Parolayla OpenSSH | Sınırlı | Gizli istemler kilitleyebilir; Windows'ta plink, Linux'ta anahtar tercih edilir |

## Başarım

X11 yanıt süresi büyük ölçüde ağ kalitesine bağlıdır. Yüksek gecikmeli bir
bağlantıda uzak grafiksel uygulama yavaş hissettirir ve bunu telafi eden bir
istemci ayarı yoktur. Uzun etkileşimli oturumlar için sitenizin uzak masaüstü
veya web tabanlı bir seçeneği olup olmadığını sorun.

## Temizlik

Yardımcı süreçler uygulama kapanırken temizlenir ve sahipsiz kalan süreçler
savunmacı biçimde ele alınır. Yukarıdaki iki Ayarlar seçeneği, VcXsrv ile
X11/SSH süreçlerinin uygulamayla birlikte kapatılıp kapatılmayacağını
belirler.

## Ayrıca bkz.

[[Terminal ve Uzak Komutlar|Terminal-and-Remote-Commands-TR]] · [[Ayarlar Referansı|Settings-Reference-TR]] · [[Sorun Giderme|Troubleshooting-TR]]
