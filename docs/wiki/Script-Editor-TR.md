# Betik Düzenleyici

> English: [[Script-Editor]]

Uzak betikleri yerinde düzenleyin: açın, düzenleyin, geri kaydedin ve
gönderin — elle indirip yükleme döngüsü olmadan.

## Açma ve kaydetme

**Open**, **Remote:** yolundaki dosyayı yükler; dosya yöneticisinin **Edit** ve
**Edit in new window** eylemleri de aynı işi yapar. Aynı anda birkaç belge
sekmelerde açık olabilir. **Save** dosyayı geri yazar ve yazma başarısız olursa
hatayı bildirir.

## Gönderme

| Eylem | Etkisi |
|---|---|
| **Submit (sbatch)** | Geçerli dosyayı gönderir |
| **Save + Submit** | Önce kaydeder, sonra gönderir |
| **Save + Run** | Kaydeder, sonra betiği terminalde çalıştırır |

Düz bir kaydetmenin ardından düzenleyici hemen göndermeyi önerebilir. Başarılı
bir gönderim **iş kimliğini** bildirir; başarısızlık hesabı, bölümü, süreyi,
belleği ve betiğin yönergelerini denetlemeyi önerir ve hesabınız için geçersiz
bir QOS'u ayrıca belirtir.

## Kaydetmeden önce doğrulama

Bir Slurm betiğini kaydetmek önce onu denetler ve şunlar için uyarır:

- eksik shebang (örneğin `#!/bin/bash`)
- hiç `#SBATCH` yönergesi olmaması
- artakalan şablon yer tutucuları (`USERNAME`, `<partition>`)
- süre sınırı olmaması (`#SBATCH --time` veya `-t`)
- çıktı dosyası ayarlanmamış olması (`#SBATCH --output` veya `-o`)

Bunlar ret değil uyarıdır — yine de kaydetmek isteyip istemediğiniz sorulur.
Aksi hâlde dakikalar sonra başarısız olan bir iş ya da süre sınırı
belirtilmediği için bölümün azami süresine kadar çalışan bir iş olarak yüzeye
çıkacak hataları yakalarlar.

**Lint**, aynı denetimi istediğinizde çalıştırır ve ya belirgin bir sorun
bulunmadığını ya da bulduklarını bildirir. Önce bir hedef yol gerektirir.

## Bul ve değiştir

**Find** ile **Find next**, **Replace** ile **Replace** ve **Replace all**.

## Klavye kısayolları

Kısayollar etkin belge sekmesinde geçerlidir.

| Kısayol | Eylem |
|---|---|
| `Ctrl+S` | Etkin dosyayı kaydet |
| `Ctrl+Shift+S` | Etkin Slurm dosyasını kaydet ve gönder |
| `Ctrl+Z` | Geri al |
| `Ctrl+Y` | Yinele |
| `Ctrl+X` | Kes |
| `Ctrl+C` | Kopyala |
| `Ctrl+V` | Yapıştır |
| `Ctrl+A` | Tüm metni seç |
| `Ctrl+F` | Etkin dosyada metin ara |
| `F3` | Sonraki eşleşmeyi bul |
| `Ctrl+O` | Uzak yol alanına odaklan; açmak için Enter'a bas |
| `Ctrl+W` | Etkin belge sekmesini kapat |
| `Ctrl+Tab` | Sonraki belge sekmesine geç |
| `Ctrl+Shift+Tab` | Önceki belge sekmesine geç |
| `Page Up` / `Page Down` | Bir ekran yukarı/aşağı git |
| `End` | Dosyanın sonuna git |

## Şablondan başlama

Dosya yöneticisi **Core**, **CPU**, **GPU** veya **MPI** şablonundan yeni bir
Slurm betiği oluşturup burada açabilir. Bkz.
[[İş Betiği Şablonları|Job-Script-Templates-TR]].

## Komut satırından düzenleme

```bash
hpc-client-gui --profile mycluster edit /scratch/$USER/job.sh
```

Bu, dosyayı indirir, yerel düzenleyicinizde açar (`--editor`, öntanımlı olarak
`TRUBA_EDITOR` ve sonra `EDITOR`) ve işiniz bitince geri yükler. `--verify`,
yüklemeden sonra SHA-256 değerini denetler.

## Ayrıca bkz.

[[Slurm İşleri|Slurm-Jobs-TR]] ·
[[Uzak Dosya Yöneticisi|Remote-File-Manager-TR]] ·
[[İş Betiği Şablonları|Job-Script-Templates-TR]]
