# Automatic update support

The updater selects an artifact from verified installation evidence, operating
system, and architecture. Automatic installation requires Ed25519-signed
metadata verified by a public key embedded in the application. The metadata
binds product, version, channel, platform, architecture, filename, type, exact
size, SHA-256, and an allowlisted HTTPS GitHub Releases URL. Adjacent SHA-256
files remain for manual verification but are not an update trust root.

Signing-key rotation requires an application release containing the new public
key. Release publication fails if the repository signing secret is unavailable.

| Installation | Update behavior |
| --- | --- |
| Windows portable x86_64 | Self-update. The independent WinForms updater extracts and copies with real byte progress, health-checks, restarts, and rolls back. |
| macOS `.app` bundle (arm64 / x86_64) | Conditional self-update. Signed/notarized, architecture-correct DMGs can replace a writable bundle after `codesign` and Gatekeeper checks. Other locations/builds stay manual. |
| Linux AppImage x86_64 | Self-update for a verified user-writable `APPIMAGE` target, with byte progress, atomic replacement, health check, and rollback. |
| Debian / Ubuntu `.deb` amd64 | APT-managed. The verified package is passed to `pkexec apt install`; APT owns authentication and installed files. |
| Flatpak | Flatpak-managed. The verified release bundle is passed to Flatpak using the detected user/system scope; host handoff failure falls back safely. |
| Source / pip | Manual update. Source trees are never overwritten. |
| Unknown installation | Unsupported; no installation target is guessed. |

Download cancellation removes the partial `.part` file and leaves the running
application untouched. Installation progress is numeric only for measurable
self-update work; APT and Flatpak transactions remain indeterminate. Destructive
installation cannot be cancelled from the updater UI.
