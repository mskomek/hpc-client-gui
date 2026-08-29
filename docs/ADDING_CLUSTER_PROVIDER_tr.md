# Küme sağlayıcısı ekleme

En kısa başarılı yol, bildirimsel ve küçük bir sağlayıcı profili hazırlamaktır.
Sağlayıcı paketleri uygulama kaynak koduna değil,
[plugin deposuna](https://github.com/mskomek/hpc-client-gui-plugins) eklenir.

1. Depodaki minimal sağlayıcı şablonunu kopyalayın.
2. Sağlayıcı kimliği, profil kimliği, görünen ad, desteklenen zamanlayıcı ve
   gereken minimum uygulama sürümünü girin.
3. Yalnızca doğrulanmış yolları, Slurm varsayılanlarını ve herkese açık yardım
   bağlantılarını ekleyin.
4. Kota ve bilmediğiniz diğer alanları boş veya devre dışı bırakın.
5. Profil, README ve manifesti birlikte doğrulayıp paketleyin.
6. Üretilen paket ve doğrulama sonuçlarıyla registry pull request’i açın.

## İsteğe bağlı kota

Kota, kullanılabilir bir sağlayıcı için gerekli değildir. Eksik, null, boş veya
yalnızca boşluklardan oluşan kota komutu; kota isteği, probe, timer, retry veya
dosya sistemi taraması oluşturmaz. Bilinen yollar ve yardım metni kullanılmaya
devam eder.

Yalnızca incelenmiş ve güvenli komut sözleşmesi olan bir backend canlı kota
verisi sağlayabilir. Başka bir kümeden komut kopyalamayın; kimlik bilgisi,
shell hook’u, login banner ayrıştırması veya `df`, `du`, `find` tabanlı tahmin
eklemeyin.

## Herkese açık profile ait bilgiler

- sağlayıcı ve profil kimlikleri;
- Slurm komut şablonları ve gizli olmayan varsayılanlar;
- bilinen home, scratch, project veya özel yollar;
- kuyruk/hesap yönlendirmeleri ve yazılım notları;
- herkese açık dokümantasyon ve destek bağlantıları;
- bilinmeyen olduğu açıkça belirtilen isteğe bağlı politika notları.

Kullanıcı adlarını, hesap yetkilerini, parolaları, özel endpoint’leri, VPN
ayarlarını, ölçülmüş kullanımı ve canlı hesap verilerini public pakete koymayın.

## Doğrulama kontrol listesi

- Minimal örneği kota alanları olmadan doğrulayın.
- İsteğe bağlı alanları boş/devre dışı full örneği doğrulayın.
- Placeholder sözdizimini ve public URL’leri kontrol edin.
- Manifestte her dosyanın boyut ve SHA-256 hash değerinin bulunduğunu kontrol edin.
- Mevcut yayınlanmış sürüm dizininin değişmediğini doğrulayın.
- Sağlayıcıyı cluster bağlantısı olmadan yüklemeyi test edin.

Uygulama hataları için [uygulama issue chooser](https://github.com/mskomek/hpc-client-gui/issues/new/choose),
provider içeriği veya registry talepleri için
[plugin deposunu](https://github.com/mskomek/hpc-client-gui-plugins/issues/new/choose) kullanın.
