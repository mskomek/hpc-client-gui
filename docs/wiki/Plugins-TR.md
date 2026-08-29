# Eklentiler

HPC Client GUI, tek bir resmî kayıt defterinden gelen **bildirimsel
eklentileri** destekler. Sağ üstteki **Eklentiler** düğmesiyle Eklenti
Yöneticisi'ni açın; yükleme otomatik başlar (durum: *Eklentiler yükleniyor…*,
sonra *Çevrimiçi*, *Önbellek* veya *Çevrimdışı*).

## Eklentiler ne sağlar?

- **Küme profilleri** — *Bağlantı Profili → System Templates → Installed
  Plugins* altında site yolları ve zamanlayıcı komutları.
- **Slurm / çözücü iş şablonları** — editördeki *Şablondan Yeni...* ile kullanılır.
- **Lint kural paketleri** — editörün *Lint* eylemi uygular.

Plugin API v1 eklentileri yalnızca bildirimsel veri içerir: Python, betik ve
ikili dosya indirilmez/çalıştırılmaz. Her dosya aktivasyondan önce SHA-256
ile doğrulanır, kurulum tamamen masaüstünüzde olur (kümeye hiçbir şey
kurulmaz) ve kayıtlı bağlantı profilleriniz asla sessizce değiştirilmez.
Eklentiler *Kurulu* sekmesinden her an devre dışı bırakılabilir veya kaldırılabilir.

## Kurulu sürümler: Etkinleştirme ve geri alma

Bir eklentinin birden fazla kurulu sürümü varsa *Kurulu* sekmesinde sürüm
listesi görünür. Başlıkta gösterilen sürüm her zaman gerçekten etkin olan
sürümdür; sürümler numaraya göre sıralanır (1.10, 1.9'dan daha yenidir).
Bir sürüm seçip onaylayarak daha yenisini **etkinleştirebilir** veya eski bir
sürüme **geri dönebilirsiniz**:

- Geri alma işlemi kurulu hiçbir sürümü silmez.
- Eklentinin etkin/devre dışı durumu seçilen sürümden bağımsızdır.
- Etkinleştirme doğrulamayı geçemezse önceki etkin sürüm etkin kalır.
- Sürüm değiştirme arka planda çalışır; arayüz yanıt vermeye devam eder.

## Yerel bütünlük kontrolleri

Bir eklenti sürümü her yüklendiğinde veya etkinleştirildiğinde uygulama onu
yerel olarak yeniden doğrular: manifest, kurulum sırasında kaydedilen
SHA-256 değeriyle eşleşmelidir; bildirilen tüm dosyaların boyutu ve karması
doğrulanır; eklenti klasöründeki beklenmeyen ek dosyalar reddedilir. Bu
denetimleri geçemeyen eklenti, yeniden kurulum önerisiyle atlanır — otomatik
olarak asla silinmez, diğer sağlam eklentiler çalışmaya devam eder ve
doğrulanan daha eski bir sürüme elle geri dönüş yapılabilir.

Bu kayıt tutma başlamadan önce kurulmuş eski yüklemeler bir kez geçirilir:
dosyaları mevcut manifest'lerine göre doğrulanır ve ancak o zaman bu karma
başlangıç güven değeri olarak kaydedilir. Bu tek seferlik geçişin, kurulum
ile geçiş arasında oluşmuş değişiklikleri tespit edemediğini unutmayın.

## Eklenti isteği

Bir küme profili, çözücü şablonu veya lint paketi mi eksik? Yönetici
başlığındaki **Eklenti iste** düğmesini kullanın veya istek formunu doğrudan açın:

[Eklenti iste](https://github.com/mskomek/hpc-client-gui-plugins/issues/new?template=plugin-request.yml)

Sorun yönlendirme:

- Uygulama hataları (SSH/SFTP/FTP, arayüz, çökmeler, sürümler) →
  [hpc-client-gui sorunları](https://github.com/mskomek/hpc-client-gui/issues/new/choose)
- Eklenti istekleri ve içerik düzeltmeleri →
  [hpc-client-gui-plugins sorunları](https://github.com/mskomek/hpc-client-gui-plugins/issues/new/choose)

Tam kılavuz:
[PLUGINS_tr.md](https://github.com/mskomek/hpc-client-gui/blob/main/src/hpc_gui/docs/PLUGINS_tr.md)
