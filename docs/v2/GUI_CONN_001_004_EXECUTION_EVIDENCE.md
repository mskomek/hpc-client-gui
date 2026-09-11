# wx Connection execution evidence (Wave 71 → 71.5)

This record reports only checks actually run against the repository. It does
not treat static controls or service-only tests as visual parity evidence.

## Repository state

- Branch: `develop`
- Starting HEAD (Wave 71.5): `f72692805038e5dfc88305222d6e0a0bd9da3b87`
- Tested code HEAD: `815cfeb20fcc137740ee1cc56f5700e5c50cbe9e`
- Evidence record HEAD: `9658ddbbe2a242d4b6dcbb348cc894547c7e7615`
- Worktree state: clean (only pre-existing unrelated `.integration-recovery/`, `audit.zip`, `waves.zip`)
- OS: Windows 11 (win32)
- Python: 3.12.4
- wxPython: available (headless)
- Runtime contract: Qt remains the production runtime; `DEFAULT_GUI_RUNTIME` remains `qt`.

## CI governance

- GitHub Actions CI: intentionally disabled by moving `.github/workflows/ci.yml`
  to `docs/ci-disabled/ci.yml`.
- Automatic push/pull_request runs: none.
- Repository validation: performed locally; see
  `docs/REMEDIATION_STATUS_2026-09-11.md`.
- `release.yml` remains manual-only (`workflow_dispatch`).

## Root causes fixed (Wave 71.1–71.4)

- Saved master-password connection defect
- Test Cluster saved-credential defect
- wx password dialog defect
- Blank-name Save & Connect bug
- Tautological assertions removed
- Ruff violations cleaned
- CI workflow moved out of GitHub's executable workflow directory
- Parity source-of-truth synchronized
- Global F841 test ignore removed
- connect_selected() returns bool
- on_save_and_connect() consumes connect_selected() result
- Master Remember=false/true persistence proofs
- Test Cluster Remember=false/true persistence proofs
- Save & Connect master-cancel/wrong-master/worker-failure regression tests

## Root causes fixed (Wave 71.5)

- **begin_connect() failure recovery**: Previously swallowed with `pass`, leaving controller in `connecting` and buttons disabled. Now aborts synchronously: `controller.fail()`, transient password cleared, status failed, buttons restored, returns `False`.
- **Thread.start() failure recovery**: Previously returned `False` but left controller in `connecting` and buttons disabled. Now calls `controller.fail()`, clears transient password, sets status failed, restores buttons, returns `False`.
- **connect_selected() bool contract proven**: Direct assertion of return value via `host._wx_connection_connect_selected()` for no-selection (False) and worker-start (True) cases.
- **Remember=true settings persistence proven**: `update_settings({"master_password_dpapi": protected_token})` asserted with exact token value, not just `protect_secret` call.
- **Test Cluster Remember=true persistence proven**: Same strict assertion for Test Cluster path — `protect_secret` + `update_settings` with protected token, profile unchanged, master not in profile.
- **Save & Connect master-cancel callback result asserted**: `callback_result[0] is False` explicitly verified.
- **Save & Connect wrong-master rewritten as real Save & Connect**: Not a normal Connect test — uses FakeDialog with `on_save_and_connect`, profile saved via `_handle_save`, master prompt returns wrong master, callback returns False.
- **Save & Connect Thread.start failure test added**: Save succeeds, Thread.start raises, callback returns False, profile persists.

## Connection start contract

```
No selection: False
Profile missing: False
Credential failure: False
Master cancel: False
Wrong master: False
begin_connect failure: False
Thread.start failure: False
Worker successfully started: True
Worker later network failure: True (async, controller eventually failed)
```

## Controller recovery

```
begin_connect failure final state: failed
Thread.start failure final state: failed
Controls restored: YES (on both paths)
Transient secret cleared: YES (on both paths)
```

## Master Remember persistence

```
Remember=false protect_secret: NOT CALLED
Remember=false settings write: NOT CALLED
Remember=true protect_secret: CALLED (with master password)
Remember=true settings write: CALLED (with protected token)
Plaintext master persisted: NO
```

## Test Cluster persistence

```
Remember=false settings mutation: NO
Remember=true protected settings write: YES (protect_secret + update_settings with protected token)
Profile mutation: NO
Master used as SSH password: NO
Cancel backend call: NO
```

## Save & Connect contract

```
Master cancel result: False
Wrong master result: False
Thread.start failure result: False
Worker starts result: True
Worker later fails: True (async, controller eventually failed)
```

## Tests actually run (against committed HEAD `815cfeb2`)

### Full Connection suite
```
tests/test_wx_connection.py + tests/test_wx_connection_profiles.py
+ tests/test_wx_connection_hardening.py + tests/test_wx_connection_71_2.py
+ tests/test_wx_connection_71_3.py + tests/test_wx_connection_71_4.py
+ tests/test_wx_connection_71_5.py
Result: 88 passed in 37.19s (re-verified against committed HEAD 815cfeb20fcc137740ee1cc56f5700e5c50cbe9e: 88 passed in 42.36s)
```

### Broader regression
```
tests/test_optional_ssh_credentials.py + test_provider_capabilities.py + test_plugin_v2.py
+ test_quota_monitor.py + test_quota_runtime.py + test_log_redaction.py + test_cluster_self_test.py
Result: 33 passed, 9 subtests passed in 2.26s
```

### Ruff
```
python -m ruff check src/hpc_gui/wx_connection.py src/hpc_gui/wx_connection_dialog.py
  src/hpc_gui/services/connection_profile_service.py tests/test_wx_connection.py
  tests/test_wx_connection_profiles.py tests/test_wx_connection_hardening.py
  tests/test_wx_connection_71_2.py tests/test_wx_connection_71_3.py tests/test_wx_connection_71_4.py
  tests/test_wx_connection_71_5.py
Result: All checks passed (0 errors)
```

## Parity synchronization

- `parity_matrix.py`: GUI-CONN-001 PARTIAL, GUI-CONN-002 PARTIAL, GUI-CONN-003 PARTIAL, GUI-CONN-004 PARTIAL
- `V2_PARITY_STATUS.md`: GUI-CONN-001 PARTIAL, GUI-CONN-002 PARTIAL, GUI-CONN-003 PARTIAL, GUI-CONN-004 PARTIAL
- `GUI_CONN_001_004_EXECUTION_EVIDENCE.md`: PARTIAL for all four
- **They agree.**

## Parity assessment

| ID | Status | Evidence |
|---|---|---|
| GUI-CONN-001 | PARTIAL | Headless wx event chains + production Save & Connect + async contract + connect_selected bool contract + begin_connect/Thread.start recovery proven; no desktop screenshot |
| GUI-CONN-002 | PARTIAL | Real wx prompt path + real decrypt + cancel/wrong paths + Remember=false/true persistence proofs (including update_settings assertion) + Test Cluster Remember=true proven; no live desktop prompt capture |
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
