# Wave 71 / 71.1 wx Connection execution evidence

This record reports only checks actually run against the repository. It does
not treat static controls or service-only tests as visual parity evidence.

## Repository state

- Branch: `develop`
- Expected starting HEAD (Wave 71.1 audit): `da44f6394a4c2cbd82a86f626865ea51b940cf9e`
- Actual starting HEAD: `da44f6394a4c2cbd82a86f626865ea51b940cf9e`
- Wave 71.1 implementation commits: `28aa317`, `a1728aa`, `e1fefab` (hardening, host-key popup fix, global wx dialog mock)
- Evidence/test HEAD: `e1fefab3a61e35018db559400c5c340af201bba4`
- Runtime contract: Qt remains the production runtime; `DEFAULT_GUI_RUNTIME` remains `qt`.
- PySide6/shiboken6 were not removed. `.tmp/` was not touched.
- Pre-existing untracked files were preserved: `.integration-recovery/`, `audit.zip`, `waves.zip`.
- Worktree after hardening: no new untracked files except the intentional `tests/test_wx_connection_hardening.py`.

## Root causes fixed (Wave 71.1)

- **Saved master-password connection defect**: `ssh_info_from_profile` used `decrypt_profile_password(allow_prompt=False)` and never prompted for the master password, so profiles with `password_enc`/`password_salt` always raised `saved_password_unavailable` instead of unlocking via the wx master prompt. Fixed by using the shared `resolve_password_for_connect` on the GUI thread with a wx-native `ask_master` callback, keeping the plaintext only in transient memory.
- **Test Cluster saved-credential defect**: `WxConnectionDialog._test_cluster` called `_collect_profile()` which had already popped all secret fields, so editing an existing saved profile could only test with a freshly typed password. Fixed to resolve via `original persisted profile + typed password + shared resolver` without mutating storage and without copying the secret into the visible field.
- **wx password dialog defect**: MFA and edit-auth used `wx.TextEntryDialog(..., style=wx.TE_PASSWORD)`. Replaced with `wx.PasswordEntryDialog` for `echo=False` (MFA) and for edit-auth; `echo=True` now correctly uses `wx.TextEntryDialog`. Explicit `echo` wins over heuristic fallback.
- **Weak Add test**: `assert called.get("opened") is True or True` was always true. Replaced with strict `assert ctor==1 and show==1 and destroy==1` and verified the real `wx.EVT_BUTTON` event is what opened the dialog.
- **Fake action-state test**: the old test did `button.Disable(); button.Enable(True); assert IsEnabled()` and therefore proved nothing about production. Replaced with real `Connect` button events against a blocking fake connector that asserts `Connect/Edit/Duplicate/Delete/Add` are disabled and status is `Connecting` while the worker is blocked, then verifies restore on success and on synthetic failure without any test-side `Enable` calls.
- **Save & Connect evidence gap**: previously only `dlg._save_and_connect_clicked()` with a mocked callback was tested. Added a full wx event chain: `build Connection panel -> Add click -> Fake WxConnectionDialog -> Save & Connect -> shared save service -> profile written -> list refreshed -> new profile selected -> Connect Selected -> fake backend -> controller Connected -> status Connected`, plus failure variants (save failure prevents connect; connect failure after save keeps profile and restores UI).

## Real wx event chains exercised

- `Add click -> WxConnectionDialog ctor 1, ShowModal 1, Destroy 1`
- `Connect click -> blocking fake -> status Connecting, all conflicting buttons disabled -> release -> status Connected, Add/Edit restored, on_connected 1`
- `Connect click -> failing fake -> status Connection failed, buttons restored, no secret in error, no stuck disabled`
- `Save & Connect -> persisted profile -> refresh -> selected -> connection -> Connected` (and failure variants)
- `Delete -> Cancel keeps profile, Confirm deletes, Active-connected delete blocked`
- `Selection -> detail and button states, double-click and context menu retarget`
- `Host-key dialog mapping: YES->save, NO->once, CANCEL->reject` (mocked `wx.MessageDialog`)
- `MFA: echo False -> PasswordEntryDialog, echo True -> TextEntryDialog, order preserved, cancel aborts, no log`

All use real `wx.App`/`wx.Frame`/`wx.Panel`/`wx.ListBox`/`wx.Button` objects and `ProcessEvent(wx.EVT_BUTTON)` / `ProcessEvent(wx.EVT_LISTBOX)` where required. No real HPC cluster was used.

Popup handling: `tests/conftest.py` now auto-mocks `wx.MessageDialog`, `wx.MessageBox`, `wx.PasswordEntryDialog`, `wx.TextEntryDialog` to a non-blocking fake (returning `ID_CANCEL`/`ID_OK` by default). Tests that need a specific answer patch the dialog themselves with `mock.patch("wx.MessageDialog")` and set `ShowModal` to `ID_YES`/`ID_NO`/`ID_CANCEL`. This prevents any test from hanging waiting for a human to click Yes/No/Cancel. Previous manual clicks for “Verify server identity” (host-key) were due to an unmocked `decide_host_key` call; that path is now fully mocked (see `test_host_key_mapping` fix – 0.56s vs 15s before, 257s in the full suite before).

## Security evidence

- Saved `password` is always cleared; only one of `password_keychain_ref` / `password_dpapi` / `password_enc`+`salt` survives a save.
- Existing secure material survives unrelated edits; disabling Save Password removes it; rotated keychain refs are cleaned up.
- Saved secrets are never populated into the edit field (`password_ctrl.GetValue() == ""` for encrypted profiles).
- `resolve_password_for_connect` order: `typed -> keychain -> DPAPI -> master-encrypted (wx prompt) -> ""`. Plaintext kept only in transient `transient["password"]` and `SSHConnInfo.password`, never written back, wiped after `done`.
- Wrong master -> `master_wrong` -> `login.err_master_wrong` (non-secret, `master_password` never logged). Cancel -> `master_cancelled` -> clean abort, no generic failure. Saved unavailable -> `saved_password_unavailable` -> translated, no fallback to empty password.
- MFA responses transient, not retained on model, not logged (caplog check), echo handling respects explicit `echo` over heuristic.
- No secret appears in `MessageBox` or logs (redaction check).

## Parity assessment

Functional Connection parity is now proven headlessly; visual/a11y still requires a human desktop.

| ID | Status | Evidence |
|---|---|---|
| GUI-CONN-001 | PARTIAL | `test_wx_connection.py` + `test_wx_connection_profiles.py` (fixed Add strict, real action-state blocking, Save & Connect event chain) + `test_wx_connection_hardening.py` (Save & Connect chain, failure variants, second-attempt, selected vs active, delete-active, controller transitions). Headless wx event chains only; no desktop screenshot. |
| GUI-CONN-002 | PARTIAL | Secure secret lifecycle plus new matrices: `test_keychain_connect_resolves`, `test_dpapi_connect_resolves`, `test_master_encrypted_connect_with_prompt_and_cancel_and_wrong`, `test_test_cluster_resolves_keychain_dpapi_master_and_does_not_mutate`, `test_typed_password_precedence`, `test_saved_password_unavailable_error`, MFA echo, host-key mapping, `SSHConnInfo` advanced mapping. All via mocks, no live cluster, no real OS keychain. |
| GUI-CONN-003 | PARTIAL | Builtin/plugin/user templates, provenance, required project/account (existing) + `test_provider_template_no_generic_branch` – no desktop capture. |
| GUI-CONN-004 | PARTIAL | Fail-closed quota, nested provider lookup (existing) + `test_quota_fail_closed` – no real transport. |
| GUI-I18N-001 impact | PARTIAL | New keys `connection.auth_cancelled`, `connection.test_credential_error`, `connection.master_unlock_error`, `connection.saved_credential_unavailable`, `connection.credential_unlock_prompt` added to EN/TR and verified; `scripts/check_i18n.py` still fails only on pre-existing unrelated missing references (125, none are new Connection keys). |
| GUI-A11Y-001 impact | PARTIAL | Named primary actions, visible labels, focus-on-error, textual statuses, keyboard-bound buttons (existing) – no screen-reader audit. |
| GUI-VISUAL-001 impact | PARTIAL | Scrollable editor, fixed action row, sizers, wrapping (existing) – no 100/150/200% screenshots. |

## Tests actually run

Python 3.12.4, wxPython 4.3.1 msw (phoenix) wxWidgets 3.3.3, win32.

Focused Connection (Wave 71.1) – the set required by the audit:

```text
python -m pytest -q tests/test_wx_connection.py tests/test_wx_connection_profiles.py tests/test_connection_profile_service.py tests/test_optional_ssh_credentials.py tests/test_profile_patch_preservation.py tests/test_profile_transfer_settings.py tests/test_profile_duplicate.py tests/test_provider_capabilities.py tests/test_plugin_v2.py tests/test_quota_monitor.py tests/test_quota_runtime.py tests/test_log_redaction.py tests/test_cluster_self_test.py tests/test_wx_i18n.py tests/test_wx_a11y.py
99 passed, 9 subtests passed in 11-15s
```

Hardening-only (new):

```text
python -m pytest -q tests/test_wx_connection_hardening.py
20 passed in 2-3s
```

Combined 64 (original 8+28+8 plus 20 hardening):

```text
python -m pytest -q tests/test_wx_connection.py tests/test_wx_connection_profiles.py tests/test_connection_profile_service.py tests/test_wx_connection_hardening.py
64 passed in 11-12s
```

Full 64 with global wx dialog mock (no manual clicks required):

```text
python -m pytest -q tests/test_wx_connection.py tests/test_wx_connection_profiles.py tests/test_connection_profile_service.py tests/test_wx_connection_hardening.py -v
64 passed in 11.62s (previously 91.88s with host-key popup requiring manual Yes/No/Cancel; now 0.56s for that test)
```

Regression slices:

```text
python -m pytest -q tests/test_linux_x11.py tests/test_macos_x11.py tests/test_profile_identity.py tests/test_profile_storage_areas.py tests/test_profile_exchange.py tests/test_cluster_self_test_dialog.py
21 passed in 2.26s
```

`python scripts/check_i18n.py` – still FAILED only on pre-existing unrelated missing references (125, e.g. `splash.*`, `updates.*`); no new Connection key is missing.

The full repository run (`python -m pytest -q`) was not completed headlessly in the time available (300s timeout at ~75-81% with ~5 failures, same pre-existing stale expectations as Wave 71). The focused and hardening suites are the honest evidence; no full-suite success is claimed.

## Manual wx evidence and limitations

The environment can instantiate wx under pytest (`wx.App`/`wx.Frame`/`wx.Panel`/`wx.ListBox`/`wx.Button` with `ProcessEvent`). `tests/conftest.py` now auto-mocks `wx.MessageDialog`/`wx.MessageBox`/`wx.PasswordEntryDialog`/`wx.TextEntryDialog` so no test hangs waiting for a human to click Yes/No/Cancel – previous manual “Verify server identity” clicks are no longer required. Computer Use still found no targetable native wx application window (`apps: []`), so no human desktop walkthrough, DPI screenshots, or screen-reader audit were performed. Unverified: interactive desktop Add/Edit/Duplicate/Delete, real fake-backend Save & Connect display, 150%/200% DPI, keyboard-only operation.

Credential schemes proven via mocks (no real OS keychain, no real cluster): keychain, DPAPI/OS-protected, master-encrypted (correct, cancel, wrong), typed override, unavailable, MFA echo, host-key mapping. No plaintext secret was persisted and no secret appeared in logs.
