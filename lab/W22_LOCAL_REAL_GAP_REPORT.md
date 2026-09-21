# W22 LOCAL_REAL gap report








This report is a capability map, not a Wave status change.








| W22 external requirement | Local lab capability | Remaining gap |
|---|---|---|
| GJ-01 infrastructure: fresh profile/auth/host-key/connect | Real OpenSSH key authentication against a separate Linux VM; automation uses a lab-private `known_hosts` file with `StrictHostKeyChecking=accept-new`, and later key changes fail | Maintained GUI first-contact accept/reject/mismatch flow and exact packaged-artifact replay |
| GJ-02 infrastructure: connected terminal -> disconnect/reconnect | Real `ssh -tt` PTY against the controller VM plus explicit SSH transport-loss/recovery injection | GUI-visible terminal I/O, disconnect/reconnect state, stale-session fencing and exact package evidence |
| Real SSH identity | `lab-status.ps1` records topology, Ubuntu/package/Slurm versions, source-image SHA-256 and base-VHDX source hash | Bind this environment identity to the W22 GUI/package replay |
| Real SFTP support | Windows `sftp` performs real download and upload/hash verification against the VM | Useful adjacent remote-files evidence; it is not a substitute for GJ-01/GJ-02 GUI proof |
| Slurm commands | Controller and two compute VMs run real Slurm; tests cover `sinfo`, `squeue`, `srun`, `sbatch`, `sacct`, `scontrol`, and `scancel` | GUI Jobs journey belongs to its owning Wave; W22 may reuse only relevant connection/session evidence |
| Transport loss / reconnect | `lab-fault.ps1 -Action ssh-loss|reconnect` stops the listener, kills the active hpctest SSH session, verifies the port/session loss, and provides recovery | GUI-visible callback/state-transition evidence |
| Node drain/down / daemon loss | `slurm-loss`, `drain`, and `down` actions | Bind any reused evidence to the owning requirement IDs; no automatic PASS claim |
| Shared filesystem | NFS-backed `/home`, `/scratch`, `/project`, plus write/read/delete and permission-denied fixtures | GUI files/editor journey belongs to its owning Wave |








## Current LOCAL_REAL status


LOCAL_REAL is complete.


- `lab-up.ps1`: PASS;
- `lab-status.ps1`: PASS;
- pinned image provenance: PASS;
- generated LOCAL_REAL profile validation: PASS;
- `lab-test.ps1`: `LOCAL_REAL_READY`;
- required behavioral gates: 23;
- failed gates: 0;
- direct PTY: `/dev/pts/0`;
- real SSH/SFTP/MUNGE/Slurm/shared-storage/cancel/negative-permission paths: PASS.


The remaining W22 gap is entirely above the infrastructure layer: maintained GUI GJ-01/GJ-02 replay plus exact packaged-artifact evidence.








A successful lab run may supply W22's real-system `EXTERNAL` infrastructure
class because it uses separately running Linux VMs and real OpenSSH/SFTP/Slurm
daemons under the maintainer's control. It does not by itself prove W22's GUI
or PACKAGE claims, and it must not be represented as TRUBA/site-specific
evidence. `GJ-01` and `GJ-02` remain open until the maintained GUI harness
runs against the emitted profile and the exact packaged artifact is hashed.
No Wave status is modified here.