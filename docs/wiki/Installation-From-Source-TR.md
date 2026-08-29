# Kaynaktan Kurulum

> English: [[Installation-From-Source]]

Kaynaktan çalıştırma Windows ve Linux'ta işler ve size paketli derlemelerle
aynı uygulamayı ve aynı komut satırı arayüzünü verir.

## Gereksinimler

- Python 3.14.x (`requires-python = "==3.14.*"`).
- Linux'ta PySide6'nın ihtiyaç duyduğu Qt platform kitaplıkları
  (Ubuntu/Debian'da `libegl1`, Fedora ve openSUSE'de dağıtımın karşılığı).
- İsteğe bağlı, yalnızca X11 için: Windows'ta `plink.exe` ve VcXsrv, Linux'ta
  sistem OpenSSH istemcisi.

## Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[test]
python -m hpc_gui
```

## Linux

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[test]
python -m hpc_gui
```

## Kurulum seçenekleri

- `pip install -e .` yalnızca uygulamayı kurar.
- `pip install -e .[test]` ek olarak test bağımlılıklarını kurar; çevrimdışı
  test paketini çalıştırmak için bunlara ihtiyacınız vardır. Bkz.
  [[Test ve CI|Testing-and-CI-TR]].

## Komut satırı arayüzü

Aynı giriş noktası komut satırına da hizmet eder:

```bash
python -m hpc_gui --help
```

Yardım çıktısında görünen program adı `hpc-client-gui` şeklindedir. Bkz.
[[CLI Kılavuzu|CLI-Guide-TR]].

## Masaüstü uygulamasını başsız çalıştırma

Otomatik denetimler için Qt'nin offscreen platformu pencere açılmasını önler:

```bash
QT_QPA_PLATFORM=offscreen python -m hpc_gui --help
```

## Sonraki adımlar

[[Kaynaktan Derleme|Building-from-Source-TR]] · [[Mimari|Architecture-TR]] · [[Katkıda Bulunma|Contributing-TR]]
