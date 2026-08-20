# Glossary

> Türkçe: [[Glossary-TR]]

**AppImage** — a single-file Linux application format that runs without
installation. See [[Installation on Linux|Installation-Linux]].

**Accounting** — Slurm's record of finished jobs, queried with `sacct`. Useful
for what a job actually used, as opposed to what it requested.

**AppRun** — the launcher script inside an AppImage. Validated during the Linux
build.

**Conflict resolution** — what happens when a transfer's destination already
exists: overwrite, skip, rename, or resume. See
[[File Transfers|File-Transfers]].

**`--yes`** — the explicit confirmation required by commands that destroy data
or change cluster state. Without it they exit `2`.

**Diagnostic bundle** — the redacted ZIP produced by the send-logs dialog,
suitable for attaching to a bug report. See
[[Crash Reports and Send Logs|Crash-Reports-and-Send-Logs]].

**Exit code** — the numeric status a command-line invocation ends with.
Contractual; branch on it rather than on message text. See
[[CLI Guide|CLI-Guide]].

**Host key** — the cryptographic identity a remote host presents. Trusting one
saves it to `~/.truba_slurm_gui/known_hosts`. A *changed* host key is always
rejected. See [[Security Model|Security-Model]].

**i18n** — internationalization. This project ships Turkish and English, and
both are updated together. See
[[Interface Language and i18n|Interface-Language-and-i18n]].

**Job ID** — the identifier Slurm assigns at submission, used by
`jobs status`, `jobs cancel`, `scontrol`, and `scancel`.

**`known_hosts`** — the file of host keys you have chosen to trust.

**Module** — an environment module on the cluster (`module avail`,
`module load`). Names differ by site, which is why templates leave them
commented out.

**MPI** — the message-passing interface used by multi-node parallel jobs. See
[[Job Script Templates|Job-Script-Templates]].

**Partition** — a Slurm queue. Names are site-specific; the bundled templates'
partition names are examples.

**plink** — PuTTY's command-line client. Used on Windows for X11
(`plink.exe -X`). Not bundled. See [[X11 Forwarding|X11-Forwarding]].

**Profile** — a saved connection: host, port, username, key path, and host-key
policy. See [[Connecting and Profiles|Connecting-and-Profiles]].

**QOS** — quality of service, a Slurm policy object that can cap time, CPU,
memory, or GPU use per account.

**Redaction** — replacing your local and remote usernames and saved hostnames
with `<user>` and `<host>` before a log leaves the machine. Best-effort. See
[[Data and Privacy|Data-and-Privacy]].

**Resume** — continuing an interrupted transfer instead of restarting it,
backed by the transfer journal.

**Scratch** — fast cluster storage for large data and running jobs, usually
subject to periodic cleanup. Keep results you care about in home or project
storage.

**SFTP** — the file transport used by default; `--transport` also accepts
`ftp`.

**SHA-256** — the checksum used by `--verify` on transfers and by the `.sha256`
files published beside each release artifact.

**Slurm** — the cluster workload manager this application drives: `sbatch`,
`squeue`, `sacct`, `scancel`, `sinfo`, `scontrol`.

**Smoke test** — a minimal end-to-end check. `doctor smoke` round-trips a file
over the transport; the release workflow smoke-tests the packaged artifacts.

**VcXsrv** — the X server used on Windows to display remote graphical
applications. Not bundled.

**X11** — the protocol that displays a remote graphical application on your
local screen. Needed only for graphical programs, never for batch jobs.

## See also

[[FAQ|FAQ]] · [[Slurm Help Library|Slurm-Help-Library]] · [[Architecture|Architecture]]
