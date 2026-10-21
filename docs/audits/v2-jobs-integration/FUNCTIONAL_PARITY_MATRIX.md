# Functional Parity Matrix

Status values remain **NOT VERIFIED** until focused tests pass against the integration source. Historical branch reports and prior artifacts are references, not current acceptance evidence.

| Area | Required behavior | Current evidence | Status |
|---|---|---|---|
| Jobs persistence | Finished Details, workdir, raw details, Files paths, stdout/stderr, Outputs, profile/job identity, safe migrations and tombstones | At `c1d8e66f`: 45 focused tests passed; synthetic v2 migration, scoped records, tombstones, bounded/redacted snapshots, path fallback and selected identity covered | PARTIALLY VERIFIED; UI restoration remains |
| Jobs history | Reopen old jobs, retain cached accounting, ordering/hide settings | At `d12a752c`: history parser, workdir provenance, cache retention, wx history callback, hide-finished persistence and identity refresh tests passed | PARTIALLY VERIFIED; final acceptance remains |
| Jobs deletion | Delete Details is local-only, multi-delete scopes targets, Cancel Job stays distinct | At `d12a752c`: store tombstone and `test_wx_jobs_bulk_delete.py` passed; no remote cancel/delete was issued | PARTIALLY VERIFIED |
| Async Jobs | Refresh/reconnect preserve selected job and reject stale async results | At `d12a752c`: controller coordinator, provider status, refresh identity, stale-selection/reconnect tests passed | PARTIALLY VERIFIED |
| wx Jobs | Details/Files/Outputs selection and event lifecycle | At `d12a752c`: 95 focused controller/workspace tests and 64 extended GUI tests passed; post-fix teardown stress passed | PARTIALLY VERIFIED; Windows11 guest acceptance remains |
| Release runner | Dynamic GUI discovery, isolated processes, portable/acceptance scopes, pinned evidence hashes, crash visibility and coverage | At `4ed2075c`: 13 runner tests passed; hash check and temporary wheel build passed; dynamic wx/Qt and future FTP split selectors are covered | PARTIALLY VERIFIED; full acceptance suite and coverage matrix remain |
| Config | Profiles, legacy JSON, unknown fields, atomic writes, settings, transfer and window state | At `71ef960b`: 356 focused persistence/profile/CLI/SSH/history tests passed, one POSIX-only skip; 27 wx settings/window-state tests passed; sbatch follow preference regression passed | PARTIALLY VERIFIED; full acceptance remains |
| SSH/SFTP | Password/key/keyboard-interactive, credential store, jump host, reconnect and redaction | Focused auth tests pending | NOT VERIFIED |
| CLI | Aliases, saved profiles, policy, Files/Jobs commands, validation, exit codes and JSON/UTF-8 | Focused CLI tests pending | NOT VERIFIED |
| Plugins | Legacy schemas, manifests, trusted commands, providers, quota/storage and compatibility | Contract suite pending | NOT VERIFIED |
| Qt Outputs | stdout/stderr tracking, refresh/follow, lifecycle, ANSI/truncation and thread ownership | Qt suite pending | NOT VERIFIED |
| Splash/updater/dialogs | Update checks, download progress, errors, close/recovery and persisted settings | Focused GUI tests pending | NOT VERIFIED |
| Files/FTP | Listings/cache/tabs, queue, destinations, conflicts, cancellation, reconnect and stale results | Mocked FTP/SFTP suites pending | NOT VERIFIED |
| Windows/Linux | Native GUI, release artifact and package acceptance | Not yet run on integration source | NOT VERIFIED |
