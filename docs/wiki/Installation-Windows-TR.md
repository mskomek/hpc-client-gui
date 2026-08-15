# Windows Kurulumu

> English: [[Installation-Windows]]

Windows için önerilen kurulum **taşınabilir ZIP** paketidir. Python gerekmez.

## Kurulum

1. [Sürümler sayfasını](https://github.com/mskomek/hpc-client-gui/releases)
   açın ve 1.2.6 sürümü için Windows ZIP dosyasını indirin.
2. ZIP dosyasına sağ tıklayıp **Tümünü ayıkla** deyin. Yazma izniniz olan bir
   klasöre, örneğin kullanıcı profiliniz altındaki bir klasöre ayıklayın.
3. Ayıklanan klasördeki `hpc-client-gui.exe` dosyasını çalıştırın.

Uygulamayı doğrudan ZIP görüntüleyicisinin içinden çalıştırmak güvenilir
biçimde işlemez — önce ayıklayın.

## İlk çalıştırma

İlk açılışta küme sunucu adınız ve kullanıcı adınızla bir bağlantı profili
oluşturup bağlanın. Bkz.
[[Bağlantı ve Profiller|Connecting-and-Profiles-TR]].

Uygulama verileri — yapılandırma, döngüsel günlük ve kaydedilen ana bilgisayar
anahtarları — `~/.truba_slurm_gui` dizinine, yani
`C:\Users\<siz>\.truba_slurm_gui` yoluna yazılır. Dizin adı eskiden kalmadır ve
mevcut kurulumlarla uyumluluk için korunmaktadır.

## İsteğe bağlı X11 yardımcıları

X11 yönlendirmesi yalnızca uzak **grafiksel** uygulamalar için gereklidir.
Terminal iş yükleri, dosya aktarımları veya Slurm iş yönetimi için gerekmez.

Windows'ta iki dış bileşen devreye girer ve **ikisi de EXE ile birlikte
gelmez**:

- PuTTY'den `plink.exe` — uygulama X11 oturumları için `plink.exe -X`
  çalıştırır.
- **VcXsrv** — uzak uygulamayı görüntüleyen X sunucusu.

X11'i etkinleştirdiğinizde uygulama bu yardımcıları indirmeden önce onay
ister; dilerseniz kendiniz de kurabilirsiniz. Uzak bir grafiksel uygulamayı
başlatmadan önce VcXsrv'i çalıştırın. Ayrıntılar:
[[X11 Yönlendirme|X11-Forwarding-TR]].

## Kurumsal ortamlar

Güvenlik duvarı ve virüsten koruma ilkeleri çalıştırılabilir dosyayı, yardımcı
indirmelerini veya giden SSH bağlantısını engelleyebilir. Yönetilen
ortamlarda uygulamanın bağlanabilmesi için BT biriminizin onayı gerekebilir.

## Komut satırı arayüzü

Taşınabilir paket, kaynaktan kurulumla aynı komut satırı arayüzünü sunar. Bkz.
[[CLI Kılavuzu|CLI-Guide-TR]].

## Sonraki adımlar

[[Hızlı Başlangıç|Quick-Start-TR]] · [[Yükseltme ve kaldırma|Upgrading-and-Uninstalling-TR]] · [[Sorun Giderme|Troubleshooting-TR]]
