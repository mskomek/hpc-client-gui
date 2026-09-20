# W22 LOCAL_REAL gap report

This report is a capability map, not a Wave status change.

| W22 external requirement | Local lab capability | Remaining gap |
|---|---|---|
| Real SSH authentication and host-key flow | `lab-test.ps1` uses real OpenSSH and a generated key | GUI/runtime capture and exact packaged artifact |
| Real PTY shell / GJ-02 | `lab-test.ps1` requests `ssh -tt`; `LOCAL_REAL` profile is emitted | GUI terminal input/output, reconnect, stale-session and package evidence |
| Real SFTP / GJ-01 | Windows `sftp` copies from the VM | GUI profile creation, host-key UI, browse evidence, package evidence |
| Slurm commands | Controller and two compute VMs run Slurm; test captures `sinfo`, `squeue`, `sbatch`, `sacct`, `scontrol` | GUI Jobs journey and exact packaged artifact |
| Transport loss / reconnect | `lab-fault.ps1 -Action ssh-loss|reconnect` | GUI-visible state transition and callback evidence |
| Node drain/down / daemon loss | `slurm-loss`, `drain`, and `down` actions | Bind replay evidence to W22 IDs; no automatic PASS claim |
| Shared filesystem | NFS-backed `/home`, `/scratch`, `/project` | GUI file/editor journey and package evidence |

The lab can supply the W22 `EXTERNAL` class after a successful run. It cannot
supply W22's required `GUI` or `PACKAGE` classes. `GJ-01` and `GJ-02` remain
open until the maintained GUI harness runs against the emitted profile and the
exact packaged artifact is hashed. No Wave status is modified here.
