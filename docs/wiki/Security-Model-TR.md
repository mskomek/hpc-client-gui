# Güvenlik Modeli

> English: [[Security-Model]]

## Kapsam

Bu, **istemci tarafında** çalışan bir uygulamadır. Zaten hesabınızın olduğu
kümelere oturum açar, dosyalarınızı aktarır ve sizin adınıza zamanlayıcı
komutları çalıştırır. Uzak HPC altyapısını değiştirmez, kümeye hiçbir şey
kurmaz ve kendine ait bir sunucu bileşeni yoktur.

Kümenizin kendi ilkeleri — kimlik doğrulama gereksinimleri, tahsis sınırları,
X11 yönlendirmesine izin verilip verilmediği — yürürlükte kalır ve uygulamanın
gevşetebileceği ya da gevşettiği şeyler değildir.

## Kimlik bilgileri

- Parolalar ve belirteçler **komut geçmişine asla yazılmaz** ve arayüzde
  **asla gösterilmez**.
- Gizli değerler **asla günlüğe yazılmaz**. Komutlar günlükte görünebilir;
  onları çalıştırmak için kullanılan kimlik bilgileri görünmez.
- Bir profil parolasını kaydetmeyi seçerseniz düz metin yerine korunarak
  saklanır. Windows'ta bu, işletim sisteminin kendi veri koruma olanağını
  kullanır; ana parola yolu ise PBKDF2 ile bir anahtar türetir ve gizli değeri
  her kayıt için ayrı bir tuzla Fernet kullanarak şifreler.
- Bu veriyi barındıran `config.json`, tanılama paketlerinden bilinçli olarak
  dışarıda bırakılır. Bkz. [[Veri ve Gizlilik|Data-and-Privacy-TR]].

Otomasyon için anahtar tabanlı kimlik doğrulamayı tercih edin. Parola
kaçınılmazsa komut satırı argümanı veya ortam değişkeni yerine
`--password-stdin` ile verin — bkz.
[[Betik Örnekleri|Scripting-Examples-TR]].

## Ana bilgisayar anahtarları

İki ilke desteklenir:

| İlke | Bilinmeyen anahtar | Değişen anahtar |
|---|---|---|
| `accept-new` | Güvenip kaydetme, bir kerelik güvenme veya iptal sorulur | Her zaman reddedilir |
| `strict` | Reddedilir | Her zaman reddedilir |

Güvendiğiniz ve kaydettiğiniz anahtarlar `~/.truba_slurm_gui/known_hosts`
dosyasına yazılır. `--strict-host-key` seçeneği tek bir çağrı için katı ilkeyi
zorlar; gözetimsiz otomasyon için doğru seçim budur.

**Değişen** bir ana bilgisayar anahtarı her iki ilkede de her zaman
reddedilir. Ciddiye alınması gereken durum budur: ana bilgisayarın sunduğu
anahtar, güvendiğiniz anahtarla artık eşleşmiyor demektir. Bir şey yapmadan
önce yeni parmak izini bağlantının kendisi dışında bir kanaldan doğrulayın.
Hatayı susturmak için `known_hosts` girdisini silmek denetimi işlevsiz kılar.

## Dış komut satırı erişimi

Uzak CLI erişimi **öntanımlı olarak kapalıdır**. Ayarlar'daki "Allow external
CLI access to remote commands" seçeneği bunu denetler. Etkinleştirildiğinde, bu
uygulamanın komut satırı arayüzünü çalıştıran her yerel süreç kayıtlı
profillerinizi kullanarak uzak komutlara — dosyalar, işler, düzenleme, kabuk ve
tanılama — grafik oturum olmadan ve başka bir soru sorulmadan ulaşabilir.

Bunu bilinçli olarak ve yalnızca yerel süreçlere güvendiğiniz makinelerde
açın. Bkz. [[Ayarlar Referansı|Settings-Reference-TR]] ve
[[CLI Genel Bakış|CLI-Overview-TR]].

## Yıkıcı işlemler

Veriyi yok eden veya küme durumunu değiştiren işlemler açık onay gerektirir.
Komut satırında bu, `files rm`, `jobs submit`, `jobs cancel` ve
`profile delete` için `--yes` seçeneğidir; olmadan komut reddeder ve `2` ile
çıkar. Grafik arayüz bir iletişim kutusuyla sorar.

## İsteğe bağlı yardımcılar

Windows X11 yolu `plink.exe` ve VcXsrv kullanır; ikisi de uygulamayla birlikte
gelmez. Yalnızca indirmeyi onayladıktan sonra indirilirler ya da kendiniz
kurabilirsiniz. X11 yardımcı süreçleri uygulama kapanırken temizlenir ve
sahipsiz kalan süreçler çalışır durumda bırakılmak yerine savunmacı biçimde
ele alınır. Bkz. [[X11 Yönlendirme|X11-Forwarding-TR]].

## Güvenlik açığı bildirimi

Deponun Security sekmesindeki **Private Vulnerability Reporting** akışını
kullanın — genel bir bildirim, tartışma, pull request veya paylaşım değil.
Etkilenen sürümü ve işletim sistemini, kısa bir etki açıklamasını, sahte veya
tek kullanımlık veriyle yeniden üretme adımlarını ve kimlik bilgileri,
belirteçler, ana bilgisayarlar ve kişisel veriler çıkarılmış ilgili günlükleri
ekleyin.

Gerçek küme kimlik bilgileri eklemeyin. Yalnızca en son yayımlanan sürüm
güvenlik düzeltmesi alır; bildirmeden önce yükseltin. İlkenin tamamı depodaki
`SECURITY.md` dosyasındadır.

## Ayrıca bkz.

[[Veri ve Gizlilik|Data-and-Privacy-TR]] ·
[[Bağlantı ve Profiller|Connecting-and-Profiles-TR]] ·
[[Ayarlar Referansı|Settings-Reference-TR]]
