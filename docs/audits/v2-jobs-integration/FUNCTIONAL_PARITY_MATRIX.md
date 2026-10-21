# Functional Parity Matrix

Status values remain **NOT VERIFIED** until focused tests pass against the integration source. Historical branch reports and prior artifacts are references, not current acceptance evidence.

| Area | Required behavior | Current evidence | Status |
|---|---|---|---|
| Jobs persistence | Finished Details, workdir, raw details, Files paths, stdout/stderr, Outputs, profile/job identity, safe migrations and tombstones | At `c1d8e66f`: 45 focused tests passed; synthetic v2 migration, scoped records, tombstones, bounded/redacted snapshots, path fallback and selected identity covered | PARTIALLY VERIFIED; UI restoration remains |
| Jobs history | Reopen old jobs, retain cached accounting, ordering/hide settings | At `c1d8e66f`: parser/workdir provenance and history service tests pass; stale accounting UI cache remains for wx Jobs wave | PARTIALLY VERIFIED |
| Jobs deletion | Delete Details is local-only, multi-delete scopes targets, Cancel Job stays distinct | `test_wx_jobs_bulk_delete.py`; not run | NOT VERIFIED |
| Async Jobs | Refresh/reconnect preserve selected job and reject stale async results | controller/provider/status tests identified; not run | NOT VERIFIED |
| wx Jobs | Details/Files/Outputs selection and event lifecycle | wx Jobs suite identified; not run | NOT VERIFIED |
| Release runner | Dynamic GUI discovery, isolated processes, scope selection, evidence hashes, crash visibility and coverage | Jobs/V2 runner overlap; not reconciled | NOT VERIFIED |
| Config | Profiles, legacy JSON, unknown fields, atomic writes, settings, transfer and window state | Focused persistence tests pending | NOT VERIFIED |
| SSH/SFTP | Password/key/keyboard-interactive, credential store, jump host, reconnect and redaction | Focused auth tests pending | NOT VERIFIED |
| CLI | Aliases, saved profiles, policy, Files/Jobs commands, validation, exit codes and JSON/UTF-8 | Focused CLI tests pending | NOT VERIFIED |
| Plugins | Legacy schemas, manifests, trusted commands, providers, quota/storage and compatibility | Contract suite pending | NOT VERIFIED |
| Qt Outputs | stdout/stderr tracking, refresh/follow, lifecycle, ANSI/truncation and thread ownership | Qt suite pending | NOT VERIFIED |
| Splash/updater/dialogs | Update checks, download progress, errors, close/recovery and persisted settings | Focused GUI tests pending | NOT VERIFIED |
| Files/FTP | Listings/cache/tabs, queue, destinations, conflicts, cancellation, reconnect and stale results | Mocked FTP/SFTP suites pending | NOT VERIFIED |
| Windows/Linux | Native GUI, release artifact and package acceptance | Not yet run on integration source | NOT VERIFIED |
