# İş Çıktıları

> English: [[Job-Outputs]]

Bir Slurm işi standart çıktısını ve standart hatasını kümedeki dosyalara yazar.
**Outputs** alanı, iş çalışırken bu dosyaları takip eder.

## İki çıktı paneli

**Output 1: Standard Output** ve **Output 2: Error Output** iki paneldir.
Etkin Slurm betiği bunların üstünde gösterilir; hiçbir şey takip edilmiyorsa
*(none)* yazar.

Listedeki bir dosya için şunları seçebilirsiniz:

- **Follow in Output 1** veya **Follow in Output 2**
- **Follow in Output 1/2 in new tab**
- **Follow in Output 1/2 in new window** ya da **Follow file in new window**
- Bir dosyayı var olan bir takip penceresine veya sekmesine göndermek için
  **Assign to \<target\> Output 1 / Output 2**

Takip sekmeleri ve pencereleri numaralanır; birleşik bir pencerenin başlığı
takip ettiği hem çıktı hem hata dosyasını adlandırır; böylece eşzamanlı
işler birbirinden ayırt edilebilir kalır.

## Canlı takip

Çıktı yazıldıkça izlenir.

| Denetim | Etkisi |
|---|---|
| **Auto-scroll** | Görünümü en yeni satırda tutar |
| **Pause live follow** | Görünümü kapatmadan güncellemeyi durdurur |
| **Resume live follow** | Devam ettirir |
| **Search output** ve **Next** | O ana dek okunanlarda metin arar |
| **Close window** / **Close tracking screen** | Takibi bırakır |

Takip durduğunda görünüm bunu açıkça söyler; sessizleşmiş canlı bir görünüm
gibi durmaz — bir işi beklerken bu fark önemlidir.

Canlı takip, pencere simge durumundayken kendiliğinden duraklatılabilir ve uzun
süren takip için düzenli bir uyarı açılıp kapatılabilir. Bkz.
[[Ayarlar Referansı|Settings-Reference-TR]].

## Gönderimden sonra ne açılır

Ayarlar'dan yapılandırılır:

| Seçim | Sonuç |
|---|---|
| Takipçi açma | İş kaydedilip yenilenir; geçerli görünüm değişmez |
| Jobs & Outputs — Outputs sekmesi | Çıktı var olan Output 1 ve Output 2 panellerinde sürer |
| Yeni takip sekmesi | Çıktı ve hatayı birlikte taşıyan yeni bir alt sekme |
| Tek birleşik takip penceresi | İkisini birlikte taşıyan bağımsız bir pencere |
| Ayrı çıktı ve hata pencereleri | İki bağımsız pencere |

Yeni takip pencereleri simge durumunda açılabilir.

## Çıktı dosyalarını bulma

**Files** ve **Scratch** panelleri, işinizin çıktısını yazdığı yere gitmenizi
sağlar. Şablonlar çıktı dosyalarını `logs/%x_%j.out` ve `.err` — iş adı ve iş
kimliği — biçiminde adlandırdığı için eşzamanlı çalışmalar birbirinin üzerine
yazmaz ve her işin dosyaları tanınabilir olur. Bkz.
[[İş Betiği Şablonları|Job-Script-Templates-TR]].

İşler ve çıktılar görünümlerinin yenileme aralığı yapılandırılabilir.

## Sonuçları indirme

Herhangi bir çıktı dosyası dosya yöneticisinden ya da komut satırından
indirilebilir:

```bash
hpc-client-gui --profile mycluster files download \
  /scratch/$USER/logs/run_123456.out ./run.out --verify
```

## Ayrıca bkz.

[[Slurm İşleri|Slurm-Jobs-TR]] · [[Uzak Dosya Yöneticisi|Remote-File-Manager-TR]] · [[Dosya Aktarımları|File-Transfers-TR]]
