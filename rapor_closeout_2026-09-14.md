# Test Suite Integration Closeout — Devam Raporu (2026-09-14)

Durum: **READY TO MERGE INTO DEVELOP.** Her iki kapatma engeli çözüldü; yetkili sürüm paketi ve kapsam (coverage) kapısı exit 0 ile geçti; daha önce düzeltilen kusurlar devam HEAD'inde yeniden doğrulandı. Sürüm yayını hazırlığı (release readiness) ayrı bir karardır ve NO-GO olarak kalmaktadır.

## 1. Kesintiye uğrayan çalışmanın devralındığı nokta

- Dal: `test-suite-governance-integration-closeout-20260913`
- Çalışma ağacı: `D:\Projeler\hpc-client-gui-integration-closeout`
- Devralınan HEAD: `09a4c014b003f070541cdeac59d5ce4c0f7c9ecf`
- Devralınan commitler:
  - `d47d04f9` fix: fall back to remote path when entry name is empty
  - `31a2aca4` test: preserve wx app ownership across stress tests
  - `09a4c014` test: clean up wx stress windows between modules
- Kesinti anındaki durum: taksonomi tamam; Blocker A düzeltilmiş; Blocker B için stres testi sahiplik düzeltmeleri yapılmış ancak 02:11 geniş koşusu hedef testte hâlâ `PyNoAppError` veriyordu; kök neden minimizasyonu sürüyordu (03:53'e kadar iz kayıtları, tekrar üretmeyen üç adet 31-düğüm denemesi).

## 2. Repository sonucu

```text
Başlangıç SHA: 09a4c014b003f070541cdeac59d5ce4c0f7c9ecf
Bitiş SHA:      a2c0f6e18b404ddc1688ad3af8f24c9a3d165644
Dal:            test-suite-governance-integration-closeout-20260913
Çalışma ağacı:  temiz
Push:           evet — origin/test-suite-governance-integration-closeout-20260913
                21ff7d55..a2c0f6e1 (develop'a dokunulmadı)
```

Devam oturumunda üretilen commitler:

| SHA | Amaç | Doğrulama |
| --- | --- | --- |
| `c1f3642e` | fix: preserve wx app ownership across test lifecycle | Yetkili sürüm paketi exit 0; coverage exit 0 (66.38%); komşu modül grubu 78 passed; mutasyon doğrulandı |
| `a2c0f6e1` | docs: finalize integration closeout | Doküman tarayıcı testleri 9 passed |

## 3. Blocker A — Uzak dosya filtresi (çözüldü)

```text
İlk durum:  Geniş koşuda FAILED; Logs filtresi seçilince liste boş kalıyordu, run.log görünmüyordu.
Kök neden:  file_filter_registry._entry_name, dolu RemoteEntry.path yerine boş RemoteEntry.name'i
            tercih ediyordu; uzantı filtresi hiçbir dosya adı göremiyordu.
Düzeltme:   Anlamlı ve boş olmayan ad önceliklidir; ad yok/boş/beyaz ise yolun basename'i kullanılır
            (ters bölü normalize edilir, sondaki eğik çizgi kırpılır). run.log veya Logs filtresine
            özel durum eklenmedi; test fixture'ı değiştirilmedi.
Kanıt:      Hedef düğüm 1 passed; registry + hedef 23 passed; tüm geniş/coverage koşularında geçti.
Mutasyon:   Yol yedeği kaldırıldığında 2 failed (hedef GUI + registry edge case); geri alınınca pass.
```

Dosyalar: `src/hpc_gui/services/file_filter_registry.py`, `tests/test_file_filter_registry.py` (commit `d47d04f9`).

## 4. Blocker B — wx uygulama sahipliği (çözüldü)

```text
İlk geniş hata:  tests/test_wx_files_sync_compare.py içinde PyNoAppError
                 ("The wx.App object must be created first!"), iki ardışık geniş koşuda.
Kök neden:       C++ wxApp süreç-genelidir. wxPython, herhangi bir wx.App sarmalayıcısı
                 çöp toplama ile yok edildiğinde süreç-geneli uygulamayı da yok eder;
                 sarmalayıcı daha yeni bir uygulama tarafından değiştirilmiş olsa bile.
                 Hedef modül uygulamasını _get_files_page içinde sahipsiz oluşturuyordu;
                 sarmalayıcı yalnızca çerçeve döngüleri üzerinden yaşıyordu.
İz kanıtı:       Enstrümante geniş koşuda uygulama test setup'ında mevcut, teardown'da yok;
                 arada hiçbir wx.App.Destroy çağrısı yok (deallocation yolu).
Süpürme kanıtı:  Yalnızca hedef modül düzeltilmiş haldeyken hata başka modüllere taşındı
                 (test_wx_file_actions_lifecycle.py ve test_wx_file_actions_stress.py),
                 yani kirlilik süreç geneline yayılıyor.
Düzeltme:        (1) tests/conftest.py: yeni bir wx.App kurulmadan önce, değiştirilecek olan
                     uygulama hâlâ güncel uygulama iken yok edilir; böylece en fazla bir canlı
                     yerel uygulama kalır ve terk edilmiş sarmalayıcı zaman bombası kalkar.
                 (2) tests/test_wx_files_sync_compare.py: modül kapsamlı autouse wx_app fixture'ı
                     uygulamaya sahip olur ve modül sonunda yalnızca kendi oluşturduğunu yok eder;
                     _get_files_page artık fixture'ın sahibi olduğu uygulamayı şart koşar.
                 Hiçbir test atlanmadı, yeniden adlandırılmadı, zayıflatılmadı.
Sıra regresyonu: tests/test_wx_files_sync_compare.py::test_wx_files_sync_app_survives_forced_collection
                 (primary: gui; qualifiers: regression, resource, semantic, wx).
                 Kabuk oluşturur, kapatır, tüm güçlü referansları bırakır, gc.collect()
                 zorlar, sahipli uygulamanın hâlâ güncel olduğunu ve ikinci bir kabuğun
                 kurulabildiğini doğrular.
Mutasyon:        conftest koruması kaldırılınca regresyon başarısız; modül fixture'ı
                 kaldırılıp sahipsiz oluşturmaya dönülünce sahiplik regresyonu hata verir.
```

Kanıt dosyası: [`audit/test-governance/integration-closeout-20260914/wx-app-order-minimization.json`](audit/test-governance/integration-closeout-20260914/wx-app-order-minimization.json).

## 5. Önceki düzeltmelerin yeniden doğrulaması

| Kusur | Koşulan sahip | Sonuç |
| --- | --- | --- |
| Yerel dizin izin hatası | `test_list_entries_permission_error` (+ rename selection ve Notebook callback) | 3 passed, exit 0 |
| Rename seçim koruması | aynı odaklı koşu | 3 passed, exit 0 |
| Yok edilmiş Notebook callback'i | aynı odaklı koşu | 3 passed, exit 0 |
| Jobs uzak-okuma örtüşmesi | `test_wx_jobs_behavior`, `test_wx_jobs_files_outputs`, `test_wx_jobs_final_fix`, `test_wx_jobs_stress` | 50 passed, exit 0 |
| Plugin menü takılması | `tests/test_hardening_additional.py` (25 döngülük sahip dahil) | 12 passed, exit 0 |
| Uzak boş-ad filtresi | hedef düğüm + `tests/test_file_filter_registry.py` | 23 passed, exit 0 |

## 6. Taksonomi

```text
Toplam: 2658
Primary: unit 760, gui 674, contract 566, integration 362, audit 159,
         release 102, reporting 22, e2e 7, runtime_smoke 6
zero-primary: 0
multi-primary: 0
semantic: 965, regression: 164, resource: 121
Ratchet: PASS (sıfır borç taban çizgisine karşı)
```

## 7. Yetkili sürüm paketi

```text
Komut:  python -X faulthandler scripts/release_test_suite.py
Exit:   0 — "[release-test-suite] all release preflight gates passed"
Ön kontrol: compileall, check_i18n, smoke_test tümü exit 0
Geniş çocuk: 2402 passed, 0 failed, 20 skipped, 4 deselected, 29 subtests passed
             (1484.25 sn / 24dk 44sn)
İzole gruplar:
  tests/test_ftp_widget.py               168 passed (14.63 sn)
  tests/test_download_cancel_wire.py       4 passed (13.39 sn)
  tests/test_editor_flow.py               14 passed (0.50 sn)
  tests/test_corrective_jobs_details.py   17 passed (8.67 sn)
  tests/test_wx_terminal_webview.py       29 passed (24.14 sn)
xfail/xpass: 0
```

## 8. Yetkili kapsam (coverage)

```text
Komut:  python scripts/release_test_suite.py --coverage
Exit:   0
Kapsam: 66.38% (gereken eşik 65%) — "Required test coverage of 65% reached."
Geniş çocuk: 2402 passed, 0 failed, 20 skipped, 4 deselected, 29 subtests passed
             (1470.31 sn / 24dk 30sn)
İzole gruplar: 168 / 4 / 14 / 17 / 29 passed (coverage append ile)
Çıktılar: coverage.json, coverage.xml
```

## 9. Doğrulama tablosu

| Komut | Exit |
| --- | --- |
| `python -m pytest tests --collect-only -q` (2658 düğüm) | 0 |
| `python scripts/check_test_taxonomy.py --mode report` | 0 |
| `python scripts/check_test_taxonomy.py --mode ratchet --baseline audit/test-governance/integration-closeout-20260913/taxonomy-ratchet-strict.json` | 0 (PASS) |
| `python -m compileall -q src/hpc_gui` | 0 |
| `python -m ruff check src tests scripts` | 0 |
| `python scripts/check_i18n.py` | 0 |
| `python scripts/smoke_test.py` | 0 |
| `git diff --check` | 0 |
| Sahiplik korumalı komşu modül grubu (78 test) | 0 |
| Doküman/audit tarayıcıları (9 test) | 0 |
| Aşırı GC eklentisiyle hedef modül (9 test) | 0 |

## 10. Koleksiyon deltası

```text
2657 → 2658
Eklenen:  tests/test_wx_files_sync_compare.py::test_wx_files_sync_app_survives_forced_collection
Kaldırılan: yok
Yeniden adlandırılan: yok
```

Kanıt: [`collection-delta.json`](audit/test-governance/integration-closeout-20260914/collection-delta.json).

## 11. Kararlar

```text
Merge hazırlığı: READY TO MERGE INTO DEVELOP
```

Gerekçe: yetkili sürüm paketi exit 0; kapsam kapısı exit 0 (66.38% ≥ 65%); koleksiyon temiz (zero-primary 0, multi-primary 0); her iki engel regresyon kanıtıyla düzeltildi; önceki tüm kusurlar devam HEAD'inde geçiyor; compileall/ruff/i18n/smoke geçiyor.

```text
Sürüm yayını hazırlığı: NO-GO (ayrı karar)
```

- Windows paketlenmiş smoke: FAIL/PARTIAL
- GUI-TERM-001: PARTIAL
- Linux paketlenmiş wx/WebKit: NOT EVIDENCED
- macOS paketlenmiş runtime: NOT EVIDENCED
- Canlı küme: NOT EVIDENCED
- Paketlenmiş GUI manuel onayı: NOT EVIDENCED
- Otomatik CI kasıtlı olarak devre dışı; manuel sürüm iş akışı yalnızca `workflow_dispatch`.

## 12. Kalan sorunlar

- Merge'ü engelleyen açık sorun yok.
- Ortam notu: Aynı makinede eşzamanlı iki tam GUI paketi çalıştığında yerel erişim ihlalleri (native AV) gözlemlendi; geçen yetkili koşular makine sakin iken alındı. Değiştirme anında eski uygulamayı yok eden conftest koruması ve hedef modülün sahiplik fixture'ı bu sınıfı kapatır.
- Dokümanlar: kapatma raporunun devam bölümü `docs/testing/TEST_SUITE_INTEGRATION_CLOSEOUT_2026-09-13.md`; özet güncellemeler `PHASE_2_EXECUTION_REPORT.md` ve `TEST_TAXONOMY_FINAL_REPORT.md` içinde.
