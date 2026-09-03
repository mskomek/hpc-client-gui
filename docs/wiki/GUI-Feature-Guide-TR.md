# HPC Client GUI özellik rehberi

Bu rehber mevcut Qt üretim ekranlarını ve wx geçiş ekranlarını geçici mock
verilerle kaydeder. Qt görüntüleri eski GUI referansıdır; `wx-*.png` görüntüleri
yeni GUI adayını gösterir. Görüntüler gerçek kümeye bağlantı kanıtı değildir.

## Çalışma zamanı

Üretim varsayılanı hâlâ Qt’dir (`DEFAULT_GUI_RUNTIME = "qt"`). wx arayüzü
`python -m hpc_gui --wx` ile ayrıca açılır.

## Özellikler ve görüntüler

| Özellik | Eski Qt referansı | Yeni wx görüntüsü | Mock akışı |
|---|---|---|---|
| Bağlantı/profil | `assets/overview.png` | `assets/gui-guide/wx-connection.png` | geçici profil listesi |
| Yerel dosyalar | `assets/file-manager.png` | `assets/gui-guide/wx-local-files.png` | betik ve sonuç klasörü |
| Uzak dosyalar/SFTP | `assets/file-manager.png` | `assets/gui-guide/wx-remote-files.png` | uzak liste ve async okuma |
| Editör | `assets/script-editor.png` | `assets/gui-guide/wx-editor.png` | betik editörü |
| İşler/durum | `assets/jobs.png` | `assets/gui-guide/wx-jobs.png` | RUNNING ve PENDING işler |
| İş stdout/stderr | `assets/jobs.png` | `assets/gui-guide/wx-detached-output.png` | ayrık çıktı görünümü |
| Yardım | Qt yardım penceresi | `assets/gui-guide/wx-help-shortcuts.png` | kısayol konusu |
| Terminal | ana Qt penceresindeki terminal | `assets/gui-guide/wx-terminal.png` | ağsız terminal adaptörü |
| Ayarlar | `assets/settings.png` | henüz wx pencere adaptörü yok | yalnızca Qt referansı |
| Eklentiler/ANSYS | Qt ekranları ve dokümanlar | henüz wx pencere adaptörü yok | geçiş engeli |
| Tanılama/log | `assets/send-logs.png` | henüz wx pencere adaptörü yok | yalnızca Qt referansı |

## Bağlantı ve güvenlik

Görüntülerde yalnızca sahte `127.0.0.1`, profil, dosya ve iş verileri kullanılır.
Gerçek parola, MFA, özel anahtar, token veya küme bilgisi kullanılmaz. Host-key,
secret store, SSH/SFTP ve Slurm güvenlik kuralları üretimde aynen geçerlidir.

## Dosyalar ve SFTP

Yerel ve uzak dosya ekranları gerçek wx list kontrollerini kullanır. Uzak liste
`/scratch/demo` içeriğini sahte SFTP adaptörüyle gösterir.

## İşler ve Slurm

Jobs ekranı sahte RUNNING/PENDING işler ve ayrık stdout/stderr gösterir. Gerçek
Slurm komutları ve çıktı takibi ayrıca mock roundtrip testiyle doğrulanır.

## Editör

Editör akışı yerel dosyada kaydet → yükle → gönder/çalıştır; uzak dosyada kaydet
→ gönder/çalıştır şeklindedir. Ekran görüntüsü tek başına gerçek küme testi
değildir.

## Yardım, terminal ve araçlar

Help, terminal, eklenti, ANSYS, updater ve tanılama yüzeyleri mevcut wx adaptörü
olmadığında model varmış gibi gösterilmez; bunlar sonraki migration kalemleridir.

## Kanıtı yeniden üretme

```powershell
python scripts/capture_wiki_screenshots.py
python scripts/capture_wx_gui_guide.py
python -m pytest -q tests/test_mock_cluster_roundtrip.py tests/test_wx_editor_cross_view_actions.py
```
