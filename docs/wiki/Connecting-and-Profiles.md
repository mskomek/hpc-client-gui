# Connecting and Profiles

> Türkçe: [[Connecting-and-Profiles-TR]]

## The connection form

| Field | Notes |
|---|---|
| **Host / IP** | The cluster login node |
| **Port** | The SSH port |
| **Username (optional)** | Your cluster account |
| **Password (optional)** | Leave empty when using a key |
| **SSH key file (opt.)** | Path to your private key; **Browse** opens a file picker |
| **Enable X11 forwarding (for GUI apps)** | Only needed for remote graphical applications |
| **Strict host key checking** | Rejects unknown host keys instead of prompting |
| **Remember password** | Stores the password protected, not in plain text |
| **Save profile** | Keeps the connection for reuse |
| **Simulation / Dry-run (UI test without a remote system)** | Explores the interface with no cluster at all |

**Connect** starts the session; the status line moves through *Connecting…* to
*Connected*, or reports *Mock mode (simulation)* in dry-run. **Disconnect**
ends it. The **Console** panel shows connection and SSH messages as they
happen — it is the first place to look when a connection does not come up.

## Saving a profile

**Add Connection** opens the dialog; **Save** stores the profile and
**Save & Connect** stores it and connects immediately. **Edit** changes an
existing profile. If a profile has a saved password, editing it requires
entering that password first — a failed verification leaves the profile
untouched.

Additional per-profile options:

- **Do not ask for the password again when connecting.**
- **Allow this connection to be used from the CLI** — a per-profile
  counterpart to the global external-access gate.
- **Remember the encryption password for this Windows account.**
- **Profile transfer parallelism** — overrides the global parallel transfer
  count for this connection.
- **SSH timeout (0 = default).**

If a password cannot be protected for your account, the application says so
rather than silently storing it unprotected.

## System presets

A profile also carries the cluster-specific commands and paths the application
uses, so sites with non-standard tooling work without code changes:

| Field | Purpose |
|---|---|
| **System name** | A label for the preset |
| **Home directory**, **Job / scratch directory** | Default paths the file manager opens at |
| **List jobs command** | Normally `squeue` |
| **Submit job command** | Normally `sbatch` |
| **Cancel job command** | Normally `scancel` |
| **Accounting command** | Normally `sacct` |
| **Job details command** | Normally `scontrol` |
| **Custom status command**, **Active job IDs command**, **Completed job state command** | Site-specific overrides |

**System Defaults** restores the standard set. Presets can be saved as
templates (**Add as template**) and reused; both system presets and your own
user templates appear in the preset menu.

## Verifying the host

On first connection to an unknown host you are asked to verify the server
identity, with three choices: **Trust and save**, **Trust once**, or cancel.
Trusting and saving writes the key to `~/.truba_slurm_gui/known_hosts`.

With **Strict host key checking** on, an unknown key is rejected outright
instead of prompting. A *changed* key is always rejected under either setting.
See [[Security Model|Security-Model]].

## If the session drops

The application notices a dropped session, reports the reason, and offers to
reconnect — press `r` or answer Yes at the prompt. The command placeholder
changes to remind you the session is disconnected.

## From the command line

```bash
hpc-client-gui profile list
hpc-client-gui profile show mycluster
hpc-client-gui profile create mycluster --host login.example.org --user me --key ~/.ssh/id_ed25519
hpc-client-gui profile test mycluster
```

`profile create` and `profile update` accept non-sensitive fields only, so no
password ever appears on a command line. `profile delete` requires `--yes`.
See [[CLI Command Reference|CLI-Command-Reference]].

## See also

[[Quick Start|Quick-Start]] ·
[[Settings Reference|Settings-Reference]] ·
[[Troubleshooting|Troubleshooting]]
