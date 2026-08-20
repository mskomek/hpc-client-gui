# Ayarlar Referansı

> English: [[Settings-Reference]]

**Settings** iletişim kutusundaki her seçenek, iletişim kutusunun kullandığı
bölümlere göre. Aşağıdaki etiketler arayüzün İngilizce metinleridir.

![Settings Reference](https://raw.githubusercontent.com/wiki/mskomek/hpc-client-gui/assets/settings.png)

*Ayarlar iletişim kutusu: Connection and X11, Jobs & Outputs ve File transfer.*

## Connection and X11

| Ayar | Ne yapar |
|---|---|
| **When X11 is enabled, check/download/start required tools** | Bağlanırken `plink.exe` ve VcXsrv denetlenir. Eksikse onayınızla indirilip başlatılır. |
| **Close VcXsrv when the app exits** | VcXsrv'i uygulama başlattıysa çıkışta PID ile kapatılır. |
| **Close X11/SSH processes on exit** | Uygulamanın başlattığı plink/ssh süreçlerini sonlandırır. |

X11'in kendisi bağlantı başına etkinleştirilir — bağlantı formundaki **Enable
X11 forwarding (for GUI apps)** seçeneği. Bkz.
[[X11 Yönlendirme|X11-Forwarding-TR]].

## Jobs & Outputs

| Ayar | Ne yapar |
|---|---|
| **Jobs & Outputs refresh interval (seconds)** | İşler ve çıktılar görünümlerinin yenilenme sıklığı. |
| **Live tracking warning interval (0 disables)** | Canlı takibin ne sıklıkla uyaracağı; `0` uyarıyı kapatır. |
| **Pause live following when minimized** | Pencere simge durumundayken canlı çıktı takibini durdurur. |
| **Open new follow windows minimized** | Yeni takip pencereleri simge durumunda açılır. |
| **Automatically refresh squeue** | Kuyruk görünümünü aralıkla yeniler. |
| **Automatically refresh sacct** | Muhasebe görünümünü aralıkla yeniler. |
| **Automatically refresh lssrv** | Kaynak görünümünü aralıkla yeniler. |
| **After sbatch submission, show output/error in** | Başarılı gönderimden sonra çıktının nerede takip edileceği. |

Gönderim sonrası takip seçiminin beş değeri vardır:

| Değer | Davranış |
|---|---|
| Takipçi açma | İşi kaydeder ve yeniler, geçerli görünümü değiştirmez |
| Jobs & Outputs — Outputs sekmesi | Var olan Output 1 ve Output 2 panellerinde sürer |
| Yeni takip sekmesi | Çıktı ve hatayı birlikte taşıyan yeni bir alt sekme |
| Tek birleşik takip penceresi | İkisini birlikte taşıyan bağımsız bir pencere |
| Ayrı çıktı ve hata pencereleri | İki bağımsız pencere |

Bkz. [[İş Çıktıları|Job-Outputs-TR]].

## File transfer

| Ayar | Ne yapar |
|---|---|
| **Default file transfer type** | Binary, ASCII veya otomatik. |
| **Default Home path** | Dosya yöneticisinin açıldığı uzak home yolu. |
| **Default Scratch path** | Uzak scratch yolu kısayolu. |
| **Parallel transfer count** | Kaç paralel yükleme ve indirmenin yalıtılmış kanal kullanacağı. Diğer dosya işlemleri sıralı kalır. |
| **Use remote directory listing cache** | Gezilen uzak klasörleri bellekte tutar; oluşturma, silme ve yenileme ilgili girdiyi günceller. |
| **Clear remote directory cache** | Önbelleği hemen boşaltır. |
| **Show upload plan confirmation** | Aktarım başlamadan önce nelerin yükleneceğini gösterir. |
| **Verify transfers with SHA-256 after completion** | Bir aktarımı başarılı saymadan önce kaynak ve hedef sağlama toplamlarını karşılaştırır. |
| **Remote test size** | Hız testinde kullanılan geçici dosya boyutu. |
| **Run remote transfer speed test** | Uzak arka uçta geçici bir dosyayı yükleyip indirir, doğrular, siler ve yükleme ile indirme hızlarını bildirir. |
| **Reset to defaults** | Dosya aktarım öntanımlarını geri getirir. |

Bkz. [[Dosya Aktarımları|File-Transfers-TR]].

## Komut satırı erişimi

| Ayar | Ne yapar |
|---|---|
| **Allow external CLI access to remote commands** | **Öntanımlı olarak kapalıdır.** Açıkken, bu uygulamanın komut satırı arayüzünü çalıştıran her yerel süreç kayıtlı profilleri kullanarak uzak komutlara — dosyalar, işler, düzenleme, kabuk, tanılama — grafik oturum olmadan ulaşabilir. |
| **Default CLI profile** | Bir komut satırı çağrısı `--profile` belirtmediğinde kullanılan profil. Boş bırakılabilir. |

Dış erişimi bilinçli olarak ve yalnızca yerel süreçlere güvendiğiniz
makinelerde açın. Bkz. [[Güvenlik Modeli|Security-Model-TR]] ve
[[CLI Kılavuzu|CLI-Guide-TR]].

## Local file associations

Dosya yöneticisinden uzak bir dosyayı açtığınızda belirli bir dosya türünü
hangi yerel programın açacağını seçin. Her ilişki değiştirilebilir veya
temizlenebilir; ayarlanmamış ilişkiler seçili değil olarak görünür.

## Dil

Arayüz dili — Türkçe veya İngilizce — uygulama içinde seçilir ve
`~/.truba_slurm_gui/language.json` dosyasında saklanır. Bkz.
[[Arayüz Dili ve i18n|Interface-Language-and-i18n-TR]].

## Ayrıca bkz.

[[Bağlantı ve Profiller|Connecting-and-Profiles-TR]] · [[Dosya Aktarımları|File-Transfers-TR]] · [[Güvenlik Modeli|Security-Model-TR]]
