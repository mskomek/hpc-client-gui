# LOCAL_REAL HPC Lab Protocol


This protocol applies to the HPC W01-W61 program only.


## Purpose


Use the maintainer-owned LOCAL_REAL Hyper-V cluster as the default real
authorized infrastructure for HPC Wave requirements that require generic real
SSH/SFTP/Slurm/filesystem/job/connection evidence and do not explicitly require
a named production/site-specific system.


`LOCAL_REAL_HYPERV` is real external infrastructure for acceptance purposes. It is not:
- a mock server;
- a fake scheduler;
- a substitute identity for TRUBA;
- evidence for a site-specific requirement that explicitly names another system.


## Canonical target


- profile: `C:\Users\mskomek\AppData\Local\hpc-client-gui-lab\hpc-client-profile.json`
- controller/login: `192.168.250.11:22`
- user: `hpctest`
- compute nodes: `compute01`, `compute02`
- infrastructure class: `LOCAL_REAL_HYPERV`
- provider/profile ID: `local-real`
- scheduler: real Slurm
- shared storage: real NFS-backed Home/Scratch/Project
- auth: generated SSH key from the emitted profile
- host-key policy: isolated lab known_hosts with `accept-new`; later key changes fail

## Capability-scoped password target

`LOCAL_REAL_HYPERV` is intentionally key-only (`ssh_pwauth: false`) and is
authoritative only for the capabilities it actually provisions. It must not
be used as password-auth evidence.

For generic password-auth requirements, the maintained secondary target is
`LOCAL_PASSWORD_REAL`: the disposable OpenSSH/Slurm fixture defined by
`docs/testing/LOCAL_HPC_LAB.md` and `devtools/lab/docker-compose.yml`. It is
bound to `127.0.0.1` only, uses a real containerized OpenSSH/Slurm runtime
(not an in-process mock), and uses documented throwaway fixture input supplied
through stdin or an equivalent secure input channel. It is authoritative only
for generic password success/failure and invalid-password rejection. It does
not replace `LOCAL_REAL_HYPERV` for key, host-key, Slurm, SFTP, storage, or
site-specific claims. Its password must never appear in logs, reports,
manifests, or evidence.


## Verified baseline


Current accepted LOCAL_REAL baseline:
- `lab-up.ps1`: PASS
- `lab-status.ps1`: PASS
- image pin: PASS
- generated profile validation: PASS
- `lab-test.ps1`: `LOCAL_REAL_READY`
- behavioral gates: 23/23 PASS
- real PTY evidence: `/dev/pts/0`
- controller and both compute transports/services: PASS
- compute nodes: Slurm `idle`
- real SSH key login: PASS
- host-key pins: PASS
- real SFTP download/upload/hash: PASS
- MUNGE: PASS
- two-node `srun`: PASS
- `sinfo/squeue/scontrol/sbatch/sacct/scancel`: PASS
- shared-home compute execution: PASS
- permission-denied negative path: PASS


Repository context:
- `lab/LAB_AUDIT_REPORT.md`
- `lab/README.md`
- Wave-specific LOCAL_REAL gap reports when present


Private runtime state/evidence remains local/disposable. Never copy private keys,
VM disks, generated secrets, or LOCAL_REAL private state into Wave reports,
Git, Drive evidence, or worktree overlays.


## Wave selection rule


For an HPC Wave whose required evidence includes `EXTERNAL`:


1. Read the Wave's owned requirement wording first.
2. If it requires generic real SSH/SFTP/Slurm/remote-files/jobs/storage/
   connection/session behavior and does not name a specific external site,
   use LOCAL_REAL by default.
3. If it explicitly requires TRUBA, another named site, special hardware, an
   authoritative production service, or a capability LOCAL_REAL does not
   implement, LOCAL_REAL cannot substitute for that requirement.
4. Do not declare HUMAN/EXTERNAL blocked merely because TRUBA is unavailable
   when the owned generic requirement can be truthfully satisfied by LOCAL_REAL.
5. Do not claim LOCAL_REAL proves GUI or PACKAGE evidence merely because the
   infrastructure itself is healthy. Run the required GUI/package journey
   against LOCAL_REAL.


## Use contract


Before external replay:
- prefer `lab-status.ps1` for a bounded health check;
- use the existing emitted profile rather than manually reconstructing secrets;
- do not rebuild/reset/recreate VMs, rotate keys, or change lab configuration
  unless a fresh demonstrated infrastructure defect requires repair;
- use `lab-test.ps1` when the Wave needs the lab behavioral baseline refreshed
  or when health/evidence has been invalidated.


For GUI claims:
- drive the maintained wx/runtime harness or exact required public GUI action;
- prove visible/semantic result, not controller-only state.


For PACKAGE claims:
- bind evidence to the exact packaged artifact path and SHA-256 under
  acceptance;
- source/runtime proof cannot replace package proof.


For EXTERNAL claims:
- bind evidence to the selected real target's environment identity,
  target/profile identity, current repository HEAD/worktree identity, and exact
  Wave requirement IDs;
- in-process mocks cannot replace real target evidence. `LOCAL_PASSWORD_REAL`
  is authoritative only for its declared generic password scope.


## Shared-state and parallelism


LOCAL_REAL is a shared mutable external resource.


Two Waves must not concurrently mutate or acceptance-test the same LOCAL_REAL
cluster/profile/session/job/filesystem namespace unless the Wave contracts and
test harnesses explicitly prove disjoint external resources.


For `/wave-a-end-l-p` and other program parallel modes:
- Git worktree isolation does not isolate LOCAL_REAL;
- serialize LOCAL_REAL EXTERNAL replay by default;
- PLAN and source-only work may still run in parallel;
- GUI/PACKAGE/EXTERNAL acceptance using LOCAL_REAL requires an exclusive
  LOCAL_REAL lease unless explicitly proven disjoint;
- after a fault-injection Wave, recover/reset only through the maintained lab
  lifecycle tooling before another Wave consumes the lab.


## Failure classification


A LOCAL_REAL health/configuration failure is infrastructure/orchestration until
diagnosed.


A product behavior failure observed against healthy LOCAL_REAL is a technical
Wave finding and must be routed to the true owner.


Unavailable site-specific authority that LOCAL_REAL cannot truthfully replace
may be HUMAN_DEFERRED/BLOCKED_ENV.


Never weaken the Wave requirement to make LOCAL_REAL sufficient.


## Closeout


A Wave using LOCAL_REAL may close only when:
- required LOCAL_REAL EXTERNAL evidence is current and truthful;
- any required GUI/PACKAGE evidence has been executed against the real target;
- exact artifact/final-SHA rules are satisfied where applicable;
- cleanup leaves the lab suitable for the next serialized consumer;
- fresh independent audit accepts the evidence.


LOCAL_REAL completion does not itself advance or close any Wave.
