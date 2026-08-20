# FAQ

> Türkçe: [[FAQ-TR]]

## Do I need Python?

Not for the packaged builds. The Windows portable ZIP and the Linux AppImage
and `.deb` bundle everything they need. Python 3.10+ is required only when you
run from source.

## Is this an official tool from my cluster or my institution?

No. It is an independent, provider-neutral community project. It is not
affiliated with any cluster operator or vendor, and it works with any
Slurm-based system you already have access to.

## Does it change anything on the cluster?

Only what you ask it to: your files, and the jobs you submit or cancel. It is
client-side and does not modify HPC infrastructure, install anything on the
cluster, or alter site configuration.

## Which clusters does it work with?

Any system where SSH access is available, Slurm commands exist (`sbatch`,
`squeue`, `sacct`, …), and — only if you need remote graphical applications —
X11 forwarding is permitted. See
[[Compatibility and Support Matrix|Compatibility-and-Support-Matrix]].

## Why is the data directory called `.truba_slurm_gui`?

It is a legacy name kept so existing installations keep working after the
project was renamed. Renaming it would strand everyone's saved profiles and
trusted host keys, so it stays.

## Where is the log?

`~/.truba_slurm_gui/app.log`, rotating. See
[[Logs and Diagnostics|Logs-and-Diagnostics]].

## Do I need X11?

Only for remote graphical applications such as MATLAB or ParaView. Terminal
workloads — Python scripts, batch solvers, training jobs — do not need it.

## Why does X11 work differently on Windows and Linux?

They use genuinely different mechanisms. Windows runs `plink.exe -X` with
VcXsrv as the X server; Linux uses the system OpenSSH client (`ssh -X/-Y`).
Neither Windows helper is used on Linux. See
[[X11 Forwarding|X11-Forwarding]].

## Are my passwords safe?

They are never written to command history and never shown in the interface,
and secrets are never logged. A saved profile password is stored protected
rather than in plain text. For automation, prefer keys. See
[[Security Model|Security-Model]].

## Why does the command line say remote access is disabled?

"Allow external CLI access to remote commands" is off by default. Enable it in
Settings if you want to script against the cluster. See
[[CLI Guide|CLI-Guide]].

## Why did my delete or submit command exit with code 2?

It needed `--yes`. Commands that destroy data or change cluster state refuse to
run without explicit confirmation. See [[CLI Guide|CLI-Guide]].

## Can I resume an interrupted transfer?

Yes — `--if-exists resume` on the command line, or the resume choice in the
conflict dialog. See [[File Transfers|File-Transfers]].

## Is it safe to attach my log to a public issue?

Export the diagnostic bundle rather than the raw log: the bundle is redacted
and excludes your saved profiles. Then read it before attaching — redaction is
best-effort and cannot know about identifiers it never saw. See
[[Data and Privacy|Data-and-Privacy]].

## Can I use it at work?

Non-commercial use is covered by the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate license. See
[[Licensing and Commercial Use|Licensing-and-Commercial-Use]].

## How do I change the interface language?

Turkish and English are both built in and switchable in the application. See
[[Interface Language and i18n|Interface-Language-and-i18n]].

## How do I report a bug or ask for a feature?

Through GitHub issues. For anything with security impact, use the private
reporting channel instead. See
[[Support and Donations|Support-and-Donations]] and
[[Security Model|Security-Model]].
