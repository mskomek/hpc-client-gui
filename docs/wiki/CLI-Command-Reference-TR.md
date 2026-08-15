# CLI Komut Referansı

> English: [[CLI-Command-Reference]]

Bu sayfa, yetkili kaynak olan `hpc-client-gui commands` çıktısını yansıtır.
İkisi çelişirse kurulu sürümünüzde o komutu çalıştırın.

## Genel seçenekler

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

## Yerel komutlar

| Komut | Argümanlar | Amacı |
|---|---|---|
| `gui` | — | Masaüstü arayüzünü başlatır |
| `version` | — | Sürüm ve derleme bilgisini yazdırır |
| `commands` | — | Komut ağacını, takma adları ve çıkış kodlarını yazdırır |

## `profile` — kayıtlı bağlantı profilleri

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

## `doctor` — tanılama

| Komut | Seçenekler | Ne yapar |
|---|---|---|
| `doctor environment` | — | Yerel ortamı denetler |
| `doctor connection` | — | Oturum açar ve dosya taşımasını başlatır |
| `doctor smoke` | `[--keep]` `[--artifact ARTIFACT]` | Bir deneme dosyasını gidiş-dönüş aktarır; `--keep` uzak deneme dizinini korur, `--artifact` JSON sonucu yerel bir yola yazar |

Bkz. [[Günlükler ve Tanılama|Logs-and-Diagnostics-TR]].

## `files` — uzak dosya işlemleri

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

## Düzenleme ve çalıştırma

| Komut | Argümanlar ve seçenekler | Amacı |
|---|---|---|
| `edit` | `remote_path` `[--editor EDITOR]` `[--verify]` | İndirir, yerel düzenleyicide açar ve geri yükler. `--editor` öntanımlı olarak `TRUBA_EDITOR`, sonra `EDITOR` |
| `sh` | `-- COMMAND [ARG ...]` | Tek bir uzak komut çalıştırır; komutun önüne `--` koyun |
| `run` | `remote_script [ARG ...]` | Uzak bir betiği argümanlarla çalıştırır |
| `terminal` | `[--cols COLS]` `[--rows ROWS]` | Etkileşimli uzak terminal açar |
| `interactive` | — | Bu arayüz için etkileşimli bir komut istemi açar |

## `jobs` — zamanlayıcı işlemleri

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

## Takma adlar

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

## Ayrıca bkz.

[[CLI Çıkış Kodları|CLI-Exit-Codes-TR]] ·
[[CLI Çıktı Sözleşmesi|CLI-Output-Contract-TR]] ·
[[Betik Örnekleri|Scripting-Examples-TR]]
