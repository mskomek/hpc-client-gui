# CLI Çıkış Kodları

> English: [[CLI-Exit-Codes]]

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

## Otomasyon için notlar

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

[[CLI Çıktı Sözleşmesi|CLI-Output-Contract-TR]] ·
[[Betik Örnekleri|Scripting-Examples-TR]] ·
[[Sorun Giderme|Troubleshooting-TR]]
