# Katkıda Bulunma

> English: [[Contributing]]

Bildirimler ve pull request'ler
[GitHub](https://github.com/mskomek/hpc-client-gui) üzerinden ilerler. Güvenlik
etkisi olan her şey için genel bir bildirim yerine gizli bildirim kanalını
kullanın — bkz. [[Güvenlik Modeli|Security-Model-TR]].

## Başlamadan önce

- [[Mimari|Architecture-TR]] sayfasını okuyun. İnceleme geri bildirimlerinin
  çoğu, kodun yanlış katmana inmesiyle ilgilidir.
- Çevrimdışı paketi ve yardımcı denetimleri yerelde çalıştırın — bkz.
  [[Test ve CI|Testing-and-CI-TR]]. Her CI işi engelleyicidir.

## İncelemede sık çıkan kurallar

**Her zaman iki dil.** Kullanıcıya görünen her metin hem Türkçe hem İngilizce
bulunmalıdır. `scripts/check_i18n.py`, anahtar sapmasında, arayüz kodundaki
sabit metinlerde ve var olmayan çeviri anahtarlarına yapılan referanslarda
başarısız olur. Yalnızca İngilizce bir metin eklemek CI'ı kırar.

**Qt katmanını ince tutun.** Mantık bir bileşenin dışında test edilebiliyorsa
bir servise aittir. Çevrimdışı paketi mümkün kılan şey budur.

**Uzun süren işi arayüz iş parçacığından uzak tutun.** Oturum, aktarım ve
süreç işleri pencereyi bloke etmemelidir.

**Dış komutları tırnaklayın ve sahtesini kullanın.** Uzak komut satırlarını
serbest metinden birleştirmeyin ve küme ayarları uydurmayın — testler gerçek
bir kümeye bağımlı olmamalıdır.

**Yıkıcı işlemleri onaylatın.** Veriyi yok eden veya küme durumunu değiştiren
her şey açık onay gerektirir (komut satırında `--yes`, arayüzde bir iletişim
kutusu).

## Belge değişiklikleri

Ürün belgeleri için kanonik kaynak `src/hpc_gui/docs/` ve `README.md`
dosyasıdır. Bu wiki depodaki `docs/wiki/` dizininden üretilir ve kod gibi
incelenir — sayfaları github.com üzerinde düzenlemeyin, çünkü bir sonraki
eşitleme üzerine yazar. `scripts/check_wiki.py`; bağlantı çözümünü,
İngilizce/Türkçe sayfa eşliğini, başlık eşliğini, kenar çubuğu bütünlüğünü ve
yasak terimleri denetler.

## Lisans etkisi

Proje v1.2.0'dan itibaren **PolyForm Noncommercial License 1.0.0** ile
lisanslıdır. Katkılar bu lisans altında yapılır; yani bu koşullarla ticari
olmayan kullanıma açıktır, ticari kullanım ise telif hakkı sahibinden ayrı bir
lisans gerektirmeyi sürdürür. Bir işveren adına katkı veriyorsanız önce bunun
onlar için kabul edilebilir olduğunu doğrulayın. Bkz.
[[Lisanslama ve Ticari Kullanım|Licensing-and-Commercial-Use-TR]].

## Ayrıca bkz.

[[Test ve CI|Testing-and-CI-TR]] ·
[[Kaynaktan Derleme|Building-from-Source-TR]] ·
[[Destek ve Bağış|Support-and-Donations-TR]]
