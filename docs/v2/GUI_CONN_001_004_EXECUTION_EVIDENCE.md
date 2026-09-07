# wx Connection execution evidence (Wave 71 → 71.3)

This record reports only checks actually run against the repository. It does
not treat static controls or service-only tests as visual parity evidence.

## Repository state

- Branch: `develop`
- Expected starting HEAD (Wave 71.3 task): `52aa565f3ce775afdc9e6f84f0a131a9d695362d`
- Exact tested HEAD: `bd7dc118`
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

## Root causes fixed (Wave 71.1)

- Saved master-password connection defect: `ssh_info_from_profile` never prompted for master.
- Test Cluster saved-credential defect: `_test_cluster` called `_collect_profile()` which popped secret fields.
- wx password dialog defect: MFA/edit-auth used wrong dialog type.
- Weak Add test: tautological assertion replaced with strict count.
- Fake action-state test: replaced with real Connect button events.
- Save & Connect evidence gap: added full wx event chain.

## Root causes fixed (Wave 71.2)

- Blank-name Save & Connect bug: `_handle_save()` returns authoritative saved profile dict; callers use canonical name.
- Tautological assertion removed: `assert result is True or result is False` removed.
- Ruff violations cleaned: unused imports and variables removed.
- CI develop trigger removed: `develop` removed from push/pull_request triggers.
- Parity source-of-truth synchronized: `V2_PARITY_STATUS.md` matches `parity_matrix.py`.
- pyproject.toml: `F841` added to test file ignores (now removed in 71.3).

## Root causes fixed (Wave 71.3)

- **Save & Connect async contract**: `on_save_and_connect` returns `True` when save succeeds + connection worker starts. Worker failure is async and does not retroactively change the return value. The connect-after-save failure test now correctly asserts `True` + eventual `controller.failed`.
- **Production Save & Connect event-chain**: New test uses real `WxConnectionDialog`, real `btn_save_connect` EVT_BUTTON, real production `on_save_and_connect` callback from `wx_connection.py`, real `save_profile()`, real `connect_selected()`, blank-name canonical `alice@login.cluster.edu` path.
- **Master-password real wx prompt**: New test seeds NO DPAPI cache. Mocks only wx.Dialog/TextCtrl widgets so `_master_ask_factory` creates a real dialog that returns "master123". Real `resolve_password_for_connect` + real `decrypt_with_master` exercised. Prompt invoked exactly once.
- **Master-password cached path**: Separated into own test. Proves cache optimization works but is NOT evidence for wx prompt chain.
- **Master-password cancel via wx prompt**: New test with NO cache. wx.Dialog mocked to Cancel. Real resolver. No SSH, buttons restored.
- **Test Cluster real button event**: New test dispatches real `btn_test_cluster` EVT_BUTTON. Real `_test_cluster()` → real credential resolver → real decrypt → fake self-test. No direct `_test_cluster()` call.
- **Test Cluster cancel path**: New test with wx.Dialog Cancel. No self-test backend call, button re-enabled, storage unchanged.
- **Global F841 removed**: `pyproject.toml` no longer ignores F841 for tests. All `app = wx.App.Get()` renamed to `_wx_app = wx.App.Get()` across all Connection test files.

## Async Save & Connect contract

`on_save_and_connect(...)` returns:

- **True**: save succeeded, canonical saved profile was selected, connection attempt was successfully started (worker thread launched).
- **False**: save failed, canonical profile could not be selected, or connection could not be started synchronously.

A later worker/network failure does **not** retroactively change the callback return value. Worker failure is represented by:
- `controller.state == "failed"`
- Visible status text shows failure
- Controls are restored by the production `done()` callback

## Real wx event chains exercised (Wave 71.3)

1. **Production Save & Connect (blank-name)**: Real Add button → real WxConnectionDialog (ShowModal subclassed for non-blocking) → real `btn_save_connect` EVT_BUTTON → real `_save_and_connect_clicked()` → real production `on_save_and_connect` → real `save_profile()` → canonical `alice@login.cluster.edu` → real `connect_selected()` → fake backend → Connected.
2. **Async failure**: Save & Connect → save succeeds → `on_save_and_connect` returns True → worker starts → fake backend raises → controller.failed → profile persists → buttons restored.
3. **Master-password wx prompt (no cache)**: Saved master-encrypted profile → Connect Selected real wx button → real `resolve_password_for_connect` → real `_master_ask_factory` → wx.Dialog mocked (ShowModal=ID_OK, TextCtrl=master123) → real `decrypt_with_master` → transient password → Connected. Prompt invoked exactly once.
4. **Master-password cancel (no cache)**: Same chain but wx.Dialog returns Cancel → `master_cancelled` → no SSH, buttons restored.
5. **Test Cluster real button**: Saved master-encrypted profile → edit dialog → real `btn_test_cluster` EVT_BUTTON → real `_test_cluster()` → real credential resolver → wx.Dialog mocked → real decrypt → fake self-test → storage unchanged.
6. **Test Cluster cancel**: Same chain but wx.Dialog returns Cancel → no self-test, button re-enabled, storage unchanged.

## Security evidence

- Saved `password` always cleared; only secure reference types survive save.
- `resolve_password_for_connect` resolution order: typed → keychain → DPAPI → master-encrypted (wx prompt) → "".
- MFA responses transient, not logged. No secret appears in `MessageBox` or logs.
- Blank-name produces canonical `username@host` from persistence service.
- Wrong master never starts SSH; no empty-password fallback; secret never in error messages.
- Cancel never starts SSH; no persisted profile mutation.
- Test Cluster never mutates storage.
- Master password not persisted when Remember checkbox is false.
- No master password logged.

## Tests actually run (against committed HEAD `bd7dc118`)

### Full Connection suite
```
tests/test_wx_connection.py + tests/test_wx_connection_profiles.py
+ tests/test_wx_connection_hardening.py + tests/test_wx_connection_71_2.py
+ tests/test_wx_connection_71_3.py
Result: 71 passed in 23.26s (re-verified against committed HEAD: 71 passed in 40.83s)
```

### Broader regression
```
tests/test_optional_ssh_credentials.py + test_provider_capabilities.py + test_plugin_v2.py
+ test_quota_monitor.py + test_quota_runtime.py + test_log_redaction.py + test_cluster_self_test.py
Result: 33 passed, 9 subtests passed in 1.79s
```

### Ruff
```
python -m ruff check src/hpc_gui/wx_connection.py src/hpc_gui/wx_connection_dialog.py
  src/hpc_gui/services/connection_profile_service.py tests/test_wx_connection.py
  tests/test_wx_connection_profiles.py tests/test_wx_connection_hardening.py
  tests/test_wx_connection_71_2.py tests/test_wx_connection_71_3.py
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
| GUI-CONN-001 | PARTIAL | Headless wx event chains + production Save & Connect + async contract proven; no desktop screenshot |
| GUI-CONN-002 | PARTIAL | Real wx prompt path + real decrypt + cancel/wrong paths proven; no live desktop prompt capture |
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
