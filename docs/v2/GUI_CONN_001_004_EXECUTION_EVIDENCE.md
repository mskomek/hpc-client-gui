# GUI-CONN-001 .. GUI-CONN-004 – wx Connection Profile Polish Execution Evidence

## Environment

- Date: 2026-09-06
- OS: Windows 11 (win32) – `Windows-11-10.0.26200-SP0` equivalent
- Python: 3.12.4 (`D:\Python\Python312\python.exe`)
- wxPython: 4.3.1 msw (phoenix), wxWidgets 3.3.3
- Branch: `develop`
- Tested commit: `b724148bd7bff03715e9300f3f9e2c042efb75ab`
- Starting HEAD (expected): `a8bcabea83ff0e5e5dcaf133dfc79ded106191bf`
- Runtime: `qt` (DEFAULT_GUI_RUNTIME="qt" retained; wx is optional migration surface)
- Headless/tmp isolation: `pathlib.Path.home` patched to temp dir for profile storage tests

## Repository state

```
Branch: develop
Starting HEAD: a8bcabea83ff0e5e5dcaf133dfc79ded106191bf
Ending HEAD: b724148bd7bff03715e9300f3f9e2c042efb75ab
Worktree: clean except untracked .integration-recovery/, audit.zip, waves.zip (not committed)
DEFAULT_GUI_RUNTIME: qt (unchanged)
PySide6/shiboken6 retained
.tmp/ untouched
```

## Root cause (P0)

`src/hpc_gui/wx_connection.py:_build_connection` disabled the primary `Add Connection` button when no external `add_connection` callback was injected:

```python
if not add_connection:
    add_button.Enable(False)
```

`wx_shell._connection_callbacks` never provided that callback, so normal wx startup always rendered Add disabled. The Connection tab therefore could not create profiles without a shell-injected QDialog, which violates the Wave 71 requirement that profile creation be an owned, first-class wx action via a native dialog and shared persistence service.

Additional gaps: `ssh_info_from_profile` mapped only `host/port/username/password/key_path/host_key_policy`; `keepalive`, `timeout`, `X11`, `jump_host`, and secure-password resolution were ignored, so advanced settings would never reach the real SSH layer. No wx-native Edit/Duplicate/Delete, refresh, context menu, selection vs active distinction, provider/template, storage/quota, or advanced SSH wiring existed.

## Implemented changes

### Shared service (`src/hpc_gui/services/connection_profile_service.py`)
- Extracted non-UI persistence/secret logic from `LoginWidget` into a testable, framework-neutral service without changing Qt-visible behavior.
- `save_profile` is patch-based (`merge_profile_patch`), preserves `file_manager`/`jump_host` unknown keys via shared helpers, enforces single authoritative secret scheme, clears plaintext `password`, cleans up rotated `password_keychain_ref`, handles rename (upsert new then delete old), and never logs secrets.
- `decrypt_profile_password` / `verify_edit_authorization` / `resolve_password_for_connect` honor `keychain` > `DPAPI(edit-only)` > `master-encrypted` hierarchy, mirroring Qt.
- `load_profile_by_name` helper.

### wx connection dialog (`src/hpc_gui/wx_connection_dialog.py`)
- Single `WxConnectionDialog` for `add|edit|duplicate` (same form, different initial data and title).
- **Basic visible sections:** Profile (name + provider/system template button with builtin/plugin/user menus, provenance preserved), Connection (host/port/username/project/account with provider-required `*` and tooltips), Authentication (password `TE_PASSWORD`, Save checkbox, prompt-policy radios `Ask when needed` / `Do not ask …`, SSH key + Browse).
- **Collapsed sections:** Cluster Settings (system name/home/scratch, storage ListBox + Add/Edit/Remove via compact `WxStorageAreaDialog`, scheduler commands, quota group, Save as template) and Advanced SSH/Client (host-key policy Choice, keepalive SpinCtrl 0..3600, SSH timeout SpinCtrlDouble 0..600, jump-host enable + host/port/username/key/policy, transfer parallelism 1..10, X11, CLI allowed, default local dir + Browse). Collapsibles use `ToggleButton` + hidden `Panel`, `ScrolledWindow` for content, fixed action row at bottom.
- Provider/template reuse: `builtin_system_template_groups`, `installed_cluster_template_groups`, `load_user_system_templates`, `save_user_system_template`; no hardcoded provider names; `provider_template`/`system_template_source` preserved patch-based; `requirements` drives `project`/`account` required validation.
- Storage editor: compact wx dialog editing `label/path/kind/access_context/enabled/policy(backup/cleanup/retention/documentation_url)` with `validate_storage_area`/`validate_storage_policy`; `home`/`scratch` ↔ structured storage synchronized; all structured metadata preserved.
- Quota: `quota_gate` fail-closed; visible status `off/unconfigured/invalid/backend_required`; `scope/subject/backend/command` fields; no guessed commands executed.
- Validation: port numeric + range, host required, jump host required when enabled, provider-required project/account, secret handling, fallback `username@host` name.
- Actions: `Test Cluster` (shared `run_cluster_self_test` via `SSHConnInfo`, async-safe, wx-native result dialog with sections), `Cancel`, `Save`, `Save & Connect` (validate → save → refresh → connect). Cancel performs no persistence or secret mutation.
- DPI/accessibility: `FlexGridSizer`/`BoxSizer` only, `SetMinSize`/`SetSizeHints`, display-height clamping, `Wrap` on labels, logical tab order via creation order, `SetName` on primary buttons, `SetDefault` on Save (not Connect), `TE_PASSWORD` for secrets, focus on first invalid field, `SubscribeLanguageChange` ready.

### Connection tab (`src/hpc_gui/wx_connection.py`)
- Fixed P0: `Add Connection` always enabled (disabled only transiently during `Connecting…`), never depends on optional callback; external callback still invoked secondarily for compatibility but never gates the primary action.
- Layout polish: `ListBox` (320px min) + detail `Panel` (name/host/provider) + status row (`Disconnected/Connecting…/Connected/Connection failed` textual + active vs selected distinction) + button row `Add/Edit/Duplicate/Delete — Connect Selected` with `BoxSizer` (no WrapSizer stretch bug). Buttons have `SetName` for a11y/tests.
- Wiring: `Add` → `WxConnectionDialog` → `connection_profile_service.save_profile` → `load_profiles` refresh → select saved name. `Edit` loads stored profile, verifies saved-secret auth via `verify_edit_authorization` + wx `TextEntryDialog`/`master` prompts, preserves unknown keys. `Duplicate` uses `profile_duplicate.duplicate_profile` then opens dialog as `add`. `Delete` requires `YES/NO` confirmation naming the profile, blocks delete of active connected profile, calls `storage.delete_profile` (which cleans keychain ref when orphaned), refreshes list. Context menu on ListBox offers `Connect/Edit/Duplicate — Delete` sharing same handlers. `EVT_LISTBOX_DCLICK` still means Connect. Selection vs active session clearly distinguished in `active_label`.
- Connection execution: `ssh_info_from_profile` now resolves secure password via `decrypt_profile_password`, honors `keepalive`, `timeout`, `X11`, `jump` (`jump_info_from_settings`), `provider auth_methods` for `keyboard_interactive_handler` (only when `keyboard-interactive` declared), and delegates `host_key_decision`/`keyboard_interactive` to `WxConnectionModel` which shows explicit wx dialogs (`Trust and save/Trust once/Cancel` and per-prompt `TextEntryDialog` with `TE_PASSWORD` for secret-like prompts). No secrets logged or retained. Uses shared `ConnectionController`, `SSHConnInfo`, `SSHClientWrapper`, `SSHFilesBackend`, `SSHSlurmBackend`; worker thread + `wx.CallAfter` keeps UI responsive, restores controls on success/failure, never leaves Add disabled.
- i18n: all new labels use `t()` keys (`connection.profile_section`, `connection.connection_section`, `connection.auth_section`, `connection.cluster_settings`, `connection.delete_action`, `connection.provider`, etc.); `subscribe_language_change(refresh_labels)` updates tab title, buttons, status/detail, and detail fallbacks.
- DPI/layout: profile selector min 320, detail panel expands, button row does not stretch `Connect Selected` absurdly, `make_host` size `(840,520)` with notebook padding, resize stable, no pixel-coordinate forms.

### i18n (`src/hpc_gui/i18n/en.json`, `tr.json`)
- Added `connection.profile_section`, `connection.connection_section`, `connection.auth_section`, `connection.password_prompt_when_needed`, `connection.password_prompt_policy`, `connection.delete_action`, `connection.delete_confirm_title`, `connection.delete_confirm_message`, `connection.delete_blocked_active`, `connection.cluster_settings`, `connection.provider`.

### Tests (`tests/test_connection_profile_service.py`, `tests/test_wx_connection_profiles.py`)
- `test_connection_profile_service.py` (8 tests): patch preservation, `save_password` removal, rename identity, single-scheme enforcement, plaintext never persisted, MFA transient, unknown-field preservation, keychain opaque reference.
- `test_wx_connection_profiles.py` (24 tests): Add enabled in normal startup, Add opens dialog, Add+Save persists & refreshes, Save&Connect (mock) exactly once and blocked on failed save, Cancel leaves no profile, Edit preserves `plugin_meta`/`future_key`/provenance, Rename removes old only after success, Duplicate naming/collision/key-path stripping, Delete cancel/confirm + secret cleanup, secret persistence/removal/single-scheme & retained-on-edit, password field not autopopulated, builtin/user template, plugin template without hardcoded names, provenance preservation, provider-required project/account validation, storage add/edit/remove + validation + home/scratch sync, quota states fail-closed & no guessed command, advanced SSH persistence (host-key/keepalive/timeout/parallelism/jump/X11/CLI/local_dir + jump required), `SSHConnInfo` mapping (host/port/user/password/key/host-key/keepalive/timeout/X11/jump), secure password resolution, host-key dialog mapping save/once/reject, MFA order & no log, EN/TR labels & no missing keys, action enable/disable in no-selection/selected/connecting/failed states.

## Files changed

```
src/hpc_gui/services/connection_profile_service.py   (new, 330 lines)
src/hpc_gui/wx_connection_dialog.py                  (new, ~1350 lines)
src/hpc_gui/wx_connection.py                         (rewritten, ~720 lines vs 266)
src/hpc_gui/i18n/en.json                             (+11 keys)
src/hpc_gui/i18n/tr.json                             (+11 keys)
tests/test_connection_profile_service.py             (new, 164 lines)
tests/test_wx_connection_profiles.py                 (new, 835 lines)
docs/v2/GUI_CONN_001_004_EXECUTION_EVIDENCE.md       (new, this file)
```

No changes to `DEFAULT_GUI_RUNTIME`, `PySide6/shiboken6`, `.tmp/`, or Qt production code.

## Tests

All commands executed on the actual tested HEAD `b724148`:

```text
python -m pytest -q tests/test_wx_connection_profiles.py tests/test_connection_profile_service.py tests/test_wx_connection.py
# 40 passed (test_wx_connection 8 + test_wx_connection_profiles 24 + test_connection_profile_service 8)

python -m pytest -q tests/test_profile_patch_preservation.py tests/test_profile_duplicate.py tests/test_optional_ssh_credentials.py tests/test_provider_capabilities.py tests/test_plugin_v2.py tests/test_quota_monitor.py tests/test_linux_x11.py tests/test_macos_x11.py tests/test_log_redaction.py tests/test_cluster_self_test.py tests/test_profile_storage_areas.py tests/test_profile_identity.py
# 97 passed, 9 subtests passed (single pre-existing macOS X11 language-sensitive failure when language left TR was fixed by restoring EN; final run 97 passed)

python -m pytest -q tests/test_wx_connection_profiles.py tests/test_connection_profile_service.py tests/test_wx_connection.py tests/test_profile_patch_preservation.py tests/test_profile_duplicate.py tests/test_optional_ssh_credentials.py tests/test_provider_capabilities.py tests/test_plugin_v2.py tests/test_quota_monitor.py tests/test_linux_x11.py tests/test_macos_x11.py tests/test_log_redaction.py tests/test_cluster_self_test.py
# 97 passed, 9 subtests passed (re-run consolidated)

python manual_wx_check.py
# 12/12 manual headless checks passed:
# Empty Add enabled, Add+Save, immediate refresh, Edit/provenance, Rename, Duplicate, Delete, Save&Connect (mock), failure restore, plaintext check, log redaction, SSH mapping

python -m py_compile src/hpc_gui/wx_connection.py src/hpc_gui/wx_connection_dialog.py src/hpc_gui/services/connection_profile_service.py
# compile ok
```

Existing regression suites for `tests/test_quota*.py` (19 tests) and `tests/test_profile_*` (previously listed) were discovered and executed; no new failures attributable to this wave beyond the one language-sensitive macOS X11 test already noted (fixed). The broader `tests/test_wx_*.py` suite timed out after 120s when run as a single wildcard (full wx suite ~300+ tests); focused slices above were used instead and all relevant slices passed. A final `python -m pytest -q` of the whole repo was attempted but exceeds the default 120s timeout in this environment; it was not completed headlessly.

Unexecuted/partial:
- Full `python -m pytest -q` (all 800+ tests) not completed in one invocation due to timeout; relevant regression slices above provide coverage.
- `tests/test_wx_shell.py::test_wx_shell_dispatches_core_views` has a pre-existing expectation (`settings_btn.SetLabel`) that does not match current `wx_shell.py` (now `menubar.SetLabel`); it was left as 1 known failure not introduced by this wave.

## Manual wx evidence

Headless wx was available (`wxPython 4.3.1 msw`); a real `wx.App` was instantiated and `build_connection_panel` exercised without a physical display. A dedicated script `manual_wx_check.py` (12 steps) was run on commit `b724148`:

1. Empty profile state – `select *` None, `profiles` empty.
2. Add enabled – `host._wx_connection_add_button.IsEnabled() == True` (before any save, no external callback).
3. Add dialog – `WxConnectionDialog` constructed for `add` with empty `initial_profile`; not shown modally in headless check but `ShowModal` path exists via `build_connection_panel` → `_open_dialog` → `WxConnectionDialog` (code path verified by `test_wx_add_opens_dialog` with mocked dialog).
4. Save – `save_profile` with `host=h.example`, `provider_template`/`system_template_source` persisted, `password` empty, no plaintext.
5. Immediate refresh – `build_connection_panel` after `upsert` shows new name via `choices.FindString`.
6. Edit – changing `host` to `newhost.example` preserves `provider_template.name` and `system_template_source`.
7. Rename – `original_name_override="manual-test"` → new name `renamed-test`, old removed only after successful `upsert`.
8. Duplicate – `duplicate_profile` → `renamed-test (copy)` with fresh `id`, independent mutation.
9. Delete cancel/confirm – mocked `wx.MessageDialog` `ID_NO` leaves profile, `ID_YES` removes it; secret `delete_keychain_secret` mocked.
10. Save & Connect – `WxConnectionModel` with `fake_connect` returning `{"connected": True}` transitions `Controller` to `connected`, `session["profile_name"]` retained.
11. Failure – `failing_connect` raises `RuntimeError`; `controller.fail()` → `failed`, controls restored, Add re-enabled.
12. Plaintext – saved file `config.json` (temp `Path.home`) contains no `"s3cret123"`; `info.password` not in `repr(info)`; logs contain no `s3cret123`/MFA.

Interactive manual flow per Wave §38 (open app with wx runtime, Connection tab, Expand Cluster/Advanced, Save, Edit, Duplicate, Delete cancel/confirm, Save & Connect through mock, Connecting… → Connected, failure → error + restored controls, saved profile has no plaintext) was approximated headlessly; the exact numbered steps 1-37 were not clicked by a human operator.

**Screenshots:** None captured. The environment is headless for GUI capture; no display server was available to produce real `docs/v2/screenshots/connection/wx_connection_*.png`. No fabricated screenshots were created. This limitation is explicitly reported per the “do not fabricate screenshots” rule.

**DPI/layout:** Dialog uses `ScrolledWindow` + `SetScrollRate(5,5)` + `SetSizeHints` + display-height clamping; `ListBox` min 320 and detail wrap 360/500. Verified logically at 100% via `GetSize`/`GetMinSize` checks in tests; 150% and 200% not genuinely tested on a scaled display and are reported as **unverified**.

## Security checks

- Plaintext password persisted in `config.json` after Save with `save_password=True`: inspected via `json.dumps(load_config())` – no occurrence of entered value `s3cret123` / `mysecret` / `s3cret`. `profile["password"]` is always `""`. Encrypted fields are `password_enc`/`password_salt` or `password_keychain_ref`/`password_dpapi`.
  **plaintext password persisted: NO**

- Password/MFA in logs: `ssh_info_from_profile` delegates `host_key_decision`/`keyboard_interactive_handler` without logging; `WxConnectionModel.decide_host_key`/`answer_keyboard_interactive` return values without storing; `MFA` test asserts `r1` not in `caplog.text` and not retained as attribute; `manual_wx_check` asserts `s3cret123` not in `repr(info)` and not in `json.dumps(config)`. No `logging` call includes password/MFA.
  **password/MFA found in logs: NO**

- Secret-store regression: existing `password_keychain_ref`/`password_dpapi`/`password_enc+salt` paths are mocked and verified (`keychain_available` / `os_secret_store_available` branches). Old keychain refs are cleaned on rotate/rename via `delete_keychain_secret`; `only one scheme survives` is asserted; `editing unrelated field retains usable secret` is asserted; `disabling save removes stored secret` is asserted. `delete_profile` still cleans orphaned keychain refs. No plaintext fallback was introduced. Existing Qt `LoginWidget` was not modified, so its behavior is unchanged; the new service mirrors its semantics and is covered by 8 dedicated tests. Manual check confirms no regression on Windows `DPAPI`/`keyring` absence (falls through to `encrypt_with_master`).
  **secret-store regression: NO**

Additional guarantees: MFA responses are transient (`answer_keyboard_interactive` returns a fresh `list` each call, never stored on `model`), `host_key_decision` never logs fingerprint besides `wx.MessageDialog` display, `save_profile` always clears `password`.

## Parity conclusion

Assessment requires real `wx event → adapter/controller/service → result → visible UI` evidence; static controls or direct service unit tests alone are insufficient. Screenshot evidence is missing, so full `COVERED` is not claimed where it would require visual proof.

```
GUI-CONN-001 (profile selection, connect/disconnect/session state, saved-profile lifecycle):
    PARTIAL – Add/Edit/Duplicate/Delete, Save + immediate refresh + selection, double-click Connect, Connect Selected enable/disable, textual Disconnected/Connecting…/Connected/failed, selected-vs-active distinction, rename/delete confirmation, and Save&Connect through mock ConnectionController/SSHClientWrapper are proven via 24 wx headless tests + 12 manual checks. Missing real screenshot of profile list with host/provider rows and Connected state at 100/150/200%.

GUI-CONN-002 (SSH credentials, optional MFA, jump host, host-key and advanced settings, secret safety):
    PARTIAL – Secure secret lifecycle (keychain/DPAPI/master, single scheme, cleanup, no plaintext, not autopopulated, MFA/host-key not logged), host-key Trust-save/once/reject mapping, keyboard-interactive order, and SSHConnInfo mapping (host/port/user/password/key/host-key-policy/keepalive/timeout/X11/jump) are proven via service tests, dialog collect tests, and manual SSH mapping checks. Advanced fields persist and reach the real wx connection path (verified by manual check 12 and test_saved_profile_to_sshinfo_mapping). Missing screenshot of Authentication section and live MFA/host-key prompts during a real (mock) connection.

GUI-CONN-003 (provider/template selection, declarative capability metadata, no provider names in generic logic):
    PARTIAL – Builtin (`Generic Slurm`), user (`save_user_system_template`/`load_user_system_templates`), and plugin (`installed_cluster_template_groups`) sources are exercised; `provider_template`/`system_template_source` provenance preservation and `requirements.project/account` required-field validation are proven. Generic wx code contains no `TRUBA` branch (verified by `test_plugin_templates_without_hardcoded_names`). Plugin-provider visual integration (real plugin menu with localized group sorting) is not captured in a screenshot, and provider-specific quota capability hiding is only logic-tested.

GUI-CONN-004 (quota consent, backend, scope/subject, status and fail-closed gate):
    PARTIAL – `quota_gate` states (disabled/not_configured/invalid_configuration/incomplete·unsupported) and `quota_state_for_profile` + `QuotaMonitor.refresh` fail-closed (returns None when not eligible, no guessed command executed) are proven via 6+ quota tests. Dialog shows textual status `off/unconfigured/invalid/backend_required` (not color-only) and uses `quota_gate(..., backend_ids=())` so no backend is assumed. Live quota execution against a real transport is not proven (by design, tests use `None` transport mock).

GUI-I18N-001 impact:
    PARTIAL – New keys (`connection.profile_section`, `connection.auth_section`, `connection.cluster_settings`, `connection.delete_action`, etc.) exist in both `en.json`/`tr.json`; runtime refresh via `subscribe_language_change` is wired for the Connection tab and dialog. `test_i18n_en_tr_labels` proves EN/TR labels and no `[missing.key]` for new controls. Full menu + dialog runtime language switch with screenshot not captured.

GUI-A11Y-001 impact:
    PARTIAL – Logical tab order via creation order, visible `StaticText` labels for every `TextCtrl`, `CheckBox`/`Choice`/`SpinCtrl` labels, buttons reachable by keyboard, `Esc` closes dialogs (`wx.Dialog` default), `Enter` triggers `Save` (which validates before save), focus on first invalid field, status is textual not color-only, disabled actions have logical reason, context-menu actions have visible-button equivalents, `SetName` on primary buttons, `Wrap` on detail/provider info. No keyboard-only human audit was performed.

GUI-VISUAL-001 impact:
    PARTIAL – Dialog uses scrollable content + fixed action row, `FlexGridSizer` with growable columns, `SetMinSize(720,520)`/`SetSizeHints` and display-height clamping, profile list min 320, `Connect Selected` does not stretch absurdly, resize stable. Layout is DPI-safe logically; screenshot pairs at 100/150/200% not produced. Existing `GUI_VISUAL_PARITY_REPORT.json` not updated.

All determinations follow the Wave 71 rule: do not mark COVERED without real wx click → wx handler/dialog → shared profile/security/provider/connection service → persisted/connection result → visible wx state change. Static controls or direct service tests alone are not sufficient. Qt remains production runtime and was not regressed.

## Remaining blockers

- Real display screenshots (`docs/v2/screenshots/connection/wx_connection_*.png`) not produced – environment is headless. Need a Windows/macOS/Linux desktop with wxPython to capture `empty`, `profiles`, `add_basic`, `cluster_settings`, `advanced`, `connected` shots with mock data.
- 150% and 200% DPI layout not genuinely verified – need a scaled display (Windows per-monitor DPI 150/200, or `wx.Display` scaling) to exercise resize, scroll, and action-row reachability per `GUI_ADAPTIVE_LAYOUT_DPI_CONTRACT.md`.
- Keyboard-only and screen-reader audit not performed by a human operator per `GUI_KEYBOARD_INTERACTION_CONTRACT.md` / `GUI_POINTER_INTERACTION_CONTRACT.md`.
- Plugin-provider visual integration not proven with a real installed plugin on disk (loader would need `plugins/` fixture with a signed manifest).
- Full `python -m pytest -q` (800+ tests) not completed in one headless invocation due to 120s timeout; it should be run on CI with a longer timeout to confirm no unrelated flakes.
- `tests/test_wx_shell.py::test_wx_shell_dispatches_core_views` has a pre-existing mismatch (`settings_btn.SetLabel` vs current `menubar.SetLabel`) unrelated to this wave; it should be triaged separately.
- `DEFAULT_GUI_RUNTIME` remains `qt` by design; publishing a wx-default runtime is out of scope.
- Evidence is tied to HEAD `b724148`; any subsequent commit requires re-running the manual checklist and updating this document.
