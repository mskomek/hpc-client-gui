## v1.1.15
- CLI: added a full command-line interface (`hpc-client-gui` / `python -m
  truba_gui`) covering connection profiles (`profile list/show/create/
  update/delete/test`), diagnostics (`doctor environment/connection/smoke`),
  remote file operations (`files ls/stat/checksum/mkdir/upload/download/cp/
  mv/rm`), and Slurm job operations (`jobs list/status/accounting/lssrv/
  submit/cancel`), with `--format text|json` output and a documented text/
  JSON error contract. See `CLI_GUIDE_tr.md` and `CLI_GUIDE_en.md`.
- Documentation: added Turkish and English CLI guides and a maintenance/
  GUI-CLI parity policy (`MAINTENANCE_POLICY.md`) describing when a new GUI
  action needs a CLI counterpart and which release gates must stay connected.
- Reliability: increased the default SSH connect/banner timeout (15s/30s to
  45s/45s) so slower VPN or busy login-node connections no longer time out
  prematurely; the timeout remains configurable.
- Tests: fixed a hang in the FTP conflict-resolution test suite (a
  `patch.object` on `RemoteDirPanel._session_conflict_action` was silently
  reverting session state between test steps, causing a later step to fall
  through to a real, unmocked confirmation dialog and block indefinitely).
- Tests: added a local, fully offline SSH/SFTP integration harness
  (`tests/support/mock_ssh_server.py`) that drives the real CLI over an
  actual paramiko wire connection against a disposable local server, proving
  the file-transfer and job-command code paths round-trip correctly without
  any real cluster or credential involved.
- Release quality: added a local, offline gate that runs a Turkish-filename
  transfer round trip and places the `sftp-smoke/1` JSON artifact under the
  version folder; any gate failure stops the release.
- Verification: the CLI's connection, file-transfer, and read-only job
  commands were independently verified end to end against a real TRUBA
  cluster account (authentication, SFTP, checksum, upload/download/copy/
  move/delete round trip, `jobs list/lssrv/accounting`).
