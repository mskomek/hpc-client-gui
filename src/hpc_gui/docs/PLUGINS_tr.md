# Eklentiler

HPC Client GUI, küme profilleri, iş şablonları ve lint kuralları sağlayan
**bildirimsel eklentileri** destekler. Plugin API v1 yalnızca veri dağıtır;
eklenti sistemi hiçbir zaman Python kodu, betik veya ikili dosya
indirmez/çalıştırmaz.

## Eklentiler düğmesi

Sağ üstteki kontrol şeridinde (Güncelle ve Günlük Gönder arasında) **Eklentiler**
düğmesi bulunur. Üç sekmeli Eklenti Yöneticisi'ni açar:

- **Keşfet** — resmi kayıt defteri kataloğuna göz atın. Yönetici açıldığında
  yükleme otomatik başlar (durum sırayla *Eklentiler yükleniyor…*, *Çevrimiçi*,
  *Önbellek*, *Çevrimdışı* olur); Yenile ile manuel kontrol yapılır.
- **Kurulu** — kurulu sürümleri görün; devre dışı bırak/etkinleştir veya kaldır.
- **Güncellemeler** — uyumlu yeni sürümler burada görünür; güncelleme her zaman
  sizin açık tercihinizdir (otomatik güncelleme yok).

Her Keşfet kartında eklenti adı/sürümü, yayıncı, kısa açıklama, çevrilmiş
yetenek rozetleri (*Küme profilleri*, *İş şablonları*, *Lint kuralları*),
çalışan uygulama sürümünüzle uyumluluk ve mevcut durum (kurulu, devre dışı,
uyumsuz, güncelleme var) görünür. **Ayrıntılar** tam kaydı gösterir: kimlik,
yayıncı, sürüm, lisans, uyumlu uygulama aralığı, yetenekler, açıklama, eski
sürümler, kurulum durumu ve kaynak (*Resmî eklenti kayıt defteri*).

Bir eklenti mi eksik? Yönetici başlığındaki **Eklenti iste** düğmesini
kullanın. Eklenti deposundaki özel istek formunu açar:

[Eklenti iste](https://github.com/mskomek/hpc-client-gui-plugins/issues/new?template=plugin-request.yml)

Uygun istekler: başka bir HPC merkezi desteği, yeni Slurm küme profili,
ileride değerlendirilmek üzere PBS/diğer zamanlayıcılar, ANSYS Fluent veya
OpenFOAM şablonları, journal/iş betiği lint kuralları, kuruma özgü yollar ve
kuyruklar. Uygulama hataları
[hpc-client-gui](https://github.com/mskomek/hpc-client-gui/issues/new/choose)
deposuna; eklenti istekleri ve içerik düzeltmeleri
[hpc-client-gui-plugins](https://github.com/mskomek/hpc-client-gui-plugins/issues/new/choose)
deposuna açılır.

## Resmi kayıt defteri ve çevrimdışı davranış

Eklentiler tek bir resmi kayıt defterinden gelir:

`https://raw.githubusercontent.com/mskomek/hpc-client-gui-plugins`

Kurulum **yalnızca seçilen eklenti sürümü için bildirilen dosyaları** indirir,
her baytı kayıt defterinde kayıtlı SHA-256 özetleriyle doğrular ve atomik
olarak etkinleştirir. Ağ erişimi yoksa bilinen son iyi katalog **Önbellek**
durumunda gösterilir; önbellek hiç yoksa yönetici **Çevrimdışı** durumunu
gösterir ve uygulama normal çalışmaya devam eder.

## Güvenlik modeli

- Kurulum asla eklenti içeriğini çalıştırmaz.
- Her manifest ve içerik dosyası aktivasyondan önce hash ile doğrulanır.
- Başarısız veya kurcalanmış kurulum mevcut duruma dokunmaz; başarısız
  güncellemeler otomatik olarak önceki aktif sürüme geri döner.
- Yayınlanmış eklenti sürümleri diskte değişmezdir: özdeş ve doğrulanmış bir
  sürümü yeniden kurmak idempotenttir; çelişen içerik uyarı bildirilir,
  üzerine yazılmaz.
- v1'de yalnızca resmi kayıt defteri desteklenir; özel kayıt defteri adresleri
  arayüzde sunulmaz.
- Eklentiler kayıtlı bağlantı profillerinizi sessizce değiştirmez: kayıtlı
  profiller kendi kopyalanmış ayar anlık görüntülerini korur.

## Kurulu sürümler, geri alma ve yerel bütünlük

*Kurulu* sekmesi gerçekten etkin olan sürümü gösterir ve kurulu tüm
sürümleri sıralar (1.10, 1.9'dan daha yenidir). Bir sürüm seçmek, açık
onaydan sonra daha yeni sürüm için **etkinleştirmeyi**, eski sürüm için
**geri almayı** sunar. Geri alma kurulu hiçbir sürümü silmez,
etkin/devre dışı tercihini sürümden bağımsız tutar ve doğrulama başarısız
olursa önceki etkin sürümü otomatik korur.

Her yükleme ve etkinleştirmede uygulama kurulu dosyaları yerel olarak yeniden
doğrular: manifest kurulumda kaydedilen hash ile eşleşmeli, bildirilen tüm
dosyaların boyutu ve SHA-256 değeri kontrol edilmeli, beklenmeyen ek dosyalar
reddedilmelidir. Denetimi geçemeyen eklenti yeniden kurulum önerisiyle
atlanır — asla silinmez — sağlam eklentiler yüklenmeye devam eder. Bu kayıt
tutmadan önce yapılmış kurulumlar bir kez geçirilir; tek seferlik bu geçiş
kurulum ile geçiş arasında oluşan değişiklikleri tespit edemez.

## Aktarımlar ve paralellik (ilgili ayar)

Bağlantı penceresindeki *Gelişmiş → En fazla eş zamanlı aktarım* ayarı kaç
dosyanın aynı anda yüklenecek/indirileceğini belirler. **Ayarlanan** değer
profile özgüdür; aktarım penceresi bağlantının **geçerli** limitini de
gösterir (arka uç yeteneğine veya sunucu sınırlarına göre daha düşük
olabilir). Birden çok dosya paralel gidebilir; tek büyük dosya şu anda
parçalara bölünerek aktarılmaz.

## Küme profilleri ve System Templates

Bağlantı penceresinde yerleşik olarak generic **Generic Slurm** şablonu gelir.
TRUBA eklentisini kurduğunuzda *System Templates → Installed Plugins* altında
TRUBA görünür. Uygulamak site yollarını ve zamanlayıcı komutlarını doldurur;
sonrasında her alanı düzenleyebilirsiniz.

Kayıtlı bağlantılar kendi kopyalanmış ayar anlık görüntülerini taşır; bu yüzden
eklentiyi kaldırmak veya güncellemek mevcut bağlantıları asla değiştirmez.
Şablon menüsünün altındaki *Daha fazla eklenti...* Eklenti Yöneticisi'ni açar.

## İş şablonları ve lint

Eklentiler iş betiği şablonları (editörde *Şablondan Yeni...*) ve bildirimsel
lint kural paketleri (editörün *Lint* eylemi) sağlayabilir. Şablonlar düz
yer tutucu değişimiyle üretilir, her zaman kaydedilmemiş bir sekmede incelemeye
açılır; kaydetme/gönderme tamamen size bağlıdır.

## Denetleyici araçları (Plugin API v2)

Plugin API v2 sözleşmesi, resmî kayıt defterinin **denetleyici araçları**
yayımlaması için hazırdır; bu sürümde ANSYS paketi henüz yayımlanmamıştır.
yayımlayabilir: alınan manifest/kurulum doğrulama zinciri içinde SHA-256 ile
sabitlenmiş, saf Python analiz motoru taşıyan isteğe bağlı eklentiler.
Kurulum sırasında hiçbir şey çalıştırılmaz; motor yalnızca aracı açtığınızda
tembel yükleme ile devreye girer.

Planlanan ilk denetleyici aracı **ANSYS Script & Journal Linter**
(`org.hpcclient.ansyslint`), Ansys journal/betikleri için gayriresmî,
çevrimdışı bir denetleyicidir: Fluent journal (TUI/Scheme), iç içe
`SendCommand` payload'ları da dahil Workbench `.wbjn`, Mechanical APDL
girdileri, CFX/CFD-Post/TurboGrid CCL oturum ve durum dosyaları, ICEM replay
betikleri, System Coupling betikleri ayrıca DesignModeler, Mechanical,
SpaceClaim/Discovery, Electronics Desktop ve Motion dosyaları için yapısal
tanıma sunar.

Kayıt defteri paketi yayımlanıp kurulduğunda **Kurulu** sekmesindeki kartında
**Aracı aç** düğmesi belirir.
Sayfa; dosya/klasör seçimi, manuel geçersiz kılma ile otomatik ürün algılama,
Ansys sürüm seçici (24.2 / 25.1 / 25.2 / 26.1), batch/headless/interactive
modu, Linux/Windows hedefi, önem filtreleri, tanı başına resmî kaynak
bağlantısı ve JSON/metin dışa aktarma sunar. Aynı motor, eklenti deposu
çıkışında CLI da sağlar (`scripts/ansys-journal-lint.py`).

ANSYS, Inc. tarafından geliştirilmemiştir, onaylanmaz; resmî dokümantasyonun
yerini tutmaz ve sezgisel bulguları açıkça etiketler — betiklerinizi kurulu
sürümünüze göre doğrulayın.

Türkçe sürüm bu sayfadır; İngilizcesi için [PLUGINS_en.md](PLUGINS_en.md).

Sağlayıcı yazma rehberi: [Türkçe](../../../docs/ADDING_CLUSTER_PROVIDER_tr.md) ·
[English](../../../docs/ADDING_CLUSTER_PROVIDER.md).

