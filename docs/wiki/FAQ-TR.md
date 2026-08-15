# SSS

> English: [[FAQ]]

## Python gerekli mi?

Paketli derlemeler için hayır. Windows taşınabilir ZIP ile Linux AppImage ve
`.deb` paketleri ihtiyaç duydukları her şeyi içerir. Python 3.10+ yalnızca
kaynaktan çalıştırırken gerekir.

## Bu, kümemin veya kurumumun resmî aracı mı?

Hayır. Bağımsız, sağlayıcıdan bağımsız bir topluluk projesidir. Hiçbir küme
işletmecisi veya satıcıyla bağlantılı değildir ve zaten erişiminiz olan her
Slurm tabanlı sistemle çalışır.

## Kümede bir şeyi değiştiriyor mu?

Yalnızca sizin istediğinizi: dosyalarınızı ve gönderdiğiniz ya da iptal
ettiğiniz işleri. İstemci tarafındadır; HPC altyapısını değiştirmez, kümeye bir
şey kurmaz ve site yapılandırmasını bozmaz.

## Hangi kümelerle çalışır?

SSH erişiminin bulunduğu, Slurm komutlarının var olduğu (`sbatch`, `squeue`,
`sacct`, …) ve — yalnızca uzak grafiksel uygulamalara ihtiyacınız varsa — X11
yönlendirmesine izin verilen her sistemle. Bkz.
[[Uyumluluk ve Destek Matrisi|Compatibility-and-Support-Matrix-TR]].

## Veri dizininin adı neden `.truba_slurm_gui`?

Proje yeniden adlandırıldıktan sonra mevcut kurulumların çalışmayı sürdürmesi
için korunan eski bir addır. Yeniden adlandırmak herkesin kayıtlı profillerini
ve güvenilen ana bilgisayar anahtarlarını sahipsiz bırakırdı; bu yüzden
kalıyor.

## Günlük nerede?

`~/.truba_slurm_gui/app.log`, döngüsel. Bkz.
[[Günlükler ve Tanılama|Logs-and-Diagnostics-TR]].

## X11'e ihtiyacım var mı?

Yalnızca MATLAB veya ParaView gibi uzak grafiksel uygulamalar için. Terminal iş
yükleri — Python betikleri, toplu çözücüler, eğitim işleri — buna ihtiyaç
duymaz.

## X11 neden Windows ve Linux'ta farklı çalışıyor?

Gerçekten farklı mekanizmalar kullanırlar. Windows, X sunucusu olarak
VcXsrv ile `plink.exe -X` çalıştırır; Linux, sistem OpenSSH istemcisini
(`ssh -X/-Y`) kullanır. Windows yardımcılarının hiçbiri Linux'ta kullanılmaz.
Bkz. [[X11 Yönlendirme|X11-Forwarding-TR]].

## Parolalarım güvende mi?

Komut geçmişine hiç yazılmaz, arayüzde hiç gösterilmez ve gizli değerler asla
günlüğe yazılmaz. Kaydedilen bir profil parolası düz metin yerine korunarak
saklanır. Otomasyon için anahtarları tercih edin. Bkz.
[[Güvenlik Modeli|Security-Model-TR]].

## Komut satırı neden uzak erişimin kapalı olduğunu söylüyor?

"Allow external CLI access to remote commands" öntanımlı olarak kapalıdır.
Kümeye karşı betik yazmak istiyorsanız Ayarlar'dan etkinleştirin. Bkz.
[[CLI Kılavuzu|CLI-Guide-TR]].

## Silme veya gönderme komutum neden 2 koduyla çıktı?

`--yes` gerekiyordu. Veriyi yok eden veya küme durumunu değiştiren komutlar
açık onay olmadan çalışmayı reddeder. Bkz.
[[CLI Kılavuzu|CLI-Guide-TR]].

## Kesilen bir aktarımı sürdürebilir miyim?

Evet — komut satırında `--if-exists resume`, arayüzde çakışma iletişim
kutusundaki sürdürme seçeneği. Bkz.
[[Dosya Aktarımları|File-Transfers-TR]].

## Günlüğümü herkese açık bir bildirime eklemek güvenli mi?

Ham günlük yerine tanılama paketini dışa aktarın: paket maskelenmiştir ve
kayıtlı profillerinizi içermez. Sonra eklemeden önce okuyun — maskeleme elden
gelenin en iyisidir ve hiç görmediği tanımlayıcıları bilemez. Bkz.
[[Veri ve Gizlilik|Data-and-Privacy-TR]].

## İş yerimde kullanabilir miyim?

Ticari olmayan kullanım PolyForm Noncommercial License 1.0.0 kapsamındadır.
Ticari kullanım ayrı bir lisans gerektirir. Bkz.
[[Lisanslama ve Ticari Kullanım|Licensing-and-Commercial-Use-TR]].

## Arayüz dilini nasıl değiştiririm?

Türkçe ve İngilizce yerleşiktir ve uygulama içinde değiştirilebilir. Bkz.
[[Arayüz Dili ve i18n|Interface-Language-and-i18n-TR]].

## Hata veya özellik isteğini nasıl bildiririm?

GitHub bildirimleri üzerinden. Güvenlik etkisi olan her şey için bunun yerine
gizli bildirim kanalını kullanın. Bkz.
[[Destek ve Bağış|Support-and-Donations-TR]] ve
[[Güvenlik Modeli|Security-Model-TR]].
