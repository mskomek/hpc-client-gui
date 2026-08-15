# Arayüz Dili ve i18n

> English: [[Interface-Language-and-i18n]]

Uygulama **Türkçe** ve **İngilizce** olarak gelir. İkisi de eksiksizdir:
kullanıcıya görünen her metin her iki dilde bulunur ve bu bozulursa CI
başarısız olur.

## Dil seçme

Dili uygulama içinde seçin; seçim hemen etkili olur — açık pencereler yeniden
başlatma gerektirmeden yeniden çevrilir.

Seçiminiz `~/.truba_slurm_gui/language.json` dosyasında saklanır ve bir sonraki
açılışta yeniden kullanılır. Henüz bir şey saklanmamışken, ilk çalıştırmada
uygulama işletim sisteminizin yerel ayarını izler: Türkçe bir yerel ayar
Türkçe, diğerleri İngilizce verir.

Dil dosyası yazılamazsa uygulama başarısız olmak yerine bu oturumda seçilen
dille çalışmayı sürdürür — yalnızca seçim anımsanmaz.

## Metinler nerede

Çeviriler `src/hpc_gui/i18n/tr.json` ve `src/hpc_gui/i18n/en.json`
dosyalarındaki JSON kataloglarıdır ve noktalı adlarla anahtarlanır
(`settings.dialog_title`, `transfer.conflict_overwrite`). Kod metin gömmek
yerine anahtar arar; dili çalışma zamanında değiştirebilmeyi mümkün kılan
budur.

## Neler çevrilmez

Komutlar, bayraklar, dosya yolları, çıkış kodları ve tanımlayıcılar her iki
dilde de olduğu gibi kalır — `sbatch` her yerde `sbatch`'tir. Kümeden gelen
çıktı (Slurm iletileri, kabuk çıktısı, uzak hatalar) kümenin ürettiği dilde
gelir ve değiştirilmeden gösterilir.

Buna komut satırı arayüzü de dâhildir: yardım metni, seçenek adları ve hata
iletileri İngilizcedir ve otomasyonun dayanması gereken sözleşme çıkış
kodlarıdır. Bkz. [[CLI Çıkış Kodları|CLI-Exit-Codes-TR]].

## Katkı verenler için

Türkçe ve İngilizce kaynaklar **birlikte** güncellenir.
`scripts/check_i18n.py` engelleyici bir CI kapısıdır ve şunlarda başarısız
olur:

- bir katalogda olup diğerinde bulunmayan bir anahtar,
- katalog anahtarı yerine arayüz kodunda sabit kodlanmış kullanıcı metni,
- her iki katalogda da bulunmayan bir çeviri anahtarına yapılan referans.

Yalnızca İngilizce bir metin eklemek CI'ı kırar. Bkz.
[[Katkıda Bulunma|Contributing-TR]] ve [[Test ve CI|Testing-and-CI-TR]].

Aynı kural bu wiki için de geçerlidir: her İngilizce sayfanın bir Türkçe
karşılığı vardır ve bunu `scripts/check_wiki.py` denetler.

## Ek diller

Bugün yalnızca Türkçe ve İngilizce desteklenir. Başka bir dil eklemek, tam
anahtar kapsamına sahip yeni bir katalog ve çevrilmiş bir wiki aynası
gerektirir — bir yapılandırma değişikliği değil, önemli bir katkıdır.

## Ayrıca bkz.

[[Ayarlar Referansı|Settings-Reference-TR]] ·
[[Katkıda Bulunma|Contributing-TR]] ·
[[Sözlük|Glossary-TR]]
