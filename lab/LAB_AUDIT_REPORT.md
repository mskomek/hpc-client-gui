# LOCAL_REAL Lab Audit Report
















Audit date: 2026-09-20
Scope: Drive `Projeler/hpc-client-gui/lab`, provisioning scripts, generated profile contract, evidence semantics, and the project's FreeFileSync exclusions.
















Decision: **LOCAL_REAL_COMPLETE**
















The real Hyper-V/SSH/Slurm/NFS/MariaDB infrastructure has passed runtime health. The final pinned-image/provider-profile replay also passed: `image_pin_ok=true`, `profile_valid=true`, and the emitted profile SHA-256 was recorded. The behavioral replay remained `LOCAL_REAL_READY` with all 23 required gates passing. The LOCAL_REAL milestone is complete.
















## Runtime replay history


### Replay 8 — final profile/health replay
- `lab-up.ps1`: PASS.
- Prerequisite/config checks: PASS, including configured image digest and topology.
- `lab-status.ps1`: PASS.
- `image_pin_ok`: true.
- Expected image SHA-256 equals actual image SHA-256 and base-VHDX source SHA-256.
- `profile_valid`: true.
- Generated profile SHA-256: `a99c96fdff52105b6f539fa0335a4b34a7b6ad00ceaacdf628fd09b320b4c0bf`.
- Controller and both compute-node transports/services: PASS.
- Slurm nodes: `compute01=idle`, `compute02=idle`.
- Final `lab-test.ps1`: `LOCAL_REAL_READY`.
- Required behavioral gates: 23.
- Failed behavioral gates: 0.
- LOCAL_REAL milestone is complete.
- This remains laboratory evidence only and does not by itself make W22 PASS.






### Replay 7 — LOCAL_REAL_READY
- Behavioral replay result: `LOCAL_REAL_READY`.
- Required gates: 23.
- Failed gates: 0.
- Direct PTY evidence: `/dev/pts/0`, user `hpctest`, host `login-control01`.
- Host-key pins: PASS on controller and both compute nodes.
- SSH key login: PASS on all three nodes.
- Canonical storage paths and UID/GID identity: PASS.
- SFTP download and upload/hash verification: PASS.
- MUNGE: PASS.
- Two-node `srun`: PASS.
- `sinfo`, `squeue`, `scontrol`, `sbatch`, `sacct`: PASS.
- Shared-home compute execution on both nodes: PASS.
- Permission-denied negative path: PASS.
- Submit/cancel and observed `CANCELLED` state: PASS.
- Behavioral LOCAL_REAL milestone is complete.
- This is laboratory evidence only; it is not W22 PASS.












### Replay 6 — direct PTY evidence fix
- Behavioral replay again passed every gate except `ssh_pty`.
- Observed output from the encoded-script helper was `hpctest / login-control01 / pty=no`, while all SSH/SFTP/Slurm/storage gates passed.
- Conclusion: the arbitrary-command bridge is unsuitable as PTY evidence because it changes file-descriptor topology.
- Fix: `lab-test.ps1` now performs a separate direct OpenSSH probe using `ssh -tt` with `tty && id -un && hostname`.
- PASS requires a real terminal device such as `/dev/pts/0`, the expected user, the expected controller hostname, and SSH exit code 0.
- No infrastructure reset or reprovision is required for this fix.
























### Replay 1
- Prerequisites: PASS.
- Blocker: `Set-VMMemory -DynamicMemoryEnabled` received a string instead of a Boolean.
- Resolution: corrected to the real PowerShell Boolean `$false`.
















### Replay 2
- Prerequisites: PASS.
- Controller reached package installation, NFS, MUNGE, MariaDB and slurmdbd.
- Blocker: Slurm accounting pre-check failed to recognize the already-existing
  `local` account association and retried `sacctmgr add account`.
- Resolution: association checks now parse fields and use verified postconditions.
















### Replay 3
- Prerequisites: PASS.
- Controller and both compute-node SSH transports: PASS.
- Required services: PASS.
- Slurm: `compute01` and `compute02` both `idle`.
- Environment identity: Ubuntu 24.04.5 LTS, Slurm 23.11.4, OpenSSH 9.6p1,
  MUNGE 0.5.15, MariaDB 10.11.14.
- Source-image SHA-256 matched base-VHDX provenance:
  `612b2c0cc1bc413a6cb8c38fd611794caf0f2b436c50013d8b3794db12ad7354`.
- Result: core runtime infrastructure PASS.
















### Replay 4
- Behavioral operations ran through the final verdict stage.
- Blocker: generic result introspection attempted to index `exit_code` on a
  heterogeneous/null result and raised `Cannot index into a null array`.
- Resolution: verdict now consists only of explicitly named required gates and
  records required/failed counts and names.
















### Replay 5 — recorded pre-fix evidence
The generated `LOCAL_REAL_TEST.json` reached all substantive real operations.
















Passed:
- SSH key login on all three VMs;
- host-key pinning;
- canonical storage paths;
- identical hpctest/slurm UID/GID identity;
- Home/Scratch/Project write-read-delete round trips;
- SFTP download;
- SFTP upload plus SHA-256 content match;
- MUNGE round trip;
- two-node `srun`;
- Slurm node discovery;
- `squeue`, `scontrol`, `sbatch`, `sacct`;
- shared-home compute execution on both nodes;
- permission-denied negative path;
- job submit/cancel and observed CANCELLED state.
















Only failed gate:
- `ssh_pty`: the script checked `[ -t 0 ]`.
- Root cause: `Invoke-LabSshCapture` decodes and pipes the command into
  `bash -s`, so stdin is intentionally a pipe even after SSH `-tt`.
- Fix: PTY evidence now checks stdout with `[ -t 1 ]`.
















Result: **22/23 recorded gates PASS; fresh post-fix replay pending.**
















## Per-file audit
















| File | Audit state | Important findings / changes |
|---|---|---|
| `config.json` | PASS after changes | Cloud image SHA-256 is now pinned. |
| `lab-common.ps1` | PASS static | Private state outside repo; isolated known_hosts; public key can be re-derived from private key and is validated. |
| `lab-prereq.ps1` | PASS static | Checks Hyper-V/OpenSSH/WSL tooling plus configured image digest and topology shape. |
| `lab-up.ps1` | PASS static, fresh runtime replay required | Boolean bug fixed; image digest enforced; base provenance cannot be fabricated; VM/network provisioning remains idempotent; generated LOCAL_REAL profile upgraded to provider schema v2 shape. |
| `provision/controller.sh` | PASS static + prior runtime | Real MUNGE/Slurm/slurmdbd/MariaDB/NFS; random DB secret; idempotent accounting associations; shared-home bind verification. |
| `provision/compute.sh` | PASS static + prior runtime | UID/GID alignment; real NFS; expected NFS source is now verified; shared-home bind identity verified. |
| `lab-status.ps1` | PASS static, fresh runtime replay required | Separates transport/service health; validates pinned image, base provenance, emitted profile and provider-template basics; records environment identity. |
| `lab-test.ps1` | PASS static, fresh runtime replay required | Explicit behavioral gates; stale SFTP state removed; safe failure defaults; host-key pins checked for all nodes; PTY probe fixed to fd1. |
| `lab-fault.ps1` | PASS static | Real SSH transport loss; slurmd loss; drain/down; reconnect defaults to the most recently faulted node. |
| `lab-reset.ps1` | PASS static | Cancels only hpctest jobs; removes test artifacts; resumes only nodes actually in recoverable bad states. |
| `lab-down.ps1` | PASS static | Attempts graceful shutdown and hard-powers off only after timeout. |
| `README.md` | PASS after changes | Updated to match image pinning, profile generation, evidence levels and lifecycle. |
| `W22_LOCAL_REAL_GAP_REPORT.md` | PASS | Keeps LOCAL_REAL infrastructure distinct from required GUI/PACKAGE proof. |
| `.gitignore` / FreeFileSync | PASS | Generated state/evidence/images/backups excluded from source/sync. |
















## Reproducibility and provenance
















The lab image is pinned to:
















`612b2c0cc1bc413a6cb8c38fd611794caf0f2b436c50013d8b3794db12ad7354`
















`lab-up.ps1` now:
1. validates that the configured SHA-256 is syntactically valid;
2. hashes the cached/downloaded image;
3. rejects a mismatch;
4. compares the base VHDX source hash case-insensitively;
5. refuses to invent a missing source-provenance file for an existing base VHDX.
















The configured URL may remain Ubuntu Noble `current`, but a future upstream
image cannot silently replace the reviewed base because the pinned digest
stops provisioning until deliberately updated.
















## Provider/profile contract
















The emitted LOCAL_REAL profile now carries:
- target host/port/user/key;
- `accept-new` host-key policy;
- no stored password;
- provider template `schema_version: 2`;
- stable `profile_id: local-real`;
- scheduler `slurm`;
- structured access host object;
- declarative `ssh-key` auth metadata;
- Home/Scratch/Project storage rows with required labels, kinds and shared
  access context;
- no quota source until a real quota implementation exists.
















`lab-status.ps1` verifies the emitted profile before considering environment
identity healthy.
















## Security and sync hygiene
















Generated private state lives under:
















`%LOCALAPPDATA%\hpc-client-gui-lab`
















Drive copies of the previously synced private key, public key, cloud image,
base VHDX and backups were removed. FreeFileSync now excludes generated
`lab/state`, `lab/evidence`, `.pytest-tmp`, VM/image files and backups.
















An empty legacy Drive folder may remain because the available Drive deletion
action cannot delete folders; it contains no secret/runtime files.
















## Current gate


LOCAL_REAL is complete.


Final verified state:


```text
lab-up      PASS
lab-status  PASS
image pin   PASS
profile     PASS
lab-test    LOCAL_REAL_READY
gates       23/23 PASS
```


The next gate is no longer infrastructure. W22 now needs the maintained GUI GJ-01/GJ-02 journeys and exact packaged-artifact evidence against this LOCAL_REAL target.
















## Future full-feature lab backlog
















Not yet claimed:
- password authentication success/failure;
- keyboard-interactive/MFA;
- first-contact reject plus controlled host-key rotation/mismatch;
- jump/bastion host;
- X11 forwarding;
- filesystem quota/over-quota;
- configurable network latency/packet loss;
- large/parallel/resumable transfers.