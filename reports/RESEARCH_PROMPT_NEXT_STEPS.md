# Research Prompt — Remaining ANSYS Journal Studio Acceptance

You are researching the remaining external and product acceptance work for ANSYS Journal Studio as of 2026-10-23. Start from the handoff ZIP's reports and evidence; do not repeat completed work unless evidence has expired or the tested source revision differs.

## Goal

Produce a source-backed, actionable plan to close the BLOCKED_EXTERNAL / PARTIAL items without weakening tailnet security, changing production data, or treating historical tests as current evidence.

## Known state

- App feature branch: codex/ansys-journal-studio-host-integration; source commit 1cec0471e3daf50a16ba4161282aff2260ba9dd9.
- Plugin feature branch: codex/ansys-journal-studio-plugin; code commit 744d1bb556660576eb2597fe0b593ef2acc7e83b.
- Remote Windows workstation DESKTOP-TMGUAH7 is online in Tailscale and accepts the configured strict-key SSH connection, but it is not the Hyper-V host: vmms and the Hyper-V PowerShell module are absent.
- The development host reaches the lab guests through its existing lab path. Current live SFTP and Slurm tests used that path, not a Tailscale route from DESKTOP-TMGUAH7.
- SFTP: current-source live integration passed 19/19 on login-control01.
- Slurm 23.11.4: isolated one-node draft passed sbatch --test-only; no job was submitted.
- Current per-user Windows installer installed and uninstalled on Windows11; the current per-machine installer was not guest-tested. Both current acceptance installers are unsigned.
- Current-source OS-level drag/drop and cross-session persistence are not verified. The broad pytest run also encountered a wx native access violation.
- 42 first-party over-limit allowlist entries remain; 12 conflict with the separately dirty codex/log-repeat-groups checkout and must not be edited until safely integrated.
- Historical Fluent startup/TUI acceptance did not load a case or mesh. A current RustDesk attempt did not produce a Fluent process. No solver job was started.
- The overall verdict is BLOCKED_EXTERNAL.

## Research questions

1. Which least-privilege topology can route from the remote Tailscale workstation to the existing Hyper-V guest network: direct guest Tailscale membership, a dedicated/narrowly scoped subnet router, or another already-supported route? Compare operational ownership, ACL boundaries, route advertisement and approval requirements, host/guest forwarding, firewall scope, DNS, and rollback. Do not prescribe globally broad routes or ACL changes.
2. What exact read-only probes should distinguish DNS, route, firewall, guest service, SSH host-key, SFTP subsystem, and Slurm failures? Preserve strict host-key validation.
3. Which current-source tests should be repeated over that route, and what evidence binds each result to the commit, host path, and artifact? Include SFTP 19-check matrix and Slurm read-only plus test-only behavior without submitting a real job.
4. Define a minimal Windows11 GUI acceptance script for real Explorer drag/drop, Command Library/Visual Flow drag/drop, unsaved-document handling, and fresh-process panel/layout persistence. Identify reliable evidence capture and cleanup.
5. Define safe remaining installer coverage: current per-machine install/uninstall, app launch, plugin lifecycle, repair/reinstall, upgrade/downgrade, rollback, and data preservation. Explain signing prerequisites and keep unsigned acceptance separate from production release acceptance.
6. Define an isolated security test matrix for archive traversal, absolute paths, symlink/junction escapes, manifest/hash/domain failures, oversized archives/resource limits, interruption, rollback, permissions, logging, and open-editor lifecycle.
7. Recommend the next 500-line refactors from the 30 non-conflicting entries and a safe integration sequence for the 12 conflicted files. Preserve current behavior and do not add allowlist exceptions.
8. State whether Fluent case solve is actually in the minimum product acceptance scope. If it is, list the exact owner-provided prerequisites and approval needed before any licensed compute is launched.

## Output requirements

Return a prioritized plan with: finding, source and date, confidence, decision/owner required, exact commands or GUI steps, expected evidence, rollback/cleanup, and pass criteria. Prefer official Tailscale, Microsoft Hyper-V, OpenSSH, Slurm, and Inno Setup documentation or other primary sources. Clearly label source-backed facts versus inferences. Do not include private keys, passwords, raw tailnet addresses, or user secrets. Do not change networking or start licensed/paid compute during research.
