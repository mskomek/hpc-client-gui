# Changelog

## v1.4.0 (Unreleased)

### Plugin ecosystem
- Introduced the Plugin Manager (Plugins button): Discover/Installed/Updates tabs backed by an official, hash-verified plugin registry.
- Official downloadable cluster/application plugins; TRUBA system settings moved to a downloadable TRUBA cluster-profile plugin while saved connection profiles remain fully compatible (they keep their copied settings snapshot).
- Added a declarative lint engine with plugin-delivered rule packs, including an ANSYS Fluent journal linter plugin.
- Added plugin-delivered job templates ("New from Template...") with safe placeholder rendering and editor-side preview.
- Added Slurm/Fluent resource cross-checks (CPU allocation vs solver process count) to the lint workflow.

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
