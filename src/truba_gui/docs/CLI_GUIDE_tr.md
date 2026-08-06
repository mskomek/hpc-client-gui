# HPC Client GUI — Komut Satırı Kılavuzu (CLI)

> Bu kılavuz, HPC Client GUI'nin komut satırı arayüzünü (CLI) uçtan uca belgeler: bağlantı profilleri, tanılama, uzak dosya işlemleri, zamanlayıcı işlemleri ve masaüstü GUI başlatma.

## Giriş

Komut satırı arayüzü, HPC Client GUI'nin grafik arayüz olmadan da kullanılmasını sağlar. TRUBA veya benzeri **Slurm tabanlı HPC** sistemlerinde, kayıtlı bağlantı profillerini yönetebilir, yerel ortamı ve bağlantıyı teşhis edebilir, uzak dosya aktarım işlemleri yapabilir ve zamanlayıcıya iş gönderebilir / iş iptal edebilirsiniz. Ayrıca masaüstü GUI'yi bu arayüzden başlatabilirsiniz.

Kaynak kod dizininden çağrılışı:

```bash
python -m truba_gui <komut> [seçenekler]
```

Paketlenmiş çalıştırılabilir sürüm de `hpc-client-gui <komut> [seçenekler]` biçiminde aynı arayüzü sunar.

> Not: Bu CLI'nin uzak çağrıları gerçek ağ bağlantısına ve gerçek küme durumuna bağlıdır. Bu kılavuz canlı bir kümenin davranışını garanti edemez; beklenmedik sonuçlarla karşılaşırsanız ilgili çıkış koduna ve hata mesajına bakın.

---

## Genel seçenekler

Aşağıdaki seçenekler tüm komut grupları için geçerlidir ve genellikle alt komuttan önce yazılır:

| Seçenek | Açıklama |
|---|---|
| `--format {text,json}` | Komut sonuçlarının çıktı biçimi. |
| `--quiet` | Hata dışındaki çıktıları bastırır. |
| `--verbose` | Ayrıntılı tanılama çıktısını etkinleştirir. |
| `--timeout TIMEOUT` | Varsayılan işlem zaman aşımı, saniye cinsinden. |
| `--profile PROFILE` | Kayıtlı bağlantı profili adı. |
| `--host HOST` | Bağlantı için uzak sunucu adresini geçersiz kılar. |
| `--port PORT` | Bağlantı için uzak portu geçersiz kılar. |
| `--user USERNAME` | Bağlantı için uzak kullanıcı adını geçersiz kılar. |
| `--key KEY_PATH` | Bağlantı için özel anahtar yolunu geçersiz kılar. |
| `--password-stdin` | Uzak parola değerini komut satırı argümanı olarak değil, **stdin'den** okur. |
| `--no-saved-password` | Profilin kayıtlı DPAPI korumalı sırrını kullanma; bunun yerine `--password-stdin` gereklidir. |
| `--strict-host-key` | Bilinmeyen uzak sunucu anahtarlarını reddeder (varsayılan `accept-new` politikasının tersi). |

### Kayıtlı sır çözümleme sırası (`--profile`)

`--profile NAME` kullanıldığında ve `--password-stdin` verilmediğinde, CLI bağlantı sırrını şu sırayla çözer:

1. `--no-saved-password` verilmişse veya profil anahtar tabanlı kimlik doğrulama kullanıyorsa (`--key` veya kayıtlı bir anahtar yolu), kayıtlı sır kullanılmaz — `--password-stdin` de verilmedikçe bağlantı parolasız devam eder.
2. Aksi halde, profilin kayıtlı bir DPAPI korumalı sırrı varsa (GUI'nin "parolayı hatırla" akışının yazdığı aynı alan) ve işletim sistemi kimlik bilgisi deposu kullanılabilirse (yalnızca Windows), bu sır bellek içinde çözülür ve kullanılır.
3. Aksi halde, bağlantı `--password-stdin` verilmedikçe parolasız devam eder.

Çözülen sır hiçbir zaman yazdırılmaz, günlüğe kaydedilmez veya `--verbose` çıktısına ya da JSON sonuçlarına dahil edilmez.

### Harici CLI erişimi, varsayılan profil ve komut envanteri

GUI'deki **Ayarlar → Bağlantı ve X11** penceresindeki iki ayar, bu CLI'nin kayıtlı profillere nasıl erişeceğini belirler:

- **Uzak komutlara harici CLI erişimine izin ver** (`cli_external_access_enabled` ayarı, varsayılan olarak kapalı). Kapalıyken her uzak oturum komutu — `files *`, `jobs *`, `profile test`, `doctor connection`, `doctor smoke` — herhangi bir bağlantı denemesinden önce, bu ayarı adıyla anan tek bir mesajla ve `1` (`OPERATION_FAILED`) çıkış koduyla başarısız olur. `profile list`, `profile show`, `doctor environment`, `version`, `gui` ve `commands` her zaman kullanılabilir.
- **Varsayılan CLI profili** (`cli_default_profile` ayarı). `--profile` verilmediğinde CLI, kayıtlı varsayılan profili kullanır; açıkça verilen `--profile` her zaman bunu geçersiz kılar. Kayıtlı profiller arasında artık var olmayan bir varsayılan, yine mevcut `Profile not found: NAME` hatasını üretir.

Yukarıdaki iki ayardan bağımsız olarak, her kayıtlı bağlantının kendi **"Bu bağlantının CLI üzerinden kullanılmasına izin ver"** onay kutusu da vardır (bağlantı ekle/düzenle penceresindeki, profilin `cli_allowed` alanı, varsayılan olarak kapalı). `--profile NAME` ile kullanılan ve bu kutusu işaretli olmayan bir profil, harici CLI erişimi genel olarak açık olsa bile, herhangi bir bağlantı denemesinden önce `Profile 'NAME' is not allowed for CLI use.` hatasıyla başarısız olur. Var olan kayıtlı bağlantılar, düzenlenip kutu işaretlenerek yeniden kaydedilene kadar varsayılan olarak izinsizdir.

> **Güvenlik notu:** harici CLI erişimini etkinleştirmek, bu uygulamanın çalıştırılabilir dosyasını çalıştırabilen **herhangi bir yerel sürece**, GUI'nin kayıtlı profilleriyle aynı uzak komut yüzeyini verir. Bu, araç başına değil, konak düzeyinde geniş bir güven kararıdır — bu nedenle ayar varsayılan olarak kapalıdır.

`commands` alt komutu, komut dosyası oluşturma ve otomasyon için tam komut envanterini yazdırır: tüm komut ağacı (grup, alt komut, bayraklar ve yardım metni) ve çıkış kodu tablosu. `--format text|json` biçimini kabul eder ve her zaman kullanılabilir. Genel bayraklar alt komuttan önce yazılmalıdır:

```bash
# Metin biçimi
hpc-client-gui commands

# JSON biçimi
hpc-client-gui --format json commands
```

---

## Komut grupları

### `gui`

Masaüstü GUI'yi başlatır. Argüman almaz.

```bash
python -m truba_gui gui
```

### `version`

Sürüm ve derleme bilgilerini yazdırır. Argüman almaz.

```bash
python -m truba_gui version
```

### `profile`

Kayıtlı bağlantı profillerini yönetir. Alt komutlar: `list`, `show`, `create`, `update`, `delete`, `test`.

- `hpc-client-gui profile list` — Profil adlarını, gizli alanlar olmadan listeler.
- `hpc-client-gui profile show NAME` — Bir profili, gizli alanlar olmadan gösterir.
- `hpc-client-gui profile create NAME [--host HOST] [--port PORT] [--user USERNAME] [--key KEY_PATH] [--host-key-policy {accept-new,strict}]` — Yalnızca hassas olmayan alanlardan oluşan bir profil oluşturur.
- `hpc-client-gui profile update NAME [--host HOST] [--port PORT] [--user USERNAME] [--key KEY_PATH] [--host-key-policy {accept-new,strict}]` — Bir profilin hassas olmayan alanlarını günceller (`create` ile aynı bayrak yapısına sahiptir).
- `hpc-client-gui profile delete NAME [--yes]` — Bir profili siler; `--yes` olmadan silmeyi reddeder.
- `hpc-client-gui profile test NAME` — Kayıtlı bir profilin bağlantısını doğrular.

**Değişiklik yapan komutlar:** `profile delete`, `--yes` bayrağı verilmediği takdirde, herhangi bir işlem yapılmadan reddedilir. `profile create` ve `profile update` hassas olmayan alanlarla çalışır; gizli alanlar (örneğin parola) bu komutlarla ayarlanmaz.

```bash
# Bir profil oluştur (hassas olmayan alanlar)
python -m truba_gui profile create myprofile --host hpc.example --port 22 --user myuser

# Profili güncelle
python -m truba_gui profile update myprofile --host hpc.example --host-key-policy strict

# Profili sil (onay gerekir)
python -m truba_gui profile delete myprofile --yes
```

### `doctor`

Yerel tanılama komutları çalıştırır. Alt komutlar: `environment`, `connection`, `smoke`.

- `hpc-client-gui doctor environment` — Yerel çalışma ortamını inceler.
- `hpc-client-gui doctor connection` — Bağlanır ve uzak dosya aktarımını başlatır.
- `hpc-client-gui doctor smoke [--keep] [--artifact ARTIFACT]` — Uzak dosya aktarımı üzerinden bir test dosyasını gidiş-dönüş gönderir; `--keep`, uzak test dizinini silmeden bırakır; `--artifact ARTIFACT`, test sonucu JSON çıktısını belirtilen yerel yola yazar.

```bash
python -m truba_gui doctor environment
```

### `files`

Uzak dosya işlemleri. Tüm alt komutlar, uzak dosya aktarım katmanı üzerinde uzak yollara uygulanır; CLI katmanının kendisi uzak komut metni oluşturmaz. Alt komutlar: `ls`, `stat`, `checksum`, `mkdir`, `upload`, `download`, `cp`, `mv`, `rm`.

- `hpc-client-gui files ls [REMOTE_PATH]` — Uzak bir dizini listeler; yol verilmezse `.` (geçerli uzak dizin) kullanılır.
- `hpc-client-gui files stat REMOTE_PATH` — Uzak bir dosyanın meta verilerini gösterir.
- `hpc-client-gui files checksum REMOTE_PATH` — Uzak bir dosyanın SHA-256 özetini gösterir.
- `hpc-client-gui files mkdir REMOTE_PATH` — Uzak bir dizin oluşturur.
- `hpc-client-gui files upload LOCAL_PATH REMOTE_PATH [--recursive] [--mode {binary,ascii,auto}] [--verify] [--if-exists {overwrite,skip,rename,resume}]` — Yerel bir dosyayı veya dizini yükler; `--verify`, yükleme sonrası SHA-256 doğrular; `--if-exists`, uzak hedef zaten mevcutsa izlenecek çakışma politikasını belirler.
- `hpc-client-gui files download REMOTE_PATH LOCAL_PATH [--recursive] [--mode {binary,ascii,auto}] [--verify] [--if-exists {overwrite,skip,rename,resume}]` — Uzak bir dosyayı veya dizini indirir; `upload` ile aynı bayrak yapısına sahiptir.
- `hpc-client-gui files cp REMOTE_SRC REMOTE_DST [--recursive]` — Uzak bir dosyayı veya dizini kopyalar.
- `hpc-client-gui files mv REMOTE_SRC REMOTE_DST` — Uzak bir yolu taşır veya yeniden adlandırır.
- `hpc-client-gui files rm REMOTE_PATH [--recursive] [--yes]` — Uzak bir yolu siler; `--yes` olmadan silmeyi reddeder.

**Değişiklik yapan komutlar:** `files rm`, `--yes` bayrağı verilmediği takdirde, herhangi bir uzak işlem yapılmadan reddedilir. `files upload` ve `files download` için hedef zaten mevcutsa `--if-exists` politikası devreye girer; `--verify`, aktarım sonrası bütünlüğü doğrular.

```bash
# Uzak bir dosyayı indir (hedef zaten varsa atla)
python -m truba_gui files download /remote/path/run.sh /local/path/run.sh --if-exists skip

# Yerel bir dosyayı yükle ve doğrula
python -m truba_gui files upload /local/path/run.sh /remote/path/run.sh --verify

# Uzak bir dizini sil (onay gerekir)
python -m truba_gui files rm /remote/path/eski_dizin --recursive --yes
```

### `jobs`

Zamanlayıcı işlemleri. Mevcut zamanlayıcı servisi üzerinden çalışır; CLI katmanının kendisi zamanlayıcı komut metni oluşturmaz. Alt komutlar: `list`, `status`, `accounting`, `lssrv`, `submit`, `cancel`.

- `hpc-client-gui jobs list` — Kullanıcının sırada bekleyen ve çalışan işlerini listeler.
- `hpc-client-gui jobs status JOB_ID` — Tek bir işin durumunu gösterir.
- `hpc-client-gui jobs accounting` — Kullanıcının işlerine ait muhasebe verilerini gösterir.
- `hpc-client-gui jobs lssrv` — Giriş düğümü küme durumunu gösterir.
- `hpc-client-gui jobs submit SCRIPT [--yes]` — Zamanlayıcıya bir toplu iş betiği gönderir; `--yes` olmadan göndermeyi reddeder; betik yolu bir uzak yoldur.
- `hpc-client-gui jobs cancel JOB_ID [--yes]` — Sırada bekleyen veya çalışan bir işi iptal eder; `--yes` olmadan iptali reddeder. Herhangi bir bağlantı denemesinden önce güvensiz karakter içeren bir iş kimliğini reddeder; yalnızca sayısal kimlikleri ve `12345_3` veya `12345.0` gibi dizi iş / alt adım biçimlerini kabul eder.

**Değişiklik yapan komutlar:** `jobs submit` ve `jobs cancel`, `--yes` bayrağı verilmediği takdirde, herhangi bir uzak işlem yapılmadan reddedilir.

```bash
# Bir toplu iş betiğini gönder (onay gerekir)
python -m truba_gui jobs submit /remote/path/run.sh --yes

# Bir işi iptal et (onay gerekir)
python -m truba_gui jobs cancel 12345 --yes
```

---

## Çıkış kodları

| Çıkış kodu | Ad | Anlam |
|---|---|---|
| `0` | `SUCCESS` | Komut başarıyla tamamlandı. |
| `1` | `OPERATION_FAILED` | Genel işlem hatası (örneğin `profile show` için bilinmeyen bir profil adı). |
| `2` | `USAGE` | Kullanım hatası veya onay reddi (desteklenmeyen alt komut/argüman ya da `--yes` verilmeden yapılan değişiklik komutu). argparse'ın kendi ayrıştırma hataları da `2` ile çıkar. |
| `3` | `CONNECTION` | Oturum açılırken bağlantı hatası (örneğin `--profile` ile istenen bir profilin bulunamaması). |
| `124` | `TIMEOUT` | Uzak bir işlem zaman aşımına uğradı; `--timeout` genel seçeneği işlem başına varsayılan zaman aşımını belirler. |

### `files` hata mesajları

Uzak `files` işlemleri, "bulunamadı" ve "izin reddedildi" durumlarını ilgili uzak yolla birlikte raporlar; böylece hata, tam olarak hangi yolun etkilendiğini gösterir:

| Durum | Sonuç | Çıkış kodu |
|---|---|---|
| Uzak yol mevcut değil | `Not found: <yol>` | `1` (`OPERATION_FAILED`) |
| Uzak yola erişim reddedildi | `Permission denied: <yol>` | `1` (`OPERATION_FAILED`) |
| `files ls`, mevcut ve boş bir dizinde | Başarılı boş liste (JSON biçiminde `[]`) | `0` (`SUCCESS`) |

`<yol>`, hatanın işaret ettiği uzak yoldur; örneğin `Not found: /remote/path/run.sh` veya `Permission denied: /remote/path/run.sh`.

---

## Metin / JSON çıktı sözleşmesi

Bir komut başarısız olduğunda çıktı, seçili biçime göre şu şekilde üretilir:

- **Metin biçimi:** İşlem yapılabilir bir hata mesajı **stderr**'e yazılır.
- **JSON biçimi:** **stdout**'a `{"error": {"message": "...", "exit_code": N}}` biçiminde tek, ayrıştırılabilir bir nesne yazılır.

Aynı mesaj metni iki biçim arasında asla tekrarlanmaz: mesaj, metin biçiminde yalnızca stderr'de, JSON biçiminde ise yalnızca `message` alanının içinde görünür.

---

## Son not

Bu kılavuz ve İngilizce karşılığı (`CLI_GUIDE_en.md`, ayrı bir paketten) birebir aynı komutları ve konuları kapsar. Bu belge ile canlı çıktı arasında bir çelişki olursa `hpc-client-gui --help` (veya kaynak kodda `python -m truba_gui --help`) her zaman son söz sahibidir.
