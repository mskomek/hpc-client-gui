# CLI Kılavuzu

> English: [[CLI-Guide]]

Komut satırı yüzeyinin tamamı: ne işe yaradığı, tüm komutlar, çıktı
sözleşmesi ve çıkış kodları.

## Genel bakış

Uygulama, masaüstü arayüzünün yanında bir komut satırı arayüzü de sunar.
Amacı, bağlantı profillerinin, dosya işlemlerinin ve Slurm iş işlemlerinin
grafik oturum olmadan betiklenebilmesidir.

### Çağırma

```bash
python -m hpc_gui --help
```

Yardım çıktısında görünen program adı `hpc-client-gui` şeklindedir. Paketli
Windows ve Linux derlemeleri aynı arayüzü sunar.

### Komutları keşfetme

```bash
hpc-client-gui commands
hpc-client-gui --format json commands
```

`commands`, komut ağacının tamamını, her seçeneği, takma ad tablosunu ve çıkış
kodu tablosunu yazdırır. Yetkili envanter budur; bu wiki onu
[[CLI Kılavuzu|CLI-Guide-TR]] sayfasında yansıtır.

### Dış erişim kapısı

Uzak komutlar bir kapı ardındadır. Ayarlar'daki **"Allow external CLI access to
remote commands"** seçeneği **öntanımlı olarak kapalıdır**. Kapalıyken kümeye
ulaşan komutlar çalışmayı reddeder ve şunu yazdırır:


Seçenek açıkken, bu uygulamanın komut satırı arayüzünü çalıştıran her yerel
süreç kayıtlı profilleri kullanarak uzak komutlara — dosyalar, işler,
düzenleme, kabuk ve tanılama — grafik oturum olmadan ulaşabilir. Ayarlar
ayrıca bir komut `--profile` belirtmediğinde kullanılacak öntanımlı CLI
profilini seçmenize izin verir. Bkz.
[[Ayarlar Referansı|Settings-Reference-TR]] ve
[[Güvenlik Modeli|Security-Model-TR]].

Genel seçenekler her komut için geçerlidir; tam tablo
[Komut referansı](#komut-referans%C4%B1) bölümündedir.

### Çıktı ve çıkış kodları

Sonuçlar metin veya JSON olarak yazdırılır ve her çağrı belgelenmiş bir çıkış
koduyla sonlanır. Otomasyon, ileti metnine değil çıkış koduna dallanmalıdır.
Bkz. [[CLI Kılavuzu|CLI-Guide-TR]] ve
[[CLI Kılavuzu|CLI-Guide-TR]].

## Komut referansı

Bu sayfa, yetkili kaynak olan `hpc-client-gui commands` çıktısını yansıtır.
İkisi çelişirse kurulu sürümünüzde o komutu çalıştırın.

### Genel seçenekler

| Seçenek | Anlamı |
|---|---|
| `--format {text,json}` | Komut sonuçları için çıktı biçimi |
| `--quiet` | Hata dışı çıktıyı bastırır |
| `--verbose` | Ayrıntılı tanılamayı açar |
| `--timeout TIMEOUT` | Saniye cinsinden öntanımlı işlem zaman aşımı |
| `--profile PROFILE` | Kayıtlı bağlantı profili adı |
| `--host HOST` | Ana bilgisayar geçersiz kılması |
| `--port PORT` | Port geçersiz kılması |
| `--transport {sftp,ftp}` | Dosya taşıması (öntanımlı `sftp`) |
| `--user USERNAME` | Kullanıcı adı geçersiz kılması |
| `--key KEY_PATH` | Özel anahtar yolu geçersiz kılması |
| `--password-stdin` | Oturum parolasını stdin'den okur |
| `--password-prompt` | Ekrana yansıtmadan sorar (yalnızca terminal) |
| `--no-saved-password` | Profilde korunarak saklanan gizli değeri kullanmaz; `--password-stdin` gerektirir |
| `--strict-host-key` | Bilinmeyen ana bilgisayar anahtarlarını reddeder |

### Yerel komutlar

| Komut | Argümanlar | Amacı |
|---|---|---|
| `gui` | — | Masaüstü arayüzünü başlatır |
| `version` | — | Sürüm ve derleme bilgisini yazdırır |
| `commands` | — | Komut ağacını, takma adları ve çıkış kodlarını yazdırır |

### `profile` — kayıtlı bağlantı profilleri

| Komut | Argümanlar ve seçenekler |
|---|---|
| `profile list` | — |
| `profile show` | `name` |
| `profile create` | `name` `[--host]` `[--port]` `[--user]` `[--key]` `[--host-key-policy]` |
| `profile update` | `name` `[--host]` `[--port]` `[--user]` `[--key]` `[--host-key-policy]` |
| `profile delete` | `name` `--yes` |
| `profile test` | `name` |

`profile create` ve `profile update` yalnızca gizli olmayan alanları kabul
eder. `profile delete`, `--yes` olmadan çalışmayı reddeder.

### `doctor` — tanılama

| Komut | Seçenekler | Ne yapar |
|---|---|---|
| `doctor environment` | — | Yerel ortamı denetler |
| `doctor connection` | — | Oturum açar ve dosya taşımasını başlatır |
| `doctor smoke` | `[--keep]` `[--artifact ARTIFACT]` | Bir deneme dosyasını gidiş-dönüş aktarır; `--keep` uzak deneme dizinini korur, `--artifact` JSON sonucu yerel bir yola yazar |

Bkz. [[Günlükler ve Tanılama|Logs-and-Diagnostics-TR]].

### `files` — uzak dosya işlemleri

| Komut | Argümanlar ve seçenekler |
|---|---|
| `files ls` | `[path]` |
| `files stat` | `path` |
| `files checksum` | `path` |
| `files mkdir` | `path` |
| `files upload` | `local_path` `remote_path` `[--recursive]` `[--mode {binary,ascii,auto}]` `[--verify]` `[--if-exists {overwrite,skip,rename,resume}]` |
| `files download` | `remote_path` `local_path` `[--recursive]` `[--mode {binary,ascii,auto}]` `[--verify]` `[--if-exists {overwrite,skip,rename,resume}]` |
| `files cp` | `source` `destination` `[--recursive]` |
| `files mv` | `source` `destination` |
| `files rm` | `path` `[--recursive]` `--yes` |

`--verify`, aktarılan dosyanın SHA-256 değerini denetler. `files rm` yıkıcıdır
ve `--yes` olmadan çalışmayı reddeder (çıkış kodu `2`).

### Düzenleme ve çalıştırma

| Komut | Argümanlar ve seçenekler | Amacı |
|---|---|---|
| `edit` | `remote_path` `[--editor EDITOR]` `[--verify]` | İndirir, yerel düzenleyicide açar ve geri yükler. `--editor` öntanımlı olarak `TRUBA_EDITOR`, sonra `EDITOR` |
| `sh` | `-- COMMAND [ARG ...]` | Tek bir uzak komut çalıştırır; komutun önüne `--` koyun |
| `run` | `remote_script [ARG ...]` | Uzak bir betiği argümanlarla çalıştırır |
| `terminal` | `[--cols COLS]` `[--rows ROWS]` | Etkileşimli uzak terminal açar |
| `interactive` | — | Bu arayüz için etkileşimli bir komut istemi açar |

### `jobs` — zamanlayıcı işlemleri

| Komut | Argümanlar ve seçenekler |
|---|---|
| `jobs list` | — |
| `jobs status` | `job_id` |
| `jobs accounting` | — |
| `jobs lssrv` | — |
| `jobs submit` | `script` `--yes` |
| `jobs cancel` | `job_id` `--yes` |

`jobs submit` ve `jobs cancel` küme durumunu değiştirir ve `--yes` olmadan
çalışmayı reddeder.

### Takma adlar

| Takma ad | Karşılığı |
|---|---|
| `ls` | `files ls` |
| `stat` | `files stat` |
| `checksum` | `files checksum` |
| `mkdir` | `files mkdir` |
| `put` | `files upload` |
| `get` | `files download` |
| `cp` | `files cp` |
| `mv` | `files mv` |
| `rm` | `files rm` |
| `squeue` | `jobs list` |
| `scontrol` | `jobs status` |
| `sacct` | `jobs accounting` |
| `sbatch` | `jobs submit` |
| `scancel` | `jobs cancel` |
| `lssrv` | `jobs lssrv` |

Takma adlar tanıdık Slurm ve kabuk komutlarının adını taşır, ancak bu
uygulamanın kendi dağıtımından geçerler — doğrudan aktarım değildirler.

## Çıktı sözleşmesi

Her komut `--format {text,json}` seçeneğine uyar. Aşağıdaki sözleşme
`src/hpc_gui/cli/errors.py` tarafından uygulanır ve kanonik olarak
`docs/cli/exit_codes.md` içinde belgelenir.

### Başarı çıktısı

- **Metin kipi** (öntanımlı): `stdout` üzerinde insan tarafından okunabilir
  sonuçlar.
- **JSON kipi**: `stdout` üzerinde ayrıştırılabilir tek bir nesne.

```bash
hpc-client-gui --format json commands
```

`--quiet` hata dışı çıktıyı bastırır; `--verbose` tanılama ekler. Hiçbiri
çıkış kodunu değiştirmez.

### Hata çıktısı

Hatalar `emit_error` üzerinden yönlendirilir:

- **Metin kipi** — `stderr` üzerinde eyleme dönük bir insan iletisi, altta
  yatan ayrıntı korunarak.
- **JSON kipi** — `stdout` üzerinde tek bir nesne:

```json
{
  "error": {
    "message": "...",
    "exit_code": 1
  }
}
```

### Yinelememe kuralı

Aynı ileti metni asla iki kez yazdırılmaz. Metin kipinde yalnızca `stderr`
üzerinde, JSON kipinde yalnızca `message` alanının içinde görünür. `stdout`
üzerinde JSON tüketen bir ayrıştırıcı aynı iletiyi `stderr` üzerinde de
bulmaz; metin kipinde `stderr` yakalayan bir betik ise `stdout` üzerinde
başıboş bir kopya görmez.

### Çıktıyı tüketme

```bash
if output=$(hpc-client-gui --format json files ls /home/$USER); then
  printf '%s\n' "$output" | jq '.'
else
  status=$?
  printf '%s\n' "$output" | jq -r '.error.message'
  exit "$status"
fi
```

Hata nesnesindeki `exit_code`, sürecin çıkış durumuyla eşleşir; yani her iki
kaynak da kullanılabilir — ancak dallanmak için sürecin çıkış durumu daha
basittir.

## Çıkış kodları

Komut satırı arayüzünün kararlı bir sayısal çıkış kodu sözleşmesi vardır.
Sabitler `src/hpc_gui/cli/errors.py` içindedir (`ExitCode`) ve kanonik tablo
depodaki `docs/cli/exit_codes.md` dosyasıdır. Bu sayfa o tabloyu aktarır,
çatallamaz.

| Çıkış kodu | Ad | Anlamı |
|---|---|---|
| `0` | `SUCCESS` | Komut başarıyla tamamlandı. |
| `1` | `OPERATION_FAILED` | Genel işlem hatası — örneğin başarısız bir dosya işlemi veya var olmayan bir ad için `profile show`. |
| `2` | `USAGE` | Kullanım hatası veya reddedilen onay: desteklenmeyen bir alt komut ya da argüman, veya `files rm` gibi yıkıcı bir komutun `--yes` olmadan verilmesi. Argüman ayrıştırma hataları da `2` ile çıkar. |
| `3` | `CONNECTION` | Oturum açılırken bağlantı hatası. Bağlantı için istenen eksik bir profil de buraya düşer. |
| `124` | `TIMEOUT` | İşlem zaman aşımına uğradı. |

### Otomasyon için notlar

- İleti metnine değil, çıkış koduna dallanın. İletiler yerelleştirilir ve
  yeniden yazılabilir; kodlar sözleşmedir.
- `2`, *arayüzün yapmayacağı bir şeyi istediğiniz* anlamına gelir — genellikle
  yıkıcı bir komutta eksik `--yes`. Çağrıyı düzeltmeden yeniden denemek aynı
  şekilde başarısız olur.
- `3`, "kümeye ulaşılamadı veya kimlik doğrulanamadı" durumunu "işlem çalıştı
  ve başarısız oldu" (`1`) durumundan ayırır. Yeniden deneme mantığı `1` için
  değil `3` için uygundur.
- `124` alışılmış zaman aşımı kodudur. `--timeout` hem bağlantı ayarlarını hem
  de işlem başına öntanımlı zaman aşımını belirler.

## Ayrıca bkz.

[[Betik Örnekleri|Scripting-Examples-TR]] · [[Ayarlar Referansı|Settings-Reference-TR]] · [[Güvenlik Modeli|Security-Model-TR]]
