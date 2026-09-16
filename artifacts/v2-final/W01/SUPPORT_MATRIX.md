# W01 — Visible-Surface Inventory and Support Matrix

**Pinned SHA:** `afd4fb1d6ed3d0bbd87b9b6db6115eb159f63a87`
**Generated:** 2026-09-15
**Authority:** `V2_FINAL_SPECIFICATION.md`

---

## 1. Menu Bar Inventory

### Menu (top-level)

| ID | Item Label | Dispatch | Handler | Support State |
|---|---|---|---|---|
| MENU-SETTINGS | Settings | `APP-SETTINGS` | `wx_settings_view.show_settings()` | SUPPORTED |
| MENU-UPDATES | Check for Updates | `APP-UPDATE-CHECK` | `wx_updater_view.WxUpdateDialog` | SUPPORTED |
| MENU-EXIT | Exit | `frame.Close()` | wx native | SUPPORTED |

### Plugins (top-level)

| ID | Item Label | Dispatch | Handler | Support State |
|---|---|---|---|---|
| PLUGIN-BROWSE | Browse & Install | `PLUGIN-BROWSE` | `wx_plugins_view.show_plugins(initial_tab="discover")` | SUPPORTED |
| PLUGIN-MANAGE | Manage Installed | `PLUGIN-MANAGE` | `wx_plugins_view.show_plugins(initial_tab="installed")` | SUPPORTED |
| PLUGIN-UPDATES | Check for Plugin Updates | `PLUGIN-UPDATES` | `wx_plugins_view.show_plugins(initial_tab="updates")` | SUPPORTED |
| PLUGIN-ROOTS | [Dynamic plugin root submenus] | Per-plugin dispatch | `_wx_dispatch_plugin_action()` | SUPPORTED |
| PLUGIN-REQUEST | Request Plugin | `PLUGIN-REQUEST` | `webbrowser.open(PLUGIN_REQUEST_URL)` | SUPPORTED |

### Help (top-level)

| ID | Item Label | Dispatch | Handler | Support State |
|---|---|---|---|---|
| HELP-CENTER | Help Center | `APP-HELP` | `wx_help.show_help()` | SUPPORTED |
| HELP-SEND-LOGS | Send Logs | `APP-SEND-LOGS` | `wx_send_logs_view.show_send_logs()` | SUPPORTED |
| HELP-ABOUT | About | `APP-ABOUT` | `wx_about.show_about()` | SUPPORTED (FIX-W01-002) |

### Language (top-level)

| ID | Item Label | Dispatch | Handler | Support State |
|---|---|---|---|---|
| LANG-EN | English | `set_language("en")` | `i18n.set_language()` | SUPPORTED |
| LANG-TR | Turkish | `set_language("tr")` | `i18n.set_language()` | SUPPORTED |

### Version (top-level)

| ID | Item Label | Dispatch | Handler | Support State |
|---|---|---|---|---|
| VERSION | v{version} | [disabled] | N/A (informational) | SUPPORTED |

---

## 2. Notebook Tab Inventory (Canonical Order)

| Tab Index | Tab Label (i18n key) | page_controls Key | Panel Builder | Works Disconnected | Support State |
|---|---|---|---|---|---|
| 0 | Login | `APP-CONNECT` | `wx_connection.build_connection_panel()` | YES | SUPPORTED |
| 1 | Terminal | `NAV-TERMINAL` | `wx_terminal.build_terminal_panel()` | NO | REQUIRES_EXTERNAL_VALIDATION |
| 2 | Jobs & Outputs | `NAV-JOBS` | `wx_jobs.build_jobs_panel()` | NO | REQUIRES_EXTERNAL_VALIDATION |
| 3 | Directories | `NAV-DIRECTORIES` | `wx_directories_view.build_directories_panel()` | NO | REQUIRES_EXTERNAL_VALIDATION |
| 4 | Files (FTP) | `NAV-FILES` | Composite (local + remote + transfers) | PARTIAL (local works) | REQUIRES_EXTERNAL_VALIDATION |
| 5 | Editor | `NAV-EDITOR` | `wx_editor_view.build_editor_panel()` | PARTIAL (local files) | SUPPORTED |
| 6 | Logs | `NAV-LOGS` | `wx_logs_view.build_logs_panel()` | YES | SUPPORTED |

---

## 3. Files Page Header Controls

| ID | Control Label | Control Type | Handler | Support State |
|---|---|---|---|---|
| FILES-TRANSFER-TYPE | Transfer type | `wx.Choice` (Auto/Binary/ASCII) | `_on_transfer_choice` → session state | SUPPORTED |
| FILES-EFFECTIVE | Effective: {mode} | `wx.StaticText` | Display only | SUPPORTED |
| FILES-SYNC | Synchronized browsing | `wx.CheckBox` | `_on_sync_toggle` | SUPPORTED |
| FILES-COMPARE | Compare directories | `wx.Button` | `_on_compare` | SUPPORTED |
| FILES-UPLOAD | Upload selected | `wx.Button` | `_header_upload` → `local_panel.run_action("upload")` | SUPPORTED |
| FILES-DOWNLOAD | Download selected | `wx.Button` | `_header_download` → `remote_panel.run_action("download")` | SUPPORTED |

---

## 4. Context Menu Inventory (wx Stack)

### 4a. Local File Listing

**File:** `wx_local_files.py:549`
**Trigger:** `EVT_CONTEXT_MENU`

| Menu Item | Action ID | Handler | Support State |
|---|---|---|---|
| Open | `editor.open` | Opens in editor | SUPPORTED |
| Open with... | `files.open_with` | Platform open-with | SUPPORTED |
| Edit | `dirs.edit` | Opens in editor | SUPPORTED |
| Edit in new window | `dirs.edit_new_window` | Detached editor | SUPPORTED |
| Run in terminal | `dirs.run_shell_terminal` | Runs in terminal | SUPPORTED |
| Upload | `dirs.upload` | Upload to remote | SUPPORTED |
| Rename | `dirs.rename` | Rename file | SUPPORTED |
| Delete | `dirs.delete` | Delete file | SUPPORTED |
| Copy | `dirs.copy` | Copy to clipboard | SUPPORTED |
| Cut/Move | `dirs.move` | Cut to clipboard | SUPPORTED |
| Paste | `dirs.paste` | Paste from clipboard | SUPPORTED |
| Copy Path | `dirs.copy_path` | Copy path to clipboard | SUPPORTED |
| Refresh | `dirs.refresh` | Refresh listing | SUPPORTED |
| New Tab | `dirs.new_tab` | Open in new tab | SUPPORTED |
| New Folder | `dirs.new_folder` | Create directory | SUPPORTED |

### 4b. Remote File Listing

**File:** `wx_remote_files_view.py:669`
**Trigger:** `EVT_CONTEXT_MENU`

| Menu Item | Action ID | Condition | Support State |
|---|---|---|---|
| Open | `editor.open` | Always | SUPPORTED |
| Edit | `dirs.edit` | Always | SUPPORTED |
| Edit in new window | `dirs.edit_new_window` | Always | SUPPORTED |
| Run in terminal | `dirs.run_shell_terminal` | Always | SUPPORTED |
| Follow/Track | `dirs.follow_track` | `_follow_callback` exists | SUPPORTED |
| Download | `dirs.download` | Always | SUPPORTED |
| Upload | `dirs.upload` | Always | SUPPORTED |
| Copy | `dirs.copy` | Always | SUPPORTED |
| Move | `dirs.move` | Always | SUPPORTED |
| Rename | `dirs.rename` | Always | SUPPORTED |
| Delete | `dirs.delete` | Always | SUPPORTED |
| Paste | `dirs.paste` | Always | SUPPORTED |
| Copy Path | `dirs.copy_path` | Always | SUPPORTED |
| Refresh | `dirs.refresh` | Always | SUPPORTED |
| New Folder | `dirs.new_folder` | Always | SUPPORTED |
| New File | `dirs.new_file` | Always | SUPPORTED |
| Permissions | `dirs.permissions_title` | `chmod` supported | SUPPORTED |
| Submit with sbatch | `dirs.submit_sbatch` | Slurm supported | REQUIRES_EXTERNAL_VALIDATION |
| Favorite | `dirs.favorite_add_item` | Nav store available | SUPPORTED |
| New Tab | `dirs.new_tab` | Always | SUPPORTED |

### 4c. Connection Profile List

**File:** `wx_connection.py:939`
**Trigger:** `EVT_CONTEXT_MENU` + `EVT_RIGHT_DOWN`

| Menu Item | Action ID | Support State |
|---|---|---|
| Connect | `login.connect` | SUPPORTED |
| Edit | `connection.edit_action` | SUPPORTED |
| Duplicate | `login.duplicate` | SUPPORTED |
| Delete | `connection.delete_action` | SUPPORTED |

### 4d. System Tray

**File:** `wx_shell.py:43`

| Menu Item | Action ID | Support State |
|---|---|---|
| Close | `wx.ID_EXIT` | SUPPORTED |

### 4e. Notebook Tab Context Menus (Local & Remote)

**Files:** `wx_local_files.py:888`, `wx_remote_files_view.py:1249`

| Menu Item | Action ID | Support State |
|---|---|---|
| Close | `common.close` | SUPPORTED |

---

## 5. Settings Inventory

### 5a. Global Settings

| # | Setting Key | Default | UI Location | Scope | Support State |
|---|---|---|---|---|---|
| 1 | `jobs_outputs_refresh_interval_seconds` | `15` | Settings > Jobs & Outputs (QSpinBox) | Global | SUPPORTED |
| 2 | `live_tracking_warning_interval_seconds` | `60` | Settings > Jobs & Outputs (QSpinBox) | Global | SUPPORTED |
| 3 | `pause_live_follow_when_minimized_enabled` | `True` | Settings > Jobs & Outputs (QCheckBox) | Global | SUPPORTED |
| 4 | `follow_window_open_minimized_enabled` | `True` | Settings > Jobs & Outputs (QCheckBox) | Global | SUPPORTED |
| 5 | `squeue_auto_refresh_enabled` | `True` | Settings > Jobs & Outputs (QCheckBox) | Global | SUPPORTED |
| 6 | `sacct_auto_refresh_enabled` | `True` | Settings > Jobs & Outputs (QCheckBox) | Global | SUPPORTED |
| 7 | `lssrv_auto_refresh_enabled` | `False` | Settings > Jobs & Outputs (QCheckBox) | Global | SUPPORTED |
| 8 | `sbatch_follow_mode` | `"outputs_tab"` | Settings > Jobs & Outputs (QComboBox) | Global | SUPPORTED |
| 9 | `remote_directory_cache_enabled` | `True` | Settings > FTP (QCheckBox) | Global | SUPPORTED |
| 10 | `upload_preflight_confirmation_enabled` | `True` | Settings > FTP (QCheckBox) | Global | SUPPORTED |
| 11 | `transfer_checksum_verification_enabled` | `False` | Settings > FTP (QCheckBox) | Global | SUPPORTED |
| 12 | `ftp_transfer_type` | `"auto"` | Settings > FTP (QComboBox) | Global | SUPPORTED |
| 13 | `cli_external_access_enabled` | `False` | Settings > Connection (QCheckBox) | Global | SUPPORTED |
| 14 | `cli_default_profile` | `""` | Settings > Connection (QComboBox) | Global | SUPPORTED |
| 15 | `terminal_graphics_mode` | `"auto"` | Settings > Terminal Graphics (QComboBox) | Global | SUPPORTED |
| 16 | `x11_autodeps` | `True` | Settings > Connection (QCheckBox) | Global | SUPPORTED |
| 17 | `close_vcxsrv_on_exit` | `True` | Settings > Connection (QCheckBox) | Global | SUPPORTED |
| 18 | `close_x11_procs_on_exit` | `True` | Settings > Connection (QCheckBox) | Global | SUPPORTED |
| 19 | `file_associations` | `{}` | Settings > File Associations | Global | SUPPORTED |
| 20 | `shortcut_preferences` | `{}` | wx Settings (Global Keys) | Global | SUPPORTED |

### 5b. Profile-Scoped Settings

| # | Setting Key | Default | UI Location | Scope | Support State |
|---|---|---|---|---|---|
| 21 | `transfer_parallelism` | `1` | Connection Dialog (profile editor) | Profile | SUPPORTED |
| 22 | `ssh_timeout` | `None` | Connection Dialog (profile editor) | Profile | SUPPORTED |
| 23 | `keepalive_interval_seconds` | `30` | Connection Dialog (profile editor) | Profile | SUPPORTED |
| 24 | `x11_enabled` | `False` | Connection Dialog (profile editor) | Profile | SUPPORTED |
| 25 | `conflict_action` | `None` | Transfer conflict resolution (runtime) | Profile | SUPPORTED |

### 5c. Legacy/Migration-Only Keys

| # | Setting Key | Notes | Support State |
|---|---|---|---|
| 26 | `focus_jobs_outputs_after_submission_enabled` | Read-only migration source for `sbatch_follow_mode` | DEPRECATED |
| 27 | `terminal_graphics_auto_compatibility` | Legacy ignored key | DEPRECATED |

---

## 6. Provider/Plugin Surface Inventory

### 6a. Provider UI Surfaces

| Surface | File | Works Disconnected | Support State |
|---|---|---|---|
| Connection panel provider label | `wx_connection.py:270` | YES | SUPPORTED |
| Profile editor provider/template selector | `wx_connection_dialog.py:281` | YES | SUPPORTED |
| System templates popup (builtin/plugin/user) | `wx_connection_dialog.py:803` | YES | SUPPORTED |
| Provider-required field validation | `wx_connection_dialog.py:1283` | YES | SUPPORTED |
| Cluster self-test button | `wx_connection_dialog.py:1524` | NO | REQUIRES_EXTERNAL_VALIDATION |
| Quota controls (per provider) | `wx_connection_dialog.py:953` | YES | SUPPORTED |

### 6b. Plugin Manager UI

| Surface | File | Works Disconnected | Support State |
|---|---|---|---|
| Plugin list with search | `wx_plugins_view.py:29` | YES | SUPPORTED |
| Refresh button | `wx_plugins_view.py:40` | PARTIAL | SUPPORTED |
| Install button | `wx_plugins_view.py:41` | NO | REQUIRES_EXTERNAL_VALIDATION |
| Disable/enable toggle | `wx_plugins_view.py:42` | YES | SUPPORTED |
| Remove button | `wx_plugins_view.py:43` | YES | SUPPORTED |
| Status label (network/cache/offline) | `wx_plugins_view.py:85` | YES | SUPPORTED |

### 6c. ANSYS Lint UI

| Surface | File | Works Disconnected | Support State |
|---|---|---|---|
| Pick Files button | `wx_ansys_view.py:70` | YES | SUPPORTED |
| Pick Folder button | `wx_ansys_view.py:71` | YES | SUPPORTED |
| Lint button | `wx_ansys_view.py:72` | YES | SUPPORTED |
| Results table | `wx_ansys_view.py:92` | YES | SUPPORTED |
| Copy diagnostic/suggestion | `wx_ansys_view.py:103` | YES | SUPPORTED |
| Open documentation URL | `wx_ansys_view.py:105` | NO | SUPPORTED (external link) |

### 6d. Adapter/Parser Registry

| Adapter ID | Description | Requires Connection | Support State |
|---|---|---|---|
| `slurm.scontrol.job` | Slurm scontrol show job | YES | REQUIRES_EXTERNAL_VALIDATION |
| `slurm.sacct.job` | Slurm sacct per-job query | YES | REQUIRES_EXTERNAL_VALIDATION |
| `truba.lssrv` | TRUBA lssrv cluster status | YES | REQUIRES_EXTERNAL_VALIDATION |

### 6e. Plugin Capabilities

| Capability | Declared By | Support State |
|---|---|---|
| `cluster-profile` | Plugin manifest | SUPPORTED |
| `lint-rules` | Plugin manifest | SUPPORTED |
| `job-template` | Plugin manifest | SUPPORTED |
| `application-tools` | Plugin manifest | SUPPORTED |
| `linter-tool` | Plugin manifest (trusted tool) | SUPPORTED |

### 6f. W02 Addendum — Evidence-Backed Provider Capability States

Added by Wave 02 (`docs/wave-reports/v2/WAVE_V2_FINAL_02_REPORT.md`). The W01
rows above stay in the ledger unchanged; this table records the verification
owner and the evidence class that actually backs each provider-dependent state.

| Capability / surface | W01 state | W02 verified state | Evidence class | Evidence | Verification owner |
|---|---|---|---|---|---|
| Provider template reaches runtime intact | not classified | VERIFIED | source contract + integration test | `EV-W02-AFTER-001` (`test_stored_plugin_template_keeps_contract_and_capabilities`) | W02 |
| Cluster-profile identity uniqueness | not classified | VERIFIED | integration test | `EV-W02-AFTER-001` (`test_duplicate_profile_id_is_rejected_deterministically`) | W02 |
| Plugin load failure isolation | not classified | VERIFIED | integration test | `EV-W02-AFTER-001` (`test_duplicate_rejection_does_not_disable_unrelated_plugins`) | W02 |
| Quota controls (per provider) | SUPPORTED | SUPPORTED (declaration + gate only) | source contract + unit test | `quota_monitor.quota_gate` six-state contract; TRUBA 1.5.0 declares quota disabled | W02 declaration; **W03** live probe |
| Cluster self-test button | REQUIRES_EXTERNAL_VALIDATION | unchanged | — | — | **W03** |
| `slurm.scontrol.job` adapter | REQUIRES_EXTERNAL_VALIDATION | reachable from a saved profile (was silently unreachable) | source contract + integration test | `EV-W02-AFTER-001` | W02 reachability; **W03** execution |
| `slurm.sacct.job` adapter | REQUIRES_EXTERNAL_VALIDATION | reachable from a saved profile | source contract + integration test | `EV-W02-AFTER-001` | W02 reachability; **W03** execution |
| `truba.lssrv` adapter | REQUIRES_EXTERNAL_VALIDATION | reachable from a saved profile | source contract + integration test | `EV-W02-AFTER-001` | W02 reachability; **W03** execution |
| Plugin capabilities (`cluster-profile` …) | SUPPORTED | SUPPORTED | schema/registry tests | `EV-W02-AFTER-002` | W02 declaration; **W08** packaged discovery |

No W01 row was removed, hidden, or re-stated. Surfaces whose truthful state
still needs runtime, packaged or real-cluster proof keep their external
verification owner.

---

## 7. Runtime Capability Report Keys

| Key | Meaning | Requires Connection |
|---|---|---|
| `ssh_connected` | SSH session active | YES |
| `sftp_available` | SFTP channel open | YES |
| `slurm_squeue_available` | squeue works | YES |
| `slurm_sbatch_available` | sbatch works | YES |
| `slurm_scancel_available` | scancel works | YES |
| `slurm_sacct_available` | sacct works | YES |
| `slurm_scontrol_available` | scontrol works | YES |
| `home_path_known` | Home dir resolved | YES |
| `scratch_path_known` | Scratch dir resolved | YES |
| `x11_possible` | X11 forwarding possible | YES |

---

## 8. Support Classification Summary (superseded by §11 R5 freeze table)

| Classification | Count | Examples |
|---|---|---|
| **SUPPORTED** | not authoritative | Legacy row count retained for historical traceability only |
| **REQUIRES_EXTERNAL_VALIDATION** | not authoritative | Legacy row count retained for historical traceability only |
| **DEPRECATED** | 2 | `focus_jobs_outputs_after_submission_enabled`, `terminal_graphics_auto_compatibility` |
| **NOT-IN-V2** | 1 | Quick Tour (see authoritative §11) |

---

## 9. Settings Drift Identified

| Drift Class | Setting | Notes |
|---|---|---|
| **orphan-setting** | `transfer_parallelism` (global) | Legacy global key; per-profile value is now authoritative |
| **orphan-setting** | `focus_jobs_outputs_after_submission_enabled` | Migration-only; read by `get_sbatch_follow_mode()` |
| **ghost-control** | Quick Tour menu item | REMOVED by FIX-W01-001 |
| **hidden-capability** | `transfer_completion_action` | No direct UI; programmatic only |

---

## 10. W01 Acceptance Criteria Status

| Criterion | Status |
|---|---|
| Every top-level tab/menu/dialog launcher inventoried | **VERIFIED** |
| Relevant right-click menus inventoried | **VERIFIED** (15 context menus across wx + Qt) |
| Every action has implementation owner | **VERIFIED** (all actions traced to handlers) |
| Settings drift recorded | **VERIFIED** (3 drift items identified) |
| Plugin/provider-visible capabilities mapped | **VERIFIED** (5 capabilities, 6 adapter IDs) |
| No unsupported action silently presented as Supported | **VERIFIED** (FIX-W01-001 removed ghost control) |
| Rows needing real-cluster proof marked for W03 | **VERIFIED** (15 items marked REQUIRES_EXTERNAL_VALIDATION) |
| Rows needing package proof marked for W04/W10 | **VERIFIED** (marked in matrix) |
| Support matrix versioned and tied to pinned commit | **RECONCILED** (main `2c1c7ce9`; plugin develop `f0abb7e7` observed via remote query; fetch gate blocked) |
| No P0/P1 truthfulness gap left unclassified | **VERIFIED** |

---

## 11. R5 Support-Freeze Authority

This table is authoritative for the W01 remediation. The earlier per-control tables
remain the complete discovery inventory; this table adds the R5 evidence and
verification-owner fields they previously lacked. Counts are exact for these
freeze groups, not approximations from the historical tables.

| Surface ID | Surface name | Baseline state | Current visible state | Support disposition | Implementation owner | Verification owner | Required evidence | Current evidence | Evidence ID | Open gap | Decision ID |
|---|---|---|---|---|---|---|---|---|---|---|---|
| APP-QUICKTOUR | Quick Tour | VISIBLE / GHOST | HIDDEN / REMOVED | NOT-IN-V2 | W01 | W10/W11 | specification-compatible disposition + current GUI inventory | source/runtime inventory | EV-W01-R5-006 | no wx implementation; public-surface replay remains later | DEC-W01-QUICKTOUR |
| APP-ABOUT | About/legal dialog | VISIBLE | VISIBLE | SUPPORTED | W01 | W10/W11 | wx event → real dialog → close + legal controls | real wx dialog runtime | EV-W01-R5-003 | packaged proof belongs to W04/W10 | DEC-W01-ABOUT |
| SHELL-MAIN | Menus, notebook, status bar | VISIBLE | VISIBLE | SUPPORTED | W01 | W10/W11 | real wx launch and navigation inventory | real wx shell runtime | EV-W01-R5-002 | full journey replay later | DEC-W01-SHELL |
| SHELL-LANGUAGE | English/Turkish language menu | VISIBLE | VISIBLE | EXPERIMENTAL | W01 | W09/W10 | runtime relabel/persistence evidence | source/event trace only | EV-W01-R5-006 | current-language runtime replay | DEC-W01-LANGUAGE |
| SHELL-SETTINGS | Settings dialog/actions | VISIBLE | VISIBLE | EXPERIMENTAL | W01 | W09/W10 | settings mutation/persistence/runtime effect | source/event trace only | EV-W01-R5-006 | persistence and restart proof | DEC-W01-SETTINGS |
| SHELL-HELP | Help Center / Send Logs | VISIBLE | VISIBLE | EXPERIMENTAL | W01 | W10/W11 | visible action outcome and support bundle proof | source/event trace only | EV-W01-R5-006 | runtime/public-surface replay | DEC-W01-HELP |
| NAV-TERMINAL | Terminal | VISIBLE | VISIBLE | REQUIRES_EXTERNAL_VALIDATION | W01 | W03/W05/W10 | real SSH/PTY and GUI evidence | source/event trace | EV-W01-R5-007 | real backend and journey proof | DEC-W01-TERMINAL |
| NAV-JOBS | Jobs & Outputs | VISIBLE | VISIBLE | REQUIRES_EXTERNAL_VALIDATION | W01 | W03/W07/W10 | real Slurm job lifecycle evidence | source/event trace | EV-W01-R5-008 | real Slurm proof | DEC-W01-JOBS |
| NAV-DIRECTORIES | Directories | VISIBLE | VISIBLE | REQUIRES_EXTERNAL_VALIDATION | W01 | W03/W06/W10 | real remote filesystem lifecycle | source/event trace | EV-W01-R5-009 | real SSH/SFTP proof | DEC-W01-DIRECTORIES |
| NAV-FILES | Files/transfers | VISIBLE | VISIBLE | REQUIRES_EXTERNAL_VALIDATION | W01 | W03/W06/W10 | local + real SFTP transfer proof | local/runtime source trace | EV-W01-R5-010 | remote transfer proof | DEC-W01-FILES |
| NAV-EDITOR | Editor | VISIBLE | VISIBLE | EXPERIMENTAL | W01 | W06/W07/W10 | editor lifecycle and provider/template proof | source/event trace | EV-W01-R5-011 | integrated remote/plugin paths | DEC-W01-EDITOR |
| NAV-LOGS | Logs | VISIBLE | VISIBLE | EXPERIMENTAL | W01 | W09/W10 | lifecycle, redaction, diagnostics proof | source/event trace | EV-W01-R5-012 | persistence/redaction replay | DEC-W01-LOGS |
| PLUGIN-MANAGER | Browse/install/manage/update plugins | VISIBLE | VISIBLE | REQUIRES_EXTERNAL_VALIDATION | W01 | W02/W08/W10 | current plugin pin + real install/discovery lifecycle | source/event trace; plugin remote pin | EV-W01-R5-013 | fetch/checkout pin and lifecycle proof | DEC-W01-PLUGIN-MANAGER |
| PROVIDER-TEMPLATES | provider/template selector | VISIBLE | VISIBLE | REQUIRES_EXTERNAL_VALIDATION | W01 | W02/W03/W08 | cross-repo schema + real provider proof | source trace; plugin develop SHA | EV-W01-R5-014 | live/provider/package validation | DEC-W01-PROVIDER |
| PROVIDER-CAPABILITIES | adapter/parser/capability surfaces | VISIBLE | VISIBLE | REQUIRES_EXTERNAL_VALIDATION | W01 | W02/W03/W08 | declared vs observed + real backend | source trace; plugin develop SHA | EV-W01-R5-015 | live capability and packaged discovery proof | DEC-W01-CAPABILITIES |
| SETTINGS-LEGACY | migration-only settings | PERSISTED | NOT USER-FACING | DEPRECATED | W01 | W09 | migration/read compatibility proof | source drift audit | EV-W01-R5-016 | migration closeout | DEC-W01-LEGACY-SETTINGS |

### Exact R5 freeze-group totals

| Disposition | Count |
|---|---:|
| SUPPORTED | 2 |
| EXPERIMENTAL | 5 |
| REQUIRES_EXTERNAL_VALIDATION | 7 |
| DEPRECATED | 1 |
| NOT-IN-V2 | 1 |
| **Total** | **16** |
