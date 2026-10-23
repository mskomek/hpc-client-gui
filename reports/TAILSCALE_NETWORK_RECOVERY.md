# Tailscale Network Recovery

Date: 2026-10-23

## Result

Status: BLOCKED_EXTERNAL for remote Hyper-V guest access.

The remote Windows workstation DESKTOP-TMGUAH7 is online in Tailscale. Its Tailscale service is running, and its status query reported Online=true. The configured OpenSSH alias codex-remote authenticated with the already provisioned key and returned the expected hostname and account. The private key and tailnet addresses are intentionally excluded from this report.

The development workstation does not have the tailscale command available in PATH. The remote workstation is reachable over the existing SSH path. The active RustDesk session reports a relayed, encrypted TCP connection; this is a separate transport from the SSH/Tailscale path.

## Hyper-V and lab reachability

The remote workstation is not the Hyper-V host: the Hyper-V PowerShell module is absent, the vmms service is not installed, and Get-VM is unavailable there. Consequently it cannot enumerate or control Windows11, Ubuntu-Test, login-control01, compute01, or compute02.

Those guests were reachable from the development host through its existing lab/Hyper-V path. That path does not establish Tailscale-to-guest reachability from DESKTOP-TMGUAH7. Live SFTP and Slurm checks below used the development-host-to-lab path, not a subnet route through the RustDesk workstation.

No subnet route, ACL, firewall rule, guest Tailscale identity, or route advertisement was changed. Strict SSH host-key checking remained enabled.

## Findings by layer

| Layer | Result |
|---|---|
| Remote workstation Tailscale service | PASS: running; status online |
| Existing SSH access to remote workstation | PASS: key-authenticated |
| Remote workstation is Hyper-V host | FAIL: Hyper-V components absent |
| Development host Tailscale CLI | BLOCKED_ENV: command unavailable |
| Remote workstation to HPC guest network | BLOCKED_EXTERNAL: no verified guest route |
| login-control01 from existing lab path | PASS: current-source SFTP acceptance completed |
| compute01/compute02 scheduler relationship | PASS for scheduler-side test-only evidence; no SSH route from Tailscale was proven |

The earlier Windows11, Ubuntu-Test, login-control01, compute01, and compute02 observations are tied to the local lab host path and must not be represented as remote Tailscale VM acceptance.

## Required owner action

The tailnet or Hyper-V owner must choose an approved path: make the necessary guest an authorized tailnet member, or configure a narrowly scoped subnet router with approved routes and ACLs. After approval, verify guest routes and port 22 from the remote workstation, then repeat SSH host-key verification and live SFTP/Slurm checks over that exact route. No network policy changes were made here.

Evidence: current session probes via codex-remote; live SFTP and Slurm evidence snapshots in the handoff package.
