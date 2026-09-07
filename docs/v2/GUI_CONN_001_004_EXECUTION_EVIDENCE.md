# wx Connection execution evidence (Wave 71 → 71.4)

This record reports only checks actually run against the repository. It does
not treat static controls or service-only tests as visual parity evidence.

## Repository state

- Branch: `develop`
- Starting HEAD (Wave 71.3): `77a5debf467de87a3a25a58e29108a1fcc45b4df`
- Tested code HEAD: `e810ae09`
- Evidence record HEAD: (this document)
- Worktree state: clean (only pre-existing unrelated `.integration-recovery/`, `audit.zip`, `waves.zip`)
- OS: Windows 11 (win32)
- Python: 3.12.4
- wxPython: available (headless)
- Runtime contract: Qt remains the production runtime; `DEFAULT_GUI_RUNTIME` remains `qt`.
- PySide6/shiboken6 were not removed. `.tmp/` was not touched.

## CI governance

- develop automatic CI: DISABLED
- User authorized enabling CI: NO
- Workflow file: `.github/workflows/ci.yml` — `push: [main]`, `pull_request: [main]`

## Root causes fixed (Wave 71.1–71.2)

- Saved master-password connection defect
- Test Cluster saved-credential defect
- wx password dialog defect
- Blank-name Save & Connect bug
- Tautological assertions removed
- Ruff violations cleaned
- CI develop trigger removed
- Parity source-of-truth synchronized

## Root causes fixed (Wave 71.3)

- Save & Connect async contract: `on_save_and_connect` returns `True` when save succeeds + worker starts
- Production Save & Connect event-chain test with real WxConnectionDialog
- Master-password real wx prompt test (no cache, mock wx widgets only)
- Test Cluster real button EVT_BUTTON test
- Global F841 test ignore removed

## Root causes fixed (Wave 71.4)

- **`connect_selected()` return contract**: Returns `False` for all synchronous early-return paths (no selection, profile not found, master cancel/wrong/unavailable, credential resolution failure). Returns `True` only after `Thread(target=worker, daemon=True).start()` is successfully invoked, with try/except around Thread.start().
- **`on_save_and_connect()` consumes return value**: `started = connect_selected(None); return bool(started)`.
- **Master Remember=false proof**: Settings unchanged, `protect_secret` not called, `update_settings` not called for master persistence, plaintext master never stored.
- **Master Remember=true proof**: `protect_secret` called with master password, plaintext never stored in profile.
- **Test Cluster Remember=false proof**: Profiles unchanged, settings unchanged, `protect_secret` not called.
- **Test Cluster cancel proof**: No self-test backend call, button re-enabled, no settings change.
- **Save & Connect + master cancel**: Profile saved, no SSH, `on_save_and_connect` returns False.
- **Save & Connect + wrong master**: No SSH, returns False.

## Async Save & Connect contract

`on_save_and_connect(...)` returns:

- **True**: save succeeded, canonical saved profile selected, connection worker successfully launched.
- **False**: save failed / profile couldn't be selected / credential resolution failed / master prompt cancelled / worker couldn't start.

Worker failure is async: `controller.state → failed`, visible status updates, buttons restored by production `done()` callback. Does NOT retroactively change the callback return value.

## Master password persistence

```
Remember=false profile mutation: NO
Remember=false settings mutation: NO
Remember=false protect_secret called: NO
Remember=false update_settings called for master: NO

Remember=true protect_secret called: YES (with master password)
Remember=true plaintext master persisted: NO
```

## Test Cluster persistence

```
Profile mutation: NO
Settings mutation with Remember=false: NO
Secret-store mutation: NO
Backend call on Cancel: NO
```

## connect_selected contract

```
No selection: False
Master cancel: False
Wrong master: False
Saved credential unavailable: False
Worker started: True
Worker later failed: True (async)
```

## Tests actually run (against committed HEAD `e810ae09`)

### Full Connection suite
```
tests/test_wx_connection.py + tests/test_wx_connection_profiles.py
+ tests/test_wx_connection_hardening.py + tests/test_wx_connection_71_2.py
+ tests/test_wx_connection_71_3.py + tests/test_wx_connection_71_4.py
Result: 79 passed in 26.92s
```

### Broader regression
```
tests/test_optional_ssh_credentials.py + test_provider_capabilities.py + test_plugin_v2.py
+ test_quota_monitor.py + test_quota_runtime.py + test_log_redaction.py + test_cluster_self_test.py
Result: 33 passed, 9 subtests passed in 1.77s
```

### Ruff
```
python -m ruff check src/hpc_gui/wx_connection.py src/hpc_gui/wx_connection_dialog.py
  src/hpc_gui/services/connection_profile_service.py tests/test_wx_connection.py
  tests/test_wx_connection_profiles.py tests/test_wx_connection_hardening.py
  tests/test_wx_connection_71_2.py tests/test_wx_connection_71_3.py tests/test_wx_connection_71_4.py
Result: All checks passed (0 errors)
Global F841 test ignore: REMOVED
```

## Parity synchronization

- `parity_matrix.py`: GUI-CONN-001 PARTIAL, GUI-CONN-002 PARTIAL, GUI-CONN-003 PARTIAL, GUI-CONN-004 PARTIAL
- `V2_PARITY_STATUS.md`: GUI-CONN-001 PARTIAL, GUI-CONN-002 PARTIAL, GUI-CONN-003 PARTIAL, GUI-CONN-004 PARTIAL
- `GUI_CONN_001_004_EXECUTION_EVIDENCE.md`: PARTIAL for all four
- **They agree.**

## Parity assessment

| ID | Status | Evidence |
|---|---|---|
| GUI-CONN-001 | PARTIAL | Headless wx event chains + production Save & Connect + async contract + connect_selected return contract proven; no desktop screenshot |
| GUI-CONN-002 | PARTIAL | Real wx prompt path + real decrypt + cancel/wrong paths + Remember=false/true persistence proofs proven; no live desktop prompt capture |
| GUI-CONN-003 | PARTIAL | Templates provenance; no desktop capture |
| GUI-CONN-004 | PARTIAL | Fail-closed quota, nested provider lookup; no real transport |
| GUI-I18N-001 | PARTIAL | New EN/TR keys verified; no visual language-switch |
| GUI-A11Y-001 | PARTIAL | Named actions, visible labels; no screen-reader audit |
| GUI-VISUAL-001 | PARTIAL | Scrollable editor, sizers; no 100/150/200% screenshots |

## Remaining limitations

- No desktop wx session available for manual walkthrough.
- All wx modals auto-mocked via `tests/conftest.py` or test-level mocking.
- No DPI screenshots, no screen-reader audit, no visual language-switch capture.
- All parity statuses remain PARTIAL for lack of manual desktop evidence.
