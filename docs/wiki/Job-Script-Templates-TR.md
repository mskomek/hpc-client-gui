# İş Betiği Şablonları

> English: [[Job-Script-Templates]]

Projeyle birlikte `templates/` altında üç başlangıç şablonu gelir:

| Dosya | Ne için |
|---|---|
| `template_cpu.slurm` | Tek düğümlü CPU işleri |
| `template_gpu.slurm` | Tek düğümlü GPU işleri |
| `template_mpi.slurm` | Çok düğümlü MPI işleri |

Bunlar başlangıç noktalarıdır, taşınabilir öntanımlar değil. **İçlerindeki
bölüm adları ve kaynak boyutları örnektir** ve kümeniz ile hesabınız için
geçerli değerlerle değiştirilmelidir — bu değerleri nasıl bulacağınız için bkz.
[[Slurm Yardım Kütüphanesi|Slurm-Help-Library-TR]].

## CPU şablonu

```bash
#!/bin/bash
#SBATCH -p <partition>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --job-name=cpu_job
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail
```

## GPU şablonu

Aynı yapı; bir GPU isteği ile daha büyük bellek ve süre payı:

```bash
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
```

Temiz bir modül ortamıyla (`module purge`) başlar ve CUDA modülü yükleme satırı
yorum içinde bırakılmıştır, çünkü modül adı siteye göre değişir.

## MPI şablonu

```bash
#SBATCH --nodes=2
#SBATCH --ntasks=64
#SBATCH --cpus-per-task=1
#SBATCH --time=01:00:00
```

O da `module purge` ile başlar; MPI modülü yükleme ve `srun ./mpi_app` başlatma
satırlarını yorum içinde gösterir.

## Korunmaya değer alışkanlıklar

- **`set -euo pipefail`** — iş, bozuk bir durumda devam edip başarı bildirmek
  yerine ilk hatada durur.
- **`logs/%x_%j.out` ve `.err`** — çıktı, iş adı ve iş kimliğiyle adlandırılır;
  böylece eşzamanlı çalışmalar birbirinin üzerine yazmaz. Göndermeden önce
  `logs` dizinini oluşturun; Slurm bunu sizin için oluşturmaz ve eksikse iş
  hemen başarısız olur.
- **Önce `module purge`** — temiz bir ortam, oturum kabuğunuzda ne yüklü
  olursa olsun işi yeniden üretilebilir kılar.
- **Kullandığınız kadarını isteyin.** Fazla CPU, bellek veya süre istemek
  zamanlamayı geciktirir; az istemek işin öldürülmesine yol açar.

## Bir şablonu kullanma

Kümeye kopyalayın, işiniz için düzenleyin ve gönderin. Düzenleme:
[[Betik Düzenleyici|Script-Editor-TR]]. Gönderme:
[[Slurm İşleri|Slurm-Jobs-TR]] ya da

```bash
hpc-client-gui --profile mycluster jobs submit /scratch/$USER/job.sh --yes
```

## Ayrıca bkz.

[[Slurm Yardım Kütüphanesi|Slurm-Help-Library-TR]] ·
[[Betik Örnekleri|Scripting-Examples-TR]] ·
[[İş Çıktıları|Job-Outputs-TR]]
