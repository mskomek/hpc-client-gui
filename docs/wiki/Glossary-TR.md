# Sözlük

> English: [[Glossary]]

**AppImage** — kurulum gerektirmeden çalışan tek dosyalık Linux uygulama
biçimi. Bkz. [[Linux Kurulumu|Installation-Linux-TR]].

**Muhasebe (accounting)** — Slurm'ün tamamlanmış işlere ilişkin kaydı; `sacct`
ile sorgulanır. Bir işin istediğinin değil, gerçekte kullandığının kaydıdır.

**AppRun** — AppImage içindeki başlatıcı betik. Linux derlemesi sırasında
doğrulanır.

**Çakışma çözümü** — bir aktarımın hedefi zaten varsa ne olacağı: üzerine
yazma, atlama, yeniden adlandırma veya sürdürme. Bkz.
[[Dosya Aktarımları|File-Transfers-TR]].

**`--yes`** — veriyi yok eden veya küme durumunu değiştiren komutların
gerektirdiği açık onay. Olmadan `2` ile çıkarlar.

**Tanılama paketi** — günlük gönderme iletişim kutusunun ürettiği, hata
bildirimine eklenmeye uygun maskelenmiş ZIP. Bkz.
[[Çökme Raporları ve Günlük Gönderme|Crash-Reports-and-Send-Logs-TR]].

**Çıkış kodu** — bir komut satırı çağrısının bittiği sayısal durum.
Sözleşmedir; ileti metni yerine buna dallanın. Bkz.
[[CLI Kılavuzu|CLI-Guide-TR]].

**Ana bilgisayar anahtarı** — uzak ana bilgisayarın sunduğu kriptografik
kimlik. Güvenilen anahtar `~/.truba_slurm_gui/known_hosts` dosyasına kaydedilir.
*Değişen* bir anahtar her zaman reddedilir. Bkz.
[[Güvenlik Modeli|Security-Model-TR]].

**i18n** — uluslararasılaştırma. Bu proje Türkçe ve İngilizce sunar ve ikisi
birlikte güncellenir. Bkz.
[[Arayüz Dili ve i18n|Interface-Language-and-i18n-TR]].

**İş kimliği (Job ID)** — Slurm'ün gönderimde atadığı tanımlayıcı;
`jobs status`, `jobs cancel`, `scontrol` ve `scancel` tarafından kullanılır.

**`known_hosts`** — güvenmeyi seçtiğiniz ana bilgisayar anahtarlarının dosyası.

**Modül** — kümedeki bir ortam modülü (`module avail`, `module load`). Adlar
siteye göre değişir; şablonlarda yorum içinde bırakılmasının nedeni budur.

**MPI** — çok düğümlü paralel işlerin kullandığı mesajlaşma arayüzü. Bkz.
[[İş Betiği Şablonları|Job-Script-Templates-TR]].

**Bölüm (partition)** — bir Slurm kuyruğu. Adlar siteye özgüdür; şablonlardaki
bölüm adları örnektir.

**plink** — PuTTY'nin komut satırı istemcisi. Windows'ta X11 için kullanılır
(`plink.exe -X`). Birlikte gelmez. Bkz.
[[X11 Yönlendirme|X11-Forwarding-TR]].

**Profil** — kaydedilmiş bir bağlantı: ana bilgisayar, port, kullanıcı adı,
anahtar yolu ve ana bilgisayar anahtarı ilkesi. Bkz.
[[Bağlantı ve Profiller|Connecting-and-Profiles-TR]].

**QOS** — hesap başına süre, CPU, bellek veya GPU kullanımını sınırlayabilen
Slurm hizmet kalitesi ilkesi.

**Maskeleme (redaction)** — bir günlük makineden ayrılmadan önce yerel ve uzak
kullanıcı adlarınızla kayıtlı ana bilgisayar adlarınızın `<user>` ve `<host>`
ile değiştirilmesi. Elden gelenin en iyisidir. Bkz.
[[Veri ve Gizlilik|Data-and-Privacy-TR]].

**Sürdürme (resume)** — kesilen bir aktarımı baştan başlatmak yerine devam
ettirmek; aktarım günlüğüne dayanır.

**Scratch** — büyük veri ve çalışan işler için hızlı küme deposu; genellikle
düzenli olarak temizlenir. Önemsediğiniz sonuçları home veya proje deposunda
tutun.

**SFTP** — öntanımlı dosya taşıması; `--transport` ayrıca `ftp` kabul eder.

**SHA-256** — aktarımlarda `--verify` tarafından ve her sürüm çıktısının yanında
yayımlanan `.sha256` dosyalarında kullanılan sağlama toplamı.

**Slurm** — bu uygulamanın sürdüğü küme iş yükü yöneticisi: `sbatch`, `squeue`,
`sacct`, `scancel`, `sinfo`, `scontrol`.

**Duman testi (smoke test)** — en yalın uçtan uca denetim. `doctor smoke` bir
dosyayı taşıma üzerinden gidiş-dönüş aktarır; sürüm iş akışı paketli çıktıları
duman testinden geçirir.

**VcXsrv** — uzak grafiksel uygulamaları görüntülemek için Windows'ta
kullanılan X sunucusu. Birlikte gelmez.

**X11** — uzak bir grafiksel uygulamayı yerel ekranınızda gösteren protokol.
Yalnızca grafiksel programlar için gerekir, toplu işler için asla.

## Ayrıca bkz.

[[SSS|FAQ-TR]] · [[Slurm Yardım Kütüphanesi|Slurm-Help-Library-TR]] · [[Mimari|Architecture-TR]]
