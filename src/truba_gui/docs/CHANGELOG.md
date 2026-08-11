# Changelog

## v1.2.2

### Reliability and workflow
- Jobs and accounting views now use structured scheduler output while retaining
  the raw command response for troubleshooting.
- Upload finalization keeps the temporary upload and remote rename on the same
  transfer channel, avoiding a second connection during the critical rename.
- CI and cross-platform regression checks were tightened for queue formatting,
  file-conflict ordering, diagnostic redaction, and local transfer behavior.
