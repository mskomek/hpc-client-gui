# Changelog

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
