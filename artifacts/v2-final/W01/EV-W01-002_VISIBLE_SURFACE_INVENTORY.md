# EV-W01-002 — Visible-Surface Inventory

**Pinned SHA:** `afd4fb1d6ed3d0bbd87b9b6db6115eb159f63a87`
**Generated:** 2026-09-15

---

## Notebook Tab Order (Canonical)

| Index | Tab Label | i18n Key | page_controls Key | Panel Builder |
|---|---|---|---|---|
| 0 | Login | `tabs.login` | `APP-CONNECT` | `wx_connection.build_connection_panel()` |
| 1 | Terminal | `help.section_terminal` | `NAV-TERMINAL` | `wx_terminal.build_terminal_panel()` |
| 2 | Jobs & Outputs | `tabs.jobs_outputs` | `NAV-JOBS` | `wx_jobs.build_jobs_panel()` |
| 3 | Directories | `tabs.directories` | `NAV-DIRECTORIES` | `wx_directories_view.build_directories_panel()` |
| 4 | Files (FTP) | `tabs.ftp` | `NAV-FILES` | Composite (local + remote + transfers) |
| 5 | Editor | `tabs.editor` | `NAV-EDITOR` | `wx_editor_view.build_editor_panel()` |
| 6 | Logs | `tabs.logs` | `NAV-LOGS` | `wx_logs_view.build_logs_panel()` |

---

## Menu Bar Structure

### Menu (`menu.menu`)
| Item | i18n Key | Dispatch | Handler |
|---|---|---|---|
| Settings | `menu.settings` | `APP-SETTINGS` | `wx_settings_view.show_settings()` |
| Check for Updates | `menu.check_updates` | `APP-UPDATE-CHECK` | `wx_updater_view.WxUpdateDialog` |
| ---separator--- | | | |
| Exit | `menu.exit` | `wx.ID_EXIT` | `frame.Close()` |

### Plugins (`menu.plugins`)
| Item | i18n Key | Dispatch | Handler |
|---|---|---|---|
| Browse & Install | `menu.browse_install` | `PLUGIN-BROWSE` | `wx_plugins_view.show_plugins(initial_tab="discover")` |
| Manage Installed | `menu.manage_installed` | `PLUGIN-MANAGE` | `wx_plugins_view.show_plugins(initial_tab="installed")` |
| Check for Plugin Updates | `menu.check_plugin_updates` | `PLUGIN-UPDATES` | `wx_plugins_view.show_plugins(initial_tab="updates")` |
| ---separator--- | | | |
| [Dynamic plugin roots] | per-plugin | per-plugin | `_wx_dispatch_plugin_action()` |
| ---separator--- | | | |
| Request Plugin | `menu.request_plugin` | `PLUGIN-REQUEST` | `webbrowser.open(PLUGIN_REQUEST_URL)` |

### Help (`menu.help`)
| Item | i18n Key | Dispatch | Handler |
|---|---|---|---|
| Help Center | `menu.help_center` | `APP-HELP` | `wx_help.show_help()` |
| Send Logs | `menu.send_logs` | `APP-SEND-LOGS` | `wx_send_logs_view.show_send_logs()` |
| About | `menu.about` | `APP-ABOUT` | `wx_about.show_about()` (FIX-W01-002) |

### Language (`help.language`)
| Item | i18n Key | Dispatch | Handler |
|---|---|---|---|
| English | `language.english` | `set_language("en")` | `i18n.set_language()` |
| Turkish | `language.turkish` | `set_language("tr")` | `i18n.set_language()` |

### Version (`v{version}`)
| Item | i18n Key | Dispatch | Handler |
|---|---|---|---|
| v{version} | N/A | [disabled] | N/A (informational) |

---

## Files Page Header Controls

| Control | i18n Key | Type | Handler |
|---|---|---|---|
| Transfer type | `ftp.transfer_type` | `wx.Choice` (Auto/Binary/ASCII) | `_on_transfer_choice` |
| Effective type | `ftp.effective_type` | `wx.StaticText` | Display only |
| Synchronized browsing | `ftp.sync_browsing` | `wx.CheckBox` | `_on_sync_toggle` |
| Compare directories | `ftp.compare_directories` | `wx.Button` | `_on_compare` |
| Upload selected | `ftp.upload_selected` | `wx.Button` | `_header_upload` |
| Download selected | `ftp.download_selected` | `wx.Button` | `_header_download` |

---

## Status Bar

| Property | Value |
|---|---|
| Initial text | `t("common.ready")` |
| On language change | Reset to `t("common.ready")` |

---

## System Tray

| Menu Item | Dispatch | Handler |
|---|---|---|
| Close | `wx.ID_EXIT` | `frame.Close()` |

---

## Dispatch Map

| Command ID | Handler | Dialog/Frame |
|---|---|---|
| `APP-HELP` | `wx_help.show_help()` | Frame |
| `APP-SETTINGS` | `wx_settings_view.show_settings()` | Dialog |
| `APP-UPDATE-CHECK` | `wx_updater_view.WxUpdateDialog` | Dialog |
| `APP-SEND-LOGS` | `wx_send_logs_view.show_send_logs()` | Dialog |
| `APP-ABOUT` | `wx_about.show_about()` | Dialog |
| `PLUGIN-BROWSE` | `wx_plugins_view.show_plugins(initial_tab="discover")` | Dialog |
| `PLUGIN-MANAGE` | `wx_plugins_view.show_plugins(initial_tab="installed")` | Dialog |
| `PLUGIN-UPDATES` | `wx_plugins_view.show_plugins(initial_tab="updates")` | Dialog |
| `PLUGIN-REQUEST` | `webbrowser.open(PLUGIN_REQUEST_URL)` | External browser |
| `APP-CONNECT` | `wx_connection.show_connection()` | Dialog |
| `NAV-FILES` | `wx_local_files.show_local_files()` | Frame |
| `NAV-DIRECTORIES` | `wx_directories_view.show_directories()` | Frame |
| `NAV-LOGS` | `wx_logs_view.show_logs()` | Frame |
| `NAV-EDITOR` | `editor_manager.open_primary()` | Embedded |
| `NAV-TERMINAL` | `wx_terminal.show_terminal()` | Frame |
| `NAV-JOBS` | `wx_jobs.show_jobs()` | Frame |
| `PLUGIN-ANSYS-LINTER` | `wx_ansys_view.show_ansys_lint()` | Frame |
