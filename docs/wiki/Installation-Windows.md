# Installation on Windows

> Türkçe: [[Installation-Windows-TR]]

The recommended Windows install is the **portable ZIP**. Python is not required.

## Install

1. Open the
   [releases page](https://github.com/mskomek/hpc-client-gui/releases) and
   download the Windows ZIP for version 1.5.9.
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

The local X server is optional and **not bundled in the EXE**:

- **VcXsrv** — the X server that displays remote applications.

The active Paramiko SSH terminal provides forwarding; Plink is not required.
When started by the application, VcXsrv uses a loopback listener and MIT
cookie authentication. Details: [[X11 Forwarding|X11-Forwarding]].

## Institutional environments

Firewall and antivirus policies may block the executable, the helper downloads,
or outbound SSH. In managed environments you may need approval from your IT
department before the application can connect.

## Command-line interface

The portable package exposes the same command-line interface as the source
install. See [[CLI Guide|CLI-Guide]].

## Next steps

[[Quick Start|Quick-Start]] · [[Upgrading and uninstalling|Upgrading-and-Uninstalling]] · [[Troubleshooting|Troubleshooting]]
