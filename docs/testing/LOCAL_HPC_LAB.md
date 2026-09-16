# Local HPC Lab — real SSH / SFTP / Slurm target

A disposable single-node cluster you run on your own machine. It exists so the
integration Waves can be proven against a **genuine** SSH server, a **genuine**
SFTP subsystem and a **genuine** Slurm controller — submitting, tracking and
cancelling real jobs — instead of mocks.

> **Scope of truth.** This lab proves *real-system* behaviour, not *site*
> behaviour. Evidence taken here must be recorded with
> `remote environment class: local containerized single-node Slurm`. It does
> not substitute for acceptance against a production site when a Wave asks for
> one, and it does not prove packaged-artifact behaviour.

---

## 1. What's inside

| Component | Detail |
|---|---|
| Base | `debian:trixie-slim` (Debian 13.6) |
| SSH | OpenSSH server, password auth enabled, `internal-sftp` subsystem |
| Scheduler | Slurm 24.11 (`slurmctld` + `slurmd`), partitions `debug` (default) and `short` |
| Accounting | `slurmdbd` + MariaDB, so **`sacct` answers for finished jobs** |
| Auth | `munge` |
| Cgroups | **disabled** (`CgroupPlugin=disabled`); no systemd/dbus in the container |
| Node | `hpclab`, hardware auto-detected from the container, `State=UNKNOWN` → resumed at boot |
| Paths | `/home/hpctest`, plus `/arf/home/hpctest` and `/arf/scratch/hpctest` so a TRUBA-shaped cluster profile resolves unchanged |
| Locales | `en_US.UTF-8` and `tr_TR.UTF-8` generated, `AcceptEnv LANG LC_*` |

Accounting matters: the client looks a job's **final** state up with `sacct`
once it disappears from `squeue`. Without `slurmdbd` that path cannot be
exercised, so it is part of the lab rather than an optional extra.

---

## 2. Credentials — test-only, on purpose

| Field | Value |
|---|---|
| Host | `127.0.0.1` |
| Port | `2222` |
| User | `hpctest` |
| Password | `hpctest` |

These are **fixed, public, throwaway fixture credentials**. They are safe only
because the port is published on `127.0.0.1` and nowhere else.

- Never reuse this password anywhere.
- Never republish the port on `0.0.0.0` or a LAN address.
- Never point this profile at a real cluster.
- The container has no data worth protecting; `down -v` destroys it.

Key auth also works — drop a public key into the container's
`/home/hpctest/.ssh/authorized_keys` and connect with `--key`.

---

## 3. Lifecycle

```bash
docker compose -f devtools/lab/docker-compose.yml up -d --build
```

Wait for health (first boot initialises MariaDB, so allow ~40 s):

```bash
docker inspect -f '{{.State.Health.Status}}' hpclab
```

Check the cluster:

```bash
docker exec hpclab sinfo
docker exec hpclab scontrol ping
```

Tear down, destroying all state:

```bash
docker compose -f devtools/lab/docker-compose.yml down -v
```

Logs when something looks wrong:

```bash
docker logs hpclab | tail -40
docker exec hpclab tail -40 /var/log/slurm/slurmctld.log
```

---

## 4. Point the client at it

Create a profile once (no secret is stored on the command line — the client
prompts, or reads the password from stdin):

```bash
hpc-gui profile create lab --host 127.0.0.1 --port 2222 --user hpctest --host-key-policy accept-new
```

Or pass overrides per command:

```bash
hpc-gui --host 127.0.0.1 --port 2222 --user hpctest --password-stdin doctor connection --format json
```

### Connection diagnostics

```bash
hpc-gui --profile lab doctor connection --format json
```

### Real SFTP round trip (upload → list → download → SHA256 → cleanup)

```bash
hpc-gui --profile lab doctor smoke --format json --artifact artifacts/lab/sftp-smoke.json
```

Emits schema `sftp-smoke/1`. Add `--keep` to leave the remote temp directory in
place when you need to inspect it; otherwise it is removed automatically.

### Jobs

```bash
hpc-gui --profile lab jobs list --format json
hpc-gui --profile lab jobs submit <script>
hpc-gui --profile lab jobs cancel <job-id>
```

---

## 5. Useful fixture jobs

Short job that finishes on its own (job-completion and `sacct` lookup):

```bash
docker exec -u hpctest hpclab bash -lc \
  'cd ~ && printf "#!/bin/bash\n#SBATCH -J lab-short\n#SBATCH -t 00:01:00\nsleep 5; echo done > ~/lab-short.out\n" > short.slurm && sbatch short.slurm'
```

Long job that must be cancelled (cancellation and terminal-state checks):

```bash
docker exec -u hpctest hpclab bash -lc \
  'cd ~ && printf "#!/bin/bash\n#SBATCH -J lab-long\n#SBATCH -t 00:30:00\nsleep 1800\n" > long.slurm && sbatch long.slurm'
```

Job that fails (non-zero exit mapping):

```bash
docker exec -u hpctest hpclab bash -lc \
  'cd ~ && printf "#!/bin/bash\n#SBATCH -J lab-fail\nexit 3\n" > fail.slurm && sbatch fail.slurm'
```

Watch a job through its whole life:

```bash
docker exec hpclab squeue
docker exec hpclab scontrol show job <id>
docker exec hpclab sacct -n -X -j <id> -o State -P      # after it leaves squeue
```

---

## 6. Failure injection

The lab is the only place these can be exercised safely.

| Scenario | How |
|---|---|
| Unreachable host | `docker compose ... stop` while the client is connected |
| Disconnect mid-operation | `docker exec hpclab pkill -f "sshd.*hpctest"` |
| Auth failure | connect with a wrong password |
| Host-key mismatch | `down -v` then `up` (fresh host keys) against a stored `known_hosts` |
| Permission denied | `docker exec hpclab chmod 000 /home/hpctest/locked` |
| Missing remote path | target a path you never created |
| Scheduler down | `docker exec hpclab pkill slurmctld` |
| Node drained | `docker exec hpclab scontrol update NodeName=hpclab State=DRAIN Reason=test` |

Undo a drain with `State=RESUME`.

---

## 7. Evidence rules

Every record taken against this lab must carry:

```text
main SHA
plugin SHA
client OS / build mode
provider ID
remote environment class: local containerized single-node Slurm
auth method (secret omitted)
timestamp + timezone
action
observed result
cleanup result
```

Redact nothing that isn't a secret, and record no secret at all — the fixture
password is documented here precisely so it never has to appear in an evidence
file.

Reset between evidence runs when a clean slate matters:

```bash
docker compose -f devtools/lab/docker-compose.yml down -v && \
docker compose -f devtools/lab/docker-compose.yml up -d
```

---

## 8. Verified on first build

Recorded against main `1e8b76eb`, client Windows 11 / source runtime,
remote environment class `local containerized single-node Slurm`,
auth `password (fixture)`, 2026-09-16:

| Check | Command | Result |
|---|---|---|
| Cluster up | `sinfo` | `debug*` and `short` both `idle hpclab` |
| Connection diagnostics | `hpc-gui --format json … doctor connection` | dns / port / auth / sftp / slurm / checksum all **PASS** |
| SFTP round trip | `hpc-gui --format json … doctor smoke --artifact …` | temp_dir / upload / list / download / checksum / cleanup all **PASS**, exit 0, `artifacts/lab/sftp-smoke.json` |
| Job lifecycle | `sbatch` → `squeue` → `sacct` | `PENDING` → ran → `COMPLETED`, output marker written |
| Job visible to client | `hpc-gui … jobs list` | running job listed with id, partition, state |
| Cancel | `hpc-gui … jobs cancel <id> --yes` | `OK`, then `sacct` reports `CANCELLED` |

## 9. Limits

- Single node — no multi-node, topology, GPU or MPI behaviour.
- `task/none` and `proctrack/linuxproc`: no cgroup enforcement, so memory and
  CPU limits are **not** enforced the way a real site enforces them.
- No site modules, no `lssrv`, no project/quota accounting beyond what
  `slurmdbd` records.
- Loopback networking — latency, MTU and firewall behaviour are unrealistic.
- Fixture credentials: never a model for how a user should store real ones.
