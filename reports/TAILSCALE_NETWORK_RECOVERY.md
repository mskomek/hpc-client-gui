# Tailscale Network Recovery

Date: 2026-10-23

## Result

Status: **BLOCKED_EXTERNAL** for Tailscale-to-Hyper-V/HPC guest access. The current developer machine `MSKomeK` is the Hyper-V host and is itself a Tailscale node, correcting the earlier assumption that `DESKTOP-TMGUAH7` was the only Hyper-V-capable machine. The guests are not Tailscale nodes, and this host advertises no guest subnet route.

## Live topology evidence

The host reports `MSKomeK` and owns a Tailscale address. `tailscale status` lists `DESKTOP-TMGUAH7` as its only other peer. The host's `AllowedIPs` contain only its own `/32` and `/128`; there is no advertised route for the Hyper-V internal networks.

`Get-VM` reported `Windows11`, `Ubuntu-Test`, `login-control01`, `compute01`, and `compute02` Running. `Get-VMSwitch` reported internal switches `hpc-lab`, `Ubuntu-SSH`, `Default Switch`, and `FSE Switch`. Ubuntu-Test has adapters on `Default Switch` and `Ubuntu-SSH`.

Ubuntu-Test's canonical status/doctor checks passed. Its SSH alias resolves to `192.168.77.10`, uses account `test`, identity `~/.ssh/ubuntu_test_ed25519`, and `StrictHostKeyChecking yes`. A read-only probe returned `test-Virtual-Machine`, account `test`, `eth1=192.168.77.10/24`, and `eth0=172.20.213.133/20`. `tailscaled` is inactive and no guest `tailscale` executable is installed. The Windows11 guest runner verified the active `test\\home` account; the guest has neither the `tailscale` command nor a Tailscale service.

These observations establish the existing developer-host-to-lab path over the dedicated Hyper-V SSH network. They do not establish Tailscale-to-guest access. Existing SSH host-key checking was retained; no credential or key material was read or copied into the report.

## Tailscale health

The host Tailscale service is Running and UDP connectivity is available. The current `tailscale netcheck` also reports an intercepted DERP TLS connection with a self-signed `ZyXELcert` certificate and a WinHTTP control-plane proxy lookup error (`#12167/0x2f87`). `tailscale status` does not show any of the Hyper-V guests as peers. The local Tailscale node remains reachable as a node, but no guest route exists through it.

## Findings by layer

| Layer | Result |
|---|---|
| Developer PC to Hyper-V guest over existing lab path | PASS: Ubuntu-Test doctor and strict-key SSH probe |
| Developer PC's Tailscale membership | PASS: service running, host Tailscale address assigned |
| Tailscale to DESKTOP-TMGUAH7 | Peer is listed; route health is degraded by router certificate interception |
| Tailscale to Windows11 guest | BLOCKED_EXTERNAL: no guest Tailscale identity or route |
| Tailscale to Ubuntu-Test | BLOCKED_EXTERNAL: `tailscaled` inactive; no route advertised |
| Tailscale to login-control01 / compute01 / compute02 | BLOCKED_EXTERNAL: guests absent from tailnet; no guest subnet route |
| Live SFTP / Slurm evidence | Existing PASS remains tied to the direct lab route; no Tailscale re-acceptance is claimed |

## Owner prerequisite

The tailnet/Hyper-V owner must select an authorized path: join only the approved guests to the tailnet, or approve a narrowly scoped subnet router for the required guest addresses and ports. The router's DERP/control-plane TLS interception also needs owner-side diagnosis. No ACL, route advertisement, firewall rule, guest identity, or security policy was changed during this continuation.

After the approved route is available, verify the guest-specific Tailscale address or advertised route, SSH port 22, and host key. Then rerun the live SFTP matrix and Slurm test-only workflow over that exact path. Until then, F02/F03 Tailscale acceptance remains blocked and cannot be promoted to PASS.

Evidence: `.tmp` command logs and canonical runner output from the current Windows host. Historical SFTP 19/19 and Slurm `sbatch --test-only` results are retained in `reports/LIVE_SFTP_ACCEPTANCE.md` and `reports/LIVE_SLURM_DRAFT_ACCEPTANCE.md`; they are not Tailscale-route evidence.
