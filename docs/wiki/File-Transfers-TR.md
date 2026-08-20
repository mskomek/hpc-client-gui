# Dosya Aktarımları

> English: [[File-Transfers]]

Yüklemeler ve indirmeler kendi görünümü olan bir kuyruk üzerinden ilerler;
böylece uzun bir aktarım arayüzün geri kalanını asla bloke etmez.

## Aktarımı başlatma

**Upload selected** ve **Download selected** geçerli seçim üzerinde çalışır;
sürükle bırak ve panonun yapıştırma eylemleri de aynı işi yapar. Hiçbir şey
seçili değilse uygulama sessiz kalmak yerine bunu söyler.

## Aktarım türü

**Transfer type**; **Auto**, **Binary** veya **ASCII** olabilir ve panel
kullanılan etkin kipi gösterir. Öntanım Ayarlar'dan belirlenir — bkz.
[[Ayarlar Referansı|Settings-Reference-TR]].

## Aktarım görünümü

Dört sekme: **Queue**, **Transfers** (etkin), **Failed** ve **Completed**.

Denetimler:

| Denetim | Etkisi |
|---|---|
| **Process Queue** | Kuyruğu işlemeye başlar |
| **Stop** | Geçerli aktarım bittikten sonra durur |
| **Cancel** / **Cancel all** | Geçerli aktarımı veya hepsini iptal eder |
| **Stop and remove all** | Durdurur ve kuyruğu temizler |
| **Retry failed** / **Retry selected** | Başarısızları yeniden kuyruğa alır |
| **Remove selected** | Girdileri kuyruktan çıkarır |
| **Clear queued** / **Clear failed** / **Clear completed** | Listeleri toparlar |
| **Set Priority** | Highest, High, Normal, Low veya Lowest |

İlerleme; çalışan öğeyi, aktarılan ve toplam bayt sayısını, anlık hızı ve
tahmini kalan süreyi gösterir. Geçerli aktarımdan sonra durma ile iptal
etmenin ikisi de ayrı ayrı bildirilir; böylece hangisinin gerçekleştiğini
bilirsiniz.

## Paralellik

Yapılandırılan paralel aktarım sınırı görünümde gösterilir. Paralel yüklemeler
ve indirmeler yalıtılmış kanallar kullanır; diğer dosya işlemleri sıralı
kalır. Bir profil genel sınırı geçersiz kılabilir — bkz.
[[Bağlantı ve Profiller|Connecting-and-Profiles-TR]].

## Yükleme planı onayı

Etkinleştirildiğinde bir yükleme önce planını gösterir: her girdi için
**Operation** (**Upload**, **Create folder**, **Delete existing**), **Source**
ve **Destination**. **Start transfer** devam ettirir; **Don't ask again**
onayı kapatır.

Bir aktarımın bir şeyi sileceğini yapmadan önce görebileceğiniz son nokta
budur.

## Çakışmalar

Hedef dosya zaten varsa çakışma iletişim kutusu her iki dosyayı boyut ve
değişiklik zamanıyla gösterir ve şunları sunar:

| Eylem | Etkisi |
|---|---|
| **Overwrite** | Koşulsuz değiştirir |
| **Overwrite if source newer** | Yalnızca kaynak daha yeniyse değiştirir |
| **Overwrite if different size** | Yalnızca boyutlar farklıysa değiştirir |
| **Overwrite if different size or source newer** | Yukarıdakilerden biri |
| **Resume** | Kesilen aktarımı sürdürür |
| **Rename** | İkisini de saklar |
| **Skip** | Hedefe dokunmaz |

Seçim **Always use this action** ile anımsanabilir; **Apply to current queue
only** veya **Apply only to downloads** ile kapsamı daraltılabilir.

## Sürdürme

**Resume**, kesilen bir aktarımı baştan başlatmak yerine sürdürür; güvenilmez
bağlantılardaki büyük dosyalarda bu önemlidir. Aktarım durumu yerelde günlüğe
yazıldığı için sürdürme, uygulamanın yeniden başlatılmasından sonra da
geçerlidir.

## Bütünlüğü doğrulama

**Verify transfers with SHA-256 after completion** etkinken bir aktarım
başarılı sayılmadan önce kaynak ve hedef sağlama toplamları karşılaştırılır.
Komut satırındaki karşılığı `--verify` seçeneğidir:

```bash
hpc-client-gui --profile mycluster files download /scratch/$USER/out.csv ./out.csv --verify
hpc-client-gui --profile mycluster files upload ./inputs /scratch/$USER/inputs --recursive --if-exists resume
```

`--if-exists`; `overwrite`, `skip`, `rename` veya `resume` alır. Bkz.
[[CLI Kılavuzu|CLI-Guide-TR]].

## Hızı ölçme

**Run remote transfer speed test**, uzak arka uçta yapılandırılan boyutta
geçici bir dosyayı yükler ve indirir, doğrular, siler ve yükleme ile indirme
hızlarını bildirir. Bu bir tahmin değil, kümenize karşı gerçek bir
gidiş-dönüştür.

## Kuyruk bittiğinde

Kuyruk boşaldığında bir eylem çalışabilir: hiçbiri, bildirim balonu, dikkat
isteme, ses, bir komut, uygulamayı kapatma (bir kerelik veya kalıcı) ya da bir
kerelik sistem yeniden başlatma, kapatma veya askıya alma.

Bir kerelik seçenekler yalnızca bir sonraki tamamlanmaya uygulanır — gece
boyunca sürecek bir aktarım için, sonrasında ne olacağını kalıcı olarak
değiştirmeden kullanışlıdır.

## Ayrıca bkz.

[[Uzak Dosya Yöneticisi|Remote-File-Manager-TR]] · [[Ayarlar Referansı|Settings-Reference-TR]] · [[Sorun Giderme|Troubleshooting-TR]]
