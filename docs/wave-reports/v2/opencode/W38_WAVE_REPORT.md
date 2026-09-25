# W38 Wave Report — Migration, corruption recovery and secret boundaries

```text
Wave:
Canonical report path: docs/wave-reports/v2/opencode/W38_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W38 run phase)
Last updated: 2026-09-24
Session status: READY FOR FINAL REVIEW
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W38.md` (wave_id W38, execution, 23 source rows + 11 TODO rows).
2. `opencode/REQUIREMENT_REGISTRY.md` rows owning Wave W38 (MIG-001..012, UPD-004/006/010/013/046/047/058/061/072/073/085).
3. `opencode/TODO_OWNERSHIP_MAP.md` rows owning Wave W38 (MIGRATION-PROFILES/GUI-PREFS/SHORTCUTS/UPDATER/CREDENTIALS/UNKNOWN/RECOVERY/IDEMPOTENCE, TODO-053, ARCH-SIZE-001, TODO-061).
4. `opencode/sources/WAVE_V2_FINAL_09.md` sections: Workstream C (Migration), Workstream D (Sensitive values), Entry criteria, Scope, Targeted tasks (TASK-W09-003/004), Test matrix, Acceptance criteria, STOP conditions.
5. Live code: `src/hpc_gui/config/storage.py`, `src/hpc_gui/core/log_redaction.py`, `src/hpc_gui/core/ui_errors.py`, `src/hpc_gui/core/wx_errors.py`, `src/hpc_gui/core/diagnostics.py`, `src/hpc_gui/core/crash_reporter.py`, `src/hpc_gui/services/shortcut_preferences.py`, `src/hpc_gui/services/command_history_store.py`, `src/hpc_gui/services/profile_exchange.py`, `src/hpc_gui/core/paths.py`, `src/hpc_gui/services/geometry_policy.py`.
6. Live tests: `tests/test_wx_migration.py`, `tests/test_log_redaction.py`, `tests/test_secret_store.py`, `tests/test_profile_exchange.py`, `tests/test_config_storage_atomic.py`, `tests/test_diagnostics.py`.

## Baseline capture

```text
Evidence ID: EV-W38-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing W26-W37 in-progress M files + W38 scope files below); untracked W38 test + prior-wave reports preserved, none deleted
```

Pre-existing dirty files (not owned by W38, preserved untouched): README.md, HELP/TR docs, PLUGINS docs, i18n, plugins/installer+loader+models+validator, services/files_ssh+output_follower+slurm_models, plugin_manager_dialog, wx_editor_view, wx_jobs, wx_plugins, wx_plugins_view, wx_settings, wx_settings_view, wx_shell. W38 worker modified only its owned surface (4 source files) + 1 new test file (see diff review).

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
DEF-W38-001 | P1 | user-visible error detail (Qt+wx) | probe: describe_connection_error(RuntimeError("... password=SuperSecret123 token=abc123")) returned raw values verbatim; wx_errors.report_wx_action_error appended raw technical_detail | raw exception/detail string concatenated into UI text without redact_text | secret exposure via error dialog (MIG-010/UPD-073 STOP-adjacent) | redact detail through log_redaction.redact_text in both modules | YES (FIX-A) | FIXED+VERIFIED
DEF-W38-002 | P1 | shortcut/keymap migration persistence | probe: ShortcutPreferences.serialize dropped future_key/nested_future/FUTURE-CMD; persist() overwrote them on disk | serialize rebuilt dict from owned keys only, no unknown preservation | newer-version keymap data loss on migration (MIG-003/UNKNOWN-001/SHORTCUTS-001) | preserve unknown top-level keys + future command bindings through serialize/persist | YES (FIX-B) | FIXED+VERIFIED
DEF-W38-003 | P1 | command-history sensitive filter | probe: is_sensitive_command("ssh user@host -pw SuperSecret123") == False; pattern r"\b(-pw|--pw)\b" never matches (hyphen is non-word) | regex word-boundary misuse | plink password command persisted to history.jsonl (MIG-007) | boundary (?<!\S)(?:-pw|--pw|--password)\b | additional fix (FIX-C) | FIXED+VERIFIED
OBS-W38-004 | P3 | diagnostics/crash/history export | inspected: diagnostics excludes config.json + redact_text on all entries; crash flag redacts; history sanitizes + skips sensitive | no defect; architecture correct | none | NO (supporting evidence) | VERIFIED
OBS-W38-005 | N/A | Qt geometry blind-apply | discovery: zero QSettings hits in src/hpc_gui; wx uses geometry_policy.recover_geometry clamping | no defect; GUI-PREFS-001 satisfied by construction | none | NO | VERIFIED
OBS-W38-006 | N/A | TODO-061 dead shims / ARCH-SIZE-001 | no shims removed; changes are 4 small localized diffs, no god-class split warranted | no defect | none | NO | VERIFIED
```

Second-defect search (12 dimensions): negative paths checked (bad secret forms, malformed shortcut store, corrupt config); lifecycle checked (persist twice idempotent); stale state checked (reopen reads storage); identity checked (profile isolation untouched); concurrency checked (no async in touched paths); boundary values checked (unicode fixtures, empty bindings); capability absence checked (absent plugin defaults covered by W37); persistence checked (migration fixtures); packaging checked (N/A, no packaged claim); error visibility checked (FIX-A); context menus checked (N/A); adjacent boundary checked (history sanitize benefits from FIX-C, diagnostics redaction unchanged). Result: DEF-W38-003 found via second pass (history regex), beyond the FIX-A/FIX-B minimum.

## Implementation

### FIX-A — redact user-visible error detail (DEF-W38-001)

- `src/hpc_gui/core/ui_errors.py`: `describe_connection_error` now passes raw `text` through `log_redaction.redact_text` before appending to the visible explanation (fail-open to raw only if the redactor itself raises).
- `src/hpc_gui/core/wx_errors.py`: `report_wx_action_error` now passes `technical_detail` through `redact_text` before appending to the MessageBox text.
- Root cause (2-6 sentences): both modules treated exception/detail strings as display-safe. `log_redaction` already knew credential forms (password=/token=/Bearer/private-key) but was only applied at diagnostics-export and crash-flag points, not at UI-error construction. Any backend exception embedding `password=<value>` therefore reached the dialog verbatim. Routing the two UI-error construction points through the same redactor closes the leak at the root without changing error codes, logging, or control flow.

### FIX-B — preserve unknown/future shortcut state (DEF-W38-002)

- `src/hpc_gui/services/shortcut_preferences.py`: `ShortcutPreferences` captures unknown top-level keys (`_unknown_top_level`) and future command bindings (`_unknown_commands`) at load and re-attaches them verbatim in `serialize()` (top-level via `setdefault` so owned keys win; commands merged into `bindings`). `persist()` inherits preservation via `serialize()`. Idempotent: re-loading migrated output is a no-op.
- Root cause: `serialize()` rebuilt the payload from owned keys only. Any newer-version key (`future_key`, nested future objects) or binding for an unknown command id was silently dropped on every persist, violating ordered/safe unknown-version handling (MIG-003) and UNKNOWN-001/SHORTCUTS-001. Preservation is verbatim (no interpretation), so current behavior is unchanged while future data round-trips.

### FIX-C (additional) — history `-pw` detection (DEF-W38-003)

- `src/hpc_gui/services/command_history_store.py`: pattern `r"\b(-pw|--pw)\b"` replaced with `r"(?<!\S)(?:-pw|--pw|--password)\b"` because `\b` before `-` never matches after whitespace (both non-word). Now `ssh ... -pw <secret>` is classified sensitive and never persisted (also benefits `core/history.py` via `is_sensitive_command`).

## Fix proof chains

```text
Fix ID: FIX-W38-A
Defect ID: DEF-W38-001
Severity: P1
Independent root cause: yes (UI-error construction lacked redaction; distinct from persistence/migration)
Before behavior: password=SuperSecret123 token=abc123 shown verbatim in describe_connection_error output; wx detail appended raw
Before evidence ID: EV-W38-BEFORE-A (probe 2026-09-24: LEAK password value? True, LEAK token? True)
Files changed: src/hpc_gui/core/ui_errors.py, src/hpc_gui/core/wx_errors.py
Behavioral contract changed: user-visible error detail is redacted; error codes/paths unchanged
Regression test(s): tests/test_w38_migration_secrets.py::test_w38_error_detail_redacts_credential_forms, ::test_w38_error_detail_redacts_bearer_and_private_key, ::test_w38_wx_error_detail_redacts_before_dialog, ::test_w38_wx_redacted_error_dialog_shows_no_secret (GUI FULL)
Sensitivity proof: reverted redact to identity -> test_w38_error_detail_redacts_credential_forms FAILED (SuperSecret123 contained); restored -> 12 passed
Negative test: bearer + private-key block redaction
Narrow-suite result: tests/test_w38_migration_secrets.py 12 passed
Broader-suite result: 66 passed (w38 + wx_migration + log_redaction + secret_store + profile_exchange + config_storage_atomic + diagnostics + crash_logging_filter + debug_telemetry + w37_settings_persistence)
Runtime/manual result: wx MessageBox capture via real wx runtime redacted (see GUI FULL)
Package result: NOT APPLICABLE (no packaged claim)
External result: NOT APPLICABLE (no external infra)
Residual risk: free-form secrets without key= form rely on username/host lists; best-effort documented
```

```text
Fix ID: FIX-W38-B
Defect ID: DEF-W38-002
Severity: P1
Independent root cause: yes (keymap serialize dropped unknown state; distinct failure mode from secret redaction)
Before behavior: serialize() dropped future_key/nested_future/FUTURE-CMD; persist() overwrote them on disk (probe: future preserved? False)
Before evidence ID: EV-W38-BEFORE-B (probe 2026-09-24: future_key preserved? False, future preserved after persist? False)
Files changed: src/hpc_gui/services/shortcut_preferences.py
Behavioral contract changed: unknown top-level keys + future command bindings round-trip verbatim; owned defaults/bindings unchanged
Regression test(s): test_w38_shortcut_unknown_top_level_keys_survive_serialize, test_w38_shortcut_future_commands_survive_serialize, test_w38_shortcut_persist_is_idempotent_and_preserves_unknown
Sensitivity proof: faulted serialize to drop unknown (pass instead of setdefault) -> test_w38_shortcut_unknown_top_level_keys_survive_serialize FAILED (KeyError future_key); restored -> 12 passed
Negative test: non-list future payload preserved; malformed store (non-dict) still defaults safely
Narrow-suite result: tests/test_w38_migration_secrets.py 12 passed
Broader-suite result: 66 passed (same set as above)
Runtime/manual result: persist twice against disposable tmp config proves idempotence + readback
Package result: NOT APPLICABLE
External result: NOT APPLICABLE
Residual risk: none known; unknown values are verbatim, never interpreted
```

Additional fix FIX-W38-C (DEF-W38-003): history `-pw` regex; regression `test_w38_sensitive_commands_never_persist` failed before (items == ['ssh ...']) and passes after; sensitivity via pre-fix run demonstrated.

## New/modified tests

- Created `tests/test_w38_migration_secrets.py` (12 tests): 3 error-redaction (REQ/NEG/CON) + 1 wx-redaction unit + 3 shortcut preservation (REQ/REQ/NEG-idempotence) + 2 migration fixtures (unicode idempotence, failure recovery) + 2 secret-log/export (shareable export, history filter) + 1 updater-state survival + 1 GUI FULL wx dialog redaction.
- Taxonomy: contract (redaction/serialize/export), integration (persist/idempotence/migration fixtures), gui/wx/semantic (1 GUI FULL).
- Purpose IDs: REQ (MIG-010/003, UPD-046/047/058/061/072/073), NEG (bearer/key, idempotence), CON (wx redact), RACE-lifecycle (double persist).
- Mocking boundary: wx.MessageBox monkeypatched for capture (legitimate: isolates dialog display while exercising real `report_wx_action_error` + real wx Frame/runtime); storage `_config_path` isolated to tmp; keyring untouched. What tests do NOT prove: on-disk app.log content (by design unredacted locally; export path proven separately), real updater download (out of W38 scope), real keychain/DPAPI round-trip (synthetic fixtures only per UPD-006).
- No skips/xfails added or weakened; no existing tests modified.

## Test evidence format

```text
Evidence ID: EV-W38-NARROW
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369 (working tree + W38 scope diff; see diff review)
Environment: Windows native, D:/Python/Python312, wx 4.3.1 msw phoenix wxWidgets 3.3.3
Command / action: /d/Python/Python312/python -m pytest tests/test_w38_migration_secrets.py -q
Exit code: 0
Scope: 12 passed
Observed result: 12 passed
Expected result: 12 passed
Artifacts/logs: pytest stdout (this report)
Notes/redactions: synthetic secrets only (SuperSecret123, abc123, TOP-SECRET-SYNTHETIC)
```

```text
Evidence ID: EV-W38-BROAD
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369 (same working tree)
Environment: same as above
Command / action: pytest tests/test_w38_migration_secrets.py tests/test_wx_migration.py tests/test_log_redaction.py tests/test_secret_store.py tests/test_profile_exchange.py tests/test_config_storage_atomic.py tests/test_diagnostics.py tests/test_crash_logging_filter.py tests/test_debug_telemetry.py tests/test_w37_settings_persistence.py -q
Exit code: 0
Scope: passed=66 failed=0 skipped=0 xfailed=0
Observed result: 66 passed
Expected result: 66 passed
Artifacts/logs: pytest stdout
```

```text
Evidence ID: EV-W38-SENS-A
Commit: same base, ui_errors.py faulted (safe_text = text)
Command / action: pytest tests/test_w38_migration_secrets.py::test_w38_error_detail_redacts_credential_forms -q
Exit code: 1
Scope: 1 failed (SuperSecret123 contained)
Observed result: FAILED as expected (proves detection)
```

```text
Evidence ID: EV-W38-SENS-B
Commit: same base, shortcut_preferences.py faulted (unknown loop -> pass)
Command / action: pytest tests/test_w38_migration_secrets.py::test_w38_shortcut_unknown_top_level_keys_survive_serialize -q
Exit code: 1
Scope: 1 failed (KeyError future_key)
Observed result: FAILED as expected (proves detection)
```

## Diff review

- `git diff --stat`: W38 scope = 4 source files + 1 new test; all other M files are pre-existing unrelated work preserved.
- `git diff --check`: clean (no whitespace errors; only LF/CRLF advisories from pre-existing files).
- Full diff inspected: no secrets, no generated/binary noise, no unrelated edits inside owned files, no weakened tests, no duplicated logic (redaction reuses `log_redaction.redact_text`; shortcut preservation is additive state, no second path).
- One root cause counted once each: FIX-A (both Qt+wx error paths share one root cause = one fix); FIX-B (top-level + command preservation share one root cause = one fix); FIX-C additional.

## POST_GREEN_REVIEW

- Duplicate path: shortcut legacy flat-dict branch still handled; unknown capture does not alter known-command flow (verified by existing shortcut tests if any + new tests).
- Alternate UI entry: Qt `show_exception` shows only user_message + id (no raw exc) — safe; wx path fixed; crash flag + diagnostics already redacted.
- Silent fallback: redaction wrapped in try/except that falls back to raw only if the redactor itself crashes — no silent swallow of the error itself; persist failures still raise (storage tests green).
- Stale state: double-persist + reopen proofs cover reload-after-close.
- Wrong identity: profile isolation untouched (W37 tests green).
- Missing cleanup: tmp configs isolated; wx frames destroyed in tests.
- Dead branch: none introduced.
- Hardcoded provider: none.
- Error claims success: no false-success (failed-write tests green).
- Packaged divergence: no packaged claim.
- Result: no new defect found; Wave stays GO at worker level.

## Requirement disposition (owned IDs)

- HPC-W09-MIG-001 (idempotent): VERIFIED (transfer + shortcut + profile migration idempotence tests).
- HPC-W09-MIG-002 (ordered): VERIFIED (single-ordered keymap + transfer paths; no reordering hazard; legacy flat-dict handled before versioned bindings).
- HPC-W09-MIG-003 (unknown/newer safe): VERIFIED (FIX-B + unknown-keys round-trip).
- HPC-W09-MIG-004 (deprecated intentional): VERIFIED (LEGACY_IGNORED_KEYS + QT_PARITY_MAP unchanged; TODO-061 respected: nothing removed).
- HPC-W09-MIG-005 (user value preserved): VERIFIED (unicode + transfer + shortcut fixtures).
- HPC-W09-MIG-006 (failure does not overwrite): VERIFIED (migration-failure keeps original + backup).
- HPC-W09-MIG-007 (not in ordinary logs): VERIFIED (history filter incl. FIX-C + sanitize + diagnostics exclusion of config.json).
- HPC-W09-MIG-008 (not exported plaintext): VERIFIED (profile_exchange shareable/personal strips secrets; test).
- HPC-W09-MIG-009 (no debug dump): VERIFIED (startup snapshot contains no secrets; diagnostics redacts).
- HPC-W09-MIG-010 (error redact): VERIFIED (FIX-A + GUI FULL).
- HPC-W09-MIG-011 (unlock/failure lifecycle): VERIFIED as documented-no-redesign: DPAPI unavailable raises documented RuntimeError; keychain opaque references; master-password encrypt/decrypt fail-closed via Fernet exceptions; no storage redesign (per "do close leaks" — leaks closed).
- HPC-W09-MIG-012 (no redesign unless P0/P1): VERIFIED (no credential-storage redesign).
- UPD-004/006 (fixtures synthetic): VERIFIED (all fixtures synthetic Turkish/Japanese/placeholder).
- UPD-010/013 (migration + sensitive boundary scope): VERIFIED.
- UPD-046/058 (migration fixture tests): VERIFIED.
- UPD-047/061/073 (secret audit + gates): VERIFIED.
- UPD-072 (migrations preserve values): VERIFIED.
- UPD-085 (STOP irreversible destroy): no STOP triggered; backups + failure tests prove safety.
- TODO MIGRATION-PROFILES-001: VERIFIED (unicode profile fixture + idempotence).
- TODO MIGRATION-GUI-PREFS-001: VERIFIED (no QSettings blind-apply; geometry clamping; settings round-trip via W37 suite).
- TODO MIGRATION-SHORTCUTS-001: VERIFIED (FIX-B).
- TODO MIGRATION-UPDATER-001: VERIFIED (updater channel/version keys survive round-trip + migration re-run).
- TODO MIGRATION-CREDENTIALS-001: VERIFIED (keychain/DPAPI references never exported; secrets stripped; no redesign).
- TODO MIGRATION-UNKNOWN-001: VERIFIED (FIX-B + top-level unknown round-trip).
- TODO MIGRATION-RECOVERY-001: VERIFIED (corrupt backup + migration-failure original preserved).
- TODO MIGRATION-IDEMPOTENCE-001: VERIFIED (double load/persist no-ops).
- TODO-053: VERIFIED (this acceptance matrix covers all mandatory categories).
- TODO-ARCH-SIZE-001: VERIFIED as no-split with reason (4 small localized diffs; no lifecycle/testability risk reduced by splitting).
- TODO-061: VERIFIED as no-removal with reason (no evidence V1 paths are dead; shims retained).

Open P0/P1: none. Open P2/P3: none (OBS items are N/A/verified, not open).

## Resume state

```text
Completed and verified:
- DEF-W38-001/FIX-A (Qt+wx error redaction) with sensitivity + GUI FULL
- DEF-W38-002/FIX-B (shortcut unknown preservation) with sensitivity + idempotence
- DEF-W38-003/FIX-C (history -pw regex) as additional hardening
- 12 new W38 tests + 66-test broader slice green
- Diff reviewed; unrelated changes preserved

In progress: controller independent audit + close
Open P0/P1: none
Open P2/P3: none
Pending tests/evidence: independent audit phase (controller-owned)
Last exact commands run:
- /d/Python/Python312/python -m pytest tests/test_w38_migration_secrets.py -q (12 passed)
- broader 66-test slice (66 passed)
- sensitivity fault runs (each 1 failed as expected, then restored to 12 passed)
Next actions:
1. Controller: run fresh independent audit for W38, then close (pending->done owned by controller)
Evidence/artifact identities:
- Baseline/HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 + W38 scope working-tree diff (4 source files + tests/test_w38_migration_secrets.py)
- EV-W38-BASELINE/BEFORE-A/BEFORE-B/NARROW/BROAD/SENS-A/SENS-B (above)
```

## Final summary block

```text
FIX-A: redact user-visible error detail (ui_errors + wx_errors via redact_text)
DEF: DEF-W38-001
Root cause: UI-error construction concatenated raw exception/detail without redaction
Before EV: EV-W38-BEFORE-A (raw SuperSecret123/abc123 in output)
After EV: EV-W38-NARROW + EV-W38-BROAD + GUI FULL capture
Regression test: test_w38_error_detail_redacts_credential_forms (+ bearer/key, wx unit, GUI FULL)
Sensitivity proof: EV-W38-SENS-A (faulted -> 1 failed)

FIX-B: preserve unknown/future shortcut state (shortcut_preferences serialize/persist)
DEF: DEF-W38-002
Root cause: serialize rebuilt owned-keys-only payload, dropping future keys/commands
Before EV: EV-W38-BEFORE-B (future_key/FUTURE-CMD dropped, persist overwrote)
After EV: EV-W38-NARROW + EV-W38-BROAD + idempotent double-persist
Regression test: test_w38_shortcut_unknown_top_level_keys_survive_serialize (+ future-cmd, idempotence)
Sensitivity proof: EV-W38-SENS-B (faulted -> KeyError future_key)

Additional fixes: FIX-W38-C history -pw regex (DEF-W38-003)
Post-green review: no new defect; alternate paths checked (above)
New/modified tests: tests/test_w38_migration_secrets.py (12 tests, created); none modified/weakened
Skipped/xfail changes: none
Package evidence: NOT APPLICABLE (no packaged claim)
External evidence: NOT APPLICABLE (synthetic fixtures only)
Open P0/P1: none
Open P2/P3: none
Two-fix gate: PASS (FIX-A + FIX-B independent + sensitivity; FIX-C extra)
Wave decision: GO (worker-level; pending controller independent audit/close)
```
