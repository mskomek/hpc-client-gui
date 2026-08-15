# Troubleshooting

> Türkçe: [[Troubleshooting-TR]]

Organized by what you observe. In every case, `~/.truba_slurm_gui/app.log` has
the detail — see [[Logs and Diagnostics|Logs-and-Diagnostics]].

## The application will not start

**On Linux, it exits with an error mentioning the `xcb` platform plugin.**
Qt's platform libraries are missing. Install them:

```bash
sudo apt install libegl1
```

Fedora and openSUSE ship equivalents under their own names. See
[[Installation on Linux|Installation-Linux]].

**On Windows, nothing happens when you double-click the executable.** Make sure
you extracted the ZIP rather than running from inside the ZIP viewer, and check
whether antivirus or an application-control policy blocked it. See
[[Installation on Windows|Installation-Windows]].

**It started once and now fails after an upgrade or downgrade.** An older build
may not understand configuration written by a newer one. Move
`~/.truba_slurm_gui/config.json` aside and let the application recreate it —
you will need to re-enter your profiles.

## Connection fails

Start with the diagnostics, which separate local problems from remote ones:

```bash
hpc-client-gui doctor environment
hpc-client-gui --profile mycluster doctor connection
```

**Exit code 3.** The session could not be opened or authenticated. Check the
hostname, port, username, and whether your key path is correct. A profile name
that does not exist also produces exit `3` when it is requested for a
connection.

**Exit code 124.** The operation timed out. Raise `--timeout`, and check
whether you can reach the host at all from this network — a VPN requirement is
a common cause.

**Authentication fails with a key that works elsewhere.** Confirm the key path
in the profile points at the private key, and that the cluster has the matching
public key. Some sites require the key to be registered separately.

## An unknown or changed host key

**Unknown key.** Under the `accept-new` policy you are asked to trust and save,
trust once, or cancel. Trusting saves the key to
`~/.truba_slurm_gui/known_hosts`. Under `strict` the connection is rejected
instead.

**Changed key.** This is always rejected, under either policy. Do not delete
the `known_hosts` entry to silence it and do not switch to a laxer policy as a
workaround — both remove the only check you have. Verify the new fingerprint
with your cluster's administrators through a channel other than the connection
itself, then update the entry once you know the change is legitimate.

## A command-line command refuses to run

**"Remote CLI access is disabled."** The external-access gate is off. Enable
"Allow external CLI access to remote commands" in Settings. See
[[CLI Overview|CLI-Overview]].

**Exit code 2 on a delete, submit, or cancel.** The command requires explicit
confirmation. Add `--yes`. See [[CLI Exit Codes|CLI-Exit-Codes]].

## Transfers

**A large transfer was interrupted.** Restart it with `--if-exists resume`, or
choose resume in the conflict dialog. See [[File Transfers|File-Transfers]].

**You want certainty that a file arrived intact.** Use `--verify`, which checks
SHA-256 after the transfer, or compare `files checksum` against a local hash.

## Slurm output looks wrong or empty

Slurm output parsing varies with site customization, and login banners or
warnings mixed into command output can degrade it. The application is written
to fail softly and log the details rather than guess. Compare against the raw
command:

```bash
hpc-client-gui --profile mycluster sh -- squeue -u $USER
```

If the raw output looks right but the parsed view does not, the log entry for
that operation is what to attach to an issue.

## X11 applications do not appear

**On Windows.** Start VcXsrv before launching the remote application, and
confirm `plink.exe` is available. Both are optional helpers and neither is
bundled in the executable.

**On Linux.** X11 uses the system OpenSSH client. Confirm it is installed and
that `DISPLAY` is set in your session. The Windows plink/VcXsrv path does not
apply here.

**Everything connects but the window is slow.** X11 responsiveness depends
heavily on network quality; there is no client-side setting that compensates
for a high-latency link. See [[X11 Forwarding|X11-Forwarding]].

## Still stuck

Export a diagnostic bundle, read it, and attach it to an issue. For anything
with security impact use the private reporting channel instead. See
[[Crash Reports and Send Logs|Crash-Reports-and-Send-Logs]] and
[[Security Model|Security-Model]].
