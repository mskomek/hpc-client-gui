# LOCAL_REAL HPC laboratory


This is a disposable, maintainer-owned, real-infrastructure Hyper-V lab for
HPC Client GUI integration testing. It runs three separate Ubuntu VMs with
real OpenSSH/SFTP, MUNGE, Slurm, Slurm accounting, MariaDB, and NFS. It is
not a mock SSH server or an in-process scheduler fixture.


## Topology


- `login-control01` — login/controller, OpenSSH/SFTP, MUNGE, `slurmctld`,
  `slurmdbd`, MariaDB, NFS.
- `compute01` — real `slurmd` compute node.
- `compute02` — real `slurmd` compute node.
- Internal Hyper-V network: `192.168.250.0/24`.
- Test user: `hpctest`.


## Normal workflow


Run elevated PowerShell from the repository root:


```powershell
.\lab\lab-up.ps1
.\lab\lab-test.ps1
```


Useful lifecycle commands:


```powershell
.\lab\lab-status.ps1
.\lab\lab-fault.ps1 -Action drain -Node compute01
.\lab\lab-fault.ps1 -Action ssh-loss
.\lab\lab-fault.ps1 -Action reconnect
.\lab\lab-reset.ps1
.\lab\lab-down.ps1
```


When `reconnect` is called without `-Node`, it reuses the node from the last
fault record when available.


## Prerequisites


- Windows with Hyper-V enabled.
- Windows OpenSSH: `ssh`, `sftp`, `ssh-keygen`.
- WSL with `genisoimage` and `qemu-img`.
- Administrator PowerShell for Hyper-V lifecycle operations.


`lab-prereq.ps1` also validates the configured topology and the pinned cloud
image SHA-256.


## Reproducible image provenance


`config.json` contains both the Ubuntu cloud-image URL and the expected
SHA-256. `lab-up.ps1` verifies the downloaded/cached image against that
digest before using it.


The URL currently points at Ubuntu Noble's `current` image, but a new upstream
image is never silently accepted: a digest mismatch stops the lab until the
new image is explicitly reviewed and the configured SHA-256 is intentionally
updated.


The base VHDX also records its source-image digest. An existing base VHDX with
no trusted source digest is rejected rather than having provenance invented
after the fact.


## State and secrets


Generated private state is stored outside the repository:


```text
%LOCALAPPDATA%\hpc-client-gui-lab
```


This contains the generated SSH key, private `known_hosts`, VM disks/cloud
image, source-image provenance, and the emitted connection profile. Do not
sync or publish this directory.


Runtime evidence under `lab/evidence/` is local/disposable and ignored by Git
and the project FreeFileSync configuration.


SSH/SFTP automation uses a lab-private `known_hosts` file with
`StrictHostKeyChecking=accept-new`. First contact may be accepted into that
isolated file; a subsequent host-key change fails instead of being silently
accepted.


## Application profile


After a successful `lab-up.ps1`, the lab profile is written to:


```text
%LOCALAPPDATA%\hpc-client-gui-lab\hpc-client-profile.json
```


The generated profile uses the app's declarative provider/profile shape,
including a schema-v2 `local-real` provider template, `ssh-key`
authentication metadata, and Home/Scratch/Project storage definitions.


It does not alter a TRUBA production profile.


## Evidence levels


A healthy `lab-up.ps1` proves the core LOCAL_REAL infrastructure is running.
A successful `lab-test.ps1` must report:


```text
status: LOCAL_REAL_READY
failed_count: 0
```


That still does **not** make W22 PASS by itself. W22 additionally needs the
maintained GUI/runtime GJ-01/GJ-02 journey and exact packaged-artifact evidence
against this real target. See `W22_LOCAL_REAL_GAP_REPORT.md`.


## Deliberate future expansion


The current core lab does not yet claim:


- password-auth success/failure;
- keyboard-interactive/MFA;
- controlled first-contact reject and host-key rotation/mismatch journeys;
- bastion/jump-host topology;
- X11 forwarding;
- filesystem quota/over-quota;
- configurable network latency/packet loss;
- large/parallel/resumable transfer scenarios.


Those are separate expansion milestones and must not be fabricated into current
evidence.