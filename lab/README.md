# LOCAL_REAL HPC laboratory

This is a disposable, real-infrastructure Hyper-V lab. It runs three separate
Ubuntu VMs, real OpenSSH/SFTP, MUNGE, Slurm, MariaDB, and NFS. It is not a
mock server or an in-process test fixture.

Run PowerShell as Administrator from the repository root:

```powershell
lab\lab-up.ps1
lab\lab-status.ps1
lab\lab-test.ps1
lab\lab-fault.ps1 -Action drain -Node compute01
lab\lab-reset.ps1
lab\lab-down.ps1
```

Prerequisites: Windows 11/Server Hyper-V, an Ubuntu cloud image download,
WSL with `genisoimage` and `qemu-img` (used only to build NoCloud seed ISOs
and convert the cloud image), and Windows
OpenSSH (`ssh`, `sftp`, `ssh-keygen`). The generated key, host keys, VM disks,
and reports stay under `lab/state/` and `lab/evidence/`, which are ignored.

The profile shape used by the application is written to
`lab/state/hpc-client-profile.json` after `lab-up.ps1`; import it into a
disposable application profile or use the existing CLI profile commands. No
TRUBA production profile is changed.

The first milestone is intentionally reported as `LOCAL_REAL_READY`, not W22
PASS. W22 still needs the exact packaged GUI artifact and its full GUI/package
evidence. See `lab/evidence/W22_LOCAL_REAL_GAP_REPORT.md` after a healthy run.
