# Uzak Dosya Yöneticisi

> English: [[Remote-File-Manager]]

Yan yana iki panel: bir tarafta **Local**, diğer tarafta uzak dizin. İkisi
arasındaki aktarımlar [[Dosya Aktarımları|File-Transfers-TR]] sayfasında
anlatılır; bu sayfa gezinme ve dosya işlemleriyle ilgilidir.

![Remote File Manager](https://raw.githubusercontent.com/wiki/mskomek/hpc-client-gui/assets/file-manager.png)

*Solda yerel panel, sağda uzak dizin, altta aktarım kuyruğu.*

## Gezinme

**Back**, **Up** ve **Refresh** ağaçta dolaşır; yerel birimler için
**Drives**, uzak tarafta **Home** ve **Scratch** kısayolları bulunur. Geçerli
yol **Directory** alanında gösterilir ve geçerli klasör **Set current folder as
default Home** ya da **Set current folder as default Scratch** ile öntanımınız
olarak kaydedilebilir.

Listeler **Name**, **Size**, **Type** ve **Modified** sütunlarıyla gösterilir;
süzgeç sekmeleri daraltır: **All**, **Folders**, **ISO**, **Archives**,
**Slurm**, **SH** ve **Other**.

Bir uzak dizin okunamazsa panel, sessizce boş bir klasör göstermek yerine
hatayı bildirir.

## Oluşturma

**New**, bir **New Folder** ya da **New File** oluşturur ve adı sorar. Boş olan
ya da `/` veya `\` içeren bir ad reddedilir; var olan bir ad üzerine yazılmak
yerine bildirilir.

## Kopyala, taşı, yapıştır

Pano iki panel arasında çalışır:

| Eylem | Etkisi |
|---|---|
| **Copy** / **Move** | Seçimi panoya alır |
| **Paste** | Geçerli klasöre yapıştırır |
| **Paste into folder** | Vurgulanan klasöre yapıştırır |
| **Paste from local** / **Paste from local into folder** | Yerel pano içeriğini yükler |
| **Paste to local (download)** | Uzak pano içeriğini indirir |
| **Copy path with file name** | Tam yolu metin olarak kopyalar |
| **Undo** | Son taşımayı geri alır |

Paneller arasında sürükle bırak da çalışır.

Uzun işlemler, çalışanı (**Now**) ve bekleyeni (**Next**) gösteren bir
**Operation queue** üzerinden yürür; **Cancel** ile durdurabileceğiniz bir
ilerleme kutusu eşlik eder. İptal, sessizce bırakılmak yerine bildirilir.

## Ad çakışmaları

Bir ad zaten varsa ne yapılacağı sorulur: **Overwrite**, **Skip**, **Rename**
veya **Cancel**. Aktarımların daha zengin bir seçenek kümesi vardır — bkz.
[[Dosya Aktarımları|File-Transfers-TR]].

## Yeniden adlandırma ve silme

**Rename** tam olarak bir öğe seçilmesini ister ve yeni adı sorar. **Delete**,
seçimi kaldırmadan önce onay ister.

## İzinler

**Change file attributes**, uzak öğelerdeki POSIX izinlerini düzenler. Sekizlik
bir kip (`755`, `0644`) yazabilir ya da **Owner**, **Group** ve **Others** için
okuma/yazma/çalıştırma ızgarasını kullanabilirsiniz; ayrıca **Set-user-ID**,
**Set group-ID** ve **Sticky bit** vardır. Değişiklikler alt dizinlere
inebilir; her şeye, yalnızca dosyalara ya da yalnızca dizinlere uygulanabilir.
Geçersiz bir kip açıklamayla reddedilir, başarısız bir güncelleme bildirilir.

## Dosyalarla yerinde çalışma

| Eylem | Etkisi |
|---|---|
| **Edit** / **Edit in new window** | Dosyayı betik düzenleyicide açar |
| **Download** / **Download selected** | Yerel tarafa getirir |
| **Upload** | Yerel dosyaları geçerli uzak klasöre gönderir |
| **Save as** | Seçilen bir konuma indirir |
| **Open with…** | Dosyayı yerel bir programda açar; seçimi o uzantı için kaydedebilirsiniz |
| **Template Upload** | Birlikte gelen bir şablonu yükler |

Klasörler düzenlenemez; uygulama boş bir düzenleyici açmak yerine bunu söyler.

## Slurm ve kabuk dosyaları

Betik dosyalarının kendi eylemleri vardır:

- **Create/Edit Slurm**, **Core**, **CPU**, **GPU** veya **MPI** şablonundan
  başlar, dosya adını sorar ve var olan bir dosyanın üzerine yazmadan önce
  sorar. Bkz. [[İş Betiği Şablonları|Job-Script-Templates-TR]].
- **Submit with sbatch** ve çoklu seçim için **Submit all with sbatch**. Toplu
  gönderim, kaç betiğin gönderildiğini ve kaçının başarısız olduğunu bildirir.
- Kabuk betikleri için **Run in terminal** ve **Run all in terminal**. Bkz.
  [[Terminal ve Uzak Komutlar|Terminal-and-Remote-Commands-TR]].

Başarılı bir gönderim, işler görünümünün ardından izlediği iş kimliğini
bildirir — bkz. [[Slurm İşleri|Slurm-Jobs-TR]].

## Dizin listeleme önbelleği

Gezilen uzak klasörler, gezinmeyi hızlandırmak için bellekte tutulabilir;
oluşturma, silme ve yenileme işlemleri ilgili girdiyi günceller. Önbellek
Ayarlar'dan kapatılabilir veya temizlenebilir — bkz.
[[Ayarlar Referansı|Settings-Reference-TR]].

## Komut satırından

```bash
hpc-client-gui --profile mycluster files ls /scratch/$USER
hpc-client-gui --profile mycluster files mkdir /scratch/$USER/run1
hpc-client-gui --profile mycluster files rm /scratch/$USER/old --recursive --yes
```

Bkz. [[CLI Kılavuzu|CLI-Guide-TR]].

## Ayrıca bkz.

[[Dosya Aktarımları|File-Transfers-TR]] · [[Betik Düzenleyici|Script-Editor-TR]] · [[Ayarlar Referansı|Settings-Reference-TR]]
