# Changelog

## Unreleased

## v1.5.7

### Cross-platform updater architecture
- Download progress now shows the real package percentage and transferred/total size; downloads without a known total remain indeterminate and show only downloaded bytes.
- Added an independent Windows WinForms installation splash with real byte-based extraction/copy progress, relative file status, monotonic phases, timestamped logs, startup health checking, and rollback.
- Made installation strategies and Linux/macOS architecture-specific artifact selection explicit; package-owned, source, and unknown installations retain safe documented fallbacks instead of guessed writes.
- Added installation-context, artifact-selection, PowerShell parser, progress, rollback, cancellation, and splash-lifecycle regression coverage.

## v1.5.6

### Update experience
- Replaced the generic update progress dialog with a dedicated application-update splash that remains responsive while checking, downloading, verifying, and starting installation.
- Download progress shows transferred and total package sizes alongside the progress bar; downloads without a known total remain visibly active.
- Ensured the installation splash is painted before the external updater starts, preventing it from being skipped during the handoff.
- Kept update checking, download, and checksum verification off the Qt GUI thread, with cancellation and partial-file cleanup preserved.

### Startup splash
- Removed translation-key leakage such as `splash.title` by making startup and updater splash copy self-contained English text.
- Added regression coverage for splash copy and byte-level updater progress reporting.

### Transfer dialog reliability
- Prevented stalled transfer workers from signaling deleted dialogs or panels during shutdown.

## v1.5.5

### Runtime and compatibility
- Moved the application and release toolchain to Python 3.14 as the single supported Python generation.
- Added installation-aware update handoff so packaged Windows builds can download, verify, and safely launch their replacement workflow while source and unsupported installations remain manual-only.

### Structured provider profiles and storage
- Preserved cluster-profile v2 data, provider overrides, provenance, unknown future fields, scheduler paths, and structured storage metadata across connection-profile edits.
- Added provider storage-area cards and editors for paths, retention, cleanup, backup, source URLs, and scheduler work-directory classification.
- Added English and Turkish provider-authoring guides and TRUBA profile-v2 contract coverage.

### Quota safety foundations
- Added explicit opt-in quota metadata and a shared, side-effect-free eligibility gate; incomplete, unsupported, or unapproved quota sources never trigger remote work.
- Persisted quota consent and scope metadata, validated storage-policy values, and exposed configuration status without claiming that a live quota backend or dashboard exists.

### Slurm path reliability
- Preferred scheduler-reported job paths when previewing and opening scripts.
- Preserved array-job paths, spaces, and scheduler working directories without requiring quota access.

### Release and repository reliability
- Unified release version declarations, aligned the application with the released plugin contract, and restored performance and packaging checks.
- Hardened unsigned macOS publication so it runs only after the final release gate succeeds; retained architecture-specific compatibility and bundle diagnostics.
- Restored ignore safeguards for credentials, virtual environments, build products, coverage, IDE state, local agent files, and generated development artifacts.
- Repaired merged CI compatibility issues and missing upload translations, leaving all required platform, GUI, CLI, plugin, packaging, audit, and documentation checks green.


## v1.5.4

### Demo and developer experience
- Added a 49-second English-captioned offline demo covering connection profiles, remote file management, parallel transfers, Slurm jobs and output, Plugin Manager, and ANSYS journal lint.
- Added a reproducible `python scripts/create_demo_gif.py` generator using disposable mock data.
- Localized startup splash status messages in English and Turkish.

## v1.5.3

### Local plugin checks
- Added a splash-sized update status window with live download and verification progress.
- Grouped local file plugin actions under an `Eklentiler` / `Plugins` submenu.
- Enabled ANSYS Journal lint for installed declarative lint packs, including multi-file `.jou` checks.

## v1.5.2

### macOS and release reliability
- Restored macOS x86_64 compatibility by selecting a supported `cryptography` version for Intel Macs.
- Fixed the final release gate so x86_64 job results are evaluated under their complete job IDs.
- Kept macOS release artifacts unsigned when the unsigned publication mode is selected, with checksums and clear Gatekeeper guidance.

## v1.5.1

### CI and developer workflow
- Unified local and GitHub Actions validation behind `scripts/ci.py`, added deterministic development dependencies and commit/push hooks, and kept the `%65` coverage gate after all GUI suites are combined.
- Fixed plugin version activation/rollback test coverage, isolated installed-plugin fixtures, and corrected the GUI transfer candidate helper used by context menus.

### Structured provider profiles
- Cluster-profile payload v2 now round-trips through the loader and connection
  dialog while legacy v1 profiles remain supported.
- Provider storage areas can be added, edited, removed, and annotated with
  backup, cleanup, retention, and HTTPS source metadata.
- Optional quota settings are explicit and off by default; the shared gate
  rejects incomplete or unsupported sources without starting remote work.

### Release integrity
- Repaired the release dependency graph: publication now runs only after a final release gate that requires the Linux, Windows, both macOS builds, the selected macOS verification path, and — in signed mode — both signing/notarization jobs plus signed-candidate verification. A failed, cancelled, or unexpectedly skipped required job can no longer race ahead of publication.
- Replaced the ambiguous `publish` + `sign` input combination with explicit `publish` (boolean, default `false`) and `macos_mode` (`signed` default / `unsigned`) inputs; a normal dry run never publishes, unsigned publication is an explicit choice, and an unsigned release can never claim signing.
- Release preflight now executes the same shared test suite as CI (`scripts/release_test_suite.py`) instead of `unittest discover`, so a red suite blocks releases exactly like it blocks PRs.

### macOS
- macOS packaging excludes QtWebEngine DevTools resources (matching Windows/Linux), records a sorted largest-files bundle report per architecture, and enforces an evidence-based compressed-DMG size budget (600 MiB by default, overridable via `HPC_GUI_DMG_BUDGET_MIB`).
- Every publication emits `RELEASE_SECURITY.json` stating the macOS mode, source commit, Developer ID/notarization/stapling/Gatekeeper outcomes, and artifact architectures; release notes are generated from the changelog and carry a prominent warning for unsigned builds.
- The in-app updater shows an explicit unsigned-build (or unknown-status) warning before pointing macOS users at a DMG; missing metadata is displayed as unknown, never as signed.

### Documentation and policy
- Honest Gatekeeper guidance in English/Turkish installation, verification, quick-start, and release-process docs: try opening normally, then Finder right-click → Open or System Settings → Privacy & Security → Open Anyway; never disable Gatekeeper globally.
- All GitHub Actions across every workflow are pinned to verified full commit SHAs with version comments; an automated scanner fails any floating action reference.
- Artifact-size reporting moved after all platform artifacts are downloaded, so summaries include both DMGs and the true total.

### Repository
- Branch protection on `main` enforces pull requests and required checks for everyone including the repository owner (no direct admin pushes).
- The plugin registry gains a blocking consumer-contract CI job against application v1.5.0, and registry tag `v1.0.0` received its formal GitHub Release object.

## v1.5.0

### Plugin API v2 and the ANSYS Script & Journal Linter
- Added Plugin API v2 as a strictly additive extension of v1: one new capability, `linter-tool`, lets the official registry ship hash-verified, pure-Python linter engines inside the existing manifest/installer verification chain. Nothing executes at install time; engines load lazily only when the user opens the tool, wrapped in defensive error handling.
- Added an "Open tool" action on installed plugin cards for linter-tool plugins, hosting the engine-provided page in a dialog.
- The official registry now publishes `org.hpcclient.ansyslint` 0.1.0 (ANSYS Script & Journal Linter), an unofficial offline linter for Ansys journals/scripts across Fluent, MAPDL, Workbench (including nested `SendCommand` payloads), CCL products, ICEM replays, System Coupling and more. It requires app >= 1.5.0.
- Note for users on releases <= 1.4.x: once the registry carries a Plugin API v2 entry, those clients report the official registry as unavailable until upgraded.
- Plugin Manager now shows the "Linter tool" capability badge; Turkish and English resources updated.

### Plugin Manager
- Installed plugins with more than one version now offer **Activate / Roll back**: installed versions are listed in PEP 440 order (1.10 > 1.9), the truly active version is shown as the headline version, and switching requires explicit confirmation. Activation runs off the GUI thread, keeps every installed version (nothing is deleted), leaves enabled/disabled state untouched, and restores the previous active version automatically when validation fails.
- Installed plugin versions are re-validated locally on load and activation: the manifest is compared against the SHA-256 trusted at install time, every declared payload file is checked for size and hash, and undeclared extra files inside the immutable version directory are rejected. A broken plugin is skipped with an actionable reinstall message; healthy plugins keep loading and nothing is ever deleted automatically.
- Existing installs are migrated once via trust-on-first-use verification: files are verified against their current manifest, and only then is that hash recorded atomically as the initial trust anchor (`installed.json` schema 2). This migration cannot prove the files were unchanged between installation and migration.

### Repository and CI
- PR-based contribution model documented for `main` (short-lived feature branches, deleted after merge); stale references to removed internal instruction files cleaned up.
- CI workflows gain branch/PR-scoped concurrency cancellation; all GitHub Actions are pinned to verified full commit SHAs; release builds report artifact sizes.
- macOS releases can be published unsigned when Apple signing credentials are unavailable; Gatekeeper approval is required on first launch.

## v1.4.2

### macOS release support
- Added native Apple Silicon and Intel macOS DMG packaging, signed-release gates, and architecture-aware update assets.
- Added macOS Keychain storage, XQuartz preflight checks, and documented terminal/X11 limitations.
- Release diagnostics now use the HPC naming convention and update cancellation preserves downloaded candidates.
- Updated the release workflow cache action to the supported v4.2.3 implementation.

## v1.4.1

### Plugin Manager
- The Plugin Manager now loads the registry automatically when first opened (Loading → Online/Cached/Offline states); Refresh is disabled while a request is in flight and re-enabled afterwards, and closing the dialog mid-load stays safe.
- Discover cards show translated capability badges, compatibility with the running app, and installed/disabled/incompatible/update-available state; Details adds license range, source (*Official plugin registry*), installed state, and older versions.
- Added **Request a plugin** (Turkish: *Eklenti iste*) which opens the dedicated issue form in the official plugin repository; the destination URL is fixed and allow-listed.
- Successful installs/updates now show a completion summary with counts of added cluster profiles, job templates, and lint rule packs (from loader data).
- Opening the Plugin Manager can no longer fail silently: failures are logged with an error id and surfaced to the user.

### Transfers
- Migrated the legacy global transfer-parallelism setting: profiles saved before v1.4.0 now inherit the old global value once (clamped to 1–10); profile-specific values always win and later launches never rewrite them.
- Plain FTP transfers now run over isolated per-transfer connections, so FTP supports parallel file transfer safely; a single large file is still never segmented.
- The transfer dialog shows configured versus effective parallelism and explains when the effective limit is reduced to one.

### Packaging and CI
- Declared `packaging>=23` as a runtime dependency (used by the plugin stack) and fixed the wheel asset declarations (SVG/terminal HTML-JS-CSS assets were missing due to an `*.seg` typo); new packaging test builds and inspects the wheel.
- New module-specific coverage floors plus a 65% global coverage gate in CI; release workflow third-party actions are pinned to full commit SHAs.
- The cross-repository Plugin API contract suite is pinned to official registry tag [`hpc-client-gui-plugins v1.0.0`](https://github.com/mskomek/hpc-client-gui-plugins/releases/tag/v1.0.0) for this release.

## v1.4.0

### File management and connection UX
- Profile edits now patch known fields onto the stored profile, so plugin provenance, file-manager state, jump settings, and unknown/future keys survive every edit; secret fields are only removed intentionally.
- Added a per-profile **Default local folder** (Advanced → File browser) that opens in the local pane when the profile connects.
- Added **Synchronized browsing**: navigation-only mirroring between the local pane and the active remote pane via an explicit, per-profile root pair captured from the current folders.
- Added metadata-only **directory comparison** with a Comparison column (Same / Local only / Remote only / Type differs / Size differs / Local newer / Remote newer), computed from existing snapshots with zero extra SFTP traffic.
- Connection dialog advanced section now groups SSH / Transfers / Other, offers secure host-key verification modes as a two-option combo, an editable per-profile SSH keepalive interval (0 disables), and clearer SSH timeout wording (0 = application defaults).
- Renamed the per-profile transfer limit to **Maximum simultaneous transfers** and made it the single user-facing source of truth; removed the duplicate global transfer-parallelism editor from Settings (stored legacy value is untouched).
- Added one-hop **SSH jump host (bastion)** support using Paramiko `direct-tcpip`: jump authenticates with key/agent only, both host keys are verified independently, jump/target failures clean up all resources, and transfers never create additional jump logins.

### Plugin ecosystem
- Introduced the Plugin Manager (Plugins button): Discover/Installed/Updates tabs backed by an official, hash-verified plugin registry.
- Official downloadable cluster/application plugins; TRUBA system settings moved to a downloadable TRUBA cluster-profile plugin while saved connection profiles remain fully compatible (they keep their copied settings snapshot).
- Added a declarative lint engine with plugin-delivered rule packs, including an ANSYS Fluent journal linter plugin.
- Added plugin-delivered job templates ("New from Template...") with safe placeholder rendering and editor-side preview.
- Added Slurm/Fluent resource cross-checks (CPU allocation vs solver process count) to the lint workflow.
- Discover now groups registry entries by plugin and shows only the latest compatible version (older versions remain in details); update actions use PEP 440 version comparison and downgrades are never offered as updates.
- Registry resolution now selects the highest compatible semantic version instead of relying on listing order; explicitly requested versions resolve exactly; invalid or duplicate registry versions are rejected clearly.
- Published plugin versions are immutable on disk: identical reinstalls are idempotent, conflicting or corrupt same-version content raises an integrity error without deleting the active version, failed installs/updates keep the previous active version, and state files are written atomically.
- The official registry client now refuses redirects to any non-official host (HTTPS-only final URLs) in addition to plain HTTP.

## v1.3.0

### Quality gates, release provenance, and transfer performance
- Redesigned the README front page with an offline-captured product screenshot and added a step-by-step download verification guide.
- Connection dialog: advanced settings collapsed by default with guaranteed profile round-trips and a minimum dialog width.
- SFTP overwrite uploads now use write pipelining like resume and atomic paths; a local wire benchmark measured ~10-21% faster 32 MiB uploads.
- Added an offline GUI directory-listing benchmark with regression gate; kept the QTreeWidget architecture based on measured evidence.
- Extracted pure presentation helpers from the remote file panel.
- Added a conservative Ruff lint gate, a Python 3.10/3.12 compatibility matrix job, pip-audit dependency auditing, and report-only coverage reporting to CI.
- Releases now publish a MANIFEST.json inventory and signed build-provenance attestations alongside SHA-256 checksums.
- Added a TRUBA-independent Slurm compatibility fixture matrix, a capability report contract, and a read-only cluster validation kit; fixed directory parsing when login banners precede scheduler output.
- Decomposed the SSH client behind a stable facade into dedicated SFTP-channel and interactive-shell owners without behavior change.
- Stabilized the offline test suite against startup modals and strengthened profile round-trip coverage.

## v1.2.8

### Embedded terminal and clearer connection diagnostics
- Replaced the legacy terminal surface with a bundled xterm.js terminal that requires no CDN or runtime download.
- Added live PTY streaming, resize synchronization, find, clear, and font-size controls.
- Fixed connection-page spacing and removed the unused fallback console that appeared behind saved connections.
- Added actionable Turkish and English explanations for authentication, DNS, timeout, port, key, banner, and SSH protocol failures.
- Clarified diagnostic codes so users can match an error dialog to the corresponding log entry.

## v1.2.7

### Transfer reliability and release hardening
- Added streaming remote directory listings over a reused SFTP channel.
- Improved cancellation cleanup, in-flight transfer key release, and partial-download decisions.
- Added end-to-end SSH/SFTP coverage for cancelled transfers and directory streaming.
- Hardened release automation for cached cross-platform builds and package validation.
- Added a release-surface guard and reproducible synthetic SFTP listing benchmark.

## v1.2.6

### Universal HPC branding
- Renamed the Python package to hpc_gui and aligned product-facing branding with generic HPC terminology.
- Improved Linux release startup geometry so the GUI opens within the available desktop area and remains resizable.

## v1.2.5

### Cross-platform release
- Added unified Windows GUI/CLI release validation and coordinated Windows/Linux release workflow.
- Multi-file Windows builds are distributed as portable archives with checksums.

## v1.2.4

### Transfer and UI reliability
- Added resumable remote transfer behavior with chunked partial files and cancellation-safe cleanup.
- Added configurable live-output idle warnings and a remote transfer speed test with 8, 32, and 100 MiB samples.
- Improved SFTP read-ahead/pipelining, asynchronous remote directory refresh, shutdown cancellation, and local tab headers.

## v1.2.3

### Public product polish
- Hardened local downloads with timeout, cancellation, cleanup, and atomic replacement.
- Added Windows CI coverage, security reporting guidance, dependency monitoring, and public repository hygiene.
- Improved the README product entry point and release packaging documentation.


## v1.2.2

### Reliability and workflow
- Jobs and accounting views now use structured scheduler output while retaining
  the raw command response for troubleshooting.
- Upload finalization keeps the temporary upload and remote rename on the same
  transfer channel, avoiding a second connection during the critical rename.
- CI and cross-platform regression checks were tightened for queue formatting,
  file-conflict ordering, diagnostic redaction, and local transfer behavior.
