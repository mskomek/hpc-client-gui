# Wave 71 / 71.1 / 71.2 wx Connection execution evidence

This record reports only checks actually run against the repository. It does
not treat static controls or service-only tests as visual parity evidence.

## Repository state

- Branch: `develop`
- Expected starting HEAD (Wave 71.1 audit): `da44f6394a4c2cbd82a86f626865ea51b940cf9e`
- Actual starting HEAD: `e2d8cdbb86acdffbeda0dac01384eb7b842fc766`
- Wave 71.1 implementation commits: `28aa317`, `a1728aa`, `e1fefab`, `5ca4b80`, `44734c5`
- Wave 71.2 tested HEAD: `e2d8cdbb86acdffbeda0dac01384eb7b842fc766`
- Runtime contract: Qt remains the production runtime; `DEFAULT_GUI_RUNTIME` remains `qt`.
- PySide6/shiboken6 were not removed. `.tmp/` was not touched.
- Pre-existing untracked files were preserved: `.integration-recovery/`, `audit.zip`, `waves.zip`.

## Root causes fixed (Wave 71.1)

- **Saved master-password connection defect**: `ssh_info_from_profile` used `decrypt_profile_password(allow_prompt=False)` and never prompted for the master password. Fixed by using the shared `resolve_password_for_connect` on the GUI thread.
- **Test Cluster saved-credential defect**: `_test_cluster` called `_collect_profile()` which had already popped secret fields. Fixed by building a resolve profile with original stored secret fields.
- **wx password dialog defect**: MFA/edit-auth used wrong dialog type; replaced with `wx.PasswordEntryDialog` for `echo=False`.
- **Weak Add test**: Tautological assertion replaced with strict constructor/show/destroy count.
- **Fake action-state test**: Replaced with real Connect button events against a blocking fake connector.
- **Save & Connect evidence gap**: Added full wx event chain from Add click through Save & Connect.

## Root causes fixed (Wave 71.2)

- **Blank-name Save & Connect bug**: `_handle_save()` now returns the authoritative saved profile dict. `on_save_and_connect()` uses `saved["name"]` from the persistence service instead of recalculating `collected["name"] or collected["host"]`. This prevents `alice@login.cluster.edu` from being stored while `login.cluster.edu` is used for refresh/selection.
- **`_handle_save()` return type changed from `bool` to `dict | None`**: Returns the authoritative saved profile dict on success, `None` on failure. Callers use the canonical name.
- **Tautological assertion removed**: `assert result is True or result is False` replaced with `assert result is False` with a deterministic contract for connect-after-save failure.
- **Ruff violations cleaned**: Unused imports (`normalize_file_manager_settings`, `normalize_jump_host_settings`, `coerce_profile_transfer_parallelism`, `normalize_system_settings`, `threading`, `unittest`, `decrypt_profile_password`, `save_profile`, `HostKeyInfo`) and unused variables (`result`, `save_tmpl_row`, `wx`, `pos`, `orig_factory`, `saved_profiles`, `orig_pwd`, `orig_txt`, `answers2`) removed.
- **CI develop trigger removed**: `develop` removed from `push` and `pull_request` triggers in `.github/workflows/cli.yml`.
- **Parity source-of-truth synchronized**: `V2_PARITY_STATUS.md` now matches `parity_matrix.py` (GUI-CONN-001-004 remain PARTIAL; GUI-I18N-001 and GUI-A11Y-001 corrected to PARTIAL).
- **pyproject.toml Ruff config**: Added `F841` to test file ignores for wx.App initialization side-effect assignments.

## Real wx event chains exercised (Wave 71.2)

1. **Blank-name Save & Connect**: Real `WxConnectionDialog` button → `on_save_and_connect` → shared `save_profile` → canonical `alice@login.cluster.edu` name → list refresh → `connect_selected` → connected.
2. **Real WxConnectionDialog button event**: Real `btn_save_connect` wx.EVT_BUTTON → `_save_and_connect_clicked()` → panel `on_save_and_connect` callback → shared save service → list refresh → canonical profile.
3. **Master-password real wx chain**: Saved master-encrypted profile → DPAPI cache seeded → `connect_selected` wx.EVT_BUTTON → real `resolve_password_for_connect` → real `decrypt_with_master("master123", ...)` → transient password → connected.
4. **Master password cancel**: Saved master-encrypted profile → wx.EVT_BUTTON → `resolve_password_for_connect` → `ask_master` returns None → `RuntimeError("master_cancelled")` → no SSH, buttons restored.
5. **Wrong master password**: Saved master-encrypted profile → wx.EVT_BUTTON → `resolve_password_for_connect` → `ask_master` returns "wrong-master" → real `decrypt_with_master("wrong-master", ...)` fails → `RuntimeError("master_wrong")` → status failed, no secret exposed, buttons restored.
6. **Test Cluster master-password chain**: Saved master-encrypted profile → edit dialog → Test Cluster button → real `resolve_password_for_connect` → DPAPI cache seeded → real `decrypt_with_master` → transient credential → fake cluster self-test → storage unchanged.
7. **Typed password precedence**: Stored encrypted secret + typed password → typed wins → `resolve_password_for_connect` returns typed, stored secret not mutated.

## Security evidence

- Saved `password` always cleared; only secure reference types survive save.
- `resolve_password_for_connect` resolution order: typed -> keychain -> DPAPI -> master-encrypted (wx prompt) -> "".
- MFA responses transient, not logged. No secret appears in `MessageBox` or logs.
- Blank-name produces canonical `username@host` from persistence service, not wx recalculated fallback.
- Wrong master never starts SSH; no empty-password fallback; secret never in error messages.
- Cancel never starts SSH; no persisted profile mutation.
- Test Cluster never mutates storage.

## Tests actually run

### Focused Connection suite
```
tests/test_wx_connection.py + tests/test_wx_connection_profiles.py + tests/test_wx_connection_71_2.py
Result: 43 passed in 11.32s
```

### Hardening suite
```
tests/test_wx_connection_hardening.py
Result: 20 passed in 8.59s
```

### Broader regression
```
tests/test_optional_ssh_credentials.py + test_provider_capabilities.py + test_plugin_v2.py
+ test_quota_monitor.py + test_quota_runtime.py + test_log_redaction.py + test_cluster_self_test.py
Result: 33 passed, 9 subtests passed in 1.40s
```

### Ruff
```
python -m ruff check src/hpc_gui/wx_connection.py src/hpc_gui/wx_connection_dialog.py
  src/hpc_gui/services/connection_profile_service.py tests/test_wx_connection.py
  tests/test_wx_connection_profiles.py tests/test_wx_connection_hardening.py
  tests/test_wx_connection_71_2.py
Result: All checks passed
```

## Parity assessment

| ID | Status | Evidence |
|---|---|---|
| GUI-CONN-001 | PARTIAL | Headless wx event chains only; no desktop screenshot |
| GUI-CONN-002 | PARTIAL | Secure secret lifecycle via fakes, real decrypt chain proven; no live desktop prompt capture |
| GUI-CONN-003 | PARTIAL | Templates provenance; no desktop capture |
| GUI-CONN-004 | PARTIAL | Fail-closed quota, nested provider lookup; no real transport |
| GUI-I18N-001 | PARTIAL | New EN/TR keys verified; no visual language-switch |
| GUI-A11Y-001 | PARTIAL | Named actions, visible labels; no screen-reader audit |
| GUI-VISUAL-001 | PARTIAL | Scrollable editor, sizers; no 100/150/200% screenshots |

## Manual wx evidence and limitations

- No desktop wx session available for manual walkthrough.
- All `wx.MessageDialog`/`MessageBox`/`PasswordEntryDialog`/`TextEntryDialog`/`wx.Dialog` (master prompt) are auto-mocked via `tests/conftest.py` (`_no_wx_modal_popups`) or test-level mocking.
- No DPI screenshots, no screen-reader audit, no visual language-switch capture.
- All parity statuses remain PARTIAL for lack of manual desktop evidence.
