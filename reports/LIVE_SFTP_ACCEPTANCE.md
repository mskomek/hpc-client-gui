# Live SFTP Acceptance

Date: 2026-10-23

## Result

Status: PASS for the current application source over a real SFTP subsystem; BLOCKED for the requested Tailscale-to-HPC route because the verified connection used the existing development-host lab path.

Application branch: codex/ansys-journal-studio-host-integration
Application source commit: 1cec0471e3daf50a16ba4161282aff2260ba9dd9
Remote service SHA-256: dafb80fe9f2874c3109e5dfb7c88db58ef1599001dffd0fbbf143099f5dbd8d1

The acceptance harness created an isolated journal-studio-acceptance directory on login-control01 and removed only its own run directory. No existing user work directory was cleaned.

## Results

19/19 checks passed:

- Real SFTP subsystem and isolated test area.
- UTF-8 BOM and CRLF open; exact SHA-256 round trip.
- Save without edits remained byte-identical.
- Parameter edit, save, and reopen.
- Unicode/space-containing Save As; missing-file handling.
- Concurrent-client conflict detection and external-change detection.
- Remote compare and restore.
- Permission denial.
- Target and parent symlink rejection; lexical traversal rejection.
- UTF-8/LF handling.
- Interrupted upload preserved the original and removed its temporary file.
- Disconnect surfaced without data loss; reconnect and reopen preserved bytes.
- Test-area cleanup completed.

The debug evidence recorded one upload temporary before cleanup and zero afterward; the final check reported orphan_temporaries=0. SHA-256 values are retained in the sanitized machine-readable evidence.

## Limits

This was an actual SFTP integration run, not a mock, but it did not traverse Tailscale from DESKTOP-TMGUAH7. The app's native GUI was not used for this remote file run; the current-source integration harness exercised the service workflow. GUI acceptance is tracked separately. No production files were touched.

Evidence: evidence/live-sftp-final.log and evidence/live-sftp-debug.log in the handoff ZIP.
