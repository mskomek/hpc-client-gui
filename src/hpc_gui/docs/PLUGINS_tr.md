# Eklentiler

HPC Client GUI, küme profilleri, iş şablonları ve lint kuralları sağlayan
**bildirimsel eklentileri** destekler. Plugin API v1 yalnızca veri dağıtır;
eklenti sistemi hiçbir zaman Python kodu, betik veya ikili dosya
indirmez/çalıştırmaz.

## Eklentiler düğmesi

Sağ üstteki kontrol şeridinde (Güncelle ve Günlük Gönder arasında) **Eklentiler**
düğmesi bulunur. Üç sekmeli Eklenti Yöneticisi'ni açar:

- **Keşfet** — resmi kayıt defteri kataloğuna göz atın.
- **Kurulu** — kurulu sürümleri görün; devre dışı bırak/etkinleştir veya kaldır.
- **Güncellemeler** — uyumlu yeni sürümler burada görünür; güncelleme her zaman
  sizin açık tercihinizdir (otomatik güncelleme yok).

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
- v1'de yalnızca resmi kayıt defteri desteklenir; özel kayıt defteri adresleri
  arayüzde sunulmaz.

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

Türkçe sürüm bu sayfadır; İngilizcesi için [PLUGINS_en.md](PLUGINS_en.md).
