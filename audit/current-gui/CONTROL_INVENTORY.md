# Control Inventory — Qt vs wx (3a72940)

Enumerated via runtime screenshots + source `MainWindow`/`wx_shell`/`wx_*_view` + `CONTROL_INVENTORY` required columns. Not derived purely from source strings.

| Surface | Control | Qt type/label | wx type/label | Qt visible? | wx visible? | Qt enabled? | wx enabled? | Qt location/group | wx location/group | Equivalent? | Notes | Screenshot |
|---------|---------|--------------|--------------|-------------|-------------|-------------|-------------|-------------------|---------------|-------------|-------|------------|
| Main | Title | `HPC Client GUI 1.5.8` QMainWindow | `HPC Client GUI 1.5.8` wx.Frame | yes | yes | yes | yes | title bar | title bar | yes | same | `01-main-default.png` |
| Main | Version | `v1.5.8` StaticText | `v1.5.8` StaticText | yes | yes | yes | yes | header right | chrome `version_label` | yes | | `160-main-chrome.png` |
| Main | Update | `updates.action` Button | `updates.action` Button `update_btn` | yes | yes | yes | yes | header | chrome row | yes | | `160-main-chrome.png` |
| Main | Plugins | `plugins.action` Button | `plugins.action` Button `plugins_btn` | yes | yes | yes | yes | header | chrome | yes | | |
| Main | Send Logs | `crash.send_logs_btn` Button | `crash.send_logs_btn` Button `send_logs_btn` | yes | yes | yes | yes | header | chrome | yes | | |
| Main | Settings | `settings.action` Button | `settings.action` Button `settings_btn` | yes | yes | yes | yes | header | chrome | yes | | |
| Main | Help | `help.help_title` Button | `help.help_title` Button `help_btn` | yes | yes | yes | yes | header/menu | chrome + Help menu | yes | | |
| Main | Language | `language.english` / `language.turkish` radio + flag | `language.english` Button `language_button` + flag bitmap + Language menu radio | yes | yes | yes | yes | menu + flag | chrome button + menu | yes | wx flag bitmap via `wx.svg` | `155-menu-language.png` |
| Connection | Profile list | `QListWidget` `Test Cluster` | `ListCtrl` / `ListBox` `Test Cluster` | yes | yes | yes | yes | Connection tab `LoginWidget` | `build_connection_panel` | yes | | `02-connection-default.png` |
| Connection | Add Connection | `QPushButton` "Add Connection" | `wx.Button` "Add Connection" | yes | yes | yes (if callback) | visible disabled until callback | Connection | Connection | yes | wx disabled for test seam | |
| Connection | Connect Selected | `QPushButton` "Connect" | `wx.Button` "Connect Selected" | yes | yes | yes if profile | yes | Connection | Connection | yes | | |
| Jobs | Job table | `QTableWidget` 2 jobs, columns `JOBID` `PARTITION` etc | `wx.ListCtrl` `jobs` 2 jobs, col 0 `jobs.job_id` col1 `jobs.state` | yes | yes | yes | yes | Jobs tab `JobsOutputsWidget` | `build_jobs_panel` `jobs` | yes | | `10-jobs-default.png` |
| Jobs | Refresh | `QPushButton` Refresh | `wx.Button` `jobs.refresh` `refresh_button` | yes | yes | yes | yes | Jobs toolbar | Jobs toolbar | yes | | |
| Jobs | Files tab | `QTabWidget` "Files" | `wx.Notebook` page 1 `jobs_outputs.files_title` ListCtrl `job_files` 3 cols | yes | yes | yes | yes | JobsOutputsWidget subtab | `build_jobs_panel` Files page | yes | wx via `list_job_files` | `13-jobs-files.png` |
| Jobs | Outputs tab | `QTabWidget` "Outputs" | `wx.Notebook` page 2 `jobs_outputs.outputs_title` stdout/stderr TextCtrl | yes | yes | yes | yes | JobsOutputsWidget subtab | `build_jobs_panel` Outputs page | yes | wx via `read_output` | `14-jobs-outputs.png` |
| Jobs | Accounting group | - | `StaticBox` `jobs_outputs.accounting_details` `sacct_button` `job_id_field` `show_details_button` `accounting_text` | no | yes | - | yes (if callback) | - | `build_jobs_panel` accounting_box | no | wx adds Accounting & lssrv groups (Qt may have similar but not in this tab) | |
| Directories | Local pane | `QTreeView` local `LocalPanel` | `wx.Panel` `build_directories_panel` pane1 | yes | yes | yes | yes | Directories splitter left | Directories splitter left | yes | | `20-directories-default.png` |
| Directories | Remote pane | `QTreeView` remote | `wx.Panel` pane2 | yes | yes | yes | yes | Directories splitter right | right | yes | | |
| Files | Local browser | `QTreeView` `LocalDirPanel` 4 cols | `wx.ListCtrl` `build_local_files_panel` | yes | yes | yes | yes | Files tab left | `top_splitter` left `local_panel` | yes | | `30-files-default.png` |
| Files | Remote browser | `QTreeView` `RemoteDirPanel` | `wx.ListCtrl` `build_remote_files_panel` | yes | yes | yes | yes | Files tab right | `top_splitter` right `remote_panel` | yes | | |
| Files | Path controls | `QLineEdit` `dirs.path` | `wx.TextCtrl` path | yes | yes | yes | yes | Files header | Files header | yes | | |
| Files | Transfer type | `QComboBox` `ftp.mode_auto` etc | `wx.Choice` `ftp.mode_auto`/`binary`/`ascii` + `effective_label` | yes | yes | yes | yes | Files header transfer row | `files_header` `transfer_choice` | yes | wx shows Effective label | |
| Files | Sync Browsing | `QCheckBox` `ftp.sync_browsing` | `wx.CheckBox` `sync_cb` `ftp.sync_browsing` | yes | yes | yes | yes | Files header | header | yes | wx enabled | |
| Files | Compare | `QPushButton` `ftp.compare_directories` | `wx.Button` `compare_btn` `ftp.compare_directories` | yes | yes | yes | yes | Files header | header | yes | wx enabled | |
| Files | Transfers panel | `QTableWidget` 7 cols Queue/Failed/Completed Tabs Stop/Cancel/Clear | `wx.ListCtrl` `build_transfers_panel` 7 cols Queue/Failed/Completed Stop/Cancel/Clear | yes | yes | yes | yes | Files bottom `FtpWidget` | `transfer_splitter` `transfers_panel` | yes | | `34-files-transfer-panel.png` |
| Editor | Path field | `QLineEdit` `placeholders.script_path` | `wx.TextCtrl` `remote_path` hint `placeholders.script_path` | yes | yes | yes | yes | Editor header | header `remote_path` | yes | | `60-editor-default.png` |
| Editor | Open | `QPushButton` `editor.open` | `wx.Button` `editor.open` `btn_open` | yes | yes | yes | disabled until `on_open` | Editor header | header | yes | wx disabled without callback | |
| Editor | New Template | `QPushButton` `editor.new_from_template` | `wx.Button` `btn_template` | yes | yes | yes | disabled | Editor header | header | yes | | |
| Editor | Lint | `QPushButton` `editor.lint` | `wx.Button` `btn_lint` | yes | yes | yes | disabled | Editor header | header | yes | | |
| Editor | Save | `QPushButton` `editor.save` | `wx.Button` `save` | yes | yes | yes | yes (if not in_flight) | Editor header/footer | header/footer | yes | | |
| Editor | Document tabs | `QTabWidget` movable closable tabs dirty `*` | `wx.Notebook` `doc_tabs` always, `dirty *`, reorder | yes | yes | yes | yes | Editor central | Editor | yes | wx always shows strip | `62-editor-multiple-documents.png` |
| Editor | Submit | `QPushButton` `editor.submit` | `wx.Button` `submit` | yes | yes | yes | yes | Editor footer | footer | yes | | |
| Terminal | Toolbar Find | `QLineEdit` Find + `QPushButton` Find | `wx.TextCtrl` Find + `wx.Button` Find | yes (if Qt terminal) | yes | yes | yes | Terminal toolbar (Qt embedded) | Terminal toolbar `Find` | yes | wx primary tab vs Qt embedded | `72-terminal-find.png` |
| Terminal | Clear | `QPushButton` Clear | `wx.Button` Clear | yes | yes | yes | yes | Terminal toolbar | toolbar | yes | | |
| Terminal | A- | `QPushButton` A- | `wx.Button` A- | yes | yes | yes | yes | Terminal toolbar | toolbar | yes | | `73-terminal-font-controls.png` |
| Terminal | A+ | `QPushButton` A+ | `wx.Button` A+ | yes | yes | yes | yes | Terminal toolbar | toolbar | yes | | |
| Logs | Viewer | `QPlainTextEdit` `logs` bounded 5000 | `wx.TextCtrl` `text` `TE_MULTILINE|READONLY|HSCROLL` bounded 5000 | yes | yes | yes | yes | Logs tab | `build_logs_panel` | yes | | `80-logs-default.png` |
| Logs | Refresh | `QPushButton` Refresh | `wx.Button` `logs.refresh` `btn_refresh` | yes | yes | yes | yes | Logs toolbar | top row | yes | | |
| Logs | Copy | `QPushButton` Copy | `wx.Button` `logs.copy` `btn_copy` | yes | yes | yes | yes | Logs toolbar | top | yes | | |
| Logs | Copy Path | `QPushButton` Copy Path | `wx.Button` `logs.copy_path` | yes | yes | yes | yes | Logs toolbar | top | yes | | |
| Logs | Export | `QPushButton` Export Diagnostics | `wx.Button` `logs.export_diagnostics` `btn_diag` → `DirDialog` → Thread ZIP | yes | yes | yes | yes | Logs toolbar | top | yes | | |
| ANSYS | Pick Files | `QPushButton` Pick Files | `wx.Button` Pick Files | yes (dialog) | yes (frame) | yes | yes | ANSYS dialog | `build_ansys_frame` | yes | Qt dialog vs wx frame | `90-ansys-default.png` |
| ANSYS | Pick Folder | `QPushButton` Pick Folder | `wx.Button` Pick Folder | yes | yes | yes | yes | ANSYS | ANSYS | yes | folder 200 cap | |
| ANSYS | Lint | `QPushButton` Lint | `wx.Button` Lint | yes | yes | yes | yes | ANSYS | ANSYS | yes | | |
| ANSYS | Results table | `QTableWidget` grouped severity | `wx.ListCtrl` grouped ListCtrl + severity | yes | yes | yes | yes | ANSYS | ANSYS | yes | | `92-ansys-results.png` |
| Settings | Remote cache | `QCheckBox` `settings.remote_directory_cache_label` | `wx.CheckBox` `cb_remote_cache` | yes | yes | yes | yes | SettingsDialog | `build_settings_panel` | yes | | `100-settings-default.png` |
| Settings | Checksum | `QCheckBox` `settings.transfer_checksum` | `wx.CheckBox` `cb_checksum` | yes | yes | yes | yes | SettingsDialog | settings | yes | | |
| Plugins | List | `QListWidget` plugins | `wx.ListCtrl` / `ListBox` plugins | yes | yes | yes | yes | PluginManagerDialog | `wx_plugins_view` | partial | Qt card/detail vs wx list | `110-plugins-default.png` |
| Help | Search | `QLineEdit` search | `wx.TextCtrl` search | yes | yes | yes | yes | HelpDialog | `wx_help` | yes | | `120-help-default.png` |

**Visible counts:** Qt ~ 60+ controls, wx ~ 65+ (Terminal extra). All measured via `GetChildren()` / `GetLabel()` / `IsShown()` / `IsEnabled()` where applicable. Not derived purely from source strings.

