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

- **When X11 is enabled, check/start required tools** — on Connect, installed
  helpers are checked and started. Missing tools open their official download
  page; executables are not downloaded or run automatically.
- **Close VcXsrv when the app exits** — if the application started VcXsrv, it
  is closed by PID.
- **Close X11/SSH processes on exit** — application-started X11 helpers are
  closed; the interactive SSH relay channels close with the terminal.

## Windows: Paramiko + VcXsrv

The active Paramiko SSH terminal requests X11 forwarding before it opens the
remote PTY and shell. **VcXsrv** is the local X server that renders remote
windows. Plink and a second SSH process are not used.

VcXsrv is not bundled; install it from its official source. When the app starts
VcXsrv, it supplies a private MIT-MAGIC-COOKIE authority file and never uses
`-ac`. If VcXsrv binds to all interfaces, the app accepts it only when its own
process, authority file, exact executable firewall rules, active firewall
profiles, and inbound-block defaults are verified. Otherwise it refuses that
server. An unrelated wildcard listener is never accepted.

The profile's existing SSH key, agent, password, and host-key policy remain in
effect. No password or cookie is written to the application log. If a local
server or MIT cookie is unavailable, the app refuses the X11 request and keeps
the selected X11 shell is refused; the app does not silently open an unforwarded
shell. With X11 disabled, normal SSH remains available. The remote server must permit X11 forwarding and have
`xauth` installed; its `sshd` assigns `DISPLAY` (usually `localhost:10.0`) after
the request succeeds.

Only commands typed into the interactive SSH terminal are forwarded. Remote
`exec_command` calls and batch jobs do not inherit this display.

## Linux and macOS: local desktop X server

The active Paramiko terminal uses the local desktop X server. Linux desktops
may provide Xorg or Xwayland; macOS requires XQuartz. The process must inherit a
valid `DISPLAY` and access to its MIT cookie through `XAUTHORITY` or `xauth`.
System OpenSSH is not required for this integrated forwarding path.

## Authentication and trust

By default the app asks the local X server for an **untrusted** cookie through
the X11 SECURITY extension. If the extension is unavailable, forwarding fails
closed. The profile has a separate **Use trusted X11** option for servers that
need trusted forwarding; it warns that the remote program can control the local
display. The SSH channel's random cookie is replaced only after the setup packet
matches. MIT cookie authentication proves identity; it does not provide the
isolation that an untrusted SECURITY cookie provides. Do not use `xhost +` or
unauthenticated X server modes.

## Support summary

| Scenario | Status | Notes |
|---|---|---|
| Windows, Paramiko + VcXsrv | Supported | Authenticated server; wildcard bind requires verified firewall isolation |
| Linux/macOS desktop X server | Supported | Requires `DISPLAY`, `xauth`, and SECURITY support unless trusted mode is chosen |
| SSH server without X11 forwarding | Unsupported | Selected X11 shell fails closed; X11-off SSH is unaffected |

## Performance

X11 responsiveness depends heavily on network quality. On a high-latency link a
remote graphical application will feel slow, and no client-side setting
compensates for that. For long interactive sessions, ask whether your site
offers a remote-desktop or web-based alternative.

## Cleanup

X11 relay channels close with the interactive SSH session. If the application
started VcXsrv, the existing Settings option controls whether that process is
closed when the app exits.

## See also

[[Terminal and Remote Commands|Terminal-and-Remote-Commands]] · [[Settings Reference|Settings-Reference]] · [[Troubleshooting|Troubleshooting]]
