# Test ve CI

> English: [[Testing-and-CI]]

## Test paketi çevrimdışıdır

Testler küme olmadan çalışır. Uzak tarafın yerine sahte dosya ve Slurm
katmanları geçer; CI'ın aktarım, düzenleyici ve iş akışlarını sınayabilmesinin
nedeni budur. Hiçbir test gerçek bir küme işlemi yapmaz.

```bash
pip install -e .[test]
PYTHONPATH=src QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
```

`QT_QPA_PLATFORM=offscreen`, Qt testlerinin ekran olmadan çalışmasını sağlar.

## Yardımcı denetimler

| Betik | Denetlediği |
|---|---|
| `scripts/check_i18n.py` | Türkçe/İngilizce anahtar eşliği, sabit kodlanmış arayüz metinleri ve eksik çeviri referansları |
| `scripts/check_branding.py` | Yeniden adlandırmadan gelen bozuk kullanıcı metinlerinin geri dönememesi |
| `scripts/check_wiki.py` | Wiki bağlantı çözümü, TR/EN sayfa eşliği, başlık eşliği, kenar çubuğu bütünlüğü, öksüz sayfalar, yasak terimler ve görsel referansları |
| `scripts/smoke_test.py` | Temel bir uygulama duman testi |
| `scripts/linux_release_smoke.py` | Paketli Linux çıktılarına karşı duman testi |
| `scripts/check_release_consistency.ps1` | Bir sürüm için sürüm, etiket, değişiklik günlüğü ve yardım dosyası tutarlılığı |

## Sürekli tümleştirme

GitHub Actions CI kasıtlı olarak devre dışıdır. Önceki iş akışı
`.github/workflows/` dışında, `docs/ci-disabled/ci.yml` konumunda korunur; bu
nedenle normal push ve pull request işlemleri CI çalıştırmaz. Depo doğrulaması
şimdilik yerel olarak yapılır; bkz. `docs/REMEDIATION_STATUS_2026-09-11.md`.

Bu değişiklikten sonra hiçbir CI işinin başarılı olduğu iddia edilmez.

## Sürüm CI'ı

`.github/workflows/release.yml` ayrıdır ve elle tetiklenir. Her iki platformu
derler ve yüklemeden önce gerçek çıktılara karşı paketli duman testleri
çalıştırır. Bkz. [[Sürüm Süreci|Release-Process-TR]].

## Pull request açmadan önce

```bash
PYTHONPATH=src python scripts/check_i18n.py
python scripts/check_branding.py
python scripts/check_wiki.py
PYTHONPATH=src QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
```

## Ayrıca bkz.

[[Katkıda Bulunma|Contributing-TR]] · [[Mimari|Architecture-TR]] · [[Kaynaktan Derleme|Building-from-Source-TR]]
