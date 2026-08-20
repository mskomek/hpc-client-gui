# Veri ve Gizlilik

> English: [[Data-and-Privacy]]

Uygulama istemci tarafındadır. Kendi kendine veri göndermez ve siz bir eylemde
bulunmadıkça makinenizden hiçbir şey ayrılmaz.

## Yerelde ne saklanır

Her şey `~/.truba_slurm_gui` altındadır:

| Dosya | İçeriği |
|---|---|
| `config.json` | Bağlantı profilleri (ana bilgisayar, kullanıcı adı, port, anahtar yolu) ve korunan parola verisi |
| `known_hosts` | Güvenip kaydettiğiniz ana bilgisayar anahtarları |
| `app.log` (+ döngüler) | Yerel hata ayıklama için maskelenmemiş uygulama günlüğü |
| `crash.log` | Çökme raporlayıcısının kaydı |
| `history.json`, `history.jsonl` | Komut ve iş geçmişi |
| `last_batch.json` | En son toplu gönderim kaydı |
| `processes.json` | İzlenen yardımcı süreçler |
| `transfer_journal.jsonl` | Kesilen aktarımları sürdürmek için kullanılan durum |
| `language.json` | Seçilen arayüz dili |
| `downloads` | İndirdiğiniz dosyalar |
| `third_party` | Onayınızla indirilen isteğe bağlı yardımcılar |

Dizini silmek bunların tümünü kaldırır. Bkz.
[[Yükseltme ve Kaldırma|Upgrading-and-Uninstalling-TR]].

## Makineden ne ayrılabilir

Tam olarak üç şey, hepsi sizin başlattığınız:

1. **Kendi aktarımlarınız ve komutlarınız** — yüklediğiniz ya da indirdiğiniz
   dosyalar ve kümede çalıştırdığınız komutlar.
2. Günlük gönderme iletişim kutusundan **dışa aktardığınız tanılama paketi**.
3. O iletişim kutusundan **panoya kopyaladığınız günlük metni**.

İsteğe bağlı X11 yardımcıları (plink, VcXsrv) yalnızca indirmeyi
onayladıktan sonra indirilir.

## Tanılama paketi ne içerir

Paket; `app.log`, geçmiş dosyaları, `last_batch.json`, `processes.json`,
`transfer_journal.jsonl`, VcXsrv çıktı günlükleri, `language.json` ve
oluşturma zaman damgasını taşıyan küçük bir `manifest.json` içerir.

Tasarım gereği **`config.json` dosyasını dışarıda bırakır**; böylece kayıtlı
profilleriniz ve şifrelenmiş parola veriniz onunla birlikte yolculuk etmez.

## Maskeleme neyi değiştirir

Bir metin dosyası pakete yazılmadan önce maskelemeden geçer; bu şunları
değiştirir:

- yerel hesap adınız → `<user>`
- kayıtlı her profilin uzak kullanıcı adı → `<user>`
- kayıtlı her profilin ana bilgisayar adı veya IP'si → `<host>`

Değişim bu değerleri yolların ve URL'lerin içinde de tanır; böylece
`/scratch/adiniz/data` yolu `/scratch/<user>/data` olur. Üç karakterden kısa
değerler olduğu gibi bırakılır, çünkü değiştirilmeleri ilgisiz metni bozar.
Daha uzun adlar önce değiştirilir; böylece iç içe geçen adlar yarım eşleşmeler
bırakmaz.

## Maskelemenin sınırları, açıkça

Maskeleme elden gelenin en iyisidir. Yalnızca yerel hesap adınızı ve
kaydettiğiniz profilleri bilir. Şunları yakalamaz:

- günlük metninde geçen ama profil olarak hiç kaydedilmemiş bir ana bilgisayar
  adı veya kullanıcı adı,
- kendi iş çıktınızın ya da betiklerinizin içindeki tanımlayıcılar,
- proje, tahsis veya iş tanımlayıcıları,
- metin olarak okunamadığı için değiştirilmeden eklenen dosyaların içeriği.

**Paylaşmadan önce paketi okuyun.** Düz metin dosyalarından oluşan bir ZIP'tir;
açın ve bakın. İçinde herkese açık olmasını istemediğiniz bir şey varsa gizli
bir kanaldan iletin — bkz. `SECURITY.md` ve
[[Güvenlik Modeli|Security-Model-TR]].

## Ayrıca bkz.

[[Çökme Raporları ve Günlük Gönderme|Crash-Reports-and-Send-Logs-TR]] · [[Günlükler ve Tanılama|Logs-and-Diagnostics-TR]] · [[Güvenlik Modeli|Security-Model-TR]]
