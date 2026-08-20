# Security Model

> Türkçe: [[Security-Model-TR]]

## Scope

This is a **client-side** application. It opens sessions to clusters you
already have accounts on, transfers your files, and runs scheduler commands on
your behalf. It does not modify remote HPC infrastructure, does not install
anything on the cluster, and has no server component of its own.

Your cluster's own policies — authentication requirements, allocation limits,
whether X11 forwarding is permitted — remain in force and are not something the
application can or does relax.

## Credentials

- Passwords and tokens are **never written to command history** and are
  **never shown in the interface**.
- Secrets are **never logged**. Commands may appear in the log; the credentials
  used to run them do not.
- A profile password, if you choose to save one, is stored protected rather
  than in plain text. On Windows this uses the operating system's own data
  protection facility; a master-password path derives a key with PBKDF2 and
  encrypts the secret with Fernet, using a per-secret salt.
- `config.json`, which holds that material, is deliberately excluded from
  diagnostic bundles. See [[Data and Privacy|Data-and-Privacy]].

For automation, prefer key-based authentication. When a password is
unavoidable, feed it through `--password-stdin` rather than a command-line
argument or an environment variable — see
[[Scripting Examples|Scripting-Examples]].

## Host keys

Two policies are supported:

| Policy | Unknown host key | Changed host key |
|---|---|---|
| `accept-new` | Prompts you to trust and save, trust once, or cancel | Always rejected |
| `strict` | Rejected | Always rejected |

Keys you trust and save are written to `~/.truba_slurm_gui/known_hosts`. The
`--strict-host-key` option forces the strict policy for a single invocation,
which is the right choice for unattended automation.

A **changed** host key is always rejected, under either policy. That is the
case worth taking seriously: it means the key presented by the host no longer
matches the one you trusted. Verify the new fingerprint through a channel other
than the connection itself before doing anything about it. Deleting the entry
from `known_hosts` to make the error go away defeats the check.

## External command-line access

Remote CLI access is **off by default**. "Allow external CLI access to remote
commands" in Settings controls it. When enabled, any local process that runs
this application's command-line interface can reach remote commands — files,
jobs, edit, shell, and diagnostics — using your saved profiles, with no GUI
session and no further prompt.

Enable it deliberately, on machines where you trust the local processes. See
[[Settings Reference|Settings-Reference]] and [[CLI Guide|CLI-Guide]].

## Destructive operations

Operations that destroy data or change cluster state require explicit
confirmation. On the command line that is `--yes` on `files rm`,
`jobs submit`, `jobs cancel`, and `profile delete`; without it the command
refuses and exits `2`. The graphical interface asks in a dialog.

## Optional helpers

The Windows X11 path uses `plink.exe` and VcXsrv, neither of which is bundled.
They are downloaded only after you approve the download, or you can install
them yourself. X11 helper processes are cleaned up when the application exits,
and orphaned processes are handled defensively rather than left running. See
[[X11 Forwarding|X11-Forwarding]].

## Reporting a vulnerability

Use GitHub's **Private Vulnerability Reporting** on the repository's Security
tab — not a public issue, discussion, pull request, or post. Include the
affected version and operating system, a concise impact description,
reproduction steps using mock or disposable data, and relevant logs with
credentials, tokens, hosts, and personal data removed.

Do not attach real cluster credentials. Only the latest published release
receives security fixes; upgrade before reporting. The full policy is
`SECURITY.md` in the repository.

## See also

[[Data and Privacy|Data-and-Privacy]] · [[Connecting and Profiles|Connecting-and-Profiles]] · [[Settings Reference|Settings-Reference]]
