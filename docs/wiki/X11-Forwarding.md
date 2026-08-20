# X11 Forwarding

> Türkçe: [[X11-Forwarding-TR]]

X11 forwarding displays a remote **graphical** application — MATLAB, ParaView,
and the like — on your local screen. It is **not** needed for batch jobs,
terminal workloads, file transfers, or job management, and it costs nothing to
leave off.

X11 runs in the background. There is no dedicated X11 tab: you enable it on the
connection and launch graphical applications as commands.

## Enabling it

**Enable X11 forwarding (for GUI apps)** on the connection form. Three related
options live in Settings, under Connection and X11:

- **When X11 is enabled, check/download/start required tools** — on Connect,
  the required helpers are checked and, if missing, downloaded with your
  consent and started.
- **Close VcXsrv when the app exits** — if the application started VcXsrv, it
  is closed by PID.
- **Close X11/SSH processes on exit** — the plink/ssh processes the application
  started are terminated.

## Windows: plink + VcXsrv

On Windows the path is `plink.exe -X` together with **VcXsrv** as the X server
listening on `127.0.0.1:6000`.

**Neither is bundled in the executable.** When one is missing you are asked
before anything is downloaded — the prompt names the file and its size — and
you can install them yourself instead. If no stable checksum or signature is
available for an installer, the application says so and asks again before
running it; declining rejects the unverified installer rather than proceeding
quietly.

Common failures are reported specifically: `plink.exe` could not be prepared,
VcXsrv could not be started (a firewall or permissions issue), VcXsrv started
but exited immediately, or VcXsrv appears to be running but port 6000 never
opened.

Start VcXsrv before launching a remote graphical application. When a session
starts, the launched command is echoed and the window opens separately.

## Linux: system OpenSSH

On Linux, X11 forwarding uses the **system OpenSSH client** with `-X` or `-Y`.
It does **not** use the Windows plink/VcXsrv path, and nothing is downloaded.

Requirements: the OpenSSH client installed, an X server already running (your
desktop session), and `DISPLAY` set in the environment.

The launch is deliberately non-interactive: forwarding failures are made
explicit rather than silently continuing without X11, and host-key checking
follows the profile's policy — `strict` maps to strict checking, otherwise
`accept-new`. Password authentication is not attempted on this path, because
the prompt would appear on a hidden console and hang; **use a key on Linux**.

## Which flag: `-X` or `-Y`

`-Y` is trusted forwarding and `-X` is untrusted. Untrusted forwarding is more
restrictive and some applications will not run under it; trusted forwarding
gives the remote application more access to your local X server. The connection
carries this choice.

## Support summary

| Scenario | Status | Notes |
|---|---|---|
| Windows, plink + VcXsrv | Recommended | Most reliable on Windows |
| Any platform, OpenSSH with a key | Supported | `ssh -X/-Y` |
| OpenSSH with a password | Limited | Hidden prompts can block; plink preferred on Windows, a key preferred on Linux |

## Performance

X11 responsiveness depends heavily on network quality. On a high-latency link a
remote graphical application will feel slow, and no client-side setting
compensates for that. For long interactive sessions, ask whether your site
offers a remote-desktop or web-based alternative.

## Cleanup

Helper processes are cleaned up when the application exits, and orphaned
processes are handled defensively. The two Settings options above control
whether VcXsrv and the X11/SSH processes are closed with the application.

## See also

[[Terminal and Remote Commands|Terminal-and-Remote-Commands]] · [[Settings Reference|Settings-Reference]] · [[Troubleshooting|Troubleshooting]]
