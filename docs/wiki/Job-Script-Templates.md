# Job Script Templates

> Türkçe: [[Job-Script-Templates-TR]]

Three starter templates ship with the project, under `templates/`:

| File | For |
|---|---|
| `template_cpu.slurm` | Single-node CPU jobs |
| `template_gpu.slurm` | Single-node GPU jobs |
| `template_mpi.slurm` | Multi-node MPI jobs |

They are starting points, not portable defaults. **The partition names and
resource sizes in them are examples** and must be replaced with values valid
for your cluster and your account — see [[Slurm Help Library|Slurm-Help-Library]]
for how to find those.

## CPU template

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

## GPU template

Same shape, with a GPU request and a larger memory and time allowance:

```bash
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
```

It starts from a clean module environment (`module purge`) with the CUDA module
load commented out, because the module name differs by site.

## MPI template

```bash
#SBATCH --nodes=2
#SBATCH --ntasks=64
#SBATCH --cpus-per-task=1
#SBATCH --time=01:00:00
```

It also starts with `module purge`, and shows the MPI module load and the
`srun ./mpi_app` launch commented out.

## Conventions worth keeping

- **`set -euo pipefail`** — the job stops on the first error instead of running
  on with a broken state and reporting success.
- **`logs/%x_%j.out` and `.err`** — output is named by job name and job ID, so
  concurrent runs do not overwrite each other. Create the `logs` directory
  before submitting; Slurm will not create it for you and the job will fail at
  once if it is missing.
- **`module purge` first** — a clean environment makes a job reproducible
  regardless of what your login shell had loaded.
- **Request what you use.** Over-requesting CPUs, memory, or time delays
  scheduling; under-requesting gets the job killed.

## Using a template

Copy it to the cluster, edit it for your job, and submit. Editing:
[[Script Editor|Script-Editor]]. Submitting: [[Slurm Jobs|Slurm-Jobs]] or

```bash
hpc-client-gui --profile mycluster jobs submit /scratch/$USER/job.sh --yes
```

## See also

[[Slurm Help Library|Slurm-Help-Library]] · [[Scripting Examples|Scripting-Examples]] · [[Job Outputs|Job-Outputs]]
