# Cluster Compatibility Validation (Read-Only)

This kit proves how HPC Client GUI behaves on a standard SSH + Slurm system
**without running anything state-changing**. It is written for an authorized
user validating their own cluster; the application developers never connect to
any cluster themselves.

Compatibility wording used across this project:

- **Designed for** — generic SSH/SFTP/Slurm behavior targeted by the code.
- **Expected compatible** — plausible but not yet exercised.
- **Verified on** — a real environment with a saved sanitized report.

Only environments with a report under "Verified on" may be claimed as verified.

## 1. Read-only probe

Run `scripts/slurm_readonly_probe.sh` **on the cluster login node**, from your
own account. It only prints or reads:

```text
uname -s          whoami           pwd
command -v squeue|sbatch|sacct|scancel|scontrol
squeue --version  sacct --version  scontrol --version
squeue -u "$USER" -h -o "%i|%P|%j|%u|%T|%M|%D|%C|%R"
sacct -u "$USER" --format=JobID,JobName,State,Elapsed,MaxRSS,AllocTRES -n -P
```

It never runs `sbatch`, `scancel`, `scontrol update`, any file upload/delete,
or submits a job. Set `REDACT=1` to strip your username and hostname from the
captured output before sharing it.

```bash
bash slurm_readonly_probe.sh > capture.txt          # raw, keep private
REDACT=1 bash slurm_readonly_probe.sh > capture_sanitized.txt
```

Then connect once with HPC Client GUI (read-only browsing: Jobs list and Files
browse) and note what renders.

## 2. Capability checklist

Mark each row pass/fail/unsupported. `scripts/capability_report.py` style keys
are shown so failures map back to code.

| capability key | check | result |
|---|---|---|
| ssh_connected | profile connects (password or key) | |
| sftp_available | remote files panel lists a directory | |
| slurm_squeue_available | Jobs tab shows your queue | |
| slurm_sbatch_available | `command -v sbatch` found | |
| slurm_scancel_available | `command -v scancel` found | |
| slurm_sacct_available | accounting output parses | |
| slurm_scontrol_available | job details render | |
| home_path_known | home dir auto-filled correctly | |
| scratch_path_known | scratch dir configured/preset | |
| x11_possible | optional; leave blank if untested | |

A failed capability should be reported as failed — never silently worked around.

## 3. Report template

Copy this block into a new file per validated cluster (anonymize freely):

```markdown
### Compatibility report — <label>

- Validation date: YYYY-MM-DD
- Client version: <x.y.z>
- OS client: <e.g. Windows 11 / Ubuntu 24.04>
- Cluster label: <optional anonymized label>
- SSH: pass/fail (auth method: password/key)
- SFTP browse: pass/fail
- squeue: pass/fail
- sacct: pass/fail/unsupported
- scontrol: pass/fail/unsupported
- custom preset needed: yes/no (which fields)
- known deviations: <exact command + trimmed output, host identifiers removed>
- state-changing tests performed: NO
- validator notes:
```

## 4. After a read-only pass

State-changing smoke tests (`sbatch` a trivial sleep job, cancel it, transfer a
small scratch file) are a separate, explicitly authorized step by the cluster
account owner. Attach both reports when claiming "Verified on".
