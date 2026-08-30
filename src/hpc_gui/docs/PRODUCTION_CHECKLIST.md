# HPC Client GUI — Production Checklist (Windows)

Bu dosya, HPC Client GUI'nin "ürün" gibi paketlenip sahada kullanılmasında en sık sorun çıkaran alanlar için tek sayfalık kontrol listesidir.

## 1) Windows / Ortam

- [ ] Windows 10/11 (x64)
- [ ] Python/PySide6 sürümü sabit (paketleme yapılıyorsa tek exe)
- [ ] Antivirus/EDR politikaları: `vcxsrv.exe` ve `plink.exe` ilk çalıştırmada engellenmiyor

## 2) VcXsrv (X11)

- [ ] HPC Client GUI tarafından kullanılan VcXsrv tek instance
- [ ] `127.0.0.1:6000` dinliyor (DISPLAY `:0`)
- [ ] VcXsrv argümanları: `-listen tcp` (plink -X için gerekli)
- [ ] Loglar:
  - `~/.truba_slurm_gui/vcxsrv_stdout.log`
  - `~/.truba_slurm_gui/vcxsrv_stderr.log`

## 3) PuTTY / plink

- [ ] `~/.truba_slurm_gui/third_party/putty/plink.exe` mevcut (ya da sistem PATH)
- [ ] X11 komutu plink ile çalıştırılıyorsa: `-X -t` ve `env TERM=xterm bash -lc '...'
- [ ] Şifre/token hiçbir zaman history veya UI log içine düşmüyor

## 4) SSH / Paramiko

- [ ] Paramiko yalnızca "normal" komutlar + SFTP için
- [ ] X11 forwarding için Paramiko kullanılmıyor

## 5) Dosya İşlemleri (Remote Files)

- [ ] Permission denied / quota / read-only durumlarında kullanıcıya anlaşılır mesaj
- [ ] Büyük dosya transferlerinde "resume" davranışı doğrulandı
- [ ] Kapanışta aktif batch işlemleri iptal ediliyor (best-effort) ve `~/.truba_slurm_gui/last_batch.json` yazılabiliyor (diagnostics)

## 6) Loglar

- [ ] `~/.truba_slurm_gui/app.log` yazılıyor (rotating)
- [ ] Uncaught exception loglanıyor
- [ ] Kapanışta `graceful shutdown completed` satırı görülüyor

## 7) i18n

- [ ] `tr.json` ve `en.json` key setleri uyuşuyor (startup log'da drift warning yok)

## 8) Saha Troubleshooting (en hızlı kontrol)

1. `app.log` içinden son hata bloğunu bulun
2. X11 ise: VcXsrv loglarına bakın
3. SSH ise: ağ/VPN/port 22 erişimini kontrol edin
4. Permission/quota ise: hedef dizinde `ls -l`, `df -h`, `quota` (varsa)

## 9) Release doğrulaması

- [ ] `scripts/release.ps1` EXE başlangıç smoke testini ve geçici yerel FTP
  upload/download bütünlük testini tamamladı
- [ ] Gerçek kümeye giden release için, ayrılmış test hesabıyla SFTP bağlantısı,
  dizin, upload/download ve SHA-256 doğrulaması kaydedildi
- [ ] Local Turkish-filename transfer gate and the `sftp-smoke/1` JSON artifact
  placement under the version folder were verified locally before any live-cluster
  release step

## 10) CLI Bakım Politikası

- [ ] Yeni/değişen bir CLI komutu varsa `MAINTENANCE_POLICY.md`'deki gate'ler
  (help metni, JSON sözleşmesi, unit test, ilgiliyse smoke, TODO/CHANGELOG)
  sağlandı — bkz. [MAINTENANCE_POLICY.md](MAINTENANCE_POLICY.md)

## 11) Plugin and signed-update release gates
- [ ] `UPDATE_SIGNING_PRIVATE_KEY_B64` contains the Ed25519 private key matching
  embedded key id `release-2026-01`; it exists only as a protected Actions secret.
- [ ] `UPDATE_METADATA.json` was generated and its signature, platform, size,
  digest, and GitHub release URL passed the updater verification tests.
- [ ] Development CI may follow the plugin registry's `main`; **before cutting a
  release, pin the "Plugin API contract" job's checkout `ref:` in
  `.github/workflows/ci.yml` to an explicit plugin repository tag or commit**
  and advance that pin intentionally after the release.
- [ ] The pinned contract suite passed against the real registry content
  (registry validation, manifests, hashes, TRUBA profile load, declarative lint
  rules and template rendering, update/rollback). No plugin payload is executable.
- [ ] Release workflow uses commit-SHA-pinned third-party actions (see
  .github/workflows/release.yml); version comments kept next to each SHA.
