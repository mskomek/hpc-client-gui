# Wave 71 wx Connection execution evidence

This record reports only checks actually run against the repository. It does
not treat static controls or service-only tests as visual parity evidence.

## Repository state

- Branch: `develop`
- Expected starting HEAD: `a8bcabea83ff0e5e5dcaf133dfc79ded106191bf`
- Actual starting HEAD: `bda842366b72e1752fadd2b764261fb101aa00fa`
- Implementation commit: `8b29cd8fb28c8e1066dbd986b5923d7806ad54b8`
- Runtime contract: Qt remains the production runtime; `DEFAULT_GUI_RUNTIME` remains `qt`.
- PySide6/shiboken6 were not removed. `.tmp/` was not touched.
- Pre-existing untracked files were preserved: `.integration-recovery/`, `audit.zip`, `waves.zip`.

## Root cause

At the requested expected revision, `wx_connection.py` disabled Add when no
`add_connection` callback was supplied and routed normal creation through
that callback. The wx shell did not supply one. The fix makes profile creation
owned by the Connection surface and opens the wx-native editor directly.

## Real wx event chains exercised

The focused wx tests exercised real wx event dispatch for Add enabled/Add
dialog, Delete confirmation/cancel/confirm, selection and action states, and
host-key dialog mapping. The profile/security/provider tests exercised the
shared persistence and connection adapters with temporary storage and fake
backends. No real HPC connection or cluster was used.

## Security evidence

- Saved `password` is cleared; keychain/DPAPI/Fernet schemes remain mutually exclusive.
- Existing secure material survives unrelated edits; disabling Save Password removes it; rotated keychain references are cleaned up.
- Saved secrets are not populated into the edit field.
- MFA responses are transient and prompt echo metadata is preserved.
- No password, MFA response, or master password is logged by the wx path.

## Parity assessment

The status is intentionally `PARTIAL`: the headless wx event path and shared
service result are tested, but no desktop screenshots or human keyboard/
screen-reader audit were available.

| ID | Status | Evidence |
|---|---|---|
| GUI-CONN-001 | PARTIAL | `test_wx_connection.py` and `test_wx_connection_profiles.py`: owned CRUD, refresh, selection, double-click/context actions, controller states, and fake connection results. |
| GUI-CONN-002 | PARTIAL | Secure secret lifecycle, MFA, host-key decisions, jump host, keepalive, timeout, X11 flag, transfer setting, local directory, and `SSHConnInfo` mapping tests. |
| GUI-CONN-003 | PARTIAL | Builtin/plugin/user declarative template sources, provenance preservation, and provider-required project/account tests. |
| GUI-CONN-004 | PARTIAL | Fail-closed quota states, nested provider-template lookup, and no-command-on-ineligible tests. |
| GUI-I18N-001 impact | PARTIAL | Connection keys exist in EN/TR and wx refresh callbacks are wired; full desktop language-switch capture is unavailable. |
| GUI-A11Y-001 impact | PARTIAL | Visible labels, named primary actions, keyboard-equivalent buttons, focus-on-error, and textual status are tested; no human screen-reader audit. |
| GUI-VISUAL-001 impact | PARTIAL | Scrollable editor, fixed action row, growable sizers, wrapping, and size hints are implemented; no 100/150/200% screenshot set. |

## Tests actually run

The final implementation test run reported:

```text
python -m pytest -q tests/test_wx_connection.py tests/test_wx_connection_profiles.py tests/test_connection_profile_service.py tests/test_profile_patch_preservation.py tests/test_profile_transfer_settings.py tests/test_provider_capabilities.py tests/test_plugin_v2.py tests/test_quota_monitor.py tests/test_quota_runtime.py tests/test_log_redaction.py tests/test_cluster_self_test.py tests/test_wx_i18n.py tests/test_wx_a11y.py
86 passed
```

The focused provider/security/regression run reported:

```text
python -m pytest -q tests/test_profile_duplicate.py tests/test_profile_exchange.py tests/test_profile_identity.py tests/test_profile_patch_preservation.py tests/test_profile_storage_areas.py tests/test_profile_transfer_settings.py tests/test_optional_ssh_credentials.py tests/test_provider_capabilities.py tests/test_plugin_v2.py tests/test_quota_monitor.py tests/test_quota_runtime.py tests/test_linux_x11.py tests/test_macos_x11.py tests/test_log_redaction.py tests/test_cluster_self_test.py tests/test_cluster_self_test_dialog.py tests/test_wx_i18n.py tests/test_wx_a11y.py
76 passed, 4 skipped, 9 subtests passed
```

`python scripts/check_i18n.py` was also run. It remains non-zero because of
pre-existing unrelated missing references in wx splash/updater code and one
pre-existing hardcoded About label; no new connection keys were reported as
missing after the Wave changes.

`tests/test_wx_layout_resize.py` was attempted but is not a passing result:
its current shell contract expects removed toolbar controls (`version`,
`update`, `plugins`, `send_logs`, `settings`, `help`, `language_button`) in
`_wx_shell_controls`. That contract is outside this Connection change and is
unchanged here. A later full resize sweep did not complete in the headless
runner, so it is not counted as evidence.

## Manual wx evidence and limitations

The environment can instantiate wx under pytest, and the tests above use real
`wx.App`/window/event objects. Computer Use discovery found no targetable
native wx application window (`apps: []`), so the requested human desktop
check could not be performed. No screenshots were captured or fabricated.

Unverified: interactive desktop Add/Edit/Duplicate/Delete walkthrough,
real fake-backend Save & Connect display, 150%/200% DPI, and keyboard-only or
screen-reader operation. Those require a targetable desktop wx application.
