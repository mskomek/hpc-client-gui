# Action Inventory — Qt vs wx (3a72940)

| Action ID | Qt Label | wx Label | Qt Placement | wx Placement | Qt Enabled | wx Enabled | Qt Icon | wx Icon | Shortcut | Opens | Notes | Screenshot |
|-----------|----------|----------|--------------|--------------|------------|------------|---------|---------|----------|-------|-------|------------|
| APP-HELP | Help | Help | Help menu, F1, chrome Help button | chrome Help button (`help_btn`), Help menu | yes | yes | - | - | F1 | dialog `HelpDialog` | | `qt/120-help-default.png` / `wx/150-menu-file.png` |
| APP-UPDATE | Update | Update | chrome Update button, menu | chrome `update_btn` | yes | yes | - | - | - | `UpdateSplash` / `wx_lifecycle` check | | `qt/01-main-default.png` / `wx/01-main-default.png` |
| APP-PLUGINS | Plugins | Plugins | chrome Plugins | chrome `plugins_btn` | yes | yes | - | - | - | `PluginManagerDialog` / `show_plugins` | | `qt/110-plugins-default.png` / `wx/110* MISSING` |
| APP-SETTINGS | Settings | Settings | SettingsDialog | chrome `settings_btn` → `show_settings` | yes | yes | - | - | - | dialog | `qt/100-settings-default.png` / `wx/100-settings-default.png` |
| APP-SEND-LOGS | Send Logs | Send Logs | chrome Send Logs | chrome `send_logs_btn` → `show_send_logs` | yes | yes | - | - | - | `SendLogsDialog` | | `qt/80-logs-default.png` / `wx/80-logs-default.png` |
| LANG-EN | English | English | Language menu radio | Language menu radio + `language_button` (flag) | yes (checked if en) | yes | flag gb.svg | flag bitmap | - | - | | `qt/170-language-english.png` / `wx/170-language-english.png` |
| LANG-TR | Turkish | Turkish | Language menu | Language menu radio + button | yes | yes | flag tr.svg | flag | - | - | | `qt/171-language-turkish.png` / `wx/171-language-turkish.png` |
| CONN-ADD | New / Add Connection |Add Connection| Connection tab `LoginWidget` | `build_connection_panel` | yes | visible but disabled until callback | - | - | - | `ConnectionDialog` | | `qt/02-connection-default.png` / `wx/02-connection-default.png` |
| CONN-CONNECT | Connect | Connect Selected | Connection | Connection | yes (if profile) | yes | - | - | - | session | | |
| JOBS-REFRESH | Refresh | Refresh | Jobs toolbar | `jobs` `refresh_button` + `files_refresh` + `outputs_refresh` | yes | yes | - | - | - | `list_jobs` | | `qt/10-jobs-default.png` / `wx/10-jobs-default.png` |
| JOBS-CANCEL | Cancel | Cancel | Jobs toolbar | `cancel_button` | yes (if job) | yes | - | - | - | `scancel` | | |
| JOBS-OPEN-OUTPUT | Open Output | Open Output | Jobs toolbar | `detached_button` | yes | yes | - | - | - | detached `show_job_output` | | |
| JOBS-FILES-TAB | Files | Files | JobsOutputsWidget subtab | `notebook` page 1 `jobs_outputs.files_title` | yes | yes | - | - | - | ListCtrl `job_files` | | `qt/13-jobs-files.png` / `wx/13-jobs-files.png` (alias) |
| JOBS-OUTPUTS-TAB | Outputs | Outputs | JobsOutputsWidget subtab | `notebook` page 2 `jobs_outputs.outputs_title` | yes | yes | - | - | - | TextCtrl `outputs_stdout`/`stderr` | | `qt/14-jobs-outputs.png` / `wx/14-jobs-outputs.png` |
| FILES-SYNC | Synchronized browsing | Synchronized browsing | Files header CheckBox | `sync_cb` CheckBox | yes | yes (enabled) | - | - | - | `SyncRoots` guard | | `qt/30-files-default.png` / `wx/30-files-default.png` |
| FILES-COMPARE | Compare directories | Compare directories | Files header Button | `compare_btn` Button (WrapSizer) | yes | yes | - | - | - | `compare_directory_entries` → TextCtrl result | | |
| FILES-UPLOAD | Upload Selected | Upload Selected | Files header `Upload` | `upload_selected_btn` | yes | yes | - | - | - | `TransferItem` | | |
| FILES-DOWNLOAD | Download Selected | Download Selected | Files header `Download` | `download_selected_btn` | yes | yes | - | - | - | `TransferItem` | | |
| EDITOR-OPEN | Open | Open | Editor header | `btn_open` | yes | disabled until callback | - | - | - | `on_open` | | `qt/60-editor-default.png` / `wx/60-editor-default.png` |
| EDITOR-NEW-TEMPLATE | New from Template | New from Template | Editor header | `btn_template` | yes | disabled | - | - | - | `on_new_template` | | |
| EDITOR-LINT | Lint | Lint | Editor header | `btn_lint` | yes | disabled | - | - | - | `on_lint` or internal SBATCH checks | | |
| EDITOR-SAVE | Save | Save | Editor header | `save` Button | yes | yes (if not in_flight) | - | - | Ctrl+S | `save_remote` / local write | | |
| EDITOR-SUBMIT | Submit | Submit | Editor footer | `submit` Button | yes | yes | - | - | - | `slurm.sbatch` | | |
| EDITOR-RUN | Save+Submit | Save+Submit | Editor footer | `run` Button | - (wx only) | yes | - | - | - | | | |
| TERMINAL-FIND | Find | Find | Terminal toolbar (Qt embedded) | Terminal toolbar `Find` TextCtrl+Button | yes | yes | - | - | Ctrl+F | `TerminalModel.find` | wx-only primary tab vs Qt embedded | `wx/72-terminal-find.png` / `qt-only-*` |
| TERMINAL-CLEAR | Clear | Clear | Terminal toolbar | `Clear` Button | yes | yes | - | - | - | `clear` | | `wx/73-terminal-font-controls.png` |
| TERMINAL-A- | A- | A- | Terminal toolbar | `A-` Button | yes | yes | - | - | - | `change_font_size(-1)` | | |
| TERMINAL-A+ | A+ | A+ | Terminal toolbar | `A+` Button | yes | yes | - | - | - | `change_font_size(+1)` | | |
| LOGS-REFRESH | Refresh | Refresh | Logs toolbar | `btn_refresh` | yes | yes | - | - | - | `WxLogsModel.refresh` off-thread | | `qt/80-logs-default.png` / `wx/80-logs-default.png` |
| LOGS-COPY | Copy | Copy | Logs toolbar | `btn_copy` | yes | yes | - | - | - | clipboard | | |
| LOGS-COPY-PATH | Copy Path | Copy Path | Logs toolbar | `btn_copy_path` | yes | yes | - | - | - | clipboard | | |
| LOGS-EXPORT | Export Diagnostics | Export Diagnostics | Logs toolbar | `btn_diag` → `DirDialog` → `bundle` Thread | yes | yes | - | - | - | `create_diagnostic_bundle` ZIP | | `qt/81-logs-populated.png` / `wx/82-logs-actions.png` |
| ANSYS-PICK-FILES | Pick Files | Pick Files | ANSYS dialog `Pick Files` | `build_ansys_frame` `Pick Files` Button | yes | yes | - | - | - | `lint_files` | | `wx/90-ansys-default.png` / `qt/90* MISSING` |
| ANSYS-PICK-FOLDER | Pick Folder | Pick Folder | ANSYS | `Pick Folder` Button | yes | yes | - | - | - | `lint_folder` 200 cap | | |
| ANSYS-LINT | Lint | Lint | ANSYS | `Lint` Button | yes | yes | - | - | - | engine → grouped ListCtrl | | `wx/92-ansys-results.png` |
| ANSYS-CLEAR | Clear | Clear | ANSYS | `Clear` Button | yes | yes | - | - | - | - | | |
| SETTINGS-APPLY | Apply | Apply | SettingsDialog Apply | `btn_apply` | yes | yes | - | - | - | `WxSettingsModel.apply` thread | | `qt/100-settings-default.png` / `wx/100-settings-default.png` |

**Enabled states:** Qt and wx both disable `Add Connection` until callback, editor `Open`/`New Template`/`Lint` disabled until callback (wx shows disabled, Qt similar). File `Sync`/`Compare` enabled in wx (for test seam) vs Qt may disable until connected — documented as enabled in this capture (wx header `sync_cb` enabled, `compare_btn` enabled).

**Placement:** Qt uses `QTabWidget` + `QVBoxLayout` per tab; wx uses `wx.Notebook` + `wx.BoxSizer`/`WrapSizer` + `SplitterWindow`. Header chrome row order `Update, Plugins, Send Logs, Settings, Help, Language, version` same.

**Screenshots:** See `MANIFEST.md` per action.
