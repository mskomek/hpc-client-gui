# Automatic update support

The updater selects an artifact from verified installation evidence, operating
system, and architecture. Every downloaded package is checked against its
published SHA-256 file before installation is offered.

| Installation | Update behavior |
| --- | --- |
| Windows portable x86_64 | Fully automatic. An independent WinForms updater waits for the application, extracts and copies with real byte progress, keeps backups, checks the restarted process, and rolls back on failure. |
| macOS `.app` bundle (arm64 / x86_64) | Manual DMG handoff. The correct architecture is selected; bundle replacement remains manual so signing, notarization, Gatekeeper, and non-writable application locations are not bypassed. |
| Linux AppImage x86_64 | Manual installation. The AppImage artifact and checksum are selected correctly, but no independent GUI runtime is currently shipped for safe automatic replacement. |
| Debian / Ubuntu `.deb` amd64 | Package-manager-managed installation. The `.deb` artifact is selected from `dpkg-query` ownership evidence; administrator authentication and installation remain delegated to the system. |
| Flatpak | Flatpak-managed update. Application files are never replaced directly. |
| Source / pip | Manual update. Source trees are never overwritten. |
| Unknown installation | Unsupported; no installation target is guessed. |

Download cancellation removes the partial `.part` file and leaves the running
application untouched. Once Windows replacement begins, cancellation is
disabled because interrupting file replacement cannot be made safely.
