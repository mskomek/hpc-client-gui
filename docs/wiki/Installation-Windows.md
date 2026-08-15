# Installation on Windows

> Türkçe: [[Installation-Windows-TR]]

The recommended Windows install is the **portable ZIP**. Python is not required.

## Install

1. Open the
   [releases page](https://github.com/mskomek/hpc-client-gui/releases) and
   download the Windows ZIP for version 1.2.6.
2. Right-click the ZIP and choose **Extract All**. Extract to a folder you can
   write to, such as a folder under your user profile.
3. Run `hpc-client-gui.exe` from the extracted folder.

Running the application directly from inside the ZIP viewer does not work
reliably — extract first.

## First run

On first launch, create a connection profile with your cluster hostname and
username, then connect. See [[Connecting and Profiles|Connecting-and-Profiles]].

Application data — configuration, the rotating log, and saved host keys — is
written to `~/.truba_slurm_gui` (that is,
`C:\Users\<you>\.truba_slurm_gui`). The directory name is legacy and is
retained for compatibility with existing installations.

## Optional X11 helpers

X11 forwarding is only needed for remote **graphical** applications. It is not
needed for terminal workloads, file transfers, or Slurm job management.

Two external components are involved on Windows, and **neither is bundled in
the EXE**:

- `plink.exe` from PuTTY — the application runs `plink.exe -X` for X11 sessions.
- **VcXsrv** — the X server that displays the remote application.

When you enable X11, the application asks for approval before downloading these
helpers; you may also install them yourself. Start VcXsrv before launching a
remote graphical application. Details: [[X11 Forwarding|X11-Forwarding]].

## Institutional environments

Firewall and antivirus policies may block the executable, the helper downloads,
or outbound SSH. In managed environments you may need approval from your IT
department before the application can connect.

## Command-line interface

The portable package exposes the same command-line interface as the source
install. See [[CLI Guide|CLI-Guide]].

## Next steps

[[Quick Start|Quick-Start]] · [[Upgrading and uninstalling|Upgrading-and-Uninstalling]] · [[Troubleshooting|Troubleshooting]]
