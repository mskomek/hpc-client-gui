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
- **Close X11/SSH processes on exit** — uygulamanın başlattığı X11 yardımcıları
  kapatılır; SSH aktarma kanalları terminalle birlikte kapanır.

## Windows: Paramiko + VcXsrv

Etkin Paramiko SSH terminali, uzak PTY ve kabuğu açmadan önce X11 yönlendirme
isteği gönderir. Uzak pencereleri yerel ekranda **VcXsrv** gösterir. Plink veya
ikinci bir SSH süreci kullanılmaz.

VcXsrv uygulamayla birlikte gelmez; resmi kaynağından kurun. Uygulama VcXsrv'i
başlatırsa özel MIT-MAGIC-COOKIE yetki dosyası sağlar ve `-ac` kullanmaz.
VcXsrv tüm arayüzlerde dinliyorsa uygulama yalnızca kendi sürecini, yetki
dosyasını, ilgili çalıştırılabilir dosyanın güvenlik duvarı kurallarını, etkin
güvenlik duvarı profillerini ve gelen bağlantılar için engelleme varsayılanını
doğrularsa kabul eder. Aksi durumda sunucuyu reddeder; başka bir wildcard
dinleyici hiçbir zaman kabul edilmez.

Profildeki SSH anahtarı, agent, parola ve host-key ilkesi korunur. Parola veya
çerez uygulama günlüğüne yazılmaz. Yerel X sunucusu veya MIT çerezi yoksa
X11 seçiliyse kabuk açılmaz; uygulama yönlendirmesiz kabuğa sessizce geçmez.
X11 kapalıyken normal SSH kullanılabilir. Uzak sunucuda X11 yönlendirmesi etkin ve `xauth` kurulu olmalıdır; istek başarılı olunca
`DISPLAY` değerini `sshd` atar (genelde `localhost:10.0`).

Yalnızca etkileşimli SSH terminaline yazılan komutlar X11'i kullanır. Uzak
`exec_command` çağrıları ve toplu işler bu DISPLAY'i devralmaz.

## Linux ve macOS: yerel masaüstü X sunucusu

Etkin Paramiko terminali yerel masaüstü X sunucusunu kullanır. Linux masaüstü
Xorg veya Xwayland sağlayabilir; macOS'ta XQuartz gerekir. Süreç geçerli bir
`DISPLAY` ve `XAUTHORITY` veya `xauth` ile erişilen MIT çerezini devralmalıdır.
Entegre terminal yönlendirmesi için sistem OpenSSH gerekmez.

## Kimlik doğrulama ve güven

Varsayılan olarak uygulama, X11 SECURITY uzantısıyla yerel X sunucusundan
**güvenilmeyen** çerez ister. Uzantı yoksa yönlendirme kapalı kalır. Profildeki
ayrı **Güvenilir X11 kullan** seçeneği, güvenilir yönlendirme gerektiren
sunucular içindir; uzak programın yerel ekranı denetleyebileceği konusunda
uyarır. SSH kanalı rastgele çerezi yalnızca bağlantı paketi eşleşince değiştirir.
MIT çerez doğrulaması kimliği kanıtlar; güvenilmeyen SECURITY çerezinin
sağladığı yalıtımı sağlamaz. `xhost +` veya kimlik doğrulamasız X sunucusu
kullanmayın.

## Destek özeti

| Senaryo | Durum | Notlar |
|---|---|---|
| Windows, Paramiko + VcXsrv | Destekleniyor | Kimlik doğrulamalı; wildcard dinleme için firewall izolasyonu doğrulanır |
| Linux/macOS masaüstü X sunucusu | Destekleniyor | `DISPLAY`, `xauth` ve trusted modu seçilmediyse SECURITY desteği gerekir |
| X11 yönlendirmesi kapalı SSH sunucusu | Desteklenmiyor | X11 seçili kabuk reddedilir; X11 kapalı bağlantı etkilenmez |

## Başarım

X11 yanıt süresi büyük ölçüde ağ kalitesine bağlıdır. Yüksek gecikmeli bir
bağlantıda uzak grafiksel uygulama yavaş hissettirir ve bunu telafi eden bir
istemci ayarı yoktur. Uzun etkileşimli oturumlar için sitenizin uzak masaüstü
veya web tabanlı bir seçeneği olup olmadığını sorun.

## Temizlik

Etkileşimli SSH oturumu kapanınca X11 aktarma kanalları da kapanır. Uygulama
VcXsrv'i başlattıysa mevcut Ayarlar seçeneği, uygulama kapanırken bu sürecin
kapatılıp kapatılmayacağını belirler.

## Ayrıca bkz.

[[Terminal ve Uzak Komutlar|Terminal-and-Remote-Commands-TR]] · [[Ayarlar Referansı|Settings-Reference-TR]] · [[Sorun Giderme|Troubleshooting-TR]]
